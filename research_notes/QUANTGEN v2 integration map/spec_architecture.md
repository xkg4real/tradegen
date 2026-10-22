# spec_architecture — implementation brief (Macro Integration Spec v2.0, sections 2 and 3)

Source: `QUANTGEN_Quant_Council_2026-10-03/claude_code/QUANTGEN_MACRO_INTEGRATION.md` (6,479 lines).
Read in full: L660-746 (section 2), L747-1267 (section 3). Looked up by citation: section 9 rows (L5489-5706), 9.0a/9.0b (L5544-5597), section 7 keys (L4123-4411, L4662-4705), section 6.1/6.2/6.6 fields (L3508-3651, L3717-3771, L4094-4119), R-02 (L1499-1508), R-19 rules 4-5 (L1866-1889), R-31 names (L3271-3302), R-35 (L3479-3497), P0/P2/P7/P8/P16-P19 (L491-518, L556-571, L636-656), section 10.3 (L6229-6252), section 12 (L6356-6372), Quick start (L14-99).
Existing code skimmed: `core/ficc/macro.py`, `core/quant/risk.py`, `core/quant/signals.py`, `core/engine/runtime.py`, `core/skills/workflows.py`, plus signatures of `core/calendars.py`, `core/markets.py`, `core/engine/{state,evaluator,orders,feed}.py`, `core/ficc/data.py`, `core/quant/{optimize,backtest,validate,strategies,garch,gjr}.py`, `core/rules/*.py`, `config.py`, `tests/run_all.py`.

Notation: `L123` = spec line. `[E]` = existing file. `[N]` = new file (proposed; spec L963 allows renaming: "binding in semantics ... Rename them to match the codebase if necessary. Every location is proposed unless the comment says exists"). "Binding vs informative" (L89): field names, parameters, bounds, formulas, test thresholds are binding; paths and function names marked proposed may be renamed; where the file is silent: "no exposure change, specification book only, fail closed".

---

## A. Scope

### A.1 What this area is

Section 2 is the decision record (KEEP / MODIFY / DROP / BACKLOG / FORWARD-SIM / BUILD-AS-INSURANCE / RETIRED) against the prior design. Section 3 is the architecture: module map, daily data flow, exposure composition (binding), core interfaces (binding in semantics), macro-sheet and signal-composite reconciliation, engine mapping (per-book runtime, HALT classes, re-arm), the `macro_daily` workflow, and the no-broker statement. There is no task file for this brief; the table below lists the tasks of `QUANTGEN_V2_TASKS.json` whose `spec_sections` cite section 3.

### A.2 Task table (tasks that cite section 3)

| Task | One-line deliverable | Target files ([E] existing, [N] proposed) |
|---|---|---|
| TASK-M0-01 | Static read-only scan: no order/cancel/withdrawal/deposit-address/transfer call, no order-client import, incl. skill scripts and workflow YAML commands (T-RO-01; 3.10) | [N] `tests/macro_acceptance.py`; [E] `tests/run_all.py` (register) |
| TASK-M0-07 | Hash-chained `governance_events.jsonl` appender (6.6; 3.8; 3.9 alert sinks) | [N] `core/rules/governance.py`; file under macro artifact dir |
| TASK-M0-10 | Acting vs display field classes; quarantine path `<artifact_dir>/quarantine/` (3.9 `bounds_ok`) | [N] `core/ficc/macro_artifacts.py`; [E] `config.py` (+`macro_artifact_dir()`) |
| TASK-M1-02 | Runtime read-only guard on KIS client; Claude API never decides (3.9) | [E] `config.py` (frozen allowlist), KIS client under `data/` |
| TASK-M1-03 | `decision_time_utc`, `close_print_bound_utc` (3.5 core/calendars) | [E] `core/calendars.py` (+functions); [N] effective-dated data files |
| TASK-M1-07 | Append-only bitemporal PIT store, pinned `knowledge_utc`, `RunContext`, `data_snapshot_id` (3.5; 3.9 `pit_snapshot`) | [N] `core/ficc/pit.py` |
| TASK-M1-10 | `pit_value()` with provisional-row guard and consumer bindings (3.5) | [N] `core/ficc/pit.py` |
| TASK-M1-12 | `ficc_cache` never serves pre-close rows to acting reads (3.9 `pit_snapshot`) | [E] `core/ficc/data.py` (`_cache_get/_cache_put`), [N] `core/ficc/pit.py` |
| TASK-M1-16 | `expected_available_utc`, `is_stale`, `pit_last` (3.5) | [N] `core/ficc/contracts.py` |
| TASK-M1-17 | Role-based failure actions, counters, admission-derived bindings; status-code map (3.5; 3.8 never-HALT list) | [N] `core/ficc/contracts.py`; [N] `core/engine/books.py` |
| TASK-M1-19 | Independent lag audit (3.9 `macro.lag_audit`) | [N] `core/ficc/contracts.py` (or `lag_audit.py`) |
| TASK-M1-20 | Minimal per-book runtime: book ids, DISARMED/ARMED/HALTED, OPS HALT + automatic re-arm (3.8; 3.5 engine hooks) | [N] `core/engine/books.py`; [E] `core/engine/state.py` untouched (see F-2) |
| TASK-M1-21 | ECOS and Treasury par-yield providers (3.4 module map) | [E] `core/ficc/data.py` or [N] provider module; OWNER data |
| TASK-M2-01 | `sma_vol`, `market_vol_target()` with per-book warm-up (3.5) | [E] `core/quant/risk.py` (+functions) |
| TASK-M2-03 | `compose()` and `apply_overlays()` by `min()`, 0.5 x vt floor (3.3) | [E] `core/quant/risk.py`, [E] `core/quant/signals.py`, [N] `core/rules/macro_rules.py` (`combine != min` refused) |
| TASK-M2-04 | `hedge_state()` date-aligned corr63 (3.6 risk-model inputs) | [E] `core/quant/risk.py` |
| TASK-M4-01 | Map six composite components to families (BL-G07; 3.7) | [E] `core/quant/signals.py`; rules store family mapping; OWNER |
| TASK-M4-02 | Family tags + exposure basis wiring (3.7; 3.3) | [E] `core/quant/signals.py`, [E] `core/quant/risk.py` |
| TASK-M4-03 | `sleeve_vol_scale()` revisions 1-3 (3.3; 3.5) | [E] `core/quant/risk.py` |
| TASK-M4-06 | `inverse_vol_weights`, `base_weights` (3.3 base weights) | [E] `core/quant/optimize.py`, [E] `core/quant/signals.py` |
| TASK-M4-07 | Recommended / specification book builders (3.3 books) | [N] `core/engine/books.py` (builder) + [E] `core/quant/signals.py` (`composite_weights`) + [E] `core/quant/risk.py` (`risk_layer`) |
| TASK-M5-02 | `concentration_bound()` (3.3 concentration bound) | [E] `core/quant/risk.py` |
| TASK-M5-03 | RISK class: hard stop, automatic re-arm, post-re-arm cap (3.8 re-arm row, NAV valuation) | [N] `core/engine/books.py`; [E] `core/quant/risk.py` |
| TASK-M5-04 | Remaining OPS triggers: heartbeat, NAV, coverage, operator kill (3.8) | [N] `core/engine/books.py`; [E] `core/engine/feed.py` (heartbeat signal) |
| TASK-M5-05 | `drawdown_ladder()` (3.8 ladder steps) | [E] `core/quant/risk.py`; [E] `core/engine/evaluator.py` |
| TASK-M5-06 | Evaluator BLOCKED decisions for new entries (3.8; 3.5) | [E] `core/engine/evaluator.py` (+`Outcome.BLOCKED`, `evaluator_block`, `evaluator_annotate`) |
| TASK-M5-10 | Simulated fill model R-27 (3.8 execution row) | [E] `core/engine/orders.py` (+`simulated_fill`) |
| TASK-M5-12 | Run the simulated books, persist state, enforce no reallocation (3.8; 3.3 T-MONO-01) | [N] `core/engine/books.py` |
| TASK-M6-01 | Reconcile 18-indicator sheet + regime read (3.6; BL-G06; P19) | [E] `core/ficc/macro.py`, [E] `ui/macro_page.py` |
| TASK-M6-03 | Context isolation: static import check + runtime guard (3.5 interface rules) | [N] `tests/macro_acceptance.py`; guard in [N] `core/ficc/context_log.py` |
| TASK-M6-05 | `build_macro_state()`, `build_overlay_decisions()` (3.2) | [N] `core/ficc/macro_artifacts.py` |
| TASK-M6-06 | Macro page panel + brief `macro_state` section (3.1 UI box; 3.6 rule 4) | [E] `ui/macro_page.py`, [E] `core/ficc/macro.py` (`daily_brief`/`weekly_brief`) |
| TASK-M8-01 | `macro_daily` workflow with decision gates (3.9; 3.2) | [N] `core/skills/macro_daily.py` + [N] `core/skills/macro_daily.yaml` (see F-1) |
| TASK-M8-04 | Per-book HALT scope end to end (3.8 scope C-1) | tests + [N] `core/engine/books.py` |
| TASK-M8-05 | Atomic `engine_feed` per book (3.9 `run_record`) | [N] `core/skills/macro_daily.py`, [N] `core/engine/books.py` |
| TASK-M8-06 | Run records, missed-decision detection, alert sinks, log verification (3.9) | [N] `core/skills/macro_daily.py`; `run_log.jsonl`; [E] `ui/macro_page.py` banner |

### A.3 Package-by-package placement (existing file vs new file)

Facts about the repo that drive this table: `core/calendars`, `core/markets`, `core/ficc/data`, `core/ficc/macro`, `core/quant/risk`, `core/quant/signals`, `core/quant/optimize`, `core/quant/backtest`, `core/skills/workflows` are single `.py` modules, not packages. `core/rules` and `core/engine` are packages. The existing nine-step gate is in `core/quant/validate.py` (`GATE`, `DECISIONS = ("PASS","REVISE","REJECT","INSUFFICIENT_DATA")`, `ModelCard`, `md5_of`) and the costed engine is `core/quant/strategies.simulate`; `core/quant/backtest.py` is a 155-line three-strategy backtest, not the gate.

| Spec package (L965-1102, L923-959) | Existing file | Extend in place | New file (proposed) |
|---|---|---|---|
| `core/ficc/data` (R-01, R-19) | `core/ficc/data.py` [E] (`Series`, `load_many`, `_cache_get/_cache_put`, `synthetic_series`; `auto` degrades to SYNTHETIC) | ingest hook that appends fetched rows to the PIT store; cache becomes read-through of the store (L796) | `core/ficc/pit.py` [N]: `PITValue`, `MissingInput`, `RunContext`, store, `pit_value`, `data_snapshot_id`, `pit_last`. `core/ficc/contracts.py` [N]: registry loader, `contract`, `expected_available_utc`, `is_stale`, `on_input_failure`, `usable_cross_market`, `add_publication_bdays`, lag audit. Data: `data/macro/series_registry.yaml` [N] |
| `core/calendars` (R-20, R-10, R-17) | `core/calendars.py` [E] (`is_trading_day`, `special_session`, `coverage`, `stale_markets`; JSON in `data/calendars/<VENUE>.json`, coverage 2026-01-01..2027-12-31 only) | `decision_time_utc`, `close_print_bound_utc`, `usable_at`, `regime_tags`, `gap_sessions`, `is_session`, `session`, `fed_business_day`, `sifma_status`, `nyse_holiday`, `publication_instant`, `next_expected_obs`; event store | Data: `data/macro/calendars/*.yaml` [N] (KR effective-dated closes, `kr_regime_tags.yaml`, `source_skipped.yaml`, FED/SIFMA sets), `data/macro/event_calendar.json` [N]. Not `data/calendars/*.json` (that glob is loaded as market calendars, `calendars.py:100`) |
| `core/markets` | `core/markets.py` [E] (venue codes KRX, US, TSE, ...) | market-id to venue map (KR->KRX, US->US, JP->TSE, CN->SSE, HK->HKEX, TW->TWSE) | — |
| `core/quant/risk` (R-02, R-03, R-06, R-07, R-09, R-31) | `core/quant/risk.py` [E] (`RiskReport`, `analyze_history` on log returns, `BasketStats`) | `sma_vol`, `ewma_vol`, `market_vol_target`, `sleeve_vol_scale`, `hedge_state`, `lookthrough_exposure`, `concentration_bound`, `drawdown_ladder`, `compose`, `risk_layer`, display labels | `core/quant/refusal.py` [N]: `refusal_krw_leg`, `refusal_rates_leg` (kept out of `risk.py` so the I-03 / T-CTX-01 static check can be module-level) |
| `core/quant/signals` (R-02, R-04, R-05, R-15) | `core/quant/signals.py` [E] (`SignalComponent`, `compute_signals`: per-symbol score in [-100, +100]) | `family` tag on `SignalComponent`; `base_weights`, `dm_gate`, `apply_overlays`, `composite_weights` | — |
| `core/quant/optimize` | `core/quant/optimize.py` [E] (`optimize_portfolio`, objectives incl. `risk_parity`) | `inverse_vol_weights` | — |
| `core/ficc/macro` (R-13, R-18, R-32) | `core/ficc/macro.py` [E] (`INDICATORS` x18, `MacroRow`, `Regime`, `macro_sheet`, `daily_brief`, `weekly_brief`) | `daily_brief`/`weekly_brief` gain a `macro_state` section; regime-read relabel (F-9) | `core/ficc/context_log.py` [N]: `build_context_log`, `log_break`, runtime isolation guard. `core/ficc/macro_artifacts.py` [N]: `build_macro_state`, `build_overlay_decisions`, validator / `bounds_ok`, artifact writer, quarantine. Schemas: `core/ficc/schemas/*.v2.0.json` [N]. Keep acting-artifact types out of `macro.py` so engine/risk never import the sheet |
| `core/engine` (R-07, R-08, R-10, R-27) | `runtime.py`, `state.py`, `evaluator.py`, `orders.py`, `feed.py` [E] (one global `EngineState`, manual re-arm only; `Outcome` = fired/skipped/rejected/halted; rule-triggered `OrderBook`) | `evaluator.py`: `Outcome.BLOCKED`, `evaluator_block`, `evaluator_annotate`. `orders.py`: `simulated_fill` | `core/engine/books.py` [N]: per-book runtime (`runtime_halt`, `runtime_rearm`), counters, NAV, weight books, persistence. Existing `EngineState`/`EngineRuntime` stay as they are (F-2) |
| `core/rules` (section 7, 7.1, R-33) | `model.py`, `store.py`, `validation.py` [E] (operator price-trigger `Rule`; `RuleStore` JSON at `config.trading_dir()`) | — | `core/rules/macro_rules.py` [N]: section 7 config loader, section 7.1 rule objects, DO-NOT-BUILD predicates, owner-decision registry + `{ref}` resolver. `core/rules/governance.py` [N]: appender. Data: `data/macro/rules_v2.0.0.json` [N] (F-3) |
| `core/quant/backtest` (gate package, R-21..R-25, R-34) | `core/quant/backtest.py` [E] (toy), `core/quant/validate.py` [E] (the gate), `core/quant/strategies.py` [E] (costed `simulate`) | reuse `validate.sharpe`, `lo_se`, `block_bootstrap_ci`, `sharpe_diff_bootstrap`, `deflated_sharpe`, `pbo_cscv`, `newey_west_t`, `kupiec`, `christoffersen`, `pit_tests`, `ModelCard`, `md5_of`; `strategies.simulate` | gate-package module(s) [N] per the gate briefs (`overlay_card_eval`, `episodes`, `family_ledger`, `n_eff`, `timing_profile`, `power_line`, `gate_acceptance_test`, `forward_monitor`) |
| `core/quant/garch` (R-30, R-16) | `garch.py`, `gjr.py`, `montecarlo.py` [E] | — | estimator gate module [N] (`estimator_gate`) per the estimator brief |
| `core/skills` (R-35) | `workflows.py` [E] parses `<config.skills_root()>/workflows/*.yaml` in the external trading-skills repo; `runner.py` runs skills as subprocess scripts | — | `core/skills/macro_daily.py` [N] (in-process pipeline + gates), `core/skills/macro_daily.yaml` [N] (F-1) |
| `config.py` | [E] credentials, `trading_dir()` (`~/.nextgen/trading`), `ficc_cache_dir()` (`~/.nextgen/ficc_cache`, TTL 6 h) | `macro_artifact_dir()` (L797, L4126), KIS endpoint allowlist | — |
| UI | `ui/macro_page.py` [E] | macro_state panel, overlay_decision table, verdict/disposition badges, rel/abs vol labels, event calendar, context log, owner decisions (L761-763) | — |
| docs | `docs/asset_expansion_study.py` [E] (pattern: one JSON card per model) | — | `docs/macro_overlay_study.py` [N], `docs/vol_backtest.py` [N] |
| tests | `tests/run_all.py` [E] (imports `tests()` from each suite) | register `macro/` suite | `tests/macro_acceptance.py` [N], `tests/fixtures/macro/` [N], `tests/reference/` [N] |

