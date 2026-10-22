# spec_M6_context_breaks — implementation brief (QUANTGEN v2.0, milestone M6 "Context and breaks")

Source: `QUANTGEN_Quant_Council_2026-10-03/claude_code/QUANTGEN_MACRO_INTEGRATION.md` (cited `L<line>`), task file `prep/tasks/M6.json` (TASK-M6-01 … 06), backlog `QUANTGEN_MACRO_BACKLOG.md` (cited `BL:L<line>`), tech-fund synthesis `QUANTGEN_techfund_research/research_notes/R3_TF_neural_link.md` (cited `TF:L<line>`).
Ranges read in full: L1115-1163 (§3.6), L1667-1694 (R-13), L1775-1795 (R-18), L3859-3907 (§6.4), L5489-5598 (§9 preamble, §9.0, §9.0a, §9.0b). Also read because the ranges or tasks cite them: Quick start L14-100, §1 P0-P19 L487-656, §3.1-3.5 L749-1113, §3.9 L1189-1253, §4.1 L1270-1384, §4.2 L1386-1449, R-08/R-09/R-10 L1592-1637, R-19 L1813-1981, R-20 tags L2034-2101, R-25 L2686-2704, R-28 rule L2964-3000, R-32/R-33 L3361-3393, §6 conventions + §6.1 + §6.2 L3501-3798, §6.6 L4094-4119, §7 L4123-4173 / L4195-4243 / L4270-4411 / L4465-4476 / L4620-4684, §7.1 L4687-4705, §8.8 L5303-5365, §8.10 L5441-5487, §9.1/9.2 rows of the cited tests, Level-1 tolerances L5734-5736, §9.4 L5994-6014, §9.5 L6016-6035, §10 items 21-37 + §10.3 + §10.4 L6160-6260, §11 L6264-6352, §12 M6 row L6368.

Repo state checked 2026-10-05: no M0-M5 code exists (`pit_value`, `MissingInput`, `value_status`, `context_log`, `governance_events`, `macro_state`: 0 hits in repo `*.py`). `core/ficc/macro.py` (309 lines) and `ui/macro_page.py` (232 lines) exist. `core/ficc/macro` is a single module, not a package. Importers of `core.ficc.macro` today: `ui/macro_page.py:24`, `ui/fcharts.py:32,410`, `core/ficc/insights.py:31` (TYPE_CHECKING) and `:580` (`__main__`), `tests/ficc_acceptance.py:23`. No file under `core/quant/` or `core/engine/` imports it (T-CTX-01 baseline is green). `tests/fixtures/` and `tests/macro_acceptance.py` do not exist. File names below follow the sibling brief `spec_architecture.md` (A.3): `core/ficc/context_log.py`, `core/ficc/macro_artifacts.py`, `core/ficc/pit.py`, `core/ficc/contracts.py`, `core/rules/macro_rules.py`, `core/rules/governance.py`, `core/engine/books.py`, `tests/macro_acceptance.py`, `config.macro_artifact_dir()`.

Rule for silence (L89): "no exposure change, specification book only, fail closed".

---

## A. Scope

| Task | Deliverable (one line) | Target files (E = exists, N = proposed new) |
|---|---|---|
| TASK-M6-01 (spike, BL-G06) | The 18 indicators, z-window and regime-read method read from the code and mapped onto §3.6; verdict "rule-based, not a regime model"; relabel as descriptive text; no acting reader | E `core/ficc/macro.py` (add `SHEET_ITEMS` map; no behaviour change), E `ui/macro_page.py`, E `ui/fcharts.py:395-397`, E `core/ficc/insights.py:390,542-543` (wording only) |
| TASK-M6-02 | `build_context_log()` → one `quantgen.context_log` v2.0 per decision; R-13 items with `vintage`, `retrieved_at_utc`, first print / latest / vintage date; live snapshots; stale label; refuse + quarantine + alert on failure, never HALT | N `core/ficc/context_log.py`; registry rows for C-role series (M1 registry file); rules-store block `context_log` (M0 store) |
| TASK-M6-03 | Context isolation: static import check with a positive control + runtime guard on every reader of `context_log`, the sheet, the R-18 logs and refusal books | N `tests/macro_acceptance.py` (T-CTX-01); guard in N `core/ficc/context_log.py`; one guard call in E `core/ficc/macro.py::macro_sheet` |
| TASK-M6-04 | R-18: `BreakEvent`, `log_break()`, official-framework trigger (shrink macro-conditioned multipliers to 1.0 + forward-record start), write-only research log (statistical flag, v1.2 2×-median flag, BOCPD probability), market-structure break log from regime-tag transitions, re-anchor eligibility predicate | N `core/ficc/context_log.py` (same file; see F-22); E `core/calendars.py` (`regime_tags`, M1); rules-store block `breaks` |
| TASK-M6-05 | `build_macro_state()` (one per market per decision) and `build_overlay_decisions()` (one per market × family), always written, validated by the M0 validator | N `core/ficc/macro_artifacts.py` (M0 creates the file for the validator/writer; M6 adds the builders) |
| TASK-M6-06 | Macro page panel from validated artifacts (macro_state, overlay_decision table, verdict/disposition badges, both vol labels, event calendar, context log, owner decisions D1-D6); `macro_state` section in the daily and weekly brief | E `ui/macro_page.py`; E `core/ficc/macro.py` (`daily_brief` / `weekly_brief` gain an optional section); UI detail in sibling brief `code_ui.md` |

M6 exit list (L5556): `T-CTX-01/02, T-BREAK-01`. Clauses that join at M6 (L5590, L5594): the built-`macro_state` assertion of T-HEDGE-01; "`macro_state` validates" of I-06c. §12 M6 adds (L6368): "§11's context values are reproduced; every sheet item appears in `context_log` with `from_sheet=true`"; "The Macro page panel, listing every open owner decision". "Until M6, tests assert the outputs of the functions that fill these artifacts … never a built artifact" (L6368).

---

## B. Build spec, module by module

### B.0 Rules that bind every function here

- Signature rule (L1105): every function takes `decision_utc` and the run's pinned `knowledge_utc` (parameters or one `RunContext{decision_utc, knowledge_utc, run_mode}`), never "now"; data is read only through `pit_value(series_id, decision_utc, knowledge_utc, consumer, require_session=None)` (L998-999). Context reads use `consumer = "R-13"`.
- "No function reads a raw DataFrame of a series directly" (L1106). The existing `macro_sheet()` (`load_many`) stays as the legacy display path only; `build_context_log` does not call it.
- Context role (L1110, L1878): "a **context** input is labelled 'stale' (status `stale`, value shown)"; "`context`: the item is labelled `stale` in `context_log`. Nothing else happens." §7: `data_contracts.on_failure.context: {action: label_stale}` (L4236).
- Never HALT (L1178, L4362-4363): `never_halt_on: [… context_input_stale, … display_or_context_field_validation_failure, context_log_or_event_calendar_validation_failure]`.
- "No acting function may read `context_log`, the R-18 break log or a refusal book (T-CTX-01, I-03)" (L1113).
- P9 (L573-577): Sahm, curve and probit, Taylor residuals, real yields, term premium, breakevens, credit levels, survey data, Street and Fed projections "are logged daily and never act"; includes every sheet indicator that is not an acting input and "leverage and flow monitors, VRP, live implied-vol snapshots and turbulence"; "Acting on any of them requires a new card."
- P19 (L653-656): "No jump-model, Markov-switching, GMM or change-point 'regime' state acts on exposure or is shown on any QUANTGEN page in v2.0." "A BOCPD scale-break probability may be written to the R-18 research log only: never acting, never displayed".
- Decimals inside the core, % and bp only in the UI (L373). See F-9 for the unit of `context_log` values.
- Exception isolation (derived from L1240-1243 + L3370): `macro.build_artifacts` is inside the acting step range "pit_snapshot through verdict_filter", where a raised error counts a failed decision for every book and can HALT (OPS `run_error`). Therefore `build_context_log`, `log_break`, the research-log writers and `sync_market_structure_breaks` are each called inside their own `try/except Exception` by the caller: on exception → alert + quarantine record, the step continues, no book counter moves. Without this wrapper a context failure would HALT books, which L3370 forbids.

### B.1 TASK-M6-01 — BL-G06 result (read from `core/ficc/macro.py`)

BL-G06 asks (BL:L1441-1445): role per indicator (CONTEXT by default), timing rule, whether the z-window is causal, whether the regime read uses smoothed or filtered probabilities.

**The 18 indicators** (`INDICATORS`, `macro.py:54-73`). All are CONTEXT (role C, L1401). None is in the §3.6 acting / risk-model table (L1137-1144) except DGS10's backtest binding.

| # | id | label | unit | provider | §3.6 class (L1155-1163) / R-13 row | registry binding today (§7 L4246-4269) | timing |
|---|---|---|---|---|---|---|---|
| 1 | DGS2 | UST 2y | pct | FRED | policy rates / curve; R-13 "2y, 10y, 30y" (L1681) | none → context | publication (H.15: 16:15 ET next Fed business day, L1299) |
| 2 | DGS10 | UST 10y | pct | FRED | same; "the 10y is also a risk-model input to corr63 and the R-12 refusal book's input" (L1155) | `[{role: risk_model, consumer: corr63_backtests}, {role: context, consumer: R-12_refusal_book}]` (L1936) | publication, strict H.15 |
| 3 | DGS30 | UST 30y | pct | FRED | same | none | publication |
| 4 | T10Y2Y | 2s10s | bp | FRED | curve slope; level + z only. "Do **not** log 10y–2y as a prior" (L1679): no probit from it | none | publication |
| 5 | DFII10 | 10y real (TIPS) | pct | FRED | real yields (L1156); R-13 "`DFII10` level and 20/63-day change" (L1681) | none | publication |
| 6 | T10YIE | 10y breakeven | pct | FRED | breakevens (L1682) | none | publication |
| 7 | SOFR | SOFR | pct | FRED | policy rates | none | publication |
| 8 | DFF | Fed funds | pct | FRED | policy rates | none | publication |
| 9 | BAMLC0A0CM | IG OAS | bp | FRED | credit (L1157); not in R-13's list → "Existing sheet items" row (L1694) | none | publication ("posts with ≈ 1-day lag", L1433) |
| 10 | BAMLH0A0HYM2 | HY OAS | bp | FRED | credit; R-13 "HY OAS and BAA10Y levels and 21-day changes" (L1683); "on FRED only since 2023-10" (L1433) | none | publication |
| 11 | DTWEXBGS | Broad USD | level | FRED | "CONTEXT (DTWEXBGS included)" (L1158); "DTWEXBGS → `context`; it is never an acting input" (L1886) | `DTWEXBGS: context` (L4265) | publication (H.10 weekly, Mondays 16:15 ET, L1301) |
| 12 | DEXUSEU | EUR/USD | fx | FRED | FX | none | publication (H.10) |
| 13 | DEXJPUS | USD/JPY | fx | FRED | FX; R-13 "USD/JPY and its distance to the 160–164 zone" (L1684) | none | publication (H.10) |
| 14 | DEXKOUS | USD/KRW | fx | FRED | "USD/KRW feeds only the R-11 refusal book" (L1158); labelled proxy; "Production never reads DEXKOUS" as an input (L1414) | `DEXKOUS: context` (L4266) | publication (H.10) |
| 15 | VIXCLS | VIX | level | FRED | "VIX/VIX3M feed the R-08 annotation (no exposure effect)" (L1160) | none | publication (FRED posting time, L1426) |
| 16 | DCOILWTICO | WTI | level | FRED | oil: "CONTEXT; oil feeds Monte Carlo scenarios and replays" (L1159) | none | publication |
| 17 | ZN=F | 10y note future | level | Yahoo | not in the §3.6 table → CONTEXT by rule 1 | none | value_proxy (vendor close) |
| 18 | GC=F | Gold | level | Yahoo | "Oil (named series), gold, copper: CONTEXT" (L1159) | none | value_proxy |

