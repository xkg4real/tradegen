# Direction model study design (research only)

Status: proposed, 2026-11-24 (Asia/Seoul), revised twice after the main session's reviews. Checklist item M11-T6,
after the owner chose option (a) for O32 (2026-11-24 19:05:53 KST): a separate direction model, built in TRADEGEN
research, that uses QUANTGEN DIDM records and QuantGPT judgments as features. This document is a design and has no
code. Implementation waits for the owner decisions in section 10.

The study's forecasts are research inputs. They never become an order input, an approval or a signed term. Every
rule in `docs/direction-forecast-contract.md` section 5 applies, and this study adds its own tools to it:

- **Imports.** No module in the D14 code closure imports any new tool in section 12 (the price and quote recorders,
  the run-log wrapper, the feature builder, the fit-and-freeze tool, the forecast writer, the stage 1 evaluator and
  the replay carry-over), the adapter, the bridge, or any QuantGPT or QUANTGEN code. Every tool PR in section 12 runs
  two checks:
  - no `tools/research/` path appears in `code_files(repo_root)`;
  - every import in the closure resolves to the standard library, an in-repo module or a package pinned in
    `constraints.txt`, and no top-level `quantgpt` or `quantgen` name is imported. `code_files` lists only in-repo
    files, so the first check cannot see code outside the repository.
- **Flags.** Every report or manifest that any new tool in section 12 writes states `research_only=true`,
  `live_eligible=false`, `execution_ready=false`, `source_authenticated=false` and `owner_approval_verified=false`,
  as the bridge and the adapter already do. The `tradegen-direction-forecast-v1` format cannot carry these flags, so
  the forecast writer writes a manifest beside each snapshot.
- **No release, no signal.** A forecast never clears an alert, an entry block, a daily stop, a floor halt or a loss
  stop, and never creates an entry or sell signal. `CLAUDE.md` section 7.5 forbids using model output to release an
  alert, entry hold or loss stop that has already fired, so no path leads to `entry_unblock`, whatever benefit metric
  OQ9 later defines (section 10, row 15). In the stage 2 replay, too, no forecast, model output or Y change releases a
  latch (section 7).
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
skill stage 1 most likely ends without a pass: INCONCLUSIVE if the model makes too few calls, NOT SHOWN if it makes
enough. The design reports that outcome rather than stretching the test until it passes.

## 2. Where the study sits

```text
TRADEGEN Upbit bars ─┐
DIDM snapshot ───────┼─> point-in-time feature table ─> frozen model ─> forecasts + manifest
QuantGPT snapshots ──┘         (owner PC, private)       (sha256)       (tradegen-direction-forecast-v1)
                                                                              │
                         BR-26 replay <── adapter (PR #75) <───────────────────┘
```

- **Price bars.** TRADEGEN's own Upbit record. A bar's `known_at` is when this PC actually had it. The adapter refuses
  a history with any missing bar, so the recorder backfills a missed bar with its real, late `known_at` (section 9).
- **DIDM.**
  - Read only through `tools/research/didm_source_bridge.py`.
  - The owner's store is above the bridge's 64 MiB limit on `main`. Reading it needs PR #76 merged (O39); until
    then the bridge refuses the store. PR #76 in turn refuses a store above 2,000,000 rows, which one growing store
    at the 15-minute cadence passes in about a week. The default therefore keeps one store per KST day (section 10,
    row 5).
  - One bridge report lists every version of every record, with receipt times. The bridge's
    `selected_record_sha256` is right only for that report's cutoff. So, for each bar, the feature builder applies
    the bridge's rule again:
    - among each (`source_id`, `item_id`), take the latest record with `received_at` at or before `as_of`;
    - ties go to the higher `payload_sha256`.
  - A test checks the feature builder's selection against the bridge's at several cutoffs.
- **DIDM V0 scores (D3).**
  - QUANTGEN's collector writes no V0 score rows, and the bridge refuses any extra table in a store. D3 therefore
    first needs QUANTGEN to produce V0 scores live. Then it needs either windowed `tradegen-didm-exchange-v1`
    exports within the bridge's limits (64 MiB parsed in memory, 25,000 scores), or a bridge and schema change.
    Without both, D3 is dropped.
  - D3 uses only scores whose `model_version` and `prompt_sha256` equal the pinned values. Scores from any other
    version are counted and reported, never averaged in.
  - A score is known at the later of its `received_at` and the logged receipt time, on the owner's PC, of the export
    that delivered it. Each export's SHA-256 and receipt time go into an append-only log. A score that first arrives
    in a later export for an earlier `as_of` is not live at that `as_of`.
- **QuantGPT.**
  - Its recorded outputs (M11-T7) are read as explicit snapshot files with a hash. The model is never run during
    replay.
  - A record is known at the later of its `issued_at` and its receipt on the owner's PC. While records lack
    `issued_at`, as v0.1 does, its `as_of` stands in for it (contract section 3, rule 7).
- **Upstream identity.** When training starts, the identities that produce Q1 and D3 are pinned and written into the
  frozen artifact, so `model.sha256` binds them:
  - QuantGPT's `model.id`, `model.adapter`, `model.prompt_version` and decoding settings;
  - DIDM V0's `model_version` and `prompt_sha256`.

  Every snapshot or export read, in training and in evaluation, checks these identities and the creation time. A
  change during training restarts training and counts as an attempt. A change after the freeze stops the study (S4).
- **Storage.** All code lives in `tools/research/`. The following stay in a private folder on the owner's PC,
  outside Git and OneDrive: the fitted model, the feature tables, the forecasts and quote records, the owner's
  section 10 answers, and the M11-T4 record. The reason is that DIDM data rights are unverified, and everything
  else is derived from that data.
- **What is public.** Code, this design, and SHA-256 values of records whose private content cannot be guessed, such
  as the frozen artifact and the data files. The study object, the M11-T4 record and the section 10 answers hold few
  unknowns, such as the ceiling and `up_y`, so a plain SHA-256 of them could be reversed by guessing. Their hashes
  stay private, or are published only over a wrapper record that adds a random 256-bit private salt. The owner
  should not post section 10 answers on the public PR.

