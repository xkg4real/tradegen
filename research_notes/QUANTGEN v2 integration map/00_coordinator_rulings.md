# 00 — Coordinator rulings for the QUANTGEN v2.0 build (binding for every implementer)

As of 2026-10-06. These rulings resolve the layout collisions, contradictions and open readings that the 33 reader briefs
in this folder raised. Where a ruling and a brief differ, the ruling wins; where both are silent, the Council spec v2.0
wins; where the spec is silent, take the conservative reading (no exposure change, specification book only, fail closed).

## 1. What is built, and what is honestly reported as blocked

- Build every module of M0–M10 and the tech-fund BUILD NOW / INVARIANT / GOVERNANCE / FORWARD-SIM items as code, data and
  hermetic tests. Nothing waits for owner inputs: a missing owner input is a typed null that fails closed and is listed
  on the Macro page under "Open owner actions".
- Reference datasets (`/home/claude/quantgen_macro_data`, council CSVs, KRX official closes, marcap, French files) are
  NOT on this machine. Every golden or integration clause that needs them is implemented as a test that raises
  `NotRun("REFDATA: <what is missing>")` (see section 6) and is reported as NOT_RUN — never faked, never counted as PASS.
  The same for OWNER-blocked clauses (`NotRun("OWNER: ...")`).
- The gate package is built and unit-tested on synthetic panels, but **never frozen here**: `gate.package.status` stays
  `NOT_FROZEN`, every macro card stays `NOT_RUN`, the recommended book holds invariants only (vt enters as 1.0 with
  status `not_run`), no forward record starts. The study runner refuses to run a formal card and says why.
- Local vendor data (`docs/asset_expansion/cache/*.csv`, Yahoo total-return closes to 2026-09-25) may feed a labelled
  **dry run** (`run_mode = "backtest"`, value_status `vendor_close`, source `Yahoo`) whose artifacts are written to a
  `dry_run/` sub-directory and displayed with a red "vendor data, not an official close, not a card run" chip. Books
  stay DISARMED in a dry run (acting inputs are not `official_close`). This exists so the pipeline is demonstrably
  wired end to end; it never acts and never writes a verdict.

## 2. Layout rulings (collisions between spec paths and real modules)

