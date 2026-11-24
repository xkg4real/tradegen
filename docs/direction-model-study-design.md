# Direction model study design (research only)

Status: proposed, 2026-11-24 (Asia/Seoul), revised after the main session's review. Checklist item M11-T6, after
the owner chose option (a) for O32 (2026-11-24 19:05:53 KST): a separate direction model, built in TRADEGEN
research, that uses QUANTGEN DIDM records and QuantGPT judgments as features. This document is a design and has no
code. Implementation waits for the owner decisions in section 10.

The study's forecasts are research inputs. They never become an order input, an approval or a signed term. Every
rule in `docs/direction-forecast-contract.md` section 5 applies, and this study adds its own tools to it:

- **Imports.** No module in the D14 code closure imports the feature builder, the fit-and-freeze tool, the forecast
  writer, the adapter, the bridge, or any QuantGPT or QUANTGEN code. Check: no `tools/research/` path appears in
  `code_files(repo_root)`. Every tool PR in section 12 runs this check.
- **Flags.** Every report or manifest the three new tools write states `research_only=true`, `live_eligible=false`,
  `execution_ready=false`, `source_authenticated=false` and `owner_approval_verified=false`, as the bridge and the
  adapter already do. The `tradegen-direction-forecast-v1` format cannot carry these flags, so the forecast writer
  writes a manifest beside each snapshot.
- **No release, no signal.** A forecast never clears an alert, an entry block, a daily stop, a floor halt or a loss
  stop, and never creates an entry or sell signal. Under `CLAUDE.md` section 7.5 no path leads to `entry_unblock`,
  whatever benefit metric OQ9 later defines (section 10, row 15).
- **Signed terms.** The 5% maximum, the owner's signed ceiling and every other signed term stay. A forecast cannot
  change any of them.
- **Producers.** QuantGPT and QUANTGEN never touch orders, signatures, keys, `.env` or the real home directory.

## 1. The question and the default answer

**Question.** Can a direction forecast built from TRADEGEN's own price bars, plus DIDM records and QuantGPT
judgments, choose BR-26's working Y better than two alternatives?

- a static Y at the ceiling;
- an adaptive Y driven by a forecast from prices alone (B1).

**Default answer.** No. The answer becomes yes only if the success criteria in section 7 hold on forward data
registered before it is collected. Without that evidence BR-26 would keep a static Y. BR-26 is not yet part of the
runtime, and no Y has been signed (O18 is open), so the ceiling the study uses is itself an owner decision
(section 10, row 7).

**Two stages.**

- **Stage 1** asks whether the model has directional skill beyond prices (criteria 1, 2 and 4).
- **Stage 2** runs only if stage 1 passes. It asks whether that skill improves BR-26 on recorded quotes (criterion 3).

**Prior.** The prior is weak. Public news reaches DIDM with a delay of minutes to days. Many participants see the
same news, and crypto direction over hours is hard to predict after costs. Section 6 shows that under realistic
skill the most likely result of stage 1 is "inconclusive". The design reports that outcome rather than stretching
the test until it passes.

## 2. Where the study sits

```text
TRADEGEN Upbit bars ─┐
DIDM snapshot ───────┼─> point-in-time feature table ─> frozen model ─> forecasts + manifest
QuantGPT snapshots ──┘         (owner PC, private)       (sha256)       (tradegen-direction-forecast-v1)
                                                                              │
                         BR-26 replay <── adapter (PR #75) <───────────────────┘
```

- **Price bars.** TRADEGEN's own Upbit record. A bar's `known_at` is when this PC actually had it.
- **DIDM.**
  - Read only through `tools/research/didm_source_bridge.py`.
  - The owner's store is above the bridge's 64 MiB limit on `main`. Reading it needs PR #76 merged (O39); until
    then the bridge refuses the store.
  - One bridge report lists every version of every record, with receipt times. The bridge's
    `selected_record_sha256` is right only for that report's cutoff. So, for each bar, the feature builder applies
    the bridge's rule again:
    - among each (`source_id`, `item_id`), take the latest record with `received_at` at or before `as_of`;
    - ties go to the higher `payload_sha256`.
  - A test checks the feature builder's selection against the bridge's at several cutoffs.