---

## B. Build spec

### B.0 Section 2 decision record (what the code must and must not contain)

Decision codes (L665-672): KEEP unchanged; MODIFY changed as stated; DROP never build (section 10); BACKLOG not built; FORWARD-SIM (v1.0 SHADOW) "runs forward in the specification book as a card; never a recommendation until re-gated"; BUILD-AS-INSURANCE "built in the recommended book as labelled insurance, only on a formal CARD-P PASS"; RETIRED "a REJECT recorded on long history; kept only as a labelled, display-only refusal book". v2.0 note (L662): the 0-3 integers of section 2.2 and R-15 are "admissibility filters and display scores, not weights".

| Prior element (L) | Decision | What v2.0 builds |
|---|---|---|
| Directional signal layer (L683) | KEEP | families are tagged components of the existing composite (3.7) |
| XS momentum 12-1 + 5-day reversal KR+US (L684) | MODIFY | US 12-1 only with own-vol scaling + D&M gate; Korea 12-7 / residual variant (UNVERIFIED) and 1-5-day reversal; all tests net of KRX stock cost 35 bp per side (covers the 0.20% sell tax); 2x stress 70 bp |
| Vol to sizing (L685) | KEEP, strengthened | weight = min(1.0, target/sigma_hat); cap 1.0 permanent; SMA20 displayed baseline; Korea vol target BUILD-AS-INSURANCE on a formal PASS (expected INSUFFICIENT DATA, so not expected to build) |
| Per-market x per-family weight table (L686) | KEEP -> MODIFY | priors are admissibility filters; base_weight(m, f) = IV_m x 1/K_m over admissible families, inverse-vol across markets |
| Regime-multiplier hook (L687) | MODIFY | bounds [0.5, 1.0]; exposure basis declared; clipping logged; overlays and ladder compose by `min()`, never by product |
| Falsification pipeline (L688) | MODIFY -> nine-step gate | every rule is a model card; CARD-P class; KRX stock 35 bp per side = 70 bp round trip; 2x stress; gate v2 adopted once and blind |
| US XS momentum weight 3 (L694) | MODIFY | 2 if vol-scaled with D&M gate (1 if unscaled) |
| Japan XS momentum 0 (L695) | KEEP 0 | may rise to 1 if own vol-scaled card passes |
| Europe / EM / APxJ XS momentum 3 (L696) | KEEP (prior only) | — |
| Korea XS momentum 1 (L697) | MODIFY | 12-1 -> 0; 12-7 / residual -> 1 (UNVERIFIED) |
| Korea reversal 3, flow 3 (L698) | KEEP; v2.0 reversal prior 3 -> 1 (UNVERIFIED until BL-U02) | no flow-conditioned multiplier |
| TS momentum per index (L699) | MODIFY | KOSPI 2->1; KOSDAQ->0; STOXX50 0, DAX 1, FTSE 0-1; Japan 1-2; Taiwan 1-2; China A 0; India 1; US 3; crypto 2 with BTC own vol cap |
| "Vol scaling helps every strategy" (L700) | MODIFY | robust only for momentum; index vol targeting is risk control |
| Volume-spike reversal (L701) | KEEP as signal spec; UNTESTED | not built as an overlay |
| Value-momentum hedge universal (L702) | MODIFY | measure on own sleeves |
| Published Sharpe as priors (L703) | MODIFY | haircuts value -49%, momentum -23%, carry about -25%, defensive 0, multifactor -18%; `live_sharpe_multiplier: 0.60` reported on every card with the Harvey-Liu haircut |
| Real 10y momentum cut (L709); curve re-steepening gross cut (L710); HY OAS quality tilt (L713); PMI value tilt (L714); Fed liquidity crypto scaling (L715); VIX term-structure switch (L712) | DROP | context log only; R-08 is an execution-state annotation that changes no weight; `max(sigma_hat, implied)` retired |
| Broad USD beta scaling (L711) | MODIFY | context + hedge-validity state (R-09); DTWEXBGS context; labelled live USD proxy feeds `hedge_state`, never HALTs |
| Overlay range 0.5-1.5 / 0-1 (L716) | MODIFY | [0.5, 1.0] for both; 0x only from the risk layer (backtest) or HALTED (simulated book) |
| US ISM/2y tilts (L722); Japan BoJ tilts (L724); Korea SOX 60-day gate (L725); Korea flow weight up (L727); Taiwan semis gate (L728); India Brent gate (L730); crypto net liquidity (L732) | DROP | SOX(t-1) is an opening-gap input only; flows logged from day one |
| Europe BTP-Bund/TTF (L723); China gates (L729); EM USD-trend gate (L731); crypto funding rate (L732) | BACKLOG | not built |
| Korea USD/KRW 20-day > +3% gross cut (L726) | RETIRED | R-11 refusal book only (REJECT on 1997-2026; 54 strict-H.10 onsets; dMDD -1.3 pp; tail-exposure ratio 1.00) |
| Four-state regime (L738); SOX x KRW scalar (L743); 24 h event blackout (L740) | DROP | short intraday windows (R-10) as evaluator blocks on simulated entries |
| Market gross from two local drivers (L739) | MODIFY | own vol target (cap 1.0) composed by `min()` with the ladder; both legs retired (R-06, R-11, R-12) |
| 1,000-path bootstrap falsification (L741) | MODIFY | nine-step gate (2,000 x 10-session blocks) + protective class; longer of 10 sessions and Politis-White length |
| Data sources (L742) | MODIFY | CBOE via FRED VIXCLS/VXVCLS; production USD/KRW = timestamped 15:30:00 KST snapshot (`USDKRW_1530_SNAPSHOT`) or ECOS 15:30 close; KIS US 10y quote in production; strict backtests lag DGS10 by two business days; Treasury par yields +1 business day with logged posting time |

### B.1 Daily data flow (3.2, L805-848) — one decision per market per close

Order of operations for a decision at the official close of session t of market m:

1. `decision_utc = close_print_bound_utc(m, t)` = scheduled close + 30 s. KRX 15:30 KST: 06:30:30Z from 2016-08-01; 06:00:30Z before; CSAT close + 30 s; before 2015-06-15 scheduled close + the 30 s print tolerance. NYSE 16:00 ET = 20:00Z EDT / 21:00Z EST, + 30 s (L806-809).
2. `core/ficc` PIT snapshot at `decision_utc`, `knowledge_utc` pinned for the run; `value_status` / session check; staleness by role (R-19; `data_ok` gate); lag audit (independent re-derivation of `usable_at`) (L812-813).
3. Failure routing (L814-816): acting input missing / stale / provisional / synthetic -> "its component fails closed (state carried, alert); repeated failure HALTs only the books the input is bound to"; risk_model input stale or failing -> `hedge_credit_off = TRUE` (never HALTED); context input stale -> label.
4. `core/ficc/macro` `context_log` (never acts; isolation guard) -> Macro page, weekly brief (L818).
5. `core/quant/risk`: sigma_hat (SMA20), `vt(m)`, `sleeve_vol_scale` vs, `hedge_state`, look-through caps, ladder state, `compose()`: `vt x min(1.0, overlays, ladder, post_rearm_cap) >= 0.5 x vt` (L820-821).
6. `core/quant/signals`: base weights (R-15), family overlays, exposure basis (`apply_overlays`); `core/quant/optimize`: `inverse_vol_weights` (IV_m); covariance inputs honour `hedge_credit_off` (L823-824).
7. `core/ficc/macro`: build `macro_state`, `overlay_decision` (each factor tagged with its card verdict and disposition); `bounds_ok` then validates the built artifacts (L827-828).
8. `core/calendars`: event windows, KR opening-gap nights, multi-session gap tags (L829).
9. `core/engine` evaluator: BLOCKED new entries for R-10 windows and the ladder -12% step; R-08 writes an annotation only. Orders: simulated order book, recommended and specification books; fills per R-27, "priced at the official close of t, earning from t+1, costed per P10 (tick floor applied)" (L832-834).
10. Runtime, one state per book: DISARMED | ARMED | HALTED (0x for that book only) (L836-840).
11. Forward evaluator (`core/quant/backtest` + `core/engine/state`): FORWARD-SIM books (R-28, R-29), refusal books (R-11, R-12; display only), forward alarms on whole-book NAV (R-25) (L842-843).
12. `docs/macro_overlay_study.py` + gate -> model cards (frozen gate package) -> Strategy Lab (L845).

### B.2 Exposure composition (3.3, L850-897) — BINDING (R-02; QC resolution 6)

For market m, family f, instrument i, decided at the close of t (`decision_utc`), effective from t+1. Verbatim formula block (L856-879):

```
# base weights (R-15)                                      core/rules + core/quant/optimize [+]
IV_m               = inverse-vol weight of market m on weekly returns
                     (EWMA λ 0.97 acting; a Ledoit–Wolf 156-week line printed); Σ_m IV_m = 1
A_m                = { f : prior(m,f) ≥ 1  and  card(m,f).verdict ≠ REJECT }      # admissible families
base_weight(m,f)   = IV_m × 1/|A_m|  if f ∈ A_m, else 0                          # Σ_f base_weight(m,f) = IV_m
                   # R-15: a range prior resolves to its lower bound; a family with no registered prior is not
                   # admissible; ts_trend is admissible in the recommended book only on its own PASS (R-14)

# family level (exposure_basis = active)                   core/quant/signals [+]
active_budget(m,f) = base_weight(m,f)
                   × vs(m,f)                               # own-vol scale, in [0,1] (R-03; momentum only, else 1.0)
                   × min(1.0, family_overlay_1(m,f), …)    # each in [0.5,1]; empty = 1.0 (R-04: specification book only)

# market level (exposure_basis = total)                    core/quant/risk [+]
composed(m)        = vt(m)                                 # market vol target, in [0,1] (R-06)
                   × min(1.0, gross_overlay_1(m), …, ladder(m), post_rearm_cap(m))   # each in [0.5,1]; ladder, post_rearm_cap ∈ {1.0, 0.5} (R-07, R-31)
gross(m)           = min(composed(m), concentration_bound(m))     # look-through limit (R-07); a risk limit, not an overlay
# HALTED (a RISK or OPS trigger of this book, §3.8) sets this book to 0×; it is never an argument of min(); other books continue

target_weights     = composite_weights(i | active_budget, gross)               # core/quant/signals
final_weights      = risk_layer(target_weights)              # caps, single-name active cap; hedge_state (risk model only)
simulated_orders   = engine.orders(final_weights)            # recommended and specification books (§3.8)
```

Order of operations (must be this order, per book):

| # | Step | Range / rule | Where |
|---|---|---|---|
| 1 | `IV_m` | weekly returns, EWMA lambda 0.97 acting; Ledoit-Wolf 156-week line printed; sum_m IV_m = 1 | `optimize.inverse_vol_weights` |
| 2 | `A_m` | prior(m,f) >= 1 and card(m,f).verdict != REJECT; range prior -> lower bound; no registered prior -> not admissible; ts_trend admissible in the recommended book only on its own PASS | rules store + `signals.base_weights` |
| 3 | `base_weight(m,f)` | IV_m x 1/|A_m| if f in A_m else 0; sum_f = IV_m | `signals.base_weights` |
| 4 | `active_budget(m,f)` | base_weight x vs(m,f) in [0,1] x min(1.0, family overlays each in [0.5,1]); empty list = 1.0 | `signals.apply_overlays` |
| 5 | `composed(m)` | vt(m) in [0,1] x min(1.0, gross overlays in [0.5,1], ladder in {1.0,0.5}, post_rearm_cap in {1.0,0.5}) | `risk.compose` |
| 6 | `gross(m)` | min(composed(m), concentration_bound(m)); may go below 0.5 x vt without a bounds failure | `risk.concentration_bound` |
| 7 | HALTED override | that book 0x; never an argument of `min()` | `engine/books` |
| 8 | `target_weights` | `composite_weights(i | active_budget, gross)` | `signals.composite_weights` |
| 9 | `final_weights` | `risk_layer(target_weights)`: caps, single-name active cap; never renormalises | `risk.risk_layer` |
| 10 | `simulated_orders` | recommended and specification books only | `engine/books` -> simulated order book |

Per-book factor selection (L885-890; R-31 L3302):

| Book | vt | overlays | ladder | post_rearm_cap |
|---|---|---|---|---|
| `recommended:<m>` | `VT.weight` only if R-06(m) card verdict PASS (disposition `BUILD_AS_INSURANCE`), else 1.0 | only factors whose card is PASS (`RECOMMENDATION` CARD-O or `BUILD_AS_INSURANCE` CARD-P); every other factor enters as 1.0 | `step_mult` only if disposition `INVARIANT_STEP` (binding share <= 0.10) or R-31 PASS, else 1.0 | that book's runtime (invariant) |
| `specification:<m>` | `VT.weight` | every BUILD NOW factor whatever its verdict, labelled; includes R-04 at floor 0.5 | `step_mult` (also while binding share > 10%) | that book's runtime |
| `forward_sim:<rule>` | specification book + that card's factor on the card's declared instrument book and notional | | | |
| `refusal:<rule>` | display only; "No recommended or specification book reads their multipliers (I-03)" | | | |

