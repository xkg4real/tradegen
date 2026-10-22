# spec_M4_sleeves — implementation brief (QUANTGEN v2.0, milestone M4 "Factor sleeves")

Sources read in full: `QUANTGEN_MACRO_INTEGRATION.md` (SPEC) lines 1165-1172 (§3.7), 1510-1553 (R-03, R-04, R-05), 1707-1741 (R-15); supporting: 14-100 (Quick start), 487-657 (P0-P19), 679-704 (§2.1-2.2), 850-898 (§3.3), 961-1113 (§3.5), 1135-1149, 1173-1187 (§3.8), 1866-1936 (R-19 rules 4-5), 3514-3586 (§6.1), 3708-3798 (§6.2), 4094-4119 (§6.6), 4123-4362 (§7), 4687-4705 (§7.1), 4781-4838 (§8.1.2-8.1.3), 5441-5487 (§8.10), 5489-5706 (§9.0-9.2), 5708-5764 (§9.3.1), 5946-5956, 5982-6035 (§9.3.3-9.5), 6039-6260 (§10), 6296-6301 (§11), 6366 (§12 M4). Tasks: `prep/tasks/M4.json` (TASK-M4-01..07). Backlog BL-G07 (`QUANTGEN_MACRO_BACKLOG.md` 1449-1455). Tech-fund `R3_TF_neural_link.md` §13 (1283-1310), §11.7 (1007-1032), §2 (24-72), §3 W-rules (96). Code: `core/quant/signals.py`, `core/quant/optimize.py`, `core/quant/strategies.py`, `core/quant/risk.py`, `core/quant/validate.py`, `core/rules/*`, `docs/asset_expansion/cards/*.json`.

"SPEC n" = line n of `QUANTGEN_MACRO_INTEGRATION.md`. "proposed" = not fixed by the spec (SPEC 963: locations/names may be renamed; SPEC 89: field names, parameters, bounds, formulas, thresholds are binding).

---

## A. Scope