- **DIDM V0 scores (D3).**
  - The bridge reads V0 scores only from the `tradegen-didm-exchange-v1` JSON. That route has limits of 64 MiB,
    parsed in memory, and 25,000 scores.
  - QUANTGEN does not export that format, and the owner's store is already about 123 MiB.
  - D3 therefore needs either windowed QUANTGEN exports within those limits, or a bridge change that reads score
    rows from SQLite. Without one of them D3 is dropped.
- **QuantGPT.**
  - Its recorded outputs (M11-T7) are read as explicit snapshot files with a hash. The model is never run during
    replay.
  - A record is known at the later of its `issued_at` and its receipt on the owner's PC. While records lack
    `issued_at`, as v0.1 does, its `as_of` stands in for it (contract section 3, rule 7).
- **Upstream identity.** The M11-T4 record pins the identities that produce Q1 and D3:
  - QuantGPT's `model.id`, `model.adapter`, `model.prompt_version` and decoding settings;
  - DIDM V0's `model_version` and `prompt_sha256`.

  Every snapshot read checks these identities and the snapshot's creation time. A change stops the study (S4).
- **Storage.** All code lives in `tools/research/`. The following stay in a private folder on the owner's PC,
  outside Git and OneDrive: the fitted model, the feature tables, the forecasts and quote records, the owner's
  section 10 answers, and the M11-T4 record. The reason is that DIDM data rights are unverified, and everything
  else is derived from that data. Only code, this design and SHA-256 values go into the public repository. The
  owner should not post section 10 answers on the public PR.

## 3. Time scales and how Y behaves

BR-26 works on two time scales:

- **Seconds.** Each quote is checked. If the last trade is older than 30 seconds and the bid is at or below
  `last × (1 − Y)`, the alert triggers.
- **Hours.** A forecast can only propose a change to the working Y.

**What happens to Y in the replay** (`tools/research/adaptive_bid_gap_replay.py`):

- **Tightening.** A qualified "down" call tightens Y from the next observation.
- **Widening.** A qualified "up" call widens Y only after a later clean observation confirms it, before the
  forecast expires.
- **After the forecast expires.** The working Y does not change back. It stays until a later qualified proposal
  changes it. A widening to `up_y` can therefore last far beyond its horizon. Only a pending widening confirmation
  expires with the forecast.
- **No live forecast.** If a bar's features are incomplete, no forecast is written for that bar. The previous
  forecast stays live until its window closes. After that, with no live forecast, the working Y stays as it is.

The inputs cannot support a seconds-scale forecast:

- GDELT arrives in 15-minute files.
- ALFRED and OpenDART have only date precision, and ECOS has no release time. The bridge flags all three
  `PRECISE_RELEASE_TIME_UNAVAILABLE`.
- QuantGPT runs on request.

Proposal (section 10, row 1):

| Term | Proposed value | Reason |
| --- | --- | --- |
| Bar | 1 hour (`step_seconds` 3600) | The replay history holds at most 1,024 bars. Hourly bars cover about 42 days; 15-minute bars cover 10.7. |
| Horizon | 2 bars (7,200 s) | Up to 12 non-overlapping outcome windows per day. It is the shortest horizon the adapter allows. |
| Forecast time | Every bar close | The adapter accepts only `as_of` on the bar grid. |
| Quotes | Unchanged, seconds | A forecast never changes the alert test itself, only the Y the test uses. |

## 4. Inputs and features

**Feature cutoff.** A feature at `as_of` uses only inputs known at or before `as_of`. The bar that ends at `as_of`
is known only after `as_of`, because `known_at` comes after the bar's end. So P1-P4 use the latest bar with
`known_at <= as_of`, normally the bar ending at `as_of − 3600`. Training uses the same cutoff. An earlier cutoff
would need a contract change adding a separate feature cutoff at or before `issued_at`; this design does not ask for
one.

The feature set is fixed before training, with at most eight features. A change of definition after the freeze stops
the study (S4).

