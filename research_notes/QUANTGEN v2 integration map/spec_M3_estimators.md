# spec_M3_estimators — R-30 estimator family, forecast-evaluation harness, B5, staged gate, fail-closed fallback

Sources. Spec = `QUANTGEN_Quant_Council_2026-10-03/claude_code/QUANTGEN_MACRO_INTEGRATION.md` (`L####` = line). Read in full: R-30 L3155-3261, R-16 L1742-1749, R-06 L1554-1577, section 9 rows for every cited test, 9.0a/9.0b L5544-5598, 7 `vol_target` L4286-4315, 6.1 `vol` L3548-3568, 6.5 `forecast_eval` L4057-4059, 10 items 11/25/28/29/30 and 10.3. Backlog BL-C04 (L554-618) and BL-G01 (L1277-1321) of `QUANTGEN_MACRO_BACKLOG.md`. Tasks: `TASK-M3-01..05`. The tech-fund R3 synthesis (`R3_TF_neural_link.md`) contains no amendment to R-30, the estimators or B5 (grep: no hits).

Transliteration: inside quotes, the spec's symbols are written in ASCII (sigma-hat -> `sigma`, Delta -> `d` as in `dSR`/`dMDD`, plus-minus -> `+-`, nu/alpha/beta/gamma/omega/lambda spelled out, `<=`/`>=`). Config keys, enum strings and numbers are character-exact.

Markers: **[V]** = verbatim/binding text of the spec. **[R]** = this note's reading where the spec is silent (each one is listed in section F). Spec paths and function names marked "proposed" may be renamed (L89, L963); field names, parameters, bounds, formulas, thresholds are binding (L89).

---

## A. Scope

| Task | Deliverable (one line) | Target files |
|---|---|---|
| TASK-M3-01 | Estimator family: `sma20`, `ewma094`, `ewma097`, `garch_t`, `gjr_t`, range proxy, `log_har_range`, `comb`; all emit h-step variance forecasts of y[t,h] = sum of r^2 over the next h days. No ML vol-state classifier. Unlocks the EWMA(0.94) clause of G-US-01c. | NEW `core/quant/vol_estimators.py` (spec name: `core/quant/garch`); MODIFY `core/quant/garch.py`, `core/quant/gjr.py` (kw-only `stationarity_max`, multi-step forecast helper) |
| TASK-M3-02 | Forecast registry + forecast-evaluation harness: losses (QLIKE, MSE, tick), DM (+HLN), Clark-West, Giacomini-White, MCS (T_max, stationary bootstrap), Kupiec, Christoffersen CC, ES Z2, fan PIT(h), reliability table. | NEW `core/quant/forecast_eval.py` (spec name: `core/quant/backtest`, proposed); MODIFY `core/quant/validate.py` (`dm_test` gains `h`/HLN; reuse `kupiec`, `christoffersen`, `pit_tests`) |
| TASK-M3-03 | Publish `docs/vol_backtest.py` (B5: rolling origins, FHS and model forms, PIT) with its seed; rerun B5 on SPY and KODEX 200 for 2016-26; expose incumbent B5 status for R-21's cap (wired M7). | NEW `docs/vol_backtest.py`; output dir NEW `docs/vol_backtest/` (results.csv + manifest.json with seed and md5, same shape as `docs/asset_expansion/manifest.json`) |
| TASK-M3-04 | `estimator_gate()` Stages 1-3 returning `status` in {`registered_default`, `challenger_selected`, `fallback_to_sma20`, `NOT_RUN`}; SMA20 stays acting. | `core/quant/forecast_eval.py` (`estimator_gate`, `EstimatorSelection`, `sized_book`) |
| TASK-M3-05 | Fail-closed fallback to SMA20 per decision (GJR bounds, range-proxy quality flag, any challenger-path failure); no blend; no stale challenger forecast. | `core/quant/vol_estimators.py` (`gjr_fit_ok`, `range_quality_flag`, `sigma_for_decision`) |
| (tests) | Hermetic synthetic tests + fixture-gated golden reproductions. | NEW `tests/estimator_acceptance.py`; MODIFY `tests/run_all.py` (register; see F-20) |