| Spec assumption | Reality | Ruling |
|---|---|---|
| `core/calendars/data/*.yaml` | `core/calendars.py` is a module | **Convert to a package**: move `core/calendars.py` to `core/calendars/__init__.py` unchanged (DATA_DIR becomes `parents[2]/"data"/"calendars"`); add `core/calendars/clocks.py`, `publication.py`, `regime.py`, `events.py`, `store.py` and `core/calendars/data/` (spec paths verbatim). Legacy API and engine tests 69–75 unchanged. |
| `core/skills/workflows/macro_daily.yaml` | `core/skills/workflows.py` is a module | Data directory `core/skills/macro_workflows/macro_daily.yaml` (no `__init__.py`); runner `core/skills/pipeline.py` (in-process, headless, injectable clock/paths) + `core/skills/macro_daily.py` (the nine skills and three gates). Never route through `runner.run_skill` or the Flet workflow page. |
| PIT store "inside" `core/ficc/data` | single module, tests patch its privates | Sibling modules `core/ficc/pit.py` (PITValue, MissingInput, RunContext, PITStore, pit_value, pit_last, data_snapshot_id), `core/ficc/contracts.py` (registry loader, contract, expected_available_utc, is_stale, on_input_failure, usable_cross_market, add_publication_bdays), `core/ficc/lag_audit.py`. `core/ficc/data.py` gets only the ingest hook and the cache fix. Registry data: `data/macro/series_registry.yaml`. |
| gate harness in `core/quant/backtest` | that file is the Signals toy | New modules: `core/quant/gate_stats.py` (R-24), `core/quant/gate_ledger.py` (R-23), `core/quant/cardp.py` (R-21, R-22, R-34), `core/quant/gate_package.py` (freeze/acceptance), `core/quant/cards.py` (headers, registry, verdicts.jsonl, archive). `backtest.py` untouched. Reuse `validate.py` primitives; never duplicate `sharpe`, `lo_se`, `deflated_sharpe`, `pbo_cscv`, `newey_west_t`, `kupiec`, `christoffersen`, `pit_tests`, `md5_of`, `ModelCard`. |
| risk functions in `core/quant/risk` | 170-line stats module importing gs_quant | New `core/quant/risk_layer.py` (sma_vol, ewma_vol, market_vol_target, compose, risk_layer, hedge_state, lookthrough_exposure, concentration_bound, drawdown_ladder, display labels) re-exported from `risk.py` by name. `core/quant/refusal.py` for R-11/R-12 (I-03 static check is module-level). |
| estimators in `core/quant/garch` | single module | `core/quant/vol_estimators.py` (seven estimators, registry, SMA20 fallback), `core/quant/forecast_eval.py` (QLIKE, DM, MCS, B5, estimator_gate). |
| sleeves in `core/quant/signals` | per-symbol composite | `core/quant/sleeves.py` (family tags, sleeve_vol_scale, dm_gate, base_weights, inverse_vol_weights, apply_overlays, book builders); `signals.py` gains only the `family` field default `""`. |
| rule objects in `core/rules` | operator order-rule store | New `core/rules/macro_rules.py` (RuleObject section 7.1, validate_rule_object, DO-NOT-BUILD predicates incl. `do_not_build.tf_items`, owner-decision registry, `{ref}` resolver, store loader with config_hash, refusal log) and `core/rules/governance.py` (append_event, verify_chain). Shipped store: `data/macro/rules_v2.0.0.json` (read-only, version 2.0.0). Existing `Rule`, `validate`, `RuleStore`, `rules.json` untouched. |
| artifacts/schemas | none exist | `core/ficc/schemas/*.v2.0.json` (7 files), `core/ficc/macro_schema.py` (stdlib validator: required, type, enum, const, minimum/maximum, exclusiveMinimum/Maximum, pattern, items, properties, additionalProperties/unevaluatedProperties=false, $ref local, allOf/anyOf/oneOf, if/then; canonical_json; header_md5; results_md5), `core/ficc/macro_artifacts.py` (build_macro_state, build_overlay_decisions, writer, provenance, quarantine), `core/ficc/context_log.py` (R-13, R-18). `canonical_json` lives in `macro_schema.py` (pure leaf); `core/rules` imports it from there. |
| per-book runtime in `core/engine` | one global EngineState, manual re-arm | New `core/engine/books.py`: `BookRuntime`, `BookRegistry`, `runtime_halt`, `runtime_rearm`, counters, NAV/weights ledger, persistence in `config.macro_dir()/books/`. `EngineState`, `EngineRuntime`, the manual contract of `OrderBook.fill` and `engine.json` untouched. `orders.py` gains pure `fill_model(venue)`/`simulate_fill(order, session) -> Fill or NonFillable` (R-27 + INV-2). `evaluator.py` gains `Outcome.BLOCKED`, `evaluator_block`, `evaluator_annotate` and an `OUTCOME_STYLE` row. |
| macro cards next to legacy cards | Strategy Lab indexes legacy keys | Macro and tech-fund cards live under `docs/macro_overlay/` (`headers/`, `cards/`, `cards/verdicts.jsonl`, `archive/`); runner `docs/macro_overlay_study.py`. Tech-fund screen-card drafts: `docs/techfund/`. Never write a v2 card into `docs/asset_expansion/cards/`. |
| cost table "in the gate" | lives in `docs/asset_expansion_study.py:60` | Single source `core/quant/validate.COST_BP_PER_SIDE` (KRX ETF 3, KRX stock 35, US via KIS 50, crypto 10, futures 5, FX 10) plus `cost_per_side(instrument_book, ...)` with the R-26 tick floor in `core/quant/cards.py`; `docs/asset_expansion_study.py` imports the constant (same numbers, no behaviour change). |
| tests | six suites, PASS/FAIL only | `tests/macro_acceptance.py` (M0–M6, M8–M10), `tests/macro_gate_acceptance.py` (M7), `tests/techfund_acceptance.py`, registry `tests/macro_registry.csv` (test_id, tier, runs_from, modules, clause), `tests/fixtures/macro/MANIFEST.csv` + fixtures, `tests/reference/`. |

Mutable state never lives in the repo: artifacts, governance_events.jsonl, run_log.jsonl, alerts, book states, family
ledgers (working copies), acceptance_runs.jsonl go under `config.macro_dir()` = `~/.nextgen/macro` (env
`QUANTGEN_MACRO_DIR`). Shipped seeds (ledger seeds, the section 7 store, calendars, series registry, tech-fund CSVs)
live in the repo and are read-only (T-HERM-02 checks their md5 before and after the suite).

## 3. Global rulings