## 3. Time scales and how Y behaves

BR-26 works on two time scales:

- **Seconds.** Each quote is checked. If the last trade is older than 30 seconds and the bid is at or below
  `last × (1 − Y)`, the alert triggers.
- **Hours.** A forecast can only propose a change to the working Y.

**What happens to Y in the replay** (`tools/research/adaptive_bid_gap_replay.py`):

- **Tightening.** A qualified "down" call tightens Y from the next observation.
- **Widening.** A qualified "up" call widens Y only after a later clean observation confirms it, before the
  forecast expires. With 10-second quotes the same forecast is normally still live at the next observation, so a
  widening usually takes effect one quote interval after the first up call. That confirmation is not independent
  evidence. Whether it should be is O38, an open owner decision that comes before the M11-T4 record (section 6).
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
`known_at <= as_of`, normally the bar ending at `as_of − 3600`. Training uses the same cutoff. Using the bar that
ends at `as_of` would need a feature cutoff after `as_of`, at or before `issued_at`. That is a contract change, and
this design does not ask for one. B2's holdout uses the just-closed bar, so B2 sees one bar more than M and B1, and
its criterion 1 report is not like-for-like.

The feature set is fixed before training, with at most eight features. A change of definition after the freeze stops
the study (S4).

| ID | Feature at `as_of` | Source | Known time |
| --- | --- | --- | --- |
| P1 | Log return of the latest known bar | TRADEGEN bars | bar `known_at` |
| P2 | Log return of the latest 4 known bars | TRADEGEN bars | bar `known_at` |
| P3 | Log return of the latest 24 known bars | TRADEGEN bars | bar `known_at` |
| P4 | Realized volatility over the latest 24 known bars | TRADEGEN bars | bar `known_at` |
| D1 | In the last 24 hours, a new item, or a changed payload, was first received for an event series on the pre-registered list | DIDM ALFRED, ECOS | first `received_at` of that item or payload |
| D2 | GDELT items in the last 96 15-minute slots, divided by the mean per 96 slots over the last 7 days, including the current 96 | DIDM GDELT | `received_at`; all 96 numerator slots present |
| D3 | Mean `ess_like_0_100` of pinned-version V0 scores known in the last 24 hours, for event types `crypto_regulation_hack` and `monetary_policy` | DIDM V0 scores | later of score `received_at` and export receipt (section 2) |
| Q1 | A QuantGPT judgment of a pre-registered risk news type was known in the last 24 hours | QuantGPT records | later of `issued_at` (or `as_of`) and receipt |

**Cadence.** D1, D2 and Q1 are measured by receipt time, so a slow collector looks like quiet news. To avoid that:

- The collector and delivery cadence is pre-registered and kept the same in training and evaluation (section 10,
  row 5).
  - **Proposed DIDM cadence:** a collector run every 15 minutes, into one store per KST day. The pinned GDELT
    collector ingests the newest 15-minute slot per run, so a slower schedule would make D2 measure the schedule,
    not the news. The feature builder merges the bridge reports of the daily stores its lookback spans.
- **Run log.** A wrapper runs each collector run and QuantGPT delivery and writes an append-only run log. For each
  source it records whether the fetch succeeded, and for GDELT the slot stamps fetched or missing. It takes this from
  the collector's output and the store's own rows, not from the run having happened, because the pinned collector
  exits 0 when a source fails. This log is the heartbeat.
- **D2** counts items by their slot. A slot missing from the run log is missing, not zero.
  - The wrapper backfills a missed slot by its stamp on the next run. A backfilled slot is known only from its
    backfill time, so a quick backfill costs at most about one bar. If the pinned collector cannot fetch a named slot,
    the slot stays missing.
  - The numerator needs all 96 slots. The denominator uses the slots present and needs at least 95% of its 672.
  - One slot that is never backfilled makes D2 missing for 24 bars. A 6-week window therefore absorbs two such misses
    within S1's 5%, and a third voids it.
- **D1**, when chosen, is missing unless the run log shows its sources' scheduled run succeeded. Its event time is the
  first `received_at` of each (`source_id`, `item_id`), or of a changed payload. The selected version's `received_at`
  cannot be used: every run re-adds each ALFRED vintage and ECOS observation with a fresh `received_at`, which would
  make D1 true every day. A test re-fetches an unchanged vintage and checks that D1 stays false.
- **Q1** is missing when a scheduled delivery is missing.

**Rules.**

- **Known times.** Release dates and observation dates are never used as known times.
- **Missing data.** There is no imputation. Missing features are counted by S1.
- **QuantGPT confidence.** Q1 is categorical. QuantGPT's confidence scores are uncalibrated (v0.1), so they are not
  used.
- **No retroactive data.**
  - D3 and Q1 enter only if their scores or records were received live, at each bar, through the whole training
    window. D3's known time includes the export receipt (section 2), so a backfilled score cannot pass as live.
  - Scores or records produced afterwards for past times are not admitted. They were unknown at those `as_of`
    times, and using them would be look-ahead.
  - A feature without live data is dropped before the freeze, never added later.
- **Few events (D1).** D1 is non-zero only around scheduled releases. The proposed event series (row 3) give about 3
  events in 4 weeks, at most about 6, well below the minimum of 8. So D1 is not in the default feature set (row 2).
  It is an option only with a training window long enough to reach the minimum. A fixed penalty does not make a
  coefficient fitted on a few events informative. Daily-updated series, such as a policy rate published every
  business day, are excluded: D1 would then mark weekdays, not releases.

## 5. Model, frozen artifact and baselines

- **Model M.** Multinomial logistic regression over `up`, `down` and `neutral`, using the contract's hurdle:
  - "up" means the compounded return over the window is above `+hurdle_bps`, which is already net of costs (row 6);
  - "down" means it is below `-hurdle_bps`;
  - otherwise the outcome is "neutral".

  Every label and outcome class, in training and in criterion 2, comes from the same integer `return_bps` bar record
  that the adapter scores, compounded as the adapter does, so outcomes near the hurdle cannot disagree.

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
  - the upstream identities (section 2);
  - the feature-builder code commit.

  Changing any of them makes a new model version and a new study (contract section 3, rule 5).