| ID | Feature at `as_of` | Source | Known time |
| --- | --- | --- | --- |
| P1 | Log return of the latest known bar | TRADEGEN bars | bar `known_at` |
| P2 | Log return of the latest 4 known bars | TRADEGEN bars | bar `known_at` |
| P3 | Log return of the latest 24 known bars | TRADEGEN bars | bar `known_at` |
| P4 | Realized volatility over the latest 24 known bars | TRADEGEN bars | bar `known_at` |
| D1 | In the last 24 hours, a new ALFRED vintage or a new ECOS observation was received for a series on the pre-registered list | DIDM ALFRED, ECOS | `received_at` |
| D2 | GDELT items in the last 96 15-minute slots, divided by the mean per 96 slots over the 7 days before | DIDM GDELT | `received_at`, all 96 slots ingested |
| D3 | Mean `ess_like_0_100` of V0 scores received in the last 24 hours, for event types `crypto_regulation_hack` and `monetary_policy` | DIDM V0 scores | score `received_at` and selected source |
| Q1 | A QuantGPT judgment of a pre-registered risk news type was known in the last 24 hours | QuantGPT records | later of `issued_at` (or `as_of`) and receipt |

**Cadence.** D1, D2 and Q1 are measured by receipt time, so a slow collector looks like quiet news. To avoid that:

- The collector and delivery cadence is pre-registered and kept the same in training and evaluation (section 10,
  row 5).
  - **Proposed DIDM cadence:** a collector run every 15 minutes. The pinned GDELT collector ingests the newest
    15-minute slot per run, so a slower schedule would make D2 measure the schedule, not the news.
- Every collector run and QuantGPT delivery leaves a run-log entry, the heartbeat.
- **D2** counts items by the slot the collector ingested. If a slot has no heartbeat by `as_of`, D2 is missing, not
  zero.
- **D1** needs the scheduled daily run of its sources to have a heartbeat. Otherwise it is missing.
- **Q1** is missing when a scheduled delivery is missing.

**Rules.**

- **Known times.** Release dates and observation dates are never used as known times.
- **Missing data.** There is no imputation. Missing features are counted by S1.
- **QuantGPT confidence.** Q1 is categorical. QuantGPT's confidence scores are uncalibrated (v0.1), so they are not
  used.
- **No retroactive data.**
  - D3 and Q1 enter only if their scores or records were received live, at each bar, through the whole training
    window.
  - Scores or records produced afterwards for past times are not admitted. They were unknown at those `as_of`
    times, and using them would be look-ahead.
  - A feature without live data is dropped before the freeze, never added later.
- **Few events.** D1 is non-zero only around scheduled releases. Four weeks of training may hold only a few of them.
  - D1 enters only if the training window holds at least the pre-registered minimum number of events (section 10,
    row 3). Otherwise it is dropped before the freeze.
  - A fixed penalty does not make a coefficient fitted on a few events informative.

## 5. Model, frozen artifact and baselines

- **Model M.** Multinomial logistic regression over `up`, `down` and `neutral`, using the contract's hurdle:
  - "up" means the compounded return over the window is above `+hurdle_bps`, net of costs;
  - "down" means it is below `-hurdle_bps`;
  - otherwise the outcome is "neutral".

  How M is fitted:
  - The L2 penalty is fixed in advance.
  - Features are standardized with training-window statistics only.
  - It uses the standard library or packages already pinned in `constraints.txt`; nothing new is installed.
- **Training labels.** A label whose 2-bar outcome window ends after the training window is purged.
  `model.training_cutoff` is the end of the last outcome bar used by any label. `frozen_at` comes after it, and
  `evaluation_start` comes after `frozen_at`.
- **Frozen artifact.** `model.sha256` is the SHA-256 of one canonical JSON file. The file holds:
  - the coefficients and intercepts;
  - the standardization means and deviations;
  - the feature definitions and lists (the D1 series and Q1 news types);
  - the class order, `hurdle_bps` and the L2 penalty;
  - the feature-builder code commit.

  Changing any of them makes a new model version and a new study (contract section 3, rule 5).
- **Probability strings.** The writer turns each probability into a decimal string:
  - `up` and `down` are rounded to 6 decimals, and `neutral` is 1 minus their sum, so the three sum to exactly 1;
  - if the highest class is tied after rounding, no forecast is written for that bar.

  B0 uses the same rule.