**Z-score and change windows** (`macro.py:35-36, 119-130`): `_Z_WINDOW = 252` — the last 252 observations of the loaded series (all of them if fewer), ending at the last loaded observation; `z = (x[-1] − mean) / std` with numpy population SD (ddof 0), `0.0` when SD is 0; `pct_1y = mean(x ≤ x[-1])`. Changes `chg_1d/1w/1m/3m` are over 1/5/21/63 observations (positional), weekend rows dropped (`_weekdays`). The window is trailing, so it is causal relative to its last observation. v2 requirement (rule 2, L1123): "computed causally, on expanding or trailing windows ending at `decision_utc`, and never thresholded for exposure (P6, P9)". M6 therefore recomputes the z on the PIT-visible rows (`available_at_utc ≤ decision_utc`, `retrieved_at_utc ≤ knowledge_utc`) and writes `zscore_window = "trailing_252_obs"` (or `"trailing_<n>_obs"` when fewer; `zscore_causal = null` when n < 2 or SD = 0).

**Regime-read method** (`macro.py:161-186`): five threshold rules, no probabilities, no latent state, no smoothing.

| Field | Rule in code | Label set |
|---|---|---|
| `curve` | `curves._regime(d10, d2, d10 − d2)` on 20-session changes of DGS10 and DGS2 | `CURVE_REGIMES` (7 strings: bull/bear steepener, bull/bear flattener, parallel up/down, unchanged) |
| `risk` | `risk_z = (z_1y(VIXCLS) + z_1y(BAMLH0A0HYM2)) / 2`; `> 0.75` → `risk-off`; `< −0.5` → `risk-on`; else `neutral` | `RISK_REGIMES` |
| `dollar` | DTWEXBGS 1-month (21-obs) relative change `> 0.015` → `strong`; `< −0.015` → `weak`; else `range` | `DOLLAR_REGIMES` |
| `inflation` | `_trend(T10YIE.chg_1m, 10 bp)` | `TREND_REGIMES` (rising / falling / stable) |
| `real_rates` | `_trend(DFII10.chg_1m, 15 bp)` | `TREND_REGIMES` |

**Verdict.** Not "a regime model (Markov switching, HMM, jump model, mixture or change-point)" (L1125). Rule 3 second bullet applies (L1126): "it may stay in the brief as a descriptive text summary of the indicators, computed causally from filtered values. It is never presented as a regime state, never reuses the calm / normal / elevated / stressed names (they belong to R-06's volatility labels), and never feeds `core/quant/signals`, `core/quant/risk` or the engine." §7 (L4468): `existing_sheet: {all_items_context_unless_acting: true, zscores: causal_display_only, regime_read: removed_if_regime_model_else_text_only}`. Label check: none of the 16 distinct label strings equals calm / normal / elevated / stressed.

**Required edits (wording / presentation only; no numeric change):**

| File:line | Now | v2 |
|---|---|---|
| `ui/macro_page.py:139-145` | chip row `curve: / risk: / dollar: / breakevens: / real yields:` (state badges) | remove the chips; keep `rg.summary` as one text line under a caption such as "Descriptive read of the indicators (rule-based; feeds no signal, risk or engine decision)" |
| `ui/macro_page.py:1-13, 194-195`, `_REGIME_TOKEN` (`:35`) | docstring and subtitle say "regime read" / "regime chips" | "descriptive read"; delete `_REGIME_TOKEN` |
| `ui/fcharts.py:395-397` | chart title carries `curve …, risk …, USD …, inflation …` | title = `Macro sheet {as_of} — 1y z-scores` |
| `core/ficc/insights.py:390` | "the 20-session regime is a {curve}" | "the 20-session curve move is a {curve}" |
| `core/ficc/insights.py:542-543` | report prompt asks for "the curve regime" / "the risk regime" | "the curve move" / "the risk tone" |
| `core/ficc/macro.py:235` (`daily_brief`) | payload key `"regime"` | see F-2 (keep key, add `"descriptive_read_note"`; or rename with the one test line `tests/ficc_acceptance.py:540`) |
| `core/ficc/macro.py` | — | add `SHEET_ITEMS: dict[str, dict]` = the table above (`role`, `timing`, `r13_row`), consumed by `build_context_log` |

`Regime`, `sheet.regime`, `CURVE_REGIMES` etc. are internal names referenced by 20+ call sites and three test files; they are not a page presentation and stay (F-2). No removal from pages is scheduled because the read is not a regime model.

### B.2 `core/ficc/context_log.py` — `build_context_log` (TASK-M6-02)

```python
CONTEXT_CONSUMER = "R-13"

def build_context_log(ctx: RunContext) -> dict
#   spec signature (L1075): build_context_log(decision_utc: datetime) -> dict   # "items carry vintage and retrieved_at_utc"
#   returns a dict that validates against quantgen/context_log.v2.0 (§6.4); acts = False
def write_context_log(log: dict) -> Path | None
#   validate (M0 validator) -> OK: <artifact_dir>/context_log/<decision_utc as YYYYMMDDTHHMMSSZ>.json
#   invalid: NOT written to the artifact dir; written to <artifact_dir>/quarantine/ with its errors; alert raised; returns None; never HALT (L3370, L3865)
```

One log per decision: "`as_of_utc` is the run's `decision_utc` (one log per decision)" (L3865). With two daily workflow runs (`after_close: KRX`, `after_close: NYSE`, L1194) there are two logs per day, one per `decision_utc`.

**Envelope** (required, L3869): `schema = "quantgen.context_log"`, `schema_version = "2.0"`, `read_only = true`, `generated_at_utc` (wall clock at write; the only "now"; volatile field L4683), `knowledge_utc` (pinned), `git_hash`, `config_hash` (hash of the rules-store state, L3508), `data_snapshot_id` (`data_snapshot_id(knowledge_utc)`, L1014), `decision_utc`, `as_of_utc = decision_utc`, `items[]`, `acts = false`; `extras` open.

**Item fields** (L3876-3888). Required: `name, series_id, value, obs_date, available_at_utc, retrieved_at_utc, vintage, source, timing, value_status, stale`. Optional: `first_release, latest, vintage_date, zscore_causal, zscore_window, from_sheet, range, note`.

| Field | Fill rule | Source line |
|---|---|---|
| `name` | human label; ends with the unit in parentheses (F-9); "Every series is named (no unnamed 'Brent')" | L549, L1377 |
| `series_id` | registry id; a derived item has its own id | L3878 |
| `value` | number, string or null; the value visible at `knowledge_utc` (highest `value_status` rank among visible rows, L1004-1006); null for a range-only item or a NaN-by-gap derived value | L3878, L1353 |
| `obs_date` | ISO date; monthly series: first day of the reference month | L1351, L3507 |
| `available_at_utc` | `PITValue.available_at_utc`; derived: "the latest `available_at_utc` of their inputs" | L1282 |
| `retrieved_at_utc` | `PITValue.retrieved_at_utc` (first-seen); derived: latest among inputs (proposed) | L1279 |
| `vintage` | "the vintage of value (ALFRED realtime_start); null for unrevised series"; derived: latest vintage among revised inputs, else null (matches the two §6.4 examples) | L3881, L3899, L3902 |
| `first_release` | first print (FRED `output_type=4`), revised series only | L1373, L3863 |
| `latest`, `vintage_date` | "the latest vintage visible at `knowledge_utc`" and its date, revised series only | L3865, L3883 |
| `value_status` | copied from the PIT record; enum `official_close, vendor_close, live_snapshot, provisional_intraday, first_release, revised, vendor_derived, vendor_derived_across_gap`; derived: "the weakest input status (the rank of §3.5)" | L3884, L1282, L4199 |
| `source` | provider + channel string, e.g. `"FRED/ALFRED PAYEMS"` | L3885 |
| `timing` | enum `live`, `publication`, `value_proxy` (the registry `timing_class`, L1392) | L3885 |
| `stale` | `is_stale(series, decision_utc, knowledge_utc)` is `Stale(...)`; derived: any input stale. Value still shown | L1018-1020, L1110 |
| `zscore_causal`, `zscore_window` | sheet items (B.1); null elsewhere unless computed | L3886 |
| `from_sheet` | `true` for each of the 18 sheet indicators | L3887, L6368 |
| `range` | `[min, max]` (Taylor range; SEP bands) | L3888 |
| `note` | e.g. "never thresholded", "known then vs known now", `pre_vintage_history`, "labelled proxy", "structural break 2026-07-16" | L3900, L3906, L1278 |

**Algorithm.**
1. `specs = context_item_specs()` — the 18 `SHEET_ITEMS` plus the R-13 catalogue below, restricted to series declared as `inputs[]` of rule object `R-13` in the rules store (kind CONTEXT, §7.1 L4693-4699). A series whose `source_kind` is `regime_model` or `ml_classifier` is refused by M0 validation (T-DNB-01, L6238), so it can never reach the log or the page.
2. For each spec: `rec = pit_value(sid, decision_utc, knowledge_utc, consumer="R-13")`.
   - `PITValue` → item; `stale` from `is_stale`.
   - `MissingInput` with an older visible record (`pit_last`) → item from that record, `stale = true`, `note` = the reason code.
   - no visible record at all → no item (the schema requires non-null `obs_date`, `available_at_utc`, `retrieved_at_utc`); append `{series_id, reason}` to `extras.missing_items` (F-10).
   - `PITValue.synthetic is True` → no item; append to `extras.synthetic_excluded`; alert (F-11).
3. Derived items: computed by the calculators below from PIT reads only; a calculator that raises is caught per item → `extras.item_errors[{series_id, error}]`, alert `CONTEXT_ITEM_ERROR` (severity `info`), other items unaffected.
4. Assemble the envelope, validate, write or quarantine (above). A validation failure raises alert `CONTEXT_LOG_INVALID` (severity `warn`), shown as a label on the Macro page ("context log unavailable for this decision").
5. Return the dict. The function returns nothing an acting function may consume; the workflow step passes only the written path to `macro.brief`.

**R-13 item catalogue** (definitions column of L1676-1694 is binding; ids marked (v) are verbatim from the spec, (p) proposed).