- **Probability strings.** The writer turns each probability into a decimal string:
  - `up` and `down` are rounded to 6 decimals, and `neutral` is 1 minus their sum, so the three sum to exactly 1;
  - if the highest class is tied after rounding, no forecast is written for that bar.

  B0 uses the same rule.
- **Baselines.**
  - **B0: class frequencies** of the training window. It is fitted and scored like M.
  - **B1: price-only.** The same model with P1-P4, fitted and scored like M on the same bars.
  - **B2: the replay's built-in moving-block rule.** Its terms are fixed by this design, not by an owner row:
    - `cost_bps` = `hurdle_bps`, horizon 2, `step_seconds` 3600, `lookback` 24, `block` 2 and `paths` 1,000;
    - its gate terms equal M's, and the M11-T4 record holds its `seed`;
    - it runs once, on the last 1,024 bars of the stage 1 record, so its holdout covers the last 1,000 bars rather
      than exactly M's windows. That uses about half of the holdout's simulation budget.

    It is not fitted. Its path-fraction probabilities can be exactly 0, which makes log loss infinite. B2 is
    therefore reported on criterion 1 only, never in log-loss comparisons or in stage 2.

## 6. Pre-registration and sample size

Before stage 1 opens, the terms below are recorded in the pre-registration record, called the M11-T4 record here.
That record's format is still to be defined. Two prerequisites come first:

- **O38.** The PR #70 points, including whether the same forecast may confirm its own widening (section 3).
- **M9-T4, as the checklist stands.** The checklist's M11-T4 is the BR-26 forward-validation pre-registration built
  on A0 measurements and the 577-slot study data, and it waits for O28 and M9-T4. Unless the checklist gives this
  study's record its own item, stage 1 waits for M9-T4 too.

**Who sets the values.** The owner's section 10 answers supply the market, bar and horizon, the features and fit
terms, the cadence, the hurdle, the ceiling and targets, the gate terms, the criteria margins, the stage 2 terms, the
latch convention and the attempt budget. The design fixes the rest: the B2 terms (section 5), the bootstrap (24-bar
blocks, 10,000 replications), the interim date at half the window, the call-count estimate below and stage 2's
`evaluation_start` (section 7).

- **Adapter study fields**, with the adapter's exact names:
  - `rule_version` (`external-forecast-v1`), `scope`, `source_id`, `market`, `forecast_model`, `evaluation_start`;
  - `step_seconds`, `horizon_seconds`, `hurdle_bps`, `confidence`, `min_validation_calls`;
  - `max_calibration_gap`, `up_y`, `down_y`.

  `hurdle_bps` is an integer (row 6).
- **Fields only in the M11-T4 record:**
  - `evaluation_end` and the interim date. The adapter has neither, so the stage 1 evaluator cuts the window at
    `evaluation_end` itself.
  - The feature lists, the L2 penalty, the training dates and the upstream identities (section 2).
  - The cadence and, if D1 is chosen, the D1 minimum.
  - The criterion 2 margin, the bootstrap terms, the stage 2 limits and length, and the latch convention.
  - The B2 seed and the attempt budget.

**How calls are counted.** `confidence` does two jobs in the adapter:

- **Call filter.** A forecast is a call only when its direction is up or down and its probability for that
  direction is at least `confidence`. Other forecasts still use up their outcome window and never count as calls.
- **Hit-rate bar.** A direction qualifies when its calls reach `min_validation_calls`, the nominal 95% Wilson lower
  bound of its hit rate reaches `confidence`, and its calibration gap is within `max_calibration_gap`.

Up and down are counted separately. A hit needs the realized return to clear the hurdle in the called direction, and
a neutral outcome is a miss. So a model without skill hits well under half the time. For KRW-BTC, treat 2-hour
returns as normal with a standard deviation of about 0.61%: the daily standard deviation of the last 365 daily
closes, 2.10%, scaled by the square root of time. The chance of a 2-hour return above +10, +15 or +25 bps is then
about 0.43, 0.40 and 0.34. Hit rates of 0.55 to 0.65 are therefore edges of about 12 to 30 points over that base
rate.

**Call-count estimate.** Before `confidence` is chosen, M11-T4 estimates how many calls the model makes. It fits on
the training window minus its last week, and counts calls on that held-out week, using only non-overlapping 2-bar
forecasts as the adapter does. A count over every bar close of the fit window would overstate the forward count
about twice, and in-sample probabilities are more extreme than forward ones. M11-T4 also reports the hit
autocorrelation on that week.

The table shows, for each true hit rate:

- **Break-even calls:** the count where the observed rate equals the true rate. At that count a direction passes only
  about half the time.
- **Calls for 80%:** the count needed to pass 80% of the time.
- **Pass chance** at 100, 250 and 500 calls in one direction, under the full gate: the call minimum, the Wilson bound
  and a calibration gap of at most 0.10, the proposed default (row 9).
- **The same at 100 calls with a gap of at most 0.05.**

The figures assume independent calls with a constant hit probability (binomial), and a calibrated model whose mean
called probability equals its true hit rate.

| `confidence` | True hit rate | Break-even calls (~50% pass) | Calls for 80% pass | Pass chance at 100 / 250 / 500 calls, gap 0.10 | At 100 calls, gap 0.05 |
| --- | --- | --- | --- | --- | --- |
| 0.55 | 0.60 | 381 | 760 | 16% / 37% / 63% | 5% |
| 0.60 | 0.65 | 369 | 730 | 16% / 35% / 63% | 5% |
| 0.60 | 0.70 | 93 | 177 | 54% / 90% / 100% | 44% |
| 0.75 | 0.80 | 289 | 548 | 19% / 47% / 77% | 11% |
| 0.75 | 0.85 | 73 | 127 | 67% / 98% / 100% | 62% |

- **The gap leg binds at the call minimum.** At 100 calls and a cutoff of 0.60, a pass needs at least 70 hits. With
  a gap of 0.05, the mean called probability must then be at least 0.65, and at a true rate of 0.70 the hits must
  also stay at or below 75.
