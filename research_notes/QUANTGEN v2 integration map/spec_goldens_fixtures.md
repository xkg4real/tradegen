# spec_goldens_fixtures — implementation brief (QUANTGEN v2.0: golden values, fixture manifest, pending register)

Source: `C:/Users/whydi/OneDrive/Desktop/QUANTGEN/QUANTGEN_Quant_Council_2026-10-03/claude_code/QUANTGEN_MACRO_INTEGRATION.md` (cited `L<n>`).
Ranges read in full: L5708-6038 (§9.3 goldens, §9.3.3 modes, §9.4 pending, §9.5 manifest and acquisition register), L6376-6479 (§13), L5489-5707 (§9 hermetic rule, §9.0, §9.0a, §9.0b, §9.1, §9.2), L6264-6375 (§11, §12), L14-102 (Quick start), L4799-4839 (§8.1.3 freeze), L4967-5076 (§8.5), L5077-5170 (§8.6), L5171-5302 (§8.7), L1270-1340 (§4.1), L1386-1452 (§4.2), L1485-1498 (R-01), L1554-1577 (R-06), and every rule-table test the goldens cite (L1963-1969, L2096-2101, L2253-2260, L2400-2405, L2522-2528, L2628-2633, L2744-2748, L2869-2873, L2952-2955, L3045-3048, L3135-3139, L3243-3247, L3345-3349, L3461-3463). Tech-fund: `R3_TF_neural_link.md` §11 (L896-1239) and §13-15 (L1283-1345); `datalab/results/` listings. Task file: none for this brief; task ids below are from `QUANTGEN_V2_TASKS.json`.
Binding rulings: `00_coordinator_rulings.md` (NotRun, `tests/macro_registry.csv`, module names, no new dependencies, `git_hash: "UNVERSIONED"`, dry run on local vendor data). Where this brief and the rulings differ, the rulings win.
Silence rule (L89): no exposure change, specification book only, fail closed.

## 0. Machine facts (checked 2026-10-06, read-only)

| Fact | Evidence |
|---|---|
| `/home/claude/quantgen_macro_data/` (CATALOG.md, scripts/, results/), `research_notes/…/council/`, every `QX_*.csv`, `R4_golden_values.csv`, `R4b_golden_values_net.csv`, `.v1.2_INTEGRATION_backup.md`, `QC_modules.csv` are ABSENT | `find` over the QUANTGEN tree: zero hits |
| `tests/fixtures/`, `tests/reference/` do not exist; `tests/run_all.py` knows PASS/FAIL only; suites expose `tests() -> [(name, fn)]` | `tests/` listing; `run_all.py` L34-60 |
| Local daily series: `docs/asset_expansion/cache/*.csv` (46 files; one close column each; no OHLC, no provenance columns). Present: `yf_SPY` 1995-01-03→2026-09-25, `yf__VIX` 1995→2026-09-25, `yf__VIX3M` 2006-07-17→2026-09-25, `fred_DEXKOUS` 2017-01-02→2026-09-18, `fred_DGS3MO` 1990→2026-09-23, `yf_005930.KS` 2000-01-04→2026-09-23, `yf_069500.KS` 2007-01-29→2026-09-23, `yf_QQQ`, `yf_TLT`, sector ETFs, futures, crypto. ABSENT: `^KS11`, `^GSPC`, `KRW=X`, `^TNX`, `^RUT`, `000660.KS`, French files, FRED `DGS10`/`DTWEXBGS`/`VIXCLS`/`VXVCLS`/`NASDAQ100`/`DTB3`/`IRSTCI01KRM156N`, SOX, trend indices, ECOS. `yf__KS200.csv` has 1 row | cache listing with first/last rows |
| US-session cache files were written 2026-09-26 01:28–01:33 local (KST) = 2026-09-25 16:28–16:33Z, inside the NYSE session of 2026-09-25 (close 20:00Z): their last row is an intraday print. T-FIX-01 (L5613) refuses such a file unless that row is dropped | file mtimes |
| Tech-fund result CSVs (`QUANTGEN_techfund_research/datalab/results/{kr,r2_idx,r2_kr,r3,us}`) are scalar result tables; their inputs (`kr/cache/kospi_rebuilt.parquet`, `/home/claude/data_raw/us/spy_lean_daily.zip`, marcap parquet) are absent. `r3/r3_golden_values.csv` GV-273..302 (= R3 §11.8) reproduces the §9.3.1 KOSPI VT20 goldens against their PRE-patch values on a rebuilt KOSPI ending 2026-09-29 (30/30 within Level 1; `r2_idx_validation.csv` V3) | files read |
| `core/quant/validate.py` already has `sharpe` (ddof 1, √252), `sharpe_diff_bootstrap(a, b, block, B, level, seed)` (paired circular blocks, `default_rng(seed)`, returns `p` = share of resamples with ΔSR* ≤ 0), `deflated_sharpe`, `expected_max_sharpe`, `pbo_cscv(S)`, `kupiec`, `christoffersen`, `pit_tests`, `md5_of` | L80-212, L560-608, L791 |
| Reproduced today on existing code: G-DSR-01 0.9505 (N 46) / 0.9004 (N 100) with the L2522 mapping; T-PBO-01 noise control `pbo_cscv(default_rng(11).normal(0, 0.01, (2600, 10))[:2592], S=16)["pbo"]` = 0.5359 (spec 0.536 ± 0.001) | run 2026-10-06 |
| `arch` 8.0.0 importable but undeclared; rulings forbid new dependencies → Politis–White block length must be ported in-house (`core/quant/gate_stats.py`) | `requirements.txt`; rulings §3.2 |
| Folder is not a git repository → `git_hash: "UNVERSIONED"`; the M7 freeze and the f = 1 route refuse (rulings §3.1) | rulings |

Consequence: of the 77 golden ids, one (G-DSR-01) and the T-PBO-01 noise control are reproducible here; a few rows are arithmetic identities; every other golden is REFDATA and must be reported `NOT_RUN` via `NotRun("REFDATA: …")`, never faked.

---

## A. Scope

| Task | One-line deliverable | Target files (E existing, N new) |
|---|---|---|
| TASK-M0-02 | Macro suites registered in the hermetic runner; third status `NOT_RUN`; registry with `tier`, `runs_from`, clause deferrals; `--milestone M<k>` exit set | E `tests/run_all.py`; N `tests/notrun.py`; N `tests/macro_acceptance.py`, `tests/macro_gate_acceptance.py`, `tests/techfund_acceptance.py`; N `tests/macro_registry.csv` |
| TASK-M0-03 | `MANIFEST.csv` (one row per fixture) + loader verifying md5, refusing unlisted files and rows without licence/owner/md5; seed, B, block rule per stochastic golden | N `tests/fixtures/macro/MANIFEST.csv`; N `tests/fixtures/macro/__init__.py` (`manifest()`, `require_fixture()`, `fixture_path()`) |
| (this brief) GF-1 | Machine-readable golden registry: every §9.3 id (value, tolerance kind, mode, runs_from, fixtures, tests, status) and the 17 §9.4 pending items with `value: null` | N `tests/fixtures/macro/goldens.csv` |
| (this brief) GF-2 | Tolerance and class-assertion helpers | N `tests/golden_tools.py` |
| TASK-M1-22 | Generate the golden-value fixtures once at M1's exit through the data layer (provenance fields + `value_status`), md5-freeze, T-FIX-01 refusal; G-POST-01 M1 rows | N `docs/macro_fixtures.py` (generator); N `core/ficc/pit.py::check_fixture` (owned by spec_M1_pit_contracts); N `tests/fixtures/macro/*` |
| TASK-M1-16 | G-STALE-01 table reproduced by T-STALE-01 | `tests/macro_acceptance.py`; fixture F25 `source_skipped.yaml` |
| TASK-M1-21 | Data-acquisition register as a file | N `tests/fixtures/macro/ACQUISITION.csv` |
| TASK-M2-06 | Costed golden engine + research bootstrap (circular, 63-day, 1,000, seed 20261002) on the §9.3.1 conventions | N `core/quant/gate_stats.py` (`research_bootstrap`, `pw_block`), N `core/quant/cardp.py` (`costed_book`) per rulings; `core/quant/backtest.py` untouched |
| TASK-M2-07 | v1.2-check mode (PC-1…PC-7 of L5985-5990) and reference mode (`reference_only=True`, reachable only from `tests/reference/` or `docs/`) | N `core/quant/cardp.py::v12_checks`; N `tests/reference/__init__.py`, `tests/reference/reference_goldens.py` |
| TASK-M2-08 | G-KR-01..04, 02b, 02c, G-US-01/01b/01c, G-POST-01 M2 rows, I-02 | `tests/macro_acceptance.py` (golden tier) |
| TASK-M2-09 (spike) | §9.4 item 2 official-close rerun; md5-freeze; G-KR-06 joins M2 only afterwards | `tests/reference/`; `goldens.csv` status flip `pre_patch_pending → golden` |
| TASK-M3-02/03/04 | G-EST-01..04, G-B5-01..04 (B5 harness `docs/vol_backtest.py` with seed) | N `core/quant/forecast_eval.py`, N `docs/vol_backtest.py`; tests golden tier |
| TASK-M4-03/04/07 | G-MOM-01..06, 08, G-INTL-01, G-BOOK-01, G-YRS-01; G-MOM-07 reference | N `core/quant/sleeves.py`; `tests/reference/` |
| TASK-M5-07, M5-13, M5-14 | G-R08-01 (132 spells); G-LAD-01..03 reference; §9.4 items 9–10 (G-LAD-04, HALT count) | `tests/reference/`; `goldens.csv` pending rows |
| TASK-M7-02 | Ledger seeds (R-03 26 rows; R-06; R-28 94; R-31 EX1 L1–L6) md5-listed in `definitions_md5` | N `tests/fixtures/macro/ledger_seed_R-03.csv`, `ledger_seed_R-06.csv`, `ledger_seed_R-28.csv`, `ledger_seed_R-31.csv` |
| TASK-M7-13 | I-05 full-sample lag audit over every COMPLIANT golden | `tests/macro_gate_acceptance.py` |
| TASK-M7-21/22/24/30 | G-KR-L01..13, G-US-F01..10, G-PWR-01/02, G-DSR-01/02; §9.4 items 1, 4, 11, 12, 14 | `tests/macro_gate_acceptance.py`; `goldens.csv` |
| TASK-M8-09/11/12/13 | G-TR-01..05; French 1926+ acquisition; G-KR-05/05s, G-REF-01/02, G-US-02..04 | `tests/macro_acceptance.py`; `ACQUISITION.csv` |

---

## B. Build spec, module by module

### B.1 Runner, NotRun, registry (`tests/run_all.py` E; `tests/notrun.py` N; `tests/macro_registry.csv` N)

```python
# tests/notrun.py
class NotRun(Exception):          # reason prefix is binding: "REFDATA: …" | "OWNER: …" | "PENDING: §9.4 item <n>"
    pass
```
- `run_all.py`: a test raising `NotRun` → status `NOT_RUN`, reason recorded, counted separately, exit code unaffected; summary `passed/failed/not_run`. `--milestone M<k>` runs exactly the rows of `macro_registry.csv` whose `runs_from ≤ M<k>` (L5546: "A milestone's exit runs exactly the tests and clauses whose runs_from is that milestone or earlier").
- `macro_registry.csv` columns: `test_id, clause, tier, runs_from, modules, suite, notes`. One row per test and one extra row per §9.0b deferred clause (L5567-5595, encoded verbatim in D.4). Tiers (L5496): `fast` (≤ 10 min total), `golden` (≤ 2 h), `freeze` (I-08, formal I-07 and I-16 runs, GJR-null paths, PBO; "runs only in the M7 freeze job and at formal card runs; `tests/run_all.py` verifies its md5s and never recomputes it").
- Hermetic (L5491-5495, T-HERM-01/02 L5607-5608): every network touchpoint patched to raise at import (`core.ficc.data._fred_fetch`, `_yf_fetch`, KIS/FMP/crypto clients); every write to `tempfile` copies of the rules store, ledgers, artifact dir; shipped seeds md5-checked before and after the suite.
- A golden whose fixture is absent calls `require_fixture("<file>")` → `NotRun("REFDATA: <file> not in tests/fixtures/macro/MANIFEST.csv")`. Never skip silently, never PASS.

### B.2 Manifest and loader (`tests/fixtures/macro/MANIFEST.csv`, `tests/fixtures/macro/__init__.py`) — L6018, L6035, L5492, R-01 (5) L1493

```python
def manifest() -> list[dict]                       # parsed MANIFEST.csv; raises if a listed file is missing or its md5 differs
def fixture_path(file: str) -> Path                # refuses a file not in the manifest, or a row without licence, owner, md5 ("a file without them is not a fixture", L6035)
def require_fixture(file: str) -> Path             # fixture_path or NotRun("REFDATA: …")
def verify_all() -> list[str]                      # T-HERM-01 pre-check: every row md5 == md5_of(path); every file in the dir is listed
```
- Columns (verbatim from L6018 + L6035 + rulings §6): `file, source, series, span, retrieved_at_utc, value_status_rule, available_at_source_rule, md5, licence, owner, tests, seed, B, block_rule, exempt_post_close`.
- `source` = a path under `/home/claude/quantgen_macro_data/` per its `CATALOG.md`, or under `research_notes/…/council/` (L6018).
- "Historical close-type vendor rows carry `available_at_source = calendar_bound`" (L6018); "Every stochastic golden names its seed, B and block rule" (L6018) → the three columns.
- Post-close check (T-FIX-01, L5613; R-01 (5) L1493; `data.fixtures: {post_close_only: true, min_minutes_after_close: 10, md5_per_file: true}` L4213; `data.reject_rows_retrieved_before_close_plus_minutes: 10` L4206): a fixture any of whose close-type rows has `retrieved_at_utc < close_print_bound_utc(session) + 10 min`, or any of whose publication-timed rows was retrieved before its `publication_instant`, is refused. `official_close_utc ≡ close_print_bound_utc` of the row's session (L5613). The synthetic T-PROV-01 store file is labelled `exempt_post_close = true` (L5612 "exempt from the post-close-file rule"). Implemented as `core/ficc/pit.check_fixture(rows, market)` (M1 brief); the loader calls it on every close-type fixture at load.

### B.3 Golden registry and tolerance helpers (`tests/fixtures/macro/goldens.csv`, `tests/golden_tools.py`)

`goldens.csv` columns: `golden_id, sub_id, quantity, value, unit, kind, level, mode, runs_from, timing, fixtures, tests, status, source_line, note`.
- `kind` ∈ {sharpe, mdd, window_return, weight, share, p_hi, p_lo, z, es_pp, count_exact, count_boot, percentile, qlike_ratio, se, vol_level, ratio, price, verdict, text}.
- `mode` ∈ {v12_check, reference_only, frozen_v2, print_only}. `status` ∈ {golden, pre_patch_pending, pending, reference}.
- `timing` ∈ {COMPLIANT, VALUE, NON-COMPLIANT} (L5739-5741), copied from the row.

Tolerances, verbatim (L5734-5737):
```python
LEVEL1 = {"sharpe": 0.01, "mdd": 0.01, "window_return": 0.01, "weight": 0.02, "share": 0.03,
          "p_hi": 0.01,   # p ≥ 0.05
          "p_lo": 0.005,  # p < 0.05
          "z": 0.05, "es_pp": 0.002,  # ES, CDaR and ΔES ±0.2 pp
          "count_exact": 0, "count_boot": 1, "percentile": 5, "qlike_ratio": 0.005, "se": 0.005,
          "vol_level": 0.001,         # ±0.1 pp
          "ratio": 0.01, "price": 0}
LEVEL2 = {"sharpe": 0.03, "window_return": 0.02, "mdd": 0.02, "p": 0.02}   # production feeds (e.g. KIS KOSPI official closes); "Every deviation must be explained in the acceptance report"
def within(kind, got, want, level=1) -> bool
def assert_golden(golden_id, got: dict, level=1) -> None          # raises AssertionError listing each sub_id's deviation
def assert_class(stat, threshold, tol, verdict, allowed: set) -> None
```
- `assert_class`: "A verdict derived from a statistic within tolerance of its threshold is asserted as a class, never as a point" (L5738, L5499). Example: G-KR-L10's 1998-10 start (p_ni 0.103 vs 0.10) → {PASS, INSUFFICIENT}; G-TR-01 p_ni 0.000 and G-MOM-08 "0.000 (251-session PW)" → `p < 1/B` (T-PZERO-01 L2631).
- Level 2 has no tolerance for weights, shares, counts, z, ES: print, do not assert, at Level 2.