| R-13 row | Items (`series_id`) | Definition / formula | Extra fields | `timing` |
|---|---|---|---|---|
| Sahm (real-time) (L1678) | `SAHMREALTIME` (v); `SAHM_INHOUSE` (p); `UNRATE_3M_CHANGE` (p); `ICSA_4WK_AVG` (p); `UNRATE` (v) | "`SAHMREALTIME`, plus Sahm computed in-house from UNRATE (a gap gives NaN), the U-3 3-month change and the ICSA 4-week average". FRED Sahm values "across the gap are tagged `vendor_derived_across_gap`" (Oct-2025 missing). In-house Sahm is the M1 derived record (TASK-M1-13); formula not in the spec (F-13) | `UNRATE`: `first_release`, `latest`, `vintage_date` | publication |
| 10y–3m and probit (L1679) | `T10Y3M` (v); `RECESSION_PROBIT_ET` (v, L3901) | `P = Φ(−0.6045 − 0.7374 × spread)`, "spread = monthly GS10 − TB3MS converted to bond-equivalent (Estrella–Trubin published coefficients, 1959–2005)". "Do **not** log 10y–2y as a prior." | `note: "published coefficients"` | publication |
| Taylor-rule residual range (L1680) | `TAYLOR_RESIDUAL_RANGE` (v, L3898) | "EFFR minus a family of rules `R = r* + π + 0.5(π − 2) + a·gap`, with π = core PCE YoY, r* ∈ {0.5, 1.0, 2.0}, gap ∈ {Okun 2×(NROU − UNRATE), CBO 100×(GDPC1/GDPPOT − 1)}, a ∈ {0.5, 1.0}. Report the min–max range only." 3 × 2 × 2 = 12 rules | `value = null`, `range = [min, max]` (pp), `note: "never thresholded"` | publication |
| Real yield and term premium (L1681) | `DFII10` (sheet); `DFII10_CHG_20D`, `DFII10_CHG_63D` (p); `THREEFYTP10` (v); `MOVE` (p; Yahoo `^MOVE`, L1430); DGS2, DGS10, DGS30 (sheet) | "`DFII10` level and 20/63-day change; `THREEFYTP10` (named 'Kim–Wright'); `MOVE`; 2y, 10y, 30y". `name` of THREEFYTP10 must contain "Kim–Wright" ("name the model; do not mix it with ACM", L1429) | — | publication; MOVE value_proxy |
| Breakevens (L1682) | `T10YIE` (sheet); `T5YIFR` (v); `BREAKEVEN_NOMINAL_BETA_YEARLY` (p) | "`T10YIE`, `T5YIFR`; yearly all-day Δbreakeven / Δnominal β" (F-14) | — | publication |
| Credit (L1683) | `BAMLH0A0HYM2` (sheet) + `BAMLH0A0HYM2_CHG_21D` (p); `BAA10Y` (v) + `BAA10Y_CHG_21D` (p) | "HY OAS and BAA10Y levels and 21-day changes" | — | publication |
| FX (L1684) | `DTWEXBGS` (sheet); `USD_LIVE_PROXY` (v; default `DX-Y.NYB`, L1431); `DEXJPUS` (sheet) + `USDJPY_DIST_TO_160` (p); `ECOS_1530_CLOSE` / `USDKRW_1530_SNAPSHOT` (v, L1887); `DEXKOUS` (sheet, labelled proxy) | "Broad USD (DTWEXBGS plus live proxy), DXY, USD/JPY and its distance to the 160–164 zone, USD/KRW (ECOS 15:30 or a timestamped 15:30:00 KST snapshot)" | USD/KRW items carry the FX-regime metadata in `note` ("FX-regime metadata … is recorded with every KRW input", L1414) | H.10: publication; proxy / snapshot: live; ECOS backfill: value_proxy (L1414) |
| Oil (L1685) | `DCOILBRENTEU` (v); `BZ=F` (v); `BRENT_DATED_MINUS_BZF` (p) | "Dated Brent, BZ=F and their spread"; a BZ=F roll day is flagged and excluded from changes (T-SER-01, L5629) | — | per source |
| Inflation and labour (L1686) | `PCEPILFE_YOY`, `CPIAUCSL_YOY`, `CPILFESL_YOY` (p; M1 derived, calendar offset); `PAYEMS` (v) monthly change; `PAYEMS` calendar-year monthly average (the §6.4 example, `name: "Payrolls, 2025 monthly average (k)"`); `UNRATE` | "Core PCE YoY, CPI YoY, core CPI YoY (calendar lag); payrolls and unemployment with first prints and vintage dates"; "the brief shows 'known then' and 'known now'" | `first_release`, `latest`, `vintage`, `vintage_date`; `note: "known then vs known now"` | publication |
| Korea (L1687) | `PAIR_SHARE_KOSPI`, `PAIR_LOOKTHROUGH_KODEX200` (p); `KOSPI_RV21`, `KOSPI_RV21_PCTILE_3Y` (p); `KRX_FLOW_FOREIGN`, `KRX_FLOW_INSTITUTION`, `KRX_FLOW_INDIVIDUAL` (p); `BOK_BASE_RATE` (p); `KOSPI_TREND_SMA10M` (p) | "Pair share of KOSPI (and KODEX 200 look-through); KOSPI rv21 and its trailing-3-year percentile; investor-type flows; BoK rate; the KOSPI trend state (SMA10m)". "The KOSPI trend state is context only (R-28 has no Korea instance)" | trend item: `value` = `"above"` / `"below"`; flows: final after close; "preliminary intraday figures are stamped with their own time" (L1412) | closes: live; BoK: publication |
| Leverage and flow (L1688) | `KOFIA_MARGIN_DEBT`, `KRX_LETF_AUM_INDEX`, `KRX_LETF_AUM_SINGLE_STOCK`, `KRX_LETF_VALUE_TRADED`, `KRX_LEVERAGED_SHARE` (p) | "KOFIA margin debt; single-stock and index leveraged-ETF AUM and value traded; the leveraged share; once acquired (BL-U01). The 16 Jul 2026 rule change is logged as a structural break: new single-stock leveraged-ETF listings suspended, deposit raised from ₩10m to ₩30m, LP divergence limit cut from 3% to 2%" | `note: "structural break 2026-07-16"` on items with `obs_date ≥ 2026-07-16`; plus one R-18 break-log entry (B.4) | `live` (T-CTX-02) |
| Variance risk premium (L1689) | `VRP_US` (p); `VRP_KR` (p, "once logged") | "VRP = VIX²/12 − 21-day realised variance; KOSPI MFIV² − RV once logged" | — | `live` (T-CTX-02) |
| Live implied-vol snapshots (L1690) | `VIX_1600ET_SNAPSHOT`, `VIX3M_1600ET_SNAPSHOT`, `KOSPI200_MFIV_1530KST` (p) | "VIX/VIX3M at 16:00 ET; KOSPI200 model-free implied variance at 15:30 KST; both stamped `live`" | `value_status = live_snapshot` (quote snapshot, L1319) | `live` |
| Turbulence and absorption ratio (L1691) | `TURBULENCE`, `ABSORPTION_RATIO` (p) | "Kritzman turbulence and absorption ratio (500-day window, half-life 250, N/5 eigenvectors), display only". "Never a multiplier; a stressed-covariance use needs a pre-registered win (R-09)" | — | per inputs |
| Policy (L1692) | `FOMC_DECISION`, `FOMC_VOTE_SPLIT`, `FOMC_DISSENT_DIRECTION` (p, string values); `SEP_TABLE2_BANDS` (p, `range`) | "FOMC decision, vote split and dissent direction; SEP Table-2 error bands (when released)"; "SEP bands feed Monte Carlo priors (R-16)" | — | publication (statement 14:00 ET, L1437) |
| EPU (L1693) | `USEPUINDXD` (v) | "`USEPUINDXD`"; "Variance only (N-04)" | — | publication |
| Existing sheet items (L1694) | the 18 ids of B.1 | "Each of the 18 indicators of `core/ficc/macro` not listed above, with its causal z-score" | `from_sheet = true`, `zscore_causal`, `zscore_window` | per B.1 |

Config read (verbatim, L4465-4470):
```yaml
context_log:
  probit: {alpha: -0.6045, beta: -0.7374, spread: "GS10 - TB3MS (bond-equivalent), monthly"}
  taylor_family: {r_star: [0.5, 1.0, 2.0], gap: [okun_2x, cbo], a: [0.5, 1.0], pi: core_pce_yoy, pi_star: 2.0}
  existing_sheet: {all_items_context_unless_acting: true, zscores: causal_display_only, regime_read: removed_if_regime_model_else_text_only}
  vintages_required: true
  additions: [leverage_and_flow, vrp, live_implied_vol_snapshots, turbulence_and_absorption_ratio]
```
Also read: `data.monthly_lag_method: calendar`, `data.vintages: {source: alfred, store_first_release: true, store_latest: true}`, `data.derived_series_in_house: [sahm, yoy, taylor_range]   # a gap gives NaN`, `data.named_series_required: true`, `data.brent_series: {spot: DCOILBRENTEU, futures: BZ=F}` (L4217-4221).

**Calculators (pure functions; inputs are PIT values; all percent inputs in percentage points unless noted).**

```python
def recession_probit_et(gs10_pct: float, tb3ms_pct: float, alpha=-0.6045, beta=-0.7374) -> float:
    # spread = GS10 - bond_equivalent(TB3MS); P = Phi(alpha + beta * spread)             (L1679, L4466)
    # bond_equivalent(d) = 100 * (365 * d/100) / (360 - 91 * d/100)    <- NOT in the spec; Estrella-Trubin (2006) convention (F-12)
def taylor_residual_range(policy_pct, core_pce_yoy_pct, unrate, nrou, gdpc1, gdppot,
                          r_star=(0.5, 1.0, 2.0), a=(0.5, 1.0), pi_star=2.0) -> tuple[float, float]:
    # gaps = {okun_2x: 2*(nrou - unrate), cbo: 100*(gdpc1/gdppot - 1)}
    # R = r + pi + 0.5*(pi - pi_star) + a_i*gap ; residual = policy - R ; return (min, max) over the 12 rules   (L1680, L4467)
def taylor_midpoint(lo: float, hi: float) -> float      # (lo + hi) / 2 ; the R-18 statistical series (B.4)
def vrp(vix_level: float, daily_returns_21: Sequence[float]) -> float:
    # (vix_level/100)**2 / 12 - sum(r*r for r in daily_returns_21)                         (L1689; RV definition: F-15)
def trend_state_sma10m(month_end_closes: Sequence[float]) -> str:
    # last 10 month-end official closes incl. the latest; "below" if close < mean else "above"   (R-28 rule 1, L2983)
def rv21_and_percentile(closes: Sequence[float]) -> tuple[float, float]:
    # rv21 = stdev(last 21 simple returns, ddof=1) * sqrt(252); percentile vs the trailing 756 sessions of rv21 (F-16)
def turbulence_absorption(returns: np.ndarray, window=500, half_life=250) -> tuple[float, float]:
    # EW mean/cov on the trailing window; turbulence = (y_t - mu)' inv(Sigma) (y_t - mu);
    # absorption = sum(top n eigenvalues) / sum(all), n = N/5                              (L1691; universe and rounding: F-17)
```

- Probit check available hermetically: `recession_probit_et(3.57, 5.14)` = Φ(−0.6045 − 0.7374 × (3.57 − 5.280)) = Φ(0.6565) = 0.744; the spec's evidence line says "P = 0.744 in May-2023" (L1679). The two inputs are this brief's recollection of the FRED May-2023 monthly values, not spec values; the match supports the bond-equivalent formula.
- Monthly arithmetic (L1350-1355): monthly index keyed by the first day of the reference month; YoY and 3-month changes "by **calendar offset**, never by positional `shift`"; a missing month (Oct-2025 CPI and household survey) "makes NaN every derived value that uses it as an input: an endpoint or a member of an averaging window (YoY for Oct-2025 and Oct-2026, MoM for Oct and Nov 2025, Sahm's 3-month means)"; "An endpoint change whose window merely contains it is computed (Aug-2026 YoY = 3.35%)". Test value: positional `shift(12)` gives 3.71%, "which is wrong". These derived records are M1 deliverables (TASK-M1-13); M6 reads them.
- Quarterly Taylor inputs (NROU, GDPC1, GDPPOT) are as-of carried to the reference month (the last value visible at `decision_utc`); no interpolation ("Nothing is ever silently interpolated", L546); `obs_date` = the reference month of π and UNRATE (example `"2026-08-01"`, L3898).
- Revised series (`PAYEMS`, `UNRATE`, `PCEPILFE`, `CPIAUCSL`, `CPILFESL`, GDP): three values stored — `first_release` (FRED `output_type=4`), `latest`, `vintage_date` (L1373, L1435-1436). Observations older than the series' first ALFRED vintage: `vintage = null`, `value_status = revised`, label `pre_vintage_history` in `note` (L1278).

