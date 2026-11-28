# TRADEGEN Continuous Model Factory (`qlib_lab`, research only)

Status: implemented in `qlib_lab/` (isolated research package). Zero module in the D14 signed execution closure (`core/compliance/owner.py:code_files`) imports `qlib_lab/`.

Every artifact, recorder `meta.json`, model card, `FrozenModelSpec`, promotion dossier, revision proposal, and snapshot sidecar manifest written by `qlib_lab` embeds:

```json
{
  "research_only": true,
  "live_eligible": false,
  "execution_ready": false,
  "source_authenticated": false,
  "owner_approval_verified": false
}
```

A forecast, score, model card, or promotion candidate produced by `qlib_lab` never places an order, never alters a signed ceiling or loss limit, and never clears an alert, entry block, daily stop, or floor halt.

---

## 1. Design Principles & Isolation Guarantees

`qlib_lab` adapts Microsoft Qlib's five core abstractions—formulaic expression engine, `DataHandlerLP` / `DatasetH` dual-pipeline data layer, `Model` / `ModelFT` zoo (`HistGBDT`, `DoubleEnsemble`, drift adapters), `Experiment` / `Recorder` (`R`) workflow, and `RollingGen` / `OnlineManager` continuous lifecycle—to TRADEGEN's fail-closed bitemporal governance rules:

1. **Zero `pickle` / `dill` / `marshal` / `eval` / `exec`**:
   - Component instantiation uses `qlib_lab.registry.COMPONENT_REGISTRY` (`init_instance_by_config`) with no dynamic `importlib.import_module`.
   - Formulaic expressions parse via `ast.parse(..., mode="eval")` against a strict AST node and operator whitelist (`OPERATOR_WHITELIST`), blocking attribute access, subscripts, lambdas, comprehensions, and `__` tokens.
   - Frozen models serialize as canonical ASCII JSON (`tradegen-qlib-frozen-model-v1`) verified by `model_sha256`; arrays and panels serialize via `np.savez_compressed` + `.schema.json` sidecars read exclusively with `np.load(..., allow_pickle=False)`.
2. **Bitemporal Point-in-Time & Anti-Leakage Discipline**:
   - **Static Future-Shift Ban**: `Ref($close, -1)` or any expression with `max_forward_bars() > 0` raises `LookAheadSyntaxError` at parse time unless inside `with LabelContext():`.
   - **Causal Bar & PIT Visibility**: Bar fields enforce `known_at <= as_of` (supporting both fail-closed `CausalLagViolationError` and point-in-time `NaN` masking of late-backfilled bars). Irregular `$$series` collapse via `known_at = max(available_at / received_at, retrieved_at / receipt_at) <= as_of`, never using `obs_date` or `release_date` as `known_at`.
   - **Purged & Embargoed Splits**: `StatefulProcessor` subclasses require explicit `[fit_start_time, fit_end_time]` with `fit_end_time <= train_end` (`FitLeakageError`). `DatasetH` purges any training/validation row whose `meta.label_end_utc > boundary`, enforces `embargo_bars` between splits, and blocks `prepare("test", data_key=DK_L)` outside `authorized_eval_context` (`TestLabelLeakageError`).
3. **Filesystem & State Isolation**:
   - Every writer validates paths through `core.isolation.checked_target` (`~/.nextgen` refused, symlinks/junctions/hardlinks refused). Library APIs require explicit `uri` / `state_dir` paths and never default to `~/.tradegen`.
   - Zero network calls and zero wall-clock calls outside `qlib_lab/cli.py:main()`.
4. **Trial Multiplicity Honesty**:
   - Every evaluated configuration registers in `core.quant.gate_ledger.FamilyLedger` (`ledger_bridge.py`) and deflates Sharpe / selection checks using cumulative $N_{\text{eff}} = \max(N_{\text{clusters}}, N_{\text{equiv}})$. Passes `core.quant.gate_ledger.scan_forbidden` with zero hits.

---

## 2. Package Architecture

