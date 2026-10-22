# spec_M9_M10 — R-16 Quant Lab (expanding fits, FHS/EVT tails, self-grading, scenarios, replays) and R-17 planned sleeves (CRYPTO clock, FX instrument)

Sources. Spec = `QUANTGEN_Quant_Council_2026-10-03/claude_code/QUANTGEN_MACRO_INTEGRATION.md` (`L####` = line). Read in full: R-16 L1742-1748, R-17 L1750-1773, section 12 L6356-6373, Quick start L14-100, section 9 rows I-11 L5701, T-REPRO-01a/b/c L5666-5668, T-CRYPTO-01 L5657, T-FX-01 L5658, 9.0/9.0a/9.0b L5501-5598, section 10 L6039-6260, P0/P2/P5/P10/P11/P13-P19 L491-656, R-30 L3155-3260, R-10 multi-session gaps L1631-1634, R-26 rule 2 L2801-2808, section 3.5 L961-1113, section 7 keys L4153-4166 / L4286-4315 / L4462-4464 / L4680-4684, section 7.1 L4687-4705, 6.1 `vol` L3548-3568, 6.3 L3817-3830, 6.5 header L3909-3990, 8.1.2 L4781-4797, 8.2 L4840-4853, 8.6 shock table L5114-5143, 8.9 R-17 row L5399, 9.3.1 L5708-5737, 9.4/9.5 L5994-6035. Backlog (`QUANTGEN_MACRO_BACKLOG.md`, `BL####`): BL-G01 BL1277-1321, BL1836, BL1875-1882, BL1917-1918, BL-U06 BL1168-1174, ST-06 BL266. Tech-fund R3 (`R3_TF_neural_link.md`, `R3:####`): TF-67..70, XS-17, G-29/53/54/75/76. Tasks: TASK-M9-01..04, TASK-M10-01..02.

Transliteration: inside quotes, en dashes in numeric and date ranges are written as hyphens ("2016-26", "0.27-1.00") and "McNeil-Frey" is hyphenated; every other character, number, key and enum string is as printed.

Markers: **[V]** = verbatim/binding spec text. **[R]** = this note's reading where the spec is silent (each listed in section F). "proposed" paths/names may be renamed (L89, L963); field names, parameters, bounds, formulas, thresholds are binding (L89).

Class of both rules: R-16 = `CHANGED · CONTEXT · P1 · M9` (L1746), "DEFERRED / CONTEXT ... built, but never acts" (L4790, L4849). R-17 = `CHANGED · CONVENTION · P2 · M10` (L1752), build status DEFERRED: "specified, dormant until the planned sleeve exists" (L1461, L4790).

---

## A. Scope

| Task | Deliverable (one line) | Target files (E = existing, N = new/proposed) |
|---|---|---|
| TASK-M9-01 | Lab GARCH/GJR fits on expanding windows of >= 10 years (replaces the 504-close window); tails by FHS and by a GPD on the lower 10% of standardised residuals (McNeil-Frey); SMA20 stays the only sizing estimator; GARCH(1,1)-t fan keeps its own B5 label; 1-day VaR shown only from a model that passes 1-day B5; no ML vol-state classifier. | N `core/quant/lab.py` (tails, envelope); E `ui/quant_lab_page.py` (history depth, chips); reuse M3 `core/quant/vol_estimators.py` (`garch_t`, `gjr_t` expanding drivers) and E `core/quant/garch.py`, `core/quant/gjr.py` unchanged |
| TASK-M9-02 | Self-grading display: envelope `max(fast FHS, GJR-EVT)`; Kupiec + Christoffersen CC at 95% and 99%; ES 97.5% Z2 (simulated critical values); Basel zones; fan PIT at h = 21 and 126; 2016-26 and 2026 separately; post-holiday sessions separately; displayed 1-day VaR x sqrt(max(n_US, 1)); per-label coverage by tick loss; label "path-vol quartile"; M9 gate on the OOS 2016-26 thresholds. | N `core/quant/lab.py` (`grade`, `m9_gate`); N `docs/quant_lab_grading.py` -> `docs/quant_lab/*.json` + manifest [R]; E `ui/quant_lab_page.py` (grading block); reuse E `core/quant/validate.py` (`kupiec`, `christoffersen`, `traffic_light`, `pit_tests`) and M3 `core/quant/forecast_eval.py` (`es_z2`, `fan_pit`, `b5`, tick loss) |
| TASK-M9-03 | Seeded scenario library (a)-(e); SEP Table-2 short-rate error bands as rate-path uncertainty through `core/ficc/ratesim`; every scenario names its Brent series; leveraged-ETF path formula. | N `core/quant/lab.py` (`SCENARIOS`, `run_scenario`, `letf_path_return`); E `core/ficc/ratesim.py` (+ `sep_band_params`) |
| TASK-M9-04 | Historical-replay library (8 replays) on the current simulated book with regime metadata; GMM scenario regimes NOT built; guard that no lab output is read by a sizing module. | N `core/quant/lab.py` (`REPLAYS`, `run_replay`); reads M1 `regime_tags`, M5 book state; guard test |
| TASK-M10-01 (deferred) | `decision_time_utc("CRYPTO", d)` = 00:00:00Z on d+1, declared per venue; 365-day annualisation; weekday macro data joined as-of with staleness labels; no mixing with FRED `CBBTCUSD`; crypto vol-target CARD-P + hard gross cap registered only when a crypto sleeve exists (header committed, FORWARD-SIM first). | M1's calendar module (E `core/calendars.py` today; `core/calendars` package proposed by M1) CRYPTO branch; rules-store keys `time.markets.CRYPTO`; card header for `crypto_venue`; N small `asof_join` helper next to the PIT layer |
| TASK-M10-02 (deferred) | An FX sleeve card without a declared instrument (`FX_KRX_USD_futures` or `FX_broker_spot`) is refused; FX costs 10 bp per side; carry de-risk and intervention rules are sleeve-level risk limits, not overlays; never a rate-differential direction forecast. | M0's `core/rules` `validate_card_header` (TASK-M0-13) + rule-object predicate |
| tests | I-11 (5 clauses), T-REPRO-01c, T-CRYPTO-01, T-FX-01 | N `tests/lab_acceptance.py` (register in `tests/run_all.py`); T-CRYPTO-01 / T-FX-01 in the macro suite (`tests/macro_acceptance.py`, name proposed by the M4 brief) |

Adjacent tech-fund items (owned by the tech-fund briefs; recorded so M10 does not contradict them): CRY-1 / G-29 "keep C3 PASS; add a vol-scaled long-only control, a 2024-01-10 split, an ETH replication and a cut-time test (3 extra trials)" (R3:342-347, R3:826); XS-17 "R-15 crypto ST reversal 2 -> 0" (R3:1305); G-53 CTREND-lite + down-only funding/basis multiplier BACKLOG (R3:860); G-54 one USD/KRW slow-trend test at 10 bp BACKLOG (R3:861); G-76 "G10 FX technical rules ... DROP (weight 0)" (R3:893); OQ-09 crypto C3 prior 2 vs 3 open (R3:1322).

Existing-code facts the build must respect:
- `core/quant/montecarlo.py`: `MODELS = ("garch_t", "gbm", "jump", "bootstrap")`; `tests/quant_acceptance.py::test_mc_all_models_run` asserts that tuple exactly. The envelope / EVT is a graded VaR/ES line, NOT a fifth fan model: do not extend `MODELS`.
- `run_monte_carlo(history, *, model="garch_t", n_paths=5000, horizon_days=126, target=None, var_level=0.95, seed=7, n_sample_paths=40, drift="premium", rf_rate=0.03, erp=0.04) -> MCResult`; `MCResult.var_pct` is a HORIZON loss fraction, not a 1-day VaR; it is not graded.
- `ui/quant_lab_page.py` calls `load_history(symbol.value, source=...)` with the default `days=504` (the "504-close window" of L1747). `core/ficc/data._period_for(days)` returns `"10y"` for any `days > 1260`: Yahoo cannot return more than ten years.
- `docs/build_models_primer.py` imports `_garch_blocks`, `_study_chips` from `ui/quant_lab_page.py` and reads that file's source: keep both names and signatures.
- `ui/quant_lab_page.py` / `ui/qcharts.py` contain NO path colouring by conditional-vol quartile and no `calm / normal / elevated / stressed` string (sample paths are drawn in `pal.muted`). The spec's "path colours are renamed" (L481, L1747) has no object in this repo (F-12).
- `core/quant/validate.py` already has `kupiec(hits, alpha) -> {"n","x","rate","lr","p"}`, `christoffersen(hits, alpha) -> {"lr_ind","p_ind","lr_cc","p_cc"}`, `traffic_light(hits99, window=250) -> "green"|"yellow"|"red"` (<= 4 / <= 9 / else), `pit_tests(u)["chi2_p"]` (10 bins). Reuse; write no second copy.
- `core/ficc/ratesim.py`: `calibrate(series, *, model, dt) -> ShortRateParams{model,kappa,theta,sigma,r0,note}`, `simulate(params, *, horizon=1.0, n_paths=5000, steps_per_year=252, seed=7, threshold=None, curve=None) -> RateSimResult`; `MODELS = ("vasicek", "cir", "hull_white")`; seeded with `np.random.default_rng(seed)`.
- The gate's cost table lives at `docs/asset_expansion_study.py:60`: `COST = {"krx_etf": 3.0, "us": 50.0, "krx_stock": 35.0, "crypto": 10.0, "futures": 5.0, "fx": 10.0}`. The same script runs FX carry at 5 bp (`COST["fx"] / 2` at :408, `cost_bps=5.0` at :426) and `core/ficc/fx.carry_backtest(..., cost_bps=5.0)` defaults to 5 bp (F-27).
- `data/crypto/crypto_client.py`: Upbit daily candles are keyed by `candle_date_time_utc[:10]` ("KST 09:00 boundary" = 00:00Z); Binance `1d` klines are UTC-dated. No CoinGecko client exists. `core/crypto/analytics.py`: `CRYPTO_DAYS = 365`; `kimchi_premium` forward-fills FRED `DEXKOUS` by date onto UTC-midnight closes (F-25).
- `core/calendars.py` is a single file (`is_trading_day`, `special_session`, ...; JSON under `data/calendars/`); it has no `decision_time_utc` (TASK-M1-03 adds it).

---

## B. Build spec

