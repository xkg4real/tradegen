# spec_M2_risk — implementation brief (QUANTGEN v2.0, milestone M2 "Risk layer")

Source: `QUANTGEN_Quant_Council_2026-10-03/claude_code/QUANTGEN_MACRO_INTEGRATION.md` (cited as `L<line>`), task file `prep/tasks/M2.json` (TASK-M2-01 … 09).
Ranges read in full: L850-898 (§3.3), L1499-1509 (R-02), L1554-1577 (R-06), L1605-1617 (R-09), L5489-5708 (§9.0-9.2), L5708-5840 (§9.3.1, G-POST-01), L5982-6038 (§9.3.3-9.5). Also read because the ranges cite them: §1 P0-P19 (L487-657), §3.5 (L961-1113), §3.6 (L1115-1163), §3.8-3.9 (L1173-1251), §4.1 staleness (L1357-1366), §4.2 (L1386-1449), R-07 (L1578-1590), R-19 (L1813-1981), R-32/R-33 (L3361-3393), §6.1-6.2 (L3514-3798), §7 (L4123-4400), §7.1 (L4687-4705), §8.5 costs (L5016-5027), §8.6 windows (L5114-5142), §10 (L6072-6252), §11 (L6264-6337), §12 (L6356-6364).

Repo state checked (2026-10-05): no M0/M1 code exists yet (`pit_value`, `MissingInput`, `close_print_bound_utc`, `runtime_halt`, `value_status`: 0 hits in `*.py`). `core/calendars.py` and `core/markets.py` are single modules, not packages. `core/rules/` is the trading-rule store (PriceCondition, Rule), not the §7 macro rules store. `tests/fixtures/` does not exist. `.v1.2_INTEGRATION_backup.md`, `QX_DLA_postpatch.csv`, `R4_golden_values.csv`, `R4b_golden_values_net.csv` and `/home/claude/quantgen_macro_data/` are not on this machine.

Binding rule for silence (L89): "no exposure change, specification book only, fail closed".

---

## A. Scope

| Task | Deliverable (one line) | Target files (E = exists, N = proposed new) |
|---|---|---|
| TASK-M2-01 | `sma_vol` (SMA20 σ̂, simple returns, ddof 1, ×√252) and `market_vol_target()` → `VTResult`; per-book warm-up / MissingInput mapping; exception → OPS HALT of fed books | N `core/quant/risk_layer.py`, re-exported from E `core/quant/risk.py` (see F-21) |
| TASK-M2-02 | `display_label_rel` (trailing 756 quartiles) and `display_label_abs` (expanding ≥ 10-year quartiles), causal, display only | N `core/quant/risk_layer.py` |
| TASK-M2-03 | `compose()` by `min()` with the 0.5 × vt floor, binding log, product path raises; `apply_overlays()`; overlay layer cannot emit 0 | N `core/quant/risk_layer.py`; E `core/quant/signals.py` (append `apply_overlays`); M0 rules-store validation (`overlay.combine ≠ min` refused) |
| TASK-M2-04 | `hedge_state()` → `HedgeState` with date-aligned corr63, core-PCE vintage read, `hedge_failure`, `classic_risk_off`, display-only `fx_hedge_credit`; never HALTs | N `core/quant/risk_layer.py` |
| TASK-M2-05 | Hedge state applied to correlation inputs of VaR / stress / optimiser (`max(corr, 0)`); Korea covariance series with carry-5-then-drop; covariance status printed | N `core/quant/risk_layer.py`; E `core/quant/optimize.py` (accept adjusted `BasketStats`), E `core/quant/risk.py` (`align_histories` consumer) |
| TASK-M2-06 | Costed golden engine (`|Δw|` per side on the day the weight earns; 2× rerun) and the research bootstrap (circular, 63-day blocks, 1,000, seed 20261002) | E `core/quant/backtest.py` (append; do not change `run_backtest`) |
| TASK-M2-07 | v1.2-check mode (PC-1…PC-7 of v1.2) and reference mode (`reference_only=True`, callable only from `tests/reference/` or `docs/`) | E `core/quant/backtest.py`; N `tests/reference/` |
| TASK-M2-08 | Reproduce G-KR-01…04, 02b, 02c, G-US-01/01b, G-POST-01 M2 rows, I-02 at Level-1 tolerance | N `tests/macro_acceptance.py` (golden tier), N `tests/fixtures/macro/` + `MANIFEST.csv`; E `tests/run_all.py` (register suite) |
| TASK-M2-09 (spike) | Official-close rerun of the pre-patch R4/R4b values (§9.4 item 2); md5-freeze; G-KR-06 joins M2 exit only afterwards | N `tests/reference/`; fixtures manifest |

