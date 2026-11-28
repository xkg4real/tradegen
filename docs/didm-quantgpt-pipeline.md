# DIDM & QuantGPT Offline Research Pipeline (Section 12)

Status: research-only offline toolchain implementing Section 12 of `docs/direction-model-study-design.md`,
`docs/direction-forecast-contract.md`, and `QUANTGPT_TRADEGEN.md` (v0.2).

Every output produced by these tools is a **research input only**. None of these tools places orders, reads
credentials or `.env`, touches `~/.tradegen` or `~/.nextgen`, signs owner terms, or releases any runtime alert,
entry hold, floor halt, or daily loss stop.

---

## 1. Isolation & Safety Invariants

1. **D14 Code Closure Isolation**:
   - No module in `core.compliance.owner.code_files(repo_root)` (`core/compliance`, `core/odds`, `execution*`,
     `tools/owner`, and their transitive imports) imports `tools.research`, `quantgpt`, `quantgen`, or `qgpt`.
   - Every direction-study module in `tools/research/` is checked via AST to ensure zero imports from
     `core.compliance`, `core.odds`, `core.isolation`, `execution*`, `tools.owner`, `tools.signer`, `config`,
     `main`, `quantgpt`, or `quantgen`.
2. **Mandatory Research Flags**:
   Every report, summary, inspection document, and sidecar manifest embeds:
   ```json
   {
     "research_only": true,
     "live_eligible": false,
     "execution_ready": false,
     "source_authenticated": false,
     "owner_approval_verified": false
   }
   ```
3. **Two Canonical JSON Regimes**:
   - **Regime A (TRADEGEN ASCII)**: `json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")`
     — used for `tradegen-direction-forecast-v1` `snapshot_sha256`, `quantgen-feature-snapshot-v0` `snapshot_sha256`,
     `tradegen-direction-model-v1` `sha256`, hash-chained research archives, and sidecar manifests.
   - **Regime B (QUANTGEN / QuantGPT / DIDM UTF-8)**: `json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")`
     — used for `qgpt-env-v1` `request_sha256`, QuantGPT `AttemptLedger` `attempt_id` / `row_sha256`, and
     `didm_source_bridge.py` record digests.
4. **Input & Output Hardening**:
   - Rejects UTF-8 BOM, CRLF in published artifacts, duplicate JSON keys, `NaN`/`Infinity`, lone UTF-16 surrogates,
     unknown keys, nesting depth `> 32`, pre-parse container/colon/comma floods, symlinks, `st_nlink != 1`, and any
     path containing `.tradegen` or `.nextgen`.
   - All final files are published atomically without overwrite (`tempfile.mkstemp` + `fsync` + `os.link` + `unlink`).

---

## 2. Pipeline Architecture & CLI Modules (`tools/research/`)

```text
upbit_price_recorder.py ──> bars.jsonl / history.json (+ manifest) ─────────┐
didm_run_log.py + didm_source_bridge.py ──> run_log.jsonl + daily reports ──┼─> direction_feature_builder.py
quantgpt_feature_bridge.py ──> verified feature snapshots / qgpt-env-v1 ────┘            │
                                                                                         ▼
                                                                               direction_model_fit.py (M, B1, B0)
                                                                                         │
                                                                                         ▼
                                                                             direction_forecast_writer.py (+ manifest)
                                                                                         │
                                        ┌────────────────────────────────────────────────┴───────────────────────┐
                                        ▼                                                                        ▼
                          direction_stage1_evaluator.py                                           direction_stage2_replay.py
                         (Criteria 1, 2, 4; S1..S4; B2)                                     (+ upbit_quote_recorder.py; S5..S7)
```

### 2.1 `quantgpt_feature_bridge.py`
- **Surface A (`quantgen-feature-snapshot-v0`)**: Validates `<= 16 MiB`, `<= 50,000` records, 16 core keys (plus
  optional `calibration_version`), rejects `title`/`body`/`prompt`, enforces `as_of <= issued_at <= generated_at`,
  `direction_probs` summing to `1`, `ess_like_0_100` and `uncertainty_entropy` identities, Regime A `snapshot_sha256`,
  non-revision across snapshots by `(model.sha256, producer, record_id)`, and effective
  `known_at = max(issued_at, snapshot_receipt_at)`.