File-layout facts (existing code): `core/quant/backtest.py` is a 155-line single module (`run_backtest`, `BacktestResult`) imported by `ui/signals_page.py`, `ui/qcharts.py`, `core/quant/insights.py`, `tests/quant_acceptance.py`. `core/quant/garch.py` (753 lines) is the Quant Lab GARCH(1,1)-t fit/simulator; `core/quant/gjr.py` (236 lines) is `fit_gjr` (t / normal / Hansen skew-t). Neither is a package. Recommendation: keep both importable as they are and add the two new sibling modules above instead of converting `backtest`/`garch` into packages (decision for the coordinator; M7's gate package also targets `core/quant/backtest`).

---

## B. Build spec

### B.0 Conventions that bind every function here

| Item | Value | Source |
|---|---|---|
| Returns | simple daily close-to-close returns | L1561, L4310, L5721 |
| Forecast target | `y[t, h] = sum_{j=1..h} r^2_{t+j}`, forecast made at the close of t from data through t | L3179 |
| Units | daily variance units summed over h ("variance units"); annualise with 252 | L3189, L4309 |
| Horizons evaluated | h = 1, 5, 21; sizing horizon = 21 | L3190, L3243, L5910 |
| Selection loss | QLIKE, pre-declared | L3183 |
| Fit schedule (fitted models) | `fit: {window: expanding, min_years: 10, refit_every_origins: 21}` | L3216 |
| Seeds / resamples | MCS: `B=2000`, `seed=11`, `block=max(10, 2h)`; study seed 11 | L3172, L3219 |
| Inputs | daily OHLC with `value_status` and the open-quality and range-quality flags; official closes; the card's declared instrument book and cost | L3178-3180 |
| Stale-carry day | excluded from the SMA20 window; window extends to the last 20 valid returns | L1561 |
| Data access in `core/` | only through `pit_value(...)` with `RunContext{decision_utc, knowledge_utc, run_mode}`; never a raw DataFrame, never "now" | L1105-1106 |

Design rule for testability [R]: every statistical function is a pure function on numpy arrays (no I/O); one thin wrapper (`estimator_gate`) pulls series through the M1 PIT layer. Hermetic tests call the pure layer.

### B.1 `core/quant/vol_estimators.py` (NEW) — R-30 rule 2

Estimator names [V] (the only legal values of `macro_state.vol.estimator`, L3230, L3549): `sma20`, `ewma094`, `ewma097`, `garch_t`, `gjr_t`, `log_har_range`, `comb`.

Rule-object `estimator = {name, kind}`, `kind` in {`sma`, `ewma`, `garch`, `har`, `comb`, `ml`} (L4700). Map [R]: sma20->sma; ewma094, ewma097->ewma; garch_t, gjr_t->garch; log_har_range->har; comb->comb. `ml` is refused (items 11a, 29).

Complexity order [V] (L3198, L3222): `[sma20, ewma094, ewma097, garch_t, gjr_t, log_har_range, comb]`.

```python
@dataclass(frozen=True)
class OHLC:                       # arrays aligned by session, ascending
    dates: tuple[str, ...]; open: np.ndarray; high: np.ndarray; low: np.ndarray; close: np.ndarray
    stale_carry: np.ndarray       # bool; M1 flag flat_ohlc_zero_volume_on_session_day (L4209)

@dataclass(frozen=True)
class VarForecast:
    name: str; h: int
    var: np.ndarray               # len T; var[t] = forecast of sum_{j=1..h} r^2_{t+j} made at close t; NaN before warm-up
    ok: np.ndarray                # bool per origin; False => challenger path failed at t (fallback applies)
    reason: tuple[str | None, ...]  # per origin: None | "gjr_bounds" | "gjr_not_converged" | "open_quality" | "flat_range" | "insufficient_history" | "proxy_nonpositive" | "error:<type>"

def sma(r, h, window=20) -> VarForecast
def ewma(r, h, lam) -> VarForecast                      # lam in {0.94, 0.97}
def garch_t(r, h, *, min_years=10, refit_every=21, persistence_max=0.9999, nu_bounds=(2, 100)) -> VarForecast
def gjr_t(r, h, *, min_years=10, refit_every=21, persistence_max=0.9999, nu_bounds=(2, 100)) -> VarForecast
def range_proxy(ohlc: OHLC, market: str) -> np.ndarray  # p_t, daily variance units
def range_quality_flag(ohlc: OHLC, market: str, *, max_share=0.05, window_sessions=252) -> np.ndarray  # bool per session, True = tripped
def log_har_range(r, ohlc, market, h, *, min_years=10, refit_every=21) -> VarForecast
def comb(r, ohlc, market, h, **fit_kw) -> VarForecast   # 0.5 * (gjr_t + log_har_range), variance units
def forecast(name: str, r, h, *, ohlc=None, market=None, **kw) -> VarForecast   # registry dispatch; unknown name -> ValueError
def gjr_fit_ok(fit) -> tuple[bool, str | None]
def sigma_for_decision(declared: str, r, *, ohlc=None, market=None, h=21) -> SigmaDecision
```

| Estimator | Exact definition | Source |
|---|---|---|
| `sma20` | [V] "SMA20 = h x the sample variance of the last 20 returns". Sample variance = mean-adjusted, `ddof = 1` (L1561: "the mean-adjusted sample SD (ddof = 1, R-30's 'sample variance')"). `var[t] = h * np.var(r[t-19..t], ddof=1)`. Acting sigma: `sigma_m(t) = stdev(r_m[t-19 .. t]) x sqrt(252)`; must reproduce rv20 28.82% and vt 0.694 on 2 Oct 2026. Reuse M2's `core.quant.risk.sma_vol` for the valid-return window (stale-carry exclusion); do not re-implement it. | L3185, L1561, L5673 |
| `ewma094`, `ewma097` | [V] "EWMA(lambda), RiskMetrics recursion", lambda = 0.94, 0.97. [R] `s2[t+1] = lam*s2[t] + (1-lam)*r[t]**2` (zero mean); `var[t] = h * s2[t+1]`; initial `s2` = sample variance of the first 20 returns; first usable origin after 20 returns (F-3). | L3186, L3222 |
| `garch_t` | [V] GARCH(1,1)-t, constant mean, expanding windows of >= 10 years, refit every 21 origins, constrained to `alpha + beta + gamma/2 <= 0.9999` (gamma = 0). Reuse `core.quant.garch.fit_garch(r_window, dist="t", profile=False)`. [R] between refits the parameters are held and the variance recursion is filtered daily with each new return; `var[t] = sum_{j=1..h} E[s2_{t+j}]`, `E[s2_{t+j}] = s2bar + p**(j-1) * (s2_{t+1} - s2bar)`, `p = alpha + beta`, `s2bar = omega / (1 - p)`. | L3167, L3187 |
| `gjr_t` | [V] "GJR-GARCH(1,1)-t with constant mean on expanding windows of >= 10 years, refit every 21 origins"; same constraint. Reuse `core.quant.gjr.fit_gjr(r_window, dist="t")` and `next_variance`. [R] multi-step as above with `p = alpha + beta + gamma/2`. `dist="skewt"` is NOT an R-30 estimator (L482 "The skewed-t stays out of the menu"; item 25 "the skewed-t is untested"). | L3167, L3187 |
| range proxy `p` | [V] `range_proxy: {KR: overnight_sq_plus_garman_klass, US: parkinson}`; "overnight^2 + Garman-Klass for KOSPI and Parkinson for the US", computed from regular-session OHLC. [R] standard definitions (not printed in the spec): KR `p_t = ln(O_t/C_{t-1})**2 + 0.5*ln(H_t/L_t)**2 - (2*ln2 - 1)*ln(C_t/O_t)**2`; US `p_t = ln(H_t/L_t)**2 / (4*ln2)`. Any other market: no proxy registered -> `ok=False` (fallback). | L3188, L3217, L1747 |
| `log_har_range` | [V] "a direct h-step OLS of log(mean p over the next h) on [1, log p_t, log mean p_{t-4..t}, log mean p_{t-21..t}], rescaled to r^2 units by the expanding ratio sum r^2 / sum p". [R] at origin t: train rows s with s + h <= t only (targets fully realised), expanding window, coefficients refit every 21 origins; `m_hat = exp(x_t @ beta)`; `var[t] = h * m_hat * (sum_{s<=t} r_s**2 / sum_{s<=t} p_s)`. No separate Jensen term (the expanding ratio is the only rescale the spec names). Rows with `p <= 0` are dropped from the OLS; `p_t <= 0` at the origin -> `ok=False`, reason `proxy_nonpositive`. | L3188 |
| `comb` | [V] "COMB = 1/2 (GJR-t + log-HAR-range), in variance units"; config `definition: "0.5*(gjr_t + log_har_range)"`. `ok = gjr.ok & har.ok`; if either leg fails the result is not a one-legged COMB, it is a failure (fallback to SMA20, never a blend). | L3189, L3214 |

Fit-bounds check `gjr_fit_ok(fit)` [V] (L3203; config `gjr_bounds: {persistence_max: 0.9999, nu: [2, 100]}` L3224): OK iff `omega > 0`, `alpha >= 0`, `alpha + gamma >= 0`, `beta >= 0`, `alpha + beta + gamma/2 <= 0.9999`, `nu in (2, 100]`, `converged`. Anything else, or an exception in the fit, -> `ok=False`.

Existing-code deltas needed (smallest diff):
- `core/quant/garch.py`: `STATIONARITY_MAX = 0.9995` (L80 of the file), eta = 1/nu bounded `[0.0, 0.4]` (nu >= 2.5, nu = inf allowed). `core/quant/gjr.py`: `GAMMA_BOUNDS = (0.0, 0.5)`, persistence penalty at `STATIONARITY_MAX`. Add a keyword-only `stationarity_max: float = STATIONARITY_MAX` to `fit_garch` / `fit_gjr` (threaded to `_loglik`) so R-30 calls pass `0.9999` and every existing Quant Lab caller is unchanged. Do not change the module constants (the lab refit is M9/R-16).
- A fit that converges to effectively normal innovations (existing `nu = inf` or `nu > 100`) is outside `nu in (2, 100]` -> fallback under the literal rule (F-6).
- Existing docstrings say "daily log returns"; R-30 feeds simple returns (functions accept any array).
- Name collisions: `core.quant.signals.sma(px, n)` is a price SMA; `core.quant.strategies.ewma_vol(prices, com)` is a 261-day mean-adjusted log-return EWMA. Neither is an R-30 estimator; do not reuse them.

Quality flag `range_quality_flag` [V] (L3204; config `open_quality_max_share: 0.05`, `flat_range_max_share: 0.05`, `window_sessions: 252`, "thresholds: default, judgment"):
- Garman-Klass and the overnight leg (KR): tripped when "opens equal to the prior close on > 5% of the trailing 252 sessions".
- Parkinson (US): tripped when "high = low on > 5%" of the trailing 252 sessions.
- The per-row open flag is M1's `data.open_quality_flag: open_equals_prior_close` (L4212, L1326); the trailing share is computed here.

### B.2 Fail-closed fallback — R-30 rule 7 and "Fail-closed behaviour" (TASK-M3-05)

```python
@dataclass(frozen=True)
class SigmaDecision:
    sigma_ann: float | None        # sqrt(var_h / h * 252) of the estimator actually used
    estimator_used: str            # declared name, or "sma20" on fallback
    fallback_used: bool
    reason: str | None             # None when no fallback
```

Rules [V]:
1. Trigger (L3202-3204): "a GJR fit outside its bounds (omega > 0, alpha >= 0, alpha + gamma >= 0, beta >= 0, alpha + beta + gamma/2 <= 0.9999, nu in (2, 100], converged)" OR "the declared range proxy's quality flag tripping".
2. Wider trigger (L3235): "Any failure in the challenger path (fit, proxy, data) -> SMA20 for that decision, logged. Never a stale challenger forecast."
3. (L3206) "Forecasts are never blended with SMA20 as a partial fallback." On fallback `sigma_ann` equals SMA20's sigma exactly.
4. Scope: "for the decision" — per decision; the next decision re-evaluates the challenger.
5. Logged: `fallback_used=True`, `reason` set, `status="fallback_to_sma20"` in the gate object; plus one structured log line (F-14).
6. [R] A refit that fails at a refit origin does not silently keep the previous parameters: every decision until the next successful refit falls back (reading of "never a stale challenger forecast", F-7).
7. If SMA20 itself is unavailable (fewer than 20 valid returns, sigma 0 or not finite) the M2 contract applies unchanged: `insufficient_history` / `MissingInput` (L1562, L1047). The fallback never invents a value.

### B.3 `core/quant/forecast_eval.py` (NEW) — R-30 rule 1 and the harness (TASK-M3-02)

**Forecast registry** [V] (L3183): "Every forecaster and every 'X predicts Y' claim is registered with its target, horizon, loss, benchmark and test (QF7-M2). The selection loss is pre-declared as QLIKE." Section 12 M3 (L6365): "losses declared in advance (QLIKE; tick loss)".

```python
@dataclass(frozen=True)
class ForecastSpec:
    name: str; kind: str            # kind in {sma, ewma, garch, har, comb}; "ml" refused
    target: str                     # "sum_r2_next_h"  (y[t,h]) or a named claim target
    horizons: tuple[int, ...]       # (1, 5, 21)
    loss: str                       # "qlike" (selection) | "mse" | "tick"
    benchmark: str                  # "sma20"
    test: str                       # "mcs_T_max" | "dm_hln" | "cw" | "gw" | "kupiec" | "christoffersen_cc" | "es_z2" | "fan_pit" | "b5"
FORECAST_REGISTRY: dict[str, ForecastSpec]    # the 7 estimators pre-registered; in-module constant
def register_forecast(spec: ForecastSpec) -> None   # refuses kind "ml" (items 11a, 29), an estimator that takes max() over an implied-vol series (item 30), a duplicate name
def require_registered(name: str) -> ForecastSpec   # evaluation of an unregistered forecaster raises
```

**Loss registry** `loss_registry` [V] names: QLIKE, MSE, tick loss (L3170).

| Key | Formula | Note |
|---|---|---|
| `qlike` | [R] `y/f - ln(y/f) - 1` (Patton normalisation; same form as the existing `core/crypto/analytics.py` scorecard) | selection loss; ratio-to-SMA20 goldens depend on the form (F-8) |
| `mse` | `(y - f)**2` | printed |
| `tick` | `(alpha - 1{x < q}) * (x - q)` for a quantile forecast q at level alpha | scores VaR and the display labels (L1565, L4314 `scoring: tick_loss`) |

**Tests** (signatures per L3171-3173; "proposed" names):

| Function | Parameters [V] | Algorithm |
|---|---|---|
| `dm_test(loss_a, loss_b, *, h)` | "HAC with lags max(10, 2h), Harvey-Leybourne-Newbold factor" | Extend the existing `core.quant.validate.dm_test(loss_a, loss_b, *, lag=0)`: add `h: int | None = None`; when given, `lag = max(10, 2*h)`, multiply t by `sqrt((n + 1 - 2h + h(h-1)/n) / n)`, p from Student-t(n-1). Existing callers (`lag=5`, no `h`) unchanged. |
| `cw_test(y, f_small, f_large, *, h)` | Clark-West (nested models) | [R] `adj_t = (y-f_small)**2 - ((y-f_large)**2 - (f_small-f_large)**2)`; HAC t with lags max(10, 2h); one-sided p. No parameters printed in the spec. |
| `gw_test(loss_a, loss_b, *, h)` | Giacomini-White | [R] conditional predictive ability with instruments `[1, d_{t-1}]`, Wald chi-square(2), HAC lags max(10, 2h) for h > 1. No parameters printed. |
| `mcs(losses, stat='T_max', block=max(10, 2h), B=2000, seed=11)` | signature verbatim L3172; config `stage2: {loss: qlike, mcs_level: 0.90, stat: T_max, block: "max(10, 2h)", resamples: 2000, seed: 11, mse_mcs: printed}`; golden header: "T_max; stationary bootstrap, mean block max(10, 2h); B 2,000" (L5912) | see pseudo-code below; returns `{name: mcs_p}`; membership of the 90% set = `mcs_p >= 0.10` |
| `kupiec(hits, alpha)` | 95% and 99% | reuse `core.quant.validate.kupiec` unchanged |
| `christoffersen_cc(hits, alpha)` | independence and conditional coverage | reuse `core.quant.validate.christoffersen` (returns `p_ind`, `p_cc`); alias only |
| `es_z2(x, var, es, alpha=0.025, *, simulate, n_sim, seed)` | "Acerbi-Szekely, simulated critical values"; ES 97.5% | [R] `Z2 = sum_t(x_t * I_t / (T * alpha * ES_t)) + 1`, `I_t = 1{x_t < -VaR_t}`, ES_t > 0; negative = risk understated (matches the spec's printed "Z2 -0.47"). p = share of `n_sim` simulated Z2 <= observed, simulation from the model's own predictive law (FHS: resampled standardised residuals). `n_sim=2000`, `seed=11` (F-11). |
| `fan_pit(h)` | 21-day fan PIT at Stage 1; h = 21 and 126 at M9 | [R] `u_t = Fhat_{t,h}(R_{t->t+h})`; chi-square on 10 equal bins (reuse `validate.pit_tests(...)["chi2_p"]`). Origins sampled every h sessions for the gated p (F-10). |
| `reliability_table(forecast, realised, bins=10)` | named only | [R] equal-count forecast bins: mean forecast, mean realised, n per bin. |

MCS pseudo-code [R] (Hansen-Lunde-Nason, T_max; only the statistic, bootstrap type, block, B, seed and level are printed in the spec):
```
L: T x m loss matrix; M = all models; p_prev = 0; rng = default_rng(seed)
idx[b] = stationary-bootstrap indices (Politis-Romano), mean block = max(10, 2h), b = 1..B   # drawn once, reused at every step
while len(M) > 1:
    dbar_i   = mean_t(L[:, i]) - mean over j in M of mean_t(L[:, j])            for i in M
    dbar*_bi = same on L[idx[b]]
    var_i    = mean_b((dbar*_bi - dbar_i)**2)
    t_i      = dbar_i / sqrt(var_i);          T_max  = max_i t_i
    T*_b     = max_i((dbar*_bi - dbar_i) / sqrt(var_i))
    p        = mean_b(T*_b >= T_max);         p_prev = max(p_prev, p)
    e        = argmax_i t_i;   mcs_p[e] = p_prev;   M.remove(e)
mcs_p[last model] = 1.0
```
P-value resolution is 1/B = 0.0005 (golden "p <= 0.0005" = at most one resample).

**B5 (kept)** [V] (L1561, L3207, L3226 `incumbent_calibration: {name: B5, var_level: 0.05, band: "+-2 binomial SE", min_origins: 200, pit: chi2_10_bins, pit_p_min: 0.01}`): "B5 pass = 5% VaR exceedance within +-2 binomial SE of 5% over >= 200 origins **and** a PIT chi-square test (10 equal bins) with p >= 0.01."

```python
def b5(r, sigma_next, *, form="fhs", var_level=0.05, min_origins=200, pit_p_min=0.01, nu=None) -> dict
# sigma_next[t] = 1-day sigma forecast for day t+1 made at close t (daily units)
# returns {"status": "PASS"|"FAIL"|"NOT_RUN", "n_origins", "exceedance", "band": (lo, hi), "pit_chi2_p",
#          "kupiec": {...}, "christoffersen": {"p_ind", "p_cc"}, "form"}
```
- `band = 0.05 +- 2*sqrt(0.05*0.95/n)` (check: n = 2,594 -> 4.14-5.86%; n = 2,663 -> 4.16-5.84%; n = 8,961 -> 4.54-5.46%, L5801-5803).
- `status = "NOT_RUN"` when `n_origins < 200`; `"PASS"` iff exceedance inside the band and `pit_chi2_p >= 0.01`; else `"FAIL"`. Enum = `macro_state.vol.estimator_b5` `{"PASS","FAIL","NOT_RUN"}` (L3550).
- Forms: `"fhs"` (filtered historical simulation — the form used for sizing estimators), `"normal"`, `"t"` (t-quantile fan-tail, the app's own form). [V] "Under a normal quantile every estimator fails PIT, so a sigma is never shown as a normal VaR" (L1561).
- FHS [R]: `z_s = r_s / sigma_next[s-1]`; `VaR_{t+1} = sigma_next[t] * quantile_0.05({z_s: s <= t})`; hit = `r_{t+1} < VaR_{t+1}`; `PIT_{t+1} = ECDF_{z, s<=t}(r_{t+1} / sigma_next[t])`. Residual pool: expanding, first origin once 252 residuals exist (F-9).

**Sized book** (Stage 3 input; G-EST-04):
```python
def sized_book(r, var21, *, target_ann, cost_bps, cap=1.0) -> dict
# w[t] = min(cap, target_ann / sqrt(var21[t] / 21 * 252)); w decided at close t earns r[t+1]
# cost: per side x |dw|, charged on the day the weight earns; initial entry not charged (L5725)
# returns {"daily", "sharpe", "max_dd", "turnover_per_year", "vol_of_vol", "weights"}
```
- [V] vol-of-vol = "the SD of the book's rolling 63-session annualised realised vol" (L3197).
- [V] G-EST-04 configuration: "KOSPI 2001-26, 3 bp; sigma from each model's 21-day forecast; target 20%; cap 1" (L5932). `cap` above 1.0 is refused in `core/` (cap 1.0 permanent, L1563).
- `dMDD_vs_sma20 = max_dd(book) - max_dd(sma20 book)` in pp, positive = shallower (COMB -37.2% vs -40.0% = +2.8 pp).
- PC-2 [V] (L2157): "TR = mean(m on the worst 5% of overlay-off days) / mean(m on all days). It passes when TR <= 0.90".

### B.4 `estimator_gate()` — R-30 rules 3-6, 8 (TASK-M3-04)

Signature conflict: R-30 lists `estimator_gate(card) -> GateResult` (L3174); section 3.5 lists `estimator_gate(market: str, instrument_book: str, horizon: int = 21) -> EstimatorSelection` (L1101). Both "proposed". Build one function, one result type (F-1):

```python
@dataclass(frozen=True)
class EstimatorSelection:            # alias: GateResult
    estimator: str                   # enum of B.1; the ACTING estimator for this decision
    estimator_b5: str                # "PASS" | "FAIL" | "NOT_RUN"   (incumbent SMA20's B5)
    status: str                      # "registered_default" | "challenger_selected" | "fallback_to_sma20" | "NOT_RUN"
    stage1: dict | None
    stage2_mcs_p: float | None
    stage3_rank: int | None
    fallback_used: bool
    reason: str | None
    forecast_eval: dict | None       # card block, see C.3
    var_1d_displayable: bool         # True only if this estimator passes the 1-day B5

def estimator_gate(market: str, instrument_book: str, horizon: int = 21, *, ctx: RunContext,
                   declared: str = "sma20", card_id: str | None = None, revision: object | None = None) -> EstimatorSelection
def evaluate_estimators(r, ohlc, market, *, horizons=(1, 5, 21), names=COMPLEXITY_ORDER, oos_start=None, min_years=10) -> dict   # pure layer
def stage1(r, fc: VarForecast, *, horizon=21) -> dict
def stage2(losses_by_model: dict, *, h=21) -> dict           # {"qlike_mcs_p": {...}, "mse_mcs_p": {...}}
def stage3(books: dict, *, delta=0.10, ci_fn=None) -> dict   # ci_fn = R-24 bootstrap, supplied from M7; None at M3 -> rank None
```

`gate_dict = {status, stage1, stage2_mcs_p, stage3_rank, fallback_used, reason}` is exactly `macro_state.vol.estimator_gate` (L3231; schema L3551-3554, required: `status`, `fallback_used`). These `vol` fields are ACTING fields: a schema failure HALTs (OPS) the books (L3370 "the rest of `vol`"), so the function must always return a schema-valid object, including on internal error.

**Stage 1 (calibration; necessary for a challenger), at the 21-day sizing horizon** [V] L3190-3193; config `stage1: {horizon_days: 21, tests: [fhs_var_exceedance_h21, fan_pit_h21, christoffersen_cc], printed: [kupiec_1d, cc_1d_95_99, es975_z2]}`:
- gated: "FHS VaR exceedance at h = 21, the 21-day fan PIT and Christoffersen conditional coverage";
- "printed: the 1-day Kupiec and Christoffersen CC at 95% and 99%, and the ES 97.5% Z2";
- "a 1-day VaR is displayed only from a model that passes the 1-day B5".
- Report keys (use the config strings): `{"horizon_days": 21, "fhs_var_exceedance_h21": {...}, "fan_pit_h21": {...}, "christoffersen_cc": {...}, "printed": {"kupiec_1d": {...}, "cc_1d_95_99": {...}, "es975_z2": {...}}, "b5_1d": {...}, "pass": bool}`.
- Pass thresholds at h = 21 are not printed in R-30 (F-10). [R] exceedance inside +-2 binomial SE over >= 200 non-overlapping origins, fan PIT chi-square p >= 0.01, Christoffersen CC p >= 0.05; fewer than 200 origins -> Stage 1 not passed.

**Stage 2 (screen)** [V] L3194: "membership of the 90% QLIKE MCS at h = 21. The MSE MCS is printed." `stage2_mcs_p` = the estimator's QLIKE MCS p at h = 21; member iff p >= 0.10.

**Stage 3 (choice)** [V] L3195-3198; config `stage3: {objective: min_vol_of_vol_rolling63, eligibility: [dSR_noninferior_vs_sma20_delta_0p10, dMDD_vs_sma20_ge_0, pc2_le_0p90], ties: overlapping_bootstrap_ci, tie_break: simplest_surviving, complexity_order: [...]}`:
- "Each survivor's sized book is built at the card's declared instrument book and cost."
- "Eligible survivors: dSR vs the SMA20 book non-inferior at delta = 0.10 (R-24 bootstrap), dMDD vs SMA20 >= 0 and PC-2 <= 0.90."
- "The **lowest vol-of-vol** wins."
- "Overlapping bootstrap CIs are **ties**, and a tie goes to the simplest surviving model, in the order SMA20 < EWMA(0.94) < EWMA(0.97) < GARCH-t < GJR-t < log-HAR-range < COMB."
- At M3: compute the point statistics (Sharpe, max DD, turnover, vol-of-vol, dMDD, TR). CI, tie and rank logic need R-24's bootstrap and join at M7 (L5553; TASK-M7-28) -> `stage3_rank = None`.

**Switching rule** [V] L3199-3201; config `switch: {counted_revision: true, full_v2_card_p: true}`: "A challenger replaces SMA20 on a card only through a **counted card revision** (an R-23 ledger trial) that passes Stages 1-3 **and** the full v2 CARD-P. Never on the 35 bp stock book (log-HAR costs -0.063 Sharpe there, COMB -0.030). Never on the registered R-06 KR card, which keeps SMA20 as its primary configuration."

**Status logic at M3** (R-23 ledger and CARD-P do not exist before M7, so no challenger can be acting):

| Condition | `estimator` | `status` | Other fields |
|---|---|---|---|
| `declared == "sma20"` (every book at M3) | `sma20` | `registered_default` | `stage1/stage2_mcs_p/stage3_rank = None` allowed (spec example L3671), `fallback_used=False`, `reason=None` |
| `declared != "sma20"` and no counted revision (`revision is None`) | refused: raise `EstimatorSwitchRefused` at header/config validation; nothing written. T-B5-01's "An estimator switch without a counted revision is refused" runs from M3 (L5553, L5642). | — | M7 supplies the ledger-row proof and the `challenger_selected` path |
| `declared in {comb, log_har_range}` and `instrument_book` not in `books_allowed` | refused ("COMB or log-HAR on a stock book is refused", L3237) | — | `books_allowed: [KRX_ETF_line, KOSPI200_futures, mini_KOSPI200_futures, CME_micro_ES]`, `books_refused: [KRX_stock_book]`; any book in neither list is refused [R] (F-12) |
| `card_id == "MACRO-R06-KR-ETF"` (registered R-06 KR card) and `declared != "sma20"` | refused (L3201) | — | |
| counted revision accepted (M7+) and challenger path OK at this decision | challenger | `challenger_selected` | stage fields filled |
| counted revision accepted (M7+) and challenger path fails at this decision | `sma20` | `fallback_to_sma20` | `fallback_used=True`, `reason` set |
| gate not evaluated / insufficient history / internal error | `sma20` | `NOT_RUN` | `fallback_used=False`, `reason` = cause; `estimator_b5="NOT_RUN"` when B5 has < 200 origins (F-13) |

**Rule 8 — incumbent calibration feeds R-21's cap** [V] L3207: "SMA20 must keep passing B5 ... Its Stage-1 lines are printed as disclosure ('its KOSPI VaR breaches cluster'). A challenger must pass Stage 1. A failure caps the card at REVISE." M3 only exposes `estimator_b5` and `stage1["pass"]`; the cap (`gate.card_p_v2.caps.estimator_calibration_fail: REVISE`, L2216; reason code `estimator_calibration`, L5222; permitted fix "lengthen the holding period" as a counted revision, L2171) is wired in M7.

### B.5 `docs/vol_backtest.py` (NEW) — TASK-M3-03

| Requirement | Detail | Source |
|---|---|---|
| Content | "B5, rolling origins, FHS and model forms, PIT", "published with its seed" | L6365, L918 |
| Pass rule | section B.3 `b5()` | L1561 |
| Settling test | "Publish `docs/vol_backtest.py` and its seed; rerun B5 on SPY and KODEX 200 for 2016-26" -> "The app's GJR / GARCH-t B5 claim, which stays UNVERIFIED until then (R-30)" | L5484; backlog L1316-1317 ("reproduce the app's 6.6% breaches and PIT p 0.003") |
| Never | display sigma as a normal-quantile VaR | L1561 |
| Output | incumbent B5 status per market, for R-21's cap (M7) | TASK-M3-03 |

Facts about the app's existing study that this script must reproduce (repo, verified): `docs/asset_expansion_study.py` -> `run_garch(symbol, loader, cid, window=504, model)` -> `core.crypto.analytics.garch_scorecard(dates, close, window=504, refit=7, model)`; t-quantile form; data from 2012-01-01; `SEED = 11`. Stored cards (`docs/asset_expansion/cards/`): `D_Q_garch_spy` REJECT, 3,199 origins (2012-01-03 -> 2026-09-25), exceed95 0.06627, PIT KS p 0.00298; `D_Q_gjr_spy` REVISE, exceed95 0.06627, PIT KS p 0.01415; `D_Q_garch_kodex200` REJECT, 3,082 origins, exceed95 0.06619, KS p 0.00040; `D_Q_gjr_kodex200` REJECT, exceed95 0.06781. The app's "PIT p" is a KS p; the B5 rule uses chi-square on 10 bins (F-15).

Script shape [R]: offline only (reads `docs/asset_expansion/cache/yf_SPY.csv`, `yf_069500.KS.csv`, and `tests/fixtures/macro/` when present; no network import); `SEED = 11`; sections (a) reproduction of the app's cards via `garch_scorecard` (window 504, refit 7, t-quantile), (b) the same fits in FHS form, (c) SMA20 and EWMA(0.94) in FHS and normal form on 2016-03 -> end of file, (d) reference-fixture lines G-B5-01..03 when the fixtures exist; writes `docs/vol_backtest/results.csv` and `manifest.json` (`run`, `seed`, `results_md5`, input file md5s).

---

## C. Schemas and config

### C.1 Config keys read (rules store, written by M0; R-30 block L3210-3227, reproduced verbatim in section 7 at L4294-4308; "If a rule and this listing ever differ, the rule governs", L4132)

```yaml
vol_target:
  estimator_gate:                                    # R-30 (replaces v1.2 B5-only selection)
    acting_default: sma20                            # also the displayed baseline
    challenger: {name: comb, definition: "0.5*(gjr_t + log_har_range)", books_allowed: [KRX_ETF_line, KOSPI200_futures,
                 mini_KOSPI200_futures, CME_micro_ES], books_refused: [KRX_stock_book]}
    fit: {window: expanding, min_years: 10, refit_every_origins: 21}
    range_proxy: {KR: overnight_sq_plus_garman_klass, US: parkinson}
    stage1: {horizon_days: 21, tests: [fhs_var_exceedance_h21, fan_pit_h21, christoffersen_cc], printed: [kupiec_1d, cc_1d_95_99, es975_z2]}
    stage2: {loss: qlike, mcs_level: 0.90, stat: T_max, block: "max(10, 2h)", resamples: 2000, seed: 11, mse_mcs: printed}
    stage3: {objective: min_vol_of_vol_rolling63, eligibility: [dSR_noninferior_vs_sma20_delta_0p10, dMDD_vs_sma20_ge_0, pc2_le_0p90],
             ties: overlapping_bootstrap_ci, tie_break: simplest_surviving,
             complexity_order: [sma20, ewma094, ewma097, garch_t, gjr_t, log_har_range, comb]}
    switch: {counted_revision: true, full_v2_card_p: true}
    fallback_to_sma20: {gjr_bounds: {persistence_max: 0.9999, nu: [2, 100]}, open_quality_max_share: 0.05,
                        flat_range_max_share: 0.05, window_sessions: 252}       # thresholds: default, judgment
    incumbent_calibration: {name: B5, var_level: 0.05, band: "+-2 binomial SE", min_origins: 200, pit: chi2_10_bins, pit_p_min: 0.01}
```
Neighbouring keys this area reads but does not own (L4286-4315): `vol_target.KR: {estimator: sma, window: 20, target_ann: 0.20, cap: 1.0, cap_permanent: true, exposure_basis: total, instrument_book: KRX_ETF_line, ...}`, `vol_target.US: {estimator: sma, window: 20, target_ann: 0.15, cap: 1.0, ...}`, `annualisation_days: 252`, `sigma: {returns: simple, ddof: 1, mean_adjusted: true, stale_carry_days: excluded_window_extends}`, `display_labels: {... per_label_coverage: reported, scoring: tick_loss}`, `logged_alt_estimators: [asymmetric_slow_cut_fast_restore]`, `data.open_quality_flag: open_equals_prior_close` (L4212), `data.stale_carry_flag: flat_ohlc_zero_volume_on_session_day` (L4209).

### C.2 `macro_state.vol` (section 6.1, L3548-3568; written by the M6 builder from `estimator_gate()` output, L6365)

| Field | Type / enum [V] |
|---|---|
| `estimator` | enum `["sma20","ewma094","ewma097","garch_t","gjr_t","log_har_range","comb"]` ("the sma60 reference line goes in extras") |
| `estimator_b5` | enum `["PASS","FAIL","NOT_RUN"]` |
| `estimator_gate` | object, required `["status","fallback_used"]`; `status` enum `["registered_default","challenger_selected","fallback_to_sma20","NOT_RUN"]`; `stage1`: object or null; `stage2_mcs_p`: number or null; `stage3_rank`: integer or null; `fallback_used`: boolean; `reason`: string or null |

Spec example (L3670-3671): `"vol":{"estimator":"sma20","estimator_b5":"PASS","estimator_gate":{"status":"registered_default","stage1":null,"stage2_mcs_p":null,"stage3_rank":null,"fallback_used":false,"reason":null}, ...}`. `estimator`, `estimator_b5`, `estimator_gate` are in `vol.required` (L3567) and are acting fields (L3370).

### C.3 `model_card.macro.forecast_eval` (section 6.5, L4057-4059; written by the M7 card writer)

[V] `forecast_eval = {qlike_mcs_p[h], mse_mcs_p[h], christoffersen_p, es_z2, fan_pit_p, vol_of_vol, dMDD_vs_sma20, dSR_vs_sma20}` (L3232). Schema: object or null; `qlike_mcs_p`, `mse_mcs_p`: objects with number values (keys = horizon as string, "1", "5", "21"); the other six: number or null. Card header field `estimator` (L3946): string, "e.g. sma20; a change is a counted revision (R-30)".

### C.4 Rules-store rule object (section 7.1 L4700; validation is M0's)

`estimator = {name, kind}`; refused when: `kind: ml` (items 11, 29); max(SMA20, implied) sizing (30); "a change outside an R-30 counted revision" (25). `do_not_build` keys touching this area: `11: {11a_ml_vol_state_classifiers: harm_E, 11b_range_log_har: admitted, ...}` (L4634), `ml_classifier_estimator_gate_or_label: [11, 29]` (L4668), `conformal_label_layer: 28`, `sizing_estimator_max_over_implied: 30`.

### C.5 Fixtures this area reads (owned by M0/M1; `tests/fixtures/macro/MANIFEST.csv`, proposed, L6018)

One row per file: file, source, series, span, `retrieved_at_utc`, `value_status` and `available_at_source` rule, md5, tests that read it. "Every stochastic golden names its seed, B and block rule." Needed here: Yahoo `^KS11` (OHLC, from 1996-12), `^GSPC` (OHLC, from 1990), `SPY`, the French daily files (Mkt-RF), "the DLB CSVs", `QX_DLA_postpatch.csv`.

---

## D. Tests

Tolerances (Level 1, L5734-5735): Sharpe +-0.01; max DD +-1 pp; p-values +-0.01 (p >= 0.05) and +-0.005 (p < 0.05); QLIKE ratios +-0.005; vol levels +-0.1 pp; other ratios +-0.01; deterministic counts exact; bootstrap-dependent counts +-1; percentiles +-5. "A verdict derived from a statistic within tolerance of its threshold is asserted as a class, never as a point" (L5499, L5737). Tiers (L5496): `fast` (unit; <= 10 min total), `golden` (fixture reproductions; <= 2 h), `freeze` (M7 only). Hermetic: no network, temp dirs only (T-HERM-01/02).

Reference data status on this machine: `/home/claude/quantgen_macro_data/`, `tests/fixtures/macro/`, the DL-B/R4b scripts and result CSVs (`QX_DLB_*.csv`, `scripts/r4b_golden_net.py`) are absent. Local cache `docs/asset_expansion/cache/` holds auto-adjusted CLOSES ONLY (no OHLC): `yf_SPY.csv` 1995-01-03 -> 2026-09-25 (7,986 rows), `yf_069500.KS.csv` (KODEX 200) 2007-01-29 -> 2026-09-23 (4,274 rows); `yf__KS200.csv` is empty (1 row); there is no `^KS11`, no `^GSPC`, no French Mkt-RF file. The tech-fund results folder holds result tables only, no price histories.

### D.1 Tests that run from M3

| ID | Exact assertion (M3 portion) | Fixture | Class |
|---|---|---|---|
| **T-EST-01** (L3243) | "DLB-T1a reproduction (KOSPI OOS 2001-26; US OOS 1995-2026)": "SMA20 is outside the 90% QLIKE MCS at h 1, 5 and 21 (MCS p <= 0.0005). COMB is inside the 90% MCS in all six cells. SMA20's MSE MCS p printed: KOSPI 0.036 / 0.066 / 0.141; US 0.112 / 0.112 / 0.290." Deferred to M7: the bootstrap-CI clause. | `^KS11` OHLC 1996-12 -> 2026-10-02 (OOS from 2001-01-02, 6,342 origins); `^GSPC` OHLC 1990 -> 2026-10-01 (OOS from 1995-01-03, 7,985 origins) | REFDATA. No local substitute (no OHLC anywhere local). SYNTH companion: on a simulated GJR-t series the MCS drops a deliberately mis-scaled forecaster with p <= 1/B and keeps the true-DGP forecaster; last survivor p = 1.0; identical output on a second run with seed 11. |
| **T-EST-02** (L3244) | "Stage-1 report: Contains the 21-day FHS exceedance, the 21-day fan PIT and Christoffersen CC. The 1-day lines show KOSPI 2001-26 Christoffersen independence p < 0.0001 for SMA20, 0.17 for COMB and 0.16 for log-HAR-range." Deferred to M7: the Stage-3 clause (rank by vol-of-vol, CI ties by simplicity). | as T-EST-01 (KOSPI) | Report-structure clause: SYNTH (keys `fhs_var_exceedance_h21`, `fan_pit_h21`, `christoffersen_cc`, `printed.kupiec_1d`, `printed.cc_1d_95_99`, `printed.es975_z2` present on synthetic data). The three p-values: REFDATA. |
| **T-EST-04** (L3246) | "A GJR fit with alpha + beta + gamma/2 > 0.9999 (or non-convergence), or a tripped OHLC quality flag, makes sigma come from SMA20 for that decision, logged. No blend." Deferred to M7: the counted-revision clause. | inline: a `GJRFit` object with persistence 0.99995; one with `converged=False`; one with nu = 150; synthetic OHLC with open == prior close on 6% of the trailing 252 sessions (KR) and high == low on 6% (US); 5% exactly must NOT trip (rule is "> 5%") | SYNTH. Assert `sigma == sigma_sma20` exactly, `fallback_used is True`, `status == "fallback_to_sma20"`, `reason` set, and the next decision with a good fit uses the challenger again. |
| **T-B5-01** (L5642) | "The B5 harness on the fixture reproduces SMA20 FHS exceedance 4.70% +- 0.3 pp on KOSPI 2016-03 -> 2026-10 and PASS (PIT p 0.11). A synthetic estimator with sigma x 0.7 fails. ... An estimator switch without a counted revision is refused (R-30)." Deferred to M7: "A vol-target card whose estimator is FAIL cannot be PASS." | `^KS11` closes 2016 -> 2026-10-02 (2,594 origins) | Golden clause: REFDATA (local KODEX 200 closes are a different series and end 2026-09-23: indicative only, never asserted). sigma x 0.7 clause: SYNTH (see F-16 for the FHS scale-invariance trap). Switch-refusal clause: SYNTH (`estimator_gate(..., declared="comb")` without a revision raises; nothing written). |
| **I-10** (L5700) | "On the KOSPI and US fixtures the harness reproduces DLB-T1a: SMA20 outside the 90% QLIKE MCS at h 1/5/21 (p <= 0.0005), COMB inside all six cells (G-EST-01). Stage 1 reports 21-day FHS exceedance, fan PIT and Christoffersen CC. ... A GJR fit outside bounds or a tripped OHLC quality flag falls back to SMA20." Deferred to M7: "COMB on KOSPI 2001-26 at 3 bp shows vol-of-vol -22% +- 2 pp vs SMA20 (G-EST-04)" (Stage-3 clause), bootstrap-CI clause, "An estimator switch without a counted revision is refused" (counted-revision clause). | as T-EST-01 | REFDATA for the reproduction; SYNTH for the fallback clause (shares T-EST-04's fixtures). |
| **G-US-01c** (L5788; clause deferred from M2 to M3, L5593 "R-30 builds `ewma094`") | "Challenger EWMA(0.94), same target: Sharpe 0.605 [gross] / 0.520 [net 1x, 50 bp] / 0.434 [net 2x]", timing COMPLIANT; US Mkt-RF 1990-02 -> 2026-09, target 15%, cap 1 | French daily Mkt-RF through 2026-08-31 spliced with the `^GSPC` price return for Sep-2026 (L5722); M2's vt book and cost model | REFDATA (French file absent; `yf_SPY.csv` starts 1995 and is a total-return ETF series: not a substitute). SYNTH companion: EWMA recursion against a hand-computed 5-step example. |
| **G-EST-01** (L5912-5922) | QLIKE relative to SMA20 with MCS p in brackets (table below), Level-1: ratios +-0.005, p per the p-value rule | as T-EST-01 | REFDATA |
| **G-EST-02** (L5924) | "MSE MCS p for SMA20. KOSPI 0.036 / 0.066 / 0.141; US 0.112 / 0.112 / 0.290." | as T-EST-01 | REFDATA |
| **G-EST-03** (L5926-5930) | "B5 (SPEC definition): KOSPI 4.70% of 2,594 (PIT p 0.107); SPY 4.99% (0.566); US 5.31% of 8,961 (0.976). EWMA 4.90% / 5.22% / 5.31%." "B5 passes 7 of 9 KOSPI forecasters and 8-9 of 9 US forecasters. Log-HAR-range narrowly fails KOSPI 1-day B5 (5.58% vs the band's upper bound 5.56%)." "Christoffersen independence, KOSPI 2001-26: SMA20 < 0.0001, EWMA94 0.0007, EWMA97 < 0.0001, GARCH-t 0.026, GJR-t 0.032, log-HAR-range 0.16, COMB 0.17. SMA20 on 2016-26: 0.0006. No US model fails." "range target gives 0.947 / 0.921 x SMA20 (KOSPI / US); QF6's log-r^2 design gives 1.390 / 1.242." | `^KS11`, `^GSPC`, SPY, French Mkt-RF | REFDATA. The "7 of 9 / 8-9 of 9" count names 9 forecasters; only 7 are registered (F-17). |
| **G-EST-04** (L5932-5942) | Sizing books table below (points; Level-1). Task wording: "SMA20 0.571 / -40.0% / vol-of-vol 0.0446; COMB 0.571 / -37.2% / 0.0347". The 90% CI column needs R-24's bootstrap (M7). | `^KS11` OHLC, 3 bp, target 20%, cap 1, 2001-26 | REFDATA |
| **G-B5-01** (L5801) | "KOSPI 2016-03 -> 2026-10 (2,594 origins; band 4.14-5.86%)": SMA20 "4.70%, PIT p 0.11 -> PASS; normal form 6.75%, PIT p < 0.001 -> FAIL; every-7th-session subsample 7.55% (371 origins; band 2.74-7.26%) -> outside"; EWMA(0.94) "4.90%, PIT p 0.03 -> PASS"; GARCH(1,1)-t refit 7 / window 504 (informational) "t-quantile 6.92% -> FAIL; FHS 5.42% -> PASS (2,123 origins)" | `^KS11` closes | REFDATA |
| **G-B5-02** (L5802) | "SPY 2016-03 -> 2026-10 (2,663 origins; band 4.16-5.84%)": SMA20 "4.99%, PIT p 0.57 -> PASS"; EWMA "5.22%, PIT p 0.79 -> PASS"; GARCH-t "t-quantile 6.33%, PIT p < 0.001 -> FAIL (the app's own study: 6.6%, PIT p 0.003, REJECT)" | frozen SPY closes through 2026-10-01 | REFDATA. Local substitute: `yf_SPY.csv` (auto-adjusted, ends 2026-09-25, about 4 fewer origins) gives a near-reproduction for `docs/vol_backtest.py`; report it as indicative, do not assert the golden on it. |
| **G-B5-03** (L5803) | "US market 1991-03 -> 2026-10 (8,961 origins; band 4.54-5.46%)": SMA20 "5.31%, PIT p 0.98 -> PASS"; EWMA "5.31%, PIT p 0.93 -> PASS"; GARCH "not run" | French Mkt-RF + `^GSPC` splice | REFDATA |
| **G-B5-04** (L5804) | "Display labels on 2 Oct 2026": "Relative (trailing 756): KOSPI **elevated** (sigma 28.8%; quartiles 15.7 / 18.6 / 33.6%; 70th percentile); US **normal** (10.7%; 10.5 / 12.7 / 15.2%; 28th percentile). Absolute (expanding full history): KOSPI **stressed**". Labels are M2's function (T-LABEL-01); M3 re-asserts them with the estimator harness in place. | `^KS11` to 2026-10-02 (official close 7,003.74); US to 2026-10-01 | REFDATA |
| **G-POST-01, M3 row** (L5574, L5831) | "G-B5-01 KOSPI SMA20 FHS PIT p (exceedance 4.70% unchanged)": pre-patch 0.12 -> golden post-patch **0.11** (0.107) | `QX_DLA_postpatch.csv`; `^KS11` with the 2-Oct official close | REFDATA |
| Settling test (L5484; not a `run_all` test) | `docs/vol_backtest.py` reruns B5 on SPY and KODEX 200 for 2016-26 and reproduces the app's stored cards (6.6% / KS p 0.003 GARCH-t on SPY) | local cache closes | Feasible locally now (closes suffice for SMA/EWMA/GARCH/GJR); output is a docs artifact, not a golden |

G-EST-01 table [V] (QLIKE / SMA20's QLIKE, MCS p in brackets; L5914-5922):

| Model | KOSPI h1 | h5 | h21 | US h1 | h5 | h21 |
|---|---|---|---|---|---|---|
| SMA20 | 1.000 (0.000) | 1.000 (0.000) | 1.000 (0.000) | 1.000 (0.000) | 1.000 (0.000) | 1.000 (0.0005) |
| EWMA 0.94 | 0.966 (0.002) | 0.867 (0.075) | 0.749 (0.462) | 0.965 (0.000) | 0.870 (0.000) | 0.814 (0.002) |
| EWMA 0.97 | 0.976 (0.001) | 0.895 (0.016) | 0.742 (0.692) | 0.980 (0.000) | 0.907 (0.000) | 0.828 (0.017) |
| GARCH(1,1)-t | 0.957 (0.002) | 0.837 (0.185) | 0.683 (1.000) | 0.949 (0.000) | 0.809 (0.000) | 0.670 (0.657) |
| GJR-t | 0.952 (0.032) | 0.841 (0.185) | 0.718 (0.692) | 0.926 (0.081) | 0.757 (0.105) | 0.652 (0.668) |
| log-HAR-range | 0.947 (0.142) | 0.818 (0.185) | 0.715 (0.692) | 0.921 (0.081) | 0.744 (0.105) | 0.695 (0.657) |
| COMB | 0.944 (1.000) | 0.809 (1.000) | 0.691 (0.692) | 0.916 (1.000) | 0.723 (1.000) | 0.642 (1.000) |

G-EST-04 table [V] (KOSPI 2001-26, 3 bp; L5934-5942):

| Book | Sharpe | Max DD | Turnover/yr | Vol-of-vol | dSR vs SMA20 [90% CI] | dMDD vs SMA20 |
|---|---|---|---|---|---|---|
| Buy and hold | 0.563 | -54.5% | 0 | 0.111 | — | — |
| SMA20 | 0.571 | -40.0% | 2.25 | 0.0446 | — | — |
| EWMA 0.94 | 0.547 | -42.1% | 1.92 | 0.0425 (-4.7%) | -0.024 [-0.053, +0.005] | -2.1 pp |
| GARCH-t | 0.550 | -40.5% | 2.49 | 0.0375 (-16.0%) | -0.022 [-0.054, +0.011] | -0.5 pp |
| GJR-t | 0.556 | -40.5% | 2.54 | 0.0373 (-16.4%) | -0.016 [-0.053, +0.020] | -0.6 pp |
| log-HAR-range | 0.578 | -35.0% | 5.28 | 0.0338 (-24.2%) | +0.006 [-0.045, +0.056] | +5.0 pp |
| COMB | 0.571 | -37.2% | 3.48 | 0.0347 (-22.2%) | -0.000 [-0.042, +0.039] | +2.8 pp |

Printed, not asserted (L5944): "On 2016-26 the gains halve: vol-of-vol -9% to -12%, dMDD +1.6 to +2.1 pp. At 35 bp, log-HAR costs dSR -0.063 (CI -0.114 to -0.013) and COMB -0.030."

Other B5 lines quoted as evidence (not test ids; L1561, L5050): KOSPI 1997-2026 5.04%, PIT p 0.46; long-window GARCH(1,1)-t / GJR-t in FHS form KOSPI 2001-26 5.38% / 5.42%, PIT p 0.98 / 0.87; US 1995-2026 5.17% / 4.91%.

### D.2 Clauses deferred out of M3 (section 9.0b and L5553) — build the hooks, do not assert

| Test | Deferred clause | Joins at | Class when it joins |
|---|---|---|---|
| T-B5-01 | "A vol-target card whose estimator is FAIL cannot be PASS." | M7 (`cardp_evaluate` cap) | SYNTH |
| T-EST-01 | bootstrap-CI clause ("The MCS and Stage-3 CIs come from the frozen R-24 bootstrap", TASK-M7-28; see F-18) | M7 | REFDATA |
| T-EST-02 | Stage-3 clause: "The Stage-3 report ranks survivors by vol-of-vol with CI ties broken by simplicity" | M7 | SYNTH + REFDATA |
| T-EST-04 | counted-revision clause: "A challenger enters a card only through a counted revision; the fallback never blends" | M7 | SYNTH |
| I-10 | Stage-3 (COMB vol-of-vol -22% +- 2 pp), bootstrap-CI and counted-revision clauses | M7 | REFDATA / SYNTH |
| T-EST-03 (L3245) | "COMB sized book (KOSPI 2001-26, 3 bp, target 20%, cap 1): Vol-of-vol -22% +- 2 pp vs SMA20 (0.0347 vs 0.0446); dMDD +2.8 pp; dSR -0.000 with 90% CI [-0.042, +0.039]" | M7 (whole test) | REFDATA |
| T-EST-05 (L3247) | "An estimator change without a new card revision and ledger row is refused. COMB declared on a `KRX_stock_book` card is refused." | M7 (whole test) | SYNTH |
| built-artifact assertions | "Until M6, tests assert the outputs of the functions that fill these artifacts (..., `estimator_gate`, ...), never a built artifact" (L6368) | M6 | SYNTH |

### D.3 Hermetic synthetic tests to write now (tier `fast`; `tests/estimator_acceptance.py`)

1. `sma20`: `var[t] == h * np.var(r[t-19:t+1], ddof=1)`; `ewma`: hand-computed recursion for lambda 0.94 and 0.97.
2. Causality: for every estimator, `forecast(...)[:k]` is unchanged when later data is appended (no look-ahead; log-HAR trains only on rows with s + h <= t).
3. `range_proxy`: GK + overnight^2 and Parkinson on a hand-computed bar; `range_quality_flag` trips at > 5% of 252 and not at exactly 5%.
4. `comb == 0.5 * (gjr_t + log_har_range)` elementwise where both ok; `ok` False where either leg fails.
5. T-EST-04 block (D.1).
6. `mcs`: bad forecaster excluded, true model retained, last survivor p = 1.0, deterministic under seed 11, p values are multiples of 1/B.
7. `dm_test` with `h`: HLN factor equals `sqrt((n+1-2h+h(h-1)/n)/n)`; legacy call `dm_test(a, b, lag=5)` unchanged.
8. `b5`: calibrated Gaussian series -> PASS; fewer than 200 origins -> NOT_RUN; mis-scaled forecast -> FAIL (F-16); band arithmetic equals the three printed bands.
9. `stage1` report keys present; `estimator_gate(declared="sma20")` returns `status="registered_default"`, and its `gate_dict` validates against the section 6.1 `estimator_gate` sub-schema.
10. Refusals: `declared="comb"` without revision; `declared="comb"` on `KRX_stock_book`; `declared="log_har_range"` on `US_shares_KIS`; registry refuses `kind="ml"` and an unregistered name.
11. `sized_book`: weights in [0, 1], t+1 timing (shifting the forecast one day later changes the result), cost charged on |dw|, initial entry free.
12. Golden tests (tier `golden`): one function per G-/T- id above that loads `tests/fixtures/macro/` through the manifest and reports "fixture missing" as not-run, never as a pass (F-20).

---

## E. Interfaces

### E.1 Needed from earlier milestones

| From | What | Shape |
|---|---|---|
| M0 (R-32/R-33) | rules-store keys of C.1; section 6.1 / 6.5 schemas; rule-object validation for `estimator {name, kind}` and DNB items 11a, 25, 28, 29, 30, 33 (T-DNB-01); fixture manifest loader | config dict; JSON Schemas; `core/rules/validation` predicates |
| M1 (R-01, R-19; TASK-M1-11) | PIT reads of daily OHLC and official closes with `value_status`; per-row open flag `open_equals_prior_close`; stale-carry flag `flat_ohlc_zero_volume_on_session_day`; `RunContext{decision_utc, knowledge_utc, run_mode}`; `MissingInput`; frozen fixtures | `pit_value(series_id, decision_utc, knowledge_utc, consumer, require_session) -> PITValue | MissingInput` (L998). Today's `core.quant.history.History` carries `dates` and `closes` only (no OHLC): the OHLC series is a hard M1 dependency for `log_har_range` / `comb`. The high == low "range-quality" flag is not named in M1's task; M3 computes it from OHLC (F-5). |
| M2 (R-06; TASK-M2-01) | `core.quant.risk.sma_vol` (20 valid simple returns, ddof = 1, stale-carry exclusion); `market_vol_target(market, decision_utc, estimator="sma20") -> VTResult` (L1044); the vt book builder, cost model and research bootstrap used by G-US-01/01b/01c | M3 adds the estimator names beyond `sma20` behind `sigma_for_decision`; the acting path accepts only what `estimator_gate` returns |

### E.2 Exposed to later milestones

| To | What | Shape |
|---|---|---|
| M6 builder (TASK-M6-05) | `estimator_gate(...) -> EstimatorSelection` | fills `macro_state.vol.estimator`, `vol.estimator_b5`, `vol.estimator_gate = {status, stage1, stage2_mcs_p, stage3_rank, fallback_used, reason}` |
| M7 (TASK-M7-28) | `stage3(books, delta=0.10, ci_fn=...)` hook for R-24's `lw_studentized_boot(x_a, x_b, block, B, seed)`; `revision` argument of `estimator_gate` (ledger-row proof); `estimator_b5` and `stage1["pass"]` for `cardp_evaluate`'s cap `estimator_calibration_fail: REVISE`; `forecast_eval` dict (C.3); `sized_book` | functions and dicts as in B.3/B.4 |
| M7 formal cards (R-06 KR, R-29) | estimator fixed `sma20`; `ewma094` line printed, not gated (L4949 `ewma094_line`) | `forecast("ewma094", ...)` |
| M9 Quant Lab (TASK-M9-01/02; I-11) | expanding >= 10-year `garch_t` / `gjr_t` fit schedule; FHS machinery; `kupiec`, `christoffersen_cc`, `es_z2`, `fan_pit(h)` (h = 21, 126), tick loss; `var_1d_displayable` | reuse, no second implementation |
| Macro page (M6/M8) | Stage-1 disclosure lines; B5 label per estimator; never a normal-quantile VaR | read-only dicts |

---

## F. Ambiguities, contradictions and conservative readings

| # | Issue (lines) | Conservative reading used above |
|---|---|---|
| F-1 | `estimator_gate(card) -> GateResult` (L3174) vs `estimator_gate(market, instrument_book, horizon=21) -> EstimatorSelection` (L1101). | One function with the 3.5 positional signature plus keyword-only `ctx`, `declared`, `card_id`, `revision`; `GateResult` is an alias of `EstimatorSelection`. |
| F-2 | `fit.min_years: 10` / "expanding windows of >= 10 years" (L3167, L3216) vs the goldens' samples: KOSPI data from 1996-12 with OOS from 2001-01-02 (6,342 origins), US from 1990 with OOS from 1995-01-03 (7,985 origins) (L5910): first fits used about 4 and 5 years. | Acting/challenger path: fewer than 10 years of history -> challenger `ok=False` -> SMA20. Golden reproduction: `min_years`/`oos_start` are harness parameters set by the fixture so the origin counts match exactly; that run is a reproduction, never a verdict. |
| F-3 | EWMA: "RiskMetrics recursion" only (L3186); initial variance, warm-up and the h-step scaling are not printed. | Zero-mean recursion, init = sample variance of the first 20 returns, `var_h = h * s2_{t+1}`. G-US-01c (0.605 / 0.520 / 0.434) settles it once the French fixture exists. |
| F-4 | GARCH-t / GJR-t: multi-step aggregation, parameter handling between refits and the innovation-mean term are not printed (L3167, L3187). Existing fits cap persistence at 0.9995 (`garch.py` `STATIONARITY_MAX`), not 0.9999; gamma is bounded [0, 0.5] (rule: alpha + gamma >= 0). | Mean-reverting sum of 1..h step forecasts; parameters held between refits, recursion filtered daily; pass `stationarity_max=0.9999` through a keyword override; keep gamma >= 0 (a subset of the rule's region). |
| F-5 | R-30 inputs name "open-quality and range-quality flags (QF6-M11)" (L3178); M1 only defines `open_quality_flag: open_equals_prior_close` (L4212). No row-level definition of the range-quality flag exists. | M3 derives both trailing shares from OHLC (`high == low` for Parkinson; `open == prior close` for GK and the overnight leg). Missing OHLC -> `ok=False` -> SMA20. |
| F-6 | Bound `nu in (2, 100]` (L3203): a fit with effectively normal innovations (nu > 100 or eta = 0, which the existing optimiser allows) is literally "outside its bounds". | Literal: fallback to SMA20 for that decision (fail closed). Thresholds are "default, judgment" for the quality flags only, not for nu. |
| F-7 | "Never a stale challenger forecast" (L3235) vs "refit every 21 origins" (parameters legitimately up to 20 origins old). | Held parameters between scheduled refits are allowed; a forecast carried over from an earlier origin, or parameters kept after a failed refit, are not: fall back until the next successful refit. |
| F-8 | QLIKE form not printed; the goldens are ratios of mean QLIKE to SMA20's (L5912), which depend on the form; `y = 0` at h = 1 makes `ln(y/f)` undefined. | `y/f - ln(y/f) - 1` with a 1e-18 guard inside the log (the app's existing form). Settled only by the DL-B script or fixture. |
| F-9 | B5 "FHS form": residual pool (expanding or trailing, minimum size) and first-origin rule are not printed. Inference only: the US market sample starts 1990-02 and its first origin is 1991-03 (L5803), about 20 + 252 sessions. | Expanding pool, first origin once 252 standardised residuals exist. The printed origin counts (2,594; 2,663; 8,961) are the check when fixtures arrive. |
| F-10 | Stage 1 lists its tests at h = 21 (L3190-3192, L3218) but prints no pass thresholds, no definition of the 21-day "fan" for a non-parametric estimator, and no rule for overlapping 21-day windows. No golden exists for any 21-day statistic. | B5 thresholds for the exceedance band and PIT (p >= 0.01), CC p >= 0.05 (the M9 thresholds of I-11, L6371), non-overlapping origins (every 21st), >= 200 origins else not passed. A challenger cannot be selected at M3 in any case, so no exposure depends on this reading. |
| F-11 | `es_z2` "simulated critical values" (L3173): number of simulations and seed not printed. | 2,000 simulations, seed 11, simulation from the model's own predictive law. |
| F-12 | `books_allowed` / `books_refused` (L3214-3215) do not cover the other `instrument_book` enum values (`US_shares_KIS`, `KRX_listed_SP500_ETF`, `crypto_venue`, `FX_KRX_USD_futures`, `FX_broker_spot`, `multi_line`, L3947). Text: "for ETF and futures books only" (L3161). | Allow-list semantics: anything not in `books_allowed` is refused for `comb` and `log_har_range`. |
| F-13 | No trigger is printed for `status: NOT_RUN` (L3231). | Returned when the gate could not be evaluated (insufficient history, internal error); acting estimator stays `sma20`; object stays schema-valid (these are acting fields, L3370). |
| F-14 | "logged" (L3202, L3235) names no sink. | `fallback_used` + `reason` in the returned object (persisted to `macro_state` by M6) plus one structured log record; no new store. |
| F-15 | The app's stored "PIT p 0.003" (L482, L5802) is a Kolmogorov-Smirnov p (`pit_ks_p` in `D_Q_garch_spy.json`); the B5 rule is chi-square on 10 bins (L1561). | `docs/vol_backtest.py` prints both; the B5 status uses chi-square only. |
| F-16 | T-B5-01 "A synthetic estimator with sigma x 0.7 fails" (L5642): in pure FHS form a constant rescaling of sigma cancels (residuals scale by 1/0.7), so such an estimator would pass. | The test scales only the out-of-sample forecast (residual pool standardised by the unscaled estimator) and also checks the normal form on Gaussian data; both must FAIL. Needs confirmation against the R4b harness when available. |
| F-17 | "B5 passes 7 of 9 KOSPI forecasters and 8-9 of 9 US forecasters" (L3157, L5928); the backlog also says "9 of 12" (backlog L573, L1291). Only 7 forecasters are named and registered. | Assert per-model B5 status for the 7 registered estimators; the "of 9" count is printed only if the DL-B result CSV naming the 9 is supplied. |
| F-18 | TASK-M7-28: "The MCS and Stage-3 CIs come from the frozen R-24 bootstrap" vs R-30's MCS on a stationary bootstrap with mean block max(10, 2h) (L3172, L5912); R-24's bootstrap is Ledoit-Wolf studentized circular block (L2596). | MCS keeps R-30's stationary bootstrap (binding in R-30 and the golden header); only Stage-3 dSR CIs use R-24. M7 to confirm when the package is frozen. |
| F-19 | T-B5-01's "estimator switch without a counted revision is refused" runs from M3 (only its "cannot be PASS" clause is deferred, L5553), while the same sentence in I-10 / T-EST-04 / T-EST-05 is deferred to M7. Also G-EST-04 runs from M3 while I-10's COMB vol-of-vol clause (citing G-EST-04) is deferred. | M3 refuses every non-`sma20` declaration unconditionally (no ledger exists yet); M7 adds the accepted-revision path. M3 computes G-EST-04's point columns; the CI column and the tie/rank logic join at M7. |
| F-20 | `tests/run_all.py` knows only PASS / FAIL; golden tests have no fixtures on this machine. The spec requires every test row to name its tier (L5496). | A missing fixture is reported as not-run and excluded from the pass count, never counted as a pass. Runner change is cross-milestone: coordinator decision. |
| F-21 | Naming: `vol_target.KR.estimator: sma` (L4287) vs `acting_default: sma20` (L3213) vs card header `estimator: sma20` and `parameters: {estimator: sma, window: 20}` (L4918-4920). | `name = "sma20"`, `kind = "sma"`; `{estimator: sma, window: 20}` resolves to `sma20`. |
| F-22 | "Never on the registered R-06 KR card" (L3201) vs the header comment "a COMB revision would be a new counted revision (R-30)" (L4920). | The registered card and its primary configuration keep SMA20 permanently; a COMB variant is a separate counted revision (a new ledger trial), never an edit of the registered header. |
| F-23 | Three different US series back the goldens: `^GSPC` OHLC (G-EST-*), French Mkt-RF with a `^GSPC` splice (G-B5-03, G-US-01c), SPY (G-B5-02). | Each golden reads its own fixture; no series is substituted for another. |
| F-24 | MCS p-values near thresholds (KOSPI h5 EWMA 0.94 = 0.075; US h5 GJR-t / log-HAR = 0.105; L5917-5921) cannot be reproduced to +-0.01 without the original RNG stream (Monte Carlo SE about 0.007 at B = 2,000). | Assert membership as a class for cells within tolerance of 0.10 (L5499); T-EST-01's binding cells (SMA20 out, COMB in) are far from the threshold. |
| F-25 | Which sample the incumbent's standing B5 status uses is not printed (goldens exist for 2016-26, 1991-2026, 1997-2026). | Full available history through the decision, >= 200 origins; `NOT_RUN` below that. |

---

## G. DO-NOT-BUILD items and invariants binding this area

| Item | Text / rule | Source |
|---|---|---|
| 11a | "ML vol-state classifiers stay prohibited: elastic-net, gradient-boosting or any other ML classifier of the next-month volatility state, as a sizing, gating or display input." | L6119; R-16(2) L1747 |
| 11b | Range-based log-HAR is admitted (not prohibited); "Intraday realised variance is an upgrade, not a prerequisite" — do not build an intraday-RV path. | L6120 |
| 25 | "Any model as the sizing estimator, except through the staged estimator gate (R-30) as a counted card revision that passes the full v2 CARD-P." Refused shape: "An estimator change outside a counted R-30 revision" (T-DNB-01, I-10). | L6176, L6242 |
| 28 | No Mondrian conformal label layer on the display labels; "The cure for miscalibrated labels is a better sigma through R-30", judged by tick loss. | L6199, L1565 |
| 29 | No maintained ML challenger pipeline (no ML volatility-state model kept running, re-tuned or re-scored). Registry refuses `kind: ml`. | L6200, L6239 |
| 30 | No `max(sigma_SMA20, implied)` sizing. Implied vol is context only; it "may enter sizing only inside HAR-IV, and only if HAR-IV wins the R-30 race" — HAR-IV is not built in M3. | L6201-6205, L1573 |
| 33 | `KRX_stock_book` is never a market-gross scalar book; COMB / log-HAR never on the 35 bp stock book. | L1564, L3200, L6244 |
| 23 / 32 | No edit of estimator, instrument book, rebalance, band or cost after a card's `results_md5` exists; a change is a new card or counted revision. | L4776, L6243 |
| Invariants | SMA20 is the acting sizing estimator and displayed baseline; "validated default" wording is struck (L3160). | |
| | Cap 1.0 permanent; no weight above 1.0; no floor (L1563). | |
| | No blend with SMA20; no stale challenger forecast; any challenger-path failure -> SMA20 for that decision, logged (L3206, L3235). | |
| | Never the registered R-06 KR card; R-29's estimator is SMA20, challenger only by counted revision (L3201, L3083). | |
| | "An estimator choice is a tracking and drawdown decision, never a Sharpe claim" (L3162). | |
| | A sigma is never shown as a normal-quantile VaR; a 1-day VaR display only from a model that passes 1-day B5 (L1561, L3193). | |
| | The skewed-t stays out of the estimator menu (L482, L6178). | |
| | "No lab output is read by a sizing module" (R-16 (6), L1747). | |
| | No real card verdict is computed before the M7 freeze (L5546); M3 goldens are reproductions under v1.2-check conventions, never verdicts (L5812). | |
| | Reference-only configurations (e.g. a cap above 1) are reachable only from `tests/reference/` or `docs/` with `reference_only=True`; `core/` cannot import that code (L5992). | |
| | Tests are hermetic: no provider reachable (T-HERM-01), temp copies only (T-HERM-02), frozen post-close fixtures with md5 (L5492). | |
| | Read-only app: nothing here may import an order-submission client (T-RO-01, L1112). No new dependency: `arch` and `statsmodels` happen to be installed in this interpreter but are not in `requirements.txt`; use the existing `fit_garch` / `fit_gjr` and numpy/scipy. | |