**Fail-closed behaviour (context variant).** Stale → `stale: true`, value shown. Missing record → item omitted, listed in `extras.missing_items`. Synthetic → omitted, listed, alerted. Calculator exception → that item omitted, listed, alerted. Whole-log validation failure → refused, quarantined, alerted. In every case: no book counter, no HALT, no change to any weight, `macro_state.fail_closed` untouched.

### B.3 Context isolation (TASK-M6-03; T-CTX-01)

Test row (L5654): "No acting module imports or reads `context_log`, the 18-indicator sheet's values, the R-18 break log or a refusal book (static import check plus a runtime guard)".

```python
# core/ficc/context_log.py  (single source of truth; the test imports these)
ACTING_MODULE_PREFIXES = ("core.quant.", "core.engine.", "core.rules.", "core.calendars", "core.markets",
                          "core.ficc.pit", "core.ficc.contracts")       # the card harness in core.quant is included (conservative)
ACTING_EXEMPT = ("core.quant.refusal", "core.quant.insights")      # refusal legs are themselves protected; insights is narrative
PROTECTED_MODULES = ("core.ficc.context_log", "core.ficc.macro", "core.quant.refusal")
PROTECTED_CALLEES = ("read_context_log", "load_break_log", "macro_sheet", "refusal_krw_leg", "refusal_rates_leg")
PROTECTED_PATH_FRAGMENTS = ("context_log/", "r18_break_log", "r18_research_log")
BUILDER_FORBIDDEN = {"core.ficc.macro_artifacts": ("core.ficc.context_log", "core.ficc.macro")}   # static only

class ContextIsolationError(RuntimeError): ...

def assert_not_acting_caller() -> None:
    # walk sys._getframe(1)...; if any frame's module __name__ matches ACTING_MODULE_PREFIXES (and not ACTING_EXEMPT) -> raise
```

- **Static check** (`tests/macro_acceptance.py::test_T_CTX_01_static`): for every `.py` file whose dotted name matches `ACTING_MODULE_PREFIXES` (minus `ACTING_EXEMPT`), parse with `ast`; collect every `Import` / `ImportFrom` at any depth (function-level lazy imports included), skipping only `if TYPE_CHECKING:` bodies and `if __name__ == "__main__":` bodies; fail if a protected module is imported directly or through the transitive closure of repo-internal imports; fail on a `Name` / `Attribute` reference to a `PROTECTED_CALLEES` entry; fail on a string literal containing a `PROTECTED_PATH_FRAGMENTS` entry. The artifact builder is checked by `BUILDER_FORBIDDEN` only: `core.ficc.macro_artifacts` may not import `core.ficc.context_log` or `core.ficc.macro` (so no context value can reach an acting field), but it may call the refusal legs for the display-only blocks `macro_state.refusal_books` and `overlay_decision.refusal[]`; it is therefore not in the runtime prefix list.
- **Positive control**: the same checker run on an in-memory source `"from core.ficc import context_log\n"` attributed to `core.quant.risk` must report a violation; otherwise the test fails (a detector that cannot fail proves nothing).
- **Runtime guard**: `assert_not_acting_caller()` is the first statement of `read_context_log()`, `load_break_log()`, `core.ficc.macro.macro_sheet()` and (from M8) `refusal_krw_leg()` / `refusal_rates_leg()`. Test: a function compiled with `__name__ = "core.quant.risk"` that calls `macro_sheet(source="synthetic")` raises `ContextIsolationError`; the same call from the test module does not.
- **Third barrier (M1, already specified)**: "A series with no binding may be read only by a `context` consumer (R-13); `pit_value` raises for any other consumer that has no binding for the series (T-SER-02)" (L1891). Context-only series carry no acting binding, so an acting consumer cannot read them through the store.
- "Keep both in force for every later milestone" (task M6-03): the two tests stay in the `fast` tier of `tests/run_all.py`; T-CTX-02 ends with "T-CTX-01 still passes".

### B.4 R-18 breaks (TASK-M6-04; T-BREAK-01)

Config (verbatim, L4471-4476):
```yaml
breaks:                                  # R-18
  policy_trigger: official_framework_change      # shrink macro-conditioned multipliers to 1.0 + start a forward record
  statistical_trigger: log_only                  # active only after the 1990-2026 false-break test
  scale_reanchor: declared_events_only           # v1.2's 2x-3y-median/60-session rule is a logged flag only
  bocpd: {hazard: "1/250", prior: declared, log_only: true, displayed: false}
  market_structure_log: true
```

```python
@dataclass(frozen=True)
class BreakEvent:                         # proposed fields; the spec names only the type (L1076)
    event_id: str                         # sha1(kind|market|tag|effective_date|new)  -> idempotent
    kind: Literal["policy_framework_change", "market_structure", "scale_reanchor"]
    market: str | None                    # §6.1 market enum; None for a central-bank framework event
    effective_date: date                  # effective-dated in the calendar (R-20)
    declared_utc: datetime
    source: str                           # the official notice / statement reference
    tag: str | None                       # regime-tag name for market_structure events
    old: object | None
    new: object | None
    note: str = ""

def log_break(event: BreakEvent, ctx: RunContext) -> None      # spec: log_break(event: BreakEvent) -> None  (L1076)
def sync_market_structure_breaks(market: str, ctx: RunContext) -> list[BreakEvent]
def log_research(kind: str, payload: dict, ctx: RunContext) -> None        # write-only; no reader is shipped
def reanchor_eligible(card_header: dict, event_id: str, ctx: RunContext) -> bool
def load_break_log() -> list[dict]                                           # guarded (B.3); Macro page display only
```

**Two files, both append-only JSON lines under `config.macro_artifact_dir()`:**
- `r18_break_log.jsonl` — declared events only (`BreakEvent` rows + common provenance `knowledge_utc`, `git_hash`, `config_hash`). Only reader: the Macro page calendar panel, through the guarded `load_break_log()`. The card harness lives under `core/quant/` (acting prefix) and reads `regime_tags` (R-20) for its split lines, never this log (L1113).
- `r18_research_log.jsonl` — statistical flag, v1.2 scale flag, BOCPD probability. **No reader function exists in production code.** T-BREAK-01 asserts that the file-name constant is referenced only by `core/ficc/context_log.py` and by tests.

**(a) Policy trigger (i), acting now** (L1780): "an official framework change. Examples: a central bank's statement on longer-run goals and strategy changing its reaction-function framework, or the end of yield-curve control. On such an event, every **macro-conditioned** multiplier is shrunk to 1.0 and a forward record starts; there is no historical re-gate. In v2.0 no macro-conditioned multiplier acts in any book, so the trigger applies to future cards."
- "Removed as a trigger: 'a sign flip in the policy direction.'" (L1781). `log_break` accepts no event kind for a direction flip; a `BreakEvent` whose `source` is empty or whose `kind` is not in the Literal raises `ValueError`.
- `log_break(kind="policy_framework_change")`: (1) append the row; (2) `targets = macro_conditioned_rules(store)` — rule ids whose rule object carries `macro_conditioned: true` (F-18; the list is empty in v2.0); (3) push, never pull: for each target call `books.neutralise_rule(rule_id, event_id)` on the per-book runtime state (`core/engine/books.py`; state key `neutralised_rules: {rule_id: event_id}`), and `apply_overlays` maps a neutralised rule to 1.0 from the next decision and says so in `reasons` (the acting side reads its own runtime state, never the break log; it is runtime state, not a rules-store edit, so it is not "an edit to an acting parameter outside a card revision", L5335). This hook is new and is required from the M2 / M5 owners (E.1); (4) append one governance event per target: `kind: "record_reset"`, `rule_id`, `actor: "runtime"`, `reason: "R-18 official framework change <event_id>: multiplier shrunk to 1.0; forward record starts; no historical re-gate"`, `refs: ["R-18"]` (§6.6 enum, L4104-4105: "forward-record reset"); (5) write a `forward_record_start_requested` marker for M8's forward monitor ("A forward record starts at the first decision written by the live `macro_daily` workflow … never before M8", L5310).
- The shrink raises exposure of the affected factor (1.0 = no de-risk). It stays at 1.0 until a counted card revision is committed after the event (F-19). Open council question (L5463): "Whether a framework event lifts an active de-risk spell at once (current text) or lets it run out." Current text binds: at once.

**(b) Statistical trigger (ii), logged only** (L1782): "a statistical break flag on the reaction-function residual (CUSUM or BOCPD on EFFR minus the midpoint of the Taylor range logged in R-13). It is written to the R-18 research log. It becomes a trigger only after EX1's test: ≤ 1 false break a decade on 1990–2026, with flags within 6 months of the 2012 and 2020 framework changes (backlog)."
- Series: `x_m = taylor_midpoint(range_lo, range_hi)` of the logged `TAYLOR_RESIDUAL_RANGE` (midpoint of the residual range = EFFR − midpoint of the rule range; identical by construction).
- Method and parameters are not specified (F-20). Proposed, log-only, recorded on every row: two-sided tabular CUSUM on `z_m = (x_m − mean_exp) / sd_exp` (expanding, causal, ≥ 60 months), `k = 0.5`, `h = 5`, reset after an alarm. Row: `{kind: "policy_stat_flag", obs_date, x, z, s_pos, s_neg, flag, method: "cusum", params, decision_utc, knowledge_utc, data_snapshot_id}`.
- Gate: `breaks.statistical_trigger` must equal `"log_only"`; any other value is refused at load unless the store also carries an `ex1_test` record (`{false_breaks_per_decade, flags_within_6m_2012, flags_within_6m_2020, results_md5}`) that meets "≤ 1 false break a decade on 1990–2026; flags within 6 months of 2012 and 2020". No code path in M6 connects the flag to `log_break`.

**(c) Scale breaks** (L1786-1789).
- "Thresholds re-anchor **only on declared events**: an R-18 log entry for a market-structure or framework change, effective-dated in the calendar (R-20), with the re-anchoring window stated on the affected card's header. Re-anchoring is logged as a counted card revision under the full package, with no lockout of its own; it never lifts a demotion or an R-25 lockout, and only events whose effective date follows the header commit qualify."
- `reanchor_eligible(card_header, event_id, ctx)` returns True only if all hold: the event is in `r18_break_log.jsonl` with `kind ∈ {market_structure, policy_framework_change}`; it is effective-dated in the calendar (a regime-tag transition, or a framework event in the event store); `event.effective_date > header commit date`; the header states the re-anchoring window (field name absent from §6.5, F-21); the card's family × market is not inside an R-25 lockout and the card is not demoted ("no new card, revision, instrument book or R-18 re-anchoring of that family in that market enters the recommended book during it", L2700). A research-log row can never be passed (different file, no `event_id`). "A pre-declared R-18 re-anchoring is not a new card" (L2702, L5357). No caller exists in v2.0 (no acting scale threshold; the R-06 label quartiles "re-anchor automatically; they are display only", L1789).
- v1.2 statistical trigger "(realised vol above 2× its trailing 3-year median for 60 sessions) is demoted to a logged flag" (L1787). Research-log row `{kind: "scale_flag_v12", market, obs_date, rv21, median_756, run_length, flag}`; `flag` is true on the 60th consecutive session. Spec facts: "It fired twice in KOSPI 1999–2026 (2008-12-10, 2026-08-11) and 4 times in the US since 1990, after the episode trough in 5 of the 6 cases." Definition detail pinned by a local probe (this brief, not a golden value): rv = `stdev(21 simple returns, ddof 1) × √252`, median over the trailing 756 sessions including t, 60 consecutive sessions; on `docs/asset_expansion/cache/yf_069500.KS.csv` this fires on 2026-08-11 (a 20-return window gives 2026-08-06); on `yf_SPY.csv` (1995-2026) it fires 4 times (2008-12-08, 2009-04-15, 2019-01-22, 2020-05-18).
- "**BOCPD research log.** A BOCPD scale-break probability (hazard 1/250, declared prior) may be written to the R-18 research log. It is never acting, never displayed, and nothing in R-18 depends on it (P19)." (L1788). Row `{kind: "scale_bocpd_prob", market, obs_date, prob, hazard: "1/250", prior, decision_utc, knowledge_utc}`. Model, series and the meaning of "probability" are not specified (F-20). Proposed: Adams–MacKay recursion, constant hazard 1/250, zero-mean Gaussian daily returns with an Inverse-Gamma prior on the variance declared in `breaks.bocpd.prior`; logged value = posterior mass on run length < 21 sessions.

