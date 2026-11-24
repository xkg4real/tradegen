# Direction forecast input contract (research only)

Status: merged 2026-11-24 (Asia/Seoul), checklist item M11-T2. Read by the research-only replay adapter in section 8
(M11-T3).

TRADEGEN can study directional forecasts from an outside model, for example one built on QUANTGEN's QuantGPT or
DIDM outputs (section 7), or the moving-block model in PR #70. This document fixes what such a forecast must contain before TRADEGEN reads it, and what TRADEGEN
may and may not do with it. The format is `tradegen-direction-forecast-v1`. It is a TRADEGEN boundary format. It
does not claim that any producer already writes it.

A forecast is a research input. It never becomes an order input, an approval or a signed term by being read.

## 1. Delivery

- **Interface, public.** The producer describes its output in a short interface note: output names, this format
  name, the meaning of `as_of`, horizons, markets, model name, version and digest, training cutoff and the SHA-256
  of each published snapshot. For QuantGPT this note is `QUANTGPT_TRADEGEN.md` on the `handoff` branch of
  `xkg4real/quantgen` (checklist M11-T1). The note carries no weights, prompts, training data or private
  specification, because both repositories are public.
- **Snapshots, private.** Snapshot files reach the owner's PC offline and stay outside Git. A future reader takes an
  explicit local path. It never downloads, polls or runs the model.
- **No code dependency.** TRADEGEN imports no producer code. Only snapshot files and the interface note cross.

## 2. Snapshot file

One UTF-8 JSON file without a byte-order mark, at most 16 MiB and 50,000 forecasts. Duplicate keys, `NaN`,
`Infinity` and unknown keys are refused. A refused file is refused whole; no forecast is dropped silently.
Times are integer UTC epoch seconds. Probabilities are decimal strings, as in PR #70. `hurdle_bps` is an integer
number of basis points from 0 to 9,999.

```json
{
  "format": "tradegen-direction-forecast-v1",
  "producer": "quantgpt",
  "model": {"name": "quantgpt-direction", "version": "0.1.0",
            "sha256": "<64 hex: digest of the frozen model artifact>",
            "training_cutoff": 1763900000, "frozen_at": 1763910000},
  "generated_at": 1764000300,
  "forecasts": [
    {"market": "KRW-BTC", "as_of": 1764000000, "issued_at": 1764000240,
     "horizon_seconds": 3600, "hurdle_bps": 25,
     "probabilities": {"up": "0.55", "down": "0.20", "neutral": "0.25"},
     "direction": "up"}
  ],
  "snapshot_sha256": "<64 hex>"
}
```

The values above are illustrative, not a model result or a suggested setting.

| Field | Rule |
| --- | --- |
| `format` | Exactly `tradegen-direction-forecast-v1`. A new major version needs a new contract. |
| `producer` | Short identifier, 1-64 characters of `[a-z0-9-]`. |
| `model.name`, `model.version` | The model identity, 1-128 characters each. One snapshot holds one model version. |
| `model.sha256` | 64 lowercase hex characters naming the frozen artifact (weights or rule set) that produced every forecast here. |
| `model.training_cutoff` | Latest time of any data used to fit or tune the model. |
| `model.frozen_at` | Time the model and its settings were fixed. `training_cutoff <= frozen_at`. |
| `generated_at` | Time the file was written. It is at least every `issued_at`. |
| `market` | An Upbit KRW market code such as `KRW-BTC`. Long spot only. |
| `as_of` | Information cutoff. Every input behind this forecast was published at or before `as_of`. |
| `issued_at` | Time the forecast itself existed. `as_of <= issued_at <= generated_at`. |
| `horizon_seconds` | The outcome window is `(as_of, as_of + horizon_seconds]`. From 60 to 2,592,000. |
| `hurdle_bps` | Cost hurdle, net of fees, spread and slippage: "up" means the compounded return over the window exceeds `+hurdle`, "down" means it is below `-hurdle`, otherwise "neutral". This is PR #70's definition. |
| `probabilities` | Exactly `up`, `down` and `neutral`, each in `[0, 1]`, summing to exactly 1 in decimal arithmetic. |
| `direction` | The class with the highest probability. A tie, or a value that disagrees with `probabilities`, refuses the file. |
| `snapshot_sha256` | SHA-256 of the document without this field, serialized as sorted, compact ASCII JSON (`sort_keys=True`, `separators=(",", ":")`, `ensure_ascii=True`), the same encoding as PR #70's `model_sha256`. It must also equal the value in the interface note. |

A matching hash proves byte identity, not authorship, authenticity or permission to trade, as with the DIDM bridge
(`docs/didm-source-bridge.md`).

## 3. Point-in-time rules

1. **Availability is `issued_at`, not `as_of`.** A replay observation at time `t` can see a forecast only when
   `issued_at <= t`. PR #70's holdout uses the bar close as the forecast time and refuses honest data whose
   `known_at` is later than the close; this contract keeps the two times apart to avoid that.
