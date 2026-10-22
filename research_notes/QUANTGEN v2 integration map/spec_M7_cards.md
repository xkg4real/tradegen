# spec_M7_cards — implementation brief (QUANTGEN v2.0, milestone M7 part 2: blind header commits and formal card runs; TASK-M7-18 … TASK-M7-30)

Sources read in full: `QUANTGEN_MACRO_INTEGRATION.md` lines 1510-1527 (R-03), 1554-1577 (R-06), 1696-1706 (R-14), 3262-3360 (R-31), 4874-4966 (§8.4), 5303-5488 (§8.8-8.10), 5489-6038 (§9, every cited test row, §9.0a/b, §9.3, §9.4, §9.5). Supporting: 14-100 (Quick start), 556-651 (P7-P18), 1040-1113 (§3.5), 1499-1508 (R-02), 1528-1542 (R-04), 1578-1590 (R-07), 1707-1740 (R-15), 2115-2275 (R-21), 2330-2418 (R-22 rules 3-6), 2420-2538 (R-23), 2763-2887 (R-26), 2964-3153 (R-28, R-29), 3155-3260 (R-30), 3395-3477 (R-34), 3479-3497 (R-35), 3752-3798 (§6.2 card object), 3909-4119 (§6.5, §6.6), 4123-4152, 4270-4344, 4400-4705 (§7), 4709-4873 (§8.1-8.3), 4967-5076 (§8.5), 5171-5301 (§8.7), 6072-6260 (§10), 6356-6372 (§12). Tasks: `prep/tasks/M7.json`. Tech-fund `R3_TF_neural_link.md` 280-329 (§5.6), 1283-1310 (§13). Code: `docs/asset_expansion_study.py`, `docs/asset_expansion/cards/S_E2_voltarget_kodex200.json`, `ui/strategy_lab_page.py`, `core/quant/validate.py` 730-792, sibling briefs `code_quant_gate.md`, `spec_M2_risk.md`, `spec_M3_estimators.md`, `spec_M4_sleeves.md`.

Notation: `L####` = line of `QUANTGEN_MACRO_INTEGRATION.md`; `R3 L###` = line of `R3_TF_neural_link.md`. E = existing file, N = new file. "proposed" = name or path not fixed by the spec (L89: field names, parameters, bounds, formulas, thresholds, council wording are binding; proposed paths and function names may be renamed).

---

## A. Scope

| Task | Deliverable (one line) | Target files |
|---|---|---|
| TASK-M7-18 | After the freeze, commit blind, immutable headers with `header_md5`, package version + md5, `ledger_hash_at_registration`: `MACRO-R06-KR-ETF`, `MACRO-R03-US-MOM` (rev 1, 2, 3), `MACRO-R14-MULTI-TREND`, `MACRO-R31-KR-ETF`, `MACRO-R28-US-TREND`, `MACRO-R06-US-FUT`; CARD-P header must match its acceptance draft; `header_commit` governance event; ≤ 8 searched parameters over all macro cards | N `core/quant/cards.py` (`commit_header`); N `docs/macro_overlay/headers/*.header.json`; E M0 `validate_card_header`, governance appender |
| TASK-M7-19 | Card-study runner: refuses before the freeze, re-hashes the manifest every run, one JSON `model_card.macro` per rule and revision through the nine-step gate / CARD-P v2, 1× and 2×, printed lines, `results_md5`, hash-chained `cards/verdicts.jsonl` | N `docs/macro_overlay_study.py`; N `core/quant/cards.py` (`write_card`, `append_verdict`); N `core/quant/card_lines.py` (R-26 rule 6 lines); E `core/quant/backtest.py` (re-export lines only) |
| TASK-M7-20 | Archive the store rows behind each formal card's `data_snapshot_id`, md5-listed; lost archive = integrity failure | N `core/quant/cards.py` (`archive_snapshot`, `rederive_snapshot_id`); N `docs/macro_overlay/archive/<card_id>.r<rev>/` |
| TASK-M7-21 | R-06 KR formal long-history card; verdict PASS iff (i)-(iv) at the computed f; prints; raw-flag data check vs G-KR-L01 at Level-2; never rescued | runner entry `MACRO-R06-KR-ETF`; gate harness (`cardp_evaluate`, M7 part 1) |
| TASK-M7-22 | Post-freeze convention reproductions and gate-power goldens in v1.2-check / reference mode; none is a card run | N `tests/macro_cards_acceptance.py` (golden tier); N `tests/reference/` |
| TASK-M7-23 | R-06 US 50 bp registered card kept as `"REJECT (instrument: US shares via KIS, 50 bp, daily)"`, never re-run; disclosed flip computed on fixture U1 as a class | runner guard; rules store `vol_target.US.registered_card`; tests |
| TASK-M7-24 | R-03 CARD-O on QUANTGEN's own sleeve vs unscaled; revisions 2 and 3 headers committed before their runs; lowest PASSing revision acts | runner entries `MACRO-R03-US-MOM` r1-r3; E M4 `sleeve_vol_scale` |
| TASK-M7-25 | R-04 add-on step 3 on the R-03 ledger → label `"step 3 FAIL"`; validation rejects A-provisional / pooled route for a card already run | runner harness call; M0 `core/rules` validation shape 34 |
| TASK-M7-26 | R-14 TS-trend sleeve (12-1 sign, monthly, `min(1.0, 0.15/σ_12m)`), `multi_line` header, CARD-O diversification claim | E `core/quant/signals.py` (`ts_trend_weights`, proposed); runner entry `MACRO-R14-MULTI-TREND` |
| TASK-M7-27 | R-31 binding share frozen with the header; step-down CARD-P; §9.4 item 8 reference run | N `core/quant/card_lines.py` (`binding_share`, `persistence_check`); runner entry `MACRO-R31-KR-ETF`; E M5 `drawdown_ladder` |
| TASK-M7-28 | R-30 card-level clauses: R-24 CIs into Stage 3, counted-revision switch, stock-book refusal, estimator-calibration cap | E M3 `estimator_gate`; gate harness cap input; M0 validation |
| TASK-M7-29 | Stack CARD-P generator before a second de-risk factor joins a market's recommended book | N `core/quant/cards.py` (`maybe_generate_stack_card`); N `core/quant/card_lines.py` (`low_exposure_share`, `rebound_capture`) |
| TASK-M7-30 (spike) | Pending package-dependent values (§9.4 items 1, 4, 11, 12, 14): computed, printed beside the research value, md5-frozen; never asserted against it | N `tests/fixtures/macro/frozen_values.json` (proposed) + MANIFEST row |
| display | Strategy Lab scorecard reads macro cards through an adapter (L845) | E `ui/strategy_lab_page.py` (`load_macro_cards`) |

File count for this area (minimum that satisfies the manifest and the legacy readers): 3 new source files (`core/quant/cards.py`, `core/quant/card_lines.py`, `docs/macro_overlay_study.py`), 1 new test module, edits to 4 existing files (`core/quant/signals.py`, `core/quant/backtest.py` re-exports, `ui/strategy_lab_page.py`, `tests/run_all.py`). Reasons two core files are needed and not one: `card_lines.py` holds printed, never-gated arithmetic; `cards.py` holds integrity (md5, chains, archive). Neither belongs in the `definitions_md5` manifest (L4820 (b) lists only the R-21-R-24 and R-34 harness functions), so a fix in either is not a new package version.

---

## B. Build spec, module by module

### B0. Facts that bind every decision below

| Fact | Evidence |
|---|---|
| Order of work is fixed: harness tests → acceptance test → freeze → header commits → card runs. `docs/macro_overlay_study.py` refuses to run before the freeze; no real card's verdict is computed before it | L4812-4828, L2243, L5546 |
| Until the package is frozen and a formal card has run, every macro card is `NOT_RUN`; the recommended book carries the invariants only | L5377, L5417-5425 |
| This machine has none of the reference fixtures (`/home/claude/quantgen_macro_data/…`: KRX official closes, ^KS11 1997-2026, French Mom / Mkt-RF, `QX_DLA_*`, `QX_DLB_*`, `QX_EX1_qf3_trial_corr_diff.csv`, PX2 cash fixture). Local: `docs/asset_expansion/cache/*.csv` (`yf_069500.KS.csv` 2007-01-29 → 2026-09-23, `yf_SPY.csv` 1995-01-03 → 2026-09-25, `fred_DGS3MO.csv`, `yf__KS200.csv` one row; no KOSPI index history, no opens, no call rate) and tech-fund summary CSVs (no series) | cache listing; `datalab/results/r2_idx/*.csv` |
| The repository is not a git checkout: `git_hash`, "committed to the repository, an external, timestamped anchor" (L4820) and `verdict_filter` check (iii) "`git_hash` is a commit whose harness sources hash to the package manifest's entries" (L3487) have no source | `git rev-parse` fails in the repo root |
| Owner inputs still null: `sleeves.KR.notional_nav`, `sleeves.US.notional_nav` (L4462-4464), the ECOS code of `BOK_CALL_RATE` and its observation calendar (L76, L6029), the KODEX 200 listing date "from the KRX listing record" (L4932-4933) | L76 item (3) |
| Consequence: the code, the schemas, the header drafts with typed placeholders and every SYNTH test are deliverable now; no formal header commit and no formal card run can be made here. Section B15 states what is recorded | F-01 |
| Legacy cards (`docs/asset_expansion/cards/*.json`, 34 files, fields `decision` / `decision_reason` / `revise_target`) are globbed whole by every reader; macro cards must live in their own directory | `ui/strategy_lab_page.py` 31, 221-222; `docs/asset_expansion_study.py` 764-780 |
| Legacy runner writes an `INSUFFICIENT_DATA` error card on any exception (`error_card`, study 230-237). Macro cards must not: "If a bootstrap, the comparator or the episode list fails, no card is written. Partial verdicts are never written." | L2245 |
| Legacy `--quick` lowers bootstrap B through the global `V.GATE` (study 191-192). Forbidden for macro cards: B 2,000, seed 11 are frozen items; pass them explicitly from `gate.*` | L4584, L4506-4508 |

### B1. `core/quant/cards.py` (N, proposed) — header registry and card integrity

Paths (proposed; root = `config.macro_artifact_dir()` from M0, default `ROOT/docs/macro_overlay`):

```
headers/<card_id>.r<revision>.header.json        immutable once written
headers/<card_id>.r<revision>.draft.json         CARD-P drafts for the acceptance population (M7-14)
cards/<card_id>.r<revision>.json                 model_card.macro (header ∪ results)
cards/verdicts.jsonl                             append-only, hash-chained (R-35)
archive/<card_id>.r<revision>/rows.jsonl         store rows behind data_snapshot_id
archive/<card_id>.r<revision>/MD5LIST            md5 per archived file
gate/acceptance_runs.jsonl                       owned by TASK-M7-15
```

```python
def canonical_json(obj) -> bytes
# UTF-8 JSON, sorted keys, floats printed with repr, no insignificant whitespace (L4683, L5616); non-finite numbers -> null before writing
def header_md5(header: dict) -> str
# md5(canonical_json(header minus {"header_md5"})); covers header fields only (L3913, L4885)
def draft_md5(header: dict) -> str
# md5 of "the header fields without the package citation" (L4815): header minus VOLATILE_AT_COMMIT (F-02)
VOLATILE_AT_COMMIT = ("header_md5", "created_utc", "gate_package_version", "gate_package_md5",
                      "ledger_hash_at_registration", "N_raw_at_registration")          # proposed reading, F-02
def commit_header(header: dict, *, store, ledgers, governance, now_utc) -> dict     # returns the committed header
def load_header(card_id: str, revision: int) -> dict                                  # re-hashes; mismatch raises CardRefused
def write_card(header: dict, results: dict) -> Path                                   # validates model_card.macro; sets results_md5
def append_verdict(card: dict) -> dict                                                # one row to cards/verdicts.jsonl
def verify_verdict_chain() -> None                                                    # raises on a broken prev_row_md5 chain
def archive_snapshot(card: dict, rows: list[dict]) -> Path
def rederive_snapshot_id(rows: list[dict]) -> str                                     # md5 of the sorted content hashes (L5616)
def card_status(card_id: str) -> dict
# {"card_id","class","verdict" in PASS|REVISE|REJECT|INSUFFICIENT_DATA|NOT_RUN,"disposition","displayed_as","label","results_md5"} (L3757-3762)
def acting_revision(card_id: str) -> int | None                                       # lowest PASSing revision (R-03, L1519)
def disposition_for(header: dict, verdict: str, *, binding_share: float | None = None) -> tuple[str, str]   # (disposition, displayed_as)
def maybe_generate_stack_card(market: str, joining: list[dict], recommended_book) -> dict | None            # B13
class CardRefused(Exception); class PackageNotFrozen(CardRefused)                    # proposed names
```

`commit_header` algorithm (each refusal raises `CardRefused`, writes nothing; L4821-4826, L4876-4896, L4088, L2244, L2513):