**(d) Market-structure break log** (L1791-1795).
- "Korean market-structure breaks become effective-dated tags in `core/calendars` (R-20) and R-18 log entries: short-sale bans, the sell tax (0.30% → 0.15% → 0.20%), tick-size reforms, leveraged-ETF rules (16 Jul 2026), and session changes."
- R-20 (L2051): "R-18 logs a market-structure break when a tag changes; any card whose evidence straddles the break prints the split." `sync_market_structure_breaks("KR", ctx)` walks the signed regime-tag file (M1, `regime_tags`, tags `price_limit, saturday_session, close_time_kst, closing_call, random_end, lunch_break, fx_regime, etf_available, short_sale_ban, sell_tax_pct, tick_regime, letf_rules, usdkrw_onshore_hours`, L2036-2047) and appends one `market_structure` event per transition not yet logged (idempotent by `event_id`). Called at app start and after a signed calendar change. Cards read the tags through `regime_tags` (R-20), not through the break log.
- "A card whose sample straddles a break prints the split." "Futures cards print a ban-period basis line." (L1793-1794) — printed by the M7 card harness from `regime_tags`; `instruments.printed_lines` includes `ban_period_basis` (L4405).
- "**No gross rule:** EX2 found no index-level short-ban break." (L1795). No break event changes any weight; only kind `policy_framework_change` has an effect, and only on macro-conditioned multipliers.

### B.5 `core/ficc/macro_artifacts.py` — builders (TASK-M6-05)

```python
def build_macro_state(market: str, ctx: RunContext) -> dict            # spec: (market, decision_utc) -> dict   (L1073)
def build_overlay_decisions(market: str, ctx: RunContext) -> list[dict]  # spec: (market, decision_utc) -> list[dict] (L1074)
```
"exactly one `macro_state` per market per decision and one `overlay_decision` per market × family" (task); "always written, also when a gate failed" (L1221); "`bounds_ok` then validates the built artifacts (R-32)" (L828). The builders compute nothing: they call the functions of M1-M5 and copy their results. They never import `core.ficc.context_log` or `core.ficc.macro` (B.3).

**`macro_state` field → source** (schema L3523-3652; required list L3527-3529).

| Field | Source |
|---|---|
| `schema, schema_version, read_only, generated_at_utc, knowledge_utc, git_hash, config_hash, data_snapshot_id` | M0 envelope helper; `knowledge_utc` from `ctx` |
| `decision_utc` | `close_print_bound_utc(market, decided_session)` (L3535) |
| `decided_session`, `effective_session` | calendar: t and the next session (L3536-3537) |
| `market` | enum `KR, US, JP, EU, TW, CN, HK, IN, EM, CRYPTO, FX` |
| `run_mode` | `ctx.run_mode` ∈ `live, backtest, replay` |
| `inputs[]` | every `pit_value` read of the run (acting and risk-model in full; context rows shown), as `$defs/input` records; `status` map (L1108): MissingInput `missing / stale / provisional_intraday / session_mismatch / synthetic_rejected` → `missing / stale_missed_release / provisional_rejected / session_mismatch / synthetic_rejected`; stale context → `stale`; dispute → `disputed`; warm-up → `warmup`; else `ok`. `expected_available_utc`, `stale_deadline_utc` from R-19 (M1) |
| `lag_audit` | `{checked, violations[]}` from the M1 lag audit (context rows skipped, L3703) |
| `vol.estimator`, `estimator_b5`, `estimator_gate{status, stage1, stage2_mcs_p, stage3_rank, fallback_used, reason}` | `estimator_gate(market, instrument_book, horizon=21)` (M3); defaults `sma20`, `registered_default`, `fallback_used=false` |
| `vol.vt_status`, `sigma_ann`, `target_ann`, `vt_weight_next` | `market_vol_target` + per-book mapping (M2); `vt_weight_next` is the specification-book value |
| `vol.vt_weight_recommended_book` | "= vt_weight_next once R-06's card is PASS; 1.0 while NOT_RUN or INSUFFICIENT" (L3559) |
| `vol.instrument_book`, `rebalance`, `no_trade_band` | rules store `vol_target.<market>` (KR: `KRX_ETF_line`, `daily`, `0.0`, L4287-4288); US: F-25 |
| `vol.display_label_rel/abs`, `label_method_rel/abs` | M2 label functions; consts `trailing756_quartiles_causal_filtered`, `expanding_full_history_quartiles_causal_filtered` |
| `vol.alt_sigma_logged` | null ("`max(SMA20, implied)` is retired") |
| `flags.dm_bear_state` | `dm_gate` (M4), specification book only |
| `flags.hedge_credit_off, hedge_failure, classic_risk_off, hedge_reasons, hedge_stale_inputs, fx_hedge_credit` | `hedge_state(decision_utc)` (M2); `hedge_reasons ⊆ {ok, risk_model_input_stale, risk_model_exception, corr_positive, core_pce_ge_3}` |
| `flags.kr_open_gap_event, gap_sessions, var_display_scale` | `gap_sessions(market, session)` and the event store (M5); `var_display_scale = sqrt(max(n_US, 1))` |
| `flags.ladder_step, ladder_dwell_left, block_new_entries, ladder_steps_act_in, hard_stop, hard_stop_level, engine_state` | `drawdown_ladder` + per-book runtime (M5); `hard_stop_level` = D2 value; `engine_state` = the market's recommended book |
| `annotations.vix_ge_vix3m`, `notes[]` | R-08 annotation (M5) |
| `refusal_books.S1_krw_flag / S2_rates_flag` | refusal legs (M8); null until then; display only |
| `forward_sim.R28_below_sma10m / R29_vt_weight_next` | FORWARD-SIM cards (M8); null until then |
| `concentration.*`, `by_book{composed, gross, binding_factor}` | `concentration_bound` (M5); `template` = D1 value |
| `owner_decisions` | "every decision whose canonical key a rule of this market reads, plus every decision with status pending" (L3605); map keyed by canonical key → `{decision, value, status}` (F-26) |
| `runtime[]` | one entry per book from the per-book runtime (M1 OPS, M5 RISK) |
| `fail_closed` | OR of the acting components' `fail_closed`; risk-model and context failures never set it (T-HEDGE-01) |
| `alerts[]` | structured alerts of the run (`alert_id, code, severity, component, first_seen_utc, count`, …) |
| `extras.regime_tags` | `regime_tags(market, decided_session)` on every KR record (L2082); `extras.validation_errors` (R-32) |

**`overlay_decision` field → source** (schema L3717-3763): `family` ∈ `momentum, reversal, flow, quality, ts_trend, market_gross`; `exposure_basis` (`active` for families, `total` for `market_gross`); `vol_scale` = vs (specification) or vt for `market_gross`; `vol_scale_recommended_book` "= vol_scale if its card is PASS, else 1.0"; `vol_scale_card` and every `card` = `{card_id, class, verdict, disposition, displayed_as, label, results_md5}` from the card store (`NOT_RUN` before the first formal run); `multipliers[]` from `dm_gate` / gross overlays (value in [0.5, 1.0]); `ladder`, `post_rearm_cap` ∈ `{0.5, 1.0, null}` (`market_gross` only); `composition = "min"`; `overlay_min = min(1.0, multipliers…, ladder, post_rearm_cap)`; `overlay_floor = 0.5`; `overlay_cap = 1.0`; `overlay_applied_spec_book`; `overlay_applied_recommended_book` (PASS factors with disposition `RECOMMENDATION` / `BUILD_AS_INSURANCE`, and `INVARIANT_STEP`; every other factor 1.0, L3769); `forward_sim[]`, `refusal[]` (display only); `binding[]`, `reasons[]` from the M2 binding log; `inputs[]`; `rule_versions`. Display rules (L3767-3768): `displayed_as ∈ {"recommendation", "insurance"}` iff `verdict = "PASS"` and `disposition ∈ {RECOMMENDATION, BUILD_AS_INSURANCE}`; `displayed_as = "invariant"` iff `disposition = INVARIANT_STEP`.

**Failure behaviour.** A component that failed closed contributes its carried previous state and sets `fail_closed = true`; the artifact is still written. Validation (M0): acting-field failure → `<artifact_dir>/quarantine/` + (from M8, `bounds_ok`) OPS HALT of the books it describes; display-field failure → written with `extras.validation_errors` + alert, never HALT (field classes, L3370). A property not classified in L3370 "is acting until it is classified here, so an unclassified field fails closed".

### B.6 Macro page and brief section (TASK-M6-06)

UI box (L761-763): "[+] Macro page: macro_state panel, overlay_decision table, card verdict and disposition badges, relative and absolute vol labels, event calendar, context log, owner decisions D1–D5 (proposed). No regime-model state is displayed (P19)." Task: D1-D6 "with value and status" (F-27).

Brief section (§3.6 rule 4, L1127-1133): "the vt and vs weights and the relative and absolute vol labels; the flags and annotations; each card's verdict and disposition; FORWARD-SIM cards and refusal books, marked 'not a recommendation'; the open owner decisions; the event calendar."

```python
# core/ficc/macro.py
def macro_state_section(states: list[dict], overlays: list[dict], owner_decisions: dict, events: list[dict]) -> dict
def daily_brief(sheet, *, top=5, macro_state: dict | None = None) -> dict       # adds out["macro_state"] when given
def weekly_brief(sheet, curve_report=None, carry_rows=None, macro_state: dict | None = None) -> dict
```
- `macro_state_section` is a pure function over validated artifacts (no data read, no computation of exposure). Keys: `weights` (per market `vt_weight_next`, `vt_weight_recommended_book`; per family `vol_scale`, `vol_scale_recommended_book`), `labels` (`display_label_rel`, `display_label_abs`), `flags`, `annotations`, `cards[]` (`card_id, verdict, disposition, displayed_as, label`), `forward_sim[]` and `refusal[]` each with `"marker": "not a recommendation"`, `owner_decisions` (D1-D6: `key, value, status`), `events[]`.
- The optional keyword keeps every existing caller and the three existing macro tests unchanged.
- The page renders only artifact fields and `context_log` items. It never computes exposure and never imports an acting module to do so. Missing, quarantined or invalid artifact → an error notice and no numbers. `extras.validation_errors` → shown in a notice.
- Owner decisions are read from the registry `owner_decisions.D1..D6` (`{key, value, default, options, status, effective_from, rationale, refs}`, L4138-4152), not from one market's `macro_state`.
- No BOCPD value, no research-log row, no regime-model field has a render path. The calm / normal / elevated / stressed words appear only from `vol.display_label_rel/abs`, captioned as volatility labels.
- Weekly brief also summarises governance events ("HALT, re-arm, demotion, package freeze, header commit, owner-decision and calendar changes are appended to `governance_events.jsonl` … and summarised in the weekly brief", L1249-1250); the forward-record lines of L5359-5365 are M8.

---

## C. Schemas and config this area writes or reads

### C.1 `context_log` schema (verbatim, L3868-3889; lives with the M0 schema registry, `$id` `quantgen/context_log.v2.0`)