- **Baselines.**
  - **B0: class frequencies** of the training window. It is fitted and scored like M.
  - **B1: price-only.** The same model with P1-P4, fitted and scored like M on the same bars.
  - **B2: the replay's built-in moving-block rule**, with its own pinned terms:
    - `cost_bps` = `hurdle_bps`, horizon 2 and `step_seconds` 3600;
    - `lookback`, `block`, `paths`, `seed` and its gate terms are fixed in M11-T4.

    It is not fitted. Its call rule and holdout are the replay's own, and its path-fraction probabilities can be
    exactly 0, which makes log loss infinite. B2 is therefore reported on criterion 1 and in stage 2 only, never in
    log-loss comparisons.

## 6. Pre-registration and sample size

Before stage 1 opens, the terms below are recorded in the M11-T4 pre-registration record. That record's format is
still to be defined. The owner's choices in section 10 supply the values.

- **Adapter study fields**, with the adapter's exact names:
  - `rule_version` (`external-forecast-v1`), `scope`, `source_id`, `market`, `forecast_model`, `evaluation_start`;
  - `step_seconds`, `horizon_seconds`, `hurdle_bps`, `confidence`, `min_validation_calls`;
  - `max_calibration_gap`, `up_y`, `down_y`.

  `hurdle_bps` is an integer, rounded up from measured costs.
- **Fields only in the M11-T4 record:**
  - `evaluation_end` and the interim date. The adapter has neither, so the evaluation code cuts the window at
    `evaluation_end` itself.
  - The feature lists, the L2 penalty, the training dates and the upstream identities (section 2).
  - The cadence and the D1 minimum.
  - The criterion 2 margin, bootstrap terms and stage 2 limits.
  - The B2 terms and the attempt budget.

**How calls are counted.** `confidence` does two jobs in the adapter:

- **Call filter.** A forecast is a call only when its direction is up or down and its probability for that
  direction is at least `confidence`. Other forecasts still use up their outcome window and never count as calls.
- **Hit-rate bar.** A direction qualifies when its calls reach `min_validation_calls` and the nominal 95% Wilson
  lower bound of its hit rate reaches `confidence`.

Up and down are counted separately. A hit needs the realized return to clear the hurdle in the called direction, and
a neutral outcome is a miss. So the hit rate a coin-flip model would get is below 0.5, and hit rates of 0.55 to 0.65
already mean real skill. Before choosing `confidence`, M11-T4 estimates from the training window how many calls the
model makes.

The table shows, for each true hit rate:

- **Break-even calls:** the count where the observed rate equals the true rate. At that count a direction passes only
  about half the time.
- **Calls for 80%:** the count needed to pass 80% of the time.
- **Pass chance** at 100, 250 and 500 calls in one direction.

| `confidence` | True hit rate | Break-even calls (~50% pass) | Calls for 80% pass | Pass chance at 100 / 250 / 500 calls |
| --- | --- | --- | --- | --- |
| 0.55 | 0.60 | 381 | 760 | 18% / 37% / 63% |
| 0.60 | 0.65 | 369 | 730 | 17% / 35% / 63% |
| 0.60 | 0.70 | 93 | 177 | 55% / 90% / 100% |
| 0.75 | 0.80 | 289 | 548 | 19% / 47% / 77% |
| 0.75 | 0.85 | 73 | 127 | 67% / 98% / 100% |

**What one window can supply.**

- One adapter run scores at most about 1,024 hourly bars after the history's first bar, and `evaluation_start` must
  be on or after that bar. So 6 weeks (1,008 bars) is the longest stage 1 window possible without changing the
  replay.
- Those 6 weeks give at most 504 non-overlapping windows for both directions together, and calls are a fraction of
  them.
- For a true hit rate near 0.55, the lowest legal cutoff (just above 0.5) needs about 385 calls just to break even.
  So that rate cannot qualify in one run.
- Rates of 0.60 to 0.65 qualify only if most windows are calls in the same direction.

**Expected outcome.** Under realistic skill the expected outcome is S3, inconclusive. A longer or pooled evaluation
needs a replay change and an owner decision (section 10, row 8). It is never done by extending a window after it
opens.

**Attempts.** Every study attempt (a voided window, a new model version, a restart) is logged in the M11-T4 record.
Results are reported with the total number of attempts. The owner sets a maximum (section 10, row 13), because
repeated attempts at a nominal 95% level raise the chance that one passes by luck.

