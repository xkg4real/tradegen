# code_quant_models — map of the existing quant model subsystem (for v2.0 extension)

Scope read in full: `core/quant/{__init__,history,risk,signals,optimize,garch,gjr,montecarlo,insights,gsq}.py`, `core/ficc/ratesim.py`.
Read in part because they collide with v2 names: `core/quant/{strategies,validate,backtest}.py`, `core/crypto/analytics.py` (`garch_scorecard`), `ui/quant_lab_page.py`, `tests/{run_all,quant_acceptance,ficc_acceptance,expansion_acceptance}.py`, `config.py`.
Spec refs: `SPEC` = `QUANTGEN_Quant_Council_2026-10-03/claude_code/QUANTGEN_MACRO_INTEGRATION.md`; `R3` = `QUANTGEN_techfund_research_bundle/.../research_notes/R3_TF_neural_link.md`. `file:N` = line N.

Machine facts (checked 2026-10-05): Python 3.13.14, numpy 2.3.5, scipy 1.18.0, pandas 2.3.3, gs_quant 2.1.4 (installed, so `risk.analyze_history` reports `engine="gs_quant"` here), yfinance 1.4.1, flet 0.85.2. `qa/acceptance_results.json`: 266 PASS = cockpit 47, engine 89, ui 4, quant 53, ficc 56, expansion 17.

---

## A. File by file

### A.1 `core/quant/__init__.py` (12 lines)
Docstring only, no exports. Claims `history.load_history` "is the only module that talks to a provider" (:4-5); in fact `insights.deep_analysis` (Claude API) and `gsq.connect` (GS Marquee) also open sockets.

### A.2 `core/quant/history.py` (504 lines) — the only price loader

| Item | Verbatim | Line |
|---|---|---|
| const | `TRADING_DAYS = 252` | 47 |
| exc | `class HistoryError(RuntimeError)` | 50 |
| const | `SOURCES = ("auto", "fmp", "kis", "yfinance", "crypto", "synthetic")` | 454 |
| const | `_CACHE_MIN_ROWS = 30`, `_CACHE_LIVE_TTL = 600.0` | 353, 356 |
| const | `_READY = {"FMP": lambda: bool(config.fmp_key()), "KIS": lambda: config.kis_ready()}` | 352 |

```python
@dataclass(frozen=True)
class History:                      # :54-90   NO __post_init__ validation
    symbol: str
    source: str                     # "FMP" | "KIS" | "YFINANCE" | "UPBIT" | "BINANCE" | "SYNTHETIC"
    dates: tuple[str, ...]          # ISO dates, ascending
    closes: tuple[float, ...]
    note: str = ""
    adjustment: str = ""            # "total" (splits+dividends) | "split" (splits only) | "" (n/a or unknown)
    __len__() -> len(closes); .last; .first_date; .last_date
    prices() -> np.ndarray(float)                  # length T
    log_returns() -> np.diff(np.log(px))           # length T-1
    simple_returns() -> px[1:]/px[:-1] - 1.0       # length T-1
```

Public functions (all return `History`; all `days: int = 504` = number of most recent sessions kept, `dates[-days:]`):

| Signature | Behaviour | Line |
|---|---|---|
| `load_history(symbol, *, source="auto", days=504)` | router, see below | 457 |
| `fmp_history(symbol, *, days=504)` | GET `{config.FMP_BASE_URL}/historical-price-eod/dividend-adjusted`, params `symbol`, `from`=today−(int(days*1.6)+10) calendar days, `apikey`; price field decided once per response: `adjClose` if any row has it else `close`; `adjustment="total"` / `"split"`; note `"FMP close adjusted for splits and dividends"` or `"FMP close, NOT dividend-adjusted (no adjClose in the response)"` + `"; N session(s) without <field> dropped"`; symbol upper-cased; key redacted from errors | 119 |
| `kis_history(code, *, days=504)` | `KISClient().daily(code, start=YYYYMMDD, end=...)` paged backwards, `days // 100 + 3` pages; note `"KIS 수정주가: adjusted for splits and rights, cash dividends not included"`; `adjustment="split"` | 188 |
| `kis_market_history(symbol, *, days=504)` | by shape: `NAS:AAPL` overseas (`adjustment="split"`), `KR…` 12-char bond ISIN, `Y0…` 5-char yield (percent), `FX@…`, else KRX futures | 292 |
| `yf_history(symbol, *, days=504)` | `core.ficc.data._yf_fetch([symbol], _period_for(days))` (yfinance `auto_adjust=True`); note `"Yahoo adjusted close"`; `adjustment=""` if symbol starts `^` or ends `=F`/`=X`/`-USD`/`-KRW`, else `"total"` | 262 |
| `crypto_history(symbol, *, days=504)` | prefix `KRW-`/`BTC-`/`USDT-` → `UpbitPublic().daily` (source `UPBIT`), else `BinancePublic().daily` (source `BINANCE`); keyless | 280 |
| `synthetic_history(symbol, *, days=504, seed=None)` | seeded GBM: `seed = int.from_bytes(sha256(SYMBOL)[:4], "big")`, `mu = 0.02 + (seed % 17)/100`, `sigma = 0.14 + (seed % 23)/100`, `s0 = 20 + (seed % 400)`; dates = last `days` weekdays ending `date.today()`; source `SYNTHETIC`; note `"Simulated series (GBM, μ=…, σ=…) — no market data provider was used."` | 228 |
| `convention_warning(hists) -> str` | one sentence iff the panel mixes `adjustment=="total"` and `"split"`; else `""` | 101 |

`load_history` routing (`source="auto"`, in this order, :484-504):
1. `_looks_krx` (6 digits, optional `.KS`/`.KQ`) → KIS `kis_history(symbol.split(".")[0])` if `config.kis_ready()`, else SYNTHETIC with note prefix `"KIS credentials are not configured; "`.
2. `_looks_crypto` (`KRW-`/`USDT-` prefix, or alnum `…USDT` of length 5..12) → `crypto_history`.
3. `_looks_yahoo` (`^…`, `…=F`, `…=X`, `…-USD`, `…-KRW`, `.KS`, `.KQ`) → `yf_history`.
4. `_looks_kis_market` → `kis_market_history` if KIS ready, else SYNTHETIC with the same KIS prefix.
5. else FMP if `config.fmp_ready()`, else SYNTHETIC with prefix `"FMP_API_KEY is not configured; "`.

Explicit `source` (`fmp`/`kis`/`yfinance`/`crypto`) never degrades: failure raises `HistoryError`. Blank symbol → `HistoryError("No symbol given.")`; unknown source → `HistoryError(f"Unknown source {source!r}. One of {SOURCES}.")`. Every loader raises `HistoryError` when fewer than 30 usable sessions. `_clean_rows` (:93) drops `None`/≤0 closes and sorts by date string; it does not de-duplicate dates.

Disk cache `_cached(provider, fetch, symbol, days)` (:398-451):
- File `config.ficc_cache_dir() / f"HIST_{provider}_{SYMBOL}_{days}.json"` (non `[A-Za-z0-9_.-]` → `_`). Default dir `~/.nextgen/ficc_cache` (env `NEXTGEN_FICC_CACHE`). Present on this machine: `HIST_FMP_KO_504.json`, `HIST_KIS_069500_504.json`, `HIST_YFINANCE__VIX_504.json`.
- JSON keys: `ts` (epoch s), `live` (bool), `symbol`, `source`, `note`, `adjustment`, `dates`, `closes`.
- TTL `config.FICC_CACHE_TTL_SECONDS` (env `NEXTGEN_FICC_CACHE_TTL`, default 21600 s), read at call time; `<= 0` disables. A series fetched while `_may_be_trading(provider, symbol)` is kept `_CACHE_LIVE_TTL` (600 s) only; a file earns the full TTL only if `"live": false` AND `not _traded_since(...)`.
- Hit: note gains `"cached YYYY-MM-DD HH:MM"` (local time). Missing credentials → provider asked directly (must raise, never served from file). Failures and series < 30 rows are never stored. Read/write errors are swallowed.
- Provider keys used in file names: `FMP`, `KIS`, `YFINANCE`, `CRYPTO`. `days` is part of the key (a different window is a different file, whole-series refetch).
- `_may_be_trading(provider, symbol, at=None)` (:359): venue `US` for FMP symbols without `.` and KIS `NAS:/NYS:/AMS:`; `KRX` for KIS/YFINANCE 6-digit codes; uses `core.markets.is_open(venue, t)` at `at` and `at − 60 min`; no calendar for FX/futures/indices (any weekday, plus Sunday ≥ 21:00 UTC); crypto always.

What `history.py` does NOT have (v2 gaps): no as-of / end-date parameter (always "latest N sessions ending today"), no OHLC, no volume, no shares outstanding, no `value_status`, no `available_at`/`retrieved_at`, no official-vs-vendor distinction, no append-only store (the cache overwrites), no session/calendar validation of dates, no stale-carry flag.

### A.3 `core/quant/risk.py` (170 lines)

Module import pulls `pandas` and `gs_quant.timeseries` inside `try` (:19-26); `_GS_OK` flag; `gs_quant_available() -> bool` (:29). Import cost measured here: 2.4 s (vs 0.12 s for `history`).

