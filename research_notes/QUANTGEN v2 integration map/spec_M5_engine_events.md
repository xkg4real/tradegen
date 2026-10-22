# spec_M5_engine_events — implementation brief (QUANTGEN v2.0, milestone M5 "Engine and events")

Source: `QUANTGEN_Quant_Council_2026-10-03/claude_code/QUANTGEN_MACRO_INTEGRATION.md` (cited `L<line>`), task file `prep/tasks/M5.json` (TASK-M5-01 … 15). Tech-fund cross-references cite `R3_TF_neural_link.md` as `R3:L<line>`.
Ranges read in full: L1173-1188 (§3.8), L1578-1604 (R-07, R-08), L1618-1638 (R-10), L2888-2963 (R-27), L3262-3360 (R-31), L3800-3858 (§6.3). Also read because the ranges cite them: Quick start L28-100, §3.3 L850-898, §3.5 L961-1114, §3.9 L1189-1254, §4.1 L1300-1345, §4.2 L1386-1449, R-19 rules 4-5 L1866-1944, R-20 L2086-2101, R-22 rule 6 L2348, R-25 L2720-2736, R-26 L2763-2887, §6.1 L3514-3707, §6.2 L3708-3799, §6.6 L4094-4119, §7 L4123-4405, §8.10 L5441-5488, §9.0-9.2 L5489-5707, §9.3.2 rows L5815-5834 / L5893-5899 / L5975-5980, §9.3.3-9.5 L5982-6035, §10 L6039-6260, §11 L6264-6313, §12 L6356-6372.

Repo state checked 2026-10-05: no v2 code exists (`runtime_halt`, `pit_value`, `book_id`, `macro_state`: 0 hits in `*.py`). `core/engine/state.py` is one global `EngineState` whose contract is "This program never re-arms itself" (`state.py:10-13`, tests `engine/test_02-04,78`). `core/engine/orders.py` is a rule-triggered `OrderBook` with manual fills only (`orders.py:167-169`). `core/engine/evaluator.py` `Outcome` = `fired|skipped|rejected|halted` (`evaluator.py:43-47`). `core/calendars.py` is a module; `data/calendars/KRX.json` and `US.json` cover 2026-01-01 → 2027-12-31, holidays and special sessions only (KRX 2026-10-05, 2026-10-09 holidays; US 2026-11-26 holiday, 2026-11-27 close 13:00; KRX 10:00 open on 2026-01-02; no CSAT day). `core/quant/history.py` holds daily `History(dates, closes)` only: no bar record exists. `QuoteFeed` (`feed.py:77-86`) keeps per-symbol miss counts, no success timestamp.

Naming used below follows the sibling briefs: per-book runtime in N `core/engine/books.py` (spec_M1_pit_contracts B0/B15), risk-layer functions in N `core/quant/risk_layer.py` re-exported from E `core/quant/risk.py` (spec_M2_risk F-21). `EngineState`, `EngineRuntime`, `OrderBook.fill` keep their contracts (code_rules_engine D.4, A-1).

Binding rule for silence (L89): "no exposure change, specification book only, fail closed".

---

## A. Scope

| Task | Deliverable | Target files (E existing, N new/proposed) |
|---|---|---|
| TASK-M5-01 | `lookthrough_exposure()`: daily KODEX 200 basket as `acting_exposure` input (books recommended + specification, `halt_after_consecutive_decisions: 5`), carried with age printed, bounds recomputed on current prices; L/I ETFs × L; tick > 10 bp of price → ineligible | N `core/quant/risk_layer.py`; E `core/markets.py` (instrument table from M0-12: `L`, tick eligibility); registry row `KODEX200_PDF` (M1-08) |
| TASK-M5-02 | `concentration_bound()` → `{absolute_bound, active_bound, aggregate_bound, semis_bound, bound, binding_factor}`; template from rules store (D1); `gross = min(composed, bound)` per book; breach test on post-action weights; exception → OPS HALT | N `core/quant/risk_layer.py`; rules store key `risk_layer.korea_caps.*` |
| TASK-M5-03 | RISK class: hard stop on whole-book NAV, 10-session refusal, automatic re-arm, reference reset, `post_rearm_cap` 0.5 for 10 decisions; breach re-arm rule; `halt.causes[]` merge; NAV valuation | N `core/engine/books.py` (extend M1 runtime); N `core/quant/risk_layer.py` (hard-stop evaluation) |
| TASK-M5-04 | Remaining OPS triggers: heartbeat > 60 s, NAV unavailable > 2 decisions, acting risk-layer exception, operator kill; owner-only retire; card on/off/S killed and retired together | N `core/engine/books.py`; E `core/engine/feed.py` (last-success timestamp) |
| TASK-M5-05 | `drawdown_ladder()` → `LadderState` (R-31 names), −8% / −12% steps, 21-session dwell, `min()` composition, specification book only while binding share > 0.10 | N `core/quant/risk_layer.py`; E `core/engine/evaluator.py` (the −12% block) |
| TASK-M5-06 | `evaluator_block()` → `BLOCKED(rule_id, reason)` for new entries during an R-10 window or the −12% step; logged | E `core/engine/evaluator.py` (`Outcome.BLOCKED`) |
| TASK-M5-07 | `evaluator_annotate()`: R-08 raw parity flag, annotation + KIS spread-snapshot request, switch-budget log; no weight change | E `core/engine/evaluator.py`; `macro_state.annotations` is filled by the M6 builder |
| TASK-M5-08 | Event store, window generator, `event_calendar` artifact (`quantgen/event_calendar.v2.0`) | N `core/calendars/events.py` (package layout of spec_M1_calendars B0) or N `core/calendar_events.py` (module layout of spec_architecture F-6); event source data file (owner-maintained) |
| TASK-M5-09 | `kr_open_gap_event`, `KRX_HOLIDAY_GAP` events, `var_display_scale`, overnight-move log; book-builder assertion that tags change no weight | same events module; N `core/quant/risk_layer.py` (`var_display_scale`) |
| TASK-M5-10 | `fill_model(venue)`, `simulate_fill(order, session)`; limit-lock, LP-exempt flag, iNAV residual flag, tracking-error line | E `core/engine/orders.py`; E `core/markets.py` (closing call, random end, LP duties) |
| TASK-M5-11 | Bar record with `bar_end` UTC, closing auction as its own bar, `available_at = bar_end + latency`; loader refuses bar-derived daily closes | E `core/quant/history.py` |
| TASK-M5-12 | Weight-driven simulated books (recommended, specification, card on/off/S, FORWARD-SIM), per-book runtime, persistence of counts and ladder state; no-reallocation property | N `core/engine/books.py`; E `core/quant/signals.py` (`composite_weights`), `core/quant/risk_layer.py` (`risk_layer`) from M4 |
| TASK-M5-13 | Reference-mode reproduction of the literal v1.2 ladder, QF4's 11-session fix, sensitivity lines | N `tests/reference/` (`reference_only=True`; M2-07 scaffold) |
| TASK-M5-14 (spike) | v2 HALT count for KOSPI VT20 1997–2026 (§9.4 item 9) and G-LAD-04 (item 10), printed beside D2 | E `core/quant/backtest.py` replay; D2 owner page (M6 Macro page) |
| TASK-M5-15 (spike) | Event-conditional variance test (DM on the squared gap); pre-registration of the 2027–28 post-holiday VaR breach check | research harness in `docs/` |

All M5 tests go in N `tests/macro_acceptance.py` (suite registered in `tests/run_all.py` beside the six existing suites), each with `runs_from: M5` and a tier (L5496).

---

## B. Build spec, module by module

### B.0 Order of operations at one decision (close of t, one book)

The spec gives the pieces, not the order (F-1). Order adopted:

```
1. nav_t = book_nav(book, ctx)                       # B.8; MissingInput -> hold ladder state, alert, NAV counter +1 (B.6)
2. if HALTED: evaluate every uncleared cause (B.5); if all cleared -> re-arm (B.4 step R)
3. if ARMED:  ladder = ladder_step(state, nav_t)     # B.9; hard stop -> runtime_halt(book, "RISK", "hard_stop")
4. if ARMED:  composed = compose(vt, overlays, ladder = step_mult if steps_act_in_book else 1.0,
                                  post_rearm_cap = 0.5 if post_rearm_left > 0 else 1.0)       # M2 compose, L1058
              cb = concentration_bound(...); gross = min(composed, cb.bound)                  # L873
              target_weights = composite_weights(...); final = risk_layer(target_weights)     # L876-877
              if post_rearm_left > 0: post_rearm_left -= 1
5. breach test on the post-action weights (B.3) -> runtime_halt(book, "RISK", "risk_limit_breach")
6. if HALTED: weights decided at t = 0 (book earns 0 from t+1)                                # L1178 "Effective time"
7. persist book state; append governance events; expose the runtime[] entry (B.17)
```
HALTED "is never an argument of min()" (L874). Every function takes `decision_utc` and the pinned `knowledge_utc` (or `RunContext`), never "now" (L1105).

### B.1 `lookthrough_exposure` (R-07 (1) L1585; R-26 rule 2 L2801-2805; registry L1411)

```python
def lookthrough_exposure(book: Book, decision_utc: datetime) -> Exposure   # L1053: "daily ETF baskets; L/I ETFs at × L (R-07)"
# Exposure: per_name: dict[code, share]   (s_i, share of the line's NAV on look-through, cash in the denominator)
#           basket_date, basket_age_sessions, carried: bool, fail_closed: bool, inputs: tuple[dict, ...]
```
- Input: `pit_value("KODEX200_PDF", decision_utc, knowledge_utc, consumer=<R-07 binding>)`. Binding verbatim (L4254): `KODEX200_PDF: {role: acting_exposure, books: [recommended, specification], halt_after_consecutive_decisions: 5}`. Pair and KOSPI caps: `KRX_MARKET_CAPS_005930_000660_KOSPI: {role: acting_exposure, books: [recommended, specification]}` (L4255; a registry group, L1891).
- Availability (L1411): "Publication instant measured in M1 beside the KIS quote check. Until then `expected_available_utc` = 08:00 KST on the next KRX session (default, judgment), so the decision at the close of t reads the basket dated t−1; … meanwhile the last basket is carried, its age is printed and the bound is recomputed on current prices".
- Recompute on current prices (formula not in the spec, F-4): `s_i(t) = s_i(d0) × (P_i(t)/P_i(d0)) / (P_line(t)/P_line(d0))`, d0 = basket date, P = official closes read through `pit_value` (constituents and the 069500 line are role A, L1409-1411).
- "Leveraged and inverse products count at × L" (L1585 (1)); `instruments.li_etf: {max_tick_bp_of_price: 10, cost_class: KRX_LI_ETF, lookthrough_multiplier: L, eligibility_rules: metadata}` (L4397). A held L/I ETF contributes `w × L × s_i(underlying basket)` per name. Sign of L for inverse products: F-5.
- Eligibility (R-26 rule 2, L2802): "Eligible only if the tick is ≤ 10 bp of the price." `eligible = tick(price, date) / price <= 0.0010`; exactly 10 bp is eligible. ETF tick table (L2803): "₩1 below ₩2,000 and ₩5 at ₩2,000 or more from 2023-12-11; earlier ticks come from the KRX notices (owner action)". "An instrument whose tick table cannot be read for the date is not tradable in the simulated book" (L2863).
- Failure (R-19 rule 4, L1866-1871): `MissingInput` → carry the last basket, `fail_closed = true`, alert, the (book, series) input counter +1; HALT (OPS) when the counter "reaches that binding's `halt_after_consecutive_decisions`" = 5 (L1870). "A look-through input that fails beyond its declared misses is an OPS trigger (R-19 rule 4), not a breach" (L1178). `KODEX200_PDF` has a non-default limit, so it does not feed the book counter (L1869: "with the default limit").
- A book that has never read a basket stays DISARMED (arming needs every bound acting input fresh, L1180).

### B.2 `concentration_bound` (R-07 (2)-(6) L1585; §3.3 L873, L896; schema L3593-3604; config L4331-4344)

```python
def concentration_bound(market: str, decision_utc: datetime, template: str) -> ConcentrationBound
# L1054: {absolute_bound, active_bound, aggregate_bound, semis_bound, bound = their min, binding_factor};
#        per book: gross = min(composed, bound), binding_factor 'none' when composed <= bound (R-07)
```
Definitions (verbatim descriptions L3597-3600; all shares are "a share of Korea sleeve NAV on look-through (cash in the denominator), met through g", L1585 (3)):

