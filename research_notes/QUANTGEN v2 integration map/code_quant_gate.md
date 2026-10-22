# code_quant_gate — the existing validation gate, mapped for the v2 gate package (CARD-P class)

Read completely: `core/quant/validate.py` (869 lines), `core/quant/backtest.py` (155), `core/quant/strategies.py` (469), `docs/asset_expansion_study.py` (846), cards `S_E2_voltarget_spy.json`, `D_Q_gjr_spy.json`, `M_C1_kimchi.json` (plus `S_V4_dollar_carry`, `S_B2_pca_fly`, `S_C3_*` inspected), `docs/asset_expansion/manifest.json`. Skimmed `docs/ASSET_EXPANSION_SPEC.md`. Cross-read for flows/tests: `tests/run_all.py`, `tests/expansion_acceptance.py`, `tests/quant_acceptance.py` (backtest block), `tests/flet_api_guard.py` (head), `ui/strategy_lab_page.py`, card readers in `ui/etf_page.py`, `ui/crypto_page.py`, `ui/quant_lab_page.py`, `docs/build_expansion_primer.py`.

Line-ref prefixes: `V:` validate.py · `S:` strategies.py · `B:` backtest.py · `ST:` asset_expansion_study.py · `SPEC:` QUANTGEN_MACRO_INTEGRATION.md · `R3:` R3_TF_neural_link.md · `AES:` ASSET_EXPANSION_SPEC.md.

Three facts the v2 builder must hold before anything else:

1. **The gate is `core/quant/validate.py`, not `core/quant/backtest`.** `core/quant/backtest.py` is a 155-line single-asset long/flat toy backtester for the Signals page; it has no gate, no ledger, no walk-forward. The spec files every v2 harness function under "`core/quant/backtest` (exists; these functions proposed)" (SPEC:1089-1098, 2124, 2429, 2551, 3404). The costed, causal engine the spec means is `core/quant/strategies.py::simulate` / `pnl_matrix`.
2. **A single-configuration card can never PASS the existing gate** (verified by running it: true Sharpe 2.0, CI [1.57, 2.40], DSR 1.00, G = 1 → `REVISE`, reason "interval check failed (interval includes zero)"). Cause: `pbo_cscv` returns `prob_loss = NaN` when G < 2 (V:190-191) and `flat = NaN <= 0.10` is False (V:479, 510). Every v2 macro card "declared no searched parameter" (SPEC:2546).
3. **`GATE` is a module-level mutable dict that tests, the UI and the study mutate at run time** (`bootstrap_B`: tests/expansion_acceptance.py:273 → 300; ui/strategy_lab_page.py:70 → 1000; ST:192 → 300 under `--quick`). A "frozen" v2 package must not read thresholds from it.

---

## A. File by file

### A1. `core/quant/validate.py` — the gate

Purpose (V:1-33): two loops, one vocabulary, one model card. Strategy loop = purged walk-forward on a pre-computed T×G P&L matrix + nine checks. Distribution loop = rolling-origin VaR / coverage / PIT. numpy + scipy only; "every random draw is seeded".

#### A1.1 Constants (verbatim)

```python
TRADING_DAYS = 252                                                   # V:48
EULER_GAMMA = 0.5772156649015329                                     # V:49
DECISIONS = ("PASS", "REVISE", "REJECT", "INSUFFICIENT_DATA")        # V:50
GATE = {                                                             # V:53-74  "change them here and nowhere else"
    "w_is": 756, "w_oos": 126, "min_is": 504, "ci_level": 0.90, "bootstrap_B": 2000, "block": 10,
    "dsr_min": 0.95, "pbo_max": 0.05, "pbo_reject": 0.20, "oos_is_min": 0.5, "years_pos_min": 0.60,
    "plateau_min": 0.5, "trades_min": 100, "trades_floor": 30, "oos_years_min": 5,
    "haircut": 0.6, "cost_stress": 2.0,
    "pbo_min_configs": 8, "prob_loss_max": 0.10,
    "bench_p_max": 0.10,
    "var95_min_origins": 500, "var99_min_origins": 1000, "pit_ks_min": 0.05, "pit_ks_reject": 0.01,
    "kupiec_min": 0.05, "cc_min": 0.05, "exceed_reject_mult": 2.0, "nonconv_max": 0.05,
}
```

Unused keys: `var99_min_origins` (never read). `cost_stress` is read only for text and the card's `costs.stress_multiplier`; the stress actually applied is the separate default `pnl_matrix(..., stress=2.0)` (S:380).

#### A1.2 Public API — statistics

| Function (line) | Signature | Returns / formula | Degenerate cases |
|---|---|---|---|
| `sharpe` V:80 | `(daily) -> float` | mean/std(ddof=1)·√252 on finite values; raw returns, no rf subtraction | size < 2 → NaN; sd = 0 → 0.0 |
| `lo_se` V:89 | `(daily) -> float` | Lo (2002) **iid** SE: √((1 + ½·sr_d²)/T)·√252, sr_d = SR/√252 | T < 2 → NaN. No autocorrelation term |
| `min_track_record` V:99 | `(sr_annual, level=0.90) -> float` | 252·(z/SR)², z = Φ⁻¹(1 − (1−level)/2) (1.645 at 0.90) | SR ≤ 0 → inf |
| `block_bootstrap_ci` V:106 | `(daily, *, block=10, B=2000, level=0.90, seed=11) -> (lo, hi)` | **Studentised circular block bootstrap** (Ledoit–Wolf 2008 form): T* = (SR* − SR)/SE*, CI = [SR − t_hi·SE, SR − t_lo·SE]; SE and SE* are the iid Lo SE; `starts = rng.integers(0, T, size=(B, ceil(T/block)))`, index `(start + arange(block)) % T`, truncated to T | T < 2·block → (NaN, NaN) |
| `sharpe_diff_bootstrap` V:129 | `(a, b, *, block=10, B=2000, level=0.90, seed=11) -> {"diff", "ci", "p"}` | **Paired** circular block bootstrap (same blocks for both); `diff` = SR(a) − SR(b) on the last `min(len)` points; `ci` = percentile interval of the bootstrap differences (tuple); `p = mean(d* ≤ 0)` — an **uncentred percentile p**, not studentised | T < 2·block → NaN dict. `p` can be exactly 0.0 (printed "p 0.00") |
| `expected_max_sharpe` V:154 | `(n_trials, sr_sd) -> float` | sd·[(1−γ)Φ⁻¹(1−1/N) + γΦ⁻¹(1−1/(N·e))] | N = 1 → 0.0 |
| `deflated_sharpe` V:163 | `(daily, *, n_trials, sr_sd_daily) -> float` | Bailey–López de Prado 2014, per-period units: Φ((sr − sr0)·√(T−1)/√(1 − g3·sr + (g4−1)/4·sr²)), sr0 = `expected_max_sharpe(n_trials, sr_sd_daily)`; g4 = non-excess kurtosis | T < 3 → NaN; denom ≤ 0 → NaN |
| `pbo_cscv` V:183 | `(pnl, *, S=8) -> {"pbo", "n_splits", "prob_loss", "slope"}` | CSCV: `np.array_split(arange(T), S)`; for every C(S, S/2) train choice: in-sample best column by annualised Sharpe, OOS rank `sum(sr_te <= sr_te[best])`, w = rank/(G+1), logit; `pbo = mean(logit < 0)`; `prob_loss = mean(OOS SR of the IS winner < 0)`; `slope` = OLS slope of OOS SR on IS SR | G < 2 or T < 2·S → all NaN, `n_splits` 0. **Objective is hard-coded Sharpe** |
| `_col_sharpe` V:211 | `(M) -> ndarray` | column-wise annualised Sharpe | sd = 0 **or NaN in the column** → 0.0 silently |
| `newey_west_t` V:216 | `(d, lag) -> float` | mean / √(Bartlett HAC variance / n) | n < 5 → NaN |
| `dm_test` V:230 | `(loss_a, loss_b, *, lag=0) -> {"t", "p", "mean_diff", "n"}` | Diebold–Mariano on d = loss_a − loss_b; two-sided normal p; negative t favours A | — |
| `data_checks` V:241 | `(dates, closes, *, max_gap_sessions=5, stale_days=5, today=None) -> list[str]` | problems list (empty = clean): `< 30 sessions`, duplicate dates, non-positive/non-finite closes, > 20 % zero returns, any |log return| > 0.5, calendar gap > `max_gap_sessions*2+3` days, last session older than `stale_days` | **Not called by the study or any page** (only by the self-check) |

#### A1.3 Strategy loop

```python
@dataclass(frozen=True)
class WalkForward:                      # V:275-285
    dates: tuple[str, ...]              # OOS session dates, concatenated
    pnl: np.ndarray                     # OOS net daily P&L (fraction of equity)
    pnl_stress: np.ndarray              # same at stressed costs
    turnover: np.ndarray                # |Δposition| per OOS session
    origins: tuple[int, ...]
    chosen: tuple[int, ...]             # grid index chosen at each origin
    is_sharpes: np.ndarray              # n_origins × G
    n_configs: int
    note: str = ""                      # f"IS {w_is} / OOS {w_oos} / embargo {embargo}; {n} origins; {G} configs"

def walk_forward(pnl, dates, *, turnover=None, pnl_stress=None, w_is=GATE["w_is"], w_oos=GATE["w_oos"],
                 embargo=0, min_is=GATE["min_is"]) -> WalkForward          # V:288
```

