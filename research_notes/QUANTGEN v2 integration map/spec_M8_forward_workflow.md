# spec_M8_forward_workflow — M8: `macro_daily` workflow, forward records, FORWARD-SIM and refusal books

Source: `QUANTGEN_Quant_Council_2026-10-03/claude_code/QUANTGEN_MACRO_INTEGRATION.md` ("L" = line number). Read in full: L1173-1254 (§3.8, §3.9), L1639-1666 (R-11, R-12), L2647-2762 (R-25), L2964-3154 (R-28, R-29), L3479-3500 (R-35), L5303-5366 (§8.8), L5489-5706 (§9.0-§9.2). Cited from elsewhere: L103-178 (review changelogs), L803-898 (§3.2, §3.3), L961-1113 (§3.5), L1493 (R-01 rule 7), L1813-1969 (R-19), L2348 and L2372-2378 (R-22), L3361-3372 (R-32), L3514-3798 (§6.1, §6.2), L4037-4065 (§6.5), L4094-4119 (§6.6), L4195-4280, L4330-4363, L4408-4497, L4662-4684 (§7), L4781-4838 (§8.1.2-3), L4855-4872 (§8.3), L5381-5439 (§8.9), L5441-5487 (§8.10), L5734-5737, L5776-5795, L5815-5840, L5871-5891, L5958-5966, L5982-5992 (§9.3), L5994-6035 (§9.4, §9.5), L6162-6252 (§10), L6298-6337 (§11), L6370 (§12 M8). Tech-fund: `QUANTGEN_techfund_research_bundle/QUANTGEN_techfund_research/research_notes/R3_TF_neural_link.md` ("R3 L"). Task file: `prep/tasks/M8.json` (TASK-M8-01 … -13). Repo checked 2026-10-05.

Precedence (L89): field names, parameters, bounds, formulas, thresholds, status strings are BINDING; paths and function names marked "proposed" may be renamed. Silent spec ⇒ **no exposure change, specification book only, fail closed**. File names below follow the sibling briefs (`spec_constitution.md`, `code_skills_workflows.md` D.2-D.4, `code_rules_engine.md` D.3-D.4). E = exists, N = new.

State of the world that bounds this milestone: every macro card is NOT_RUN (L5417), D5 = none/pending (L4148), `sleeves.US.notional_nav: null` and `sleeves.KR.notional_nav: null` (L4463-4464), the repo is not a git repository, and the reference datasets are absent. Consequence: `verdict_filter` admits nothing, the recommended book carries invariants only, R-28/R-29 cannot commit headers (so no forward record starts), R-25 has zero active cards. M8 code must be correct in exactly that state and in the synthetic states its tests inject.

---

## A. Scope

| Task | One-line deliverable | Target files |
|---|---|---|
| TASK-M8-01 | In-process `macro_daily` pipeline: 12 ordered entries (9 skills, 3 gates), start bound `close_print_bound_utc + 10 min`, one artifact per decision, gates by role and book, `bounds_ok` field classes | N `core/skills/pipeline.py` (generic runner, run log, missed decisions); N `core/skills/macro_daily.py` (step + gate registry, thin wrappers over M1-M7 functions); N `core/skills/macro_workflows/macro_daily.yaml` (data-only dir; path per `spec_constitution` F-3); E `config.py` (`macro_artifact_dir()` from M0) |
| TASK-M8-02 | `verdict_filter`: admission rule, verdict integrity (i)-(iii), admission-derived bindings with governance events | N `core/skills/macro_daily.py::admissions`, `::verdict_filter`; reads `cards/verdicts.jsonl` (M7 appender), `gate.package` (M7), `core/rules/governance.py` (M0) |
| TASK-M8-03 | Book-separation assertion (I-03) in the book builder, extended to FORWARD-SIM and refusal books | E `core/quant/signals.py` (book builder from M4) + N `assert_book_separation`; `core/rules/macro_rules.py` shape 22 (M0) |
| TASK-M8-04 | End-to-end HALT-scope verification (T-SCOPE-01 a-h, T-ROLE-02 M8 clause); fix any cross-book HALT | E `core/engine/runtime.py`, `core/engine/state.py` (per-book runtime from M1/M5); tests only unless a defect is found |
| TASK-M8-05 | `macro.engine_feed`: all-or-none per book; blocked for the run after an acting-step error | N `core/skills/macro_daily.py::engine_feed`; E `core/engine/orders.py` (per-book weight book from TASK-M5-12) |
| TASK-M8-06 | `run_log.jsonl`, `macro.missed_decisions`, alert store + sinks, governance-chain check at app start | N `core/skills/pipeline.py` (`append_run_record`, `missed_decisions`); N `core/skills/alerts.py` (persisted alert store; skip if M1 already ships one — reuse it); E `main.py` (start-up hook, once per process); E `ui/` Macro page (banner + Acknowledge) |
| TASK-M8-07 | Deterministic replay of a past decision (audit only) | N `core/skills/pipeline.py::replay_decision`; M0 canonicaliser; E `core/engine/state.py` (runtime restore) |
| TASK-M8-08 | R-25 forward records, calibrated alarms, CUSUM, budget panel, operational triggers, demotion, lockout | N `core/quant/forward.py` (`calibrate_alarms`, `cusum_monitor`, `false_demotion_rate`, `demote`, `forward_monitor`; spec says `core/quant/backtest`, proposed L2658); E `core/engine/state.py` (forward-record, alarm, CUSUM, switch state) |
| TASK-M8-09 | R-28 trend-axis FORWARD-SIM book `forward_sim:R-28` | E `core/quant/signals.py::trend_axis` (N function); card block `cards.R-28_trend_axis` (rules JSON, M0); `core/quant/forward.py` |
| TASK-M8-10 | R-29 `MACRO-R06-US-FUT` FORWARD-SIM book `forward_sim:R-29`, integer contracts, settling-run logic, promotion guard | E `core/quant/risk.py::market_vol_target` (US futures instance, M2) + N `micro_es_contracts`; N `core/quant/forward.py::settling_run`, `::promotion_ok` |
| TASK-M8-11 | Acquire French daily Mkt-RF/RF 1926-07 → 2026-08, md5-freeze, run the settling run | N `tests/fixtures/macro/` + `MANIFEST.csv` — **OWNER/REFDATA; not doable in this run** (HTTP 403, L3080; no web) |
| TASK-M8-12 | R-11 (S1) display-only refusal book `refusal:R-11` | E `core/quant/risk.py::refusal_krw_leg` (N function); `refusal_books.S1_krw` (rules JSON) |
| TASK-M8-13 | R-12 (S2) display-only refusal book `refusal:R-12` | E `core/quant/risk.py::refusal_rates_leg` (N function); `refusal_books.S2_rates` |
| tests | group `macro/` | N `tests/macro_acceptance.py` (one file for all milestones, per `spec_constitution`), registered in E `tests/run_all.py` |

Do not route `macro_daily` through `core/skills/runner.run_skill` or `ui/workflows_page._pipeline` (subprocess + Flet closure; `code_skills_workflows` D.2). Do not touch `EngineState`/`EngineRuntime` operator-engine semantics (manual re-arm, `engine.json`).

---

## B. Build spec

### B.0 Pipeline definition (verbatim, L1191-1245)