2. **No forecast after its window.** A forecast applies to an observation at `t` only while `t < as_of +
   horizon_seconds`. When several are live, the one with the latest `issued_at` for that market and horizon is used.
3. **No revisions.** The key is (`model.sha256`, `market`, `as_of`, `horizon_seconds`). The first received forecast
   for a key stands. A later file with different content for the same key refuses that later file.
4. **In-sample is not evidence.** A forecast with `as_of <= model.frozen_at` is in-sample. It may be shown but never
   counts toward calls, hit rate or calibration.
5. **One model version per study.** A study pins the model triple (name, version, `sha256`) before its evaluation
   window. A different triple starts a new study; versions are never pooled.
6. **Outcomes from TRADEGEN data.** Realized direction is computed by TRADEGEN from its own Upbit trade or candle
   record for `(as_of, as_of + horizon_seconds]` with the same hurdle, never taken from the producer.
7. **Producer timestamps are trusted only as claims.** A reader cannot detect a backdated `as_of` or `issued_at`
   from JSON alone. Forward validation (section 5) therefore records each snapshot's receipt time on the owner's PC
   and uses the later of receipt and `issued_at`.

## 4. Where TRADEGEN may use it

- **BR-26 working Y (PR #70 replay).** An adapter (M11-T3, `tools/research/` only, section 8) feeds these
  forecasts to the replay in place of its built-in moving-block forecast. The replay's own rules stay: a decision
  applies only to later observations, a widening needs a later clean observation under the old Y, a block or stop
  suppresses proposals, and `0 < Y <= signed ceiling <= 0.05`. The direction-to-target map (`up_y`, `down_y`), the
  confidence cutoff, minimum calls and calibration gap are fixed in the pinned terms before the evaluation window,
  as PR #70 requires. Qualification uses only earlier out-of-sample forecasts whose windows ended before the
  observation.
- **OQ9 buy-advantage candidate.** The PR #65 design (owner decisions, PR #71) lets an authorized, tested model
  release an entry block when a new buy has a verified advantage, but the benefit metric and acceptance test are
  not yet defined. Until they are, these forecasts serve only offline study of candidate metrics. No code path
  leads from a forecast to `entry_unblock`.
- **Order of steps.** Offline replay, then forward validation with criteria registered before the window starts
  (M11-T4), then the owner's decision and signature (M11-T5). Any runtime use is a separate, reviewed change.

## 5. Prohibitions

- No module in the D14 code closure (`core/compliance/owner.py` `code_files`: `core/compliance`, `core/odds`,
  `execution`, `execution_control`, `execution_orders`, `execution_accounts`, `execution_network`,
  `execution_launch`, `tools/owner` and everything they import) imports the reader, the adapter or producer code.
  Check: no `tools/research/` path appears in `code_files(repo_root)`.
- Every report from a reader or adapter states `research_only=true`, `live_eligible=false`,
  `execution_ready=false`, `source_authenticated=false` and `owner_approval_verified=false`.
- A forecast never clears an alert, an entry block, a daily stop, a floor halt or any loss stop, and never creates an
  entry or sell signal.
- A forecast cannot change the 5% maximum, the owner's signed ceiling, the signed loss limits or any signed term.
  Loosening a signed term follows D12 and the owner's signature.
- The producer never touches orders, signatures, keys, `.env`, the owner log or the real home directory, and
  TRADEGEN never writes to the producer's repository or ledger.

## 6. Checking an interface note (M11-T1)

Compare a producer's interface note with this contract and report any gap. It should state:

1. the format name and version, or a mapping from its own format to every field in section 2;
2. what `as_of` means, and whether `issued_at` is recorded separately;
3. the horizons, markets and hurdle definition, including which costs the hurdle covers;
4. the probability classes, and that they sum to 1;
5. the model name, version, artifact digest, training cutoff and freeze time;
6. how snapshot hashes are published and how files reach the owner offline;
7. that no weights, prompts, private specification or credentials appear in the public note.

## 7. QuantGPT interface v0.1 (checked 2026-11-24)

`QUANTGPT_TRADEGEN.md` v0.1 on `xkg4real/quantgen` `handoff` (`0c6fb61`) states that QuantGPT produces **no price
direction, return or probability forecast**. Its outputs are explanations, summaries, research hypotheses and
news-type judgments in a `qgpt-env-v1` envelope, and its confidence scores are uncalibrated. So no QuantGPT output
is a `tradegen-direction-forecast-v1` forecast today, and none can enter the BR-26 replay or an OQ9 study as is.
A direction model built separately, with QuantGPT or DIDM outputs as its features, would deliver this format; its
features are the producer's business, but its forecasts follow sections 2-5.

Other differences from this contract:

- QuantGPT's `as_of` is the evidence receipt time, which matches `as_of` here. There is no separate `issued_at`.
- The model is identified by `model.id`, `model.adapter` and `model.prompt_version`. A producer maps that triple,
  plus the decoding settings, to one `model.sha256`. Replay reads recorded outputs; it never reruns the model.
- `request_sha256` names a request, not an output file. A snapshot still needs `snapshot_sha256`.
- The import boundary in v0.1 lists the `execution*` packages only. The boundary here is the whole D14 closure,
  which also includes `core/compliance`, `core/odds` and `tools/owner` (section 5).
- An "owner screen explain button" in TRADEGEN, mentioned in v0.1, would be an application change, not a research
  input. It needs its own review and owner approval, outside this contract.

Answers to v0.1 section 8:

1. **Paths QuantGPT must not touch.** The D14 closure in section 5, the owner log and signer, `.env` and keys, the
   real home `~/.tradegen`, and TRADEGEN's Git repository. TRADEGEN reads snapshot files only.
2. **Preregistration.** TRADEGEN's `research_lab/` is a frozen retrospective study: `research_lab/run.py` refuses to
   run after any pinned source changes, so nothing is added there. Preregistration for direction forecasts is
   checklist item M11-T4 and is not defined yet. It will pin the model triple, hurdle, horizon, cutoffs, targets and
   start time before the window opens.
3. **Input for BR-26 and OQ9.** Section 2: one forecast per market and horizon, probabilities over up, down and
   neutral against a cost hurdle. A missing, stale or refused forecast means no forecast, and BR-26 keeps the
   working Y. Refresh at least once per horizon for each market studied. The lag between `as_of` and `issued_at` is
   recorded, not capped, and replay uses `issued_at`.
4. **Python and dependencies.** TRADEGEN requires Python 3.13 or later (`pyproject.toml`). It takes no private
   dependency, because it imports no producer code.

## 8. Replay adapter (M11-T3)

`tools/research/direction_forecast_adapter.py` checks snapshots against sections 2 and 3 and replays them through the
PR #70 BR-26 replay in place of its built-in moving-block forecast. The replay's quote, block, tightening and
confirmation rules are unchanged; only the source of the direction differs.

```shell
python -m tools.research.direction_forecast_adapter --replay study.json --snapshot forecasts-001.json=<sha256>
```

Repeat `--snapshot` in receipt order. Each `<sha256>` is the value from the producer's interface note. One run reads
at most 50,000 forecasts across all its files; a file's size in objects is checked before it is parsed. Exit code 0
means only that the files passed these checks. Exit code 2 prints a fixed reason and no partial result. Every report
carries the five flags in section 5.

`study.json` is a `tradegen-adaptive-bid-gap-replay-v1` document. Its `history` is TRADEGEN's own contiguous bar
record (`end`, `known_at`, `return_bps`; at most 1,024 bars, so choose the bar size to cover the study). Its `model` is
the study's preregistered terms, pinned by `terms.model_sha256` as in PR #70:

| Field | Meaning |
| --- | --- |
| `scope`, `source_id` | As in PR #70: the replay scope and the bar record's source. |
| `rule_version` | `external-forecast-v1`. |
| `market`, `horizon_seconds`, `hurdle_bps` | The forecasts this study uses. Others in the snapshots are ignored. The horizon is a whole number of bars, at least two. |
| `forecast_model` | The model's `name`, `version` and `sha256`. A snapshot of another model is refused. |
| `evaluation_start` | Start of the evaluation window. It must be after the model's `frozen_at` and on or after the first bar. Earlier forecasts never count. |
| `step_seconds` | Bar spacing of `history`. |
| `confidence` | A forecast is a call when its direction's probability is at least this value (above 0.5). |
| `min_validation_calls`, `max_calibration_gap`, `up_y`, `down_y` | As in PR #70. Targets stay within the signed ceiling and 5%. |

At each observation the adapter uses only forecasts issued at or before it. Their `as_of` must be on the history's
bar grid (a bar's `end`), so a producer serving a BR-26 study issues forecasts at bar closes. One that is not
refuses the study at that observation with `FORECAST_OFF_BAR_GRID`. Each outcome window `(as_of, as_of + horizon]`
is then a run of whole bars whose last bar ends at `as_of + horizon`. Evidence comes from the earliest
non-overlapping forecasts in the evaluation window whose last outcome bar was known before the observation, so
every scored window ended before it (section 4). A call needs the PR #70 minimum count, a nominal 95% hit-rate lower
bound at or above `confidence`, and a calibration gap within the limit. The live forecast is the latest issued one whose window is
still open; none means the working Y is kept. Offline replay uses `issued_at` as the visible time. Forward validation
must also record each snapshot's receipt time (section 3, rule 7).

Verification: `python -m unittest tools.research.test_direction_forecast_adapter` uses synthetic data only.

법률, 세무, 투자 조언이 아니며 면허를 가진 자문가가 아니다
