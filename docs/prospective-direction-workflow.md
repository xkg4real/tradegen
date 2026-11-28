# Private prospective direction study

This offline workflow links the frozen M, price-only B1 and class-frequency B0 models to their inputs, records when a forecast first became available, and preserves interim, final and Stage 2 results. It implements the separate forward windows in §9 of the [direction study design](direction-model-study-design.md). A qualifying result goes to the owner's M11-T5 review. The separate first-order candidate follows the [sealed launch study](launch-workflow.md).

## Before registration

Use an explicit private folder outside Git, OneDrive and the owner's application state. Keep a separate private backup of source files, recorder archives and journal checkpoints. Register before the first evaluation bar after collecting the agreed training data and freezing the models. With the design's proposed schedule, collection needs seven warm-up days, four training weeks and six forward evaluation weeks. Including D1 calls for longer training. Stage 2 opens only after a Stage 1 PASS, with its own collection window.

Prepare the following in that folder.

| Input | Contents |
| --- | --- |
| `fit/` | Unmodified `model_M.json`, `model_B1.json`, `model_B0.json` and `fit_report.json` from `tools.research.direction_model_fit`. All must reproduce from the named training sources in the same numerical environment. |
| `refs.json` | Object with keys `O28`, `O38`, `M9-T4`, `section10`. Each value is the SHA-256 reference to the corresponding private prerequisite record, including the source-use decisions. Have the authorized person check those records. The tool records declared references and cannot authenticate authorization. |
| `training-inputs.json` or a later `inputs.json` | Keys `history` (price export filename, or ordered contiguous export filenames for a long training window), `price_log` (directory with `bars.jsonl`), `run_log` (directory with `run_log.jsonl`), `didm_reports`, `didm_exports`, `quantgpt_snapshots` (arrays of filenames). Paths are relative to this JSON's directory. Keep the original price/quote exporters' adjacent `.manifest.json` files. |
| `terms.json` | The agreed values in the table below, established before evaluation. The fit provides the model identities, feature names/definitions, upstream identities, training dates and penalty. Model pins can also be supplied for cross-checking. |

| Terms | Fields |
| --- | --- |
| Instrument, clock, cost | `rule_version` equal to `external-forecast-v1`, `market`, `scope`, `source_id`, `step_seconds`, `horizon_seconds`, `hurdle_bps`. Times below are UTC epoch seconds. |
| Stage 1 | `evaluation_start`, `evaluation_end`, `interim_at` exactly halfway on the bar grid, `stage1_writer_mode` (`batch` or `live`), `confidence`, `min_validation_calls`, `max_calibration_gap`, `criterion2_margin`, `bootstrap_seed`, `b2_seed`, `attempt_number`, `attempt_budget`. The bootstrap uses 10,000 replications. Optional `z_value` may retain or tighten the design bound, and `min_d1_events` records the selected fit requirement. |
| Stage 2 | `ceiling_y`, `up_y`, `down_y`, `ceiling_mode` (`7a` or `7b`), `latch_convention` (`17a` or `17b`), `stage2_start` and exclusive `stage2_end` at KST midnight. Start must follow the final gate by at most 14 days. Set `min_stage2_days`, `quote_interval_seconds`, `min_daily_quote_coverage`, `min_daily_live_forecast_coverage`, `early_warning_window_seconds`, `max_excess_alerts_per_day`, `min_early_warnings`. This workflow supports the three-arm comparison with static Y at the research ceiling. |

Use ratio strings for `confidence`, calibration gap, and the three Y values as in the forecast contract. Use JSON numbers for Stage 2 coverage and criterion margins. All thresholds and scheduling choices must match the actual private decisions. Coordinate the attempt number and family-wide budget across all archived runs, including adverse outcomes.

D1/D2 need original, recorded bridge reports and the collector run log. D3 needs full DIDM exchange exports matching the recorded raw byte digests. Q1 supports the versioned QuantGPT feature-snapshot surface with its model identity, content digest and actual receipt. Optional D3/Q1 need a contemporaneous delivery covering every training bar. Individual source JSON files must fit the 64 MiB reader. Partition large source stores before exporting, retaining all required records and their original receipt times. The feature builder uses the receipt as an availability constraint. A Qlib retrospective scan can nominate a candidate for its own preregistration. Its scores cannot replace the frozen models' captured forecasts.

## Commands

Run from the application checkout with an explicit private archive. PowerShell examples below use local variables for the two directories. The archive path is a new directory for this prospective attempt.

```powershell
$tool = 'tools.research.prospective_direction_study'
python -m $tool --archive $archive register --terms "$private/terms.json" --prerequisites "$private/refs.json" --fit-dir "$private/fit" --inputs "$private/training-inputs.json"
python -m $tool --archive $archive forecast --inputs "$private/inputs.json"
python -m $tool --archive $archive interim --history "$private/interim.json" --price-log "$private/price-log"
python -m $tool --archive $archive forecast --inputs "$private/inputs.json"
python -m $tool --archive $archive final --history "$private/final.json" --price-log "$private/price-log"
```

Run `forecast` after each eligible source capture. Stage 1 batch mode issues every new available grid row together, while live mode takes only the latest fresh row. Each invocation timestamps creation using the local clock and records receipt after sealing. Duplicate or superseded submissions cannot revise issued forecasts. Run the single interim after its price boundary and before the final boundary. The two price exports must end exactly at the relevant boundary. Retain the journal head returned at registration and at later checkpoints independently.

After a timely final PASS, repeat `forecast` on fresh Stage 2 rows. Store each completed KST day of quotes, including failed observations, with a private ceiling-history extract. This JSON has `kst_date`, `initial_signed_y`, time-ordered `events` containing `at` and `signed_y`, and `source_sha256` for the separately retained authority history. Its reference and completeness require owner corroboration. The tool does not read the owner's state.

```powershell
python -m $tool --archive $archive quote-day --quotes "$private/day.json" --quote-log "$private/quote-log" --ceiling "$private/day-ceiling.json"
python -m $tool --archive $archive review
python -m $tool --archive $archive status --pinned-head $privateCheckpoint
```

Call `review` after the registered end when all available days have been recorded. It freezes the verdict. A missing day or absence of live captures yields INCONCLUSIVE. Daily export coverage uses the full preregistered denominator. A duplicate interval, mismatched recorder entry, revised historical price, altered blob or non-descending recorder head is refused. Inspect the failure privately and retain the original inputs. Retrieve a report as `<archive>/<report>.json` using its returned content address. The journal binds adverse outcomes as well as successes. An independent checkpoint detects rewrite or rollback before that checkpoint. Independent timestamping and source authentication require separate evidence.

## Interpreting the records

For an upside comparator, use `stage2_forecast` events in the verified `prospective.jsonl`. Each event's `models.M.forecast` and `models.B1.forecast` refer to frozen forecast-contract documents. Join by market, as-of, hurdle and horizon. Earliest usable time is the later of the forecast's `issued_at` and the event's `at`. Discard expired forecasts. A Stage 1 batch has no standing as a contemporaneous trading signal.

A price-based test of catching a surge needs a separately registered surge definition, baseline, fees, slippage and contemporaneous executable ask and bid. The daily Stage 2 export contains a bid. The original quote-recorder entry additionally records the ask and whether both calls finished in the same second. A missing side stays missing. Stage 1 scores conditional direction and Stage 2 scores alert behavior. Neither establishes realized returns, fill prices or net alpha. The independent fill-record check, strategy review, risk terms and owner activation remain separate.