## 7. Success criteria

**Stage 1.** Criteria 1, 2 and 4 are judged once, at `evaluation_end`, on the forward window. They are not judged at
any earlier observation, because re-testing as data arrives inflates the nominal 95% level.

1. **Gate, per direction.** A direction passes only on its own terms:
   - its calls reach `min_validation_calls`;
   - the Wilson lower bound reaches `confidence`;
   - the calibration gap is within `max_calibration_gap`.

   A direction that does not pass is never acted on in stage 2.
2. **Directional value over prices.** The comparison uses every bar-close forecast where both M and B1 exist.
   - **Test.** On the windows whose outcome is not neutral, take M's and B1's up-versus-down log loss, using
     `p_up / (p_up + p_down)`. M's loss must be lower than B1's by more than the pre-registered margin.
   - **Interval.** A one-sided 95% lower bound from a day-block bootstrap: blocks of 24 bar closes, one KST day,
     10,000 replications.
   - **Why up versus down.** Three-class log loss is reported too, but it is not the test. A news-volume feature
     can lower it just by predicting "move versus neutral", which is volatility, not direction.
   - **Also:** M must beat B0.
   - **If it fails:** the news features add nothing, and BR-26 keeps a static Y. B1 or B2 would need their own
     pre-registered forward study.
3. **BR-26 effect (stage 2).** See below.
4. **Stability.** In each half of the window (at most 252 windows each), the passing direction's hit rate is at or
   above `confidence`, and M's up-versus-down log loss is below B1's. These are point estimates. A full gate in each
   half would need the call minimum twice, which 6 weeks cannot supply (section 6). This half-window check is the
   only regime check.

**Stage 2.** Stage 2 runs only if stage 1 passes. It needs live forecasts and a quote record (section 9).

The arms are replayed on the same frozen quote record:

- static Y at the ceiling;
- adaptive Y from M;
- adaptive Y from B1.

How the replay is set up:

- The replay pins `evaluation_start` inside the stage 1 window. Within its 1,024-bar history, its gate is then fed by
  stage 1 forecasts.
- The effect is measured only on observations after the gate first qualifies.

**Criterion 3:**

- **No missed alerts by construction.** Adaptive Y never exceeds the ceiling. Against a static Y at the ceiling,
  every static alert is also an adaptive alert, so missed or delayed alerts cannot increase. Zero misses is therefore
  not evidence.
- **The test is the trade-off**, with limits pre-registered in section 10, row 12:
  - **Benefit:** early warnings. An early warning is an adaptive alert that precedes a static alert, or an adverse
    move of at least the ceiling, within the pre-registered time T.
  - **Cost:** excess alerts. An excess alert is an adaptive alert with neither within T. Excess alerts per day must
    stay within the limit.
  - **M versus B1:** M must give at least as many early warnings as the B1 arm, for no more excess alerts.
- **Also reported, per arm:** every item that `docs/adaptive-bid-gap-preview.md` requires before operational
  approval:
  - alert misses and delays, adverse price moves and excess blocks;
  - execution costs and stale or unknown evidence;
  - floor and daily-stop latches;
  - restart continuity and timing.

**Long records.** One replay document holds at most 128 observations. The record is split at boundaries fixed in
advance, every 128 observations. State carries over per arm:

- The next document's `terms.current_y` is the previous document's `final_working_y`.
- If the previous document ended latched, the first observation's `prior_block_active` is true. A carried latch is
  released only by the BR-26 release rule in force; stage 2 cannot open until that rule is fixed.
- A pending widening confirmation is dropped at a boundary, and each drop is counted.

The alternative is a replay change that reads a long record (section 10, row 11).

**After success.** Passing makes the model a candidate for the owner's decision and signature (M11-T5, D12). Any
runtime use is a separate, reviewed change that binds the model digest in signed terms.

## 8. Stop criteria