### B.0 Conventions that bind every function here

| Item | Value | Source |
|---|---|---|
| Role | CONTEXT. "**Outputs are descriptive.** No lab output is read by a sizing module." | L1747 (6) |
| Sizing estimator | "**One estimator family sizes: SMA20 (R-06).** It changes only through the staged gate (R-30)." | L1747 (2) |
| Fit schedule | "GARCH and GJR parameters are fitted on expanding windows of at least 10 years"; config `fit: {window: expanding, min_years: 10, refit_every_origins: 21}` (R-30 key, reused) | L1747 (1), L4298 |
| Tails | "tails by FHS and a GPD on the lower 10% of standardised residuals (McNeil-Frey)" | L1747 (1) |
| VaR / ES levels | VaR 95% and 99% (1-day); ES 97.5%; fan PIT at h = 21 and 126 | L1747 (3) |
| Report periods | "It reports 2016-26 and 2026 separately." | L1747 (3) |
| Seeds | lab scenarios "all seeded and reproducible"; `reproducibility: {seed_study: 11, seed_research_bootstrap: 20261002, ...}`; existing lab default `seed=7` | L1747 (4), L4680 |
| Determinism | `determinism: {canonical_json: sorted_keys_repr_floats_no_whitespace, volatile_fields: [generated_at_utc, git_hash], rng: numpy_pcg64_seedsequence_spawned_children, blas_threads: 1, relative_tol: 1.0e-12}` | L4683-4684 |
| Annualisation | 252 (`vol_target.annualisation_days: 252`); CRYPTO 365 (`annualisation_days: 365`) | L4309, L4163 |
| Data access | `pit_value(series_id, decision_utc, knowledge_utc, consumer, require_session)`; lab bindings carry role `history` or `context`; never `acting_exposure` | L998, L987, L1105 |
| Regime states | none acting or displayed; "GMM scenario regimes stay deferred ... never labelled as a current regime (P19)" | L1747 (5), L653-656, L6186-6190 |

Design rule [R]: `core/quant/lab.py` holds pure functions on numpy arrays (no I/O, no provider import) plus frozen dataclasses; the page and the docs script do the loading. Every result object carries `acts: False`.

### B.1 Expanding-window fits (TASK-M9-01; R-16 rules (1)-(2))

[V] L1747 (1): "QUANTGEN's 504-close window ending 2026-09 is regime-captured: GARCH-t persistence ranges 0.27-1.00 across 303 monthly refits, and the latest fit implies a 61% unconditional vol."

```python
LAB_MIN_YEARS = 10                                   # L1747 (1); = vol_target.estimator_gate.fit.min_years
def has_min_history(dates: Sequence[str], t: int, *, min_years: int = 10) -> bool
# [R] True iff dates[t] - dates[0] >= min_years calendar years (F-3)
def lab_fit(returns, dates, *, model: str = "gjr_t", min_years: int = 10) -> LabFit
# model in {"garch_t", "gjr_t"}; fits on ALL returns through the last date (expanding, not trailing)
# returns LabFit{model, fit (GarchFit | GJRFit) | None, n_obs, first_date, last_date,
#                status: "ok" | "insufficient_history" | "fit_failed", reason: str | None, acts: False}
```
- Interactive fit: `core.quant.garch.fit_garch(r, dist="t")` / `core.quant.gjr.fit_gjr(r, dist="t")` on the full history; the lab keeps the module constant `STATIONARITY_MAX = 0.9995` (existing tests assert it). Rolling-origin fits for grading: call M3's `vol_estimators.garch_t(r, 1, min_years=10, refit_every=21)` / `gjr_t(...)` unchanged (they pass `stationarity_max=0.9999`, the R-30 constraint "α + β + γ⁄2 ≤ 0.9999", L3187) so "GJR" in the lab and in R-30 is one implementation (F-2).
- `insufficient_history` (fewer than 10 years): the fit is not presented as calibrated. Page behaviour [R]: the fan still draws, with an error-toned chip `fit window <N> sessions < 10 years (R-16): regime-captured, not graded`; no 1-day VaR line; no grading block (F-4).
- Page change: request the longest available history (role `history`), not `days=504`. Yahoo's `"10y"` cap makes a Yahoo pull land at 10 years minus 0-3 days: either extend `_period_for` with `"max"` for `days > 2520` or read the M1 store's history channel (F-5). `load_history(source="auto")` SYNTHETIC fallback stays allowed for the lab (role `history`) and stays loudly labelled (L985 forbids it for acting inputs only).
- GARCH(1,1)-t fan label [V] L1747 (2): "The GARCH(1,1)-t fan keeps its own label (REJECT on SPY in the t-quantile form; UNVERIFIED until `docs/vol_backtest.py` and its seed are published, BL-G01)." Keep `_study_chips()`; add the word `UNVERIFIED` to the SPY/KODEX chips while `docs/vol_backtest/manifest.json` (M3 output) is absent; once present, show its B5 line instead.
- 1-day VaR display gate [V] L1747 (2), L3193: "A 1-day VaR display comes only from a model that passes 1-day B5 (log-HAR-range narrowly misses it on KOSPI: 5.58% vs 5.56%)." B5 [V] L1561: "B5 pass = 5% VaR exceedance within ±2 binomial SE of 5% over ≥ 200 origins **and** a PIT χ² test (10 equal bins) with p ≥ 0.01." Use M3 `forecast_eval.b5(r, sigma_next, form="fhs")["status"]` per component model on the symbol's own history; status `FAIL` or `NOT_RUN` -> that model's 1-day VaR is withheld with the reason shown (F-8). "a σ̂ is never shown as a normal VaR" (L1561).
- [V] L1747 (2): "EWMA ≈ GARCH for KOSPI at one day; a long-window GARCH is better at 5-21 days, and the 504-window GARCH is worse than both." "Log-HAR on daily ranges ... is admitted to the R-30 race at the 21-day sizing horizon." (M3 owns it.) "Intraday realised variance is an upgrade, not a prerequisite." "**ML vol-state classifiers stay prohibited** (§10 item 11)."

### B.2 Tails and the envelope (TASK-M9-01/02; R-16 rules (1), (3))

```python
@dataclass(frozen=True)
class TailLine:                     # one model, 1-day ahead, aligned to origins t (forecast for t+1)
    model: str                      # "fast_fhs" | "gjr_evt" | "envelope" | "garch_t_fhs" | ...
    var95: np.ndarray; var99: np.ndarray       # positive loss fractions
    var975: np.ndarray; es975: np.ndarray      # ES 97.5% and its VaR
    ok: np.ndarray                  # bool per origin
    status: str                     # "ok" | "insufficient_history" | "evt_fit_failed"
    acts: bool = False

def fhs_tail(r, sigma_next, *, min_pool: int = 252) -> TailLine
def gpd_tail(z, *, threshold_share: float = 0.10) -> GpdFit        # lower tail of standardised residuals
def evt_tail(r, sigma_next, mu=0.0, *, threshold_share: float = 0.10, refit_every: int = 21) -> TailLine
def envelope(a: TailLine, b: TailLine) -> TailLine                 # elementwise max of losses
```

| Object | Definition | Source |
|---|---|---|
| FHS | [R] `z_s = r_s / sigma_next[s-1]`; `VaR_a(t+1) = -sigma_next[t] * quantile_{1-a}({z_s : s <= t})`; `ES_a(t+1) = -sigma_next[t] * mean(z_s | z_s <= quantile_{1-a})`; expanding pool, first origin once 252 residuals exist (same as M3 `b5`, F-9 of the M3 brief). | L1747 (1), (3) |
| fast FHS | [R] FHS with sigma from SMA20 (`sigma_next[t] = stdev(r[t-19..t], ddof=1)`, M2 `sma_vol`, daily units). Evidence wording: "fast SMA20-FHS did best" (L1748), "2026 favours fast SMA20-FHS" (BL1309). (F-6) | L1748 |
| GJR-EVT | [R] McNeil-Frey two-step. Step 1: GJR-GARCH(1,1)-t on the expanding window (M3 `gjr_t`), 1-day sigma forecast, residuals `z`. Step 2: losses `x = -z`; `k = floor(0.10 * n)`; threshold `u` = the (k+1)-th largest `x`; exceedances `y = x - u` for `x > u`; ML fit of GPD(xi, beta) (`scipy.stats.genpareto.fit(y, floc=0)`). Tail quantile at level q: `x_q = u + (beta/xi) * (((1-q) / (k/n))**(-xi) - 1)` (xi -> 0: `u - beta*ln((1-q)*n/k)`); `ES_q = x_q/(1-xi) + (beta - xi*u)/(1-xi)`. `VaR_q(t+1) = sigma_next[t]*x_q - mu`, `ES_q(t+1) = sigma_next[t]*ES_q - mu`. GPD refit with the same 21-origin cadence, residual pool through t only. | L1747 (1); formulas not printed (F-7) |
| EVT fail-closed | [R] `xi >= 1`, non-finite fit, `k < 50`, or a GJR fit outside the R-30 bounds (`gjr_fit_ok` False) -> `status="evt_fit_failed"`, `ok=False` at those origins; the envelope is NOT shown as a one-legged envelope: the page shows `fast FHS` alone, labelled, plus the failure reason. | conservative reading (L89) |
| envelope | [V] "the envelope max(fast FHS, GJR-EVT)". [R] `env.var_q[t] = max(fast_fhs.var_q[t], gjr_evt.var_q[t])` in loss units, same for `es975`; `ok = a.ok & b.ok`. | L1747 (3) |
| display VaR after gaps | [V] R-16: "scales the displayed 1-day VaR by √n_US after multi-session gaps (R-10)"; R-10: "Its displayed 1-day VaR scales σ by √max(n_US, 1)"; schema `var_display_scale`: "sqrt(max(n_US, 1)) for multi-session gaps; display only". `VaR_display = VaR * sqrt(max(gap_sessions(market, effective_session), 1))`; KR only; `gap_sessions = 0` -> unscaled. | L1747 (3), L1631, L3829, L5695-5696 |

### B.3 Self-grading (TASK-M9-02; R-16 rule (3); I-11)