- **Chance passes.** At a true rate equal to the cutoff, one direction passes by chance about 2.2% to 2.5% of the
  time at 100 to 500 calls.
- **Dependence.** P3, P4, D2, D3 and Q1 span 24 hours, so adjacent forecasts share most of their inputs and calls
  arrive in runs. Positively correlated hits shrink the effective sample, so the pass chances and the chance-pass
  rate above are approximate and somewhat optimistic.

**What one window can supply.**

- One replay history holds at most 1,024 bars, and `evaluation_start` must be on or after its first bar. The stage 1
  evaluator applies the same limit, because stage 2 replays the stage 1 bars as its gate history (section 7). So
  6 weeks (1,008 bars) is the longest stage 1 window without changing the replay.
- Those 6 weeks give at most 504 non-overlapping windows for both directions together, and calls are a fraction of
  them.
- A true hit rate of 0.55 can qualify only at a cutoff just above 0.5. It then needs about 385 same-direction calls,
  76% of the 504 windows, to break even. Even if every window is a same-direction call, it passes about 60% of the
  time.
- Rates of 0.60 to 0.65 qualify within 6 weeks only if the cutoff sits well below the true rate. About 119 calls break
  even for 0.60 at a cutoff of 0.51, and about 96 for 0.65 at 0.55. With the cutoff 0.05 below the true rate, they
  need about 370 to 380 calls, most of the windows.

**Outcomes of stage 1.**

| Outcome | When | Meaning |
| --- | --- | --- |
| PASS | At least one direction passes criterion 1, and criteria 2 and 4 hold | Stage 2 may run, for the passing directions only. |
| NOT SHOWN | Some direction reaches `min_validation_calls`, but no direction passes criteria 1, 2 and 4 | Reported as "no skill shown at this sample size", not as proof that there is none. |
| INCONCLUSIVE | No direction reaches `min_validation_calls` by `evaluation_end` (S3) | Too few calls to judge. |
| STOPPED | S2 at the interim date | No incremental value over B1. |
| VOID | S1 | Not judged. |

**Expected outcome.** If M makes fewer than 100 calls per direction in 6 weeks, INCONCLUSIVE is expected. With 100 or
more calls and a true hit rate 0.05 above the cutoff, NOT SHOWN is the most likely outcome: the pass chance at 100
calls is about 16%. A longer or pooled evaluation needs a replay change and an owner decision (section 10, row 8). It
is never done by extending a window after it opens.

**Attempts.** Every study attempt (a voided window, a new model version, a restart) is logged in the M11-T4 record.
Results are reported with the total number of attempts.

- A window voided before `evaluation_end` is never judged, so it spends no test level. It still counts toward the
  budget.
- Each judged attempt tests two directions, so its chance of a false pass is about 5% (2 × 2.5%). With 3 judged
  attempts the family-wise chance rises to about 14%.
- Row 13 sets the budget and whether to adjust for it. A Bonferroni adjustment for 3 attempts uses z = 2.394 in place
  of 1.96 and keeps the family-wise chance near 5%.

## 7. Success criteria

**Stage 1.** The stage 1 evaluator (section 12) judges criteria 1, 2 and 4 once, at `evaluation_end`, on the forward
window. They are not judged at any earlier observation, because re-testing as data arrives inflates the nominal 95%
level.

1. **Gate, per direction.** A direction passes only on its own terms:
   - its calls reach `min_validation_calls`;
   - the Wilson lower bound reaches `confidence`;
   - the calibration gap is within `max_calibration_gap`.

   One passing direction is enough for stage 2, and only that direction can act there. A direction that fails here
   fails the same gate in stage 2, because stage 2's gate reads the same evidence (below).
2. **Directional value over prices.** The comparison uses every bar-close forecast where both M and B1 exist.
   - **Test.** On the windows whose outcome is not neutral, take M's and B1's up-versus-down log loss, using
     `p_up / (p_up + p_down)`. M's loss must be lower than B1's by more than the pre-registered margin.
   - **Interval.** A one-sided 95% lower bound from a day-block bootstrap: blocks of 24 bar closes, one KST day,
     10,000 replications.
   - **Why up versus down.** Three-class log loss is reported too, but it is not the test. A news-volume feature
     can lower it just by predicting "move versus neutral", which is volatility, not direction.
   - **B0.** M's mean up-versus-down log loss on the same windows must also be below B0's. This is a point estimate,
     not a bootstrap test: B0 carries no direction, so it is a sanity check.
   - **If it fails:** the news features add nothing, and BR-26 keeps a static Y. B1 or B2 would need their own
     pre-registered forward study.
3. **BR-26 effect (stage 2).** See below.
4. **Stability.** In each half of the window (at most 252 windows each), the passing direction's hit rate is at or
   above `confidence`, and M's up-versus-down log loss is below B1's. These are point estimates. A full gate in each
   half usually fails: at a true rate of 0.70, a cutoff of 0.60 and 100 calls per half, each half passes about 54% of
   the time and both about 29% (19% with a gap of 0.05). This half-window check is the only regime check.

**Stage 2.** Stage 2 runs only if stage 1 passes. It needs live forecasts and a quote record (section 9).

The arms are replayed on the same frozen quote record:

- static Y at the ceiling;
- adaptive Y from M;
- adaptive Y from B1.

How the replay is set up:

- **Gate history.** Each stage 2 document carries the frozen stage 1 bar record, at most 1,024 bars, as its price
  history, and the study object keeps stage 1's `evaluation_start`. The adapter does not require the history to
  reach the observation time.
  - Stage 1's batch forecasts were all issued before stage 2, so the gate counts exactly the stage 1 windows.
  - Stage 2's live forecasts end after the history, so they are never scored.
  - The gate is therefore the same at every observation and equals the stage 1 result. Nothing is re-tested as stage
    2 data arrives.
- **B1 arm.** It uses B1's own stage 1 forecasts the same way, so B1 acts only in a direction where B1 passed the
  same gate. If B1 passed none, the B1 arm behaves like the static arm.
- **Live forecasts.** M's and B1's live forecasts come from the live writer (section 9). An observation with no live
  forecast keeps Y.