Algorithm (V:296-324):

```
M = pnl as T×G (1-D → T×1);  Ms = pnl_stress or M;  To = turnover or zeros
len(dates) != T                      → ValueError("dates (..) and pnl rows (..) differ")
first = w_is if T - w_is >= w_oos + embargo else min_is
T < first + embargo + 21             → ValueError("need at least {first+embargo+21} sessions for one walk-forward step, got {T}")
o = first
while o + embargo < T - 1:
    sr = _col_sharpe(M[max(0, o - w_is):o])          # IS window ends at o, exclusive
    g  = int(np.nanargmax(sr))                        # in-sample winner
    a, b = o + embargo, min(o + embargo + w_oos, T)   # OOS block
    append dates[a:b], M[a:b, g], Ms[a:b, g], To[a:b, g];  origins += [o]; chosen += [g]; is_sharpes += [sr]
    o += w_oos                                        # blocks tile, no overlap
```

- Defaults `w_is/w_oos/min_is` are **bound at import** (default-argument evaluation): mutating `GATE["w_is"]` later does not change them.
- When T is short the first IS windows are 504, 630, … sessions (expanding from `min_is`), but `note` still says "IS 756".
- G = 1 still discards the first 756 (+ embargo) sessions from the judged record; it does not "reduce to the full sample" (contrast SPEC:4760).
- Embargo per card = the holding period, passed by the caller (study: 1, 5, 21 or 63).