```json
{"$id":"quantgen/context_log.v2.0","type":"object",
 "required":["schema","schema_version","read_only","generated_at_utc","knowledge_utc","git_hash","config_hash","data_snapshot_id","decision_utc","as_of_utc","items","acts"],
 "properties":{"schema":{"const":"quantgen.context_log"},"schema_version":{"const":"2.0"},"read_only":{"const":true},
  "generated_at_utc":{"type":"string","format":"date-time"},"knowledge_utc":{"type":"string","format":"date-time"},
  "git_hash":{"type":"string"},"config_hash":{"type":"string"},"data_snapshot_id":{"type":"string"},
  "decision_utc":{"type":"string","format":"date-time"},
  "as_of_utc":{"type":"string","format":"date-time","description":"= decision_utc (one log per decision)"},
  "acts":{"const":false},
  "items":{"type":"array","items":{"type":"object",
     "required":["name","series_id","value","obs_date","available_at_utc","retrieved_at_utc","vintage","source","timing","value_status","stale"],
     "properties":{"name":{"type":"string"},"series_id":{"type":"string"},"value":{"type":["number","string","null"]},
        "obs_date":{"type":"string","format":"date"},
        "available_at_utc":{"type":"string","format":"date-time"},"retrieved_at_utc":{"type":"string","format":"date-time"},
        "vintage":{"type":["string","null"],"format":"date","description":"the vintage of value (ALFRED realtime_start); null for unrevised series"},
        "first_release":{"type":["number","null"]},"latest":{"type":["number","null"]},
        "vintage_date":{"type":["string","null"],"format":"date","description":"the latest vintage visible at knowledge_utc"},
        "value_status":{"enum":["official_close","vendor_close","live_snapshot","provisional_intraday","first_release","revised","vendor_derived","vendor_derived_across_gap"]},
        "source":{"type":"string"},"timing":{"enum":["live","publication","value_proxy"]},"stale":{"type":"boolean"},
        "zscore_causal":{"type":["number","null"]},"zscore_window":{"type":["string","null"]},
        "from_sheet":{"type":"boolean","description":"true for the existing 18-indicator sheet items"},
        "range":{"type":["array","null"],"items":{"type":"number"}},"note":{"type":"string"}}}},
  "extras":{"type":"object"}}}
```
Closed-object rule (L3509): `additionalProperties: false` on the envelope and on each item; `extras` is open. An undeclared item field fails validation. The §6.4 example (L3895-3906: Taylor range, probit 0.095, payrolls 9.7 / 119.4) must validate (T-SCHEMA-01).

### C.2 Rules-store keys read

`context_log.*` (L4465-4470) and `breaks.*` (L4471-4476), quoted in B.2 and B.4. `data_contracts.on_failure.context: {action: label_stale}` (L4236). `risk_layer.never_halt_on` (L4362-4363). `data.vintages`, `data.derived_series_in_house`, `data.monthly_lag_method` (L4217-4219). `owner_decisions.D1..D6` (L4140-4152). `do_not_build.refused_shapes.regime_model_source_acting_or_displayed: [11, 24, 27]`, `smoothed_or_forward_looking_label: 24` (L4666-4667). Proposed additions (not in §7; each must be written to the store explicitly because "the store's model is immutable and has no financial defaults", L4127): `breaks.bocpd.prior` (the declared prior), `breaks.statistical.{method, k, h}`, optional `macro_conditioned: true` on a rule object (F-18), `context_log.turbulence_universe` (F-17).

### C.3 Registry rows this area needs (M1 registry file; role C unless noted)

Series named by the spec for R-13 (§4.2): `T10Y3M`, `T10Y2Y`, `DFII10`, `T10YIE`, `T5YIFR`, `DGS2`, `DGS30` (L1428); `THREEFYTP10` (L1429); `^MOVE` (L1430); `DTWEXBGS`, `USD_LIVE_PROXY` (L1431); `DEXJPUS` (L1432); `BAMLH0A0HYM2`, `BAA10Y` (L1433); `DCOILBRENTEU`, `BZ=F` (L1434); `PCEPILFE`, `PCEPI`, `CPIAUCSL`, `CPILFESL` with ALFRED vintages (L1435); `UNRATE`, `SAHMREALTIME`, `PAYEMS`, `ICSA` (L1436); `FEDFUNDS / DFEDTARU`, FOMC statements, SEP Table 2 (L1437); `USEPUINDXD` (L1438); VRP inputs (L1439); KOSPI investor-type net buys, role "C (log from day one; backlog BL-C06)" (L1412); KRX margin debt and leveraged-ETF AUM / value traded, "C once acquired (R-13; BL-U01); P until then" (L1413); BoK base rate, Korea CPI (L1415); VKOSPI and "KOSPI200 model-free implied variance at 15:30 KST … the MFIV snapshot is stamped `live`" (L1417); VIX / VIX3M with "The 16:00 ET snapshot is stamped `live`" (L1426). Not named in §4.2 but required by R-13 formulas: `GS10`, `TB3MS`, `EFFR`, `NROU`, `GDPC1`, `GDPPOT`. Sheet-only ids to add: `SOFR`, `DFF`, `BAMLC0A0CM`, `DEXUSEU`, `DCOILWTICO`, `ZN=F`, `GC=F`.

Bindings to add: `{role: context, consumer: R-13}` for every series the context log reads that already has another binding (`DGS10`, `PCEPILFE`, `USD_LIVE_PROXY`, `SPX_OFFICIAL_CLOSE`, `KOSPI_OFFICIAL_CLOSE`, `KRX_MARKET_CAPS_005930_000660_KOSPI`, `KODEX200_PDF`), because `pit_value` raises for a consumer without a binding on a bound series (L1891; F-8).

### C.4 Files written (all under `config.macro_artifact_dir()`; tests use temporary copies, T-HERM-02)

| File | Content | Readers |
|---|---|---|
| `context_log/<decision_utc>.json` | C.1 | Macro page, brief (guarded reader) |
| `quarantine/context_log_<decision_utc>.json` | refused log + `errors[]` | audit, replay |
| `r18_break_log.jsonl` | declared `BreakEvent` rows | Macro page calendar panel only (guarded) |
| `r18_research_log.jsonl` | `policy_stat_flag`, `scale_flag_v12`, `scale_bocpd_prob` rows | none (write-only) |
| `governance_events.jsonl` (M0 appender) | `record_reset` rows from the policy trigger | app start verifier, weekly brief |
| `macro_state/…`, `overlay_decision/…` | §6.1, §6.2 | Macro page, brief, `bounds_ok` (M8) |

---

## D. Tests

Tier `fast` unless noted. All hermetic: frozen or inline fixtures, network patched to raise (L5491-5495). Feasibility: SYNTH = inline / synthetic fixtures; REFDATA = needs the frozen reference data under `/home/claude/quantgen_macro_data/` (absent); OWNER = owner input, credentials or live sessions.