- **Start.** The effect is measured from stage 2's first observation, because the gate already holds from the
  stage 1 evidence.

**Criterion 3:**

- **No missed alerts by construction.** Adaptive Y never exceeds the ceiling. Against a static Y at the ceiling,
  every static alert is also an adaptive alert, so missed or delayed alerts cannot increase. Zero misses is therefore
  not evidence.
- **Counting.** An alert is an episode: the first triggered observation after a clean one, per arm. Early warnings and
  excess alerts are counted by episode, not by triggered observation. A 5-minute gap at 10-second quotes gives about
  30 triggered observations but one episode.
- **The test is the trade-off**, with limits pre-registered in section 10, row 12:
  - **Benefit:** early warnings. An early warning is an adaptive alert that precedes a static alert, or an adverse
    move of at least the ceiling, within the pre-registered time T.
  - **Cost:** excess alerts. An excess alert is an adaptive alert with neither within T. Excess alerts per day must
    stay within the limit.
  - **M versus B1:** M must give at least as many early warnings as the B1 arm, for no more excess alerts.
- **Also reported, per arm, from the quote record:**
  - alert misses and delays, adverse price moves and excess blocks;
  - stale or unknown evidence;
  - floor and daily-stop latches, and the latched time under the row 17 convention;
  - restart continuity and timing;
  - the share of observations with a live forecast.
- **Not measured: execution costs.** The study places no orders and records no fills, only quotes.
  `docs/adaptive-bid-gap-preview.md` requires static and adaptive Y to be compared on frozen prospective quote and
  fill records, execution costs included, before operational approval. A stage 2 pass therefore does not meet that
  check. It stays open and must be closed before M11-T5 operational approval.

**Long records.** One replay document holds at most 128 observations. The record is split at boundaries fixed in
advance, every 128 observations. A carry-over wrapper (section 12) carries state per arm, whichever plan row 11
picks:

- The next document's `terms.current_y` is the previous document's `final_working_y`.
- If the previous document ended latched, the next one starts with `prior_block_active` true. Every alert latches an
  arm, and the replay never clears a latch inside a document, so a release can take effect only at a boundary.
- **Release.** No forecast, model output or Y change releases a carried latch. BR-26 has no release rule. At runtime
  the entry block from an alert stays until an `entry_unblock` under BR-9(b), through OQ9's routes. The replay
  instead uses a pre-registered research convention that reads only the recorded state (section 10, row 17). The
  proposed default releases a carried latch at the first boundary after its recorded cause has cleared: the quote is
  clean again and every recorded flag is false. It applies the same way in every arm. This is more lenient than
  runtime, so the time a runtime block would still have held is counted and reported per arm.
- A pending widening confirmation is dropped at a boundary, and each drop is counted.
- A voided day (S7) is still replayed, so state carries across it. It is left out of the metrics.

The alternative is a replay change that reads a long record (row 11). It still needs the row 17 convention.

**After success.** Passing makes the model a candidate for the owner's decision and signature (M11-T5, D12). Any
runtime use is a separate, reviewed change that binds the model digest in signed terms, and the fill-record check
above comes first.

## 8. Stop criteria

| ID | Trigger | Result |
| --- | --- | --- |
| S1 | Any of: a point-in-time violation, a hash mismatch or a refused snapshot; a price bar that cannot be backfilled, since the adapter refuses a history with any gap; or more than 5% of bars without features, counting run-log gaps and missing deliveries | VOID. A new window starts after the fix; windows are never spliced. It counts as an attempt but spends no test level (section 6). |
| S2 | At the interim date (half the window), the one-sided 95% upper bound of M's up-versus-down log-loss improvement over B1 is at or below zero | STOPPED: no incremental value. |
| S3 | `evaluation_end` arrives and no direction has reached `min_validation_calls` | INCONCLUSIVE. The window is not extended. A single direction below the minimum simply does not pass criterion 1. |
| S4 | From the start of training, any change to features, model, thresholds, data sources, cadence or upstream identities | During training: training restarts and it counts as an attempt. After the freeze: stop; a new study starts with a new model version and counts as an attempt. |
| S5 | A replay event that widens Y while a block, stop or alert is active | Stop and treat it as a bug. The replay's rules forbid it. |
| S6 | Under row 7 (a), a signed Y below the research ceiling appears before or during stage 2. Under row 7 (b), the signed ceiling changes during stage 2 | Stage 2 ends at that time, or does not start; any earlier part is reported alone. A pinned `up_y` above a new ceiling would make the adapter refuse the study. |
| S7 | A stage 2 day's quote coverage, or its share of observations with a live M forecast, is below the pre-registered level (row 12) | That day is void for the metrics but still replayed for state (section 7). If too few days remain for the stage 2 minimum, stage 2 is inconclusive. |

## 9. Data collection plan and forward runs

1. **Now.** There is no direction model. Code is written only after the section 10 decisions, and is tested on
   synthetic data only.
2. **Prices.**
   - A continuous research recorder keeps an hourly bar record for the chosen market, with real `known_at` times. At
     each bar close it also stores the best bid and ask, which give the spread for row 6.
   - It starts after the owner finishes O28 (A0 measurement) and lifts the Upbit no-call window.
   - **Gaps.** The recorder backfills a missed bar from Upbit's candle data, with its real, late `known_at`. Features
     that would need that bar before it was known are missing (S1). A bar that cannot be backfilled at all voids the
     window (S1), because the adapter refuses a history with any gap. The 5% rule applies to features, never to
     price bars.
   - The M9-T4 study cannot be the source. It covers only 48 hours, in 300-second universe frames, and extending it
     would change signed D14 code (section 10, row 4).
   - **Shared Upbit budget (OQ17).** The price and quote recorders make public Upbit calls from the owner's PC, which
     shares its public-IP allowance with the app, the A0 probe and M9-T4 (BR-18, BR-24, OQ17).
     - The recorders use the A0 probe's coordination folder: they read the cooldown marker before each request,
       stop and record a hold on a 429 or 418, and never clear a hold.
     - The probe's session lock is exclusive, so a continuous recorder cannot hold it without blocking the other
       cooperating runs. How the recorders coexist with A0 and M9-T4 runs is row 4.