```python
@dataclass(frozen=True)
class RiskReport:                   # :33-55
    symbol: str; sessions: int; first_date: str; last_date: str; last_price: float
    engine: str                     # "gs_quant" | "local"
    ann_return: float               # mean(log r) * 252
    ann_vol: float                  # std(log r, ddof=1) * sqrt(252), WHOLE sample
    sharpe: float                   # (ann_return - rf) / ann_vol ; 0.0 if ann_vol == 0
    sortino: float                  # denominator = std of NEGATIVE log returns (ddof=1) * sqrt(252)
    max_drawdown: float             # negative fraction
    calmar: float                   # ann_return / |mdd|
    var_1d: float                   # np.percentile(-log r, var_level*100), floored at 0  (+fraction)
    cvar_1d: float                  # mean of losses >= var, floored at 0
    var_level: float; skew: float; kurtosis: float   # excess kurtosis, z uses ddof=1 std
    best_day: float; worst_day: float                # log returns
    positive_days: float; rf_rate: float

analyze_history(history: History, *, rf_rate: float = 0.03, var_level: float = 0.95) -> RiskReport   # :63
#   r.size < 20 -> ValueError("Need at least 21 sessions to compute risk statistics.")
#   gs_quant path: fabricated index pd.bdate_range(end=today, periods=px.size);
#   _gts.returns(s, 1, _gts.Returns.LOGARITHMIC); _gts.annualize(_gts.std(log_r, _gts.Window(None, 0))).iloc[-1];
#   _gts.max_drawdown(s, _gts.Window(None, 0)).iloc[-1]; any exception -> numpy fallback, engine stays "local"

@dataclass(frozen=True)
class BasketStats:                  # :124-131  (array fields default None, repr=False)
    symbols: tuple[str, ...]
    sessions: int                   # number of overlapping PRICE dates (returns rows = sessions - 1)
    mean_returns: np.ndarray        # annualised mean log return per asset
    cov: np.ndarray                 # np.cov(R, rowvar=False, ddof=1) * 252
    corr: np.ndarray
    returns: np.ndarray             # (T-1, N) daily log returns

align_histories(histories: list[History]) -> BasketStats     # :134
#   < 2 assets -> ValueError("Need at least two assets."); intersects ISO date strings;
#   < 31 shared dates -> ValueError(f"Only {n} overlapping sessions across {[symbols]}; need at least 31.")
portfolio_point(weights, stats: BasketStats, *, rf_rate: float = 0.03) -> tuple[float, float, float]   # (ret, vol, sharpe) :163
_drawdown_curve(prices) -> np.ndarray                         # prices / running max - 1   :58
```

Not present in `risk.py`: any rolling/trailing vol estimator, vol target, sleeve scale, `min()` composition, bounds assertions, hedge state, correlation clamp, concentration caps, look-through, drawdown ladder, hard stop, weekly returns, EWMA or Ledoit–Wolf covariance. `analyze_history` has no UI caller (only `tests/quant_acceptance.py` and `insights.narrate_risk`).

### A.4 `core/quant/signals.py` (172 lines) — single-instrument technical composite

```python
@dataclass(frozen=True)
class SignalComponent:              # :22-29  (constructed positionally in this file)
    key: str; label: str
    score: float                    # -100 .. +100
    weight: float
    reason: str
    value: str = ""
@dataclass(frozen=True)
class SignalReport:                 # :32-42
    symbol: str; last_price: float
    composite: float                # -100 .. +100 = sum(score*weight)/sum(weight) over PRESENT components
    stance: str
    components: tuple[SignalComponent, ...]
    direction -> int                # 1 if composite > 15, -1 if < -15, else 0

sma(px, n) -> np.ndarray            # PRICE moving average, NaN for first n-1; all-NaN if px.size < n   :45
ema(px, n) -> np.ndarray            # PRICE EMA, alpha = 2/(n+1), seeded at px[0]                       :52
rsi(px, n=14) -> float              # Wilder; 50.0 if px.size < n+1; 100.0 if avg_loss == 0             :61
macd(px) -> (line, signal)          # 12/26/9 at the last bar                                           :78
compute_signals(history: History) -> SignalReport                                                       # :89
```

The six components (key, label, weight, score formula, presence condition):

| key | label | weight | score (clamped to ±100) | present when |
|---|---|---|---|---|
| `trend50` | `Price vs 50-day SMA` | 0.20 | `(last/SMA50 − 1)*100 * 8` | ≥ 50 closes |
| `trend200` | `Price vs 200-day SMA` | 0.20 | `(last/SMA200 − 1)*100 * 5` | ≥ 200 closes |
| `momentum` | `3-month momentum` | 0.20 | `(last/px[-64] − 1)*100 * 4` (ROC63) | ≥ 64 closes |
| `rsi` | `RSI (14)` | 0.15 | r ≥ 70: `−(r−70)*3.3`; r ≤ 30: `(30−r)*3.3`; else `(r−50)*1.2` | always |
| `macd` | `MACD (12/26/9)` | 0.15 | `hist / max(last*0.005, 1e-9) * 100` | always |
| `vol` | `Volatility regime` | 0.10 | `(1 − σ20/σ100)*120`; σ = `np.std(log r[-n:], ddof=1)`, daily units, not annualised; text `compressed` (< 0.9) / `elevated` (> 1.1) / `normal` | ≥ 100 log returns |

Stance thresholds: `≥ 50` `"strong bullish"`, `≥ 15` `"bullish"`, `> −15` `"neutral"`, `> −50` `"bearish"`, else `"strong bearish"` (the dataclass comment "strong sell .. strong buy" is stale). No family tag, no market id, no weights vector, no cross-section, no book notion, no explicit error path (an empty history raises `IndexError` at `px[-1]`; short histories just drop components; callers pass ≥ 30 closes).

### A.5 `core/quant/optimize.py` (131 lines)

```python
OBJECTIVES = ("max_sharpe", "min_vol", "risk_parity", "equal_weight")          # :22
@dataclass(frozen=True)
class OptimizedPortfolio:           # :25-35
    objective: str; symbols: tuple[str, ...]; weights: np.ndarray = None
    ann_return: float = 0.0; ann_vol: float = 0.0; sharpe: float = 0.0
    converged: bool = True; note: str = ""
    risk_contrib: np.ndarray = None # fraction of total risk, sums to 1
@dataclass(frozen=True)
class Frontier: vols, rets, cloud_vols, cloud_rets, cloud_sharpes   # all np.ndarray  :38-44

optimize_portfolio(stats: BasketStats, *, objective="max_sharpe", rf_rate=0.03, max_weight=1.0) -> OptimizedPortfolio   # :68
efficient_frontier(stats: BasketStats, *, points=25, rf_rate=0.03, n_cloud=1500, seed=11) -> Frontier                  # :103
_risk_contributions(w, cov) -> np.ndarray     # w * (cov @ w) / (w' cov w); equal shares if variance <= 0   :47
_solve(objective_fn, n, *, cap) -> (w, ok)    # SLSQP, x0 = 1/n, bounds (0, cap), sum(w) = 1, maxiter 500, ftol 1e-10; clip then renormalise  :55
```
- Always long-only, fully invested (Σw = 1, no cash leg). `cap = min(max(max_weight, 1/n + 1e-9), 1.0)`.
- Unknown objective → `ValueError(f"Unknown objective {objective!r}. One of {OBJECTIVES}.")`. Non-convergence is surfaced: `converged=False` and note `"Solver did not report convergence; treat weights as approximate."`; risk parity note `"Weights equalize each asset's contribution to portfolio risk."`.
- `efficient_frontier` ignores `max_weight` (bounds `(0, 1)`), sweeps `np.linspace(min_vol.ann_return, max(mu), points)`, drops unconverged targets; Dirichlet(1) cloud.
- No inverse-vol weights, no shrinkage, no weekly inputs, no correlation override hook.

### A.6 `core/quant/garch.py` (753 lines) — GARCH(1,1), t or normal innovations, on daily LOG returns

Model: `r_t = mu + eps_t`, `sigma²_t = omega + alpha eps²_{t−1} + beta sigma²_{t−1}`; `mu` = sample mean, FIXED; `sigma²_1` = sample variance; tail fitted as `eta = 1/nu` (`eta = 0` is the normal).

Constants (verbatim):
```python
TRADING_DAYS = 252
Z_BOUND = 22
_SIG_LO, _SIG_HI = 1e-6, 0.25
BOUNDS = {"omega": (1e-12, inf), "alpha": (0.0, 0.5), "beta": (0.0, 0.999), "eta": (0.0, 0.4), "nu": (2.5, inf)}
STATIONARITY_MAX = 0.9995          # alpha + beta cap (penalty in the objective)
LR_5PCT = 2.706                    # 5% point of 1/2 delta_0 + 1/2 chi2(1)
NU_NORMAL = 100.0                  # nu above this is drawn/treated as normal
Z95 = 1.959964
_PROFILE_CUT = 1.920729; _PROFILE_CUT0 = LR_5PCT / 2; _PROFILE_GRID = np.linspace(0.0, 0.4, 41)
_ETA_EPS = 1e-10; _PENALTY = 1e10; _MIN_OBS = 100; _OMEGA_SCALE = 1e6
```

```python
@dataclass(frozen=True)
class GarchFit:                     # :97-173
    dist: str                       # "t" | "normal"
    omega, alpha, beta: float; nu: float          # nu = inf when dist == "normal" or eta < _ETA_EPS
    mean_daily: float; n_obs: int
    persistence: float              # alpha + beta
    half_life: float                # sessions; inf if persistence >= 1
    uncond_vol: float               # ANNUALISED sqrt(omega/(1-persistence)*252); nan if persistence >= 1
    cond_vol_last: float            # ANNUALISED sqrt(sigma²_{T+1} * 252)  (next-session forecast)
    cond_vol: np.ndarray            # DAILY sigma_t, length T
    loglik, loglik_normal, loglik_gbm, aic, bic: float
    lr_t_vs_normal: float           # max(0, 2(ll_t - ll_normal))
    delta_aic_vs_gbm: float         # (4 - 2 ll_gbm) - aic ; > 0 = GARCH preferred
    converged: bool; at_bound: tuple[str, ...]    # subset of {"omega","alpha","beta","nu","stationarity"}
    note: str
    se: dict[str, float]            # keys omega/alpha/beta[/eta] + "persistence"; EMPTY when undefined
    se_note: str                    # exactly one of se / se_note is non-empty
    eta_interval: tuple[float, float] | None      # 95% profile interval, t only, None if profile=False
    interval_at_bound: tuple[str, ...]            # subset of {"alpha","beta","persistence","nu"}
    interval(name) -> (lo, hi) | None ; nu_interval ; half_life_interval ; kurtosis_excess
    effectively_normal -> bool      # dist == "normal" or nu > NU_NORMAL
    innovation -> "t" | "normal"
```