| Task | Deliverable (one line) | Target files |
|---|---|---|
| TASK-M4-01 (spike) | Read the six composite components from code, propose a family tag each (`momentum`, `reversal`, `flow`, `quality`, `ts_trend` or none), record as a rules-store revision pending owner/council confirmation; collect flow/quality prior registrations | `core/quant/signals.py` (read); macro rules store (M0) entry `family_tags` (proposed key) |
| TASK-M4-02 | Family tag on every component; overlays attach only through tags; `active_budget(m,f) = base_weight × vs × min(1.0, family overlays)` with `exposure_basis=active`; vt never on L/S sleeves or ts_trend; overlays cannot create a component or flip a sign | `core/quant/signals.py` (modify: `SignalComponent.family`, wiring into M2's `apply_overlays`); `core/quant/risk.py` (market level, M2) |
| TASK-M4-03 | `sleeve_vol_scale()` revisions 1-3 on the paper unit-gross long/short series; `MOM_PAPER_LS_SERIES` derived PIT record; warm-up / MissingInput mapping; fills `overlay_decision.vol_scale` | `core/quant/risk.py` (modify); `core/ficc/data.py` registry entry (M1 store); `core/quant/strategies.py` (reuse `xs_momentum(long_only=False)`, `simulate`) |
| TASK-M4-04 | `dm_gate()` -> {0.5, 1.0}, specification book only, label "step 3 FAIL"; inputs `DM_MKT_RET_24M`, `DM_MKT_VOL_126` | `core/quant/signals.py` (modify) |
| TASK-M4-05 | Reversal, quality (and flow) carry no overlay multiplier (fixed 1.0); `families.reversal.calm_state_downweight: not_adopted` with D3 marker; refusal of a calm-state down-weight | `core/quant/signals.py`; macro rules store + `core/rules/validation` (M0 engine) |
| TASK-M4-06 | `inverse_vol_weights()` (EWMA λ 0.97 weekly, LW-156w printed); `base_weights()` = IV_m × 1/K_m; admissibility; tilt refusal; REJECT re-weight K/(K−1) as a logged governance event | `core/quant/optimize.py` (modify); `core/quant/signals.py`; macro rules store (priors) |
| TASK-M4-07 | Specification-book and recommended-book builders for the factor sleeves; no renormalisation; specification-stack episode table | `core/quant/signals.py` (`composite_weights`, builders; proposed); `core/quant/risk.py` (`risk_layer`, M2/M5) |
| tests | T-PRIOR-01, T-R03-01 (sleeve-scale + years clauses), T-BASIS-01 (L/S runtime clause), T-COST-01 (both-legs clause), G-MOM-01..06, G-MOM-08, G-INTL-01, G-BOOK-01, G-YRS-01, G-MOM-07 (reference mode) | `tests/macro_acceptance.py` (proposed, registered in `tests/run_all.py`); `tests/reference/` (G-MOM-07); `tests/fixtures/macro/` + `MANIFEST.csv` |

Optional split (proposed, not required): if `signals.py` grows past comfort, move the new sleeve functions to one new file `core/quant/sleeves.py`; spec names stay importable from `core.quant.signals`.

---

## B. Build spec, module by module

### B0. What the repository actually contains (binds every decision below)

| Fact | Where |
|---|---|
| The "6-component composite" is a single-symbol technical score in [-100, +100], weighted mean -> stance word. It has no instrument weights, no market × family sleeves. | `core/quant/signals.py` 89-172 |
| Components (key, weight): `trend50` 0.20 (price vs 50-day SMA), `trend200` 0.20 (price vs 200-day SMA), `momentum` 0.20 (63-session rate of change), `rsi` 0.15 (RSI 14, mean-reversion flavoured), `macd` 0.15 (12/26/9), `vol` 0.10 (σ20/σ100) | `signals.py` 101-154 |
| The only cross-sectional momentum implementation: `xs_momentum(prices, *, lookback=252, skip=21, top=1/3, step=21, long_only=True)`; `long_only=False` gives long leg Σ = +1, short leg Σ = −1 | `core/quant/strategies.py` 212-229 |
| Costed simulator: `simulate(prices, weights, *, cost_bps, cash_daily) -> (pnl, turnover)`; turnover = Σ_i abs(Δw_i) charged on the session the weight changes; `summary(pnl)` gives sharpe / max_drawdown | `strategies.py` 69-105 |
| Existing model cards for family-like sleeves: `S_E5_xsmom_sectors` (nine sector SPDRs, long top third, 50 bp) decision **REJECT**; `S_E1_trend_us` REJECT; `S_E1_trend_krx` REJECT; `S_B3_tsmom_futures` REJECT; `S_C3_crypto_trend_btcusd` / `_krwbtc` PASS. No reversal, quality or flow sleeve card exists. | `docs/asset_expansion/cards/*.json` |
| `core/rules` is the operator trading-rule store (`Rule`, `PriceCondition`, `Side`...), not a config store. The macro rule objects of SPEC §7 need M0's store. | `core/rules/model.py` 118; `store.py` 130 |
| Not present yet (earlier milestones): `pit_value`, `PITValue`, `MissingInput`, `RunContext`, `compose`, `apply_overlays`, `market_vol_target`, reference / v1.2-check mode, governance appender | SPEC 966-1102 |
| Reusable statistics: `validate.sharpe` (80), `validate.sharpe_diff_bootstrap(a, b, *, block, B, level, seed)` (129; paired circular block bootstrap, one-sided p that diff ≤ 0), `validate.year_stats` (364), `strategies.summary` (97) | `core/quant/validate.py`, `strategies.py` |
| `sklearn` is not installed; numpy 2.3.5, scipy 1.18.0, pandas 2.3.3 are | environment check |

### B1. Family tags (TASK-M4-01, TASK-M4-02; SPEC 1165-1171)

Binding rule (SPEC 1169): overlays attach to components through a **family tag**: `momentum`, `reversal`, `flow`, `quality` or `ts_trend`. A component with no family tag receives no family overlay (multiplier 1.0) and is still subject to `vt(m)` and the risk layer. A family receives a base weight in market m only if admissible there (prior ≥ 1 and card not REJECT). Overlays never create a new component and never change a component's sign (SPEC 1171, P1 SPEC 502-506).

Code change: `SignalComponent` gains `family: str | None = None` (frozen dataclass field, default None; existing callers unaffected). Tag source = the rules-store revision, never a literal in code beyond the default None.

Proposed mapping (for the owner or council to confirm, SPEC 1169, 5461; backlog BL-G07 OPEN · P2):

| Component key | What it computes | Proposed tag | Effective tag until confirmed |
|---|---|---|---|
| `trend50` | price / SMA50 − 1 | `ts_trend` | none |
| `trend200` | price / SMA200 − 1 | `ts_trend` | none |
| `momentum` | 63-session rate of change of one symbol (time-series, not cross-sectional) | `ts_trend` (not `momentum`: R-03 sizes cross-sectional sleeves on a paper long/short series, SPEC 1515-1517) | none |
| `rsi` | RSI(14), contrarian above 70 / below 30 | `reversal` | none |
| `macd` | MACD histogram | `ts_trend` | none |
| `vol` | σ20/σ100 | none | none |

Conservative effective state: every component untagged (multiplier 1.0, still under vt and the risk layer). Reason: a `ts_trend` tag exempts a component from every overlay and from vt (SPEC 1701, 894), which removes a risk control, so it must not be applied on a proposal. No existing component maps to `momentum`, `flow` or `quality`.

Runtime assertions in the tag layer:
- tag ∈ {`momentum`, `reversal`, `flow`, `quality`, `ts_trend`, None}; anything else raises.
- a multiplier whose `applies_to` family differs from the component's tag is never applied to it.
- any multiplier on `ts_trend` raises; a `total`-basis multiplier (vt) on anything but `market_gross` raises (SPEC 4696; runtime check from M4 for L/S sleeves, M7 for R-14, SPEC 5569).

### B2. `core/quant/risk.py`: `sleeve_vol_scale` (TASK-M4-03; R-03, SPEC 1510-1526)

Spec signature (SPEC 1048-1050):
```python
def sleeve_vol_scale(market: str, family: str, decision_utc: datetime, revision: int) -> VSResult
#   sigma126 on the paper unit-gross long/short series; revision selects fixed / scale-free / variance-scaled (R-03);
#   fewer than 126 valid observations -> "insufficient_history", mapped per book as above (vs = 1.0 "warmup", then MissingInput)
```
Plus the pinned `knowledge_utc` as a parameter or inside `RunContext{decision_utc, knowledge_utc, run_mode}` (SPEC 1105). Data is read only through `pit_value(series_id, decision_utc, knowledge_utc, consumer='R-03')`; no raw DataFrame read (SPEC 1106).

Pure kernel (proposed name; the hermetic test target):
```python
def vol_scale_from_returns(r_ls, *, revision=1, window=126, target_ann=0.12, cap=1.0,
                           min_obs=126, median_min_obs=252, ann_days=252) -> tuple[float | None, float | None, str]
# returns (vs, sigma126_ann, status); status in {"ok", "insufficient_history", "degenerate_sigma"}
```
Algorithm:
1. `valid` = finite returns of the paper series through the close of t, excluded (flagged) days dropped; "the window extending past excluded days to the last 126 valid returns (as R-06's does)" (SPEC 1518).
2. `len(valid) < 126` -> status `insufficient_history` (SPEC 1050).
3. `σ126(t) = stdev(r_LS[t−125 … t]) × √252`, mean-adjusted sample SD, ddof = 1, returns through the close of t (SPEC 1518).
4. Revision 1 (registered; the one that acts in the specification book): `vs = min(1.0, 0.12 / σ126(t))` (SPEC 1518).
5. Revision 2, scale-free target: target = the expanding median of σ126 on the same paper long/short series (minimum 252 observations), cap 1.0: `vs = min(1.0, median(σ126[start … t]) / σ126(t))` (SPEC 1519).
6. Revision 3, variance-scaled: `vs = min(1, (0.12/σ126)²)` on the same series (SPEC 1519).
7. Parameters: window 126 days; target 0.12 annualised; cap 1.0; no floor (SPEC 1520). `assert 0.0 <= vs <= 1.0` (SPEC 1506 (1)). `cap > 1.0` raises in `core/` (reference variants live in `tests/reference/` only, SPEC 5992).
8. Timing: the weight decided at the close of t earns from t+1 (SPEC 1518, 1483).
9. Revision rule: "If more than one registered revision PASSes, the lowest PASSing revision number acts; this rule is declared before the runs" (SPEC 1519). No card has run, so revision 1 feeds the specification book; revisions 2 and 3 are callable trials only.

Never: "**vs is never computed on the benchmark-relative active series**" (SPEC 1517). Input is always the paper unit-gross long/short series, also for a long-only sleeve (SPEC 893).

`VSResult` (name from SPEC 1048; fields proposed): `{rule_id: "R-03", market, family, revision, sigma126_ann, target_ann, value, status, exposure_basis: "active", inputs: list[PITValue]}` with `value ∈ [0, 1]`.

Status and fail-closed mapping (SPEC 1047-1050, 1108, 1111, 1880):

| Condition | Result |
|---|---|
| < 126 valid observations, book never ARMED | `value = 1.0`, status `warmup`; not a failure; no counter increment |
| < 126 valid observations, book has been ARMED | `MissingInput("missing")` (role `acting_exposure`, the bound books); a failure |
| Any input `MissingInput` (`missing` / `stale` / `provisional_intraday` / `session_mismatch` / `synthetic_rejected`) | previous vs carried, component `fail_closed = true`, input status code, alert; never interpolated (SPEC 1108) |
| σ126 = 0 or not finite with ≥ 126 observations | fail closed as `MissingInput` (R-06's rule, SPEC 1047, 1562; R-03 is silent, see F-06) |
| 2 consecutive failed decisions | OPS HALT of the bound books only, i.e. `specification:<market>` (SPEC 4231, 1870-1871; T-SCOPE-01 (a) at M8) |

Reuse M2's per-book warm-up mapper built for `market_vol_target` (TASK-M2-01); do not write a second one.

Outputs (the M6 builder writes them; until M6 tests assert function outputs, SPEC 6368):
- `overlay_decision.vol_scale` (specification book), `exposure_basis=active` (SPEC 1521, 3732).
- `overlay_decision.vol_scale_recommended_book` "= vol_scale if its card is PASS, else 1.0" (SPEC 3733) -> 1.0 today.
- `overlay_decision.vol_scale_card` = `{"card_id":"MACRO-R03-US-MOM","class":"CARD-O","verdict":"NOT_RUN","disposition":"DESCRIPTIVE","displayed_as":"descriptive","label":"indicative PASS; step 3 borderline","results_md5":null}` (SPEC 3779-3780).
- reason string form: `"VS: sigma126 23.9% -> min(1, 0.12/0.239)=0.50"` (SPEC 3787).
- input record: `series_id: "MOM_PAPER_LS_SERIES"`, `obs_kind: "derived"`, `role: "acting_exposure"`, `books: ["specification:US"]` (SPEC 3788-3791).

Day-one sanity value (SPEC 6300): US Mom σ126 23.9% (2026-08-31) -> vs = 0.50.

### B3. Paper unit-gross long/short series `MOM_PAPER_LS_SERIES` (TASK-M4-03)

- Definition: "the daily returns of the sleeve's **paper unit-gross long/short series**: long leg +1 and short leg −1 notional, same ranking as the sleeve" (SPEC 1517).
- Build (proposed, reuse): `W = strategies.xs_momentum(prices, lookback=…, skip=…, top=…, step=…, long_only=False)` with the sleeve's own ranking parameters; `r_LS = strategies.simulate(prices, W, cost_bps=0.0)[0]`. Gross of the sleeve's constituent turnover (as the French goldens are, SPEC 1523).
- Storage: a derived PIT record (TASK-M1-13): `obs_kind = "derived"`, `available_at` = the latest input `available_at`, `value_status` = the weakest input status, `content_hash` over the inputs, recomputed on any input change, never served from cache; a derived acting value with any non-official close-type input returns `MissingInput("provisional_intraday")`.
- Binding (SPEC 4256, 1889): `MOM_PAPER_LS_SERIES: {role: acting_exposure, books: [specification]}`; "+ the recommended book while verdict_filter admits R-03 (R-19 rule 5)". Bindings follow admission: the runtime derives the book list each decision and logs every change as a governance event (`kind: binding_change`); a book that reads a factor whose acting inputs are not bound to it is refused at load.
- Consumer key for reads: `'R-03'` (SPEC 1105).

### B4. `core/quant/signals.py`: `dm_gate` (TASK-M4-04; R-04, SPEC 1528-1542)

Spec signature (SPEC 1062): `def dm_gate(market: str, decision_utc: datetime) -> Multiplier   # value in {0.5, 1.0}; specification book only (R-04)`.

Inputs (SPEC 1535): the sleeve market's index: 24-month total return as of the last month-end on or before t, and 126-day daily realised volatility through the close of t. Series ids `DM_MKT_RET_24M`, `DM_MKT_VOL_126`, each `{role: acting_exposure, books: [specification]}` (SPEC 4257-4258); consumer `'R-04'`.

Formula (SPEC 1536, verbatim):
```
bear24 = (Π_{24 months}(1 + r_month) − 1) < 0
hivol  = σ126_mkt(t) > Q_{2/3}(σ126_mkt over [start … t])      # an expanding quantile with at least 252 observations
dm     = 0.5 if (bear24 and hivol) else 1.0                      # decided at the close of t, earning from t+1
```
Parameters (SPEC 1537): 24 months; 126 days; quantile 2/3; multiplier 0.5; `exposure_basis=active`. "A 200-day moving average is **not** a substitute." Both comparisons are strict (`+39.7% >= 0 -> 1.0`, SPEC 3787).

Pure kernel (proposed): `dm_from_inputs(r24: float | None, sigma126_mkt: float | None, q23: float | None) -> tuple[float, bool, bool]` returning `(dm, bear24, hivol)`; None inputs -> insufficient history.

`Multiplier` (name from SPEC 1062; fields proposed, matching the `multipliers[]` item of SPEC 3735-3737): `{rule_id: "R-04-DM", value ∈ {0.5, 1.0}, exposure_basis: "active", status, reasons, inputs, card}` with `card = {"card_id":"MACRO-R04-US-DM","class":"CARD-O","verdict":"NOT_RUN","disposition":"SPECIFICATION_ONLY","displayed_as":"descriptive","label":"step 3 FAIL (indicative)","results_md5":null}` (SPEC 3781-3783).

Behaviour:
- Applied **only in the specification book** as the momentum family's overlay multiplier (SPEC 1538, 868). The recommended-book builder refuses it (SPEC 1542, 3770; assertion test I-03 runs at M8).
- Writes `macro_state.flags.dm_bear_state: boolean` "specification book only (R-04)" (SPEC 3570).
- Insufficient history (fewer than 24 complete months, fewer than 126 valid returns, or fewer than 252 quantile observations): `value 1.0`, status `warmup` before the book's first ARMED decision; `MissingInput("missing")` afterwards (SPEC 1111). Failed inputs: previous state carried, `fail_closed = true`, alert; HALT scope `specification:<market>` only (SPEC 1871).
- Routes closed: `a_provisional_route: closed`, `pooled_revision: none` (SPEC 4322); card validation rejecting an A-provisional or pooled route is T-R04-01 at M7.
- Reason string form: `"DM: 24m market return +39.7% >= 0 -> 1.0 (specification book only)"` (SPEC 3787).

Day-one sanity values (SPEC 6301): US 24-month market return +39.7% (end-Aug-2026) -> bear state OFF; Mkt vol126 14.3% vs its 2/3 quantile 17.4%.

### B5. R-05: reversal and quality fixed at 1.0× (TASK-M4-05; SPEC 1544-1552)

- "The reversal and quality families have **no overlay multiplier** (the value is fixed at 1.0) in every state. They are never up-weighted in stress, and never cut by macro or stress flags." (SPEC 1550). Config also fixes `flow` (SPEC 4323-4325).
- Implementation: the family overlay list for `reversal`, `quality`, `flow` is always empty (`min(1.0, …)` of an empty list = 1.0, SPEC 868) and `vs = 1.0` ("momentum only, else 1.0", SPEC 867). The builder asserts both.
- "Reversal simulated daily entries are decided at the official close of t and earn from t+1. There is no intraday reversal leg." (SPEC 1550); `intraday_leg: false`.
- D3: `families.reversal.calm_state_downweight: not_adopted` is the canonical key of owner decision D3 (SPEC 71, 4144, 4323). Rules-store validation refuses any rule object that multiplies `reversal` conditional on a stress level while the key is `not_adopted` (SPEC 6260; P3 SPEC 520-527). A rule block needing the value holds `{ref: families.reversal.calm_state_downweight}`, never a literal copy (SPEC 4130, T-OWNER-01).
- Reopen condition (owner only, SPEC 1740): a KRX stock-reversal test net of 35 bp plus the 0.20% tax showing 0.5× in calm beating 1.0× at one-sided p ≤ 0.10 in both 2010–17 and 2018–26.
- Net-of-cost requirement on the reversal family's own card (outside this spec): clear 35 bp per side and stay positive at 70 bp (SPEC 1552).

### B6. Base weights (TASK-M4-06; R-15, SPEC 1707-1740; §3.3 SPEC 857-863)

`core/quant/optimize.py` (SPEC 1066): `def inverse_vol_weights(markets: list[str], decision_utc: datetime, cov: str = "ewma_weekly_0.97") -> dict[str, float]`.
- IV_m = inverse-vol weight of market m on weekly returns; EWMA λ 0.97 acting; a Ledoit–Wolf 156-week line printed beside it; Σ_m IV_m = 1 (SPEC 858-859, 1716).
- "No HRP or minimum-variance; ERC only for multi-asset sleeves." (SPEC 1716). Do not route through `optimize_portfolio` objectives `min_vol` / `risk_parity`.
- "IV_m spans the markets whose sleeves exist in the composite; D5 = none removes no existing factor sleeve, only the US market-gross line." (SPEC 1716).
- Pure kernel (proposed): `inverse_vol_from_weekly(weekly_returns: dict[str, np.ndarray], lam=0.97) -> dict[str, float]` with `var_t = lam·var_{t−1} + (1−lam)·r_t²`, `IV_m = (1/σ_m) / Σ_k (1/σ_k)`; one market -> `{m: 1.0}`; no market -> `{}`. Assert `abs(Σ IV − 1) < 1e-12` when non-empty.
- LW line: numpy Ledoit–Wolf shrinkage on the last 156 weekly returns, inverse-vol from its diagonal, printed only, never acting (`cov_printed: ledoit_wolf_156w`). sklearn is absent.

`core/quant/signals.py` (SPEC 1061): `def base_weights(decision_utc: datetime) -> dict[tuple[str, str], float]   # IV_m * 1/K_m over admissible families (R-15)`.
```
A_m              = { f : prior(m,f) ≥ 1  and  card(m,f).verdict ≠ REJECT }      # SPEC 860
base_weight(m,f) = IV_m × 1/|A_m|  if f ∈ A_m, else 0                          # Σ_f base_weight(m,f) = IV_m   (SPEC 861)
```
Admissibility rules (SPEC 1713-1720, 862-863, 4283-4285):

| Rule | Text |
|---|---|
| Admissible | prior ≥ 1 and its card is not REJECT; K_m = number of admissible families |
| Range prior | "a–b" not resolved per index resolves to its lower bound for admissibility and is printed as the range |
| No registered prior | not admissible until a prior is registered as a rules-store revision (owner or council, before M4) |
| Flow, quality | no column; flow takes §2.2's prior where one exists (Korea 3); quality has none registered |
| NOT_RUN | stays admissible, except `ts_trend`, which enters the recommended book only on its own PASS (R-14) |
| Integers | the 0–3 values are admissibility filters and display scores only |
| Sums | family weights 1/K_m sum to 1 in each market and Σ_m IV_m = 1, so no weight exceeds 1.0 (assertions) |
| Tilts | a bounded tilt only after the family's own card passes, as a registered revision; rules-store validation refuses a tilt without a PASSed family card |
| Verdict change | updates admissibility from the next decision. A family-card REJECT shrinks K_m and raises the other families' base weights by K/(K−1): "the one place a verdict raises a weight". Logged as a governance event (`kind: "admissibility_reweight"`, SPEC 4104-4105) and printed |

Prior table (SPEC 1722-1732, verbatim cells; "LB" = the lower bound used for admissibility):

| Market (enum) | XS momentum | ST reversal | TS trend | Flag |
|---|---|---|---|---|
| US (`US`) | 2 if vol-scaled with the D&M gate, else 1 (LB 1) | 1 (prior) | 3 | ONE-SIDED (N-35) |
| Europe (`EU`) | 3 | 1 (prior) | 0–1 (STOXX50 0, DAX 1, FTSE 0–1) (LB 0; DAX 1) | ONE-SIDED (N-35); TS trend CORE (N-33) |
| Japan (`JP`) | 0 (vol-scaled R4 SR 0.196: may rise to 1 if verified) | 2 (prior) | 1–2 (LB 1) | ONE-SIDED |
| Korea (`KR`) | 12-1: 0; 12-7 / residual: 1 | **1 (v2.0; was 3)**: UNVERIFIED until BL-U02 runs net of 35 bp plus the 0.20% sell tax | KOSPI 1, KOSDAQ 0 | **UNVERIFIED** (N-36) |
| Taiwan (`TW`) | 1 (prior) | 3 (prior) | 1–2 (LB 1) | TS trend CORE (N-33) |
| China A (`CN`) | 0 (prior) | 3 (prior) | 0 | TS trend CORE (N-33) |
| India (`IN`) | 3 (prior) | 1 (prior) | 1 | TS trend CORE (N-33) |
| EM broad (`EM`) | 3 | 1 (prior) | — (no registered prior) | ONE-SIDED (N-35) |
| Crypto (`CRYPTO`) | 1 (prior) | 2 (prior) | 2 (own trend plus vol cap; QUANTGEN's card C3 is the trend part) | N-54 (deferred) |

Flow: Korea 3 (SPEC 698, 1718); elsewhere none. Quality: none anywhere. `HK`, `FX`: no row.

REJECT re-weight procedure: on a verdict change to REJECT for (m, f), the next decision recomputes A_m; write one governance event `{kind: "admissibility_reweight", rule_id: "R-15", key: "base_weights.<m>", old: {...}, new: {...}, actor: "runtime", reason, refs}` through M0's appender; print old/new weights.

Fail-closed: a `MissingInput` on an IV_m input carries the previous base weights with `fail_closed = true` and an alert; with no previous state the book has no factor budget.

### B7. Family level and exposure basis (TASK-M4-02; SPEC 865-868, 893-894, P8 SPEC 568-571)

```
active_budget(m,f) = base_weight(m,f)
                   × vs(m,f)                               # own-vol scale, in [0,1] (R-03; momentum only, else 1.0)
                   × min(1.0, family_overlay_1(m,f), …)    # each in [0.5,1]; empty = 1.0 (R-04: specification book only)
```
- M2 (TASK-M2-03) builds `apply_overlays(composite, multipliers, basis) -> Weights` and `compose`; M4 supplies the tag routing, `vs`, `dm` and `base_weights` to it. Do not re-implement `min()` composition.
- `exposure_basis ∈ {active, total}` on every multiplier record (SPEC 1506 (3)). `active` scales a family's long/short or benchmark-relative risk; `total` scales the market book's gross long exposure (SPEC 569-570).
- Long-only sleeve: scaling its active budget moves weights toward the benchmark, not toward cash. Long/short sleeve: toward zero (SPEC 893).
- `vt(m)` scales the market's long book only. "It does **not** scale long/short factor sleeves, which have their own `vs(m,f)`. It does **not** scale the TS-trend sleeve" (SPEC 894). Runtime check: applying a `total`-basis multiplier to an L/S sleeve raises (T-BASIS-01 M4 clause).
- Proposed instrument-level reading of `composite_weights(i | active_budget, gross)` (SPEC 876 gives only the name): with `a = vs × min(1.0, overlays)`, sleeve weights `w_s`, benchmark weights `w_b`:
  - long-only sleeve: `base_weight × [w_b + a × (w_s − w_b)]`, then the market long book × `gross(m)`; freed total exposure -> cash;
  - L/S sleeve: `base_weight × a × w_ls`; no vt.
- Invariants asserted in code: no instrument outside the union of sleeve and benchmark holdings appears; `sign(w_after) ∈ {sign(w_before), 0}`; no renormalisation across families or markets (SPEC 883).
- Binding log: whenever `min()` or a limit binds, the binding factor goes to `overlay_decision.reasons` / `binding` (SPEC 897, 3751).

### B8. Book builders (TASK-M4-07; SPEC 885-890, 4785-4797)

| Book | Factors applied in M4 | Labels |
|---|---|---|
| Specification (`specification:<market>`) | every BUILD NOW and SPECIFICATION BOOK factor whatever its verdict: `vs` (R-03 revision 1) and `dm` (R-04 at floor 0.5) on momentum; reversal / quality / flow at 1.0 | each factor labelled with its card verdict: vs `NOT_RUN` / "indicative PASS; step 3 borderline"; dm "step 3 FAIL" |
| Recommended (`recommended:<market>`) | the invariants plus PASS factors only (disposition `RECOMMENDATION` or `BUILD_AS_INSURANCE`, verdict PASS). Every macro card is NOT_RUN today, so vs and dm enter as 1.0 | the only book shown as a recommendation |

- Recommended builder refuses any factor with disposition `SPECIFICATION_ONLY`, `FORWARD_SIM` or `REFUSAL_BOOK`, and any card whose `build_status_on_pass` is BUILD_AS_INSURANCE while its verdict is NOT_RUN or INSUFFICIENT_DATA (SPEC 3770). Build the refusal in M4; its assertion test I-03 runs at M8.
- Never renormalise freed budget: freed active budget -> benchmark (long-only) or zero (L/S); freed total exposure -> cash (SPEC 883).
- Stack-card accounting: family-level vs (R-03) is **not** a de-risk factor for the stack card (SPEC 1506 (6)).
- Book ids: `recommended:<market>`, `specification:<market>` (SPEC 1180).
- Specification stack used by the goldens: momentum weight = `vs × dm` (vs is sizing, dm the single family overlay; SPEC 866-868, G-MOM-03 "R-03 × R-04").

### B9. Golden computations (test-side code; §9.3.1 conventions SPEC 5720-5737)

- Returns are simple daily returns. Timing: a weight built from information through the close of t−1 earns the return of t.
- US momentum: French Mom daily, 1990-01-02 → 2026-08-31 (SPEC 5744). T 9,233 (SPEC 5948) is about every session of that span, so the first 1990 weights use pre-1990 history (inference; the reference scripts are not on this machine).
- Costs (R4b): per side × abs(Δw), charged on the day the weight earns; initial entry not charged; momentum: the overlay's own turnover on both legs, French Mom gross of its constituent turnover (SPEC 5725). Net 1× = 50 bp, 2× = 100 bp. Net return (proposed formula): `r_net[t] = w[t]·Mom[t] − c·2·abs(w[t] − w[t−1])`, `w = vs` or `vs × dm`.
- Research bootstrap for the "share" figures: circular, 63-day blocks, 1,000 resamples, seed 20261002 (SPEC 5724) -> `validate.sharpe_diff_bootstrap(a, b, block=63, B=1000, seed=20261002)`, share = 1 − p.
- Gate-style p-values (G-MOM-08): v1.2-check mode `gate_boot` (circular blocks, 2,000 resamples, seed 11; 10-session and Politis–White 251-session blocks) from TASK-M2-07.
- Years line (G-YRS-01, T-R03-01): a year is "identical" when vs = 1.0 all year (SPEC 5503); count per-year Sharpe higher than static among the differing years; own return > 0 share.
- Level-1 tolerances (SPEC 5734-5735): Sharpe ±0.01; max DD ±1 pp; window returns ±1 pp; weights ±0.02; bootstrap shares ±0.03; p-values ±0.01 (p ≥ 0.05) and ±0.005 (p < 0.05); deterministic counts exact; bootstrap-dependent counts ±1.
- Ledger: the +0.273 result "enters as research-phase ledger rows" (SPEC 5554). M4 emits row dicts shaped per SPEC 2440 (`config_id`, `rule`, `params`, `timing_class`, `span`, `instrument_book`, `cost`, `phase: "research"`, `run_utc`, `script`, `results_md5`, reference to the stored difference series); persistence is M7's `family_ledger`.

---

## C. Schemas and config this area writes or reads

### C1. Rules-store blocks (SPEC §7; verbatim)

```yaml
# SPEC 4281-4285
base_weights:                            # R-15
  cross_market: {method: inverse_vol, returns: weekly, cov_acting: ewma_0.97, cov_printed: ledoit_wolf_156w, spans: markets_with_sleeves}   # no HRP, no min-variance; ERC only for multi-asset sleeves
  family: {admissible_if: {prior_min: 1, card_verdict_not: REJECT}, weight: one_over_K, range_prior: lower_bound,
           no_registered_prior: not_admissible, not_run_admissible_except: [ts_trend], reject_reweight: logged_governance_event}   # R-15
  tilt_requires_family_card_pass: true

# SPEC 4316-4329
families:
  momentum:
    own_vol_scale: {window: 126, target_ann: 0.12, cap: 1.0, floor: 0.0, min_obs: 126, exposure_basis: active,
                    series: paper_unit_gross_long_short, apply_to: sleeve_budget,
                    revisions: {2: {target: expanding_median_sigma126, min_obs: 252}, 3: {vs: "min(1, (0.12/sigma126)^2)"}}}
    dm_gate: {market_return_months: 24, market_vol_window: 126, vol_quantile: 0.6667, quantile_min_obs: 252,
              multiplier: 0.5, exposure_basis: active, books: [specification], label: "step 3 FAIL", a_provisional_route: closed, pooled_revision: none}
  reversal: {overlay: fixed_1.0, intraday_leg: false, calm_state_downweight: not_adopted}   # canonical key of D3 (Quick start)
  quality:  {overlay: fixed_1.0}
  flow:     {overlay: fixed_1.0}
  ts_trend: {signal: sign_12_1, rebalance: monthly, vol_window_months: 12, target_ann: 0.15, cap: 1.0, overlay_exempt: true,
             card: {class: CARD-O, claim: diversification, instrument_book: multi_line}}
weights_prior: see_R-15                  # 0-3 integers: admissibility filter and display only
prior_haircuts: {value: 0.49, momentum: 0.23, carry: 0.25, defensive: 0.0, multifactor: 0.18}   # one-sided (prof); live_sharpe_multiplier 0.60 (take 40% off) printed too

# SPEC 4144-4145
owner_decisions:
  D3: {key: families.reversal.calm_state_downweight, value: not_adopted, default: not_adopted, options: [not_adopted, reopen_after_krx_net_test],
       status: default, effective_from: null, rationale: null, refs: []}

# SPEC 4256-4258 (data_contracts.roles)
    MOM_PAPER_LS_SERIES: {role: acting_exposure, books: [specification]}   # + the recommended book while verdict_filter admits R-03 (R-19 rule 5)
    DM_MKT_RET_24M: {role: acting_exposure, books: [specification]}        # R-04
    DM_MKT_VOL_126: {role: acting_exposure, books: [specification]}        # R-04

# SPEC 4272-4280 (read)
overlay:
  floor: 0.5
  cap: 1.0
  combine: min
  floor_vs_vt_outside_halted: 0.5
  zero_only_in: [risk_layer, book_HALTED]
  books: [recommended, specification, forward_sim_per_card, refusal_display_only]
  recommended_dispositions: [RECOMMENDATION, BUILD_AS_INSURANCE, INVARIANT_STEP]
```
Also read: `data_contracts.on_failure.acting_exposure: {action: fail_closed, alert: true, halt_after_consecutive_decisions: 2, scope: bound_books, book_counter_halt_after: 2}` and `not_failures: [warmup_before_first_armed_decision, disputed]` (SPEC 4231-4241); `vol_target.annualisation_days: 252` (SPEC 4309).

### C2. Entries M4 adds that the spec names but does not shape (proposed shapes)

```yaml
family_tags:                 # BL-G07 revision; status: proposed until the owner or council confirm (SPEC 1169)
  status: proposed
  components: {trend50: null, trend200: null, momentum: null, rsi: null, macd: null, vol: null}      # effective
  proposal:   {trend50: ts_trend, trend200: ts_trend, momentum: ts_trend, rsi: reversal, macd: ts_trend, vol: null}
priors:                      # R-15 table (SPEC 1722-1732); [lo, hi] = range; null = no registered prior
  KR: {momentum: {"12-1": 0, "12-7_residual": 1}, reversal: {value: 1, flag: UNVERIFIED, until: BL-U02},
       ts_trend: {KOSPI: 1, KOSDAQ: 0}, flow: 3, quality: null}
  US: {momentum: {value: 1, if_vol_scaled_with_dm_gate: 2}, reversal: 1, ts_trend: 3, flow: null, quality: null}
  # EU, JP, TW, CN, IN, EM, CRYPTO per the table in B6
tilts: []                    # each entry needs {market, family, family_card_id}; refused unless that card's verdict is PASS
```

### C3. Rule-object fields (SPEC 4691-4705) for the M4 rules (proposed mapping; field names and bounds are the spec's)

| rule | `kind` | `output_range` | `exposure_basis` | `applies_to` | `composition` | `books[]` |
|---|---|---|---|---|---|---|
| R-03 own_vol_scale | CARD-O | [0.0, 1.0] | active | momentum | min | specification (recommended on PASS) |
| R-04 dm_gate | CARD-O | [0.5, 1.0] | active | momentum | min | specification |
| R-05 | CONVENTION | [1.0, 1.0] | active | reversal, quality | min | recommended, specification |
| R-15 | CONVENTION | [0.0, 1.0] | active | every family | min | recommended, specification |

Refused shapes that touch this area: `output_range` hi > 1.0, overlay outside [0.5, 1.0], vs outside [0, 1.0] (items 2, 8); a vt rule on anything but `market_gross`; any multiplier on `ts_trend`; `composition` other than `min` (31); the recommended book reading a non-PASS multiplier (22); a pooled or A-provisional tier added after results (34).

### C4. Artifact fields this area fills (builders are M6)

- `overlay_decision` v2.0 (SPEC 3717-3763), one per market × family per decision: `market`, `family ∈ ["momentum","reversal","flow","quality","ts_trend","market_gross"]`, `exposure_basis`, `vol_scale` (min 0, max 1), `vol_scale_recommended_book`, `vol_scale_card`, `multipliers[] {rule_id, value (0.5..1.0), exposure_basis, card}`, `composition: "min"`, `overlay_min`, `overlay_floor: 0.5`, `overlay_cap: 1.0`, `overlay_applied_spec_book`, `overlay_applied_recommended_book`, `binding[]`, `reasons[]`, `inputs[]`, `rule_versions {"R-03":"2.0","R-04":"2.0"}`.
- `$defs.card`: `card_id`, `class ∈ ["CARD-O","CARD-P"]`, `verdict ∈ ["PASS","REVISE","REJECT","INSUFFICIENT_DATA","NOT_RUN"]`, `disposition ∈ ["RECOMMENDATION","BUILD_AS_INSURANCE","INVARIANT_STEP","SPECIFICATION_ONLY","FORWARD_SIM","REFUSAL_BOOK","DESCRIPTIVE"]`, `displayed_as ∈ ["recommendation","insurance","invariant","descriptive","refusal"]`, `label`, `results_md5`.
- `macro_state.flags.dm_bear_state` (SPEC 3570).
- `governance_event` (SPEC 4099-4110): kinds used here `admissibility_reweight`, `binding_change`; required `schema, schema_version, event_id, utc, kind, book_id, rule_id, key, actor, reason, refs, prev_row_md5`; `actor ∈ ["owner","operator","runtime","harness","council"]`.

---

## D. Tests

Classes: SYNTH = hermetic with synthetic or inline fixtures; REFDATA = needs frozen reference data absent from this machine; OWNER = needs owner input.

### D1. Tests whose runs_from is M4 (SPEC 5554)

| ID | Exact assertion | Fixture | Class |
|---|---|---|---|
| T-PRIOR-01 (SPEC 5648) | `base_weight(m, f) = IV_m × 1/K_m` over the families with prior ≥ 1 and card not REJECT. Family weights sum to 1 per market and Σ IV_m = 1 (assertions). The Korea reversal prior is stored as 1 (UNVERIFIED). A tilt without a PASSed family card is refused by rules-store validation. | Inline priors + synthetic weekly returns + a temporary rules-store copy (T-HERM-02). Example: EWMA weekly σ KR 0.04, US 0.02 -> IV {KR 1/3, US 2/3}; specification book KR A = {momentum, reversal, flow, ts_trend}, K 4 -> 0.08333 each; US K 3 -> 0.22222 each; set US momentum REJECT -> US reversal 0.22222 -> 0.33333 (× 1.5) at the next decision with exactly one `admissibility_reweight` event; range "0–1" and an unregistered prior are inadmissible. | SYNTH for the mechanics; OWNER for "runs on the confirmed mapping" (TASK-M4-01) and the flow / quality priors |
| T-R03-01, sleeve-scale clause (SPEC 5644; M4 part per 5554) | On the French Mom fixture (50 bp, both legs): ΔSR vs unscaled +0.273 ± 0.01; recorded as research-phase ledger rows | French daily Mom 1990-01-02 → 2026-08-31 with ≥ 126 sessions of pre-1990 history | REFDATA (Ken French `F-F_Momentum_Factor_daily`; no local substitute) |
| T-R03-01, years clause | The years line prints the 20 differing years, with 15 higher gross / 11 net | same | REFDATA |
| G-YRS-01 (SPEC 5953-5955) | cap 1, 1990–2026, 37 calendar years; per-year Sharpe higher than static 15/37 = 40.5% gross with 17 identical years; excluding those 15/20 = 75% gross, 11/20 = 55% net; own return > 0: 73.0% gross, 70.3% net | same | REFDATA |
| G-MOM-01 (SPEC 5748) | Static Mom Sharpe 0.399 / max DD −63.3% (net identical: no overlay turnover) | same | REFDATA |
| G-MOM-02 (SPEC 5749) | R-03 vol scale (σ126, 12%, cap 1): gross 0.714 / −27.9% / avg weight 0.870 / 60.6% of days at cap; net 1× 0.672 / −28.7%; net 2× 0.631 / −29.4% | same | REFDATA |
| G-MOM-08 (SPEC 5755) | Net 1×: ΔSR +0.273 (share 1.00); one-sided p 0.0005 (10-session) / 0.000 (251-session PW); 70% of years positive. Net 2×: ΔSR +0.231 (0.998) | same + M2-07 `gate_boot` and Politis–White block | REFDATA |
| G-MOM-03 (SPEC 5750) | R-03 × R-04 (DM 0.5): gross 0.798 / −20.9% / vol-matched max DD −30.5%; net 1× 0.745 / −21.6%; net 2× 0.691 / −22.7% | French Mom daily + French daily Mkt-RF (σ126_mkt) + monthly F-F factors (24-month market return); ^GSPC only for Sep-2026 (not needed to 2026-08) | REFDATA |
| G-MOM-04 (SPEC 5751) | DM add-on over R-03, gross: full +0.084 (0.996) / ex Sep-2008–Dec-2009 +0.056 (0.97) / 2013-04 → 2026-08 +0.055 (0.94) / 2020–26 +0.101 (0.93); net 1×: full +0.072 (0.983), 2013-04+ +0.044 (0.92), 2020–26 +0.080 (0.91); net 2×: full +0.061 (0.958) | same | REFDATA |
| G-MOM-05 (SPEC 5752) | DM gate on 10.6% of days / 7 spell onsets / 0.38 transitions a year (deterministic counts exact) | same | REFDATA |
| G-MOM-06 (SPEC 5753) | Static → specification stack (gross): Apr-2009 −26.8% → −4.2%; Mar–May 2009 −45.6% → −8.0%; Jan-2001 −21.9% → −15.7%; Nov-2020 −12.0% → −3.9%; Jan-2023 −13.7% → −3.8%; Jul-2026 −10.9% → −5.9%; calendar 2020 −11.0% → +3.1%; calendar 2022 +17.4% → +12.3%; May–Nov 2008 +21.8% → +9.5% (window returns ±1 pp). The §9.3.1 row lists nine windows; TASK-M4-07 quotes six of them. | same | REFDATA |
| G-INTL-01 (SPEC 5762) | Vol scale cap 1, 12%, full sample from 127 days after start, gross: Japan 0.073 → 0.196; Europe 0.843 → 1.143; APxJ 0.924 → 1.125 (2016–26: 0.921 → 0.897); Developed ex-US 0.799 → 0.996. Net not computed. | French regional WML daily (Japan, Europe, Asia Pacific ex Japan, Developed ex US) | REFDATA |
| G-BOOK-01 (SPEC 5756) | (Mom + ST_Rev + RMW)/3: static → spec 1.358 → 1.753; 2020–26 0.400 → 0.618; ST_Rev static 1.253; RMW static 0.480. Net not recomputed. | French Mom, ST_Rev and 5-factor 2×3 (RMW) daily | REFDATA |
| G-MOM-07 (SPEC 5754, 5992) | Reference only: vol scale cap 2: 0.907; DM 0×: 0.657. Reachable only from `tests/reference/` or `docs/` with `reference_only=True`; `core/` cannot import that code; never enters a book, card or artifact | French Mom + market files; M2-07 reference mode | REFDATA |

### D2. Clauses that join at M4 (SPEC 5563-5595)

| Test (home) | Clause | Assertion | Fixture | Class |
|---|---|---|---|---|
| T-BASIS-01 (M0; SPEC 5628, 5569) | "vt is not applied to L/S sleeves" (runtime check, L/S sleeves) | With one long-only and one L/S sleeve in market m, instrument weights of the L/S sleeve are identical under vt 1.0 and vt 0.5; every multiplier object carries `exposure_basis`; a `total`-basis multiplier on an L/S sleeve, or any multiplier on `ts_trend`, raises | synthetic sleeve registry | SYNTH |
| T-COST-01 (M2; SPEC 5638, 5591) | "both legs for L/S sleeves" | A change Δvs on a unit-gross L/S sleeve is charged `c × 2 × abs(Δvs)` on the day the new weight earns; a long-only sleeve one leg; initial entry not charged | synthetic two-leg weights through `strategies.simulate` | SYNTH |

### D3. Hermetic unit checks to add (proposed; not spec ids)

| Check | Assertion | Fixture | Class |
|---|---|---|---|
| vs formula | 126 returns alternating ±0.01 -> σ126 0.159379, vs(rev 1) 0.752923, vs(rev 3) 0.566893; ±0.005 -> σ126 0.079689, vs 1.0; 125 returns -> `insufficient_history`; all-zero returns -> fail closed | inline | SYNTH |
| vs vs local tech-fund rows | `min(1, 0.12/σ126)` reproduces `s_on_2026_06_22` to 1e-5: 0.216946 → 0.553134; 0.438216 → 0.273837; 0.341929 → 0.350950; 0.589982 → 0.203396 | `datalab/results/r2_kr/r2_kr_crash_exposure_2026.csv` (L/S rows only; the `LO_* excess` rows are benchmark-relative and are not a model for acting vs) | SYNTH (local file) |
| dm logic vs local sample | for all 377 rows: `dm == 0.5` iff `r24 < 0 and sig_mkt > q23`; blank inputs -> 1 (verified: 0 mismatches, 36 rows at 0.5) | `datalab/results/r2_kr/r2_kr_dm_gate_sample.csv` (columns `date,r24,sig_mkt,q23,bear,hivol,dm`) | SYNTH (local file) |
| warm-up mapping | never-ARMED book: (1.0, `warmup`), no counter; ARMED book: `MissingInput("missing")` | inline | SYNTH |
| R-05 | overlay list for reversal / quality / flow empty in both books under any flag state; a rule object down-weighting reversal on a stress level is refused while D3 = `not_adopted` | temp rules store | SYNTH |
| recommended book | with every card NOT_RUN, vs and dm enter as 1.0; passing dm to the recommended builder raises | inline | SYNTH |
| no renormalisation | lowering vs or dm for (m, f) changes no other (m′, f′) budget and never raises its own (pre-check of T-MONO-01) | inline, seed 11 | SYNTH |
| sign / creation | overlays never create an instrument or flip a sign | inline | SYNTH |

### D4. Tests in this area that run later (do not gate M4)

| ID | Clause | runs_from |
|---|---|---|
| T-R03-01 | deflated ΔSR 0.98 ± 0.01 at N_equiv 6.3 (PASS), 0.947 ± 0.01 at linear N̂ 12.6 flagged "step 3 borderline"; each revision's header md5 committed before its run and incrementing the R-03 family ledger | M7, after the freeze (SPEC 5558) |
| T-R04-01 | deflated add-on 0.77 ± 0.02 at N_equiv 6.3 → "step 3 FAIL"; A-provisional or pooled route rejected | M7, after the freeze |
| G-DSR-02 | R-03 net of 50 bp: SR 0.6723, T 9,233, skew −0.687, kurtosis 6.948; ΔSR +0.2729, HAC SE 0.0716 | M7 |
| T-MONO-01 | monotone, zero cross-partials on the I-01 fixtures (seed 11); K/(K−1) the one logged exception | M5 |
| I-03 | recommended book never reads a non-PASS factor; refuses R-04 | M8 |
| T-SCOPE-01 (a), (g) | R-04 inputs and R-03's paper series failing on 3 consecutive decisions HALT the specification book only; on admission `MOM_PAPER_LS_SERIES` is bound to the recommended book in the same run | M8 |
| T-BASIS-01 | R-14 runtime clause; S2 clause | M7; M8 |
| T-PLACEBO-01 | R-03 and R-04 pass the timing gate | M7, before the freeze |

Local data inventory relevant to REFDATA rows: `docs/asset_expansion/cache/` holds `yf_SPY.csv` (1995-01-03 → 2026-09-25), sector SPDRs, `yf_069500.KS.csv`, `yf__KS200.csv` (one row); no Ken French file. `datalab/results/us/us_C_factors.csv` holds monthly factor test metrics to 2018-11, not daily series. SPY can exercise `dm_gate` end to end but reproduces no golden (price return, 1995 start).

---

## E. Interfaces

### E1. Needed from earlier milestones

| From | Name and shape | Used for |
|---|---|---|
| M0 (TASK-M0-04/05) | macro rules store with §7 blocks, rule-object validation, edit history; bound assertions `0.5 <= overlay <= 1.0`, `0.0 <= vs <= 1.0` | `families.*`, `base_weights.*`, priors, tilt and D3 refusals |
| M0 (TASK-M0-06) | `owner_decisions.D3`, `{ref: <key>}` resolver | R-05 |
| M0 (TASK-M0-07) | governance appender, kinds `admissibility_reweight`, `binding_change` | R-15 re-weight, derived bindings |
| M1 | `PITValue`, `MissingInput(series_id, reason, role, books)`, `pit_value(series_id, decision_utc, knowledge_utc, consumer, require_session=None)`, `RunContext` | every read |
| M1 (TASK-M1-13) | derived PIT records with lineage | `MOM_PAPER_LS_SERIES`, `DM_MKT_RET_24M`, `DM_MKT_VOL_126` |
| M1 (TASK-M1-17) | role-based failure actions, per-(book, series) and per-book counters, admission-derived bindings, "has this book ever been ARMED" | warm-up mapping, HALT scope |
| M1 | calendars: month-end sessions, `close_print_bound_utc` | `dm_gate` month-end, decision instant |
| M2 (TASK-M2-01) | per-book warm-up mapper of `market_vol_target` | reuse for vs and dm |
| M2 (TASK-M2-03) | `compose(vt, overlays, ladder, post_rearm_cap) -> float`; `apply_overlays(composite, multipliers, basis) -> Weights`; binding log | family and market level |
| M2 (TASK-M2-06) | costed golden harness, research bootstrap (63-day blocks, 1,000 resamples, seed 20261002) | G-MOM-* |
| M2 (TASK-M2-07) | v1.2-check mode `gate_boot`, Politis–White block; reference mode under `tests/reference/` | G-MOM-08, G-MOM-07 |
| card registry (existing gate + M0) | `card(m, f).verdict ∈ {PASS, REVISE, REJECT, INSUFFICIENT_DATA, NOT_RUN}`, `disposition` | admissibility, book builders |

### E2. Exposed to later milestones

| To | Name and shape |
|---|---|
| M5 (TASK-M5-12), M8 | `composite_weights(i | active_budget, gross)` and the two book builders; both monotone, zero cross-partials, no renormalisation |
| M5 | `base_weights(...) -> dict[tuple[str, str], float]`; `inverse_vol_weights(markets, decision_utc, cov="ewma_weekly_0.97") -> dict[str, float]` |
| M6 (`build_overlay_decisions`, `build_macro_state`) | `VSResult`, `Multiplier` (with `card`, `reasons`, `inputs`), `dm_bear_state`, the binding list |
| M7 (TASK-M7-24) | `sleeve_vol_scale(..., revision ∈ {1, 2, 3})`; the paper long/short series builder; research-phase ledger rows for +0.273; years-line function |
| M7 (TASK-M7-25) | `dm_gate` add-on series over R-03 for step 3 on the R-03 family ledger |
| M7 (TASK-M7-26) | `base_weights` for the R-14 ts_trend sleeve; the `ts_trend` exemption checks |
| M8 (TASK-M8-03, `verdict_filter`) | recommended-builder refusal hook; admission -> binding change for `MOM_PAPER_LS_SERIES` |
| UI (Signals / Macro page) | `SignalComponent.family` for display; verdict labels |

---

## F. Ambiguities, contradictions and conservative readings

| # | Issue (lines) | Conservative reading adopted |
|---|---|---|
| F-01 | The composite's six components are single-symbol technical indicators, not market × family factor sleeves; SPEC 1167 says the sources do not list them and 1169 leaves the mapping "proposed" (BL-G07 OPEN, no council ruling). | Every component untagged until the owner or council confirm; proposal stored as a revision with `status: proposed`. No exposure change. |
| F-02 | SPEC 1526 and 4823 assume "QUANTGEN's own momentum sleeve (US shares via KIS, 50 bp on both legs)". The repo's only cross-sectional momentum sleeve is `S_E5_xsmom_sectors` (sector SPDRs), decision REJECT. Which existing card is `card(US, momentum)` is not stated. | A family whose only existing card is REJECT is inadmissible (SPEC 1713). No US momentum sleeve is registered until the owner names one; M4 machinery is validated on synthetic and reference fixtures. Blocks the M7 formal card, not M4 code. |
| F-03 | No sleeve registry is specified (which (market, family) sleeves exist, long-only vs L/S, benchmark, ranking parameters); SPEC 1716 only says IV_m "spans the markets whose sleeves exist in the composite". | Empty registry in production: `inverse_vol_weights` returns `{}`, books carry no factor budget. Registry entries are owner-registered rules-store revisions. |
| F-04 | `base_weights(decision_utc)` (SPEC 1061) has no book argument, yet `ts_trend` is admissible in the recommended book only on its own PASS (SPEC 863, 1718) while the specification book holds every BUILD NOW factor (SPEC 887); YAML `not_run_admissible_except: [ts_trend]` (4284) is book-agnostic. Literal reading makes K_m smaller, hence other families' weights larger, in the recommended book. | Add a book-kind argument. Recommended book: `ts_trend` keeps its slot in K_m when prior ≥ 1 and not REJECT, but its budget enters as 0 until its own PASS (freed budget idles; never renormalised, SPEC 883). Flag for the council; the literal reading is the alternative. At M4 no ts_trend sleeve exists (built in TASK-M7-26). |
| F-05 | A_m empty (K_m = 0), or a family admissible by prior with no built sleeve: SPEC 861 asserts Σ_f base_weight(m,f) = IV_m. | Budget of a missing sleeve or an empty market idles (cash / benchmark); the market stays in the IV span; no reallocation to other markets. |
| F-06 | R-03 is silent on σ126 = 0 or not finite; R-06 treats it as `MissingInput` (SPEC 1047, 1562). | Fail closed (`MissingInput`), never vs = 1.0 on an ARMED book. |
| F-07 | Status case: R-03 writes "`WARMUP`" (SPEC 1518); §3.5 and schemas use `warmup` (SPEC 1050, 1111, 3555). | Lowercase `warmup`. |
| F-08 | Revision 2 "minimum 252 observations" (SPEC 1519; YAML `min_obs: 252`): of returns or of σ126 values? | 252 σ126 observations (the longer warm-up). |
| F-09 | Which revision feeds the specification book before any card runs (SPEC 1519 states only the lowest-PASS rule). | Revision 1 (the registered formula); revisions 2 and 3 never act before a PASS. |
| F-10 | R-04 "24-month total return" (SPEC 1535): total-return index or price index; Mkt-RF + RF or Mkt-RF for the US golden (SPEC 5713 says "monthly F-F factors for the 24-month market return"). | Compound monthly total returns where a total-return series is registered; the golden's exact series is fixed by the reference scripts (REFDATA). Do not guess a value. |
| F-11 | R-04 σ126_mkt estimator details (ddof, mean adjustment, simple vs log) and the quantile interpolation for `vol_quantile: 0.6667` are not restated. | R-03 / R-06 convention: simple returns, ddof = 1, mean-adjusted, × √252; `numpy.quantile(…, 2/3)` linear interpolation; validate on G-MOM-05 when data arrive. |
| F-12 | Start of the expanding quantile window "[start … t]" and warm-up of `dm_gate` (SPEC 1536). | Start = first available σ126 of the registered series; 252 counts σ126 observations; fewer -> `warmup` 1.0 before first ARMED, `MissingInput` after. Analogous local evidence: in `r2_kr_dm_gate_sample.csv` the first `q23` (1996-08-12) appears about 250 sessions after the first `sig_mkt` (1995-10-05), and blank inputs give dm = 1. |
| F-13 | `MOM_PAPER_LS_SERIES` is one id (SPEC 4256) while `sleeve_vol_scale(market, family, …)` is per market. | Register it as a registry group with one member id per momentum sleeve (as SPEC 1891 does for other groups). |
| F-14 | IV_m input series, weekly-return definition (week end, simple vs log), EWMA initialisation and mean adjustment, minimum weeks, and the role bindings of those inputs are not specified; `US_SLEEVE_OFFICIAL_CLOSE` has `books: []` (SPEC 4247). | Weekly simple returns on the last session of each ISO week of the market's registered close series; zero-mean EWMA seeded with the sample variance of the first 26 weeks; fewer than 52 weeks -> insufficient history. Inputs are acting inputs: no binding -> no IV (fail closed). Mark all four as "default, judgment" in the store. |
| F-15 | LW-156w line: shrinkage target not stated; sklearn absent. | numpy Ledoit–Wolf (2004) toward scaled identity; printed only. |
| F-16 | "both legs" cost count: SPEC 1523 "0.85 units a year"; whether that is Σ abs(Δvs) or twice it is not stated. Check: 0.85 × 50 bp ≈ 0.43%/yr, matching the 0.714 → 0.672 Sharpe drop at roughly 10% vol. | Charge `c × Σ_legs abs(Δw_leg)` = `c × 2 × abs(Δvs)`; confirm against G-MOM-02 net (0.672 ± 0.01) once the fixture exists. |
| F-17 | "research-phase ledger rows" at M4 (SPEC 5554) while the family ledger is built at M7 (R-23). | M4 produces row dicts only; nothing is written to production state (T-HERM-02). |
| F-18 | R-04 label: rules store `label: "step 3 FAIL"` (SPEC 4322); §6.2 example `"step 3 FAIL (indicative)"` with verdict NOT_RUN (3783). R-03 disposition while NOT_RUN: example `DESCRIPTIVE` (3779) vs build status SPECIFICATION BOOK (4788). | Use the §6.2 example values in artifacts before the cards run; the rules-store label stays "step 3 FAIL". |
| F-19 | US momentum prior "2 if vol-scaled with the D&M gate, else 1" (SPEC 1724): R-04 never reaches the recommended book. | Admissibility uses 1 in both books (lower bound); display prints the conditional text. |
| F-20 | Sub-index priors (Korea 12-1 vs 12-7 / residual; KOSPI vs KOSDAQ; STOXX50 / DAX / FTSE) do not fit a (market, family) key. | Priors keyed (market, family, variant); a sleeve declares its variant; an undeclared variant resolves to the lowest value in the cell. |
| F-21 | Tech-fund cross-spec amendments (R3 §13, written against macro v1.2) conflict with R-15: XS-01 Korea flow 3 → 1; XS-02 Korea reversal → 0; XS-16 US momentum 1; XS-17 crypto reversal 2 → 0; XS-18 Korea 12-7 / residual → FS-2 FORWARD-SIM card; XS-21 `base_weight = w / 3`; XS-05 replace `prior_haircuts`. | Not applied in M4. v2.0 already answers the normalisation point with IV_m × 1/K_m (SPEC 95, 1712). Each prior change is an owner-confirmed rules-store revision (R3 line 34: "for the owner to confirm"). XS-01 and XS-16 leave admissibility unchanged (still ≥ 1); XS-02 and XS-17 would make the family inadmissible and raise the others by K/(K−1), so they wait for the owner. XS-10 (R-03 on every momentum sleeve in every market) and XS-15 (R-04 specification book only) agree with this brief. |
| F-22 | Tech-fund CR-12 / DNB-TF-12 lists classic technical index-timing rules (RSI, MACD, golden / dead cross) as DO-NOT-BUILD as signals unless they pass the family gate; the existing composite is built from exactly those. | The composite stays a descriptive display (Signals page). No M4 book reads its score; no base weight is attached to it. Decision on the page itself belongs to the tech-fund brief. |
| F-23 | TASK-M4-04 says the recommended-book refusal of R-04 "lands in M8"; SPEC 1542 says the builder refuses it. | Build the refusal in M4; the I-03 assertion test runs at M8. |

---

## G. DO-NOT-BUILD items and invariants that bind this area

DO-NOT-BUILD (SPEC §10.2; refused by rules-store validation where a shape exists, §10.3):

| Item | Text | Line |
|---|---|---|
| 1 | The prior four-state trend × stress classifier and its multiplier table | 6076 |
| 2 | Any multiplier above 1.0: momentum 1.5× in "risk-on", reversal 1.5× or 2×, quality / low-vol / min-vol 1.5×, flow ×1.5, vol-target caps above 1 | 6077 |
| 3 | A VIX-term-structure switch for momentum (0× or halved) or for reversal (1.5×), and the post-stress-clear 0.5× momentum schedule | 6078 |
| 4 | Cut-and-re-add gates on existing exposure | 6079 |
| 6 | Macro-variable factor gates: credit-triggered factor weights (momentum 0.5×, quality 1.5×), momentum 0.5× under rates stress, a real-rate gate on momentum | 6094-6099 |
| 9 | Post-trigger crowding cuts | 6109 |
| 14 | Korean foreign flow as a direction signal or a flow-regime up-weight | 6141 |
| 17 | A 200-day-average conjunction (also: never a substitute for the D&M trigger, SPEC 1537) | 6146 |
| 21 | Any order, cancel, withdrawal, deposit-address or transfer path | 6162 |
| 22 | A non-PASS card's output as a recommendation; R-04 in the recommended book | 6163-6167 |
| 31 | Product-composed de-risk stacks | 6206 |
| 34 | A pooled or A-provisional route for a card already run (R-04's is closed) | 6216-6218 |
| 36 | The Kish trial count | 6223 |
| R-15 | HRP or minimum-variance for cross-market weights; a tilt without a PASSed family card | 1716, 1719 |
| R-05 | Up-weighting reversal or quality in stress; cutting them on macro or stress flags; an intraday reversal leg; a calm-state reversal down-weight while D3 = `not_adopted` | 1550, 1740, 6260 |
| R-03 | vs computed on the benchmark-relative active series; a cap above 1.0 or a floor; DM gate at 0× or cap 2 outside `tests/reference/` | 1517, 1520, 5992 |

Invariants:
- Read-only: no function here imports an order-submission client (SPEC 1112, T-RO-01).
- No acting function reads `context_log`, the R-18 break log or a refusal book (SPEC 1113).
- `0.5 <= overlay_multiplier <= 1.0`; `0.0 <= vs <= 1.0`; nothing above 1.0; the overlay layer cannot emit 0 (SPEC 1506).
- Composition by `min()` at each level; a product-composed path raises (SPEC 1506 (2)).
- Every multiplier declares `exposure_basis ∈ {active, total}` (P8).
- Overlays output multipliers only; they never create a component and never change a sign (P1, SPEC 1171).
- No reallocation: lowering any multiplier never raises another budget; the R-15 K/(K−1) re-weight is the one logged exception (SPEC 883).
- Decide at the close of t, earn from t+1; every input through `pit_value` with `available_at_utc ≤ decision_utc`; pinned `knowledge_utc`, never "now" (SPEC 1105).
- Acting inputs fail closed; warm-up is neutral 1.0 only before the book's first ARMED decision; afterwards a shortfall is `MissingInput("missing")` (SPEC 1111).
- HALT scope: R-03 / R-04 inputs are bound to the specification book and can HALT only that book (SPEC 1871, 1889).
- Only PASS cards feed the recommended book (P7); every macro card is NOT_RUN today, so vs and dm enter it as 1.0.
- No formal card verdict is computed before the M7 freeze (P11, SPEC 5546); M4 goldens are harness reproductions on v1.2 conventions, never a verdict.
- Tests are hermetic and write only to temporary copies of the rules store, ledgers and artifact directory (T-HERM-01/02).