3. **DIDM.**
   - The collector runs at the pre-registered cadence through the run-log wrapper (section 4), one store per KST day
     under the default.
   - The owner takes offline snapshots as in the O29 guide. That needs PR #76 merged (O39); until then the bridge
     refuses the store.
   - V0 scores and an exchange export for D3 are QUANTGEN's task (section 2).
   - **Hourly bridge runs** (stage 2, and row 16 (b) from the start):
     - A consistent snapshot needs the collector paused, or SQLite's backup mechanism coordinated with it. One
       bridge run on the 123 MiB store took about 27 s (M11-T8).
     - Each run writes a new report about the size of its store and never overwrites one. On one growing store, 14
       days of hourly reports would take at least about 40 GiB, and row 16 (b)'s 11 weeks about 1,850 runs. Per-day
       stores keep each run small.
     - **Retention.** Each report's SHA-256 and the feature rows built from it go into the append-only log, and the
       report is then deleted, keeping the latest. Closed daily stores are kept until the study ends, so any report
       can be rebuilt.
4. **QuantGPT.**
   - Under M11-T7, TRADEGEN's main session asked QUANTGEN on 2026-11-24 for periodic records: `as_of`, `issued_at`,
     model identity and snapshot hash. There is no answer yet.
   - Q1 is possible only after those records arrive live.
5. **Warm-up and training.**
   - D2 needs 7 days of slots and P3/P4 need 24 bars, so complete feature rows begin about 7 days after collection
     starts.
   - Training then takes at least 4 weeks: 672 hourly bars and 336 non-overlapping windows. With D1, it takes at
     least 12 weeks (row 2).
   - Then the model is fitted and frozen.
6. **Stage 1 forecasts.** Proposed (section 10, row 16): batch forecasts of M and B1 from point-in-time features,
   written after each DIDM snapshot.
   - `issued_at` is the actual write time.
   - Each snapshot's SHA-256 and capture time go into an append-only log when the snapshot is taken.
   - Batch forecasts are written after their bars. They serve criteria 1, 2 and 4, and they are the evidence behind
     the stage 2 gate (section 7). They never act as live forecasts.
7. **Stage 1 evaluation.** The next 6 weeks run forward, with the section 6 terms registered before they start. The
   stage 1 evaluator judges criteria 1, 2 and 4, S2 and S3, cut at `evaluation_end`.
8. **Stage 2, only if stage 1 passes.**
   - **Live forecasts.** The forecast writer runs for M and B1 at each bar close. For that, the DIDM snapshot, the
     bridge and the feature builder run automatically each hour. `issued_at` is the actual write time, and write and
     receipt times go into an append-only log (contract section 3, rule 7).
   - **Quote record.** A quote recorder captures the last trade price, the last trade time and the best bid in the
     same second, at a fixed interval, with the block, floor and daily-stop flags.
     - **Flags source.** The app's runtime state, read at the same second. Blocks caused by the app's own bid-gap
       alerts are left out, because each arm simulates its own. If the app is not running, the flags are recorded
       as false, and the record says so.
     - Each day's file is frozen with its SHA-256.
     - The coverage thresholds and the void rule are S7.
     - Its Upbit public calls start only after O28 and share the budget (step 2).
   - **Length.** Stage 2 lasts at least the pre-registered minimum number of days.
9. **Owner decision (M11-T5).** It uses the reports of sections 7 and 8. The open fill-record check (section 7)
   comes before any operational approval.

**Recurring owner work.** For about 11 weeks, plus stage 2, the owner's PC must run the collector with its run-log
wrapper, the snapshots and the recorders. Under row 4 (a), the owner also stops the recorders around A0 and M9-T4
runs. A missed run makes features missing, and enough of them voids a window (S1). Section 10, rows 4 and 5, set
this schedule.

**Earliest dates.** Stage 1 ends about 11 weeks after price and DIDM collection start: 7 days of warm-up, 4 weeks
of training and 6 weeks of evaluation. Collection starts after O28. The M11-T4 record, before stage 1 opens, also
waits for O38 and, as the checklist stands, M9-T4 (section 6).

## 10. Owner decisions

Who builds the model is already decided: TRADEGEN research, O32 (a), 2026-11-24 19:05:53 KST. The rows below are
open. Each gives the options with the proposed default first, and what each choice means. O38, the PR #70 points,
is a separate owner decision that must come before the M11-T4 record (section 6). Please give answers privately, not
on the public PR (section 2).