| Test (runs_from) | Exact assertion | Fixture | Class |
|---|---|---|---|
| T-CTX-01 (M6; L5654) | Static: no module matching `ACTING_MODULE_PREFIXES` imports (directly or transitively) `core.ficc.context_log`, `core.ficc.macro` or `core.quant.refusal`, nor names a protected artifact path. Positive control: an injected import is reported. Runtime: a protected reader called from a frame whose module is acting raises `ContextIsolationError` | repo source; in-memory source strings | SYNTH |
| T-CTX-02 (M6; L5655, L5520) | "Every `context_log` item carries `vintage` and `retrieved_at_utc`. Revised series store the first print, the current value and the vintage date. LETF AUM, KOFIA margin debt, VRP, the VIX/VIX3M snapshot (16:00 ET) and the KOSPI200 MFIV snapshot (15:30 KST) are stamped `live`. T-CTX-01 still passes." Concretely: every item has keys `vintage` (may be null) and `retrieved_at_utc`; every item of a revised series that has an ALFRED vintage has non-null `first_release`, `latest`, `vintage_date` (an observation older than the first vintage has `vintage == null` and `note` containing `pre_vintage_history`); the five named item classes have `timing == "live"`; snapshots have `value_status == "live_snapshot"`; all 18 sheet ids present with `from_sheet == true`, `zscore_window` set; the log validates; `acts == false` | inline PIT-store rows for the 18 sheet ids, `PAYEMS` with two ALFRED vintages (first print 119.4, latest 9.7), synthetic rows for `KOFIA_MARGIN_DEBT`, `KRX_LETF_AUM_*`, `VIX_1600ET_SNAPSHOT`, `VIX3M_1600ET_SNAPSHOT`, `KOSPI200_MFIV_1530KST` | SYNTH for the assertions. Real leverage, MFIV and 16:00 ET snapshot data: OWNER (BL-U01 / BL-D02 provider; "The 16:00 ET VIX / VIX3M snapshot source — vendor or KIS — M6", L6031; KIS live sessions) |
| T-CTX-02 failure paths (R-32, L3865) | A log with an undeclared item field or a missing required field is not written to the artifact dir, is written to `quarantine/` with errors, raises one alert, moves no book counter, leaves every `runtime[].engine_state` unchanged. A stale context series yields `stale == true` with the value present and nothing else | inline | SYNTH |
| §12 M6 (L6368) "§11's context values are reproduced" at Level-1 (L5734-5735: vol levels ±0.1 pp; other ratios ±0.01; p-values ±0.01; prices exact) | 10y TIPS / 10y breakeven / 5y5y `2.93% / 2.36% / 2.36%`; Kim–Wright `1.02 (2026-09-25)`; MOVE `108.1 (2026-10-01)`; 10y–3m / 10y–2y `+1.07 / +0.46 (2026-10-01)`; probit "last read 0.095 (Q1a)"; Sahm (real-time) / U-3 `−0.07 / 4.1% (Aug-2026)`; CPI YoY `3.35%` (calendar lag; `3.71%` must not be produced; T-MISS-01: `3.353% ± 0.01`); Taylor residual "0.4–2.3 pp below the rules; central −0.9 pp; Fed range 3.75–4.00%"; Brent "Dated spot $113.96 (2026-09-29); BZ=F futures $102.59 (2026-10-01)"; USD/JPY `157.18 (DEXJPUS, 2026-09-25)`; BoK base rate `3.00%` (L6343-6352). Stress rows: VIX / VIX3M `16.34 / 18.37 (2026-09-30)`; HY OAS `3.12%`, 21-day change `+47 bp`; Baa−10y `1.47`, 21-day change `−12 bp` (L6319-6321). Broad USD `120.33 (2026-09-25)`, 20-day change `+1.67%` (L6336). Payrolls 2025: `+119.4k` first prints vs `+9.7k` current, "1 vs 6 negative months" (L1686). KOSPI rv21 `31.9%` at the 73rd percentile of the trailing 3 years (L6303) | "FRED series as downloaded on 2026-10-02 (latest vintage)" (L5714), ALFRED vintages, Yahoo `^MOVE`, `BZ=F`, ECOS; "the FRED snapshot of 2026-10-02" in the fixture manifest (L6018) | REFDATA. Local cache holds none of these series except `fred_DEXKOUS.csv` (last row 2026-09-18), `yf__VIX.csv`, `yf__VIX3M.csv` (to 2026-09-25), `yf_SPY.csv`, `yf_069500.KS.csv`, `yf_ZN_F.csv`, `yf_GC_F.csv`, `yf_CL_F.csv`; none reaches the §11 data dates, so they serve plumbing tests only, never goldens |
| Calculator unit checks (this brief; support T-CTX-02) | `recession_probit_et(3.57, 5.14)` = `0.744 ± 0.001`; `taylor_residual_range` returns (min, max) over exactly 12 rules and `value` is null; `vrp(16.34, [0.0]*21)` = `0.1634²/12`; `trend_state_sma10m` on 10 closes; a monthly series with a missing month gives NaN for the YoY whose endpoint is that month and a number for one whose window merely contains it | inline numbers | SYNTH |
| T-BREAK-01 (M6; L5656, L5525) clause 1 | "An official framework-change event shrinks every macro-conditioned multiplier to 1.0 and starts a forward record." With a temp rules store holding one rule object flagged macro-conditioned at 0.5: after `log_break(kind="policy_framework_change")` its multiplier is 1.0 from the next decision, one `record_reset` governance event exists for it, the forward-record marker exists; every non-flagged multiplier and every weight is unchanged. With the shipped v2.0 store the target list is empty and no weight changes. A direction-flip "event" cannot be logged as a trigger | temp rules store, temp artifact dir | SYNTH |
| T-BREAK-01 clause 2 | "The statistical-break flag and the BOCPD probability (hazard 1/250) are logged with no reader in any acting module or display." Rows of kinds `policy_stat_flag` and `scale_bocpd_prob` (with `hazard == "1/250"`) are appended; a repo-wide scan finds the research-log file name only in `core/ficc/context_log.py` and tests; `ui/` contains no reference; no `load_*` function for it exists | inline series | SYNTH |
| T-BREAK-01 clause 3 | "Scale-break re-anchoring occurs only on declared events." `reanchor_eligible` is False for: an unknown `event_id`; an event with `effective_date ≤` the header commit date; a card inside an R-25 lockout or demoted; a header without the re-anchoring window. True for a declared, calendar-dated event after the commit. The v1.2 2×-median flag writes a research row and changes nothing | inline | SYNTH |
| T-BREAK-01 clause 4 | "The statistical leg activates only after EX1's test (≤ 1 false break a decade on 1990–2026; flags within 6 months of 2012 and 2020)." Loading a store with `breaks.statistical_trigger != log_only` and no passing `ex1_test` record is refused | temp store | SYNTH for the gate. The EX1 test itself (1990-2026 EFFR, PCEPILFE, UNRATE, NROU, GDPC1, GDPPOT) is a backlog settling test (L5481), REFDATA, not an M6 exit condition |
| T-BREAK-01 market-structure | Every transition in the signed regime-tag file yields exactly one `market_structure` row; a second sync appends nothing; the 2026-07-16 leveraged-ETF rule change is present | the M1 regime-tag fixture (T-REGIME-01) | SYNTH once the M1 tag file exists; exact notice dates are OWNER-signed (L2034). Local cross-check values: TF GV-210…GV-218 (TF:L1114-1125): short-sale bans 2008-10-01…2009-05-31, 2011-08-11…2011-11-09, 2020-03-16 (partial lift 2021-05-03), 2023-11-06…2025-03-30; price limit ±30% 2015-06-15; sell tax 0.20% from 2026-01-01, 0.15% in 2025 |
| v1.2 scale flag reproduction (L1787) | fires on KOSPI 1999-2026 at 2008-12-10 and 2026-08-11; 4 fires in the US since 1990 | ^KS11 and ^GSPC histories | REFDATA. Local substitute: `yf_069500.KS.csv` reproduces 2026-08-11 with the definition of B.4 (c); `yf_SPY.csv` gives 4 fires. Not an M6 exit test |
| T-HEDGE-01, built-artifact clause (M6; L1968, L5590) | "With the live USD proxy and DTWEXBGS both stale, `hedge_credit_off = TRUE`, no acting component of the KR or US books fails closed (`fail_closed` false; asserted on the built `macro_state` from M6, §9.0b), and `vt` is unchanged". On the built KR and US `macro_state`: `flags.hedge_credit_off is True`; `"risk_model_input_stale" in flags.hedge_reasons`; `"USD_LIVE_PROXY" in flags.hedge_stale_inputs`; `fail_closed is False`; `vol.vt_weight_next` equals the fresh-input build; every `runtime[].halt is None`. "A stale DTWEXBGS alone (context) changes no hedge flag" | inline store with stale `USD_LIVE_PROXY` and `DTWEXBGS` rows | SYNTH |
| I-06c, "`macro_state` validates" clause (M6; L5696, L5594) | "The KR decision of 2026-11-26 (effective session 2026-11-27; the NYSE was closed on 2026-11-26): `gap_sessions` = 0, VaR scale 1, `kr_open_gap_event` false; `macro_state` validates; the books stay ARMED." "An out-of-schema context field never HALTs" | inline store + calendars covering 2026-11 | SYNTH |
| I-06c deferred clause (L5595) | "an acting-field schema error HALTs (OPS) the books the artifact describes" | — | runs from M8 (`bounds_ok`); not an M6 exit |
| T-SCHEMA-01 / T-SCHEMA-03 (M0; L5669, L5671) | the built `macro_state`, `overlay_decision`, `context_log` validate; "a field a rule writes that its schema lacks fails the test"; the §6.4 example validates with typed placeholders | built artifacts | SYNTH |
| T-DNB-01 (M0; L5682, L6238) for M6-06 | a rule object or context series with `source_kind: regime_model` is refused, so no displayed field can have a regime-model source; rendering the Macro page from a fixture yields no text node containing "regime" and no BOCPD value | fixture artifacts; walk the Flet control tree | SYNTH |
| §12 M6 "the Macro page lists every open owner decision" | the rendered page and the brief section contain D1…D6, each with `key`, `value`, `status`; FORWARD-SIM and refusal rows carry the text "not a recommendation" | registry fixture | SYNTH |
| T-TREND-03 (M8; L3047) | "The KOSPI trend state appears only in `context_log`." M6 provides the item `KOSPI_TREND_SMA10M`; the assertion runs from M8 | — | deferred to M8 |
| T-SCOPE-01 (f) (M8; L5675) | "A context_log schema failure HALTs nothing." M6 provides the refuse / quarantine / alert path | — | deferred to M8 |

---

## E. Interfaces

### E.1 Needed from earlier milestones

| From | Name and shape | Used for |
|---|---|---|
| M0 | schema registry keyed by `$id`; `validate(obj, schema_id) -> (acting_errors, display_errors)`; `write_artifact(obj, kind) -> Path` with quarantine; `config.macro_artifact_dir()` | all three artifacts |
| M0 | rules store loader with `context_log`, `breaks`, `owner_decisions`, rule object `R-13` (`kind: CONTEXT`, `inputs[]` with `source_kind`); DO-NOT-BUILD predicates | item whitelist, T-DNB-01 |
| M0 | `append_governance_event(kind, book_id, rule_id, key, old, new, actor, reason, refs)` (hash-chained, §6.6) | `record_reset` |
| M1 | `PITValue`, `MissingInput`, `RunContext`, `pit_value`, `pit_last`, `data_snapshot_id`, `is_stale`, `expected_available_utc` (L967-1020) | every read |
| M1 | derived PIT records with lineage: YoY and 3-month changes by calendar offset, in-house Sahm, monthly index; ALFRED vintages with `first_release`, `latest`, `vintage_date` (TASK-M1-13) | R-13 items |
| M1 | `regime_tags(market, d) -> dict`, the signed tag file with its transition list; `close_print_bound_utc`; `usable_at` (TASK-M1-04) | market-structure log, `decision_utc`, `extras.regime_tags` |
| M1 | lag-audit record `{checked, violations[]}`; per-book runtime entries (`runtime[]`); alert objects | `macro_state` |
| M1 | registry rows and bindings of C.3; providers for ALFRED, ECOS, Treasury | context reads |
| M2 | `market_vol_target -> VTResult`, per-book `BookVT`, label functions, `hedge_state -> HedgeState`, `compose -> ComposeResult` | `vol`, `flags`, `overlay_min`, `binding` |
| M3 | `estimator_gate(market, instrument_book, horizon=21) -> EstimatorSelection` | `vol.estimator*` |
| M4 | `sleeve_vol_scale -> VSResult`, `dm_gate -> Multiplier` (with `card`, `reasons`, `inputs`), `base_weights`, the binding list | `overlay_decision` |
| M5 | `concentration_bound -> ConcentrationBound`, `drawdown_ladder -> LadderState`, `gap_sessions`, the event store, R-08 annotation, RISK runtime; derived record for the pair share | `concentration`, `flags`, `annotations`, Korea context items |
| M2 / M5 (new hook, not in their briefs) | `books.neutralise_rule(rule_id, event_id)` on the per-book runtime state; `apply_overlays` returns 1.0 for a neutralised rule and logs it in `reasons` | R-18 trigger (i); no target exists in v2.0, so only the synthetic-rule test exercises it |

### E.2 Exposed to later milestones

| To | Name and shape |
|---|---|
| M7 (cards) | `regime_tags` remains the cards' source for "prints the split" and the ban-period basis line (the harness never reads the break log); `reanchor_eligible(card_header, event_id, ctx) -> bool`, called by the revision-commit path outside `core/quant/` |
| M8 (workflow) | `build_macro_state(market, ctx) -> dict`, `build_overlay_decisions(market, ctx) -> list[dict]`, `build_context_log(ctx) -> dict`, `write_context_log`, `sync_market_structure_breaks` — called by step `macro.build_artifacts` (L1220), the context and R-18 calls each inside their own exception wrapper (B.0); `macro_state_section(...)` for step `macro.brief` (L1236) |
| M8 (R-25) | `forward_record_start_requested` marker and the `record_reset` governance events |
| M8 (refusal legs) | `assert_not_acting_caller()` to place at the top of `refusal_krw_leg` / `refusal_rates_leg`; `ACTING_MODULE_PREFIXES` for I-03's static part |
| M8 tests | `KOSPI_TREND_SMA10M` context item (T-TREND-03); refuse / quarantine path (T-SCOPE-01 (f)) |
| M9 (R-16) | `SEP_TABLE2_BANDS` and the named oil series as Monte Carlo priors and scenario inputs, read through the PIT store, never from `context_log` |
| UI | the validated artifacts in the artifact dir; the guarded readers |

---

## F. Ambiguities, contradictions and conservative-reading decisions