| Signature | Returns / raises | Line |
|---|---|---|
| `fit_garch(returns, *, dist="t", profile=True) -> GarchFit` | `ValueError` on unknown dist or `< 100` obs (`"Need at least 100 observations to fit GARCH; got N."`); L-BFGS-B from 3 starts (beta0 0.80/0.90/0.94); `"stationarity"` flagged when `alpha+beta > 0.995`; `profile=False` skips the eta profile (use in loops) | 446 |
| `loglik_iid_normal(returns) -> float` | GBM benchmark | 215 |
| `forecast_variance(fit, horizon, var_in=1.0) -> np.ndarray` | DAILY variances T+1..T+H; recursion `omega + (alpha*var_in + beta)*s2` | 558 |
| `horizon_vol(fit, horizon, var_in=1.0) -> float` | ANNUALISED `sqrt(mean(forecast_variance)*252)` | 574 |
| `t_density(z, nu)`, `bounded_t_stats(nu, bound) -> (mass, var_in)` | unit-variance t; `(1.0, 1.0)` above `NU_NORMAL` | 584, 642 |
| `martingale_correction(sigma_daily, nu, dist, bound=Z_BOUND) -> np.ndarray` | `ln E[exp(sigma z)]`; `ValueError` for an unbounded t | 654 |
| `simulate_returns(fit, *, n_paths, horizon, seed=7, drift_daily=None, rate_daily=None, bound=Z_BOUND) -> (ret[n_paths, horizon], corr_daily)` | starts at `sigma²_{T+1}` | 674 |
| `simulate_garch_series(omega, alpha, beta, nu, *, n, seed, dist="t") -> np.ndarray` | zero-mean test series, 500 burn-in, unbounded | 705 |

`note` format: `"GARCH(1,1)-{dist} on {T} sessions, mu fixed at {±x.xxx}%/day: alpha=… beta=… persistence=… nu=… (lo to hi|normal); <flags|no guardrail hit>."` Flag strings (verbatim): `"solver did not converge"`, `"near-integrated (alpha+beta > 0.995)"`, `"nu at lower bound: tails heavier than the model allows"`, `"normal innovations (eta = 0)"`/`"(nu = N > 100)"`, `"omega at bound: unconditional vol undefined"`, `"{alpha|beta} at bound"`, `"standard errors undefined: <se_note>"`, `"95% interval reaches a bound: …"`, `"persistence interval reaches 1"`.

Private names imported elsewhere (renaming breaks them): `_variance_path, _t_const, _ETA_EPS, _PENALTY, _OMEGA_SCALE` (gjr.py, docs/b1_evidence, docs/b2_evidence), `_draw_z, _t_scale` (tests, docs/bounded_innovation_sweep.py).

Not present: SMA/EWMA variance estimators, any estimator registry, rolling/expanding refit driver, multi-step FHS quantiles, EVT/GPD tails, range proxies (Parkinson, Garman–Klass), log-HAR, COMB, QLIKE/MSE/tick losses, MCS.

### A.7 `core/quant/gjr.py` (235 lines) — GJR-GARCH(1,1), fit and one-step variance only

```python
GAMMA_BOUNDS = (0.0, 0.5); LAMBDA_BOUNDS = (-0.9, 0.9); _ETA_MIN_SKEW = 1.0/50.0; _MIN_OBS = 100
skewt_logpdf(z, nu, lam); skewt_cdf(z, nu, lam); skewt_ppf(u, nu, lam)      # Hansen (1994), zero mean, unit variance
@dataclass(frozen=True)
class GJRFit:                       # :76-102
    omega, alpha, gamma, beta, nu: float; mean_daily: float; n_obs: int
    persistence: float              # alpha + beta + gamma/2
    loglik: float; loglik_symmetric: float; converged: bool
    at_bound: tuple[str, ...]       # subset of {"alpha","gamma","beta","nu","lambda","stationarity"}
    cond_vol: np.ndarray            # DAILY sigma_t
    next_var: float = 0.0           # DAILY sigma²_{T+1}
    lam: float = 0.0                # Hansen skew (dist="skewt")
    lr_asymmetry -> max(0, 2(loglik - loglik_symmetric))     # compare to 2.706
    effectively_normal -> not isfinite(nu) or nu > 100.0
fit_gjr(returns, *, dist="t") -> GJRFit     # dist in ("t","normal","skewt"); ValueError("dist must be 't', 'normal' or 'skewt'"); ValueError(f"Need at least 100 observations, got N.")
next_variance(fit, eps_prev, s2_prev) -> float
simulate_gjr_series(omega, alpha, gamma, beta, nu, *, n, seed=1) -> np.ndarray
```
Stationarity penalty `alpha + beta + 0.5*gamma > STATIONARITY_MAX` (0.9995); `"stationarity"` flag at `> 0.995`; gamma on its lower bound 0 is reported as `"gamma"` in `at_bound`. No standard errors, no simulation, no multi-step forecast, no martingale correction. Used for scoring only by `core/crypto/analytics.garch_scorecard`.

### A.8 `core/quant/montecarlo.py` (332 lines)

```python
MODELS = ("garch_t", "gbm", "jump", "bootstrap"); DRIFTS = ("premium", "zero", "rf", "sample"); FAN_PERCENTILES = (5, 25, 50, 75, 95)
run_monte_carlo(history: History, *, model="garch_t", n_paths=5000, horizon_days=126, target=None, var_level=0.95,
                seed=7, n_sample_paths=40, drift="premium", rf_rate=0.03, erp=0.04) -> MCResult        # :229
resolve_drift(mode, *, sample_mu, rf_rate, erp) -> ("rate"|"log", annual value)                       # :189
```
- Clamps: `n_paths` to [200, 100000], `horizon_days` to [5, 252*5]. `ValueError` on unknown model/drift, `< 21` sessions (`"Need at least 21 sessions of history to calibrate."`), and (garch_t) `< 100` returns from `fit_garch`.
- `MCResult` (frozen, :71-108): `symbol, model, n_paths, horizon_days, spot, mu_annual` (effective log drift), `sigma_annual` (GARCH: `fit.cond_vol_last`; others: sample σ), `fan: dict[int, np.ndarray]` (length `horizon_days+1`, starts at spot), `sample_paths`, `terminal`, `mean_terminal, median_terminal, p05, p95, prob_loss, prob_target, target`, `var_pct`/`cvar_pct` (HORIZON loss as +fraction of spot: `losses = 1 − terminal/spot`, percentile at `var_level`, floored at 0), `var_level, jump_note, garch: GarchFit|None, drift_mode, garch_horizon_vol, rf_rate, erp, drift_note, correction_annual, z_bound, bound_note`; property `expected_return_pct`.
- Models: GBM (sample σ), Merton jump (3σ split; no outliers → note `"No >3σ daily moves in the sample — jump model degrades to GBM."`), circular block bootstrap with fixed `block = 5`, GARCH-t via `garch.simulate_returns`. Rate drifts subtract each model's exact per-step convexity correction.
- `prob_target` is `None` when `target` is falsy (0.0 included).
- No scenario library, no historical replay, no named shock sets, no multi-asset simulation.

### A.9 `core/quant/insights.py` (339 lines)

```python
@dataclass(frozen=True)
class Analysis: text: str; engine: str; error: str = ""      # engine "local" | model id | "none"
ai_ready() -> bool
narrate_monte_carlo(mc: MCResult) -> str; narrate_risk(r: RiskReport) -> str; narrate_signals(s: SignalReport) -> str
narrate_backtest(b: BacktestResult) -> str; narrate_portfolio(p: OptimizedPortfolio) -> str
deep_analysis(kind: str, payload: dict, *, question: str = "") -> Analysis     # never raises
```
`deep_analysis`: POST `https://api.anthropic.com/v1/messages`, `anthropic-version: 2023-06-01`, model `config.ai_model()` (env `QUANTGEN_AI_MODEL`, default `"claude-sonnet-5"`), `max_tokens` 1500, timeout 60 s, plain `requests` (not the retrying `data.net.session`). No key → `Analysis("", "none", error="ANTHROPIC_API_KEY is not configured.")`. Arrays in the payload are truncated to 50 elements. `_SYSTEM` asks for "what the trade expression would be". `core/ficc/insights.py` re-exports `Analysis`, `ai_ready`, `deep_analysis`.

### A.10 `core/quant/gsq.py` (103 lines)
`GsStatus(installed, version, offline_analytics, credentials_present, session_active, detail)` frozen; `status() -> GsStatus`; `connect() -> GsStatus` (`GsSession.use(Environment.PROD, client_id, client_secret, scopes=("run_analytics",))`, failure recorded in `detail`, never raised); `price_example_swap(tenor="10y", ccy="USD") -> dict` (`{"ok": False, "detail": …}` without a session; `IRSwap("Pay", tenor, ccy).resolve()` with one). Module-level mutable `_session_state`. Env: `GS_CLIENT_ID`, `GS_CLIENT_SECRET`. Pricing only; no order call.