```python
def plateau_share(grid, sharpes, best, domain=None) -> tuple[float, bool]      # V:327
```
Share of the ±1-step neighbours of `grid[best]` (ONE parameter moved to its adjacent value in that axis's sorted value set; other parameters fixed) whose Sharpe ≥ 0.5 × best's (if best ≤ 0: ≥ best's). `edge` = best sits on the first/last value of an axis that has ≥ 3 values and that value is not a declared natural limit (`domain[name] = (lo, hi)`, match within 1e-12). `len(grid) < 2` or no neighbour found → `(1.0, edge)`. Called with the **last origin's in-sample Sharpes** and the last chosen index (V:444-445), not OOS numbers.

```python
def year_stats(dates, pnl) -> {"by_year": {yyyy: sum of daily P&L}, "positive_share", "max_year_share", "n_years"}   # V:364
def regime_split(pnl, bench, *, window=63) -> {} | {"high_vol", "low_vol", "up_market", "down_market"}             # V:374
```
`year_stats`: arithmetic sum of daily P&L per calendar-year prefix `d[:4]`; `max_year_share = max|year| / Σ|year|`. `regime_split`: trailing-63-session benchmark vol above/below its median and trailing sum > 0; returns `{}` when there is no benchmark, lengths differ, or `len(pnl) < 126`.

```python
@dataclass
class StrategyScore:                    # V:389-423 (mutable; _decide_strategy fills the last four)
    sr_oos: float; se_lo: float; ci90: tuple[float, float]; sr_is: float; oos_is: float
    dsr: float; pbo: float; pbo_slope: float; prob_loss_oos: float
    sr_stress: float; turnover_annual: float; n_trades: int; n_sessions: int
    years_positive: float; n_years: int; max_year_share: float
    plateau: float; edge: bool; regime: dict
    total_return: float; max_drawdown: float; haircut_sr: float; bench_sr: float; n_trials: int
    n_configs: int = 1
    bench_diff: float = nan             # SR − SR_bench
    bench_p: float = nan                # one-sided bootstrap P(diff ≤ 0)
    bench_ci: tuple[float, float] = (nan, nan)
    bench_mdd: float = nan              # benchmark max drawdown over the same OOS sessions
    decision: str = ""; reason: str = ""; revise_target: Optional[str] = None
    lines: list[str] = []

def score_strategy(wf, *, grid, full_pnl, n_trials, bench_daily=None, seed=11, domain=None) -> StrategyScore   # V:426
```

How each field is computed (V:432-465):

| Field | Computation |
|---|---|
| `sr_oos`, `se_lo` | `sharpe(wf.pnl)`, `lo_se(wf.pnl)` |
| `ci90` | `block_bootstrap_ci(p, block=GATE["block"], B=GATE["bootstrap_B"], level=GATE["ci_level"], seed=seed)` (read at call time) |
| `sr_is` | mean over origins of the chosen config's in-sample Sharpe |
| `oos_is` | `sr_oos / sr_is`; NaN when `sr_is` is 0 / NaN |
| `dsr` | `deflated_sharpe(p, n_trials=max(n_trials,1), sr_sd_daily)`, `sr_sd_daily = nanstd(_col_sharpe(full_pnl)/√252)` over the **current grid's columns** (0.0 when G = 1), even when `n_trials` > G |
| `pbo`, `pbo_slope`, `prob_loss_oos` | `pbo_cscv(full_pnl, S = 8 if len(full_pnl) < 2000 else 16)` (70 or 12,870 splits) |
| `sr_stress` | `sharpe(wf.pnl_stress)` |
| `n_trades` | count of OOS sessions with `|turnover| > 1e-12` (position-change days, not round trips) |
| `turnover_annual` | `mean(|turnover|)·252` |
| `years_positive`, `n_years`, `max_year_share` | `year_stats(wf.dates, p)` |
| `plateau`, `edge` | `plateau_share(grid, wf.is_sharpes[-1], wf.chosen[-1], domain)` |
| `total_return`, `max_drawdown` | from `cumprod(1 + p)` of the OOS P&L |
| `haircut_sr` | `GATE["haircut"] * sr_oos` |
| `bench_sr`, `bench_mdd`, `bench_diff`, `bench_p`, `bench_ci` | only when `bench_daily is not None and len(bench_daily) == len(p)`; else NaN and **step 5 is silently skipped**; diff via `sharpe_diff_bootstrap(p, bench_daily, block, B, seed)` (same seed as the CI → same block draws) |
| `regime` | `regime_split(p, bench_daily)` |

#### A1.4 The nine steps as coded (`_decide_strategy`, V:470-554)

| Spec step (SPEC:4758-4768) | Code | Threshold (GATE key) | Role in the decision |
|---|---|---|---|
| 1 Choose in the past, test in the future | `walk_forward` | `w_is` 756, `w_oos` 126, `min_is` 504, embargo = caller | produces the OOS record |
| 2 Interval must clear zero | `block_bootstrap_ci`, `lo_se` | `ci_level` 0.90, `bootstrap_B` 2000, `block` 10; pass = `ci90[0] > 0` | `hard[0]` |
| 3 Count every try | `deflated_sharpe` | `dsr_min` 0.95; N = `n_trials` | `hard[1]`; below → REJECT |
| 4 Not over-searched | `pbo_cscv` | `pbo_max` 0.05, `prob_loss_max` 0.10, `pbo_reject` 0.20, `pbo_min_configs` 8 | `hard[2]`; `pbo_reject` → REJECT |
| 5 Beat the benchmark on the same days | `sharpe_diff_bootstrap` | `bench_p_max` 0.10 (one-sided) | fail → REJECT (only when a benchmark was supplied) |
| 6 Survive twice the costs | `sharpe(wf.pnl_stress)` | `sr_stress > 0`; `cost_stress` 2.0 (text) | fail + interval includes zero → REJECT; fail alone → REVISE "execution" |
| 7 A plateau, not a peak | `plateau_share` | `plateau_min` 0.5 and `not edge` | `eng["plateau"]` → REVISE |
| 8 Most years | `year_stats` | `years_pos_min` 0.60; top-year share printed | `eng["regime"]` → REVISE |
| 9 Take 40 % off | `haircut_sr` | `haircut` 0.6; reported, not gated | line only |
| (extra, not in the spec table) OOS/IS | `oos_is` | `oos_is_min` 0.5 | `eng["over-search"]` → REVISE |
| (extra) trade count | `n_trades` | `trades_min` 100 | `eng["sample"]` → REVISE |
| (extra) sufficiency floor | `n_trades`, `n_years` | `trades_floor` 30, `oos_years_min` 5 | INSUFFICIENT_DATA, decided first |
| (extra) minimum track record | `min_track_record(sr_oos, ci_level)` | — | INSUFFICIENT_DATA route when only the interval fails |

Decision logic, in the exact order of the code:

```
pbo_meaningful = n_configs >= 8
flat           = prob_loss_oos <= 0.10                       # NaN → False
pbo_ok         = (pbo <= 0.05 or flat) if pbo_meaningful else flat
pbo_reject     = pbo_meaningful and pbo > 0.20 and not flat
hard = (ci90[0] > 0, dsr >= 0.95, pbo_ok)
eng  = {"over-search": oos_is >= 0.5, "execution": sr_stress > 0, "regime": years_positive >= 0.60,
        "plateau": plateau >= 0.5 and not edge, "sample": n_trades >= 100}
has_bench  = isfinite(bench_p);   bench_fail = has_bench and not (bench_p <= 0.10)

1. n_trades < 30 or n_years < 5
     → INSUFFICIENT_DATA; reason "{n} trades over {y} OOS years; the gate needs ≥ 30 trades and ≥ 5 years";
       revise_target "extend history"
2. (dsr < 0.95 and isfinite(dsr)) or pbo_reject or (sr_stress <= 0 and not ci90[0] > 0) or bench_fail
     → REJECT; reason = first true of:
         "deflated Sharpe below 0.95"
         "PBO above 0.20 and the in-sample winner loses out of sample"
         "loses money at 2× costs and the Sharpe interval includes zero"
         "does not beat its benchmark (Sharpe difference {+.2f}, p {.2f})"
       revise_target = None, unless bench_fail (whatever the reason) →
         "the sleeve set or the cost model, not the rule: the benchmark is as good"
3. all(hard) and all(eng.values())
     → PASS; reason "every gate criterion met"
4. not hard[0] and hard[1] and hard[2] and n_sessions < min_track_record(sr_oos, 0.90)
     → INSUFFICIENT_DATA; reason "the Sharpe interval includes zero but DSR and PBO pass; a Sharpe of X needs
       about N sessions to certify and M were available";
       revise_target "extend history (pykrx / Yahoo .KS), do not touch the rules"
5. otherwise → REVISE; failed = [k for k in eng if not eng[k]]; target = failed[0] or "interval";
       reason f"{target} check failed ({'; '.join(failed) or 'interval includes zero'})"
       revise_target by target:
         "over-search": "coarsen the grid or fix a parameter at the plateau centre; lengthen the IS window"
         "execution":   "lengthen the holding period or add a hysteresis band; never lower the cost assumption"
         "regime":      "only a pre-registered regime condition may be tightened; otherwise this is a new hypothesis"
         "plateau":     "widen the grid (edge) or move to the plateau centre and re-run"
         "sample":      "extend history or lengthen the sample"
         "interval":    "the Sharpe interval includes zero: extend history"
```

`lines` (V:472-508), always in this order, each a full sentence ending "passes"/"fails" with number, threshold and sample: [0] OOS Sharpe / Lo SE / 90 % interval · [1] deflated Sharpe after N trials · [2] PBO (two wordings: gated when ≥ 8 configs, "reported only" otherwise) · [3] OOS/IS · [4] benchmark line (only with a benchmark; includes drawdown vs the benchmark's, "reported, not gated") · years positive · Sharpe at 2× costs + turnover · plateau/edge · position changes · regime split (only if non-empty) · McLean–Pontiff haircut. 9 to 11 lines. Tests index `lines[2]`.

#### A1.5 Distribution loop

| Function (line) | Signature | Notes |
|---|---|---|
| `kupiec` V:560 | `(hits, alpha) -> {"n", "x", "rate", "lr", "p"}` | LR_uc, χ²₁; x = 0 or x = n → z-test (`lr = z²`, two-sided normal p); n = 0 → NaN |
| `christoffersen` V:573 | `(hits, alpha) -> {"lr_ind", "p_ind", "lr_cc", "p_cc"}` | independence χ²₁; `lr_cc = lr_uc + lr_ind`, χ²₂; size < 10 → NaN |
| `traffic_light` V:593 | `(hits99, window=250) -> "green" \| "yellow" \| "red"` | last 250: ≤ 4 green, ≤ 9 yellow, else red |
| `coverage_check` V:598 | `(inband, level=0.90) -> {"coverage", "se", "ok", "n"}` | `ok = |cov − level| ≤ 2·√(level(1−level)/n)`; n = 0 → no `"n"` key, `ok` False |
| `pit_tests` V:608 | `(u, *, lags=(1, 5, 20)) -> {"n", "ks_p", "chi2_p", "berkowitz_lr", "berkowitz_p", "mean", "acf_flags", "shape"}` | KS vs uniform; χ² on 10 bins; Berkowitz LR (χ²₃) on Φ⁻¹(u) AR(1); DGT correlograms of (u − ū)^k, k = 1..4, flag when |r| > 2/√n; `shape` ∈ {"U-shaped: fan too narrow", "inverted-U: fan too wide", "flat"}. **n < 20 → dict without `shape`, `mean`, `berkowitz_lr`** |
| `crps` V:645 | `(samples, x) -> float` | E|X − x| − ½E|X − X′| from a sample |
| `score_distribution` V:673 | `(*, hits95, hits99, inband90, pit, nonconv=None, horizon=1) -> DistributionScore` | Christoffersen only when `horizon == 1` |

```python
@dataclass
class DistributionScore:   # V:657
    n: int; kupiec95: dict; kupiec99: dict; christoffersen: dict; traffic: str; coverage90: dict; pit: dict
    nonconv_share: float; decision: str = ""; reason: str = ""; revise_target: Optional[str] = None; lines: list[str] = []
```

Decision (V:702-728), n = `hits95.size`:

```
1. n < 500                                   → INSUFFICIENT_DATA "{n} origins; the 95 % tests need ≥ 500"; revise "extend history"
2. k95.rate >= 2.0*0.05  or traffic == "red"  or pit.ks_p < 0.01  or nonconv_share > 0.05
                                             → REJECT: "exceedance at twice the target" | "red traffic light" |
                                               "PIT fails at the 1 % level" | "non-convergence above 5 % of origins"
3. checks = {"tails": k95.p > 0.05, "clustering": not (cc.p_cc < 0.05), "coverage": cov.ok,
             "pit": pit.ks_p > 0.05 and not pit.acf_flags, "light": traffic == "green"}
   all → PASS "every calibration test met"
4. else REVISE "{failed, …} failed"; revise_target for failed[0]:
     tails      → "tails too thin: t innovations, a lower ν floor, or the GJR leverage term" (rate > 0.05)
                  | "fan too wide: shorter window, or the bounded-innovation variance gap"
     clustering → "volatility dynamics missing: GBM → GARCH → GJR, or a longer half-life"
     coverage   → "band width: the horizon aggregation or the ½σ²_t correction"
     pit        → "centring: drift mode or dividend / FX-rate conventions" (|mean − 0.5| > 0.03) | "shape: see the histogram diagnosis"
     light      → "recent 99 % exceptions: re-examine the last year's fits"
```
Six `lines` are built **before** the sufficiency check and index `pit["shape"]` → `KeyError` when fewer than 20 finite PIT values are passed.

#### A1.6 Model card

```python
@dataclass
class ModelCard:                         # V:734-766 (mutable)
    card_id: str
    kind: str                            # "strategy" | "distribution" | "model"  (the study also writes "error")
    hypothesis: str
    rules: dict; universe: dict; data: dict; costs: dict; protocol: dict; trials: dict
    seed: int
    stats: dict; tests: dict
    decision: str; decision_reason: str; revise_target: Optional[str]
    lines: list[str]
    decay_haircut: dict = {"factor": GATE["haircut"], "source": "McLean-Pontiff 2016 26-58%"}   # default_factory
    created: str = date.today().isoformat()                                                     # default_factory
    author: str = "QUANTGEN validation gate"
    results_file: str = ""; results_md5: str = ""
    citations: list[str] = []
    def to_json(self) -> str     # json.dumps(asdict(self), ensure_ascii=False, indent=1, default=_json_default)
    def save(self, directory: Path) -> Path   # mkdir(parents=True, exist_ok=True); <directory>/<card_id>.json, utf-8

def _json_default(o)                     # np scalar → .item(); ndarray → list; tuple → list; anything else → str(o)
def load_cards(directory: Path) -> list[dict]   # sorted *.json; a file that fails to parse is skipped silently; missing dir → []
def md5_of(path: Path) -> str            # hex md5 of the bytes, "" if missing
```
No schema validation, no hash chain, no header/result split. NaN/inf are written as bare `NaN` (not strict JSON).

#### A1.7 Units and conventions
- P&L is a daily fraction of equity, net of costs; Sharpe annualised by √252 with **no excess-return subtraction** (cash is credited inside `simulate`).
- Dates are ISO strings; the P&L row for the move t → t+1 carries date t+1.
- Seeds: every bootstrap function defaults `seed=11`; the study passes `SEED = 11`.
- Self-check `python core/quant/validate.py` (V:798-869): planted Sharpe-1 edge among 24 noise configs, self-benchmark REJECT, small-grid "reported only", five pure-noise matrices never PASS, Kupiec/Christoffersen/traffic/PIT/CRPS/DM/data_checks/card round-trip. Takes ~46 s at B = 2000.

### A2. `core/quant/strategies.py` — the costed, causal engine and the families

Contract (S:1-23): `prices (T×N) → weights (T×N)`; weight row t is decided from prices up to and including t and **held over t → t+1**.

```python
BP = 1e-4                                                                 # S:34
@dataclass(frozen=True)
class Panel: dates: tuple[str, ...]; symbols: tuple[str, ...]; prices: np.ndarray; sources: tuple[str, ...] = ()   # S:40; __len__ = len(dates)
def align_panel(histories: Sequence[History]) -> Panel                    # S:51; intersection of dates; < 60 shared → ValueError
def simulate(prices, weights, *, cost_bps: float = 5.0, cash_daily: np.ndarray | float = 0.0) -> tuple[np.ndarray, np.ndarray]   # S:69
def equity_curve(pnl) -> np.ndarray                                       # S:93; [1.0, cumprod(1+pnl)]
def summary(pnl) -> {"total_return", "ann_return", "ann_vol", "sharpe", "max_drawdown", "sessions"}   # S:97
def realised_vol(prices, window: int = 22) -> np.ndarray                  # S:119; std(ddof=1) of the last `window` log returns up to close t, ×√252; NaN before `window`
def ewma_vol(prices, com: float = 60.0) -> np.ndarray                     # S:129; MOP eq.(1), annualised with 261; NaN before t = 22
def half_life(x) -> float                                                 # S:255; −ln2/lnφ of AR(1); inf if φ ≥ 1 or φ ≤ 0 or size < 10
def adf_pvalue(x) -> float                                                # S:266; statsmodels adfuller(autolag="AIC")[1]; ANY exception → NaN
def pnl_matrix(prices, fn, grid, *, cost_bps, cash_daily=0.0, stress: float = 2.0) -> tuple[M, Ms, Tv]   # S:379; each (T−1)×G
def grid_from(**axes) -> list[dict]                                       # S:392; cartesian product, first axis outermost
FAMILIES = {"trend_switch", "vol_target", "xs_momentum", "tsmom", "crypto_trend", "risk_parity"}   # S:373 (name → function; pairs excluded)
```

`simulate` (S:74-90), exact accounting:

```
ret      = P[1:] / P[:-1] − 1                       # simple returns, T−1
held     = W[:-1]
cash_w   = 1 − Σ max(held, 0)  if every weight in the row ≥ 0  else 0.0     # may be negative when gross long > 1 (financing at the cash rate)
gross    = Σ held·ret + cash_w · cash_daily[:-1]     # cash_daily: scalar, or array broadcast to length T (aligned with prices)
turnover = |diff([0-row; W])| summed over assets     # length T; turnover[0] = |W[0]| (initial entry is charged)
pnl      = gross − turnover[:-1] · cost_bps · 1e-4   # the change made at close t is charged on the session t → t+1
return pnl (T−1,), turnover[:-1] (T−1,)
shape mismatch → ValueError("prices {..} and weights {..} differ")
```
One flat cost per unit of |Δw|, the same for buys and sells. No tick floor, no sell-side tax, no spread/impact model, no integer lots, no auction fill, no borrow cost for shorts (a book with any short earns no cash on the residual).

Families (all causal; `tests/expansion_acceptance.py::test_strategies_are_causal` asserts it):

| Function (line) | Signature | Rule |
|---|---|---|
| `trend_switch` S:162 | `(prices, *, rule="sma", lookback=210, step=21, cash_rate_daily=0.0, vol_cap=None)` | Faber: hold sleeve i (1/N) when P > SMA(lookback); `rule="tsmom"`: trailing `lookback` excess return > 0; evaluated every `step` from index `lookback`; `vol_cap` = σ* → × min(1, σ*/σ̂₂₂) |
| `vol_target` S:190 | `(prices, *, target, window=22, step=21, cap=1.0, band=0.10)` | w = min(cap, target/σ̂_window); rebalance days `arange(window+1, T, step)`; keep the previous weight when `|w − last| ≤ band·max(last, 1e-9)` (relative band); 0 before the first rebalance and where σ̂ is not finite |
| `xs_momentum` S:212 | `(prices, *, lookback=252, skip=21, top=1/3, step=21, long_only=True)` | rank on P[t−skip]/P[t−lookback] − 1; equal-weight top k = max(1, round(N·top)) |
| `tsmom` S:232 | `(prices, *, lookback=252, vol_target_ann=0.40, com=60.0, step=21, cap=1.0, long_only=False, cash_rate_daily=0.0)` | sign(excess return) × min(vol_target/σ̂_ewma, cap) / N |
| `pairs` S:287 | `(prices, *, formation=252, trading=126, entry=2.0, exit=0.0, max_hold=None, long_only=False, gross=1.0) -> (W, PairsDiagnostics)` | Engle–Granger step 1 on the formation window, frozen (a, b, μ, σ), z-score entry/exit; needs exactly two columns (y, x) else ValueError |
| `crypto_trend` S:330 | `(prices, *, lookbacks=(7,14,21,28), mas=(10,20,50,100,200), hysteresis=0.2)` | mean of 9 sign votes ∈ [−1, 1]; long above +h, flat below −h; composite lives on the lattice k/9 |
| `risk_parity` S:351 | `(prices, *, window=250, step=63)` | `core.quant.optimize.optimize_portfolio(stats, objective="risk_parity")` on a rolling covariance |

```python
@dataclass(frozen=True)
class PairsDiagnostics: formation_ends; hedge_ratios; adf_p; half_lives      # S:274; property share_cointegrated = mean(adf_p < 0.05) over finite p (NaN if none)
```
Self-check `python core/quant/strategies.py` (S:404-469) prints `ok`.

### A3. `core/quant/backtest.py` — single-asset rule backtester (NOT the gate)

```python
STRATEGIES = ("ma_cross", "momentum", "rsi_revert")                         # B:29
@dataclass(frozen=True)
class BacktestResult:                                                        # B:32
    symbol: str; strategy: str; params: dict; sessions: int; n_trades: int; cost_bps: float
    dates: tuple[str, ...] = (); equity: np.ndarray = None; bench_equity: np.ndarray = None; position: np.ndarray = None
    total_return: float = 0.0; bench_return: float = 0.0; ann_return: float = 0.0; ann_vol: float = 0.0; sharpe: float = 0.0
    max_drawdown: float = 0.0; bench_max_drawdown: float = 0.0; exposure: float = 0.0; win_rate: float | None = None
    @property beat_benchmark -> bool      # total_return > bench_return
def run_backtest(history: History, *, strategy="ma_cross", params=None, cost_bps: float = 10.0) -> BacktestResult   # B:107
```
- Long/flat 0/1 positions; signal on close t earns t+1 (`held = pos[:-1]`); cost `cost_bps/1e4` per unit of |Δpos|; benchmark = buy-and-hold of the same series; `sharpe = mean·252/vol` (arithmetic, no rf); `n_trades = int(Σ|Δpos|)` (entries + exits).
- Params: `ma_cross` {fast 20, slow 50}; `momentum` {lookback 63}; `rsi_revert` {buy_below 30, exit_above 55, period 14}.
- Errors: `< 60` sessions → ValueError("Need at least 60 sessions to backtest."); `fast >= slow` → ValueError; unknown strategy → ValueError.
- Importers: `ui/signals_page.py:17` (`STRATEGIES, run_backtest`), `ui/qcharts.py:26` and `core/quant/insights.py:30` (`BacktestResult`), `tests/quant_acceptance.py:22` (`run_backtest`). Imports `core.quant.history`, `core.quant.signals.sma` only.

### A4. `docs/asset_expansion_study.py` — the card runner

CLI: `python docs/asset_expansion_study.py [--quick] [--only id1,id2] [--refresh]` (ST:820-841). `--quick`: `V.GATE["bootstrap_B"] = 300` and GARCH `refit=21` instead of 7. A candidate that raises becomes an `error_card`; the study never stops.

Module-level state: `OUT = ROOT/"docs"/"asset_expansion"`, `CACHE = OUT/"cache"`, `CARDS = OUT/"cards"` (all `mkdir`-ed **at import**, ST:54-58); `SEED = 11`; `QUICK = False`; `REFRESH = False` (defined at ST:844, after its users); `ROWS`, `CARD_LIST`, `DATA_SPANS` (declared, never filled).

**Cost table (bp per side = per unit of turnover; ST:60), verbatim:**

```python
COST = {"krx_etf": 3.0, "us": 50.0, "krx_stock": 35.0, "crypto": 10.0, "futures": 5.0, "fx": 10.0}
```

| Key | bp | Meaning (ST:18-20, AES / README) | Cards |
|---|---|---|---|
| `krx_etf` | 3 | KRX ETF | S_E1_trend_krx, S_E2_voltarget_kodex200, S_E8_pairs_kodex_tiger |
| `us` | 50 | US via KIS | S_E1_trend_us, S_E2_voltarget_spy, S_E3_riskparity_us, S_E5_xsmom_sectors, S_E8_pairs_gld_iau |
| `krx_stock` | 35 | KRX stock "incl. tax" (flat both sides) | S_S6_pairs_samsung_pref, S_S6_pairs_hyundai_kia |
| `crypto` | 10 | crypto | S_C3_crypto_trend_btcusd / _krwbtc |
| `futures` | 5 | futures | S_B3_tsmom_futures |
| `fx` | 10 | FX | S_V3_fx_momentum (10, stress 20); S_V4_dollar_carry runs at `COST["fx"]/2` = 5 with stress 10 but its card says `cost_bps: 10.0` (ST:408-409, 439) |
| (literal) | 5 | VIX roll-down | S_V1_vix_rolldown: `cost_bps=5.0` hard-coded; `universe.venue` text says "us (10 bp per side, futures-like)" (ST:386-387) |
| (literal) | 1 | PCA fly: `cost_bp = 1.0` "per leg per round trip, yield bp" (ST:483) | S_B2_pca_fly |

Stress = 2× via `pnl_matrix(stress=2.0)`.

Data loaders (cached CSV, one series per file): `_cached(name, loader)` ST:68 (file = name with `= ^ : /` → `_`), `yf(symbol, start="1995-01-01")` (yfinance `auto_adjust=True` close; file `yf_<symbol>.csv`), `fred(series_id, start="1990-01-01")` (`fred_<id>.csv`), `upbit(market="KRW-BTC")`, `binance(symbol="BTCUSDT")`, `binance_funding(symbol)`, `panel(series: dict, *, start=None) -> S.Panel` (inner join, `< 300` shared sessions → RuntimeError), `rf_daily(index) -> ndarray` (FRED DGS3MO /100/252, ffill, 0.03 fallback; any failure → constant 0.03/252).

Card builders:

```python
def strategy_card(card_id, *, hypothesis, fn, grid, pnl: S.Panel, cost_bps, embargo, bench, universe, citations,
                  cash_daily=0.0, rules=None, ledger=None, n_trials=None, domain=None) -> V.ModelCard        # ST:173
def model_card(card_id, *, kind, hypothesis, decision, reason, stats, tests, lines, universe, data, citations,
               revise=None, rules=None) -> V.ModelCard                                                      # ST:218
def error_card(card_id, exc) -> V.ModelCard                                                                 # ST:230
def _rows(card_id, **metrics) -> None            # appends {"card", "metric", "value"}; tuple/list → metric_0, metric_1, …
def write_results() -> None                                                                                 # ST:764
```

`strategy_card` pipeline (ST:181-215): `n_trials = n_trials or len(grid)` → `S.pnl_matrix(pnl.prices, fn, grid, cost_bps, cash_daily)` → `dates = pnl.dates[1:]` → `V.walk_forward(M, dates, turnover=Tv, pnl_stress=Ms, embargo=embargo)` → benchmark re-indexed onto `wf.dates` through a `dict(zip(dates, bench))` → `V.score_strategy(wf, grid=grid, full_pnl=M, n_trials=n_trials, bench_daily=b, seed=SEED, domain=domain)` → `V.ModelCard(...)` → `_rows(...)`.

Strategy candidates (ST:271-446, 723-739):

| Card id | Runner / family | Grid (G) | Cost key | Embargo | Benchmark | Start |
|---|---|---|---|---|---|---|
| S_E1_trend_us / _krx | `run_trend` / `S.trend_switch` | rule {sma, tsmom} × lookback {126, 210, 252} × step {21, 42} (12) | us / krx_etf | 21 | EW daily mean of sleeve simple returns (no cost) | 2004-12-01 / 2012-01-01 |
| S_E2_voltarget_spy / _kodex200 | `run_vol_target` / `S.vol_target` | target {0.08, 0.10, 0.12, 0.15} × window {22, 44} × step {21} (8) | us / krx_etf | 21 | **buy-and-hold of the same asset (exposure 1.0)** | 1994-01-01 / 2003-01-01 |
| S_E3_riskparity_us | `run_risk_parity` | window {125, 250, 500, 750} × step {21, 63} (8) | us | 63 | EW | 2004-12-01 |
| S_E5_xsmom_sectors | `run_xs_momentum` | lookback {126, 189, 252} × skip {5, 21} × top {1/3} × step {21, 42} × long_only {True} (12) | us | 21 | EW of 9 SPDRs | 1999-01-01 |
| S_B3_tsmom_futures | `run_tsmom` | lookback {63, 126, 252} × vol_target_ann {0.20, 0.40} × cap {1.0} × step {21, 42} × long_only {False} (12) | futures | 21 | EW of 10 Yahoo continuous futures | 2001-01-01 |
| S_C3_crypto_trend_* | `run_crypto_trend` | hysteresis {0.0, 0.222, 0.444, 0.667, 0.889} (5); `domain={"hysteresis": (0.0, 0.889)}`; `n_trials=11`; 2-entry `ledger` | crypto | 1 | buy-and-hold | full |
| S_E8 / S_S6 pairs | `run_pairs` | formation {126, 252} × trading {126} × entry {1.5, 2.0, 2.5, 3.0} × exit {0.0} × long_only {flag} (8) | per pair | 5 | EW when long_only (Samsung pref only), else None | 2009-01-01 (KODEX/TIGER), 2005-01-01 (KRX stock pairs), 2005-06-01 (GLD/IAU) |
| S_V1_vix_rolldown | `run_vix` | threshold {0.02, 0.04, 0.06, 0.08} × exit {0.0, 0.02} (8) | literal 5 | 1 | unconditional short VIXY | — |
| S_V3_fx_momentum / S_V4_dollar_carry | `run_fx` | formation_months {1, 3} (2) / rebalance_days {21} (**1**) | fx | 21 | G10 carry basket | — |

`run_pairs` mutates the returned card after scoring: `card.stats["share_cointegrated"]`, `card.stats["median_half_life"]`, and `card.lines.insert(0, …)` with a printed "gate: ≥ 60 % and 5–40 sessions" that is **not enforced** (ST:360-364).

Hand-rolled decisions for non-walk-forward cards (each runner computes its own verdict and passes it to `model_card`):

| Card | PASS condition | Otherwise |
|---|---|---|
| M_B1_dns (ST:458) | DNS beats RW at ≥ 4 of 5 maturities at 12 m and DM t < −1.96 at ≥ 3 | REVISE if beats ≥ 3, else REJECT |
| S_B2_pca_fly (ST:484-485; `kind="strategy"`) | adf_p < 0.05 and hit_rate > 0.55 and mean P&L/trade > 2×cost and half_life < 120 and n_trades ≥ 30 | REJECT if half_life > 120 or adf_p > 0.10, else REVISE |
| D_* fans (ST:498-531) | `V.score_distribution(...)`; then PASS → REVISE when the stationarity guardrail bound at > 5 % of origins (`"calibrated, but the variance is near-integrated at X of origins"`) | per A1.5; adds QLIKE vs EWMA(0.94) `V.dm_test(…, lag=5)` line |
| M_C1_kimchi (ST:539) | adf_p < 0.05 and half_life_days < 30 and pred_t finite and < −2 | REVISE |
| M_C4_funding (ST:560) | top-decile fwd30 < bottom-decile and bootstrap_p < 0.05 | REVISE |
| M_C8_ethbtc (ST:578) | never PASS: REVISE if adf_p < 0.05 else REJECT | — |
| M_C7_weekday (ST:591) | Bonferroni p > 0.05 | REVISE |
| M_E4_letf_drag (ST:627) | MAE_garch < 0.8·min(MAE_zero, MAE_last) and 0.7 ≤ slope ≤ 1.3 and R² ≥ 0.5 | REVISE |
| M_O1_board_today (ST:672) | live quotes and IV reconciliation ok and parity within ≥ 0.95 and 0 butterfly violations and SVI near-RMSE ≤ 0.5 and arbitrage-free | REVISE |
| M_O2_basis_today (ST:710) | |theo gap| ≤ 0.1 + 0.02·spot·T | REVISE |

`write_results()` (ST:764-817): merges `ROWS` into `results.csv` (rows of re-run cards replaced), computes `md5` of the merged CSV, reloads untouched cards with `V.load_cards(CARDS)`, sorts by `CANDIDATES` order, **re-stamps `results_file` / `results_md5` on every card and rewrites every card file**, writes `results.md` and `manifest.json`. `ModelCard.save()` is never used.

### A5. Artifact shapes

**Card JSON** — all 34 files share the same 22 top-level keys, in this order:
`card_id, kind, hypothesis, rules, universe, data, costs, protocol, trials, seed, stats, tests, decision, decision_reason, revise_target, lines, decay_haircut, created, author, results_file, results_md5, citations`. Kinds on disk: strategy 17, distribution 9, model 8.

| Key | Walk-forward strategy card (S_E2_voltarget_spy) | Distribution card (D_Q_gjr_spy) | Model card (M_C1_kimchi) |
|---|---|---|---|
| `rules` | `{"family", "grid": [...], "cost_bps_per_side", "embargo"}` | `{}` | `{}` |
| `universe` | `{"symbols": [...], "venue": <cost key>}` | `{"symbol"}` | free (`{"legs": [...]}`) |
| `data` | `{"sessions", "start", "end", "source": "Yahoo adjusted close unless stated"}` | `{"sessions", "start", "end", "window"}` | free (`{"start", "end"}`) |
| `costs` | `{"cost_bps", "stress_multiplier": 2.0}` | `{}` | `{}` |
| `protocol` | `{"w_is": 756, "w_oos": 126, "min_is": 504, "ci_level": 0.9, "bootstrap_B": 2000, "block": 10}` (values copied from `V.GATE` at run time) | `{}` | `{}` |
| `trials` | `{"N_planned": len(grid), "N_total": n_trials, "ledger": [free-text strings]}` | `{"N_planned": 1, "N_total": 1, "ledger": []}` | same |
| `seed` | 11 | 11 | 11 |
| `stats` | every `StrategyScore` field except `lines` (so it also repeats `decision`, `reason`, `revise_target`) + `regime`, `chosen_last`, `bench_sharpe` (= `bench_sr`), `walk_forward` (the note string), `seconds` (wall time) | `model, n_origins, exceed95, exceed99, coverage90, qlike_model, qlike_ewma, dm_t, dm_p, nonconv_share, stationarity_share, traffic, median_gamma` (+ `median_lambda` in current code) | free scalars |
| `tests` | `{"dsr", "pbo", "ci90": [lo, hi], "sr_stress"}` | `{"kupiec95_p", "kupiec99_p", "cc_p", "pit_ks_p", "berkowitz_p"}` | free (`{"adf_p"}`) |
| `decision` | one of `DECISIONS` | same | same |
| `decision_reason`, `revise_target` | from `_decide_strategy` | from `score_distribution` | runner text |
| `lines` | 9–11 gate sentences | 6 gate sentences + 2 runner sentences | runner sentences |
| `decay_haircut` | `{"factor": 0.6, "source": "McLean-Pontiff 2016 26-58%"}` — present on **every** kind | same | same |
| `created` / `author` | ISO date / "QUANTGEN validation gate" | same | same |
| `results_file` / `results_md5` | "docs/asset_expansion/results.csv" / md5 of the merged CSV | same | same |

Variants: `run_fx` cards use `rules = {"grid", "cost_bps_per_leg"}`, `protocol` with only `w_is/w_oos/min_is`, `tests` without `sr_stress`. Error card: `kind="error"`, `decision="INSUFFICIENT_DATA"`, `decision_reason=f"{type(exc).__name__}: {exc}"`, `revise_target="fix the data or the code"`, `lines=[traceback]`, `trials={}`.

**`results.csv`**: long format `card,metric,value` (502 lines). Strategy rows: `decision, sr_oos, ci_lo, ci_hi, dsr, pbo, oos_is, sr_stress, years_positive, plateau, n_trades, n_sessions, max_drawdown, bench_sharpe, total_return, haircut_sr`. Model rows: `decision` + every scalar in `stats ∪ tests`.

**`manifest.json`**: `{"run": "2026-09-27", "seed": 11, "results_md5": "ca757e25f508b588cb2f361719ec83cd", "quick": false, "cards": [34 ids], "rescored": ["M_O1_board_today"], "decisions": {card_id: decision}}`. Current tally: 5 PASS (S_C3 ×2, M_C4, M_C7, M_O2), 11 REVISE, 18 REJECT.

---

## B. Cross-file flows, persistence, environment

```
docs/asset_expansion_study.py  main()
  └─ for cid, fn in CANDIDATES: card = fn()  ── exception → error_card(cid, exc)
       run_<x>()  ── yf / fred / upbit / binance → cache/*.csv ; panel() ; S.grid_from
          └─ strategy_card: S.pnl_matrix → V.walk_forward → V.score_strategy(→ _decide_strategy) → V.ModelCard ; _rows
          └─ or model_card(decision computed in the runner) ; D_*: core.crypto.analytics.garch_scorecard → V.score_distribution, V.dm_test
  └─ write_results(): results.csv (merge) → md5 → cards/*.json (all rewritten) → results.md → manifest.json

ui/strategy_lab_page.py   load_cards() → V.load_cards(ROOT/docs/asset_expansion/cards), sorted PASS, REVISE, REJECT, other
                          run_family(family, symbols, *, source="auto", cost_bps=10.0, days=5000, bootstrap_B=1000)
                              load_history → S.align_panel → S.pnl_matrix(cash_daily=0.03/252) → V.walk_forward → V.score_strategy
                              (benchmark = EW of the panel, none for pairs; n_trials = len(grid); sets V.GATE["bootstrap_B"])
ui/etf_page.py            _CARD_FOR = {"trend": ("S_E1_trend_krx", "S_E1_trend_us"), "vol": ("S_E2_voltarget_kodex200", "S_E2_voltarget_spy")}; M_E4_letf_drag
ui/crypto_page.py         verdict chips: M_C1_kimchi, M_C4_funding, S_C3_crypto_trend_btcusd, S_C3_crypto_trend_krwbtc, D_C2_garch_btc, D_C2_skewt_btc, M_C8_ethbtc
ui/quant_lab_page.py      _study_chips(): D_Q_garch_spy, D_Q_garch_kodex200 (stats.exceed95), D_Q_skewt_spy, D_Q_skewt_kodex200
docs/build_expansion_primer.py   V.load_cards + manifest.json → PDF (asserts cards exist)
core/ficc/curve_models.py, core/ficc/fx_styles.py, core/crypto/analytics.py → V.newey_west_t ; S.adf_pvalue, S.half_life
core/ficc/vol_products.py → S.simulate, S.summary
ui/signals_page.py, ui/qcharts.py, core/quant/insights.py → core.quant.backtest (run_backtest / BacktestResult)
```

Persistence:

| Path | Writer | Content |
|---|---|---|
| `docs/asset_expansion/cards/<card_id>.json` | `write_results` | 34 cards; the directory is globbed whole by every reader |
| `docs/asset_expansion/results.csv`, `results.md`, `manifest.json` | `write_results` | as A5 (`results_run2.md`, `study.log`, `study_run2.log` are earlier-run leftovers) |
| `docs/asset_expansion/cache/*.csv` | `_cached`, `fred`, `binance_funding` | 40 one-column series, first column = date. Yahoo adjusted closes (e.g. `yf_SPY.csv` 1995-01-03..2026-09-25, `yf_069500.KS.csv` 2007-01-29..2026-09-23, `yf__VIX.csv`, `yf__VIX3M.csv` from 2006-07-17), `fred_DGS3MO.csv`, `fred_DEXKOUS.csv`, `upbit_KRW-BTC.csv`, `binance_*`. `yf__KS200.csv` holds one row; there is **no KOSPI / KOSPI 200 index history** here. Not point-in-time (re-downloaded adjusted closes, no `available_at`, no `value_status`) |
| `qa/acceptance_results.json` | `tests/run_all.py` | `[{"test", "status", "seconds", "detail"}]`, 266 rows, all PASS at the last run |

Environment: `validate.py`, `strategies.py`, `backtest.py` read no env var and touch no disk except `ModelCard.save` / `load_cards` / `md5_of`. The study does `import config` (python-dotenv loads `.env`); KIS keys are needed only by `run_board` / `run_basis`; `run_fx`, `run_dns`, `run_fly` go through `core.ficc.data` loaders (their own cache, TTL `config.FICC_CACHE_TTL_SECONDS`); `run_weekday` calls `BinancePublic().daily` live with no cache (ST:589). `yfinance`, `pandas_datareader` are imported lazily inside the loaders; `statsmodels` is used by `adf_pvalue` but is absent from `requirements.txt` (0.14.6 is installed here).

---

## C. Existing tests and how tests are registered

Registration: each test module exposes `tests() -> list[tuple[str, Callable]]`; `tests/run_all.py:30-44` imports six modules and prefixes names (`cockpit/`, `engine/`, `ui/`, `quant/`, `ficc/`, `expansion/`), runs every callable in one process, writes `qa/acceptance_results.json`, exits 0 only if all pass. Two styles exist: explicit list (`tests/expansion_acceptance.py:306-325`) and auto-discovery of `test_*` globals (`tests/quant_acceptance.py:1001-1003`). A new module needs one import line and one list line in `run_all.py`. stdout is reconfigured to UTF-8 because the Korean Windows locale is cp949 (`run_all.py:24-28`).

| Test (as named in run_all) | File:line | Asserts |
|---|---|---|
| `expansion/gate_noise_vs_edge` | expansion_acceptance.py:264 | T = 2520, 12 configs, **sets `V.GATE["bootstrap_B"] = 300`**; planted Sharpe-1.2 column: `ci90[0] > 0`, `sr_oos > 0.7`; pure noise: `decision != "PASS"`, `dsr < 0.95`; `sg.dsr > sn.dsr`; ≥ 8 non-empty `lines`; `kupiec` p > 0.05 on a correct 5 % series; `pit_tests` ks_p > 0.05 on uniforms; `ModelCard.to_json()` contains `"decision"` (9 s) |
| `expansion/strategies_are_causal` | :290 | changing prices after index 600 leaves weights before 599 unchanged for trend_switch, vol_target, xs_momentum, tsmom, crypto_trend, pairs |
| `expansion/selfcheck_validate` | :318 via `_selfcheck` (`runpy.run_path(..., run_name="__main__")`) | the V:798-869 block (46 s; a fresh module copy, so GATE is at its defaults there) |
| `expansion/selfcheck_strategies` | :319 | the S:404-469 block |
| `expansion/selfcheck_crypto_analytics`, `selfcheck_curve_models`, `selfcheck_fx_styles`, `selfcheck_vol_products` | :320-324 | users of `newey_west_t`, `adf_pvalue`, `half_life`, `simulate` |
| `quant/test_backtest_costs_only_hurt` | quant_acceptance.py:474 | 100 bp run ≤ free run; same `n_trades` |
| `quant/test_backtest_has_no_lookahead` | :482 | momentum(lookback=1) on a rising series equals buy-and-hold from bar 1 to 1e-9 |
| `quant/test_backtest_rejects_inverted_ma_params` | :496 | `fast >= slow` raises ValueError |
| `quant/test_backtest_exposure_and_drawdown_sane` | :505 | exposure ∈ [0, 1], max_drawdown ≤ 0 |
| `quant/test_narratives_state_their_numbers`, `test_every_chart_renders_a_data_uri_image` | :514, :551 | `BacktestResult` consumed by `insights.narrate_backtest` and `qcharts.equity_chart` |
| `ui/*` (flet_api_guard.py: `test_page_methods_exist`, `test_control_keywords_exist`, `test_control_attribute_assignments_exist`, `test_theme_tokens_referenced_by_ui_exist`) | flet_api_guard.py:53-172 | AST lint of every `ui/*.py` against the installed Flet 0.85.2: every `page.<method>()` exists, every keyword of the listed controls exists, attribute assignments exist, theme tokens exist |

Not covered by any test: `docs/asset_expansion_study.py` (no run, no golden values), the card JSON shape, `write_results`, `data_checks`, `score_distribution` edge cases, `walk_forward` short-sample branch, the `ui/strategy_lab_page.py` `__main__` self-check (not registered).

---

## D. Extension points for v2

### D1. Where the spec's functions go

Spec location for all of R-21 / R-22 / R-23 / R-24 / R-30 / R-34 harness code: `core/quant/backtest` (SPEC:1089-1101; tasks TASK-M7-01…30 name `core/quant/backtest.<fn>`). Reality: that path is the toy backtester of A3. Constraints that decide the layout:

- The freeze hashes "the source files of every harness function" into `definitions_md5` and `docs/macro_overlay_study.py` refuses to run on a mismatch (SPEC:4820). Harness code therefore needs files that contain nothing else: an unrelated edit to the Signals-page backtester, or to the legacy gate, must not break the frozen md5.
- `from core.quant.backtest import run_backtest, STRATEGIES, BacktestResult` has four import sites (A3) that must keep working.
- Legacy thresholds and verdicts of the 34 cards must not move (README: "pre-registered and changed nowhere else").

Layout that satisfies all three: new harness modules beside `validate.py` (proposed names: `core/quant/gate_stats.py` for R-24, `core/quant/gate_ledger.py` for R-23, `core/quant/cardp.py` for R-21/R-22/R-34), importing the reusable primitives from `validate.py` / `strategies.py`, with `core/quant/backtest.py` gaining only re-export lines so the spec's dotted names (`core.quant.backtest.cardp_evaluate`, `.step3`, `.timing_profile`, `.power_line`, …) resolve. `validate.py` and `strategies.py` then belong in the definitions manifest too, because the harness imports them.

### D2. Spec function → what exists → what to do

| v2 function (SPEC line) | Existing code to reuse | Gap |
|---|---|---|
| step 1 walk-forward (4760) | `V.walk_forward` unchanged when anything is searched | G = 1: do not route through `walk_forward` + `_decide_strategy` (drops 756 sessions, cannot PASS) |
| `lw_studentized_boot(x_a, x_b, block, B, seed)` (2552) | index construction of V:116-119 / V:140-143 (circular blocks, `default_rng(seed)`); `V.sharpe`; `V.lo_se` | Legacy paired test is a percentile bootstrap, not studentised; legacy SE is iid. New function needed |
| `pw_block_psi(x_a, x_b)` (2553), Politis–White block | nothing (no Politis–White, no stationary bootstrap anywhere in `core/`, `ui/`, `docs/`, `tests/`) | New. Block rule for macro cards: `max(21, PW on the ΔSR influence function)` (4761); `pc3_also_block_10: true` (2598) |
| `se_ladder(x_a, x_b, blocks=(10, 21, 63, 126, 250))`, `power_line(se, deltas=(0.05, 0.10))` (2554-2555) | `V.min_track_record` (level-based track length), `V.newey_west_t` (HAC) | New |
| `lo_adjusted_sr(x, lags)` (2557) | `V.lo_se` is the iid case only | New |
| `emax_iid(N)`, `emax_sim(C, draws=200_000, seed=11)`, `deflated_dsr(...)` (2432-2434) | `V.expected_max_sharpe(n, sd)` (= sd × iid E[max]), `V.deflated_sharpe` (DSR vs 0, printed on CARD-P) | N_eff, V_null, deflated ΔSR are new |
| `family_ledger`, `ledger.append/hash`, `n_eff`, `step3` (1092-1093, 2430-2435) | Only `ModelCard.trials = {"N_planned", "N_total", "ledger": [free text]}` and the `n_trials=` argument (hand-typed 11 on S_C3) | Entirely new; hash-chained rows appended by the harness itself |
| `pbo_cscv(configs, objective, S=16)`, `pbo_null` (2556) | `V.pbo_cscv(pnl, *, S=8)` — Sharpe objective, run at 8 or 16 | **Name collision, different signature.** New objective-pluggable function under another name or in the new module's namespace; legacy one stays |
| `cardp_evaluate(header, books) -> CardPResult`, `es_h`, `pc1_prime`, `tail_exposure_ratio`, `pc3_noninferiority`, `placebo_panel`, `gjr_null_percentile` (2125-2129) | Books: `S.simulate`; drawdown: the `cumprod / maximum.accumulate` idiom (V:446-447, S:105); years: `V.year_stats` (PC-5); verdict strings: `V.DECISIONS` | No ES of h-session returns, no CDaR, no tail-exposure ratio, no non-inferiority test, no placebo/shift generator exists. `core/quant/risk.py` has only a 1-day historical VaR/CVaR inside `analyze_history` |
| Comparator **S** = overlay-off book × mean multiplier, constant weight, same days, no cost (5187) | `S.simulate(prices, W_const, cost_bps=0.0, cash_daily=...)` builds it directly | No helper exists; the legacy vol-target cards are judged against buy-and-hold at exposure 1.0, never against S |
| `S_beta` = β̂ × market + (1 − β̂) × cash (R3:1300, XS-12) | `S.simulate` with a two-asset constant weight | β̂ estimation window is an open owner question (OQ-03) |
| PC-6 plateau (5205): 8 Moore neighbours on a two-axis grid | `V.plateau_share` moves one parameter at a time (≤ 2 neighbours per axis; 4, not 8, on two axes) and scores Sharpe | Not reusable for PC-6; reusable unchanged for CARD-O step 7 |
| `timing_profile(card)` (1094, 3404) | Causality test pattern in `test_strategies_are_causal`; `S.simulate` hold convention | New; lag re-timing must stay inside the function (probe sandbox) |
| `episodes`, `excess_returns`, `start_band`, `regime_lines` (R-22) | `V.regime_split` (vol / direction halves, different definition); cash via `simulate(cash_daily=)`; `ST.rf_daily` (DGS3MO, 0.03 fallback) | New. Legacy Sharpe is on raw returns; v2 wants excess returns with local cash |
| R-30 forecast harness: `dm_test`, `kupiec`, `christoffersen_cc`, `fan_pit`, ES Z2, MCS (TASK-M3-02, M9-02) | `V.dm_test`, `V.kupiec`, `V.christoffersen`, `V.pit_tests`, `V.coverage_check`, `V.traffic_light`, `V.crps`, `V.score_distribution`; `core.crypto.analytics.garch_scorecard` → `GarchScorecard(dates, hits95, hits99, inband90, pit, qlike_garch, qlike_ewma, nonconv, at_stationarity, nu_path, gamma_path, lambda_path, model, n_refits, note)` | Reuse, do not re-implement. `cw_test`, `gw_test`, `mcs`, `es_z2`, `reliability_table` are new |
| `cost_per_s` / tick floor / `tax_side` (TASK-M0-12, R-26) | `S.simulate(cost_bps=)` + `ST.COST` | Flat bp only; per-instrument tables and tick floors are new |
| Model card v2 (`model_card_header.macro`, `model_card.macro`; SPEC:3927-4012) | `V.ModelCard`, `V.load_cards`, `V.md5_of`, `V._json_default`; study pattern `strategy_card` / `error_card` / `_rows` / `write_results` | Field names differ: v2 `verdict`, `verdict_reason`, `caps_applied`, `first_failed_check`, `permitted_fix`, `results_md5` over result fields vs legacy `decision`, `decision_reason`, `revise_target`, `results_md5` of a CSV. Two schemas, closed objects |
| `docs/macro_overlay_study.py` (SPEC:800, 845) | Structure of `docs/asset_expansion_study.py`: `CANDIDATES` dict of lambdas, never-stop loop, `--only` merge, cached loaders | New file; reads fixtures / the PIT store, not the Yahoo cache |
| Break-even pre-gate screen GOV-7 (R3:1176: break-even cost per side = gross per year / turnover per year, both legs) | `StrategyScore.turnover_annual`; gross P&L = `simulate(cost_bps=0.0)` | New one-liner on top of existing outputs |
| Attribution block GOV-3 (R3:282: beta, Jensen's alpha vs a beta-matched benchmark with Newey–West t) | `V.newey_west_t` | New |
| Family gate GOV-2 (R3:289: studentised SPA / Reality Check, BH-FDR reported) | bootstrap index idiom | New |

### D3. Naming collisions and vocabulary

- `pbo_cscv` (legacy `(pnl, *, S=8)` vs spec `(configs, objective, S=16)`), `dm_test`, `kupiec`, `christoffersen` vs `christoffersen_cc`, `pit_tests` vs `fan_pit`.
- Two `FAMILIES` dicts: `strategies.FAMILIES` (name → function) and `ui/strategy_lab_page.FAMILIES` (name → `(label, fn, grid, embargo)`); the spec's `family_id` / "family ledger" is a third meaning.
- "ledger": legacy `trials.ledger` is a list of prose strings.
- "DSR": legacy `dsr` = deflated Sharpe ratio; the spec reserves `delta_sr` / `boot_delta_sr` for Sharpe differences (SPEC:2437). Legacy `bench_diff` is the Sharpe difference.
- Verdict strings: `V.DECISIONS` uses `INSUFFICIENT_DATA`, matching the v2 schema enum (SPEC:4007); spec prose writes "INSUFFICIENT DATA". `NOT_RUN` (SPEC:3759) is a card state outside `DECISIONS`.
- `live_sharpe_multiplier: 0.60` (SPEC:4768) does not exist in the repo; the code key is `GATE["haircut"]`, the card field `decay_haircut.factor`.
- Card kinds: legacy `kind ∈ {"strategy", "distribution", "model", "error"}`; v2 `class ∈ {CARD-O, CARD-P, …}`. File-name prefixes `S_`, `D_`, `M_` are a convention of `CANDIDATES` ids only (`S_B2_pca_fly` is `kind="strategy"` without a walk-forward).

### D4. Constraints

- **Do not put v2 cards in `docs/asset_expansion/cards/`.** Every reader globs the whole directory and `ui/strategy_lab_page.py:101-133` indexes `c["card_id"]`, `c["decision"]`, `c["kind"]`, `c["hypothesis"]`, `c["decision_reason"]` without `.get`; `write_results` would also re-stamp and rewrite foreign files; the primer counts every card. Macro cards need their own directory and a deliberate adapter into the Strategy Lab table.
- **Do not read frozen thresholds from `V.GATE`** (mutated at run time, A1.1 note and E1). Pass `B`, block and level explicitly; keep the v2 values in the rules-store `gate.*` blocks.
- `WalkForward`, `Panel`, `PairsDiagnostics`, `BacktestResult`, `History` are frozen dataclasses; `StrategyScore`, `DistributionScore`, `ModelCard` are mutable and are mutated after construction (run_pairs, run_garch).
- Seeds: 11 everywhere (matches SPEC `seed: int = 11` at 1093).
- Strict JSON: 5 existing cards contain bare `NaN` (S_V4_dollar_carry, three pairs cards, M_O1_board_today). A JSON-Schema-validated v2 card must map non-finite numbers to `null` before writing.
- Byte reproducibility: `stats.seconds` and `created` change between runs; `results_md5` on a legacy card is the md5 of the whole merged CSV at the last write, not of that card's results.
- Run time: the suite is single-process and sequential; `selfcheck_validate` alone is 46 s. Bootstrap-heavy v2 tests need small `B` on fixtures.
- Any change to `ui/*.py` is linted by `tests/flet_api_guard.py` against Flet 0.85.2 (`Dropdown.on_select`, `page.show_dialog` / `pop_dialog`, `page.run_thread`); Strategy Lab uses `ft.DataTable`, `ft.Dropdown(on_select via attribute)`, `ft.Button`.
- Read-only invariant: nothing in these four files has an order path; `simulate` is arithmetic on arrays.

---

## E. Gotchas

1. **Global `GATE` mutation leaks across the process.** After `expansion/gate_noise_vs_edge` runs, `core.quant.validate.GATE["bootstrap_B"]` stays 300 for the rest of `run_all.py`; after one Strategy Lab run it stays 1000 for the app session; after a `--quick` study the cards record `protocol.bootstrap_B: 300`. `walk_forward` defaults, by contrast, never follow `GATE`.
2. **G = 1 cannot PASS and is mislabelled** (fact 2 above; S_V4_dollar_carry prints "…loses out of sample, nan: fails (needs ≤ 0.1)").
3. **A benchmark of the wrong length is dropped without a word** (V:450-455): step 5 and the regime split vanish and the card can PASS without a benchmark test.
4. `revise_target` on a REJECT is set from `bench_fail` even when the stated reason is the deflated Sharpe (S_V4_dollar_carry: reason "deflated Sharpe below 0.95", target "…the benchmark is as good").
5. NaN handling in `_decide_strategy`: `dsr = NaN` skips the REJECT branch and lands in REVISE; `oos_is = NaN` fails "over-search"; a NaN column in the P&L matrix gets in-sample Sharpe 0.0 from `_col_sharpe` rather than an error. No input validation in `walk_forward` beyond lengths.
6. `score_distribution` raises `KeyError: 'shape'` with fewer than 20 finite PIT values (lines are built before the `n < 500` check).
7. The plateau test reads the **last in-sample window's** Sharpes only; the PBO `S` switches from 8 to 16 at 2,000 rows; DSR trial dispersion comes from the current grid even when `n_trials` counts earlier grids.
8. `n_trades` counts sessions with any turnover. `run_fx` feeds a 0/1 rebalance flag as turnover, so its "turnover 12.0× equity per year" line is a count of rebalances, not turnover.
9. Paired-bootstrap `p` can print as "p 0.00"; v2 requires "< 1⁄B" (SPEC:4761).
10. Yearly statistics sum arithmetic daily P&L per calendar year; drawdown and total return compound. Sharpe is on raw (not excess) returns.
11. `ui/strategy_lab_page.py:42` still runs the crypto-trend grid `[0.05, 0.1, 0.2, 0.3, 0.4, 0.5]` that the study retired as "three rules in six costumes" (ST:328-333, AES:115-119); the live run also uses a constant 3 % cash rate, `n_trials = len(grid)`, no `domain`, default cost 10 bp. A live verdict can differ from the card for the same family.
12. Kept cards are never regenerated or validated: `D_Q_gjr_spy.json` lacks `stats.median_lambda`, which the current runner writes (ST:525).
13. `manifest.json` has no data spans although the study docstring promises them (ST:10); `DATA_SPANS` is dead.
14. README is stale against run 4: it says the crypto trend rule on BTC-USD "sits on a grid edge (REVISE)" and KRW-BTC "beats buy-and-hold at p 0.02" (README:225-227); the manifest and both cards say PASS / PASS with `bench_p` 0.038 and 0.07, `edge` False.
15. Windows / cp949: the study and `run_all.py` reconfigure stdout to UTF-8 themselves; any new script that prints `×`, `≥`, `σ`, `Δ` or Hangul must do the same, and every file write must pass `encoding="utf-8"` (all existing writers do). The repository is not a git checkout here, so `git_hash` fields required by the v2 card schema (SPEC:3998) have no source.
16. `prep/readlines.py` in the run scratchpad has a syntax error (a literal newline inside a string); long spec lines were printed with an inline equivalent.
17. Importing `docs/asset_expansion_study.py` has side effects (creates `docs/asset_expansion/{cache,cards}`, inserts `ROOT` in `sys.path`, loads `.env` via `config`).
18. `S.vol_target` is not the spec's R-06 estimator: 22-session window (spec: SMA20), 21-session rebalance steps, a 10 % relative no-trade band, zero weight before the first rebalance; `ewma_vol` annualises with 261, `realised_vol` with 252.

---

## Ambiguities (source silent or contradictory; conservative reading stated)

| # | Issue | Lines | Conservative reading |
|---|---|---|---|
| 1 | Spec homes the v2 harness in `core/quant/backtest`, which is the toy backtester; the gate is `validate.py` | SPEC:1089-1098, 2124, 2429, 2551, 3404 vs B:1-155, V:1-33 | Additive modules; legacy gate and its 34 verdicts untouched; `core/quant/backtest.py` re-exports the spec names; no behaviour change to `run_backtest` |
| 2 | "With no searched parameter the walk-forward reduces to the full sample" vs code that drops the first 756 sessions and cannot PASS at G = 1 | SPEC:4760 vs V:308-320, 479, 510 | v2 evaluators judge single-configuration cards on the declared span in their own code path; a missing PBO is recorded as not run (R-24: "Run only with ≥ 10 configurations", SPEC:4763), never as a pass by default and never through `_decide_strategy` |
| 3 | Bootstrap block: legacy 10 sessions; macro spec `max(21, PW on the ΔSR influence function)`; tech-fund amendment XS-11 `max(10, Politis–White on d and d²)` "for steps 2 and 5 on every card" | V:54; SPEC:4761, 2598; R3:296, 1299 | Macro cards: the longer block of the two rules. Legacy 34 cards: not re-scored silently (a block change can flip verdicts and is a package change); print the PW-block interval beside the legacy one until the owner rules |
| 4 | Legacy checks absent from the spec's nine-step table: OOS/IS ≥ 0.5, trades ≥ 100, the 30-trade / 5-year floor, the minimum-track-record route | V:513-523, 538-544 vs SPEC:4758-4768 | Keep them for CARD-O (they can only lower a verdict); CARD-P follows §8.7's own order (SPEC:5228-5250), where sufficiency is PC-7 |
| 5 | Step 5 for protective rules: legacy compares against buy-and-hold / EW and REJECTs (S_E2 cards) | ST:286, V:524-531 vs SPEC:5187, R3:324 | The recorded REJECTs stand as outperformance claims; a protective claim is a new CARD-P card against S (or S_beta), never a re-read of the old card |
| 6 | Step 9 key name `live_sharpe_multiplier: 0.60` vs `GATE["haircut"]`; tech-fund XS-13 notes harness prints that used 0.4× | SPEC:4768, R3:1301 vs V:57, 463 | One constant, 0.6 × OOS; reuse `GATE["haircut"]` semantics; reported, never gated |
| 7 | `GATE["cost_stress"]` and `pnl_matrix(stress=2.0)` are separate constants | V:57, S:380 | Treat 2.0 as the frozen value; a v2 harness passes the multiplier explicitly |
| 8 | Card field vocabulary: `decision` / `decision_reason` / `revise_target` vs `verdict` / `verdict_reason` / `permitted_fix` | V:748-750 vs SPEC:3999-4008 | Two card types, two directories; no in-place migration of legacy cards |
| 9 | Cost semantics: 35 bp "incl. tax" charged on both sides; VIX card label vs literal; dollar-carry card reports 10 but ran at 5 | ST:19, 60, 386-387, 408-409, 439 | Legacy numbers stay as recorded; v2 costs come only from the R-26 instrument table, never from `ST.COST` |
| 10 | Local data: the cache has no KOSPI index history and no point-in-time fields | cache listing; SPEC:2133-2135 | Formal v2 cards cannot be computed from this cache; any run on it is labelled research / NOT_RUN, specification book only |
| 11 | `definitions_md5` covers "the source files of every harness function"; unclear whether imported legacy primitives count | SPEC:4820 | Include `validate.py` and `strategies.py` in the manifest once the harness imports them (fail closed on any edit) |