1. **git_hash.** The folder is not a git repository. Every artifact writes `git_hash: "UNVERSIONED"` and `tree_hash`
   (sha256 over the sorted relative paths + bytes of `core/**/*.py`, `data/macro/**`, `config.py`). The M7 freeze and
   `verdict_filter` check (iii) **refuse** on `UNVERSIONED` with the reason "owner must place the repository under git";
   this is listed as an owner action.
2. **No new dependencies.** No `jsonschema`, `arch`, `pyarrow`, notifier packages. Schema validation is the in-repo
   stdlib validator. Parquet is never read.
3. **Composition (binding, section 3.3):** `composed = vt * min(1.0, overlay_1, …, overlay_k, ladder, post_rearm_cap)`;
   `gross = min(composed, concentration_bound)`; HALTED sets the book to 0× and is never a `min()` argument;
   outside HALTED `composed >= 0.5 * vt` is asserted. `compose()` raises `ValueError` if any argument is outside its
   bound (overlays [0.5, 1.0], vt/vs [0, 1.0], ladder and cap in {0.5, 1.0}). No renormalisation anywhere.
4. **Books and ids:** `recommended:<MARKET>`, `specification:<MARKET>`, `forward_sim:<RULE>`, `refusal:<RULE>`,
   `card:<CARD_ID>:<on|off|S>`. Markets are the section 6.1 enum (`KR`, `US`, `JP`, `CN`, `HK`, `TW`, `CRYPTO`, `FX`);
   venue codes (`KRX`, `US`, `TSE`, …) only inside `core/markets` (add `market_to_venue`/`venue_to_market`).
5. **Per-book HALT scope:** only an `acting_exposure` input bound to a book can HALT that book; risk-model inputs set
   `hedge_credit_off = True`; context inputs are labelled stale; exceptions in context writers never HALT (isolation
   guard in `pipeline.py`). RISK re-arm: 0× for decisions t+1..t+10, automatic re-arm at t+10 with references reset
   and `post_rearm_cap = 0.5` inside `min()` for the next 10 decisions; OPS re-arm when the cause clears (no reset,
   no cap); lag-audit and acting-schema failures need an operator re-arm.
6. **"New entry"** (evaluator BLOCKED, ladder `block_new_entries`): for weight books, a decided target weight above the
   held weight of that instrument; decreases and exits are never blocked. For operator rules: BUY-side orders.
7. **Owner decisions D1–D6** are implemented with their Quick-start defaults, held in `owner_decisions` of the store with
   `status: default`, resolved by `{ref}` only (a literal copy that differs is refused at load). Tech-fund open questions
   OQ-01..OQ-15 and the cross-spec amendments XS-01..XS-22 are displayed as **proposals pending owner confirmation**;
   none changes an acting parameter. Where tech-fund and Council differ, Council v2.0 governs the macro package:
   bootstrap blocks `max(21, PW(psi))`; D1 `msci_25_50` (no 0.45 trigger); R-15 priors as stored; `prior_haircuts` as
   section 7; base weights `IV_m × 1/K_m` (the tech-fund `w/3` is a display column only).
8. **Tech-fund cards** (SCR-1, SCR-2 and their FORWARD-SIM cells) are CARD-O cards evaluated by the existing nine-step
   gate with the GOV amendments applied as a *tightening* (block length `max(10, PW(d, d²))`, long-only primary
   statistic against the declared benchmark set, break-even pre-gate screen, attribution block, stress table).
   They need the KRX all-stock panel, so their runs are `NOT_RUN (REFDATA)`; their golden constants are pinned from
   `data/techfund/r3_golden_values.csv` and tested as reference constants, not recomputed.
9. **Existing displays that the tech-fund DNB list names** (Signals composite RSI/MACD/SMA; the macro "regime" read)
   stay, relabelled as CONTEXT: "descriptive read — not a regime model (P19)" and "context only — not a v2 signal
   (DNB-TF-12)". No v2 book reads them (static test).
10. **Hermeticity:** the three new suites patch every network touchpoint at import (`data.net.session`, `_fred_fetch`,
    `_yf_fetch`, KIS/FMP/crypto clients) to raise, use `tempfile` directories for every write, and restore any module
    global they touch (`try/finally`). The known leak `tests/expansion_acceptance.py:273` (`V.GATE["bootstrap_B"] = 300`)
    is fixed by restoring the original in a `finally`.
11. **No `datetime.now()` / `time.time()` in acting code.** Every function takes `decision_utc` and `knowledge_utc`
    (or a `RunContext`) explicitly; clocks and paths are constructor-injected so tests pin them.