### A.11 `core/ficc/ratesim.py` (379 lines) — short-rate models

```python
MODELS = ("vasicek", "cir", "hull_white"); FAN_PERCENTILES = (5, 25, 50, 75, 95)
_KAPPA_MIN = 0.01; _MIN_OBS = 30; _MAX_REVAL_PATHS = 500
@dataclass(frozen=True) class ShortRateParams: model, kappa (1/yr), theta (decimal), sigma, r0, note=""
@dataclass(frozen=True) class RateSimResult: model, params, horizon, n_paths, fan: dict[int, np.ndarray], times, terminal,
        mean_terminal, p05, p95, prob_above: float|None, threshold: float|None,
        model_curve_at_horizon: tuple[tuple[float, float], ...], note
@dataclass(frozen=True) class HorizonPV: pvs, mean, p05, p95, var95 (>= 0), cvar95, note

calibrate(series: Series, *, model="vasicek", dt: float | None = None) -> ShortRateParams        # :101
zcb_price(params, r, t, T, *, curve: YieldCurve | None = None) -> float                          # :183
simulate(params, *, horizon=1.0, n_paths=5000, steps_per_year=252, seed=7, threshold=None, curve=None) -> RateSimResult   # :213
horizon_pv_distribution(params, sim, *, kind="bond", bond=None, swap=None, curve=None) -> HorizonPV   # :294
```
- Units: every rate a decimal; ACT/365F year fractions. `calibrate` OLS on the discretised SDE; `dt = 1/12` if `"monthly"` in `series.note.lower()`, else `1/252`; `sigma = std(resid, ddof=2)/sqrt(dt)`; kappa clamped at 0.01 with a note; CIR notes Feller failure; Hull–White note says θ(t) comes from the curve at simulation time.
- `simulate`: seeded Euler, `n_paths` clamped to [100, 100000]; CIR full truncation; Hull–White resets `r0 := curve.inst_fwd(0.0)` (flat curve at r0 when `curve is None`) and says so in `note`.
- Errors: `FICCError` (< 30 obs, non-positive vol, missing bond/swap, instrument maturing before the horizon), `ValueError` (unknown model, `dt <= 0`, `horizon <= 0`, bad `kind`).
- No externally imposed error band (nothing that maps an SEP RMSE band to paths), no scenario object, no coupling to the equity Monte Carlo.

### A.12 Adjacent modules whose names v2 would collide with (not owned by this map; recorded to prevent duplication)

| Existing | Signature / convention | Where |
|---|---|---|
| `strategies.realised_vol(prices, window=22) -> np.ndarray` | annualised trailing std of LOG returns, ddof=1, × √252, aligned with prices, includes the return ending at t, NaN for `t < window` | strategies.py:119 |
| `strategies.ewma_vol(prices, com=60.0) -> np.ndarray` | MOP eq. (1), δ = com/(1+com), mean-adjusted, annualised with **261**, NaN for `t < 22` | :129 |
| `strategies.vol_target(prices, *, target, window=22, step=21, cap=1.0, band=0.10) -> W` | `min(cap, target/σ̂)` re-decided every `step` sessions, kept when the change is ≤ `band`; 0 when σ̂ invalid | :190 |
| `strategies.tsmom(..., vol_target_ann=0.40, com=60.0, cap=1.0)`, `trend_switch(..., vol_cap=None)`, `risk_parity(prices, *, window=250, step=63)` | weight-path families | :232, :162, :351 |
| `strategies.simulate(prices, weights, *, cost_bps=5.0, cash_daily=0.0) -> (pnl, turnover)`, `summary(pnl) -> dict`, `equity_curve`, `align_panel` (≥ 60 shared dates), `pnl_matrix`, `grid_from`, `FAMILIES: dict[str, Callable]` | costed daily engine, weight at t held t→t+1 | :69, :97, :51, :373 |
| `validate.GATE` (dict of thresholds), `DECISIONS = ("PASS", "REVISE", "REJECT", "INSUFFICIENT_DATA")` | existing gate | validate.py:53, :50 |
| `validate.newey_west_t(d, lag)`, `validate.dm_test(loss_a, loss_b, *, lag=0) -> {"t","p","mean_diff","n"}` | Bartlett HAC, normal p-value, NO Harvey–Leybourne–Newbold factor | :216, :230 |
| `validate.kupiec(hits, alpha) -> {"n","x","rate","lr","p"}`, `christoffersen(hits, alpha) -> {"lr_ind","p_ind","lr_cc","p_cc"}`, `traffic_light(hits99, window=250) -> "green"|"yellow"|"red"`, `coverage_check(inband, level=0.90)`, `pit_tests(u, *, lags=(1,5,20))` (KS, χ² 10 bins, Berkowitz, correlogram flags, `shape`), `crps(samples, x)` | distribution loop | :560-655 |
| `validate.score_distribution(*, hits95, hits99, inband90, pit, nonconv=None, horizon=1) -> DistributionScore` | decision uses `GATE["var95_min_origins"]=500`, `kupiec_min 0.05`, `cc_min 0.05`, `pit_ks_min 0.05`, `pit_ks_reject 0.01`, `exceed_reject_mult 2.0`, `nonconv_max 0.05` | :673 |
| `validate.ModelCard`, `load_cards(directory)`, `md5_of(path)` | JSON cards, one file per `card_id` | :734-792 |
| `core.crypto.analytics.garch_scorecard(dates, close, *, window=730, refit=7, start=None, model="garch_t") -> GarchScorecard` | the ONLY rolling refit harness: 1-day-ahead, trailing window, t-quantile (not FHS) VaR hits 95/99, 90% band, PIT, QLIKE vs EWMA(0.94) with `r²` proxy (`ql = rv/σ² − ln(rv/σ²) − 1`), models `garch_t`/`gjr_t`/`gjr_skewt` | analytics.py:337 |
| `core/quant/backtest.py` | a 155-line FILE: `STRATEGIES = ("ma_cross","momentum","rsi_revert")`, `BacktestResult`, `run_backtest(history, *, strategy="ma_cross", params=None, cost_bps=10.0)`; imported by `insights.py`, `ui/signals_page.py`, `ui/qcharts.py`, tests | backtest.py |

---

## B. Cross-file flows

```
providers ── data.fmp / data.krx.kis_client / data.kis_markets / data.crypto.crypto_client / core.ficc.data._yf_fetch
     └─> history.load_history ──> History ──┬─> montecarlo.run_monte_carlo ─> garch.fit_garch / simulate_returns ─> MCResult ─> insights.narrate_monte_carlo
                                            ├─> risk.analyze_history ─> RiskReport ─> insights.narrate_risk          (tests only; no page calls it)
                                            ├─> risk.align_histories ─> BasketStats ─> optimize.optimize_portfolio / efficient_frontier ─> insights.narrate_portfolio
                                            ├─> signals.compute_signals ─> SignalReport ─> insights.narrate_signals
                                            └─> backtest.run_backtest (uses signals.sma) ─> insights.narrate_backtest
strategies.risk_parity ─> optimize.optimize_portfolio(objective="risk_parity") + risk.BasketStats
core.crypto.analytics.garch_scorecard ─> garch.fit_garch(profile=False) | gjr.fit_gjr + next_variance ─> validate.score_distribution (docs study)
core.ficc.data.load_short_rate / Series ─> ratesim.calibrate ─> simulate ─> horizon_pv_distribution ─> core.ficc.insights.narrate_ratesim
```

UI entry points: `ui/quant_lab_page.py` (`load_history(symbol, source)` at default 504 days → `run_monte_carlo`; rf from FRED `DGS3MO` or KRW 3m via `core.ficc.data`, else `_RF_ASSUMED = 0.03`; `_study_chips()` reads cards `D_Q_garch_spy`, `D_Q_garch_kodex200`, `D_Q_skewt_spy`, `D_Q_skewt_kodex200` and shows `stats.exceed95`, `decision`, `lines[0]`, `decision_reason`), `ui/portfolio_page.py` (`convention_warning` → `align_histories` → 4 objectives + frontier), `ui/signals_page.py` (`compute_signals` + `run_backtest`), `ui/strategy_lab_page.py` (`load_history(days=5000)`), `ui/etf_page.py` (`S.vol_target(px[:, None], target=0.12, window=22, step=21)`, `fit_garch`, `forecast_variance`), `ui/derivatives_page.py` + `core/ficc/equity_deriv.py` (`simulate_returns`), `ui/crypto_page.py` (`fit_garch`), `ui/rates_page.py` (`ratesim`), `ui/qcharts.py` (types + `signals.sma`), `ui/settings_page.py` (`gsq`). `core/engine/*` imports nothing from `core/quant`.

Persistence on disk:
- `~/.nextgen/ficc_cache/HIST_*.json` (history cache; outside the repo; overwritten, not append-only).
- `docs/asset_expansion/cards/*.json` (34 model cards; read by Quant Lab, ETF, Crypto, Strategy Lab pages through `validate.load_cards`; written by `docs/asset_expansion_study.py`).
- `docs/asset_expansion/cache/*.csv` (46 files, two columns `Date,<name>`; read only by docs study scripts, never by `load_history`).
- `qa/acceptance_results.json` (test runner output).
- In-memory only: `garch._correction_table` `lru_cache(maxsize=32)`, `gsq._session_state`.
- `risk`, `signals`, `optimize`, `garch`, `gjr`, `montecarlo`, `ratesim` write nothing.

Env vars read on these paths (through `config._clean`): `FMP_API_KEY`, `FMP_BASE_URL` (default `https://financialmodelingprep.com/stable`), `KIS_APP_KEY`, `KIS_APP_SECRET`, `NEXTGEN_HTTP_TIMEOUT` (default 12), `NEXTGEN_FICC_CACHE`, `NEXTGEN_FICC_CACHE_TTL` (default 21600), `ANTHROPIC_API_KEY`, `QUANTGEN_AI_MODEL`, `GS_CLIENT_ID`, `GS_CLIENT_SECRET`.