[V] L1747 (3): "The lab shows the envelope max(fast FHS, GJR-EVT), with Kupiec and Christoffersen conditional-coverage lines at 95% and 99%, the ES 97.5% Z2 line (simulated critical values), Basel zones and fan PIT at h = 21 and 126. It reports 2016-26 and 2026 separately. It reports post-holiday sessions separately, and scales the displayed 1-day VaR by √n_US after multi-session gaps (R-10). It reports per-label coverage of the vol labels (R-06), scored by tick loss. Path colours are renamed "path-vol quartile"."

```python
def grade(r_next, dates, line: TailLine, *, periods: dict[str, tuple[str, str]],
          gap_sessions: np.ndarray | None = None, labels: np.ndarray | None = None,
          z2_simulate=None, n_sim: int = 2000, seed: int = 11) -> dict
def fan_grade(history_returns, dates, *, model: str, h: int, drift: str, seed: int, n_paths: int) -> dict
def m9_gate(report: dict, *, period: str = "2016-26") -> dict      # {"status": "PASS"|"FAIL"|"NOT_RUN", "lines": {...}}
```

Report shape [R] (plain dict, JSON-serialisable; no section 6 schema exists for it, F-15):
```
{"symbol", "model": "envelope", "components": ["fast_fhs", "gjr_evt"], "returns": "log"|"simple", "acts": false,
 "repro": {"seed", "config_hash", "data_snapshot_id", "package_version", "git_hash", "knowledge_utc"},
 "periods": {"2016-26": P, "2026": P},
   # P = {"n", "var95": {"rate","kupiec_p","ind_p","cc_p"}, "var99": {"rate","kupiec_p","ind_p","cc_p"},
   #      "es975": {"z2","p","rejected_5pct"}, "basel": {"last_250": "green|yellow|red", "windows": {"green","yellow","red"}},
   #      "tick_loss": {"var95","var99"}}
 "post_holiday": {"n_us_1": P', "n_us_2": P', "n_us_ge3": P'},          # unscaled and scaled breach rates
 "per_label": {"calm": L, "normal": L, "elevated": L, "stressed": L},    # L = {"n","var95_rate","kupiec_p","tick_loss"}
 "fan_pit": {"h21": {"chi2_p","n_origins","overlap": false}, "h126": {"chi2_p","n_origins","overlap": false},
             "printed_overlapping": {"h21": ..., "h126": ...}},
 "components_lines": {"fast_fhs": {...}, "gjr_evt": {...}},
 "gate": {"status", "lines": {"var99_kupiec_p","var99_cc_p","es975_z2_p","fan_pit_h21_chi2_p"}}}
```

| Line | Function | Rule |
|---|---|---|
| Kupiec 95% / 99% | `validate.kupiec(hits, 0.05)` / `(hits, 0.01)`; `hit = r_next < -VaR` | displayed; 99% gated |
| Christoffersen CC 95% / 99% | `validate.christoffersen(hits, alpha)["p_cc"]` (also print `p_ind`) | displayed; 99% gated |
| ES 97.5% Z2 | M3 `forecast_eval.es_z2(x, var, es, alpha=0.025, simulate=..., n_sim=2000, seed=11)`; [R] `Z2 = sum_t(x_t * I_t / (T * alpha * ES_t)) + 1`, `I_t = 1{x_t < -VaR_t}`; p = share of simulated Z2 <= observed; "not rejected at 5%" = `p >= 0.05` | gated |
| Basel zones | `validate.traffic_light(hits99, 250)` on the last 250 origins; [R] plus counts of non-overlapping 250-origin windows per zone (the pilot line reads "Basel red 0 / yellow 2") (F-10) | displayed |
| fan PIT h = 21, 126 | M3 `fan_pit(h)`: `u_t = Fhat_{t,h}(R_{t->t+h})` from the lab model's seeded paths at origin t; chi-square on 10 equal bins. [R] gated line: non-overlapping origins (every 21st session), the lab's default fan model on the expanding fit, drift mode as displayed; overlapping-origin line and h = 126 printed only (F-11) | h = 21 gated; h = 126 not gated |
| periods | [R] "2016-26" = first session of 2016 through the fixture's last official close (2026-10-02); "2026" = first session of 2026 through the same end (F-13) | L1747 (3) |
| post-holiday | origins whose effective session has `gap_sessions >= 2`, bucketed n_US = 1 / 2 / >= 3 as in the EX2 table (L1636) | L1631 "Post-holiday sessions are reported separately in the Quant Lab backtests (R-16)" |
| per-label coverage | per `display_label_rel` in `[calm, normal, elevated, stressed]` (M2, causal): 5% VaR breach rate, Kupiec p, mean tick loss `(alpha - 1{x < q}) * (x - q)` at alpha = 0.05; config `display_labels: {... per_label_coverage: reported, scoring: tick_loss}` | L1565, L4312-4314 |
| label text | any lab element that colours or groups paths by conditional vol is captioned exactly `path-vol quartile`; the words calm / normal / elevated / stressed are reserved for the R-06 display labels | L481, L1565, L1747 (3) |

**M9 gate** [V] I-11 (L5701): "M9 acceptance is out-of-sample on 2016-26: 99% VaR with Kupiec p ≥ 0.05 and Christoffersen CC p ≥ 0.05; ES 97.5% Z2 not rejected at 5% (simulated critical values); fan PIT χ² p ≥ 0.01 at h = 21 (thresholds: default, judgment). The 2026-only lines are reported, not gated." Section 12 (L6371): "h = 126 and the 2026-only lines are reported, not gated (QF6-A5, QF6-M3)."

