# spec_constitution — the QUANTGEN v2.0 constitution (read first)

Source: `QUANTGEN_Quant_Council_2026-10-03/claude_code/QUANTGEN_MACRO_INTEGRATION.md` (spec, "L" = line number). Ranges read in full: L14-100 (Quick start), L339-486 (§0), L487-659 (§1 P0–P19), L6039-6263 (§10), L6264-6375 (§11, §12). Cited from elsewhere: §3.3 L850-898, §3.6 L1115-1163, §3.8 L1173-1187, §5 preamble + R-01/R-02 L1453-1508, R-32/R-33 L3361-3393, §6 conventions L3501-3512, §6.6 L4094-4119, §7 L4123-4165 and L4608-4684, §7.1 L4687-4705, §8.1.2 L4781-4797, §8.1.3 L4799-4838, §8.2/§8.3 L4840-4870, §8.10 L5441-5487, §9 L5489-5706, §9.5 L6016-6035. Repo facts checked 2026-10-05 against `C:/Users/whydi/OneDrive/Desktop/QUANTGEN` (section B.12).

Rule of precedence (L89): field names, parameters, bounds, formulas, test thresholds and the council wording quoted in §5 are BINDING. Paths/function names marked "proposed" may be renamed. Evidence numbers are informative unless a §9 test or §9.3 golden cites them. Where the spec is silent: **no exposure change, specification book only, fail closed**. "Any code that violates [§1, §10] is wrong even if a test passes" (L18). Where §7 and a rule differ, the rule governs (L4132); where §6 and a rule's Outputs list differ, the rule governs (L3503); where Quick start/§12 and §9.0a/§9.0b differ on exit tests, §9.0a/§9.0b govern (L5546).

---

## A. Scope

No task file is assigned to this brief. It is cross-cutting; the tasks of `QUANTGEN_V2_TASKS.json` that materialise it are below (all M0). Every other task in M0–M10 is bound by sections B.1–B.8 and G.

| Task id | One-line deliverable | Target files (E = exists, N = new/proposed) |
|---|---|---|
| TASK-M0-01 | Static read-only scan (T-RO-01); `read_only: true` on every artifact writer | E `tests/acceptance.py:169` (`test_08_no_broker_order_path`), E `tests/expansion_acceptance.py:155` (extend, do not duplicate); N `tests/macro_acceptance.py` registered in E `tests/run_all.py` as group `macro/` |
| TASK-M0-04 | §7.1 rule-object model + validation predicates + R-02 bounds (T-CAP-01, T-BASIS-01) | N `core/rules/macro_rules.py` (frozen dataclasses + `validate_rule_object`); reuse `Issue`/`Report`/`Severity` from E `core/rules/validation.py`. E `core/rules/model.py`/`store.py` model operator ORDER rules — do not overload them |
| TASK-M0-05 | v2.0.0 rules-store entries of §7 written with explicit numbers; `macro_artifact_dir()` | N `core/rules/macro_rules_v2.json` (shipped default) + runtime copy under E `config.trading_dir()`; E `config.py` |
| TASK-M0-06 | Owner-decision registry D1–D6 with `{ref}` resolution (T-OWNER-01) | N in `core/rules/macro_rules.py` (`load_macro_store`, `set_owner_decision`) |
| TASK-M0-07 | Hash-chained `governance_events.jsonl` appender + verifier (§6.6) | N `core/rules/governance.py` |
| TASK-M0-14 | DO-NOT-BUILD v2 predicates in rules-store validation (T-DNB-01) | N in `core/rules/macro_rules.py` (`dnb_violations`) |
| TASK-M0-15 | Replace §10 E labels by bootstrapped B labels (§9.4 item 7) | REFDATA — scripts/data under `/home/claude/quantgen_macro_data/` absent; leave labels as shipped; record "pending" |
| (every PR) | The nine PR invariants of B.8 | all packages |

File names are this brief's proposal; the spec's own paths (`core/rules/validation`, `core/calendars/data/`, `core/skills/workflows/macro_daily.yaml`) collide with real modules — see F-1..F-4.

---

## B. Build spec

### B.1 Principles P0–P19 and their enforceable consequence (L487-656)

"Enforced in code, as assertions, schema bounds and rules-store validation, not by convention" (L489). A request to change one is a principle change → owner (only D3 open).

| P | Binding statement (verbatim essentials) | Enforceable consequence (what code must do) | Tests |
|---|---|---|---|
| **P0** Read-only by construction (L491-500) | No module may "contain, import or call an order, cancel, withdrawal, deposit-address or transfer path on any venue". KIS = read-only quotations only. Every output is one of: an artifact (§6); an entry in the simulated order book of `core/engine`; a costed backtest or forward-simulated book; a model card; a displayed exposure recommendation. A displayed recommendation only from PASS cards (P7) | Static repo scan (forbidden symbols + AST patterns listed in the test); KIS client accepts only an allowlist of quotation endpoints frozen in `config.py`, any other path raises before a request is built; every artifact has `read_only: true`; no artifact contains an order instruction (L3511) | T-RO-01, T-RO-02 |
| **P1** Macro scales risk; never direction (L502-506) | No macro/overlay module may "create, flip or close a simulated position on its own". Overlays output multipliers only. Every acting rule states a second-moment mechanism on its card. A stress-variable level as a mean gate = principle change (D3) | Overlay functions return floats in the P2 ranges only; card header `claim` required; "A Sharpe or predictability claim on a protective rule is refused" (L4851) | T-CARD-01, T-MONO-01 |
| **P2** Bounded multipliers, composed by `min()` (L508-518) | Overlay multipliers ∈ **[0.5, 1.0]**. vt, vs ∈ **[0, 1.0]** (no floor). `composed(m) = vt × min(1.0, overlay₁, …, overlayₖ, ladder, post_rearm_cap)`. Outside HALTED `composed(m) ≥ 0.5 × vt`. Floor binds `composed(m)`, not `gross(m)`/final weights. "No multiplier anywhere may exceed 1.0" (Tier C). "0× comes only from the risk layer": backtests = `core/quant/risk` limits + hard stop; simulated book = that book's HALTED. "The overlay can never output a value below 0.5." Vol-target cap 1.0 is permanent | `assert 0.5 <= overlay <= 1.0`, `assert 0.0 <= vt <= 1.0`, `assert 0.0 <= vs <= 1.0` at schema, rules-store AND code level (L1506); a product-composed path raises; `bounds_ok` recomputes `composed` from recorded factors (L881); `output_range.hi > 1.0` refused | T-CAP-01, T-CAP-02 |
| **P3** Stress variables feed sizing, annotations, event blocks; never means (L520-528) | VIX term structure, credit, oil, EPU, USD-down-with-equities enter only via: the staged estimator gate (R-30; implied vol only inside HAR-IV if it wins); execution-state annotations (R-08, change no weight); new-entry blocks for scheduled events (R-10); the event calendar; Monte Carlo scenarios and replays (R-16). Never mean gates, never cut-and-re-add triggers on existing exposure. `max(SMA20, implied)` retired | DNB shapes 30, 4; book builder asserts no weight changes on an R-08 flag day; `families.reversal.calm_state_downweight: not_adopted` (D3) | T-ANNOT-01, T-DNB-01, I-06 |
| **P4** Korea's risk inputs are local (L530-534) | Korea gross driven by KOSPI's own vol, concentration and (later) leverage state. US/global macro states never gate Korea gross. US overnight info enters only as opening-gap and volatility input. KOSPI trend state = context only | No rule object with `market: KR`, `applies_to: market_gross` may bind a non-Korean series as `acting_exposure`; R-28 with `market: KR` refused (item 37) | T-DNB-01, T-TZ-01 |
| **P5** Point-in-time; decide at close t, earn t+1 (L536-550) | Every datum carries UTC obs timestamp, `available_at`, `retrieved_at`, `value_status`. `decision_utc` = official close from effective-dated calendar: KRX since 2015-06-15 = scheduled close + 30 s (**06:00:30Z** through 2016-07-29, **06:30:30Z** from 2016-08-01, CSAT close + 30 s on CSAT days); before 2015-06-15 scheduled close + 30 s print tolerance; NYSE scheduled close + 30 s (DST-aware). Availability rule: `available_at_utc ≤ decision_utc`. Value-status rule: close-type acting input needs `value_status = official_close` and `session_date` = decided session; a provisional intraday row is a missing input even if its `available_at_utc` precedes the decision. Lags calendar-based, never positional. Missing/stale/provisional/synthetic fail closed by role. "Nothing is ever silently interpolated." No synthetic data for acting inputs. Vintages + first prints stored; every series named | All acting reads through `pit_value` (other brief); lag audit raises `LookAheadError`; `MissingInput` statuses (`missing`, `provisional_intraday`, `session_mismatch`, `synthetic_rejected`); single exception = R-34 `timing_probe` sandbox rows tagged `synthetic_lookahead = true`, never write a production artifact, never feed a verdict | T-PROV-01, T-LAG-01/02, T-SYN-01, T-MISS-01/02, T-CLOSE-01/02, T-SER-01 |
| **P6** Thresholds on changes or percentiles (L552-554) | "never on levels calibrated to today" | Code review; no rule-object threshold on an absolute level of a stress variable (design prohibition, items 6/10) | — |
| **P7** The gate decides (L556-566) | Every exposure-changing overlay is a model card through the nine-step gate; protective rules use CARD-P. Only PASS cards feed the displayed recommendation (CARD-O PASS as recommendation; CARD-P PASS as insurance = BUILD-AS-INSURANCE). FORWARD-SIM (R-28, R-29), specification-only (R-04; ladder steps with binding share > 0.10 until R-31 passes), refusal books (R-11, R-12) stay out. "a rejected card is not deleted" | Recommended-book builder assertion; `verdict_filter`; `displayed_as ∈ {recommendation, insurance}` iff verdict = PASS | I-03, T-CARD-01, T-CARD-03, I-01 |
| **P8** Every multiplier declares its exposure basis (L568-571) | `active` = scales a family's long/short or benchmark-relative risk; `total` = scales the market book's gross long exposure | `exposure_basis ∈ {active, total}` required on every multiplier record; missing on an acting rule → refused; vt only on `market_gross`; no multiplier on `ts_trend` | T-BASIS-01 |
| **P9** Slow macro is context (L573-577) | Sahm, curve, probit, Taylor residuals, real yields, term premium, breakevens, credit levels, surveys, Street/Fed projections, every non-acting indicator of the 18-indicator sheet, leverage/flow monitors, VRP, live implied-vol snapshots, turbulence: "logged daily and never act". Acting on any needs a new card | No acting module imports or reads `context_log`, the sheet values, the R-18 break log or a refusal book (static import check + runtime guard) | T-CTX-01/02 |
| **P10** Pre-registered costs, with a floor (L579-603) | Per side / 2×: KRX ETF 3/6 bp; KRX stock 35/70; US shares via KIS 50/100; Crypto 10/20; Futures 5/10; FX 10/20. "Costs are defined once, in the gate's code. This spec reads them from there and never redefines them." Tick floor: `cost_side = max(table rate, commission + ½·tick/price + tax_side)` — only raises. Example: 252670 at ₩69 ≥ 72 bp per side. Card declares instrument book, notional NAV, rebalance rule, no-trade band in header. Futures line only if one contract ≤ ~5% of declared notional (mini KOSPI200 ≈ ₩56m; Micro ES ≈ ₩52m). Market-gross scalar never on a stock book. Different instrument book = new card. "Lowering a cost is never a permitted fix." 50 bp US rate valid for single names only | Cost read from one table (see F-5); lowering a cost in a header raises; every result also run at 2×; header-field validation; non-gating printed lines: stress-cost line, futures roll-cost line, turnover by regime | T-COST-01/02/03, T-BOOK-01 |
| **P11** One gate package, adopted once and blind (L605-609) | R-21–R-24 + R-34 fixed for every card before the first formal run; acceptance results md5-frozen with package version. No gate rule/threshold/convention chosen after seeing the card it decides; a change = new package version applied to every card with flips disclosed. No pooled/A-provisional route for a card already run | `gate.package = {version: "2.0.0", definitions_md5, acceptance_report_md5, frozen_utc}`; card study re-hashes the manifest at every run and refuses on mismatch; no test computes a real card's verdict before the M7 freeze | I-08, T-GATE-01..04, T-CARD-02 |
| **P12** A single path neither promotes nor rejects (L611-618) | Promotion needs: objective market-own episodes; no episode above 50% of the benefit; no REJECT at any start of the declared start band or in either pre-declared midpoint half; per-regime lines. Single-path ΔMDD/ΔCDaR95 printed with bootstrap bands, never REJECT alone; via the do-no-harm cap at most cap at INSUFFICIENT DATA | Gate package (other brief); verdict function never returns REJECT from ΔMDD/ΔCDaR95 alone | T-DNH-01, I-16 |
| **P13** Every selection is counted (L620-623) | Every configuration ever run in a card's family (research phase included) logged in a hashed family ledger with its timing class. "A card without a ledger hash is refused." Step 3 deflates with `N_eff = max(N_clusters, N_equiv)`. Kish form never used; revision counts are not the trial count | `ledger_hash_at_registration` / `ledger_hash_at_run` required; static scan finds no implementation of `M ⁄ (1 + (M − 1)ρ̄)`; `gate.step3.forbidden: [kish_design_effect, revision_count_as_N]` | T-NEFF-01, T-STEP3-02, T-LEDGER-01 |
| **P14** Forward months are falsification alarms, never validation (L625-628) | A forward record can demote; never raise a verdict or turn INSUFFICIENT DATA into PASS. UNDERPOWERED may convert only a failed step-5 or PC-3 p-value; never waives PC-1′, PC-2 or the PC-3 point REJECT | No code path maps a forward statistic to a verdict upgrade; card `evidence` citing a forward book as validation refused (item 35) | I-14, T-UNDERPOW-01, T-DNB-01 |
| **P15** Verdicts are book-specific; book declared before the run (L630-634) | Verdict belongs to instrument book, notional, rebalance rule, band in the header. Different venue/book = new card, never a revision. Market-gross scalar never judged on / generalised from a stock book. No instrument the desk cannot execute at the declared cost and size | Edit of `instrument_book`, `notional_nav`, `rebalance`, `no_trade_band` or a cost after `results_md5` exists refused (new `card_id` required) | T-BOOK-01, T-DNB-01 |
| **P16** Nothing may freeze, or quietly shrink, the book (L636-641) | Every hard stop has an explicit automatic re-arm. Only hard stop + risk-limit breaches (class RISK) carry the 10-session refusal and the 0.5× cooling-off; an operational HALT clears when its cause clears. HALT scoped to the book whose own trigger fired. Staleness schedule-aware and role-based. `min()` with 0.5 × vt floor outside HALTED | Per-book runtime; RISK/OPS re-arm rules of B.6 | I-04b, T-HALT-01, T-SCOPE-01, T-STALE-01 |
| **P17** No exposure path the gate never sees (L643-646) | Each new overlay judged incrementally on the current recommended book. Once ≥ 2 de-risk factors act in the recommended book, the book is gated as one stack CARD-P. Ladder steps binding on > 10% of days act only in the specification book until their CARD-P passes | Stack card auto-generated (R-02 rule 6); R-31 disposition logic | T-CAP-02 (stack clause, M7), I-04 |
| **P18** No acting decision on a provisional, intraday, bar-derived or stale input; no risk-model-only input can HALT (L648-651) | Official closes primary, reconciled against a second source. Daily closes never derived from intraday bars. Among data inputs only `acting_exposure` inputs can escalate to HALTED, only for the books they are bound to. A `risk_model`, `context`, `forward_sim` or `history` input never HALTs a recommended book | Role-based failure actions; HALT-scope table B.6 | T-BAR-01, T-ROLE-01, T-HEDGE-01, T-SCOPE-01 |
| **P19** No regime-model state, acting or displayed (L653-656) | No jump-model, Markov-switching, GMM or change-point "regime" state acts on exposure or is shown on any QUANTGEN page in v2.0. R-06 σ̂ display labels are volatility labels and stay. BOCPD scale-break probability → R-18 research log only: never acting, never displayed | `inputs[].source_kind == regime_model` refused; UI must not render any such state (see F-6 for the existing sheet "regime read") | T-DNB-01, T-BREAK-01 |