---

## C. Existing tests

Runner: `python tests/run_all.py` forces UTF-8 on stdout/stderr, imports each suite's `tests()` and prefixes names (`quant/…`, `ficc/…`, `expansion/…`), writes `qa/acceptance_results.json`, exits non-zero on any FAIL (`tests/run_all.py:22-70`).

Registration:
- `tests/quant_acceptance.py:1001` and `tests/ficc_acceptance.py:761`: `tests()` auto-collects every module-level callable named `test_*` (sorted by name). A new test function in these files is registered by existing.
- `tests/expansion_acceptance.py:306`: explicit list of `(name, fn)`; `_selfcheck("path.py")` runs a module's `__main__` block via `runpy` as one test.
- A NEW suite file needs an import line and one list term in `tests/run_all.py:31-44`.
- Hermetic helpers: `quant_acceptance._no_credentials()` patches `config.fmp_ready`, `config.fmp_key`, `config.kis_ready`, `config.anthropic_key` only (Yahoo, Upbit and Binance are keyless and are NOT blocked by it); `ficc_acceptance._no_network()` replaces `core.ficc.data._fred_fetch` and `_yf_fetch` with a raiser and sets `config.FICC_CACHE_TTL_SECONDS`.

`tests/quant_acceptance.py` — 53 tests:

| Group | Tests | Asserts |
|---|---|---|
| History (9) | `test_synthetic_is_deterministic_per_symbol`, `test_load_history_rejects_blank_and_unknown_source`, `test_auto_routing_falls_back_to_labeled_synthetic`, `test_explicit_provider_without_key_raises_not_simulates`, `test_history_cache_serves_a_rerun_without_asking_the_provider_again`, `test_fmp_history_asks_for_dividend_adjusted_closes_and_reports_refusals_honestly`, `test_the_cache_knows_when_a_market_may_be_trading`, `test_each_loader_states_its_return_convention`, `test_a_panel_mixing_total_and_price_return_series_is_called_out` | same closes per symbol; `HistoryError` on blank/unknown source; auto → `SYNTHETIC` with `"FMP_API_KEY"`/`"KIS"` in note; explicit fmp without key raises; cache: one provider call per (symbol, days), `"cached"` in note, `adjustment` survives, TTL 0 disables, live window, legacy file without `live` refetched, file `HIST_FMP_TSLA_120.json` has `live is False`, missing key never served from file; FMP URL ends `/historical-price-eod/dividend-adjusted`, dropped-row note, `"NOT dividend-adjusted"`, key redaction, 429 → `"rate limit"`; trading-window truth table; `("split","total","")` for KIS / Yahoo `.KS` / `^VIX`; `convention_warning` text |
| Monte Carlo (6) | `test_mc_is_seeded_and_reproducible`, `test_mc_fan_percentiles_are_ordered`, `test_mc_var_and_cvar_are_coherent`, `test_mc_target_probability_brackets`, `test_mc_jump_degrades_to_gbm_without_outliers`, `test_mc_all_models_run` | seed determinism; fan ordered and starts at spot; `0 ≤ var ≤ 1`, `cvar ≥ var`; target brackets; jump note non-empty; `MODELS == ("garch_t","gbm","jump","bootstrap")`, `garch` set only for garch_t |
| Risk (3) | `test_risk_vol_and_drawdown_match_numpy_whatever_engine`, `test_risk_var_cvar_bounds`, `test_align_histories_requires_overlap` | `ann_vol` = `std(log r, ddof=1)*sqrt(252)` and mdd to 1e-6 under either engine; `0 ≤ var_1d ≤ |worst_day|`, `cvar ≥ var`; disjoint dates → `ValueError` |
| Optimizer (5) | `test_optimizer_weights_are_a_long_only_allocation`, `test_optimizer_objectives_actually_optimize`, `test_risk_parity_equalizes_risk_contributions`, `test_max_weight_cap_is_respected`, `test_frontier_is_traced_and_cloud_is_dominated` | Σw = 1 ± 1e-6, w ≥ −1e-9; max_sharpe ≥ 1/N Sharpe, min_vol ≤ 1/N vol; RC within 0.02 of 0.25; max w ≤ 0.4 + 1e-6; ≥ 6 frontier points, cloud size |
| Signals (3) | `test_signals_read_the_trend_direction`, `test_signal_scores_and_weights_are_bounded`, `test_rsi_stays_in_bounds` | composite sign follows trend; scores in ±100, every reason non-empty, `|Σ weight − 1| < 0.25`; RSI in [0,100], pure uptrend = 100.0 |
| Backtest (4) | `test_backtest_costs_only_hurt`, `test_backtest_has_no_lookahead`, `test_backtest_rejects_inverted_ma_params`, `test_backtest_exposure_and_drawdown_sane` | costs lower return and do not change trades; t+1 execution exact; `ValueError` on fast ≥ slow |
| Insights (2) | `test_narratives_state_their_numbers`, `test_deep_analysis_without_key_degrades_without_network` | numbers appear in text; no key → empty text, `"ANTHROPIC_API_KEY"` in error |
| gs_quant (2) | `test_gsq_status_is_coherent`, `test_gsq_pricing_without_session_explains_itself` | detail always set |
| Charts (1) | `test_every_chart_renders_a_data_uri_image` | 7 `ui.qcharts` images start `data:image/png;base64,` |
| GARCH (7) | `test_garch_recovers_parameters_on_simulated_series`, `test_garch_scaled_t_shocks_have_unit_variance`, `test_garch_respects_bounds_and_flags_on_gbm_series`, `test_garch_t_beats_normal_and_gbm_on_clustered_series`, `test_garch_forecast_variance_converges_to_unconditional`, `test_mc_default_model_is_garch_t_seeded_and_reproducible`, `test_mc_zero_drift_lowers_median_on_positive_drift_series` | truth (ω 2e-6, α 0.08, β 0.90, ν 6) recovered with reference SEs (5.7e-7, 0.0102, 0.0117, 0.0175, 0.0065 ± 15%); `BOUNDS`/`STATIONARITY_MAX` respected; `at_bound ⊂ BOUNDS ∪ {"stationarity"}`; AIC/BIC formulas; forecast converges to ω/(1−p); `sigma_annual == garch.cond_vol_last` |
| Drift (4) | `test_drift_modes_are_ordered_and_documented`, `test_drift_zero_centres_the_cone_and_sample_reproduces_the_mean`, `test_unknown_drift_raises`, `test_garch_narrative_states_persistence_and_nu` | `DRIFTS == ("premium","zero","rf","sample")`; drift note text; narrative states persistence, ν, intervals |
| Bounded innovations (7) | `test_bounded_t_draws_respect_the_bound_and_keep_the_shape`, `test_martingale_correction_matches_quadrature_and_the_normal_closed_form`, `test_rate_modes_make_the_discounted_price_a_martingale_for_every_model`, `test_lr_is_nonnegative_and_correctly_sized_under_the_null` (26.7 s), `test_interval_coverage_on_simulated_t_garch` (17.9 s), `test_intervals_reaching_a_bound_are_flagged`, `test_horizon_vol_describes_the_bounded_paths` | `|z| ≤ Z_BOUND`; correction vs quadrature to 1e-7; `E[P_T] = spot·exp(rate·T)` within 3 SE for all 4 models; LR size ≤ 5% + 2 SE; ≥ 85% interval coverage; bound chips |

`tests/ficc_acceptance.py` (ratesim, 5 + 2 narrative uses): `test_ratesim_is_seeded_and_reproducible`, `test_ratesim_vasicek_reverts_to_theta` (mean within 10% of θ at 30y), `test_ratesim_cir_stays_non_negative`, `test_ratesim_hull_white_matches_the_curve_at_t0` (`|zcb − df| < 1e-6` at 0.5/2/10/30y; `len(model_curve_at_horizon) == len(KEY_TENORS)`), `test_horizon_pv_var_is_a_non_negative_loss` (500 PVs, `cvar95 ≥ var95 ≥ 0`).

`tests/expansion_acceptance.py`: `history_auto_degrades_without_keys`, `crypto_client_refusals_and_router` (`load_history("KRW-BTC")` → `UPBIT`; shape predicates), `etf_page_adjusted_sleeves`, `gate_noise_vs_edge` (uses `V.kupiec`, `V.pit_tests`, `V.ModelCard`; mutates `V.GATE["bootstrap_B"] = 300` globally), `strategies_are_causal` (covers `S.vol_target`), self-checks of `validate.py`, `strategies.py`, `equity_deriv.py`, `curve_models.py`, `fx_styles.py`, `vol_products.py`, `crypto/analytics.py` (which exercises `garch_scorecard` for `garch_t` and `gjr_t`).

`tests/engine_acceptance.py:1079` `test_81_…`: asserts `core.quant.history._requests is data.net.session`.

Not registered in the runner: the `__main__` self-checks of `core/quant/garch.py`, `core/quant/gjr.py` (run by hand today: rc 0, `ok gamma 0.137 LR 39.4 skew-t lambda -0.29`, 3.5 s) and `core/ficc/ratesim.py`. `gjr.py` (fit, Hansen skew-t round trips) has no direct test in the suite; only `gjr_t` scoring via the analytics self-check.

---

## D. Extension points for v2

### D.1 Placement table