| ID | Trigger | Result |
| --- | --- | --- |
| S1 | Any of: a point-in-time violation, a hash mismatch or a refused snapshot; or more than 5% of bars without features, counting missing heartbeats and missing deliveries | The window is void. A new window starts after the fix; windows are never spliced. It counts as an attempt. |
| S2 | At the interim date (half the window), the one-sided 95% upper bound of M's up-versus-down log-loss improvement over B1 is at or below zero | Stop: no incremental value. |
| S3 | `evaluation_end` arrives with a direction's calls below `min_validation_calls` | Stop: inconclusive. The window is not extended. |
| S4 | After the window opens, any change to features, model, thresholds, data sources, cadence or upstream identities | Stop. A new study starts with a new model version and counts as an attempt. |
| S5 | A replay event that widens Y while a block, stop or alert is active | Stop and treat it as a bug. The replay's rules forbid it. |
| S6 | The owner's signed ceiling changes during stage 2 | Stage 2 ends at that time; its earlier part is reported alone. A pinned `up_y` above a new ceiling would make the adapter refuse the study. |
| S7 | A stage 2 day's quote coverage is below the pre-registered level | That day is void. If too few days remain for the stage 2 minimum, stage 2 is inconclusive. |

## 9. Data collection plan and forward runs

1. **Now.** There is no direction model. Code is written only after the section 10 decisions, and is tested on
   synthetic data only.
2. **Prices.**
   - A continuous research recorder keeps an hourly bar record for the chosen market, with real `known_at` times.
   - It starts after the owner finishes O28 (A0 measurement) and lifts the Upbit no-call window.
   - The M9-T4 study cannot be the source. It covers only 48 hours, in 300-second slots, while this study needs
     about 11 weeks of contiguous bars.
   - Its source is section 10, row 4.
3. **DIDM.**
   - The collector runs at the pre-registered cadence, with a heartbeat per run.
   - The owner takes offline snapshots as in the O29 guide. That needs PR #76 merged (O39); until then the bridge
     refuses the store.
   - V0 scores and an exchange export for D3 are QUANTGEN's task (section 2).
4. **QuantGPT.**
   - Under M11-T7, TRADEGEN's main session asked QUANTGEN on 2026-11-24 for periodic records: `as_of`, `issued_at`,
     model identity and snapshot hash. There is no answer yet.
   - Q1 is possible only after those records arrive live.
5. **Warm-up and training.**
   - D2 needs 7 days of history and P3/P4 need 24 bars, so complete feature rows begin about 7 days after collection
     starts.
   - Training then takes at least 4 weeks: 672 hourly bars and 336 non-overlapping windows.
   - Then the model is fitted and frozen.
6. **Stage 1 forecasts.** Proposed (section 10, row 16): batch forecasts from point-in-time features, written after
   each DIDM snapshot.
   - `issued_at` is the actual write time.
   - Each snapshot's SHA-256 and capture time go into an append-only log when the snapshot is taken.
   - Batch forecasts become visible only after their windows, so they serve criteria 1, 2 and 4 but not stage 2.
7. **Stage 1 evaluation.** The next 6 weeks run forward, with the section 6 terms registered before they start.
8. **Stage 2, only if stage 1 passes.**
   - **Live forecasts.** The forecast writer runs at each bar close. For that, the DIDM snapshot, the bridge and the
     feature builder run automatically each hour. `issued_at` is the actual write time, and write and receipt times
     go into an append-only log (contract section 3, rule 7).
   - **Quote record.** A quote recorder captures the last trade price, the last trade time and the best bid in the
     same second, at a fixed interval, with the block, floor and daily-stop flags.
     - Each day's file is frozen with its SHA-256.
     - The coverage threshold and the void rule are S7.
     - Its Upbit public calls start only after O28.
   - **Length.** Stage 2 lasts at least the pre-registered minimum number of days.
9. **Owner decision (M11-T5).** It uses the reports of sections 7 and 8.

**Recurring owner work.** For about 11 weeks, plus stage 2, the owner's PC must run the collector, the snapshots and
the recorders. A missed run makes features missing, and enough of them voids a window (S1). Section 10, rows 4 and
5, set this schedule.

**Earliest dates.** Stage 1 ends about 11 weeks after price and DIDM collection start: 7 days of warm-up, 4 weeks
of training and 6 weeks of evaluation.

## 10. Owner decisions

Who builds the model is already decided: TRADEGEN research, O32 (a), 2026-11-24 19:05:53 KST. The rows below are
open. Each gives the options with the proposed default first, and what each choice means. Please give answers
privately, not on the public PR (section 2).