12. **Alert sinks:** Macro-page banner backed by a persisted alerts store (`alerts.jsonl`, acknowledgement writes
    `ack_utc`/`ack_by`); OS notification and e-mail are recorded as `sink: unavailable` (no dependency allowed).
13. **Scheduler:** none. `macro_daily` runs from a Macro-page button or `python -m core.skills.macro_daily --market KR`;
    `missed_decisions()` runs once per process at app start (guarded by a module-level flag) and pages MISSED_DECISION.
14. **README and counts:** the README is rewritten at the end (v2 section, test counts from the actual run, stale claims
    fixed: 229/245 → actual, BTC-USD crypto-trend verdict from the manifest).

## 4. Shared names (use these exactly; they are the contract between parallel implementers)

- `core/ficc/pit.py`: `PITValue`, `MissingInput`, `RunContext(decision_utc, knowledge_utc, run_mode)`, `PITStore(path)`
  with `append(rows)`, `pit_value(store, series_id, decision_utc, knowledge_utc, consumer, require_session=None)`,
  `pit_last(store, ...)`, `pit_window(store, series_id, ...) -> list[PITValue]` (batched read for vol windows),
  `data_snapshot_id(store, knowledge_utc)`. Library functions take `store: PITStore` as the first argument; a default
  store is created from `config.macro_dir()` only inside `core/skills/macro_daily.py`, never in library code.
- `core/ficc/contracts.py`: `load_registry(path) -> Registry`, `contract(registry, series_id)`, `expected_available_utc`,
  `is_stale -> StaleCheck`, `on_input_failure(series_id, check, binding)`, `usable_cross_market`, `add_publication_bdays`.
- `core/calendars/clocks.py`: `decision_time_utc(market, session_date)`, `close_print_bound_utc(market, session_date)`,
  `usable_at(series_id, obs_date, market)`, `gap_sessions(market, session_date)`, `is_session(market, d)`, `session(market, d)`.
  `core/calendars/regime.py`: `regime_tags(market, d) -> dict`. `core/calendars/events.py`: event store + windows +
  `event_calendar` artifact builder. `core/calendars/publication.py`: `publication_instant`, `next_expected_obs`,
  `fed_business_day`, `sifma_status`, `nyse_holiday`. `core/calendars/store.py`: signed-file loader (refuses unsigned).
- `core/quant/risk_layer.py`: `VTResult`, `VSResult`, `HedgeState`, `ConcentrationBound`, `LadderState`,
  `market_vol_target(store, market, decision_utc, knowledge_utc, estimator="sma20")`, `compose(vt, overlays, ladder, post_rearm_cap)`,
  `risk_layer(...)`, `hedge_state(...)`, `lookthrough_exposure(...)`, `concentration_bound(...)`, `drawdown_ladder(nav_path, decision_utc, config)`.
- `core/quant/sleeves.py`: `sleeve_vol_scale(...) -> VSResult`, `dm_gate(...) -> Multiplier`, `base_weights(...)`,
  `inverse_vol_weights(...)`, `apply_overlays(composite, multipliers, basis) -> Weights`, `build_recommended_book`, `build_specification_book`.
- `core/engine/books.py`: `BookRuntime` (mode DISARMED/ARMED/HALTED reusing `EngineMode` values; `halt.class`, `reason_code`,
  `causes[]`), `BookRegistry(path, clock)`, `runtime_halt(registry, book_id, cls, reason)`, `runtime_rearm(registry, book_id, mode, operator=None)`,
  `step_decision(registry, book_id, decision_utc, ...)`, `ever_armed(book_id)`, `nav_path(book_id)`.
- `core/rules/macro_rules.py`: `RuleObject`, `load_store(path) -> MacroStore` (with `.get(dotted_key)`, `.resolve_refs()`,
  `.config_hash`), `validate_rule_object(obj) -> Report`, `dnb_violations(obj) -> list[Issue]`, `owner_decision(store, d)`,
  `apply_owner_ruling(...)`. `core/rules/governance.py`: `append_event(path, event) -> str` (row_md5), `verify_chain(path) -> bool`.
- `core/ficc/macro_schema.py`: `load_schema(name)`, `validate(name, obj) -> list[str]` (empty = valid), `canonical_json(obj) -> str`,
  `header_md5(header)`, `results_md5(card)`, `field_class(name, pointer) -> "acting" | "display" | "context"`.