| v2 item (spec name, verbatim) | Spec location | Natural home | Exists today → reuse | Must add |
|---|---|---|---|---|
| `sma_vol` / SMA20 σ̂: `σ̂_m(t) = stdev(r_m[t−19 … t]) × √252`, daily SIMPLE close-to-close returns, ddof = 1, mean-adjusted; stale-carry day excluded and window extends to the last 20 valid returns (SPEC:1561, 4310) | `core/quant/risk` (SPEC:908; TASK-M2-01) | `risk.py` | `History.simple_returns()`; `TRADING_DAYS` from `history` | the estimator. `strategies.realised_vol` is LOG-return, default window 22, no stale-carry handling: not interchangeable (on `synthetic_history("AAPL")` log vs simple σ20 differ by 0.7% relative, enough to miss a Level-1 golden) |
| `market_vol_target(market: str, decision_utc: datetime, estimator: str = "sma20") -> VTResult` — fields `sigma_ann, weight in [0,1], display_label_rel, display_label_abs, inputs, status`; `vt_m = min(1.0, target_m / σ̂_m(t))`; KR target 0.20, US 0.15, window 20, cap 1.0 permanent, no floor, `exposure_basis=total`; `< 20` valid returns → status `insufficient_history` (→ `warmup`, weight 1.0, before the book's first ARMED decision; `MissingInput("missing")` after); σ̂ 0 or non-finite → `MissingInput` (SPEC:1044-1047, 1562-1563, 4286-4311; T-VT-01 SPEC:5673) | `core/quant/risk` | `risk.py` | nothing | function + frozen `VTResult`. Golden: rv20 28.82%, vt 0.694 on 2026-10-02 (KOSPI); weights 0.3025 / 0.3310 / 0.2485 earning on 2026-06-22 / 06-23 / 07-30 (R3:1049-1051) |
| `display_label_rel` (quartiles of trailing 756 sessions), `display_label_abs` (quartiles of expanding history, ≥ 10 years); values `[calm, normal, elevated, stressed]`; boundary takes the higher label; display only (SPEC:1565, 4312-4314; T-LABEL-01 SPEC:5643) | `core/quant/risk` (TASK-M2-02) | `risk.py` | nothing | function; must be causal (appending future data never changes past labels) |
| `sleeve_vol_scale(market: str, family: str, decision_utc: datetime, revision: int) -> VSResult` — `σ126(t) = stdev(r_LS[t−125 … t]) × √252` (ddof = 1) on the paper unit-gross long/short series; rev 1 `vs = min(1.0, 0.12 / σ126(t))`; rev 2 target = expanding median of σ126 (min 252 obs), cap 1.0; rev 3 `vs = min(1, (0.12/σ126)²)`; min 126 valid obs; no floor; `exposure_basis=active` (SPEC:1048-1050, 1518-1520, 4318-4320) | `core/quant/risk` (SPEC:927) | `risk.py` | nothing (`tsmom` uses EWMA/261 at 40%: different rule) | function + `VSResult`. Kernel golden (local file `datalab/results/r2_kr/r2_kr_crash_exposure_2026.csv` lines 3, 7): σ126 0.216946 → 0.553134; σ126 0.438216 → 0.273837 (2026-06-22) |
| `compose(vt: float, overlays: list[float], ladder: float, post_rearm_cap: float) -> float   # vt * min([1.0] + overlays + [ladder, post_rearm_cap]); raises on product` (SPEC:1058); bounds `assert 0.5 <= overlay_multiplier <= 1.0`, `assert 0.0 <= vt <= 1.0`, `assert 0.0 <= vs <= 1.0`; ladder, post_rearm_cap ∈ {1.0, 0.5}; `composed ≥ 0.5 × vt` outside HALTED; overlay layer cannot emit 0 (SPEC:881, 1506, 4272-4277; T-CAP-01, T-CAP-02 SPEC:5626-5627: 10,000 draws, seed 11, 0.75 and 0.5 compose to 0.5 never 0.375, binding factor logged) | `core/quant/risk.compose`; `core/quant/signals.apply_overlays` | `risk.py` (pure function, no data access) | nothing | function returning the value and the binding factor; `gross(m) = min(composed(m), concentration_bound(m))` (SPEC:873) |
| `hedge_state(decision_utc: datetime) -> HedgeState` — `hedge_credit_off = (corePCE_yoy ≥ 0.030) or (corr63 > 0) or (any input stale or failing) or (an exception inside hedge_state)`; `hedge_failure = (equity_1d < −1.5%) and (USD_proxy_1d < 0)` or weekly S&P < −2% and USD week < 0; `classic_risk_off = (equity_1d < −1.5%) and (USD_1d > 0) and (UST10_1d < 0)`; `fx_hedge_credit` display only (26-week corr of weekly KOSPI vs ΔUSD/KRW ≥ 0 → no credit); corr63 on date-aligned pairs `(r_eq(D), −Δy(D))`; effect: `max(estimated corr, 0)` between equity and duration legs in VaR, stress, optimiser inputs; never HALTs (SPEC:1051-1052, 1612-1614, 4365-4370; T-CORR-01 +0.53 ± 0.01 at 2026-09-30, a series-lag implementation gives −0.094; T-HEDGE-01) | `core/quant/risk.hedge_state`; consumed by `core/quant/optimize` (TASK-M2-04, M2-05) | `risk.py`; clamp applied to `BasketStats.corr`/`cov` before `optimize_portfolio` | `align_histories` already intersects dates (date-aligned by construction) and returns `corr`; `BasketStats` is frozen → build a new instance (`dataclasses.replace`) with the clamped matrix | function + frozen `HedgeState`; a helper that rebuilds `cov` from clamped `corr` for tagged equity/duration pairs. No asset-class tag exists on `History`/`BasketStats` |
| `lookthrough_exposure(book: Book, decision_utc: datetime) -> Exposure`; `concentration_bound(market: str, decision_utc: datetime, template: str) -> ConcentrationBound   # {absolute_bound, active_bound, aggregate_bound, semis_bound, bound = their min, binding_factor}`; active single-name cap `w_i − g·b̃_i ≤ 0.05` NAV; `g_KR ≤ min(vt, limit_k / look-through share_k, 0.05 / (s_i − b̃_i) for every name i with s_i > b̃_i)`; template default `msci_25_50` (`single_name_max: 0.225`, `names_above: 0.045`, `aggregate_max: 0.45`, breach 0.25 / 0.50); semis ≤ 0.50; leveraged/inverse at × L (SPEC:1053-1054, 1585, 4331-4344; T-CAPS-01: 22.5 / 29.8 = 0.755, 0.05 / (0.298 − 0.225) = 0.685) | `core/quant/risk` (TASK-M5-01, M5-02) | `risk.py` (pure arithmetic kernel) | nothing; basket data (KODEX 200 PDF) is not loaded anywhere in this subsystem (`data.kis_markets.KISMarkets.etf_components` exists) | kernel + result type; template values come from `core/rules`, never literals in `risk.py` |
| `drawdown_ladder(nav_path, decision_utc: datetime) -> LadderState` — `LadderState{hwm_hard, ref_step, step_mult in {1.0, 0.5}, dwell_left, block_new_entries: bool, halted: bool, rearm_not_before, post_rearm_left, binding_share}`; −8% → 0.5×, −12% → 0.5× + new-entry block, 21-session dwell, hard stop −15% from HWM since last re-arm, re-arm refused 10 sessions then automatic, `post_rearm_cap` 0.5 for 10 sessions (SPEC:1055-1057, 1586-1587, 4345-4352) | `core/quant/risk.drawdown_ladder`; `core/engine` | `risk.py` | `_drawdown_curve(prices)` (:58) gives drawdown from the all-time peak only (R3 XS-08, R3:1296: all-time-peak reference is the failing design) | state machine over a NAV path with resettable references |
| `inverse_vol_weights(markets: list[str], decision_utc: datetime, cov: str = "ewma_weekly_0.97") -> dict[str, float]` — inverse-vol on WEEKLY returns, EWMA λ 0.97 acting, Ledoit–Wolf 156-week line printed, Σ_m IV_m = 1; no HRP, no min-variance (SPEC:858-859, 1066, 1716, 4282) | `core/quant/optimize` (TASK-M4-06) | `optimize.py` | nothing (`align_histories` is daily sample covariance only) | weekly resampling, EWMA variance, the printed Ledoit–Wolf line (not installed as a dependency: write the shrinkage formula in numpy or print-only) |
| `base_weights(decision_utc: datetime) -> dict[tuple[str, str], float]   # IV_m * 1/K_m over admissible families`; admissible iff prior ≥ 1 and card verdict ≠ REJECT; range prior → lower bound; no registered prior → not admissible; NOT_RUN admissible except `ts_trend` (SPEC:860-863, 1061, 1712-1720, 4281-4285; T-PRIOR-01) | `core/quant/signals` + `core/rules` | `signals.py` | nothing | function; priors and verdicts are rules-store data |
| `apply_overlays(composite, multipliers, basis) -> Weights`, `dm_gate(market, decision_utc) -> Multiplier` (value in {0.5, 1.0}, specification book only), family tags `momentum / reversal / flow / quality / ts_trend` (SPEC:1060-1063, 1169) | `core/quant/signals` | `signals.py` | the 6-component composite has no family tag and is single-instrument | optional tag field (append with default, see D.3); the factor sleeves and `composite_weights` are new objects, not a refactor of `compute_signals` |
| R-30 estimators `sma(window)`, `ewma(lam)`, `garch_t()`, `gjr_t()`, `range_proxy(market)`, `log_har_range()`, `comb()`; `COMB = ½(GJR-t + log-HAR-range)` in variance units; expanding windows ≥ 10 years, refit every 21 origins (SPEC:3165-3168, 3184-3189, 4294-4308) | `core/quant/garch` (TASK-M3-01) | `garch.py` / `gjr.py` | `fit_garch(profile=False)`, `forecast_variance(fit, h)`, `fit_gjr`, `next_variance` | multi-step GJR forecast (only one step exists), EWMA recursion, range proxies (need OHLC, which `History` lacks), log-HAR OLS, COMB, expanding-refit driver |
| R-30 harness `loss_registry` (QLIKE, MSE, tick loss); `dm_test` (HAC lags `max(10, 2h)`, Harvey–Leybourne–Newbold factor), `cw_test`, `gw_test`; `mcs(losses, stat='T_max', block=max(10, 2h), B=2000, seed=11)`; `kupiec`, `christoffersen_cc`, `es_z2` (Acerbi–Székely, simulated critical values), `fan_pit(h)`, `reliability_table`; `estimator_gate(card) -> GateResult`; target `y[t, h] = Σ_{j=1..h} r²_{t+j}` (SPEC:3169-3179) | `core/quant/backtest` (SPEC text) | next to the existing gate in `validate.py` (see D.2 collision 4) | `validate.dm_test` + `newey_west_t` (add the HLN factor and the lag rule as arguments, do not write a second DM), `validate.kupiec`, `validate.christoffersen` (already returns `lr_cc`/`p_cc`), `validate.pit_tests`, `validate.traffic_light`, `validate.crps`; QLIKE formula in `analytics.garch_scorecard` (:395) | MSE/tick losses, MCS, CW, GW, ES Z2, h-day fan PIT, reliability table, the gate itself |
| R-16 Quant Lab: expanding ≥ 10-year fits, FHS + GPD lower-10% tails, envelope `max(fast FHS, GJR-EVT)`, Kupiec/Christoffersen lines at 95% and 99%, ES 97.5% Z2, Basel zones, fan PIT at h = 21 and 126, 2016–26 and 2026 reported separately, √n_US scaling of the displayed 1-day VaR after multi-session gaps, "path-vol quartile" colours, seeded scenario library (a)–(e), historical-replay library, SEP bands through `ratesim` (SPEC:1747; I-11 SPEC:5701) | `core/quant/garch`, `core/quant/montecarlo`, `core/ficc/ratesim`, Quant Lab page (TASK-M9-01..04) | same | `fit_garch`/`fit_gjr`, `simulate_returns`, seeded `run_monte_carlo`, `ratesim.simulate`, `validate` tests, `traffic_light` | everything listed; no lab output may be read by a sizing module (SPEC:1747 rule 6) |

### D.2 Naming collisions

1. `ewma_vol`: spec puts it in `core/quant/risk` (SPEC:908); `strategies.ewma_vol(prices, com=60.0)` already exists with centre-of-mass parameterisation and 261-day annualisation. RiskMetrics `ewma(lam)` with 252 is a different function; do not reuse the name with different semantics in a module that star-exports.
2. `sma` / `ewma` (spec, variance estimators in `core/quant/garch`, SPEC:3166) vs `signals.sma(px, n)` / `signals.ema(px, n)` (PRICE moving averages, imported by `backtest.py` and `ui/qcharts.py`) and `strategies._sma`.
3. `dm_test`, `kupiec`, `christoffersen` already exist in `validate.py`; the spec lists `dm_test`, `kupiec`, `christoffersen_cc` under `core/quant/backtest`.
4. `core/quant/backtest` is a single 155-line module (`run_backtest`), while the spec assigns ~20 gate functions to it (SPEC:1089-1098, 3169-3174) and calls the existing gate "exists". The existing gate is `core/quant/validate.py`. Converting `backtest.py` to a package must keep `from core.quant.backtest import run_backtest, BacktestResult, STRATEGIES` working (4 importers).
5. `vol_target`: config key and concept (SPEC:4286) vs `strategies.vol_target(...)` (21-session step, 10% band, window 22, log returns). The R-06 rule is daily, no band on ETF/futures lines (SPEC:1564).
6. `FAMILIES` / "family": `strategies.FAMILIES` (strategy families) and `ui.strategy_lab_page.FAMILIES` (tuples) vs the v2 factor families `momentum/reversal/flow/quality/ts_trend`.
7. `MODELS` and `FAN_PERCENTILES` are defined in both `montecarlo.py` and `ratesim.py` (different `MODELS`).
8. `simulate`: `strategies.simulate`, `ratesim.simulate`, `garch.simulate_returns`; `half_life`: `garch._half_life(p)` vs `strategies.half_life(x)`.
9. `estimator` ids in the spec `{sma20, ewma094, ewma097, garch_t, gjr_t, log_har_range, comb}` (SPEC:3230) vs `montecarlo.MODELS` id `garch_t` (a simulation model) and `garch_scorecard` model ids `garch_t / gjr_t / gjr_skewt`.
10. Label words: R-06 reserves `calm / normal / elevated / stressed` (SPEC:1126, 4313); `signals.py:153` already prints `compressed / elevated / normal` for σ20/σ100.
11. `TRADING_DAYS = 252` is defined five times (`history`, `garch`, `validate`, `ficc/common`, `ficc/equity_deriv`); spec key `annualisation_days: 252` (SPEC:4309).

### D.3 Constraints

- Every result type in this subsystem is `@dataclass(frozen=True)`; array fields are `field(repr=False, default=None)`. Follow the same pattern for `VTResult`, `VSResult`, `HedgeState`, `ConcentrationBound`, `LadderState`. Frozen dataclasses holding `np.ndarray` cannot be compared with `==` safely.
- `History` and `SignalComponent` are built positionally in several places (`History(h.symbol, h.source, h.dates, h.closes, note=…)` in `history.py:488/498/503`, tests, `strategies.py:464`; `SignalComponent("trend50", "Price vs 50-day SMA", score, 0.20, …)`). New fields must be appended with defaults. A new `History` field is dropped by the cache round trip unless both the dump (`history.py:445-448`) and the load (`:435-437`) are extended; `data.kis_markets.Bars.to_history` and `data.crypto.crypto_client.Candles.to_history` also construct `History`.
- Error conventions: `ValueError` for bad arguments or too little data, `HistoryError` for providers, `FICCError` in `ratesim`; degradation is always labelled in a field (`note`, `engine`, `converged`, `at_bound`, `se_note`, `source="SYNTHETIC"`), never silent. v2's `status` / `MissingInput` returns fit this pattern.
- Spec interface rules (SPEC:1105-1113): every function takes `decision_utc` and the run's pinned `knowledge_utc` (never "now"), reads data only through `pit_value`, never a raw frame; acting input failure → previous state, `fail_closed = true`; risk-model failure → `hedge_credit_off = TRUE`; no function may import an order-submission client (T-RO-01); no acting function may read `context_log`. Existing functions here take an already-loaded `History`/array and use `date.today()` (`synthetic_history`, `fmp_history`, `kis_history`, `analyze_history`'s gs_quant index). Workable split: a pure array kernel in `risk.py` (unit-testable on fixtures) plus a thin wrapper with the spec signature that does the PIT read.
- SYNTHETIC fallback of `load_history(source="auto")` is forbidden for acting inputs (`synthetic: bool  # True is never accepted for an acting input -> MissingInput`, SPEC:985); `load_history` can serve the `history` role only.
- Seeds in use: 7 (`run_monte_carlo`, `simulate_returns`, `ratesim.simulate`), 11 (`efficient_frontier` cloud). Spec seeds: 11 (T-CAP-02, `mcs`, `n_eff`).
- `rf_rate=0.03` and `erp=0.04` are literal defaults in `risk`, `optimize`, `montecarlo`; v2 cards use excess returns with call-rate cash (SPEC:1574) from the data layer, not these defaults.
- `risk.py` imports pandas + gs_quant at import time (2.4 s). `core/engine` currently imports nothing from `core/quant`; engine hooks that import `core.quant.risk.compose` will pull gs_quant into engine start-up unless the gs_quant import is moved inside `analyze_history` or the pure functions live in a module that does not import it.
- Flet 0.85 guard (`tests/flet_api_guard.py`) scans `ui/*.py` only: `ft.Dropdown(on_select=…)` not `on_change`, `page.show_dialog`/`pop_dialog` not `open`/`close`, constructor kwargs of the listed controls checked against the installed Flet. Applies to any Quant Lab / Macro page additions, not to `core/quant`.
- Quant Lab reads cards by literal ids (`D_Q_garch_spy`, …) and keys `stats.exceed95`, `decision`, `lines`, `decision_reason`; new card schemas (`model_card.macro`) must not break `validate.load_cards` consumers (it returns raw dicts and skips unreadable files).
- Optimiser semantics differ from v2: `optimize_portfolio` always sums to 1 and renormalises after clipping; v2 forbids renormalising freed budget (T-MONO-01, SPEC:883). Do not route v2 book weights through `_solve`.
- Tech-fund items landing here: MOM-1 = R-03 on every momentum sleeve including KRX (R3:227-232, XS-10 R3:1298); RISK-1 caps by book type (R3:234-239); IDX-1 = R-06 unchanged (R3:250-255); SCR-1 lottery composite (volatility + MAX + turnover ranks) and SCR-2 dilution (252-session share growth > 10%) need volume and share-count panels that `History` (closes only) cannot carry; Politis–White block lengths (XS-11, R3:1299) exist nowhere (`montecarlo._simulate_bootstrap` block 5, `validate.block_bootstrap_ci` block 10).