```yaml
name: macro_daily
runs: [after_close: KRX, after_close: NYSE]
run_mode: live                 # live | backtest | replay (L1196, L4198)
steps:
  - skill: macro.pit_snapshot
  - gate: data_ok
  - skill: macro.lag_audit
  - skill: macro.vol_and_overlays
  - skill: macro.build_artifacts
  - gate: bounds_ok
  - gate: verdict_filter
  - skill: macro.engine_feed
  - skill: macro.forward_books
  - skill: macro.forward_monitor
  - skill: macro.brief
  - skill: macro.run_record
```
- `decision_utc = close_print_bound_utc(market, session_date)` (R-20). Run starts **no earlier than `close_print_bound_utc + 10 min`** (06:40:30Z for KRX today; US 20:10:30Z EDT / 21:10:30Z EST) (L1194-1195). Boundary: 06:40:29Z refused, 06:40:30Z allowed (`>=`; same anchor as T-CLOSE-01's quarantine boundary, L5617).
- "Acting steps" = `pit_snapshot` **through** `verdict_filter` (L1240-1241) = entries 1-7.
- "skill" here = in-process Python function; "gate" = automatic check (not the existing human `decision_gate`). Unknown YAML key or unregistered step name ⇒ raise at load.
- Credentials env-only; the Claude API, when a key is set, "receives the computed numbers only and never decides" (L1253); called without tools, its text never parsed by an acting module (T-RO-02, L5606).

### B.1 `core/skills/pipeline.py` (N)

```python
@dataclass(frozen=True) class PipelineStep: kind: str; name: str         # kind in {"skill","gate"}
@dataclass(frozen=True) class Pipeline: name: str; runs: tuple[str, ...]; run_mode: str; steps: tuple[PipelineStep, ...]; source: Path
@dataclass class RunContext: market: str; session_date: date; decision_utc: datetime; knowledge_utc: datetime | None
                             run_mode: str; run_id: str; acting_error: bool; step_results: list[dict]; ...
class TooEarly(Exception)                       # start bound not reached; nothing is written
ACTING_STEPS = ("macro.pit_snapshot","data_ok","macro.lag_audit","macro.vol_and_overlays","macro.build_artifacts","bounds_ok","verdict_filter")

def load_pipeline(path: Path) -> Pipeline                          # yaml.safe_load, utf-8; fail closed on unknown key/name
def earliest_start_utc(market: str, session_date: date) -> datetime  # close_print_bound_utc + timedelta(minutes=10)
def run_pipeline(p: Pipeline, *, market: str, session_date: date, clock: Callable[[], datetime],
                 steps: Mapping[str, Callable[[RunContext], dict]], run_mode: str | None = None) -> dict   # returns the run record; never raises past run_record
def append_run_record(record: dict, path: Path) -> None            # one canonical JSON line, binary append, "\n"
def read_run_log(path: Path) -> list[dict]
def missed_decisions(expected: Iterable[tuple[str, date, datetime]], rows: Iterable[dict]) -> list[dict]   # pure
def replay_decision(market: str, session_date: date, *, artifact_dir: Path) -> dict   # B.5
```

`run_pipeline` algorithm:
1. `decision_utc = close_print_bound_utc(market, session_date)`; `NotASession` propagates. If `clock() < earliest_start_utc(...)` ⇒ `raise TooEarly` (T-CLOSE-01 M8 clause).
2. **One artifact per decision** (L1199-1200): if `run_log.jsonl` already holds a `live` row for `(market, session_date)`, force `run_mode = "replay"` (audit only: no `engine_feed`, no forward-record append). See F-12 for an earlier errored row.
3. Execute entries in order, each inside `try/except Exception`. A raising step records `{status: "error", error: "<Type>: <msg>"}` and the loop continues under these rules (L1239-1245):
   - error in an acting step ⇒ `ctx.acting_error = True`; raise alert `RUN_ERROR` (severity `page`); remaining acting compute steps are skipped **except** `macro.build_artifacts`, which writes a `fail_closed` artifact; `macro.engine_feed` is recorded `blocked` and not executed (books carry their weights); every book the step serves gets `book_counter += 1`; at `book_counter_halt_after: 2` ⇒ `runtime_halt(book, "OPS", "run_error")` (L1243, L4358 `acting_step_error_beyond_limit`). "Books the step serves" = `recommended:<market>` and `specification:<market>` (F-9).
   - error in `macro.forward_monitor` ⇒ the decision is queued; at the next successful run the monitor is re-run for **each** skipped decision (L1244-1245, T-OBS-04). Needs a per-(card, decision) `monitor_done` marker in the forward state.
   - error in `engine_feed`, `forward_books`, `brief` ⇒ recorded, `RUN_ERROR` page; no counter (not acting steps).
4. A gate that *fails* is not an exception: it sets per-book outcomes (fail-closed component, HALT, quarantine) and the run continues; `build_artifacts` is "always written, also when a gate failed" (L1221).
5. `macro.run_record` is the runner's `finally` epilogue (listed in YAML for fidelity): builds and appends the row even when a step raised (`status = error`).
6. `late = generated_at_utc > open of that market's next session` (L5311). A late run: forward books carry the previous weights for that session, the late artifact is display-only; `engine_feed` is not called (F-13).

Timestamps `…Z` (L3507); `run_id` format reusable from `runner.py:189-190` (`%Y%m%d-%H%M%S-macro_daily-<6 hex>`).

### B.2 Steps and gates — `core/skills/macro_daily.py` (N)

Each is `fn(ctx: RunContext) -> dict` (the step result); all data access via `pit_value(series_id, ctx.decision_utc, ctx.knowledge_utc, consumer, require_session)`; never "now" (L1105).

**(1) `macro.pit_snapshot`** (L1198-1201; `core/ficc/data`, M1). Retry missing inputs per `data.ingest` until they arrive or the deadline passes, then pin `knowledge_utc` for the run; return `pit_value` for every registry binding at `decision_utc` with `value_status` and `session_date` checks.
- Config (L4201-4203): `data.ingest: {trigger: [pit_snapshot, publication_schedule], retries_min: [1, 5, 15, 60], decision_deadline: next_session_open_minus_30min, dedupe_key: [series_id, obs_date, vintage, source, value, value_status], first_seen_is_retrieved_at: true, fetch_log: fetch_log.jsonl, rows_mutated: never, posting_time_pollers: {TREASURY_PAR: "17:30-21:00 ET every 5 min", FRED_REPOSTS: last_updated}}`; `data.knowledge_utc: {pinned_once_per_run: true, defaults_to_now: false, written_to_every_artifact: true}` (L4197).
- `knowledge_utc` in `live` = the end of the `pit_snapshot` fetches (L1002); `replay` = the artifact's `knowledge_utc`.
- Never block the UI thread: one attempt per invocation; the scheduler re-invokes on the `retries_min` ladder until the deadline (F-14).

**(2) gate `data_ok`** (L1202-1209, L3482-3486; R-19 rule 4 L1866-1882). Per binding `(series, consumer, role, books)`; failure = `MissingInput.reason ∈ {missing, stale, provisional_intraday, session_mismatch, synthetic_rejected}`, `Stale("missing"|"missed_release")`, or a contract violation (out of range, schema error, non-monotone date, provisional row for a close-type input). Status map to `macro_state.inputs[].status`: missing / stale_missed_release / provisional_rejected / session_mismatch / synthetic_rejected (L1108).

| role | action (verbatim keys L4230-4241) |
|---|---|
| `acting_exposure` | `{action: fail_closed, alert: true, halt_after_consecutive_decisions: 2, scope: bound_books, book_counter_halt_after: 2}`: component `fail_closed = true`, previous state carried, alert; for **each bound book**: input counter +1 (reset at its next fresh decision) and book counter +1 if the input has the default limit (reset at a decision where all default-limit acting inputs bound to the book are fresh); HALT (class `OPS`, `reason_code: "acting_input_stale:<series_id>"`, L1951) when an input counter reaches its binding's limit (default 2; `KODEX200_PDF` 5; `NAV_LINE_CLOSES` 3) **or** the book counter reaches 2 (two inputs failing on alternate decisions still HALT). Books the input is not bound to are untouched. |
| `forward_sim` | `{action: fail_closed_that_book, alert: true, halt: never}`: that FORWARD-SIM book fails closed (its multiplier is carried); never HALTs any book. |
| `risk_model` | `{action: conservative_default, set: {hedge_credit_off: true}, hedge_failure_from: USD_LIVE_PROXY, operator_alert_after_missed_releases: 2, halt: never, also_on: hedge_state_exception}`; **the gate PASSES**. |
| `risk_model_covariance` | `{action: carry_last_valid_terms_stale_then_drop, carry_max_decisions: 5, alert: true, halt: never, sets_hedge_credit_off: false}` |
| `context` | `{action: label_stale}`; **the gate PASSES**. |
| `history` | `{action: refuse_card_if_span_not_covered, alert: true, read_by_weight_decisions: false}` |
| not failures | `[warmup_before_first_armed_decision, disputed]` — no counter. |

Unreadable publication calendar ⇒ every acting input fails closed and every risk-model default is set; never a fallback to observation-age staleness (L1956). Bound-book lists are the **derived** lists of B.2(7) (bindings follow admission).

**(3) `macro.lag_audit`** (L1210-1217; function from M1, wired here). Independent of `pit_value`: for every acting and risk-model input (context is skipped, L3703) recompute `usable_at(series, obs_date, market)` from `core/calendars` + the registry and require: `usable_at <= decision_utc`; `available_at_utc >= publication_instant(series, obs_date)` (closes: ≥ the scheduled close; a derived input: each input of its lineage); `retrieved_at_utc <= knowledge_utc`; the R-01 status and session checks.
- acting violation ⇒ `runtime_halt(book, "OPS", "lag_audit_violation")` for the books it feeds, `rearm_mode: operator` (L4360); a provisional row reaching an acting input counts as a violation (L1497).
- risk-model violation ⇒ `hedge_credit_off` + alert, never HALT (covariance-only binding: carried, then dropped).
- record ⇒ `macro_state.lag_audit = {checked: int, violations: [{series_id, obs_date, check, expected_usable_at_utc, stamped_available_at_utc}]}` (L3541-3547).
- any violation touching a card's forward record ⇒ R-25 operational trigger (B.6).

**(4) `macro.vol_and_overlays`** (L1218-1219): calls M2/M4/M5 functions — `market_vol_target`, `sleeve_vol_scale`, `base_weights`, `hedge_state`, `concentration_bound`, `drawdown_ladder`, `compose(vt, overlays, ladder, post_rearm_cap)`; composition by `min()`. An exception in `market_vol_target`, `concentration_bound`, `drawdown_ladder`, `compose` ⇒ OPS HALT of the books it feeds; an exception in `hedge_state` ⇒ `hedge_credit_off = TRUE`, alert, never HALT (L1178, T-MISS-02). These are caught *inside* the step (they are risk-layer outcomes, not step errors).

**(5) `macro.build_artifacts`** (L1220-1221): `build_macro_state`, `build_overlay_decisions` (verdict and disposition per factor), `build_context_log`, event windows and gap tags, R-08 annotation (M6 builders). Always written, also when a gate failed; after an acting-step error it writes a `fail_closed` artifact (`macro_state.fail_closed = true`, weights carried).

**(6) gate `bounds_ok`** (L1222-1227; R-32 L3370). Validates each built artifact:
1. schema 2.0 (draft 2020-12, one registry keyed by `$id`, closed objects; M0 validator);
2. P2 bounds: every overlay multiplier ∈ [0.5, 1.0]; `vt`, `vs` ∈ [0, 1.0];
3. exposure basis present and valid on every multiplier;
4. `min()` composition **recomputed from the recorded factors**: `composed = vt × min(1.0, overlays…, ladder, post_rearm_cap)` must equal the recorded value, and `composed ≥ 0.5 × vt` outside HALTED (floor on `composed`, never on `gross`; L881);
5. in code (because `extras` is never schema-validated): `extras.w_target`, `extras.w_held` ∈ [0, 1].

Field classes (exhaustive; L3370). **Display**: in `macro_state` — `owner_decisions`, `alerts`, `annotations`, `refusal_books`, `forward_sim`, the flags `gap_sessions`, `kr_open_gap_event`, `var_display_scale`, `hedge_credit_off`, `hedge_failure`, `classic_risk_off`, `fx_hedge_credit`, `hedge_reasons`, `hedge_stale_inputs`; in `macro_state.vol` — `display_label_rel`, `display_label_abs`, `label_method_rel`, `label_method_abs`, `alt_sigma_logged`; in `overlay_decision` — `reasons`, `refusal`, `forward_sim`; in both — `inputs` entries whose role is not `acting_exposure`. **Everything else is acting** ("A property added later is acting until it is classified here").

| Failure | Outcome |
|---|---|
| acting field of `macro_state` / `overlay_decision` | HALT (OPS, `acting_field_schema_or_bounds_failure`, operator re-arm) of the books the artifact describes; artifact written to `<artifact_dir>/quarantine/` with its errors |
| display or context field only | artifact written with `extras.validation_errors`, alert; never a HALT |
| `context_log` / `event_calendar` (/ `model_card`) | refused (not written to the artifact dir), written to `<artifact_dir>/quarantine/` with its errors, alert; never a HALT |

**(7) gate `verdict_filter`** (L1228-1230, L3487-3489; TASK-M8-02).

```python
def admissions(cards: Mapping[str, CardRecord], verdict_rows: list[dict], package: dict, *,
               snapshot_id_at: Callable[[datetime], str], harness_hashes_at: Callable[[str], dict | None],
               lockouts: Callable[[str, str, datetime], bool], decision_utc: datetime) -> AdmissionResult
# AdmissionResult{admitted: dict[book_id, tuple[rule_id, ...]], refused: dict[rule_id, reason], integrity_failures: tuple[rule_id, ...], chain_ok: bool}
```
Admission predicate for the recommended book:
```
admit(f) :=  ( card.verdict == "PASS"
               and card.build_status_on_pass in {"BUILD_NOW", "BUILD_AS_INSURANCE"}      # dispositions RECOMMENDATION / BUILD_AS_INSURANCE
               and authenticated(card) and not locked_out(card.family, card.market) )
          or ( f is an R-31 step and disposition == "INVARIANT_STEP" )                     # binding share <= 0.10, frozen with the R-31 header
```
Refused (stay in the specification book): everything else, explicitly a card whose `build_status_on_pass` is `BUILD_AS_INSURANCE` while its verdict is `NOT_RUN` or `INSUFFICIENT_DATA` (R-06 KR today); dispositions `SPECIFICATION_ONLY`, `FORWARD_SIM`, `REFUSAL_BOOK`, `DESCRIPTIVE`; R-04 always.

`authenticated(card)` — **all** of (L3487):
- (i) the card file re-hashes to the committed `results_md5` **and** the `cards/verdicts.jsonl` chain verifies (each row's `prev_row_md5` = md5 of the previous line). A broken chain blocks **every** admission until restored (T-CARD-03).
- (ii) `card.gate_package_md5 == gate.package.definitions_md5` (the frozen package).
- (iii) the snapshot is reproducible: `data_snapshot_id` recomputed from the store at the card's `knowledge_utc` matches (archived rows, §9.4 item 16, L6013); **and** `card.git_hash` is a commit whose harness sources hash to the package manifest's entries.

Failure of any ⇒ factor stays in the specification book; governance event `kind: "verdict_integrity"`; alert `VERDICT_INTEGRITY` (severity `page`).

Bindings follow admission (L1889): for each admitted factor, every acting input bound to `specification:<m>` is also bound to `recommended:<m>` for this decision (R-03 → `MOM_PAPER_LS_SERIES`; R-06 KR → `KOSPI_OFFICIAL_CLOSE`). The runtime derives each binding's book list at every decision from the admissions **without editing** `data_contracts.roles`; each change of a derived binding (admission or demotion) ⇒ governance event `kind: "binding_change"` in the same run. Load-time assertion: a book that reads a factor whose acting inputs are not bound to it is refused (T-SCOPE-01 (g)).

Order (F-1): `admissions(...)` is a pure function computed once at run start (needed by `data_ok` binding lists and by the builders' `vt_weight_recommended_book` / `vol_scale_recommended_book` / `overlay_applied_recommended_book`); the `verdict_filter` gate entry re-runs it on the built artifacts and asserts that no recommended-book value departs from neutral (1.0) without an admission. A mismatch ⇒ `engine_feed` blocked for that recommended book + `VERDICT_INTEGRITY` page.

Stack card: once two or more de-risk factors act in a recommended book it is gated as one stack CARD-P (L3489; generation is M7's, T-CAP-02 stack clause).

**(8) `macro.engine_feed`** (L1231-1232; TASK-M8-05; §9.4 item 17 L6014).
- Books: `recommended:<market>` and `specification:<market>` **only**. Any other book kind ⇒ raise (never a FORWARD-SIM or refusal book; T-TREND-04, I-01).
- Not executed when `ctx.acting_error`, `run_mode != "live"`, or `late`.
- Payload per book: `{book_id, run_id, decision_utc, effective_session, weights: {line: w}, blocked: [BLOCKED rules]}`; a HALTED book's target is 0 (the HALT decided at the close of t sets the weights decided at t to 0, L1178); a DISARMED book receives nothing.
- **Atomic per book**: all of a book's weights for a decision are delivered or none; an interrupted delivery leaves the book on its previous weights and is recorded (`{book_id, delivered: false, error}` in the step result + alert). Implementation: build the complete payload, write temp + `os.replace` (existing idiom `runtime.py:378-384`), then one call to the M5 book API; idempotent on `(book_id, decision_utc)`.
- Reaches `core/engine/orders` only through the simulated order book API (T-RO-01).

**(9) `macro.forward_books`** (L1233-1234; L1184-1185). Forward evaluator for `forward_sim:R-28`, `forward_sim:R-29`, `refusal:R-11`, `refusal:R-12` and every committed card's `card:<card_id>:<on|off|S>`; recorded in `core/engine/state`; display only; never through `engine_feed`. Each decision writes timestamped `macro_state` and `overlay_decision` artifacts (`decision_utc`, every input with `available_at_utc` and `value_status`) (L5308). Integrity rules B.6.1.

**(10) `macro.forward_monitor`** (L1235): R-25 alarms on whole-book NAV; integrity triggers demote immediately (B.6).

**(11) `macro.brief`** (L1236): Macro page and weekly brief section; open owner decisions listed; `monitoring_report` (weekly brief; monthly card page, L5359-5365): ΔSR, ΔES21 and ΔMDD vs S (or vs overlay-off), CUSUM state and alarms; time under water, worst-day coverage, re-entry lag; the bull tax for Korea, switch counts against the card's 99th percentile; lag-audit status and the rules-store edit log; the honesty line; forward-on, forward-off and S simulated P&L.

**(12) `macro.run_record`** (L1237-1245): row in C.2.

**`macro.missed_decisions`** (L1246-1247): on app start **and** at every scheduled run, compare the calendar's expected decisions with `run_log.jsonl`; each missing decision, and each decision whose run record has `status = error` in an acting step, raises `MISSED_DECISION` (severity `page`) and the books carry their weights. Pure function over `(expected, rows)`; `main.py` only wires it (once per process).

**Alerts** (L1248-1250; object schema L3625-3629): sinks = a Macro-page banner (always; page alerts persist until acknowledged), an OS notification, an optional e-mail skill. Persisted store (survives restart, T-OBS-03); re-raise of the same `(code, component, series_id, books)` increments `count`, keeps `first_seen_utc`; `ack_utc` set only by the operator. Codes owned here (all severity `page`): `RUN_ERROR`, `MISSED_DECISION`, `VERDICT_INTEGRITY`, `GOVERNANCE_LOG_BROKEN`. Every HALT also pages (TASK-M8-06).

**Governance log at app start** (L1250, T-OBS-05): `core.rules.governance.verify_chain(path)`; a hand-edited row ⇒ `GOVERNANCE_LOG_BROKEN` (page). Events appended by this area: `halt`, `rearm`, `book_state`, `demotion`, `binding_change`, `record_reset`, `verdict_integrity` (enum L4104-4105).

### B.3 Book separation — I-03 (TASK-M8-03)

```python
def assert_book_separation(book_id: str, reads: Iterable[FactorRead]) -> None   # raises BookSeparationError; called by the book builder for every book, every decision
# FactorRead{rule_id, card.verdict, card.disposition, source_book_kind}
```
| Book | May read | Must never read (assert) |
|---|---|---|
| `recommended:<m>` | invariants; factors with `verdict == "PASS"` and `disposition ∈ {RECOMMENDATION, BUILD_AS_INSURANCE}`; R-31 steps with `disposition == INVARIANT_STEP` | a FORWARD-SIM multiplier; a refusal-book multiplier; a non-PASS factor; R-04 (always); R-31 steps while the frozen binding share > 0.10 and the card has not passed; dispositions `SPECIFICATION_ONLY`, `FORWARD_SIM`, `REFUSAL_BOOK` (L3770) |
| `specification:<m>` | every BUILD NOW and SPECIFICATION BOOK factor, labelled with its verdict | the R-11 or R-12 multiplier; a FORWARD-SIM card's factor (that lives in its own book) |
| `forward_sim:<rule>` | the specification book × that card's factor, on the card's instrument book and notional | a refusal multiplier; never read by another book; never `engine_feed` |
| `refusal:<rule>` | its own multiplier | read by no other book; never `engine_feed`; no acting module imports it (T-CTX-01) |

Every other factor enters the recommended book as 1.0 (L886). Config: `overlay.books: [recommended, specification, forward_sim_per_card, refusal_display_only]`; `overlay.recommended_dispositions: [RECOMMENDATION, BUILD_AS_INSURANCE, INVARIANT_STEP]` (L4278-4279). Rules-store shape `recommended_book_reads_non_pass_multiplier: 22` (L4678) is the static half (M0); this assertion is the runtime half.

### B.4 HALT scope end to end — T-SCOPE-01 (TASK-M8-04; L5675, L1178)

Scope rule: a trigger HALTs only the books whose own NAV breached, whose own artifact failed acting-field validation, or that read the failed input or component through an `acting_exposure` binding. A global failure (PIT store, calendars, QuoteFeed) HALTs every book that reads it; never "the engine". Per-book hooks never call `EngineState.halt()`.

| Case | Injection | Expected |
|---|---|---|
| (a) | R-04 inputs (`DM_MKT_RET_24M`, `DM_MKT_VOL_126`) and `MOM_PAPER_LS_SERIES` fail on 3 consecutive decisions | specification book HALTED (OPS) only; recommended book ARMED with unchanged weights |
| (b) | S&P close (`SPX_OFFICIAL_CLOSE`) missing on 3 decisions | `forward_sim:R-28` and `forward_sim:R-29` fail closed (never HALTED); `recommended:KR` ARMED; `hedge_credit_off` set through the corr63 binding (T-ROLE-02) |
| (c) | specification-book NAV at −16% | specification book HALTED (RISK) only |
| (d) | recommended-book NAV at −16% | recommended book HALTED (RISK) |
| (e) | exception inside `hedge_state` | `hedge_credit_off = TRUE`; nothing HALTED |
| (f) | `context_log` schema failure | refused + quarantined + alert; nothing HALTED |
| (g) | `verdict_filter` admits R-03 | `MOM_PAPER_LS_SERIES` bound to the recommended book in the same run (governance event); the series failing on 3 decisions HALTs the recommended book too; a book reading a factor whose acting inputs are not bound to it is refused at load |
| (h) | R-06 KR NOT_RUN; KOSPI close missing on 3 consecutive decisions, every other input fresh | `specification:KR` HALTED only; `recommended:KR` ARMED (vt enters it as 1.0) |

Never a HALT trigger (L1178, L4362-4363): `[risk_model_input_stale_or_failing, hedge_state_exception, context_input_stale, disputed_input, warmup_input_before_first_armed_decision, input_bound_only_to_other_books, display_or_context_field_validation_failure, context_log_or_event_calendar_validation_failure]`. A FORWARD-SIM book never HALTs on a NAV-input failure: the decision is marked failed-closed, printed and counted toward §8.8 (b)'s 10% budget (L1181, L107).

T-OBS-01: each HALT class writes its book's `macro_state.runtime[].halt` block (C.4) and a governance event `kind: "halt"`.

### B.5 Deterministic replay — R-01 rule 7, T-REPLAY-01 (TASK-M8-07; L1493, L5616)

1. Read the past artifact; take its `decision_utc` and `knowledge_utc`.
2. Restore the runtime state from **before** the decision — per-book counters, `halt.causes`, the derived bindings, each covariance input's carry count — from the previous decision's artifacts and the governance log; the carry count is derived from the input's stale labels in **at most the last 5 artifacts**.
3. Re-run the pipeline with `run_mode = "replay"` at that `knowledge_utc` (never now): no `engine_feed`, no forward-record start/backfill/extension (§8.8 (a): "replays are audits only").
4. Canonicalise both artifacts — UTF-8 JSON, sorted keys, floats printed with `repr`, no insignificant whitespace (`reproducibility.determinism: {canonical_json: sorted_keys_repr_floats_no_whitespace, volatile_fields: [generated_at_utc, git_hash], …}`, L4683) — excluding **only** `generated_at_utc` and `git_hash`; compare bytes. Python: `json.dumps(o, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")`.
5. `data_snapshot_id` = md5 of the sorted content hashes visible at `knowledge_utc` ⇒ order-invariant, unchanged when a later correction is appended.

Constraint this imposes on M1-M6 writers: every instant inside an artifact other than `generated_at_utc` (`halt.since_utc`, `alerts[].first_seen_utc`, …) must derive from `decision_utc` / `knowledge_utc` / store rows, and every id (`alert_id`) must be deterministic (e.g. `uuid5` of code + component + decision), or byte equality fails.

### B.6 R-25 forward-record monitoring and demotion v2 — `core/quant/forward.py` (N; TASK-M8-08)

Forward records are "falsification alarms and integrity checks only"; a forward record "can lower a verdict and never raise one" (L2654).

#### B.6.1 Forward books and record integrity (§8.8, L5305-5314; §3.8 L1180)
- From its header commit every card runs three books: `card:<card_id>:on`, `:off` and, for a CARD-P, `:S`. Each FORWARD-SIM card (R-28, R-29) and each refusal book (R-11, R-12) has its own book. The recommended book reads none of them.
- (a) A record starts at the **first decision written by the live `macro_daily` workflow after the header commit** — never before M8, never backfilled; replays are audits only.
- (b) `late`: artifact `generated_at_utc` after the opening of that market's next session ⇒ forward books carry the previous weights for that session; the late artifact is display-only. A missed decision carries the previous weights the same way. Counted and printed on the card page: late and missed decisions, decisions whose acting or forward_sim input failed closed, and every HALTED or DISARMED decision of the card's forward books (once per decision, however many of the three it affects). **More than 10% of a card's scheduled decisions in any rolling 12 months** (default, judgment) is an operational integrity trigger.
- (c) A change of `git_hash` or `config_hash` between consecutive forward decisions is a governance event. A change inside the card's acting-code manifest outside a registered revision is an integrity trigger.
- (d) The forward S book uses the **design-sample m̄ written in the header**, never the forward realised mean (printed beside it).
- (e) Forward on, off and S books follow R-22 rule 6 (L2348): data invariants (R-01, R-19, R-20, R-26) and bounds (R-02) apply; the R-07 hard stop, concentration caps and semiconductor cap are **excluded** (except a card whose claim concerns them: R-31).
- Append-only (R2-C4): a record never spans a DISARMED period; within a card revision its alarm state (CUSUM, rolling windows, counts) is never reset; reset only with a new card revision (governance event `record_reset` with its reason); the record's age still counts from the card's first registration. Every HALTED or DISARMED gap of any of the three books is marked and excluded from **both sides** of every forward comparison.
- The three books are retired together, never singly; an operator kill of one kills all three and is an operational integrity trigger (the gap still excluded). DISARMED → ARMED for card books requires the header to be committed (L1180).
- A card with no calibrated thresholds (no design sample) cannot start a forward record in the recommended book (L2737).

#### B.6.2 Functions

```python
@dataclass(frozen=True) class AlarmThresholds:
    dsr12_p2_5: float            # design sample's 2.5th percentile of rolling 12-month dSR (vs S for CARD-P; vs comparator for CARD-O)
    gap6m_sigma: float | None    # CARD-O: sigma of the 6-month gap (comparator - on) tracking distribution on book NAV
    cusum_mu: float; cusum_sigma: float; cusum_k: float; cusum_h: float
    switch_model: str; switch_p99: float          # "poisson" | "negbin"
    split_per_year: float; panel_offsets: int; panel_alarms_per_year: float
def calibrate_alarms(card) -> AlarmThresholds                      # on the card's full design sample; fixed at record start
def cusum_monitor(d_monthly: Sequence[float], th: AlarmThresholds, s_prev: float = 0.0) -> tuple[float, bool]
def false_demotion_rate(card, shifts: int = 20) -> float           # alarms per record-year on the shift panel
def forward_monitor(card_id: str, book_nav) -> list[Alarm]         # whole-book NAV (signature L1098)
def demote(card, reason: str) -> None
```

1. **Denominator** (L2671): every statistical trigger uses **whole-book NAV**, per-card attribution printed; sleeve NAV is never the denominator (`monitoring.denominator: whole_book_nav`).
2. **Operational and integrity triggers** — immediate, outside the budget (L2672-2678; config list verbatim L2710-2712):
   `[lag_audit_violation, acting_param_edit_outside_revision, provisional_or_stale_input_reached_acting_decision, switches_gt_p99_poisson_negbin, operator_kill_of_forward_books, decision_gaps_gt_10pct_rolling_12m]`
   - any lag-audit violation in the forward record;
   - an acting-parameter edit outside a card revision (rules-store edit history);
   - a provisional or stale input that reached an acting decision;
   - an operator kill of a card's forward books;
   - `> 10%` of a card's scheduled decisions in any rolling 12 months late, missed, failed closed, HALTED or DISARMED (T-DEMOTE-04: 26 HALTED decisions in 12 months trips it);
   - switches above the 99th percentile of the card's Poisson or negative-binomial fit on the design sample (`switch_model: {default: poisson, negbin_if_lr_test_p_lt: 0.05}`); replaces "2× the budget".
3. **Catastrophic bound** (statistical; inside the budget; thresholds calibrated by bootstrap on the card's full design sample):
   - CARD-P — **all three** over a rolling 12 months: `{all_of: ["fwd_dMDD_vs_S <= 0", "fwd_dES95_21_vs_S <= 0", "fwd_dSR_12m_vs_S < design_p2.5"], window_months: 12}`. Trigger text, verbatim: **"forward ΔMDD vs S ≤ 0 = no protection"** (the corrected sign). Reference 2.5% thresholds: −0.39 KOSPI VT, −0.73 US VT.
   - CARD-O — **either**: `{any_of: ["gap6m_comparator_minus_on_book_nav > 2 * sigma_design", "fwd_dSR_12m_vs_comparator < design_p2.5"]}` (R-03: −0.20).
4. **Sequential trigger** (inside the budget): one-sided CUSUM on monthly paired differences
   `z_m = (d_m − μ_design) / σ_design;  S_m = max(0, S_{m−1} − z_m − k);  alarm when S_m ≥ h`
   `k = 0.25`; `h` = the smallest value whose in-control ARL is ≥ 20 years under a stationary bootstrap of the design sample's monthly paired differences (`B = 2,000`, `seed 11`, mean block 12 months). Config: `cusum: {frequency: monthly, k: 0.25, h: bootstrap_calibrated, in_control_arl_years_min: 20}`, `cusum_calibration: {bootstrap: stationary, resamples: 2000, seed: 11, mean_block_months: 12}`. (The naive h 8 alarms 10-13 times a decade — do not hard-code.)
5. **Book-level false-demotion budget** (D4): `false_demotion_budget_per_year: 0.10` across all statistical triggers, `false_demotion_budget_split: {rule: equal_across_active_cards, fixed_at_record_start: true, recalibrated_on_new_card: false}`. "Active cards" = cards with disposition RECOMMENDATION or BUILD_AS_INSURANCE whose forward record is running. A later card receives an equal share of the budget then unallocated; the book-level total is printed. A card whose panel exceeds its split before its start tightens `h`, then its quantile thresholds, until it passes; the result is recorded in its header. The owner may only tighten (`options: [tighten_only_le_0p10]`; accept only `value <= 0.10`).
   - Verification panel: `budget_check: {panel: circular_shift, shifts: 20, min_offset_sessions: 252, short_sample: floor_T_over_252_offsets, seed: 11}` — the card's design-sample paired series, circularly shifted by 20 evenly spaced offsets (≥ 252 sessions apart, so ≥ 20 × 252 = 5,040 sessions needed; shorter sample: ⌊T / 252⌋ offsets, count printed); the calibrated triggers run on each shifted record; **alarms per record-year ≤ the card's split**; book-level rate ≤ the budget (T-DEMOTE-03). Offset grid: F-18.
6. **What a forward record may do** (L2694-2697): may demote; may **never raise a verdict** and never turn INSUFFICIENT DATA into PASS (`forward_record_can_raise_verdict: false`). Upward re-gate only when new history adds an objective episode (continuous rules) or brings de-clustered onsets to the tier count (discrete rules) — `regate_up_only_on_new_history: {continuous: new_objective_episode, discrete: tier_onset_count}` — as one counted revision under the full frozen package; forward-window statistics are printed and never used to raise. **Any attempt to use forward statistics to change a verdict upward raises** (L2738).
7. **After a demotion** (L2698-2703): the card's output leaves the recommended book; new revision with a new header; `demotion_verdict: {operational_or_integrity: REVISE, catastrophic_or_cusum: REJECT}` (default, judgment; council to confirm); `lockout_months_after_demotion: 6`, `lockout_scope: family_x_market` — no new card, revision, instrument book or R-18 re-anchoring of that family in that market enters the recommended book during it. Demoting a CARD-P never removes the risk-layer invariants. A pre-declared R-18 re-anchoring is not a new card. `bull_lag_alone_demotes: false`. The hard stop is a review event, not a demotion trigger. Retiring a card's books while its factor acts in the recommended book first removes the factor (governance event, treated as a demotion for the lockout; L1180). An owner ruling (§8.10) is not an acting-parameter edit and never demotes (L65).
8. **Honesty line** on every card page, verbatim: **"12 months of forward record can only detect catastrophic decay."** Beside it the card's calibrated 2.5% threshold (−0.20 / −0.39 / −0.73 Sharpe for R-03 / KOSPI VT / US VT).

`demote(card, reason)` pseudo-code:
```
kind = "operational_or_integrity" if reason in monitoring.operational_triggers (or manifest/kill) else "catastrophic_or_cusum"
governance.append_event(kind="demotion", rule_id=card.rule_id, book_id=recommended:<m>, old=card.verdict, new=monitoring.demotion_verdict[kind], reason=reason, actor="runtime")
record.demoted = True; record.demotion_reason = reason
lockout[(card.family, card.market)] = utc + 6 months
# next admissions() refuses the factor -> binding_change events; risk-layer invariants untouched; a new revision (new header) is required
```

Fail-closed (L2735-2738): whole-book NAV unavailable ⇒ statistical triggers suspended and alerted, operational triggers stay live; NAV unavailable on more than 2 consecutive decisions (`nav_unavailable_ops_halt_after_decisions: 2`) ⇒ OPS HALT of the books it values (only `acting_exposure` NAV bindings; FORWARD-SIM books never HALT), and the forward record marks the gap.

### B.7 R-28 trend-axis card, FORWARD-SIM (TASK-M8-09; L2964-3063)

```python
# core/quant/signals.py
def trend_axis(market: str, decision_utc: datetime) -> Multiplier     # value in {0.5, 1.0}; exposure_basis = "total"; raises for market == "KR"
```
1. At each month-end official close `t_m`: `SMA10m(t_m)` = the mean of the last 10 month-end closes, **including** `t_m`. `flag = close(t_m) < SMA10m(t_m)`.
2. `trend(t_m) = 0.5 if flag else 1.0`; decided at the close of `t_m`; holds from `t_m + 1` session to the next month-end decision.
3. Composition by `min()`: `composed = vt × min(trend, other overlays, ladder, post_rearm_cap)`; outside HALTED `composed ≥ 0.5 × vt`.
4. Claim, registered verbatim: **"slow-bear protection via the volatility state"**. No Sharpe, return or predictability claim.
5. Judged incrementally on the vol-targeted book: overlay-off = the VT book without the trend axis; for the US instance = R-29's futures vt book (`CME_micro_ES`, 5 bp, daily vt) — both FORWARD-SIM cards share one book; `S = that book × the trend's mean multiplier`; PC-1′ to PC-7 under the frozen package; on monthly data the horizons are 1 and 6 months. **Claim line**: stacked ΔMDD on VT ≥ 3 pp, printed with its bootstrap band; a miss caps the card at INSUFFICIENT DATA ("claim not shown"); it never REJECTs.
6. Tier A via a pooled-onset rule **declared in the header before any run**: onsets de-clustered at the rule's own lookback (10 months); pooled across the declared non-Korean index set (default the six of DLB-T3e: S&P 500, Nikkei 225, HSI, DAX, FTSE 100, TAIEX); the own-market estimate (and the cross-market dispersion τ, L4868) always printed; an own-market PC-1′ or PC-2 failure vetoes a pooled pass; pooling never rescues a card already run. The US instance alone has 45 de-clustered onsets on 1927-2026.
7. Printed lines: the GJR-null percentile; the snooping haircut over the trend family (94 variants; ΔMDD ≥ 3 pp in all; Sharpe deflated probability 0.43-0.59); the daily and horizon-matched PC-2.
8. Scope: one card per US or other non-Korean equity sleeve; the US is the first instance (`MACRO-R28-US-TREND`, L4824). **A Korea instance is refused** by rules-store validation (shape `r28_instance_market_kr: 37`); the KOSPI trend state is displayed as context only (`context_log`, R-13 L1687) and is computed by a context function, never by an acting path; a horizon-matched PC-2 may never rescue KOSPI trend. The 200-day band (BAND200) is a logged trial in the same ledger, never a second card.
9. Status: FORWARD-SIM in the specification book until a US or other non-Korean sleeve exists (D5); then BUILD-AS-INSURANCE on a formal v2 PASS. The forward record is a falsification alarm only.

Inputs: the sleeve index's official month-end closes (`value_status = official_close`, `session_date` = the last session of the month); `vt` of the same market (R-06, R-29); cash at the local short rate (R-22). Bindings: `SPX_OFFICIAL_CLOSE` (`forward_sim`, consumer `R-28_R-29`), `NON_KR_INDEX_MONTH_END_CLOSES: {role: forward_sim, books: ["forward_sim:R-28"]}`.

Fail-closed: a missing month-end official close leaves the multiplier unchanged and fails closed (R-19); a Korea instance, a header without a pooling rule, or a header with a Sharpe claim is refused; the FORWARD-SIM book is never read by the recommended book.

Header validation (T-TREND-01): refuse a header missing any of — monthly SMA10m; gross 0.5× below trend; `min()` composition; the claim string above; a pooled-onset rule — all declared before the run.

Outputs: `macro_state.forward_sim.R28_below_sma10m` (display); `overlay_decision.forward_sim[]` with `rule_id: R-28` while FORWARD-SIM (`multipliers[]` with `exposure_basis: total` once promoted), each with `card: {class: CARD-P, verdict, disposition, displayed_as}`; `model_card.macro.claim_lines`, `claim_line_results = {stacked_dMDD, band, pass}`, `pooling = {rule, n_onsets_own, n_onsets_pooled}`, `gjr_null_pct`, `snooping = {n_variants, share_dMDD_ge_3pp, deflated_prob_sr}`.

### B.8 R-29 `MACRO-R06-US-FUT`, FORWARD-SIM (TASK-M8-10; L3065-3153)

1. `vt_US(t) = min(1.0, 0.15 / σ̂_SMA20(t))`, daily, decided at the US close of t, earning from t+1. Cap 1.0, no floor. Estimator SMA20 fixed before the run (R-30's challenger only through a counted revision).
2. Book: `CME_micro_ES` at 5 bp per side (futures cost class); `rebalance: daily`; `no_trade_band: 0`; `notional_nav` declared (`{ref: sleeves.US.notional_nav}`; never declared on the card).
   - Live use requires one contract (≈ ₩52m; `instruments.futures_granularity.contract_notional_krw.CME_micro_ES: 52e6`, `max_contract_share_of_sleeve: 0.05`) ≤ 5% of the notional ⇒ sleeve ≈ ₩1bn or more (52e6 / 0.05 = 1.04e9).
   - `contracts = round_half_away_from_zero(vt × notional_nav_KRW / (multiplier_USD × index level × USDKRW_t))`; `USDKRW_t` = the book's `nav_fx` series at the decision (the latest `USDKRW_1530_SNAPSHOT` usable then; `ECOS_1530_CLOSE` for history), recorded in `overlay_decision.extras` (`extras.usdkrw`, `extras.contracts`, L3755). Python `round()` is banker's rounding — use `math.copysign(math.floor(abs(x) + 0.5), x)`.
   - Roll before expiry on a fixed calendar, with a roll-cost line.
3. Episodes: objective ≥ 15% S&P episodes (`episodes: {theta: 0.15}`).
4. **Settling run** — `settling_run(card, data='FF_daily_1926', starts='decade')` (L3073) on French daily Mkt-RF 1926-07 → 2026-08 at 5 bp. PASS only if both hold:
   - PC-1′ holds at 1× **and** 2× (both legs, points > 0, `p_h × f ≤ 0.10`; R-21);
   - the card PASSes at ≥ 80% of the 10 decade-spaced starts (**≥ 8**, integer count; R-22's frozen shape `decade_spaced: {min_span_years: 80, starts: declared_start_then_january_of_each_decade, last_start_min_years_before_end: 10, pass_share_min: "4/5"}`, L2375): the declared start (first close + 20-session warm-up), then the first session of January 1930, 1940, … 2010; **no REJECT at any of these starts and no REJECT in either calendar-midpoint half** (`stability_floor: {no_reject_at_any_band_start: true, pass_share_min: from_band_shape, compare: integer_counts, no_reject_in_midpoint_halves: true, applies_to_every_shape: true}`, L2376-2377).
   ```python
   def settling_pass(pc1p_1x: bool, pc1p_2x: bool, start_verdicts: Sequence[str], h1: str, h2: str, full_span: str) -> bool:
       return (pc1p_1x and pc1p_2x and len(start_verdicts) == 10
               and sum(v == "PASS" for v in start_verdicts) >= 8
               and "REJECT" not in start_verdicts and "REJECT" not in (h1, h2)
               and full_span == "PASS")                       # settling_run.full_span_must_pass: true
   ```
   T-USFUT-02 negatives: a 70% share (7/10) ⇒ no PASS; 9 of 10 with one REJECT start ⇒ no PASS.
5. **Promotion to BUILD-AS-INSURANCE** requires all of (`promotion: {requires: [us_sleeve_or_owner_line, settling_run_pass, v2_package_pass]}`): (1) a US sleeve exists with a declared notional at which one Micro ES is ≤ ~5% of the sleeve (≈ ₩1bn), or the owner declares another executable line (D5: a KRX-listed S&P ETF line with FX and NAV lag modelled); (2) the settling run of rule 4 passes; (3) the card's v2 verdict on its full settling-run span under the blind package with objective ≥ 15% S&P episodes is PASS, with no REJECT at any decade-spaced start. Rule 4 is necessary, not sufficient; the card's recorded verdict is the full-span verdict after the caps.
6. Logged trials, never rescues: `logged_trials: [monthly_50bp, band_0p10_50bp]` — appended to the R-06 family ledger (R-23), never a revision of this card.
7. Until promotion: FORWARD-SIM in the specification book; a falsification alarm only.

Registration (T-USFUT-01): registered once as a new card — `card_id: MACRO-R06-US-FUT`, `family: R-06` (one new trial in the R-06 ledger) — with a Micro ES 5 bp book and a notional field; a second registration under the same family with a 50 bp book raises (DNB #23).

Inputs: US official closes (`value_status = official_close`); NYSE decision instant `close_print_bound_utc('US', t)` = the scheduled close (20:00Z EDT, 21:00Z EST; 17:00Z / 18:00Z on early closes) + 30 s; US RF cash; Micro ES contract specifications and the roll calendar (R-26).

Fail-closed (L3125-3129): the settling run cannot run without the frozen 1926 fixture — its absence keeps the card FORWARD-SIM; **it never falls back to the 1990 file**; a header without `notional_nav` is refused; a live book below the granularity floor is refused; the FORWARD-SIM multiplier never reaches `engine_feed`.

Outputs: `model_card.macro` with `card_id: MACRO-R06-US-FUT`, `instrument_book`, `notional_nav`, `contracts_path`, `settling_run = {span, verdict, pc1_prime_1x, pc1_prime_2x, starts[], n_pass, n_starts, n_reject, midpoint_halves}`, `start_band_results`; `overlay_decision.forward_sim[]` with `rule_id: R-29`; `macro_state.forward_sim.R29_vt_weight_next`.

### B.9 R-11 (S1) refusal book (TASK-M8-12; L1639-1651)

```python
# core/quant/risk.py
def refusal_krw_leg(decision_utc: datetime) -> Multiplier     # value in {0.75, 1.0}; status = "REFUSAL"; exposure_basis = "total"
```
- `krw20(t) = ln(USDKRW(t) / USDKRW(t−20 obs))` on a timestamped 15:30:00 KST snapshot or the ECOS 15:30 close, stamped ≤ the KRX close of t. `flag = krw20 > 0.03`. Multiplier `0.75` on Korea market gross (`exposure_basis=total`), decided at the KRX close of t and earning from t+1, **in the refusal book only**. One-sided: no action when the KRW strengthens.
- Inputs: the ECOS 15:30 close (731Y003, item 0000003; 15:00 before 2016-08-01) or a timestamped 15:30:00 KST snapshot (onshore USD/KRW trades 24 hours from 6 Jul 2026). DEXKOUS is a labelled proxy only, never read in production (`data.usdkrw: {input: [ECOS_1530_CLOSE, USDKRW_1530_SNAPSHOT], proxy: DEXKOUS, proxy_timing: H10_publication, production_reads_dexkous: false, record_fx_regime: true}`; T-H10-01: reading DEXKOUS in `run_mode = live` for an acting or risk-model input raises). FX-regime metadata recorded with the input. Bindings: `role: context`, consumer `R-11_refusal_book`.
- Config (L4409): `refusal_books.S1_krw: {lookback_obs: 20, threshold_dlog: 0.03, multiplier: 0.75, target: KR_market_gross, one_sided: true, verdict: REJECT, regate_queue: false}`.
- Status actions: remove S1 from the FORWARD-SIM re-gate queue (BL-S01 closed; BL-G04 and BL-D13 drop to P3); card records **REJECT** (54 strict-H.10 de-clustered onsets, ΔMDD vs the static book −1.3 pp, tail-exposure ratio 1.004 → "tail 1.00"); display labelled; read by no other book.
- Outputs: `macro_state.refusal_books.S1_krw_flag` (bool | null); `overlay_decision.refusal[]` entry `{rule_id, value, would_apply_to, card: {…, verdict: "REJECT", disposition: "REFUSAL_BOOK", displayed_as: "refusal"}}` in the KR `market_gross` record.

### B.10 R-12 (S2) refusal book (TASK-M8-13; L1653-1665)

```python
def refusal_rates_leg(decision_utc: datetime, applies_to: str = "market_gross") -> Multiplier   # value in {0.5, 1.0}; status = "REFUSAL"; raises unless (US, market_gross)
```
- `d10(t) = y10(t) − y10(t−20 obs)`, in percentage points, on the **KIS US 10y quote** stamped ≤ the US close of t. `flag = d10 > 0.40`. Multiplier `0.5` on **US duration-sensitive gross** (`exposure_basis=total`), decided at the close of t and earning from t+1, in the refusal book only. Scope: all US long-only equity exposure. Excluded: momentum and other long/short factor sleeves, and Korea. **S2 applied to momentum raises** (T-BASIS-01 S2 clause).
- Backtest timing (record only): DGS10 dated D posts 16:15 ET on the next Fed business day ⇒ strict H.15 uses it from the close of **D+2 business days**; Treasury's daily par yield for D is "usually available … by 6:00 PM Eastern Time" on D ("may be delayed") ⇒ with a logged posting time usable from the close of **D+1 business day**: compliant via the Treasury par-yield channel (recorded in the registry). The ^TNX close dated D is a live-feed proxy (2015+).
- Config (L4410-4411): `refusal_books.S2_rates: {lookback_obs: 20, threshold_pp: 0.40, multiplier: 0.5, target: US_duration_sensitive_gross, excludes: [momentum, ls_factor_sleeves, KR], verdict: REJECT, regate_queue: false}`. Bindings: `US10Y_KIS_QUOTE: [{role: risk_model, consumer: corr63}, {role: context, consumer: R-12_refusal_book}]`; `DGS10: [{role: risk_model, consumer: corr63_backtests}, {role: context, consumer: R-12_refusal_book}]`.
- Status actions: remove S2 from the FORWARD-SIM queue (BL-S02 closed); card records **REJECT at every timing and cost** with 71 onsets (39 in 1990-2007, 32 in 2008-26), incl. Treasury +1 business day (compliant) ΔMDD −3.1 pp at 50 bp (ΔSR −0.105) and strict +2 business days −3.5 pp (ΔSR −0.120); G-US-02a reads, verbatim, **"compliant via Treasury with logged posting time"**; timing-fragile (fragility ratio 0.75 > 0.5; R-34).
- State (L1664, L6327): flag on in data dated 23 Sep 2026 (+50 bp to 30 Sep); under strict timing the refusal book applies it from the decision at the close of 25 Sep, earning from 28 Sep. Refusal reason string (L3798): "S2 refusal book: strict-H.15 flag on from the close of 2026-09-25 (data date 2026-09-23); display only".
- Outputs: `macro_state.refusal_books.S2_rates_flag`; `overlay_decision.refusal[]` entry in the **US** record with `family: "market_gross"`, `exposure_basis: "total"`: `{"rule_id":"R-12-S2","value":0.5,"would_apply_to":"US duration-sensitive gross (refusal book)","card":{"card_id":"MACRO-R12-US-RATES","class":"CARD-P","verdict":"REJECT","disposition":"REFUSAL_BOOK","displayed_as":"refusal",…}}`.

---

## C. Schemas and config

### C.1 Where things live
- Rule blocks: the v2 rules document (`core/rules/macro_rules_v2.json`, M0). This area reads `monitoring`, `cards.R-28_trend_axis`, `cards.R-29_US_FUT`, `refusal_books`, `sleeves`, `owner_decisions.D4/D5`, `data.ingest`, `data.knowledge_utc`, `data_contracts.on_failure`, `data_contracts.roles`, `overlay.books`, `overlay.recommended_dispositions`, `risk_layer.halt_scope/halted_triggers/ops_rearm/never_halt_on`, `gate.package`, `reproducibility`. Where §7 and a rule differ, the rule governs (L4132).
- Files under `config.macro_artifact_dir()` (env-overridable; tests always pass temp paths, T-HERM-02): `run_log.jsonl`, `governance_events.jsonl`, `alerts.json`, `cards/verdicts.jsonl`, `cards/<card_id>.json`, artifacts, `quarantine/`, `fetch_log.jsonl`, per-book runtime + forward-record state (separate file from `engine.json`).

### C.2 `run_log.jsonl` row (L1237-1245)
Binding fields: `{run_id, market, session_date, decision_utc, knowledge_utc, started_utc, finished_utc, step results with errors, git_hash, config_hash, data_snapshot_id, late}`. Proposed concrete shape (names of the non-binding parts are this brief's):
```json
{"run_id":"…","market":"KR","session_date":"2026-10-02","decision_utc":"2026-10-02T06:30:30Z","knowledge_utc":"2026-10-02T06:40:50Z",
 "started_utc":"…Z","finished_utc":"…Z","run_mode":"live","status":"ok|error","late":false,
 "steps":[{"name":"macro.pit_snapshot","kind":"skill","status":"ok|error|blocked|skipped","error":null}],
 "git_hash":"…","config_hash":"…","data_snapshot_id":"<md5>"}
```
Append-only; one line per run; written even when a step raises.

### C.3 Alert object (verbatim L3625-3629; also embedded in `macro_state.alerts[]`)
`required: ["alert_id","code","severity","component","first_seen_utc","count"]`; `severity ∈ {"info","warn","page"}`; optional `series_id`, `books[]`, `escalated`, `ack_utc`.

### C.4 `macro_state` fields this area writes (L3589-3630)
- `runtime[]`: `required ["book_id","engine_state","halt","consecutive_failures","book_counter"]`; `engine_state ∈ {DISARMED, ARMED, HALTED}`; `halt` (object|null): `required ["class","reason_code","since_utc","rearm_mode","causes"]`, `class ∈ {RISK, OPS}`, `rearm_mode ∈ {auto, operator}`, `causes[]` of `{class, reason_code, since_utc, rearm_mode, rearm_not_before, cleared_utc}`, optional `component`, `series_id`, `rearm_not_before`, `ack_by`, `ack_utc`; plus `post_rearm_cap_until`, `nav`, `hwm_hard`, `ref_step`. Book ids: `recommended:<market>`, `specification:<market>`, `forward_sim:<rule>`, `refusal:<rule>`, `card:<card_id>:<on|off|S>`.
- `refusal_books: {S1_krw_flag: bool|null, S2_rates_flag: bool|null}` ("display only; read by no book").
- `forward_sim: {R28_below_sma10m: bool|null, R29_vt_weight_next: number|null in [0, 1]}` ("never the recommended book").
- `lag_audit: {checked, violations[]}`; `fail_closed`; `alerts[]`; `extras.validation_errors`; `flags.engine_state` reports the market's recommended book.
- `inputs[].status` enum: `ok, stale, stale_missed_release, missing, provisional_rejected, session_mismatch, synthetic_rejected, disputed, warmup`.

### C.5 `overlay_decision` fields (L3745-3762)
- `forward_sim[]`: `required ["rule_id","value","card"]`, `value ∈ [0, 1.0]`, optional `would_apply_to`.
- `refusal[]`: `required ["rule_id","value","card"]`, `value ∈ [0.5, 1.0]`, optional `would_apply_to`.
- `$defs.card`: `required ["card_id","class","verdict","disposition","displayed_as","results_md5"]`; `verdict ∈ {PASS, REVISE, REJECT, INSUFFICIENT_DATA, NOT_RUN}`; `disposition ∈ {RECOMMENDATION, BUILD_AS_INSURANCE, INVARIANT_STEP, SPECIFICATION_ONLY, FORWARD_SIM, REFUSAL_BOOK, DESCRIPTIVE}`; `displayed_as ∈ {recommendation, insurance, invariant, descriptive, refusal}`. `displayed_as ∈ {recommendation, insurance}` iff `verdict = PASS` and `disposition ∈ {RECOMMENDATION, BUILD_AS_INSURANCE}`; `displayed_as = invariant` iff `disposition = INVARIANT_STEP`.
- `extras` (open): R-26 `{instrument_book, contracts, w_target, w_held, band, usdkrw}`, R-27 `{fill_model, decision_price_source, fill_status, flags}`, R-32 `validation_errors`.

### C.6 `model_card.macro` result fields (L4037-4065)
- `forward_record = {start_utc, first_registered_utc, months, dSR_vs_S, dES21, dMDD, cusum_S, alarms[], switches, switch_p99, lag_audit_violations, demoted: bool, demotion_reason, honesty_line, missed_decisions, gaps[]}` ("falsification alarms only (R-25); can never raise the verdict"; the age counts from `first_registered_utc`).
- `settling_run = {span, verdict ∈ {PASS, REVISE, REJECT, INSUFFICIENT_DATA}, pc1_prime_1x: bool, pc1_prime_2x: bool, starts[], n_pass, n_starts, n_reject, midpoint_halves}`; `contracts_path` (array|null).
- `start_band_results = {starts[], verdicts[], n_pass, n_starts, n_reject, floor_pass}`; `midpoint_halves_results = {h1, h2}`.
- `claim_line_results = {stacked_dMDD, band[], pass}`; `pooling = {rule, n_onsets_own, n_onsets_pooled}`; `snooping = {n_variants, share_dMDD_ge_3pp, deflated_prob_sr}`; `gjr_null_pct` (0-100).

### C.7 `cards/verdicts.jsonl` row (L3487; appender = M7)
Append-only, hash-chained: `card_id`, revision, `header_md5`, `results_md5`, verdict, disposition, `gate_package_md5`, `data_snapshot_id`, `git_hash`, `ledger_hash_at_run`, `prev_row_md5`; committed with the card file.

### C.8 `governance_event` (L4099-4110; appender `core/rules/governance.py`, M0)
`required ["schema","schema_version","event_id","utc","kind","book_id","rule_id","key","actor","reason","refs","prev_row_md5"]`; `kind ∈ {halt, rearm, book_state, demotion, package_freeze, package_redesign, header_commit, owner_ruling, calendar_change, notional_change, admissibility_reweight, binding_share_recompute, binding_change, record_reset, verdict_integrity}`; `actor ∈ {owner, operator, runtime, harness, council}`.

### C.9 Config blocks, verbatim

`monitoring` (L2708-2729 = L4477-4497):
```yaml
monitoring:
  denominator: whole_book_nav
  operational_triggers: [lag_audit_violation, acting_param_edit_outside_revision, provisional_or_stale_input_reached_acting_decision,
                         switches_gt_p99_poisson_negbin, operator_kill_of_forward_books,
                         decision_gaps_gt_10pct_rolling_12m]
  catastrophic:
    card_p: {all_of: ["fwd_dMDD_vs_S <= 0", "fwd_dES95_21_vs_S <= 0", "fwd_dSR_12m_vs_S < design_p2.5"], window_months: 12}
    card_o: {any_of: ["gap6m_comparator_minus_on_book_nav > 2 * sigma_design", "fwd_dSR_12m_vs_comparator < design_p2.5"]}
  cusum: {frequency: monthly, k: 0.25, h: bootstrap_calibrated, in_control_arl_years_min: 20}
  false_demotion_budget_per_year: 0.10              # canonical key of D4
  false_demotion_budget_split: {rule: equal_across_active_cards, fixed_at_record_start: true, recalibrated_on_new_card: false}
  budget_check: {panel: circular_shift, shifts: 20, min_offset_sessions: 252, short_sample: floor_T_over_252_offsets, seed: 11}
  cusum_calibration: {bootstrap: stationary, resamples: 2000, seed: 11, mean_block_months: 12}
  switch_model: {default: poisson, negbin_if_lr_test_p_lt: 0.05}
  demotion_verdict: {operational_or_integrity: REVISE, catastrophic_or_cusum: REJECT}
  lockout_scope: family_x_market
  nav_unavailable_ops_halt_after_decisions: 2
  forward_record_can_raise_verdict: false
  regate_up_only_on_new_history: {continuous: new_objective_episode, discrete: tier_onset_count}
  lockout_months_after_demotion: 6
  bull_lag_alone_demotes: false
```

`cards.R-28_trend_axis` (L3011-3030 = L4413-4430):
```yaml
R-28_trend_axis:
  rule: {signal: month_end_close_below_sma10m, multiplier_below: 0.5, multiplier_above: 1.0,
         decided: month_end_close, applies: next_month, composition: min, exposure_basis: total}
  claim: "slow-bear protection via the volatility state"
  judged: {incremental_on: vol_targeted_book, comparator: S_of_VT_book, claim_line_stacked_dMDD_min_pp: 3.0,
           claim_line_failure: cap_INSUFFICIENT}
  pooling: {decluster_gap_months: 10, indices: [SPX, N225, HSI, DAX, FTSE100, TAIEX], own_market_veto: true,
            declared_before_any_run: true}
  markets_allowed: [US, other_non_korean]
  markets_refused: [KR]
  logged_trials_same_ledger: [BAND200]
  status: FORWARD_SIM
  us_sleeve: {ref: sleeves.US.line}
  instrument_book: CME_micro_ES
  rebalance: monthly
  no_trade_band: 0.0
  notional_nav: {ref: sleeves.US.notional_nav}
  fill_model: NYSE_moc
```

`cards.R-29_US_FUT` (L3101-3118 = L4431-4447):
```yaml
R-29_US_FUT:
  card_id: MACRO-R06-US-FUT
  family: R-06
  rule: {estimator: sma, window: 20, target_ann: 0.15, cap: 1.0, floor: none, rebalance: daily, exposure_basis: total}
  instrument_book: CME_micro_ES
  cost_class: futures                              # 5 bp per side, read from the gate
  no_trade_band: 0.0
  notional_nav: {ref: sleeves.US.notional_nav}
  nav_fx: {series: USDKRW_1530_SNAPSHOT, history: ECOS_1530_CLOSE}
  episodes: {theta: 0.15}
  settling_run: {data: FF_daily_MktRF_1926-07_to_2026-08, cost_bp: 5, pc1_prime_at: [1x, 2x],
                 starts: decade_spaced, pass_share_min: from_band_shape, no_reject_at_any_start: true,
                 no_reject_in_midpoint_halves: true, full_span_must_pass: true}
  promotion: {requires: [us_sleeve_or_owner_line, settling_run_pass, v2_package_pass]}
  us_sleeve_and_line: {ref: sleeves.US.line}
  logged_trials: [monthly_50bp, band_0p10_50bp]
  status: FORWARD_SIM
```

Others: `refusal_books` (B.9, B.10); `sleeves: {US: {line: none, notional_nav: null}, KR: {notional_nav: null}}` (L4462-4464); `owner_decisions.D4: {key: monitoring.false_demotion_budget_per_year, value: 0.10, default: 0.10, options: [tighten_only_le_0p10], status: default, …}`; `owner_decisions.D5: {key: sleeves.US.line, value: none, default: none, options: [CME_micro_ES, KRX_listed_SP500_ETF, none], status: pending, …, refs: [instruments.us_line_choice, cards.R-28_trend_axis.us_sleeve, cards.R-29_US_FUT.us_sleeve_and_line]}` (L4146-4149); `risk_layer.halt_scope: per_book`; `risk_layer.halted_triggers.OPS: [lag_audit_violation, acting_field_schema_or_bounds_failure, acting_input_fail_closed_beyond_declared_misses, feed_heartbeat_loss_60s, acting_risk_layer_exception, whole_book_nav_unavailable_gt_2_decisions, calendar_coverage, operator_kill, acting_step_error_beyond_limit]`; `risk_layer.ops_rearm: {when: cause_cleared, operator_required_after: [lag_audit_violation, acting_field_schema_or_bounds_failure], reference_reset: false, post_rearm_cap: false}` (L4353-4361); `reproducibility: {seed_study: 11, seed_research_bootstrap: 20261002, record: [git_hash, config_hash, data_snapshot_id, knowledge_utc, seed, results_md5, gate_package_version, gate_package_md5, ledger_hash_at_registration, ledger_hash_at_run], determinism: {canonical_json: sorted_keys_repr_floats_no_whitespace, volatile_fields: [generated_at_utc, git_hash], rng: numpy_pcg64_seedsequence_spawned_children, blas_threads: 1, relative_tol: 1.0e-12}}` (L4680-4684); `do_not_build.refused_shapes`: `header_edit_after_results_md5: [23, 32]`, `forward_record_cited_as_validation: 35`, `r28_instance_market_kr: 37`, `recommended_book_reads_non_pass_multiplier: 22` (L4672-4678).

---

## D. Tests

Classes: **SYNTH** = hermetic with synthetic/inline fixtures; **REFDATA** = needs frozen reference data not on this machine; **OWNER** = needs owner input, credentials or live sessions. Tolerances for goldens: Level 1 (L5734-5735: Sharpe ±0.01; max DD ±1 pp; bootstrap shares ±0.03; p ±0.01/±0.005; deterministic counts exact; bootstrap-dependent counts ±1; percentiles ±5); a verdict within tolerance of its threshold is asserted as a class (L5499). A REFDATA test must be reported as a labelled skip, never as PASS and never against invented numbers. Local data that exists: `docs/asset_expansion/cache/fred_DEXKOUS.csv` (2017-01-02 → 2026-09-18), `yf_SPY.csv` (1995-01-03 → 2026-09-25), `yf_069500.KS.csv` (2007-01-29 → 2026-09-23), `yf__VIX.csv`, `fred_DGS3MO.csv`; no ^KS11, ^GSPC, KRW=X, ^TNX, DGS10, Treasury par, French files, index panel; the tech-fund `datalab/results/*` are result tables, not series.

| ID (runs_from) | Assertion | Fixture | Class |
|---|---|---|---|
| **I-01** (M8; L5688) — mechanics | End-to-end `macro_daily`: all five artifacts produced and valid against schema 2.0; the HTTP transport records zero non-allowlisted KIS requests; `data_ok` passes a stale risk-model input with `hedge_credit_off` set and fails closed on a stale acting input (for the bound books only); `verdict_filter` admits only PASS factors (RECOMMENDATION or BUILD_AS_INSURANCE) and R-31 steps with `INVARIANT_STEP`; R-06 KR (BUILD_AS_INSURANCE on PASS, NOT_RUN today) refused; refusal books (R-11, R-12) and FORWARD-SIM cards (R-28, R-29) never reach `engine_feed`; decision gates fire on injected failures | synthetic PIT store + temp rules store, cards dir, artifact dir; injected clock | SYNTH |
| **I-01** — golden clauses | KR decisions 2026-07-30 and 2026-10-02, US decisions 2026-07-30 and 2026-10-01: the 2026-10-02 run uses the official close **7,003.74** and its flags match §11 (vt 0.694, rv20 28.82%, `hedge_credit_off` TRUE with `hedge_reasons` [corr_positive, core_pce_ge_3], `gap_sessions` 2, `var_display_scale` 1.4142, `kr_open_gap_event` true, `absolute_bound` 0.755, `active_bound` 0.685, gross 0.685 in both books, binding factor `active_single_name`, both KR books ARMED, hard stop armed, S1 flag OFF, S2 flag on); the 2026-07-30 KR run reproduces **vt 0.25** (G-KR-04) | post-close fixtures: KOSPI official closes, KODEX 200 PDF, pair and KOSPI market caps, S&P closes, corr63 inputs (KIS 10y / DGS10), core PCE vintages, USD proxy, event calendar. Local cache does not reach 2026-10-01/02 and has no ^KS11 | REFDATA |
| **T-CLOSE-01** M8 clause (L5588, L5617) | The workflow never starts before 06:40:30Z for the KRX decision of 2026-10-02 (06:40:29Z refused; 06:40:30Z starts) | injected clock; calendar from M1 | SYNTH |
| **T-RO-02** M8 clause (L5587, L5606) | I-01 runs with the HTTP transport patched to record every request; the recording shows zero non-allowlisted requests. Claude API called without tools; its text never parsed by an acting module | patch `data/net.py` transport; static check on `macro.brief` | SYNTH |
| **I-06c** M8 clause (L5595, L5696) | An acting-field schema error HALTs (OPS) the books the artifact describes; an out-of-schema context field never HALTs | corrupt one acting field / one context field of a built `macro_state` | SYNTH |
| **T-CARD-03** (M8; L5665) | A card file whose verdict is edited to PASS after its run is refused by `verdict_filter`: the factor stays in the specification book and VERDICT_INTEGRITY pages. A hand-edited `cards/verdicts.jsonl` row breaks the chain and blocks every admission until it is restored. A verdict whose `gate_package_md5` differs from the frozen package's, or whose `data_snapshot_id` does not reproduce from the store, is refused the same way | temp cards dir with a synthetic PASS card + chained rows; synthetic store; injected `harness_hashes_at` | SYNTH |
| **I-03** (M8; L5690) | The recommended book never reads a FORWARD-SIM multiplier, a refusal-book multiplier or a non-PASS factor (assertion on the book builder). It refuses R-04. No recommended or specification book reads the R-11 or R-12 multiplier | builder called with each forbidden read | SYNTH |
| **T-SCOPE-01** (M8; L5675) | The eight cases of B.4 | synthetic store, per-book runtime, synthetic NAV paths | SYNTH |
| **T-ROLE-02** M8 clause (L5581, L1969) | The S&P close failing on 3 decisions fails the R-28 and R-29 FORWARD-SIM books closed, sets `hedge_credit_off` through its corr63 binding, and HALTs no recommended book | as T-SCOPE-01 (b) | SYNTH |
| **T-OBS-01** (L5677) | Each HALT class writes the `runtime[].halt` block of its book and a governance event | one RISK and one OPS HALT | SYNTH |
| **T-OBS-02** (L5678) | A skipped scheduled run raises MISSED_DECISION (severity page) at the next app start, and the books carry their weights | run log with a gap; injected calendar/clock | SYNTH |
| **T-OBS-03** (L5679) | Page-severity alerts persist until acknowledged | alert store reloaded from disk | SYNTH |
| **T-OBS-04** (L5680) | An exception injected in **each** acting step writes status = error, raises RUN_ERROR (page), blocks engine_feed, adds 1 to the counter of every book the step serves and HALTs them (OPS, `run_error`) at the limit; the errored decision counts for MISSED_DECISION. An exception in `forward_monitor` is re-evaluated for every skipped decision at the next successful run | 7 parametrised injections + 1 for `forward_monitor` | SYNTH |
| **T-OBS-05** (L5681) | At app start the `governance_events.jsonl` hash chain is verified; a hand-edited row raises GOVERNANCE_LOG_BROKEN (page) | temp log, one byte edited | SYNTH |
| **T-REPLAY-01** (L5616) | Re-running a past decision from the store at its `knowledge_utc` reproduces the artifact byte for byte after canonicalisation (UTF-8 JSON, sorted keys, floats printed with repr, no insignificant whitespace), excluding only `generated_at_utc` and `git_hash`; runtime state restored first; `data_snapshot_id` order-invariant and unchanged when a later correction is appended | synthetic store with a later correction row; two consecutive decisions | SYNTH |
| **I-14** (L5704) | CARD-P demotion reads "forward ΔMDD vs S ≤ 0 = no protection"; all statistical triggers use whole-book NAV; on a 20-shift placebo panel the book-level false-demotion rate is ≤ the declared budget (default 10% a year; D4); an injected lag-audit violation, or an acting-parameter edit outside a revision, demotes immediately; no forward record can raise a card's verdict | seeded synthetic design sample (seed 11) | SYNTH |
| **T-DEMOTE-01** (L2744) | Trigger text reads "forward ΔMDD vs S ≤ 0 = no protection". A synthetic forward record with ΔMDD > 0 and ES protection never demotes | synthetic record | SYNTH |
| **T-DEMOTE-02** (L2745) | Every statistical trigger reads whole-book NAV. A card at 20% of the book with sleeve-level noise does not fire on the seeded fixture (seed 11). (EX1 reference: the 6-month 2% rule fires in 3.3% of 12-month records at 20% of NAV vs 31% at sleeve level — informative; `QX_EX1_demotion.csv` absent) | seeded synthetic book + sleeve | SYNTH (EX1 rates REFDATA) |
| **T-DEMOTE-03** (L2746) | On the 20-shift panel the book-level false-demotion rate is ≤ the declared budget (default 10% a year, D4); each card is ≤ its equal split | synthetic design sample ≥ 5,040 sessions, two cards | SYNTH |
| **T-DEMOTE-04** (L2747) | An injected lag-audit violation, or an acting-parameter edit outside a revision, demotes immediately, even with the budget unused; so does an operator kill of a card's forward books (its gap still excluded); 26 HALTED decisions of a card's books in 12 months trip §8.8 (b)'s 10% budget | synthetic record + rules-store edit history | SYNTH |
| **T-DEMOTE-05** (L2748) | No forward record can raise a card's verdict. An INSUFFICIENT card with 12 strong forward months stays INSUFFICIENT until new history adds an objective episode | synthetic record; raise attempt must raise | SYNTH |
| **I-12** (L5702) | Header declares monthly SMA10m, gross 0.5× below trend, `min()` composition, the claim and a pooled-onset rule, all before the run; a Korea instance is refused; runs FORWARD-SIM until a US sleeve exists | header fixtures | SYNTH |
| **I-12** numbers | stacked ΔMDD on VT ≥ 3 pp (+14.9 pp on the daily US VT15 book, 1991-2026; PX2); French monthly 1927-2026: PASS at 5 and 50 bp with 45 de-clustered onsets (G-TR-01); GJR-null percentile 87th | French monthly Mkt-RF + RF 1927-2026; daily US VT15 fixture (French daily Mkt-RF + ^GSPC Sep-2026); GJR-null paths | REFDATA |
| **T-TREND-01** (L3045) | A header missing any of SMA10m / 0.5× below trend / `min()` composition / the claim / the pooled-onset rule is refused | five header mutations | SYNTH |
| **T-TREND-02** (L3046) | Stacked ΔMDD on VT ≥ 3 pp (+14.9 pp, daily US VT15 1991-2026); DLB-T3a at Level-1: ΔSR +0.083 at 5 bp and +0.059 at 50 bp; ΔMDD +15.9 pp; tail 0.78; 9 of 10 episodes; 45 de-clustered onsets; PASS at 5 and 50 bp under the v1.2 checks; GJR-null percentile 87th (± 5); the v2 verdict is computed blind and printed; a difference from PASS is a disclosed flip, never tuned | as I-12 numbers; frozen package (M7) | REFDATA |
| **T-TREND-03** (L3047) | Registering the card for KR raises. The KOSPI trend state appears only in `context_log` | registration call; built artifacts scan | SYNTH |
| **T-TREND-04** (L3048) | Until a US sleeve exists (D5), the R-28 multiplier appears only in its FORWARD-SIM book and never in `engine_feed` | pipeline run, payload scan | SYNTH |
| **G-TR-01** (L5962) | US monthly 1927-2026, SMA10m 0.5×, cash = RF. 5 bp: ΔSR +0.083 [0.019, 0.134], p_ni 0.000, ΔMDD +15.9 pp (2×: +15.9), tail 0.78, 9/10 episodes (max 0.21), years 68%, onsets 73 raw / 45 de-clustered, plateau 1.0 → PASS. 50 bp: ΔSR +0.059 [−0.007, 0.113], ΔMDD +15.8 (+15.6) pp, 9/10 (0.22) → PASS. Cash 0: +0.078 / +15.2 pp (5 bp) and +0.055 / +15.0 (+14.8) pp (50 bp) → PASS | French monthly file; `QX_DLB_trend_cards.csv`; v1.2-check mode (M7) | REFDATA |
| **G-TR-02** (L5963) | Starts 1930 / 1940 / 1950 / 1960: ΔSR +0.081 / +0.052 / +0.063 / +0.058; ΔMDD +21.4 / +15.3 / +15.5 / +15.2 pp → PASS. Starts 1970 / 1980 / 1990 / 2000 / 2008: ΔMDD +15.3 / +15.8 / +15.8 / +15.2 / +16.2 pp, onsets 27 / 22 / 17 / 13 / 10 → INSUFFICIENT (sufficiency) | same | REFDATA |
| **G-TR-03** (L5964) | 94/94 variants (SMA 2-24 m, TS 1-24 m, 0.5× and 0×) ΔMDD ≥ 3 pp (median +16.4 pp); SMA10 ranks 33rd on ΔSR and 51st on ΔMDD; deflated ΔSR probability 0.99 (N 1), 0.59 (N̂ 30.7), 0.43 (N 94), 0.07 (N 7,846) | same + R-28 ledger seed (94 DLB-T3f variants) | REFDATA |
| **G-TR-04** (L5965) | Other indices (price, cash 0, 5 bp), ΔMDD vs S: S&P +17.5, Nikkei +4.2, HSI +8.0, DAX +14.0, FTSE +7.4, TAIEX +12.0, KOSDAQ +9.8 pp; each index alone 15-21 de-clustered onsets | six trend indices + KOSDAQ month-end closes | REFDATA |
| **G-TR-05** (L5966) | KOSPI daily 1998-2026, 3 bp (context only). Cash 0: ΔSR +0.070, ΔMDD +3.6 pp; tail 0.929 daily / 0.853 at 21 days; 17 de-clustered onsets → INSUFFICIENT. From 2016: −2.3 pp (tail 1.02) | Yahoo ^KS11 daily | REFDATA |
| **I-13** (L5703) | Registered once as a new card (one trial) with a Micro ES 5 bp book and a notional field; settling run PASS only if PC-1′ holds at 1× and 2× and the card passes at ≥ 8 of the 10 decade-spaced starts with no REJECT at any; recorded verdict = full-span v2 verdict; promoted only if that run passes and a US sleeve with notional ≥ ~₩1bn exists (D5); monthly and banded 50 bp variants logged as trials | injected sub-verdicts; temp ledger | SYNTH (logic); the real run REFDATA + OWNER |
| **T-USFUT-01** (L3135) | Registered once as a new card (one ledger trial), Micro ES 5 bp book and a notional field. A second registration under the same family with a 50 bp book raises (DNB #23) | temp rules store + ledger | SYNTH |
| **T-USFUT-02** (L3136) | PASS only if PC-1′ holds at 1× and 2× and the card passes at ≥ 80% of decade-spaced starts; a synthetic 70% share returns no PASS; a synthetic 9-of-10 result with one REJECT start returns no PASS | injected sub-verdicts | SYNTH (logic) |
| **T-USFUT-02** fixture clause / TASK-M8-11 | "On the 1926-07 → 2026-08 fixture the run returns PASS only if …" | French Data Library daily Mkt-RF and RF from 1926-07 (DL-A fetch: HTTP 403); licence, owner, md5 to be recorded; "a file without them is not a fixture" (L6035) | OWNER + REFDATA |
| **T-USFUT-03** (L3137) | The card stays FORWARD-SIM unless the settling run passes **and** a US sleeve with notional ≥ ~₩1bn (or a D5 line) exists | truth table over `promotion_ok` inputs | SYNTH |
| **T-USFUT-04** (L3138) | The monthly and banded 50 bp variants appear as ledger trials of the R-06 family and never as a revision of this card | temp ledger | SYNTH |
| **T-USFUT-05** (L3139) | DLA-U2 within Level-1 on fixture U1 (v1.2 checks): ΔMDD +3.6 pp (2×: +3.2), p_ni 0.002, 6 of 11 episodes (max 0.46), plateau 0.875; the 44 quarterly-start verdicts match G-US-F08 (11 PASS / 9 REVISE / 24 REJECT; 11 PASS = 1990-02 to 1992-05 and 2000-11; 9 REVISE = 1992-08 to 1994-08; 24 REJECT = 1994-11 to 2000-08), a start within tolerance of its threshold asserted as a class and the counts as the implied ranges | U1 = French daily Mkt-RF 1990-02 → 2026-08 + ^GSPC Sep-2026; v1.2-check mode | REFDATA |
| **T-REF-01** (L5652) | S1 is absent from the FORWARD-SIM re-gate queue (BL-S01 closed; BL-G04/BL-D13 at P3). Its card records REJECT (54 strict-H.10 onsets, ΔMDD −1.3 pp, tail 1.00) | rules store (`regate_queue: false`) + the archived refusal record | SYNTH (record is archived council evidence, labelled as not reproduced locally) |
| **T-REF-02** (L5653) | S2 is absent from the FORWARD-SIM queue (BL-S02 closed). Its card records REJECT with 71 onsets, including the compliant Treasury +1-business-day timing (ΔMDD −3.1 pp at 50 bp) and strict +2 days (−3.5 pp). G-US-02a reads "compliant via Treasury with logged posting time" | as T-REF-01 | SYNTH (same label) |
| **T-BASIS-01** S2 clause (M8; L5550, L5628) | S2 applied to momentum raises an error | call `refusal_rates_leg(…, applies_to="momentum")` | SYNTH |
| **G-KR-05** (L5776) | S1 KRW 0.75× (DEXKOUS, D ≤ K−1), value timing: ΔSR vs buy-and-hold +0.032 (0.967) / on VT20 +0.042 (0.977) / 9.0% of days; net KRX ETF 3 bp +0.029 (0.94) / +0.038 (0.96); KRX stock 35 bp −0.008 (0.32) / −0.007 (0.34); +0.025 / +0.034 at 6 bp; −0.048 / −0.057 at 70 bp; timing label **VALUE** | Yahoo ^KS11 2016-2026 + FRED DEXKOUS snapshot of 2026-10-02; research bootstrap (circular, 63-day blocks, 1,000 resamples, seed 20261002). Local `fred_DEXKOUS.csv` starts 2017-01-02 and ends 2026-09-18 — not the frozen fixture; ^KS11 absent | REFDATA |
| **G-KR-05s** (L5777) | S1 strict H.10: +0.001 (0.53) / on VT20 +0.013 (0.74) / 9.1% of days / 26 onsets (20-session); 3 bp −0.000 (0.49) / +0.012 (0.70); 35 bp −0.016 (0.22) / −0.007 (0.34); −0.002 / +0.010 at 6 bp; −0.034 / −0.027 at 70 bp; **COMPLIANT** | same + Fed publication calendar | REFDATA |
| **G-POST-01** M8 rows (L5577, L5830, L5840) | G-KR-05 KRW value timing share +0.032 (**0.967**) post-patch (0.965 pre-patch); "unchanged": G-KR-05s and G-KR-05 on VT20 | `QX_DLA_postpatch.csv`; as G-KR-05 | REFDATA |
| **G-REF-01** (L5875-5882) | R-11 refusal record (KOSPI 1997-04 → 2026-10, 0.75× on VT20), onsets de-clustered at 20 · ETF 3 bp ΔMDD / tail / ΔSR · stock 35 bp ΔMDD / ΔSR: Value 74 · −1.7 / 0.996 / −0.015 · −1.7 / −0.048; Strict H.10 54 · −1.3 / 1.004 / −0.022 · −1.4 / −0.036; Strict H.10 holiday-aware 54 · −1.3 / 1.004 / −0.027 · −1.5 / −0.041; Yahoo KRW=X lagged 2 sessions (2004+) 69 · +0.3 / 0.996 / −0.006 · −0.4 / −0.059; all REJECT | ^KS11 1997+, DEXKOUS 1997+, KRW=X 2004+ | REFDATA |
| **G-REF-02** (L5884-5891) | R-12 refusal record (US 1990-02 → 2026-09, 0.5× on VT15; 71 onsets at every timing, 39 + 32), 50 bp ΔMDD / ΔSR · 5 bp · gross · tail: Value (NON-COMPLIANT) −0.8 / −0.076 · +1.1 / +0.026 · +1.2 / +0.037 · 0.99; +1 bd via Treasury (COMPLIANT via Treasury) −3.1 / −0.105 · +0.1 / −0.002 · +0.3 / +0.009 · 0.99 (also PC-4 2/11); +2 bd strict H.15 (COMPLIANT) −3.5 / −0.120 · +0.8 / −0.019 · +0.9 / −0.007 · 0.995; ^TNX close of D (VALUE) −1.5 / −0.090 · +1.4 / +0.016 · +1.5 / +0.027 · 0.99; all REJECT | French Mkt-RF 1990-02 → 2026-08 + ^GSPC, DGS10, Treasury par yields with posting times, ^TNX | REFDATA |
| **G-US-02a** (L5790) | S2 at +1 business day: gross +0.010 (0.67), 1990-2007 −0.017; net 50 bp −0.093 (0.00); net 100 bp −0.196; label "COMPLIANT via the Treasury par-yield channel with a logged posting time; NON-COMPLIANT via H.15/FRED by 15 minutes" | as G-REF-02 | REFDATA (label string SYNTH via T-REF-02) |

Deferred clauses (§9.0b) that join their test at M8: T-FIX-01 / G-POST-01 "Row: G-KR-05 share. 'Unchanged' items: G-KR-05s and G-KR-05 on VT20" (L5577); T-ROLE-02 "fails the R-28 and R-29 FORWARD-SIM books closed … and HALTs no recommended book" (L5581); T-RO-02 "I-01 runs with the HTTP transport patched …" (L5587); T-CLOSE-01 "the workflow never starts before 06:40:30Z (§3.9)" (L5588); I-06c "an acting-field schema error HALTs (OPS) the books the artifact describes" (L5595); T-BASIS-01's S2 clause (L5550, L5559). M8 exit list (L5559, L6370): I-01, I-03, I-12, I-13, I-14, T-REF-01/02, T-REPLAY-01, T-SCOPE-01, T-OBS-01..05, T-CARD-03, T-DEMOTE-01..05, T-TREND-01..04, T-USFUT-01..05, T-BASIS-01 (S2 clause); G-KR-05/05s, G-TR-*, G-REF-*.

Tiers (L5496): the SYNTH rows are `fast`; the golden rows are `golden`; nothing here is `freeze`. Tests write only to temporary copies of the rules store, the ledgers and the artifact directory (T-HERM-02).

---

## E. Interfaces

### E.1 Needed from earlier milestones

| From | Names and shapes |
|---|---|
| M0 | schema registry + `validate(artifact) -> list[{path, message}]` (draft 2020-12; `jsonschema` is not installed today); artifact writer with canonical JSON and provenance (`git_hash`, `config_hash`, `data_snapshot_id`, `knowledge_utc`, `read_only: true`); `core/rules/governance.py::append_event`, `::verify_chain`; rules document with `cards.*`, `monitoring`, `refusal_books`, `sleeves`, `owner_decisions`; DNB shapes 22, 23/32, 35, 37; `config.macro_artifact_dir()`; the exposure-basis predicate (T-BASIS-01); `validate_card_header` (R-32) |
| M1 | `PITValue`, `MissingInput`, `pit_value(series_id, decision_utc, knowledge_utc, consumer, require_session)`, `data_snapshot_id(knowledge_utc)`, `is_stale`, `on_input_failure`, `contract`; registry bindings `(series, consumer, role, books, halt_after_consecutive_decisions)` with a hook for derived book lists; the lag-audit function; `close_print_bound_utc`, `decision_time_utc`, `usable_at`, `publication_instant`, session iteration (expected decisions, next session open), coverage; per-book runtime (book ids; DISARMED/ARMED/HALTED; input and book counters; `runtime_halt(book_id, cls, reason)`, `runtime_rearm(book_id, mode, operator=None)`; `halt.causes[]`); KIS endpoint allowlist; ingest retry + `fetch_log.jsonl`; an alert emitter |
| M2 | `market_vol_target`, `compose`, `hedge_state`; research bootstrap (circular, 63-day blocks, 1,000 resamples, seed 20261002) for G-KR-05 shares |
| M3 | `estimator_gate()` status |
| M4 | `sleeve_vol_scale`, `dm_gate`, `base_weights`, `apply_overlays`; the recommended/specification book builder (TASK-M4-07) into which `assert_book_separation` is inserted |
| M5 | RISK class, operator kill, heartbeat; `concentration_bound`, `drawdown_ladder`; one weight book per book id with whole-book NAV (TASK-M5-12: overlay-on/off and FORWARD-SIM simulated books), per-card switch counts; `simulate_fill`; `evaluator_block`; a single all-or-none `apply_target_weights(book_id, payload)` |
| M6 | `build_macro_state`, `build_overlay_decisions`, `build_context_log` (incl. the KOSPI trend-state item), event-calendar artifacts, the Macro page panel |
| M7 | frozen `gate.package = {version, definitions_md5, acceptance_report_md5, frozen_utc}` + manifest; committed card headers (`header_md5`, `first_registered_utc`, design-sample m̄); card files with `results_md5`; the `cards/verdicts.jsonl` appender (TASK-M7-19/20); archived snapshot rows per formal card; `overlay_card_eval`, `episodes`, `family_ledger` (+ append-trial), PC-1′ … PC-7, start-band and midpoint-half evaluation, the verdict function with caps, v1.2-check mode, GJR-null paths, `register_card` |

### E.2 Exposed to later milestones and the UI

| Name | Shape | Consumers |
|---|---|---|
| `run_pipeline`, `load_pipeline`, step/gate registries | B.1 | scheduler/app start; M10 sleeves (new markets register steps; "FORWARD-SIM first") |
| `read_run_log`, `missed_decisions` | rows of C.2 | Macro page, Runs page |
| alert store: `raise_alert(code, severity, component, *, series_id=None, books=()) -> dict`, `open_alerts() -> list[dict]`, `acknowledge(alert_id, by) -> None` | C.3 | Macro-page banner; every later module |
| `admissions(...) -> AdmissionResult`, `locked_out(family, market, utc) -> bool` | B.2(7), B.6 | builders, M9 displays, any later card |
| `assert_book_separation(book_id, reads)` | B.3 | every book builder incl. tech-fund sleeves |
| forward-book registration: `register_forward_book(book_id, card_id, kind)`; `forward_record(card_id) -> dict` (C.6); `monitoring_report() -> dict` | B.6 | M10 (R-17), tech-fund FORWARD-SIM cells FS-1 … FS-5 (R3 L828-836), weekly brief, card pages |
| `calibrate_alarms`, `cusum_monitor`, `false_demotion_rate`, `demote` | B.6.2 | card pages; any new card's header commit |
| `settling_run`, `settling_pass`, `promotion_ok` | B.8 | TASK-M8-11 once the 1926 fixture exists |
| `replay_decision` | B.5 | audits; M9 T-REPRO-01c style checks |
| `trend_axis`, `refusal_krw_leg`, `refusal_rates_leg`, `micro_es_contracts` | B.7-B.10 | forward evaluator, displays |

---

## F. Ambiguities, contradictions, conservative readings

| # | Issue | Lines | Conservative reading |
|---|---|---|---|
| F-1 | `verdict_filter` is listed **after** `build_artifacts` and `bounds_ok`, yet binding book lists (`data_ok`) and the artifacts' recommended-book values depend on admissions | L1220-1230 vs L1889, L3559, L3733 | Compute `admissions()` once at run start (pure); the gate entry re-verifies it on the built artifacts; a mismatch blocks `engine_feed` for that recommended book and pages `VERDICT_INTEGRITY` |
| F-2 | Workflow path `core/skills/workflows/macro_daily.yaml` collides with the module `core/skills/workflows.py`; L1192 claims such YAMLs exist there (they live in an external skills checkout) | L1189, L1192, L3481 | In-repo data-only directory (`core/skills/macro_workflows/`), separate strict loader; never the external repository; existing parser untouched |
| F-3 | "decision gates" = automatic `gate:` checks; the existing `decision_gate` is a human pause | L1189-1232 | No operator click is needed for the pipeline to complete; nothing a click does can raise exposure |
| F-4 | Repo is not a git repository; `git_hash` is required in run records and artifacts and integrity check (iii) needs "a commit whose harness sources hash to the package manifest's entries" | L1238, L3487, L3508 | Record an explicit sentinel (never a fabricated commit id); check (iii) fails ⇒ no factor can be admitted ⇒ everything stays in the specification book. Owner action: put the repo under git before any formal card run |
| F-5 | "All five artifacts" is not enumerated | L5688 | Read as the five §6.1-§6.5 schemas: `macro_state`, `overlay_decision`, `event_calendar`, `context_log`, `model_card(.macro)`; the test validates every artifact the run writes plus the cards it cites |
| F-6 | Refusal-leg function names: `fwd_krw_leg` / `fwd_rates_leg` vs `refusal_krw_leg` / `refusal_rates_leg` | L935-936 vs L1069-1070 | Use `refusal_*` (§3.5 and TASK-M8-12/13) |
| F-7 | What the R-28 FORWARD-SIM book is: "the specification book × the trend multiplier" vs "incremental on R-29's futures vt book"; no US book exists while D5 = none | L2975, L3006 vs L2988, L888 | `forward_sim:R-28` = `vt_US` (R-29) × `min(1, trend)` on S&P official closes at the `CME_micro_ES` cost class; weights only; no contracts while `notional_nav` is null |
| F-8 | R-28 `rebalance: monthly` on a book whose `vt` changes daily | L3026 vs L3083-3084 | The trend multiplier changes only at month-end decisions and is carried between them; `composed` is recomputed at each daily decision |
| F-9 | "every book the step serves" for `run_error` counters is undefined; FORWARD-SIM books have no acting-input counters and "never HALT" on input or NAV failures | L1242-1244, L1178, L1181 | Served books = `recommended:<market>` and `specification:<market>`. Forward/refusal books mark the decision failed-closed and count it toward the 10% budget; they are not HALTed by `run_error` |
| F-10 | "the books the artifact describes" for an acting-field failure | L1224, L3370 | The market `macro_state` / `overlay_decision` describe `recommended:<m>` and `specification:<m>`; a forward book's own artifact describes that forward book only |
| F-11 | `sleeves.US.notional_nav: null`; "A header without `notional_nav` is refused"; a forward record starts only after the header commit; card books arm only with a committed header | L4463, L3127, L5310, L1180 | Until the owner supplies the notional (and M7 commits headers): no R-28/R-29 forward record, books stay DISARMED, the rule state is displayed only (`macro_state.forward_sim`), `contracts` = null. Never invent a notional |
| F-12 | "A later run for the same decision is a replay" — also when the earlier run errored? | L1199-1200, L1247 | Yes: once any artifact exists for the decision (a `fail_closed` one included) a later run is `replay` (audit only). The errored decision stays counted for MISSED_DECISION; books carry their weights |
| F-13 | A `late` run: forward books carry weights; nothing is said for recommended/specification books | L5311 | No `engine_feed` on a late run (no exposure change); artifact display-only |
| F-14 | Scheduler semantics; app closed at the close; `retries_min: [1, 5, 15, 60]` with `decision_deadline: next_session_open_minus_30min` implies hours of waiting | L1194, L4201 | Never block the UI thread; one attempt per invocation, re-invoked by a process-singleton timer; a decision with no row is MISSED_DECISION (page); missed decisions do not increment HALT counters (only errored runs do) |
| F-15 | Baseline of "the calendar's expected decisions" before the first ever run | L1246-1247 | Expected decisions start after the first `run_log.jsonl` row of that market; an empty log raises nothing |
| F-16 | OS notification and e-mail sinks unspecified; Flet 0.85.2 has no notification API | L1248-1249 | Banner + persisted store are mandatory; OS notification best-effort with a labelled degradation; e-mail not built |
| F-17 | Alert severity for a single fail-closed input is not given | L1204, L1868 | `warn` for a fail-closed component; `page` for every HALT, RUN_ERROR, MISSED_DECISION, VERDICT_INTEGRITY, GOVERNANCE_LOG_BROKEN |
| F-18 | 20-shift panel: "20 evenly spaced offsets (≥ 252 sessions apart …)" gives no grid; what is shifted is not stated | L2692 | Placebo = the card's multiplier path circularly shifted against the returns, on/S books rebuilt. `n = 20 if T ≥ 5,040 else ⌊T/252⌋`; `τ_k = round((k + ½)·T/n)`, `k = 0…n−1` (spacing ≥ 252, never 0 or T). Default, judgment; print `n` |
| F-19 | CUSUM `d_m` ("monthly paired differences") and the whole-book paired series are not defined | L2688, L2671 | `d_m` = monthly return of whole-book NAV with the card on minus the same book with the comparator (S for CARD-P, off for CARD-O) substituted = Σ over the month of `w_card × (r_on − r_cmp)`; attribution printed |
| F-20 | "> 10% of a card's scheduled decisions in any rolling 12 months": denominator for a record younger than 12 months | L2677, L5311, L2747 | Denominator = the market's scheduled decisions in the trailing 12 calendar months (≈ 250, consistent with "26 HALTED decisions" in T-DEMOTE-04); numerator = flagged decisions since record start in that window; strict `>` |
| F-21 | Switch-count trigger: counting window not stated | L2678 | Fit on design-sample 12-month switch counts; compare the trailing-12-month forward count; trigger iff count > p99 |
| F-22 | Demotion verdict for a card that is not PASS (e.g. operational trigger on an INSUFFICIENT or NOT_RUN FORWARD-SIM card ⇒ REVISE could read as a raise); the rule itself is "default, judgment; council to confirm" | L2700, L2696, L5464 | A forward record changes a verdict only downward: PASS → REVISE/REJECT; any → REJECT on a catastrophic/CUSUM trigger; otherwise the verdict is left as is and the alarm, lockout and revision requirement are recorded |
| F-23 | "Active cards" (budget split) excludes FORWARD-SIM cards, yet their forward record "is a falsification alarm" | L2691, L3007, L3097 | FORWARD-SIM cards get calibrated thresholds and printed alarms under a split computed as if active (book total still ≤ D4); with zero active cards no split is allocated and the book total prints 0 |
| F-24 | No `governance_event.kind` for a `git_hash` / `config_hash` change between forward decisions (closed enum) | L5312 vs L4104-4105 | Use `kind: "book_state"` with `key` = `"git_hash"` or `"config_hash"`, plus `old`/`new`; do not extend the enum without the coordinator |
| F-25 | "the card's acting-code manifest" is not defined | L5312 | Manifest = md5 of the source files of the functions the card's factor calls, listed per card at header commit; a change outside a registered revision ⇒ operational demotion |
| F-26 | Verdict and status tokens appear in two spellings: "INSUFFICIENT DATA" vs `INSUFFICIENT_DATA`; "BUILD NOW" / "BUILD-AS-INSURANCE" vs `BUILD_NOW` / `BUILD_AS_INSURANCE`; `FORWARD_SIM`; `SPECIFICATION_BOOK` | L3759, L4089, L3023, L4461 | Underscore tokens in data (schema enums); prose forms only in display strings |
| F-27 | Does `INVARIANT_STEP` need authentication ("each verdict is authenticated first" vs "needs no PASS")? | L1230, L3768 | Require the committed R-31 header to verify (header md5) and its frozen binding share ≤ 0.10; KR is ≈ 19% ⇒ not admitted today |
| F-28 | T-SCOPE-01 says "failing on 3 consecutive decisions" while the HALT limit is 2 | L5675 vs L1870 | HALT at the 2nd failed decision; the test asserts the state after 3 |
| F-29 | GOVERNANCE_LOG_BROKEN: only a page is specified | L1250, L5681 | Page; no new admission or derived-binding change while unacknowledged; nothing is demoted and no book is HALTed (no exposure change) |
| F-30 | T-REF-01/02 "its card records REJECT (…)" and "re-gate queue" — the queue object and BL ids live only in the backlog document; the numbers cannot be recomputed here | L5652-5653, L1644 | Ship the refusal record as an archived council record with `source: "DL-A; not reproduced on this machine"`; queue = `refusal_books.*.regate_queue: false`; the G-REF goldens stay REFDATA skips |
| F-31 | R-11/R-12 production inputs (ECOS 15:30 / snapshot; KIS US 10y quote) have no provider or credentials here | L1646, L1659 | Flag = null, input labelled missing; never substitute DEXKOUS or DGS10 in `run_mode = live` |
| F-32 | `settling_run` "returns no PASS": the returned verdict when a condition fails is not named | L3089-3091, L3136 | Return the full-span verdict after the M7 caps and stability floor; expose `settling_pass: bool`; tests assert `!= "PASS"` |
| F-33 | Tech-fund FS-1 "KOSPI floored trend × VT20" as a FORWARD-SIM CARD-P vs "A Korea instance is refused" and DNB item 37 | R3 L257-262, L832 vs L3003, L6224-6227 | Never register a KR instance of R-28 (T-TREND-03 stays binding). If FS-1 is built it is a separate tech-fund card id, FORWARD-SIM only, never acting, composed by `min()`; owner/coordinator decides |
| F-34 | Tech-fund GOV-10 "prospective incubation (FORWARD-SIM ≥ 252 sessions from 2026-10-01) as the clean out-of-sample test"; OQ-11 statistical review triggers | R3 L317, L821, L1324 vs L5310, L5318, L6219-6222 | A forward record starts at the first live decision after the header commit (no backfill to 2026-10-01), never counts toward sufficiency and never raises a verdict; OQ-11 is not adopted (R-25 governs) |
| F-35 | R-28 de-clustering "at the rule's own lookback (10 months)": algorithm not spelled out | L2993 | Keep an onset (flag 0→1) only if ≥ 10 months after the previous kept onset |
| F-36 | Hard-stop and caps inside forward card books | L5314, L2348 | Excluded (R-22 rule 6); a hard stop of a recommended book is never a demotion trigger |

---

## G. DO-NOT-BUILD items and invariants binding this area

- **Item 21 / P0**: no order, cancel, withdrawal, deposit-address or transfer path, no broker adapter. `engine_feed` reaches only the simulated order book; KIS = allowlisted quotation endpoints; every artifact `read_only: true`; no artifact contains an order instruction (L3511).
- **Item 22 / P7**: never offer a non-PASS card's output as a recommendation; never let a FORWARD-SIM multiplier reach the recommended book. Includes R-28 and R-29 until their build conditions hold; R-04; a ladder step binding on > 10% of days before its CARD-P passes; R-11 or R-12 in any book other than its display-only refusal book (L6163-6167).
- **Items 23 and 32**: no lowering of a pre-registered cost, no instrument-book/venue switch after results; an instrument-book change is a new card; `MACRO-R06-US-FUT` is a new card, not a revision of the 50 bp card; monthly and banded 50 bp variants are logged trials, never rescues; the US 50 bp card keeps "REJECT (instrument: US shares via KIS, 50 bp, daily)" and is never re-run.
- **Item 31 / P2**: composition is `vt × min(…)`, never a product; no multiplier above 1.0; overlays ∈ [0.5, 1.0]; `0.75` and `0.5` compose to `0.5`, never `0.375`.
- **Item 35 / P14**: a forward record is never validation; it can demote, never raise; an INSUFFICIENT Korea card has no forward-record route; the US futures card is settled on 1926+ history, not forward months. Rules-store shape `forward_record_cited_as_validation: 35`.
- **Item 37**: no acting KOSPI trend card; `markets_refused: [KR]`; KOSPI trend state is context only; no pooled or horizon-matched rescue (also item 34).
- **Items 19 and 26**: no value-timed, provisional or bar-derived acting input; DEXKOUS/DGS10 as-if-same-day are never production inputs; G-KR-05 is labelled VALUE, G-US-02 NON-COMPLIANT.
- **Item 17**: the 200-day conjunction on the vol target stays prohibited; R-28 is a different object (stand-alone, pre-registered CARD-P composed by `min()`); BAND200 is a logged trial only.
- **Per-book HALT (C-1, P16, P18)**: only an `acting_exposure` input bound to a book can HALT that book; risk-model, context, forward_sim, history inputs and `hedge_state` exceptions never HALT; a HALT never applies to "the engine"; the operator engine's `EngineState` is not touched.
- **Fail closed**: missing/stale/provisional/synthetic acting input ⇒ state carried, `fail_closed = true`, alert, no interpolation; an acting-step error blocks `engine_feed` for the whole run; a missing 1926 fixture keeps R-29 FORWARD-SIM (never the 1990 file); a missing month-end close leaves the R-28 multiplier unchanged.
- **Forward-record integrity**: never backfilled; replays are audits only; append-only; alarm state reset only with a new revision; gaps excluded from both sides; S uses the header's design-sample m̄.
- **Budget discipline**: thresholds and split fixed at record start, never recalibrated when cards are added; the owner may only tighten D4; a bull-market lag alone never demotes; demoting a CARD-P never removes risk-layer invariants.
- **Hermetic tests**: no network (T-HERM-01), temp copies only (T-HERM-02), no invented golden values — an absent fixture is a labelled skip.
- **Claude API**: computed numbers only, no tools, output never parsed by an acting module; the brief works with no key.
- **Tech-fund programme**: its FORWARD-SIM cells live "in the third (forward) book, never in the displayed book" (R3 L128) — same isolation rule; its DNB-TF list adds nothing specific to this area; XS-01 … XS-22 change no workflow, run-log, alert or forward-monitor rule.