### B.2 Constitutional formulas (L856-897, L1506)

```
IV_m               = inverse-vol weight of market m on weekly returns (EWMA λ 0.97 acting); Σ_m IV_m = 1
A_m                = { f : prior(m,f) ≥ 1  and  card(m,f).verdict ≠ REJECT }
base_weight(m,f)   = IV_m × 1/|A_m|  if f ∈ A_m, else 0
active_budget(m,f) = base_weight(m,f) × vs(m,f) × min(1.0, family_overlay_1(m,f), …)   # vs ∈ [0,1]; overlays ∈ [0.5,1]; empty = 1.0
composed(m)        = vt(m) × min(1.0, gross_overlay_1(m), …, ladder(m), post_rearm_cap(m))   # ladder, post_rearm_cap ∈ {1.0, 0.5}
gross(m)           = min(composed(m), concentration_bound(m))                             # a risk limit, not an overlay
# HALTED sets this book to 0×; it is never an argument of min(); other books continue
target_weights     = composite_weights(i | active_budget, gross)
final_weights      = risk_layer(target_weights)
simulated_orders   = engine.orders(final_weights)      # recommended and specification books only
```
- Invariant (T-CAP-02): `composed(m) ≥ 0.5 × vt(m)` on every non-HALTED day ("written as a product, so vt = 0 needs no division"). 0.75 and 0.5 compose to 0.5, never 0.375. Binding factor logged in `overlay_decision.reasons`.
- Invariant (T-MONO-01): lowering any multiplier never raises any gross or active budget; no renormalisation of freed budget across families/markets; freed active budget → benchmark (long-only) or zero (L/S); freed total exposure → cash. One exception: R-15 admissibility re-weighting K/(K−1), logged as a governance event.
- `vt(m)` scales the market's long book only; not L/S factor sleeves (own `vs`), not the TS-trend sleeve (L894).
- De-risk factor (for the stack card) = market-level (`exposure_basis = total`) factor carried by a card that can take a value < 1.0 in the recommended book: vt (R-06 KR), R-28, R-29, R-31 steps once their card PASSes. Not de-risk factors: look-through caps, hard stop, post-re-arm cap, R-31 steps as `INVARIANT_STEP`, family-level vs (L1506).

### B.3 Rule-object model and validation (§7.1, L4687-4705) — TASK-M0-04

Store model is "immutable and has no financial defaults, so every number … must be written explicitly" (L4127). Proposed signatures:

```python
# core/rules/macro_rules.py  (new; frozen dataclasses, no defaults on financial fields)
@dataclass(frozen=True)
class RuleInput:   series_id: str; role: str; books: tuple[str, ...]; timing: str; source_kind: str
@dataclass(frozen=True)
class RuleObject:
    rule_id: str; kind: str                       # kind ∈ {INVARIANT, CONVENTION, CARD-O, CARD-P, CONTEXT, GOVERNANCE}
    output_range: tuple[float, float] | None      # [lo, hi]
    exposure_basis: str | None                    # active | total
    applies_to: str | None                        # momentum | reversal | flow | quality | ts_trend | market_gross
    composition: str | None                       # min
    books: tuple[str, ...]                        # recommended | specification | forward_sim | refusal
    inputs: tuple[RuleInput, ...]
    estimator: dict | None                        # {name, kind}; kind ∈ {sma, ewma, garch, har, comb, ml}
    label_layer: str | None                       # none | conformal
    instrument_book: str | None; market: str | None
    card_id: str | None; tier: str | None; header_md5: str | None; results_md5: str | None
    n_rule: str | None                            # must be "max(N_clusters, N_equiv)"

def validate_rule_object(obj: RuleObject, *, previous: RuleObject | None, store: dict) -> Report
    # Report/Issue/Severity reused from core/rules/validation.py; Issue.message names the §10 item and label.
    # On any ERROR: nothing is written; the refusal is logged in the store's edit history (L6231).
```

Predicates (each is refused → ERROR; field → condition → §10 item):

| Field | Refused when | Item(s) |
|---|---|---|
| `output_range` | `hi > 1.0`; an overlay outside [0.5, 1.0]; vt or vs outside [0, 1.0] | 2, 8 (Tier C, `gate.tiers.C: {allowed: false}`) |
| `exposure_basis` | missing on an acting rule (P8); value ∉ {active, total} | — |
| `applies_to` | a vt (R-06) rule on anything but `market_gross`; any multiplier on `ts_trend` (R-14 exempt from overlays) | T-BASIS-01 |
| `composition` | anything but `min` | 31 |
| `books[]` | recommended book reading a non-PASS, FORWARD-SIM or refusal multiplier; `INVARIANT_STEP` only for R-31 | 22 |
| `inputs[]` | `source_kind == regime_model` acting or displayed, or a smoothed/forward-looking label (11, 24, 27); `source_kind == ml_classifier` (11, 29); a value-timed or provisional acting input (19, 26); an acting input without a contract or binding (R-19) | 11, 19, 24, 26, 27, 29 |
| `estimator` | `kind == ml` (11, 29); max(SMA20, implied) sizing (30); a change outside an R-30 counted revision (25) | 11, 25, 29, 30 |
| `label_layer` | `conformal` | 28 |
| `instrument_book`, `market` | `KRX_stock_book` as a market-gross scalar (33); an R-28 instance with `market: KR` (37) | 33, 37 |
| `card_id`, `tier`, `header_md5`, `results_md5` | header edit after `results_md5` exists (23, 32); pooled or A-provisional tier added after results (34) | 23, 32, 34 |
| `n_rule` | the Kish form or any other N_eff rule | 36 |
| any field | an order, cancel, withdrawal, deposit-address or transfer path, or a broker adapter (21); a forward record cited as validation (35) | 21, 35 |

Enum sources: `source_kind ∈ {market_price, published_series, derived, implied_vol, regime_model, ml_classifier}` (L4699); `instrument_book ∈ {KRX_ETF_line, KRX_stock_book, KOSPI200_futures, mini_KOSPI200_futures, CME_micro_ES, US_shares_KIS, KRX_listed_SP500_ETF, crypto_venue, FX_KRX_USD_futures, FX_broker_spot, multi_line}` (L3947); `tier ∈ {A, B, C}` (L3939), `A_provisional: closed` (L4610); `timing_class ∈ {VALUE, NON-COMPLIANT, COMPLIANT}` (L4028).

Pseudo-code for the edit-time predicates:
```
if previous and previous.results_md5 and obj.card_id == previous.card_id and any(changed(f) for f in
      ("instrument_book","notional_nav","rebalance","no_trade_band","cost_bp")):  refuse(items 23/32, "a new card id is required")
if obj.tier in ("A_provisional","pooled") and any_market_result_exists(obj.family): refuse(34)
if previous and obj.estimator != previous.estimator and not r30_counted_revision(obj): refuse(25)
if obj.n_rule != "max(N_clusters, N_equiv)" and obj.kind in ("CARD-O","CARD-P"): refuse(36)
if obj.composition not in (None,) and obj.composition != "min": refuse(31)   # None only on rules with no multiplier
if "recommended" in obj.books and obj.kind in ("CARD-O","CARD-P") and disposition(obj) not in
      ("RECOMMENDATION","BUILD_AS_INSURANCE","INVARIANT_STEP"): refuse(22)
if disposition(obj) == "INVARIANT_STEP" and not obj.rule_id.startswith("R-31"): refuse(22)
```

### B.4 DO-NOT-BUILD v2 — every item, label, predicate (§10, L6072-6252; §7 `do_not_build` L4620-4679) — TASK-M0-14