| Field | Formula | Under `msci_25_50` on 2 Oct 2026 |
|---|---|---|
| `absolute_bound` | "template single-name level / look-through share" = `single_name_max / max_i s_i` | 22.5 / 29.8 = **0.755** (L896) |
| `active_bound` | "min over names of 0.05 / (s_i - b_tilde_i)", for every name with `s_i > b̃_i` (L1585 (4), config `active_bound`, L4340) | at most 0.05 / (0.298 − 0.225) = **0.685** ("an upper bound: it takes b̃ for Samsung at the 22.5% cap; the risk layer computes b̃ on the day's basket", L896) |
| `aggregate_bound` | "aggregate template limit / look-through share of names above 4.5%" = `aggregate_max / Σ s_i [s_i > names_above]` | not printed (0.45 / 0.538 ≈ 0.836 if only the pair exceeds 4.5%; does not bind) |
| `semis_bound` | "0.50 / look-through semiconductor share of sleeve NAV" (R-07 (5)) | `null` in the §6.1 example (L3684); pair alone is 53.8% of KODEX 200 (L1585 (5)) |
| `bound` | min of the non-null bounds | 0.685 |
| per book `gross` | `min(composed, bound)` | recommended:KR `composed 1.0 → gross 0.685`; specification:KR `composed 0.694 → gross 0.685`; `binding_factor: "active_single_name"` in both (L3685-3686, L6310) |

- Active single-name cap (R-07 (2)): `w_i − g·b̃_i ≤ 0.05` of NAV, `b̃` = "the benchmark b̃ capped under the template"; key `active_single_name_cap_nav: 0.05` (L4339). On an ETF line `w_i = g·s_i`, hence `g ≤ 0.05/(s_i − b̃_i)`. Capping algorithm for `b̃`: F-6.
- Meeting a binding cap (R-07 (4)): "First lower the ETF line's weight: g_KR ≤ min(vt, limit_k / look-through share_k, 0.05 / (s_i − b̃_i) …)". `meet_cap_order: [lower_etf_line_weight, ex_pair_basket_only_if_owner_and_stock_card_pass_and_limit_lock_flags]` (L4343). The ex-pair basket route is closed in v2.0 (no stock-book card has passed).
- Template read from the rules store through D1's canonical key `risk_layer.korea_caps.template` (value `msci_25_50`), never a literal (T-OWNER-01). Templates verbatim (L4334-4338):
  ```yaml
  templates:
    msci_25_50: {single_name_max: 0.225, names_above: 0.045, aggregate_max: 0.45, review: [quarterly, on_breach],
                 breach_single_name: 0.25, breach_aggregate: 0.50}   # targets bound g daily; a breach is above the hard levels after the action
    domestic_max10_or_weight: {single_name_max: "max(0.10, market_cap_weight)"}
    pair_35: {pair_max_share_of_sleeve_nav: 0.35}    # look-through, cash in the denominator (R-07 (3))
  ```