M2 exit list (L5552): T-CAP-02 (stack-card clause from M7), T-VT-01, T-CORR-01, T-HEDGE-01, T-COST-01, T-LABEL-01, I-02; G-KR-01..04, G-KR-02b/02c, G-US-01/01b/01c; G-KR-06 (reference mode, only once §9.4 item 2's rerun is md5-frozen); plus the §9.0b clauses that join at M2 (section D.2). §12 M2 adds (L6364): "§11's `hedge_credit_off` is reproduced from R-09's inputs, with core PCE read as of its vintage at the decision; `hedge_failure` uses the live USD proxy's 1-day change."

Until M6, tests assert function outputs, never a built artifact (L6368).

---

## B. Build spec, module by module

Every function takes `decision_utc` and the run's pinned `knowledge_utc` (parameters or one `RunContext{decision_utc, knowledge_utc, run_mode}`), never "now", and reads data only through `pit_value` with `consumer` = the binding's consumer key (L1105). No function reads a raw DataFrame of a series (L1106). No function may import an order-submission client (L1112). No acting function may read `context_log`, the R-18 break log or a refusal book (L1113).

### B.1 Types (N `core/quant/risk_layer.py`)

```python
@dataclass(frozen=True)
class VTResult:                      # L1044-1047: "sigma_ann, weight in [0,1] (cap 1.0 permanent), display_label_rel, display_label_abs, inputs, status"
    market: str                      # §6.1 enum: KR, US, JP, EU, TW, CN, HK, IN, EM, CRYPTO, FX
    estimator: str                   # "sma20" in M2
    status: str                      # "ok" | "insufficient_history"
    sigma_ann: float | None          # decimals (0.2882), None when insufficient_history
    target_ann: float                # 0.20 KR, 0.15 US
    weight: float | None             # min(1.0, target/sigma) in [0, 1]; None when insufficient_history
    n_valid_returns: int
    display_label_rel: str | None    # calm | normal | elevated | stressed
    display_label_abs: str | None
    exposure_basis: str              # "total"
    inputs: tuple[dict, ...]         # macro_state $defs/input records of the closes read (L3632-3651)

@dataclass(frozen=True)
class BookVT:                        # per-book mapping of a VTResult / MissingInput
    book_id: str
    weight: float                    # value entering compose() for this book
    vt_status: str                   # "ok" | "warmup" | "fail_closed"   (macro_state.vol.vt_status enum, L3555)
    fail_closed: bool
    missing: "MissingInput | None"

@dataclass(frozen=True)
class ComposeResult:
    composed: float                  # vt * overlay_min
    overlay_min: float               # min(1.0, overlays..., ladder, post_rearm_cap), in [0.5, 1.0]
    binding: tuple[str, ...]         # factor ids equal to overlay_min when overlay_min < 1.0; () otherwise

@dataclass(frozen=True)
class HedgeState:                    # L1051-1052
    hedge_credit_off: bool
    hedge_failure: bool
    classic_risk_off: bool
    fx_hedge_credit: bool | None     # display only
    hedge_reasons: tuple[str, ...]   # subset of {ok, risk_model_input_stale, risk_model_exception, corr_positive, core_pce_ge_3}
    hedge_stale_inputs: tuple[str, ...]   # series ids
    core_pce_yoy: float | None       # decimals
    corr63: float | None
    alerts: tuple[dict, ...]         # macro_state alerts[] records (L3625-3629)
    inputs: tuple[dict, ...]
```

`MissingInput`, `PITValue` come from M1 (`core/ficc/data`, L967-996). `MissingInput.reason ∈ {"missing","stale","provisional_intraday","session_mismatch","synthetic_rejected"}`; "disputed" and "warmup" are statuses of a used value, never failures (L993-994).

### B.2 `sma_vol` (R-06 estimator row, L1561; config L4309-4310)

```python
def sma_vol(valid_returns: Sequence[float], window: int = 20, annualisation_days: int = 252) -> float | None
```
- Input: daily **simple** close-to-close returns `r_d = C_d / C_{d-1} - 1` through the close of t, in date order, flagged stale-carry days already excluded.
- `σ̂_m(t) = stdev(r_m[t−19 … t]) × √252`; "the mean-adjusted sample SD (ddof = 1, R-30's 'sample variance')" (L1561).
- Returns `None` when `len(valid_returns) < window`.
- Config read verbatim: `vol_target.annualisation_days: 252`; `vol_target.sigma: {returns: simple, ddof: 1, mean_adjusted: true, stale_carry_days: excluded_window_extends}` (L4309-4310).
- Golden: rv20 28.82% and vt 0.694 on 2026-10-02 (L1561, L5673).
- Do not reuse `History.log_returns()` or `analyze_history` (`core/quant/risk.py` L66, L84 use log returns).
- "A flagged stale-carry day is excluded and the window extends to the last 20 valid returns" (L1561). Stale-carry flag = `data.stale_carry_flag: flat_ohlc_zero_volume_on_session_day` (L4209).

### B.3 `market_vol_target` (L1044-1047, L1562-1563, L1566; config L4286-4293, L4311)

```python
def market_vol_target(market: str, decision_utc: datetime, estimator: str = "sma20", *, knowledge_utc: datetime) -> VTResult | MissingInput
```
Algorithm:
1. Parameters from the rules store, verbatim:
   - `vol_target.KR: {estimator: sma, window: 20, target_ann: 0.20, cap: 1.0, cap_permanent: true, exposure_basis: total, instrument_book: KRX_ETF_line, notional_nav: {ref: sleeves.KR.notional_nav}, rebalance: daily, no_trade_band: 0.0, fill_model: KRX_close_auction, card: {card_id: MACRO-R06-KR-ETF, build_status_on_pass: BUILD_AS_INSURANCE, conditions: see_R-06_card_korea, forward_record: falsification_only}}` (L4287-4289)
   - `vol_target.US: {estimator: sma, window: 20, target_ann: 0.15, cap: 1.0, cap_permanent: true, exposure_basis: total, registered_card: {instrument_book: US_shares_KIS, verdict: REJECT, label: "REJECT (instrument: US shares via KIS, 50 bp, daily)", rerun: false}, futures_card: cards.R-29_US_FUT}` (L4290-4292)
   - `vol_target.other_markets: {estimator: sma, window: 20, target_ann: null, cap: 1.0}` — "pre-register per market on its card" (L4293). A market with `target_ann: null` raises (no default target is invented; L1563 "Other markets must be pre-registered per market on their card before they run").
   - `estimator` other than `"sma20"` raises in M2 (challengers enter only through R-30 as a counted revision, L1561; §10 item 25).
2. `t` = the session with `close_print_bound_utc(market, t) == decision_utc` ("decided at the close of t (KRX `decision_utc` = `close_print_bound_utc(KR, t)`, 06:30:30Z today), earning from t+1", L1562).
3. Read closes through `pit_value(series_id, decision_utc, knowledge_utc, consumer="R-06", require_session=<session>)` (`require_session` is mandatory for close-type acting reads, L1012). Series: KR → `KOSPI_OFFICIAL_CLOSE`; US → `US_SLEEVE_OFFICIAL_CLOSE` (L4246-4247). "Close-type inputs need `value_status = official_close` (R-01)" (L1566). "Local inputs only" (L1566; P4 L530-533).
4. A `MissingInput` for the decided session's close is returned unchanged (reason preserved).
5. Walk sessions backwards collecting valid simple returns; skip flagged stale-carry sessions; stop at `window` valid returns.
6. Fewer than 20 valid returns → `VTResult(status="insufficient_history", sigma_ann=None, weight=None)` (L1562, L1046).
7. `sigma = sma_vol(...)`. `sigma == 0` or `not math.isfinite(sigma)` with 20 valid returns → "a contract violation, so the component fails closed and counts toward its books' HALT limit" (L1562): return `MissingInput(series_id, reason="missing", role, books)` (reason choice: F-5).
8. `vt_m = min(1.0, target_m / σ̂_m(t))` (L1562). `assert 0.0 <= vt <= 1.0` (R-02 rule 1, L1506). "**The cap of 1.0 is permanent**: any vt > 1.0 fails validation … No floor. `exposure_basis=total`." (L1563)
9. Labels per B.5; `inputs` = the PIT records read (at least the decided-session close).

Config for warm-up, verbatim (L4311): `vol_target.warmup: {min_valid_returns: 20, value: 1.0, status: warmup, counts_as_failure: false, only_before_first_armed_decision: true, after_armed: MissingInput, degenerate_sigma: MissingInput}`.

Never: `max(σ̂_SMA20, implied)` (retired, L1573; §10 item 30); any model estimator outside R-30 (§10 item 25); US or global inputs for Korea gross (P4).

### B.4 Per-book mapping (L1046-1047, L1111, L1562, L1880, L1884)

```python
def vt_for_book(result: VTResult | MissingInput, book_id: str, *, ever_armed: bool, prev_weight: float | None) -> BookVT
```
| `result` | book never ARMED | book has been ARMED |
|---|---|---|
| `VTResult(status="ok")` | weight = result.weight, `vt_status="ok"` | same |
| `VTResult(status="insufficient_history")` | weight **1.0**, `vt_status="warmup"`, `fail_closed=False`, no counter increment | `MissingInput("missing")`: `vt_status="fail_closed"`, `fail_closed=True`, weight = `prev_weight` (state unchanged), alert, counts toward the HALT limit — "never weight 1.0" (L5673) |
| `MissingInput` (any reason, incl. degenerate σ̂) | `vt_status="fail_closed"`, `fail_closed=True`; the book cannot ARM (L1180: ARMED needs every bound acting input "fresh and past warm-up") | `vt_status="fail_closed"`, `fail_closed=True`, weight = `prev_weight`, alert, counter +1 |

- "a store loss or a truncated history never resets a de-risk factor to 1.0" (L1111).
- Acting-input failure: "return the previous state with the component's `fail_closed = true` and the input's status code, and raise an alert; it never interpolates" (L1108). Status-code map `MissingInput.reason` → `macro_state.inputs[].status`: missing / stale / provisional_intraday / session_mismatch / synthetic_rejected → `missing` / `stale_missed_release` / `provisional_rejected` / `session_mismatch` / `synthetic_rejected` (L1108).
- HALT counters are M1's (`data_contracts.on_failure.acting_exposure: {action: fail_closed, alert: true, halt_after_consecutive_decisions: 2, scope: bound_books, book_counter_halt_after: 2}`, L4231-4232). M2 only reports the failure to the runtime.
- Books fed by the KR close: `KOSPI_OFFICIAL_CLOSE: {role: acting_exposure, books: [specification]}` "+ the recommended book while verdict_filter admits R-06 KR … vt enters it as 1.0 until then" (L4246). `US_SLEEVE_OFFICIAL_CLOSE: {role: acting_exposure, books: []}` while `sleeves.US.line = none` (L4247): a US failure HALTs no book.
- Recommended book: "While R-06 KR is NOT_RUN, vt enters as 1.0" (L886); `vt_weight_recommended_book` "= vt_weight_next once R-06's card is PASS; 1.0 while NOT_RUN or INSUFFICIENT" (L3559). The selection is the book builder's (M4/M6/M8); `compose` is book-agnostic.

### B.5 Display labels (L1565; config L4312-4314; schema L3562-3565)

```python
def display_label_rel(sigma_history: Sequence[float]) -> str | None   # trailing 756 σ̂ values ending at t
def display_label_abs(sigma_history: Sequence[float], first_date: date, t: date) -> str | None   # expanding full history, >= 10 years
```
- "`display_label_rel`: σ̂ against the quartiles of its own trailing 756 sessions; `display_label_abs`: σ̂ against the quartiles of its expanding full history (≥ 10 years). Both are computed causally from filtered, never smoothed, values. They are volatility labels, not regime states (P19)." (L1565)
- Values: `[calm, normal, elevated, stressed]`. Mapping (confirmed by the goldens): σ̂ < Q1 → `calm`; Q1 ≤ σ̂ < Q2 → `normal`; Q2 ≤ σ̂ < Q3 → `elevated`; σ̂ ≥ Q3 → `stressed`. "A value exactly on a quartile boundary takes the higher label (default, judgment)" (L5643).
- Config verbatim: `vol_target.display_labels: {rel: {method: trailing_756_quartiles}, abs: {method: expanding_full_history_quartiles, min_years: 10}, values: [calm, normal, elevated, stressed], filtered_only: true, acts: false, per_label_coverage: reported, scoring: tick_loss}`.
- Schema constants: `label_method_rel = "trailing756_quartiles_causal_filtered"`, `label_method_abs = "expanding_full_history_quartiles_causal_filtered"`.
- Each σ̂(s) in the history is the B.2 value computed from data through s only; appending future data never changes a past label (T-LABEL-01).
- Goldens (L1565, L5804, L5838): KOSPI 2026-10-02 `elevated` (relative: σ̂ 28.8%, 70th percentile; trailing quartiles 15.7 / 18.6 (18.55) / 33.6%) and `stressed` (absolute); US 2026-10-01 `normal` (relative: 10.7%, 28th percentile; 10.5 / 12.7 / 15.2%). rv21 31.9% at the 73rd percentile is a printed line (L5838), not a label input.
- Display only, never gating (L1565; §10 item 24). No conformal layer (§10 item 28). Field class: display (L3370), so a label validation failure never HALTs.
- "Per-label coverage is reported" (L1565): reference numbers KOSPI 2000-26 SMA20-FHS 5% VaR breaches by label 6.48 / 6.91 / 3.43 / 3.38% (Kupiec p ≤ 0.004). No M2 test asserts it; the FHS form belongs to the M3 harness (F-12).

### B.6 `compose` (§3.3 L870-881, R-02 L1506-1508, P2 L508-518; config L4272-4280)

```python
def compose(vt: float, overlays: list[float], ladder: float, post_rearm_cap: float) -> float   # L1058: "vt * min([1.0] + overlays + [ladder, post_rearm_cap]); raises on product"
def compose_detail(vt: float, overlays: Mapping[str, float], ladder: float, post_rearm_cap: float) -> ComposeResult
def verify_composition(vt, overlays, ladder, post_rearm_cap, recorded_composed: float) -> None      # raises CompositionError; reused by bounds_ok (M8)
```
- Formula: `composed(m) = vt(m) × min(1.0, gross_overlay_1(m), …, ladder(m), post_rearm_cap(m))`; "each in [0.5,1]; ladder, post_rearm_cap ∈ {1.0, 0.5}" (L871-872). Empty overlay list = 1.0 (L868).
- Assertions at code level (R-02 rule 1, L1506): `assert 0.5 <= overlay_multiplier <= 1.0`, `assert 0.0 <= vt <= 1.0` (and `assert 0.0 <= vs <= 1.0` where vs is passed); `ladder in {1.0, 0.5}`; `post_rearm_cap in {1.0, 0.5}`. Violation raises (→ B.10 guard → OPS HALT).
- Floor: `assert composed >= 0.5 * vt` — "written as a product, so vt = 0 needs no division" (L881). "The floor applies to composed(m): a concentration bound or risk-layer cap may take gross(m) lower without a bounds failure" (L881). `gross(m) = min(composed(m), concentration_bound(m))` is M5 (L873).
- "HALTED … sets this book to 0×; it is never an argument of min(); other books continue" (L874).
- Product path: "A product-composed path raises: `bounds_ok` recomputes composed(m) from the recorded factors, and the rules store refuses `combine ≠ min`" (L881). Implement (a) `compose` reads `overlay.combine` and raises unless `"min"`; (b) `verify_composition` recomputes and raises when the recorded value differs (e.g. 0.375 recorded for overlays 0.75 and 0.5).
- Binding log: "Whenever `min()` or a limit binds, the binding factor is recorded in `overlay_decision.reasons`. Each card prints the binding share of every factor." (L897). Schema also has `binding: [string]` "factors at which min() or a limit bound" (L3751). Write the factor id to `binding` and a readable line to `reasons` (F-9).
- Mandatory example: overlays 0.75 and 0.5 compose to 0.5, "never 0.375", binding factor logged (L5627).
- Config verbatim (L4272-4280):
  ```yaml
  overlay:
    floor: 0.5
    cap: 1.0
    combine: min                           # R-02; a product-composed path raises
    floor_vs_vt_outside_halted: 0.5        # composed >= 0.5 x vt on every non-HALTED day (T-CAP-02)
    zero_only_in: [risk_layer, book_HALTED]
    books: [recommended, specification, forward_sim_per_card, refusal_display_only]
    recommended_dispositions: [RECOMMENDATION, BUILD_AS_INSURANCE, INVARIANT_STEP]
    stack_card: {when_de_risk_factors_ge: 2, class: CARD-P, spec: "§8.7"}
  ```
- What vt covers (L894): the market's long book; **not** long/short factor sleeves (own `vs(m,f)`), **not** the TS-trend sleeve (R-14, exempt from overlays). Rules-store predicate: a vt rule on anything but `market_gross` is refused (L4696).
- Not in M2: the stack card (R-02 rule 6; M7), T-MONO-01 (M5), `concentration_bound`, `drawdown_ladder`.

### B.7 `apply_overlays` (E `core/quant/signals.py`, append; L1063, L865-868, R-02 rules 3-4)

```python
def apply_overlays(composite: Mapping[str, float], multipliers: Sequence[Multiplier], basis: Literal["active", "total"]) -> Weights
#   L1063: "bounds P2, min() composition, basis P8, binding log"
```
- `Multiplier` = the `overlay_decision.multipliers[]` item: `{rule_id, value, exposure_basis, card}`; `value` in [0.5, 1.0] (L3735-3737).
- Family level: `active_budget(m,f) = base_weight(m,f) × vs(m,f) × min(1.0, family_overlay_1(m,f), …)`; "each in [0.5,1]; empty = 1.0 (R-04: specification book only)" (L866-868). `base_weight` (R-15) and `vs` (R-03) arrive in M4; M2 delivers the bounded `min()` scaling and binding log.
- Raises when: a multiplier value is outside [0.5, 1.0] (so the overlay layer cannot emit 0: R-02 rule 4 "0× exists only in the risk layer and in HALTED", L1506); a multiplier's `exposure_basis` is missing or differs from `basis` (R-02 rule 3 "Every multiplier record has `exposure_basis ∈ {active, total}`"; P8 L568-570); more than one multiplier is combined other than by `min()`.
- Returns scaled values plus `overlay_min` and `binding` (same convention as B.6). No renormalisation: freed active budget moves toward the benchmark (long-only) or zero (long/short); freed total exposure moves to cash (L883).
- A component with no family tag gets multiplier 1.0 (L1169). Overlays never create a component or change a sign (L1171). Mapping of the six existing components (`trend50`, `trend200`, `momentum`, `rsi`, `macd`, `vol` in `compute_signals`) to families is BL-G07 / M4, not M2.

### B.8 `hedge_state` (R-09 L1612-1614; R-19 rule 4 L1872-1877; config L4365-4370, L4233-4235)

```python
def hedge_state(decision_utc: datetime, *, knowledge_utc: datetime) -> HedgeState
```
Inputs — all `risk_model` bindings (L1612, L1885):

| Input | Series id / binding (L4250-4263) | Read rule |
|---|---|---|
| Core PCE YoY | `PCEPILFE: risk_model` | "calendar lag, available at its release" (L1612); read "through `pit_value` at the decision's `knowledge_utc` from its ALFRED vintages" (L5637). YoY = level(M) / level(M − 12 calendar months) − 1, calendar-based, never positional (P5 L541; `data.monthly_lag_method: calendar`, L4217). |
| US equity daily return | `SPX_OFFICIAL_CLOSE: {role: risk_model, consumer: corr63}` | also corr63's equity leg (L1612) |
| US 10y | production `US10Y_KIS_QUOTE: {role: risk_model, consumer: corr63}`; backtests `DGS10: {role: risk_model, consumer: corr63_backtests}` (strict H.15) "or Treasury par yields per the Treasury channel (§4.1)" (L1612) | `data.us10y: {production: US10Y_KIS_QUOTE, history: [TREASURY_PAR, DGS10], dgs10_strict_lag_bdays: 2, treasury_lag_bdays: 1, live_proxy_history: "^TNX"}`; "code uses usable_at()" (L4224) |
| Live broad USD | `USD_LIVE_PROXY: risk_model` | "read as a quote snapshot stamped ≤ the decision instant (`obs_kind = quote_snapshot`); a vendor daily 'close' stamped after the decision instant is never used" (L1431). Default name: ICE US Dollar Index, Yahoo `DX-Y.NYB` (L1431, L6030). **DTWEXBGS is context, never an input** (L1886, L4265). |
| USD/KRW (fx_hedge_credit only) | ECOS 15:30 close (`ECOS_1530_CLOSE`), role context (L1414: "C (context; `fx_hedge_credit` display, R-09)") | weekly, Friday anchor |

corr63 (L1612): "the 63-day correlation of daily US equity returns with −Δ10y, **computed on date-aligned pairs (r_eq(D), −Δy(D)) for D ≤ the last 10y date usable at `decision_utc`; the statistic is lagged, never one leg**."
```python
def corr63(eq_closes: Mapping[date, float], y10: Mapping[date, float], last_usable_10y_date: date, window: int = 63) -> float | None
    # dates = sorted(D for D in eq ∩ y10 if D <= last_usable_10y_date); pairs (r_eq(D), -(y(D) - y(D_prev))) on consecutive common dates
    # Pearson correlation of the last 63 pairs; None if fewer than 63
```
Goldens: +0.53 ± 0.01 at 2026-09-30 (S&P vs −ΔDGS10); a series-lag implementation gives −0.094 and must fail (L5636). §11 also prints the 252-day value +0.33 (L6335; printed only).

States, verbatim (L1613):
- `hedge_credit_off = (corePCE_yoy ≥ 0.030) or (corr63 > 0) or (any hedge_state input stale or failing; a risk_model_covariance binding never sets it, R-19 rule 4) or (an exception inside hedge_state)` — "decimals in the core, §0.3: 0.030 is 3.0%".
- `hedge_failure = (equity_1d < −1.5%) and (USD_proxy_1d < 0)` (daily), "or the weekly version: S&P week < −2% and the `USD_LIVE_PROXY` week < 0 (never DTWEXBGS)".
- `classic_risk_off = (equity_1d < −1.5%) and (USD_1d > 0) and (UST10_1d < 0)`.
- `fx_hedge_credit` (display only): "no credit while the trailing 26-week correlation of weekly KOSPI returns with ΔUSD/KRW is ≥ 0 (+0.05 on 2 Oct 2026; weeks anchored on the Friday KRX close and the ECOS 15:30 USD/KRW close)". Credit (True) iff corr < 0.0; `None` when not computable (schema type `["boolean","null"]`, L3574).

Config verbatim (L4365-4370):
```yaml
risk_layer:
  hedge_state: {core_pce_yoy_threshold: 0.030, corr_window: 63, corr_threshold: 0.0, corr_pairs: date_aligned, lag: statistic_not_leg,
                stale_input: hedge_credit_off, exception: hedge_credit_off, usd_input: USD_LIVE_PROXY, reasons_field: flags.hedge_reasons,
                hedge_failure_daily: {equity_ret_lt: -0.015, usd_ret_lt: 0.0},
                hedge_failure_weekly: {equity_ret_lt: -0.02, usd_ret_lt: 0.0},
                fx_hedge_credit: {display_only: true, window_weeks: 26, credit_if_corr_lt: 0.0},
                stressed_covariance_from_turbulence: only_after_preregistered_win}
```
and (L4233-4235) `data_contracts.on_failure.risk_model: {action: conservative_default, set: {hedge_credit_off: true}, hedge_failure_from: USD_LIVE_PROXY, operator_alert_after_missed_releases: 2, halt: never, also_on: hedge_state_exception}`.

`hedge_reasons` ⊆ `{ok, risk_model_input_stale, risk_model_exception, corr_positive, core_pce_ge_3}`, "causes can co-occur" (L1949, L3572). `["ok"]` iff `hedge_credit_off` is False. §11 value on 2026-10-02: `hedge_credit_off = TRUE`, `hedge_reasons = [corr_positive, core_pce_ge_3]`, core PCE YoY 3.008% (Aug-2026), corr63 +0.53; `hedge_failure` FALSE; `fx_hedge_credit` FALSE (+0.05) (L6334-6337; example L3676-3677).

Failure behaviour (never HALT):
- Any input `MissingInput` or `is_stale(...)` ≠ Fresh → `hedge_credit_off = True`, reason `risk_model_input_stale`, series id appended to `hedge_stale_inputs`, alert raised; "an operator alert follows two missed releases" (L1614; `operator_alert_after_missed_releases: 2`).
- The whole body is wrapped: any exception → `HedgeState(hedge_credit_off=True, hedge_reasons=("risk_model_exception",), …)` + alert; "never HALTED (red line E4)" (L5625; `risk_layer.never_halt_on: [risk_model_input_stale_or_failing, hedge_state_exception, …]`, L4362).
- "A stale or failing risk-model input, or an exception inside `hedge_state`, never moves any book to HALTED" however long it stays stale (L1614, L1964). `hedge_state` never calls `runtime_halt`.
- "If the publication calendar cannot be read, … every risk-model input takes its conservative default" (L1956).
- Lag-audit violation on a risk-model input → `hedge_credit_off` + alert, never HALT (L1215).
- "**No equity-gross effect in any case.**" … "`fx_hedge_credit` changes no exposure." (L1614). vt is unchanged by any hedge-state failure (L1968).
- Field class: hedge flags are display properties "which never HALT" (L3370).
- Replay: a later core-PCE revision loaded after the decision leaves that decision's `hedge_reasons` unchanged (as-of read at the artifact's `knowledge_utc`, L5637).
- "USD down and equities down" is never an equity de-risk trigger (§10 item 15, L6144).