| # | Issue (lines) | Decision |
|---|---|---|
| F-1 | §3.6 says the sources do not give the indicator list, windows or method (L1119); BL-G06 "blocks M6" (BL:L1439) | Resolved from the code (B.1). Not a regime model; text only |
| F-2 | "never presented as a regime state" (L1126) vs internal names `Regime`, `sheet.regime`, payload key `"regime"` used by `insights.py` and asserted in `tests/ficc_acceptance.py:529-540` | Change presentation strings only (B.1 table). Keep the dataclass and attribute. Payload key: keep and add `"descriptive_read_note"`; a rename to `"descriptive_read"` is the stricter option and costs one existing test line |
| F-3 | The Rates page shows a `Regime` stat (`ui/rates_page.py:113`) from `curves._regime`, the same rule-based curve classifier | Outside §3.6 (which covers the macro sheet). Not a regime model. Flag for the UI brief: relabel to "Curve move" for consistency |
| F-4 | `narrate_weekly_strategy` turns the descriptive labels into "Positioning ideas" text (`insights.py:408-490`, prompt `:543`) while P0 allows a displayed recommendation only from PASS cards (L499) | Pre-existing FICC narrative, not a macro overlay output and not an exposure. Conservative: caption the report "descriptive; not a recommendation; feeds no book". Owner or coordinator to confirm |
| F-5 | R-13 row "Existing sheet items: each of the 18 indicators … not listed above" (L1694) vs §12 M6 "every sheet item appears in `context_log` with `from_sheet=true`" (L6368) | All 18 appear once with `from_sheet = true`; extra R-13 statistics on the same series (changes, distance) are separate derived items without `from_sheet` |
| F-6 | T10Y2Y is a sheet item, but "Do **not** log 10y–2y as a prior" (L1679) | Log its level and z as a sheet item; compute no probability from it |
| F-7 | Sheet futures `ZN=F`, `GC=F` are continuous contracts; "Continuous-futures returns across rolls are forbidden" (L1378) | Level and z only in `context_log`; `note: "continuous contract; changes not roll-adjusted"` |
| F-8 | "A series with no binding may be read only by a `context` consumer" (L1891) is silent on a context read of a series that has only non-context bindings | Add explicit `{role: context, consumer: R-13}` bindings (C.3); never read through another consumer's binding |
| F-9 | Units: "decimals inside the core" (L373) vs the §6.4 examples in pp and thousands (`"Taylor residual range (pp)"`, `[-2.3,-0.4]`, `"Payrolls, 2025 monthly average (k)"`, L3898-3904) | Every item `name` ends with its unit. Follow the examples for the items they show; other rate levels are stored as decimals as `macro.py` does (`s.scaled(0.01)`), named "(decimal)". Display only |
| F-10 | Item schema requires non-null `obs_date`, `available_at_utc`, `retrieved_at_utc` (L3877); a never-acquired series has none | Omit the item; list it in `extras.missing_items`. Never fabricate a date |
| F-11 | `value_status` has no synthetic member (L3884); the legacy sheet degrades to SYNTHETIC under `auto` | A synthetic value is never written to `context_log`; listed in `extras.synthetic_excluded`, alerted. The legacy sheet table keeps its loud SYNTHETIC label |
| F-12 | Probit spread: R-13 and §7 say "monthly GS10 − TB3MS converted to bond-equivalent" (L1679, L4466); the §6.4 example's `source` says "FRED T10Y3M; published coefficients" (L3903). The bond-equivalent formula is not in the spec | Rule text governs: GS10 − BEY(TB3MS), monthly. `T10Y3M` is logged as its own item. BEY formula per B.2, supported by the spec's 0.744 (May-2023) |
| F-13 | In-house Sahm formula is not stated (L1678); whether a NaN 3-month mean inside the 12-month low makes the value NaN is not stated (L1353: "an endpoint or a member of an averaging window") | Standard definition: 3-month average of U-3 minus the minimum of the 3-month averages over the previous 12 months. Strict reading: NaN while any 3-month mean in the lookback is NaN (so NaN through the Dec-2026 reference month); `value = null`, `note` says why. M1-13 owns the series |
| F-14 | "yearly all-day Δbreakeven / Δnominal β" (L1682): window not defined | OLS slope of daily ΔT10YIE on daily ΔDGS10, calendar year to date; prior full years in `note`. Default, judgment |
| F-15 | VRP: "21-day realised variance" (L1689): return type, mean adjustment and VIX source not defined | Sum of 21 squared daily simple S&P 500 returns (monthly variance units, matching VIX²/12); VIX = the 16:00 ET live snapshot (item is "stamped `live`"). Default, judgment |
| F-16 | "KOSPI rv21 and its trailing-3-year percentile" (L1687): estimator details not given | `stdev(21 simple returns, ddof 1) × √252`; percentile within the trailing 756 sessions. Golden: 31.9% at the 73rd percentile (L6303) |
| F-17 | Turbulence / absorption ratio: asset universe and the rounding of N/5 are not specified (L1691) | Universe = a registry group named in `context_log.turbulence_universe` (owner input); until declared the two items are omitted and listed in `extras.missing_items`. n = max(1, round(N/5)). Local plumbing substitute: the nine `yf_XL*.csv` sector files |
| F-18 | "every **macro-conditioned** multiplier" (L1780): §7.1 has no field that marks a rule macro-conditioned (L4691-4705) | Optional rule-object flag `macro_conditioned: true`; the v2.0 list is empty ("no macro-conditioned multiplier acts in any book"). A future card conditioning on a policy or macro series must set it; M0 validation should refuse such a card without it |
| F-19 | How long a shrunk multiplier stays at 1.0 is not stated; mid-spell behaviour is an open council question (L5463) | At once (current text); stays 1.0 until a counted card revision is committed after the event; never reverts automatically. The shrink raises exposure of that factor, so it is the one place where the conservative default of L89 is overridden by explicit rule text |
| F-20 | Statistical flag: "CUSUM or BOCPD" with no parameters (L1782); BOCPD: "hazard 1/250, declared prior" with no model, series or output definition (L1788, L4475) | Log-only defaults of B.4 (b), (c); every row records its method and parameters; nothing reads them. Parameters need an explicit store entry (`prior: declared`) |
| F-21 | "the re-anchoring window stated on the affected card's header" (L1786): no such field in the §6.5 header schema, which is closed | `reanchor_eligible` returns False until the M7 package defines the field. No re-anchoring happens in v2.0 |
| F-22 | The architecture brief puts `log_break` in `core/ficc/context_log.py`; the R-18 logs are a second protected surface | One file for both (fewest files); both sit behind the same guard |
| F-23 | Policy rate in the Taylor family: "EFFR" (L1680) vs the example source "EFFR 3.875 mid" (L3900), which is the midpoint of the 3.75–4.00 target range | Use FRED `EFFR`, monthly mean of the reference month; the `source` string names the series used. The difference is a few bp, below the printed 0.1 pp |
| F-24 | "central −0.9 pp" (L1680, L6349) is not the midpoint of [−2.3, −0.4] (−1.35); R-18 uses "the midpoint of the Taylor range" (L1782) | Log the range only ("Report the min–max range only"). The R-18 series is the arithmetic midpoint. "Central" is not computed |
| F-25 | US `macro_state.vol.instrument_book` is required (L3567) but the only registered US book is the REJECTed `US_shares_KIS` (L4291) and D5 = none | Write `"US_shares_KIS"` with `vt_weight_recommended_book = 1.0`; the card label carries "REJECT (instrument: US shares via KIS, 50 bp, daily)". No US book exists, so no exposure follows |
| F-26 | `owner_decisions` description includes "every decision with status pending" (L3605); D5 is `pending` (L4148); the KR example shows only D1 and D2 (L3687-3688) | Follow the description: include D5 in every market's record |
| F-27 | UI box lists "owner decisions D1–D5" (L762); the Quick start and the task say D1-D6 (L65-74) | Show all six with value and status |
| F-28 | `vol.display_label_rel/abs` are required enums without null (L3562-3564); the absolute label needs ≥ 10 years of history (L4312) | When a label cannot be computed the builder omits it; the artifact is written with `extras.validation_errors` and an alert (display field, never HALT, L3370) |
| F-29 | A `MissingInput` with no visible record cannot fill the required non-null fields of `$defs/input` (L3633-3634) | Emit the entry from `pit_last` (last visible row) with the failure `status`; with no row at all the acting-field validation fails and the artifact is quarantined (fail closed) |
| F-30 | T-CTX-02 says "stamped `live`" for KOFIA margin debt and LETF AUM, which are published daily figures (L1413: "per source") | `timing = "live"` as the test requires; `value_status` from the PIT record |
| F-31 | Dates of "the 2012 and 2020 framework changes" (L1782) are not given | From the public record: the FOMC Statement on Longer-Run Goals and Monetary Policy Strategy, 2012-01-25, and its revision of 2020-08-27. They enter the break log only as owner-signed calendar events |
| F-32 | Tech-fund G-58 routes market valuation (CAPE, Fed model, forward P/E) to the context log as "CONTEXT display only" (TF:L870, TF:L442) | No data path exists here; registry role P (planned). Not built in M6; if added later it is a context item, never a signal (DNB-TF-11) |
| F-33 | Tech-fund XS-07 defines the pair share as 005930 + 005935 + 000660 over all KOSPI lines (53.71% on 2026-09-29, TF:L1295); the macro spec leaves the denominator to anchors (51–54%, L6310) | The context item logs the value the M5 risk layer computes and names its definition in `note`; the denominator choice is M5's and the owner's |

---

## G. DO-NOT-BUILD items and invariants that bind this area

- **§10 item 27** (L6186-6198): "A regime-model state, acting or displayed". "No regime-model state (jump model, Markov switching, GMM label or change-point 'regime') acts on exposure or is displayed on any QUANTGEN page in v2." "A BOCPD scale-break probability (hazard 1/250, declared prior) may be written to the R-18 research log only: never acting, never displayed, no R-18 dependency." "GMM scenarios stay deferred … and are never labelled as a current regime".
- **§10 item 24** (L6175): "Smoothed or forward-looking calm / normal / elevated / stressed labels, or using those labels (or the existing regime read or sheet z-scores) as gates". Sheet z-scores and the descriptive read gate nothing.
- **§10 item 30** (L6201-6205): "`max(σ̂_SMA20, implied)` sizing". "Implied vol is context, logged as live snapshots (VIX/VIX3M at 16:00 ET; QUANTGEN's KOSPI 200 MFIV at 15:30 KST; R-13)." "VKOSPI is not available at the KRX decision: KOSPI 200 options close at 15:45 KST".
- **§10 item 37** (L6224-6227): "A KOSPI trend card that acts". "In Korea the trend state is CONTEXT-ONLY: displayed, never acting."
- **§10 item 22** (L6163-6167): no non-PASS output as a recommendation; R-11 / R-12 only in display-only refusal books. FORWARD-SIM and refusal rows are marked "not a recommendation".
- **§10 item 21 / P0**: no order, cancel, withdrawal, deposit-address or transfer path; every artifact has `read_only: true`.
- **§10.3 refused shape** (L6238): "An acting or displayed field whose source is a regime model (`source_kind: regime_model`), or a smoothed or forward-looking label" — items 11c, 24, 27; check T-DNB-01.
- **§10.4** (L6257-6259): the R-06 σ̂ display labels stay; "The BOCPD scale-break probability is a research-log entry (R-18), never acting or displayed"; "The KOSPI trend state is displayed as context (R-28)".
- **Backlog DO-NOT-BUILD** (BL:L1761-1769): no trading-volume proxy for Korean leverage; "A leverage state needs direct AUM and margin data and BL-U01's test". Log the inputs; build no leverage state.
- **Tech-fund**: DNB-TF-11 (valuation timing as a signal; context display only, CR-12, TF:L437-442); DNB-TF-12 (classic technical indicators as signals, TF:L444-449): neither may appear in `context_log` as a signal or gate. XS-14 / G-60 (TF:L1302, TF:L872): "Do not count R-08 as factor-crash protection"; any crowding or stress gauge on the Macro page is a display. DATA-6 / G-11 (TF:L808): "log final investor-type flows with timestamps (t-1 history); no direction rule" — matches the R-13 Korea flow items. DATA-5 / G-10 (TF:L807): Korean regime and event flags; "event layer may only exclude or scale <= 1.0".
- **Invariants.** `context_log.acts` is the constant `false`. No context, sheet, break-log or refusal value reaches `core/quant/signals`, `core/quant/risk`, `core/quant/optimize` or `core/engine` (T-CTX-01, I-03). A stale or failing context input, a `context_log` validation failure and a display-field failure never HALT and never move a book counter (L1178, L3370, L4362-4363). Z-scores are "never thresholded for exposure" (L1123). No event tag or break entry changes any weight ("**No gross rule**", L1795; `events.tags_change_weights: false`, L4386); the single exception is the official-framework trigger on macro-conditioned multipliers, of which v2.0 has none. Turbulence is "Never a multiplier" (L1691). Forecasts and surveys are never inputs (L1162). Every item is point-in-time: `available_at_utc ≤ decision_utc`, `retrieved_at_utc ≤ knowledge_utc`; revised series carry vintages; nothing is interpolated (P5). Tests write only to temporary copies of the rules store and artifact directory (T-HERM-02).