| # | Decision | Options (default first) | What it means |
| --- | --- | --- | --- |
| 1 | Market, bar, horizon | (a) KRW-BTC, 1-hour bars, 2-bar horizon. (b) 15-minute bars. (c) Another KRW market. | (a) At most 504 outcome windows in 6 weeks. (b) One replay covers only 10.7 days, too short for the gate. (c) Thinner trading gives more stale-trade alerts and fewer reliable bars. |
| 2 | Feature set | (a) P1-P4, D1 and D2; D3 and Q1 only if admitted under section 4. (b) P1-P4 only. (c) P1-P4 and D1 only. | (a) Tests whether news adds direction beyond prices. (b) M equals B1, so the study tests nothing new. (c) Fewer inputs, but D1 alone may have too few events. |
| 3 | Feature lists and fit terms | (a) D1 series: US CPI, payrolls and the policy rate target (ALFRED) and the Bank of Korea base rate (ECOS). Q1 types: regulation, exchange hacks and monetary policy, mapped to QuantGPT's type names in M11-T4. D1 needs at least 8 events in training. L2 penalty 1.0 on standardized features. Training: 4 weeks after a 7-day warm-up. (b) Longer lists or a longer training window. | (a) With monthly series, 4 weeks may hold fewer than 8 events, and D1 is then dropped before the freeze. (b) More events, but a later start. Any change after the freeze starts a new study. |
| 4 | Price recorder | (a) A new research recorder of hourly Upbit bars with real `known_at`, about one public call per hour, started after O28. (b) Extend the M9-T4 recorder to run for about 11 weeks. | (a) A small new tool, and the PC runs continuously. Gaps over 5% void a window. (b) Ties this study to the universe study's schedule and recorder changes. |
| 5 | Collector and delivery cadence | (a) DIDM collector every 15 minutes with a run log; QuantGPT records at the cadence in M11-T7's answer; same cadence in training and evaluation. (b) Daily DIDM collection, with D2 dropped. | (a) Owner PC work for about 11 weeks. Missed runs count as missing data (S1). (b) Less work, but no news-volume feature, and D1 only by day. |
| 6 | `hurdle_bps` | (a) An integer rounded up from TRADEGEN's measured fees, spread and slippage for the market; training waits for the measurement. (b) A provisional value set now. | (a) May delay training. (b) If measured costs differ, outcomes are mislabeled, and the restart counts as an attempt. |
| 7 | Replay ceiling and targets | Ceiling: (a) the owner's signed Y after O18; (b) a private research ceiling at or below 0.05, chosen now. Targets: `up_y` = ceiling and `down_y` = half the ceiling. | (a) Stage 2 waits for O18. (b) Results hold only for that ceiling. A widening to `up_y` stays in force after the forecast expires (section 3), so choose an `up_y` you accept holding indefinitely. A lower `down_y` gives more alerts and blocks. |
| 8 | Evidence plan | (a) One 6-week stage 1 window, judged once at the end, per direction. (b) A longer or pooled evaluation. (c) A lighter bar, using criterion 2 only. | (a) The most likely result is inconclusive unless skill is large (section 6). (b) Needs a replay and adapter change and a revised design first. (c) Easier to pass, but says nothing about acting on calls. |
| 9 | Gate terms | (a) `confidence` 0.60, `min_validation_calls` 100 per direction, `max_calibration_gap` 0.05. (b) Higher cutoffs. (c) More calls. | (a) A direction passes about 55% of the time if its true hit rate is 0.70, and about 17% if 0.65. (b) and (c) need more calls than 6 weeks supply. |
| 10 | Criteria 2 and 4 | (a) Margin 0: the one-sided 95% lower bound of the up-versus-down log-loss improvement over B1 must be above zero; the per-half check uses point estimates. (b) A positive margin. (c) A full gate in each half. | (a) Any reliable improvement counts, however small. (b) Stricter: a small gain fails. (c) Usually impossible in 6 weeks. |
| 11 | Stage 2 plan and baseline | Plan: (a) a separate live stage after stage 1 passes, at least 14 days, measured after the gate qualifies; (b) one live window for both stages. Baseline: (a) static Y at the ceiling; (b) a fixed lower static Y. Long records: (a) carry state between 128-observation documents (section 7); (b) a replay change first. | Plan (a) adds at least 14 days, but only after evidence of skill; plan (b) needs live forecasts and quote recording from the first day. Baseline (a) makes missed alerts impossible, so the test is the trade-off; with baseline (b), misses become possible. Long records (b) needs a code change and review before stage 2. |
| 12 | Stage 2 quote record and limits | (a) A quote every 10 seconds; 95% daily coverage; T = 30 minutes; at most 1 excess alert per day on average. (b) Other values. | (a) About 8,640 quote captures per day during stage 2, after O28: one or two public Upbit calls each, or a WebSocket stream. A stricter limit is harder to pass; a looser one tolerates more blocked buying. |
| 13 | Attempt budget | (a) At most 3 attempts for this model family, all reported. (b) 1 attempt. (c) No limit. | (a) Allows recovery from a voided window. (b) Strictest; one data gap ends the study. (c) Not recommended: retries inflate the chance of a lucky pass. |
| 14 | Storage, privacy, data rights | (a) A private folder outside Git and OneDrive for data, models, forecasts, quote records, the M11-T4 record and these answers; only SHA-256 values are public. Confirm research use of DIDM data. | If DIDM research use cannot be confirmed, the DIDM features are dropped. The study then reduces to B1, so it stops. |
| 15 | OQ9 | (a) No: under `CLAUDE.md` section 7.5, model output never releases an entry hold, so this study serves OQ9 only offline. (b) Revisit later as a separate owner decision. | OQ9 (PR #65/#71) lets an authorized, tested model release an entry block, which conflicts with section 7.5 for models with QuantGPT or DIDM features. Until the owner resolves this, no path leads to `entry_unblock`. |
| 16 | Stage 1 forecast production | (a) Batch after each snapshot, with snapshot hashes logged at capture. (b) A live writer at each bar close from the start. | (a) Less automation, but forecasts serve only criteria 1, 2 and 4. (b) Needs hourly DIDM refresh from the start, and allows plan (b) in row 11. |

## 11. Review against the edge-strategy-reviewer criteria

The skill's eight criteria, applied to this design. There is no position or exit: Y is a monitoring threshold, not
a trade.

| Criterion | Assessment |
| --- | --- |
| C1 Edge plausibility | Weak. The latency of public news makes the edge doubtful. Criterion 2 tests direction beyond prices, and the default answer is no. |
| C2 Overfitting risk | Partly controlled: at most 8 features, a fixed penalty, one fit, a frozen artifact, no tuning on the evaluation window, and an attempt budget. D1 rests on few events and enters only above a minimum count. The feature lists carry selection risk, so they are fixed before any training data is examined. |
| C3 Sample adequacy | The main risk. At realistic skill, 6 weeks gives a pass chance well under 50% (section 6), and the expected result is inconclusive. |
| C4 Regime dependency | Checked only by the half-window point estimates. Six weeks covers few crypto regimes, so a pass is weak evidence. |
| C5 Exit calibration | Not applicable. Targets are Y values bounded by the ceiling; a widening persists until a later proposal (section 3). |
| C6 Risk concentration | Not applicable. There is no position size or order, and Y stays at or below the ceiling and 5%. |
| C7 Execution realism | The hurdle is net of measured costs, bars use real receipt times and features lag one bar. Stage 2 uses live issue times and a recorded quote stream. |
| C8 Invalidation quality | Seven specific stop rules (section 8). |

Overall: REVISE until the section 10 decisions are made. The design is not a trading strategy and is never
export-eligible.

## 12. Not in this document

- **No code.** After the owner decides, separate PRs add the following under `tools/research/`, with synthetic tests,
  the five flags and the D14 import check:
  - a price recorder;
  - a point-in-time feature builder, including DIDM re-selection per bar;
  - a fit-and-freeze tool;
  - a forecast writer with its manifest;
  - for stage 2, a quote recorder and the replay carry-over or a long-record replay.
- **The M11-T4 pre-registration record.**
- **OQ9's benefit metric.** It is still undefined (row 15).

법률, 세무, 투자 조언이 아니며 면허를 가진 자문가가 아니다