---

## E. Gotchas

1. README is stale on counts: it says 229 / 245 checks and "48 equity quant checks" (`README.md:347-379`); the runner records 266 with 53 quant. It also lists a "GJR / skewed-t" self-check in the expansion group; `expansion_acceptance.tests()` has no `gjr.py` entry.
2. `synthetic_history` closes are deterministic per symbol but its dates end at `date.today()`, so any fixture built from it shifts daily; weekends are skipped, holidays are not.
3. `analyze_history` under gs_quant builds a fake business-day index ending today; the history's own dates are ignored. Its `sortino` uses the std of negative returns, not a downside deviation about a target.
4. Two different "VaR"s: `RiskReport.var_1d` is a 1-day historical VaR on LOG returns over the whole sample; `MCResult.var_pct` is a horizon loss fraction of spot. Neither is FHS, neither is graded.
5. Three ad hoc 20-ish-day vols coexist, none equal to the spec's SMA20: `signals` (`std(log r[-20:], ddof=1)`, daily units), `strategies.realised_vol` (log, default 22, ×√252), `analyze_history` (whole sample). `strategies.ewma_vol` annualises with 261.
6. `GarchFit.cond_vol` is daily, `cond_vol_last` and `uncond_vol` are annualised, `GJRFit.next_var` is a daily variance. `forecast_variance` returns daily variances.
7. The 504-session default (`load_history(days=504)`) drives every Quant Lab fit; the spec calls this window "regime-captured" (SPEC:1747 rule 1). Yahoo is capped at `"10y"` by `core.ficc.data._period_for` for any `days > 1260`, so `load_history` cannot return more than ten years from Yahoo, and the R-16/R-30 "expanding ≥ 10 years" fits need another path.
8. Yahoo closes are `auto_adjust=True` (restated on every dividend/split): not point-in-time, and tagged `adjustment="total"`; KIS closes are 수정주가 (`"split"`). Neither is an unadjusted official close.
9. `History` is not validated at construction and `_clean_rows` does not de-duplicate dates (FMP/Yahoo paths); `align_histories` builds `dict(zip(dates, closes))`, so a duplicate date silently keeps the last value.
10. `align_histories` intersects date strings: mixing a crypto series (7-day weeks) or a KRX series with a US one silently drops non-shared days; `sessions` counts price dates, not return rows; it does not look at `adjustment` (the page calls `convention_warning` separately).
11. Cache keys include `days`; the cache stores whole series and overwrites them, and a hit changes `note` only. `expansion_acceptance` sets `config.FICC_CACHE_TTL_SECONDS = 0.0` to keep fake rows out of the real cache directory; a new test that calls `load_history` with a ready provider and a positive TTL writes into `~/.nextgen/ficc_cache`.
12. `_no_credentials()` does not block Yahoo, Upbit or Binance: `load_history("^VIX")` or `"KRW-BTC"` under it would reach the network. New tests must patch `core.ficc.data._yf_fetch` / the crypto transport or use fixtures.
13. `tests/expansion_acceptance.py:273` mutates `V.GATE["bootstrap_B"] = 300` for the rest of the process (the expansion suite runs last).
14. `fit_garch` flags `"stationarity"` at 0.995 while the hard cap is `STATIONARITY_MAX = 0.9995`; on iid data SEs are empty by design (`"not positive definite"`); `eta = 0` (ν = inf) is a valid answer, not a failure.
15. `efficient_frontier` ignores `max_weight`; `_solve` clips then renormalises, so a cap can be exceeded by rounding (test tolerance 1e-6).
16. `montecarlo` requires ≥ 21 sessions but the default model needs ≥ 100 returns; the error then comes from `fit_garch`.
17. Windows / cp949: the runner reconfigures stdout to UTF-8; source files contain `σ`, `μ`, `—`, `±`, Hangul notes (`history.py:221`), so a script that prints `History.note` or `GarchFit.note` outside the runner needs `PYTHONIOENCODING=utf-8` or `-X utf8`; always pass `encoding="utf-8"` when reading/writing JSON or CSV.
18. The local data cache has no KOSPI index history: `docs/asset_expansion/cache/yf__KS200.csv` holds one row (2026-09-23) and there is no `^KS11` file. Available long series: `yf_069500.KS.csv` (KODEX 200, 2007-01-29 → 2026-09-23, Yahoo adjusted), `yf_SPY.csv` (1995-01-03 → 2026-09-25), `yf__VIX.csv`, `yf__VIX3M.csv` (from 2006-07-17), `yf_TLT.csv`, `fred_DGS3MO.csv`, `fred_DEXKOUS.csv` (from 2017), `upbit_KRW-BTC.csv`. All end before 2026-10-02.
19. `prep/readlines.py` in the scratchpad has a syntax error (unterminated string literal on line 4) and cannot be used.
20. `insights._SYSTEM` asks the model for "what the trade expression would be" and `signals.py`'s docstring says the module's job is "to hold an opinion"; v2 shows weights as a recommendation only from the recommended book (SPEC:886).