1. `gate.package.frozen_utc` set and the manifest re-hash equals `gate.package.definitions_md5` (TASK-M7-16 `verify_package()`), else `PackageNotFrozen`.
2. `header["gate_package_version"] == gate.package.version` (`"2.0.0"`) and `header["gate_package_md5"] == gate.package.definitions_md5`; `header["checks"] == "gate_package_2.0.0"`. "A card whose header cites a package version or md5 other than the frozen one is refused" (L2244).
3. `validate_card_header(header)` (M0, R-26; schema `quantgen/model_card_header.macro.v2.0`, closed by `unevaluatedProperties: false`). Refused headers (L4088): no `ledger_hash_at_registration`; missing any of `instrument_book`, `rebalance`, `no_trade_band`, `notional_nav`; `notional_nav` ≠ `sleeves.<market>.notional_nav` at commit; a stock book used as a market-gross scalar; a futures line whose one contract exceeds 5% of `notional_nav` (exactly 5% allowed, L2816); a non-KRW book without `nav_fx`; a header that declares `selection_factor` or any other result field (`timing_profile`, `forward_record`, stability results; L4876, L3913); an acting long-sample card whose `start_band` or `midpoint_halves` is null. Also refused: header lacking `episode_rule_version`, `cash_convention` or `start` (L2391); `cash_convention.returns` other than `excess` (L2337); lowering a cost (L2800); `costs.schedule` that lowers a cost (L4882); a protective rule with a Sharpe or predictability claim (L4851, L3038); an R-28 instance with `market: KR` (L3003); COMB or log-HAR on `KRX_stock_book` (L3237); timing-fragile card without `live_feeds` (L3455; known only after a run, so enforced at `write_card`).
4. Family ledger: chain verifies (L2514); `header["ledger_hash_at_registration"] == ledger.hash(family_id)`; `header["N_raw_at_registration"] == len(rows)` (L4955-4956). `family_id` is assigned by rule from `QC_modules.csv` (L4902, L2440), never chosen.
5. CARD-P in the acceptance population (R-06 KR, R-28, R-29, R-31): `draft_md5(header)` equals the draft md5 cited in `acceptance_report.json`; "a CARD-P header must match its step-2 draft" (L4826). A CARD-P registered after the freeze (changed header, stack card, another market's card) first runs its own panels under the frozen rule 9(a): 300 shifted placebos (≤ 10% passing PC-1′) and 20 per-card placebos (≤ 2 passing); an excess leaves that card `NOT_RUN` pending council question Q5; the panels' results are md5-frozen with its header; no package version is created (L4815).
6. Span end: `data_span.end == gate.evaluation.data_cutoff[market]` for the drafted CARD-Ps (KR `"2026-10-02"`, US `"2026-10-01"`; a card whose data file ends earlier ends at that file's last date, L2339); for a header registered after the freeze "the last month-end official close before its commit" (L2339); never `"latest"`.
7. Parameter budget: Σ `len(searched_parameters)` over every committed macro header ≤ 8 (`gate.parameter_budget_searched: 8`, L4613, L4896). "Conventions declared before any backtest do not count."
8. Immutability: if `headers/<card_id>.r<revision>.header.json` exists → refuse (a header is "immutable once committed", L4876). Set `created_utc`, compute `header_md5`, write the file with `encoding="utf-8"`.
9. Append one governance event: `kind: "header_commit"`, `rule_id`, `key: card_id`, `new: header_md5`, `actor: "harness"`, `refs: ["§8.1.3 step 4"]` (L4096-4110). The family ledger hash is committed with the header (L2440).
10. `owner_decisions` in the header records the values at commit and is checked only at commit; a later ruling gives a dependent card a counted revision (L5672, L65).

Revision vs new card (L4890-4894, L4852; never an edit of a committed header):

| Change | Result |
|---|---|
| any threshold, window, multiplier, timing, universe, estimator, class, cash convention, start band or episode rule; adoption of a new gate-package version | new revision (`revision + 1`, same `card_id`), counted in N |
| a different claim, instrument book, rebalance rule, band or venue | new card (new `card_id`), also counted (DNB #23) |
| edit to `instrument_book`, `notional_nav`, `rebalance`, `no_trade_band` or a cost after a card's `results_md5` exists | refused; a new card id is required (L6243) |
| edit to an acting parameter in the rules store outside a revision | demotes the card (R-25, L4894) |
| D1 / D2 owner ruling | governance event; affected printed lines re-run; never a demotion; D2 gives R-31 a counted revision before its next run (L5446) |

Revision counts are never the trial count; every configuration ever run is a ledger row (L4893). T-CARD-01 words "A class or claim change creates a new revision and increments the family ledger" (L5663); see F-03, F-04.

`disposition_for` (L4089, L3767-3770, L4012):

| Condition | `disposition` | `displayed_as` |
|---|---|---|
| verdict `PASS`, `build_status_on_pass = BUILD_NOW` | `RECOMMENDATION` | `recommendation` |
| verdict `PASS`, `build_status_on_pass = BUILD_AS_INSURANCE` (requires `class = CARD-P` and a non-null `label`) | `BUILD_AS_INSURANCE` | `insurance` |
| R-31 step with frozen binding share ≤ 0.10 (needs no PASS) | `INVARIANT_STEP` | `invariant` |
| FORWARD-SIM cards R-28, R-29 until promoted | `FORWARD_SIM` | `descriptive` |
| R-11, R-12 | `REFUSAL_BOOK` | `refusal` |
| non-PASS factor held in the specification book (R-04; R-31 at share > 0.10; R-06 KR `NOT_RUN` / `INSUFFICIENT_DATA`) | `SPECIFICATION_ONLY` | `descriptive` |
| everything else (R-03 `NOT_RUN` per L3779; R-14 until its own PASS, L1705) | `DESCRIPTIVE` | `descriptive` |

Invariant asserted in `write_card` and in T-CARD-01: `disposition ∈ {RECOMMENDATION, BUILD_AS_INSURANCE}` iff `verdict = PASS`; `displayed_as ∈ {recommendation, insurance}` iff `verdict = PASS` and that disposition.

### B2. The headers (TASK-M7-18): field values per card

Common to all (schema consts, L3927-3992): `costs: {per_side: read_from_gate, floor: tick_floor, stress: 2.0, stress_line: printed}`; `cash_convention.returns: excess`; `regime_lines: from_R20_tags`; `timing.decision: close_t_earn_t_plus_1`; `checks: gate_package_2.0.0`; `gate_package_version: "2.0.0"`; `seed: 11`; `searched_parameters: []` (stated for R-06 KR, L4919: PC-6 neighbours come from the frozen `pc6_axes`, never from the header; proposed for the other cards, whose parameters are all fixed ex ante in their rules). `<…>` = typed placeholder filled at commit; "UNSPEC" = the spec gives no value, so the cell is a proposal or is left to the owner (section F). A cell without a line number is a proposal.

| Field | `MACRO-R06-KR-ETF` (L4900-4965, verbatim in C1) | `MACRO-R03-US-MOM` r1 / r2 / r3 | `MACRO-R14-MULTI-TREND` | `MACRO-R31-KR-ETF` | `MACRO-R28-US-TREND` | `MACRO-R06-US-FUT` (R-29) |
|---|---|---|---|---|---|---|
| `family_id` | `R-06` | `R-03` | `R-14` | `R-31` | `R-28` (BAND200 is a logged trial in the same ledger, L3004) | `R-06` (L3104) |
| `rule_id` | `R-06-KR-VT20` | UNSPEC (proposed `R-03-US-VS12`) | UNSPEC | UNSPEC | UNSPEC | UNSPEC |
| `revision` | 2 (v1.2's 2016-26 card was revision 1) | 1; 2; 3 | 1 | 1 | 1 | 1 (a new card, never a revision of the 50 bp card, L3067) |
| `class` | `CARD-P` | `CARD-O` | `CARD-O` | `CARD-P` | `CARD-P` | `CARD-P` |
| `claim` | the crisis-clustering label (C1) | UNSPEC verbatim text; substance: own-vol scaling of the momentum sleeve outperforms the same sleeve unscaled (L1515, L1526) | "diversification, i.e. correlation and drawdown behaviour against the equal-weight long-only basket, not outperformance" (L1702) | `"protection in persistent drawdowns; time-boxed; no Sharpe claim"` (L3308) | `"slow-bear protection via the volatility state"` (L2986) | UNSPEC verbatim; a protection claim, no Sharpe claim (L1559) |
| `claim_type` | `protection` | `outperformance` | `diversification` | `protection` | `protection` | `protection` |
| `build_status_on_pass` | `BUILD_AS_INSURANCE` | `BUILD_NOW` (L4785) | `BUILD_NOW` (L5397) | UNSPEC (F-11) | `BUILD_AS_INSURANCE` (L3006) | `BUILD_AS_INSURANCE` (L3092) |
| `tier` | `A` | `A` (L5383) | `A` (L5397) | "declared on the card" (L5396); F-11 | `A` via the pooled-onset rule (L2992) | `A` ("A pending", L5391) |
| `rule` | `vt = min(1.0, 0.20 / sigma_SMA20(t))` … | r1 `vs = min(1.0, 0.12 / σ126(t))`; r2 target = expanding median of σ126 (min 252 obs), cap 1.0; r3 `vs = min(1, (0.12/σ126)²)` (L1518-1519) | 12-1 month sign, monthly; per-asset weight `min(1.0, 0.15 / σ_12m)` (L1701) | steps −8% → 0.5×, −12% → 0.5× + new-entry block, 21 sessions (L3277-3301) | month-end close < SMA10m → 0.5 else 1.0, applies next month (L2983-2984) | `vt_US(t) = min(1.0, 0.15 / σ̂_SMA20(t))`, daily (L3083) |
| `parameters` | `{estimator: sma, window: 20, target_ann: 0.20, cap: 1.0, floor: none}` | `{window: 126, target_ann: 0.12, cap: 1.0, floor: 0.0, min_obs: 126, series: paper_unit_gross_long_short, apply_to: sleeve_budget}` + r2 `{target: expanding_median_sigma126, min_obs: 252}`, r3 `{vs: "min(1, (0.12/sigma126)^2)"}` (L4318-4320) | `{signal: sign_12_1, rebalance: monthly, vol_window_months: 12, target_ann: 0.15, cap: 1.0, overlay_exempt: true}` (L4326) | `{steps: [{dd: -0.08, mult: 0.5}, {dd: -0.12, mult: 0.5, evaluator_block_new_entries: true}], dwell_sessions: 21, step_reference: running_peak_since_last_reset, hard_stop_reference_resets_at_dwell_end: false, composition: min, denominator: whole_book_nav}` (L3316-3321) | `{signal: month_end_close_below_sma10m, multiplier_below: 0.5, multiplier_above: 1.0, decided: month_end_close, applies: next_month, composition: min, exposure_basis: total}` (L3013-3014) | `{estimator: sma, window: 20, target_ann: 0.15, cap: 1.0, floor: none, rebalance: daily, exposure_basis: total}` (L3105) |
| `estimator` | `sma20` | UNSPEC (σ126 sample SD, ddof 1; proposed `sd126`) | UNSPEC (proposed `sd12m`) | UNSPEC (proposed `sma20`, the declared VT20 book's) | UNSPEC (proposed `sma20`, the vt book's) | `sma20`, fixed before the run (L3083) |
| `instrument_book` | `KRX_ETF_line` | `US_shares_KIS` (50 bp, both legs, L4823) | `multi_line` + `instrument_lines[]` = one `{market, instrument_book}` per index, futures or ETF line, never a stock book (L1702, L3949) | `KRX_ETF_line` (KR book; KOSPI VT20 at 3 bp, L5396) | `CME_micro_ES` (incremental on R-29's futures vt book, L2988, L3025) | `CME_micro_ES`, cost class futures 5 bp (L3106-3107) |
| `rebalance` / `no_trade_band` | `daily` / `0.0` | `daily` (daily recomputation, L1520) / `0.0` | `monthly` / `0.0` | `daily` / `0.0` | `monthly` / `0.0` | `daily` / `0.0` |
| `notional_nav` | `<sleeves.KR.notional_nav at commit, KRW>` | UNSPEC key (F-07) | UNSPEC (one per line market; F-10) | `<sleeves.KR.notional_nav>` | `{ref: sleeves.US.notional_nav}` resolved (L3028) | `{ref: sleeves.US.notional_nav}` resolved (L3109) |
| `nav_fx` | none (KRW book) | required (non-KRW book): `{series: USDKRW_1530_SNAPSHOT, history: ECOS_1530_CLOSE, role}` (L2812) | required for non-KRW lines | none | required, role `forward_sim` | `{series: USDKRW_1530_SNAPSHOT, history: ECOS_1530_CLOSE}`, role `forward_sim` (L3110, L2812) |
| `fill_model` | `KRX_close_auction` | UNSPEC (proposed `NYSE_moc`) | per line | `KRX_close_auction` | `NYSE_moc` (L3030) | UNSPEC (proposed `NYSE_moc`); `roll_calendar` required |
| `data` / `history_first_close` / `data_span` | KRX official closes, `1997-04-01`, start `first_close_plus_20_session_warmup`, end `"2026-10-02"` | the sleeve's paper long/short series "over its declared history (history start and span written in the header)" (L4823); UNSPEC values (F-07) | 12 index lines; UNSPEC list and span (F-10) | KRX official closes; as R-06 KR | US month-end official closes; span UNSPEC (F-05) | French daily Mkt-RF and RF 1926-07-01 → 2026-08-31 for the settling span (L3080, L3095); F-05 |
| `cash_convention` | `{returns: excess, cash_series: BOK_CALL_RATE, day_count: act_365}` | zero-investment L/S series get no cash term (L2334); F-08 | `US_RF` / registry cash per market (L4546) | as R-06 KR | `{returns: excess, cash_series: US_RF}` | `{returns: excess, cash_series: US_RF}` |
| `episode_rule_version` | `"1"` (θ 0.20 KOSPI) | `"1"` | `"1"` | `"1"` | `"1"` (θ 0.15 S&P) | `"1"` (`episodes: {theta: 0.15}`, L3111) |
| `start_band` | `{shape: R-06_KR, from: "1997-05", to: "1999-12", step: month, starts: 32, require: {no_reject: true, pass_share_min: "2/3"}}` | F-09 | null until it would act on a long sample (F-09) | null (specification book) | null | `{shape: decade_spaced, step: decade, starts: 10, require: {no_reject: true, pass_share_min: "4/5"}}` (L2341, L3091) |
| `midpoint_halves` | `{split: calendar_midpoint, split_date: "<the calendar midpoint of the fixed span>", require: no_reject}` | F-09 | null | null | null | required (no REJECT in either half, L3091) |
| `gating_lines` | `full_span: v2_PASS`; `etf_era: {from: "<first day of the first full month after the KODEX 200 listing>", to: "2025-12-31", require: v2_PASS}` | none | none | none | none | none (the settling-run conditions are in `settling_run`, L3112-3114) |
| `primary_oos_line` | `etf_era` | declared on the card (L4563); UNSPEC | UNSPEC | UNSPEC | UNSPEC | UNSPEC |
| `comparator` | `S_same_average_exposure` | `overlay_off` (the same sleeve unscaled, L1526) | `overlay_off` enum; benchmark = the equal-weight long-only basket of the same indices (L1705); F-10 | `S_same_average_exposure` (S = declared book without steps × the steps' mean multiplier, L3308) | `S_same_average_exposure` (S = VT book × the trend's mean multiplier, L2989) | `S_same_average_exposure` |
| `benchmarks` | `[buy_and_hold, overlay_off, static_same_avg_exposure, ewma_derisk]` | all four (L4969-4973) | all four | all four | all four | all four |
| `claim_lines` / `pooling_rule` | none | none | none | none | claim line: stacked ΔMDD on VT ≥ 3 pp, miss → cap INSUFFICIENT DATA (`claim_not_shown`), never REJECT (L2991); `pooling_rule: {decluster_gap_months: 10, indices: [SPX, N225, HSI, DAX, FTSE100, TAIEX], own_market_veto: true, declared_before_any_run: true}` (L3018-3019) | none |
| `outcomes` | `{PASS: BUILD-AS-INSURANCE, INSUFFICIENT_DATA: specification_book_control_regated_on_new_objective_episode, REJECT: archive}` | PASS → factor enters the recommended book through `verdict_filter` with its "step 3 borderline" flag; else specification book | PASS → sleeve acts; else displayed descriptively (L1705) | PASS → steps act in the recommended book; else specification book while share > 0.10 | PASS → BUILD-AS-INSURANCE once a US / non-Korean sleeve exists (D5); else FORWARD-SIM | promotion requires all of L3092-3095; else FORWARD-SIM |
| `owner_decisions` | `{risk_layer.korea_caps.template: msci_25_50}` | none | none | `{risk_layer.drawdown.hard_stop.level: -0.15}` (value of `{ref}` at commit; never a literal copy in the rules block, L3327) | `{sleeves.US.line: none}` | `{sleeves.US.line: none}` |
| `label` | byte-identical to the R-06 label | null or UNSPEC | null; printed failure-mode text "not fast-crash protection" (L5647) | UNSPEC; default label L5248 (F-11) | UNSPEC; default label L5248 | UNSPEC; default label L5248 |

Default CARD-P label (L5248): `"protective: reduces tail losses vs a same-exposure static book; not expected to outperform"`.

R-03 revision rule, declared before the runs (L1519): each revision has its header md5 committed before its run, is one trial, and passes step 3 at N_eff or fails; "If more than one registered revision PASSes, the lowest PASSing revision number acts". Research-phase runs of revisions 2 and 3 are already ledger rows (L5384-5385); step 3 is recomputed on the enlarged ledger.

### B3. `docs/macro_overlay_study.py` (N) — the runner (TASK-M7-19)

```
python docs/macro_overlay_study.py [--only <card_id>[.r<rev>],…] [--mode formal|v12check|reference] [--commit-headers]
```

| Mode | Writes | Notes |
|---|---|---|
| `formal` (default) | card file, `verdicts.jsonl` row, archive, ledger rows | refuses before the freeze; frozen package only |
| `v12check` | harness outputs only, never a card record | v1.2 protective checks of §9.3.3 (L5984-5990); may set `returns: raw`; reachable only from `tests/reference/` and `docs/` (L5498) |
| `reference` | harness outputs only | `reference_only=True`; configurations the rules store refuses (cap above 1, DM gate at 0×, product stacks, literal v1.2 ladder); `core/` cannot import that code (L5992) |

Process setup (T-REPRO-01b, L5667, L4683-4684): set `OMP_NUM_THREADS`, `OPENBLAS_NUM_THREADS`, `MKL_NUM_THREADS` to `1` before importing numpy; every random stream = `np.random.Generator(np.random.PCG64(ss))` with `ss = np.random.SeedSequence(11)` and `ss.spawn(n)` children for workers; reconfigure stdout to UTF-8 (cp949 console); no network (reads fixtures or the PIT store only, L2133).

```python
def preflight() -> None
#  1 gate.package frozen, else refuse ("docs/macro_overlay_study.py refuses to run", L2243)
#  2 verify_package(): re-hash the definitions manifest == gate.package.definitions_md5, acceptance_report.json md5 ==
#    gate.package.acceptance_report_md5; any mismatch -> refuse (T-CARD-02, L4820)
#  3 chains verify: governance_events.jsonl, every family ledger, cards/verdicts.jsonl, gate/acceptance_runs.jsonl
#  4 R-34 positive control tripped (LP >= 0.20), else every card run is blocked (L3454)
def run_card(card_id: str, revision: int, *, knowledge_utc) -> dict     # the written card, or raises (nothing written)
def main() -> int
```

`run_card`, formal mode (order binding where a line is cited):

1. `h = cards.load_header(card_id, revision)`; re-hash ≠ `header_md5` → refused (T-CARD-01). Package citation ≠ frozen → refused (L2244). No ledger hash or missing R-26 header fields → refused.
2. Registered-card guard: `card_id` of the R-06 US 50 bp card → refused (`vol_target.US.registered_card.rerun: false`, L4291).
3. Pin `knowledge_utc`; freeze the data snapshot; `data_snapshot_id` = md5 of the sorted content hashes visible at `knowledge_utc` (L5616). Close-type inputs need `value_status = official_close` (L1566); episodes built from vendor-derived or provisional closes are refused (L2394). Cash series read from the frozen snapshot, role `history`, `available_at` recorded and never filtered; a day of the series' own calendar without a value refuses the card (never cash = 0; L2333, L2393).
4. Books on R-22 excess returns `x_t = w_t·(r_t − c_t) − cost_t` (L2331): on, off, S (`x_S = m̄ · x_off`, constant, same days, uncosted, L2143), buy-and-hold, EWMA(0.94) de-risk line (same target, cap 1.0, L4973). Card-book convention (rule 6, L2348): data invariants and bounds applied; R-07 hard stop with its re-arm, concentration caps and semiconductor cap excluded, except a card whose claim concerns them (R-31 includes the hard stop; the stack card includes both). A run with the convention flipped is refused (T-RLAYER-01).
5. Costs: per-side rate from the gate's table through `cost_per_side(instrument, date, price, side)` with the tick floor `max(table_rate, commission + 0.5*tick/price + tax_side)` (L2794-2795); turnover `|Δw|` charged on the day the new weight earns; both legs for L/S sleeves; buy-and-hold and S uncosted (L5019-5020); declared `costs.schedule` applied (may only raise). Every card is built twice: 1× and 2× (`cost_stress: 2.0`; T-COST-01).
6. Lag audit on the L ≥ 1 and strict rows: a violation raises `LookAheadError` and the card is not written (L5609); `lag_audit_violations` const 0 (L4082).
7. `step3(card)` (R-23): N lines, `selection_factor = {value, rule: "computed_by_step3", alt_value}`, recomputed at the run; where it differs from the acceptance report's f for the draft, the larger binds and both are printed; the run is never refused for the difference (T-SEL-01 (e), L2473). The card's own run rows and null-distribution runs never enter its f.
8. Gate: CARD-P → `cardp_evaluate(header, books) -> CardPResult` (PC-1′…PC-7, caps, verdict order coded once, L2125, L5228-5250), evaluated for every gating line, every band start, both midpoint halves, every regime line; CARD-O → `overlay_card_eval(card, ledger) -> CardResult` (steps 1-9 with R-23 and R-24, L4758-4768). Verdict at the binding f; `verdict_at_f1` and `verdict_at_f_neff` both written (L4091).
9. `timing_profile(card)`: L ∈ {−1, 0, 1, 2, 3} + publication-strict; L ≤ 0 rows only inside the `timing_probe` sandbox, tagged `synthetic_lookahead`, written outside the production artifact directory; `assert abs(dSR[1] - card.reported_dSR) < 1e-9`; every lag appended to the family ledger (L ≤ 0 as `NON-COMPLIANT`); a card whose gate statistics read an L ≤ 0 row is refused (L3417-3432, L3462). FR printed with a paired-bootstrap 90% interval, never gating, until the council answers the Sharpe-neutral question (L5457).
10. `power_line(card)`: `se_hac`, `se_blk250`, `se_plateau`, `mde80 = 2.1232 × SE_plateau`, power at Δ +0.05 and +0.10; CARD-P also `pc3_power_at_0` and `years_to_detect_0p05`; a card without them is refused (T-POWER-02).
11. Printed lines: R-21 rule 10 (ΔMDD, ΔCDaR95, daily ΔES99 with bands; GJR-null percentile, 1,000 paths, seed 11; 20-shift placebo panel; time under water; re-entry lag; post-trough → +63-session window and the three cost episodes; rolling 5-year blocks; DSR vs 0 and PSR vs S); R-26 rule 6 (B4); `with_risk_layer` (hard stop and caps) for the on and S books (L2348); step 9: `live_sharpe_multiplier: 0.60` with the Harvey-Liu haircut and a BY q-value; CARD-P also 60% of the ΔES legs and of ΔMDD (L4768); Lo-adjusted Sharpe at 20 and all lags; the values of `owner_decisions` in force (L5444); every acceptance attempt and its outcome beside the verdict (L2188, `printed_beside_every_verdict: true`).
12. `ledger_hash_at_run` = hash of the ledger including the run's own rows; it must match the stored ledger, or the card is not written (L2513).
13. `cards.write_card(h, results)`: card = header ∪ results, validated against `quantgen/model_card.macro.v2.0` (closed); `results_md5` over the result fields (F-15); `read_only: true`; reproducibility fields `seed`, `git_hash`, `config_hash`, `data_snapshot_id`, `knowledge_utc`, ledger hashes, `results_md5`, `gate_package_version`, `gate_package_md5` (L4680-4682).
14. `cards.append_verdict(card)`; `cards.archive_snapshot(card, rows)`; the card file and `verdicts.jsonl` are committed together (L3487).
15. Any exception in steps 3-12 → nothing is written, the card stays `NOT_RUN`, the exception is reported. No error card.

Verdict strings: `PASS`, `REVISE`, `REJECT`, `INSUFFICIENT_DATA` (schema enum L4007; prose "INSUFFICIENT DATA"). `NOT_RUN` exists only in `overlay_decision.card.verdict` (L3759) and in `cards.card_status`; it is never written to a `model_card.macro` file. Reason codes (L4779): `sufficiency`, `inconclusive`, `underpowered`, `do_no_harm`, `timing_fragile`, `stability`, `claim_not_shown`, `estimator_calibration`, or the failed check's id. `permitted_fix ∈ {null, "widen_grid", "lengthen_holding", "extend_history", "repair_rerun"}` (L4014). A REVISE names the first failed check and the only permitted fix; lowering a cost is never permitted (L4775-4777).

CARD-O gate as the runner calls it (L4758-4768, L4985): step 1 purged walk-forward 756 / 126 / embargo = holding period, and "With no searched parameter the walk-forward reduces to the full sample, and the card says so"; step 2 LW studentized circular-block bootstrap, blocks `max(21, PW(ψ))`, B 2,000, seed 11, HAC p printed, p = 0 printed `"< 1/B"`; step 3 deflated ΔSR vs overlay-off ≥ 0.95 at `N_eff = max(N_clusters, N_equiv)`, printed at N_raw and N_hat_linear with `"step 3 borderline"` if < 0.95 there; step 4 PBO by CSCV (16 blocks) over ledger ∪ the frozen PC-6 grid on paired ΔSR, run only with ≥ 10 configurations else print `"PBO not run (n < 10)"`, REJECT when PBO > 0.2 and the winner loses in > 10% of splits; step 5 paired ΔSR vs overlay-off, one-sided p ≤ 0.10, a failed p with MDE80 > 0.10 → INSUFFICIENT DATA (`underpowered`); step 6 rebuilt at 2×, Sharpe > 0, losing at 2× is a REJECT only when the interval includes zero, otherwise REVISE; step 7 ≥ 50% of neighbours keep ≥ half the Sharpe; step 8 ≥ 60% of calendar years positive, tied years printed as ties; step 9 printed. Plus the timing-fragility cap (INSUFFICIENT DATA) and the estimator-calibration cap (REVISE).

### B4. `core/quant/card_lines.py` (N, proposed) — printed, never gated (R-26 rule 6, L2827-2832; R-31; §8.7)

```python
def exec_variants(card) -> dict            # {"A": sr, "B": sr, "C": sr}
#  A same close: weight decided at the close of t traded at that close, earns from t+1 (the card's own convention)
#  B next open: traded at the open of t+1; the overnight gap (close t -> open t+1) is earned at the old weight
#  C one-session lag: traded at the close of t+1, earns from t+2
def overnight_intraday_attribution(card) -> dict
#  returns and the overlay's benefit split into close->open and open->close legs; "Any KRX intraday long card must clear
#  the -11% a year open-to-close drift" (L2829)
def turnover_by_regime(card) -> dict       # sum|dw| per year, per R-20 regime line
def stress_cost_line(card) -> dict
#  cost x clip(sigma20 / sigma_median, 1, 5), plus 10 bp per side on ETF-line close fills on days with |r| >= 3%;
#  printed and non-gating until calibrated on KIS quote snapshots; can only raise a cost (L2831, L2870)
def roll_calendar(future) -> list; def roll_cost_line(card) -> dict; def ban_basis_line(card) -> dict
#  futures books only: roll before expiry on a fixed calendar (the expiring KOSPI200 contract stops at 15:20 KST on its
#  last day); a basis line for short-sale-ban periods (R-20 tags) (L2832)
def binding_share(step_mult: np.ndarray) -> float            # n_bind / n_sessions, n_bind = sessions with step_mult < 1 (L3305)
def persistence_check(returns, activations, horizon: int = 21) -> dict   # Kaminski-Lo: mean next-21-session return after an activation vs unconditional
def low_exposure_share(total_exposure: np.ndarray, level: float = 0.25) -> float    # stack card: share of days at <= 0.25x
def rebound_capture(book_returns, bh_returns, cost_episodes: dict) -> dict          # stack card: book vs buy-and-hold in gate.evaluation.cost_episodes
```

Outputs: `model_card.macro.printed = {exec_variants: {A, B, C}, overnight_intraday, turnover_by_regime, stress_cost, roll_cost, ban_basis, binding_share, binding_shares, n_halts, persistence_check, …}` (L4077-4081, L2855); `costs_per_side = {table_bp, floor_bp, applied_bp, stress_line, roll_cost_line}` (L2854). B needs daily opens with `value_status` and `session_date` (L2785); an instrument whose tick table cannot be read for the date is not tradable in the simulated book (L2863). Reuse: `core.quant.strategies.simulate` for constant-weight books and M2's `costed_book` / `static_comparator`; no new engine.

Config read: `instruments.printed_lines: [exec_variants_ABC, overnight_intraday, turnover_by_regime, stress_cost_line, roll_cost, ban_period_basis]`; `instruments.stress_line: {multiplier: "clip(sigma20/sigma_median, 1, 5)", etf_close_extra_bp_if_abs_ret_ge_3pct: 10, gated: false}` (L4405-4406); `gate.evaluation.cost_episodes: {rebound_2009: ["2009-03-09", "2009-06-30"], rebound_2020: ["2020-03-23", "2020-06-08"], h1_2026: ["2026-01-02", "2026-06-30"]}` (L4543-4544).

### B5. `cards/verdicts.jsonl` and the snapshot archive (TASK-M7-19, TASK-M7-20)

Row (one JSON line, canonical; L3487): `card_id`, `revision`, `header_md5`, `results_md5`, `verdict`, `disposition`, `gate_package_md5`, `data_snapshot_id`, `git_hash`, `ledger_hash_at_run`, `prev_row_md5` (md5 of the previous line; null only on the first). Append-only; a hand-edited row breaks the chain and blocks every admission until restored (T-CARD-03, M8).

`verdict_filter` (M8) admits a factor only if (i) the card file re-hashes to the committed `results_md5` and the chain verifies; (ii) `gate_package_md5` equals the frozen `definitions_md5`; (iii) `data_snapshot_id` recomputed from the store at the card's `knowledge_utc` matches and `git_hash` is a commit whose harness sources hash to the manifest's entries; otherwise the factor stays in the specification book and `VERDICT_INTEGRITY` (severity page) is raised (L3487). This area must therefore write all four items verifiably.

Archive (L6013): with every formal card, the store rows behind its `data_snapshot_id`, sorted by content hash, one canonical JSON row per line, plus `MD5LIST`. `rederive_snapshot_id(rows) == card["data_snapshot_id"]`, and re-running the card's statistics from the archived rows reproduces them bit for bit (TASK-M7-20, T-REPRO-01b). A lost archive is an integrity failure, never a reason to re-run silently; losing it "would drop every admission at once and step exposure up to the invariants-only level" (L6013). The card schema is closed, so the md5 list is a sidecar file, not a card field.

### B6. R-06 KR formal long-history card (TASK-M7-21; L1574, L5387, L5706)

Inputs: KRX official KOSPI closes from 1997-01-03, Saturday sessions before 1998-12-12 included (L6026, L4937); `BOK_CALL_RATE` daily (latest rate dated on or before the previous session × calendar days / 365; a closed day of the rate's own calendar carries the prior rate, L2333); KODEX 200 listing date; `sleeves.KR.notional_nav`; R-20 regime tags; the R-06 family ledger seeded per §9.5 (L6020).

Run definition: SMA20 σ̂ (`stdev(r[t−19 … t]) × √252`, simple returns, ddof 1; a flagged stale-carry day excluded and the window extended, L1561); `vt = min(1.0, 0.20 / σ̂)`, cap 1.0 permanent, decided at the KRX close (`available_at ≤ close_print_bound_utc(KR, t)`: 06:30:30Z today, 06:00:30Z before 2016-08-01), earning from t+1; start = first close 1997-04-01 + 20-session warm-up; end 2026-10-02; KRX ETF line 3 bp with the futures cost class before the KODEX 200 listing; objective ≥ 20% KOSPI episodes with the §8.6 windows printed; `p_ni = max(p₁₀, p_PW)`; 8-neighbour plateau on `pc6_axes.vol_target` = {10, 20, 40} sessions × {0.15, 0.20, 0.25} (L4516).

Verdict (the card receives the worst of its gating lines, order REJECT < INSUFFICIENT DATA < REVISE < PASS, then the stability cap; L5226, L5221). PASS requires all of:

| # | Condition | Schema field (the mapping of (i) and (ii) onto `regime_line_results` is proposed) |
|---|---|---|
| (i) | a v2 PASS on the full span | `regime_line_results[{line: "full_span", gated: true}]` |
| (ii) | a v2 PASS on the ETF-era line, from the first full month after KODEX 200's October-2002 listing to 2025-12 (exact date from the KRX listing record, written in the header) | `regime_line_results[{line: "etf_era", gated: true}]` |
| (iii) | no REJECT at any monthly start 1997-05 … 1999-12 (32 starts) and PASS in ≥ 22 of them, compared as integers `3·n_pass ≥ 2·n_starts` | `start_band_results = {starts, verdicts, n_pass, n_starts, n_reject, floor_pass}` |
| (iv) | no REJECT in either pre-declared calendar-midpoint half | `midpoint_halves_results = {h1, h2}` |

all at the computed selection factor, with both verdicts printed (f = 1 and f = N_eff). The function that combines (i)-(iv) lives in the frozen gate harness (`cardp_evaluate`'s gating-line and stability-cap path); I-16 tests it "with injected sub-verdicts for each failing branch" (L5706). Needed as a pure function (name proposed; E1):

```python
def combine_card_verdict(gating: dict[str, str], band: list[str] | None, halves: tuple[str, str] | None,
                         shape: str | None) -> tuple[str, str | None, list[str]]      # (verdict, verdict_reason, caps_applied)
# base = worst of gating verdicts (REJECT < INSUFFICIENT_DATA < REVISE < PASS)
# stability cap (only lowers a PASS or REVISE to INSUFFICIENT_DATA, reason "stability"; never creates a REJECT):
#   any REJECT in band, or 3*n_pass < 2*n_starts (5*n_pass < 4*n_starts for decade_spaced), or a REJECT in either half
```

Printed, not gated (L1574): the 2002-10 → 2015-12 pre-design line; the ETF-era line to the present; 1997-2002 and 2016-25 alone; rolling decades; PC-4 under §8.6; the EWMA(0.94) line; timing return, years lagging S, the H1-2026 bull tax and the median re-entry lag; the per-regime table (price limits, Saturday sessions, the 1997 peg, ETF availability); `with_risk_layer`; `krx_etf_3bp_throughout`; the insurance label; the differences from G-KR-L01 (Yahoo, cash 0, v1.2 checks) with the expected direction of each convention change (excess returns: ΔSR +0.026 → +0.006, p_ni 0.052 → 0.078), "informative, never a pass condition and never a reason to change the package" (L5706).

Data check (v1.2-check mode): the raw-flag run on the KRX official-close fixture reproduces G-KR-L01 within Level-2 tolerance (Sharpe ±0.03; window returns ±2 pp; max DD ±2 pp; p-values ±0.02; L5736), each deviation explained in the acceptance report; "it tests the data source, never the card".

Indicative expectation (never asserted; L5387, L53): INSUFFICIENT DATA through f. Indicative f on Yahoo 2016-26 difference series vs S: 1.26-1.30 on R4's rows alone, 1.49 with the DL-A grid, 2.87 family-wide with the US VT15 rows (N_clusters 2); PC-3 needs `p_ni × f ≤ 0.10`; at the indicative excess-return p_ni 0.078 any f > 1.28 gives INSUFFICIENT DATA, reason `underpowered` (MDE80 = 2.1232 × 0.066 = 0.14 > 0.10). Not computed anywhere yet: the 126-session leg's p, step-4 PBO on the protective objective. v1.2-check values: ΔMDD +12.7 pp (2×: +12.5), tail 0.68, ΔSR +0.026 (2×: +0.021), p_ni 0.052, years 70%, plateau 0.875; PC-4 14 of 18 objective episodes positive, max share 0.174 (0.493 on §8.6).

Outcomes (L1574): PASS → BUILD-AS-INSURANCE in the recommended book with the label and the premium beside it (share of years lagging S, timing return, bull tax, L5249); INSUFFICIENT → a labelled control in the specification book, re-gated only when new history adds an objective episode, as one counted revision under the full frozen package on the extended sample (L5326-5328), no forward-record route; REJECT → archive. "no convention may be changed to rescue it": no change of convention, window, cap, cash series or row set. Until the formal run, `vt(KR)` runs in the specification book as a descriptive control with its indicative verdict; `vt_weight_recommended_book` = 1.0 while NOT_RUN or INSUFFICIENT (L3559).

Honesty-line threshold for the card page (L5322): −0.39 Sharpe (KOSPI vol target); R-03 −0.20; US vol target −0.73.

### B7. Post-freeze reproductions (TASK-M7-22) and pending values (TASK-M7-30)

Reproductions (golden tier; none is a card run; R-21's stationary-bootstrap z printed beside every research z, never asserted against it): T-EPIS-02, T-TROUGH-01, T-ES-02, T-RLAYER-01, G-PWR-01/02, G-US-F01…F10, G-KR-L01…L13, G-POST-01's M7 rows. Modes: v1.2-check for the §9.3.1 goldens and the "v1.2 checks" columns of §9.3.2; reference mode for the cap-1.5 variant of G-KR-L13 and T-ES-02's z (fixed 250-session circular bootstrap, B 1,000, `qf3_alt_metrics`). v1.2 checks to code once in the M2 v1.2-check module (L5985-5990): PC-1 `MDD(rule) − MDD(S) ≥ +3.0 pp` at 1× and 2× and better than overlay-off; PC-2 tail-exposure ratio ≤ 0.90; PC-3 δ 0.10, one-sided percentile bootstrap p ≤ 0.10, `p_ni = max(p at 10-session blocks, p at max(10, PW(d), PW(d²))-session blocks)`, 2,000 resamples, seed 11, Bonferroni × the configurations recorded in each golden's source row; PC-4 on the §8.6 windows ≥ 3 positive and none above 50%; PC-5 ≥ 60% of years; PC-6 ≥ 50% of 8 neighbours keep ≥ half of the centre's PC-1 improvement and the PC-3 point; PC-7 ≥ 30 de-clustered onsets, ≥ 5 §8.6 windows, ≥ 756 + 126 sessions; raw returns, cash 0; verdict order sufficiency, REJECT, inconclusive, REVISE, PASS.

Pending values (L5996-6011): each is computed at its first run, printed beside the research value, md5-frozen, and becomes a golden only once frozen; never asserted against the research number.

| §9.4 item | Value | When |
|---|---|---|
| 11 | T-POWER-01's years line restated to a point: `T_years = sessions / 252`, SE = `SE_plateau` of the named fixture; `years = T_years × (2.1232 × SE_plateau / 0.05)²` (derived; reproduces G-PWR-01's 241-246 at SE 0.061 / 36.6 y and 319-330 at SE 0.130-0.132 / 10.4 y) | before the freeze |
| 12 | R-06 KR selection factor under `any_overlap` for every defensible row-set reading, maximum binding; printed in the acceptance report before any card runs | before the freeze |
| 14 | excess-return cell of T-EXCESS-01 and I-09 under R-22's cash and R-24's studentized PC-3; T-GATE-02's p_ni; T-ES-02's z under R-21's stationary bootstrap | first formal runs |
| 4 | the Korea card's ES126 z (ES126 +6.4 pp in PX1's horizon file) | first formal run |
| 1 | every §9.3.1 regression golden restated on excess returns | first formal runs |

Storage (proposed): `tests/fixtures/macro/frozen_values.json`, one entry `{id, value, research_value, package_version, frozen_utc}` per value, the file's md5 in `MANIFEST.csv`.

### B8. R-06 US 50 bp registered card (TASK-M7-23; L1575, L4291, L5390)

- Displayed string, exact: `"REJECT (instrument: US shares via KIS, 50 bp, daily)"`. Stored at `vol_target.US.registered_card: {instrument_book: US_shares_KIS, verdict: REJECT, label: "REJECT (instrument: US shares via KIS, 50 bp, daily)", rerun: false}`.
- "never re-run" = no new card record is written; a reference reproduction such as G-US-F01 is not a card run (L5992). `run_card` refuses its id.
- Disclosed flip (T-GATE-02): `cardp_evaluate` on fixture U1 (French Mkt-RF + ^GSPC Sep-2026, 1990-2026, 50 bp, daily) under the frozen package, harness output only: verdict asserted as the class INSUFFICIENT DATA; ES21 +1.65 pp and ES126 +3.8 pp (± 0.2 pp); p_ni printed (0.146 is R4b's percentile `gate_boot` value; R-24's studentized p is a different statistic, never asserted against it); 2× ΔSR −0.125; the recorded label stays the instrument REJECT.
- Monthly and banded 50 bp variants are R-06 ledger trials, never rescues (§10 item 23). Any `vt > 1.0` fails schema and rules-store validation (T-CAP-01).

### B9. R-03 card and revisions (TASK-M7-24); R-04 step 3 (TASK-M7-25)

R-03 run (L1526, L4823): CARD-O; on = the sleeve's budget × `vs` from `sleeve_vol_scale(market, family, decision_utc, revision)` (M4) on the paper unit-gross long/short series; overlay-off = the same sleeve unscaled on the same costed engine; 50 bp per side on the overlay's own turnover, both legs; `vs` never on the benchmark-relative active series (L1517); before the book's first ARMED decision `vs = 1.0` flagged `WARMUP`, card books start after the warm-up. Sequence: r1 header committed in step 4; r2 and r3 header md5s committed before their runs; each run appends its ledger row; step 3 recomputed on the enlarged ledger each time. Years line: print the differing years with the count of higher-Sharpe years gross and net (French fixture: 20 differing of 37, 15 higher gross / 11 net; 70% of calendar years positive, step 8). Demotion note printed: R-25; "review if the 2016+ ΔSR is below 0 in ≥ 2 regions".

Harness verification on the French Mom fixture, not this card (L4823): T-R03-01, G-DSR-01, G-DSR-02. Arithmetic (checked): `deflated = Φ((ΔSR − SE_null·e(N)) / SE_obs)` with ΔSR 0.2729, SE_obs 0.0716, SE_null 0.0935 → 0.98 at `e(N_equiv 6.3) = E_sim 1.33`, 0.947 at `e(12.6) = 1.688` (BLdP closed form); break-even N ≈ 11.9.

Indicative: r1 PASS flagged "step 3 borderline"; z 3.84 / 3.29 / 2.99 at 10 / 63 / 240-session blocks ≥ 2.50; SE ladder 0.072 → 0.091, z 3.81 → 3.0; PBO 0.000 (family) / 0.009 (grid); plateau 100%; timing FR 0.03. r2, r3: NOT_RUN. On a formal PASS the factor enters the recommended book only through `verdict_filter` (M8), and `MOM_PAPER_LS_SERIES` is bound to that book in the same run (L5675 (g)).

R-04 (L1542, L5386, L5645): add-on step 3 computed on the R-03 family ledger: deflated add-on 0.77 ± 0.02 at N_equiv 6.3 (inputs ΔSR 0.0724, SE_obs 0.0349, SE_null 0.0349; z 2.06-2.08 < 2.50) → label `"step 3 FAIL"`; specification book only, floor 0.5; `families.momentum.dm_gate: {…, books: [specification], label: "step 3 FAIL", a_provisional_route: closed, pooled_revision: none}` (L4321-4322). Card validation rejects any A-provisional or pooled route for a card already run (refused shape `pooled_or_a_provisional_tier_after_results: 34`, L4674; `gate.tiers.A_provisional: closed`, L4610). The would-be pooled trial is R-03 revision 3. Card object today: `{"card_id":"MACRO-R04-US-DM","class":"CARD-O","verdict":"NOT_RUN","disposition":"SPECIFICATION_ONLY","displayed_as":"descriptive","label":"step 3 FAIL (indicative)","results_md5":null}` (L3782-3783); F-13.

### B10. R-14 TS-trend sleeve and card (TASK-M7-26; L1696-1705, L4326-4327)

```python
def ts_trend_weights(month_end_closes: np.ndarray, *, vol_window_months: int = 12, target_ann: float = 0.15,
                     cap: float = 1.0) -> np.ndarray            # core/quant/signals.py; proposed name; one column per index
# signal_m = sign of the 12-1 month return (month-end m-12 to month-end m-1); monthly rebalance
# sigma_12m = mean-adjusted SD of the last 12 monthly returns x sqrt(12)
# per-asset weight = signal_m x min(1.0, 0.15 / sigma_12m); cap > 1.0 raises (reference mode only)
# sleeve weight = base_weight(m, ts_trend) per R-15 (IV_m x 1/K_m) x per-asset weight
```

- Exempt from all overlay multipliers and from the market vol target; subject to risk-layer caps and the hard stop; costs per venue (L1701). Runtime assertions (T-BASIS-01, M7 clause): vt is not applied to TS trend and no overlay multiplier applies to `ts_trend`; rules-store predicate: any multiplier on `ts_trend` is refused (L4696).
- Admissibility: `base_weights.family.not_run_admissible_except: [ts_trend]` (L4284): ts_trend enters the recommended book only on its own PASS (L1718).
- Header refused unless it declares `instrument_book: multi_line` with `instrument_lines[]` (never a stock book) and the claim CARD-O, diversification (L1702; T-R14-01).
- Card: CARD-O, benchmark = the equal-weight long-only basket of the same indices. Printed: failure-mode text containing `"not fast-crash protection"`; goldens restated at cap 1 with sub-period correlations: SR 0.449; correlation with the S&P 0.03 (0.027) over 2001-26, 0.34-0.36 over 2013-26 (L1703, L5397). Displayed descriptively until its own card passes; KOSPI trend state is context only (L1705). Indicative verdict: NOT_RUN ("diversification claim; not computed").
- Related record: QUANTGEN card E1 (trend switch on US ETF sleeves) REJECTED on an outperformance test, OOS Sharpe 0.84 vs 0.95, p 0.75 (L1705); legacy `S_E1_trend_us`, `S_E1_trend_krx` stay untouched.

### B11. R-31 step-down card and binding share (TASK-M7-27; L3262-3359)

State machine: M5's `drawdown_ladder(nav_path, decision_utc) -> LadderState{hwm_hard, ref_step, step_mult, dwell_left, block_new_entries, halted, rearm_not_before, post_rearm_left, binding_share}` (names binding, L3271); pseudo-code L3279-3302 (DWELL = 21 sessions including the first; levels in % of whole-book NAV; multipliers are totals, never cumulative; composition `composed = vt * min(overlay_1, …, overlay_k, step_mult if steps_act_in_book else 1.0, post_rearm_cap)`; at re-arm both references reset to the NAV at re-arm).

Binding share (L3305-3307):
- `binding_share = n_bind / n_sessions`, sessions with `step_mult < 1`, on the declared book over its declared history; printed on every card.
- Placement share: per market book, on the recommended book's current composition without the steps (the invariants plus the PASS factors, each market on its declared instrument book; whole-book NAV), over the full declared history, at the R-31 header commit. Frozen with that header. Recomputed only through a new counted R-31 revision when the recommended book's composition changes (a card promotion or demotion, a D1 or D2 ruling), logged as governance event `kind: "binding_share_recompute"`. Never on a trailing window.
- `≤ 0.10` → the steps act as part of the R-07 invariant in the recommended book, disposition `INVARIANT_STEP`. `> 0.10` → specification book only until this card PASSes; the recommended-book builder refuses the step multiplier (I-03, L3339). Compare `"n_bind / n_sessions > 0.10"` on the exact computed share, never on T-STEP-02's ≈ 10% ± 3 pp fixture (L3348).

Card: CARD-P, judged incrementally on the declared book with the hard stop and every other factor, minus the steps; S = that book × the steps' mean multiplier; checks = the frozen package; claim verbatim; PC-6 axes `threshold_rule: {threshold_mult: [0.75, 1, 1.25], lookback_or_dwell_mult: [0.5, 1, 2]}` (L4517). Printed: `model_card.macro.printed = {binding_share, n_halts, persistence_check}` (L3334); Kaminski-Lo reference values: after an activation the next 21 sessions returned −0.57% vs +0.98% unconditional on KOSPI, +0.57% vs +0.78% in the US (L3309).

Reference run (§9.4 item 8, L6005): the same book with and without steps, separate `hwm_hard` and `ref_step` references; ΔSR printed and md5-frozen so T-STEP-03 has a reference; EX1 L5's +0.005 / +0.006 used one shared reference and is informative only.

Fail-closed (L3336-3339): whole-book NAV unavailable → step state held, alert raised, hard stop stays armed; a ladder path composed by product raises (R-02); binding share > 10% and no PASS → builder refuses the step multiplier.

Indicative (L5396): NOT_RUN; SPECIFICATION BOOK while the binding share is > 10% (KOSPI ≈ 19%; EX1 L5: binding 19% / 10%, ΔMDD +4.8 / +1.5 pp, 3 / 0 HALTs). A US card is registered only once D5 creates a US sleeve (L4824).

Config read (verbatim, L3312-3329 = L4448-4461): `cards.R-31_step_down.{steps, dwell_sessions: 21, step_reference: running_peak_since_last_reset, hard_stop_reference_resets_at_dwell_end: false, composition: min, denominator: whole_book_nav, binding_share_threshold: 0.10, binding_share: {book: recommended_without_steps, span: declared_history, computed_at: [header_commit, composition_change], window: full_never_trailing, compare: "n_bind / n_sessions > 0.10", disposition_if_le: INVARIANT_STEP}, judged: {incremental_on: declared_book_without_steps, comparator: S}, claim, hard_stop_level: {ref: risk_layer.drawdown.hard_stop.level}, status: SPECIFICATION_BOOK}`.

### B12. R-30 card-level clauses (TASK-M7-28; L3195-3207, L5047-5062)

- Stage 3 and the MCS take their CIs from the frozen R-24 bootstrap (T-EST-01 clause); eligible survivors: ΔSR vs the SMA20 book non-inferior at δ 0.10, ΔMDD vs SMA20 ≥ 0, PC-2 ≤ 0.90; lowest vol-of-vol (SD of the book's rolling 63-session annualised realised vol) wins; overlapping bootstrap CIs are ties, to the simplest surviving model in the order `[sma20, ewma094, ewma097, garch_t, gjr_t, log_har_range, comb]`.
- Switching rule: a challenger replaces SMA20 on a card only through a counted card revision (an R-23 ledger trial) that passes Stages 1-3 and the full v2 CARD-P. Never on the 35 bp stock book; never on the registered R-06 KR card. `commit_header` and `write_card` refuse an `estimator` that differs from the previous revision's without a new revision and ledger row (T-EST-05), and refuse COMB or log-HAR on `KRX_stock_book` (`books_refused: [KRX_stock_book]`, L4297).
- Estimator-calibration cap input to `cardp_evaluate`: the incumbent's B5 status (5% FHS VaR exceedance within ±2 binomial SE over ≥ 200 origins and PIT χ² p ≥ 0.01) or a challenger's Stage-1 result; a failure caps the card at REVISE, reason `estimator_calibration`, permitted fix `lengthen_holding` as a counted revision (L2171, L5061). T-B5-01 clause: a vol-target card whose estimator is FAIL cannot be PASS.
- The fallback never blends (L3206). `model_card.macro.forecast_eval = {qlike_mcs_p[h], mse_mcs_p[h], christoffersen_p, es_z2, fan_pit_p, vol_of_vol, dMDD_vs_sma20, dSR_vs_sma20}` (L3232) written by `write_card` when a revision changes the estimator.

### B13. Stack CARD-P (TASK-M7-29; L1506 (6), L5275-5291)

- De-risk factor = a market-level (`exposure_basis = total`) factor carried by a card that can take a value < 1.0 in the recommended book: vt (R-06 KR), R-28, R-29 and the R-31 steps once their card PASSes. Not de-risk factors: look-through caps, the hard stop, the post-re-arm cap, R-31 steps acting as `INVARIANT_STEP`, family-level vs (R-03); the stack card's composed book includes them and prints their binding shares.
- When: the book builder calls `maybe_generate_stack_card` before a second (or further) de-risk factor joins a market's recommended book. Several factors passing in one batch join in header-commit order, fixed before the run.
- Judged, both under the frozen package: (a) the joining factor incrementally on the current recommended book (its own card where that is its declared book); (b) the composed book `composed = vt × min(1.0, overlay₁ … overlayₖ, ladder, post_rearm_cap)` with the hard stop and caps applied, as one CARD-P against the invariants-only book, `S = that book × the stack's mean multiplier`.
- Consequence: the joining factor acts in the recommended book only if both (a) and (b) read PASS; otherwise it stays in the specification book labelled with the stack verdict. A product-composed stack is refused (rules store shape `composition_not_min: 31`).
- Printed: the share of days at ≤ 0.25× total exposure; rebound capture in the cost episodes.
- The stack card is a CARD-P registered after the freeze: its own panels under rule 9(a) at its header commit (B1 step 5); `benchmarks` may include `current_recommended_book` (schema enum L3983); span end = the last month-end official close before its commit.
- Today: NOT_RUN, generator dormant (no de-risk factor is PASS; `overlay.stack_card: {when_de_risk_factors_ge: 2, class: CARD-P, spec: "§8.7"}`, L4280).
- Reference numbers (EX1, KOSPI at 3 bp; buy-and-hold +47.3% in the 2020 rebound): VT20 0.8% of days ≤ 0.25×, +23.9%; VT20 × SMA10m 8.2%, +15.5%; VT20 × SMA10m × ladder (product) 31.0%, +7.6%; VT20 × min(SMA10m, ladder) 11.2%, +12.6% (L5284-5289).

### B14. `ui/strategy_lab_page.py` (E) — scorecard adapter

- Add `MACRO_CARDS_DIR` and `load_macro_cards() -> list[dict]` mapping each `model_card.macro` to the keys the existing table indexes without `.get` (lines 100-133): `card_id`, `kind` ← `class`, `decision` ← `verdict`, `decision_reason` ← `verdict_reason` plus `label`, `hypothesis`, `lines` (built from `tests` and `printed`), `seed`, `results_md5`, `citations: []`. Headers without a card appear with `decision = "NOT_RUN"` and the indicative label.
- `_TOKEN` gains `"NOT_RUN": "muted"`. A non-PASS card is never rendered with the PASS token or the word "recommendation" (DNB 22); show `displayed_as`, `disposition`, `verdict_at_f1` / `verdict_at_f_neff`, `header_md5[:8]`, the package version.
- Every change is linted by `tests/flet_api_guard.py` (Flet 0.85.2). The Macro page card panel, the weekly brief and the monthly card page (L5359-5365) are M6 / M8.

### B15. What is recorded when a formal run cannot be made

| Card | Committable today? | Recorded state | Why |
|---|---|---|---|
| `MACRO-R06-KR-ETF` | no | header draft with typed placeholders; `verdict: NOT_RUN`; `vt(KR)` in the specification book as a descriptive control labelled "NOT_RUN; indicative PASS on v1.2 checks, fragile; expected INSUFFICIENT DATA under v2 (through f; R2-C1)" (L5427); `vt_weight_recommended_book = 1.0`; no `verdicts.jsonl` row; `results_md5: null` | no KRX official-close fixture, no `BOK_CALL_RATE` code, `sleeves.KR.notional_nav` null, listing date not signed, package not frozen |
| `MACRO-R03-US-MOM` r1-r3 | no | `vol_scale_card` object of L3779-3780: `verdict NOT_RUN`, `disposition DESCRIPTIVE`, `displayed_as descriptive`, `label "indicative PASS; step 3 borderline"`, `results_md5 null`; `vol_scale_recommended_book = 1.0` | sleeve and notional undefined (F-07); no freeze |
| R-04 | not a step-4 header | `verdict NOT_RUN`, `SPECIFICATION_ONLY`, label `"step 3 FAIL (indicative)"`; refused by the recommended-book builder | L3782-3783, I-03 |
| `MACRO-R14-MULTI-TREND` | no | NOT_RUN; sleeve displayed descriptively; never in the recommended book before its own PASS | index list, lines and notionals unspecified (F-10) |
| `MACRO-R31-KR-ETF` | no | NOT_RUN; `status: SPECIFICATION_BOOK`; step multiplier only in the specification book; the recommended book carries the hard stop only (T-STEP-04) | binding share needs the KR book NAV history |
| `MACRO-R28-US-TREND` | no | NOT_RUN / `FORWARD_SIM`; FORWARD-SIM book cannot start before a committed header (M8, L5310 (a)) | `sleeves.US.notional_nav` null (F-06) |
| `MACRO-R06-US-FUT` | no | NOT_RUN / `FORWARD_SIM`; "The settling run cannot run without the frozen 1926 fixture. Its absence keeps the card FORWARD-SIM; it never falls back to the 1990 file." (L3126) | F-05, F-06 |
| R-06 US 50 bp | never run | the instrument-labelled REJECT string | L1575 |
| Stack card | n/a | NOT_RUN (no stack acts yet) | L5398 |

Recommended book in every one of these states: invariants only (R-01, R-19, R-20 data rules; R-02 bounds and `min()`; R-07 caps and the −15% hard stop with re-arm; R-09 hedge state; R-26 realism), L5417-5425. No exposure reduction and no exposure increase follows from an unrun card.

---

## C. Schemas and config this area writes or reads

### C1. R-06 KR header (L4900-4965, verbatim; validates against `model_card_header.macro`, T-SCHEMA-01)

```yaml
card_id: MACRO-R06-KR-ETF
family_id: R-06                               # assigned by rule (QC_modules.csv; R-23)
rule_id: R-06-KR-VT20
revision: 2                                   # v1.2's 2016-26 card was revision 1; new span and conventions
class: CARD-P
claim: &label "Crisis-clustering insurance: reduces drawdown in volatility-clustering crises (1997–98, 2008, 2026); no help against gap shocks from calm states (2018-10, 2020-02, 2024-08); Sharpe non-inferiority is marginal — it pays a premium in calm decades (2016–25 alone: tail 0.95, ΔSR −0.079) and is short the post-crash rebound premium; not expected to outperform; cap 1.0 permanent."
label: *label                                 # byte-identical to the R-06 label (UTF-8)
claim_type: protection
build_status_on_pass: BUILD_AS_INSURANCE
tier: A                                       # continuous; objective episodes (18 on 1997-2026)
created_utc: "<commit time>"
header_md5: "<md5 of the header fields, committed before the run>"
gate_package_version: "2.0.0"
gate_package_md5: "<gate.package.definitions_md5 at the freeze>"
hypothesis: "VT20 lowers tail losses vs a same-average-exposure static book without a Sharpe loss beyond 0.10"
mechanism: "variance reduction (variance ratio 0.59); implicitly short the rebound premium (timing return -1.8%/yr)"
rule: "vt = min(1.0, 0.20 / sigma_SMA20(t)); decided at the KRX close of t (available_at <= close_print_bound_utc(KR, t)); earns from t+1"
parameters: {estimator: sma, window: 20, target_ann: 0.20, cap: 1.0, floor: none}
searched_parameters: []                       # PC-6 neighbours come from the frozen pc6_axes, never from the header (R-21)
estimator: sma20                              # a COMB revision would be a new counted revision (R-30)
instrument_book: KRX_ETF_line                 # KODEX 200; tick floor applies
notional_nav: "<sleeves.KR.notional_nav at commit, KRW>"   # owner-signed (R-26); a futures line only if one mini contract <= 5% (about KRW 1bn+)
rebalance: daily
no_trade_band: 0.0                            # bands only on stock and US-share books
fill_model: KRX_close_auction                 # R-27
costs:
  per_side: read_from_gate
  floor: tick_floor
  stress: 2.0
  stress_line: printed
  schedule:                                   # no ETF existed before Oct-2002; a declared cost may only rise (P10)
    - {to: "<the day before the KODEX 200 listing, from the KRX listing record>", cost_class: futures}
    - {from: "<the KODEX 200 listing date>", cost_class: krx_etf}
  printed_lines: [krx_etf_3bp_throughout]     # the DLA-K8 / G-KR-L01 convention, printed for comparison
data: {source: KRX_official_closes, value_status: official_close, history_file: "<the frozen KRX official-close fixture>",
       reconciliation: "R-01: index 1 bp, stocks exact", golden_tolerance: "Level-2, only for I-16's raw-flag data check vs G-KR-L01; the formal run's differences are printed, never gated",
       saturday_sessions_before: "1998-12-12"}
history_first_close: "1997-04-01"             # gate.evaluation.history_start KR (R-22)
data_span: {start: first_close_plus_20_session_warmup, end: "2026-10-02"}   # gate.evaluation.data_cutoff.KR (R-22): fixed now, never "latest"
cash_convention: {returns: excess, cash_series: BOK_CALL_RATE, day_count: act_365}
episode_rule_version: "1"                     # alternating >= 20% on KOSPI's own closes; Sep-2026 is not an episode
gating_lines:
  full_span: v2_PASS
  etf_era: {from: "<the first day of the first full month after the KODEX 200 listing>", to: "2025-12-31", require: v2_PASS}
start_band: {shape: R-06_KR, from: "1997-05", to: "1999-12", step: month, starts: 32, require: {no_reject: true, pass_share_min: "2/3"}}
midpoint_halves: {split: calendar_midpoint, split_date: "<the calendar midpoint of the fixed span>", require: no_reject}
regime_lines: from_R20_tags
printed_lines: [etf_era_to_present, pre_design_2002-10_to_2015-12, "1997_to_2002_alone", "2016_to_2025_alone",
                rolling_decades, pc4_under_section_8_6, ewma094_line, timing_return, years_lagging_S,
                h1_2026_bull_tax, median_reentry_lag, per_regime_table, with_risk_layer]
primary_oos_line: etf_era
comparator: S_same_average_exposure
benchmarks: [buy_and_hold, overlay_off, static_same_avg_exposure, ewma_derisk]
checks: gate_package_2.0.0
ledger_hash_at_registration: "<md5 of the R-06 family ledger at commit>"
N_raw_at_registration: "<R-06 ledger row count at commit>"
# selection_factor: never declared here; step3() computes it at the run and the card prints f = 1 and f = N_eff (R-23)
timing:
  decision: close_t_earn_t_plus_1
  inputs: {KOSPI: {series: KOSPI_OFFICIAL_CLOSE, value_status: official_close, available_at: "<= close_print_bound_utc(KR, t)"}}
outcomes: {PASS: BUILD-AS-INSURANCE, INSUFFICIENT_DATA: specification_book_control_regated_on_new_objective_episode,
           REJECT: archive}               # the forward record is a falsification alarm only (R-25)
owner_decisions: {risk_layer.korea_caps.template: msci_25_50}   # D1; caps are excluded from the card books and printed (R-22 rule 6)
seed: 11
```

### C2. Header schema (M0 owns; `$id: quantgen/model_card_header.macro.v2.0`, L3927-3992)

Required (L3929-3933): `card_id, family_id, rule_id, revision, class, claim, claim_type, label, build_status_on_pass, tier, created_utc, header_md5, gate_package_version, gate_package_md5, hypothesis, mechanism, rule, parameters, searched_parameters, estimator, instrument_book, rebalance, no_trade_band, notional_nav, fill_model, costs, data, history_first_close, data_span, cash_convention, episode_rule_version, start_band, midpoint_halves, regime_lines, primary_oos_line, printed_lines, comparator, benchmarks, checks, ledger_hash_at_registration, N_raw_at_registration, timing, outcomes, seed`. Optional: `instrument_lines`, `nav_fx`, `roll_calendar`, `gating_lines`, `claim_lines`, `pooling_rule`, `live_feeds`, `owner_decisions`.

Enums: `class ∈ {CARD-O, CARD-P}`; `claim_type ∈ {outperformance, protection, diversification}`; `build_status_on_pass ∈ {BUILD_NOW, BUILD_AS_INSURANCE}`; `tier ∈ {A, B, C}`; `instrument_book ∈ {KRX_ETF_line, KRX_stock_book, KOSPI200_futures, mini_KOSPI200_futures, CME_micro_ES, US_shares_KIS, KRX_listed_SP500_ETF, crypto_venue, FX_KRX_USD_futures, FX_broker_spot, multi_line}`; `rebalance ∈ {daily, weekly, monthly}`; `no_trade_band ∈ {0.0, 0.10}` (0.10 only on `KRX_stock_book` and `US_shares_KIS`); `notional_nav` number > 0, KRW; `nav_fx.role ∈ {acting_exposure, forward_sim}`; `data.value_status ∈ {official_close, vendor_close}`; `start_band.shape ∈ {default, R-06_KR, decade_spaced}`, `step ∈ {month, decade}`, `require.pass_share_min ∈ {"2/3", "4/5"}`; `midpoint_halves.split = calendar_midpoint`, `require = no_reject`; `comparator ∈ {S_same_average_exposure, overlay_off}`; `benchmarks` items `∈ {buy_and_hold, overlay_off, static_same_avg_exposure, ewma_derisk, current_recommended_book}`; `timing.decision = close_t_earn_t_plus_1`; `regime_lines = from_R20_tags`.

### C3. Card schema result block (`$id: quantgen/model_card.macro.v2.0`, L3996-4084; closed)

Required result fields (L3998-4002): `schema` (`quantgen.model_card.macro`), `schema_version` (`2.0`), `read_only` (true), `generated_at_utc`, `knowledge_utc`, `git_hash`, `config_hash`, `data_snapshot_id`, `verdict`, `verdict_reason`, `caps_applied`, `verdict_at_f1`, `verdict_at_f_neff`, `disposition`, `first_failed_check`, `permitted_fix`, `ledger_hash_at_run`, `N_raw`, `N_clusters`, `N_equiv`, `N_hat_linear`, `N_eff`, `E_max_sim`, `V_null`, `V_trials`, `selection_factor {value ≥ 1, rule: computed_by_step3, alt_value ≥ 1}`, `power {se_hac, se_blk250, se_plateau, mde80, power_at_0p05, power_at_0p10[, se_curve, pc3_power_at_0, years_to_detect_0p05, underpowered]}`, `timing_profile {lags[{L, dSR, dMDD, dES21, timing_class[, lag_audit]}], strict, LP, LF, FR, label ∈ {robust, timing_fragile}, live_feeds}`, `episodes[{peak, trough, depth, open[, window, benefit_vs_S, share, regime_tags, post_trough_63]}]`, `start_band_results`, `midpoint_halves_results`, `regime_line_results[{line, span, verdict, gated[, numbers]}]`, `gjr_null_pct`, `costs_per_side {table_bp, floor_bp, applied_bp[, stress_line, roll_cost_line]}`, `cost_stress` (2.0), `tests`, `printed`, `lag_audit_violations` (const 0), `results_md5`.

Optional result fields this area fills: `cost_episodes`, `pc4_section_8_6`, `claim_line_results {stacked_dMDD, band, pass}`, `pooling {rule, n_onsets_own, n_onsets_pooled}`, `snooping`, `settling_run {span, verdict, pc1_prime_1x, pc1_prime_2x, starts, n_pass, n_starts, n_reject, midpoint_halves}`, `contracts_path`, `forecast_eval`, `forward_record` (M8 only).

`tests` keys (closed set, L4066-4076): `step1 … step9`; `step3 = {deflated_dSR, at_N_raw, at_N_hat_linear, borderline, break_even_N, z_check, by_q, dsr_vs0, psr_vs_S, selection_factor, pass}`; `step4 = {pbo, winner_loses_share, pbo_null, slope, n_configs}`; `PC1p = {legs: [{h, dES, z, p, p_adj, pass}], two_x: […]}`; `PC2 = {ratio_daily, ratio_horizon, ci90, horizon_used, pass}`; `PC3 = {dSR, p10, pPW, block_PW, p_ni, p_adj, point_2x, pass, p_lw, p_hac, block, n_blocks}`; `PC4 = {positive, n, max_share}`; `PC5`, `PC6`, `PC7`.

`printed` keys (L4077-4081): `dMDD, dCDaR95, dES99, bands, placebo_panel, tuw, reentry_lag, post_trough, rolling_5y, with_risk_layer, lo_sr_20, lo_sr_all, by_q, hl_haircut, exec_variants, overnight_intraday, turnover_by_regime, stress_cost, roll_cost, ban_basis, fill_tracking_error, binding_share, binding_shares, n_halts, persistence_check`.

### C4. Rules-store keys read (M0 writes; verbatim values)

- `gate.package: {version: "2.0.0", definitions_md5: written_at_freeze, acceptance_report_md5: written_at_freeze, frozen_utc: written_at_freeze, manifest: [gate_blocks_canonical_json, harness_source_files, acceptance_fixture_md5s, seeds], anchor: repository_commit_before_any_card_run, rehash_at_every_card_run: true}`; `gate.frozen_before_first_card_run: true`; `gate.card_classes: [CARD-O, CARD-P]` (L4499-4503).
- `gate.parameter_budget_searched: 8`; `gate.stress_report_window: ["2022-01-01", "2026-10-02"]` (reported, not a holdout); `gate.locked_holdout_start: "2027-01-01"`; `gate.costs: read_from_gate` (KRX ETF 3 bp, KRX stock 35 bp, US via KIS 50 bp, crypto 10, futures 5, FX 10; ×2 stress) (L4613-4616).
- `gate.card_header_required: [instrument_book, notional_nav, rebalance, no_trade_band, fill_model, cash_convention, episode_rule_version, family_id, ledger_hash_at_registration, history_first_close, data_span]`; `gate.card_result_required: [timing_profile, ledger_hash_at_run, selection_factor, results_md5]` (L4617-4619).
- `gate.evaluation.{history_start: {KR: "1997-04-01", default: first_close_of_frozen_fixture}, span_end: {drafted_cards: data_cutoff, later_cards: last_official_close_before_header_commit}, data_cutoff: {KR: "2026-10-02", US: "2026-10-01"}, start_band_shapes: {default: {months: 33, step: month, pass_share_min: "2/3"}, R-06_KR: {from: "1997-05", to: "1999-12", step: month, starts: 32, pass_share_min: "2/3"}, decade_spaced: {min_span_years: 80, starts: declared_start_then_january_of_each_decade, last_start_min_years_before_end: 10, pass_share_min: "4/5"}}, stability_floor: {no_reject_at_any_band_start: true, pass_share_min: from_band_shape, compare: integer_counts, no_reject_in_midpoint_halves: true, applies_to_every_shape: true}, midpoint_halves: {split: calendar_midpoint_of_fixed_span, split_date_in_header: true}, risk_layer_in_card_books: {hard_stop: excluded_printed, caps: excluded_printed, except: card_claim_concerns_them}, cash: {KR: BOK_CALL_RATE, US: US_RF, other: registry_before_first_run}}` (L4545-4564).
- `gate.card_p_v2.*`, `gate.step3.*`, `gate.stats.*`, `gate.timing.*` (L4504-4607): read by the gate harness; this area passes none of them through `V.GATE`.
- `vol_target.KR: {estimator: sma, window: 20, target_ann: 0.20, cap: 1.0, cap_permanent: true, exposure_basis: total, instrument_book: KRX_ETF_line, notional_nav: {ref: sleeves.KR.notional_nav}, rebalance: daily, no_trade_band: 0.0, fill_model: KRX_close_auction, card: {card_id: MACRO-R06-KR-ETF, build_status_on_pass: BUILD_AS_INSURANCE, conditions: see_R-06_card_korea, forward_record: falsification_only}}`; `vol_target.US.registered_card` (B8); `vol_target.US.futures_card: cards.R-29_US_FUT` (L4287-4292).
- `families.momentum.own_vol_scale`, `families.momentum.dm_gate`, `families.ts_trend: {signal: sign_12_1, rebalance: monthly, vol_window_months: 12, target_ann: 0.15, cap: 1.0, overlay_exempt: true, card: {class: CARD-O, claim: diversification, instrument_book: multi_line}}` (L4317-4327).
- `cards.R-28_trend_axis`, `cards.R-29_US_FUT`, `cards.R-31_step_down` (L4412-4461); `sleeves: {US: {line: none, notional_nav: null}, KR: {notional_nav: null}}` (L4462-4464); `overlay.stack_card`, `overlay.recommended_dispositions: [RECOMMENDATION, BUILD_AS_INSURANCE, INVARIANT_STEP]` (L4279-4280).
- `owner_decisions.D1 … D6` (L4138-4152); `{ref: <key>}` objects have exactly one key and are resolved at load.
- `reproducibility: {seed_study: 11, seed_research_bootstrap: 20261002, record: [git_hash, config_hash, data_snapshot_id, knowledge_utc, seed, results_md5, gate_package_version, gate_package_md5, ledger_hash_at_registration, ledger_hash_at_run], determinism: {canonical_json: sorted_keys_repr_floats_no_whitespace, volatile_fields: [generated_at_utc, git_hash], rng: numpy_pcg64_seedsequence_spawned_children, blas_threads: 1, relative_tol: 1.0e-12}}` (L4680-4684).
- `do_not_build.refused_shapes` (L4662-4679), enforced by M0 validation at `commit_header`.

### C5. Files this area writes

`headers/*.header.json`, `headers/*.draft.json`, `cards/*.json`, `cards/verdicts.jsonl`, `archive/**`, governance events (`header_commit`, `binding_share_recompute`), family-ledger rows (through the harness only, `phase: card`), `tests/fixtures/macro/frozen_values.json`. Tests write only to temporary copies of the rules store, the ledgers and the artifact directory (T-HERM-02, L5608).

---

## D. Tests

Registration: N `tests/macro_cards_acceptance.py` exposing `tests() -> list[tuple[str, Callable]]`, one import line and one list line in `tests/run_all.py` (existing convention). Tiers (L5496): `fast` (SYNTH rows below), `golden` (REFDATA reproductions), `freeze` (I-08, the formal runs of I-07 and I-16, GJR-null paths, PBO: only in the M7 freeze job and at formal card runs; `run_all.py` verifies their md5s and never recomputes). Verdicts near a threshold are asserted as a class (L5499). Level-1 tolerances L5734-5735; Level-2 L5736.

Feasibility: SYNTH = hermetic with synthetic or inline fixtures; REFDATA = needs frozen reference data not on this machine; OWNER = needs owner input, credentials or an external anchor.

| ID (runs_from M7 after the freeze unless stated) | Assertion and thresholds | Fixture | Class |
|---|---|---|---|
| T-CARD-01 (L5663) | header md5 ≠ committed header → refused; class or claim change → new header record and family ledger incremented; no ledger hash or missing R-26 header fields → refused; `displayed_as ∈ {recommendation, insurance}` iff verdict = PASS | synthetic header, temp ledger, temp rules store with a dummy frozen `gate.package` | SYNTH |
| T-CARD-02 (L5664; TASK-M7-16 owns) | runner re-hashes the manifest at every card run and refuses on a mismatch; an edit to any `gate.*` block, harness source file, acceptance fixture or seed after the freeze is detected | temp manifest; flip one byte per category | SYNTH |
| I-07 (L5697) clause 1 | under the frozen package the study writes one card per rule with all nine gate lines, the CARD-P v2 checks, the power line, the timing profile and the ledger hash | structure: synthetic series + dummy package; values: frozen fixtures | SYNTH (structure) / REFDATA (fixtures) |
| I-07 clause 2 | v1.2-check mode on the Yahoo fixture reproduces G-KR-L01 … L08 within Level-1 | ^KS11 1997-04 → 2026-10; `QX_DLA_korea_grid.csv`. Local: none (`yf_069500.KS.csv` starts 2007 and is an ETF) | REFDATA |
| T-BOOK-02 (L2872) | every card prints execution variants A / B / C and the overnight / intraday attribution; KOSPI VT20, 3 bp, 1997-2026: SR 0.448 / 0.450 / 0.465 (± 0.01) | structure: synthetic OHLC; numbers: KOSPI closes and opens 1997-2026 | SYNTH / REFDATA |
| T-BOOK-01 printed-line clause (L5641, L5550) | every card prints A/B/C and the attribution | synthetic | SYNTH |
| T-COST-01 clause "a 2× run exists for every card" (L5592) | card has `cost_stress: 2.0`, `tests.PC1p.two_x`, `tests.PC3.point_2x` or step 6 | synthetic | SYNTH |
| T-REPRO-01b (L5667) | same seed, rules-store hash, data snapshot, package version → identical bootstrap and GJR-null outputs, relative difference ≤ 1e-12, single-threaded BLAS, PCG64 via SeedSequence with spawned children; re-deriving `data_snapshot_id` from the archived rows reproduces the snapshot and the statistics bit for bit (TASK-M7-20) | synthetic series run twice; temp archive | SYNTH |
| I-16 (L5706) verdict function | PASS iff (i)-(iv); one injected sub-verdict per failing branch: full span not PASS; ETF era not PASS; one REJECT start with 31 PASS; 21 PASS and no REJECT; a REJECT in h1; a REJECT in h2; both halves INSUFFICIENT with no REJECT keeps PASS; both verdicts (f = 1, f = N_eff) present | injected sub-verdicts | SYNTH |
| I-16 prints | card prints the insurance label, the timing return, the per-regime table and its differences from G-KR-L01 (informative) | synthetic (structure) | SYNTH |
| I-16 data check and formal verdict | raw-flag run on the KRX official-close fixture reproduces G-KR-L01 within Level-2; the formal verdict, header md5 and results md5 are written | KRX official KOSPI closes from 1997-01-03 incl. Saturday sessions (KRX marketplace); ECOS `BOK_CALL_RATE`; KODEX 200 listing date; `sleeves.KR.notional_nav`; an external anchor | REFDATA + OWNER |
| I-09 (L5699) | 18 alternating ≥ 20% KOSPI episodes on 1997-2026 (12 with troughs before 2008), 4 on 2016-26; 16 S&P episodes at 15% on 1990-2026; no Sep-2026 episode; PC-4 max share 0.174 ± 0.01 (0.493 under §8.6 printed); p_ni 0.078 ± 0.01 on PX2's cash fixture in v1.2-check mode; every card prints the trough → +63-session window | ^KS11, ^GSPC 1990-2026, FRED `IRSTCI01KRM156N` (PX2). Local: none (`yf_SPY.csv` starts 1995, is not ^GSPC) | REFDATA |
| G-POST-01 M7 rows (L5576, L5828-5829) | v1.2-check: R-06 KR 3 bp p_ni 0.25 (0.246) / 0.21 (0.208); R-06 KR 35 bp ΔSR −0.029 | ^KS11 2016-01-04 → 2026-10-02 post-patch. Local cross-check only (no series): `r2_idx_r4b_crosscheck.csv`, `r2_idx_golden_values.csv` (rebuilt KOSPI to 2026-09-29) | REFDATA |
| G-KR-L01 … L08 (L5846-5853) | values and v1.2-check verdicts as listed in the task (L01: +12.7 (+12.5) pp · 0.68 · +0.026 (+0.021) · 0.052 / 0.029 (PW block 183) · 4/11 (0.493) · 0.70 · 0.875 → PASS (fragile); L02 +12.6 (+12.3), p_ni 0.055 → PASS; L03 p_ni 0.141 → INSUFFICIENT; L04 +3.8 → PASS (thin); L05 +11.0, p_ni 0.038 → PASS; L06 INSUFFICIENT; L07 REJECT (PC-2, PC-4); L08 INSUFFICIENT) | DL-A grid + ^KS11 | REFDATA |
| G-KR-L09 … L13 (L5854-5858) | L09 14/18 (max 0.174) vs §8.6 + Sep-2026 5/12 (0.490); L10 71-72 of 72 monthly starts 1997-02 → 2003-01 PASS (1998-10 start asserted as PASS or INSUFFICIENT); L11 episode benefits (GFC +9.1 … Jul-2026 +21.4; cost episodes −6.9 / −15.5 / −31.5 / −13.2); L12 ΔES99 +1.95 pp, ΔES95 21-day +2.9 pp, ΔCDaR95 +7.1 pp, SD of ΔSR 0.066; L13 variants (cap 1.5 in reference mode) | DL-A files. Local: `r2_idx_start_date_sensitivity.csv` is a different series (rebuilt KOSPI from 1996-06/09) and different rules; informative only | REFDATA |
| T-EPIS-02 (L2401) | Korea definitive cell, raw flag: 14 of 18 objective episodes positive, max share 0.174 ± 0.01; printed §8.6 line 0.493 (4 of 11) | as G-KR-L09 | REFDATA |
| T-TROUGH-01 (L2403) | every card prints a trough → +63-session window per episode and the three cost episodes; Korea cell vs S: −6.9 / −15.5 / −31.5 pp; none enters PC-4 | structure synthetic; numbers DL-A | SYNTH / REFDATA |
| T-ES-02 (L2260) | ΔES99 daily +1.95 pp; ΔES95 of 21-day returns +2.9 pp; ΔCDaR95 +7.1 pp; z (4.3; 2.3) in reference mode only; R-21's z printed and frozen, never asserted against them | DL-A K10 | REFDATA |
| T-RLAYER-01 (L2405) | R-06 KR on / off / S books follow rule 6; `with_risk_layer` reproduces Check C2 (24 HALTs, MDD −56.4% vs −45.3%) within Level-1; flipped convention refused | refusal: synthetic; C2: KOSPI 1997-2026 | SYNTH / REFDATA |
| G-PWR-01, G-PWR-02 (L5972-5973) | SE(ΔSR) vs S: US VT15 0.061 (241-246 years), KOSPI VT20 2016-26 0.132 (319-330), MDE80 0.128 / 0.276; P(REJECT) at a true 0 per cell (e.g. 0.69 · 0.58 · 0.44 at 11 y) | `QX_DLB_power_se.csv`, `QX_DLB_power_sim.csv`. Local: `r2_idx_gate_sim.csv` is a different simulation | REFDATA |
| G-US-F01 … F10 (L5864-5873) | v1.2-check values and verdicts as listed in the task; F08 class assertions near thresholds | fixture U1 (French Mkt-RF + ^GSPC Sep-2026), DLB-T1h | REFDATA |
| T-R06-US-01 (L5646) | registered card shows the exact label and is never re-run; any vt > 1.0 fails validation | rules store temp copy | SYNTH |
| T-GATE-02 (L2254); I-08 US clause | U1: v2 verdict INSUFFICIENT DATA as a class; ES21 +1.65 pp, ES126 +3.8 pp (± 0.2 pp); p_ni printed and md5-frozen, never asserted against 0.146; 2× ΔSR −0.125; label stays | U1 | REFDATA |
| T-R03-01 step-3 and header clauses (L5644) | French Mom fixture (50 bp, both legs): ΔSR +0.273 ± 0.01; deflated 0.98 ± 0.01 at N_equiv 6.3 (PASS), 0.947 ± 0.01 at linear N̂ 12.6 flagged "step 3 borderline"; r2 and r3 each carry a committed header md5 before their runs and increment the R-03 ledger; years line 20 differing years, 15 higher gross / 11 net | arithmetic from QF3 inputs (0.2729, 0.0716, 0.0935): inline; header / ledger clauses: synthetic; ΔSR and N_equiv: French Mom daily 1990-01-02 → 2026-08-31 and `QX_EX1_qf3_trial_corr_diff.csv`. Local: none | SYNTH (arithmetic, header order) / REFDATA |
| G-DSR-01 (L5947) | 0.9505 at N 46; 0.9004 at N 100 with `delta_SR = 2.5/√250`, `SE_obs = √((1 + 3·SR + 9/4·SR²)/(T − 1))`, T 1,250, `SE_null·hurdle = √(0.5/250)·e(N)` | inline (L2522) | SYNTH |
| G-DSR-02 (L5948-5951) | R-03 net of 50 bp: SR 0.6723, T 9,233, skew −0.687, kurtosis 6.948; ΔSR +0.2729, HAC SE 0.0716 (NW-250 0.093); at N̂ 12.5-12.6 deflated ΔSR 0.947; at M 34 (N̂ 16.2) 0.927 | French Mom | REFDATA |
| T-R04-01 (L5645) | step 3 on the R-03 family ledger: deflated add-on 0.77 ± 0.02 at N_equiv 6.3 → "step 3 FAIL"; validation rejects any A-provisional or pooled route for a card already run | arithmetic inline (0.0724 / 0.0349 / 0.0349); refusal synthetic; real ledger: QF3 26-trial series | SYNTH / REFDATA |
| T-R14-01 (L5647) | header refused without `instrument_book` (multi_line + lines) and the claim (CARD-O, diversification); goldens restated at cap 1 with sub-period correlations (SR 0.449; corr 0.03 on 2001-26; 0.34-0.36 on 2013-26); failure-mode text reads "not fast-crash protection" | refusal and text: synthetic; goldens: 12 index series 2001-26 (list not in the spec) | SYNTH / REFDATA |
| T-BASIS-01 R-14 runtime clause (L5569) | vt is not applied to TS trend; no overlay multiplier applies to `ts_trend` | synthetic sleeve | SYNTH |
| I-15 (L5705) | step references reset after 21 sessions, the hard-stop reference does not; binding share printed (≈ 19% KOSPI VT20, 10% US VT15); above 10% steps act only in the specification book until this CARD-P passes; ΔSR vs no steps printed and matching the R-31 reference run | references and placement: synthetic NAV; shares and ΔSR: KOSPI / US fixtures and the pending reference run | SYNTH / REFDATA |
| T-STEP-01 (L3345) | synthetic NAV: −9% → 0.5× for exactly 21 sessions; −13% → 0.5× and the new-entry block for exactly 21 each; then `ref_step` resets to the NAV and `hwm_hard` does not; a later −15% from `hwm_hard` → HALTED although `dd_step` is shallower | inline NAV path | SYNTH |
| T-STEP-02 (L3346) | binding share ≈ 19% (KOSPI VT20, 3 bp, 1997-04-15 → 2026-10-02) and ≈ 10% (US VT15, 5 bp, 1990-04-02 → 2026-09-30), ± 3 pp, printed | `QX_EX1_ladder.csv` inputs. Local: `yf_069500.KS.csv` exercises the code path from 2007 only | REFDATA |
| T-STEP-03 (L3347) | ΔSR vs the same book without steps printed and matching the R-31 reference run | §9.4 item 8 run (pending) | REFDATA |
| T-STEP-04 (L3348) | KOSPI share > 10% and no PASS: step multiplier only in the specification book, recommended book carries the hard stop only; US placement uses the exact computed share once D5 enables a sleeve | injected shares 0.10 (allowed as INVARIANT_STEP), 0.1001 (specification only) | SYNTH |
| T-EST-03 (L3245) | COMB sized book, KOSPI 2001-26, 3 bp, target 20%, cap 1: vol-of-vol −22% ± 2 pp vs SMA20 (0.0347 vs 0.0446); ΔMDD +2.8 pp; ΔSR −0.000 with 90% CI [−0.042, +0.039] | KOSPI OHLC from 1996-12 | REFDATA |
| T-EST-05 (L3247) | estimator change without a new card revision and ledger row refused; COMB declared on a `KRX_stock_book` card refused | synthetic headers | SYNTH |
| T-EST-01 / T-EST-02 / T-EST-04 / I-10 M7 clauses (L5553) | MCS and Stage-3 CIs come from the frozen R-24 bootstrap; Stage-3 report ranks survivors by vol-of-vol with CI ties broken by simplicity; a challenger enters a card only through a counted revision; the fallback never blends | call-path and ordering on synthetic books; values as M3 | SYNTH / REFDATA |
| T-B5-01 "cannot be PASS" clause (L5642) | a vol-target card whose estimator is FAIL cannot be PASS (cap REVISE, `estimator_calibration`) | synthetic estimator σ̂ × 0.7 | SYNTH |
| T-CAP-02 stack clause (L5510, L5627) | stack card prints the share of days at ≤ 0.25× total exposure and the rebound capture; once ≥ 2 de-risk factors act a stack CARD-P is generated and gated; EX1 on KOSPI 31.0% (product, reference mode) vs 11.2% (`min()`) | generation: two synthetic PASS factors; EX1 values: KOSPI 1997-2026 | SYNTH / REFDATA |
| T-POWER-01 years clause (L5661, L6008) | years to detect +0.05 restated to a point inside 241-246 / 319-330 before the freeze | formula inline; point on the named fixtures | SYNTH / REFDATA |
| T-EXCESS-01 frozen-convention clause (L2402) | frozen-convention values computed, printed, md5-frozen at first run; never asserted against the research numbers | KRX closes + daily `BOK_CALL_RATE` | REFDATA + OWNER |
| T-GATE-02 p_ni clause; T-ES-02 z clause (L6011) | printed under R-24's studentized bootstrap / R-21's stationary bootstrap and md5-frozen; never asserted against 0.146 / 4.3 / 2.3 | U1; DL-A K10 | REFDATA |
| T-SEL-01 (e) (L5589) | at the card run f is recomputed; the larger of it and the acceptance report's binds, both printed, the run never refused | temp ledger with a row registered between report and run | SYNTH |
| T-ROLE-02 cash clause (L5580) | a missing cash day refuses the card (never cash = 0) | synthetic cash series with one missing own-calendar day | SYNTH |
| T-LAG-01 "refuses to write the card" clause (L5582) | an injected datum with `available_at_utc > decision_utc` → `LookAheadError`, no card file | synthetic | SYNTH |

Hermetic checks to add (proposed, not spec ids; all SYNTH): `commit_header` before the freeze raises `PackageNotFrozen`; second commit of the same `(card_id, revision)` refused; CARD-P header that differs from its draft in a non-volatile field refused; ninth searched parameter refused; an exception inside `run_card` leaves no card file, no `verdicts.jsonl` row and no archive; `verify_verdict_chain` fails on a hand-edited row; `disposition_for` truth table; a `NaN` result is written as `null` and the card still validates; `run_card` on the registered US card id refused; `binding_share` of an all-ones vector is 0.0.

---

## E. Interfaces

### E1. Needed from earlier milestones and from M7 part 1

| From | Name and shape | Used for |
|---|---|---|
| M0 | schemas `model_card_header.macro` and `model_card.macro` in one registry keyed by `$id`; `validate_card_header(header)`; rules store with the §7 blocks, `{ref}` resolver, `owner_decisions`; DNB validation (`refused_shapes`); governance appender (kinds `header_commit`, `binding_share_recompute`, `package_freeze`, `package_redesign`); `cost_per_side(instrument, date, price, side)` with the tick floor; artifact writer with git, config, snapshot, package and ledger hashes; `config.macro_artifact_dir()` | B1, B3, B5 |
| M1 | `pit_value`, `PITValue`, `MissingInput`, `RunContext{decision_utc, knowledge_utc, run_mode}`; `data_snapshot_id` and row content hashes; calendars (sessions, month-ends, `close_print_bound_utc`, regime tags, Saturday sessions); `LookAheadError` and the lag audit; registry series `KOSPI_OFFICIAL_CLOSE`, `BOK_CALL_RATE`, `US_RF`, daily opens; fixtures and `tests/fixtures/macro/MANIFEST.csv` | B3, B5, B6 |
| M2 | `market_vol_target`, `vt_weights`, `costed_book`, `static_comparator`, `compose`, v1.2-check mode (`gate_boot`, PW on d and d²), reference mode under `tests/reference/` | books, B7 |
| M3 | `estimator_gate(market, instrument_book, horizon=21) -> EstimatorSelection`, B5 status, `ewma094` (the EWMA(0.94) line), `comb` | B12, R-06 KR printed line |
| M4 | `sleeve_vol_scale(market, family, decision_utc, revision ∈ {1, 2, 3}) -> VSResult`; the paper long/short series builder (`MOM_PAPER_LS_SERIES`); `dm_gate`; `base_weights`; the years-line function; research-phase ledger rows for +0.273 | B9, B10 |
| M5 | `drawdown_ladder(nav_path, decision_utc) -> LadderState`; the hard stop with its automatic re-arm in backtests; `concentration_bound`; per-book runtime; the R-27 fill model (`KRX_close_auction`) | B11, `with_risk_layer`, B13 |
| M7 part 1 (TASK-M7-01 … 17) | `family_ledger(family_id) -> FamilyLedger`, `ledger.append(family_id, config)`, `ledger.hash(family_id)`; `step3(card) -> Step3Result`; `n_eff`; `deflated_dsr(dsr, se_obs, se_null, hurdle)`; `lw_studentized_boot`, `pw_block_psi`, `se_ladder`, `power_line(card) -> PowerLine`, `by_qvalue`, `harvey_liu_haircut`, `lo_adjusted_sr`; `pbo_cscv(configs, objective, S=16)`; `episodes(market, rule, threshold)`, `excess_returns`, `start_band`, `midpoint_halves`, `regime_lines`; `cardp_evaluate(header, books) -> CardPResult`; `overlay_card_eval(card, ledger) -> CardResult`; `placebo_panel(header, n=20)`; `gjr_null_percentile(header, n_paths=1000)`; `timing_profile(card) -> TimingProfile`; `gate_acceptance_test`; `verify_package()` (manifest re-hash); `acceptance_report.json` with each CARD-P draft's md5 and f per row-set reading; the frozen `gate.package` | every card run |
| M7 part 1 (requested, proposed name) | `combine_card_verdict(gating, band, halves, shape)` as a pure, separately testable function inside the frozen harness | I-16 injected sub-verdicts (B6) |

Gap to close with M7 part 1: the per-rule-type CARD-O neighbour grid for step 7 and the configuration set for step 4 on a card with `searched_parameters: []` (R-03, R-14) are not written out in the ranges read; if the configuration set has fewer than 10 members the card prints `"PBO not run (n < 10)"` (L4763).

### E2. Exposed to later milestones

| To | Name and shape |
|---|---|
| M8 `verdict_filter` (R-35) | `cards/verdicts.jsonl` rows (B5); `cards.verify_verdict_chain()`; card files with `results_md5`; `archive/**` with `rederive_snapshot_id`; `cards.card_status(card_id)`; `cards.acting_revision("MACRO-R03-US-MOM")` |
| M8 FORWARD-SIM books (R-28, R-29) and forward records (R-25) | committed headers under `headers/`; each card's design-sample mean multiplier m̄ (F-18); each card's design-sample ΔSR distribution (2.5th percentile) for the catastrophic bound; honesty-line thresholds −0.20 / −0.39 / −0.73 |
| M8 book builders | R-31 frozen placement share and its disposition (`INVARIANT_STEP` or `SPECIFICATION_ONLY`); `maybe_generate_stack_card`; the recommended-builder refusal of any factor whose `card_status` is not PASS |
| M6 / M8 builders | the `card` object `{card_id, class, verdict, disposition, displayed_as, label, results_md5}` for `overlay_decision` and `macro_state` |
| UI (Strategy Lab, Macro page) | `load_macro_cards()`; label strings; `verdict_at_f1`, `verdict_at_f_neff` |
| any later re-gate | `commit_header` (new revision on the extended sample, one counted revision, L5328) |

---

## F. Ambiguities, contradictions and conservative-reading decisions

| # | Issue (lines) | Conservative reading adopted |
|---|---|---|
| F-01 | No reference fixtures, no git repository and null owner inputs on this machine, while the freeze, the header commits and the formal runs require all three (L4812-4828, L76, L6016-6035) | Build code, schemas, drafts with typed placeholders and SYNTH tests. No package freeze, no header commit, no card file, no `verdicts.jsonl` row. Every macro card stays `NOT_RUN`; recommended book = invariants only |
| F-02 | "The header committed in step 4 must match its draft"; draft md5 = "the header fields without the package citation" (L4815), yet `created_utc`, `header_md5`, `ledger_hash_at_registration` and `N_raw_at_registration` necessarily change at commit (adoption adds one revision to every family ledger, L4820) | Match asserted on every field except `VOLATILE_AT_COMMIT` (B1); any other difference refuses the commit |
| F-03 | T-CARD-01: "A class or claim change creates a new revision" (L5663); §8.4: class → new revision (L4891), a different claim → new card (L4892); §8.2: "Changing the claim after results is a new card" (L4851) | Class change → `revision + 1`; claim change → new `card_id`. Both are new header records and both add to the family ledger. The test asserts "old header unchanged, new header record exists, ledger incremented", not which of the two |
| F-04 | When the ledger increments: rows are appended "by `core/quant/backtest` itself on every run … never by hand" (L2440); revisions "increment the R-03 family ledger" with the header "committed before its run" (L1519, L5644) | `commit_header` appends nothing; the harness appends the row at the revision's run. `N_raw_at_registration` is the count at commit |
| F-05 | R-29's draft belongs to the acceptance population with "its span ending at `gate.evaluation.data_cutoff`" (L4815; US 2026-10-01), but its band is decade-spaced on a ≥ 80-year daily span (L2341, L3091) and its verdict span is the 1926+ file to 2026-08 (L3095); that file was never fetched (HTTP 403, L3080) and is listed "needed by M8" (L6028). R-28 is incremental on R-29's book (L2988) and its own data span is not stated | R-29 and R-28 headers are not drafted or committed without the frozen 1926 file. They register after the freeze under L4815 (own panels at header commit), or the freeze waits for the file. Never the 1990 file (L3126). Both stay NOT_RUN; FORWARD-SIM books do not start |
| F-06 | `notional_nav` is required, > 0 and equal to `sleeves.US.notional_nav` (L3953, L3127), which is null while D5 = none (L4463); the granularity floor is checked at the header commit (L4438): one Micro ES ≈ ₩52m needs ≥ ≈ ₩1.04bn | Headers refused until the owner signs a US sleeve notional that passes the floor. No default notional is invented |
| F-07 | R-03 runs on "QUANTGEN's own momentum sleeve (US shares via KIS, 50 bp on both legs …)" over "its declared history" (L1526, L4823); the repository has no cross-sectional US-share momentum sleeve (the composite is a single-symbol score; the only `xs_momentum` card is nine sector SPDRs, REJECT); "a factor sleeve on US shares is not a US sleeve in D5's sense" (L73), so `sleeves.<market>.notional_nav` has no key for it | Card NOT_RUN until the owner names the sleeve universe, its history start and a signed notional key. Harness verified on the French fixture only (REFDATA). Revision 1 keeps acting in the specification book as built in M4 |
| F-08 | Zero-investment long/short series "get no cash term" (L2334); the schema requires `cash_convention {returns: excess, cash_series}` (L3969) | `cash_convention: {returns: excess, cash_series: US_RF}`; the harness applies no cash term to a series flagged zero-investment and prints that convention |
| F-09 | `start_band` and `midpoint_halves` are "null unless the card is an acting long-sample card" (L4883); "long sample" has no threshold; the stability-floor cap is listed for CARD-P (L5221); R-03 would act on a PASS | R-03 declares the default shape (33 monthly starts, `"2/3"`) and midpoint halves: extra conditions can only lower a verdict. R-14, R-31, R-28 leave both null until a revision makes them acting long-sample cards |
| F-10 | R-14: the claim is "diversification … not outperformance" (L1702) but the CARD-O path is steps 1-9 against a benchmark (L4844, L4985) and no diversification statistic is defined; the 12-index set is not listed (L1703); "sign" may be long/short or long/flat; SD ddof not stated; `comparator` enum has no "equal-weight basket" value | Do not invent a diversification gate. Run steps 1-9 against the equal-weight long-only basket as written, print correlation and drawdown lines, keep the sleeve descriptive. Long/flat on ETF lines unless the header declares futures lines; ddof = 1. Card NOT_RUN until the council fixes the index list and the claim statistic |
| F-11 | R-31: `build_status_on_pass`, `tier` and `label` are not given (L4785-4788, L5396). Its "declared book" is KOSPI VT20 at 3 bp (L5396, T-STEP-02) while the placement share is computed on the recommended book without the steps (L3305), which today has no vt. Whether the placement share is measured with the steps acting or as a shadow state is not said | `build_status_on_pass: BUILD_AS_INSURANCE` with the default CARD-P label (protection claim; affects display only after a PASS). `tier` from the deterministic de-clustered activation count of the declared book (≥ 30 → A, else B). Header names the declared book; card prints both shares in `printed.binding_shares`; the frozen placement share is the shadow share on the recommended book without the steps. Steps stay in the specification book either way |
| F-12 | `QC_modules.csv` row for R-31: "ΔSR vs no steps within ±0.01 on the fixtures" (L5538) vs T-STEP-03 "matches the R-31 reference run" (L3347) | The rule table governs (L5505); the reference run is pending (§9.4 item 8), so T-STEP-03 cannot be asserted yet |
| F-13 | R-04 is not in the step-4 header list (L4821-4824), yet T-R04-01 says "The card computes step 3" and a card id `MACRO-R04-US-DM` appears (L3782) | No card file without a committed header. R-04 keeps `NOT_RUN` with label "step 3 FAIL (indicative)"; the step-3 number is published as harness output on the R-03 ledger. A formal R-04 header needs the council's word; the recommended book refuses R-04 in both cases |
| F-14 | Disposition of a REJECT card that is not a refusal book (R-06 US; R-06 KR "REJECT → archive", L1574) is not mapped; `NOT_RUN` is absent from the card schema's verdict enum (L4007) | `DESCRIPTIVE`, read by no book. "Archive" = the factor leaves the specification book as well (enters as 1.0) and the card stays on record with the same weight as a PASS (L4778). `NOT_RUN` is never written to a card file |
| F-15 | Exact byte coverage of `header_md5` and `results_md5` (self-reference; `generated_at_utc`, `git_hash` are `volatile_fields`, L4683) | `header_md5` over the header minus itself; `results_md5` over the result fields minus `{results_md5, generated_at_utc, git_hash}`, canonical JSON. Both rules written in the manifest |
| F-16 | `cards/verdicts.jsonl`, `gate/acceptance_runs.jsonl` and the card directory have no stated root; the legacy card directory must not receive macro cards | One macro artifact root (B1); legacy directory untouched |
| F-17 | External anchor and `git_hash` without a git repository (L4820, L3487 (iii)) | Fail closed: no freeze and no header commit until the owner provides a repository or another external, timestamped anchor. `git_hash` is never fabricated |
| F-18 | "The forward S book uses the design-sample m̄ written in the header" (L5313) while a header carries no run output (L4876) and the closed schema has no m̄ field | m̄ is written in the card's result block and read from there by M8; flagged to the M8 owner |
| F-19 | Stress-cost line: `sigma_median` window undefined (L2831) | Expanding median of σ20 through t (causal); printed only |
| F-20 | Tech-fund XS-11 (R3 L296, L1299): blocks `max(10, PW on d and d²)` for steps 2 and 5 on every card. Council: "That rule is withdrawn"; frozen rule `max(21, PW(ψ))` (L4991, L4586) | Macro cards use the frozen Council rule; a different rule is a package change that must be decided before the first acceptance attempt. The PW(d, d²) interval may be printed, never gating. XS-11 applies to non-macro cards |
| F-21 | Tech-fund XS-12 `S_beta` comparator (R3 L1300) and XS-09 "add a CARD-P cell" for R-14 single-index trend (R3 L1297); XS-20 judged-history question for R-06 KR (R3 L1308) | `S_beta` is for stock-level sleeves, none of which is an M7 card. XS-09 is a proposal for a new card, never a change to `MACRO-R14-MULTI-TREND`; a KOSPI trend card that acts is DNB item 37. `gate.evaluation.history_start.KR = "1997-04-01"` stays |
| F-22 | Band starts: "monthly starts 1997-05 … 1999-12" (L1574) does not say which session or how σ̂ warms up | First session of each month (as R-29's "first session of January", L3091); σ̂ uses the fixed history before the start, so the weight earns from the start session |
| F-23 | `selection_factor`, `verdict_at_f1`, `verdict_at_f_neff`, `gjr_null_pct` are required on every card (L3998-4002) but f applies only to CARD-P | CARD-O: `selection_factor = {value: 1.0, rule: "computed_by_step3", alt_value: N_eff}`, both `verdict_at_*` equal to `verdict`, `gjr_null_pct: null` |
| F-24 | Whether T-GATE-02's harness run on U1 appends an R-06 ledger row ("research scripts included", L2440) although the card is "never re-run" | It appends a row in the temporary ledger copy in tests; in a docs-mode run it appends a `phase: research` row. No card record in either case (L5992) |
| F-25 | §8.9 states an expected verdict for R-06 KR (INSUFFICIENT DATA) | Tests never assert the formal run's verdict; it is computed blind. Only the verdict function and the printed fields are asserted |

---

## G. DO-NOT-BUILD items and invariants that bind this area

| Item | Binding rule for the card code | Check |
|---|---|---|
| P0, §10 item 21 | No order, cancel, withdrawal, deposit-address or transfer path; the runner reads fixtures or the PIT store only; no network in tests | T-RO-01, T-HERM-01 |
| P11 (L605-608) | The package is frozen before any formal card run; nothing in it changes after a card result has been seen; a change is a new package version, re-run on every card, flips disclosed, never justified by the card it flips | T-CARD-02, I-08 |
| R2-C1 (L53, L5407) | R-06 KR is never rescued: no change of convention, window, cap, cash series, row set, estimator or start band after results | code review; ledger |
| §10 item 2 | No multiplier, weight or vol-target cap above 1.0; cap 1.0 is permanent; cap-1.5 variants only in reference mode from `tests/reference/` or `docs/` | T-CAP-01, T-R06-US-01 |
| §10 item 22, P7 | A non-PASS card's output is never offered as a recommendation; FORWARD-SIM multipliers (R-28, R-29), R-04, R-31 steps at share > 0.10 before a PASS, R-11 / R-12 never reach the recommended book | I-03, T-CARD-01 |
| §10 items 23, 32, P15 | No cost lowered; no instrument book, notional, rebalance rule, band or venue changed after results; each variant is a new card counted in the family ledger; MACRO-R06-US-FUT is a new card, never a revision of the 50 bp card; the 50 bp card is never re-run | T-COST-03, T-BOOK-01, T-USFUT-01 |
| §10 item 25 | No estimator change outside a counted R-30 revision that passes the full v2 CARD-P; never on the registered R-06 KR card or on a stock book | T-EST-05 |
| §10 item 31, P17 | Composition is `min()`; a product-composed stack is refused; a second de-risk factor joins only after the stack card's (a) and (b) both PASS | T-CAP-02 |
| §10 item 33 | No stock book as a market-gross scalar; the R-06 KR 35 bp line is printed for reference only | T-BOOK-01 |
| §10 item 34 | No pooled or A-provisional route for a card already run (R-04, the jump model, KOSPI trend) | T-R04-01 |
| §10 item 35, P14 | A forward record is a falsification alarm only; it never raises a verdict, never counts toward sufficiency; INSUFFICIENT R-06 KR has no forward-record route | I-14 (M8) |
| §10 item 36, P13 | No Kish trial count; no revision count as N; every configuration run, research phase and every timing lag included, is a ledger row; null-distribution runs append no row | T-STEP3-02, T-SEL-01 (f) |
| §10 item 37 | No R-28 instance with `market: KR`; KOSPI trend is context only | T-TREND-03 |
| §10 items 18, 19, 26 | 2022-01-01 → 2026-10-02 is a reported stress window, not a holdout (locked holdout from 2027-01-01); no provisional, intraday or bar-derived close in a card; VALUE and NON-COMPLIANT goldens are labelled and never feed a production rule | T-LAG-01, I-05 |
| P12, red line Q2 | A drawdown line (ΔMDD, ΔCDaR95) never REJECTs; a cap only lowers and never creates a REJECT | T-DNH-01, T-ORDER-01 |
| R-22 rule 6 | Card books exclude the R-07 hard stop and caps, except R-31 (hard stop) and the stack card (both); a flipped convention is refused | T-RLAYER-01 |
| L2245 | No partial verdict, no error card: a failed bootstrap, comparator or episode list writes nothing | hermetic check (section D) |
| L4876, L3913 | A header is immutable once committed and carries no result field; `selection_factor` is computed by `step3()`, never declared | T-CARD-01, T-SEL-01 (c) |
| L4896 | All macro cards together have at most 8 searched parameters | hermetic check |
| R-34 (L3432) | `timing_probe` is callable only from `timing_profile()` in tests or the R-34 sandbox; never from the runtime, a book builder or a verdict path; probe output is tagged `synthetic_lookahead` and lands outside the production artifact directory | T-PLACEBO-02 |
| T-HERM-02 | Tests write only to temporary copies of the rules store, the ledgers and the artifact directory | byte-identity check after `run_all.py` |
| Tech-fund DNB (R3 L349-478, XS-19 at R3 L1307) | DNB-TF-01 … 17 extend §10 and are enforced by M0 validation. The one that touches an M7 card: DNB-TF-05 (R3 L395), "US single-index trend or volatility targeting on SPY is a viable protective card at QUANTGEN's 50 bp per side" is refuted, which agrees with the instrument-labelled REJECT of the R-06 US 50 bp card; it is no ground to re-run that card. The others are signal families outside the M7 cards | M0 validation |