### B.9 Applying the hedge state; Korea covariance (R-09 Effect L1614; R-19 rule 4 L1877; R-07 (7) L1585)

```python
def apply_hedge_state(stats: BasketStats, asset_class: Mapping[str, str], hedge: HedgeState) -> BasketStats
    # asset_class values: "equity" | "duration" | "usd_hedge" | "jpy_hedge" | other
    # hedge_credit_off: corr[i,j] = max(corr[i,j], 0) for every (equity, duration) pair
    # hedge_failure:    additionally corr[i,j] = max(corr[i,j], 0) for every (equity, usd_hedge | jpy_hedge) pair
    # cov rebuilt from the adjusted corr and the unchanged vols; weights of equity gross are never touched
```
- "When `hedge_credit_off`, the risk layer gives **no diversification credit** to duration-type hedges: it uses `max(estimated corr, 0)` between equity and bond/duration legs in VaR, stress, optimiser inputs and sizing. When `hedge_failure`, it also removes USD/JPY-hedge credit." (L1614)
- Consumers in the existing code: `align_histories` → `BasketStats` (`core/quant/risk.py` L134-160) → `optimize_portfolio`, `efficient_frontier` (`core/quant/optimize.py`). "QUANTGEN has no bond sleeve, so the effect is mainly on risk-model assumptions (the Bonds and Rates pages and the Portfolio optimiser)" (L1616).
- "Cross-asset regimes (turbulence, absorption ratio) stay in the risk model and the display, never as multipliers. A turbulence-based stressed covariance may replace the stock–bond-regime input only if it beats it in a pre-registered test." (L1614) → not built in M2.
- Korea covariance (R-07 (7), L1585): "Treat Korea gross as semiconductor exposure in the covariance. Shanghai, HSI, TAIEX and Nikkei stay in the Korea covariance, on synchronous or lagged returns (§4.1)." Bindings (L4250-4264): `SPX_OFFICIAL_CLOSE … {role: risk_model, consumer: korea_covariance, action: risk_model_covariance}`, `SOX_CLOSE: {role: risk_model, consumer: korea_covariance, action: risk_model_covariance}`, `ASIA_INDEX_CLOSES: {role: risk_model, consumer: korea_covariance, action: risk_model_covariance}` (Nikkei, Shanghai, HSI, TAIEX); `risk_layer.korea_covariance_extra: [SHANGHAI, HSI, TAIEX, NIKKEI]` (L4364).
- Covariance-only failure: `risk_model_covariance: {action: carry_last_valid_terms_stale_then_drop, carry_max_decisions: 5, alert: true, halt: never, sets_hedge_credit_off: false}` (L4239-4240): carry the series' last valid covariance terms labelled stale for up to 5 decisions, then drop the series and label it; "the displayed risk prints the covariance status" (L1877). The carry count is derived from the input's stale labels in at most the last 5 artifacts (L5616).
- Cross-market usability: `close_print_bound_utc(m, D) + buffer < decision_utc`, `buffer_s: 60` (L4242); "Covariances use synchronous or lagged returns only" (L1894).
```python
def korea_covariance(decision_utc, *, knowledge_utc, carry_state: Mapping[str, int]) -> KoreaCov
    # KoreaCov{cov, series_used, status: {series_id: "ok" | "stale_carried:<n>" | "dropped"}, carry_state_next}
```