- **Surface B (`qgpt-env-v1`)**: Pure-stdlib verifier and independent re-checker for `tool` vs `owner` mode rules,
  `extract_ok_body`, `T-NEWS` (`1..50` unique `(target_kind, entity_id)` judgments), `T-CARD` `qss-v0` (`draft` only),
  `AttemptLedger` Regime B SHA-256 chain check, `PF-1..PF-6` policy scan, `%`/`bp` number check, citation `as_of`
  check, look-ahead date leakage (`S1_QGPT_LOOKAHEAD_LEAKAGE`), upstream identity pinning
  (`S4_UPSTREAM_IDENTITY_CHANGED`), and batch evaluation scoring (`score_envelopes` with Wilson 95% CIs).

```shell
python -m tools.research.quantgpt_feature_bridge --feature-snapshot snap.json=<sha256>@1764000500 --output merged.json
python -m tools.research.quantgpt_feature_bridge --score-envelopes eval_items.jsonl --output scores.json
python -m tools.research.quantgpt_feature_bridge --verify-ledger attempts.jsonl --pinned-head <sha256>
```

### 2.2 `upbit_price_recorder.py`
- Captures public `/v1/candles/minutes/60` (or `15`) and `/v1/orderbook` only when `--allow-public-network` is passed.
- Records live bars with `known_at = max(end + 1, ceil(received_wall))` (`known_at > end`), exact `Decimal`
  `return_bps`, and close `bid`/`ask`/`spread_bps` (supporting Section 10 Row 6 `hurdle_bps`).
- Backfills missed bars with honest late `known_at` (`S1_UNBACKFILLABLE_BAR` if missing on venue) and coordinates
  transiently per poll via `upbit-public-cooldown.json` (stopping on 429/418 and never deleting an existing hold).

```shell
python -m tools.research.upbit_price_recorder poll --market KRW-BTC --archive-dir /private/prices --coordination-dir /private/coord --allow-public-network
python -m tools.research.upbit_price_recorder export --archive-dir /private/prices --scope upbit-krw-spot --source-id price-v1 --output /private/history.json
```

### 2.3 `didm_run_log.py`
- Wraps 15-minute DIDM collector runs into per-KST-day stores (`kst_YYYYMMDD/didm_store.sqlite`), inspecting both
  stdout status and newly inserted SQLite rows (`seq > pre_max_seq`) because the pinned collector can exit `0` when a
  source fails.
- Tracks 15-minute UTC GDELT slot stamps (`slot_known_at`) and queues missed slots for next-run backfill with honest
  backfill receipt times.
- Coordinates offline SQLite backups + `didm_source_bridge` snapshots with Section 9 superseded-report cleanup, and
  records PC receipt times for `tradegen-didm-exchange-v1` exports and QuantGPT snapshots.

```shell
python -m tools.research.didm_run_log take-snapshot --log-dir /private/logs --database /private/stores/kst_20261124/didm_store.sqlite --as-of 2026-11-24T12:05:00+00:00 --output /private/reports/r1.json
python -m tools.research.didm_run_log record-didm-export --log-dir /private/logs --export /private/export.json
python -m tools.research.didm_run_log record-quantgpt --log-dir /private/logs --snapshot /private/qgpt.json
```