"Never implement any of these unless a new model card passes the gate (§8) with new evidence" (L6041). "A label never lifts a prohibition" (L6066). A G item reopens only by owner principle change. The refusal "names the item and its label. It is logged in the store's edit history, and nothing is written" (L6231). Label vocabulary: `harm` / `null` / `inconclusive`; basis `B` (QF3 bootstrap: 63-day blocks, 1,000 resamples; or share < 0.05), `E` (item's own evidence; provisional), `G` (breaks P0–P19 or a red line) (L6052-6062).

Shape key = key in `do_not_build.refused_shapes` (L4662-4679). "code review" = no configuration shape (items 1, 3–7, 9, 10, 12–18, 20; L6252).

| # | Label (store value) | Prohibited thing (short, verbatim core) | Refused shape key → predicate over §7.1 | Check |
|---|---|---|---|---|
| 1 | `inconclusive_B` | Prior four-state trend × stress classifier and its multiplier table | code review (its > 1.0 multipliers also hit shape for item 2) | — |
| 2 | `harm_B` (+G) | Any multiplier above 1.0 (momentum 1.5× "risk-on", reversal 1.5×/2×, quality/low-vol/min-vol 1.5×, Korea gross 1.5×, flow ×1.5, AAII-reversal ×1.25, vol-target caps above 1) | `multiplier_weight_or_cap_above_1: [2, 8]` → `output_range.hi > 1.0` or any stored weight/cap > 1.0 | T-CAP-01 |
| 3 | `inconclusive_B` | VIX-term-structure switch for momentum (0× or halved) or reversal (1.5×); post-stress-clear 0.5× momentum schedule | code review | — |
| 4 | `harm_E` | Cut-and-re-add gates on existing exposure | code review | — |
| 5 | `inconclusive_B` | Korea gates built from US or global inputs (SOX 60-day trend × USD/KRW 20-day; SOX trend; AI-hardware; US stress row on KOSPI; two-speed/residual KRW gates, dollar "regime B", three-way KRW conjunction) | code review (P4) | — |
| 6 | `{curve_resteepening: harm_B, real_rate: null_B, credit_weights: inconclusive_B, mom_under_rates_stress: inconclusive_E, level_thresholds: inconclusive_E}` | Macro-variable factor or gross gates | code review | — |
| 7 | `null_E` | Lagged oil-price gate on equity or KOSPI gross (Brent +30% over 63 days, or 20-day > +25%) | code review | — |
| 8 | `inconclusive_B` | Net-liquidity (WALCL − TGA − RRP) or M2 rules for crypto or equities | symmetric 1.5/0.5 form hits `multiplier_weight_or_cap_above_1`; else code review | T-CAP-01 |
| 9 | `{forecasts_surveys_positioning: inconclusive_E, crowding_cuts: inconclusive_E, consensus_surprise_entries: null_E}` | Street point forecasts, house views, recession odds, target dispersion as inputs; FMS, Bull & Bear, AAII, COT timing rules; post-trigger crowding cuts; consensus-surprise entries at retail latency | code review | — |
| 10 | `inconclusive_E` | Sahm, curve, probit or growth × inflation-quadrant gates; fixed-coefficient Okun, Phillips, sacrifice-ratio or M2 → CPI relations | code review | — |
| 11 | `{11a_ml_vol_state_classifiers: harm_E, 11b_range_log_har: admitted, smoothed_regime_probabilities: harm_G, unpenalised_hmm_ms_gates: harm_E, complexity_rff_timing: null_E, llm_text_pre_cutoff_backtests: harm_G}` | 11a ML vol-state classifiers (elastic-net, gradient-boosting, any ML classifier of next-month vol state, as sizing, gating or display input). 11b range-based log-HAR ADMITTED to the R-30 race. 11c smoothed regime probabilities; unpenalised daily HMM/Markov-switching gates; "complexity"/random-feature macro ML timing; LLM or text signals backtested before the model's training cutoff | `ml_classifier_estimator_gate_or_label: [11, 29]` → `estimator.kind == "ml"` or any `inputs[].source_kind == "ml_classifier"`; `regime_model_source_acting_or_displayed: [11, 24, 27]` → any `inputs[].source_kind == "regime_model"` | T-DNB-01 |
| 12 | `{event_blackouts_24h_and_swing: inconclusive_E, quad_witching_blackout: null_E, expiry_close_fade: inconclusive_E}` | 24-hour pre-event blackouts; swing-book blackouts around FOMC, CPI, NFP, BoK, export prints; KRX quad-witching blackout; index expiry-close fade | code review | — |
| 13 | `inconclusive_E` | Calendar and supply-timing tilts | code review | — |
| 14 | `{rate_differential_models: null_E, foreign_flow_rules: inconclusive_E}` | Rate-differential models of USD/KRW direction; hard-wired "foreign selling ⇒ weak KRW"; Korean foreign flow as a direction signal or flow-regime up-weight | code review | — |
| 15 | `inconclusive_E` | "USD down and equities down" as an equity de-risk trigger | code review | — |
| 16 | `inconclusive_E` | Credibility-state blackout rule | code review | — |
| 17 | `inconclusive_E` | 200-day-average conjunction on the vol target (R-28 is a different object) | code review | — |
| 18 | `harm_G` | Treating 2022–26 as a clean holdout. Locked holdout starts **2027-01-01**; `2022-01-01 → 2026-10-02` is a reported stress window (`gate.stress_report_window`, `gate.locked_holdout_start`, L4614-4615) | code review; config keys fixed | — |
| 19 | `harm_G` | Data shortcuts: Yahoo continuous-futures returns across rolls; unnamed "Brent"; intraday circuit-breaker prints as closes; positional lags on monthly series with gaps; H.10/H.15 used as if same-day; US-session data on same-date KOSPI close-to-close returns; a provisional, intraday or bar-derived row as an acting close (e.g. the 2-Oct vendor row 6,943.66) | `value_timed_or_provisional_acting_input: [19, 26]` → an input with role `acting_exposure` (and `risk_model` in `run_mode = live`, T-H10-01) whose `timing` ≠ COMPLIANT, or a provisional/bar-derived close | T-LAG-01, T-PROV-01, T-BAR-01 |
| 20 | `inconclusive_E` | China PMI or CNY as a Korea signal (China stays in the covariance only); CESI as an equity feature | code review | — |
| 21 | `harm_G` | Any order, cancel, withdrawal, deposit-address or transfer path, or a broker execution adapter, inside this programme ("§3.10 … is not a design") | `order_path_or_broker_adapter: 21` → any field/value naming such a path or adapter | T-RO-01 (static scan), T-RO-02 (runtime guard) |
| 22 | `harm_G` | Offering a non-PASS card's output as a recommendation, or a FORWARD-SIM multiplier reaching the recommended book. Includes R-28/R-29 until build conditions hold; R-04 (DEMOTED, "step 3 FAIL"); a ladder step binding on > 10% of days before its CARD-P passes; R-11 or R-12 in any book other than its display-only refusal book | `recommended_book_reads_non_pass_multiplier: 22` (an R-31 step with disposition `INVARIANT_STEP`, binding share ≤ 0.10, is not specification-only) | I-03 |
| 23 | `harm_G` | Lowering a pre-registered cost, or switching a card's instrument book after seeing results. Monthly and banded 50 bp US variants are logged trials, never rescues | `header_edit_after_results_md5: [23, 32]` (fields: `instrument_book, notional_nav, rebalance, no_trade_band, cost_bp`); lowering a cost raises | T-DNB-01, T-BOOK-01, T-COST-03 |
| 24 | `harm_G` | Smoothed or forward-looking calm / normal / elevated / stressed labels, or using those labels (or the existing regime read or sheet z-scores) as gates. R-06 display labels are causal, display only | `smoothed_or_forward_looking_label: 24`; `regime_model_source_acting_or_displayed` | T-DNB-01, T-LABEL-01 |
| 25 | `harm_G` | Any model as the sizing estimator, except through the staged estimator gate (R-30) as a counted card revision that passes the full v2 CARD-P. GJR fit outside bounds or tripped OHLC open-quality flag → fall back to SMA20 | `estimator_change_outside_r30_revision: 25` | T-DNB-01, I-10 |
| 26 | `harm_G` | Value-timing golden values presented as compliant (H.10/H.15 before publication must be labelled VALUE or NON-COMPLIANT; a production rule may not read the published series in their place) | `value_timed_or_provisional_acting_input` | T-LAG-01, T-H10-01 |
| 27 | `{jump_model: inconclusive_E, markov_switching: harm_E, gmm_and_change_point_states: inconclusive_E, prohibition: binding_red_line_E1}` | A regime-model state, acting or displayed (jump model, Markov switching, GMM label, change-point "regime"). BOCPD (hazard 1/250) → R-18 research log only, "no R-18 dependency". GMM scenarios deferred, never labelled as a current regime | `regime_model_source_acting_or_displayed` | T-DNB-01 |
| 28 | `null_E` | Mondrian conformal label layer on the display labels | `conformal_label_layer: 28` → `label_layer == "conformal"` | T-DNB-01 |
| 29 | `harm_E` | A maintained ML challenger pipeline (no ML vol-state model kept running, re-tuned or re-scored; harness script kept in `docs/` as the record) | `ml_classifier_estimator_gate_or_label`; a challenger entry of kind `ml` | T-DNB-01 |
| 30 | `harm_B` | `max(σ̂_SMA20, implied)` sizing. Implied vol = context (VIX/VIX3M at 16:00 ET; KOSPI 200 MFIV at 15:30 KST); may enter sizing only inside HAR-IV if it wins R-30 | `sizing_estimator_max_over_implied: 30` | T-DNB-01 |
| 31 | `harm_G` | Product-composed de-risk stacks | `composition_not_min: 31` → `composition != "min"`; runtime: product path raises / fails `bounds_ok` → HALT (OPS) of the books whose artifact it is (L1508) | T-CAP-02 |
| 32 | `harm_G` | A venue switch after results (extends 23 to every header field of R-26). MACRO-R06-US-FUT is a new card (R-29), not a revision | `header_edit_after_results_md5` | T-DNB-01, T-BOOK-01 |
| 33 | `harm_G` | A stock book as a market-gross scalar. R-06 KR at 35 bp printed for reference only | `krx_stock_book_on_market_gross_scalar: 33` → `instrument_book == "KRX_stock_book" and applies_to == "market_gross"`; config `instruments.market_scalar_on_stock_book: refused` | T-DNB-01, T-BOOK-01 |
| 34 | `harm_G` | A pooled or A-provisional route for a card already run (none open to R-04, the jump model, the KOSPI trend card) | `pooled_or_a_provisional_tier_after_results: 34`; `gate.tiers.A_provisional: closed`; `pooled_rule: declare_before_any_market_is_run` | T-DNB-01, T-R04-01 |
| 35 | `harm_G` | A forward record presented as validation | `forward_record_cited_as_validation: 35` → card evidence field cites a forward book as validation | T-DNB-01, I-14 |
| 36 | `harm_G` | The Kish trial count | `kish_or_other_n_eff_rule: 36` → `n_rule` ≠ `gate.step3.n_gate: max(N_clusters, N_equiv)`; `kish_design_effect` ∈ `gate.step3.forbidden` | T-DNB-01, T-NEFF-01, T-STEP3-02 |
| 37 | `inconclusive_E` | A KOSPI trend card that acts (SMA10m card registered for US / non-Korean sleeves only; Korea trend state CONTEXT-ONLY: displayed, never acting) | `r28_instance_market_kr: 37` → `rule_id` is R-28 and `market == "KR"` | T-DNB-01 |

Not on the list (L6254-6260): range-based log-HAR and COMB (admitted to R-30); R-06 σ̂ display labels; BOCPD probability as R-18 research-log entry; KOSPI trend state displayed as context; D3 (owner decision, default enforced by `families.reversal.calm_state_downweight: not_adopted`).

### B.5 Owner decisions D1–D6 (canonical: Quick start table L65-74; registry L4138-4152; procedure L5441-5455) — TASK-M0-06

| ID | Decision | Default implemented | Canonical key | Stored value / options / status |
|---|---|---|---|---|
| D1 | Korea concentration template | **MSCI 25/50**: single name ≤ 22.5% after the buffer; names above 4.5% ≤ 45% in aggregate; checked quarterly and on breach | `risk_layer.korea_caps.template` | `msci_25_50`; options `[domestic_max10_or_weight, msci_25_50, pair_35]`; `default`; refs `[]` |
| D2 | Drawdown hard-stop level | **−15% of book NAV** from the high-water mark since the last re-arm. Option (b): −1.5 σ_book | `risk_layer.drawdown.hard_stop.level` | `-0.15`; options `[-0.15, "-1.5*sigma_book"]`; `default`; refs `[cards.R-31_step_down.hard_stop_level]` (a ruling gives R-31 a counted revision) |
| D3 | Calm-state reversal down-weight, QF5-M10 | **Not adopted: P3 stands** | `families.reversal.calm_state_downweight` | `not_adopted`; options `[not_adopted, reopen_after_krx_net_test]`; `default`; refs `[]` |
| D4 | Book-level false-demotion budget | **≤ 10% a year** across all statistical demotion triggers, split equally across active cards, each split verified on a 20-shift placebo panel | `monitoring.false_demotion_budget_per_year` | `0.10`; options `[tighten_only_le_0p10]`; `default`; refs `[]` |
| D5 | Whether/which line to run a US sleeve | **No US sleeve until decided**: R-28 and R-29 stay FORWARD-SIM and never enter the recommended book. Scope: US market-gross line (R-06 US, R-28, R-29); R-03's momentum sleeve on US shares is not a US sleeve in D5's sense | `sleeves.US.line` | `none`; options `[CME_micro_ES, KRX_listed_SP500_ETF, none]`; **`pending`**; refs `[instruments.us_line_choice, cards.R-28_trend_axis.us_sleeve, cards.R-29_US_FUT.us_sleeve_and_line]` |
| D6 | CDaR-guard calibration (applied only if a negative control passes) | **lowest-placebo-false-pass rule**, frozen with the package; ties → Professors' test; if no candidate brings every negative control to REJECT/INSUFFICIENT DATA the attempt fails (R-21 9(a)); an owner ruling naming one candidate accepted only before the first acceptance attempt | `gate.acceptance_test.cdar_guard.calibration` | `lowest_placebo_false_pass_rule`; options `[lowest_placebo_false_pass_rule, professors_bootstrap_one_sided_5pct, executives_placebo_p10_margin, qf_blind_margin]`; `default`; refs `[]` |

Algorithm (binding behaviour, proposed names):
```
load_macro_store(path) -> dict:
  for Dn in D1..D6:
     e = store["owner_decisions"][Dn]; assert set(e) == {key,value,default,options,status,effective_from,rationale,refs}
     assert e["status"] in {"default","owner_set","pending"}
     v = get_path(store, e["key"]); assert is_plain_scalar(v) and v == e["value"]          # T-OWNER-01
     for p in e["refs"]:                                                                   # dependent blocks
        x = get_path(store, p)
        if x == {"ref": e["key"]}: continue                                               # exactly one key
        if is_plain_scalar(x) and x != e["value"]: refuse("literal copy differs from its key")
  walk(store): any dict containing "ref" must be exactly {"ref": <canonical key>} else refuse at load; replace by resolved value
set_owner_decision(Dn, value, *, rationale, effective_from, now_utc):
  validate value against options (D4: value ≤ 0.10 only; D6: only while gate/acceptance_runs.jsonl has no attempt)
  write canonical key and registry value; status -> "owner_set"; append edit history
  append governance event {kind:"owner_ruling", actor:"owner", key:<canonical key>, old, new, reason:rationale}
  # never a demotion, never a gate-package version (L5445-5446); D2 -> R-31 marked for a counted revision before its next run
```
- A card header's `owner_decisions` records the values at commit and is checked only at commit (L5672).
- Macro page lists every open owner decision (L65); `macro_state.owner_decisions` = "every decision whose canonical key a rule of this market reads, plus every decision with status pending", items `{decision, value, status}` (L3605-3606, example L3687-3688).
- D1 and D2 act on the recommended book only (card books exclude hard stop and caps, R-22 rule 6) (L5446).

Owner inputs (not decisions; L76, L5465): (1) M1 sign calendar files (T-CAL-01) incl. pre-2015-06-15 conditional random-end extensions, Saturday-session close times before 1998-12-12, lunch-break dates, pre-2016 CSAT session window, ETF tick table; sign 2027 calendars before 2026-11-01 (T-CAL-02). (2) M1 KIS credentials for the quote-field check (069500 and 005930 bid/ask at 15:19:59 KST on 20 sessions) — without them record "not run", dependent features labelled UNVERIFIED. (3) Before M7 header commit: `sleeves.<market>.notional_nav`; ECOS code of `BOK_CALL_RATE` + observation calendar. (4) Optional D6 ruling before first acceptance attempt. Also: SSE/HKEX/TWSE close times, choice of `USD_LIVE_PROXY` (default `DX-Y.NYB`, L6030).

### B.6 Books, statuses, HALT scope (constitutional parts of §3.8/§8.1.2)

Book ids (L1180): `recommended:<market>`, `specification:<market>`, `forward_sim:<rule>`, `refusal:<rule>`, `card:<card_id>:<on|off|S>`. Runtime states per book: `DISARMED` (initial; retired) → `ARMED` (automatic, from initial only, at the first decision at which every acting input bound to the book is fresh and past warm-up, calendars cover ≥ 60 sessions ahead, and for card books the header is committed) → `HALTED`. ARMED/HALTED → DISARMED: owner action only.

| Book | Holds | Shown as recommendation |
|---|---|---|
| recommended | invariants + factors of PASS cards (disposition `RECOMMENDATION` or `BUILD_AS_INSURANCE`), every other factor enters as 1.0; R-31 steps with binding share ≤ 0.10 as `INVARIANT_STEP`. While R-06 KR is NOT_RUN vt enters as 1.0 | yes (the only one) |
| specification | every BUILD NOW and SPECIFICATION BOOK factor, labelled with its verdict (incl. R-04 at floor 0.5; R-31 steps while binding > 10%) | no |
| forward_sim (R-28, R-29) | specification book × the card's factor, on the card's declared book/notional; never passes through `engine_feed` | no |
| refusal (R-11, R-12) | display only; read by no other book | no |

Build statuses (L4783-4790): BUILD NOW (R-01, R-02, R-03, R-05, R-07, R-08 annotation, R-09, R-10, R-14, R-15, R-18, R-19–R-27, R-30, R-32–R-35); BUILD-AS-INSURANCE ("not a fifth verdict"; R-06 KR on a formal PASS; R-28/R-29 once promoted); FORWARD-SIM (R-28, R-29); SPECIFICATION BOOK (R-04; R-31 while binding share > 10%; R-06 KR while NOT_RUN or INSUFFICIENT); RETIRED (R-11, R-12); DEFERRED / CONTEXT (R-17 / R-13, R-16, KOSPI trend state).

HALT triggers by class (L1178-1179):
- **RISK**: hard stop (−15% of the book's NAV from the HWM since last re-arm, D2; breach test `<=`, T-HALT-01); risk-limit breach (an R-07 limit its prescribed action cannot meet by the next decision). Re-arm: earns 0 on t+1…t+10; automatic at the decision at the close of t+10; after a hard stop both references reset to NAV at re-arm; `post_rearm_cap = 0.5` inside `min()` for the weights decided at the re-arm decision and the 9 after it.
- **OPS**: lag-audit violation at runtime; acting-field schema or bounds failure in the book's own `macro_state`/`overlay_decision`; an `acting_exposure` input bound to the book failing closed on more consecutive decisions than its declared limit (default: more than one); `run_error`; feed heartbeat loss > 60 s during a session (re-arm after feed restored 5 minutes); exception in `market_vol_target`, `concentration_bound`, `drawdown_ladder`, `compose`; whole-book NAV unavailable on more than 2 consecutive decisions; decision date outside calendar coverage (`reason = calendar_coverage`); operator kill. Re-arm: automatic at the first decision at which the cause has cleared, except lag-audit violation or acting-artifact schema failure → operator re-arm. No refusal window, no reference reset, no cap.
- **Never a HALT trigger**: stale/failing `risk_model` or `context` input; exception inside `hedge_state` (→ `hedge_credit_off = TRUE`); a `disputed` input; a `warmup` input before the book's first ARMED decision; failure of an input not bound to the book; validation failure confined to display/context fields or of a `context_log`/`event_calendar` artifact.
- Scope: a trigger HALTs only the books whose own NAV breached, whose own artifact failed acting-field validation, or that read the failed input through an `acting_exposure` binding. "it never HALTs 'the engine' as such."
- Every HALT and re-arm is a governance event.

Verdict / disposition / display enums (L3759-3761, L4007-4012): verdict ∈ `PASS | REVISE | REJECT | INSUFFICIENT_DATA` (card result) plus `NOT_RUN` (in `overlay_decision` card refs); disposition ∈ `RECOMMENDATION | BUILD_AS_INSURANCE | INVARIANT_STEP | SPECIFICATION_ONLY | FORWARD_SIM | REFUSAL_BOOK | DESCRIPTIVE`; displayed_as ∈ `recommendation | insurance | invariant | descriptive | refusal`; `build_status_on_pass ∈ {BUILD_NOW, BUILD_AS_INSURANCE}`. Rule kinds: `INVARIANT | CONVENTION | CARD-O | CARD-P | CONTEXT | GOVERNANCE` (L1463-1469).

### B.7 Read-only enforcement (P0; T-RO-01, T-RO-02)

- Static scan (extend existing tests): whole repository incl. `core/skills` scripts and the commands of every workflow YAML; "no order, cancel, withdrawal, deposit-address or transfer call and no import of an order-submission client (the forbidden symbols and AST patterns are listed in the test)"; `core/engine/orders` reached only through the simulated order book API; every artifact has `read_only: true` (L5605).
  - Existing needles to keep: `order_cash, order-cash, place_order, submit_order, TTTC0802U, TTTC0801U, VTTC0802U` (`tests/acceptance.py:171`); `KIS_ACCOUNT, CANO, ACNT_PRDT_CD` (`:181`); `/v1/orders, /v1/withdraws, /api/v3/order, private_key, seed_phrase, import ccxt, import web3` (`tests/expansion_acceptance.py:155`). Add: `pyupbit`, `/v1/deposits/generate_coin_address`, `/sapi/v1/capital/withdraw`, `/uapi/*/trading/`.
  - `core/engine/orders.py` legitimately defines `OrderBook.place/fill/cancel/cancel_all_open` (simulation) — the scan must target venue endpoints/clients, not these method names; add an import-graph assertion that only `core/engine/*` (and the new macro `engine_feed`) import `core.engine.orders`.
- Runtime guard: one check in the single KIS choke point `data/krx/kis_client.py:176 KISClient._get(path, tr_id, params)` — path must be in an allowlist "frozen in `config.py`"; "any trading or account path raises before a request is built". Current call sites use 24 distinct `/uapi/.../quotations/...` paths found by grep (3 in `data/krx/kis_client.py`, 21 in `data/kis_markets.py`; re-enumerate when freezing the list) + token `POST /oauth2/tokenP` (`kis_client.py:159`, not routed through `_get`).
- "The Claude API is called without tools, and its text is never parsed by an acting module." (L5606)

### B.8 Invariants to check in every pull request (L78-87, verbatim essentials)

1. No order, cancel, withdrawal, deposit-address or transfer path; KIS is read-only (P0, T-RO-01).
2. No multiplier or weight above 1.0. Overlays in [0.5, 1.0]; vt and vs in [0, 1.0]. `composed(m) = vt × min(1.0, overlay₁, …, overlayₖ, ladder, post_rearm_cap)`, never a product; outside HALTED `composed(m) ≥ 0.5 × vt` (P2, T-CAP-01, T-CAP-02). Concentration bound and risk-layer caps act after and may take gross lower; the floor assertion is on `composed(m)`, never on gross or final weights.
3. Every acting input read through `pit_value` with `available_at_utc ≤ decision_utc`. A close-type acting input needs `value_status = official_close` for the decided session. No synthetic, provisional, bar-derived or stale acting input (P5, P18, T-PROV-01).
4. HALTED is scoped per book. Among data inputs only an `acting_exposure` input bound to a book can HALT that book; an input bound only to specification, FORWARD-SIM or refusal books fails that book closed and never HALTs the recommended book. A stale/failing `risk_model` input, or an exception inside `hedge_state`, sets `hedge_credit_off = TRUE` and never HALTs (P16, P18, T-ROLE-01, T-SCOPE-01).
5. Only PASS cards feed the recommended (displayed) book, as a recommendation (CARD-O) or as insurance (CARD-P, BUILD-AS-INSURANCE). Specification-only factors (R-04; R-31 steps whose binding share exceeds 0.10), FORWARD-SIM cards (R-28, R-29) and refusal books (R-11, R-12) never do (P7, I-03). R-31 steps with binding share ≤ 0.10 act in the recommended book as part of the R-07 invariant, disposition `INVARIANT_STEP`.
6. Every artifact and card validates against its §6 schema; a field a rule writes is declared in that schema (T-SCHEMA-03).
7. Costs read from the gate's table with the tick floor applied, never lowered, every result also at 2×. Every card header declares its instrument book, notional NAV, rebalance rule and no-trade band (P10, P15, T-COST-02/03, T-BOOK-01).
8. The gate package is frozen before any formal card run (P11, I-08).
9. Macro tests are hermetic and read frozen post-close fixtures only (T-HERM-01, T-FIX-01).

### B.9 Gate-freeze ordering (P11; L46-51, L4812-4828) — constraints every milestone obeys

1. Build R-21, R-22, R-23, R-24, R-34; harness tests on synthetic data / frozen fixtures / `timing_probe` sandbox, writing to temporary ledger copies.
2. Gate-acceptance test (I-08): ≤ 10% of 300 circular-shift placebos per family pass PC-1′; ≤ 2 of 20 per card pass PC-1′; five negative controls (US VT 5-day and 10-day at 50 bp; post-shock-day and post-shock-week 0.5×; stale VT with σ lag 252) each REJECT or INSUFFICIENT DATA. Every attempt appended to `gate/acceptance_runs.jsonl` (append-only, hash-chained). Failure freezes nothing and blocks every card run; one bounded redesign per package version; second failure (across all 2.x) → no card can be evaluated under v2.
3. If a control passes: add the D6 guard before any card runs.
4. Freeze: `gate.package = {version: "2.0.0", definitions_md5, acceptance_report_md5, frozen_utc}`; then commit formal headers blind (`MACRO-R06-KR-ETF`, `MACRO-R03-US-MOM`, `MACRO-R14-MULTI-TREND`, `MACRO-R31-KR-ETF`, `MACRO-R28-US-TREND`, `MACRO-R06-US-FUT`; ids proposed), then run.
5. Nothing in the package changes after a card result has been seen; a change = new package version re-run on every card with flips disclosed.
- R-06 KR is expected to return INSUFFICIENT DATA (f > 1.282 at p_ni 0.078; PC-3 needs `p_ni × f ≤ 0.10`); "no convention may be changed to rescue it" (L53).
- "No test runs a formal card before the M7 freeze" (L19). Freeze-tier tests are never recomputed by `tests/run_all.py`; only md5s are re-verified (L5494-5496).

### B.10 Build order and exit tests (authoritative: §9.0a L5548-5561)

| runs_from | Tests and clauses |
|---|---|
| M0 | T-RO-01, T-HERM-01/02, T-SCHEMA-01/02/03, T-CAP-01, T-BASIS-01 (S2 clause from M8), T-REPRO-01a, T-COST-02/03, T-BOOK-01 (header clauses; printed-line clause from M7), T-DNB-01, T-OWNER-01 |
| M1 | T-PROV-01, T-FIX-01, T-BAR-01/02, T-CLOSE-01/02, T-AVAIL-01, T-STALE-01, T-ROLE-01/02, T-XMKT-01, T-LAG-01/02, T-SYN-01, T-TZ-01/02, T-MISS-01/02, T-SER-01/02, T-PRINT-01, T-H10-01/02, T-H15-01, T-VIX-01, T-SAT-01, T-REGIME-01, T-CAL-01/02, T-RO-02, G-POST-01 (data rows) |
| M2 | T-CAP-02 (stack-card clause from M7), T-VT-01, T-CORR-01, T-HEDGE-01, T-COST-01, T-LABEL-01, I-02; G-KR-01..04, G-KR-02b/02c, G-US-01/01b/01c; G-KR-06 (reference mode) |
| M3 | T-B5-01, I-10, T-EST-01/02/04; G-B5-01..04, G-EST-01..04 |
| M4 | T-R03-01 (sleeve-scale and years clauses), T-PRIOR-01; G-MOM-01..06, G-MOM-08, G-INTL-01, G-BOOK-01; G-MOM-07 (reference mode) |
| M5 | I-04, I-04b, I-06, I-06b, I-06c, T-CAPS-01, T-ANNOT-01, T-FILL-01..03, T-BAR-01 (R-27 clause), T-HALT-01, T-STEP-05, T-BOOK-03, T-MONO-01; G-LAD-01..03 (reference mode) |
| M6 | T-CTX-01/02, T-BREAK-01 |
| M7 before freeze | T-DSR-01/02, T-NEFF-01, T-STEP3-01/02, T-SEL-01, T-LEDGER-01, T-ES-01, T-DNH-01, T-ORDER-01, T-EPIS-01, T-EXCESS-01, T-BAND-01, T-POWER-01/02, T-UNDERPOW-01, T-PZERO-01, T-PBO-01, T-SE-01, T-PLACEBO-01/02, T-GATE-04; I-05; then I-08 with T-GATE-01 and T-GATE-03 |
| M7 after freeze | I-08's US VT15 clause and T-GATE-02; I-09, I-07, I-15, I-16, T-EPIS-02, T-TROUGH-01, T-ES-02, T-RLAYER-01, T-R03-01 (step-3 and header clauses), T-R04-01, T-R14-01, T-R06-US-01, T-CARD-01/02, T-REPRO-01b, T-BOOK-02, T-STEP-01..04; G-KR-L*, G-US-F*, G-PWR-*, G-DSR-01/02 |
| M8 | I-01, I-03, I-12, I-13, I-14, T-REF-01/02, T-REPLAY-01, T-SCOPE-01, T-OBS-01..05, T-CARD-03, T-DEMOTE-01..05, T-TREND-01..04, T-USFUT-01..05, T-BASIS-01 (S2 clause); G-KR-05/05s, G-TR-*, G-REF-* |
| M9 | I-11, T-REPRO-01c |
| M10 | T-CRYPTO-01, T-FX-01 |

"Do not start M(k+1) until M(k)'s exit tests pass in `tests/run_all.py`" (L19). Test tiers (L5496): `fast` (unit; ≤ 10 minutes total), `golden` (fixture reproductions; ≤ 2 hours), `freeze` (I-08, formal runs of I-07 and I-16, GJR-null paths, PBO). "A verdict derived from a statistic within tolerance of its threshold is asserted as a class … never as a point" (L5499).

### B.11 §11 current-state snapshot (2026-10-02, post-patch; L6264-6352) — values the build must reproduce (Level-1 tolerance)

Reading rules: KRX decision of 2 Oct stamped 06:30:30Z, earns from the next KRX session **6 Oct** (5 Oct = substitute holiday). "No card has been formally run, and the gate package is not frozen yet. So every row's recommended-book value is the invariant-only value." Outputs are specification-book values unless stated. Owner decisions at defaults.

| Item | Value (data date) | Output / function | From |
|---|---|---|---|
| KOSPI official close | **7,003.74** (2026-10-02; +0.46%; `value_status = official_close`); vendor row 6,943.66 (file written 10:56 KST) is provisional | `pit_value` (T-PROV-01) | M1 |
| Drawdown from 9,114.55 closing peak | **−23.2%** (−23.16%) | G-POST-01 | M1 |
| Close / 200-day average | **1.107** | G-POST-01 | M1 |
| rv20 (SMA20) | **28.8%** (28.82%); rv21 31.9% at the 73rd percentile of trailing 3 years | `market_vol_target` (simple returns, ddof = 1) | M2 |
| vt_KR | earning on 2 Oct = **0.61**; decided at the 2 Oct close for 6 Oct = **0.694** (SMA20, target 0.20, cap 1.0, KRX ETF line) | `market_vol_target` | M2 |
| KR display labels | **elevated** (relative: 70th percentile; quartiles 15.7 / 18.6 / 33.6%) · **stressed** (absolute) | T-LABEL-01 | M2 |
| KRW=X | **1,356.84 (1 Oct)**; 20-observation change −0.11%; provisional 2-Oct row 1,360.63 dropped | store | M1 |
| US Mom σ126 | 23.9% (2026-08-31) → **vs = 0.50** (R-03; indicative PASS; step 3 0.98 at N_equiv 6.3, 0.947 at linear N̂ 12.6) | `sleeve_vol_scale` | M4 |
| US 24-month market return | +39.7% (end-Aug-2026) → D&M bear state **OFF**; Mkt vol126 14.3% vs its 2/3 quantile 17.4% | `dm_gate` (specification book only) | M4 |
| S&P 500 | 7,666.45 (2026-10-01); 1.062 × 200-day; rv20 10.7% → **vt_US = 1.00**; label **normal** (relative: 28th percentile); US card REJECT by instrument; with D5 = none nothing reaches the recommended book | `market_vol_target` | M2 |
| Samsung + SK hynix | ≈ 51% of KOSPI (51.2% Sedaily-anchored; 53.6% on the 25-Oct-2024 KRX-weight anchor); 53.8% of KODEX 200 on look-through; ≈ 75% of KOSPI's 63-day variance | Template MSCI 25/50: absolute bound 22.5 / 29.8 = **0.755**; active-cap bound ≤ 0.05 / (0.298 − 0.225) = **0.685**. Specification book gross `min(0.694, 0.755, 0.685) = 0.685`; recommended book (vt NOT_RUN → 1.0) `min(1.0, 0.755, 0.685) = 0.685`. Active bound binds in both; `concentration.by_book` printed. Semiconductor cap 0.50 unchanged | `concentration_bound` (T-CAPS-01) | M5 |
| Ladder / hard stop | Ladder steps specification-book only until R-31 passes (Korea VT20 binding share ≈ 19%). Hard stop **armed** at −15%. Both KR books **ARMED** | runtime | M5 |
| Next KRX session | Tue 6 Oct: `gap_sessions` 2 (US sessions of 2 and 5 Oct), tag KRX_HOLIDAY_GAP, displayed 1-day VaR × √2; Sep NFP (2 Oct 08:30 ET = 21:30 KST) sets `kr_open_gap_session` = 6 Oct. Annotations only | R-10 (I-06b, T-TZ-02) | M5 |
| Next two weeks | Hangul Day Fri 9 Oct; Columbus Day Mon 12 Oct (NYSE open, Fed closed) → 12 Oct is second multi-session gap session; H.10 release for the week of 5 Oct usable from the KRX close of Wed 14 Oct | T-H10-02, T-AVAIL-01 | M1 |
| VIX / VIX3M | 16.34 / 18.37 (2026-09-30) → annotation **OFF** (usable from the 2026-10-01 US close) | R-08 | M5 |
| HY OAS | 3.12%; 21-day change +47 bp (2026-09-30) | context | M6 |
| Baa−10y | 1.47; 21-day change −12 bp | context | M6 |
| US 10y | 5.29% (2026-09-30); 20-day change **+50 bp** → S2 flag on in data dated 23 Sep 2026; strict H.15 refusal book applies it from the close of 25 Sep (earning 28 Sep); REJECT at every timing and cost | refusal book R-12 | M8 |
| USD/KRW | DEXKOUS 1,356.51 (2026-09-25), 20-obs dlog −1.81%; KRW=X 20-obs dlog −0.11% → **S1 flag OFF**; latest DEXKOUS usable at the 2 Oct KRX close is dated 25 Sep (published Mon 28 Sep, 16:15 ET) | refusal book R-11 | M8 |
| Core PCE YoY | 3.01% (Aug-2026; 3.008%) → contributes to `hedge_credit_off` | `hedge_state` | M2 |
| Stock–bond corr 63 / 252 | +0.53 / +0.33 (2026-09-30; S&P vs −ΔDGS10, date-aligned) → **`hedge_credit_off = TRUE`**; `hedge_reasons = [corr_positive, core_pce_ge_3]` | `hedge_state` (T-CORR-01) | M2 |
| Broad USD | 120.33 (2026-09-25); 20-day +1.67% → `hedge_failure` FALSE (computed from `USD_LIVE_PROXY`'s 1-day change) | `hedge_state` | M2 |
| Weekly KOSPI vs ΔUSD/KRW, 26 weeks | +0.05 → `fx_hedge_credit` FALSE (display only) | `hedge_state` | M2 |
| Context | 10y TIPS / breakeven / 5y5y 2.93% / 2.36% / 2.36%; Kim–Wright TP 1.02 (2026-09-25); MOVE 108.1 (2026-10-01); 10y–3m / 10y–2y +1.07 / +0.46; probit 0.095; Sahm −0.07, U-3 4.1% (Aug-2026); CPI YoY **3.35%** (calendar lag; 3.71% positional = test value; exact 3.353% ± 0.01, T-MISS-01); Taylor residual central −0.9 pp, Fed range 3.75–4.00%; Brent dated $113.96 (2026-09-29), BZ=F $102.59 (2026-10-01); USD/JPY 157.18; BoK base rate 3.00% | `context_log` | M6 |

### B.12 What the spec believes already exists (§0.5, §3.1, §3.4) vs the repo (checked 2026-10-05)

| Spec claim | Reality | Consequence |
|---|---|---|
| Read-only by construction; no order path (L463-464) | TRUE. `tests/acceptance.py:169,177`; `tests/expansion_acceptance.py:155`; `data/krx/kis_client.py` quotations only; all KIS GETs route through `KISClient._get` (`:176`) | Extend existing tests; one allowlist check in `_get` |
| Four verdicts PASS / REVISE / REJECT / INSUFFICIENT DATA (L466) | TRUE: `core/quant/validate.py:50 DECISIONS = ("PASS","REVISE","REJECT","INSUFFICIENT_DATA")` (underscore) | Use `INSUFFICIENT_DATA` in code/JSON; "INSUFFICIENT DATA" only in display text |
| Nine-step gate numbers (L467-476) | TRUE in `core/quant/validate.py:53-74 GATE`: `w_is 756, w_oos 126, ci_level 0.90, bootstrap_B 2000, block 10, dsr_min 0.95, pbo_max 0.05, pbo_reject 0.20, prob_loss_max 0.10, bench_p_max 0.10, plateau_min 0.5, years_pos_min 0.60, haircut 0.6, cost_stress 2.0`. `pbo_cscv(S=8)` default vs v2 `gate.stats.pbo.cscv_blocks: 16` | Do not edit `GATE` ("change them here and nowhere else"); v2 params live in the macro rules store |
| "Costs are defined once, in the gate's code" (L591) | PARTLY FALSE: the table is `docs/asset_expansion_study.py:60 COST = {"krx_etf": 3.0, "us": 50.0, "krx_stock": 35.0, "crypto": 10.0, "futures": 5.0, "fx": 10.0}`; `core/quant/validate.py` holds only `cost_stress: 2.0` | F-5 |
| Strategy Lab: 34 cards, 5 PASS / 11 REVISE / 18 REJECT / 0 INSUFFICIENT (L478) | TRUE (`docs/asset_expansion/cards/*.json`, counted) | — |
| Quant Lab path colours carry calm / normal / elevated / stressed quartile labels (L481) | NOT FOUND by grep in `ui/`, `core/` | The R-16 rename to "path-vol quartile" may be moot; verify in `ui/quant_lab_page.py`/`ui/qcharts.py` before M9 |
| `core/engine` runtime DISARMED→ARMED→HALTED (L767) | ONE global `EngineState` (`core/engine/state.py`), HALTED "needs a manual re-arm"; no book concept; `core/engine/runtime.py` drives operator order rules on a quote loop | Per-book runtime is a NEW module beside it; leave inherited behaviour (125 inherited checks) untouched |
| `core/rules`: immutable model, no financial defaults, validation, one JSON store with edit history (L780-783) | TRUE but it is the operator ORDER-rule store (`Rule` with side/size/conditions; `validate(rule) -> Report`); store file under `config.trading_dir()` (`~/.nextgen/trading`), history cap `HISTORY_LIMIT = 50` | F-1 |
| `core/calendars` package with `data/` (L76, L789) | `core/calendars.py` is a MODULE reading `data/calendars/*.json` (22 venues incl. `KRX.json`, `US.json`; holidays 2026-01-01 → 2027-12-31 only; `is_trading_day` → `None` outside coverage). No close times by era, regime tags, Fed/SIFMA calendars, `signed_off_by` | F-2; history calendars 1997–2025 are new, OWNER-signed |
| `core/skills` workflows as YAML with decision gates; `core/skills/workflows/macro_daily.yaml` (L785, L917) | `core/skills/workflows.py` is a MODULE that parses `workflows/*.yaml` under `config.skills_root()` (external skills checkout) | F-3 |
| `core/ficc/data`: explicit provider raises, only `auto` degrades to labelled synthetic (L374) | TRUE: `SOURCES = ("auto","fred","yfinance","synthetic")`, `FICCError`. No PIT store, no registry | PIT store is new |
| `core/ficc/macro`: 18-indicator sheet, z-scores, "regime read" (L1117) | TRUE. BL-G06 answered from code: `_regime_from` (`core/ficc/macro.py:161-187`) = threshold rules on 20-session changes and 1-year z-scores (`risk-off` if mean z of VIXCLS and BAMLH0A0HYM2 > 0.75, `risk-on` if < −0.5); NOT a regime model. z/changes are positional over 252/1/5/21/63 observations. Macro page shows "regime chips" (`ui/macro_page.py:135-141`) | F-6 |
| `tests/run_all.py`: engine + quant + FICC acceptance, hermetic (L799) | TRUE; 6 groups (`cockpit, engine, ui, quant, ficc, expansion`), each module exposes `tests() -> [(name, fn)]`; `qa/acceptance_results.json` = 266/266 PASS (README still says 229/245) | Add group `macro/`; keep 266 green |
| `docs/macro_overlay_study.py`, `docs/vol_backtest.py` (L800) | ABSENT (spec marks proposed) | new |
| JSON Schema 2020-12 validation (L3506) | `jsonschema` NOT installed, not in `requirements.txt`/`pyproject.toml` | F-7 |
| `config.py` gains macro artifact dir + KIS allowlist | Neither exists; `trading_dir()`, `ficc_cache_dir()`, `KIS_BASE_URL` exist | add two small items |
| Reference data `/home/claude/quantgen_macro_data/`, `council/*.csv` (L22, L384) | ABSENT on this machine (searched: no `QC_modules*`, `QX_*`, `QF3_dnb*`, `R4*_golden*`, `^KS11`). Local cache `docs/asset_expansion/cache/` ends **2026-09-23/25** (before the snapshot date): `yf_069500.KS` 2007-01-29→2026-09-23, `yf_005930.KS` 2000-01-04→2026-09-23, `yf_SPY` 1995-01-03→2026-09-25, `yf__VIX` 1995→2026-09-25, `yf__VIX3M` 2006-07-17→2026-09-25, `fred_DEXKOUS` 2017-01-02→2026-09-18, `fred_DGS3MO` 1990→2026-09-23, `yf__KS200` = 1 row | Every §11 number and every G-* golden is REFDATA |

---

## C. Schemas and config this area writes or reads

### C.1 `owner_decisions` (rules store; keys and values verbatim from L4135-4152, comments trimmed)
```yaml
version: "2.0.0"
as_of: "2026-10-02"
read_only: true
owner_decisions:      # status: default | owner_set | pending
  D1: {key: risk_layer.korea_caps.template, value: msci_25_50, default: msci_25_50, options: [domestic_max10_or_weight, msci_25_50, pair_35],
       status: default, effective_from: null, rationale: null, refs: []}
  D2: {key: risk_layer.drawdown.hard_stop.level, value: -0.15, default: -0.15, options: [-0.15, "-1.5*sigma_book"], status: default,
       effective_from: null, rationale: null, refs: [cards.R-31_step_down.hard_stop_level]}
  D3: {key: families.reversal.calm_state_downweight, value: not_adopted, default: not_adopted, options: [not_adopted, reopen_after_krx_net_test],
       status: default, effective_from: null, rationale: null, refs: []}
  D4: {key: monitoring.false_demotion_budget_per_year, value: 0.10, default: 0.10, options: [tighten_only_le_0p10], status: default,
       effective_from: null, rationale: null, refs: []}
  D5: {key: sleeves.US.line, value: none, default: none, options: [CME_micro_ES, KRX_listed_SP500_ETF, none], status: pending,
       effective_from: null, rationale: null, refs: [instruments.us_line_choice, cards.R-28_trend_axis.us_sleeve, cards.R-29_US_FUT.us_sleeve_and_line]}
  D6: {key: gate.acceptance_test.cdar_guard.calibration, value: lowest_placebo_false_pass_rule, default: lowest_placebo_false_pass_rule,
       options: [lowest_placebo_false_pass_rule, professors_bootstrap_one_sided_5pct, executives_placebo_p10_margin, qf_blind_margin], status: default,
       effective_from: null, rationale: null, refs: []}
```
Dependent literal keys seen in §7: `families.reversal: {overlay: fixed_1.0, intraday_leg: false, calm_state_downweight: not_adopted}` (L4323); `monitoring.false_demotion_budget_per_year: 0.10` (L4486); `instruments.us_line_choice: {ref: sleeves.US.line}` (L2849).

### C.2 `do_not_build` (rules store; verbatim L4620-4679)
```yaml
do_not_build:
  labels: [harm, null, inconclusive]
  basis: {B: qf3_bootstrap_class_or_share_lt_0.05, E: item_evidence_provisional, G: breaks_P0_P19_or_red_line}
  items: {1: inconclusive_B, 2: harm_B, 3: inconclusive_B, 4: harm_E, 5: inconclusive_B,
    6: {curve_resteepening: harm_B, real_rate: null_B, credit_weights: inconclusive_B, mom_under_rates_stress: inconclusive_E, level_thresholds: inconclusive_E},
    7: null_E, 8: inconclusive_B,
    9: {forecasts_surveys_positioning: inconclusive_E, crowding_cuts: inconclusive_E, consensus_surprise_entries: null_E},
    10: inconclusive_E,
    11: {11a_ml_vol_state_classifiers: harm_E, 11b_range_log_har: admitted, smoothed_regime_probabilities: harm_G,
         unpenalised_hmm_ms_gates: harm_E, complexity_rff_timing: null_E, llm_text_pre_cutoff_backtests: harm_G},
    12: {event_blackouts_24h_and_swing: inconclusive_E, quad_witching_blackout: null_E, expiry_close_fade: inconclusive_E},
    13: inconclusive_E, 14: {rate_differential_models: null_E, foreign_flow_rules: inconclusive_E},
    15: inconclusive_E, 16: inconclusive_E, 17: inconclusive_E, 18: harm_G, 19: harm_G, 20: inconclusive_E,
    21: harm_G, 22: harm_G, 23: harm_G, 24: harm_G, 25: harm_G, 26: harm_G,
    27: {jump_model: inconclusive_E, markov_switching: harm_E, gmm_and_change_point_states: inconclusive_E, prohibition: binding_red_line_E1},
    28: null_E, 29: harm_E, 30: harm_B, 31: harm_G, 32: harm_G, 33: harm_G, 34: harm_G, 35: harm_G, 36: harm_G, 37: inconclusive_E}
  refused_shapes:
    order_path_or_broker_adapter: 21
    multiplier_weight_or_cap_above_1: [2, 8]
    composition_not_min: 31
    regime_model_source_acting_or_displayed: [11, 24, 27]
    smoothed_or_forward_looking_label: 24
    ml_classifier_estimator_gate_or_label: [11, 29]
    conformal_label_layer: 28
    sizing_estimator_max_over_implied: 30
    estimator_change_outside_r30_revision: 25
    header_edit_after_results_md5: [23, 32]   # instrument_book, notional_nav, rebalance, no_trade_band, cost_bp
    krx_stock_book_on_market_gross_scalar: 33
    pooled_or_a_provisional_tier_after_results: 34
    forward_record_cited_as_validation: 35
    kish_or_other_n_eff_rule: 36
    r28_instance_market_kr: 37
    recommended_book_reads_non_pass_multiplier: 22
    value_timed_or_provisional_acting_input: [19, 26]
```
(YAML `null` label: store the string `"null"` in JSON, not JSON null — F-10.)

### C.3 Other constitutional config keys (verbatim)
- `gate.tiers` (L4608-4612): `A: {min_onsets_declustered: 30, decluster_gap: own_lookback, min_stress_episodes_in_sample: 3, min_oos_episodes: 1, pooled_rule: declare_before_any_market_is_run}`, `A_provisional: closed`, `B: {bounds: [0.5, 1.0], external_params: true, verdict_from_backtest: INSUFFICIENT_DATA, forward_record: falsification_only}`, `C: {allowed: false}`.
- `gate.parameter_budget_searched: 8`; `gate.stress_report_window: ["2022-01-01", "2026-10-02"]`; `gate.locked_holdout_start: "2027-01-01"`; `gate.costs: read_from_gate` (L4613-4616).
- `gate.card_header_required: [instrument_book, notional_nav, rebalance, no_trade_band, fill_model, cash_convention, episode_rule_version, family_id, ledger_hash_at_registration, history_first_close, data_span]`; `gate.card_result_required: [timing_profile, ledger_hash_at_run, selection_factor, results_md5]` (L4617-4619).
- `gate.step3.forbidden: [kish_design_effect, revision_count_as_N]` (L4582); `gate.step3.n_gate: max(N_clusters, N_equiv)` (L6247).
- `gate.stats.live_sharpe_multiplier: 0.60` (L4596). `gate.timing.fragility_ratio_max: 0.5`; `lookahead_rows: {mode: timing_probe, scope: [tests, r34_sandbox], tag: synthetic_lookahead, ledger_timing_class: NON-COMPLIANT, production_writes: forbidden}` (L4601-4607).
- `instruments.market_scalar_on_stock_book: refused`; `instruments.us_shares_50bp: single_names_only`; `instruments.header_required: [instrument_book, rebalance, no_trade_band, notional_nav, fill_model, nav_fx_if_non_krw]`; `instruments.notional_source: sleeves.<market>.notional_nav`; `instruments.futures_granularity: {max_contract_share_of_sleeve: 0.05, contract_notional_krw: {KOSPI200: 280e6, mini_KOSPI200: 56e6, CME_micro_ES: 52e6, as_of: "2026-10-02", use: header_check_only}}` (L2840-2846).
- `reproducibility: {seed_study: 11, seed_research_bootstrap: 20261002, record: [git_hash, config_hash, data_snapshot_id, knowledge_utc, seed, results_md5, gate_package_version, gate_package_md5, ledger_hash_at_registration, ledger_hash_at_run], determinism: {canonical_json: sorted_keys_repr_floats_no_whitespace, volatile_fields: [generated_at_utc, git_hash], rng: numpy_pcg64_seedsequence_spawned_children, blas_threads: 1, relative_tol: 1.0e-12}}` (L4680-4684).
- `time: {storage_tz: UTC, decision: close_t_earn_t_plus_1, calendars: effective_dated, decision_instant: close_print_bound_utc}` (L4153-4157).
- Cost table (P10, L582-589): KRX ETF 3 bp; KRX stock 35 bp; US shares via KIS 50 bp; Crypto 10 bp; Futures 5 bp; FX 10 bp; 2× stress each. Not stored in the rules store ("only the floor formula and the instrument metadata live here", L4129).

### C.4 `governance_event` (verbatim L4099-4110; one JSON line per event in `governance_events.jsonl`)
```json
{"$id":"quantgen/governance_event.v2.0","type":"object",
 "required":["schema","schema_version","event_id","utc","kind","book_id","rule_id","key","actor","reason","refs","prev_row_md5"],
 "properties":{
  "schema":{"const":"quantgen.governance_event"},"schema_version":{"const":"2.0"},
  "event_id":{"type":"string"},"utc":{"type":"string","format":"date-time"},
  "kind":{"enum":["halt","rearm","book_state","demotion","package_freeze","package_redesign","header_commit","owner_ruling","calendar_change",
                  "notional_change","admissibility_reweight","binding_share_recompute","binding_change","record_reset","verdict_integrity"]},
  "book_id":{"type":["string","null"]},"rule_id":{"type":["string","null"]},"key":{"type":["string","null"]},
  "old":{},"new":{},
  "actor":{"enum":["owner","operator","runtime","harness","council"]},
  "reason":{"type":"string"},"refs":{"type":"array","items":{"type":"string"}},
  "prev_row_md5":{"type":["string","null"]}}}
```
`prev_row_md5` = md5 of the previous line, null only on the first; chain verified at app start (T-OBS-05, M8). `core/rules` (M0) owns the appender; T-OWNER-01 writes the first event.

### C.5 Common artifact conventions (L3505-3511)
JSON Schema draft 2020-12, one registry keyed by `$id` (base `quantgen/`). Times ISO-8601 UTC with "Z". Every artifact carries `schema`, `schema_version` ("2.0"), `generated_at_utc`, `knowledge_utc`, `git_hash`, `config_hash`, `data_snapshot_id`, `read_only: true`. Closed objects: `additionalProperties: false` on every object schema that declares `properties`, except `extras`, maps, schemas declaring `unevaluatedProperties`, and `model_card_header.macro.v2.0#/$defs/fields`. "No artifact contains an order instruction. Weights are targets for the simulated order book only."
Field classes (L3370): a property added later "is acting until it is classified here, so an unclassified field fails closed". Acting-field validation failure of `macro_state`/`overlay_decision` → `bounds_ok` trips, HALT (OPS) of the books it describes, artifact written to `<artifact_dir>/quarantine/`. Display/context-only failure → artifact written with `extras.validation_errors`, alert, never HALTs. `context_log`, `event_calendar`, `model_card` failing validation → refused, written to quarantine, alert, never HALTs.

---

## D. Tests

Feasibility: **SYNTH** = hermetic with synthetic/inline fixtures; **REFDATA** = needs frozen reference data not on this machine; **OWNER** = owner input, credentials or live sessions.

| Test | Exact assertion | Fixture | Class |
|---|---|---|---|
| T-RO-01 (M0) | Static scan of the whole repository incl. `core/skills` scripts and commands of every workflow YAML finds no order, cancel, withdrawal, deposit-address or transfer call and no import of an order-submission client; `core/engine/orders` reached only through the simulated order book API; every artifact has `read_only: true` | repo source; symbol/AST list inside the test | SYNTH (external skills root scanned only if present — F-3) |
| T-RO-02 (M1; I-01 clause M8) | KIS client accepts only an allowlist of quotation endpoints frozen in `config.py`; any trading or account path raises before a request is built. I-01 with HTTP transport patched records zero non-allowlisted requests. Whether the app key can trade is checked in M1 and recorded. Claude API called without tools; its text never parsed by an acting module | fake transport on `KISClient._get` | SYNTH (allowlist, Claude clauses); OWNER (app-key-can-trade → record "not run") |
| T-HERM-01 (M0) | Macro test suite passes with all network touchpoints patched to raise | existing `_no_network()` pattern `tests/ficc_acceptance.py:31` | SYNTH |
| T-HERM-02 (M0) | After `tests/run_all.py`, `core/rules` and every family ledger are byte-identical to their pre-run state; tests write only to temporary copies of the rules store, ledgers and artifact directory | md5 before/after | SYNTH |
| T-CAP-01 (M0; "cannot emit 0" clause M2) | Any overlay multiplier outside [0.5, 1.0], or any vt/vs > 1.0, fails schema validation and rules-store validation. The overlay layer cannot emit 0 | inline rule objects / artifacts | SYNTH |
| T-CAP-02 (M2; stack clause M7) | 10,000 seeded draws (seed 11) of k ∈ {0,…,5}, overlays in [0.5, 1]^k (endpoints included), vt ∈ [0, 1] (0 and 1 included), ladder ∈ {1.0, 0.5}, post-re-arm cap ∈ {1.0, 0.5}: `composed = vt × min(1.0, overlays, ladder, post_rearm_cap)` and `composed ≥ 0.5 × vt` on every non-HALTED day. A risk limit may take `gross` below it without HALTing. 0.75 and 0.5 compose to 0.5 (never 0.375); binding factor logged. A product-composed path raises. Stack card prints share of days at ≤ 0.25× total exposure and rebound capture | none | SYNTH (property); stack-card numbers 31.0% / 11.2% REFDATA (KOSPI history) |
| T-BASIS-01 (M0 predicate; runtime M4/M7; S2 clause M8) | Every multiplier has `exposure_basis`. S2 applied to momentum raises. vt is not applied to L/S sleeves or to TS trend | inline rule objects | SYNTH |
| T-DNB-01 (M0) | §10 item 11 is split (ML vol-state classifiers prohibited; range-based HAR admitted). Rules-store validation refuses: a regime-model state acting or displayed; a Mondrian conformal label layer; a maintained ML challenger pipeline; `max(SMA20, implied)` sizing; product-composed de-risk stacks; a venue switch after results; a stock book as a market-gross scalar — each "with the §10 item number in the error" (L3391). Each §10 entry is labelled harm / null / inconclusive | one §7.1 object per refused shape (7 asserted; implement and test all 17 `refused_shapes`) | SYNTH |
| T-OWNER-01 (M0) | Each D1–D6 canonical key exists and holds a scalar equal to `owner_decisions.D<n>.value`, and every `{ref: …}` resolves to it. An owner edit flips `status` to `owner_set`, every reference resolves to the new value, and the ruling is written to `governance_events.jsonl`; a literal copy that differs from its key is refused at load. A card header's `owner_decisions` records the values at commit and is checked only at commit | temp copy of the store | SYNTH |
| T-SCHEMA-01/02/03 (M0) | Every spec example validates against its §6 schema (`<…>` placeholders replaced by typed samples); missing required field fails; undeclared field fails. `model_card.macro` validates only with the L5670 field list, each removed in turn → refused. One synthetic artifact/card per rule built from its Outputs list validates | spec examples transcribed | SYNTH |
| T-REPRO-01a (M0) | Every artifact and card records the seed, `git_hash`, `config_hash`, `data_snapshot_id`, `knowledge_utc`, the ledger hashes and `results_md5` | synthetic artifact | SYNTH (repo is not a git repository — F-8) |
| T-COST-02 / T-COST-03 (M0) | 252670 at ₩69 is charged ≥ 72 bp per side; the floor never lowers a table rate. Lowering a cost in a header raises | inline price/tick | SYNTH |
| T-BOOK-01 (M0 header clauses; printed lines M7) | A card without `instrument_book`, `rebalance`, `no_trade_band` and `notional_nav` is refused. A futures line whose one contract exceeds 5% of the sleeve notional is refused (mini KOSPI200 ≈ ₩56m on a ₩0.1bn sleeve); exactly 5% is allowed. A header whose `notional_nav` differs from `sleeves.<market>.notional_nav` at commit is refused. A stock book used as a market-gross scalar is refused | inline headers | SYNTH; `sleeves.<market>.notional_nav` real value OWNER |
| T-PROV-01 (M1) | `pit_value('KOSPI_OFFICIAL_CLOSE', decision_utc=2026-10-02T06:30:30Z, knowledge_utc=…, consumer='R-06', require_session=2026-10-02)` returns `MissingInput("missing")` at knowledge_utc 01:31Z, `MissingInput("provisional_intraday")` at 02:00Z, and 7,003.74 [official_close] at 07:00Z. Rows: vendor 6,943.66 obs_utc 01:30Z, available_at_utc 01:30Z, retrieved_at_utc 01:56Z, provisional_intraday; KIS 7,003.74 available_at_utc 06:30:30Z (calendar_bound), retrieved_at_utc 06:40:45Z, official_close | synthetic store file (exempt from post-close rule) | SYNTH |
| T-FIX-01 / G-POST-01 (M1; rows per §9.0b) | A fixture any of whose close-type rows has `retrieved_at_utc < close_print_bound_utc + 10 min`, or any publication-timed row retrieved before its `publication_instant`, is refused. DLA §7 corrected values regenerate at Level-1 tolerance | refusal: inline; regeneration: `QX_DLA_postpatch.csv`, KRX official closes to 2026-10-02 | SYNTH (refusal) / REFDATA (regeneration; no local substitute — cache ends 2026-09-23, no ^KS11) |
| T-LAG-01 / T-LAG-02 (M1; card clause M7) | Datum with `available_at_utc > decision_utc` in any acting input → backtest raises `LookAheadError` and refuses to write the card; at runtime the books it feeds go HALTED (OPS). A provisional row is treated the same. Audit recomputes `usable_at` independently of `pit_value`. Shifting an input one period earlier must change the result and trip T-LAG-01; positional `shift` on a series with gaps rejected | synthetic series | SYNTH |
| T-SYN-01 (M1) | "auto" provider degrading to synthetic for an acting input → `MissingInput`, `status="synthetic_rejected"`, `fail_closed=true`; allowed and labelled for a context item | existing synthetic provider | SYNTH |
| T-MISS-02 / T-ROLE-01 (M1; risk-model clauses M2; `concentration_bound`/`drawdown_ladder` M5) | Acting input missing/stale → state unchanged, `fail_closed=true`, alert, no interpolation; miss 1 → fail closed; miss 2 → the books it is bound to HALTED (OPS), no other book; a fresh decision resets the counter. Stale risk_model input → `hedge_credit_off = TRUE`, never HALTED. Stale context input → label only. Exception in `market_vol_target`, `concentration_bound`, `drawdown_ladder`, `compose` → HALTED (OPS) for the books it feeds; exception in `hedge_state` → `hedge_credit_off = TRUE`, alert, never HALTED | synthetic store + runtime | SYNTH |
| T-BAR-01 (M1) | A bar-derived close, or a flat-OHLC zero-volume row on a session day, is never stored as a close. Two-source mismatch above 1 bp (index) or any mismatch (stock) → `disputed`, official value used, alert; nothing auto-corrected | inline rows | SYNTH |
| T-H10-01 (M1) | In `run_mode = live`, an attempt to read DEXKOUS for an acting or risk-model input raises | inline | SYNTH |
| T-H10-02 / T-AVAIL-01 / T-TZ-02 / I-06b (M1/M5) | DEXKOUS dated 2026-09-25 usable from the KRX close of Tue 2026-09-29; week of 2026-10-05 usable from KRX close Wed 2026-10-14; DGS10 dated Fri 2015-01-02 → KRX close Tue 2015-01-06; DGS10 dated 2026-10-09 → US close 2026-10-14; CSAT 2025-11-13 close 07:30Z; Sep NFP → `kr_open_gap_session = 2026-10-06`; 2026-10-06 `gap_sessions ≥ 2`, VaR × √max(n_US, 1) | Fed/KRX/NYSE calendars; `data/calendars/KRX.json` has 2026-10-05 and 2026-10-09, `US.json` has 2026-11-26 + 13:00 close 2026-11-27; 2015 and 2025 dates need new calendar files | SYNTH for 2026 dates; OWNER (signed historical calendars) for 2015/2025 rows |
| T-CAL-01 / T-CAL-02 (M1) | A calendar file without `signed_off_by` is refused at load, and every KR acting input fails closed. Every calendar covers ≥ 60 sessions beyond the decision date; `warn` at 60 left, page at 20; outside coverage → OPS HALT `reason = calendar_coverage` | fixture calendar files | SYNTH (mechanism); OWNER (the real signatures; 2027 files before 2026-11-01) |
| T-CTX-01 (M6) | No acting module imports or reads `context_log`, the 18-indicator sheet's values, the R-18 break log or a refusal book (static import check plus a runtime guard) | repo source | SYNTH |
| T-NEFF-01 / T-STEP3-02 (M7 pre-freeze) | E[max Z] = 1.33 ± 0.01 and N_equiv = 6.3 ± 0.4 on QF3's 26-trial matrix (seed 11); padding with 80 near-duplicates moves N_equiv by < 0.5; a card without a ledger hash is refused; no code path computes the Kish N̂; static scan finds no implementation of M ⁄ (1 + (M − 1)ρ̄) | `QX_EX1_qf3_trial_corr_diff.csv` | REFDATA (numbers); SYNTH (refusal + static scan) |
| T-CARD-01 (M7) | Header md5 ≠ committed header → refused. Class or claim change → new revision, ledger incremented. Card without ledger hash or R-26 header fields refused. `displayed_as ∈ {recommendation, insurance}` iff verdict = PASS | inline cards | SYNTH |
| I-08 / T-GATE-01..04 (M7) | ≤ 10% of 300 circular-shift placebos per family and ≤ 2 of 20 per card pass PC-1′ (both legs: point > 0 and p × f ≤ 0.10 at 1×); τ_k = round(252 + k·(T − 504)/19), k = 0…19; five negative controls ∈ {REJECT, INSUFFICIENT DATA}; later runs only re-verify `acceptance_report_md5` and `definitions_md5` | KRX official closes 1997+, US daily histories, drafted CARD-P headers | REFDATA (freeze tier). Local partial: `yf_SPY` (1995+), `yf_069500.KS` (2007+) cannot stand in for the frozen fixtures → gate stays NOT frozen; every card NOT_RUN |
| I-03 (M8) | Recommended book never reads a FORWARD-SIM multiplier, a refusal-book multiplier or a non-PASS factor (assertion on the book builder). It refuses R-04. No recommended or specification book reads the R-11 or R-12 multiplier | synthetic book configs | SYNTH |
| T-SCOPE-01 (M8) | (a)–(h) of L5675: e.g. (c) specification-book NAV at −16% HALTs the specification book only; (d) recommended-book NAV at −16% HALTs the recommended book (RISK); (e) exception inside hedge_state sets hedge_credit_off and HALTs nothing; (f) context_log schema failure HALTs nothing; (h) while R-06 KR is NOT_RUN, a KOSPI close missing on 3 consecutive decisions HALTs `specification:KR` only | synthetic store + runtime | SYNTH |
| T-MONO-01 (M5) | For random multiplier vectors m ≤ m′ elementwise (seed 11) every market's gross and every family's active budget is weakly monotone in its own multipliers, every cross-partial is 0; only exception R-15 K/(K−1), logged | "I-01 fixtures" | SYNTH on synthetic books; REFDATA on the I-01 fixtures |
| §11 snapshot rows (B.11): T-VT-01 (rv20 28.82%, vt 0.694), T-LABEL-01 (2026-10-02 labels), T-CORR-01 (+0.53 ± 0.01; series-lag version gives −0.094), T-MISS-01 (CPI 3.353% ± 0.01; 3.713% must not be produced), T-CAPS-01 (0.755 / 0.685 per book), I-01 (five artifacts; 7,003.74; vt 0.25 on 2026-07-30) | as stated | KOSPI official closes to 2026-10-02, S&P + DGS10 to 2026-09-30, CPI with Oct-2025 gap, KODEX 200 basket, core PCE vintages | REFDATA for every numeric assertion. SYNTH for the property clauses (T-VT-01 warm-up `insufficient_history` → weight 1.0 status `warmup` / `MissingInput`; T-LABEL-01 causality; T-CAPS-01 arithmetic with inline weights 0.298 / 0.225) |

Deferred clauses (§9.0b, L5567-5597) that touch this area: T-BASIS-01 "vt is not applied to L/S sleeves or to TS trend" → M0 as a rules-store predicate on §7.1 `applies_to`; runtime check M4 (L/S sleeves) and M7 (R-14). T-CAP-01 "The overlay layer cannot emit 0." → M2. T-OWNER-01 "the ruling is written to `governance_events.jsonl`" → M0. T-RO-02 "I-01 runs with the HTTP transport patched …" → M8. T-LAG-01 "refuses to write the card" + `timing_probe` exception → M7. T-MISS-02 risk_model clause and exceptions in `hedge_state`, `market_vol_target`, `compose` → M2; in `concentration_bound`, `drawdown_ladder` → M5. I-06c "an acting-field schema error HALTs (OPS) the books the artifact describes" → M8 (`bounds_ok`). The HALT clauses of T-ROLE-01, T-LAG-01, T-MISS-02 stay at M1 (M1 builds the OPS-only per-book runtime). Until M6, tests assert function outputs (`market_vol_target`, `hedge_state`, `estimator_gate`, `concentration_bound`, the runtime), never a built artifact (L6368).

---

## E. Interfaces

Needs from earlier milestones: nothing (M0 is first). From the existing repo: `core.rules.validation.Issue/Report/Severity`; `config.trading_dir()`; `tests/run_all.py` group pattern; `core/quant/validate.py` `DECISIONS`, `GATE`, `md5_of`, `ModelCard`.

Exposes to every later milestone (names proposed, shapes binding):

| Name | Shape | Consumers |
|---|---|---|
| `load_macro_store(path) -> dict` | resolved store (all `{ref}` replaced), raises on a differing literal copy or malformed `{ref}` | all |
| `owner_decision(Dn) -> {key, value, default, options, status, effective_from, rationale, refs}`; `set_owner_decision(...)` | registry entry; ruling appends an `owner_ruling` event | R-07 (D1, D2), R-31 (D2), R-15 (D3), R-25 (D4), R-26/R-28/R-29 (D5), R-21 (D6); Macro page |
| `validate_rule_object(obj, previous, store) -> Report` | ERROR issues name §10 item + label | rules store writes, card header commit, book-builder configuration |
| `dnb_item(n) -> {label, basis, variants}` | from `do_not_build.items` | T-DNB-01, Macro page/docs |
| `assert_overlay(x)`, `assert_vt(x)`, `assert_vs(x)` | `0.5 <= x <= 1.0`; `0.0 <= x <= 1.0` | `core/quant/signals`, `core/quant/risk`, schemas |
| `append_governance_event(kind, *, book_id, rule_id, key, old, new, actor, reason, refs) -> dict`; `verify_governance_chain(path) -> bool` | §6.6 line with `prev_row_md5` | M1 runtime (halt/rearm/book_state), M5, M7 (package_freeze, header_commit), M8 (demotion, verdict_integrity, T-OBS-05) |
| `KIS_QUOTATION_ALLOWLIST` (in `config.py`) | frozenset of exact `/uapi/.../quotations/...` paths (24 today) | `KISClient._get`, T-RO-02 |
| `config.macro_artifact_dir() -> Path` | with `quarantine/` subfolder | artifact writer (M0), builders (M6), workflow (M8) |
| Enums | verdict, disposition, displayed_as, kind, build status, book-id grammar, HALT classes `RISK`/`OPS`, `source_kind`, `instrument_book` | all |
| Cost table accessor (F-5) | `{"krx_etf": 3.0, "us": 50.0, "krx_stock": 35.0, "crypto": 10.0, "futures": 5.0, "fx": 10.0}` bp per side, ×2 stress | R-26 tick floor, every backtest |

---

## F. Ambiguities, contradictions, conservative readings

| # | Issue (lines) | Conservative decision |
|---|---|---|
| F-1 | Spec treats `core/rules` as a generic rules store for macro rule objects (L380, L4123-4131, L6231 "`core/rules/validation` refuses…"); the real `core/rules` models operator order rules (`Rule`: side, size, conditions) and `validation.py` validates those | Add separate macro rule-object model/validation/store files in `core/rules/`; reuse `Issue/Report`; never change `Rule`, `validate()`, `RuleStore` behaviour (inherited tests). §7.1 itself says "proposed; map them onto the store's actual model" (L4689) |
| F-2 | `core/calendars/data/` (L76) assumes a package; `core/calendars.py` is a module, data in `data/calendars/` | Put effective-dated/signed files under `data/calendars/v2/` (proposed) and add functions to the existing module (or a sibling module); do not turn the module into a package unless every import is kept working |
| F-3 | `core/skills/workflows/macro_daily.yaml` (L1189, L917) collides with module `core/skills/workflows.py`, which loads YAML from the external `config.skills_root()` | Ship the YAML in-repo under a new data directory (e.g. `core/skills/macro_workflows/`) and point the loader at it in addition to the external root; T-RO-01 scans in-repo YAML always and the external root only when present (labelled skip otherwise) |
| F-4 | Engine: spec per-book runtime with automatic re-arm (L1178-1180) vs existing single `EngineState` requiring manual acknowledge/re-arm | New per-book runtime module; existing `EngineState` untouched; the new books never share state with the operator engine |
| F-5 | P10 "Costs are defined once, in the gate's code" (L591) vs reality: `COST` dict in `docs/asset_expansion_study.py:60`, absent from `core/quant/validate.py` | Do not create a second copy with different values. Move/define the table once in `core/quant/validate.py` (values unchanged) and have the study import it, or have v2 import the study's constant; never lower. Coordinator picks; either way one definition |
| F-6 | P19 / §3.6 rule 3 (L1124-1126): the sheet "regime read" must be removed if it comes from a regime model; otherwise "may stay … as a descriptive text summary … never presented as a regime state". Code shows threshold rules, not a model, but the page labels it "regime" with `risk-on/risk-off` chips | Keep the computation; relabel the display as a descriptive macro read (no "regime state" wording), never reuse calm / normal / elevated / stressed, never feed `core/quant/signals`, `core/quant/risk` or the engine. z-scores stay display-only and must be computed causally on windows ending at `decision_utc` (L1123) — current positional windows are acceptable for display but may not be thresholded for exposure |
| F-7 | §6 requires JSON Schema draft 2020-12 with `$ref`, `unevaluatedProperties`, closed objects (L3506-3509); `jsonschema` is not installed or declared | Default: a small in-repo validator for the subset the schemas use (type, enum, const, required, properties, additionalProperties, items, `$ref`, `$defs`, minimum/maximum, format date-time, unevaluatedProperties) — no new dependency. Adding `jsonschema` is a coordinator/owner call |
| F-8 | Every artifact records `git_hash` (L3508); the working directory is not a git repository | Write `git_hash: "unversioned"` (string, labelled) and exclude it from replay comparison as the spec already does (`volatile_fields: [generated_at_utc, git_hash]`); `config_hash` and `data_snapshot_id` carry the reproducibility. The §8.1.3 "committed to the repository, an external, timestamped anchor" step (L4820) cannot be met → gate cannot be frozen on this machine (OWNER) |
| F-9 | §7.1 `output_range` refusal distinguishes "an overlay", "vt or vs" but no field says which the rule emits (L4694) | Add an explicit discriminator on the rule object (proposed `output_kind ∈ {overlay, vt, vs, ladder, post_rearm_cap, none}`); when absent treat as overlay → [0.5, 1.0] required (stricter) |
| F-10 | `do_not_build.labels: [harm, null, inconclusive]` (L4621) — YAML `null` parses as null | Store labels as strings (`"null"`, `"null_E"`, `"null_B"`); test asserts each of the 37 items has exactly one string label per variant |
| F-11 | Composition wording: L510 and L80 include `1.0` and `post_rearm_cap`; item 31 (L6207) and T-CAP-02's council row (L5510) omit them; L881 says the store refuses "`combine ≠ min`" while §7.1 names the field `composition` | §3.3 formula governs: `vt × min(1.0, overlays, ladder, post_rearm_cap)`. Field name `composition` (§7.1); no `combine` alias |
| F-12 | §10.3 table cites items "11c, 24, 27" and "11a, 29" (L6238-6239); `refused_shapes` stores `[11, 24, 27]` and `[11, 29]` (L4666-4668) | Numeric id 11 in data; error text names the variant ("11a"/"11c") |
| F-13 | T-DNB-01 asserts 7 refused shapes (L5682); §10.3 lists 16 rows / 17 keys | Implement and test all 17 keys; items without a shape (1, 3–7, 9, 10, 12–18, 20) are documented prohibitions checked in review — add nothing that implements them |
| F-14 | `regime_model` source "acting or displayed" refused, yet BOCPD may be written to the R-18 research log (L656, L6189) | Refuse `source_kind: regime_model` on every rule object; the BOCPD log is written by R-18 code with no rule-object input, no reader in any acting module or display (T-BREAK-01) |
| F-15 | Item 30 predicate: §7.1 `estimator` has only `{name, kind}` (L4700); how "max() over an implied-vol series" is expressed is unspecified | Refuse any sizing rule (`applies_to: market_gross` or vs) with an `acting_exposure` input of `source_kind: implied_vol` unless `estimator.kind == "har"` under an R-30 counted revision; also refuse an estimator `name` matching `max(` |
| F-16 | Item 35 predicate needs an `evidence` field not listed in §7.1 (L4705 "any field") | Card objects carry `evidence[]` entries `{kind, use}`; refuse `kind == forward_record and use == validation`; absent field = no violation |
| F-17 | Macro page: "owner decisions D1–D5 (proposed)" (L762) vs "lists every open owner decision" (L65) vs D6 | List all six with `status`; highlight `pending` (D5) |
| F-18 | L6260 says D3 is enforced "with its `owner_decision: D3` marker (§7)" while L65/L4130 say the JSON store has no marker and uses the registry | Registry `owner_decisions.D3` is the marker; no inline marker key |
| F-19 | D2 option `"-1.5*sigma_book"` is a string in a key that must hold "a plain scalar" (L4142) | Accept number or that exact string; a non-default D2 leaves the hard stop at −0.15 in code until R-07's brief defines σ_book evaluation (fail closed = keep default, log) |
| F-20 | D4 options `[tighten_only_le_0p10]` (L4146) | Accept only `0 < value ≤ 0.10` |
| F-21 | D1/D2 ruling timing: "Whether a ruling needs a notice period, and whether it may take effect while a book is HALTED or near its hard-stop level" is open (L5462) | A ruling takes effect at the next decision of an ARMED book; while a book is HALTED the old value stays until re-arm; logged |
| F-22 | Verdict spelling: prose "INSUFFICIENT DATA" vs enums/config `INSUFFICIENT_DATA` (L4007, L4603) and existing `DECISIONS` | Machine value `INSUFFICIENT_DATA`; `NOT_RUN` only in `overlay_decision` card refs (L3759), never in a card result |
| F-23 | Reference data, council CSVs and the KRX official-close history are absent; local cache ends 2026-09-23/25 | No golden value is asserted from substitute data. Gate package stays unfrozen → every card `NOT_RUN`, disposition per §8.1.2, recommended book = invariants only (vt enters as 1.0). G-* tests are registered with `runs_from` and reported as `skipped: REFDATA` (never silently passed) |
| F-24 | Quant Lab calm/normal/elevated/stressed path-colour labels (L481) not found in code | Verify before M9; if absent, record "nothing to rename" and make sure no new page introduces those names outside R-06's labels |
| F-25 | M1 "First task: KIS quote-field check" needs credentials + 20 live sessions (L44) | Record "not run"; R-27 snapshots, R-08 spread snapshots, R-26 stress-line calibration stay labelled UNVERIFIED |
| F-26 | README test count (229/245) vs actual 266 | Baseline is 266/266 PASS in `qa/acceptance_results.json`; v2 must keep them green |

---

## G. DO-NOT-BUILD items and invariants that bind this area

- All of B.4 (items 1–37) and B.8 (nine PR invariants) bind every area; this brief is their canonical restatement.
- Never build (Quick start L55-63): any order, cancel, withdrawal, deposit-address or transfer path (P0; item 21); any multiplier or vol-target cap above 1.0 (item 2); a product-composed de-risk stack (item 31); a regime-model state, acting or displayed (item 27); `max(SMA20, implied)` sizing, ML vol-state classifiers, a maintained ML challenger pipeline, Mondrian conformal labels (items 30, 11, 29, 28); a stock book as a market-gross scalar, or a venue switch after results (items 33, 32, 23); R-11 or R-12 in any book other than a display-only refusal book; R-04 in the recommended book; any FORWARD-SIM multiplier in the recommended book (item 22); the Kish trial count; a forward record presented as validation (items 36, 35).
- §3.10 "records what would have to hold if the owner ever decided otherwise. It is not a design." No broker adapter, "even behind a flag".
- Still open and CONTESTED — "nothing in v2 either way" (L97-99): jump-model regime engine (QF7-M1), Korean cross-asset futures sleeve (QF5-M8), GMM scenario regimes (QF5-M9). Build none of them.
- Owner-decision rulings are governance events, never acting-parameter edits; an acting-parameter edit outside a card revision demotes the card immediately (L1186). "Lowering a pre-registered cost is never a permitted change" (L382).
- No formal card run, no verdict other than `NOT_RUN`, and nothing in the recommended book beyond the invariants until the gate package is frozen (P11) — which on this machine is blocked by F-8 and F-23.
- Tests write only to temporary copies of the rules store, ledgers and artifact directory (T-HERM-02); no macro test reaches FRED, Yahoo, KIS, FMP, ECOS, Treasury or any other provider (T-HERM-01).