### B.10 Exception guard for acting risk-layer functions (§3.8 L1178; T-MISS-02 L5625)

```python
def guard_acting(component: str, books: Sequence[str], fn, *args, **kw)
    # try fn(...); on Exception: for b in books: runtime_halt(b, "OPS", "acting_risk_layer_exception"); raise alert; return a fail-closed marker
```
- "an exception in an acting risk-layer function (`market_vol_target`, `concentration_bound`, `drawdown_ladder`, `compose`)" is an OPS trigger (L1178); reason code from `risk_layer.halted_triggers.OPS: [… acting_risk_layer_exception …]` (L4356-4358). HALT is per book (`risk_layer.halt_scope: per_book`, L4353): only the books the function feeds.
- M2 wires `market_vol_target` and `compose`; M5 reuses the guard for `concentration_bound` and `drawdown_ladder` (L5586).
- `hedge_state` is never wrapped by this guard (B.8).
- OPS re-arm: when the cause clears, automatic, no reference reset, no post-re-arm cap (L1179). Effective time: "A HALT decided at the close of t sets the weights decided at t to 0" (L1178).

### B.11 Costed golden engine and research bootstrap (E `core/quant/backtest.py`, append; §9.3.1 L5720-5725; P10 L579-602; §8.5 L5016-5026)

```python
def vt_weights(closes: Sequence[float], target_ann: float, window: int = 20, cap: float = 1.0, *, reference_only: bool = False) -> np.ndarray
def costed_book(returns: np.ndarray, weights: np.ndarray, cost_side: float) -> np.ndarray     # daily book returns
def sharpe(daily: np.ndarray, annualisation_days: int = 252) -> float
def max_drawdown(daily: np.ndarray) -> float
def window_return(daily: np.ndarray, dates, start: date, end: date, include_start: bool) -> float
def static_comparator(returns: np.ndarray, weights: np.ndarray) -> np.ndarray             # S: constant mean(weights) × returns, uncosted
def research_bootstrap_share(d_a: np.ndarray, d_b: np.ndarray, *, block: int = 63, resamples: int = 1000, seed: int = 20261002) -> float
```
Construction rules, verbatim (L5721-5725):
- "Returns are simple daily returns."
- "The US market is French Mkt-RF through 2026-08, spliced with the ^GSPC price return for Sep-2026. Korea uses ^KS11 price returns (no dividends)."
- "**Timing:** a weight built from information through the close of t−1 earns the return of t".
- "**Research bootstrap:** circular, 63-day blocks, 1,000 resamples, seed 20261002 (R4-comparable). Gate-style statistics for the cards use §8.5."
- "**Costs (R4b):** per side × |Δw|, charged on the day the weight earns. Initial entry not charged. Buy-and-hold uncosted."
- v1.2 conventions for these goldens: "Korea with cash at 0, the US on Mkt-RF excess returns, the §8.6 windows" (L5728).
- `cap > 1.0` raises unless `reference_only=True` (B.12).
- Rates are read from the gate's cost table (M0, TASK-M0-12), never redefined (L591, L4129): KRX ETF 3 bp / 6 bp; KRX stock 35 / 70; US shares via KIS 50 / 100; crypto 10 / 20; futures 5 / 10; FX 10 / 20 (L582-589). Every result is rerun at 2× (L580). "Changing the rate in a card header raises" (L5638); lowering a cost is never a permitted fix (L602).
- "Buy-and-hold and S carry no cost" (L5020). S = "the static book at the overlay's average exposure: overlay-off × the mean multiplier, constant, same days, uncosted" (L4972).
- Existing `run_backtest` (`core/quant/backtest.py` L115-119) charges the initial entry (`np.diff(np.concatenate([[0.0], pos]))`) and takes a free `cost_bps`; it stays untouched for the Strategy Lab and is not the golden engine.
- Reference turnover: KR VT20 1.50 units a year; US VT15 2.52 a year, 1.26% a year at 50 bp (L1568, L1570).

### B.12 v1.2-check mode and reference mode (§9.3.3 L5984-5992)