### 2.4 `direction_feature_builder.py`
- Builds point-in-time feature rows at bar closes `as_of` with **zero imputation** (`None` on missing inputs):
  - `P1..P4`: from bars `as_of - m * step` (`m = 1..24`) strictly requiring `bar["known_at"] <= as_of`.
  - DIDM daily report merger & point-in-time re-selection maximizing `(utc(received_at), payload_sha256)` with exact
    `didm_source_bridge.py` parity.
  - `D1`: first-ever receipt or changed `payload_sha256` on pre-registered ALFRED/ECOS series (re-fetching an
    unchanged vintage leaves `D1 == 0.0`; missed scheduled run yields `None`).
  - `D2`: 96-slot / 672-slot GDELT ratio requiring all 96 numerator slots and `>= 95%` (`639/672`) denominator slots
    known in `run_log.jsonl` at `as_of` (a single permanently missed slot makes `D2` missing for 24 hourly bars).
  - `D3`: mean `ess_like_0_100` of pinned-version DIDM V0 scores known in `(as_of - 86400, as_of]` via
    `max(received_at, export_receipt_at)` (`50.0` when delivery succeeded with 0 matching events).
  - `Q1`: categorical `1.0`/`0.0` indicator for pinned QuantGPT risk-news judgments (never reading uncalibrated
    probabilities).

### 2.5 `direction_model_fit.py` & `direction_forecast_writer.py`
- Purges any training row whose `horizon_seconds` outcome window extends past `train_end`, enforces S1 `<= 5%`
  missingness and `D1 >= 8` events, standardizes using training statistics only, fits convex L2-penalized multinomial
  logistic regression (`L-BFGS-B` with analytic gradient) for `M` and `B1` plus empirical prior `B0`, runs the M11-T4
  held-out-week non-overlapping call-count and lag-1 hit-autocorrelation estimator, and seals Regime A
  `tradegen-direction-model-v1` artifacts (`model.sha256`).
- `direction_forecast_writer.py` checks `model.sha256` and S4 definitions, omits missing-feature and rounded-tie bars,
  quantizes `up`/`down` to 6 decimals (`ROUND_HALF_EVEN`) with `neutral = 1 - up - down`, enforces a persistent
  non-revision index on `(model.sha256, market, as_of, horizon_seconds)`, validates via
  `direction_forecast_adapter.check_snapshot`, and writes a sidecar `.manifest.json` carrying `RESEARCH_FLAGS`.

### 2.6 `direction_stage1_evaluator.py`, `upbit_quote_recorder.py`, `direction_stage2_replay.py` & `_native_bridge.py`
- **Stage 1 Evaluator**: Enforces S4 & S1 (`VOID`), `--mode interim` S2 futility (`STOPPED`), Criterion 1 gate with
  bit-identical counting parity against `direction_forecast_adapter.run()`, S3 (`INCONCLUSIVE`), Criterion 2
  non-neutral conditional up-vs-down log-loss with 24-bar KST-day cluster-weighted block bootstrap (`10,000`
  replications, `PCG64`) vs `B1` and point check vs `B0`, Criterion 4 half-window stability, and `B2` moving-block
  report (`like_for_like_with_m=False`).
- **Stage 2 Quote Recorder & 3-Arm Replay**: Captures same-second 10s quotes (`--app-not-running` or external status
  with `BID_GAP_TRIGGERED` stripped), replays `static`, `M`, and `B1` across 128-observation chunks with locked Stage 1
  gate history, non-model Row 17(a)/(b) boundary latch conventions + `lenient_unblocked_seconds`, S5 illegal-widening
  bug trap, S6 ceiling-change truncation, S7 voided-day state carry, and episode-based Criterion 3 trade-off metrics.
  Execution costs and fill records are not measured in Stage 2 (`m11_t5_fill_check_closed=false`).
- **`_native_bridge.py`**: Optional `ctypes` loader for `native/tradegen_fast/build/libtradegen_fast.so`
  (`tg_adaptive_bid_gap_mc`), falling back seamlessly to pure Python when absent or when `TRADEGEN_DISABLE_NATIVE=1`.

---

## 3. Verification

Run the complete synthetic offline test suite (network socket disabled):

```shell
/home/antigravity/xkg4real/tradegen/.venv/bin/python -X utf8 -B -m unittest discover -s tools/research -p "test_*.py"
```

법률, 세무, 투자 조언이 아니며 면허를 가진 자문가가 아니다