- "The daily bound g uses the target levels (22.5% / 45%) on every decision" (L1585 (3)). The semiconductor cap "is never measured as a share of the invested long book … so it is never a standing breach" (L1585 (5)); `semis_max_share_of_sleeve_nav: 0.50` "default, judgment … reviewed when the pair's share falls below 0.35".
- `binding_factor ∈ {none, absolute_single_name, active_single_name, aggregate, semis}` (L3603). Ties: report the factor named first in "both bounds bind, the active one first" (L896), i.e. the lowest bound; exact ties resolved in the enum order above (F-7).
- Reported (R-07 (6); `report: [pair_lookthrough_share, pair_risk_contribution]`, `report_by_book: true`): `pair_share_kospi`, `pair_lookthrough_share`, `pair_risk_contribution`, each bound, `by_book{book_id: {composed, gross, binding_factor}}`. Whenever a limit binds, write the factor to `overlay_decision.binding` and a line to `overlay_decision.reasons` (L897, L3751).
- Covariance note (R-07 (7)): "Treat Korea gross as semiconductor exposure in the covariance. Shanghai, HSI, TAIEX and Nikkei stay in the Korea covariance, on synchronous or lagged returns"; `korea_covariance_extra: [SHANGHAI, HSI, TAIEX, NIKKEI]` (L4364) — built in M2 (spec_M2_risk B.9); M5 adds nothing.
- Fail closed: an exception inside `concentration_bound` → `runtime_halt(b, "OPS", "acting_risk_layer_exception")` for the books it feeds (L1178; reuse M2's `guard_acting`). A failed input → previous bound state carried on the last basket, `fail_closed = true` (B.1). The floor `composed ≥ 0.5 × vt` is asserted on `composed`, never on `gross` (L881).
- Scope: recommended and specification books of KR only. "Card evaluation books exclude the hard stop and caps and print a `with_risk_layer` line (R-22 rule 6)" (L1590, L2348).

### B.3 Risk-limit breach (class RISK)

- Definition: "a 'breach' is a look-through weight above the hard levels (25% / 50%) after the prescribed action, which is logged and is the R-07 risk-limit breach of §3.8" (L1585 (3)); "an R-07 limit that its prescribed action (lowering g on the ETF line; carrying a limit-locked order, R-27) cannot meet by the next decision" (L1178). "A limit met by lowering g is a binding bound, never a breach, and never returns 0" (L1178).
- Test, at each decision: build the post-action weights = target weights with every carried (non-fillable) order left at its held weight; breach iff any look-through single-name weight > `breach_single_name` (0.25) or the aggregate of names above 4.5% > `breach_aggregate` (0.50). On an ETF line with a fillable line this is never true.
- On breach: `runtime_halt(book, "RISK", "risk_limit_breach")`; re-arm per B.4 (no reference reset).

### B.4 RISK class: hard stop, refusal window, automatic re-arm, post-re-arm cap (R-07 L1586; §3.8 L1179; config L4349-4352)

Config verbatim:
```yaml
drawdown:
  reference: whole_book_nav            # per-market attribution printed
  composition: min                     # with the overlays (R-02)
  steps: cards.R-31_step_down          # -8% / -12% totals, 21-session dwell; specification book while the binding share > 0.10
  hard_stop: {level: -0.15, alt: "-1.5*sigma_book", reference: hwm_since_last_rearm, action: book_HALTED, class: RISK,   # level: canonical key of D2
              scope: own_book_nav, rearm: automatic, rearm_refused_sessions: 10, rearm_calendar: book_primary_market,
              rearm_resets: [hwm_hard, ref_step], post_rearm_cap: 0.5, post_rearm_sessions: 10, post_rearm_cap_in_min: true,
              idempotent_while_halted: true, log: governance_review_event, protection_claim: false}
```
- Trigger: `dd_hard = nav_t / hwm_hard − 1 <= hard_stop_level` (L3283-3287); `<=` so "exactly −15.00% at the close of t" triggers (T-HALT-01, L5674). Guard the float edge on the triggering side (e.g. `nav_t <= hwm_hard * (1 + level) * (1 + 1e-12)`).
- `hard_stop_level` is read through `{ref: risk_layer.drawdown.hard_stop.level}` (L3327, "never a literal copy (T-OWNER-01)"). D2 option (b) `-1.5*sigma_book`: "σ_book is the book's declared target vol, else its trailing-756 realised vol frozen at each re-arm" (L1586); not built until an owner ruling (F-8).
- "The hard stop is evaluated on the NAV of the book it belongs to, and its HALT applies to that book only" (L1586). Books: every recommended and specification book; "card and FORWARD-SIM books exclude it (R-22 rule 6)" (L5400), except R-31's card book (L2348).
- Timeline (L1179, L1586, T-HALT-01, T-STEP-05), sessions of "the book's primary-market calendar (KRX for a KR book; a whole-book NAV spanning markets uses the book's declared primary market)":

| Decision at close of | State | Weights decided | Notes |
|---|---|---|---|
| t (breach) | ARMED → HALTED (RISK) | 0 | `rearm_not_before` = decided_session t+10, set once; `clear_steps()`; governance event `halt` ("governance review event", no protection claim) |
| t+1 … t+9 | HALTED | 0 | ladder not evaluated, references frozen (L3285); book earned 0 on t+1 … t+10 |
| t+10 | HALTED → ARMED, automatic | first capped weights | step R below; "the operator's acknowledgement is logged but never required" |
| t+10 … t+19 | ARMED | `post_rearm_cap` = 0.5 inside `min()` | 10 decisions, earning t+11 … t+20; "exposure ≤ 0.5 × vt, not an absolute 0.5" |
| t+20 onward | ARMED | normal | — |

- Step R (re-arm): `engine_state = ARMED`; if a hard-stop cause was in the set: `hwm_hard = ref_step = nav` at re-arm ("the hard-stop and step references reset to the NAV at re-arm"); if any RISK cause was in the set: `post_rearm_left = 10`, `post_rearm_cap_until` = re-arm decided_session + 9 sessions ("the last decided_session whose weights carry post_rearm_cap 0.5 … t+19 after an automatic re-arm at t+10", L3620); governance event `rearm` (actor `runtime`).
- Risk-limit breach (L1179): references "do not reset, and the book re-arms only at the first decision at or after the close of t+10 at which the limit is met: the target weights the book would hold on re-arming, after the prescribed action (lowering g; carrying a limit-locked order, R-27), satisfy the limit, so a HALTED book's zero exposure never counts as meeting it". Cap window as above, "starting at the actual re-arm decision".
- Idempotence: "A second trigger while HALTED changes nothing" (L1586); a second `halt()` leaves `rearm_not_before` and both references untouched (T-STEP-05).
- "I-04b requires the book to re-enter after every HALT. The hard stop makes no protection claim." (L1179)

### B.5 `runtime_halt` / `runtime_rearm` and `halt.causes[]` (L1081-1086, L1179; schema L3611-3619)

```python
def runtime_halt(book_id: str, cls: Literal["RISK", "OPS"], reason: str) -> None   # that book only; idempotent per cause; a new cause joins halt.causes[]
def runtime_rearm(book_id: str, mode: Literal["auto", "operator"], operator: str | None = None) -> None
```
M1 ships these for class OPS; M5 adds class RISK, the operator-mode causes and the merge rules:
- Same cause while HALTED: no change ("never extends `rearm_not_before` and never resets a reference").
- Different cause: appended to `halt.causes[]` as `{class, reason_code, since_utc, rearm_mode, rearm_not_before, cleared_utc}`; "the top-level `class`, `reason_code` and `since_utc` restate `causes[0]`, and the top-level `rearm_mode` is `operator` while any uncleared cause needs the operator, else `auto`".
- "the book re-arms only when every cause has cleared under its own rule (a RISK cause after its refusal window and, for a breach, its cure; an OPS cause when cleared; an operator-mode cause by the operator)".
- "References reset only if a hard-stop cause was in the set, and `post_rearm_cap` applies if any RISK cause was, its window starting at the actual re-arm decision however late another cause made it; the ladder is not evaluated while HALTED".
- OPS re-arm: "HALTED until the cause clears (input fresh, heartbeat restored, artifact valid, NAV available, calendar signed); the book re-arms automatically at the first decision at which the cause has cleared, except after a lag-audit violation or an acting-artifact schema failure, which needs an operator re-arm once the fix's test passes. No refusal window, **no reference reset**, no post-re-arm cap." Config: `ops_rearm: {when: cause_cleared, operator_required_after: [lag_audit_violation, acting_field_schema_or_bounds_failure], reference_reset: false, post_rearm_cap: false}` (L4360-4361).
- `runtime_rearm(book, "operator", operator)` marks operator-mode causes cleared (`ack_by`, `ack_utc`, `cleared_utc`); the state change happens at the next decision step (B.0 step 2), which is "the operator's re-arm decision" for the cap window (T-HALT-01).
- "Every HALT and re-arm is a governance event (`governance_events.jsonl`, §3.9)": kinds `halt`, `rearm`, `book_state` (L4104).
- Reason codes. Config tokens (L4354-4358): `RISK: [hard_stop, risk_limit_breach]`; `OPS: [lag_audit_violation, acting_field_schema_or_bounds_failure, acting_input_fail_closed_beyond_declared_misses, feed_heartbeat_loss_60s, acting_risk_layer_exception, whole_book_nav_unavailable_gt_2_decisions, calendar_coverage, operator_kill, acting_step_error_beyond_limit]`. Other literal strings in the spec: `"acting_input_stale:<series_id>"` (L1951), `reason = calendar_coverage` (L2090), `"operator_kill"` (L1186), `run_error` (L1243, T-OBS-04). Mapping: F-9.
- Never a trigger (config `never_halt_on`, L4362-4363): `[risk_model_input_stale_or_failing, hedge_state_exception, context_input_stale, disputed_input, warmup_input_before_first_armed_decision, input_bound_only_to_other_books, display_or_context_field_validation_failure, context_log_or_event_calendar_validation_failure]`.
- The per-book hooks never call `EngineState.halt()`; the operator engine's global `NO_DATA` / `STALE_DATA` halts are unchanged (code_rules_engine A-2).

### B.6 OPS triggers added in M5 (L1178, L6367)

| Trigger | Rule | Config / reason | Re-arm |
|---|---|---|---|
| Feed heartbeat | "feed heartbeat loss > 60 s during a session (new intraday simulated entries are BLOCKED at once; the book re-arms automatically once the feed has been restored for 5 minutes, default, judgment; a HALT cleared before the next decision changes no weight)"; "a HALT raised intraday (heartbeat) blocks new intraday entries at once and applies to the weights decided at that session's close" | `heartbeat: {loss_s: 60, blocks_new_intraday_entries: immediately, auto_rearm_after_restored_min: 5}` (L4359); `feed_heartbeat_loss_60s` | auto after 5 min restored |
| Whole-book NAV | "whole-book NAV unavailable on more than 2 consecutive decisions (R-25)"; binding `NAV_LINE_CLOSES … halt_after_consecutive_decisions: 3` (L4248); `monitoring.nav_unavailable_ops_halt_after_decisions: 2` (L2724) | `whole_book_nav_unavailable_gt_2_decisions` | auto when NAV available |
| Acting risk-layer exception | "an exception in an acting risk-layer function (`market_vol_target`, `concentration_bound`, `drawdown_ladder`, `compose`)" | `acting_risk_layer_exception`, `halt.component` = function name | auto when the function returns |
| Calendar coverage | "a decision date outside calendar coverage (T-CAL-02)" | `calendar_coverage` (built in M1; M5 verifies, F-10) | auto when "calendar signed" |
| Operator kill | "`runtime_halt(book_id, "OPS", "operator_kill")`: logged as a governance event and re-armed by the operator; it is never a demotion, except that a kill of a card's forward books is an operational integrity trigger" (L1186) | `operator_kill`, `rearm_mode: operator` | operator |
| KODEX basket | failure at its 5th consecutive decision (B.1) | OPS, never RISK | auto at the first fresh decision |

- NAV unavailable, decisions 1-2: "the step state is held and an alert raised. The hard stop (R-07) stays armed" (L3337); R-25: "statistical triggers are suspended and alerted, and operational triggers stay live" (L2736). "A NAV-input failure HALTs (OPS) only a book whose `NAV_LINE_CLOSES` binding has role `acting_exposure`; a FORWARD-SIM book (display-only, role `forward_sim`) never HALTs on it: the decision is marked failed-closed, printed, and counted toward §8.8 (b)'s 10% budget" (L1181). `pit_value` never raises for the NAV consumer (L1888).
- Heartbeat scope: only books that read the `QuoteFeed` ("A global failure (… the `core/engine` QuoteFeed) HALTs every book that reads it; it never HALTs 'the engine' as such", L1178). The v2.0 daily books read closes from the PIT store, so no default book is bound (F-11). `QuoteFeed` needs one new read: the instant of the last successful fetch.

### B.7 Runtime states per book (L1180)

- Book ids: `recommended:<market>`, `specification:<market>`, `forward_sim:<rule>`, `refusal:<rule>`, `card:<card_id>:<on\|off\|S>`.
- **DISARMED**: "the initial state of every book and the state of a retired book; it holds no simulated position, its artifacts carry `engine_state: DISARMED`, and no forward record runs."
- **DISARMED → ARMED**: "automatic, from the initial state only (a book that has never been ARMED), at the first decision at which every acting input bound to the book is fresh and past warm-up, the calendars cover ≥ 60 sessions ahead (T-CAL-02) and, for card books, the header is committed; logged as a governance event." (M1.)
- **ARMED or HALTED → DISARMED**: "owner action only (retiring a book), logged. A retired book never re-arms; a card's books restart only under a new card revision, with R-25's lockout."
- Card trio: "A card's forward on, off and S books are retired together, never singly, and an operator kill of one of them kills all three; such a kill is an operational integrity trigger (R-25)". "Every other HALT stays book-scoped, and every HALTED or DISARMED decision of the three books counts toward §8.8 (b)'s 10% budget (once per decision, however many of the three it affects)." "Retiring them while the card's factor acts in the recommended book first removes the factor from that book (a governance event, treated as a demotion for R-25's lockout)."
- M5 API (proposed): `retire_book(book_id, owner: str, reason: str)`; `operator_kill(book_id, operator: str)` (expands a `card:<id>:*` id to all three; emits the integrity-trigger record M8 consumes).
- HALT scope (binding, C-1, L1178): "A trigger HALTs only the books whose own NAV breached, whose own artifact failed acting-field validation, or that read the failed input or component through an `acting_exposure` binding". `macro_state.flags.engine_state` reports the market's recommended book; `runtime[]` reports every book.

### B.8 NAV valuation (L1181)

```python
def book_nav(book_id: str, ctx: RunContext) -> float | MissingInput      # proposed name
```
- "Whole-book NAV (the NAV of one book id, all of its sleeves included; in v2.0 only R-14's `multi_line` card books span markets) for R-07, R-31 and R-25 is evaluated at each decision instant from the latest official closes usable at that instant (point-in-time; bound per book through `NAV_LINE_CLOSES`, R-19 rule 5), converted to KRW through the book's declared `nav_fx` (R-26), with per-market attribution printed."
- Reads: `pit_value(<line close>, …, consumer="nav")`, `consumer="nav_fx"` for non-KRW lines (`USDKRW_1530_SNAPSHOT` live, `ECOS_1530_CLOSE` history; role of the book it values, L1887).
- Accrual: weights decided at the close of t are "priced at the close of t in the simulated order book and earn the return from close(t) to close(t+1)" (L1314); costs = pre-registered rate with the tick floor (M0-12 `cost_per_side`) on `|Δw|`. Reuse M2's costed engine for the arithmetic; cost-timing convention is the one the cost/gate brief fixes (spec_architecture F-20).
- "never one sleeve's NAV; per-market attribution is printed only for a book that spans markets" (L1586).

### B.9 `drawdown_ladder` (R-31 L3270-3311; R-07 steps L1587; §3.8 L1182)

```python
def drawdown_ladder(nav_path, decision_utc: datetime) -> LadderState     # L1055
# LadderState{hwm_hard, ref_step, step_mult in {1.0, 0.5}, dwell_left, block_new_entries: bool, halted: bool,
#             rearm_not_before, post_rearm_left, binding_share}          # L1056-1057, L3271; "R-31's names are binding"
```
Implement one pure step function and fold it over the path (the fold is `drawdown_ladder`; the runtime calls the step once per decision and persists the state). Algorithm verbatim (L3278-3303), "Levels are in % of **whole-book NAV**. Multipliers are totals, never cumulative. Composition is by `min()`.":
```python
# at the decision at the close of t, setting the multiplier for t+1 (the hard-stop part is R-07's, shown for the references)
hwm_hard = max(hwm_hard, nav_t)                       # resets only at re-arm (R-07)
if dwell_left == 0:
    ref_step = max(ref_step, nav_t)                   # running peak since the last reset
dd_hard = nav_t / hwm_hard - 1
dd_step = nav_t / ref_step - 1
if book.halted:                                       # not evaluated while HALTED; references frozen until re-arm (R-07)
    pass
elif dd_hard <= hard_stop_level:                      # default -0.15 (D2) -> R-07 HALTED (RISK), review event; halt() is idempotent
    halt(); clear_steps()
elif dwell_left > 0:                                  # inside a 21-session time box
    step_mult = 0.5
    dwell_left -= 1
    if dd_step <= -0.12:
        block_new_entries = True                      # escalation adds the block; sizing and clock unchanged
    if dwell_left == 0:
        ref_step = nav_t                              # step spent: its reference resets; the hard-stop reference does not
elif dd_step <= -0.12:
    step_mult, block_new_entries, dwell_left = 0.5, True, DWELL - 1     # DWELL = 21 sessions incl. the first
elif dd_step <= -0.08:
    step_mult, block_new_entries, dwell_left = 0.5, False, DWELL - 1
else:
    step_mult, block_new_entries = 1.0, False      # the block, like the 0.5x, covers the session after the last dwell decision
composed = vt * min(overlay_1, ..., overlay_k, step_mult if steps_act_in_book else 1.0, post_rearm_cap)
```
- "At re-arm (R-07), both references reset to the NAV at re-arm." `clear_steps()` = `step_mult 1.0, block_new_entries False, dwell_left 0`.
- Consequence to test: a trigger gives 0.5× on exactly 21 consecutive decisions (the trigger decision + 20 dwell decisions); at the 21st, `ref_step = nav_t`; `hwm_hard` is untouched; a later `dd_hard <= −0.15` HALTs "even though `dd_step` is shallower" (T-STEP-01).
- Config verbatim (`cards.R-31_step_down`, L3314-3328; `risk_layer.drawdown.steps` points to it):
  ```yaml
  steps: [{dd: -0.08, mult: 0.5}, {dd: -0.12, mult: 0.5, evaluator_block_new_entries: true}]   # totals, non-cumulative
  dwell_sessions: 21
  step_reference: running_peak_since_last_reset    # resets at dwell end and at re-arm
  hard_stop_reference_resets_at_dwell_end: false   # R-07 reference; resets only at re-arm
  composition: min
  denominator: whole_book_nav
  binding_share_threshold: 0.10                    # > 0.10 -> specification book until PASS
  binding_share: {book: recommended_without_steps, span: declared_history, computed_at: [header_commit, composition_change],
                  window: full_never_trailing, compare: "n_bind / n_sessions > 0.10", disposition_if_le: INVARIANT_STEP}
  judged: {incremental_on: declared_book_without_steps, comparator: S}
  claim: "protection in persistent drawdowns; time-boxed; no Sharpe claim"
  hard_stop_level: {ref: risk_layer.drawdown.hard_stop.level}   # D2 (Quick start); never a literal copy (T-OWNER-01)
  status: SPECIFICATION_BOOK
  ```
- Fail closed (L3336-3339): "If the whole-book NAV is unavailable, the step state is held and an alert raised. The hard stop (R-07) stays armed." "A ladder path composed by product raises (R-02)." "With a binding share > 10% and no PASS, the recommended-book builder refuses the step multiplier (I-03)." An exception in `drawdown_ladder` → OPS HALT of the books it feeds (T-MISS-02 M5 clause).
- Outputs (L3332-3334): `macro_state.flags.ladder_step ∈ {none, step_-8, step_-12, hard_stop_-15}`, `flags.ladder_dwell_left`, `flags.block_new_entries`; `hwm_hard` and `ref_step` per book in `macro_state.runtime[]`; `overlay_decision.multipliers[]` with `rule_id: R-31` and its card verdict; `overlay_decision.ladder ∈ {0.5, 1.0, null}`; `model_card.macro.printed = {binding_share, n_halts, persistence_check}` (M7).

### B.10 Where the steps act (L3305-3307, L886-887, L1587)

- `steps_act_in_book(book_id)`: `specification:*` → True. `recommended:*` → True only with disposition `INVARIANT_STEP` (binding share ≤ 0.10, "frozen with the R-31 header") or an R-31 PASS; otherwise the step multiplier and the block enter as 1.0 / False there, and "The recommended book carries the hard stop (R-07) only" (T-STEP-04).
- Binding share = `n_bind / n_sessions`, "the share of sessions with `step_mult < 1` on the declared book over its declared history … computed per market book on the book's current composition without the steps … at the R-31 header commit … never computed on a trailing window". That computation is M7. Until a header exists `binding_share` is null and the steps act in the specification book only (§11 L6311: "Ladder steps act in the specification book only until R-31's CARD-P passes (Korea VT20 binding share ≈ 19%)"); `flags.ladder_steps_act_in = "specification"` (L3678).

### B.11 `evaluator_block` (L1079, L1183; R-10 L1634)

```python
def evaluator_block(rule_id: str, decision: Decision, state: MacroState) -> Decision   # → BLOCKED(reason), new entries only
```
- "`core/engine/evaluator(rule, quote) → decision` returns `BLOCKED(rule_id, reason)` for any **new-entry** decision while an R-10 event window or the −12% step is active. Holds and exits are never blocked. The backtest applies the same rule at daily resolution. **R-08 is no longer a block**".
- Add `Outcome.BLOCKED = "blocked"`. `rule_id` is the blocking macro rule (`"R-10"` or `"R-31"`); the existing `Decision.rule_id` is the operator rule's 12-hex id, so carry the macro id as the prefix of `reason` (`"R-10: US_CPI window 12:25Z-14:00Z"`); nothing is written to the book for a block. If a new `Decision` field is added, extend `runtime._persist`/`_restore` (`runtime.py:371-374, 400-405`) or it is lost.
- Inputs from `state`: active windows for the decision's market at the decision instant (B.13) and `block_new_entries` of the book where the steps act (B.10). Window action → what is blocked: `evaluator_block_new_intraday_entries` → new intraday simulated entries of that market; `evaluator_block_new_futures_entries` → new futures entries; `annotate_only` → nothing.
- "new entry": F-12. Heartbeat loss also blocks new intraday entries "at once" (B.6).
- "Log every window hit and every evaluator BLOCKED decision." (L1637; §12 L6367).

### B.12 `evaluator_annotate` — R-08 (L1592-1603; config L4371-4373)

```python
def evaluator_annotate(rule_id: str, state: MacroState) -> Annotation                  # R-08: annotation + KIS snapshot request
```
- `flag(D) = VIX(D) ≥ VIX3M(D)`. "The threshold is fixed at parity and **never tuned**. **Clearing rule: the raw parity flag.** The annotation is on for every input date D with VIX(D) ≥ VIX3M(D) and clears at the first D with VIX(D) < VIX3M(D), with no hysteresis. It applies from the first decision after the 16:15 ET VIX close: the US close of D+1 and the KRX close of K ≥ D+1."
- Inputs: "FRED `VIXCLS` and `VXVCLS` (the official close of D is 16:15 ET, §4.1); the VIX/VIX3M snapshot at 16:00 ET, stamped `live` (R-13)". Role C (context, L1426): a stale input is labelled, never a failure. "The registry names the production channel of the R-08 annotation" (L1426).
- Config verbatim: `annotations: vix_ts: {condition: "VIXCLS >= VXVCLS", threshold: 1.0, tuned: false, clearing: raw_parity_flag, action: annotate_only, request_kis_spread_snapshots: true, from: "first decision after the 16:15 ET VIX close", switch_budget_per_year: 14.0}`.
- Effect: "On every flag day the evaluator writes an annotation (`macro_state.annotations.vix_ge_vix3m`) and requests KIS spread snapshots for the traded lines (subject to the KIS quote-field check, QF1-A25). **No book's weights change**: no BLOCKED decision, no cut, no re-add (an assertion in the book builder)."
- `Annotation` (proposed shape): `{rule_id: "R-08", vix_ge_vix3m: bool, input_date: date, notes: tuple[str, ...], kis_snapshot_request: {lines: tuple[str, ...], requested_utc, status: "queued" | "unverified_not_sent"} | None}`. The request is a record for the data layer (read-only quotation endpoints only, T-RO-02); while the KIS quote check is "not run" the record is written with `unverified_not_sent` (L44: "those features stay labelled UNVERIFIED").
- Switch log: "Switches above 2× the budget of 14 a year are logged for review (a logging rule for this annotation only; card switch triggers follow R-25's 99th-percentile rule)" → log when flag transitions in the trailing year exceed 28 (window: F-13). A transition is one on→off or off→on change (G-R08-01: 132 spells in 4,735 days = 14.0 transitions a year).
- Record only: the CARD-P REJECT (G-R08-02) stays on file; no code path may cut or re-add on this flag (§10 items 3, 4).

### B.13 Event store, window generator, `event_calendar` (R-10 L1625-1633; §6.3; config L4374-4386)

Entry: `{event_id, type, region, scheduled_utc, status ∈ {scheduled, released, cancelled, delayed}, source}` (L1625). "Windows expire automatically when an event is cancelled. Example: the Oct-2025 CPI was never published."

Config verbatim:
```yaml
events:                                  # core/calendars; evaluator blocks on simulated entries only (R-10)
  us_cpi_nfp: {block_new_intraday_entries_et: ["08:25","10:00"], resume_et: "10:00"}
  us_leaky_releases_pre_minutes: 30
  fomc: {block_new_intraday_entries_et: ["13:45","15:00"], resume_rule: "VIX<pre14 else 15:30", pre_fomc_long: false}
  bok_decision: {kospi200_futures_block_kst: ["09:45","10:15"], equity_daily_change: none}
  bok_press_conference: {kospi200_futures_block_kst: ["11:00","11:45"], equity_daily_change: none}
  kr_open: {block_first_session_minutes: 30, window_kst: ["09:00","09:30"], late_open_window_kst: ["10:00","10:30"],
            late_open_days: [first_trading_day_of_year, csat]}   # = time.markets.KR.open_no_entry_minutes (R-10)
  kr_open_gap_event_types: [US_CPI, US_NFP, FOMC, HYPERSCALER_EARNINGS]
  multi_session_gap: {tag: gap_sessions, gap_sessions_min: 0, var_display_scale: "sqrt(max(n_us, 1))", report_separately: true, gross_rule: false}
  sidecar_cb: {block_new_entries_minutes_after_cb_reopen: 30, quotes_during_halt: indicative, gross_cut: false}
  daily_book_blackouts: false
  tags_change_weights: false
```

Window table:

| Source | Window (local) | `market` | `action` | Resume / notes |
|---|---|---|---|---|
| `US_CPI`, `US_NFP` (08:30 ET) | 08:25–10:00 ET | `US` | `evaluator_block_new_intraday_entries` | "entries resume at 10:00 ET"; "No simulated stops are placed inside the window. Daily book unchanged." |
| `US_OTHER_RELEASE` with documented drift ("ISM, consumer confidence, IP, GDP preliminary and others") | "the window starts 30 minutes before the release" | `US` | same | end not stated (F-14) |
| `FOMC` (14:00 ET) | 13:45–15:00 ET | `US` | same | "Resume at 15:00 if VIX < its pre-14:00 level, else at 15:30. No pre-FOMC long. Daily book unchanged." `resume_condition: "VIX < pre-14:00 ET level else 19:30Z"` (L3845) |
| `FOMC` | same instants | `KR_FUT_NIGHT` | `evaluator_block_new_futures_entries` | "The same windows apply to KOSPI200 night futures"; example `resume_condition: null` (L3846; F-15) |
| `BOK_DECISION` (≈ 09:50 KST) | 09:45–10:15 KST | KOSPI200 futures (`market` string not given; proposed `KR_FUT`; the examples only use `US`, `KR_FUT_NIGHT`) | `evaluator_block_new_futures_entries` | "Equity daily book unchanged" |
| `BOK_PRESS_CONFERENCE` (≈ 11:10 KST) | 11:00–11:45 KST | same | same | "two separate events, each with its own status" |
| Every KRX day | 09:00–09:30 KST; 10:00–10:30 KST "on 10:00-open days: the first trading day of the year and CSAT days" | `KR` | `evaluator_block_new_intraday_entries` | per `time.markets.KR.open_no_entry_minutes: 30` (L4161); generated from the session calendar, not stored as events (F-16) |
| Circuit-breaker reopening | 30 minutes after the reopening | `KR` | same | "Quotes read during a halt are marked indicative"; "**No gross cut**" |
| `OIL_GEO` | scheduled or known risk windows | — | `annotate_only` | `scenario_tag` "for Monte Carlo and the replay library (R-16). No exposure gate." |
| `HYPERSCALER_EARNINGS`, `KRX_HOLIDAY_GAP` | — | `KR` | `annotate_only` | tags only (B.14) |

- Status handling: `cancelled` → no window; `delayed` → the window moves with the new `scheduled_utc` (no new time known → no window, F-17); `released` → `released_utc` set. A status change is a new calendar version ("one file per calendar version").
- ET ↔ UTC through `zoneinfo("America/New_York")`; KST = UTC+9. Example to reproduce (L3843-3847): FOMC 2026-10-28 14:00 EDT = 18:00Z → US window 17:45Z–19:00Z, `kr_open_gap_session: "2026-10-29"`. US NFP 2026-10-02 08:30 EDT = 12:30Z → window 12:25Z–14:00Z, `resume_condition: "10:00 ET"`, `kr_open_gap_session: "2026-10-06"` (L3853-3856).
- `event_id` pattern from the examples: `FOMC-2026-10-28`, `US-NFP-2026-10-02`.
- API (proposed): `load_events(version) -> tuple[Event, ...]`; `event_windows(event, cfg) -> tuple[Window, ...]`; `active_windows(market, at_utc) -> tuple[Window, ...]` (includes the generated KR-open and CB windows); `build_event_calendar(ctx) -> dict` (envelope + events, validated against `quantgen/event_calendar.v2.0`).
- Artifact failure: "a validation failure … of a `context_log` or `event_calendar` artifact (labelled and alerted; R-32)" never HALTs (L1178); "refused and quarantined with its errors" (L1226-1227).
- "Signals use KRX regular-session prints only. Daily decisions are taken at the official close (P5)." (L1629)
- Not built (L1635): "24-hour blackouts; daily-book blackouts; quad-witching blackout; momentum decision-day size-down (backlog BL-O02)."
- Measurement (L1637): "Log the KIS quote spread and 1-minute range around each window once the KIS quote-field check confirms bid/ask and timestamps (QF1-A25)."

### B.14 Opening-gap nights, multi-session gaps, VaR display (R-10 L1630-1631, L1634; §4.1 L1340)

- From M1 (spec_M1_calendars B7): `kr_open_gap_session(event_utc) -> date` (first KRX session whose open is later than the event) and `gap_sessions(market, session_date) -> int` ("n_US >= 0: US sessions since the previous KRX close", L1041).
- Opening-gap nights: "US CPI/NFP nights, FOMC nights (03:00/04:00 KST) and hyperscaler capex/earnings nights. The next KRX session gets `kr_open_gap_event=true`. The overnight SOX, S&P, ΔUST10 and USD/KRW moves are logged as opening-gap inputs. **No exposure change.** The flag and the realised opening gap feed backlog BL-U03."
- Multi-session gaps: "A KRX session that follows more than one US session since the previous KRX close (Seollal, Chuseok, substitute and election holidays) carries `gap_sessions = n_US ≥ 2`, `kr_open_gap_event = true` and a `KRX_HOLIDAY_GAP` calendar event. Its displayed 1-day VaR scales σ by √max(n_US, 1). A KRX session with n_US = 0 (the NYSE was closed, e.g. the KRX session of 2026-11-27 after Thanksgiving) carries `gap_sessions` = 0, no gap event and an unscaled VaR. Post-holiday sessions are reported separately in the Quant Lab backtests (R-16). **No gross rule.**"
- Functions (proposed):
  ```python
  def kr_open_gap_event(session_date: date, events) -> bool   # True iff gap_sessions('KR', d) >= 2, or a non-cancelled event of a type in
                                                              # kr_open_gap_event_types has kr_open_gap_session == d
  def var_display_scale(n_us: int) -> float                   # sqrt(max(n_us, 1)); >= 1; display only
  def holiday_gap_event(session_date: date) -> Event | None   # type KRX_HOLIDAY_GAP when n_US >= 2: gap_sessions = n_US, var_display_scale, windows action annotate_only
  ```
- The flags describe the **effective** session of the decision: the 2026-10-02 KR decision carries `kr_open_gap_event: true, gap_sessions: 2, var_display_scale: 1.4142` for 2026-10-06 (L3677, L3700).
- Check values: K = 2026-10-06 → 2 (US sessions of 2 and 5 Oct); K = 2026-10-12 → 2 (8 and 9 Oct, L6313); K = 2026-11-27 → 0; an ordinary session → 1.
- Invariant (L1634): "**No event tag changes any weight.** Windows produce BLOCKED decisions for new intraday entries only; tags and gap flags are annotations and display inputs (an assertion in the book builder)." The book builder's readable-field whitelist excludes `annotations.*`, `flags.kr_open_gap_event`, `flags.gap_sessions`, `flags.var_display_scale` and every event tag; the assertion compares weights with each tag flipped.
- Hyperscaler list: data-acquisition item "The hyperscaler list | company IR | — | M5" (L6032).

### B.15 Fill model — R-27 (L2888-2946; §3.8 L1177; config L4387-4393)

```python
def fill_model(venue: str) -> FillModel                                   # L2893; venues: "KRX", "NYSE", "KOSPI200_futures"
def simulate_fill(order, session) -> Fill | NonFillable                   # NonFillable(reason)
simulated_fill = simulate_fill                                            # §3.5 name (L1087): simulated_fill(order: SimOrder, venue: str, session_date: date) -> SimFill
```
"simulated fills only, never a broker path." R-27 "never changes a card's gate statistics, which keep the decide-at-the-close convention and print the execution variants of R-26" (L2890).

Config verbatim:
```yaml
fill_model:                                          # R-27 (simulated book only)
  KRX: {snapshot: closing_call_start_minus_1min, snapshot_kst_since_2016-08-01: "15:19", fill: official_close, random_end_max_s: 30,
        fallback: post_close_session_UNVERIFIED, limit_price: tick_rounded_toward_prev_close,
        etf: {flag: LP_exempt_auction, inav_residual_flag_bp: 30}, limit_lock: non_fillable_at_close}
  NYSE: {snapshot_et: "15:50", fill: official_close_moc_equivalent}
  KOSPI200_futures: {trades_until_kst: "15:45", expiry_day_stop_kst: "15:20"}
  bars: {stamp: bar_end_utc, closing_auction_bar: separate, available_at: "bar_end + latency", daily_close_from_bars: forbidden}
```

| Rule | Algorithm |
|---|---|
| 1 KRX daily decision | Snapshot "one minute before the closing call opens, on the last continuous price: 15:19 KST since 2016-08-01 (closing call 15:20–15:30), 14:49 KST before (closing call 14:50–15:00), and the CSAT-day equivalent from the calendar (R-20)" (`csat_closing_call_kst … {from: "2016-08-01", window: ["16:20", "16:30"]}`, L4181). Fill "at the **official close**, the closing-call print between 15:30:00 and 15:30:30 under the random end". "Fallback: the post-close closing-price session. Its status after 2026-09-14 is UNVERIFIED until it is checked." "The simulated book prints the tracking error between the snapshot decision and an official-close decision." |
| 2 ETF closes | "Each ETF close is flagged `LP_exempt_auction`, because LPs have no quoting duty from 15:20 to 15:30." `residual = close / iNAV − 1`; "\|residual\| > 30 bp is flagged" (`inav_residual_gt_30bp`). Printed allowance: "a median \|closing-auction move\| of 0.12–0.14%, p95 0.6%, max 2.0–2.3%". |
| 3 Limit-lock | "A stock at its daily limit at the close is **non-fillable at the close** in the stock book: limit-up for buys, limit-down for sells. The order carries to the next session and is logged." "'At its limit' means the official close equals the session's limit price: the previous close × (1 ± `price_limit`), rounded to the tick toward the previous close (R-20 `price_limit`, the effective-dated tick table). A `\|r\| ≥ limit` test is never used". "ETF and futures lines stay fillable unless they are themselves limit-locked." "No gross rule follows from limit-locks." |
| 4 NYSE | "Snapshot at 15:50 ET (the MOC cut-off); fill at the official close (MOC-equivalent)." |
| 5 Futures | "KOSPI200 futures trade until 15:45 KST, so a decision taken at the cash close can execute in the same session." "The expiring contract stops at 15:20 KST on its last trading day, so books roll before expiry (R-26)." |
| 7 Intraday entries | "priced at the triggering quote, with its timestamp" (the existing `SimulatedOrder.trigger_price`; add the quote's `as_of`, and to `OrderBook.snapshot/restore`, `orders.py:194-234`). The operator's manual-fill contract is unchanged. |

- Limit price: `limit_up = floor_to_tick(prev_close × (1 + price_limit))`, `limit_down = ceil_to_tick(prev_close × (1 − price_limit))`; `locked_up = (official_close == limit_up)`, `locked_down = (official_close == limit_down)`. `price_limit` from `regime_tags('KR', d).price_limit` (0.30 from 2015-06-15, L2098). Stock tick table: not in the spec (F-18).
- Outputs (L2940): `overlay_decision.extras.fill_model`, `decision_price_source ∈ {snapshot_1519, official_close}`, `fill_status ∈ {filled, non_fillable_limit_lock, carried}`, `flags[]` (`LP_exempt_auction`, `inav_residual_gt_30bp`); `model_card.macro.printed.fill_tracking_error` (M7).
- Fail closed (L2943-2946): "If no official close exists for the session, there is no fill; the order is carried and an alert raised." "A bar-derived close is refused by the loader." "An unverified KIS quote field cannot drive a snapshot. The snapshot then falls back to the official-close decision, and this is labelled."
- Cost: "Every simulated fill is charged the pre-registered cost, with the tick floor applied (P10)" (L1177) → `cost_per_side` (M0-12) on the fill.
- Shape: `simulate_fill` is a pure function over PIT inputs (official close with `value_status = official_close`, previous close, `price_limit`, tick, iNAV); the book runner applies a `Fill` through the simulated book API and leaves a `NonFillable` order open and carried (one mutation path; T-RO-01 "`core/engine/orders` is reached only through the simulated order book API", L5605). `NonFillable.reason` stays an open string: the tech-fund INV-2 adds reasons (G).
- `fill_tracking_error(weights_snapshot, weights_close, returns) -> {te_ann, mean_abs_dw}` (proposed): `te_ann = std(r_snapshot_book − r_close_book) × √252`, `mean_abs_dw = mean |w_snapshot − w_close|`; the book QF1 used is not stated (F-19).
- `core/markets` metadata to add (keyword fields with defaults): closing-call window, random-end bound, LP quoting-duty window; values come from `calendars.KR.closing_call_kst`, `random_end` (L4177-4179).

### B.16 Bar convention (R-27 rule 6 L2923-2925; §4.1 L1325)

- "Every intraday bar carries `bar_end` (UTC); the closing auction is its own bar; `available_at_utc = bar_end + latency`."
- "**A daily close is never derived from intraday bars.** Only official closes are stored as `official_close` (R-01)." "on 727 of 729 days the vendor's last KRX hourly bar is the 14:00–15:00 bar, so the 15:00–15:30 segment, including the closing auction, is missing. The last-bar close differs from the official close by a median 13.7 bp (max 205 bp)."
- Build: frozen `Bar{symbol, bar_end_utc, open, high, low, close, volume, is_closing_auction, available_at_utc, source}`; the official-close loader accepts only close-type rows (M1-11) and raises on any bar input offered as a close source, whatever its last `bar_end`. No function that returns a daily close from bars may exist in `core/`. `latency`: F-20.

### B.17 Simulated books, persistence, no reallocation (TASK-M5-12; L1184-1187, L883)

- Books and feeds (L1184): "Recommended book and specification book: fed through `macro.engine_feed`. FORWARD-SIM books (R-28, R-29) and refusal books (R-11, R-12; display only): computed by the forward evaluator in `core/quant/backtest` and recorded in `core/engine/state`; they never pass through `engine_feed` (R-35). Every book has its own runtime state". M5 builds the weight-driven book (`core/engine/books.py`): per book id, weights held/target, carried orders, NAV, runtime state; fills through B.15; "priced at the official close of t, earning from t+1 and costed with the tick floor". `engine_feed` and the forward evaluator are M8.
- Persist (L1187): "`core/engine/state` persists trigger counts, per-card switch counts, the ladder state (references, step, dwell left, re-arm and cooling-off dates), each book's runtime state and consecutive-failure counters, and forward alarms (**proposed**)." Per book: `engine_state`, `ever_armed`, `halt{class, reason_code, component, series_id, since_utc, rearm_not_before, rearm_mode, causes[], ack_by, ack_utc}`, `post_rearm_cap_until`, `post_rearm_left`, `nav`, `hwm_hard`, `ref_step`, `step_mult`, `dwell_left`, `block_new_entries`, `consecutive_failures{series_id: n}`, `book_counter`, NAV-failure count, switch counts per card, weights, carried orders. Book state (including ARMED) is restored on restart (spec_architecture F-2). A write failure must raise, not be swallowed (code_rules_engine E-3). Separate file from `engine.json`.
- No reallocation (T-MONO-01, L883): "Lowering any multiplier (vt, vs, an overlay, the ladder, the post-re-arm cap, a concentration bound) never raises gross(m′), active_budget(m′, f′) or the active risk of any other market m′ or family f′, and never raises gross(m) or active_budget(m, f) itself. `composite_weights` and `risk_layer` never renormalise freed budget across families or markets: freed active budget moves toward the benchmark (long-only) or zero (long/short), and freed total exposure moves to cash. The one documented exception is R-15's admissibility rule: a family-card REJECT shrinks K_m and raises the other families' base weights by K/(K−1) from the next decision; it is logged as a governance event and printed." Governance kind: `admissibility_reweight`.
- R-08 and R-10 assertions live in the same builder (B.12, B.14).

### B.18 Reference mode (TASK-M5-13; §9.3.3 L5992)

- "`core/quant/backtest` may compute configurations the rules store refuses (… the literal v1.2 ladder) only when called from `tests/reference/` or `docs/` with `reference_only=True`; `core/` cannot import that code. Such results never enter a book, a card or an artifact". Goldens marked `reference_only` here: "G-LAD-01 (the literal ladder: the cumulative and the non-cumulative readings), G-LAD-02 (QF4's 11-session halt) and G-LAD-03".
- What the spec states about the literal v1.2 rule: "No new drawdown reference is defined and the NAV is flat while HALTED" (L1589); the product form "made the −12% ladder step 0.25× vt" (L852). The rule text itself is in `.v1.2_INTEGRATION_backup.md`, which is not on this machine (F-21).

### B.19 Spikes

- TASK-M5-14: §9.4 item 9 "I-04b's KOSPI VT20 1997–2026 HALT count under the v2 rule (automatic RISK re-arm; Check C2 printed 24 under its re-arm)"; item 10 "G-LAD-04: the invariants-only recommended KOSPI book (ETF line, caps), with and without the −15% hard stop: HALT count, MDD and Sharpe, printed beside D2 (§8.10)". Both md5-frozen once computed; "Neither number may change a default."
- TASK-M5-15: §9.4 item 6 "The event-conditional variance test for the opening-gap flag (QF7-A28), and the 2027–28 out-of-sample post-holiday VaR breach check (R-10)"; "Before the opening-gap flag is kept as 'log only', run an event-conditional variance test (DM on the squared gap) on the local hourly bars and daily opens" (L1637). "Neither result may change a weight."

---

## C. Schemas and config

### C.1 Rules-store blocks this area reads (written by M0-05; "If a rule and this listing ever differ, the rule governs", L4132)

| Block | Lines | Content |
|---|---|---|
| `owner_decisions.D1`, `.D2` | L4140-4143 | `D1: {key: risk_layer.korea_caps.template, value: msci_25_50, default: msci_25_50, options: [domestic_max10_or_weight, msci_25_50, pair_35], status: default, …}`; `D2: {key: risk_layer.drawdown.hard_stop.level, value: -0.15, default: -0.15, options: [-0.15, "-1.5*sigma_book"], status: default, …, refs: [cards.R-31_step_down.hard_stop_level]}` |
| `risk_layer.korea_caps` | L4331-4344 | `lookthrough: {source: daily_etf_pdf, leveraged_multiplier: L}`, `template`, `templates` (B.2), `active_single_name_cap_nav: 0.05`, `active_bound`, `semis_max_share_of_sleeve_nav: 0.50`, `report_by_book: true`, `meet_cap_order`, `report` |
| `risk_layer.drawdown` | L4345-4352 | B.4 |
| `risk_layer.halt_scope`, `halted_triggers`, `heartbeat`, `ops_rearm`, `never_halt_on` | L4353-4363 | `halt_scope: per_book`; B.5, B.6 |
| `cards.R-31_step_down` | L3314-3328 | B.9 |
| `annotations.vix_ts` | L4371-4373 | B.12 |
| `events` | L4374-4386 | B.13 |
| `fill_model` | L4387-4393 | B.15 |
| `instruments.li_etf` | L4397 | B.1 |
| `time.markets.KR.open_no_entry_minutes: 30`; `time.decision: close_t_earn_t_plus_1` | L4161, L4155 | B.13 |
| `calendars.KR.closing_call_kst`, `random_end`, `csat_closing_call_kst`, `first_trading_day_open_kst: "10:00"` | L4177-4182 | B.15, B.13 |
| `data_contracts.roles.NAV_LINE_CLOSES`, `KODEX200_PDF`, `KRX_MARKET_CAPS_005930_000660_KOSPI`; `on_failure.acting_exposure`, `forward_sim` | L4231-4255 | B.1, B.6 |
| `monitoring.nav_unavailable_ops_halt_after_decisions: 2` | L2724 | B.6 |

### C.2 Artifact fields this area produces (schemas owned by M0-08; artifacts built by M6)

- `macro_state.flags` (L3575-3586): `kr_open_gap_event` bool; `gap_sessions` integer ≥ 0 ("n_US: US sessions since the previous KRX close; 0 after a US-only holiday"); `var_display_scale` number ≥ 1 ("sqrt(max(n_US, 1)); display only"); `ladder_step ∈ {none, step_-8, step_-12, hard_stop_-15}`; `ladder_dwell_left` integer ≥ 0; `block_new_entries` bool; `ladder_steps_act_in ∈ {recommended, specification}`; `hard_stop ∈ {armed, halted, rearm_refused, post_rearm_cap}`; `hard_stop_level` number; `engine_state ∈ {DISARMED, ARMED, HALTED}`. Required: `kr_open_gap_event, gap_sessions, var_display_scale, ladder_step, ladder_dwell_left, block_new_entries, hard_stop, engine_state` (plus the hedge fields).
- `macro_state.annotations` (L3587-3588): `{vix_ge_vix3m: boolean, notes: [string]}`, required `vix_ge_vix3m`.
- `macro_state.concentration` (L3593-3604): `template ∈ {domestic_max10_or_weight, msci_25_50, pair_35}`, `pair_share_kospi`, `pair_lookthrough_share`, `pair_risk_contribution`, `absolute_bound`, `active_bound`, `aggregate_bound`, `semis_bound` (each number|null), `by_book{<book_id>: {composed [0,1], gross [0,1], binding_factor}}`; required `template, by_book`.
- `macro_state.runtime[]` (L3608-3623): required `book_id, engine_state, halt, consecutive_failures, book_counter`; `halt` (object|null) required `class, reason_code, since_utc, rearm_mode, causes` with `class ∈ {RISK, OPS}`, `component`, `series_id`, `rearm_not_before` (date|null: "RISK: the decided_session (t+10) of the earliest automatic re-arm decision (a breach re-arms only once its limit is met); null for OPS"), `rearm_mode ∈ {auto, operator}`, `causes[]` (minItems 1; required `class, reason_code, since_utc, rearm_mode`; plus `rearm_not_before`, `cleared_utc`), `ack_by`, `ack_utc`; `post_rearm_cap_until` (date|null), `nav`, `hwm_hard`, `ref_step` (number|null).
- `macro_state.owner_decisions` (L3605-3607): entries for D1 and D2 keyed by canonical key, `{decision, value, status}`.
- `overlay_decision` (L3738-3755): `ladder ∈ {0.5, 1.0, null}` ("market_gross only"), `post_rearm_cap ∈ {0.5, 1.0, null}` ("an argument of min() for 10 sessions after a RISK re-arm"), `binding[]`, `reasons[]`, `extras` ("R-26 {instrument_book, contracts, w_target, w_held, band, usdkrw}, R-27 {fill_model, decision_price_source, fill_status, flags}, R-32 validation_errors"). R-31 multiplier entry: `{rule_id: "R-31", value, exposure_basis: "total", card{… disposition ∈ {INVARIANT_STEP, SPECIFICATION_ONLY, …}}}`.
- `event_calendar` (`$id quantgen/event_calendar.v2.0`, L3809-3830). Envelope required: `schema` (const `quantgen.event_calendar`), `schema_version` (`"2.0"`), `read_only` (true), `generated_at_utc`, `knowledge_utc`, `git_hash`, `config_hash`, `data_snapshot_id`, `calendar_version` ("the owner-signed core/calendars data version (T-CAL-01)"), `events`. Event required: `event_id, type, region, scheduled_utc, status, source, windows`. `type ∈ {FOMC, US_CPI, US_NFP, US_OTHER_RELEASE, BOK_DECISION, BOK_PRESS_CONFERENCE, BOJ, ECB, KOSPI200_EXPIRY, INDEX_CHANGE, HYPERSCALER_EARNINGS, OIL_GEO, FX_INTERVENTION, KRX_HOLIDAY_GAP, POLICY_FRAMEWORK_CHANGE, MARKET_STRUCTURE_CHANGE, OTHER}`; `status ∈ {scheduled, released, cancelled, delayed}`; `released_utc` (date-time|null); `windows[]` required `market, action, start_utc, end_utc`, `action ∈ {evaluator_block_new_intraday_entries, evaluator_block_new_futures_entries, annotate_only}`, `resume_condition` (string|null); `kr_open_gap_session` (date|null); `gap_sessions` (integer|null, minimum 0); `var_display_scale` (number|null); `scenario_tag` (string|null); `notes` (string). The two example entries (L3843-3857) must validate.
- `governance_event` kinds used here (L4104-4105): `halt`, `rearm`, `book_state`, `admissibility_reweight`; actor `runtime`, `operator` or `owner`.

### C.3 State and data files (proposed locations)

| File | Content | Note |
|---|---|---|
| book-state file of `core/engine/books.py` (M1 decides the path) | B.17 key set | under the `config` trading/macro directory with an env override; tests pass temp paths (T-HERM-02) |
| event source file (versioned, owner-maintained) | scheduled events with status | beside the other signed calendar data (`core/calendars/data/` or `data/macro/`, per the M1 layout decision) |
| hyperscaler list | names and earnings dates from company IR | data-acquisition register (L6032) |
| KODEX 200 PDF history | "KODEX 200 PDF history | KIS or KRX | as available | M5" (L6027) | fixture + md5 in `tests/fixtures/macro/MANIFEST.csv` |

---

## D. Tests

Feasibility: **SYNTH** hermetic with inline/synthetic fixtures; **REFDATA** needs frozen reference data not on this machine; **OWNER** needs owner input, credentials or live sessions. Level-1 tolerances (L5734-5735): Sharpe ±0.01; max DD ±1 pp; weights ±0.02; "deterministic counts exact"; other ratios ±0.01.

### D.1 Tests whose `runs_from` is M5 (L5555)

| ID (line) | Exact assertion | Fixture | Class |
|---|---|---|---|
| T-BOOK-03 (L2873) | "A product whose tick exceeds 10 bp of its price is ineligible. Look-through counts × L in R-07." | Inline: 252670 at ₩69, tick ₩1 → ineligible; KODEX 200 at ₩112,060, tick ₩5 → eligible (prices from L2799); boundary tick/price = 10 bp → eligible; a position with L = 2 doubles each look-through share | SYNTH |
| T-CAPS-01 (L5649) | "The daily KODEX 200 basket is applied. w_i − g·b̃_i ≤ 0.05 NAV is enforced. The template is read from the rules store (D1). On 2 Oct, under 25/50, the absolute bound is 22.5 / 29.8 = 0.755 and the active-cap bound is at most 0.05 / (0.298 − 0.225) = 0.685; the test asserts the gross and the binding factor in each book (specification and recommended; `concentration.by_book`). Leveraged products count at × L." Round 1 (L5505): "the active bound 0.685 binds in both books". Expected: `recommended:KR {composed 1.0, gross 0.685, active_single_name}`, `specification:KR {composed 0.694, gross 0.685, active_single_name}` | Arithmetic: inline basket with s(005930) = 0.298 and pair look-through share 0.538 (the only shares the spec prints for the line, F-29) → SYNTH. "The daily KODEX 200 basket is applied" on the real 2-Oct PDF → REFDATA (KODEX 200 PDF from KIS or KRX; no local substitute: `docs/asset_expansion/cache/yf_069500.KS.csv` is the ETF price only) | SYNTH + REFDATA |
| I-04 (L5691) | "With the overlay at 1.0 and a whole-book NAV drawdown of −12% from the step reference: evaluator BLOCKED for new entries, and the step multiplier 0.5 composed by `min()` (never 0.25 × vt). After 21 sessions in a step, the step reference resets to the current NAV; the hard-stop reference does not. Where the steps bind on more than 10% of days on the declared book, they act only in the specification book." | Synthetic NAV path; a binding share injected as 0.19 | SYNTH |
| I-04b (L5692) | "A −15% book-NAV breach (default level; owner decision D2) sets that book HALTED (RISK), refuses re-arm for 10 sessions, re-arms automatically, resets both references to the NAV at re-arm and caps exposure at 0.5 × vt (inside `min()`) for 10 sessions (T-HALT-01). The KOSPI VT20 1997–2026 HALT count under this rule is pinned once computed (§9.4). On the KOSPI 1997–2026 fixture the book re-enters after every HALT; the literal v1.2 rule stays permanently HALTED from 1997-10, with 714 cycles (G-LAD-01)." | Mechanism: synthetic NAV → SYNTH. KOSPI clause: KOSPI daily closes 1997-04-15 → 2026-10-02 (Yahoo `^KS11` fixture or KRX official closes) → REFDATA; no local `^KS11`; `yf_069500.KS.csv` starts 2007-01-29 and ends 2026-09-23 (re-entry property only, not the golden). Pinned count: pending (§9.4 item 9) | SYNTH + REFDATA |
| T-HALT-01 (L5674) | (a) "A synthetic NAV path breaching exactly −15.00% at the close of t (`<=`): HALTED (RISK) with exposure 0 on sessions t+1 … t+10; automatic re-arm at the decision at the close of t+10; both references reset to the NAV at re-arm; `post_rearm_cap` 0.5 inside `min()` for the weights decided at t+10 … t+19 (earning t+11 … t+20); then normal running." (b) "An OPS HALT (a stale acting input) clears at the first decision with the input fresh, with no refusal window, no reference reset and no cap." (c) "A risk-limit-breach HALT whose limit-locked stock-book order persists past t+10 stays HALTED at t+10 and re-arms at the first later decision at which the target weights after the prescribed action meet the limit, with no reference reset and the 0.5 cap for the weights decided at that re-arm decision and the 9 after it; a KODEX-basket failure beyond its 5 misses is OPS." (d) "A lag-audit violation raised during a RISK HALT keeps the book HALTED after t+10 until the operator re-arms (`halt.causes[]`), and the cap window starts at the operator's re-arm decision. Sessions are those of the book's primary-market calendar." | Synthetic NAV, synthetic store with a stale input, a synthetic stock book with a limit-down-locked sell, an injected lag-audit violation; inline session list | SYNTH |
| T-STEP-05 (L3349) | "NAV flat at −16% for 30 sessions after a breach at the close of t sets `rearm_not_before` once (t + 10 sessions). The book re-arms automatically at the close of t+10, re-enters at t+11 under the 0.5 post-re-arm cap (weights decided at t+10 … t+19), and a second `halt()` while HALTED changes nothing (no later re-arm date, no reference reset)." | Synthetic NAV | SYNTH |
| I-06 (L5694) | "A cancelled event (Oct-2025 CPI) produces no window. A delayed event moves its window. A US CPI night sets the KR opening-gap flag for the next KRX session. The BoK decision and the press conference are separate events with status. Window hits produce BLOCKED evaluator decisions only for new intraday entries." | Inline events; KRX/US session lists (2026 dates are covered by a fixture copy of `data/calendars/KRX.json`, `US.json`) | SYNTH |
| I-06b (L5695) | "A KRX session that follows two or more US sessions since the previous KRX close carries `gap_sessions ≥ 2`, and its displayed 1-day VaR is scaled by √max(n_US, 1). Example: 2026-10-06, after the 5-Oct substitute holiday. The BoK decision and the press conference are separate events with status. No event tag changes any weight (an assertion)." The test follows the reading "the KRX is closed while US sessions continue". Expected: `gap_sessions('KR', 2026-10-06) == 2`, scale 1.4142 | Inline 2026 session lists | SYNTH |
| I-06c (L5696) | "The KR decision of 2026-11-26 (effective session 2026-11-27; the NYSE was closed on 2026-11-26): `gap_sessions` = 0, VaR scale 1, `kr_open_gap_event` false; … the books stay ARMED. An out-of-schema context field never HALTs" | Inline session lists; M1 runtime | SYNTH (two clauses deferred, D.3) |
| T-ANNOT-01 (L5650) | "With the flag on, no book's weights change (an assertion in the book builder). Each flag day writes an annotation and a KIS spread-snapshot request. The fixture reproduces 132 spells, 50.8% of them one day long (DLB-T6a)." | Assertion and records: inline VIX/VIX3M → SYNTH. Spell counts: FRED `VIXCLS`, `VXVCLS` 2007-12-04 → 2026-09-30 (`QX_DLB_r08.csv` basis) → REFDATA. Local substitute `docs/asset_expansion/cache/yf__VIX.csv`, `yf__VIX3M.csv` (Yahoo, to 2026-09-25): computed here on 2007-12-04 → 2026-09-25 = 4,732 days, 10.12% flagged, 133 spells, 51.1% one-day, 15.8% ≥ 5 days, 14.17 transitions a year — close, not the golden; never assert the golden on it | SYNTH + REFDATA |
| G-R08-01 (L5979) | "4,735 days; 10.1% flagged; 132 spells; 50.8% one-day; 15.9% ≥ 5 days; 14.0 transitions a year; de-clustered onsets 64 / 40 / 24 at 20 / 60 / 126 sessions. 5-close clearing: 72 spells, median 8 days" (counts exact at Level 1) | same FRED fixture | REFDATA |
| G-R08-02 (L5980) | Record only ("REJECT in 10 of 10 cells"); nothing to compute in M5 | — | — |
| T-FILL-01 (L2952) | "A ≈ 15:19 KST snapshot decision filled at the official close reproduces QF1's tracking error against an official-close decision (0.19% a year on KOSPI; mean \|Δw\| 0.0013) within ±0.05 pp" | "the 15:19 snapshots" fixture (L6018) and KOSPI official closes → REFDATA, no local intraday data. Mechanics of `fill_tracking_error` on synthetic series → SYNTH (no golden) | REFDATA (+ SYNTH mechanics) |
| T-FILL-02 (L2953) | "SK hynix on 2026-07-31 (+29.95%: its close equals the tick-rounded limit price) is non-fillable at the close in a stock book. The KODEX 200 line fills." | Rule: inline previous close, `price_limit` 0.30 and tick such that the tick-rounded limit is +29.95% (below +30%), buy order → `NonFillable("non_fillable_limit_lock")`; a `\|r\| ≥ 0.30` test would wrongly fill; ETF line → `filled` → SYNTH. Actual 000660 closes of 2026-07-30/31 and the stock tick table → REFDATA/OWNER (no local 000660 file) | SYNTH + REFDATA |
| T-FILL-03 (L2954) | "An ETF close-vs-iNAV residual above 30 bp is flagged" (31 bp flagged, 30 bp not; every ETF close carries `LP_exempt_auction`) | Inline close and iNAV | SYNTH |
| T-BAR-01, R-27 clause (L2955) | "No daily close is derived from intraday bars. A fixture whose last hourly KRX bar ends at 15:00 is refused as a close source." | Inline hourly bars | SYNTH |
| T-MONO-01 (L5676) | "For random multiplier vectors m ≤ m′ elementwise on the I-01 fixtures (seed 11), every market's gross and every family's active budget is weakly monotone in its own multipliers, and every cross-partial is 0; the R-15 K/(K−1) admissibility re-weighting is the one exception, logged as a governance event." | Property test on a synthetic book of the I-01 structure (seed 11) → SYNTH; re-run on the I-01 fixtures (KR 2026-07-30, 2026-10-02; US 2026-07-30, 2026-10-01) when they exist → REFDATA | SYNTH + REFDATA |
| G-LAD-01 (L5897) | "KOSPI, buy-and-hold or VT20: permanently HALTED from 1997-10-17 under the cumulative reading (average exposure 1.3%; 714 halt cycles), from 1997-09-30 under the non-cumulative one (1.3%; 715 cycles). US, buy-and-hold or VT15: from 2000-10-13 (20–22%; 653 cycles) / from 1990-09-25 or -28 (1.1%; 907 cycles)" | `QX_DLA_ladder.csv` basis: KOSPI 3 bp from 1997-04-15, US 5 bp from 1990-04-02; the literal v1.2 rule text (F-21) | REFDATA |
| G-LAD-02 (L5898) | "KOSPI VT20: Sharpe 0.532, max DD −42.0%, days reduced 52%, 16 HALTs, ΔSR vs no ladder +0.078, ΔMDD vs S +3.9 pp. KOSPI buy-and-hold: 0.453, −50.9%, 52%, 31, +0.025, +0.4 pp. US VT15: 0.522, −42.5%, 29%, 8, −0.066, +5.7 pp. US buy-and-hold: 0.523, −51.2%, 23%, 17, −0.008, +2.0 pp" | same; QF4's rule details | REFDATA |
| G-LAD-03 (L5899) | "The 0.5× cooling-off clause moves US VT15 to 0.538 / −37.8%. A 10-session halt instead of 11 moves the KOSPI buy-and-hold cumulative Sharpe from 0.553 to 0.595" | same | REFDATA |
| §12 M5 (L6367) | "the FOMC → KST mapping test passes" = T-TZ-02 (L5623): "The 2026-09-16 statement (14:00 EDT) is 2026-09-17 03:00 KST, so `kr_open_gap_session = 2026-09-17`. The Sep NFP (2026-10-02 08:30 EDT) maps to `kr_open_gap_session = 2026-10-06`." Re-asserted through the event store. "window hits and BLOCKED decisions are logged" | Inline | SYNTH |

### D.2 Clauses that join at M5 from earlier tests (§9.0b)

| Test | Clause | Fixture | Class |
|---|---|---|---|
| T-MISS-02 (L5586, L5625) | "An exception in an acting risk-layer function (… `concentration_bound`, `drawdown_ladder` …) → HALTED (OPS) for the books it feeds" | Injected exception; assert only the fed books HALT | SYNTH |
| G-POST-01 (L5575, L5832) | Row "Samsung + SK hynix implied share (B3a anchor)": "≈ 53.6% (Samsung 29.8% + hynix 23.8%)"; closes "₩276,000 / ₩1,841,000" (the close row itself is M1) | `QX_DLA_postpatch.csv` and the 25-Oct-2024 KRX-weight anchor → REFDATA; formula not in the spec (F-22). Local sanity value only: tech-fund `datalab/results/r3/r3_pair_share_2026_daily.csv` (CR-07 definition, 0.5371 on 2026-09-29; different denominator and date) | REFDATA |

### D.3 Clauses of M5 tests that run later, and later tests M5 code must already satisfy

| Test | Clause | runs_from |
|---|---|---|
| I-06c (L5594-5595) | "`macro_state` validates" | M6 |
| I-06c | "an acting-field schema error HALTs (OPS) the books the artifact describes" | M8 (`bounds_ok`) |
| T-STEP-01 … 04 (L3345-3348), I-15 | references, binding share ≈ 19% / ≈ 10% (± 3 pp), ΔSR line, book placement | M7 after the freeze; T-STEP-01 and T-STEP-04 are SYNTH-ready on M5 code; T-STEP-02/03 REFDATA (`QX_EX1_ladder.csv` basis) |
| T-RLAYER-01 (L2405) | `with_risk_layer` reproduces Check C2: "24 HALTs, maximum drawdown −56.4%, against −45.3% without the hard stop" | M7; REFDATA |
| T-SCOPE-01 (c), (d) (L5675) | "A specification-book NAV at −16% HALTs the specification book only." "A recommended-book NAV at −16% HALTs the recommended book (RISK)." | M8; SYNTH-ready |
| T-OBS-01 (L5677) | "Each HALT class writes the `runtime[].halt` block of its book and a governance event." | M8; SYNTH-ready |
| I-04b pinned count, G-LAD-04 | §9.4 items 9, 10 | when computed (TASK-M5-14); REFDATA |
| §9.4 item 6 | DM test on the squared gap; 2027–28 breach check | TASK-M5-15; REFDATA (hourly bars, daily opens) / OWNER (2027–28 data) |
| KIS-dependent features | R-27 snapshots, R-08 spread snapshots (L44) | OWNER: KIS credentials + about 20 live sessions; until then labelled UNVERIFIED |

---

## E. Interfaces

### E.1 Needed from earlier milestones

| From | Name / shape | Used in |
|---|---|---|
| M0-05 | rules-store accessor for the blocks of C.1 | all |
| M0-06 | owner-decision registry; `{ref}` resolution of `risk_layer.korea_caps.template` and `risk_layer.drawdown.hard_stop.level` | B.2, B.4, B.9 |
| M0-07 | governance appender: kinds `halt`, `rearm`, `book_state`, `admissibility_reweight` | B.4-B.7, B.17 |
| M0-08 | schemas `event_calendar.v2.0`, `macro_state.v2.0` (`flags`, `annotations`, `concentration`, `runtime`), `overlay_decision.v2.0` | C.2 |
| M0-12 | `cost_per_side(instrument, date, price, side)`; instrument table (`type`, `leverage L`, effective-dated `tick_table`, `cost_class`, `eligibility`) | B.1, B.8, B.15 |
| M1 PIT | `pit_value`, `PITValue`, `MissingInput`, `RunContext`; bindings `KODEX200_PDF`, `NAV_LINE_CLOSES`, `KRX_MARKET_CAPS_005930_000660_KOSPI`, the VIX channel; official-close loader; lag-audit result per decision; KIS quote-check status (recorded as "not run" without KIS access, L44) | B.1, B.8, B.12, B.15 |
| M1 runtime (`core/engine/books.py`) | per-book states, `runtime_halt` / `runtime_rearm` (OPS), input and book counters, `ever_armed`, persistence, `calendar_coverage` HALT | B.4-B.7 |
| M1 calendars | `is_session`, `session` (open time, closing-call window, CSAT / late-open flags), `next_session` / `prev_session`, `close_print_bound_utc`, `regime_tags(market, d)` (`price_limit`, `tick_regime`), `kr_open_gap_session`, `gap_sessions`, signed calendar version | B.4, B.13-B.15 |
| M2 | `compose(vt, overlays, ladder, post_rearm_cap)`, `ComposeResult.binding`, `guard_acting`, `market_vol_target`, costed engine, reference-mode scaffold (`reference_only=True`, `tests/reference/`) | B.0, B.2, B.8, B.18 |
| M4 | `composite_weights`, `risk_layer`, recommended / specification book builders, `base_weights` (R-15 re-weighting event) | B.17 |

Gaps to close with the M1 owner: (1) session-count arithmetic "t + 10 sessions of the book's primary-market calendar" for dates beyond 2027-12-31 or before 2026 (history replays need the effective-dated calendars); (2) a per-book declared `primary_market`; (3) the CSAT late-open date list for `kr_open.late_open_days` (absent from `data/calendars/KRX.json`); (4) the stock tick table and pre-2023-12-11 ETF ticks (owner-signed).

### E.2 Exposed to later milestones

| To | Name | Shape |
|---|---|---|
| M6 builders | per-book runtime entries; `LadderState`; `ConcentrationBound`; `Annotation`; gap flags; `build_event_calendar`; opening-gap inputs (overnight SOX, S&P, ΔUST10, USD/KRW) for the context log | fields of C.2 |
| M7 | `drawdown_ladder` fold + binding-share count (R-31 header commit; T-STEP-01..04, I-15); hard stop and caps for the `with_risk_layer` line (T-RLAYER-01); `fill_tracking_error`; `n_halts`; stack-card inputs (binding shares of invariants) | pure functions over NAV / weight paths |
| M8 | `runtime_halt` / `runtime_rearm` with RISK and operator modes for `bounds_ok`, `run_error`, lag audit; weight books for `macro.engine_feed`; `book_nav` for `forward_monitor`; operator-kill integrity trigger; per-card switch counts; T-SCOPE-01, T-OBS-01 | B.5-B.8, B.17 |
| M9 | `var_display_scale`; post-holiday session tag; `scenario_tag` events for the replay library | B.13-B.14 |
| UI (Macro, Derivatives pages) | event windows, annotations, per-book HALT state, D1/D2 values, indicative-quote marker during halts | read-only |
| Tech-fund programme | `simulate_fill` / `NonFillable.reason` (INV-1, INV-2), `concentration_bound` templates (RISK-1 / XS-22 as an owner proposal), ladder (XS-08) | G |

---

## F. Ambiguities, contradictions and conservative-reading decisions

| # | Issue (lines) | Reading adopted |
|---|---|---|
| F-1 | Order of NAV update, re-arm check, ladder evaluation and composition inside one decision is not stated (L1179, L3278-3303). The pseudocode updates `hwm_hard` / `ref_step` before the `if book.halted` test while its comment says "references frozen until re-arm". | Order of B.0. While HALTED the two reference updates are skipped (frozen); identical to the pseudocode when NAV is flat. |
| F-2 | Hard stop in FORWARD-SIM books: "the specification book with that card's factor applied" (L888) vs "card and FORWARD-SIM books exclude it (R-22 rule 6)" (L5400) and rule 6 (L2348). | No hard stop, no caps, no RISK class in card on/off/S and FORWARD-SIM books, except R-31's card book. They keep OPS states. |
| F-3 | `flags.hard_stop ∈ {armed, halted, rearm_refused, post_rearm_cap}` and the per-market `flags.ladder_*` have no stated mapping or book (L3578-3584). | `rearm_refused` while a hard-stop cause is uncleared and decided_session < `rearm_not_before`; `halted` while HALTED by a hard-stop cause otherwise; `post_rearm_cap` while `post_rearm_left > 0`; else `armed`. `flags.hard_stop` and `engine_state` describe the recommended book; `ladder_step`, `ladder_dwell_left`, `block_new_entries` describe the book named by `ladder_steps_act_in`. Display fields only. |
| F-4 | "the bound is recomputed on current prices" (L1411) gives no formula; a full recompute needs every constituent close. | Formula of B.1 (price-relative re-weighting against the line's own return); names without a close keep their basket weight, labelled. |
| F-5 | "Leveraged and inverse products count at × L" (L1585): sign for inverse products not stated. | Caps are tested on \|L\|-weighted look-through, so an inverse position never lowers a measured concentration; the signed figure is printed. No default book holds an L/I ETF. |
| F-6 | `b̃`: "the benchmark b̃ capped under the template" (L1585 (2)); which benchmark and how excess is redistributed is not stated; aggregate threshold "names above 4.5%" on `s_i` or on `g·s_i` is not stated; semiconductor membership is not defined and the §6.1 example prints `semis_bound: null`; `pair_risk_contribution` has no formula. | Benchmark = the line's own basket shares `s`; cap single names at the template level, redistribute the excess pro rata to uncapped names, iterate. Aggregate set = names with `s_i > 0.045` (a superset of the NAV-share set, so the bound is lower). Semiconductor set from an owner-signed list, at least 005930 and 000660; `semis_bound` null only when no basket is available. Risk contribution = the pair's share of the line's 63-session variance (Euler), display only, nullable. Owner to confirm. |
| F-7 | `binding_factor` enum has no value for the `pair_35` template; tie order is not stated. | `pair_35` binds as `aggregate`; ties in enum order. Only `msci_25_50` is default. |
| F-8 | D2 option (b) `"-1.5*sigma_book"` is a string formula; D1/D2 ruling timing while HALTED is an open owner question (L5462). | Not evaluated until an owner ruling defines it for the book; default −0.15 stays. A ruling is recorded with `effective_from` and not applied to a HALTED book's references until the owner answers. |
| F-9 | Reason codes are named three ways: config tokens (L4354-4358), `"acting_input_stale:<series_id>"` (L1951), `run_error` vs `acting_step_error_beyond_limit` (L1243, L4358). | `reason_code` = the config token; the input case keeps M1's `acting_input_stale:<series_id>`; the step-error case uses `run_error` (T-OBS-04 asserts it). `series_id` and `component` carry the detail. |
| F-10 | §12 M5 lists "calendar coverage" and "the operator re-arm cases" among M5 additions (L6367) while T-CAL-02 and the HALT clauses of T-LAG-01 run at M1 (L5551, L5597). | M1 builds the HALT; M5 adds the operator-mode re-arm and the multi-cause merge and re-tests both. |
| F-11 | Heartbeat scope: no v2.0 daily book reads the `QuoteFeed`; nothing polls it unless the operator engine is ARMED (`runtime.py:240-252`). | The trigger binds only to books flagged as reading the feed (intraday simulated entries); none by default; "not measured" when nothing polls. Synthetic test only. |
| F-12 | "new-entry decision" is undefined for weight books and for operator rules (L1183). spec_architecture F-18 reads it as any BUY-side order; code_rules_engine A-8 as a caller-stated flag. | The caller states `is_new_entry`. Weight books: a line with `w_held == 0` and `w_target > 0`. Operator practice orders: BUY side in the blocked market. Increases of an existing holding, holds and exits are not blocked. Coordinator to confirm one definition. |
| F-13 | "Switches above 2× the budget of 14 a year" (L1603): window not stated. | Trailing 252 input dates; log when transitions > 28. Logging only. |
| F-14 | Drift releases: window start is given (release − 30 min), the end is not (L1626). | Release + 90 min, as CPI/NFP (08:30 → 10:00). |
| F-15 | Night-futures FOMC window: "The same windows apply to KOSPI200 night futures" (L1627) vs example `resume_condition: null` (L3846). | Artifact as in the example; the block ends with the US window's effective end (same resume rule). No intraday futures book exists in v2.0. |
| F-16 | The daily KR open window and the circuit-breaker window have no event `type` in the enum (L3819). "No simulated stops are placed inside the window" (L1626) has no object: the simulated book has no resting stop orders. | Generated at query time from the session calendar and an injected reopen instant; not stored as events. The stop sentence is recorded, nothing to build. |
| F-17 | A `delayed` event with no new time; FOMC resume needs intraday VIX at ≈ 14:00 and 15:00 ET. | No window until rescheduled. Missing VIX → resume at 15:30 ET. |
| F-18 | Limit price "rounded to the tick toward the previous close": the stock tick table is not in the spec (only "stocks reformed 2023-01-25", L2045); the price at which the tick is read is not stated; the spec gives no 000660 prices for 2026-07-30/31. | Tick read at the unrounded limit price from the owner-signed table; an unreadable tick table → "not tradable in the simulated book" (L2863). Tests pass the tick explicitly. |
| F-19 | `decision_price_source ∈ {snapshot_1519, official_close}` has no value for the 14:49 KST, CSAT and 15:50 ET snapshots; the book behind QF1's 0.19% / 0.0013 is not stated; the KIS quote field is UNVERIFIED. | Acting books always record `official_close` (the fallback, labelled) until the KIS check is verified; the snapshot variant exists only as the printed tracking-error line; other snapshot clocks are described in `extras.fill_model`. T-FILL-01's golden stays REFDATA. `fallback: post_close_session_UNVERIFIED` is never used as a fill source. |
| F-20 | `available_at_utc = bar_end + latency`: no latency value (L2924). | Declared per source in the registry; a bar source without it is unusable. Bars are never acting closes. |
| F-21 | The literal v1.2 ladder and QF4's 11-session fix are defined outside this spec (`.v1.2_INTEGRATION_backup.md`, QF4), not on this machine. | G-LAD-01..03 stay REFDATA; do not reconstruct the rules from the cycle counts. |
| F-22 | "implied share (B3a anchor)" (L5832): the implied-share formula and the anchor weights are in DLA §7, not here. | REFDATA; `pair_share_kospi` in production comes from `KRX_MARKET_CAPS_005930_000660_KOSPI`. |
| F-23 | "beyond its 5 misses" (L5674, task text) vs "when an input counter reaches … `halt_after_consecutive_decisions`" (L1870). Same for NAV: "more than 2" with limit 3. | HALT when the counter reaches the declared number (5 for the basket, 3 for NAV lines). |
| F-24 | Top-level `halt.rearm_not_before` with several causes (L3614). | The latest `rearm_not_before` among uncleared RISK causes; null when none. |
| F-25 | TASK-M5-12 says FORWARD-SIM books run "in the simulated order book"; L1184 says they "never pass through `engine_feed`" and are computed by the forward evaluator. | M5 provides the book class for every id; only recommended and specification books are fed by `engine_feed` (M8); FORWARD-SIM books are driven by the forward evaluator and recorded. |
| F-26 | `KRX_HOLIDAY_GAP` required fields `scheduled_utc`, `source`, `windows` have no stated values. | `scheduled_utc` = the gap session's open; `region: "KR"`; `source: "core/calendars"`; one `annotate_only` window over the session. |
| F-27 | Existing `EngineState` contract ("never re-arms itself", mode not persisted) vs automatic per-book arming and re-arm (L1179-1180). | Per-book runtime only; `EngineState` / `EngineRuntime` and tests `engine/test_02-04,18,78` untouched. No operator rule is ever armed automatically. |
| F-29 | Samsung's 29.8% is used two ways: as a share of KOSPI in G-POST-01 ("Samsung 29.8% + hynix 23.8%" = 53.6%, L5832) and as the look-through share of the KODEX 200 line in the bound arithmetic (22.5 / 29.8, 0.05 / (0.298 − 0.225); L896, L3705), while the pair is 53.8% of KODEX 200 on look-through (L1585). SK hynix's look-through share of the line is never printed. | The production bound uses the day's basket shares. T-CAPS-01 asserts the printed arithmetic on an inline basket with s(005930) = 0.298; nothing is asserted on hynix's share. |
| F-28 | Tech-fund XS-22 / RISK-1 (R3:L1310, R3:L811): "0.35 pair cap on look-through for market and ETF books when the pair share exceeds 0.45" vs R-07 option (c) "a 35% pair cap … without v1.2's 0.45 trigger" and D1 default `msci_25_50` (L1585). | D1 default stays; XS-22 is an owner proposal, not built. XS-08 (R3:L1296: non-cumulative, total book NAV, re-arm at 0.5 with a reset reference) matches v2 as written. |

---

## G. DO-NOT-BUILD items and invariants that bind this area

Invariants:
- P0 / item 21 (L6162): no order, cancel, withdrawal, deposit-address or transfer path, no broker adapter. `core/engine/orders` is "simulated fills only, never a broker path" (L2893). The KIS spread-snapshot "request" is a read on the quotation allowlist only (T-RO-02).
- P2 / R-02: no multiplier above 1.0; `ladder`, `post_rearm_cap ∈ {1.0, 0.5}`; composition by `min()`, "never 0.25 × vt"; `composed ≥ 0.5 × vt` outside HALTED, asserted on `composed`, never on `gross` (L80, L881). "A ladder path composed by product raises" (L3338). Item 31: product-composed de-risk stacks refused.
- P16 (L636-638): "Nothing may freeze, or quietly shrink, the book." "Every hard stop has an explicit, automatic re-arm (R-07). Only the hard stop and risk-limit breaches (class RISK) carry the 10-session refusal and the 0.5× cooling-off; an operational HALT clears when its cause clears." "A HALT is scoped to the book whose own trigger fired; other books continue."
- HALT scope C-1 (L82, L1178): only an `acting_exposure` input bound to a book, the book's own NAV or its own artifact can HALT it; a `risk_model` or `context` input, a `hedge_state` exception, an `event_calendar` or `context_log` validation failure never HALT.
- "The hard stop makes no protection claim." (L1179, L1586); `protection_claim: false`.
- R-08: "It changes no exposure." (L1597). R-10: "**No event tag changes any weight.**" (L1634); `tags_change_weights: false`, `daily_book_blackouts: false`, `gross_cut: false`, `gross_rule: false`.
- R-27: "It never changes a card's gate statistics"; "No gross rule follows from limit-locks"; "A daily close is never derived from intraday bars."
- Card evaluation books exclude the hard stop and caps (R-22 rule 6, frozen with the package): do not wire `concentration_bound` or the hard stop into card on/off/S books.
- R-31 steps: recommended book only as `INVARIANT_STEP` (binding share ≤ 0.10) or after a PASS; item 22 (L6166) lists "a ladder step that binds on more than 10% of days before its CARD-P passes" as a non-PASS output that must not reach the recommended book.
- Reference-mode results (literal v1.2 ladder, QF4's fix) "never enter a book, a card or an artifact"; `core/` cannot import that code.
- Owner decisions D1, D2 are read by reference only; a ruling "never demotes a card"; "Neither number may change a default" (spikes).

DO-NOT-BUILD list entries touching this area (§10.2):
- Item 3: "A VIX-term-structure switch for momentum (0× or halved) or for reversal (1.5×), and the post-stress-clear 0.5× momentum schedule".
- Item 4: "Cut-and-re-add gates on existing exposure" (−0.088 Sharpe; −0.185 in 2020–26) — the reason R-08 is an annotation.
- Item 12: "24-hour pre-event blackouts; swing-book blackouts around FOMC, CPI, NFP, BoK or export prints; a KRX quad-witching blackout; the index expiry-close fade". R-10 "Not built" adds "daily-book blackouts" and "momentum decision-day size-down (backlog BL-O02)".
- Item 19: "intraday circuit-breaker prints as closes"; "a provisional, intraday or bar-derived row as an acting close" (refused shape, L6250).
- Item 33: a stock book as a market-gross scalar; "An ex-pair stock basket under the Korea caps is a separate card. It opens only on the R-07 conditions: the owner asks for full Korea beta at the cap, a stock-book card has passed and limit-lock flags exist (D1)".
- Item 2: nothing above 1.0 (applies to `gross`, `post_rearm_cap`, step multipliers).
- v1.2 items struck by R-07 and not to be rebuilt: the 0.05 absolute single-name cap and "v1.2's 0.45 trigger" (L1585, L1588); "queue orders, no market orders, cancel resting orders" (needs a broker path; backlog, L1632); opening-auction limit orders and closing-auction routing ("have no object in a read-only app", L1629).

Tech-fund items landing on M5 code (owned by the tech-fund brief; recorded so the same functions take them):
- INV-1 (R3:L132-137, G-04 R3:L801): decide at the close of t, fill at the KRX official close of t, "never NXT or after-hours prints" — consistent with B.15.
- INV-2 (R3:L139-144, G-05 R3:L802): "no entry at a locked limit-up close; an exit at a locked limit-down close carries to the first unlocked session at 2x cost; VI, circuit-breaker and halt days are unfillable" — extends `NonFillable.reason` and adds a 2× cost on the carried exit ("an assumption, not measured"; "needs daily limit-state flags").
- XS-14 (R3:L1302): "Do not count R-08 as factor-crash protection".
- G-56 / G-57 (R3:L868-869): ladder clarifications and threshold units are owner decisions; no code change in M5.