v1.2-check mode — reproduction only, "never a verdict"; uses the v1.2 protective checks of `.v1.2_INTEGRATION_backup.md` §8.7, never the v2 package:
- PC-1: `MDD(rule) − MDD(S) ≥ +3.0 pp` at 1× **and** 2× costs, and MDD(rule) better than MDD(overlay-off);
- PC-2: tail-exposure ratio ≤ 0.90;
- PC-3: margin δ = 0.10, one-sided percentile bootstrap p of {ΔSR* ≤ −δ} (circular blocks, R4b's `gate_boot`) ≤ 0.10, with `p_ni = max(p at 10-session blocks, p at max(10, PW(d), PW(d²))-session blocks)`, 2,000 resamples, seed 11, Bonferroni × the configurations searched as recorded in each golden's source row; the point ΔSR ≥ −δ also at 2×;
- PC-4: on the §8.6 drawdown windows, ≥ 3 with a positive benefit vs S and none above 50% of the summed positive benefit;
- PC-5: ≥ 60% of calendar years positive; PC-6: ≥ 50% of the neighbouring cells (8 neighbours, one step on each declared axis) keep ≥ half of the centre's PC-1 improvement and the PC-3 point; PC-7: ≥ 30 de-clustered onsets for discrete rules, ≥ 5 §8.6 windows, ≥ 756 + 126 sessions;
- raw returns with cash at 0 (PX2's cash fixture FRED `IRSTCI01KRM156N` only for T-EXCESS-01 and I-09); v1.2 verdict order: sufficiency, REJECT, inconclusive, REVISE, PASS.

Reference mode: "`core/quant/backtest` may compute configurations the rules store refuses (a cap above 1, the DM gate at 0×, product stacks, the literal v1.2 ladder) only when called from `tests/reference/` or `docs/` with `reference_only=True`; `core/` cannot import that code. Such results never enter a book, a card or an artifact, and T-CAP-01 and T-DNB-01 apply to the rules store and the books, not to this mode." `reference_only` goldens: G-KR-06, G-MOM-07, the cap-1.5 variant of G-KR-L13, G-LAD-01, G-LAD-02, G-LAD-03 (L5992). M2 needs only the cap-above-1 path (G-KR-06); the others are M4/M5/M7.

The M2 goldens themselves (G-KR-01…04, 02b, 02c, G-US-01/01b) need only B.11 (Sharpe, MDD, windows, weights, shares); PC-1…PC-7 are exercised from M7 (G-KR-L*, I-07).

### B.13 TASK-M2-09 spike (§9.4 item 2, L5999)

Rerun on the 2-Oct official close and md5-freeze: cap-1.5 VT Sharpe 0.534 (G-KR-06), SMA60 0.550, EWMA (half-life 10) 0.607, EWMA at 35 bp 0.573, Korea stock-book 2× ΔSR −0.061. "They stay labelled pre-patch R4/R4b until then." "no number is invented in their place" (L5996). The sma60 reference line goes in `macro_state.extras` (L3549, L3630).

---

## C. Schemas and config this area reads or writes

Reads (rules store, M0 delivers; verbatim blocks in B): `overlay.*` (L4272-4280), `vol_target.{KR,US,other_markets}` (L4286-4293), `vol_target.annualisation_days`, `vol_target.sigma`, `vol_target.warmup`, `vol_target.display_labels`, `vol_target.logged_alt_estimators: [asymmetric_slow_cut_fast_restore]` (L4309-4315), `risk_layer.hedge_state`, `risk_layer.korea_covariance_extra`, `risk_layer.halt_scope`, `risk_layer.halted_triggers`, `risk_layer.never_halt_on` (L4353-4370), `data_contracts.on_failure.{acting_exposure, risk_model, risk_model_covariance, not_failures}` (L4230-4241), `data_contracts.roles` (L4244-4270), `data_contracts.cross_market` (L4242), `data.stale_carry_flag`, `data.monthly_lag_method`, `data.us10y`, `data.vintages: {source: alfred, store_first_release: true, store_latest: true}` (L4209-4224), `time.decision: close_t_earn_t_plus_1`, `time.decision_instant: close_print_bound_utc` (L4155-4157).

Fills (function outputs; the M6 builders write the artifacts):

`macro_state.vol` (L3548-3568) — required: `estimator` (enum `sma20, ewma094, ewma097, garch_t, gjr_t, log_har_range, comb`), `estimator_b5` (`PASS|FAIL|NOT_RUN`; M3), `estimator_gate {status, fallback_used, …}` (M3), `vt_status` (`ok|warmup|fail_closed`), `sigma_ann` (number|null, ≥ 0), `target_ann` (> 0), `vt_weight_next` ([0,1], specification book), `vt_weight_recommended_book` ([0,1]), `instrument_book`, `display_label_rel`, `label_method_rel`, `display_label_abs`, `label_method_abs`; optional `rebalance` (`daily|weekly|monthly`), `no_trade_band`, `alt_sigma_logged`.

`macro_state.flags` (L3569-3586) — M2 fills `hedge_credit_off`, `hedge_failure`, `classic_risk_off` (boolean, required), `hedge_reasons` (required array, enum above), `hedge_stale_inputs` ([string]), `fx_hedge_credit` (boolean|null).

`macro_state.inputs[]` item (L3632-3651): `name, series_id, source, channel, obs_date, session_date, obs_kind, value, value_status, dispute, available_at_utc, available_at_source, retrieved_at_utc, expected_available_utc, stale_deadline_utc, vintage, timing, role, books, status, content_hash`; `status` enum `ok, stale, stale_missed_release, missing, provisional_rejected, session_mismatch, synthetic_rejected, disputed, warmup`.

`macro_state.alerts[]` item (L3625-3629): `alert_id, code, severity (info|warn|page), component, series_id, books, first_seen_utc, count, escalated, ack_utc`.

`macro_state.concentration.by_book[book] = {composed, gross, binding_factor}` (L3601-3603): `composed` in [0,1] comes from `compose`; the rest is M5.

`overlay_decision` (L3717-3763), market-gross record: `family: "market_gross"`, `exposure_basis: "total"`, `vol_scale` (= vt, specification book), `vol_scale_recommended_book` ("= vol_scale if its card is PASS, else 1.0"), `multipliers[] {rule_id, value∈[0.5,1.0], exposure_basis, card}`, `ladder` (enum `[0.5, 1.0, null]`), `post_rearm_cap` (enum `[0.5, 1.0, null]`), `composition: "min"` (const), `overlay_min` ([0.5,1.0]), `overlay_floor: 0.5` (const), `overlay_cap: 1.0` (const), `overlay_applied_spec_book`, `overlay_applied_recommended_book` ([0.5,1.0]), `binding` ([string]), `reasons` ([string]).

Field classes (L3370): acting = every weight, multiplier and composition field, the rest of `vol`, `fail_closed`, `acting_exposure` inputs; display = hedge flags, `display_label_*`, `label_method_*`, `alt_sigma_logged`, `reasons`. An unclassified new field is acting (fails closed).

Rule-object predicates relevant here (§7.1, L4694-4697): `output_range` hi > 1.0, an overlay outside [0.5, 1.0], vt or vs outside [0, 1.0] → refused (items 2, 8); `exposure_basis` missing on an acting rule → refused; `composition` anything but `min` → refused (item 31); a vt rule `applies_to` anything but `market_gross` → refused.

Fixtures (proposed `tests/fixtures/macro/`, manifest `MANIFEST.csv`, §9.5 L6018): Yahoo `^KS11`, `^GSPC`, `SPY`, `KRW=X`, `^TNX`, `^RUT`; French daily files; the FRED snapshot of 2026-10-02; `QX_DLA_postpatch.csv`; the synthetic store fixture of T-PROV-01. Generated once at M1's exit by QUANTGEN's own data layer and md5-frozen (L5492).

---

## D. Tests

Tiers (L5496): `fast` (unit; ≤ 10 min total), `golden` (fixture reproductions; ≤ 2 h). Every row names its tier and `runs_from`. Hermetic: network patched to raise (T-HERM-01); tests write only to temporary copies of the rules store, ledgers and artifact directory (T-HERM-02). Tolerances, Level 1 (L5734-5735): Sharpe ±0.01; max DD ±1 pp; window returns ±1 pp; weights ±0.02; bootstrap shares ±0.03; p-values ±0.01 (p ≥ 0.05) / ±0.005 (p < 0.05); vol levels ±0.1 pp; other ratios ±0.01; prices exact; deterministic counts exact.

Feasibility classes: **SYNTH** = hermetic with synthetic/inline fixtures; **REFDATA** = needs frozen reference data not on this machine; **OWNER** = needs owner input / credentials / live sessions.

### D.1 Tests whose `runs_from` is M2

| ID (line) | Assertion (verbatim thresholds) | Fixture | Class |
|---|---|---|---|
| T-VT-01 (L5673) | (a) `< 20` valid returns → status `insufficient_history`; a book before its first ARMED decision maps it to weight 1.0, status `warmup`, "counted as no failure". (b) a flagged stale-carry day is excluded and the window extends. (c) σ̂ = 0 or not finite → `MissingInput`. (d) on a book that has been ARMED, a store truncated to 15 valid returns → `MissingInput("missing")`, counts toward the HALT limit, "never weight 1.0". (e) simple returns, ddof = 1. | synthetic PIT store (M1) | SYNTH |
| T-VT-01 golden clause | "reproduces rv20 28.82% and vt 0.694 on 2 Oct" (vol ±0.1 pp, weight ±0.02) | 21 KOSPI closes ending 2026-10-02 at 7,003.74 (`^KS11` / KRX official) | REFDATA. No local substitute (caches end 2026-09-23/25; `yf_069500.KS.csv` is KODEX 200, not KOSPI). Inline SYNTH identity available: `min(1, 0.20/0.2882) = 0.694`. |
| T-CAP-02 (L5627) | 10,000 seeded draws (seed 11): k ∈ {0,…,5}; overlays in [0.5, 1]^k (endpoints included); vt ∈ [0, 1] (0 and 1 included); ladder ∈ {1.0, 0.5}; post-re-arm cap ∈ {1.0, 0.5}: `composed = vt × min(1.0, overlays, ladder, post_rearm_cap)` and `composed ≥ 0.5 × vt`. "The floor applies to `composed`; a risk limit may take `gross` below it without HALTing. 0.75 and 0.5 compose to 0.5 (never 0.375), and the binding factor is logged. A product-composed path raises." | inline; force endpoint draws explicitly | SYNTH |
| T-LABEL-01 (L5643) | Both labels on date t use only σ̂ through t (relative: trailing 756 values; absolute: expanding history); never smoothed; boundary value takes the higher label; recomputing after appending future data changes no past label | inline σ̂ series | SYNTH |
| T-LABEL-01 golden clause | KOSPI 2026-10-02 = "elevated" (relative) and "stressed" (absolute); US 2026-10-01 = "normal" (relative) | `^KS11` full history (≥ 10 years) to 2026-10-02; US close history to 2026-10-01 | REFDATA. Smoke-only substitute: `yf_SPY.csv` (1995-01-03 → 2026-09-25), `yf_069500.KS.csv` (2007-01-29 → 2026-09-23); labels on those dates are not goldens. |
| T-CORR-01 (L5636) | date-aligned (r_eq(D), −Δy(D)) pairs reproduce **+0.53 at 2026-09-30 (± 0.01)**; "A series-lag implementation fails (it gives −0.094)" | S&P close + DGS10 through 2026-09-30 | REFDATA. Structural part SYNTH: on a constructed pair of series the date-aligned and leg-lagged implementations give different, known values. Smoke substitute: `yf_SPY.csv` vs `yf_TLT.csv` / `yf_ZN_F.csv` returns as a −Δy proxy to 2026-09-25 (not the golden; no DGS10 cached). |
| T-HEDGE-01 §9.1 (L5637) | a risk-model input that misses two expected releases → `hedge_credit_off = TRUE`, operator alert, never HALTs any book; `fx_hedge_credit` changes no exposure; core PCE read through `pit_value` at the decision's `knowledge_utc` from ALFRED vintages: replay after a later revision leaves `hedge_reasons` unchanged | synthetic store with a publication schedule and two vintages | SYNTH |
| T-HEDGE-01 R-19 table (L1968) | stale DTWEXBGS alone (context) changes no hedge flag; live USD proxy and DTWEXBGS both stale → `hedge_credit_off = TRUE`, no acting component of the KR or US books fails closed, `vt` unchanged | synthetic store | SYNTH (the built-`macro_state` assertion joins at M6, L5590) |
| §12 M2 line (L6364; §11 L6334-6336) | `hedge_credit_off = TRUE`, `hedge_reasons = [corr_positive, core_pce_ge_3]`, core PCE read as of its vintage at the decision; `hedge_failure` from `USD_LIVE_PROXY`'s 1-day change (FALSE) | PCEPILFE ALFRED vintages (3.008% Aug-2026), S&P, DGS10, `DX-Y.NYB` | REFDATA (none cached locally) |
| T-COST-01 (L5638) | turnover `|Δw|` charged at the pre-registered rate on the day the new weight earns; changing the rate in a card header raises | inline weights/returns; M0 cost table | SYNTH |
| T-COST-01 golden clause | R4b: KOSPI VT20 at 35 bp SR **0.609 ± 0.01**; US VT15 at 50 bp SR **0.505 ± 0.01** | `^KS11` 2016-01-04 → 2026-10-02; French Mkt-RF → 2026-08 + `^GSPC` Sep-2026 | REFDATA |
| G-KR-01 (L5770) | buy-and-hold Sharpe 0.637, max DD −43.9% | `^KS11` 2016-01-04 → 2026-10-02 (post-patch close) | REFDATA |
| G-KR-02 (L5771) | VT20 gross 0.641 / −36.8%; 2016–25 0.457 vs 0.534; 2018–24 −0.052 vs 0.071; 3 bp 0.638 / −36.8%; 35 bp 0.609 / −37.2%, 2016–25 0.428, 2018–24 −0.083; 2× 0.635 / −36.9% and 0.576 / −37.5% | same | REFDATA |
| G-KR-02b (L5772) | ΔSR vs B&H (share), 2016–26 / 2016–25 / 2018–24: gross +0.004 (0.45) / −0.077 (0.06) / −0.123 (0.03); 3 bp +0.001 (0.44) / −0.079 (0.05) / −0.125 (0.03); 35 bp −0.029 (0.36) / −0.106 (0.02) / −0.154 (0.01); 2× −0.001 at 6 bp. The 70 bp value −0.061 (0.28) is **pre-patch R4b**: not asserted until §9.4 item 2 is frozen | same; research bootstrap | REFDATA |
| G-KR-02c (L5773) | static book at 0.925: max DD −41.3%; ΔMDD of VT20 +4.5 pp gross; +4.4 (3 bp); +4.1 (35 bp); +4.4 / +3.8 pp at 2× | same | REFDATA |
| G-KR-03 (L5774) | gross vt vs B&H: Jul-2026 crash −12.2% vs −38.6%; Mar-2026 −7.9% vs −19.9%; Aug-2024 −7.9% vs −5.5%; Apr-2025 −11.7% vs −12.0%; 2020 crash −25.8% vs −34.1%; 2020 rebound +25.9% vs +49.9%; H1-2026 +51.7% vs +101.1%; 30 Jul → 30 Sep 2026 +5.9% vs +22.2%. 3 bp: −12.3%; −7.9%; −7.9%; 2020 crash −25.8%; H1-2026 +51.6%. 35 bp: −12.3%; −8.0%; −8.0%; Apr-2025 −11.8%; −26.0%; +25.4%; +50.5%; post-crash +5.6% | same; window dates §8.6 (below) | REFDATA |
| G-KR-04 (L5775) | weights 22 Jun 2026 0.30; 23 Jun 0.33; 30 Jul 0.25; earning on 2 Oct 0.61; decided at the 2 Oct close 0.69 (0.694; rv20 28.8%) | same | REFDATA (convention: F-15) |
| G-US-01 (L5786) | B&H 0.534 / −59.2% vs VT15 0.602 / −49.9% gross; 50 bp 0.505 / −53.8%, ΔSR −0.028 (0.29); 100 bp 0.409 / −57.3%, ΔSR −0.125 (0.03) | French Mkt-RF + `^GSPC` Sep-2026, 1990-02-01 → 2026-09-30 | REFDATA |
| G-US-01b (L5787) | static book at 0.890: max DD −54.0%; ΔMDD +4.1 pp gross / +0.2 pp (50 bp) / −3.4 pp (100 bp) | same | REFDATA |
| G-US-01c (L5788, L5593) | EWMA(0.94) Sharpe 0.605 / 0.520 / 0.434 — the whole row is the challenger, which joins at **M3** | — | deferred; nothing asserted at M2 (F-18) |
| I-02 (L5689) | Korea vt weights and window returns over 2024-07-31 → 2024-08-09 and 2026-06-22 → 2026-07-30 match G-KR-03 and G-KR-04, gross and net | `^KS11` | REFDATA |
| G-KR-06 (L5778) | reference mode: cap-1.5 VT Sharpe 0.534, max DD −46.2% (**pre-patch R4**) — joins M2 exit "only once §9.4 item 2's rerun is md5-frozen" | `^KS11`; TASK-M2-09 | REFDATA; value is replaced by the frozen rerun, never invented |

Window return-date rules for G-KR-03 / I-02 (L5116-5142): default "returns after the start close". Four KOSPI windows include the start-date return: Aug-2024 uses returns dated 2024-07-31 → 2024-08-09; Apr-2025 2025-03-28 → 2025-04-09; Mar-2026 2026-02-27 → 2026-03-31; H1-2026 2026-01-02 → 2026-06-30. Jul-2026: 2026-06-22 → 2026-07-30. 2020 crash (KOSPI): 2020-02-19 → 2020-03-19; 2020 rebound (KOSPI): from 2020-03-19 → 2020-06-08. "Under the strict reading … H1-2026 would read +96.7% instead of +101.1%, and Aug-2024 −6.6% instead of −5.5%."

Local cross-check (not a fixture): `QUANTGEN_techfund_research_bundle/QUANTGEN_techfund_research/datalab/results/r2_idx/r2_idx_golden_values.csv` holds an independent pre-patch reproduction ("ours" vs "spec": VT20 Sharpe 0.6329 vs 0.638; B&H 0.6284 vs 0.634; VT20 MDD −0.36995; avg exposure 0.9255; S MDD −0.4145; window returns; weights 0.3025 / 0.3310 / 0.2485). It carries result values only, no price series.

### D.2 Clauses that join at M2 from earlier tests (§9.0b, L5567-5595)

| Test | Clause joining at M2 | Assertion | Class |
|---|---|---|---|
| T-CAP-01 (L5570, L5626) | "The overlay layer cannot emit 0." | `apply_overlays` / `compose` reject a 0 (or any value < 0.5) overlay multiplier; 0× only via risk layer / HALTED | SYNTH |
| T-FIX-01 / G-POST-01 (L5573, L5823-5827, L5836-5840) | rows rv20 **28.8%** (28.82%), vt **0.694**, G-KR-01 **0.637**, G-KR-02 **0.641 / 0.638 / 0.609 / 0.635 / 0.576**, G-KR-02b at 35 bp **−0.029 (0.36)**; "unchanged" items: weights 22 Jun / 23 Jun / 30 Jul (0.30 / 0.33 / 0.25) and earning on 2 Oct (0.61), relative label "elevated" (quartiles 15.7 / 18.55 / 33.6%; 70th percentile) and rv21 31.9% at the 73rd percentile, turnover 1.50, G-KR-02c, G-KR-02b gross and at 3 bp | `QX_DLA_postpatch.csv`, `^KS11` | REFDATA |
| T-ROLE-01 (L5578, L1964) | risk-model clause; "sets every risk-model default": stale risk-model input → `hedge_credit_off = TRUE`, alert, operator escalation after 2 missed releases, never HALTED however long; unreadable publication calendar sets every risk-model default | synthetic store | SYNTH |
| T-ROLE-02 (L5579, L1969) | "sets `hedge_credit_off` through its corr63 binding": the S&P close failing on 3 decisions sets `hedge_credit_off` and HALTs no recommended book | synthetic store | SYNTH |
| T-LAG-02 (L5583, L5610) | "Re-running a rule with the input deliberately shifted one period *earlier* … must change the result and trip T-LAG-01" — on R-06's vt | synthetic store + M1 lag audit | SYNTH |
| T-MISS-02 (L5585, L5625) | risk_model clause; exception in `hedge_state` → `hedge_credit_off = TRUE`, alert, never HALTED; exception in `market_vol_target` / `compose` → HALTED (OPS) for the books it feeds | M1 runtime (temp state) | SYNTH |

### D.3 Clauses of M2 tests deferred to later milestones (do not block M2)

| Test | Clause | Joins |
|---|---|---|
| T-CAP-02 | "The stack card prints the share of days at ≤ 0.25× total exposure and the rebound capture" (L5552) | M7 |
| T-HEDGE-01 (R-19 table) | the assertion on a built `macro_state` (L5590) | M6 |
| T-COST-01 | "both legs for L/S sleeves" (L5591) | M4 |
| T-COST-01 | "a 2× run exists for every card" (L5592) | M7 |
| G-US-01c | the EWMA(0.94) challenger (L5593) | M3 |
| T-MISS-02 | exceptions in `concentration_bound` and `drawdown_ladder` (L5586) | M5 |
| T-LAG-02 | the `timing_probe` clause (L5584) | M7 |
| G-POST-01 | R-06 KR 3 bp p_ni and 35 bp ΔSR rows (v1.2-check mode) (L5576) | M7 after the freeze |
| T-MONO-01 | no reallocation (L5676) | M5 |

---

## E. Interfaces

### E.1 Needed from earlier milestones

| From | Name / shape | Used for |
|---|---|---|
| M0 (TASK-M0-04) | rules-store loader for the §7 blocks; validation refusing `overlay.combine ≠ min`, `output_range` hi > 1.0, overlay outside [0.5, 1.0] (T-CAP-01) | B.3, B.6, B.7 |
| M0 (TASK-M0-12) | pre-registered cost table with tick floor; header validation that raises on a rate change | B.11, T-COST-01 |
| M0 | artifact schemas 2.0 (`macro_state`, `overlay_decision`), governance-event appender, alert sink | C |
| M1 (TASK-M1-10) | `pit_value(series_id, decision_utc, knowledge_utc, consumer, require_session=None) -> PITValue | MissingInput`; `PITValue`, `MissingInput` dataclasses (L967-999) | all reads |
| M1 (TASK-M1-13) | derived / monthly PIT records with calendar-offset arithmetic; ALFRED vintages (`vintage`, `first_release`, `revised`) | core PCE YoY |
| M1 (TASK-M1-17) | `is_stale(series_id, decision_utc, knowledge_utc) -> Fresh | Stale("missing") | Stale("missed_release")`; role-based failure actions; per-book input and book counters; binding lookup returning `(role, books)` per `(series, consumer)` | B.4, B.8 |
| M1 (TASK-M1-20) | per-book runtime: `runtime_halt(book_id, cls: "RISK"|"OPS", reason)`, `runtime_rearm`, states `DISARMED|ARMED|HALTED`, book ids `recommended:<market>`, `specification:<market>`, … (L1081-1086, L1180) | B.10 |
| M1 (R-20) | `close_print_bound_utc(market, session_date)`, `decision_time_utc`, session iteration (`is_session`, `session`), `usable_at(series_id, obs_date, market)`, `publication_instant`, `next_expected_obs`, `add_publication_bdays` | B.3, B.8 |
| M1 (R-01) | `LookAheadError` and the lag audit (T-LAG-01) | T-LAG-02 |
| M1 (TASK-M1-22) | md5-frozen golden fixtures under `tests/fixtures/macro/` | D.1 goldens |

Gaps the M1 owner must close for M2 (not named in §3.5):
1. A query "has this book ever been ARMED" (B.4 needs `ever_armed`).
2. How a flagged stale-carry session is exposed: `PITValue` has no stale-carry field and T-BAR-01 says such a row "is never stored as a close" (L5614), yet R-06 must tell a flagged stale-carry session (skip, extend) from a missing close (fail closed). Proposed: `is_stale_carry(series_id, session_date, knowledge_utc) -> bool`.
3. A count of missed releases for a series (the escalation at 2): `is_stale` returns only `Stale("missed_release")`.
4. A batched PIT window read (776+ closes for the relative label; full history for the absolute label); otherwise `pit_value` is looped per session.
5. The previous decision's component state (previous vt per book) from `core/engine/state` for fail-closed carry.

### E.2 Exposed to later milestones

| To | Name | Shape |
|---|---|---|
| M3 (R-30) | `sma_vol`; `market_vol_target(..., estimator=…)` dispatch point; costed engine and research bootstrap | SMA20 is the fallback target of `fallback_to_sma20`; `ewma094` joins G-US-01c |
| M4 | `apply_overlays`, `compose`; reference mode (G-MOM-07) | family-level `min()`; `sleeve_vol_scale` uses the same warm-up mapping ("mapped per book as above", L1050) |
| M5 | `compose(vt, overlays, ladder, post_rearm_cap)`; `ComposeResult.binding`; `guard_acting` | `gross = min(composed, bound)`; ladder and `post_rearm_cap` arguments ∈ {1.0, 0.5}; T-MONO-01 |
| M6 | `VTResult`, `BookVT`, `HedgeState`, label functions, `korea_covariance` status | `build_macro_state`, `build_overlay_decisions` (fields in C) |
| M7 | `costed_book`, `research_bootstrap_share`, `static_comparator`, v1.2-check mode, `vt_weights` | cards, G-KR-L*, stack card |
| M8 | `verify_composition` | `bounds_ok` gate recomputation (L1222-1223); workflow step `macro.vol_and_overlays` (L1218) |

---

## F. Ambiguities, contradictions and conservative-reading decisions

| # | Issue (lines) | Conservative reading adopted |
|---|---|---|
| F-1 | Return type: §3.5 annotates `-> VTResult` (L1044) but the comment and T-VT-01 say degenerate σ̂ "returns `MissingInput`" (L1047, L5673). | Return `VTResult | MissingInput`. |
| F-2 | Stale-carry exclusion (L1561) does not say how the next return is formed. | Drop the return dated on the flagged session; compute the next return against the last valid close. |
| F-3 | An unflagged gap (session with no close row) inside the 20-return window: skip or fail? Silent. | Fail closed: `MissingInput("missing")`; only store-flagged stale-carry sessions are skipped. |
| F-4 | T-BAR-01 says a flat-OHLC zero-volume row "is never stored as a close" (L5614) while R-06 needs the flag to be visible (L1561). | M1 must expose the flag (E.1 gap 2); until then every gap is F-3. |
| F-5 | `MissingInput.reason` for degenerate σ̂ is not named; the enum has no dedicated member (L993). | `"missing"` (R-19: "A contract violation is treated as a missing input", L1882). |
| F-6 | Degenerate σ̂ before a book's first ARMED decision: warm-up covers only `insufficient_history`. | `MissingInput` regardless of armed state; the book does not ARM. |
| F-7 | Markets other than KR/US have `target_ann: null`; "default, judgment: start from the market's long-run median realised vol" (L1563). | Raise without a pre-registered card target; never derive a default in code. |
| F-8 | Which series feeds the displayed US vt (§11: vt_US = 1.00, rv20 10.7%) while D5 = none: `US_SLEEVE_OFFICIAL_CLOSE` (books `[]`) or `SPX_OFFICIAL_CLOSE` (no R-06 binding)? | `US_SLEEVE_OFFICIAL_CLOSE`, consumer `R-06`, books `[]`: a failure HALTs nothing. |
| F-9 | Binding factor destination: §3.3 says `overlay_decision.reasons` (L897); P2 says `binding` (L511); schema has both (L3751-3752). | Write the factor id to `binding` and a readable line to `reasons`. |
| F-10 | Ties at the minimum (e.g. an overlay 0.5 and the ladder 0.5) and vt as a "binding factor" are unspecified. | `binding` lists every factor equal to `overlay_min` when `overlay_min < 1.0`; vt is never a binding factor (it is outside `min()`). |
| F-11 | Quartile method (interpolation), whether the trailing 756 window includes σ̂(t), and labels with fewer than 756 values or less than 10 years are unspecified; schema makes both labels required non-null (L3562-3568). | Window includes t; numpy linear quantiles; return `None` when the history is too short (display field: the builder records `extras.validation_errors`, never a HALT, L3370). `min_years: 10` measured in calendar years from the first σ̂ date. Golden quartiles 15.7 / 18.55 / 33.6% check the method once the fixture exists. |
| F-12 | "Per-label coverage is reported" (L1565) names SMA20-FHS VaR, whose harness is M3; no M2 test covers it. | M2 exposes the label series only; the coverage table is produced with the M3 harness. |
| F-13 | corr63 date alignment when one leg has no observation (bond-market holiday with NYSE open); changes across the gap. | Inner-join the two series on dates ≤ the last usable 10y date; both legs' changes are taken over the same consecutive joined dates. |
| F-14 | The lag used by the "series-lag implementation" that gives −0.094 is not stated in the read ranges (L1615, L5636). | Negative control lives in the test only: the 10y leg shifted by its strict H.15 lag against unshifted equity returns; asserted on the frozen fixture (REFDATA). |
| F-15 | G-KR-04's "22 Jun 0.30; 23 Jun 0.33; 30 Jul 0.25" do not say "earning on" or "decided at" (L5775). I-01 reads 30 Jul as the decision's vt (L5688); the tech-fund reproduction labels all three "weight earning on" (`r2_idx_golden_values.csv`). 22 vs 23 Jun differ by 0.03 > the ±0.02 tolerance. | Do not hard-code a convention; resolve against the frozen `^KS11` fixture and record which one reproduces all three; until then the rows are not asserted. |
| F-16 | `hedge_failure` "week" (L1613): calendar week or rolling 5 sessions; `USD_proxy_1d` alignment for a KR decision (latest usable US close is dated ≤ K−1). | Rolling 5 US sessions ending at the last usable US close (equals the Fri→Fri week on a full-week Friday); both daily legs are taken on the same US session D (date-aligned, as corr63). |
| F-17 | `hedge_failure` when `USD_LIVE_PROXY` is stale: config sets only `hedge_credit_off` (L4233); the flag is a required boolean. | `hedge_failure = False` (no event fabricated), the proxy listed in `hedge_stale_inputs`, and `apply_hedge_state` also removes USD/JPY-hedge credit while the proxy is stale (no credit = fail closed; no exposure effect). |
| F-18 | G-US-01c is listed at M2 (L5552) but its only content is the EWMA(0.94) challenger deferred to M3 (L5593). | Registered at M2 as a row with nothing asserted; asserted from M3. |
| F-19 | Exception in an acting risk-layer function = immediate OPS HALT (L1178, L5625) vs an acting workflow-step error = counter +1 and HALT at the limit (`run_error`, L1240-1244, T-OBS-04 L5680). | M2: immediate OPS HALT with reason `acting_risk_layer_exception` for the four named functions; the step-level counter is M8's. |
| F-20 | Reference mode "`core/quant/backtest` may compute … `core/` cannot import that code" (L5992). | The cap assertion lives in `core/quant/backtest.vt_weights` and is lifted only by `reference_only=True`; a static test asserts no `core/` module passes `reference_only=True`; reference entry points live in `tests/reference/`. |
| F-21 | Spec targets "`core/quant/risk` (exists: risk.py)"; that file is the 170-line statistics module (log-return based) that M3-M5 also extend. | Add `core/quant/risk_layer.py` and re-export its public names from `core/quant/risk.py` so `core.quant.risk.market_vol_target` resolves (L963 permits renaming). |
| F-22 | Sample boundaries of "2016–25" and "2018–24", whether the 2016-01-04 start uses pre-sample closes for the first σ̂, Sharpe ddof, and the RNG of the research bootstrap are not stated; the R4/R4b scripts are not on this machine. | Calendar-year boundaries; weights start once 20 in-sample returns exist; ddof 1; `np.random.default_rng(20261002)` with paired block indices; share = fraction of resamples with ΔSR > 0 (L6060). All inside Level-1 tolerance per the tech-fund cross-check; confirm on the fixture. |
| F-23 | "Treat Korea gross as semiconductor exposure in the covariance" (L1585) gives no formula. | Risk-model/display only: `SOX_CLOSE` is a series of the Korea covariance and the Korea line is classed under semiconductors in the displayed risk; no weight changes. |
| F-24 | `max(corr, 0)` on selected pairs can make the correlation matrix non-PSD; spec silent. | Clip negative eigenvalues to 0 and rescale to unit diagonal; label the matrix "hedge-adjusted" in the displayed risk. |
| F-25 | Alert `code` strings and the escalation encoding are not enumerated (L3625-3629). | Proposed, non-binding: `RISK_MODEL_INPUT_STALE` (severity `warn`; `escalated: true`, severity `page` after 2 missed releases), `HEDGE_STATE_EXCEPTION` (`warn`), `ACTING_RISK_LAYER_EXCEPTION` (`page`). |
| F-26 | Co-occurring reasons when an input is stale but its last visible value still crosses a threshold. | Evaluate each cause on the latest PIT-visible value and add `risk_model_input_stale`; `hedge_credit_off` is True either way. |
| F-27 | `classic_risk_off` uses `UST10_1d < 0` (L1613) without saying yield change or price return. | 10y yield change (Δy < 0, a bond rally), matching "the 10y change" input (L1612). |
| F-28 | `fx_hedge_credit` week anchor when Friday is not a KRX session; ΔUSD/KRW as simple or log change. | Last KRX session of the week; simple change. Display only. |
| F-30 | `fx_hedge_credit` reads weekly KOSPI closes and the ECOS USD/KRW close, but `data_contracts.roles` gives no binding for that consumer: `KOSPI_OFFICIAL_CLOSE` is bound `acting_exposure` (L4246) and `ECOS_1530_CLOSE` only to `R-11_refusal_book` and `nav_fx_backtests` (L4267); `pit_value` raises for a non-context consumer without a binding (L1891). R-09's Inputs row does not list USD/KRW (L1612); §4.2 gives it role C for this display (L1414). | Read both with a `context` consumer. A stale or missing value gives `fx_hedge_credit = None` and a stale label; it never sets `hedge_credit_off`, never increments an acting counter and never HALTs. |
| F-29 | `.v1.2_INTEGRATION_backup.md` §8.7 (source of v1.2 PC-1…PC-7) is not on this machine. | Implement v1.2-check mode from §9.3.3's statement (B.12); details it omits (PW block estimator, tail-exposure ratio definition) stay unverified until the file or the R4b scripts are supplied; no M2 exit test depends on them. |

---

## G. DO-NOT-BUILD items and invariants that bind this area

DO-NOT-BUILD (§10; rules-store validation refuses each shape, L6233-6250):
- Item 2 (`harm · B`): any multiplier above 1.0, including vol-target caps above 1; "cap 1.0 is permanent (R-06)" (L6077). Check: T-CAP-01.
- Item 31 (`harm · G`): product-composed de-risk stacks; "A product of de-risk multipliers is refused" (L6206-6210). Check: T-CAP-02.
- Item 30 (`harm · B`): `max(σ̂_SMA20, implied)` sizing (L6201-6205).
- Item 25 (`harm · G`): any model as the sizing estimator except through R-30 as a counted card revision (L6176).
- Item 24 (`harm · G`): smoothed or forward-looking calm / normal / elevated / stressed labels, or those labels used as gates (L6175).
- Item 28 (`null · E`): a Mondrian conformal label layer on the display labels (L6199).
- Item 27: a regime-model state, acting or displayed (P19); the σ̂ labels are volatility labels and stay (L6257).
- Item 15 (`inconclusive · E`): "USD down and equities down" as an equity de-risk trigger (L6144) — `hedge_failure` never touches equity gross.
- Item 17: a 200-day-average conjunction on the vol target (L6146).
- Items 23, 32, 33: lowering a pre-registered cost; a venue switch after results; a stock book as a market-gross scalar — the KRX stock book (35 bp) line is "computed for reference only" (L1564).
- Item 21: any order, cancel, withdrawal, deposit-address or transfer path (P0).
- Item 5 / P4: Korea gates built from US or global inputs.

Invariants (checked in every change, L78-87):
1. No multiplier or weight above 1.0. Overlays in [0.5, 1.0]; vt and vs in [0, 1.0]. `composed(m) = vt × min(1.0, overlay₁, …, overlayₖ, ladder, post_rearm_cap)`, never a product; outside HALTED `composed(m) ≥ 0.5 × vt`; the floor assertion is on `composed(m)`, never on gross or final weights (L80).
2. 0× comes only from the risk layer and a book's HALTED state; the overlay layer never emits below 0.5 (L514-517).
3. vt has no floor ("a floor would undo the crash protection: the Korea weight was 0.30–0.33 on 22–23 Jun 2026", L512).
4. Every acting input is read through `pit_value` with `available_at_utc ≤ decision_utc`; a close-type acting input needs `value_status = official_close` for the decided session; no synthetic, provisional, bar-derived or stale acting input (L81).
5. HALTED is per book; only an `acting_exposure` input bound to a book can HALT it. A stale or failing `risk_model` input, or an exception inside `hedge_state`, sets `hedge_credit_off = TRUE` and never HALTs (L82).
6. Warm-up (before a book's first ARMED decision) and disputes are not failures; after ARMED a shortfall is `MissingInput("missing")` (L1111).
7. No lowering of costs; every result also at 2× (L85).
8. The hedge state changes no equity gross in any case; `fx_hedge_credit` and both labels are display only.
9. No test computes a real card's verdict before the M7 freeze (L5546); v1.2-check mode and reference mode never yield a verdict and never enter a book, card or artifact (L5984, L5992).
10. Tests are hermetic and write no production state (T-HERM-01/02); golden values come from frozen post-close fixtures only (T-FIX-01); a pre-patch value keeps its label and is never replaced by an invented number (L5996).
11. Read-only: nothing in this area may contain or import an order path (P0, T-RO-01).