```
m9_gate(report):
    L = report["periods"]["2016-26"]; F = report["fan_pit"]["h21"]
    if any required line is missing/NaN or n < 200:            status = "NOT_RUN"      # never a pass
    else status = "PASS" iff  L.var99.kupiec_p >= 0.05 and L.var99.cc_p >= 0.05
                          and L.es975.p >= 0.05 and F.chi2_p >= 0.01
         else "FAIL"
```
- Subject of the gate [R]: the displayed envelope on the KOSPI fixture (the pilot's market, L1748), VaR/ES series as displayed (gap scaling applied), components printed beside it (F-9).
- A FAIL is reported and labelled on the page; it changes no exposure and no model is re-tuned to pass (L89; the lab is CONTEXT). "A verdict derived from a statistic within tolerance of its threshold is asserted as a class" (L5499).
- Compute cost: about 125 GJR refits on up to ~7,500 returns per symbol. [R] The rolling-origin report is produced offline by `docs/quant_lab_grading.py` (seeded, md5 in a manifest, same shape as `docs/asset_expansion/manifest.json`) and the page reads the stored JSON the way `_study_chips()` reads cards; today's envelope number needs one fit and is computed on click.

Page block [R] (`ui/quant_lab_page.py`, new `_grading_blocks(report) -> list[ft.Control]`, existing `chip`, `_stat`, `card` helpers; Flet guard `tests/flet_api_guard.py` applies): one row per period with the six lines and PASS/FAIL chips; a "1-day VaR (envelope)" stat only when both components pass 1-day B5; chips `fast FHS`, `GJR-EVT`, `expanding fit <first>..<last>`, `h126: reported, not gated`, `2026: reported, not gated`; post-holiday table; per-label table captioned with R-06 label names; SYNTHETIC source keeps its error notice and suppresses grading.

### B.4 Scenario library (TASK-M9-03; R-16 rule (4))

[V] L1747 (4): "**Scenario library, all seeded and reproducible:**
(a) the 2026 vs 2022 oil-shock replays at +20 days (2026: KOSPI −15.5%, USD/KRW +5.2%, 10y real +32 bp; 2022: KOSPI +0.4%, USD/KRW +2.1%, 10y real −4 bp);
(b) the Jul-2026 KOSPI leverage unwind (−38.6% in 27 sessions);
(c) the Aug-2024 carry unwind;
(d) the Apr-2025 tariffs;
(e) SEP Table-2 short-rate error bands as rate-path uncertainty (±1.4 pp at 1 year, Dec-2023 SEP; an RMSE band of about 70% coverage, so a 90% fan needs about ±2.2 pp; read the latest SEP).
Rate paths go through `core/ficc/ratesim` (Vasicek / CIR / Hull-White), not through a log-return price model (architecture review C3). Every scenario names its Brent series."

```python
@dataclass(frozen=True)
class Scenario:
    scenario_id: str; kind: str                 # kind in {"shock_window", "rate_band"}
    window: tuple[str, str] | None              # return dates, inclusive
    horizon_sessions: int | None                # 20 for (a)
    series: dict[str, str]                      # factor -> named series id; MUST contain "brent": "DCOILBRENTEU" | "BZ=F"
    expected: dict[str, float]                  # the printed spec numbers (informative unless a fixture exists)
    seed: int; scenario_tag: str; note: str = ""
SCENARIOS: tuple[Scenario, ...]
def run_scenario(s: Scenario, panel: dict[str, tuple[dates, values]], *, book=None) -> ScenarioResult
# ScenarioResult{scenario_id, factor_moves: dict, path: dict[str, np.ndarray], book_pnl: float | None,
#                series: dict, seed, status: "ok" | "missing_input", missing: tuple[str, ...], repro: dict, acts: False}
```

| id | Window (return dates) | Source of the dates | Printed numbers |
|---|---|---|---|
| (a) `oil_2026_p20` | t0 + 20 sessions; t0 not printed for R-16. [R] t0 = 2026-02-27 (start of the section 8.6 "Mar-2026 ... oil / geopolitical" window) (F-16) | L5129 | KOSPI −15.5%, USD/KRW +5.2%, 10y real +32 bp |
| (a) `oil_2022_p20` | t0 not printed anywhere in the spec -> owner/fixture input (F-16) | — | KOSPI +0.4%, USD/KRW +2.1%, 10y real −4 bp |
| (b) `kospi_leverage_unwind_2026_07` | KOSPI returns 2026-06-23 -> 2026-07-30 (27 sessions; "KOSPI closing peak **9,114.55 on 22 Jun 2026**", "peak-to-trough −38.6% in 27 sessions") | L5131, L6441 | −38.6% in 27 sessions |
| (c) `carry_unwind_2024_08` | "US 2024-07-16 → 2024-08-05; KOSPI 2024-07-31 → 2024-08-09" (KOSPI window includes the start-date return, L5137) | L5126 | G-KR-03: Aug-2024 −7.9% (vt) vs −5.5% (buy-and-hold) L5774 |
| (d) `tariffs_2025_04` | "US 2025-02-19 → 2025-04-08; KOSPI 2025-03-28 → 2025-04-09" (start-date return included, L5138) | L5128 | G-KR-03: Apr-2025 −11.7% vs −12.0% |
| (e) `sep_rate_band` | rate paths, horizon 1 year | L1747 (4), L1437, L1692 | ±1.4 pp at 1 year (Dec-2023 SEP); 90% fan about ±2.2 pp |

- Brent naming [V]: config `brent_series: {spot: DCOILBRENTEU, futures: BZ=F}` (L4221); registry "`DCOILBRENTEU` (Dated spot) **and** `BZ=F` (front-month futures); always name which" (L1434); DNB item 19 "an unnamed 'Brent'" (L6150). `Scenario.__post_init__` raises when `series` has no `"brent"` key or a value outside those two ids.
- `scenario_tag` links R-10 calendar entries: "Scheduled or known risk windows (OPEC, weekend escalations) are calendar entries with a `scenario_tag` for Monte Carlo and the replay library (R-16). No exposure gate." (L1633; schema field L3830).
- Seeds [R]: default `seed = reproducibility.seed_study = 11` for library scenarios, recorded in the result; the interactive fan keeps `seed=7` (existing tests and the primer depend on it) (F-17).
- Missing series -> `status="missing_input"` with the names; nothing is interpolated or substituted (P5 L546).

**Leveraged / inverse ETF path** [V] R-26 rule 2 (L2806): "The Quant Lab path formula is ln(1 + R_L) = L·ln(1 + R) − ½(L² − L)·Σr² − carry (R-16)."
```python
def letf_path_return(R: float, sum_r2: float, L: float, carry: float = 0.0) -> float
#   exp(L*log1p(R) - 0.5*(L*L - L)*sum_r2 - carry) - 1
```
[R] `R` = underlying cumulative simple return over the path; `sum_r2` = sum of squared daily simple returns of the underlying on the path; `carry` >= 0 = cumulative financing-plus-fee drag over the path (an input; no default value is printed; "KODEX Leverage's −3.7% a year carry" is an open question, BL1918). Evidence [V] L2886: "KODEX Leverage −68.4% in the Jul-2026 crash against −81.6% naive". Local check on `docs/asset_expansion/cache` closes 2026-06-22 -> 2026-07-30: `yf_069500.KS` R = −0.4081, sum_r2 = 0.08121 (27 returns); formula (L = 2, carry 0) = −0.6770; exact daily product = −0.6806; `yf_122630.KS` actual = −0.6837; naive 2R = −0.8162.

**SEP band through ratesim** (new function in `core/ficc/ratesim.py`):
```python
SEP_RMSE_COVERAGE = 0.70                               # "an RMSE band of about 70% coverage" L1747
def sep_band_params(params: ShortRateParams, *, rmse_pp: float, horizon_years: float = 1.0,
                    coverage: float = SEP_RMSE_COVERAGE) -> ShortRateParams
```
[R] (mechanism not printed, F-18): target terminal sd `s = (rmse_pp/100) / Phi^-1((1 + coverage)/2)` (1.4 pp -> 1.351 pp; 90% half-width `1.6449 * s` = 2.22 pp, matching "about ±2.2 pp"). Return `replace(params, sigma=...)` with sigma solved from the model's closed-form terminal variance at `h = horizon_years`, kappa/theta kept: Vasicek and Hull-White `Var = sigma^2 * (1 - exp(-2*kappa*h)) / (2*kappa)`; CIR `Var = r0*(sigma^2/kappa)*(exp(-kappa*h) - exp(-2*kappa*h)) + theta*(sigma^2/(2*kappa))*(1 - exp(-kappa*h))^2`; `note` appended with the SEP date and rmse. Then `simulate(params_sep, horizon=h, seed=...)` unchanged. The band value is a context/history read of "SEP Table 2" (registry role "Calendar; C; Monte Carlo priors", L1437; context item "SEP Table-2 error bands (when released)", L1692): latest release when present; otherwise the Dec-2023 value shown with its vintage and a `stale` label (context-input rule L1110); never silently. No equity log-return model may be given a rate series by the scenario runner (rate scenarios return `RateSimResult` only).

### B.5 Historical-replay library (TASK-M9-04; R-16 rules (5)-(6))

[V] L1747 (5): "**Historical-replay library (v2.0)**, run on the current simulated book with regime metadata (price limits, the 1997 peg) attached to each replay: 1997-11/12, 1998-03→06, 2000-04-17, 2001-09-12, 2008-10, 2020-03, 2026-03-04 and 2026-06-23→07-30. GMM scenario regimes stay deferred behind it (CONTESTED, QF5-M9) and are never labelled as a current regime (P19)."

```python
@dataclass(frozen=True)
class Replay:
    replay_id: str; market: str; start: str; end: str      # return dates, inclusive
REPLAYS = (Replay("KR-1997-11_12", "KR", "1997-11-01", "1997-12-31"),
           Replay("KR-1998-03_06", "KR", "1998-03-01", "1998-06-30"),
           Replay("KR-2000-04-17", "KR", "2000-04-17", "2000-04-17"),
           Replay("KR-2001-09-12", "KR", "2001-09-12", "2001-09-12"),
           Replay("KR-2008-10",    "KR", "2008-10-01", "2008-10-31"),
           Replay("KR-2020-03",    "KR", "2020-03-01", "2020-03-31"),
           Replay("KR-2026-03-04", "KR", "2026-03-04", "2026-03-04"),
           Replay("KR-2026-06-23_07-30", "KR", "2026-06-23", "2026-07-30"))
def run_replay(rp: Replay, weights: dict[str, float], returns: dict[str, tuple[dates, r]], *,
               regime_tags, proxies: dict[str, str] | None = None, letf: dict[str, float] | None = None) -> ReplayResult
# ReplayResult{replay_id, dates, n_sessions, index_return, index_path, book_return, book_path, max_dd, worst_day,
#              regime: {"at_start": dict, "changes": [(date, tag, old, new)]}, unmapped: tuple[str, ...],
#              status: "ok" | "missing_input", repro: dict, acts: False}
```
- Month-only entries resolve to the sessions of those calendar months (F-19). Session lists come from M1 calendars (Saturday sessions before 1998-12-12 included, L2039).
- "current simulated book" [R]: the present weights of the selected book from M5's simulated books (`core/engine/state`; default the recommended book), held static through the window; daily book return = sum of weight x instrument return. An instrument with no history in the window (e.g. `etf_available` false before Oct-2002, L2042) uses a declared proxy (`proxies`: ETF -> its index; leveraged/inverse -> `letf_path_return` with L from `letf`), else it is listed in `unmapped` with zero return; nothing is proxied silently (F-20).
- Regime metadata [V]: `regime_tags(market, d) -> dict` (L1039-1040; TASK-M1-04). Tags (L2036-2047): `price_limit` (±6% from Apr-1995; ±8% from Nov-1996; ±12% from Mar-1998; ±15% from Dec-1998; ±30% from 2015-06-15), `saturday_session`, `close_time_kst`, `closing_call`, `random_end`, `lunch_break`, `fx_regime` (`peg_1997` for 1997-09-22 → 1997-10-17), `etf_available`, `short_sale_ban`, `sell_tax_pct`, `tick_regime`, `letf_rules`, `usdkrw_onshore_hours`. The result stores the full tag set at the window start plus every in-window change. `regime_tags` raising for an uncovered date -> `status="missing_input"`.
- GMM scenario regimes: not built (ST-06 runs "after the replay library", BL266; item 27 L6190). No replay or scenario result may carry a field named or captioned as a current regime.
- Guard for rule (6) [R]: (i) static import scan: none of the sizing modules — `core/quant/risk.py` and M2's risk-layer module, `core/quant/signals.py`, `core/quant/optimize.py`, `core/quant/vol_estimators.py`, `core/engine/*`, `core/rules/*`, the `macro_state` / `overlay_decision` builders in `core/ficc/macro` — imports `core.quant.lab`, `core.quant.montecarlo` or `core.ficc.ratesim` (`core.quant.garch` / `gjr` are shared fit kernels and are not lab outputs); (ii) every lab result type has `acts: False`; the book builder's existing assertion pattern (T-CTX-01, L5654: "static import check plus a runtime guard") is reused, not duplicated. Today `core/engine/*` and `core/rules/*` import nothing from `core.quant` or `core.ficc` (grep: 0 hits), so the guard starts green.

### B.6 Reproducibility of Monte Carlo paths (T-REPRO-01c)

[V] L5667-5668: "The same seed, rules-store hash, data snapshot and gate package version give identical bootstrap and GJR-null outputs (relative difference ≤ 1e-12 on the same platform and library versions, single-threaded BLAS, NumPy PCG64 seeded through SeedSequence, with spawned child seeds for parallel workers)." / "The same holds for the R-16 Monte Carlo paths."
- Existing RNG calls are already `np.random.default_rng(seed)` (PCG64 via SeedSequence) in `montecarlo.run_monte_carlo`, `garch.simulate_returns`, `ratesim.simulate`. No parallel workers exist; if the grading driver is ever parallelised, child seeds come from `np.random.SeedSequence(seed).spawn(n)`, never `seed + i`.
- [R] `repro` record on every lab result (scenario, replay, grading report; optional keyword on `run_monte_carlo`): `{seed, config_hash, data_snapshot_id, package_version, git_hash, knowledge_utc}` — the names of `reproducibility.record` (L4681-4682); `config_hash` = rules-store hash; `data_snapshot_id = data_snapshot_id(knowledge_utc)` (L1014) or the md5 of the input arrays when the lab runs on a loaded `History`.
- Never seed from the clock; `synthetic_history` dates end at `date.today()` (do not build fixtures from it).

### B.7 CRYPTO clock and crypto sleeve (TASK-M10-01; R-17) — DEFERRED

[V] L1755: "**CRYPTO clock.** `decision_time_utc('CRYPTO', d)` = 00:00:00Z on d+1, the close of the venue's daily bar dated d (that bar opens at 00:00:00Z on d), declared per venue (Upbit, Binance, CoinGecko). Annualisation uses 365 days. Weekday macro data are joined as-of, with staleness labels. FRED's CBBTCUSD is stamped at 5 PM Pacific and is never mixed with UTC candles."
Section 4.1 row (L1291): "CRYPTO (planned, R-17) | UTC | 24/7 | Venue daily bar close: the bar dated d closes at 00:00:00Z on d+1, declared per venue | 365-day annualisation; weekday macro data joined as-of with staleness labels; FRED's 17:00 PT stamp is never mixed with UTC candles."
Config [V] L4163: `CRYPTO: {tz: UTC, decision_utc: "00:00:00Z of d+1", venue_declared: true, annualisation_days: 365}   # the bar dated d closes at 00:00:00Z on d+1 (R-17; deferred)`.
Interface comment (L1028): "CRYPTO 00:00:00Z of d+1 (R-17)". Market enum includes `"CRYPTO"`, `"FX"` (L3538, L3729).

```python
decision_time_utc("CRYPTO", d)      -> datetime(d.year, d.month, d.day, tzinfo=UTC) + timedelta(days=1)
close_print_bound_utc("CRYPTO", d)  -> same instant            # [R] 0 s bound, like the non-KR/US default (L1033) (F-21)
is_session("CRYPTO", d)             -> True for every calendar date (24/7); NotASession never raised
annualisation_days("CRYPTO")        -> 365                      # sigma_ann = stdev(r, ddof=1) * sqrt(365)
CRYPTO_VENUES = ("UPBIT", "BINANCE", "COINGECKO")              # declared per venue; a card/book names exactly one
def asof_join(series_id: str, decision_dates: Sequence[date], *, ctx, consumer: str) -> list[JoinedValue]
# JoinedValue{value | None, obs_date, available_at_utc, staleness: "fresh" | "stale_missed_release" | "missing",
#             carried_days: int}   via pit_value(...) at decision_time_utc("CRYPTO", d) and M1 is_stale(...)
```
- As-of join [R]: for the crypto decision of date d the weekday macro value is the last record with `available_at_utc <= decision_utc`; weekends and holidays carry the last value with `carried_days > 0`; the staleness label is R-19's schedule-aware one ("stale iff decision_utc > stale_deadline_utc ... never the age of last_obs", L1019-1020), so a Friday value on Saturday is `fresh` with `carried_days = 1`. No interpolation, no forward shift (F-22).
- Venue declaration [R]: per venue one calendar-data row `{venue, bar_open_utc: "00:00:00Z", bar_dated: "open_date"}`; a daily series whose bar does not close at 00:00:00Z of d+1 is refused for a CRYPTO book. `CBBTCUSD` carries `bar_close_clock: "17:00 America/Los_Angeles"`; any join or panel mixing it with a 00:00Z candle series raises (`MixedClockError`) (F-23). A vendor that stamps the daily point at the close instant (00:00Z of d+1) is re-dated to d before use.
- Crypto sleeve [V] L1770-1773: "QUANTGEN's crypto desk already has a trend rule that passed the gate: card C3 on KRW-BTC, plus the BTC-USD card. The macro overlay adds only: an own risk bucket: BTC's own vol target as a CARD-P plus a hard gross cap (risk layer), on the 24/7 clock above; the BTC-equity β, estimated on rolling data; the weekly BTC-NDX correlation was 0.09, 0.47-0.50 and 0.22-0.24 across the three sub-periods on Wednesday-anchored weeks (0.06, 0.28 and 0.25 on Friday-anchored weeks; BTC trades at weekends, so the card declares its anchor); no net-liquidity or M2 input (§10)."
- Section 8.9 row [V] L5399: "**R-17** crypto vol target | CARD-P / — | The declared crypto venue (24/7 clock: 00:00Z bar close; 365-day annualisation) | None | NOT_RUN | **DEFERRED** until a crypto sleeve exists. It is then registered as a new card with its declared instrument (R-17)". Section 12 [V] L6372: "When those sleeves exist: T-CRYPTO-01 and T-FX-01 pass; card headers committed; FORWARD-SIM first". CARD-P member list: "crypto vol cap (R-17, deferred)" (L4845).
- When (and only when) the owner creates a crypto sleeve, the card header (section 6.5 schema, L3927-3990) is: `class: "CARD-P"`, `claim_type: "protection"`, `instrument_book: "crypto_venue"`, `estimator: "sma20"`, `parameters: {window: 20, target_ann: <pre-registered on the card>, cap: 1.0, annualisation_days: 365, venue: <one of CRYPTO_VENUES>, beta_week_anchor: "WED"|"FRI"}` [R names for the last three], `rebalance: "daily"`, `no_trade_band: 0.0` ("0.10 only on KRX_stock_book and US_shares_KIS", L3952), `costs: {per_side: "read_from_gate", floor: "tick_floor", stress: 2.0, stress_line: "printed"}` (crypto 10 bp, 2x 20 bp, L587), `timing.decision: "close_t_earn_t_plus_1"`, `build_status_on_pass: "BUILD_AS_INSURANCE"`. Target: "Other markets must be pre-registered per market on their card before they run (**default, judgment**: start from the market's long-run median realised vol)" (L1563); `other_markets: {estimator: sma, window: 20, target_ann: null, cap: 1.0}` (L4293). `vt > 1.0` fails validation (L1563). Missing rules-store keys the owner must sign first [R]: `sleeves.CRYPTO.notional_nav` (section 7 `sleeves` has only `US`, `KR`, L4462-4464) and the hard gross cap (no key or value printed) (F-24).
- Until then nothing is registered: no crypto book, no card, no FORWARD-SIM book, no rules-store rule object that is evaluable.

### B.8 FX instrument and FX sleeve (TASK-M10-02; R-17) — DEFERRED

[V] L1756: "**FX instrument.** An FX sleeve card declares its instrument, KRX USD futures or broker spot, before the run. A card without it is refused. FX costs 10 bp per side (P10)." P10 (L597): "An FX card declares its instrument: KRX USD futures or broker spot (R-17)." Header enum (L2808, L3947): `FX_KRX_USD_futures`, `FX_broker_spot`.

Predicate added to M0's `validate_card_header` / rule-object validation [R shape; the header schema has no `market` field, the rule object has `instrument_book`, `market` (L4702)]:
```
FX_BOOKS = {"FX_KRX_USD_futures", "FX_broker_spot"}
refuse (error names "R-17 / T-FX-01", nothing written, refusal logged in the store's edit history as in L6231) when
    rule.market == "FX" and header.instrument_book not in FX_BOOKS            # missing, null, or any other enum value
 or header.instrument_book == "multi_line" and any(line.market == "FX" and line.instrument_book not in FX_BOOKS)
 or header.instrument_book in FX_BOOKS and rule.market != "FX"                # an FX book on a non-FX card
```
- Costs: FX 10 bp per side, 20 bp at 2x, read from the gate's table, never from a header literal; "Lowering any cost in a header raises (DNB #23)" (L2800, T-COST-03).
- `FX_KRX_USD_futures` is a futures book: `roll_calendar` required and the R-26 granularity floor applies (one contract <= 5% of the sleeve notional; exactly 5% allowed, L2871). The contract multiplier is instrument metadata not printed in the spec.
- FX sleeve content [V] L1758-1768 (stored as DEFERRED rule text; nothing evaluable until a sleeve exists): "QUANTGEN's Rates & FX page currently withholds FX momentum and dollar carry as signals. Any FX sleeve is a new card set at FX cost (10 bp per side), on its declared instrument."
  - "**Never forecast FX direction from rate differentials.**" (item 14, L6141).
  - "**Carry is a crash-prone premium.** Size it small. De-risk it on: a USD/JPY trend break (0× below the 50-day average ...). That 0× belongs to a sleeve-level risk limit, not to an overlay (P2). JPY rv21 in its top quintile → 0.5× ... **Not** on VIX".
  - "**Confirmed intervention:** FX momentum × 0.5 for 20 sessions, and simulated stops × 1.5; no bet on a re-breach; USD/JPY 160-164 is the hazard zone (flag at the prior intervention maximum − 1.5%)." Calendar event type `FX_INTERVENTION` exists (L3819).
  - "**Long-KRW carry:** ... on quarter-end point-in-time FX, which tail calibration must use, skew −1.80 and worst quarter −43.8%; the current rate differential is −0.75 pp (negative carry)."
- Representation [R]: the 0x and 0.5x are risk-layer limits of the FX sleeve (0x may come only from the risk layer, L514), never overlay multipliers (overlays lie in [0.5, 1.0]); "simulated stops × 1.5" is a stop-distance scale, stored as `stop_distance_scale: 1.5`, never as a weight or multiplier field (so the `output_range` hi > 1.0 refusal, L4694, is not triggered and not weakened) (F-26).

---

## C. Schemas and config

### C.1 Keys read (rules store, section 7; "If a rule and this listing ever differ, the rule governs", L4132)

| Key | Value [V] | Line |
|---|---|---|
| `time.markets.CRYPTO` | `{tz: UTC, decision_utc: "00:00:00Z of d+1", venue_declared: true, annualisation_days: 365}` | L4163 |
| `vol_target.estimator_gate.fit` | `{window: expanding, min_years: 10, refit_every_origins: 21}` | L4298 |
| `vol_target.estimator_gate.fallback_to_sma20.gjr_bounds` | `{persistence_max: 0.9999, nu: [2, 100]}` | L4306 |
| `vol_target.estimator_gate.incumbent_calibration` | `{name: B5, var_level: 0.05, band: "+-2 binomial SE", min_origins: 200, pit: chi2_10_bins, pit_p_min: 0.01}` | L4308 |
| `vol_target.annualisation_days` | `252` | L4309 |
| `vol_target.display_labels` | `{rel: {method: trailing_756_quartiles}, abs: {method: expanding_full_history_quartiles, min_years: 10}, values: [calm, normal, elevated, stressed], filtered_only: true, acts: false, per_label_coverage: reported, scoring: tick_loss}` | L4312-4314 |
| `vol_target.other_markets` | `{estimator: sma, window: 20, target_ann: null, cap: 1.0}` | L4293 |
| `data.brent_series` | `{spot: DCOILBRENTEU, futures: BZ=F}` | L4221 |
| `sleeves` | `US: {line: none, notional_nav: null}`, `KR: {notional_nav: null}` (no CRYPTO, no FX entry) | L4462-4464 |
| `gate.costs` | `read_from_gate   # KRX ETF 3 bp, KRX stock 35 bp, US via KIS 50 bp, crypto 10, futures 5, FX 10; x2 stress` | L4616 |
| `reproducibility` | `{seed_study: 11, seed_research_bootstrap: 20261002, record: [git_hash, config_hash, data_snapshot_id, knowledge_utc, seed, results_md5, gate_package_version, gate_package_md5, ledger_hash_at_registration, ledger_hash_at_run], determinism: {canonical_json: sorted_keys_repr_floats_no_whitespace, volatile_fields: [generated_at_utc, git_hash], rng: numpy_pcg64_seedsequence_spawned_children, blas_threads: 1, relative_tol: 1.0e-12}}` | L4680-4684 |
| `do_not_build` labels | `8: inconclusive_B`; `11: {11a_ml_vol_state_classifiers: harm_E, 11b_range_log_har: admitted, ...}`; `14: {rate_differential_models: null_E, foreign_flow_rules: inconclusive_E}`; refused shapes `regime_model_source_acting_or_displayed: [11, 24, 27]`, `ml_classifier_estimator_gate_or_label: [11, 29]` | L4631-4638, L4666-4668 |

### C.2 Keys that do not exist and are proposed [R]

Section 7 has NO `quant_lab` block and no R-16 / R-17 rule object; R-16's numbers exist only in L1747 and L5701. "The store's model is immutable and has no financial defaults, so every number below must be written explicitly" (L4127). Proposed block, values copied from the rule text (F-14):
```yaml
quant_lab:                                # R-16, kind CONTEXT; proposed, not in section 7
  fit: {ref: vol_target.estimator_gate.fit}
  tails: {fhs: true, evt: {dist: gpd, side: lower, threshold_share: 0.10, method: mcneil_frey}}
  envelope: "max(fast_fhs, gjr_evt)"
  lines: {var_levels: [0.95, 0.99], es_level: 0.975, es_test: z2_simulated_critical_values, basel_zones: true, fan_pit_h: [21, 126]}
  report_periods: ["2016-26", "2026"]
  post_holiday: {reported_separately: true, var_display_scale: "sqrt(max(n_US, 1))"}
  acceptance: {sample: oos_2016_26, var99_kupiec_p_min: 0.05, var99_cc_p_min: 0.05, es975_z2_reject_level: 0.05,
               fan_pit_h21_chi2_p_min: 0.01, reported_not_gated: [fan_pit_h126, period_2026]}    # thresholds: default, judgment
  path_colour_label: "path-vol quartile"
  sep_band: {rmse_pp_1y: 1.4, sep_date: "2023-12-13", coverage: 0.70, read_latest: true}
  outputs: descriptive
```
Rule objects (section 7.1, L4693): `{rule_id: "R-16", kind: "CONTEXT", books: []}`; `{rule_id: "R-17", kind: "CONVENTION"}` kept non-evaluable while DEFERRED.

### C.3 Artifact fields read (section 6)

- `event_calendar` entry (L3827-3830): `"gap_sessions":{"type":["integer","null"],"minimum":0}`, `"var_display_scale":{"type":["number","null"],"description":"sqrt(max(n_US, 1)) for multi-session gaps; display only"}`, `"scenario_tag":{"type":["string","null"]}`; event `type` enum includes `"OIL_GEO"`, `"FX_INTERVENTION"`, `"KRX_HOLIDAY_GAP"` (L3819).
- `macro_state.vol.display_label_rel` / `display_label_abs`: enum `["calm","normal","elevated","stressed"]` (L3562-3565), for the per-label coverage table.
- `model_card_header.macro` (L3927-3990): `instrument_book` enum `["KRX_ETF_line","KRX_stock_book","KOSPI200_futures","mini_KOSPI200_futures","CME_micro_ES","US_shares_KIS","KRX_listed_SP500_ETF","crypto_venue","FX_KRX_USD_futures","FX_broker_spot","multi_line"]`; `instrument_lines[]` items `{market, instrument_book}`; `no_trade_band` enum `[0.0, 0.10]`; `nav_fx` `{series, history, conversion_instant, role}`; `roll_calendar` "futures books only".

### C.4 What this area writes

No section 6 artifact has a lab field, and R-16 has no "Outputs and schema fields" list, so T-SCHEMA-03 has nothing to validate for R-16 (F-15). Lab outputs: in-memory result objects; `docs/quant_lab/<symbol>.json` + `docs/quant_lab/manifest.json` (`run`, `seed`, `results_md5`, input md5s) from the docs script [R]. Tests write only to temporary directories (T-HERM-02, L5608).

---

## D. Tests

Tolerances (L5734-5737): window returns ±1 pp (Level 1), ±2 pp (Level 2, production feeds); p-values ±0.01 (p >= 0.05) and ±0.005 (p < 0.05); deterministic counts exact; "A verdict derived from a statistic within tolerance of its threshold is asserted as a class, never as a point". Tiers (L5496): `fast` (<= 10 min total), `golden` (<= 2 h). Hermetic (T-HERM-01 L5607): every network touchpoint patched to raise. A missing fixture is reported not-run, never a pass.

`runs_from` (L5560-5561): M9 = I-11, T-REPRO-01c; M10 = T-CRYPTO-01, T-FX-01. Section 9.0b (L5567-5595) lists NO deferred clause for any of these four tests.

Reference data on this machine: `/home/claude/quantgen_macro_data/` and `tests/fixtures/macro/` are absent. No `^KS11` file (`docs/asset_expansion/cache/yf__KS200.csv` has 1 row). Local closes only: `yf_069500.KS.csv` (KODEX 200, Yahoo adjusted, 2007-01-29 -> 2026-09-23, 4,274 rows), `yf_122630.KS.csv` (KODEX Leverage, 2010-02-22 -> 2026-09-23), `yf_SPY.csv` (1995-01-03 -> 2026-09-25), `yf_BTC-USD.csv` (2014-09-17 ->), `upbit_KRW-BTC.csv` (2017-09-25 -> 2026-09-25), `binance_BTCUSDT.csv` (2017-08-17 ->), `fred_DEXKOUS.csv` (2017 ->), `fred_DGS3MO.csv`, `yf_CL_F.csv` (WTI, not Brent). The tech-fund results folder has no daily index history.

### D.1 I-11 (L5701), clause by clause

| Clause [V] | Exact assertion | Fixture | Class |
|---|---|---|---|
| "GARCH/GJR parameters are fitted on expanding (≥ 10-year) windows." | `lab_fit` uses every return through the last date (`n_obs == len(r)`); the grading driver's fit at origin t reads `r[:t+1]` only (appending later data leaves earlier forecasts unchanged); refit every 21 origins; a series shorter than 10 years returns `status="insufficient_history"` and no graded line; no call passes a 504-row window. | simulated GJR-t series (`simulate_gjr_series`, n >= 3,000, synthetic dates spanning > 10 years) | SYNTH |
| "The lab shows max(fast FHS, GJR-EVT) with Kupiec, Christoffersen and ES Z2 lines, and reports 2016-26 and 2026 separately." | report has `model == "envelope"`, `components == ["fast_fhs","gjr_evt"]`; `env.var99 == np.maximum(fast_fhs.var99, gjr_evt.var99)` elementwise (same for `var95`, `es975`); keys `var95/var99` with `kupiec_p`, `cc_p`; `es975` with `z2`, `p`; `periods` has exactly the two keys `"2016-26"` and `"2026"` with different `n`; the headless page driver (pattern of `ui/quant_lab_page.py __main__`) finds the Kupiec, Christoffersen and ES Z2 line texts for both periods, and no lab path caption uses calm / normal / elevated / stressed; an injected EVT failure (`xi = 1.2`) withholds the envelope and shows `fast FHS` alone with the reason. | synthetic series with synthetic dates covering 2016-2026; injected `GpdFit(xi=1.2)` | SYNTH |
| "The replay library reproduces the Jul-2026 KOSPI path (−38.6% in 27 sessions) on the current book with regime metadata." | `run_replay` on the replay whose `replay_id == "KR-2026-06-23_07-30"`: `n_sessions == 27`; `index_return == -0.386 ± 0.01` (Level 1; ±0.02 on a production feed); `regime["at_start"]["price_limit"] == 0.30`; `book_return` present for a non-empty book; `acts is False`. | `^KS11` (or KRX official) closes 2026-06-22 -> 2026-07-30 (start close 9,114.55, L6441) + M1 regime-tag file + a book state | REFDATA. Local substitute, indicative only, never asserted as the golden: `yf_069500.KS.csv` gives −40.81% over the same 27 sessions. SYNTH companions: (i) a 28-close inline path built to fall exactly 38.6% in 27 returns with a stub `regime_tags`; (ii) `letf_path_return(-0.4081, 0.08121, 2) == -0.677 ± 0.001` and within 1 pp of the −68.4% of L2886 (inline numbers from the local cache). |
| "No lab output is read by a sizing module." | static AST scan of the sizing-module list of B.5 finds no import of `core.quant.lab`, `core.quant.montecarlo`, `core.ficc.ratesim`; every lab result class has `acts == False`; a planted import in a temp copy of a sizing module makes the scan fail. | repo source | SYNTH |
| "M9 acceptance is out-of-sample on 2016-26: 99% VaR with Kupiec p ≥ 0.05 and Christoffersen CC p ≥ 0.05; ES 97.5% Z2 not rejected at 5% (simulated critical values); fan PIT χ² p ≥ 0.01 at h = 21 (thresholds: default, judgment). The 2026-only lines are reported, not gated." | on the KOSPI fixture: `m9_gate(report)["status"] == "PASS"` with the four lines printed; `report["periods"]["2026"]` and `fan_pit.h126` present and absent from the gate's inputs. | KOSPI daily closes with >= 10 years before 2016 (i.e. from 2005 or earlier; the pilot used 2001-26, 6,346 days, and the M3 fixtures name `^KS11` from 1996-12) through 2026-10-02 (official close 7,003.74); KR + US session calendars for `gap_sessions`; rf history for the fan drift | REFDATA. Local substitute: KODEX 200 from 2007-01-29 reaches 10 years only in 2017-01, so it cannot cover 2016 and ends 2026-09-23: indicative run only. SYNTH companion (gate logic): `m9_gate` returns PASS / FAIL / NOT_RUN for injected line dicts at each threshold edge (0.0499 vs 0.05; 0.0099 vs 0.01; n = 199); on a simulated GJR-t series graded with the true-DGP forecast the 99% Kupiec line is not rejected, and with sigma x 0.6 it is. |

Pilot numbers (evidence, informative; not asserted unless a fixture names them; L1748): GJR-EVT on KOSPI 2001-26 (6,346 days): "99% VaR breaches 0.91% (Kupiec p 0.47), conditional-coverage p 0.19, ES Z2 −0.07 (p 0.23), Basel red 0 / yellow 2"; "the lab's GARCH-t-504: 1.48%, Z2 −0.47"; "the lab's GBM-504: 2.25%, 5 red"; "At h = 21 every fan sits within ±2 SE; at h = 126 the lab models fail PIT (p 0.001-0.007)"; "In 2026 every slow model under-covered (GJR-EVT 95% 6.5%, 99% 2.7%), and fast SMA20-FHS did best"; "After multi-session gaps, FHS 95% breaches reach 12.2% (n_US = 2) and 17.4% (n_US ≥ 3), against 4.8% (EX2)". Backlog: "GJR-EVT fails ES on 2016-26 (p 0.0125)" (BL1309) (F-9).

### D.2 T-REPRO-01c (L5668) — SYNTH

Assert, for `run_monte_carlo` (all four `MODELS`), `garch.simulate_returns`, `ratesim.simulate` (three models), `run_scenario` (each id with a synthetic panel) and `run_replay`: two runs with the same seed, the same rules-store hash, the same input arrays (`data_snapshot_id`) and the same package version give `max(|a - b| / max(|a|, 1e-300)) <= 1e-12` on every array output (`fan[p]`, `terminal`, `sample_paths`, rate `fan`, paths); a different seed changes a stochastic output; `repro` carries `seed`, `config_hash`, `data_snapshot_id`, `package_version`; no result depends on wall-clock time. Fixture: inline synthetic returns with fixed dates (not `synthetic_history`). Existing weaker tests stay: `test_mc_is_seeded_and_reproducible`, `test_mc_default_model_is_garch_t_seeded_and_reproducible`, `test_ratesim_is_seeded_and_reproducible`.

### D.3 T-CRYPTO-01 (L5657) — SYNTH (runs_from M10)

[V] "`decision_time_utc('CRYPTO', d)` = 00:00:00Z on d+1, the close of the venue's daily bar dated d; annualisation 365; weekday macro data joined as-of with staleness labels." Round-1 note (L5505): "T-CRYPTO-01 (00:00:00Z on d+1)".
- `decision_time_utc("CRYPTO", date(2026,10,2)) == datetime(2026,10,3,0,0,0,tzinfo=UTC)`; month/year ends (2026-12-31 -> 2027-01-01T00:00:00Z); Saturday and Sunday dates return a value (no `NotASession`); the result is tz-aware UTC.
- annualisation: sigma of a constant-variance daily series scales with `sqrt(365)`, and the equity path still uses 252.
- as-of join on a synthetic PIT store (the T-PROV-01-style fixture): Friday value joined to Saturday and Sunday decisions with `carried_days` 1 and 2 and `staleness == "fresh"`; a missed scheduled release -> `"stale_missed_release"`; a value with `available_at_utc > decision_utc` is not used; no interpolated value appears.
- a panel that mixes `CBBTCUSD` with a UTC candle series raises; an undeclared venue raises.

### D.4 T-FX-01 (L5658) — SYNTH (runs_from M10)

[V] "An FX sleeve card without a declared instrument (KRX USD futures or broker spot) is refused."
- header for a `market: FX` card with `instrument_book` missing / `null` / `"KRX_ETF_line"` / `"crypto_venue"` -> refused, error names R-17, the temp store is byte-identical afterwards; with `"FX_KRX_USD_futures"` (+ `roll_calendar`) or `"FX_broker_spot"` -> accepted by this predicate; `multi_line` with an FX line lacking an FX book -> refused; a header carrying a cost literal below 10 bp raises (T-COST-03 unchanged). Fixture: the section 8.4 header example with a typed FX variant, validated in a temp copy of the rules store.

### D.5 Neighbouring tests this area must keep green (owned elsewhere)

I-06b / I-06c (M5, L5695-5696: `gap_sessions`, "√max(n_US, 1)", zero-gap session unscaled); T-LABEL-01 (M2, causal labels); T-DNB-01 (M0: regime-model state displayed, ML classifier as "estimator, gate or label source"); T-CTX-01 (M6 import-guard pattern); T-BOOK-01 / T-COST-03 (M0 header refusals); T-CLOSE-01/02, T-REGIME-01 (M1); T-RO-01 (no order path in any new module); existing `tests/quant_acceptance.py` Monte Carlo/GARCH tests and `tests/ficc_acceptance.py` ratesim tests (signatures and `MODELS` unchanged).

---

## E. Interfaces

### E.1 Needed from earlier milestones

| From | What | Shape |
|---|---|---|
| M0 | rules store with the C.1 keys; `validate_card_header` and rule-object validation (TASK-M0-13); DNB predicates (T-DNB-01); `reproducibility.record` hashing helpers; cost-table reference | config dict; `core/rules` validators |
| M1 | `pit_value` + `RunContext{decision_utc, knowledge_utc, run_mode}` + `data_snapshot_id(knowledge_utc)`; history channel with >= 10 years of official closes; `decision_time_utc(market, session_date)`, `close_print_bound_utc`, `is_session`; `regime_tags(market, d) -> dict` (TASK-M1-04); `is_stale(series_id, decision_utc, knowledge_utc) -> StaleCheck`; fixture manifest loader | L998-1040 |
| M2 | `sma_vol` (SMA20, ddof = 1, simple returns); causal `display_label_rel` | arrays / label per date |
| M3 | `vol_estimators.garch_t`, `gjr_t` (expanding >= 10 years, refit every 21), `gjr_fit_ok`; `forecast_eval.b5`, `es_z2`, `fan_pit`, tick loss; `docs/vol_backtest/manifest.json` | `VarForecast{name, h, var, ok, reason}`; dicts |
| M5 | `gap_sessions(market, session_date) -> int` and the event-calendar fields `gap_sessions`, `var_display_scale`, `scenario_tag` (TASK-M5-09); the simulated books and their persisted state (TASK-M5-12); leveraged-ETF look-through L | L1041, L3827-3830 |
| M6 | context store entry for the SEP Table-2 band (R-13 "Policy" item) | context read with vintage |
| M7 / M8 | only if a crypto or FX sleeve is created: `docs/macro_overlay_study.py` card runner, `cards/verdicts.jsonl`, the frozen gate package, FORWARD-SIM books, `verdict_filter` | TASK-M7-19, R-35 |

### E.2 Exposed to later consumers

| To | What | Shape |
|---|---|---|
| Quant Lab page | `lab_fit`, `TailLine`, grading report dict, `m9_gate` status, `SCENARIOS`, `REPLAYS`, `run_scenario`, `run_replay` | section B |
| Rates page / lab | `ratesim.sep_band_params(params, *, rmse_pp, horizon_years=1.0, coverage=0.70) -> ShortRateParams` | B.4 |
| R-10 calendar entries | scenario and replay ids usable as `scenario_tag` values | strings |
| Any future L/I ETF display | `letf_path_return(R, sum_r2, L, carry=0.0) -> float` | B.4 |
| ST-06 (backlog, not v2) | the replay library as the benchmark GMM scenarios must beat on 99% ES coverage with >= 90% label agreement (BL266, L5479) | nothing built |
| A future crypto / FX sleeve | `decision_time_utc("CRYPTO", d)`, `annualisation_days("CRYPTO") = 365`, `asof_join`, the FX-book header predicate | B.7, B.8 |
| No sizing module | nothing. The lab exports no function a sizing module may import (rule (6)). | — |

---

## F. Ambiguities, contradictions and conservative readings

| # | Issue (lines) | Conservative reading used above |
|---|---|---|
| F-1 | Spec packages: R-16 names `core/quant/garch`, `core/quant/montecarlo`, `core/ficc/ratesim` (L1742); the import guard of rule (6) cannot forbid `core.quant.garch` because R-30's estimators reuse its fit. | Lab-only code in one new module `core/quant/lab.py`; `garch.py` / `gjr.py` untouched; guard forbids `lab`, `montecarlo`, `ratesim` in sizing modules. |
| F-2 | Stationarity bound for lab fits not printed; R-30 uses 0.9999 (L3187), existing lab code 0.9995. | Interactive fit keeps 0.9995 (existing tests); graded rolling fits reuse M3's drivers at 0.9999. |
| F-3 | "at least 10 years" (L1747): sessions or calendar years not said. | Calendar span of 10 years between the first return date and the origin. |
| F-4 | Behaviour with less than 10 years of history not printed. | `status="insufficient_history"`: fan drawn with an error-toned label, no 1-day VaR, no grading; never presented as calibrated. |
| F-5 | The lab's loader caps Yahoo at `"10y"` (`core/ficc/data._period_for`), so a Yahoo-sourced fit can miss the 10-year floor by days; `load_history` is not a PIT read. | Lab reads the M1 history channel when present; otherwise the loader needs a `"max"` period. Until one exists, Yahoo-sourced symbols show `insufficient_history`. |
| F-6 | "fast FHS" is not defined in R-16; evidence text says "fast SMA20-FHS" (L1748, BL1309). | fast FHS = FHS with SMA20 sigma, expanding residual pool. |
| F-7 | GPD threshold, estimator, quantile/ES formulas and refit cadence are not printed ("a GPD on the lower 10% of standardised residuals (McNeil-Frey)" only). | Standard McNeil-Frey POT with ML GPD, k = floor(0.10 n), 21-origin refit; failure -> envelope withheld. |
| F-8 | "A 1-day VaR display comes only from a model that passes 1-day B5" (L1747) vs an envelope of two models (a max is conservative and may itself fall below the B5 band). | B5 is applied to each component model, not to the envelope; a failing component withholds the envelope's 1-day number. |
| F-9 | I-11 does not say which model or market the thresholds apply to. Pilot: GJR-EVT passes on 2001-26 (Z2 p 0.23, L1748); backlog: "GJR-EVT fails ES on 2016-26 (p 0.0125)" (BL1309), i.e. GJR-EVT alone would fail the 2016-26 ES line. | Gate subject = the displayed envelope on the KOSPI fixture; component lines printed. If the gate fails on the reference data it is reported as FAIL; no threshold or model is changed after seeing the result; no exposure depends on it. |
| F-10 | "Basel zones" (L1747) vs the pilot's "Basel red 0 / yellow 2" (a count of windows); the window rule is not printed. | Show the last-250-origin zone (existing `traffic_light`) and counts over non-overlapping 250-origin windows. |
| F-11 | Fan PIT: which fan model, which drift, overlapping or not are open ("Fan acceptance. For 126-252-session fans, which drift and which overlapping-origin test define acceptance? (QF6) → R-16", BL1917); R-16 does not answer. | Gated h = 21 line: default fan model on the expanding fit, drift as displayed, non-overlapping origins, chi-square 10 bins; overlapping line and other models printed with their own labels; h = 126 never gated. |
| F-12 | "Path colours are renamed 'path-vol quartile'" (L481, L1747): no such colouring or label exists in `ui/quant_lab_page.py` / `ui/qcharts.py`. | Nothing to rename; the caption `path-vol quartile` is mandatory if such colouring is added; R-06 label words never appear on lab paths. |
| F-13 | "2016-26" and "2026" bounds not printed (G-B5-01 uses 2016-03 -> 2026-10 for a different statistic). | First session of 2016 / of 2026 through the fixture's last official close (2026-10-02). |
| F-14 | No rules-store keys for R-16 (section 7 silent) although the store "has no financial defaults" (L4127). | Proposed `quant_lab` block (C.2) with the rule's numbers; coordinator decides; the rule text governs. |
| F-15 | No section 6 schema or "Outputs and schema fields" list for R-16. | No section 6 artifact is written or extended; report is a docs-style JSON. |
| F-16 | Scenario (a): the event anchors t0 and the meaning of "+20 days" (sessions vs calendar days; whose sessions) are not printed; the Brent series per scenario is not printed. | 20 sessions of the market concerned; 2026 anchor = 2026-02-27 (section 8.6 window start); 2022 anchor is an owner/fixture input: without it the scenario returns `missing_input`. The printed moves are asserted only against a frozen fixture. |
| F-17 | Seed of the scenario library not printed; existing lab seed 7; study seed 11. | Library default 11, always recorded; interactive fan unchanged at 7. |
| F-18 | How SEP error bands become rate-path uncertainty "through `core/ficc/ratesim`" is not printed; "±1.4 pp ... about 70% coverage ... 90% fan needs about ±2.2 pp". | Rescale the model's sigma so the terminal sd at 1 year equals 1.4 / Phi^-1(0.85) pp (reproduces 2.22 pp at 90%); kappa and theta untouched; value read as context with vintage, Dec-2023 value labelled stale if nothing newer is stored. |
| F-19 | Replay entries are given as months or single days ("1997-11/12", "2008-10", "2000-04-17"); exact windows not printed; only the last is a dated range. | Month entries = all sessions of those calendar months; single days = that session; the list is fixed in code and md5-listed. |
| F-20 | "the current simulated book" (L1747): which book, static or re-decided weights, and the treatment of instruments that did not exist in the window are not printed. | Recommended book's current weights held static; missing instruments use a declared proxy or are listed `unmapped` at zero return; never silent. |
| F-21 | `close_print_bound_utc` for CRYPTO not printed. | Equal to `decision_time_utc` (0 s), the non-KR/US default. |
| F-22 | "joined as-of, with staleness labels" (L1755): label vocabulary not printed. | R-19 schedule-aware label plus `carried_days`; weekend carry is `fresh`. |
| F-23 | "declared per venue (Upbit, Binance, CoinGecko)": the declaration's form is not printed; no CoinGecko client exists; CoinGecko daily points are commonly stamped at the bar close. | One calendar-data row per venue; a series not closing at 00:00:00Z of d+1 is refused or re-dated explicitly; `CBBTCUSD` never joins a UTC candle panel. |
| F-24 | Crypto card parameters not printed: vol target level, hard gross cap value and key, beta window, `sleeves.CRYPTO.notional_nav`. | Owner inputs before any header commit; nothing registered until then (R-17 is DEFERRED). |
| F-25 | Existing `core/crypto/analytics.kimchi_premium` forward-fills FRED `DEXKOUS` by date onto UTC-midnight closes (H.10 publishes later, item 19). | Descriptive page statistic, not part of M10; flagged for the data-layer owner; a crypto sleeve may not read it. |
| F-26 | "simulated stops × 1.5" and "0× below the 50-day average" (L1761-1765) vs "No multiplier anywhere may exceed 1.0" and "0× comes only from the risk layer" (L513-514). | 0x / 0.5x are FX-sleeve risk-layer limits; 1.5 is a stop-distance scale stored under its own field name, never a weight. |
| F-27 | FX cost: P10 says 10 bp per side (L589); the existing study runs dollar carry at `COST["fx"] / 2` and `carry_backtest` defaults to 5 bp. | Any FX sleeve card reads 10 bp from the gate table; the existing descriptive defaults are not reused for a card. |
| F-28 | R-16 (3) says "√n_US"; R-10 and I-06b say "√max(n_US, 1)" (L1631, L5505, L5695). | `sqrt(max(n_US, 1))`. |
| F-29 | Whether graded VaR lines use the gap-scaled or the unscaled series is not printed; the 2027-28 out-of-sample breach check of the scaling is pre-registered (L1631, L5485). | Gate on the series as displayed (scaled); print the unscaled line and the per-bucket breach rates beside it. |
| F-30 | Return convention for lab fits: existing lab uses log returns; R-06 / R-30 use simple returns (L1561, L5721). | Lab keeps log returns for its own fits and records `returns` in the report; the fast-FHS sigma is M2's SMA20 on simple returns. |
| F-31 | ES Z2 "simulated critical values" for an envelope of two models: the simulating law is not printed. | Simulate under the GJR-EVT predictive law (empirical body + GPD lower tail), 2,000 simulations, seed 11; components' own Z2 lines printed. |
| F-32 | T-REPRO-01c inherits "gate package version" from T-REPRO-01b although the lab is not gated. | Record the gate package version when one exists, else the app/package version. |
| F-33 | M10 is DEFERRED ("when those sleeves exist") yet T-CRYPTO-01 / T-FX-01 are hermetic and need no sleeve. | Build only the clock branch, the header predicate, the as-of helper and the two tests; create no sleeve, book, card or FORWARD-SIM book. |
| F-34 | Tech-fund XS-17 (crypto ST reversal 2 -> 0, type "Supersession") and OQ-09 (C3 prior 2 vs 3) change R-15 priors that a crypto sleeve would read. | Priors are rules-store data owned by M4; M10 hard-codes none; no crypto family acts. |
| F-35 | `prep/readlines.py` in the scratchpad has a syntax error; long lines were read with an equivalent ad hoc printer. | No effect on content. |

---

## G. DO-NOT-BUILD items and invariants binding this area

| Item | Text / rule | Source |
|---|---|---|
| 11a | "**ML vol-state classifiers stay prohibited:** elastic-net, gradient-boosting or any other ML classifier of the next-month volatility state, as a sizing, gating or display input." The lab is a display: none there either. | L6119, L1747 (2) |
| 11c | No smoothed regime probabilities; no unpenalised daily HMM / Markov-switching gates. | L6122-6123 |
| 27 | "No regime-model state (jump model, Markov switching, GMM label or change-point "regime") acts on exposure or is displayed on any QUANTGEN page in v2." "GMM scenarios stay deferred behind the replay library and are never labelled as a current regime (R-16)." | L6187-6190, P19 L653-656 |
| 24 / 28 | No smoothed or forward-looking calm/normal/elevated/stressed labels; no conformal layer on the display labels; "Per-label coverage reporting stays (R-06)". | L6175, L6199 |
| 25 | "Any model as the sizing estimator, except through the staged estimator gate (R-30) as a counted card revision that passes the full v2 CARD-P". A lab fit never sizes. | L6176 |
| 30 | No `max(σ̂_SMA20, implied)` sizing; implied vol is context. | L6201-6205 |
| 19 | "an unnamed 'Brent'"; "Yahoo continuous-futures returns across rolls"; "intraday circuit-breaker prints as closes". Every scenario names `DCOILBRENTEU` or `BZ=F`. | L6148-6155 |
| 7 | No lagged oil-price gate on equity or KOSPI gross; oil scenarios are descriptive ("No exposure gate", L1633). | L6102 |
| 8 | "Net-liquidity (WALCL − TGA − RRP) or M2 rules for crypto or equities"; R-17: "no net-liquidity or M2 input (§10)". | L6103, L1773 |
| 14 | "Rate-differential models of USD/KRW direction"; R-17: "Never forecast FX direction from rate differentials." | L6141-6143, L1759 |
| 21 | No order, cancel, withdrawal, deposit-address or transfer path; `data/crypto/crypto_client.py` stays read-only ("There is no order path in this class or this module"). | L6162, P0 L491-500 |
| 22 | No non-PASS card output as a recommendation; a deferred crypto / FX card is NOT_RUN and reaches no recommended book; "FORWARD-SIM first". | L6163, L6372 |
| 23 / 32 | Instrument book, notional, rebalance, band and cost are fixed before the run; another venue is a new card. Applies to `crypto_venue`, `FX_KRX_USD_futures`, `FX_broker_spot`. | L6170-6174, L6211 |
| 2 | No multiplier, weight or vol-target cap above 1.0; crypto vt cap 1.0. | L6077, L1563 |
| TF DNB-TF-16 / DNB-TF-17 | Crypto short-term reversal weight 0; G10 FX technical rules weight 0 (tech-fund list; proposal XS-19 adds them to section 10). | R3:471-476, R3:892-893, R3:1307 |
| Invariant | "No lab output is read by a sizing module." | L1747 (6), I-11 |
| Invariant | SMA20 is the only sizing estimator; it changes only through R-30. | L1747 (2) |
| Invariant | "a σ̂ is never shown as a normal VaR"; 1-day VaR only from a model that passes 1-day B5. | L1561, L1747 (2) |
| Invariant | "Rate paths go through `core/ficc/ratesim` (Vasicek / CIR / Hull-White), not through a log-return price model". | L1747 (4) |
| Invariant | "**No event tag changes any weight.**" (`scenario_tag`, gap flags are annotations and display inputs). | L1634 |
| Invariant | Missing or stale inputs are labelled, never interpolated; SYNTHETIC history is loudly labelled and never graded. | P5 L542-548 |
| Invariant | Tests hermetic; temp copies only; no fixture built from `synthetic_history` (its dates end today). | L5491-5495 |
| Invariant | No new dependency: scipy (`genpareto`, `norm`) and numpy cover everything here. | repo `requirements.txt` |