---

## Ambiguities (with the conservative reading)

| # | Issue | Lines | Conservative reading |
|---|---|---|---|
| 1 | `estimator_gate` has two signatures: `estimator_gate(market: str, instrument_book: str, horizon: int = 21) -> EstimatorSelection` vs `estimator_gate(card) -> GateResult` | SPEC:1101 vs SPEC:3174 | One function taking the card (which carries market, book, horizon); selection never acts: SMA20 stays the acting estimator (SPEC:3160) |
| 2 | Home of SMA/EWMA: `sma_vol`, `ewma_vol` in `core/quant/risk` vs `sma(window)`, `ewma(lam)` in `core/quant/garch` | SPEC:908, TASK-M2-01 vs SPEC:3166, TASK-M3-01 | One implementation of the SMA20 σ̂ (in `risk.py`); the R-30 registry entry delegates to it, so the acting estimator and the harness baseline cannot diverge |
| 3 | GJR bounds differ: spec `α + β + γ⁄2 ≤ 0.9999`, `ν ∈ (2, 100]`, `α + γ ≥ 0`; code `STATIONARITY_MAX = 0.9995`, `eta ∈ [0, 0.4]` (ν ≥ 2.5, ν = inf allowed), `α ≥ 0`, `γ ∈ [0, 0.5]` | SPEC:3187, 3203, 4306 vs garch.py:73-80, gjr.py:35 | Keep the code's tighter optimiser bounds; fall back to SMA20 (fail closed, SPEC:3202) whenever `converged` is False, `"stationarity"` or `"nu"` is in `at_bound`, or the fit is `effectively_normal` (ν > 100) |
| 4 | Return type: R-06 says simple returns; R-30's target `Σ r²` and DLB §1 (not on this machine) do not say; existing GARCH/GJR fit log returns | SPEC:1561, 4310, 3179 | Simple returns for σ̂ in R-06/R-03 exactly as written; GARCH-family forecasts stay on log returns; the harness records which it used on the card |
| 5 | Base weight normalisation: macro `IV_m × 1/K_m` (binding) vs tech-fund proposal `base_weight = w / 3` | SPEC:861, 1712 vs R3:703, R3:1309 (XS-21, type Proposal) | Macro formula; `w/3` is not built without an owner ruling; one-sided (`*`) cells feed no book |
| 6 | Korea caps: macro default `msci_25_50` + active 0.05, `pair_35` listed "without v1.2's 0.45 trigger"; tech-fund proposes by-book-type caps with a 0.35 pair cap triggered when the pair share exceeds 0.45, and the CR-07 denominator | SPEC:1585, 4333-4339 vs R3:234, R3:1295, R3:1310 (XS-07, XS-22) | Owner decision D1; default `msci_25_50`; bounds only ever lower gross (`gross = min(composed, bound)`); the pair-share denominator is rules-store data |
| 7 | Priors disagree between programmes (Korea ST reversal 1 vs 0, Korea flow 3 vs 1, US XS momentum 2/1 vs 1, crypto ST reversal 2 vs 0) | SPEC:1722-1732 vs R3:1289-1290, 1304-1305 | Priors live in `core/rules`; `base_weights` reads them and hard-codes none. Note that removing a family RAISES the others' weights by K/(K−1) (SPEC:1720), so no sleeve should act on either table until the owner rules |
| 8 | Mapping of the six composite components to families is "proposed and must be filled from the code" (BL-G07) | SPEC:1169 | Components are single-instrument technical indicators, none is cross-sectional momentum, reversal, flow or quality. Default: no tag (multiplier 1.0), composite stays a display read. Candidate mapping for owner confirmation only: `trend50`, `trend200`, `macd`, `momentum` (ROC63) → `ts_trend`; `rsi` → `reversal`; `vol` → untagged |
| 9 | "Mincer–Zarnowitz" is named in the task brief but appears in neither source bundle (0 matches) | — | Not a gate input; at most a printed diagnostic. R-30's registered tests are DM (HLN), CW, GW and the MCS |
| 10 | Which VaR is "the displayed 1-day VaR" to scale by √n_US: `RiskReport.var_1d` has no page; the Quant Lab shows a horizon VaR | SPEC:1747 rule 3, TASK-M5-09 | Display-only scaling on the lab's new 1-day line; never an input to sizing |
| 11 | R-16 says a 1-day VaR display comes only from a model that passes 1-day B5; the lab's current GARCH-t fan is labelled REJECT/UNVERIFIED on SPY until `docs/vol_backtest.py` exists (it does not) | SPEC:1561, 1747 rule 2, 3260 | Keep the existing fan with its study chips; add graded lines only from the new FHS path |
| 12 | T-VT-01 golden (rv20 28.82%, vt 0.694 on 2026-10-02) needs KOSPI official closes through 2 Oct 2026; none are on this machine | SPEC:5673; gotcha 18 | Test the kernel on a synthetic fixture with hand-computed σ̂ and on the tech-fund result values; mark the dated golden as pending data, not as passed |
| 13 | TF-32 "floored trend x VT20" is written as a product | R3:257-262 | It equals `vt × min(1.0, trend)` with one overlay in [0.5, 1], which is the `compose` form; FORWARD-SIM book only (R3:262) |