Invariants always applied in every book: point-in-time data, bounds, look-through caps, the hard stop, the hedge state (L886). State on 2026-10-02 (L886, L896, L3685-3686): `recommended:KR` composed 1.0, gross 0.685, binding_factor `active_single_name`; `specification:KR` composed 0.694, gross 0.685, binding_factor `active_single_name`. Absolute single-name bound 22.5 / 29.8 = 0.755; active single-name bound 0.05 / (0.298 - 0.225) = 0.685 (upper bound; the risk layer computes b-tilde on the day's basket).

Invariant T-CAP-02 (L881): "For any overlay vector in [0.5, 1]^k, ladder step in {1.0, 0.5} and post-re-arm cap in {1.0, 0.5}, composed(m) = vt(m) x min(1.0, overlays, ladder, post_rearm_cap), and composed(m) >= 0.5 x vt(m) on every non-HALTED day (written as a product, so vt = 0 needs no division). The floor applies to composed(m): a concentration bound or risk-layer cap may take gross(m) lower without a bounds failure. A product-composed path raises: `bounds_ok` recomputes composed(m) from the recorded factors, and the rules store refuses `combine != min`."

Invariant T-MONO-01, no reallocation (L883): lowering any multiplier (vt, vs, an overlay, the ladder, the post-re-arm cap, a concentration bound) never raises gross(m'), active_budget(m', f') or the active risk of any other market or family, and never raises gross(m) or active_budget(m, f) itself. `composite_weights` and `risk_layer` "never renormalise freed budget across families or markets: freed active budget moves toward the benchmark (long-only) or zero (long/short), and freed total exposure moves to cash." One documented exception: R-15 admissibility: a family-card REJECT shrinks K_m and raises the other families' base weights by K/(K-1) from the next decision; "logged as a governance event and printed".

Notes on the formula (L892-897):
- Active budget: scaling a long-only sleeve moves weights toward the benchmark, not cash; long/short moves toward zero. For a long-only momentum sleeve, vs is computed on the paper unit-gross long/short series and applied to the active budget (R-03).
- `vt(m)` scales the market's long book. It does not scale long/short factor sleeves (own `vs(m,f)`), nor the TS-trend sleeve (vol-scaled per asset, exempt from overlays, R-14).
- Instrument book: Korea `vt(m)` on the KRX ETF line (KODEX 200, 3 bp, tick floor applied). KOSPI200 futures line allowed only where one mini contract (about KRW 56m) is <= ~5% of declared notional. "A stock book is never used as a market-gross scalar (R-26)". The card declares its book before it is run.
- Concentration bound on the ETF line: g <= limit_k / look-through share_k (R-07).
- Binding is logged: whenever `min()` or a limit binds, the binding factor is recorded in `overlay_decision.reasons` (and `binding[]`); each card prints the binding share of every factor.
- Stack card (L890; R-02 (6) L1506): once two or more de-risk factors act in the recommended book, the book is gated as one stack CARD-P (8.7); prints the share of days at <= 0.25x total exposure and the rebound capture. De-risk factor = market-level (`exposure_basis = total`) factor carried by a card that can take a value < 1.0 in the recommended book: vt (R-06 KR), R-28, R-29, R-31 steps once their card PASSes. Invariants (look-through caps, hard stop, post-re-arm cap, `INVARIANT_STEP` steps) and family-level vs are not de-risk factors. Several factors passing in one batch join in header-commit order.

Reference implementation (the whole of `compose`; everything else is bookkeeping):

```python
def compose(vt, overlays, ladder, post_rearm_cap):
    if not 0.0 <= vt <= 1.0: raise BoundsError("vt")                      # R-02 (1)
    if any(not 0.5 <= o <= 1.0 for o in overlays): raise BoundsError("overlay")
    if ladder not in (1.0, 0.5) or post_rearm_cap not in (1.0, 0.5): raise BoundsError("ladder/cap")
    return vt * min([1.0] + list(overlays) + [ladder, post_rearm_cap])    # L1058

def check_composed(recorded, vt, overlays, ladder, post_rearm_cap):       # used by bounds_ok (L1222-1223)
    if recorded != compose(vt, overlays, ladder, post_rearm_cap): raise ProductComposedError
```

Config keys read (L4272-4280): `overlay.floor: 0.5`, `overlay.cap: 1.0`, `overlay.combine: min`, `overlay.floor_vs_vt_outside_halted: 0.5`, `overlay.zero_only_in: [risk_layer, book_HALTED]`, `overlay.books: [recommended, specification, forward_sim_per_card, refusal_display_only]`, `overlay.recommended_dispositions: [RECOMMENDATION, BUILD_AS_INSURANCE, INVARIANT_STEP]`, `overlay.stack_card: {when_de_risk_factors_ge: 2, class: CARD-P, spec: "§8.7"}`. Any exception inside `compose` is an OPS HALT trigger for the books it feeds (L1178, T-MISS-02).

### B.3 Core interfaces (3.5) — verbatim (L965-1102)

```python
# core/ficc/data  (exists; these types and functions proposed)  — R-01, R-19
@dataclass(frozen=True)
class PITValue:
    series_id: str
    value: float
    obs_date: date                    # market or local date the value refers to (monthly series: first day of the month, §4.1)
    session_date: date | None         # exchange session the value belongs to (required for close-type inputs)
    obs_utc: datetime                 # when the observation was made (e.g. the scheduled close)
    obs_kind: Literal["close", "quote_snapshot", "release", "bar", "derived"]   # "close-type" means obs_kind == "close"
    value_status: Literal["official_close", "vendor_close", "live_snapshot", "provisional_intraday", "first_release",
                          "revised", "vendor_derived", "vendor_derived_across_gap"]
    dispute: bool                     # True: official value used, two-source mismatch alerted (R-01 (3)); never a failure
    available_at_utc: datetime        # when the market or publisher released it
    available_at_source: Literal["published", "calendar_bound", "inferred_from_retrieval"]
    retrieved_at_utc: datetime        # when QUANTGEN first saw it (knowledge clock; first-seen, §4.1)
    vintage: date | None              # FRED/ALFRED realtime_start of this value; None for unrevised market prices
    source: str                       # provider: KIS, KRX, FRED, ALFRED, Treasury, ECOS, Yahoo, FMP
    channel: str | None               # e.g. "H.15", "Treasury par yield", "ECOS 731Y003/0000003", "KIS live"
    provider_mode: Literal["explicit", "auto"]
    synthetic: bool                   # True is never accepted for an acting input -> MissingInput
    content_hash: str                 # md5 of the record; feeds data_snapshot_id
    role: Literal["acting_exposure", "forward_sim", "risk_model", "context", "history"]   # of the calling consumer's binding (§4.2, R-19 rule 5)
    books: tuple[str, ...]            # the books that binding feeds: the HALT scope (§3.8)

@dataclass(frozen=True)
class MissingInput:
    series_id: str
    reason: Literal["missing", "stale", "provisional_intraday", "session_mismatch",
                    "synthetic_rejected"]          # "disputed" and "warmup" are statuses of a used value, never failures
    role: Literal["acting_exposure", "forward_sim", "risk_model", "context", "history"]
    books: tuple[str, ...]

def pit_value(series_id: str, decision_utc: datetime, knowledge_utc: datetime, consumer: str,
              require_session: date | None = None) -> PITValue | MissingInput
#   as-of read of an append-only store: only records with available_at_utc <= decision_utc and
#   retrieved_at_utc <= knowledge_utc are visible; corrections are new rows. knowledge_utc is pinned once per run and
#   never defaults to "now" (run_mode live: the end of the pit_snapshot fetches; backtest: the card's data snapshot;
#   replay: the artifact's knowledge_utc); it is written to every artifact. consumer selects the binding (role, books).
#   Among the visible rows of one (series_id, obs_date): the highest value_status rank (official_close > revised >
#   first_release > vendor_close > vendor_derived > vendor_derived_across_gap > live_snapshot > provisional_intraday), then registry source
#   precedence, then the latest available_at_utc, then the latest retrieved_at_utc.
#   A close-type acting read returns MissingInput("provisional_intraday") unless value_status == "official_close"
#   (any other status), and MissingInput("session_mismatch") unless session_date == require_session (T-PROV-01).
#   A close-type read selects among the visible rows with obs_date == require_session: none visible -> MissingInput("missing")
#   (T-PROV-01 at 10:31 KST, even when the previous session's close is visible); session_mismatch means the selected row
#   carries another session_date (a mis-dated row).
#   require_session is mandatory for close-type acting reads (calling without it raises). A backtest may read
#   vendor_close rows only when its card header declares that vendor as data.source (§4.1).
def data_snapshot_id(knowledge_utc: datetime) -> str    # md5 of the sorted content hashes visible at knowledge_utc
def expected_available_utc(series_id: str, last_obs: date) -> datetime   # R-19 step 3: when the NEXT observation after
                                                        # last_obs is due = publication_instant(series, next_expected_obs(series,
                                                        # last_obs)); never the availability of last_obs itself
def is_stale(series_id: str, decision_utc: datetime, knowledge_utc: datetime) -> StaleCheck   # Fresh | Stale("missing") | Stale("missed_release")
#   stale iff decision_utc > stale_deadline_utc = expected_available_utc(series, last_obs) + grace (one publication
#   business day): the due time of the next observation, never the age of last_obs (R-19 step 3 is normative)
# further R-19 functions: contract, on_input_failure, usable_cross_market, pit_last, add_publication_bdays

# core/calendars (exists; these functions proposed)  — R-20, R-10, R-17
def decision_time_utc(market: str, session_date: date) -> datetime   # the scheduled official close, NOT decision_utc (that is
                                                                      # close_print_bound_utc); API unchanged from v1.2: KR 06:00Z before
                                                                      # 2016-08-01, 06:30Z after; CSAT close per calendar (07:30Z from
                                                                      # 2016-08-01); US 20:00Z / 21:00Z, early closes 13:00 ET (17:00Z
                                                                      # EDT / 18:00Z EST); CRYPTO 00:00:00Z of d+1 (R-17)
def close_print_bound_utc(market: str, session_date: date) -> datetime   # scheduled close + print bound: KR from 2015-06-15
                                                                      # + 30 s (06:00:30Z to 2016-07-29, 06:30:30Z after, CSAT close + 30 s);
                                                                      # KR before 2015-06-15 + the 30 s print tolerance; US + 30 s
                                                                      # (calendars.US.close_print_bound_s); JP, CN, HK, TW + their
                                                                      # calendars.<m>.close_print_bound_s (0 s default); the decision instant
                                                                      # (macro_state.decision_utc) and the lag-audit instant
# further calendar functions (is_session, session, fed_business_day, sifma_status, nyse_holiday,
# publication_instant, next_expected_obs): R-20. Market identifiers are the §6.1 enum (KR, US, JP, …, CRYPTO, FX);
# venue codes (KRX, NYSE, TSE) are used only inside core/markets.
def usable_at(series_id: str, obs_date: date, market: str) -> datetime  # first decision_utc that may use it (§4.1)
def regime_tags(market: str, d: date) -> dict          # price_limit, saturday_session, close_time, random_end,
                                                        # short_ban, fx_regime, sell_tax, lunch_break (R-20)
def gap_sessions(market: str, session_date: date) -> int   # n_US >= 0: US sessions since the previous KRX close (R-10)

# core/quant/risk (exists: risk.py; these functions proposed)
def market_vol_target(market: str, decision_utc: datetime, estimator: str = "sma20") -> VTResult
#   sigma_ann, weight in [0,1] (cap 1.0 permanent), display_label_rel, display_label_abs, inputs, status (R-06):
#   fewer than 20 valid returns -> status "insufficient_history"; each book it feeds maps that to "warmup", weight 1.0, before the
#   book's first ARMED decision and to MissingInput("missing") afterwards (T-VT-01); sigma 0 or not finite -> MissingInput
def sleeve_vol_scale(market: str, family: str, decision_utc: datetime, revision: int) -> VSResult
#   sigma126 on the paper unit-gross long/short series; revision selects fixed / scale-free / variance-scaled (R-03);
#   fewer than 126 valid observations -> "insufficient_history", mapped per book as above (vs = 1.0 "warmup", then MissingInput)
def hedge_state(decision_utc: datetime) -> HedgeState  # hedge_credit_off, hedge_failure, classic_risk_off,
                                                       # fx_hedge_credit (display only), stale inputs (R-09)
def lookthrough_exposure(book: Book, decision_utc: datetime) -> Exposure   # daily ETF baskets; L/I ETFs at × L (R-07)
def concentration_bound(market: str, decision_utc: datetime, template: str) -> ConcentrationBound   # {absolute_bound, active_bound, aggregate_bound, semis_bound, bound = their min, binding_factor}; per book: gross = min(composed, bound), binding_factor 'none' when composed <= bound (R-07)
def drawdown_ladder(nav_path, decision_utc: datetime) -> LadderState
#   LadderState{hwm_hard, ref_step, step_mult in {1.0, 0.5}, dwell_left, block_new_entries: bool, halted: bool,
#               rearm_not_before, post_rearm_left, binding_share}  (R-07, R-31; R-31's names are binding)
def compose(vt: float, overlays: list[float], ladder: float, post_rearm_cap: float) -> float   # vt * min([1.0] + overlays + [ladder, post_rearm_cap]); raises on product

# core/quant/signals (exists; these functions proposed)
def base_weights(decision_utc: datetime) -> dict[tuple[str, str], float]   # IV_m * 1/K_m over admissible families (R-15)
def dm_gate(market: str, decision_utc: datetime) -> Multiplier             # value in {0.5, 1.0}; specification book only (R-04)
def apply_overlays(composite, multipliers, basis) -> Weights               # bounds P2, min() composition, basis P8, binding log

# core/quant/optimize (exists; this function proposed)
def inverse_vol_weights(markets: list[str], decision_utc: datetime, cov: str = "ewma_weekly_0.97") -> dict[str, float]

# refusal books (core/quant/risk; proposed). Display only; no other book may read them (I-03)
def refusal_krw_leg(decision_utc: datetime) -> Multiplier     # R-11; value in {0.75, 1.0}; status="REFUSAL"
def refusal_rates_leg(decision_utc: datetime) -> Multiplier   # R-12; value in {0.5, 1.0};  status="REFUSAL"

# core/ficc/macro (exists; these builders proposed)
def build_macro_state(market: str, decision_utc: datetime) -> dict      # validates against macro_state 2.0
def build_overlay_decisions(market: str, decision_utc: datetime) -> list[dict]
def build_context_log(decision_utc: datetime) -> dict                   # items carry vintage and retrieved_at_utc
def log_break(event: BreakEvent) -> None                                 # R-18 break log (research log, never read by acting code)

# core/engine (exists; these hooks proposed)
def evaluator_block(rule_id: str, decision: Decision, state: MacroState) -> Decision   # → BLOCKED(reason), new entries only
def evaluator_annotate(rule_id: str, state: MacroState) -> Annotation                  # R-08: annotation + KIS snapshot request
def runtime_halt(book_id: str, cls: Literal["RISK", "OPS"], reason: str) -> None   # → HALTED for that book only; idempotent per cause; a new cause joins halt.causes[]
                                                   # while HALTED (never extends rearm_not_before, never resets a reference);
                                                   # logged as a governance event (§3.8)
def runtime_rearm(book_id: str, mode: Literal["auto", "operator"], operator: str | None = None) -> None
                                                   # RISK: auto at the decision after the 10-session refusal, references reset,
                                                   # 0.5× inside min() for 10 sessions; OPS: when the cause clears, no reset, no cap
def simulated_fill(order: SimOrder, venue: str, session_date: date) -> SimFill          # R-27 fill model

# core/quant/backtest (exists; these functions proposed) — the v2 gate package (§8)
def overlay_card_eval(card: CardHeader, ledger: FamilyLedger) -> CardResult  # on/off books, comparator S, v2 checks
def episodes(market: str, rule: str = "bear_bull_own_closes", threshold: float = 0.20) -> list[Episode]  # R-22
def family_ledger(family_id: str) -> FamilyLedger      # every configuration ever run, with timing class; ledger_hash
def n_eff(ledger: FamilyLedger, draws: int = 200_000, seed: int = 11) -> NResult   # max(N_clusters, N_equiv) (R-23)
def timing_profile(card: CardHeader) -> TimingProfile  # L in {-1, 0, 1, 2, 3} + publication-strict; the L <= 0 rows run
                                                       # only in the timing_probe sandbox (R-34)
def power_line(card: CardHeader) -> PowerLine          # SE ladder, MDE80, power (R-24)
def gate_acceptance_test(package_version: str) -> AcceptanceResult   # run once; results md5-frozen (R-21)
def forward_monitor(card_id: str, book_nav) -> list[Alarm]           # whole-book NAV; calibrated alarms (R-25)

# core/quant/garch + core/quant/backtest (forecast evaluation; proposed) — R-30
def estimator_gate(market: str, instrument_book: str, horizon: int = 21) -> EstimatorSelection
```

Rules every interface must follow (L1104-1113, binding):

1. Every function takes `decision_utc` and the run's pinned `knowledge_utc` "as parameters or in one `RunContext{decision_utc, knowledge_utc, run_mode}`, never 'now'", and reads data only through `pit_value` with `consumer` = the binding's `consumer` key in `data_contracts.roles`: a rule id such as 'R-06', or a named component such as 'corr63' (R-09), 'korea_covariance', 'nav', 'nav_fx' or 'R-28_R-29'. An entry without a `consumer` key binds every consumer of the series; a bare book kind in `books` means that kind's book in the series' market. One exception: R-34's `timing_probe` sandbox.
2. "No function reads a raw DataFrame of a series directly. The lag audit enforces this."
3. Failure by role (R-19):
   - acting input: return the previous state with the component's `fail_closed = true` and the input's status code, raise an alert, never interpolate.
   - Status map `MissingInput.reason` -> `macro_state.inputs[].status`: `missing` -> `missing`; `stale` -> `stale_missed_release`; `provisional_intraday` -> `provisional_rejected`; `session_mismatch` -> `session_mismatch`; `synthetic_rejected` -> `synthetic_rejected`. R-19 `Stale("missing")` -> `missing`; `Stale("missed_release")` -> `stale_missed_release`. Same map for risk_model and forward_sim inputs; a stale context input is `stale`. "Only these statuses count as failures".
   - risk-model input: `hedge_state` returns `hedge_credit_off = TRUE`; so does an exception inside `hedge_state` (never HALTED).
   - context input: labelled "stale" (status `stale`, value shown).
4. Warm-up and disputes are not failures. Warm-up returns the factor's neutral value (1.0) with status `warmup` "only while the book has never been ARMED"; on a book that has been ARMED, fewer valid observations than the factor's minimum is `MissingInput("missing")`, a failure, "so a store loss or a truncated history never resets a de-risk factor to 1.0". A disputed official close returns the official value with `dispute = true` and status `disputed`. Neither increments a consecutive-failure counter.
5. "No function in this list may import an order-submission client (T-RO-01)."
6. "No acting function may read `context_log`, the R-18 break log or a refusal book (T-CTX-01, I-03)."

Type catalogue (names used in 3.5 without a field list in section 3; fields from the comments above or the cited rule):

| Type | Fields named in the spec | Defined by |
|---|---|---|
| `RunContext` | `decision_utc`, `knowledge_utc`, `run_mode` (`live | backtest | replay`) | L1105, L1196 |
| `StaleCheck` | `Fresh | Stale("missing") | Stale("missed_release")` | L1018 |
| `VTResult` | `sigma_ann`, `weight` in [0,1], `display_label_rel`, `display_label_abs`, `inputs`, `status` (`insufficient_history` at function level; per book `ok | warmup | fail_closed` in `macro_state.vol.vt_status`) | L1044-1047, L3555 |
| `VSResult` | sigma126, vs in [0,1], status as above; `revision` 1 fixed target 0.12, 2 `expanding_median_sigma126` (min_obs 252), 3 `min(1, (0.12/sigma126)^2)` | L1048-1050, L4318-4320 |
| `HedgeState` | `hedge_credit_off`, `hedge_failure`, `classic_risk_off`, `fx_hedge_credit` (display only), stale inputs; `hedge_reasons` in {`ok`,`risk_model_input_stale`,`risk_model_exception`,`corr_positive`,`core_pce_ge_3`} | L1051-1052, L3572 |
| `ConcentrationBound` | `absolute_bound`, `active_bound`, `aggregate_bound`, `semis_bound`, `bound` = their min, `binding_factor` in {`none`,`absolute_single_name`,`active_single_name`,`aggregate`,`semis`} | L1054, L3603 |
| `LadderState` | `hwm_hard`, `ref_step`, `step_mult` in {1.0, 0.5}, `dwell_left`, `block_new_entries: bool`, `halted: bool`, `rearm_not_before`, `post_rearm_left`, `binding_share` | L1056-1057 |
| `Multiplier` | `value`, `status` (e.g. `"REFUSAL"`); artifact form `{rule_id, value, exposure_basis, card}` | L1062, L1069, L3735 |
| `Exposure`, `Book`, `Weights`, `BreakEvent`, `MacroState`, `Annotation`, `SimOrder`, `SimFill` | not specified in section 3 | R-07, R-18, 6.1, R-08, R-27 briefs |
| `CardHeader`, `FamilyLedger`, `CardResult`, `Episode`, `NResult`, `TimingProfile`, `PowerLine`, `AcceptanceResult`, `Alarm`, `EstimatorSelection` | not specified in section 3 | section 8, R-21..R-25, R-30, R-34 briefs |

### B.4 Module notes (what section 3 binds per package)

**core/ficc (PIT, R-01/R-19).** v2 adds (L906): `available_at`, `retrieved_at`, `value_status`, `session_date`, vintages and first prints; append-only as-of reads; provisional-row guard; two-source close reconciliation; lag audit; "no synthetic degrade for acting inputs". Existing `load_many(..., source="auto")` degrades to SYNTHETIC: allowed only for context consumers (labelled); for an acting consumer it must yield `MissingInput(reason="synthetic_rejected")` (T-SYN-01). `ficc_cache` (6 h) becomes a read-through cache of the PIT store (L796). New providers proposed: BoK ECOS 731Y003 (USD/KRW 15:30 KST close), US Treasury par yields with logged posting time, KRX/KOFIA leverage data (L794-795, L905). Config read: `data.store`, `data.knowledge_utc: {pinned_once_per_run: true, defaults_to_now: false, written_to_every_artifact: true}`, `data.run_mode.values: [live, backtest, replay]`, `data.value_status_rank`, `data.value_status_required_for_close_inputs: official_close`, `data.require_session_match: true`, `data.reject_rows_retrieved_before_close_plus_minutes: 10`, `data.synthetic_for_acting_inputs: forbidden`, `data.interpolate: false`, `data.fail_closed_on_missing_acting_input: true` (L4195-4216).

**core/calendars (R-20, R-10).** `decision_time_utc` returns the scheduled close; the decision instant is `close_print_bound_utc` (L1024-1034). Market ids are the 6.1 enum `["KR","US","JP","EU","TW","CN","HK","IN","EM","CRYPTO","FX"]` (L3729); venue codes only inside `core/markets`. Config: `calendars.KR.close_kst: [{to: "2016-07-31", time: "15:00"}, {from: "2016-08-01", time: "15:30"}]`, `calendars.KR.random_end: [{to: "2015-06-14", kind: conditional, print_tolerance_s: 30, ...}, {from: "2015-06-15", kind: unconditional, max_s: 30}]`, `calendars.US: {close_et: "16:00", early_close_et: "13:00", holiday_set: NYSE, tz: America/New_York, close_print_bound_s: 30}`, `calendars.JP ... close_print_bound_s: 0` (also CN, HK, TW), `calendars.coverage: {min_sessions_ahead: 60, warn_at_sessions_left: 60, page_at_sessions_left: 20, outside_coverage: OPS_HALT}` (L4174-4194). `time.decision: close_t_earn_t_plus_1`, `time.decision_instant: close_print_bound_utc` (L4155-4157).

**core/quant/risk.** `market_vol_target`: SMA20, cap 1.0 permanent, no floor; `vol_target.KR: {estimator: sma, window: 20, target_ann: 0.20, cap: 1.0, cap_permanent: true, exposure_basis: total, instrument_book: KRX_ETF_line, ... rebalance: daily, no_trade_band: 0.0, fill_model: KRX_close_auction}`; `vol_target.US: {... target_ann: 0.15 ...}`; `vol_target.sigma: {returns: simple, ddof: 1, mean_adjusted: true, stale_carry_days: excluded_window_extends}`; `vol_target.annualisation_days: 252`; `vol_target.warmup: {min_valid_returns: 20, value: 1.0, status: warmup, counts_as_failure: false, only_before_first_armed_decision: true, after_armed: MissingInput, degenerate_sigma: MissingInput}`; `vol_target.display_labels: {rel: {method: trailing_756_quartiles}, abs: {method: expanding_full_history_quartiles, min_years: 10}, values: [calm, normal, elevated, stressed], filtered_only: true, acts: false, ...}` (L4286-4314). Note: existing `risk.analyze_history` and `strategies.realised_vol` use log returns; `sma_vol` must use simple returns (`History.simple_returns()` exists), ddof 1. `hedge_state` keys: `risk_layer.hedge_state: {core_pce_yoy_threshold: 0.030, corr_window: 63, corr_threshold: 0.0, corr_pairs: date_aligned, lag: statistic_not_leg, stale_input: hedge_credit_off, exception: hedge_credit_off, usd_input: USD_LIVE_PROXY, ...}` (L4365-4370). Hard stop / ladder keys in B.7.

**core/quant/signals.** Family tags `momentum, reversal, flow, quality, ts_trend` (L1169); artifact `family` enum adds `market_gross` (L3730). `dm_gate`: `families.momentum.dm_gate: {market_return_months: 24, market_vol_window: 126, vol_quantile: 0.6667, quantile_min_obs: 252, multiplier: 0.5, exposure_basis: active, books: [specification], label: "step 3 FAIL", a_provisional_route: closed, pooled_revision: none}`; `families.momentum.own_vol_scale: {window: 126, target_ann: 0.12, cap: 1.0, floor: 0.0, min_obs: 126, exposure_basis: active, series: paper_unit_gross_long_short, apply_to: sleeve_budget, revisions: {...}}`; `families.reversal: {overlay: fixed_1.0, intraday_leg: false, calm_state_downweight: not_adopted}`; `families.quality: {overlay: fixed_1.0}`; `families.flow: {overlay: fixed_1.0}`; `families.ts_trend: {signal: sign_12_1, rebalance: monthly, vol_window_months: 12, target_ann: 0.15, cap: 1.0, overlay_exempt: true, card: {class: CARD-O, claim: diversification, instrument_book: multi_line}}` (L4316-4327). `base_weights` keys: `base_weights.cross_market: {method: inverse_vol, returns: weekly, cov_acting: ewma_0.97, cov_printed: ledoit_wolf_156w, spans: markets_with_sleeves}`, `base_weights.family: {admissible_if: {prior_min: 1, card_verdict_not: REJECT}, weight: one_over_K, range_prior: lower_bound, no_registered_prior: not_admissible, not_run_admissible_except: [ts_trend], reject_reweight: logged_governance_event}`, `base_weights.tilt_requires_family_card_pass: true` (L4281-4285).

**core/quant/refusal (display only).** `refusal_books.S1_krw: {lookback_obs: 20, threshold_dlog: 0.03, multiplier: 0.75, target: KR_market_gross, one_sided: true, verdict: REJECT, regate_queue: false}`; `refusal_books.S2_rates: {lookback_obs: 20, threshold_pp: 0.40, multiplier: 0.5, target: US_duration_sensitive_gross, excludes: [momentum, ls_factor_sleeves, KR], verdict: REJECT, regate_queue: false}` (L4408-4411). Return `Multiplier(status="REFUSAL")`. Read by no recommended or specification book.

**core/ficc/macro builders.** `build_macro_state` validates against `macro_state` 2.0; `build_overlay_decisions` returns one record per market x family (incl. `market_gross`); artifacts are "always written, also when a gate failed" (L1220-1221). `bounds_ok` runs after building (L1222-1227). Until M6, tests assert function outputs, never a built artifact (L6368).

**core/engine hooks.** See B.7. **Workflow.** See B.8.

### B.5 Reconciliation with the macro sheet (3.6, L1115-1163)

Spec says the 18 indicators, z-score windows and regime-read method are not given and must be completed from the code (BL-G06). Actual code (`core/ficc/macro.py:54-73`, `:35-36`, `:161-186`):

| Indicator id | Label | Source | v2.0 role (proposed mapping L1153-1163) |
|---|---|---|---|
| DGS2, DGS30, T10Y2Y | UST 2y, 30y, 2s10s | FRED | CONTEXT |
| DGS10 | UST 10y | FRED | CONTEXT; also `risk_model` (consumer `corr63_backtests`) and `context` (consumer `R-12_refusal_book`); production corr63 uses `US10Y_KIS_QUOTE` |
| DFII10, T10YIE | 10y real, 10y breakeven | FRED | CONTEXT |
| SOFR, DFF | SOFR, Fed funds | FRED | CONTEXT |
| BAMLC0A0CM, BAMLH0A0HYM2 | IG OAS, HY OAS | FRED | CONTEXT (BL-C03) |
| DTWEXBGS | Broad USD | FRED | CONTEXT, "never acting" |
| DEXUSEU, DEXJPUS | EUR/USD, USD/JPY | FRED | CONTEXT |
| DEXKOUS | USD/KRW | FRED | CONTEXT; labelled proxy; R-11 refusal book input; reading it for an acting or risk-model input in `run_mode = live` raises (T-H10-01) |
| VIXCLS | VIX | FRED | CONTEXT; feeds the R-08 annotation (no exposure effect) |
| DCOILWTICO | WTI | FRED | CONTEXT; oil feeds Monte Carlo scenarios and replays; must be a named series |
| ZN=F, GC=F | 10y note future, Gold | Yahoo | CONTEXT |

Existing method facts: z and percentile use the last 252 observations ending at the latest observation (`_Z_WINDOW = 252`, population std); changes over 1/5/21/63 observations (positional); regime read = five threshold rules: curve via `curves._regime` on 20-session DGS10/DGS2 changes; `risk` = mean of VIXCLS and HY OAS z: > 0.75 `risk-off`, < -0.5 `risk-on`, else `neutral`; `dollar` from DTWEXBGS 1m change > 1.5% `strong`, < -1.5% `weak`, else `range`; `inflation`/`real_rates` trend bands 10 bp / 15 bp. It is not a Markov-switching, HMM, jump, mixture or change-point model.

Binding rules (L1121-1133):
1. Every sheet indicator becomes a CONTEXT item in `context_log` with `obs_date`, `available_at_utc`, `retrieved_at_utc`, `vintage` and source, unless it is one of the acting or risk-model inputs (M6 acceptance: every sheet item appears with `from_sheet=true`, L6368).
2. Z-scores stay display-only, computed causally on expanding or trailing windows ending at `decision_utc`, "never thresholded for exposure".
3. Regime read (P19): removed from every page if it came from a regime model; otherwise it "may stay in the brief as a descriptive text summary", "never presented as a regime state, never reuses the calm / normal / elevated / stressed names", never feeds `core/quant/signals`, `core/quant/risk` or the engine.
4. The brief gains a `macro_state` section: vt and vs weights and the relative and absolute vol labels; flags and annotations; each card's verdict and disposition; FORWARD-SIM cards and refusal books marked "not a recommendation"; the open owner decisions; the event calendar.

Acting and risk-model inputs, "the only series that feed sizing or the risk model" (L1135-1144):

| Input | Role | Feeds | Rule |
|---|---|---|---|
| KOSPI and S&P 500 (or US sleeve) official closes | acting_exposure, bound to its market's specification book, and to its recommended book only once that market's vt card is PASS (US close bound to no book while D5 = none) | `vt(m)` via SMA20 | R-06 |
| Momentum sleeve daily returns (paper unit-gross long/short series) | acting_exposure, specification book until R-03 PASSes | `vs(m, momentum)` | R-03 |
| Market 24-month return and 126-day realised vol | acting_exposure (specification book only) | D&M gate | R-04 |
| Samsung + SK hynix and KOSPI market caps; daily KODEX 200 basket (PDF) from KIS or KRX | acting_exposure | look-through caps | R-07 |
| Core PCE YoY; stock-bond corr63 on date-aligned pairs; labelled live broad-USD proxy | risk_model | `hedge_state` (no exposure effect; never HALTs) | R-09 |
| Monthly index closes of a US or other non-Korean sleeve | forward_sim (never HALTs another book) | trend-axis card | R-28 |

Inputs that act on nothing (L1146-1149): VIXCLS / VXVCLS -> R-08 annotation (context). USD/KRW (ECOS 15:30 close or timestamped 15:30:00 KST snapshot) -> R-11 refusal book (context) and `nav_fx` of non-KRW books with the role of the book it values. US 10y (KIS quote; Treasury par yields for history): `risk_model` for corr63 and `context` for the R-12 refusal book.

### B.6 Reconciliation with the signal composite (3.7, L1165-1171)

Actual six components (`core/quant/signals.py:94-154`): `trend50` (w 0.20), `trend200` (0.20), `momentum` = 63-session rate of change (0.20), `rsi` (0.15), `macd` (0.15), `vol` = sigma20/sigma100 posture (0.10). Output is a per-symbol composite in [-100, +100] with a stance word, not a weight vector.

Binding rule: overlays attach through a family tag (`momentum, reversal, flow, quality, ts_trend`). "A component with no family tag receives no family overlay (multiplier 1.0) and is still subject to `vt(m)` and the risk layer." A family receives a base weight in market m only if its prior is >= 1 and its card is not REJECT. "Overlays never create a new component and never change a component's sign (P1)." Mapping is proposed and owner-filled (BL-G07, TASK-M4-01). Build: add `family: str | None = None` to `SignalComponent`; default None for all six (see F-4).

### B.7 Engine mapping (3.8, L1173-1187) — per-book runtime

**Book ids (L1180):** `recommended:<market>`, `specification:<market>`, `forward_sim:<rule>`, `refusal:<rule>`, `card:<card_id>:<on|off|S>`. One runtime state per book. `macro_state.flags.engine_state` reports the market's recommended book; `macro_state.runtime[]` reports every book.

**States and transitions (L1180):**

| Transition | Rule |
|---|---|
| DISARMED (initial, or retired) | holds no simulated position; artifacts carry `engine_state: DISARMED`; no forward record runs |
| DISARMED -> ARMED | automatic, "from the initial state only (a book that has never been ARMED)", at the first decision at which every acting input bound to the book is fresh and past warm-up, the calendars cover >= 60 sessions ahead (T-CAL-02) and, for card books, the header is committed; logged as a governance event (`kind: book_state`) |
| ARMED -> HALTED | triggers below, by class and scope |
| HALTED -> ARMED | re-arm rules below |
| ARMED or HALTED -> DISARMED | owner action only (retiring a book), logged. "A retired book never re-arms"; a card's books restart only under a new card revision with R-25's lockout; a card's on/off/S books are retired together, and an operator kill of one kills all three (an operational integrity trigger, R-25) |

**HALT scope (binding, C-1; L1178):** a trigger HALTs only the books whose own NAV breached, whose own artifact failed acting-field validation, or that read the failed input or component through an `acting_exposure` binding. "The recommended book is never HALTed by a factor or input it does not read (I-03)." A global failure (PIT store, calendars, the `core/engine` QuoteFeed) HALTs every book that reads it; "it never HALTs 'the engine' as such". HALT sets that book's target exposure to 0 and records `halt.class` and `halt.reason_code` in that book's `macro_state.runtime[]` entry.

**Triggers (L1178; config `risk_layer.halted_triggers`, L4354-4358):**

| Class | Trigger (`reason_code` per config list) | Detail |
|---|---|---|
| RISK | `hard_stop` | -15% of the book's NAV from the high-water mark since the last re-arm (default; D2); comparison `<=` at exactly -15.00% (T-HALT-01) |
| RISK | `risk_limit_breach` | an R-07 limit that its prescribed action (lowering g on the ETF line; carrying a limit-locked order, R-27) cannot meet by the next decision. A limit met by lowering g is a binding bound, never a breach, never returns 0 |
| OPS | `lag_audit_violation` | at runtime; needs operator re-arm |
| OPS | `acting_field_schema_or_bounds_failure` | in the book's own `macro_state` or `overlay_decision` (R-32); needs operator re-arm |
| OPS | `acting_input_fail_closed_beyond_declared_misses` | input counter reaches the binding's `halt_after_consecutive_decisions` (default 2; `KODEX200_PDF` 5; `NAV_LINE_CLOSES` 3) or the book counter reaches 2 (`book_counter_halt_after: 2`) |
| OPS | `acting_step_error_beyond_limit` (`run_error`) | error in an acting workflow step counted on the book counter |
| OPS | `feed_heartbeat_loss_60s` | feed heartbeat loss > 60 s during a session: new intraday simulated entries BLOCKED at once; automatic re-arm once the feed has been restored for 5 minutes; "a HALT cleared before the next decision changes no weight" |
| OPS | `acting_risk_layer_exception` | exception in `market_vol_target`, `concentration_bound`, `drawdown_ladder`, `compose` |
| OPS | `whole_book_nav_unavailable_gt_2_decisions` | whole-book NAV unavailable on more than 2 consecutive decisions (R-25) |
| OPS | `calendar_coverage` | a decision date outside calendar coverage (T-CAL-02) |
| OPS | `operator_kill` | `runtime_halt(book_id, "OPS", "operator_kill")` |

**Never a HALTED trigger (L1178; `risk_layer.never_halt_on`, L4362-4363):** `risk_model_input_stale_or_failing`, `hedge_state_exception` (-> `hedge_credit_off = TRUE`), `context_input_stale`, `disputed_input`, `warmup_input_before_first_armed_decision`, `input_bound_only_to_other_books`, `display_or_context_field_validation_failure`, `context_log_or_event_calendar_validation_failure`. An input bound only to FORWARD-SIM or refusal books fails that FORWARD-SIM book closed, or labels the refusal book's input, and never HALTs.

**Effective time (L1178):** a HALT decided at the close of t sets the weights decided at t to 0 (the book earns 0 from t+1); a HALT raised intraday (heartbeat) blocks new intraday entries at once and applies to the weights decided at that session's close.

**Backtests (L1178):** `core/quant/risk` returns 0 only for a risk-limit breach, the hard stop, or a data or system failure, and only in the books whose convention applies them (card evaluation books follow R-22 rule 6).

**Re-arm (L1179; config `risk_layer.drawdown.hard_stop`, `risk_layer.ops_rearm`, L4349-4361):**

```
hard_stop: {level: -0.15, alt: "-1.5*sigma_book", reference: hwm_since_last_rearm, action: book_HALTED, class: RISK,
            scope: own_book_nav, rearm: automatic, rearm_refused_sessions: 10, rearm_calendar: book_primary_market,
            rearm_resets: [hwm_hard, ref_step], post_rearm_cap: 0.5, post_rearm_sessions: 10, post_rearm_cap_in_min: true,
            idempotent_while_halted: true, log: governance_review_event, protection_claim: false}
heartbeat: {loss_s: 60, blocks_new_intraday_entries: immediately, auto_rearm_after_restored_min: 5}
ops_rearm: {when: cause_cleared, operator_required_after: [lag_audit_violation, acting_field_schema_or_bounds_failure],
            reference_reset: false, post_rearm_cap: false}
halt_scope: per_book
```

- RISK, sessions counted on the book's primary-market calendar (KRX for a KR book): HALT decided at close of t earns 0 on sessions t+1 ... t+10; re-arm is automatic at the decision at the close of t+10, in every book, backtest and forward alike (I-04b); operator acknowledgement logged, never required.
- After a hard-stop HALT the hard-stop and step references reset to the NAV at re-arm. After a risk-limit breach they do not reset, and the book re-arms only at the first decision at or after the close of t+10 at which the target weights the book would hold on re-arming, after the prescribed action, satisfy the limit ("a HALTED book's zero exposure never counts as meeting it").
- In both RISK cases `post_rearm_cap = 0.5` joins the `min()` for the weights decided at the actual re-arm decision and the 9 decisions after it (closes of t+10 ... t+19, earning t+11 ... t+20 when re-armed at t+10); "exposure <= 0.5 x vt, not an absolute 0.5"; then normal running. `runtime[].post_rearm_cap_until` = the last decided_session carrying the cap.
- OPS: HALTED until the cause clears (input fresh, heartbeat restored, artifact valid, NAV available, calendar signed); automatic re-arm at the first decision at which the cause has cleared, except after a lag-audit violation or an acting-artifact schema failure (operator re-arm once the fix's test passes). "No refusal window, no reference reset, no post-re-arm cap."
- Idempotence: a HALT raised while HALTED is idempotent for its own cause: never extends `rearm_not_before`, never resets a reference. A different cause is appended to `halt.causes[]` (`{class, reason_code, since_utc, rearm_mode, rearm_not_before, cleared_utc}`); top-level `class`, `reason_code`, `since_utc` restate `causes[0]`; top-level `rearm_mode` is `operator` while any uncleared cause needs the operator, else `auto`. The book re-arms only when every cause has cleared under its own rule. References reset only if a hard-stop cause was in the set; `post_rearm_cap` applies if any RISK cause was, its window starting at the actual re-arm decision. The ladder is not evaluated while HALTED.
- Every HALT and re-arm is a governance event. "The hard stop makes no protection claim."

**NAV valuation (L1181):** whole-book NAV (one book id, all sleeves; in v2.0 only R-14's `multi_line` card books span markets) for R-07, R-31, R-25 is evaluated at each decision instant from the latest official closes usable at that instant (bound per book through `NAV_LINE_CLOSES`), converted to KRW through the book's declared `nav_fx`, with per-market attribution printed. NAV-input failure HALTs (OPS) only a book whose `NAV_LINE_CLOSES` binding has role `acting_exposure`; a FORWARD-SIM book never HALTs on it: the decision is marked failed-closed, printed, and counted toward 8.8 (b)'s 10% budget.

**Ladder steps (L1182; `cards.R-31_step_down`, L4448-4460):** `steps: [{dd: -0.08, mult: 0.5}, {dd: -0.12, mult: 0.5, evaluator_block_new_entries: true}]` (totals, non-cumulative); `dwell_sessions: 21`; `step_reference: running_peak_since_last_reset`; `hard_stop_reference_resets_at_dwell_end: false`. Compose with the overlays by `min()`. Where the steps bind on more than 10% of days on the declared book (about 19% for KOSPI VT20) they act only in the specification book until the R-31 CARD-P passes.

**Entry blocks (L1183):** `core/engine/evaluator(rule, quote) -> decision` returns `BLOCKED(rule_id, reason)` for any new-entry decision while an R-10 event window or the -12% step is active. "Holds and exits are never blocked." The backtest applies the same rule at daily resolution. R-08 is not a block: on a flag day the evaluator writes an annotation and requests KIS spread snapshots; no book's exposure changes.

**Execution (L1177; R-27):** simulated order book; decision on the official close of t, earns from t+1 (QUANTGEN rule 02); every simulated fill charged the pre-registered cost with the tick floor. KRX daily weights fill at the official close (closing call; random end <= 30 s); executable variant (about 15:19 KST snapshot filled at the close) printed as a tracking-error line; a limit-locked name is non-fillable at the close; ETF close vs iNAV residual above 30 bp flagged; NYSE fills MOC-equivalent at the official close; intraday simulated entries priced at the triggering quote with its timestamp; "No daily close is ever derived from intraday bars."

**Books routing (L1184-1185):** recommended and specification books are fed through `macro.engine_feed`. FORWARD-SIM (R-28, R-29) and refusal (R-11, R-12) books are computed by the forward evaluator and recorded in `core/engine/state`; "they never pass through `engine_feed`". FORWARD-SIM books run from the header-commit date, write timestamped `macro_state` and `overlay_decision` artifacts, and are falsification alarms only.

**Kill vs card kill (L1186):** operator kill = `runtime_halt(book_id, "OPS", "operator_kill")`, governance event, operator re-arm, never a demotion (except a kill of a card's forward books = operational integrity trigger). Card kill = demotion: "any edit of an acting parameter outside a card revision appears in the rules store's edit history, demotes the card immediately and opens a new revision". An owner ruling (8.10) is not such an edit.

**Persistence (L1187):** `core/engine/state` persists trigger counts, per-card switch counts, the ladder state (references, step, dwell left, re-arm and cooling-off dates), each book's runtime state and consecutive-failure counters, and forward alarms. Forward records are append-only: never span a DISARMED period; alarm state never reset within a card revision; every HALTED or DISARMED gap is marked and excluded from both sides of every forward comparison (L1180).

**Counters (R-19 rule 4, L1869-1871):** per (book, series) input counter = consecutive decisions at which that input failed closed, reset at its next fresh decision; book counter = consecutive decisions at which any acting input bound to the book with the default limit failed closed, reset when all are fresh. HALT when an input counter reaches its binding's `halt_after_consecutive_decisions` (default 2) or the book counter reaches 2 ("two inputs failing on alternate decisions still HALT the book"). Bindings follow admission (L1889): the runtime derives each binding's book list at every decision from `verdict_filter` admissions without editing `roles`; each change is a governance event (`kind: binding_change`); load-time assertion refuses any book that reads a factor whose acting inputs are not bound to it.

### B.8 `macro_daily` workflow (3.9, L1189-1253; R-35 L3479-3497)

Header: `name: macro_daily`; `runs: [after_close: KRX, after_close: NYSE]`; `decision_utc = close_print_bound_utc` from the calendar; "the run starts no earlier than close_print_bound_utc + 10 min (06:40:30Z for KRX today), so no provisional row is read"; `run_mode: live` (`live | backtest | replay`).

| # | Step | Kind | Behaviour (binding) |
|---|---|---|---|
| 1 | `macro.pit_snapshot` | skill, acting | retries missing inputs per `data.ingest` (`retries_min: [1, 5, 15, 60]`) until they arrive or `data.ingest.decision_deadline` (`next_session_open_minus_30min`) passes, then pins `knowledge_utc` for the run; one artifact per decision (a later run for the same decision is a replay, never a second forward decision); `pit_value` for every registry binding at `decision_utc` with `value_status` and `session_date` checks |
| 2 | `data_ok` | gate | acting_exposure missing/stale/provisional/synthetic -> that component `fail_closed=true`, alert, previous state carried; bound books' counters +1; at the declared limit those books HALTED (OPS); unbound books untouched. forward_sim failing -> that FORWARD-SIM book fails closed, never HALTs another book. risk_model stale or failing -> `hedge_credit_off=TRUE`, alert (operator alert after two missed releases); the gate PASSES. context stale -> labelled "stale"; the gate PASSES |
| 3 | `macro.lag_audit` | skill, acting | independent of `pit_value`: for every acting and risk-model input recompute `usable_at(series, obs_date, market)` from `core/calendars` and the registry; require `usable_at <= decision_utc`, `available_at_utc >= publication_instant(series, obs_date)` (closes: >= the scheduled close; derived input: each input of its lineage), `retrieved_at_utc <= knowledge_utc` and the R-01 status and session checks. Acting violation -> HALT (OPS) of the books it feeds. Risk-model violation -> `hedge_credit_off` + alert, never HALT (covariance-only binding: carried, then dropped). Record written to `macro_state.lag_audit` (`{checked, violations[{series_id, obs_date, check, expected_usable_at_utc, stamped_available_at_utc}]}`) |
| 4 | `macro.vol_and_overlays` | skill, acting | vt, vs, base weights, `hedge_state`, look-through caps, ladder state; composition by `min()` |
| 5 | `macro.build_artifacts` | skill, acting | `macro_state`, `overlay_decision` (verdict and disposition per factor), `context_log`, event windows and gap tags, R-08 annotation; "always written, also when a gate failed" |
| 6 | `bounds_ok` | gate | schema 2.0 + P2 bounds + exposure basis + `min()` composition recomputed from the recorded factors. Acting-field failure -> HALT (OPS) of the books the artifact describes; artifact to `<artifact_dir>/quarantine/` with its errors. Display- or context-field failure -> written with `extras.validation_errors` and an alert. `context_log` / `event_calendar` failure -> refused and quarantined, alerted; never a HALT |
| 7 | `verdict_filter` | gate | PASS factors with disposition `RECOMMENDATION` or `BUILD_AS_INSURANCE`, and R-31 steps with disposition `INVARIANT_STEP`, enter the recommended book; everything else -> specification book. Each verdict is authenticated first against `cards/verdicts.jsonl`: (i) card file re-hashes to the committed `results_md5` and the chain verifies; (ii) card's `gate_package_md5` equals the frozen package's `definitions_md5`; (iii) `data_snapshot_id` recomputed from the store at the card's `knowledge_utc` matches and `git_hash` is a commit whose harness sources hash to the package manifest. Otherwise the factor stays in the specification book and `VERDICT_INTEGRITY` (severity page) is raised. A card with `build_status_on_pass` BUILD_AS_INSURANCE but verdict NOT_RUN or INSUFFICIENT DATA (R-06 KR today) is refused |
| 8 | `macro.engine_feed` | skill | recommended and specification books -> `core/engine` (simulated order book only); BLOCKED rules; never a FORWARD-SIM or refusal book; atomic per book (section 9.4 item 17) |
| 9 | `macro.forward_books` | skill | FORWARD-SIM books (R-28, R-29) and, if kept, refusal books (R-11, R-12) -> forward evaluator; display only |
| 10 | `macro.forward_monitor` | skill | R-25 alarms on whole-book NAV; integrity triggers demote immediately; an error here is re-run for each skipped decision at the next successful run |
| 11 | `macro.brief` | skill | Macro page and weekly brief section; open owner decisions listed |
| 12 | `macro.run_record` | skill | appends `{run_id, market, session_date, decision_utc, knowledge_utc, started_utc, finished_utc, step results with errors, git_hash, config_hash, data_snapshot_id, late}` to `run_log.jsonl`; a step that raises still writes its record (`status = error`) and raises `RUN_ERROR` (page) |

Error handling (L1240-1247): an error in an acting step (`pit_snapshot` through `verdict_filter`) blocks `engine_feed` for that run: the books carry their weights, `build_artifacts` writes a `fail_closed` artifact, and every book the step serves counts a failed decision (book counter +1; OPS HALT `run_error` at the limit). On app start and at every scheduled run `macro.missed_decisions` compares the calendar's expected decisions with `run_log.jsonl`; each missing decision, and each decision whose run record has `status = error` in an acting step, raises `MISSED_DECISION` (severity page) and the books carry their weights.

Alert sinks (L1248-1250): a Macro-page banner (always; page alerts persist until acknowledged), an OS notification, an optional e-mail skill. HALT, re-arm, demotion, package freeze, header commit, owner-decision and calendar changes are appended to `governance_events.jsonl` (append-only, hash-chained; one 6.6 record per line, verified at app start; T-OBS-05) and summarised in the weekly brief. Alert codes named in this area: `RUN_ERROR`, `MISSED_DECISION`, `VERDICT_INTEGRITY`, `GOVERNANCE_LOG_BROKEN` (all severity `page`).

"Credentials stay env-only, as in the existing runner. The Claude API, when a key is set, receives the computed numbers only and never decides" (L1253).

### B.9 If a broker path were ever added (3.10, L1255-1264)

Nothing to build. "This spec therefore does not design one." Recorded conditions only: (1) only PASS cards (RECOMMENDATION or BUILD-AS-INSURANCE) could drive it, with pre-registered costs, tick floor and 2x stress on the declared instrument book; (2) fail-closed: HALTED, any lag-audit or schema failure, any stale acting input would block submission; 0x only from the risk layer; (3) its own forward record gated like any card; (4) nothing in section 5 would change. Owner decision; out of scope.

---

## C. Schemas and config this area writes or reads

### C.1 Artifacts (schemas next to the builders; `core/ficc/schemas/` proposed)

Common provenance on every artifact (L3508): `schema`, `schema_version` ("2.0"), `generated_at_utc`, `knowledge_utc`, `git_hash`, `config_hash`, `data_snapshot_id`, `read_only: true`.

`macro_state` (`quantgen.macro_state`, one per market per decision) required (L3527-3529): `schema, schema_version, read_only, generated_at_utc, knowledge_utc, git_hash, config_hash, data_snapshot_id, decision_utc, decided_session, effective_session, market, run_mode, inputs, lag_audit, vol, flags, annotations, concentration, owner_decisions, runtime, fail_closed, alerts`.

- `inputs[]` required (L3633-3634): `name, series_id, source, obs_date, session_date, obs_kind, value, value_status, dispute, available_at_utc, available_at_source, retrieved_at_utc, expected_available_utc, stale_deadline_utc, vintage, timing, role, books, status, content_hash`; `timing` in {`live`,`publication`,`value_proxy`}; `status` in {`ok`,`stale`,`stale_missed_release`,`missing`,`provisional_rejected`,`session_mismatch`,`synthetic_rejected`,`disputed`,`warmup`}.
- `vol` required (L3567-3568): `estimator, estimator_b5, estimator_gate, vt_status, sigma_ann, target_ann, vt_weight_next, vt_weight_recommended_book, instrument_book, display_label_rel, label_method_rel, display_label_abs, label_method_abs`; `vt_status` in {`ok`,`warmup`,`fail_closed`}; `vt_weight_recommended_book` "= vt_weight_next once R-06's card is PASS; 1.0 while NOT_RUN or INSUFFICIENT".
- `flags` required (L3585-3586): `hedge_credit_off, hedge_failure, classic_risk_off, hedge_reasons, kr_open_gap_event, gap_sessions, var_display_scale, ladder_step, ladder_dwell_left, block_new_entries, hard_stop, engine_state`; `ladder_step` in {`none`,`step_-8`,`step_-12`,`hard_stop_-15`}; `ladder_steps_act_in` in {`recommended`,`specification`}; `hard_stop` in {`armed`,`halted`,`rearm_refused`,`post_rearm_cap`}; `engine_state` in {`DISARMED`,`ARMED`,`HALTED`}.
- `concentration` required `template, by_book`; `by_book[<book_id>]` required `composed, gross, binding_factor` (L3601-3604).
- `runtime[]` required (L3608): `book_id, engine_state, halt, consecutive_failures, book_counter`; optional `post_rearm_cap_until, nav, hwm_hard, ref_step`. `halt` (object or null) required `class, reason_code, since_utc, rearm_mode, causes`; optional `component, series_id, rearm_not_before, ack_by, ack_utc`; `class` in {`RISK`,`OPS`}; `rearm_mode` in {`auto`,`operator`}; `causes[]` (minItems 1) required `class, reason_code, since_utc, rearm_mode`, optional `rearm_not_before, cleared_utc`.
- `alerts[]` required `alert_id, code, severity, component, first_seen_utc, count`; `severity` in {`info`,`warn`,`page`} (L3625-3629).

`overlay_decision` (`quantgen.overlay_decision`, one per market x family per decision) required (L3720-3723): `schema, schema_version, read_only, generated_at_utc, knowledge_utc, git_hash, config_hash, data_snapshot_id, decision_utc, effective_session, market, family, exposure_basis, vol_scale, vol_scale_recommended_book, multipliers, composition, overlay_min, overlay_floor, overlay_cap, overlay_applied_spec_book, overlay_applied_recommended_book, forward_sim, refusal, binding, reasons, inputs, rule_versions`. `multipliers[].value` min 0.5 max 1.0; `ladder` and `post_rearm_cap` in {0.5, 1.0, null} (market_gross only); `composition: {"const": "min"}`; `overlay_floor: {"const": 0.5}`; `overlay_cap: {"const": 1.0}`. `$defs.card` required `card_id, class, verdict, disposition, displayed_as, results_md5`; `verdict` in {`PASS`,`REVISE`,`REJECT`,`INSUFFICIENT_DATA`,`NOT_RUN`}; `disposition` in {`RECOMMENDATION`,`BUILD_AS_INSURANCE`,`INVARIANT_STEP`,`SPECIFICATION_ONLY`,`FORWARD_SIM`,`REFUSAL_BOOK`,`DESCRIPTIVE`}; `displayed_as` in {`recommendation`,`insurance`,`invariant`,`descriptive`,`refusal`}. Rules (L3767-3771): `displayed_as` in {recommendation, insurance} iff verdict PASS and disposition in {RECOMMENDATION, BUILD_AS_INSURANCE}; `invariant` iff `INVARIANT_STEP`; recommended-book builder refuses `SPECIFICATION_ONLY`, `FORWARD_SIM`, `REFUSAL_BOOK`.

`governance_event` (`quantgen.governance_event`, one JSON line in `governance_events.jsonl`) required (L4100): `schema, schema_version, event_id, utc, kind, book_id, rule_id, key, actor, reason, refs, prev_row_md5`; optional `old, new`; `kind` in {`halt`,`rearm`,`book_state`,`demotion`,`package_freeze`,`package_redesign`,`header_commit`,`owner_ruling`,`calendar_change`,`notional_change`,`admissibility_reweight`,`binding_share_recompute`,`binding_change`,`record_reset`,`verdict_integrity`}; `actor` in {`owner`,`operator`,`runtime`,`harness`,`council`}; `prev_row_md5` null only on the first line.

`run_log.jsonl` record (L1237-1238): `run_id, market, session_date, decision_utc, knowledge_utc, started_utc, finished_utc, step results with errors, git_hash, config_hash, data_snapshot_id, late` (+ per-step `status`).

`cards/verdicts.jsonl` row (L3487): `card_id`, revision, `header_md5`, `results_md5`, verdict, disposition, `gate_package_md5`, `data_snapshot_id`, `git_hash`, `ledger_hash_at_run`, `prev_row_md5` (append-only, hash-chained).

Canonical JSON for replay (T-REPLAY-01; L4683): UTF-8, sorted keys, floats printed with repr, no insignificant whitespace; volatile fields `generated_at_utc`, `git_hash`.

### C.2 Rules-store keys this area reads (section 7; proposed home `data/macro/rules_v2.0.0.json` + `core/rules/macro_rules.py`)

Top level: `version: "2.0.0"`, `as_of: "2026-10-02"`, `read_only: true` (L4135-4137). Owner decisions `owner_decisions.D<n> = {key, value, default, options, status, effective_from, rationale, refs}`; a rule block holds `{ref: <canonical key>}`, never a literal copy (L4130). Values read here: D1 `risk_layer.korea_caps.template` = `msci_25_50`; D2 `risk_layer.drawdown.hard_stop.level` = `-0.15`; D5 `sleeves.US.line` = `none` (status `pending`).

Blocks quoted in B: `time.*` (L4153-4173), `calendars.*` (L4174-4194), `data.*` (L4195-4224), `data_contracts.on_failure.*` and `data_contracts.roles.*` (L4230-4270), `overlay.*` (L4272-4280), `base_weights.*` (L4281-4285), `vol_target.*` (L4286-4315), `families.*` (L4316-4327), `risk_layer.*` (L4330-4370), `annotations.vix_ts` (L4372-4373), `events.*` (L4374-4386), `fill_model.*` (L4387-4393), `refusal_books.*` (L4408-4411), `cards.R-31_step_down` (L4448-4460), `reproducibility` (L4680-4684).

`data_contracts.on_failure` verbatim (L4230-4241):
```
acting_exposure: {action: fail_closed, alert: true, halt_after_consecutive_decisions: 2, scope: bound_books, book_counter_halt_after: 2}
risk_model:      {action: conservative_default, set: {hedge_credit_off: true}, hedge_failure_from: USD_LIVE_PROXY, operator_alert_after_missed_releases: 2, halt: never, also_on: hedge_state_exception}
context:         {action: label_stale}
forward_sim:     {action: fail_closed_that_book, alert: true, halt: never}
history:         {action: refuse_card_if_span_not_covered, alert: true, read_by_weight_decisions: false}
risk_model_covariance: {action: carry_last_valid_terms_stale_then_drop, carry_max_decisions: 5, alert: true, halt: never, sets_hedge_credit_off: false}
not_failures:    [warmup_before_first_armed_decision, disputed]
```

Bindings that define HALT scope today (L4246-4259): `KOSPI_OFFICIAL_CLOSE: {role: acting_exposure, books: [specification]}`; `US_SLEEVE_OFFICIAL_CLOSE: {role: acting_exposure, books: []}`; `NAV_LINE_CLOSES: [{role: acting_exposure, consumer: nav, books: [recommended, specification], halt_after_consecutive_decisions: 3}, {role: forward_sim, consumer: nav, books: ["forward_sim:R-28", "forward_sim:R-29"]}]`; `KODEX200_PDF: {role: acting_exposure, books: [recommended, specification], halt_after_consecutive_decisions: 5}`; `KRX_MARKET_CAPS_005930_000660_KOSPI: {role: acting_exposure, books: [recommended, specification]}`; `MOM_PAPER_LS_SERIES: {role: acting_exposure, books: [specification]}`; `DM_MKT_RET_24M` and `DM_MKT_VOL_126: {role: acting_exposure, books: [specification]}`; `SPX_OFFICIAL_CLOSE` forward_sim + risk_model bindings; `USD_LIVE_PROXY: risk_model`; `PCEPILFE: risk_model`; `DTWEXBGS: context`; `DEXKOUS: context`.

Section 7.1 rule-object fields (L4691-4705): `rule_id`, `kind` in {INVARIANT, CONVENTION, CARD-O, CARD-P, CONTEXT, GOVERNANCE}; `output_range` [lo, hi]; `exposure_basis` in {active, total}; `applies_to` (family enum incl. `market_gross`); `composition` (only `min`); `books[]` in {recommended, specification, forward_sim, refusal}; `inputs[]` `{series_id, role, books, timing, source_kind}` with `source_kind` in {market_price, published_series, derived, implied_vol, regime_model, ml_classifier}; `estimator` `{name, kind}` with `kind` in {sma, ewma, garch, har, comb, ml}; `label_layer` in {none, conformal}; `instrument_book`, `market`; `card_id`, `tier`, `header_md5`, `results_md5`; `n_rule`.

### C.3 Files and directories (proposed)

| Item | Location |
|---|---|
| Macro artifact dir (`macro_state`, `overlay_decision`, `context_log`, `quarantine/`, `run_log.jsonl`, `governance_events.jsonl`, `cards/verdicts.jsonl`, `fetch_log.jsonl`) | `config.macro_artifact_dir()` [N], default `~/.nextgen/macro` (same pattern as `trading_dir()`); env override; tests use temp copies (T-HERM-02) |
| PIT store (append-only) | under the macro artifact dir or `~/.nextgen/pit_store`; `~/.nextgen/ficc_cache` stays a read-through cache |
| Book runtime state | `<trading_dir>/macro_books.json` [N] (separate from `engine.json`) |
| Rules store v2 seed | `data/macro/rules_v2.0.0.json` [N] |
| Calendar data | `data/macro/calendars/` [N] (spec literal `core/calendars/data/` cannot exist while `core/calendars.py` is a module; F-6) |

---

## D. Tests

Feasibility classes: SYNTH (hermetic, synthetic or inline fixtures), REFDATA (frozen reference data under `/home/claude/quantgen_macro_data/` not on this machine), OWNER (owner input, credentials or live sessions). Local data: `docs/asset_expansion/cache/` has no KOSPI index series (only `yf_069500.KS` 2007-01-29..2026-09-23, `yf_005930.KS`, `yf_SPY` 1995..2026-09-25, `yf__VIX`, `yf__VIX3M`, `fred_DEXKOUS` 2017..2026-09-18, `fred_DGS3MO`; `yf__KS200` has one row) and ends before 2026-10-02; all Yahoo rows are `vendor_close`, never `official_close`. Tech-fund results: `datalab/results/r2_idx/r2_idx_golden_values.csv` (KOSPI VT20 goldens on rebuilt KOSPI 2016-01-04..2026-09-29), `r3/r3_pair_share*.csv`.

| Test (runs_from) | Exact assertion (line) | Fixture | Class |
|---|---|---|---|
| T-CAP-02 (M2) | 10,000 seeded draws (seed 11) of k in {0..5}, overlays in [0.5, 1]^k (endpoints included), vt in [0, 1] (0 and 1 included), ladder in {1.0, 0.5}, post-re-arm cap in {1.0, 0.5}: composed = vt x min(1.0, overlays, ladder, post_rearm_cap) and composed >= 0.5 x vt on every non-HALTED day; floor applies to `composed`, a risk limit may take `gross` below it without HALTing; "0.75 and 0.5 compose to 0.5 (never 0.375), and the binding factor is logged"; a product-composed path raises (L5627) | inline RNG | SYNTH |
| T-CAP-02 stack-card clause (M7) | stack card prints the share of days at <= 0.25x total exposure and the rebound capture; generated once >= 2 de-risk factors act in the recommended book (L5510, L5552) | synthetic two-factor book; EX1 reference numbers 31.0% vs 11.2% need KOSPI history | SYNTH for the mechanism; REFDATA for the EX1 numbers (not asserted in the 9.1 row) |
| T-CAP-01 (M0; "overlay layer cannot emit 0" from M2) | any overlay multiplier outside [0.5, 1.0], or any vt/vs > 1.0, fails schema validation and rules-store validation; the overlay layer cannot emit 0 (L5626, L5570) | inline | SYNTH |
| T-MONO-01 (M5) | for random multiplier vectors m <= m' elementwise on the I-01 fixtures (seed 11), every market's gross and every family's active budget is weakly monotone in its own multipliers, and every cross-partial is 0; the R-15 K/(K-1) re-weighting is the one exception, logged as a governance event (L5676) | I-01 fixtures (M8) | SYNTH on a synthetic multi-market/multi-family book at M5; REFDATA for the literal I-01 fixtures (F-12) |
| T-BASIS-01 (M0; runtime clause M4 / M7; S2 clause M8) | every multiplier has `exposure_basis`; S2 applied to momentum raises; vt is not applied to L/S sleeves or to TS trend (L5628, L5569) | inline rule objects | SYNTH |
| T-PROV-01 (M1) | rows: vendor 6,943.66 (obs_utc 01:30Z, available_at_utc 01:30Z, retrieved_at_utc 01:56Z, `provisional_intraday`); KIS 7,003.74 (available_at_utc 06:30:30Z `calendar_bound`, retrieved_at_utc 06:40:45Z, `official_close`). `pit_value('KOSPI_OFFICIAL_CLOSE', decision_utc=2026-10-02T06:30:30Z, knowledge_utc=..., consumer='R-06', require_session=2026-10-02)` returns `MissingInput("missing")` at knowledge 01:31Z, `MissingInput("provisional_intraday")` at 02:00Z, 7,003.74 [official_close] at 07:00Z. "The fixture is a synthetic store file, exempt from the post-close-file rule." (L5612) | inline synthetic store | SYNTH |
| T-VT-01 (M2) | < 20 valid returns -> status `insufficient_history`; book before first ARMED maps to weight 1.0 status `warmup`, no failure; flagged stale-carry day excluded and the window extends; sigma 0 or not finite -> `MissingInput`; on a book that has been ARMED a store truncated to 15 valid returns -> `MissingInput("missing")`, counts toward the HALT limit, never weight 1.0; simple returns, ddof = 1; reproduces rv20 28.82% and vt 0.694 on 2 Oct (L5673) | synthetic returns; KOSPI official closes to 2026-10-02 for the last clause | SYNTH except the rv20/vt clause = REFDATA (no KOSPI index series locally; `r2_idx_golden_values.csv` ends 2026-09-29, different date) |
| T-RO-01 (M0) | static scan of the whole repository incl. `core/skills` scripts and the commands of every workflow YAML: no order, cancel, withdrawal, deposit-address or transfer call, no import of an order-submission client (forbidden symbols and AST patterns listed in the test); `core/engine/orders` reached only through the simulated order book API; every artifact has `read_only: true` (L5605) | repo source | SYNTH |
| T-RO-02 (M1; I-01 clause M8) | KIS client accepts only an allowlist of quotation endpoints frozen in `config.py`; any trading or account path raises before a request is built; Claude API called without tools, text never parsed by an acting module (L5606) | patched transport | SYNTH; "whether the KIS app key can trade" = OWNER |
| T-CTX-01 (M6) | no acting module imports or reads `context_log`, the 18-indicator sheet's values, the R-18 break log or a refusal book (static import check plus a runtime guard) (L5654) | repo source; baseline today: only `ui/*`, `core/ficc/insights.py` and tests import `core.ficc.macro` | SYNTH |
| T-SCOPE-01 (M8) | (a) R-04 inputs and R-03 paper L/S series failing on 3 consecutive decisions HALT the specification book only; recommended stays ARMED with unchanged weights. (b) missing S&P close on 3 decisions fails the R-28/R-29 FORWARD-SIM books closed, KR recommended stays ARMED. (c) specification-book NAV at -16% HALTs the specification book only. (d) recommended-book NAV at -16% HALTs the recommended book (RISK). (e) exception inside `hedge_state` sets `hedge_credit_off`, HALTs nothing. (f) `context_log` schema failure HALTs nothing. (g) once `verdict_filter` admits R-03, `MOM_PAPER_LS_SERIES` is bound to the recommended book in the same run (governance event) and its failure on 3 decisions HALTs the recommended book too; a book that reads a factor whose acting inputs are not bound to it is refused at load. (h) while R-06 KR is NOT_RUN, a KOSPI close missing on 3 consecutive decisions HALTs `specification:KR` only; `recommended:KR` stays ARMED (L5675) | synthetic store + injected failures | SYNTH |
| T-CAL-02 (M1) | every calendar, regime-tag and publication-schedule file covers >= 60 sessions beyond the decision date; `warn` at 60 left, page at 20; a decision date outside coverage fails closed as an OPS HALT with `reason = calendar_coverage`, never a silent `NotASession`; 2027 KRX, NYSE, Fed, SIFMA files signed off before 2026-11-01 (L2101) | truncated synthetic calendar | SYNTH for the mechanism; sign-off = OWNER |
| T-LAG-01 (M1; card clause and `timing_probe` exception M7) | inject a datum with `available_at_utc > decision_utc` into any acting input -> backtest raises `LookAheadError` and refuses to write the card; at runtime the books the input feeds go HALTED (OPS); a provisional row reaching an acting input is treated the same way; audit recomputes `usable_at` independently of `pit_value` (L5609) | synthetic store | SYNTH |
| T-MISS-02 (M1; risk_model clause and `hedge_state`/`market_vol_target`/`compose` exceptions M2; `concentration_bound`/`drawdown_ladder` exceptions M5) | acting input missing or stale -> state unchanged, `fail_closed=true`, alert, no interpolation; same failure for more than one decision -> HALTED; stale risk_model -> `hedge_credit_off = TRUE`, never HALTED; exception in an acting risk-layer function -> HALTED (OPS) for the books it feeds; exception in `hedge_state` -> `hedge_credit_off = TRUE`, alert, never HALTED (L5625, L5585-5586) | injected exceptions | SYNTH |
| T-ROLE-01 (M1; risk-model clause M2) | stale acting input: miss 1 -> fail closed; miss 2 -> bound books HALTED (OPS), no other book; a fresh decision resets the counter; two acting inputs on one book failing on alternate decisions HALT it at the 2nd decision; stale risk_model -> `hedge_credit_off`, never HALTED; stale context -> label only (L5621, L1964) | synthetic store | SYNTH |
| T-SYN-01 (M1) | "auto" provider degrading to labelled synthetic data for an acting input -> `MissingInput`, `status="synthetic_rejected"`, `fail_closed=true`; same provider for a context item allowed and labelled (L5611) | existing `data._fred_fetch = _boom` patch pattern | SYNTH |
| T-HALT-01 (M5) | NAV breaching exactly -15.00% at close of t (`<=`): HALTED (RISK), exposure 0 on t+1..t+10; automatic re-arm at the close of t+10; both references reset to NAV at re-arm; `post_rearm_cap` 0.5 inside `min()` for weights decided t+10..t+19 (earning t+11..t+20); OPS HALT (stale acting input) clears at the first fresh decision, no refusal window, no reset, no cap; breach with a limit-locked order persisting past t+10 stays HALTED and re-arms at the first later decision at which post-action target weights meet the limit, no reset, 0.5 cap for that decision and the 9 after; KODEX-basket failure beyond its 5 misses is OPS; a lag-audit violation during a RISK HALT keeps the book HALTED after t+10 until operator re-arm, cap window starts at the operator's re-arm decision; sessions = book's primary-market calendar (L5674) | synthetic NAV path + synthetic session calendar | SYNTH |
| T-STEP-05 (M5) | NAV flat at -16% for 30 sessions after a breach at close of t sets `rearm_not_before` once (t + 10 sessions); automatic re-arm at close of t+10, re-enters at t+11 under the 0.5 cap (weights decided t+10..t+19); a second `halt()` while HALTED changes nothing (L3349) | synthetic NAV | SYNTH |
| I-03 (M8) | recommended book never reads a FORWARD-SIM multiplier, a refusal-book multiplier or a non-PASS factor (assertion on the book builder); it refuses R-04; no recommended or specification book reads the R-11 or R-12 multiplier (L5690) | synthetic cards with each disposition | SYNTH |
| I-04 (M5) | overlay 1.0 and whole-book NAV drawdown -12% from the step reference: evaluator BLOCKED for new entries, step multiplier 0.5 composed by `min()` (never 0.25 x vt); after 21 sessions the step reference resets to current NAV, the hard-stop reference does not; steps binding > 10% of days act only in the specification book (L5691) | synthetic NAV | SYNTH |
| I-04b (M5) | -15% book-NAV breach sets that book HALTED (RISK), refuses re-arm for 10 sessions, re-arms automatically, resets both references to NAV at re-arm, caps exposure at 0.5 x vt inside `min()` for 10 sessions; KOSPI VT20 1997-2026 HALT count pinned once computed (section 9.4); on the KOSPI 1997-2026 fixture the book re-enters after every HALT; literal v1.2 rule permanently HALTED from 1997-10 with 714 cycles (G-LAD-01) (L5692) | synthetic NAV; KOSPI 1997-2026 closes | SYNTH for the sequence; REFDATA for the KOSPI 1997-2026 clause (no local KOSPI index history; KODEX 200 from 2007 is not a substitute for 1997) |
| I-06c (M5; `macro_state validates` M6; schema-error HALT M8) | KR decision 2026-11-26 (effective session 2026-11-27; NYSE closed 2026-11-26): `gap_sessions` = 0, VaR scale 1, `kr_open_gap_event` false; books stay ARMED; an out-of-schema context field never HALTs; an acting-field schema error HALTs (OPS) the books the artifact describes (L5696) | existing `data/calendars/KRX.json`, `US.json` cover 2026-2027 | SYNTH |
| T-CLOSE-01 workflow clause (M8) | "the workflow never starts before 06:40:30Z (§3.9)"; quarantine boundary `close_print_bound_utc` + 10 min: KIS close row retrieved at 06:40:29Z is never `official_close`, one at 06:40:30Z is (L5617, L5588) | inline clock | SYNTH |
| T-CARD-03 (M8) | a card file whose verdict is edited to PASS after its run is refused by `verdict_filter`: factor stays in the specification book and VERDICT_INTEGRITY pages; a hand-edited `cards/verdicts.jsonl` row breaks the chain and blocks every admission until restored; a verdict whose `gate_package_md5` differs from the frozen package's, or whose `data_snapshot_id` does not reproduce from the store, is refused (L5665) | synthetic card + chain | SYNTH |
| T-OBS-01 (M8) | each HALT class writes the `runtime[].halt` block of its book and a governance event (L5677) | synthetic | SYNTH |
| T-OBS-02 (M8) | a skipped scheduled run raises MISSED_DECISION (severity page) at the next app start, and the books carry their weights (L5678) | synthetic run_log + calendar | SYNTH |
| T-OBS-03 (M8) | page-severity alerts persist until acknowledged (L5679) | synthetic | SYNTH |
| T-OBS-04 (M8) | exception injected in each acting step writes status = error, raises RUN_ERROR (page), blocks engine_feed, adds 1 to the counter of every book the step serves and HALTs them (OPS, `run_error`) at the limit; the errored decision counts for MISSED_DECISION; exception in `forward_monitor` re-evaluated for every skipped decision at the next successful run (L5680) | injected exceptions | SYNTH |
| T-OBS-05 (M8) | at app start the `governance_events.jsonl` hash chain is verified; a hand-edited row raises GOVERNANCE_LOG_BROKEN (page) (L5681) | synthetic log | SYNTH |
| T-REPLAY-01 (M8) | re-running a past decision from the store at its `knowledge_utc` reproduces the artifact byte for byte after canonicalisation, excluding only `generated_at_utc` and `git_hash`; replay first restores per-book counters, `halt.causes`, derived bindings and covariance carry counts (from at most the last 5 artifacts); `data_snapshot_id` order-invariant and unchanged when a later correction is appended (L5616) | synthetic store | SYNTH |
| I-01 (M8) | end-to-end `macro_daily` for KR decisions 2026-07-30 and 2026-10-02 and US decisions 2026-07-30 and 2026-10-01: all five artifacts valid against schema 2.0; 2026-10-02 uses official close 7,003.74 and flags match section 11; 2026-07-30 KR reproduces vt 0.25 (G-KR-04); zero non-allowlisted KIS requests; `data_ok` passes a stale risk-model input with `hedge_credit_off` set and fails closed on a stale acting input; `verdict_filter` admits only PASS factors and `INVARIANT_STEP`; R-06 KR (NOT_RUN) refused; refusal and FORWARD-SIM books never reach `engine_feed`; decision gates fire on injected failures (L5688) | post-close fixtures (KOSPI official closes, KODEX 200 PDF, market caps, PCE vintages, 10y, USD proxy) | REFDATA for the numeric clauses; SYNTH for gate behaviour on a synthetic store |
| T-HERM-01/02 (M0) | macro suite passes with all network touchpoints patched to raise; after `tests/run_all.py`, `core/rules` and every family ledger are byte-identical; tests write only to temporary copies (L5607-5608) | temp dirs | SYNTH |
| T-SER-02 `pit_value` clause (M1) | `pit_value` raises when a consumer other than a `context` consumer reads a series it has no binding for (L5630) | synthetic registry | SYNTH |

Deferred clauses (9.0b) owned by this area: T-CAP-01 zero-emission clause M2 (L5570); T-BASIS-01 runtime checks M4 / M7 (L5569); T-ROLE-01 risk-model clause M2 (L5578); T-ROLE-02 corr63 clause M2 and FORWARD-SIM clause M8 (L5579-5581); T-LAG-01 card and `timing_probe` clauses M7 (L5582); T-LAG-02 "must change the result" on R-06's vt M2 (L5583); T-MISS-02 splits M2 / M5 (L5585-5586); T-RO-02 I-01 clause M8 (L5587); T-CLOSE-01 workflow clause M8 (L5588); T-HEDGE-01 built-`macro_state` assertion M6 (L5590); I-06c splits M6 / M8 (L5594-5595). "The HALT clauses of T-ROLE-01, T-LAG-01 and T-MISS-02 stay at M1, because M1 builds the OPS-only per-book runtime" (L5597).

Test-plan rules that bind every macro test (L5491-5499): frozen post-close fixtures only under `tests/fixtures/macro/` with an md5 per file; tiers `fast` (<= 10 minutes total), `golden` (<= 2 hours), `freeze`; every test carries `runs_from`; "A verdict derived from a statistic within tolerance of its threshold is asserted as a class ... never as a point"; refined 9.1 / 9.2 rows govern over the verbatim 9.0 council rows (L5505).

---

## E. Interfaces across milestones

Needs from earlier milestones:

| From | Name | Shape |
|---|---|---|
| M0 | rules store v2 loader | `get(key) -> scalar/dict` with `{ref}` resolution; `config_hash() -> str`; validation refusing `combine != min`, multipliers > 1.0, DO-NOT-BUILD shapes |
| M0 | governance appender | `append_event(kind, book_id, rule_id, key, old, new, actor, reason, refs) -> None`; `verify_chain(path) -> bool` |
| M0 | artifact writer / validator | `write_artifact(obj, kind) -> Path`; `validate(obj, schema_id) -> (acting_errors, display_errors)`; quarantine |
| M1 | PIT layer | `pit_value(...) -> PITValue | MissingInput`; `data_snapshot_id(knowledge_utc)`; `is_stale(...)`; `RunContext` |
| M1 | calendars | `decision_time_utc`, `close_print_bound_utc`, `usable_at`, `is_session`, `gap_sessions`, coverage check |
| M1 | per-book runtime (OPS) | `runtime_halt(book_id, cls, reason)`, `runtime_rearm(book_id, mode, operator=None)`; `book_state(book_id) -> {engine_state, halt, consecutive_failures, book_counter, ...}`; input/book counters |

Exposes to later milestones:

| To | Name | Shape |
|---|---|---|
| M2+ | `compose(vt, overlays, ladder, post_rearm_cap) -> float`; `check_composed(...)` | pure, raises on bounds / mismatch |
| M2+ | `market_vol_target(market, decision_utc, estimator="sma20") -> VTResult` | per-book mapping `insufficient_history -> warmup | MissingInput("missing")` done by the book builder, not the function |
| M4 | `base_weights(decision_utc) -> dict[(market, family), float]`; `apply_overlays(composite, multipliers, basis) -> Weights`; `composite_weights`; `risk_layer` | no renormalisation (T-MONO-01) |
| M5 | `drawdown_ladder(nav_path, decision_utc) -> LadderState`; `concentration_bound(market, decision_utc, template) -> ConcentrationBound`; RISK class in the runtime; `Outcome.BLOCKED`; `simulated_fill` | names in B.3 |
| M6 | `build_macro_state(market, decision_utc) -> dict`; `build_overlay_decisions(market, decision_utc) -> list[dict]`; `build_context_log(decision_utc) -> dict` | schema 2.0 |
| M7 | card harness reads `compose`, `risk_layer` conventions; `cards/verdicts.jsonl` writer | R-22 rule 6 decides whether the hard stop and caps are in card books |
| M8 | `macro_daily` pipeline: `run(market, session_date, run_mode) -> run_record`; gates `data_ok`, `bounds_ok`, `verdict_filter`; `missed_decisions()`; alert sink API `raise_alert(code, severity, component, series_id=None, books=())` | B.8 |
| UI | `macro_state`, `overlay_decision`, `context_log`, alerts, owner decisions | read-only display; only `recommended:<m>` weights shown as a recommendation |

Milestone order for this area (L6360-6372): M0 bounds + appender + schemas; M1 PIT + calendars + OPS runtime; M2 `compose`, vt, hedge state; M4 family level and books; M5 RISK class, ladder, caps, BLOCKED, fill; M6 builders + Macro page; M7 stack card; M8 workflow. "Do not start M(k+1) until M(k)'s acceptance tests pass in `tests/run_all.py`."

---

## F. Ambiguities, contradictions and conservative readings

| # | Issue (lines) | Conservative reading adopted |
|---|---|---|
| F-1 | `core/skills/workflows/macro_daily.yaml` (L848, L1189, L3481, L6370) cannot coexist cleanly with the module `core/skills/workflows.py`; existing workflows are parsed from the external repo `<config.skills_root()>/workflows/*.yaml` (`workflows.py:167`), require a top-level `id` (`:138`), and a step without `skill` is dropped (`:98`), so the spec's `name:` / `gate:` shape does not parse; existing skills run as subprocess scripts (`runner.py`), whereas `macro.*` steps are in-process QUANTGEN functions | Build an in-process pipeline `core/skills/macro_daily.py` with the 12 steps and 3 gates as functions; keep a declarative `core/skills/macro_daily.yaml` (with `id: macro_daily`) for display and for T-RO-01's "commands of every workflow YAML" scan. Do not route macro steps through the external-repo runner |
| F-2 | Existing `EngineState` is one global state, "This program never re-arms itself", restart always lands in DISARMED and mode is deliberately not persisted (`core/engine/state.py:10-13, 161-186`). Spec requires per-book states, automatic DISARMED -> ARMED, automatic RISK and OPS re-arm, persisted book state (L1179-1180, L1187, P16 L637) | Add a separate per-book runtime (`core/engine/books.py`) for simulated macro books; leave `EngineState` / `EngineRuntime` semantics and their acceptance tests untouched. Book states (incl. ARMED) are restored from persisted state on restart, because DISARMED is reachable again only by owner retirement and "A retired book never re-arms"; missed decisions are surfaced by `MISSED_DECISION`. Owner should confirm that the "never re-arms itself" contract stays scoped to the operator rule engine |
| F-3 | Spec treats `core/rules` as the home of section 7 parameters and section 7.1 rule objects (L916, L4127, L4689 "map them onto the store's actual model"); the existing model is an operator price-trigger `Rule` (side, conditions, limits) with no such fields | Separate macro rules module and JSON file; do not add macro fields to `Rule`. Edit history / revision log implemented in the new store |
| F-4 | "A 6-component composite. Its components are not listed" (L1167). Actual components are per-symbol technical scores (trend50, trend200, 63-session momentum, rsi, macd, vol posture); no cross-sectional momentum, flow or quality component, and no weight vector. `composite_weights(i | active_budget, gross)` (L876) has no existing counterpart | All six components stay untagged (`family = None`, multiplier 1.0) until the owner fills BL-G07. Under any plausible mapping (trend/momentum/macd -> `ts_trend`, overlay-exempt; rsi -> `reversal`, fixed 1.0) no component receives a multiplier != 1.0, so the composite score is unchanged in v2.0. `composite_weights` for a market without factor sleeves returns the single declared instrument line at weight gross(m); family active budgets are computed and recorded in `overlay_decision` but act only on sleeves that exist |
| F-5 | `compose(...)` "raises on product" (L1058) while its formula is a `min()`; a pure function cannot observe a product | `compose` computes only the `min()` form and raises on out-of-range arguments; the product check is `bounds_ok` recomputing composed from recorded factors (L881) plus rules-store refusal of `combine != min`. The family-level `base_weight x vs x min(overlays)` (L866-868) is the prescribed form: vs is sizing in [0,1], not an overlay |
| F-6 | Config paths `calendars.regime_tags_file: core/calendars/data/kr_regime_tags.yaml` and `data_contracts.source_exceptions: core/calendars/data/source_skipped.yaml` (L4192, L4229) assume a `core/calendars/` package; repo has `core/calendars.py` with data in `data/calendars/` where every `*.json` is loaded as a market calendar | Keep the module; put new files in `data/macro/calendars/`; store the actual path under the same keys (path is "proposed", L89) |
| F-7 | Market ids `KR, US, JP, ...` (L1036) vs existing calendar/venue codes `KRX, US, TSE, SSE, HKEX, TWSE` | Explicit map in `core/markets.py`; new calendar functions accept only the 6.1 enum |
| F-8 | Existing calendars cover 2026-01-01..2027-12-31 (SSE to 2026-12-31), holidays + special sessions only; no effective-dated close times, Saturday sessions, CSAT windows, random-end regimes, FED/SIFMA/publication calendars (L4174-4193; owner actions L76). `calendars.STALE_WITHIN` is 60 calendar days; spec is 60 sessions | Effective-dated rules for 2015-06-15 / 2016-08-01 and US DST are encodable from the spec text; pre-2015 conditional random end, Saturday close times, pre-2016 CSAT window, lunch-break dates and the ETF tick table are OWNER inputs: until signed, decisions before the covered range fail closed (`calendar_coverage`). Coverage check counts sessions, not days |
| F-9 | Regime read (L1124-1126): existing `Regime` dataclass and "regime read" wording present five rule-based labels (`risk-on/risk-off/neutral`, `strong/weak/range`, ...) as a regime | It is not a regime model, so it may stay only as a descriptive text summary: relabel in brief and Macro page (no "regime" state presentation), never feed quant/engine. `core/quant/signals.py:151-153` labels its `vol` component "Volatility regime" with words `elevated` / `normal`: rename to avoid reuse of R-06's label vocabulary (display-only change) |
| F-10 | Sheet method: changes are positional over observations and z uses population std on 252 obs (`macro.py:35-36,124-126`); spec requires causal windows ending at `decision_utc` (L1123) and forbids positional shift on gapped series for acting paths (T-LAG-02) | Sheet stays CONTEXT/display only; `context_log` items read through `pit_value`; no acting code may reuse `Series.change()` |
| F-11 | `pit_value` returns `MissingInput("provisional_intraday")` for a close-type acting read whose status is anything other than `official_close` (L1007-1008), i.e. also for `vendor_close` | Implement literally; map to `provisional_rejected`. All local cached Yahoo closes are `vendor_close`, so no acting read can succeed on them in `run_mode = live`; backtests may read them only if the card header declares that vendor as `data.source` |
| F-12 | T-MONO-01 runs from M5 (L5555) but is stated "on the I-01 fixtures" (L5676), which are M8 REFDATA | Run at M5 on a synthetic book of the same structure; re-run on the I-01 fixtures when they exist |
| F-13 | Section 9.0 verbatim rows differ from refined rows: T-CAP-02 "final = vt x min(overlays, ladder)" without `post_rearm_cap` (L5510 vs L5627); I-04b "resets the hard-stop reference" vs "both references" (L5514 vs L5692); T-PROV-01 "MissingInput(provisional_intraday) at 10:31 KST" vs `missing` at 10:31 and provisional at 11:00 (L5509 vs L5612); R-35 "only PASS and BUILD-AS-INSURANCE" vs also `INVARIANT_STEP` (L5542 vs L5688) | Refined 9.1 / 9.2 / rule-table rows govern (L5505) |
| F-14 | HALT threshold wording: "more consecutive decisions than its declared limit (default: more than one)" (L1178) vs `halt_after_consecutive_decisions: 2` (L4231) vs T-SCOPE-01's "3 consecutive decisions" (L5675) | HALT when the counter reaches 2 (the 2nd consecutive failed decision); T-SCOPE-01's 3 decisions is a sufficient condition, not the limit |
| F-15 | Heartbeat trigger (L1178, L4359): existing `QuoteFeed` has per-symbol miss counts, no session heartbeat; v2.0 daily books read closes from the PIT store, not the QuoteFeed | Implement the trigger and its 60 s / 5 min rule on a heartbeat signal derived from `QuoteFeed`; bind it only to books that take intraday simulated entries (none among the v2.0 daily books). Synthetic test only |
| F-16 | `runs: [after_close: KRX, after_close: NYSE]` and "at every scheduled run" (L1194, L1246): QUANTGEN is a desktop app with no scheduler; `pit_snapshot` may retry until `next_session_open_minus_30min` | Manual "Run macro_daily" action plus missed-decision check on app start; an in-app timer while the app is open is optional. No OS-level scheduled task is created. Runs after the deadline are recorded `late` |
| F-17 | Live acting inputs (KRX official close with exchange print time, KODEX 200 PDF, market caps, KIS 10y quote, USD live proxy) need KIS credentials and live sessions; the KIS quote-field check needs about 20 sessions (L44) | Without them every book stays DISARMED (the automatic arming condition "every acting input bound to the book is fresh" never holds); features labelled UNVERIFIED. No synthetic or vendor substitute for acting reads |
| F-18 | `evaluator_block(...)`: "new entries only"; "Holds and exits are never blocked" (L1079, L1183). Existing rules are operator buy/sell price triggers; "new entry" is undefined for them | A new entry = a BUY-side simulated order in the blocked market; SELL-side rules are never blocked. `Outcome.BLOCKED` is a new enum value; existing outcomes unchanged |
| F-19 | `risk_layer(...)` and `engine.orders(final_weights)` (L877-878) are used in the formula but absent from the 3.5 list; existing `OrderBook` is rule-triggered, not weight-driven | `risk_layer` is an internal function of `core/quant/risk` (caps, single-name active cap, no renormalisation). Weight-driven simulated books live in `core/engine/books.py` and emit simulated orders through the existing `OrderBook.place` API only |
| F-20 | Spec maps the gate package to `core/quant/backtest` (L914, L1089); the gate actually lives in `core/quant/validate.py` and `core/quant/strategies.py`. Existing `strategies.simulate` charges turnover on the session the weight changes; T-COST-01 says "on the day the new weight earns" | New gate-package module(s) reuse `validate.py` statistics; cost-timing convention to be settled by the cost/gate brief before goldens are compared |
| F-21 | UI box lists "owner decisions D1-D5" (L762) while the registry and T-OWNER-01 use D1-D6 (L4138-4152); M6 says "listing every open owner decision" (L6368) | Show every decision in the registry with its status |
| F-22 | `decision_time_utc` is "the scheduled official close, NOT decision_utc" (L1024) while section 7 has `time.markets.US.decision_utc: close_print_bound_utc` (L4162) | Never stamp `macro_state.decision_utc` from `decision_time_utc`; always from `close_print_bound_utc` |
| F-23 | Tech-fund R3 cross-spec amendments touching composition inputs: XS-21 proposes `base_weight = w / 3` (R3 L1309) against v2.0's `IV_m x 1/K_m` with priors as filters (L858-861, L95 "answered"); XS-01/02/17/18 lower priors (Korea flow 3 -> 1, Korea ST reversal -> 0, crypto ST reversal -> 0, Korea 12-7 replaced by FORWARD-SIM FS-2); XS-22 proposes a 0.35 pair cap where v2.0 defaults D1 to `msci_25_50` with `pair_35` as an option | Keep the v2.0 formula and D1 default (binding). Treat R3 prior supersessions as registry values awaiting owner confirmation; applying a prior of 0 removes a family from A_m and raises the others by K/(K-1) (the documented exception, governance event), so it is not applied silently. No Korean factor sleeve exists today, so no book changes either way |
| F-24 | Recommended book while R-06 KR is NOT_RUN: vt enters as 1.0 and gross is set by the concentration bound (L886), so the displayed recommendation is gross 0.685 with no vol target | Implement as written; label the recommended book's vt as "1.0 (card NOT_RUN)" |

---

## G. DO-NOT-BUILD items and invariants that bind this area

Principles (section 1; "enforced in code, as assertions, schema bounds and rules-store validation, not by convention", L489):

- P0 read-only by construction: no module may contain, import or call an order, cancel, withdrawal, deposit-address or transfer path on any venue; KIS read-only quotations only; outputs are an artifact, a simulated-order-book entry, a costed backtest / forward-simulated book, a model card, or a displayed exposure recommendation (L491-499). Section 3.10: no broker path is designed.
- P1: no macro or overlay module may create, flip or close a simulated position on its own; overlays output multipliers only (L502-505).
- P2: overlay multipliers in [0.5, 1.0]; vt and vs in [0, 1.0] with no floor; no multiplier anywhere above 1.0; composition by `min()`, never by product; composed(m) >= 0.5 x vt outside HALTED (floor binds `composed`, not `gross` or final weights); 0x only from the risk layer (backtests) or a book's HALTED state; "The overlay can never output a value below 0.5" (L508-517).
- P7: only PASS cards feed the displayed recommendation (CARD-O as recommendation, CARD-P as insurance); FORWARD-SIM, specification-only and refusal factors stay out of the recommended book; "a rejected card is not deleted" (L556-565).
- P8: every multiplier declares `exposure_basis` (`active` or `total`) (L568-570).
- P16: every hard stop has an explicit, automatic re-arm; only RISK carries the 10-session refusal and the 0.5x cooling-off; a HALT is scoped to the book whose own trigger fired (L636-640).
- P17: each new overlay judged incrementally on the current recommended book; stack CARD-P once two or more de-risk factors act; ladder steps binding on more than 10% of days act only in the specification book until their CARD-P passes (L643-646).
- P18: no acting decision on a provisional, intraday, bar-derived or stale input; only `acting_exposure` inputs can escalate to HALTED and only for the books they are bound to; a `risk_model`, `context`, `forward_sim` or `history` input never HALTs a recommended book (L648-651).
- P19: no jump-model, Markov-switching, GMM or change-point "regime" state acts on exposure or is shown on any page; sigma_hat display labels are volatility labels and stay; BOCPD probability only in the R-18 research log (L653-656).

Section 3 invariants:

- HALTED is never an argument of `min()`; it sets that book to 0x; other books continue (L874).
- No renormalisation of freed budget across families or markets (L883).
- A stock book is never used as a market-gross scalar (L895).
- No function reads "now"; `knowledge_utc` is pinned once per run and written to every artifact (L1001-1003, L1105).
- No function reads a raw DataFrame of a series directly; all reads through `pit_value` (L1106).
- No synthetic, provisional or interpolated acting input (L814, L1108).
- No acting function reads `context_log`, the R-18 break log or a refusal book (L1113).
- No daily close is derived from intraday bars (L1177).
- The recommended book is never HALTed by a factor or input it does not read (L1178).
- FORWARD-SIM and refusal books never pass through `engine_feed` (L1184, L1231-1232).
- The Claude API receives computed numbers only and never decides; credentials env-only (L1253).
- Overlays never create a new component and never change a component's sign (L1171).
- Z-scores are never thresholded for exposure; the regime read never feeds signals, risk or the engine (L1123, L1126).
- Tests are hermetic, read frozen post-close fixtures, and write only to temporary copies (L5491-5495).

Refused shapes enforced by rules-store validation (section 10.3, L6233-6250) that this area must wire: order/cancel/withdrawal/deposit-address/transfer path or broker adapter (item 21; T-RO-01, T-RO-02); multiplier, weight or vol-target cap above 1.0 (2, 8; T-CAP-01); composition other than `min()` or a product of de-risk multipliers (31; T-CAP-02); regime-model source acting or displayed, smoothed or forward-looking label (11c, 24, 27); `instrument_book: KRX_stock_book` on a market-gross scalar (33); a recommended book reading a FORWARD-SIM, refusal-book or specification-only multiplier (22; I-03); a production rule reading a value-timed or unpublished series, a provisional or bar-derived acting close (19, 26).

Never build (section 2 DROP rows; L709-743): real-yield momentum gate; curve re-steepening gross cut; VIX term-structure switch or new-entry block; HY OAS quality tilt; PMI value tilt; Fed net-liquidity crypto scaling; ISM/2y tilts; BoJ-meeting tilts; Korea SOX 60-day trend gate; Korea flow-regime weight; Taiwan semis gate; India Brent gate; four-state regime classifier with family multipliers; Korea SOX x KRW gross scalar; 24 h event blackout; any overlay range above 1.0 (the prior 0.5-1.5); `max(sigma_hat, implied)` sizing; R-11 (S1) and R-12 (S2) in any book other than a display-only refusal book; R-04 in the recommended book. The tech-fund DO-NOT-BUILD list (R3 section 6, DNB-TF-01..17) is additive and is covered by its own brief.