### B.4 Construction rules every regression golden uses (L5720-5725; §8.5 L5016-5020; §8.6 L5134-5142)

```python
def costed_book(r: np.ndarray, w_decided: np.ndarray, cost_bp_side: float) -> BookResult:
    # L5723: a weight built from information through the close of t−1 earns the return of t ("decide at the close of t, earn from t+1")
    w_held = shift(w_decided, 1)                          # w_held[t] = w_decided[t-1]
    gross = w_held * r                                    # simple daily returns (L5721)
    cost = cost_bp_side * 1e-4 * abs(diff(w_held))        # per side × |Δw|, charged on the day the weight earns; initial entry not charged (L5725)
    net = gross - cost                                    # buy-and-hold and S uncosted; momentum: both legs (L5725, L5019)
    return BookResult(net=net, gross=gross, w=w_held)
```
- US market = French Mkt-RF through 2026-08 spliced with the ^GSPC price return for Sep-2026 (L5722); Korea = ^KS11 price returns, no dividends (L5722). Cash at 0 for every §9.3.1 golden (L5728; v2 excess returns only in frozen runs).
- Sharpe = `validate.sharpe` (mean/sd·√252, ddof 1). Max DD = min(NAV/cummax(NAV) − 1) on the cumulative simple-return NAV of the costed book. Average exposure = mean(w_held). S = overlay-off × mean multiplier, "constant weight, same days, no cost" (L5187, L4972). ΔMDD = MDD(rule) − MDD(S) in pp (+ = shallower).
- Research bootstrap (L5724): circular, 63-day blocks, 1,000 resamples, seed 20261002, paired (same block indices for both books). **share** = 1 − `sharpe_diff_bootstrap(rule, comparator, block=63, B=1000, seed=20261002)["p"]` = fraction of resamples with ΔSR* > 0 (reading recorded in F-2; consistent with `pc3_share_beats_S` of the tech-fund scorecard). Gate-style card statistics (G-MOM-08, G-KR-L*, G-US-F*) use §8.5: Ledoit–Wolf studentised circular-block bootstrap, 2,000 resamples, seed 11 (L4989) — v1.2-check mode uses R4b's `gate_boot` percentile form (B.5).
- Window returns: cumulative simple return of the costed book over the window's return dates; §8.6 conventions (L5134-5142): "returns after the start close" for every US window and most KOSPI windows; four KOSPI windows include the start-date return: Aug-2024 2024-07-31→2024-08-09, Apr-2025 2025-03-28→2025-04-09, Mar-2026 2026-02-27→2026-03-31, H1-2026 2026-01-02→2026-06-30; a 2016 sample truncates the 2015–16 window to 2016-01-04→2016-02-11. Under the strict reading H1-2026 buy-and-hold would read +96.7% not +101.1%, Aug-2024 −6.6% not −5.5% (L5141) — the goldens use the stated dates.
- Weights "22 Jun 2026 0.30; 23 Jun 0.33; 30 Jul 0.25; earning on 2 Oct 0.61" (G-KR-04 L5775) are the weights EARNING on those dates (decided at the previous session's close; tech-fund reproduction 0.3025/0.3310/0.2485 as "weight earning on", `r2_idx_golden_values.csv` rows 29-31); "decided at the 2 Oct close for the next session 0.69 (0.694; rv20 28.8%)".
- G-POST-01 formulas (L5815-5834, §11 L6286-6294): KOSPI return 2 Oct = 7,003.74 / prev − 1 = +0.46%; drawdown = 7,003.74 / 9,114.55 − 1 = −23.16% (−23.2%); close / 200-day average = 7,003.74 / mean(last 200 closes incl. 2 Oct) = 1.107; rv20 = stdev(ddof = 1) of the last 20 simple returns × √252 = 28.82% (R-06 L1561); vt = min(1.0, 0.20 / 0.2882) = 0.694 (L1562); KRW=X "20-observation change" = dlog over 20 observations of the series with the provisional 2-Oct row dropped = −0.11% (last row 1,356.84 dated 1 Oct; §11 L6291, L6328 call it "20-observation dlog"); Samsung + SK hynix implied share 53.6% = 29.8% + 23.8% (B3a anchor, L5832; §11 L6310: 25-Oct-2024 KRX-weight anchor); closes ₩276,000 / ₩1,841,000 (L5833).
- B5 (G-B5-01..03, L5796-5804; T-B5-01 L5642; TASK-M3-03): rolling-origin 1-day 5% VaR, FHS form (σ̂ × empirical 5% quantile of standardised residuals) unless stated; exceedance band = 0.05 ± 2·√(0.05·0.95/n) (n 2,594 → 4.14–5.86%; 2,663 → 4.16–5.84%; 8,961 → 4.54–5.46%; 371 → 2.74–7.26%; all verified); PIT uniformity χ² over 10 equal bins, PASS if p ≥ 0.01 (TASK-M3-03) and exceedance inside the band. The GARCH "FHS 5.42% → PASS (2,123 origins)" line needs its own band (0.05 ± 2·√(0.0475/2123) = 4.05–5.95%).
- Display labels (G-B5-04, T-LABEL-01 L5643): relative = σ̂ vs quartiles of its trailing 756 σ̂ values; absolute = vs expanding full history; causal; a value exactly on a quartile boundary takes the higher label.

### B.5 v1.2-check mode (`core/quant/cardp.py::v12_checks`; L5984-5990). Reproduction only, never a verdict.

Verbatim checks, "with the v1.2 protective checks of `.v1.2_INTEGRATION_backup.md` §8.7, never with the v2 package":
- PC-1: MDD(rule) − MDD(S) ≥ +3.0 pp at 1× **and** 2× costs, and MDD(rule) better than MDD(overlay-off);
- PC-2: the tail-exposure ratio ≤ 0.90 (definition owned by R-21 / spec_M7_gate_package; this brief does not restate it);
- PC-3: margin δ = 0.10, one-sided percentile bootstrap p of {ΔSR* ≤ −δ} (circular blocks, R4b's `gate_boot`) ≤ 0.10, with p_ni = max(p at 10-session blocks, p at max(10, PW(d), PW(d²))-session blocks) as the R4b and DL-A goldens report it (G-KR-L01: 0.052 / 0.029 at PW block 183), 2,000 resamples, seed 11, Bonferroni × the configurations searched as recorded in each golden's source row (G-KR-L01's PASS at 0.052 implies a factor of 1); the point ΔSR ≥ −δ also at 2×;
- PC-4: on the §8.6 drawdown windows, ≥ 3 with a positive benefit vs S and none above 50% of the summed positive benefit;
- PC-5: ≥ 60% of calendar years positive; PC-6: ≥ 50% of the neighbouring cells (8 neighbours, one step on each declared axis) keep ≥ half of the centre's PC-1 improvement and the PC-3 point; PC-7: ≥ 30 de-clustered onsets for discrete rules, ≥ 5 §8.6 windows, ≥ 756 + 126 sessions;
- raw returns with cash at 0 (for T-EXCESS-01 and I-09 only, PX2's excess-return cash fixture instead: FRED `IRSTCI01KRM156N`, monthly, ÷ 252, used from the month after), and the v1.2 verdict order (sufficiency, REJECT, inconclusive, REVISE, PASS).

```python
def gate_boot(d_rule, d_comp, *, block, B=2000, seed=11, delta=0.10) -> float   # P(ΔSR* ≤ −δ); extend validate.sharpe_diff_bootstrap with `delta`
def pw_block(x) -> int                                                           # Politis–White optimal block length, ported (no `arch`); applied to d and d²
def v12_checks(book_on, book_off, S, *, cost_1x, cost_2x, windows, grid, bonferroni=1) -> V12Result   # fields pc1..pc7, p10, p_pw, pw_block_d, pw_block_d2, verdict (class)
```
- Draw-sequence caveat (F-6): Level-1 p ±0.01 is at the Monte Carlo error of B = 2,000; the exact R4b draw scheme is in the absent reference scripts. Until they arrive, p-values from this implementation are asserted as the verdict class and printed beside the golden.

### B.6 Reference mode (L5992)

- `core/quant/cardp.py` functions accept `reference_only: bool = False`. When true they may compute a cap above 1, the DM gate at 0×, product stacks and the literal v1.2 ladder — "only when called from `tests/reference/` or `docs/` with `reference_only=True`; `core/` cannot import that code". Guard: the reference-only code lives in `tests/reference/reference_goldens.py` and `docs/`; a static test asserts no `core/**` module imports it, and `cardp` raises `RefusedConfiguration` when `reference_only` is false and a refused configuration is requested.
- "Such results never enter a book, a card or an artifact, and T-CAP-01 and T-DNB-01 apply to the rules store and the books, not to this mode."
- Goldens marked `reference_only`: G-KR-06, G-MOM-07, the cap-1.5 variant of G-KR-L13, G-LAD-01 (cumulative and non-cumulative readings), G-LAD-02 (QF4's 11-session halt), G-LAD-03. "Never re-run" (R-06 US) means no new card record is written; G-US-F01 as a reference reproduction is not a card run.

### B.7 Stochastic goldens: seed, B, block rule (manifest columns; L6018)

| Statistic | Seed | B | Block rule | Source |
|---|---|---|---|---|
| Research bootstrap shares (G-KR-02b, 05, 05s, G-US-01/02*, G-MOM-04/08 share column) | 20261002 | 1,000 | circular, 63-day | L5724; `reproducibility.seed_research_bootstrap: 20261002` L4680 |
| v1.2-check PC-3 `gate_boot` p_ni | 11 | 2,000 | circular; 10-session and max(10, PW(d), PW(d²)) | L5987; `seed_study: 11` L4680 |
| v2 PC-3 studentised (frozen runs only) | 11 | 2,000 | circular; p_ni = max(p₁₀, p_max(21, PW(ψ))) | L4989-4990 |
| PC-1′ ES legs (frozen runs) | 11 | — | stationary, mean block 250 sessions; uncentred percentile p | L4992, L5200 |
| T-ES-02 research z (4.3; 2.3) | per `qf3_alt_metrics` | 1,000 | 250-session circular | L2260; reference mode only |
| G-EST-01 MCS | not stated | 2,000 | stationary, mean block max(10, 2h); T_max | L5912 |
| G-PWR-02 paths | not stated | 300 paths per cell | resampling and GJR-t worlds | L5973 |
| T-PBO-01 noise control | `default_rng(11)` first draw; 200 panels from `SeedSequence(11)` children | — | 16 contiguous blocks, Sharpe ddof 1 | L2632 |
| §10 E-label bootstraps (§9.4 item 7) | per `qf3_dnb_classes.py` | 1,000 | 63-day blocks | L6004 |

### B.8 Ledger seeds (`tests/fixtures/macro/ledger_seed_<family>.csv`; L6020; TASK-M7-02)

Columns verbatim: `row_id, source_file, source_row, market, span, run_utc, params, timing_class, book, cost, results_md5, difference_series` ("row id, source file and row, market, span, run_utc, params, timing class, book, cost, results md5, stored difference series").
- R-03: 26 trials (QF3's 26-trial matrix `QX_EX1_qf3_trial_corr_diff.csv`; T-NEFF-01 "QF3's 26 trials stay 26 rows").
- R-06: "every configuration whose Korean-data result was seen before the v2 freeze (R4's and R4b's comparisons, among them the window and cap comparisons on 2016–26 that make R-06 KR's f exceed 1; the DL-A Korea grid; the QF, QX and DL variants) and the family's other-market rows for the family-wide reading (the US VT15 rows DLA-U1–U5, DLB-T1h)".
- R-28: 94 DLB-T3f variants (SMA 2–24 m, TS 1–24 m, 0.5× and 0×). R-31: EX1 L1–L6 ladders.
- "a seed row whose series is missing is regenerated by the harness from its config before the freeze (R2-C1)"; every seed file and series md5-listed in the `definitions_md5` manifest (L4820 (e)); `run_utc` must cite a git commit or external anchor (§9.4 item 15) — refused while `git_hash = "UNVERSIONED"` (rulings §3.1).
- Two configurations that differ only in target, threshold, multiplier or lag are two rows (T-SEL-01 (h)); placebo, shift-panel and GJR-null runs append no row (T-SEL-01 (f)).

### B.9 Fixture generation and md5 freeze (`docs/macro_fixtures.py`; L22, L5492, TASK-M1-22)

1. Read every reference file through the M1 data layer (`PITStore.append` with provenance; vendor close-type rows `value_status = vendor_close`, `available_at_source = calendar_bound`; KRX official rows `official_close`; backfilled publication-timed rows `calendar_bound` from the registry rule, never `inferred_from_retrieval` L1278).
2. Write one fixture file per manifest row ("values unchanged; provenance fields and `value_status` added"), compute md5, write `MANIFEST.csv`.
3. Frozen once at M1's exit. "A regeneration before the M7 freeze must reproduce the same md5s or is a fixture change logged in the manifest with the tests it re-baselines" (L5492). After the freeze, fixture md5s are inside `gate.package.definitions_md5` (L4820 (c)); T-CARD-02 re-hashes at every card run.
4. Cut-offs: `gate.evaluation.data_cutoff: {KR: "2026-10-02", US: "2026-10-01"}` (L4554), KRW=X 2026-10-01 (L5715); the 17:20 KST patch of 2026-10-02 is the as-of.
5. Without `/home/claude/quantgen_macro_data/` the generator writes only the synthetic fixtures (F26, DSR inputs, T-PBO-01) and an `ACQUISITION.csv` listing every absent file; every golden that needs them is `NOT_RUN`.

### B.10 Pending register (§9.4 L5996-6014) — `goldens.csv` rows with `status = pending`, `value = null`; "no number is invented in their place"

| # | Item | Owner task | Becomes a golden when |
|---|---|---|---|
| 1 | Excess-return restatement of every §9.3.1 golden (R-22); only p_ni 0.078 (Korea, PX2 cash) exists | TASK-M7-30 | first frozen run, md5-frozen |
| 2 | Official-close reruns: cap-1.5 VT Sharpe 0.534 (G-KR-06), SMA60 0.550, EWMA (half-life 10) 0.607, EWMA at 35 bp 0.573, Korea stock-book 2× ΔSR −0.061 (labelled pre-patch R4/R4b) | TASK-M2-09 | rerun md5-frozen |
| 3 | R-29 settling run, French daily Mkt-RF 1926-07 → 2026-08, 5 bp (HTTP 403) | TASK-M8-11 | file acquired |
| 4 | Korea card ES126 z (ES126 +6.4 pp in PX1's horizon file) | TASK-M7-30 | computed |
| 5 | Formal R-06 KR card on KRX official closes (I-16) and every formal card | TASK-M7-21 | frozen package |
| 6 | Event-conditional variance test for the opening-gap flag; 2027–28 post-holiday VaR breach check | M5/M8 | run |
| 7 | Bootstraps for the §10 E labels (63-day blocks, 1,000) → B labels | TASK-M0-15 | run |
| 8 | R-31 reference run with separate `hwm_hard` / `ref_step` (T-STEP-03, I-15) | M7 | run |
| 9 | I-04b KOSPI VT20 1997–2026 HALT count under the v2 rule (Check C2 printed 24) | TASK-M5-14 | computed, pinned |
| 10 | G-LAD-04: invariants-only recommended KOSPI book with/without the −15% hard stop (HALT count, MDD, Sharpe) beside D2 | TASK-M5-14 | computed |
| 11 | T-POWER-01 years line restated to a point (T_years = sessions ⁄ 252, SE = SE_plateau) inside 241–246 ⁄ 319–330 | TASK-M7-30 | before the freeze |
| 12 | R-06 KR selection factor f under `any_overlap` for every defensible row-set reading, maximum binding | TASK-M7-30 | acceptance report |
| 13 | M1 measurements: KODEX 200 basket publication instant, NYSE print bound (default 30 s), FRED VIX posting lag (20 sessions) | OWNER (live sessions) | measured |
| 14 | Frozen-package values of T-EXCESS-01 / I-09 excess cell, T-GATE-02 p_ni, T-ES-02 z — "never asserted against the research number" | TASK-M7-30 | first run |
| 15 | Anchored timestamps for `gate.step3.spec_versions` and seed `run_utc` (git commit or external anchor) | OWNER (git) | anchored |
| 16 | Archive each formal card's snapshot rows with the card, md5-listed | TASK-M7-20 | built |
| 17 | Atomic `engine_feed` per book | M8 | built |

### B.11 Local substitutes and the dry run (rulings §1)

Local cache files may feed a labelled dry run (`run_mode = "backtest"`, `value_status = vendor_close`, `dry_run/` artifacts, red chip) and `local_substitute` smoke checks in `tests/reference/` (never a golden, never a milestone-exit pass, never listed in `MANIFEST.csv` as a golden fixture). Usable pairs: G-R08-01 anatomy on `yf__VIX`/`yf__VIX3M` (ends 2026-09-25, 3 sessions short of 2026-09-30 → counts differ by a few); G-B5-02 on `yf_SPY` 2016-03 → 2026-09-24 (drop the intraday 2026-09-25 row); T-H15-01 schedule logic on `fred_DGS3MO` (same H.15 calendar as DGS10); T-STALE-01 (d)/(e) mechanics on `fred_DEXKOUS` 2017→. Nothing Korean (`^KS11` absent; `yf_069500.KS` is KODEX 200, a different index, ending 2026-09-23).

---

## C. Schemas and config

### C.1 `tests/fixtures/macro/MANIFEST.csv` columns
`file, source, series, span, retrieved_at_utc, value_status_rule, available_at_source_rule, md5, licence, owner, tests, seed, B, block_rule, exempt_post_close` (B.2).

### C.2 Fixture row provenance (every PIT fixture row; §4.1 L1274-1281, R-01 (4) L1493)
`obs_date, session_date, obs_utc, available_at_utc, available_at_source, retrieved_at_utc, value_status, vintage, content_hash` (+ `obs_kind`, `dispute`).
- `value_status` ∈ {official_close, vendor_close, live_snapshot, provisional_intraday, first_release, revised, vendor_derived, vendor_derived_across_gap} (L1280, schema L3639).
- `available_at_source` ∈ {published, calendar_bound, inferred_from_retrieval} (L3642); backfilled history is `calendar_bound`, never `inferred_from_retrieval` (L1278).
- Status assignment (L1319): `official_close` only for the KRX regular-session close field of KIS or the KRX marketplace, retrieved ≥ `close_print_bound_utc` + 10 min; a vendor daily row retrieved after that time is `vendor_close`; a backtest may read `vendor_close` only when its card header declares that vendor as `data.source` ("the §9.3 regression goldens and I-07 do; the formal R-06 KR card does not"). Vendor rows absent on a KRX session (Yahoo Saturdays before 1998-12-12; 2011-10-04) are `vendor_missing`, not disputed (L1320, L1495).

### C.3 `tests/fixtures/macro/goldens.csv` columns — B.3. `tests/macro_registry.csv` columns — B.1. Ledger seed columns — B.8.

### C.4 `tests/fixtures/macro/ACQUISITION.csv` (L6022-6033; "series · source · depth · licence · milestone · owner · md5")

| series | source | depth | needed_by | licence | owner | md5 |
|---|---|---|---|---|---|---|
| KRX official KOSPI daily closes, Saturday sessions included | KRX marketplace | from 1997-01-03 | M1 (I-16 at M7) | | | |
| KODEX 200 PDF history | KIS or KRX | as available | M5 | | | |
| French daily Mkt-RF and RF | French Data Library (DL-A: HTTP 403) | from 1926-07 | M8 (R-29 settling run) | | | |
| The ECOS code of `BOK_CALL_RATE` | BoK ECOS | from 1997 | before the M7 freeze | | | |
| `USD_LIVE_PROXY` (named, default `DX-Y.NYB`) | registry | — | M2 | | | |
| The 16:00 ET VIX / VIX3M snapshot source | vendor or KIS | — | M6 | | | |
| The hyperscaler list | company IR | — | M5 | | | |
| JPX, SSE, HKEX, TWSE, CME and Cboe calendars | official notices | effective-dated | M1 | | | |
Plus (this machine): every file of D.2 marked ABSENT, with `source = /home/claude/quantgen_macro_data/<per CATALOG.md>`.

### C.5 Config keys read (verbatim)
- `data.reject_rows_retrieved_before_close_plus_minutes: 10` (L4206); `data.fixtures: {post_close_only: true, min_minutes_after_close: 10, md5_per_file: true}` (L4213).
- `reproducibility: {seed_study: 11, seed_research_bootstrap: 20261002, record: [git_hash, config_hash, data_snapshot_id, knowledge_utc, seed, results_md5, gate_package_version, gate_package_md5, ledger_hash_at_registration, ledger_hash_at_run], determinism: {canonical_json: sorted_keys_repr_floats_no_whitespace, volatile_fields: [generated_at_utc, git_hash], rng: numpy_pcg64_seedsequence_spawned_children, blas_threads: 1, relative_tol: 1.0e-12}}` (L4680-4684; T-REPRO-01a/b/c).
- `gate.evaluation.history_start: {KR: "1997-04-01", default: first_close_of_frozen_fixture}`; `span_end: {drafted_cards: data_cutoff, later_cards: last_official_close_before_header_commit}`; `data_cutoff: {KR: "2026-10-02", US: "2026-10-01"}` (L4552-4554).
- `gate.package: {version: "2.0.0", definitions_md5: written_at_freeze, acceptance_report_md5: written_at_freeze, frozen_utc: written_at_freeze}` (L4499; L4820); `gate.step3.card_p.overlap_rule = any_overlap` (L2473).
- `source_exceptions: core/calendars/data/source_skipped.yaml` (L1902, L4229; owner-signed, versioned).
- Cost table (rulings): `core/quant/validate.COST_BP_PER_SIDE` KRX ETF 3 / KRX stock 35 / US via KIS 50 / crypto 10 / futures 5 / FX 10; every result also at 2×.

### C.6 Reference data definitions (L5712-5718) — the as-of of every fixture
Ken French daily files (Mom, ST_Rev, 5-factor 2×3, regional Mom) through 2026-08-31, and the monthly F-F factors for the 24-month market return; FRED series as downloaded on 2026-10-02 (latest vintage); Yahoo daily closes (^KS11, ^GSPC, SPY, KRW=X, ^TNX, ^RUT) through each market's last official close before the 17:20 KST freeze (KRX 2026-10-02; US 2026-10-01; KRW=X 2026-10-01); FRED NASDAQ100. "All of these are frozen in the test fixtures."

### C.7 Section 13 (L6376-6479): what binds this area
- ID conventions (L6378-6395): "R4" = `scripts/r4_golden_values.py` → `results/R4_golden_values.csv`; "R4b" = `scripts/r4b_golden_net.py` → `results/R4b_golden_values_net.csv`, verification log `scripts/r4b_verify_spec.py` → `results/R4b_verification_log.csv`; "DLA-xx"/"DLB-Txx" = Data Lab A/B runs; sources table L6461-6477 names `QX_DLA_data_lab_protective_cards.md` + `results/QX_DLA_*.csv` and `QX_DLB_data_lab_estimators_regimes.md` + `results/QX_DLB_*.csv` as the golden sources, `results/QF3_dnb_evidence_classes.csv` (`scripts/qf3_dnb_classes.py`) for §10 basis B.
- Corrected anchors N-60 (L6438-6448): KOSPI closing peak 9,114.55 on 22 Jun 2026; Q3-2026 −19.33%; KOSPI close 2 Oct 2026 7,003.74 (6,943.66 was an intraday print ≈ 10:30 KST, file written 10:56 KST); BoK base rate 3.00%; US 10y 5.29% highest close since May 2002; D&M Table 7 0.682 → 1.041 → 1.194; Ilmanen value −49%, momentum −23% (n.s.), carry ≈ −25%, multifactor −18% (tech-fund XS-05 asks to withdraw these; no golden depends on them). The evidence rows are informative "except where a §9 test or a §9.3 golden value cites them" (L89).

---

## D. Golden values, fixtures, tests

### D.1 Fixture manifest rows (L6018 "It lists every file"). Local column: ABSENT unless stated.

| Fid | File (proposed name) | Series · vendor · span | value_status / available_at_source | Tests that read it | Local |
|---|---|---|---|---|---|
| F01 | `krx_kospi_official_close_1997-01-03_2026-10-02.csv` | KRX official KOSPI closes incl. Saturday sessions < 1998-12-12; KRX marketplace / KIS | official_close / calendar_bound (print time when logged) | I-16, T-SAT-01, T-RLAYER-01, T-PRINT-01, I-01, I-11, G-POST-01 (close row) | OWNER (KRX marketplace) |
| F02 | `ecos_bok_call_rate_1997_2026-10.csv` | `BOK_CALL_RATE` daily, BoK ECOS (code: owner) | first_release / published | I-16 frozen convention, T-ROLE-02, T-EXCESS-01 (frozen clause) | OWNER |
| F03 | `kodex200_pdf_*.csv`, `kodex200_price.csv` | KODEX 200 basket (PDF) + 069500 price; KIS/KRX | official_close / measured (M1) | T-CAPS-01, G-POST-01 share row (M5) | OWNER; `yf_069500.KS` price only, to 2026-09-23 |
| F04–F06 | `kodex_inav.csv`, `krx_snapshots_1519.csv`, `krx_daily_opens.csv` | iNAV; 15:19 KST snapshots; daily opens | live_snapshot / published | T-FILL-01..03, T-BAR-01 | OWNER (KIS sessions) |
| F07 | `fred_VIXCLS_VXVCLS_2007-12-04_2026-09-30.csv` | FRED snapshot 2026-10-02 | vendor_close / calendar_bound (16:15 ET D; FRED posting lag measured) | G-R08-01/02, T-ANNOT-01, T-VIX-01, G-STALE-01 | `yf__VIX`, `yf__VIX3M` to 2026-09-25 (near substitute, smoke only) |
| F08 | `sox_daily.csv` | SOX | vendor_close | T-PLACEBO-01 positive control (Korea SOX×KRW gate); Korea covariance | ABSENT |
| F09 | `trend_indices_daily.csv` | the six trend indices: Nikkei, HSI, DAX, FTSE, TAIEX, KOSDAQ (price) | vendor_close | G-TR-04 | ABSENT |
| F10 | `french_daily_mom_1990-01-02_2026-08-31.csv`, `french_daily_strev.csv`, `french_daily_5f_2x3.csv` (Mkt-RF, RF, RMW), `french_daily_regional_mom.csv` (Japan, Europe, APxJ, Developed ex-US) | Ken French daily through 2026-08-31 | vendor_derived / published | G-MOM-01..08, G-BOOK-01, G-INTL-01, G-YRS-01, G-DSR-02, T-R03-01, T-SE-01, G-US-01 (Mkt-RF), U1 | ABSENT |
| F11 | `french_monthly_ff_1926-07_2026-08.csv` | monthly F-F factors (24-month market return; R-28 monthly 1927–2026 with RF) | published | R-04 (G-MOM-03/04/05 bear state), G-TR-01..03, T-TREND-02 | ABSENT |
| F12 | `french_daily_mktrf_rf_1926-07_2026-08.csv` | daily Mkt-RF and RF from 1926-07 (DL-A: HTTP 403) | published | T-USFUT-02 (R-29 settling run) | NOT ACQUIRED (M8, TASK-M8-11) |
| F13 | `yahoo_KS11_1996-12_2026-10-02.csv` | Yahoo ^KS11 daily close | vendor_close / calendar_bound; vendor_missing Saturdays < 1998-12-12 and 2011-10-04 | G-KR-01..06, G-KR-L01..13, G-B5-01, G-B5-04, G-EST-01..04, G-LAD-01..03, G-REF-01, G-PWR-01/02, G-R08-02, G-TR-05, G-POST-01, T-VT-01, T-LABEL-01, T-COST-01, I-02, I-07, T-STEP-02, T-PLACEBO-01, T-ES-02, T-EPIS-01/02, T-TROUGH-01, T-BOOK-02 | ABSENT |
| F14 | `yahoo_GSPC_1990_2026-10-01.csv` (+ OHLC for R-30 open-quality) | Yahoo ^GSPC | vendor_close / calendar_bound | U1 splice (Sep-2026), G-EST-01..03 (US), G-TR-04 (S&P), T-CORR-01, T-TZ-01 | ABSENT |
| F15 | `yahoo_SPY_2015-12_2026-10-01.csv` | Yahoo SPY | vendor_close | G-B5-02 | `yf_SPY` to 2026-09-24 valid (09-25 row intraday) |
| F16 | `yahoo_KRWX_2004_2026-10-01.csv` | Yahoo KRW=X; provisional 2-Oct row dropped | vendor_close | G-POST-01 KRW=X row, G-REF-01 row 4 | ABSENT |
| F17 | `yahoo_TNX_2015_2026-10-01.csv`, `yahoo_RUT_2015_2026-10-01.csv` | ^TNX (live-feed proxy), ^RUT | vendor_close | G-US-03, G-REF-02 row 4, G-US-04 | ABSENT |
| F18 | `fred_snapshot_2026-10-02/<id>.csv` | DGS10, DEXKOUS (from 1997-04), DTWEXBGS (from 2016-01), NASDAQ100 (2008→), DTB3, DEXJPUS, PCEPILFE/PCEPI/CPIAUCSL/CPILFESL with ALFRED vintages, UNRATE, SAHMREALTIME, THREEFYTP10, BAMLH0A0HYM2, BAA10Y, DCOILBRENTEU, USEPUINDXD | first_release / revised; calendar_bound per H.15/H.10/BLS rule | G-US-02/02a/02s/03/04, G-REF-02, G-STALE-01, T-H15-01, T-H10-02, T-CORR-01, T-HEDGE-01, T-MISS-01, §11 | `fred_DEXKOUS` 2017→2026-09-18 partial; `fred_DGS3MO` (not DTB3) |
| F19 | `px2_cash_IRSTCI01KRM156N_monthly.csv` | FRED `IRSTCI01KRM156N`, monthly, ÷ 252, used from the month after; produced by `scripts/qx_px2_02_vt_assetpricing.py` | published | T-EXCESS-01, I-09 | ABSENT |
| F20 | `QX_DLA_postpatch.csv` | DL-A §7 post-patch values | result table | G-POST-01, T-FIX-01 | ABSENT |
| F21 | `QX_DLA_korea_grid.csv` | DL-A Korea grid | result table | G-KR-L01..13, I-07, ledger_seed_R-06 | ABSENT |
| F22 | `QX_EX1_qf3_trial_corr_diff.csv` | QF3's 26-trial difference-series correlation matrix (seed 11) | result table | T-NEFF-01, ledger_seed_R-03 | ABSENT |
| F23 | `QX_DLB_r03_dsr.csv`, `QX_DLB_r03_years.csv`, `QX_DLB_trend_cards.csv`, `QX_DLB_power_se.csv`, `QX_DLB_power_sim.csv`, `QX_DLB_r08.csv` (+ the DLB estimator CSVs) | DL-B results | result tables | G-DSR-02, G-YRS-01, G-TR-01..05, G-PWR-01/02, G-R08-01/02, G-EST-01..04, ledger_seed_R-28 | ABSENT |
| F24 | `QX_DLA_ladder.csv` | DL-A ladder | result table | G-LAD-01..03, ledger_seed_R-31 (EX1 L1–L6) | ABSENT |
| F25 | `core/calendars/data/source_skipped.yaml` | source-skipped dates (owner-signed) | — | T-STALE-01 (a)(b), G-STALE-01 | OWNER |
| F26 | `pit_store_T-PROV-01.json` (synthetic; `exempt_post_close = true`) | vendor row 6,943.66: obs_utc 01:30Z, available_at_utc 01:30Z, retrieved_at_utc 01:56Z, provisional_intraday; KIS row 7,003.74: available_at_utc 06:30:30Z (calendar_bound), retrieved_at_utc 06:40:45Z, official_close (L5612) | synthetic | T-PROV-01, T-CLOSE-01, I-01 gates | SYNTH |
| F27 | `krx_005930_000660_closes_mcap.csv` | Samsung, SK hynix closes and market caps (KIS/KRX; Yahoo secondary, split-adjusted → `adjustment_basis`) | official_close | G-POST-01 rows (₩276,000 / ₩1,841,000; 53.6%), T-FILL-02 (SK hynix 2026-07-31 +29.95%) | `yf_005930.KS` to 2026-09-23 only; 000660 ABSENT |
| F28 | `treasury_par_yield_daily_posting_times.csv` | US Treasury CMT with logged posting time | published | G-US-02a, G-REF-02 row 2, T-H15-01 | ABSENT |
| F29 | `ledger_seed_R-03.csv`, `ledger_seed_R-06.csv`, `ledger_seed_R-28.csv`, `ledger_seed_R-31.csv` | B.8 | — | T-NEFF-01, T-SEL-01, T-LEDGER-01, `definitions_md5` | built from F10/F13/F21-F24 (ABSENT) |
| F30 | `bldp_dsr_example.json` | BLdP worked-example inputs: delta_SR = 2.5 ⁄ √250, T 1,250, SE_obs = √((1 + 3·SR + 9⁄4·SR²) ⁄ (T − 1)), SE_null·hurdle = √(0.5 ⁄ 250)·e(N) (L2522) | synthetic | T-DSR-01, G-DSR-01 | SYNTH (reproduces) |
| U1 | alias: French Mkt-RF 1990-02-01 → 2026-08 + ^GSPC Sep-2026 (F10 + F14) | "fixture `U1`, 1990–2026" (L2254) | — | G-US-01/01b/01c, G-US-F01..10, T-GATE-02, T-USFUT-05, T-POWER-01, G-PWR-01/02, T-TREND-02 (+14.9 pp line) | ABSENT |

### D.2 Golden value table (values verbatim; tolerance kinds per B.3; `rf` = runs_from; mode v12 = v1.2-check, ref = reference_only; Local = can it be recomputed here)

**G-POST-01 post-patch rows (L5815-5840; DLA §7 `QX_DLA_postpatch.csv`; read by T-FIX-01 / G-POST-01; rf per §9.0b L5572-5577)**

| Row | Pre-patch | Golden (post-patch) | rf | Fixture | Local |
|---|---|---|---|---|---|
| KOSPI close, 2 Oct | 6,943.66 (intraday print) | **7,003.74** (price, exact) | M1 | F01/F13, F20 | ABSENT |
| KOSPI return, 2 Oct | −0.40% | **+0.46%** | M1 | F13 | ABSENT |
| Drawdown from the 9,114.55 peak | −23.8% | **−23.2%** (−23.16%) | M1 | F13 | ARITH from the two closes |
| Close / 200-day average | 1.098 | **1.107** | M1 | F13 | ABSENT |
| Samsung / SK hynix close | ₩273,750 / ₩1,832,000 | **₩276,000 / ₩1,841,000** | M1 | F27 | ABSENT |
| KRW=X last row; 20-observation change | 1,360.63 (2 Oct); +0.38% | **1,356.84 (1 Oct); −0.11%** (provisional 2-Oct row dropped) | M1 | F16 | ABSENT |
| rv20 (SMA20) | 28.9% | **28.8%** (28.82%) | M2 | F13 | ABSENT |
| vt decided at the 2-Oct close | 0.691 | **0.694** | M2 | F13 | ARITH from rv20 |
| G-KR-01 buy-and-hold Sharpe (MDD unchanged) | 0.634 | **0.637** | M2 | F13 | ABSENT |
| G-KR-02 VT20 Sharpe gross / 3 / 35 / 6 / 70 bp (MDD unchanged) | 0.638 / 0.635 / 0.605 / 0.632 / 0.573 | **0.641 / 0.638 / 0.609 / 0.635 / 0.576** | M2 | F13 | ABSENT |
| G-KR-02b at 35 bp | −0.028 (0.37) | **−0.029 (0.36)** | M2 | F13 | ABSENT |
| G-B5-01 KOSPI SMA20 FHS PIT p (exceedance 4.70% unchanged) | 0.12 | **0.11** (0.107) | M3 | F13 | ABSENT |
| Samsung + SK hynix implied share (B3a anchor) | ≈ 53.7% | **≈ 53.6%** (Samsung 29.8% + hynix 23.8%) | M5 | F03, F27 | ABSENT |
| R-06 KR 3 bp: p_ni at 10-session / PW blocks | 0.24 / 0.21 | **0.25** (0.246) / 0.21 (0.208) | M7 after freeze (v12) | F13 | ABSENT |
| R-06 KR 35 bp: ΔSR | −0.028 | **−0.029** (p_ni 0.32 / 0.29 unchanged) | M7 after freeze (v12) | F13 | ABSENT |
| G-KR-05 KRW value timing (share) | +0.032 (0.965) | +0.032 (**0.967**) | M8 | F13, F18 DEXKOUS | ABSENT |
| Unchanged at printed precision (L5836-5840) | — | weights 22 Jun / 23 Jun / 30 Jul 2026 0.30 / 0.33 / 0.25 and 2 Oct 0.61 (M2); label "elevated" (quartiles 15.7 / 18.55 / 33.6%; 70th percentile) and rv21 31.9% at the 73rd percentile (M2); turnover 1.50 (M2); G-KR-02c, G-KR-02b gross and at 3 bp (M2); G-KR-05s and G-KR-05 on VT20 (M8) | | F13 | ABSENT |

**§9.3.1 regression goldens (v1.2 conventions; mode v12; timing flags verbatim)**

| ID (L) | Quantity | Golden values (gross / net) | Series · span | Fixture | Test · rf | Local |
|---|---|---|---|---|---|---|
| G-MOM-01 (L5748) | Static Mom: Sharpe / max DD | 0.399 / −63.3%; net same (no overlay turnover) | French Mom daily 1990-01-02 → 2026-08-31; net 50 bp per side both legs | F10 | T-R03-01 · M4 | ABSENT |
| G-MOM-02 (L5749) | R-03 vol scale (σ126, 12%, cap 1): Sharpe / max DD / avg weight / % days at cap | **0.714** / −27.9% / 0.870 / 60.6%; net 1× 0.672 / −28.7%; net 2× 0.631 / −29.4% | same | F10 | T-R03-01 · M4 | ABSENT |
| G-MOM-03 (L5750) | R-03 × R-04 (DM 0.5): Sharpe / max DD / vol-matched max DD | **0.798** / −20.9% / −30.5%; net 1× 0.745 / −21.6%; net 2× 0.691 / −22.7% | + F11 24-month market return | F10, F11 | TASK-M4-04 · M4 (specification book) | ABSENT |
| G-MOM-04 (L5751) | DM add-on over R-03: full / ex Sep-2008–Dec-2009 / 2013-04 → 2026-08 / 2020–26 | +0.084 (0.996) / +0.056 (0.97) / +0.055 (0.94) / +0.101 (0.93); net 1× full +0.072 (0.983), 2013-04+ +0.044 (0.92), 2020–26 +0.080 (0.91); net 2× full +0.061 (0.958) | shares: research bootstrap | F10, F11 | M4 | ABSENT |
| G-MOM-05 (L5752) | DM gate: % of days on / spell onsets / transitions a year | 10.6% / 7 / 0.38 | counts exact | F11 | M4 | ABSENT |
| G-MOM-06 (L5753) | Episodes, static → spec stack (gross) | Apr-2009 −26.8% → −4.2%; Mar–May 2009 −45.6% → −8.0%; Jan-2001 −21.9% → −15.7%; Nov-2020 −12.0% → −3.9%; Jan-2023 −13.7% → −3.8%; Jul-2026 −10.9% → −5.9%; calendar 2020 −11.0% → +3.1%; calendar 2022 +17.4% → +12.3%; May–Nov 2008 +21.8% → +9.5% | window returns | F10, F11 | TASK-M4-07 · M4 | ABSENT |
| G-MOM-07 (L5754) | Reference (`reference_only`) | Vol scale cap 2: 0.907; DM 0×: 0.657 | — | F10, F11 | M4 (ref) | ABSENT |
| G-MOM-08 (L5755) | R-03 card statistics (vs unscaled, 50 bp) | net 1×: ΔSR +0.273 (share 1.00); one-sided p 0.0005 (10-session) / 0.000 (251-session PW) → assert `< 1/B`; 70% of years positive; net 2× ΔSR +0.231 (0.998) | gate-style §8.5 | F10 | T-R03-01 · M4 | ABSENT |
| G-BOOK-01 (L5756) | (Mom + ST_Rev + RMW)/3: static → spec | 1.358 → **1.753**; 2020–26 0.400 → 0.618. ST_Rev static 1.253; RMW static 0.480. Net not recomputed | F10 | F10 | M4 | ABSENT |
| G-INTL-01 (L5762) | Vol scale cap 1, 12% (full sample from 127 days after start) | Japan 0.073 → 0.196; Europe 0.843 → 1.143; APxJ 0.924 → 1.125 (2016–26: 0.921 → 0.897); Developed ex-US 0.799 → 0.996; net not computed | French regional WML daily | F10 | M4 | ABSENT |
| G-KR-01 (L5770) | Buy-and-hold: Sharpe / max DD | 0.637 / −43.9% (uncosted, same at every cost) | ^KS11 2016-01-04 → 2026-10-02 | F13 | TASK-M2-08 · M2 | ABSENT; cross-check `r2_idx_golden_values.csv` 0.6284 / −0.4405 (pre-patch basis) |
| G-KR-02 (L5771) | R-06 vol target (SMA20, 20%, cap 1): Sharpe / max DD | **0.641** / −36.8%; 2016–25: 0.457 vs 0.534; 2018–24: −0.052 vs 0.071; ETF 3 bp 0.638 / −36.8%; stock 35 bp **0.609** / −37.2%, 2016–25 0.428, 2018–24 −0.083; 2× (6 / 70 bp) 0.635 / −36.9%; 0.576 / −37.5% | same | F13 | M2; T-COST-01 (0.609 ± 0.01) | ABSENT; cross-check 0.6329 gross, 0.6301 at 3 bp |
| G-KR-02b (L5772) | R-06 ΔSR vs buy-and-hold (share): 2016–26 / 2016–25 / 2018–24 | +0.004 (0.45) / −0.077 (0.06) / −0.123 (0.03); 3 bp +0.001 (0.44) / −0.079 (0.05) / −0.125 (0.03); 35 bp −0.029 (0.36) / −0.106 (0.02) / −0.154 (0.01); 2×: −0.001 / −0.061 (0.28) at 70 bp (−0.061: **pre-patch R4b**) | research bootstrap | F13 | M2 (−0.061 pending §9.4 item 2) | ABSENT |
| G-KR-02c (L5773) | Static book with VT20's average exposure (0.925): max DD; ΔMDD of VT20 vs it | −41.3%; +4.5 pp; 3 bp +4.4 pp; 35 bp +4.1 pp; 2× +4.4 / +3.8 pp | S per L5187 | F13 | M2 | ABSENT; cross-check −0.4145, +4.46 / +4.43 |
| G-KR-03 (L5774) | R-06 windows (vt vs buy-and-hold) | Jul-2026 crash −12.2% vs −38.6%; Mar-2026 −7.9% vs −19.9%; Aug-2024 −7.9% vs −5.5%; Apr-2025 −11.7% vs −12.0%; 2020 crash −25.8% vs −34.1%; 2020 rebound +25.9% vs +49.9%; H1-2026 +51.7% vs +101.1%; 30 Jul → 30 Sep 2026 +5.9% vs +22.2%; 3 bp: Jul-2026 −12.3%; Mar-2026 −7.9%; Aug-2024 −7.9%; 2020 crash −25.8%; H1-2026 +51.6%; 35 bp: Jul-2026 −12.3%; Mar-2026 −8.0%; Aug-2024 −8.0%; Apr-2025 −11.8%; 2020 crash −26.0%; 2020 rebound +25.4%; H1-2026 +50.5%; post-crash +5.6% | §8.6 return dates (B.4) | F13 | M2; I-02 | ABSENT; cross-check `r2_idx_golden_values.csv` rows 13-28 |
| G-KR-04 (L5775) | R-06 weights | 22 Jun 2026 0.30; 23 Jun 0.33; 30 Jul 0.25; earning on 2 Oct 0.61; decided at the 2 Oct close for the next session 0.69 (0.694; rv20 28.8%); same at every cost | earning-on convention (B.4) | F13 | M2; I-02; I-01 (vt 0.25 on 2026-07-30) | ABSENT |
| G-KR-05 (L5776) | S1 KRW 0.75× (DEXKOUS, D ≤ K−1): ΔSR vs buy-and-hold / on VT20 / % days on | +0.032 (0.967) / +0.042 (0.977) / 9.0%; 3 bp +0.029 (0.94) / +0.038 (0.96); 35 bp **−0.008 (0.32)** / −0.007 (0.34); 2×: +0.025 / +0.034 at 6 bp; −0.048 / −0.057 at 70 bp; **VALUE** (H.10 publication ignored) | ^KS11 + DEXKOUS | F13, F18 | TASK-M8-12 · M8 (refusal book, display) | ABSENT |
| G-KR-05s (L5777) | S1 strict H.10 publication: ΔSR vs b&h / on VT20 / % days on / onsets (20-session) | **+0.001 (0.53)** / +0.013 (0.74) / 9.1% / 26; 3 bp −0.000 (0.49) / +0.012 (0.70); 35 bp −0.016 (0.22) / −0.007 (0.34); 2×: −0.002 / +0.010 at 6 bp; −0.034 / −0.027 at 70 bp; COMPLIANT | H.10 rule (T-H10-02) | F13, F18 | M8 | ABSENT |
| G-KR-06 (L5778) | Reference vol target cap 1.5 (prohibited; `reference_only`) | Sharpe 0.534; max DD −46.2% (**pre-patch R4**; not recomputed on the official close) | ^KS11 | F13 | M2 (ref) only once §9.4 item 2 is md5-frozen (L5552) | ABSENT |
| G-US-01 (L5786) | Buy-and-hold vs R-06 (SMA20, 15%, cap 1): Sharpe / max DD | 0.534 / −59.2% vs **0.602** / −49.9%; 50 bp VT15 **0.505** / −53.8%, ΔSR −0.028 (0.29); 100 bp 0.409 / −57.3%, ΔSR −0.125 (0.03) | U1 1990-02-01 → 2026-09-30 | U1 | M2; T-COST-01 (0.505 ± 0.01) | ABSENT |
| G-US-01b (L5787) | Static book with VT15's average exposure (0.890): max DD; ΔMDD | −54.0%; +4.1 pp; 50 bp +0.2 pp; 100 bp −3.4 pp | U1 | U1 | M2 | ABSENT |
| G-US-01c (L5788) | Challenger EWMA(0.94), same target: Sharpe | 0.605; 50 bp 0.520; 100 bp 0.434 | U1 | U1 | M2; EWMA clause from M3 ("R-30 builds `ewma094`", L5593) | ABSENT |
| G-US-02 (L5789) | S2 rates 0.5×, value timing: ΔSR vs b&h / on VT15 / % days on / onsets (60-session) | +0.038 (0.98) / +0.037 (0.97) / 6.2% / 50; 50 bp −0.065 (0.00) / —; 100 bp −0.168; **NON-COMPLIANT** (DGS10(D) at the close of D) | U1 + DGS10 | U1, F18 | M8 (R-12 refusal book; T-REF-02) | ABSENT |
| G-US-02a (L5790) | S2 at +1 business day (v1.0 "strict") | +0.010 (0.67); 1990–2007 −0.017; 50 bp −0.093 (0.00); 100 bp −0.196; COMPLIANT via the Treasury par-yield channel with a logged posting time; NON-COMPLIANT via H.15/FRED by 15 minutes | + F28 | U1, F18, F28 | M8; T-REF-02 reads "compliant via Treasury with logged posting time" | ABSENT |
| G-US-02s (L5791) | S2 strict H.15 (+2 business days): ΔSR vs b&h / on VT15 / 1990–2007 / 2008–26 / 2020–26 | **−0.000 (0.53)** / −0.007 (0.39) / −0.034 / +0.025 (0.77) / +0.084 (0.92); 50 bp **−0.103 (0.00)** / −0.120 (0.00); 100 bp −0.206 / −0.233; COMPLIANT | H.15 rule (T-H15-01) | U1, F18 | M8 | ABSENT |
| G-US-03 (L5792) | S2, 2015–26 by timing | DGS10 +0.066 (NON-COMPLIANT); ^TNX +0.071 (VALUE); +1 day +0.071; **+2 business days +0.053 (0.90)** (COMPLIANT); 50 bp ^TNX −0.020 (0.31), +2 bd −0.032 (0.20); 100 bp ^TNX −0.111, +2 bd −0.118 | + ^TNX | U1, F17, F18 | M8 | ABSENT |
| G-US-04 (L5793) | S2 duration proxies (value timing) | NDX 2008–26 +0.039 (0.94); Russell 2000 2015–26 +0.058 (0.97); small-cap proxy 1990–26 +0.025 (0.89); net not recomputed; NON-COMPLIANT | NASDAQ100, ^RUT | F17, F18 | M8 | ABSENT |
| G-B5-01 (L5801) | KOSPI 2016-03 → 2026-10 (2,594 origins; band 4.14–5.86%) | SMA20 4.70%, PIT p 0.11 → **PASS**; normal form 6.75%, PIT p < 0.001 → FAIL; every-7th-session subsample 7.55% (371 origins; band 2.74–7.26%) → outside; EWMA(0.94) 4.90%, PIT p 0.03 → **PASS**; GARCH(1,1)-t refit 7 / window 504 (informational): t-quantile 6.92% → FAIL; FHS 5.42% → PASS (2,123 origins) | ^KS11 | F13 | T-B5-01 (4.70% ± 0.3 pp; PIT p 0.11) · M3 | ABSENT |
| G-B5-02 (L5802) | SPY 2016-03 → 2026-10 (2,663 origins; band 4.16–5.84%) | SMA20 4.99%, PIT p 0.57 → PASS; EWMA 5.22%, PIT p 0.79 → PASS; GARCH t-quantile 6.33%, PIT p < 0.001 → FAIL (the app's own study: 6.6%, PIT p 0.003, REJECT) | SPY | F15 | M3 | `yf_SPY` smoke (4 origins short) |
| G-B5-03 (L5803) | US market 1991-03 → 2026-10 (8,961 origins; band 4.54–5.46%) | SMA20 5.31%, PIT p 0.98 → PASS; EWMA 5.31%, PIT p 0.93 → PASS; GARCH not run | U1 | U1 | M3 | ABSENT |
| G-B5-04 (L5804) | Display labels on 2 Oct 2026 | Relative (trailing 756): KOSPI **elevated** (σ̂ 28.8%; quartiles 15.7 / 18.6 / 33.6%; 70th percentile); US **normal** (10.7%; 10.5 / 12.7 / 15.2%; 28th percentile). Absolute (expanding): KOSPI **stressed** | ^KS11, U1 | F13, U1 | T-LABEL-01 · M3 (labels also M2 per T-LABEL-01) | ABSENT |
| §11 current state (L6286-6352) | sanity values at Level 1 | e.g. US Mom σ126 23.9% (2026-08-31) → vs = 0.50; US 24-month market return +39.7% → D&M bear state OFF, Mkt vol126 14.3% vs 2/3 quantile 17.4%; S&P 7,666.45 (2026-10-01), 1.062 × 200-day, rv20 10.7% → vt_US 1.00; concentration bounds 22.5 / 29.8 = **0.755**, 0.05 / (0.298 − 0.225) = **0.685**, gross min(0.694, 0.755, 0.685) = 0.685 (ARITH); corr63 +0.53 / corr252 +0.33 (2026-09-30); core PCE 3.01%; VIX/VIX3M 16.34 / 18.37 (2026-09-30); CPI YoY 3.35% (3.71% wrong lag, a test value) | per row | F10, F13, U1, F18, F03 | M2–M6 | bounds ARITH; rest ABSENT |

**§9.3.2 new goldens (DL-A / DL-B; "indicative computations under the v1.2 checks on local reference data (Yahoo ^KS11 price, Korea cash 0; French Mkt-RF for the US)" L5812; Level 1 in v12 mode; refused configurations in ref mode)**

| ID (L) | Case | Golden values | Fixture | Test · rf | Local |
|---|---|---|---|---|---|
| G-KR-L01 (L5846) | 1997-04 → 2026-10, ETF 3 bp (definitive cell); columns ΔMDD vs S (2×) · tail · ΔSR (2×) · p_ni (10 / PW) · episodes +/n (max share) · years · plateau | +12.7 (+12.5) · 0.68 · +0.026 (+0.021) · 0.052 / 0.029 (PW block 183) · 4/11 (0.493) · 0.70 · 0.875; B5 5.04%, PIT p 0.46 → PASS (fragile); Bonferroni factor 1 | F13, F21 | I-07 (L01..L08 Level 1) · M7 after freeze; I-16 data check at Level 2 on F01 | ABSENT; tech-fund analogue 1996-09-02 start: +6.5 (+6.4) · 0.70 · −0.001 · 0.051 (block 186) · 0.70 · 1.00 PASS (`r2_idx_protective_scorecard.csv` row 5) — not comparable, informative |
| G-KR-L02 (L5847) | 1997-04 → 2026-10, futures 5 bp | +12.6 (+12.3) · 0.68 · +0.023 (+0.015) · 0.055 / 0.030 · 4/11 (0.493) · 0.70 · 0.875 → PASS | F13, F21 | I-07 · M7 | ABSENT |
| G-KR-L03 (L5848) | stock 35 bp (reference line; not admissible) | +10.9 (+8.3) · 0.68 · −0.020 (−0.071) · 0.141 / 0.129 · 4/11 (0.503) · 0.70 · 0.625 → INSUFFICIENT | F13, F21 | I-07 · M7 | ABSENT |
| G-KR-L04 (L5849) | 1998-01 → 2026-10 | +3.8 (+3.7) · 0.70 · +0.001 (−0.003) · 0.082 / 0.055 · 4/11 (0.492) · 0.72 · 0.625 → PASS (thin) | F13, F21 | I-07 · M7 | ABSENT |
| G-KR-L05 (L5850) | 2002-01 → 2026-10 | +11.0 (+10.8) · 0.82 · +0.030 (+0.026) · 0.038 / 0.010 · 5/11 (0.466) · 0.72 · 1.000 → PASS | F13, F21 | I-07 · M7 | ABSENT |
| G-KR-L06 (L5851) | 1997-04 → 2015-12 | +10.6 · 0.68 · +0.025 · 0.086 · 1/3 (GFC) · 0.68 · 0.75 → INSUFFICIENT (sufficiency: 3 §8.6 windows) | F13, F21 | I-07 · M7 | ABSENT |
| G-KR-L07 (L5852) | 2016-01 → 2025-12 | +5.7 · 0.95 · −0.079 · 0.400 · 1/7 · 0.70 · 0.25 → REJECT (PC-2, PC-4) | F13, F21 | I-07 · M7 | ABSENT |
| G-KR-L08 (L5853) | 2016-01 → 2026-10 | +4.4 · 0.82 · +0.001 · 0.246 · 3/9 (0.59) · 0.73 · 0.625 → INSUFFICIENT | F13, F21 | I-07 · M7 | ABSENT; cross-check `r2_idx_r4b_crosscheck.csv` (R4b: +4.4 / +4.4, 0.82, +0.001, PW block 101, p 0.21 / 0.24, 3 of 9, 0.59, 0.73, 0.63, INSUFFICIENT DATA (inconclusive)) |
| G-KR-L09 (L5854) | Episode-set sensitivity, definitive cell | §8.6 + Sep-2026: 5/12 (max 0.490); objective bear-20: **14/18 (max 0.174)**; 10 of the 12 pre-2008 bears positive (1997-H2 +14.5 pp, 1998-H1 +19.9 pp, 2000 +10.2 and +7.9 pp) | F13 | T-EPIS-02, I-09 (0.174 ± 0.01; 0.493 printed) · M7 after | ABSENT |
| G-KR-L10 (L5855) | Start sweep, monthly starts 1997-02 → 2003-01 | 71 of 72 PASS; 1998-10 start (p_ni 0.103) asserted as PASS or INSUFFICIENT → count 71–72; ΔMDD +3.7 to +12.7 pp | F13, F21 | M7 (class) | ABSENT |
| G-KR-L11 (L5856) | Episode benefits vs S, definitive cell (pp) | GFC +9.1; 2011 −0.6; 2015–16 −1.3; 2018Q4 −1.6; 2020 crash +3.9; 2022 −3.8; Aug-2024 −3.3; Dec-2024 −0.8; Apr-2025 −1.4; Mar-2026 +9.0; Jul-2026 +21.4. Cost episodes (not gated): 2009 rebound −6.9; 2020 rebound −15.5; H1-2026 −31.5; 30 Jul → 30 Sep 2026 −13.2 | F13 | T-TROUGH-01 · M7 after | ABSENT |
| G-KR-L12 (L5857) | Tail and other metrics, 1997–2026 | ΔES99 +1.95 pp (z 4.3); ΔES95 of 21-day returns +2.9 pp (z 2.3); ΔCDaR95 +7.1 pp (z 1.26); bootstrap SD of ΔSR 0.066, 90% CI [−0.082, +0.131]; CVaR(5%) −2.64% vs −3.58% for S; mean multiplier on the worst 1% of days ÷ overall 0.54, on the 10 worst days 0.46; longest time under water 1,492 vs 1,478 sessions; median re-entry lag 17 sessions; PSR vs S 0.55; DSR vs 0: 0.99 / 0.81 / 0.63 at N 1 / 10 / 34 | F13 | T-ES-02 (points ±0.2 pp; z ref mode only) · M7 after | ABSENT |
| G-KR-L13 (L5858) | Variants of the definitive cell | Target 0.15 / 0.25: +16.5 / +8.9 pp, INSUFFICIENT / INSUFFICIENT. EWMA(0.94): +12.4 pp, p_ni 0.070, PC-4 0.51 → INSUFFICIENT. Cap 1.5 (prohibited, ref): +20.5 pp → INSUFFICIENT. 0.10 band / monthly at 3 bp: +12.6 / +8.0 pp → INSUFFICIENT (PC-4). Own expanding-median target: −3.4 pp → REJECT (PC-1) | F13, F21 | M7 (cap 1.5 ref) | ABSENT |
| G-US-F01 (L5864) | 1990–2026 daily, US shares via KIS 50 bp (registered card) | +0.2 (−3.4) · 0.79 · −0.028 · 0.146 · 6/11 (0.49) · plateau 0.375 → REJECT (PC-1) | U1 | TASK-M7-22 (v12) · M7; T-GATE-02 (v2: INSUFFICIENT class; ES21 +1.65 pp, ES126 +3.8 pp ± 0.2 pp; 2× ΔSR −0.125; p_ni printed, 0.146 is R4b's percentile `gate_boot`) | ABSENT; tech-fund SPY 1999-05-03..2021-03-31 analogue +0.3 / −3.9 REJECT (informative) |
| G-US-F02 (L5865) | futures 5 bp (R-29) | +3.6 (+3.2) · 0.79 · +0.058 · 0.002 · 6/11 (0.46) · 0.875 → PASS | U1 | T-USFUT-05 · M8; M7 v12 | ABSENT |
| G-US-F03 (L5866) | KRX S&P ETF proxy 3 bp (cost bucket) | +3.8 (+3.6) · 0.79 · +0.062 · 0.002 · 6/11 (0.46) · 0.875 → PASS | U1 | M7 | ABSENT |
| G-US-F04 (L5867) | monthly, 50 / 5 / 3 bp | +7.6 / +9.3 / +9.4 · 0.81 · +0.045 / +0.078 / +0.079 · ≤ 0.002 · 8/11 (0.58 / 0.56 / 0.56) · 1.0 → INSUFFICIENT (PC-4, GFC) | U1 | M7 | ABSENT |
| G-US-F05 (L5868) | band 0.10, 50 / 5 / 3 bp | +1.8 / +3.7 / +3.8 · 0.81 · +0.017 / +0.059 / +0.061 · 0.023 / 0.002 / 0.002 → REJECT / PASS / PASS | U1 | M7 | ABSENT |
| G-US-F06 (L5869) | 1995–2026 daily, 5 bp / 3 bp | +2.9 / +3.1 (2×: +2.9) · 0.78 · +0.058 / +0.063 · 0.007 → REJECT (PC-1) / REVISE (2×) | U1 | M7 | ABSENT |
| G-US-F07 (L5870) | 1990–2007 / 2008–2026 daily, 5 bp | +0.3 (0 §8.6 episodes) / +17.5 → INSUFFICIENT (sufficiency) / PASS | U1 | M7 | ABSENT |
| G-US-F08 (L5871) | Start sweep, 44 quarterly starts 1990-02 → 2000-11, futures 5 bp | 11 PASS (1990-02 to 1992-05, and 2000-11) / 9 REVISE (1992-08 to 1994-08) / 24 REJECT (1994-11 to 2000-08); near-threshold starts as classes, counts as ranges | U1 | T-USFUT-05 · M8 | ABSENT |
| G-US-F09 (L5872) | ES metrics, 1990–2026, 250-session blocks | Daily 50 bp: ΔES99 +1.1 pp (z 2.37, P 1.00); ΔES95 of 21-day +1.7 pp (z 1.85, P 0.99); ΔCDaR95 −4.7 pp; ΔMDD bootstrap SD 7.8 pp. Daily 5 bp: ΔES99 z 2.38; ΔES95 (21-day) z 2.05. Monthly 5 bp: ΔMDD +9.3 pp (z 1.42); ΔCDaR95 +6.1 pp; ΔES99 z 1.86 | U1 | M7 (z print-only vs R-21 z) | ABSENT |
| G-US-F10 (L5873) | Estimator choice, 1995–2026 (DLB-T1h) | 50 bp: every estimator REJECT or INSUFFICIENT (SMA20 ΔMDD −0.8 pp). 5 bp: SMA20 +2.5 pp (REJECT); GARCH +4.9, log-HAR +4.8, COMB +3.9 pp (PASS) | U1 | M7 | ABSENT |
| G-REF-01 (L5879-5882) | R-11 refusal record, KOSPI 1997-04 → 2026-10, 0.75× on VT20: timing · onsets (de-clustered at 20) · ETF 3 bp ΔMDD / tail / ΔSR · stock 35 bp ΔMDD / ΔSR · verdict | Value (DEXKOUS D ≤ K−1): 74 · −1.7 / 0.996 / −0.015 · −1.7 / −0.048 · REJECT (PC-1, PC-2); Strict H.10: 54 · −1.3 / 1.004 / −0.022 · −1.4 / −0.036 · REJECT; Strict H.10 holiday-aware: 54 · −1.3 / 1.004 / −0.027 · −1.5 / −0.041 · REJECT; Yahoo KRW=X lagged 2 sessions (2004+): 69 · +0.3 / 0.996 / −0.006 · −0.4 / −0.059 · REJECT | F13, F18, F16 | T-REF-01 (54 strict-H.10 onsets, ΔMDD −1.3 pp, tail 1.00) · M8 | ABSENT |
| G-REF-02 (L5888-5891) | R-12 refusal record, US 1990-02 → 2026-09, 0.5× on VT15; 71 onsets at every timing (39 in 1990–2007, 32 in 2008–26): timing · status · 50 bp ΔMDD / ΔSR · 5 bp · gross · tail · verdict | Value (DGS10(D) at close D): NON-COMPLIANT · −0.8 / −0.076 · +1.1 / +0.026 · +1.2 / +0.037 · 0.99 · REJECT; +1 bd via Treasury: COMPLIANT via Treasury · −3.1 / −0.105 · +0.1 / −0.002 · +0.3 / +0.009 · 0.99 · REJECT (also PC-4 2/11); +2 bd strict H.15: COMPLIANT · −3.5 / −0.120 · +0.8 / −0.019 · +0.9 / −0.007 · 0.995 · REJECT; ^TNX close of D: VALUE · −1.5 / −0.090 · +1.4 / +0.016 · +1.5 / +0.027 · 0.99 · REJECT | U1, F18, F28, F17 | T-REF-02 (71 onsets; −3.1 pp at 50 bp; −3.5 pp) · M8 | ABSENT |
| G-LAD-01 (L5897) | Literal v1.2 rule (I-04b counter-example; ref) | KOSPI, b&h or VT20: permanently HALTED from 1997-10-17 under the cumulative reading (average exposure 1.3%; 714 halt cycles), from 1997-09-30 under the non-cumulative one (1.3%; 715 cycles). US, b&h or VT15: from 2000-10-13 (20–22%; 653 cycles) / from 1990-09-25 or -28 (1.1%; 907 cycles); KOSPI 3 bp from 1997-04-15; US 5 bp from 1990-04-02 | F13, U1, F24 | TASK-M5-13 (ref) · M5; I-04b | ABSENT |
| G-LAD-02 (L5898) | QF4's fix, 11-session halt (ref) | KOSPI VT20: Sharpe 0.532, max DD −42.0%, days reduced 52%, 16 HALTs, ΔSR vs no ladder +0.078, ΔMDD vs S +3.9 pp. KOSPI b&h: 0.453, −50.9%, 52%, 31, +0.025, +0.4 pp. US VT15: 0.522, −42.5%, 29%, 8, −0.066, +5.7 pp. US b&h: 0.523, −51.2%, 23%, 17, −0.008, +2.0 pp | F13, U1, F24 | M5 (ref) | ABSENT |
| G-LAD-03 (L5899) | Sensitivity (ref) | 0.5× cooling-off moves US VT15 to 0.538 / −37.8%. 10-session halt instead of 11 moves KOSPI b&h cumulative Sharpe 0.553 → 0.595 | F13, U1, F24 | M5 (ref) | ABSENT |
| G-STALE-01 (L5905-5908) | Staleness, decisions 2016-01-04 → 2026-09-25; columns stale under "1 trading day" · "3 days" · schedule-aware · median / max age (days), at US close / KRX close | DTWEXBGS (H.10): 100.0% / 98.6% · 100% / 100% · 0.89% / 0.80% · 6 / 12; DEXKOUS (H.10): 100.0% / 98.6% · 100% / 100% · 0.52% / 0.42% · 6 / 12; DGS10 (strict H.15): 99.52% / 95.9% · 42.0% / 42.4% · 0.33% / 0.34% · 2 / 5; VIXCLS (16:15 ET): 0.0% / 2.1% · 1.9% / 2.0% · 0% / 0% · 1 / 4 | F18, F07, F25, calendars | T-STALE-01 · M1 | partial: `fred_DEXKOUS` from 2017 only |
| G-EST-01 (L5916-5922) | QLIKE relative to SMA20 (MCS p in brackets; T_max; stationary bootstrap, mean block max(10, 2h); B 2,000); KOSPI ^KS11 from 1996-12, OOS from 2001-01-02, 6,342 origins; US ^GSPC from 1990, OOS from 1995-01-03, 7,985 origins; refit every 21 origins, expanding window; target Σ r² over next h | SMA20 1.000 (0.000) ×5, US h21 1.000 (0.0005); EWMA 0.94: 0.966 (0.002) / 0.867 (0.075) / 0.749 (0.462) / 0.965 (0.000) / 0.870 (0.000) / 0.814 (0.002); EWMA 0.97: 0.976 (0.001) / 0.895 (0.016) / 0.742 (0.692) / 0.980 (0.000) / 0.907 (0.000) / 0.828 (0.017); GARCH(1,1)-t: 0.957 (0.002) / 0.837 (0.185) / 0.683 (1.000) / 0.949 (0.000) / 0.809 (0.000) / 0.670 (0.657); GJR-t: 0.952 (0.032) / 0.841 (0.185) / 0.718 (0.692) / 0.926 (0.081) / 0.757 (0.105) / 0.652 (0.668); log-HAR-range: 0.947 (0.142) / 0.818 (0.185) / 0.715 (0.692) / 0.921 (0.081) / 0.744 (0.105) / 0.695 (0.657); COMB: 0.944 (1.000) / 0.809 (1.000) / 0.691 (0.692) / 0.916 (1.000) / 0.723 (1.000) / 0.642 (1.000) | F13 (OHLC for range), F14 | T-EST-01, I-10 (SMA20 outside 90% MCS at h 1/5/21, p ≤ 0.0005 → ≤ 1/B; COMB inside all six) · M3 | ABSENT |
| G-EST-02 (L5924) | MSE MCS p for SMA20 | KOSPI 0.036 / 0.066 / 0.141; US 0.112 / 0.112 / 0.290 | F13, F14 | T-EST-01 (printed) · M3 | ABSENT |
| G-EST-03 (L5927-5930) | Calibration lines | B5: KOSPI 4.70% of 2,594 (PIT p 0.107); SPY 4.99% (0.566); US 5.31% of 8,961 (0.976); EWMA 4.90% / 5.22% / 5.31%. B5 passes 7 of 9 KOSPI and 8–9 of 9 US forecasters; log-HAR-range narrowly fails KOSPI 1-day (5.58% vs upper bound 5.56%). Christoffersen independence, KOSPI 2001–26: SMA20 < 0.0001, EWMA94 0.0007, EWMA97 < 0.0001, GARCH-t 0.026, GJR-t 0.032, log-HAR-range 0.16, COMB 0.17; SMA20 on 2016–26: 0.0006; no US model fails. h = 1 HAR: range target 0.947 / 0.921 × SMA20; QF6's log-r² design 1.390 / 1.242 | F13, F14, F15 | T-EST-02 · M3 | ABSENT |
| G-EST-04 (L5936-5944) | Sizing books (KOSPI 2001–26, 3 bp; σ̂ from each model's 21-day forecast; target 20%; cap 1): Sharpe · max DD · turnover/yr · vol-of-vol · ΔSR vs SMA20 [90% CI] · ΔMDD | B&H 0.563 · −54.5% · 0 · 0.111; SMA20 0.571 · −40.0% · 2.25 · 0.0446; EWMA 0.94 0.547 · −42.1% · 1.92 · 0.0425 (−4.7%) · −0.024 [−0.053, +0.005] · −2.1 pp; GARCH-t 0.550 · −40.5% · 2.49 · 0.0375 (−16.0%) · −0.022 [−0.054, +0.011] · −0.5 pp; GJR-t 0.556 · −40.5% · 2.54 · 0.0373 (−16.4%) · −0.016 [−0.053, +0.020] · −0.6 pp; log-HAR-range 0.578 · −35.0% · 5.28 · 0.0338 (−24.2%) · +0.006 [−0.045, +0.056] · +5.0 pp; COMB 0.571 · −37.2% · 3.48 · 0.0347 (−22.2%) · −0.000 [−0.042, +0.039] · +2.8 pp. 2016–26: gains halve (vol-of-vol −9% to −12%, ΔMDD +1.6 to +2.1 pp); at 35 bp log-HAR ΔSR −0.063 (CI −0.114 to −0.013), COMB −0.030 | F13 | T-EST-03 (COMB vol-of-vol −22% ± 2 pp; ΔMDD +2.8 pp; ΔSR −0.000 [−0.042, +0.039]) · M3 (clauses M7) | ABSENT |
| G-DSR-01 (L5947) | DSR code reproduces BLdP | 0.9505 at N 46; 0.9004 at N 100 | F30 inline | T-DSR-01 · M7 before freeze | **SYNTH: reproduces today** |
| G-DSR-02 (L5948-5952) | R-03 net of 50 bp both legs | SR 0.6723, T 9,233, skew −0.687, kurtosis 6.948; ΔSR vs unscaled +0.2729, HAC SE 0.0716 (NW-250 0.093); DSR vs 0 with V_trials / V_null: 0.886 / 0.984 at N 12; 0.668 / 0.947 at N 34; eq. 9 N̂ = ρ̂ + (1 − ρ̂)M = 12.5 (M 26; PX1's ρ̄ 0.535 gives 12.6, within T-NEFF-01's ± 0.1): DSR 0.880 / 0.983, deflated ΔSR 0.947; M 34 (N̂ 16.2): deflated ΔSR 0.927; N_equiv 6.3 → 0.98; R-04 0.77 | F10, F22, F23 | T-R03-01, T-STEP3-01 (0.98 ± 0.01 PASS; 0.947 ± 0.01 "step 3 borderline"; R-04 0.77 ± 0.02 FAIL), T-NEFF-01 (E_sim 1.33 ± 0.01; N_equiv 6.3 ± 0.4; N_clusters 5; N_hat_linear 12.6 ± 0.1; padding 6.33 → 6.59), T-SE-01 (LW-HAC 0.072, 250-block 0.091 ± 0.005; z 3.81 → 3.0) · M7 | ABSENT (T-STEP3-01 inputs are inline: R-03 ΔSR 0.2729, SE_obs 0.0716, SE_null 0.0935; R-04 0.0724 / 0.0349 / 0.0349 → SYNTH for the step-3 arithmetic) |
| G-YRS-01 (L5953-5956) | cap 1, 1990–2026, 37 calendar years | per-year Sharpe higher than static 15/37 = 40.5% gross, 17 identical years; excluding those 15/20 = 75% gross, 11/20 = 55% net; own return > 0 (step 8): 73.0% gross, 70.3% net; cap 2: 73.0% (net 43.2%); log return above vol-matched static 86.5% (cap 2), 78.4% (cap 1) | F10, F23 | T-R03-01 years clause (20 binding years; 15 higher gross / 11 net) · M4 | ABSENT |
| G-TR-01 (L5962) | US monthly 1927–2026, SMA10m 0.5×, cash = RF | 5 bp: ΔSR +0.083 [0.019, 0.134], p_ni 0.000 (→ < 1/B), ΔMDD +15.9 pp (2×: +15.9), tail 0.78, 9/10 episodes (max 0.21), years 68%, onsets 73 raw / 45 de-clustered, plateau 1.0 → PASS. 50 bp: ΔSR +0.059 [−0.007, 0.113], ΔMDD +15.8 (+15.6) pp, 9/10 (0.22) → PASS. Cash 0: +0.078 / +15.2 pp (5 bp), +0.055 / +15.0 (+14.8) pp (50 bp) → PASS | F11, F23 | T-TREND-02, I-12 (+ GJR-null percentile 87th ± 5; +14.9 pp on the daily US VT15 book 1991–2026 from U1) · M8 | ABSENT |
| G-TR-02 (L5963) | Start dates (5 bp) | 1930 / 1940 / 1950 / 1960: ΔSR +0.081 / +0.052 / +0.063 / +0.058; ΔMDD +21.4 / +15.3 / +15.5 / +15.2 pp → PASS. 1970 / 1980 / 1990 / 2000 / 2008: ΔMDD +15.3 / +15.8 / +15.8 / +15.2 / +16.2 pp, onsets 27 / 22 / 17 / 13 / 10 → INSUFFICIENT (sufficiency) | F11 | M8 | ABSENT |
| G-TR-03 (L5964) | Snooping haircut, 94 variants (SMA 2–24 m, TS 1–24 m, 0.5× and 0×; eq. 9 N̂ 30.7) | 94/94 ΔMDD ≥ 3 pp (median +16.4 pp); SMA10 ranks 33rd on ΔSR, 51st on ΔMDD; deflated ΔSR probability 0.99 (N 1), 0.59 (N̂ 30.7), 0.43 (N 94), 0.07 (N 7,846) | F11, F23 | M8; ledger_seed_R-28 (94 rows) | ABSENT |
| G-TR-04 (L5965) | Other indices (price, cash 0, 5 bp), ΔMDD vs S | S&P +17.5, Nikkei +4.2, HSI +8.0, DAX +14.0, FTSE +7.4, TAIEX +12.0, KOSDAQ +9.8 pp; each 15–21 de-clustered onsets | F09, F14 | M8 | ABSENT |
| G-TR-05 (L5966) | KOSPI daily 1998–2026, 3 bp (no Korea instance; context) | Cash 0: ΔSR +0.070, ΔMDD +3.6 pp; tail 0.929 daily / 0.853 at 21 days; 17 de-clustered onsets → INSUFFICIENT. From 2016: −2.3 pp (tail 1.02) | F13 | T-TREND-03 (KR refused; context only) · M8 | ABSENT |
| G-PWR-01 (L5972) | SE(ΔSR) of vol-target cards vs S | US VT15, 50 bp, 1990–2026: NW10 0.061 (QS 0.0605; bootstrap 0.060–0.061; ρ 0.920) → 241–246 years for +0.05 at 80% power. KOSPI VT20, 3 bp, 2016–26: NW10 0.132 (QS 0.130) → 319–330 years. KOSPI VT20 1997–2026: NW10 0.075 → 295–311 years. MDE80 0.128 (US) / 0.276 (KOSPI) | U1, F13, F23 | T-POWER-01 (0.061 ± 0.005; 0.130 ± 0.01; MDE80 0.13 / 0.28; PC-3 power at true 0 KOSPI 2016–26 0.30 ± 0.02) · M7 | ABSENT |
| G-PWR-02 (L5973) | P(REJECT) at true ΔSR 0 (300 paths per cell): QF3's definition · SPEC order · P(PC-1 at 1×) | Resampling, US VT15 50 bp: 0.69 · 0.58 · 0.44 (11 y); 0.61 · 0.45 · 0.55 (36 y); 0.62 · 0.43 · 0.57 (100 y). Resampling, KOSPI VT20 3 bp: 0.55 · 0.54 · 0.57; 0.63 · 0.63 · 0.41; 0.73 · 0.72 · 0.28. GJR-t, US: 0.72 · 0.67 · 0.43; 0.64 · 0.52 · 0.56; 0.46 · 0.28 · 0.74. GJR-t, KOSPI: 0.57 · 0.57 · 0.57; 0.27 · 0.26 · 0.81; 0.14 · 0.14 · 0.88 | U1, F13, F23 | TASK-M7-22 (freeze tier) · M7 | ABSENT |
| G-R08-01 (L5979) | Flag anatomy (raw parity flag; FRED 2007-12-04 → 2026-09-30) | 4,735 days; 10.1% flagged; 132 spells; 50.8% one-day; 15.9% ≥ 5 days; 14.0 transitions a year; de-clustered onsets 64 / 40 / 24 at 20 / 60 / 126 sessions; 5-close clearing: 72 spells, median 8 days | F07 | T-ANNOT-01 (132 spells, 50.8%) · M5 | smoke on Yahoo ^VIX/^VIX3M to 2026-09-25 (3 sessions short) |
| G-R08-02 (L5980) | Block as a CARD-P (record only) | ΔMDD vs S, raw / 5-close: US VT15 at 50 / 5 bp +0.9 / +0.6 pp and +1.3 / +0.6 pp; KOSPI VT20 at 3 / 35 bp +0.3 / +0.4 pp and −0.1 / +0.1 pp; US momentum +0.0 / −0.0 pp; tail 0.996–0.999; REJECT in 10 of 10 cells | F07, F13, U1, F10 | record only · M5 | ABSENT |

Reference-only list (L5992): G-KR-06, G-MOM-07, G-KR-L13 cap-1.5, G-LAD-01/02/03. Pre-patch labelled: G-KR-06 (0.534 / −46.2%), G-KR-02b −0.061 at 70 bp (§9.4 item 2).

### D.3 Feasibility summary (77 golden ids)

| Class | Ids |
|---|---|
| SYNTH (hermetic today) | G-DSR-01; T-PBO-01 noise control; T-STEP3-01 arithmetic (inline inputs) |
| ARITH (identities from printed numbers; asserted as consistency checks) | G-POST-01 drawdown −23.16% and vt 0.694; the four B5 bands; §11 concentration bounds 0.755 / 0.685 / 0.685 |
| SMOKE (local near-substitute; golden stays NOT_RUN) | G-R08-01 (Yahoo ^VIX/^VIX3M); G-B5-02 (`yf_SPY` to 2026-09-24); G-KR-01..04, 02c, G-KR-L08 (tech-fund scalar cross-checks `r2_idx_golden_values.csv`, `r2_idx_r4b_crosscheck.csv`); G-STALE-01 mechanics on `fred_DEXKOUS` 2017→ |
| REFDATA (everything else) | G-MOM-01..08, G-BOOK-01, G-INTL-01, G-YRS-01 (French daily/monthly); G-KR-01..06, 02b, 02c, 05, 05s (^KS11 → 2026-10-02; DEXKOUS from 1997); G-US-01..04, 01b, 01c, 02a, 02s (U1; DGS10, Treasury CMT, ^TNX, NASDAQ100, ^RUT); G-B5-01..04; G-POST-01 data rows; G-KR-L01..13; G-US-F01..10; G-REF-01/02; G-LAD-01..03; G-STALE-01 (DTWEXBGS, DGS10, VIXCLS); G-EST-01..04 (OHLC); G-DSR-02; G-TR-01..05; G-PWR-01/02; G-R08-02 |
| OWNER | F01 (KRX marketplace), F02 (ECOS code), F03–F06 (KIS sessions, KODEX PDF), F12 (French 1926+ licence/owner/md5), F25 (signed source-skipped list); licence and owner columns of every fixture; §9.4 items 13 and 15; git anchoring |

### D.4 Tests fed by this area: exact assertion, fixture, class (rf = runs_from; clauses per §9.0b)

| Test (rf) | Exact assertion | Fixture | Class |
|---|---|---|---|
| T-HERM-01 (M0) | "The macro test suite passes with all network touchpoints patched to raise"; runs on manifest-listed, md5-verified fixtures only | — | SYNTH |
| T-HERM-02 (M0) | after `run_all.py`, `core/rules` and every family ledger byte-identical; writes only to temp copies | — | SYNTH |
| T-REPRO-01a (M0) / 01b (M7) / 01c (M9) | every artifact and card records seed, `git_hash`, `config_hash`, `data_snapshot_id`, `knowledge_utc`, ledger hashes, `results_md5`; same seed, rules-store hash, snapshot and package → identical bootstrap and GJR-null outputs (rel diff ≤ 1e-12, single-threaded BLAS, PCG64 via SeedSequence, spawned children); same for R-16 paths | synthetic | SYNTH (git_hash "UNVERSIONED" per rulings) |
| T-FIX-01 (M1) | close-type row `retrieved_at_utc < official_close_utc + 10 min` → refused; publication-timed row before `publication_instant` → refused; DLA §7 values regenerate at Level 1 per §9.0b row | synthetic rows; F13/F16/F20/F27 for rows | refusal SYNTH (real local case: `yf_SPY` last row retrieved 2026-09-25T16:28Z < 20:00:30Z + 10 min must be refused); rows REFDATA |
| T-PROV-01 (M1) | `pit_value('KOSPI_OFFICIAL_CLOSE', decision_utc=2026-10-02T06:30:30Z, knowledge_utc=…, consumer='R-06', require_session=2026-10-02)` → `MissingInput("missing")` at 01:31Z, `MissingInput("provisional_intraday")` at 02:00Z, 7,003.74 [official_close] at 07:00Z | F26 | SYNTH |
| T-PRINT-01 (M1) | KOSPI close 2026-03-09 = 5,251.87 (−5.96%); the intraday −8.11% never stored | F01/F13 | REFDATA (store-row SYNTH possible for the guard) |
| T-MISS-01 (M1) | CPI YoY Aug-2026 = 3.353% ± 0.01; positional 3.713% never produced; Oct-2025-dependent derived values NaN, `vendor_derived_across_gap` tag | F18 CPIAUCSL vintages | REFDATA |
| T-STALE-01 (M1) | (a) DTWEXBGS, DEXKOUS stale ≤ 1% of decisions (0.42–0.89% expected), every hit's `d_next` in the source-skipped list; v1.2 rule 100% (98.6% at KRX close); (b) with the list no flag; (c) DGS10 strict ≤ 1% (0.33%); VIXCLS 0%; (d) deleting one H.10 release flags the next decision after the grace; (e) `last_obs`-availability reading ≈ 80% (79.8%) must not occur | F18, F07, F25 | (d)(e) SYNTH; (a)-(c) REFDATA |
| T-AVAIL-01 (M1) | DGS10 Fri 2015-01-02 → KRX close Tue 2015-01-06; DEXKOUS week of 2026-10-05 → KRX close Wed 2026-10-14; DGS10 2026-10-09 → US close 2026-10-14; CSAT 2025-11-13 close 07:30Z; injected registry error fails | calendars | SYNTH (calendar data OWNER-signed) |
| T-VT-01 (M2) | σ̂ simple returns ddof 1 reproduces rv20 28.82% and vt 0.694 on 2 Oct; < 20 valid returns → `insufficient_history` → weight 1.0 `warmup` before first ARMED, `MissingInput("missing")` after; σ̂ = 0 or not finite → `MissingInput` | F13 | dated value REFDATA; clauses SYNTH |
| T-COST-01 (M2; L/S both legs M4; 2× every card M7) | |Δw| charged at the pre-registered rate on the earning day; header rate change raises; KOSPI VT20 at 35 bp SR 0.609 ± 0.01; US VT15 at 50 bp SR 0.505 ± 0.01 | F13, U1 | mechanics SYNTH; values REFDATA |
| T-LABEL-01 (M2) | causal labels; boundary → higher label; appending future data leaves past labels; KOSPI 2026-10-02 elevated / stressed; US 2026-10-01 normal | F13, U1 | causality SYNTH; dated REFDATA |
| T-CORR-01 (M2) | corr63 on date-aligned (r_eq(D), −Δy(D)) = +0.53 at 2026-09-30 ± 0.01; series-lag implementation gives −0.094 | F14, F18 DGS10 | REFDATA |
| I-02 (M2) | replays 2024-07-31 → 2024-08-09 and 2026-06-22 → 2026-07-30 match G-KR-03/04 gross and net | F13 | REFDATA |
| T-B5-01 (M3; "cannot be PASS" clause M7) | SMA20 FHS exceedance 4.70% ± 0.3 pp on KOSPI 2016-03 → 2026-10, PASS (PIT p 0.11); synthetic σ̂ × 0.7 fails; switch without counted revision refused | F13 | value REFDATA; σ̂ × 0.7 SYNTH |
| I-10, T-EST-01/02/04 (M3; Stage-3, CI, counted-revision clauses, T-EST-03, T-EST-05 M7) | G-EST-01..04; GJR with α + β + γ⁄2 > 0.9999 or non-convergence or tripped OHLC flag → SMA20 fallback, logged, no blend; COMB on a `KRX_stock_book` card refused | F13, F14 | fallback/refusal SYNTH; values REFDATA |
| T-R03-01 (M4; step-3 and header clauses M7 after freeze) | ΔSR +0.273 ± 0.01; deflated 0.98 ± 0.01 at N_equiv 6.3 (PASS); 0.947 ± 0.01 at linear N̂ 12.6 "step 3 borderline"; revisions carry committed header md5 and increment the R-03 ledger; years line 20 differing years, 15 higher gross / 11 net | F10, F22, F23 | REFDATA |
| T-R04-01 (M7 after) | deflated add-on 0.77 ± 0.02 at N_equiv 6.3 → "step 3 FAIL"; A-provisional or pooled route rejected | F10, F11, F22 | arithmetic SYNTH; data REFDATA |
| T-ANNOT-01 (M5) | flag on → no book's weights change; annotation + KIS spread-snapshot request per flag day; 132 spells, 50.8% one-day | F07 | no-change SYNTH; anatomy REFDATA (SMOKE) |
| I-04b (M5) | −15% breach → HALTED (RISK), re-arm refused 10 sessions, references reset, 0.5× for 10 sessions; KOSPI 1997–2026 re-enters after every HALT; literal rule permanently HALTED from 1997-10, 714 cycles (G-LAD-01); HALT count pinned once computed (§9.4 item 9) | F13, F24 | mechanics SYNTH; counts REFDATA / pending |
| T-CAPS-01 (M5) | daily KODEX basket; w_i − g·b̃_i ≤ 0.05 NAV; template from the store (D1); 2 Oct bounds 0.755 and 0.685, gross and binding factor per book | F03 | ARITH; basket REFDATA / OWNER |
| T-DSR-01 (M7 before) | 0.9505 at N 46; 0.9004 at N 100 | F30 | SYNTH (passes) |
| T-DSR-02 (M7 before) | `units ∈ {daily, monthly}`; daily vs monthly DSR agree within 0.1; annualised SR with daily T raises | synthetic | SYNTH |
| T-NEFF-01 (M7 before) | E_sim 1.33 ± 0.01; N_equiv 6.3 ± 0.4; N_clusters 5; N_hat_linear 12.6 ± 0.1; padding 80 near-duplicates (ρ 0.99) moves N_equiv < 0.5 (6.33 → 6.59); no Kish N̂ | F22 | REFDATA (padding mechanics SYNTH) |
| T-STEP3-01/02 (M7 before) | R-03 0.98 ± 0.01 PASS, 0.947 ± 0.01 borderline; R-04 0.77 ± 0.02 FAIL (inline inputs); card without ledger hash refused; static scan finds no M ⁄ (1 + (M − 1)ρ̄) | inline | SYNTH |
| T-SEL-01 (M7 before; (e) after) | (a)-(h) verbatim at L2527; (g) f 1.3 / 2.9 → 2.9 binds | ledger seeds (F29) | logic SYNTH; seed rows REFDATA |
| T-LEDGER-01 (M7 before) | hand-edited row breaks the chain; research-script run appends; `ledger_hash_at_run` mismatch → card not written | — | SYNTH |
| T-PBO-01 (M7 before) | ledger ∪ frozen PC-6 grid, card's own objective; KOSPI VT grid Sharpe-objective PBO 0.28 printed; noise control 0.536 ± 0.001; 200 panels mean in [0.45, 0.55] | — | control SYNTH (0.5359 today); 0.28 REFDATA |
| T-EXCESS-01 (M7 before; frozen clause after) | v1.2-check on PX2's cash fixture: ΔSR +0.006, p_ni 0.078 ± 0.01; raw flag +0.026 and 0.052; frozen-convention values computed, printed, md5-frozen at first run, never asserted against these; missing cash day refuses the card; Columbus Day accrues prior DTB3; French RF unchanged | F13, F19, F02 | REFDATA; missing-cash-day clause SYNTH |
| T-POWER-01 / T-SE-01 (M7 before) | SE(ΔSR) 0.061 ± 0.005 (US VT15), 0.130 ± 0.01 (KOSPI VT20 2016–26); MDE80 0.13 / 0.28; years inside 241–246 / 319–330 → point before freeze; PC-3 power at true 0 0.30 ± 0.02; LW-HAC 0.072, 250-block 0.091 ± 0.005; z 3.81 → 3.0 | U1, F13, F10 | REFDATA |
| T-ES-01, T-DNH-01, T-ORDER-01, T-GATE-04 (M7 before) | synthetic: rule identical to S → ΔES 0 → REJECT; halving exposure on worst 5% of 21-session windows → ΔES_21 > 0; ΔMDD < 0 and ΔCDaR95 < 0 → INSUFFICIENT, ΔMDD alone → PASS; 26 onsets failing PC-2 → INSUFFICIENT (sufficiency first); 54-onset PC-1′ point ≤ 0 → REJECT; p × f > 0.10 → INSUFFICIENT (inconclusive); redesign path | synthetic | SYNTH |
| I-05 (M7 before) | zero lag-audit violations across every backtest behind a COMPLIANT golden | all golden fixtures | mechanism SYNTH; REFDATA |
| I-07 (M7 after) | `docs/macro_overlay_study.py` writes one card per rule; v1.2-check on the Yahoo fixture reproduces G-KR-L01..L08 at Level 1 | F13, F21 | REFDATA |
| I-09, T-EPIS-01/02, T-TROUGH-01, T-ES-02, T-RLAYER-01, T-BAND-01 (M7 after; T-EPIS-01, T-BAND-01 before) | 18 KOSPI episodes 1997–2026 (12 troughs < 2008), 4 on 2016–26, 16 S&P at 15%, no Sep-2026; open bear `open = true`; 14/18, max 0.174 ± 0.01 (0.493 printed); cost lines −6.9 / −15.5 / −31.5 pp; ΔES99 +1.95, ΔES95(21d) +2.9, ΔCDaR95 +7.1 pp (z 4.3; 2.3 ref only); `with_risk_layer` 24 HALTs, −56.4% vs −45.3%; band 32 starts 1997-05…1999-12 with `history_start` KR 1997-04-01, floor ≥ 22 (3·n_pass ≥ 2·n_starts); R-29 10 starts ≥ 8, no REJECT | F13, F14 | episode/band logic SYNTH; values REFDATA |
| T-GATE-02 (M7 after) | v2 verdict INSUFFICIENT DATA as a class; ES21 +1.65 pp, ES126 +3.8 pp ± 0.2 pp; p_ni printed (0.146 = R4b `gate_boot`, not asserted); 2× ΔSR −0.125; label stays "REJECT (instrument: US shares via KIS, 50 bp, daily)", never re-run | U1 | REFDATA |
| I-16 (M7 after) | formal Korea card PASS iff (i)-(iv); differences from G-KR-L01 printed with expected direction (ΔSR +0.026 → +0.006, p_ni 0.052 → 0.078); raw-flag run on F01 reproduces G-KR-L01 at Level 2, deviations explained; verdict function tested with injected sub-verdicts | F01, F02, F13 | verdict logic SYNTH; card REFDATA + OWNER; frozen package absent → NOT_RUN |
| T-STEP-02/03, I-15 (M7 after) | binding share ≈ 19% (KOSPI VT20, 3 bp, 1997-04-15 → 2026-10-02) and ≈ 10% (US VT15, 5 bp, 1990-04-02 → 2026-09-30) ± 3 pp; ΔSR vs no steps per the R-31 reference run (§9.4 item 8) | F13, U1 | REFDATA; pending |
| T-BOOK-02 (M7 after) | variants A / B / C and overnight / intraday attribution; KOSPI VT20, 3 bp, 1997–2026: SR 0.448 / 0.450 / 0.465 (± 0.01) | F13 (+ opens F06) | REFDATA |
| T-TREND-02, I-12 (M8) | G-TR-01 at Level 1; stacked ΔMDD on VT ≥ 3 pp (+14.9 pp daily US VT15 1991–2026); GJR-null percentile 87th ± 5; v2 verdict computed blind, a difference from PASS disclosed, never tuned | F11, U1 | REFDATA |
| T-USFUT-02/05 (M8) | settling run PASS only if PC-1′ at 1× and 2× and ≥ 80% of decade starts; synthetic 70% and 9-of-10-with-one-REJECT fail; DLA-U2 at Level 1 (+3.6 pp, 2×: +3.2, p_ni 0.002, 6/11 (0.46), plateau 0.875); G-US-F08 counts as ranges | F12 (NOT ACQUIRED), U1 | logic SYNTH; values REFDATA |
| T-REF-01/02 (M8) | S1/S2 absent from the FORWARD-SIM queue; card records REJECT (54 strict-H.10 onsets, ΔMDD −1.3 pp, tail 1.00 / 71 onsets, −3.1 pp at 50 bp Treasury +1 bd, −3.5 pp strict +2); G-US-02a reads "compliant via Treasury with logged posting time" | F13, F18, F28, U1 | queue absence SYNTH; records REFDATA |
| I-01 (M8) | 2026-10-02 run uses 7,003.74, flags match §11; 2026-07-30 KR run reproduces vt 0.25 (G-KR-04); zero non-allowlisted KIS requests | F01/F13, F26 | gates SYNTH; values REFDATA |
| I-11 (M9) | replay reproduces the Jul-2026 KOSPI path (−38.6% in 27 sessions) | F01/F13 | REFDATA |
| T-SCHEMA-02, T-DNB-01, T-CAP-01, T-CARD-02 (M0/M7) | schema fields; DNB refusals; vt > 1.0 fails validation (reference mode exempt); manifest re-hash at every card run | — | SYNTH (owned by M0/M7 briefs) |

Deferred clauses touching goldens (§9.0b L5572-5595): G-POST-01 row split (table above); G-US-01c EWMA(0.94) from M3; G-KR-06 only after §9.4 item 2; T-COST-01 "both legs" M4 and "2× every card" M7; T-EST Stage-3 / CI / counted-revision clauses, T-EST-03, T-EST-05 M7; T-B5-01 "cannot be PASS" M7; T-R03-01 step-3 and header clauses M7 after; T-SEL-01 (e) after the freeze; T-LAG-01 "refuses to write the card" and the `timing_probe` exception M7; T-RO-02 I-01 clause M8.

---

## E. Interfaces

Needs from earlier milestones:

| From | What | Shape |
|---|---|---|
| M0 (TASK-M0-02) | runner with `NotRun`, registry, `--milestone`, network patching, temp copies | `tests/macro_acceptance.tests() -> list[(name, fn)]`; `tests/macro_registry.csv` |
| M0 (TASK-M0-03) | manifest loader | `manifest()`, `fixture_path(file)`, `require_fixture(file)`, `verify_all()` |
| M0 (schemas, rules store) | `core/ficc/macro_schema.canonical_json`, `results_md5`; `core/rules/macro_rules.load_store` (`data.fixtures`, `reproducibility`, `gate.evaluation.*`) | rulings §4 |
| M1 | `core/ficc/pit.PITStore`, `PITValue`, `check_fixture(rows, market)`, `data_snapshot_id`; `core/calendars/clocks.close_print_bound_utc`, `publication.publication_instant`; `core/ficc/contracts.is_stale` (G-STALE-01) | rulings §4 |
| M2 | `core/quant/risk_layer.market_vol_target` (rv20 28.82%, vt 0.694), display labels; `core/quant/cardp.costed_book`, `core/quant/gate_stats.research_bootstrap` (share = 1 − p, block 63, B 1,000, seed 20261002), `pw_block`, `gate_boot(delta=0.10)`, `v12_checks`, `reference_only` guard | B.4–B.6 |
| M3 | `core/quant/vol_estimators` (sma20, ewma094, ewma097, garch_t, gjr_t, log_har_range, comb), `core/quant/forecast_eval` (QLIKE, MCS, B5 `docs/vol_backtest.py`, PIT χ² 10 bins, Christoffersen) | spec_M3_estimators |
| M4 | `core/quant/sleeves.sleeve_vol_scale`, `dm_gate` (specification book), book builders (G-MOM-06) | spec_M4_sleeves |
| M5 | `core/quant/risk_layer.drawdown_ladder`, `core/engine/books` (G-LAD reference paths; I-04b count) | spec_M5_engine_events |
| M7 | `core/quant/cardp.episodes`, `cardp_evaluate`; `core/quant/gate_ledger` (`family_ledger`, `n_eff`, `step3`); `core/quant/gate_stats.power_line`; `core/quant/gate_package` (`definitions_md5`); `docs/macro_overlay_study.py` | spec_M7_* |

Exposes to later milestones:

| To | What |
|---|---|
| every golden test | `goldens.csv` rows via `golden(id)`; `within(kind, got, want, level)`; `assert_golden`; `assert_class`; `NotRun` reasons |
| M7 freeze (L4820) | manifest md5s for `definitions_md5` (c) "the md5 of every fixture the acceptance test reads", (d) seeds (B.7), (e) ledger seed files and difference series (B.8); T-CARD-02 re-hash |
| M7 formal cards | pending rows (B.10) turned into goldens "computed at its first run, printed beside the research value and md5-frozen" (§9.4 item 14); `status` flips `pending → golden` only by a frozen run |
| acceptance report | per golden: got, want, kind, level, deviation; every Level-2 deviation explained (L5736); the NOT_RUN list with the series / vendor / span each needs (D.1) |
| Macro page / owner | `ACQUISITION.csv` open rows under "Open owner actions" |
| tech-fund area | `data/techfund/r3_golden_values.csv` pinned as reference constants (rulings §3.8); GV-273..302 cross-reference G-KR-01..04 pre-patch values only |

---

## F. Ambiguities, contradictions, conservative readings

| # | Issue (lines) | Conservative reading |
|---|---|---|
| F-1 | L5718 "All of these are frozen in the test fixtures"; L22 / L5492 locate them at `/home/claude/quantgen_macro_data/`; nothing is on this machine | Every REFDATA golden is `NOT_RUN("REFDATA: …")`; no fixture fabricated, no tolerance widened, no milestone exit claimed on blocked goldens. Re-acquiring public series through the keyless loaders creates a NEW vintage (an md5 change = "a fixture change logged in the manifest", L5492) → owner decision; if approved, cut at the data cut-off, record provenance, licence, owner, md5 |
| F-2 | "share" in the research-bootstrap columns (G-KR-02b (0.45), G-KR-05 (0.967), …) is never defined; L5724 names only the bootstrap | share = fraction of the 1,000 paired circular 63-day resamples (seed 20261002) with ΔSR* > 0 (= 1 − `sharpe_diff_bootstrap(...)["p"]`); consistent with `pc3_share_beats_S` of the tech-fund scorecard (0.4645 vs S). Asserted at ±0.03; recorded in the manifest |
| F-3 | Level-1 p ±0.01 (L5735) sits at the Monte Carlo error of B = 2,000; R4b's exact `gate_boot` draw sequence is in absent scripts; the tech-fund re-implementation landed 0.205 / 0.238 vs 0.21 / 0.24 | Port the draw scheme when the scripts arrive; until then p-values are asserted as the verdict class and printed |
| F-4 | §9.0a gives no `runs_from` for G-US-02/02a/02s/03/04, G-YRS-01, G-STALE-01, G-R08-01/02 | Use the reading test's milestone: G-US-02..04 → M8 (T-REF-02); G-YRS-01 → M4 (T-R03-01 years clause); G-STALE-01 → M1; G-R08-01 → M5 (T-ANNOT-01); G-R08-02 → M5 record only |
| F-5 | G-KR-04 (L5775) "22 Jun 2026 0.30; 23 Jun 0.33; 30 Jul 0.25" vs I-01 (L5688) "the 2026-07-30 KR run reproduces vt 0.25" | Registry stores them as weights EARNING on those dates (tech-fund 0.3025 / 0.3310 / 0.2485 reproduce that reading); I-01's "vt 0.25" is the weight earning on 30 Jul, carried by the 30-Jul run's state line; both printed |
| F-6 | G-KR-02b 2× column lists two values for three windows ("−0.001 / −0.061 (0.28) at 70 bp") and −0.061 is pre-patch; G-KR-02 2× column lists no sub-periods; G-MOM-04 net column omits ex-GFC | Assert only the listed cells; −0.061 `pre_patch_pending` (§9.4 item 2) |
| F-7 | G-B5-01 GARCH "FHS 5.42% → PASS (2,123 origins)" has no printed band | Band computed from n: 4.05–5.95%; PASS asserted against it; the different origin count (window 504 refit 7) recorded |
| F-8 | G-MOM-08 "0.000 (251-session PW)", G-TR-01 "p_ni 0.000" vs T-PZERO-01 (L2631) "No card field holds p = 0" | Registry `want: "<1/B"`; assertion `p < 1/B` |
| F-9 | Politis–White block (PW(d), PW(d²); block 183 in G-KR-L01, 101 in R4b 2016–26, 186 tech-fund) has no in-repo implementation; `arch` is importable but undeclared and the rulings forbid new dependencies | Port `optimal_block_length` into `core/quant/gate_stats.pw_block`; assert the block as a bootstrap-dependent count (±1) only when it matches the golden's; otherwise print |
| F-10 | `.v1.2_INTEGRATION_backup.md` §8.7 and the literal v1.2 ladder rule are absent; L5984-5990 is the only local definition; PC-6's "declared axis" grid per golden is not given; the tail-exposure ratio formula lives in R-21 | Build v1.2-check from L5984-5990 only; take PC-2 and the PC-6 grid from the M7 gate brief (for the Korea VT card the tech-fund grid window (10, 20, 40) × target (0.15, 0.20, 0.25) reproduced R4b's plateau 0.625); G-LAD-01 stays NOT_RUN until F24 arrives |
| F-11 | PC-3 "Bonferroni × the configurations searched as recorded in each golden's source row" (L5987); source rows absent | Factor 1 for G-KR-L01 (stated); other rows read from F21 when supplied; until then p_ni compared raw, verdict as a class |
| F-12 | Pre-patch values inside goldens (G-KR-06; G-KR-02b −0.061; SMA60 0.550, EWMA (half-life 10) 0.607, EWMA at 35 bp 0.573 with no G-id, L5999) | `status: pre_patch_pending`; never asserted before §9.4 item 2's rerun is md5-frozen (L5552) |
| F-13 | L6018 "the six trend indices" vs seven names in G-TR-04 (L5965) | Six = Nikkei, HSI, DAX, FTSE, TAIEX, KOSDAQ (F09); the S&P comes from F14 |
| F-14 | US span "1990-02-01 → 2026-09-30" (L5782) and splice "for Sep-2026" (L5722) vs G-B5-03 "1991-03 → 2026-10 (8,961 origins)" and "US 2026-10-01" (L5715) | The deterministic origin count 8,961 arbitrates; extend the ^GSPC splice to 2026-10-01 only if the count requires it; record the choice in the manifest |
| F-15 | L5492 "generated once, at M1's exit" vs §12 M0 "Macro fixtures under `tests/fixtures/macro/` (proposed), frozen from post-close files" (L6362) | M0 creates the manifest, loader and synthetic fixtures; M1's exit generates the golden-value fixtures (provenance + `value_status`) and freezes md5s; T-FIX-01 runs from M1 |
| F-16 | R3 §13 XS-20 (R3:L1308) "the spec's 2016-26 golden values reproduce (`r2_idx_golden_values.csv`)" and OQ-07 (judge Korea from 1996-09 rebuilt or 2016-01) | True against PRE-patch numbers (0.638 / 0.634) on a rebuilt KOSPI ending 2026-09-29; post-patch goldens are 0.641 / 0.637 on ^KS11 to 2026-10-02 → informative only. `history_start` KR stays 1997-04-01 (L4552); the 1996-09 PASS is a displayed proposal (rulings §3.7) |
| F-17 | R3 XS-11 (R3:L1299) proposes PW on d and d² for steps 2 and 5; R-24 (L4991) withdrew PW(d²) for v2 | v1.2-check mode keeps PW(d), PW(d²) as the goldens report; the v2 package uses PW(ψ); XS-11 is a pending proposal, no package change |
| F-18 | R3 XS-13 (R3:L1301): tech-fund harness prints step 9 as 0.4 × diff; spec 0.6 × OOS | Tech-fund GV-523 is arithmetic, not a lab output; no macro golden depends on it |
| F-19 | §9.4 item 15 and L4820 require a git commit or external anchor; the folder is not a git repository | Rulings §3.1: `git_hash: "UNVERSIONED"`; freeze and f = 1 route refuse; OWNER action "place the repository under git" |
| F-20 | Local cache files as stand-ins violate T-FIX-01 (no `retrieved_at_utc`, intraday last US row, no licence / owner / md5) | Never list them in `MANIFEST.csv` as golden fixtures; dry run and `local_substitute` smoke checks only, with the last US-session row dropped |
| F-21 | §9.3.2 scope (L5811): every number appears in `QX_DLA_…md` / `QX_DLB_…md` with CSVs "named in each file"; those notes are absent, so result-CSV column semantics are unknown | Registry values transcribed from the spec tables (D.2); CSV columns mapped when the files arrive |
| F-22 | Level 2 (L5736) has no tolerance for weights, shares, counts, z, ES | Level-2 assertions only for Sharpe, window returns, max DD, p-values; other kinds printed |
| F-23 | G-KR-L01 "PW block 183" (L5846) vs tech-fund block 186 (1996-09 start) vs R4b 101 (2016–26) | Different samples; not cross-asserted |
| F-24 | §11 (L6310) pair share "≈ 51% of KOSPI (51–54% by anchor)" vs G-POST-01 53.6% (L5832) vs tech-fund CR-07 53.71% on 2026-09-29 (R3:L1294-1295) | G-POST-01 asserts the B3a-anchored 53.6% (29.8 + 23.8) at M5; the CR-07 definition is a displayed proposal (XS-07), not a golden |
| F-25 | "Every golden test and the printed shock-type lines must use these return dates" (L5141) while §8.6 says v2 PC-4 uses objective episodes | Regression goldens (v12 mode) use the §8.6 table dates (B.4); v2 cards use the episode builder; both printed |

---

## G. DO-NOT-BUILD items and invariants binding this area

- No order, cancel, withdrawal, deposit-address or transfer path; KIS read-only (P0, T-RO-01). Fixtures and goldens never touch the network (T-HERM-01); tests never write production state (T-HERM-02).
- Reference mode (L5992): results "never enter a book, a card or an artifact"; `core/` cannot import it; the rules store still refuses any cap > 1.0, DM 0×, product stacks, the literal ladder (§10 items 2, 31; T-CAP-01, T-DNB-01 apply to the store and books, not to reference reproductions).
- Goldens are reproductions, "never a verdict" (L5982); v1.2-check mode never runs the v2 package; formal verdicts come only from the frozen package (L5813), which is not frozen here (rulings §1) → every card `NOT_RUN`.
- "No number is invented" for §9.4 items (L5996); pre-patch labels stay until the rerun is md5-frozen; "never re-run" R-06 US (no new card record; G-US-F01 reproduction is not a card run).
- A statistic within tolerance of its threshold is asserted as a class (L5499, L5738); no p-value printed as 0 (T-PZERO-01); Level-2 deviations explained in the acceptance report (L5736).
- Fixture md5s, seeds and ledger seeds are frozen items of `definitions_md5` (L4820); a change after the freeze is a new package version re-running every card (L4828); "No change may be justified by the card it flips".
- No Kish N̂ anywhere (§10 item 36; T-STEP3-02 static scan); no forward record presented as validation (item 35); seed rows never include the card's own lag rows or null-distribution runs (L2473).
- No new dependencies (rulings §3.2): no `arch`, no `pyarrow`; Parquet never read; PW ported.
- Missing fixture, missing owner input, unanchored timestamp → fail closed (`NotRun`, refusal), never a skip, never a default value.
- Local vendor data runs only as a labelled dry run (`vendor_close`, `dry_run/`, red chip), books DISARMED, no verdict written (rulings §1).