| Module | Responsibility |
| --- | --- |
| `qlib_lab/_accel/` | C++17 native kernel library (`kernels.cpp`, `-O3 -fno-fast-math -shared -fPIC`) compiled by `build_accel.py` into `qlib_lab/_accel/build/libqlib_accel.so` with SHA-256 source/binary verification before `ctypes.CDLL` and automatic bit-consistent NumPy fallback (`numpy_fallback.py`, toggleable via `QLIB_LAB_DISABLE_ACCEL=1`). Includes O(T) two-stack Pébay-Welford rolling `Mean`/`Sum`/`Std`/`Var`/`Skew`/`Kurt`, monotonic-deque `Max`/`Min`, causal `EMA`, Wilder `RSI`/`ATR`, bivariate `Cov`/`Corr`, OLS `Slope`/`Rsquare`/`Resi`, and 256-entry `uint8` `HistGBDT` histogram build, parent-minus-smaller-child subtraction, and NaN-routing split scan. |
| `qlib_lab/expression/` | Safe whitelist DSL parser (`parser.py`), CSE-deduplicated topological `ExpressionDAG` (`ast_nodes.py`), 39 causal time-series and cross-sectional operators (`ops.py`), and bitemporal `PIT` operators (`pit_ops.py`: `PIT`, `PRef`, `PITYoY`, `PITMoM`, `PITNewEventFlag` [D1], `PITSlotRatio` [D2], `PITPinnedScoreMean` [D3/Q1]). |
| `qlib_lab/data/` | `StaticDataLoader` & `ExpressionDataLoader` (`loader.py`), `PurgedHorizonReturnLabel` (`labels.py`) aligned with `tools/research/direction_forecast_adapter.py`, leak-free `StatefulProcessor` & `FailClosedDropnaProcessor` chains (`processors.py`), `DataHandlerLP` (`DK_R`, `DK_I`, `DK_L` + JSON processor state export, `handler.py`), and `DatasetH` / `TSDatasetH` (`dataset.py`). |
| `qlib_lab/models/` | `FrozenModelSpec` (`tradegen-qlib-frozen-model-v1`, `base.py`), `RidgeLinearModel` (L2/Huber + `finetune`, `linear.py`), `MultinomialDirectionModel` (convex L-BFGS-B + sparse event floor + `valid` temperature scaling + `finetune`), `PriorFrequencyBaselineModel` (B0), `MovingBlockBootstrapModel` (B2, `direction.py`), `HistGBDTModel` (255-bin + bin 255 NaN routing, regression & 3-class multiclass, `gbdt.py`), `DoubleEnsembleModel` (ICDM 2020 `SR` + `FS`, `double_ensemble.py`), `RegimeKernelReweighter`, and causal `OnlineHedgeCombiner` (`drift_adapter.py`). |
| `qlib_lab/workflow/` | Zero-pickle `FileGovernanceRecorder` & `R` context manager (`recorder.py`), `FamilyLedger` multiplicity bridge (`ledger_bridge.py`), and `SignalRecord`, `DirectionGateRecord`, `PortfolioGateRecord` (`records.py`). |
| `qlib_lab/online/` | `RollingGen` & `RollingTrainer` (`rolling.py`, rebinding processor fit windows per rolling step and stamping disjoint `[active_from, active_until)` OOS intervals), `DriftMonitor` & bounded `RevisionProposer` (`drift.py`), `OnlineManager` Champion vs Shadow Challenger routine (`manager.py`), and `SnapshotExporter` (`exporter.py`) producing self-verified `tradegen-direction-forecast-v1` snapshots + `.manifest.json` + `.interface_note.md`. |
| `qlib_lab/cli.py` | Offline CLI entrypoints: `qrun`, `rolling`, `routine`, `propose-revision`, `export-snapshot`, and `replay-br26`. |

---

## 3. Building Native Kernels & Running CLI Workflows

Compile the C++17 native kernel shared library and record its SHA-256 manifest. The loader also requires independent source and binary pins (Linux x86-64, Debian g++ 14.2.0-19). It maps the verified bytes from a sealed file descriptor. Other toolchain outputs and hosts use the NumPy backend.

```shell
.venv/bin/python -X utf8 -B -m qlib_lab._accel.build_accel
```

Run the full hermetic `qlib_lab` acceptance suite:

```shell
.venv/bin/python -X utf8 -B -m tests.qlib_lab_acceptance
```

Export a verified `tradegen-direction-forecast-v1` snapshot and replay it offline through TRADEGEN's BR-26 adapter (`tools/research/direction_forecast_adapter.py`):

```shell
.venv/bin/python -X utf8 -B -m qlib_lab.cli export-snapshot \
  --frozen-model /path/to/private/model.json \
  --config /path/to/private/task.yaml \
  --panel /path/to/private/bars.json \
  --output /path/to/private/forecasts-001.json

.venv/bin/python -X utf8 -B -m qlib_lab.cli replay-br26 \
  --replay /path/to/private/study.json \
  --snapshot /path/to/private/forecasts-001.json=<snapshot_sha256>
```

---

법률, 세무, 투자 조언이 아니며 면허를 가진 자문가가 아니다