| # | Decision | Options (default first) | What it means |
| --- | --- | --- | --- |
| 1 | Market, bar, horizon | (a) KRW-BTC, 1-hour bars, 2-bar horizon. (b) 15-minute bars with a 2-bar (30-minute) horizon. (c) Another KRW market. | (a) At most 504 outcome windows in 6 weeks. (b) The same maximum of about 511 windows, but one replay covers only 10.7 days: fewer releases and regimes, and a 30-minute move must clear the same cost hurdle. Keeping a 2-hour horizon (8 bars) would leave at most 127 windows. (c) Thinner trading gives more stale-trade alerts and fewer reliable bars. |
| 2 | Feature set | (a) P1-P4 and D2; D3 and Q1 only if admitted under section 4. (b) P1-P4 only. (c) (a) plus D1, with at least 12 weeks of training. | (a) Tests whether news volume adds direction beyond prices. D1 is left out because 4 weeks hold about 3 releases, well below the minimum of 8. (b) M equals B1, so the study tests nothing new. (c) About 9 releases in training, but stage 1 starts about 8 weeks later. |
| 3 | Feature lists and fit terms | (a) D1 event series, if D1 is chosen: ALFRED `CPIAUCSL` (US CPI) and `PAYEMS` (US payrolls), both monthly, and ECOS `722Y001` item `0101000` (Bank of Korea base rate) at the monthly cycle. Q1 types: regulation, exchange hacks and monetary policy, mapped to QuantGPT's type names in M11-T4. D1 needs at least 8 events in training. L2 penalty 1.0 on standardized features. Training: 4 weeks after a 7-day warm-up. (b) Longer lists or a longer training window. | (a) Each listed series gives about one new item a month, so 4 weeks hold about 3 events, at most about 6. The US policy rate target is left out because its series is daily. (b) More events, but a later start. Any change after the freeze starts a new study. |
| 4 | Price recorder and the shared Upbit budget | (a) A new research recorder of hourly bars with real `known_at` and the bid and ask at each close, about two public calls per hour, started after O28. The owner stops it during A0 and M9-T4 runs, and it backfills the missed bars afterwards. (b) The same recorder running alongside those runs, within a combined request budget the owner allocates. | (a) A small new tool, and the PC runs continuously. Stopping and restarting it around A0 and M9-T4 is owner work. Features near the missed bars go missing (S1). (b) No pauses, but it needs a shared-budget change to the A0 probe's coordination, whose lock is exclusive. In both, a 429 or 418 hold stops every reader. Extending the M9-T4 recorder is not offered: its capture is D14 closure code, so extending it would need a code change, a new code approval and re-signing. Its capture size limits would also refuse an 11-week plan, and it gives 300-second universe frames, not hourly bars with `known_at`. |
| 5 | Collector and delivery cadence | (a) DIDM collector every 15 minutes, into one store per KST day, with the run-log wrapper. QuantGPT records at the cadence in M11-T7's answer. The same cadence in training and evaluation. (b) One growing store with a cutoff-window bridge report (M11-T8 option (b)). (c) Daily DIDM collection, with D2 dropped. | (a) Owner PC work for about 11 weeks. Missed slots are backfilled when possible; others count as missing (S1). One growing store would pass PR #76's 2,000,000-row limit in about a week, and per-day stores avoid that without changing QUANTGEN. (b) Needs a reviewed bridge change before collection starts. (c) Less work, but no news-volume feature. |
| 6 | `hurdle_bps` | (a) An integer rounded up from Upbit's published fee for the market (both sides), plus the median spread from the price recorder during warm-up, plus a disclosed slippage allowance of 5 bps, fixed at the freeze. (b) A provisional value set now. | (a) Needs no extra tool; training waits only for the warm-up spread. The 5 bps slippage is an assumption, not a measurement. (b) If measured costs later differ, outcomes are mislabeled, and the restart counts as an attempt. |
| 7 | Replay ceiling and targets | Ceiling: (a) a private research ceiling at or below 0.05, chosen now and kept private; (b) the owner's signed Y after O18. Targets: (i) `up_y` = ceiling and `down_y` = half the ceiling; (ii) `up_y` below the ceiling. | Ceiling (a): results hold only for that ceiling, and a signed Y below it ends or blocks stage 2 (S6). Ceiling (b): until a Y is signed, stage 1 cannot be pre-registered and the adapter computes no gate. Signing a Y first needs the BR-26 signer and owner-log PR, code approval and the study freeze, which ties this study to the first-trade path. Targets: a widening to `up_y` stays in force after the forecast expires (section 3), and until O38 is decided the same forecast confirms its own widening about one quote later. So choose an `up_y` you accept holding indefinitely. (ii) holds less, but limits the benefit. A lower `down_y` gives more alerts and blocks. |
| 8 | Evidence plan | (a) One 6-week stage 1 window, judged once at the end, per direction. (b) A longer or pooled evaluation. (c) A lighter bar, using criterion 2 only. | (a) The most likely result is INCONCLUSIVE or NOT SHOWN unless skill is large (section 6). (b) Needs a replay and adapter change and a revised design first. (c) Easier to pass, but says nothing about acting on calls. |
| 9 | Gate terms | (a) `confidence` 0.60, `min_validation_calls` 100 per direction, `max_calibration_gap` 0.10. (b) The same with a gap of 0.05. (c) A lower cutoff, such as 0.55. (d) Higher cutoffs or more calls. | (a) At 100 calls in a direction, it passes about 54% of the time at a true hit rate of 0.70 and 16% at 0.65; at 250 calls, about 90% and 35%. The gap rarely binds. (b) At 100 calls: about 44% and 5%. (c) A true rate of 0.65 breaks even at about 96 calls, and the call filter admits more calls, but the gate then accepts a smaller edge over the base rate (section 6). (d) Need more calls than 6 weeks supply, unless the true rate exceeds the cutoff by about 0.10 or more. |
| 10 | Criteria 2 and 4 | (a) Margin 0: the one-sided 95% lower bound of the up-versus-down log-loss improvement over B1 must be above zero; the per-half check uses point estimates. (b) A positive margin. (c) A full gate in each half. | (a) Any reliable improvement counts, however small. (b) Stricter: a small gain fails. (c) Usually fails: about 29% at a true rate of 0.70 with 100 calls per half. |
| 11 | Stage 2 plan, baseline and long records | Plan: (a) a separate live stage, starting within 14 days after stage 1 passes and lasting at least 14 days; (b) one live window for both stages. Baseline: (a) static Y at the ceiling; (b) a fixed lower static Y. Long records: (a) carry state between 128-observation documents with the carry-over wrapper (section 7); (b) a replay change first. | Plan (a) adds at least 14 days, but only after evidence of skill. Plan (b) needs live forecasts and quote recording from the first day. In both, the gate stays at the stage 1 evidence (section 7). Baseline (a) makes missed alerts impossible, so the test is the trade-off; with baseline (b), misses become possible. Long records (a) needs the wrapper, and (b) a code change and review, before stage 2; both need row 17. Hourly DIDM refresh in stage 2 costs about 27 s per run plus a collector pause or a coordinated backup, and reports are deleted once their hashes and features are logged (section 9). |
| 12 | Stage 2 quote record and limits | (a) A quote every 10 seconds; 95% daily quote coverage and 95% live-forecast coverage; T = 30 minutes; at most 1 excess alert episode per day on average. (b) Other values. | (a) About 8,640 quote captures per day during stage 2, after O28: one or two public Upbit calls each, or a WebSocket stream. They share the PC's Upbit allowance under OQ17 (row 4). An alert counts once per episode. A stricter limit is harder to pass; a looser one tolerates more blocked buying. |
| 13 | Attempt budget | (a) At most 3 attempts for this model family, all reported with the family-wise false-pass chance. (b) 3 attempts with a Bonferroni-adjusted bound (z = 2.394). (c) 1 attempt. (d) No limit. | (a) Allows recovery from a voided window, which spends no test level. With 3 judged attempts, the chance of a lucky pass is about 14%. (b) Keeps it near 5%, but the adapter's gate uses 1.96, so stage 2 needs an adapter change to match. (c) Strictest; one data gap ends the study. (d) Not recommended: retries inflate the chance of a lucky pass. |
| 14 | Storage, privacy, data rights | (a) A private folder outside Git and OneDrive for data, models, forecasts, quote records, the M11-T4 record and these answers. Public hashes only for records whose content cannot be guessed (section 2). Confirm research use of DIDM data and of QuantGPT outputs. | If DIDM research use cannot be confirmed, D1-D3 are dropped. The study then continues with Q1 only if Q1 is admitted and its rights are confirmed. Otherwise M reduces to B1, and the study stops. |
| 15 | OQ9 | (a) No: under `CLAUDE.md` section 7.5, model output never releases an entry hold, so this study serves OQ9 only offline. (b) Revisit later as a separate owner decision. | OQ9 (PR #65/#71) lets an authorized, tested model release an entry block. Section 7.5 prohibits "모형 출력으로 이미 발생한 경보·진입 보류·손실 중단을 해제하는 것" (using model output to release an alert, entry hold or loss stop that has already fired) and names no model type. Section 7.3 names the OQ9 buy-advantage model candidate as a connection point, so 7.3 and 7.5 are in tension. Whether 7.5 binds every model or only section 7 pipeline models is part of this question. Until the owner resolves it, no path leads to `entry_unblock`. |
| 16 | Stage 1 forecast production | (a) Batch after each snapshot, with snapshot hashes logged at capture. (b) A live writer at each bar close from the start. | (a) Less automation. Batch forecasts serve criteria 1, 2 and 4 and the stage 2 gate, never as live forecasts. (b) Needs hourly DIDM refresh from the start, about 1,850 bridge runs over 11 weeks (section 9), and allows plan (b) in row 11. |
| 17 | Latch convention in the stage 2 replay | (a) Release a carried latch at the first 128-observation boundary after its recorded cause has cleared (a clean quote and every recorded flag false), the same in every arm, and report per arm the time a runtime block would still have held. (b) End each arm's measurement at its first latch. | (a) More lenient than runtime, where an entry block stays until the owner's release (BR-9(b), OQ9). No forecast or model output plays any part. (b) Strictest, but every alert and every unknown quote latches an arm, so with 10-second quotes stage 2 would usually end within days and be inconclusive. |

## 11. Review against the edge-strategy-reviewer criteria

The skill's eight criteria, applied to this design. There is no position or exit: Y is a monitoring threshold, not
a trade.

| Criterion | Assessment |
| --- | --- |
| C1 Edge plausibility | Weak. The latency of public news makes the edge doubtful. Criterion 2 tests direction beyond prices, and the default answer is no. |
| C2 Overfitting risk | Partly controlled: at most 8 features, a fixed penalty, one fit, a frozen artifact, no tuning on the evaluation window, and an attempt budget with a stated family-wise rate. D1 rests on few events and is out of the default set. The feature lists carry selection risk, so they are fixed before any training data is examined. |
| C3 Sample adequacy | The main risk. At realistic skill, 6 weeks gives a pass chance well under 50% (section 6). The expected result is INCONCLUSIVE if M makes fewer than 100 calls per direction, and NOT SHOWN otherwise. |
| C4 Regime dependency | Checked only by the half-window point estimates. Six weeks covers few crypto regimes, so a pass is weak evidence. |
| C5 Exit calibration | Not applicable. Targets are Y values bounded by the ceiling; a widening persists until a later proposal (section 3). |
| C6 Risk concentration | Not applicable. There is no position size or order, and Y stays at or below the ceiling and 5%. |
| C7 Execution realism | The hurdle is net of Upbit's fee, the measured spread and a disclosed slippage allowance. Bars use real receipt times, and features lag one bar. Stage 2 uses live issue times and a recorded quote stream, but no fills, so execution costs are not measured (section 7). |
| C8 Invalidation quality | Seven specific stop rules (section 8) and five outcome labels (section 6). |

Overall: REVISE until the section 10 decisions are made. The design is not a trading strategy and is never
export-eligible.

## 12. Not in this document

- **No code.** After the owner decides, separate PRs add the following under `tools/research/`. Each has synthetic
  tests, the five flags and both import checks:
  - a price recorder, with bar backfill, the bid and ask at each close, and shared-budget coordination;
  - a run-log wrapper for the DIDM collector and QuantGPT deliveries, per source and per GDELT slot, with slot
    backfill;
  - a point-in-time feature builder: DIDM re-selection per bar, D1 first receipt, the D3 version filter and export
    receipt times, and merging of daily-store reports;
  - a fit-and-freeze tool;
  - a forecast writer with its manifest;
  - a stage 1 evaluator. It reproduces the adapter's counting exactly for both directions: non-overlap from
    `evaluation_start`, the `issued_at` filter, the hurdle, the call filter, the z = 1.96 Wilson bound and the gap.
    It cuts at `evaluation_end`, and computes criteria 2 and 4, S2, S3 and B2's criterion 1 report. A test checks
    that it matches the adapter's holdout on a synthetic live run. The 6-week limit applies to stage 1 only because
    this evaluator mirrors the replay;
  - for stage 2, a quote recorder and the replay carry-over wrapper (state, the row 17 convention and voided days),
    or a long-record replay;
  - under row 5 (b), the cutoff-window bridge report.
- **The M11-T4 pre-registration record.**
- **OQ9's benefit metric.** It is still undefined (row 15).
- **The fill-record comparison** that `docs/adaptive-bid-gap-preview.md` requires before operational approval
  (section 7).

법률, 세무, 투자 조언이 아니며 면허를 가진 자문가가 아니다