- Verdict and status vocabularies (verbatim): verdicts `PASS | REVISE | REJECT | INSUFFICIENT_DATA`; card run status
  `NOT_RUN`; build statuses `BUILD-AS-INSURANCE | SPECIFICATION_BOOK | FORWARD_SIM | REFUSAL | RETIRED | CONTEXT`;
  input statuses `ok | warmup | disputed | missing | stale | stale_missed_release | provisional_rejected | session_mismatch | synthetic_rejected | fail_closed | not_run`;
  HALT classes `RISK | OPS`; dispositions `INVARIANT_STEP | DESCRIPTIVE | SPEC_BOOK_ONLY`.

## 5. Coding conventions (match the surrounding code)

- Frozen dataclasses for results; positional construction order preserved when a field is added (append with default).
- Atomic file writes (`mkstemp` + `os.replace`), `encoding="utf-8"`, LF newlines for JSONL; append-only logs are opened
  in binary append mode and **raise** on failure (do not swallow).
- Decimals in the core, percent/bp only in the UI. Dates are `datetime.date`; instants are tz-aware UTC `datetime`.
- Module docstrings state the rule ids implemented. Comments are sparse and name the spec line for a non-obvious bound.
- Every new UI file passes `tests/flet_api_guard.py` (flat `ui/*.py`, `pal.<token>` only, listed control kwargs).
- The UI never computes exposure: it renders validated artifacts and fails closed with `notice(..., "error")`.

## 6. Test conventions

- A test is a zero-argument callable named `test_*`; new suites expose `tests()` and are registered in `tests/run_all.py`
  (one import, one line). `run_all.py` gains a third status: a test that raises `tests.notrun.NotRun(reason)` is recorded
  as `NOT_RUN` with its reason, counted separately, and never affects the exit code. The summary prints
  `passed/failed/not_run`. The registry CSV lists every T-*, I-*, G-* id with tier (`fast | golden | freeze`),
  `runs_from`, and its clause deferrals (section 9.0b); `tests/run_all.py --milestone M3` runs the exit set of a milestone.
- Golden and integration tests that need absent data call `require_fixture("<file>")`, which raises
  `NotRun("REFDATA: <file> not in tests/fixtures/macro/MANIFEST.csv")`.
- Fixtures are md5-listed in `MANIFEST.csv` (file, source, series, span, retrieved_at_utc, value_status rule, md5,
  licence, owner, tests). Synthetic fixtures are generated deterministically (seed 11) and listed too.

## 7. UI rulings (details in `02_ui_design.md`)

- `ui/macro_page.py` gains a "Macro overlay v2" region (its own Refresh): per-market state tiles, the composition line,
  per-book runtime chips with HALT banners, alerts with Acknowledge, open owner actions and decisions, the context log
  table, the event calendar; a Cards tab (macro model cards with verdict/disposition/build-status chips, refusal and
  FORWARD-SIM books), and a Research tab (tech-fund weight table, go/no-go register, DO-NOT-BUILD, backlog, council
  resolutions) with buttons that open the two offline HTML pages via `os.startfile`.
- Tokens: add `warning` (`#d9a441` dark / `#8a5a00` light) to `core/theme.py` (append to the frozen dataclass with a
  default so positional constructors keep working) and a module-level `VERDICT_STYLE` map in `ui/components.py`.

## 8. Amendments after Sprints 1-2 (the sprint logs are the authority for exact signatures)

- `runtime_halt(registry, book_id, cls, reason, decision_utc, component=None, series_id=None)` and
  `runtime_rearm(registry, book_id, mode, decision_utc, operator=None, cleared=None)`; `ever_armed(registry, book_id)`.
- The five calendar methods the data layer consumes live in `core/calendars/adapter.py` (`CalendarClocks`); `clocks.py` is a leaf.
- `MissingInput` has a fifth field `detail` (default ""). `pit_window(..., statuses=pit.CLOSE_STATUSES)` for vol windows; derived
  acting values go through `pit.put_derived`.
- `validate_card_header(header, store, *, rule, ...)` returns a `Report`; the tick floor and `cost_per_side` live in
  `core/quant/instruments.py` (M7 may re-export from `cards.py`).
- `tree_hash` is an optional property of the five artifact schemas and the third volatile field.
- After adding a test with `test_ids`, run `python -m tests.macro_acceptance` (registry sync); after touching a fixture,
  `python -m tests.notrun` (manifest md5 refresh). Run one suite at a time on the host (T-HERM-02 snapshots `~/.nextgen`).
- The Bash tool fails on heredocs containing an apostrophe: use the Write tool for prose files; console is cp949, so run
  python with `PYTHONIOENCODING=utf-8`.
