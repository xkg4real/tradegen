# spec_M7_gate_package — CARD-P gate package v2 (R-21, R-22, R-23, R-24, R-34): harness, tests, acceptance test, freeze

Read completely (2026-10-05): SPEC = `QUANTGEN_Quant_Council_2026-10-03/claude_code/QUANTGEN_MACRO_INTEGRATION.md` L2115-2646 (R-21..R-24), L3395-3478 (R-34), L4752-4873 (8.1-8.3), L4967-5302 (8.5-8.7); cross-read L14-178 (Quick start, changelogs), L536-635 (P5-P15), L1078-1114 (3.5), L1416/1440/1969 (cash rows, T-ROLE-02), L2976-3030 / L3065-3154 / L3262-3360 (R-28/R-29/R-31 header facts), L3909-4120 (6.5, 6.6), L4136-4152 and L4498-4619 (section 7 `owner_decisions`, `gate`), L4874-4965 (8.4), L5367-5488 (8.9, 8.10), L5489-5736 (9.0-9.3.1), L5947-6035 (goldens, 9.3.3, 9.4, 9.5), L6072-6252 (section 10). Tasks: `prep/tasks/M7.json` TASK-M7-01..17. Code: `core/quant/validate.py` (V), `core/quant/backtest.py` (B), `core/quant/gjr.py`. R3 = `R3_TF_neural_link.md` L1283-1301 (XS-11/12/13 only).

Legend: [N] new file, [E] edit. `Lnnnn` = SPEC line. SILENT = the spec names the statistic but gives no formula; the formula written here is the textbook one and is listed again in section F. Feasibility: SYNTH / REFDATA / OWNER.

## 0. Five facts the coordinator needs first

1. **The freeze (TASK-M7-17) cannot be executed honestly on this machine.** It needs: the frozen reference data (`/home/claude/quantgen_macro_data/`, absent), `QC_modules.csv` and the section 9.5 ledger seeds with their difference series (absent), owner inputs (`sleeves.<market>.notional_nav`, ECOS code and calendar of `BOK_CALL_RATE`, optional D6 ruling), the French 1926+ daily file for R-29 (never acquired: HTTP 403, L3080), and an external timestamped anchor (the QUANTGEN folder is **not a git repository**: `git rev-parse` fails). Conservative reading: build the whole harness and every SYNTH test; leave `gate.package` at `definitions_md5: written_at_freeze` (state NOT_FROZEN); every macro card stays `NOT_RUN`; `docs/macro_overlay_study.py` refuses to run; no exposure change.
2. **Acceptance attempts are a scarce, counted resource: 2 failures across all 2.x versions end evaluation under v2 (L2181).** Tests and dry runs must write to temporary copies only (T-HERM-02, L5608). The production `gate/acceptance_runs.jsonl` must stay empty until the real attempt. Never run the acceptance test on stand-in data against the production log.
3. **The spec homes the harness in `core/quant/backtest`, which is the 155-line Signals-page backtester** (B:1-155). Paths marked "proposed" may be renamed (L89). Layout used here (same as `code_quant_gate.md` D1): new files that contain nothing but harness code, because `definitions_md5` hashes harness source files (L4820).
4. **Several statistics are named but not defined in the spec** (CDaR95, LW-HAC kernel, influence function, Politis-White details, time under water, re-entry lag, PSR vs S, Harvey-Liu haircut, BY q, de-clustering, the five negative-control rules, the three CDaR-guard candidates, the R4 B3 positive-control rule). They live in research scripts that are not on this machine. Section F lists each with the reading used.
5. **Verified numerically on this machine (pure formulas, no data):** T-DSR-01 0.950502 / 0.900397; T-STEP3-01 R-03 0.9811 (N 6.3), 0.9459 (N 12.6), R-04 0.7723; break-even N 11.86; `e_exact(2)` 0.56419, `e_closed(2)` 0.51976, `e(12.6)` 1.68837; MDE factor 2.123173; T-PBO-01 noise panel 0.535897 (6,897 of 12,870) with the existing `V.pbo_cscv` rank convention; 200-panel mean 0.4998 (SD 0.227, 1.8 s with block sums).

---

## A. Scope

| Task | Deliverable (one line) | Target files |
|---|---|---|
| TASK-M7-01 | Hash-chained family trial ledger: `append`, `hash`, chain verify, harness-only rows, family filing at rho >= 0.5, null runs never appended | [N] `core/quant/gate_ledger.py`; ledgers under `<macro_artifact_dir>/ledgers/<family_id>.jsonl` (proposed); family hash in the M0 rules store |
| TASK-M7-02 | Research-phase seeds, one row per distinct configuration (R-03 26; R-06 KR + DLA-U1..U5 + DLB-T1h; R-28 94; R-31 L1-L6) | [N] `tests/fixtures/macro/ledger_seed_<family>.csv` + difference series; manifest entries. REFDATA: sources absent |
| TASK-M7-03 | `diff_corr`, `emax_sim`, `emax_iid`, `n_equiv`, `n_clusters`, `deflated_dsr`; Kish static check | [N] `core/quant/gate_ledger.py` |
| TASK-M7-04 | `step3()`; computed selection factor f, max over row-set readings; printed N lines | [N] `core/quant/gate_ledger.py` |
| TASK-M7-05 | Anchored timestamps for `gate.step3.spec_versions` and seed `run_utc`; `step3()` refuses unanchored ones | [N] `gate_ledger.py`; [E] M0 rules store. OWNER: needs a git repo or external anchor |
| TASK-M7-06 | `lw_studentized_boot`, `pw_block_psi`, `se_ladder`, `power_line`, `by_qvalue`, `harvey_liu_haircut`, `lo_adjusted_sr`, UNDERPOWERED guard | [N] `core/quant/gate_stats.py` |
| TASK-M7-07 | `pbo_cscv(configs, objective, S=16)`, `pbo_null` | [N] `core/quant/gate_stats.py` (name collides with `V.pbo_cscv(pnl, *, S=8)`; keep both, separate modules) |
| TASK-M7-08 | `episodes`, `episode_benefits`, `post_trough_window`, cost episodes, shock-type table, leave-one-crisis-out | [N] `core/quant/cardp.py` |
| TASK-M7-09 | `excess_returns` with the cash leg by unit; refusal on a missing cash day | [N] `core/quant/cardp.py` |
| TASK-M7-10 | `start_band`, `midpoint_halves`, `regime_lines`, stability floor, card-book convention (rule 6) | [N] `core/quant/cardp.py` |
| TASK-M7-11 | `cardp_evaluate`, `es_h`, `pc1_prime`, `tail_exposure_ratio`, `pc3_noninferiority`, `overlay_card_eval`, `gjr_null_percentile`, `placebo_panel`; verdict order coded once | [N] `core/quant/cardp.py` |
| TASK-M7-12 | `timing_profile` + private `timing_probe` sandbox; positive control | [N] `core/quant/cardp.py` (or `core/quant/gate_timing.py` if the static isolation check is easier on its own file); fixture `KR_SOX_KRW_gate_B3` (REFDATA) |
| TASK-M7-13 | I-05 full-sample lag audit over COMPLIANT goldens | tests (golden tier). REFDATA |
| TASK-M7-14 | Four CARD-P header drafts (MACRO-R06-KR-ETF, MACRO-R28-US-TREND, MACRO-R06-US-FUT, MACRO-R31-KR-ETF), each md5'd | [N] `<macro_artifact_dir>/cards/drafts/*.json` (proposed). OWNER: `notional_nav`, listing dates, ECOS code |
| TASK-M7-15 | `gate_acceptance_test`, placebos, negative controls, horizon-matched PC-2 decision, D6 guard, attempts log, bounded redesign | [N] `core/quant/gate_package.py`; `gate/acceptance_runs.jsonl` |
| TASK-M7-16 | Definitions manifest; `verify_package()` re-hash used by the study runner | [N] `core/quant/gate_package.py`; `gate/definitions_manifest.json` (proposed name) |
| TASK-M7-17 | Run pre-freeze tests, run the acceptance test once, write `gate.package`, log `package_freeze` | `gate_package.freeze()`; rules store; `acceptance_report.json`. REFDATA + OWNER: not executable here |
| tests | One hermetic module registered in `tests/run_all.py` (one import line, one list line; pattern at run_all.py:30-44) | [N] `tests/macro_gate_acceptance.py`; [N] `tests/fixtures/macro/` |

`core/quant/backtest.py`: no change needed. Add re-export lines for the spec's dotted names only if another milestone imports them by that path.

---

## B. Build spec

### B0. Conventions shared by every function

- Inputs are aligned 1-D float arrays of **daily simple excess returns** (R-22) plus the session dates. Never read `V.GATE` (it is mutated at run time); pass B, block, seed explicitly from the `gate.*` blocks.
- Sharpe ratios, Delta-SR, SE and MDE are annualised: per-period value x sqrt(252) (daily) or sqrt(12) (monthly). `T_years = sessions / 252` (L2575).
- Names: `delta_sr`, `boot_delta_sr` for Sharpe differences; "DSR" only for the deflated Sharpe ratio (L2437).
- RNG: `numpy.random.Generator(PCG64(SeedSequence(seed)))`, child seeds by `SeedSequence.spawn` for parallel workers, single-threaded BLAS; same seed + store hash + snapshot + package version gives outputs within relative 1e-12 (T-REPRO-01b, L5667). Seed 11 everywhere unless a redesign logs fresh seeds.
- A p-value whose resample count is 0 is stored as the string `"< 1/B"` and compared as `1/B`; no card field holds numeric 0 (T-PZERO-01, L2567, L2631).
- Verdict strings: `PASS`, `REVISE`, `REJECT`, `INSUFFICIENT_DATA` (schema enum L4007; equals `V.DECISIONS`). No fifth verdict (L4774). `NOT_RUN` is a card state, not a verdict.
- Verdict order for "worst of": `REJECT < INSUFFICIENT_DATA < REVISE < PASS` (L2168, L5226).
- Reason codes (L4779): `sufficiency`, `inconclusive`, `underpowered`, `do_no_harm`, `timing_fragile`, `stability`, `claim_not_shown`, `estimator_calibration`, or the failed check's id.
- Refusal = raise a typed exception and write nothing. Partial verdicts are never written (L2245).
- Every function that reads data takes the run's `RunContext{decision_utc, knowledge_utc, run_mode}` and reads frozen fixtures or the PIT store only: closes with `value_status = official_close` and `session_date` (L2133-2137, L1105).

### B1. `core/quant/gate_ledger.py` — R-23

**Ledger row** (L2440, L2500, L6020; one JSON line per configuration ever run, research phase included):

`config_id`, `family_id`, `rule`, `params` (signal, threshold, target, lookback, multiplier, lag included), `estimator`, `window`, `cap`, `instrument_book`, `rebalance`, `timing_class` in {`VALUE`, `NON-COMPLIANT`, `COMPLIANT`}, `start_convention`, `market`, `span` [start, end], `cost`, `phase` in {`research`, `card`}, `run_utc`, `run_utc_anchor` (git commit or external anchor; TASK-M7-05), `script`, `results_md5`, `diff_series_ref`, `prev_row_md5`.

`config_id` = md5 of canonical JSON of the frozen row-set key `[rule, params, estimator, window, cap, book, rebalance, timing_class, start_convention]` (L2500). Two configurations that differ only in target, threshold, multiplier or lag are two rows (T-SEL-01 (h)).

```python
def append(family_id: str, config: dict, *, ledger_dir) -> dict      # ledger.append; the ONLY writer; called by the harness on every run
def hash(family_id: str, *, ledger_dir) -> str                        # ledger.hash = md5(canonical_json(sorted(ledger_rows)))   L2445
def verify_chain(family_id, *, ledger_dir) -> None                    # raises LedgerRefused on a broken prev_row_md5 chain
def family_ledger(family_id) -> FamilyLedger                          # rows + hash + loader of difference series   L1092
def file_family(d_new, rule_id) -> str                                # family by rule (QC_modules.csv); else the family whose rows correlate >= 0.5; else refuse
```

Rules (L2440, L2512-2516):
- Rows are appended by the harness on every run of a registered rule's code path, research scripts included; never by hand.
- **Never appended:** acceptance placebos, the 20-shift panel, GJR-null paths, D4 panels. They go to the attempts log or the card's evaluation log.
- Every lag of the timing profile and every variant run (instrument book, rebalance, band, estimator) **is** a row (L2482); L <= 0 rows carry `timing_class: NON-COMPLIANT`.
- Refused: a chain that does not verify; a row not appended by the harness; a row without `timing_class`; a header without `ledger_hash_at_registration`; after a run, `ledger_hash_at_run` (ledger including the run's own rows) must equal the stored ledger's hash or the card is not written.
- Test runs write to a temporary copy (T-HERM-02).
- The family hash is committed with every header (L2440). `core/rules` stores the ledger hash per family (L2437).

**N_eff and the deflated Delta-SR** (L2444-2467, verbatim algorithm):

```python
ledger_hash  = md5(canonical_json(sorted(ledger_rows)))
N_raw        = len(ledger_rows)                         # revision counts are never N
d_k          = x_k - x_comparator_k                     # comparator: overlay-off (CARD-O); S (CARD-P)
C            = corr([d_k for k in ledger])              # on the common window
rho_bar      = mean_offdiag(C)
N_hat_linear = rho_bar + (1 - rho_bar) * N_raw          # BLdP eq. 9 (linear); printed bound only
N_clusters   = n_clusters(C)                            # average linkage on sqrt(0.5*(1-rho)), cut at sqrt(0.25), i.e. rho >= 0.5
E_sim        = mean(max_k Z_k), Z ~ N(0, C)             # >= 200,000 draws, seed 11

def e(N):                                               # expected max of N iid N(0,1)
    if N <= 1: return 0.0
    if N < 2:  return emax_iid_exact(N)                 # integral of x*N*phi(x)*Phi(x)**(N-1); never Euler-Mascheroni below 2
    return (1 - g) * Phi_inv(1 - 1/N) + g * Phi_inv(1 - 1/(N*math.e))    # g = 0.5772156649

N_equiv = e_inverse(E_sim)       # bisection on N in [1, 1e6]; e drops at N = 2 from exact 0.564 to closed-form 0.520,
                                 # so any E_sim in [0.520, 0.564] gives N_equiv = 2
N_eff   = max(N_clusters, N_equiv)
hurdle  = e(N_eff)               # = E_sim whenever N_equiv >= N_clusters
SE_obs  = LW-HAC SE of the card's delta_SR vs its comparator (B2)
SE_null = median LW-HAC SE of delta_SR over the ledger's rebuilt trials of the same statistic    # fewer than 2 trials: SE_obs
          # >= 30 independent trials: V = cross-trial variance of delta_SR (BLdP's V); both printed
deflated = Phi((delta_SR - SE_null * hurdle) / SE_obs)
```

Signatures and implementation notes:

| Function | Notes |
|---|---|
| `diff_corr(family_id) -> np.ndarray` | Pearson correlation of the stored difference series on the single common window (intersection of all spans), so C is PSD. Missing series: raise `CorrUnavailable` |
| `n_clusters(C) -> int` | `scipy.cluster.hierarchy.linkage(squareform(sqrt(0.5*(1-C))), "average")`, `fcluster(Z, t=0.5, criterion="distance")`, count labels |
| `emax_sim(C, draws=200_000, seed=11) -> float` | Draw via eigen-decomposition (`multivariate_normal(..., method="eigh")`): near-duplicate rows make C singular, so Cholesky fails. Tolerance in T-NEFF-01 is 0.01, so the draw method need not match the research script bit for bit |
| `emax_iid(N) -> float` | `e(N)` above. `emax_iid_exact` by `scipy.integrate.quad` on [-12, 12] |
| `n_equiv(emax) -> float` | `emax <= 0` -> 1; `emax < 0.520` -> bisect the exact integral on [1, 2); `0.520 <= emax <= 0.564` -> 2; else bisect the closed form on [2, 1e6] |
| `deflated_dsr(dsr, se_obs, se_null, hurdle) -> float` | `Phi((dsr - se_null*hurdle)/se_obs)`; the three inputs must share one unit; `units in {daily, monthly}` argument on the DSR API; an annualised SR passed with a daily T raises (T-DSR-02) |
| `n_eff(ledger, draws=200_000, seed=11) -> NResult` | `{N_raw, rho_bar, N_hat_linear, N_clusters, E_sim, N_equiv, N_eff}` (L1093) |
| `step3(card) -> Step3Result` | below |

**`step3(card)`** (L2468-2482, L4762):
- **CARD-O:** pass iff `deflated >= 0.95` (`gate.step3.card_o_bar`).
- **CARD-P:** not gated. Prints DSR vs 0 and PSR vs S. Computes the selection factor f.
- **Printed on every card:** `N_raw`, `N_hat_linear`, `N_clusters`, `N_equiv`, `N_eff`, `E_sim`, `SE_obs`, `SE_null`, `V_trials`; the deflated value at `N_raw` and at `N_hat_linear`, with the flag `"step 3 borderline"` if the value at `N_hat_linear` is < 0.95; the break-even N (the N at which deflated = 0.95; inferred from L5383 "0.951 at the break-even 11.9", L2535); the one-sided z-check (`z >= 2.50` for <= 8 pre-registered cells; `3.34` one-sided Bonferroni beyond); a BY q-value from the global ledger; Holm-adjusted p-values across the run variants; the verdict at f = 1 and at f = N_eff; f under each row-set reading.
- **Never:** the Kish form `M / (1 + (M - 1) * rho_bar)`, or a revision count used as N. A static check enforces both (T-STEP3-02; `gate.step3.forbidden: [kish_design_effect, revision_count_as_N]`).
- **Fail closed** (L2516): if C cannot be built, CARD-O -> no verdict is written; CARD-P -> f defaults to `N_raw`.

**Selection factor f** (L2472-2474; computed, never declared; a header that declares `selection_factor` is refused):

```python
def selection_factor(card, ledger_snapshot, spec_versions, acceptance_f=None):
    rows = rows of the snapshot named by ledger_hash_at_registration
    rows = [r for r in rows if not r.own_run_of(card) and not r.null_distribution]      # row_set.excludes
    t_fix = earliest anchored instant at which this exact config was fixed:
            the header commit (md5 externally anchored) or a published SPEC version (gate.step3.spec_versions)
    if any timestamp used is unanchored: raise UnanchoredTimestamp                      # TASK-M7-05
    f_by_reading = {}
    for reading in ("market_scoped", "family_wide"):                                    # contested filings counted both ways
        R = rows under reading
        touched = [r for r in R if overlaps(r.span, card.evaluation_span)               # overlap_rule: any_overlap
                                   and r.run_utc < t_fix]                               # rows run after the commit are sensitivity rows
        f_by_reading[reading] = 1.0 if not touched else n_eff(R).N_eff                  # Bonferroni N_eff
    f = max(f_by_reading.values())                                                      # combine: max   (T-SEL-01 (g): 1.3 and 2.9 -> 2.9)
    if acceptance_f is not None: f = max(f, acceptance_f)                               # T-SEL-01 (e): larger binds, both printed, run never refused
    return f, f_by_reading
```

- f multiplies the PC-1' p-values and the PC-3 p-values (L2155, L2161). `p_adj = min(1, p * f)` (cap at 1 is cosmetic, SILENT).
- For each drafted CARD-P the acceptance report prints f under each reading with `N_raw`, `N_clusters`, `N_equiv`, `E_sim` on the frozen seed, before any card runs (L2473).
- Output `selection_factor = {value, rule: "computed_by_step3", alt_value}` (L2509, L4019).
- Indicative values (not asserted): R-06 KR 1.26-1.30 on R4's rows alone, 1.49 with the DL-A grid, 2.87 family-wide (L5387).

### B2. `core/quant/gate_stats.py` — R-24

| Function (L2552-2559) | Algorithm |
|---|---|
| `lw_hac_se(x_a, x_b) -> (se, psi)` (helper) | Delta method of Ledoit-Wolf (2008). `y_t = (x_a, x_b, x_a^2, x_b^2)`, `v = mean(y)` = (mu_a, mu_b, g_a, g_b). `grad = (g_a/(g_a-mu_a^2)^1.5, -g_b/(g_b-mu_b^2)^1.5, -0.5*mu_a/(g_a-mu_a^2)^1.5, 0.5*mu_b/(g_b-mu_b^2)^1.5)`. Influence function `psi_t = grad . (y_t - v)`. `se = sqrt(LRV(psi)/T)` x sqrt(252). LRV kernel SILENT: use the QS kernel with Andrews (1991) AR(1) automatic bandwidth (matches "QS 0.0605 / 0.130" of G-PWR-01, L5972); print the Bartlett 10-lag value ("NW10") beside it |
| `lw_studentized_boot(x_a, x_b, block, B=2000, seed=11, null=0.0) -> {dSR, se, t_obs, p_lw, p_hac, block, n_blocks}` | Circular-block resampling of the paired rows (same indices for both series; index idiom of V:140-143). `t_obs = (dSR - null)/se`. For each resample: `dSR*`, `se*` from the block-sum variance of `psi*` (LW 2008 section 3.2.2), `t* = (dSR* - dSR)/se*` (null-centred). `p_lw = #{t* >= t_obs}/B`. `p_hac = 1 - Phi(t_obs)`, printed beside it. `n_blocks = ceil(T/block)`. Step 5 (CARD-O): `null = 0`. PC-3: `null = -delta` |
| `pw_block_psi(x_a, x_b) -> int` | Politis-White (2004, Patton-Politis-White 2009 correction) circular-bootstrap block length on the scalar series `psi_t` (**not** on d or d^2), floored at 21 sessions. If it cannot be computed (non-finite or zero denominator): return 250 and log the event (L2620) |
| `se_ladder(x_a, x_b, blocks=(10, 21, 63, 126, 250)) -> {se_hac, se_by_block, se_plateau, n_blocks}` | `se_by_block[b]` = SD of `dSR*` over the B circular-block resamples at block b (annualised). `se_plateau = max(se_hac, *se_by_block)`. Prints the curve and `T/b` |
| `power_line(se, deltas=(0.05, 0.10), *, sessions, delta_ni=0.10, card_class) -> PowerLine` | `mde80 = 2.1232 * se_plateau`. `power_at_D = Phi(D/se - 1.2816)`. CARD-P: `pc3_power_at_0 = Phi(delta_ni/se - 1.2816)`; `years_to_detect_0p05 = T_years * (2.1232*se/0.05)^2`, `T_years = sessions/252`, `se = se_plateau`. `underpowered = mde80 > 0.10` |
| `apply_underpowered(check_id, ...)` | Allowed `check_id` in {`step5_p_value`, `pc3_p_value`}; any other raises (L2622). Never waives PC-1', PC-2, the PC-3 point REJECT, or step 3 (L2576, L5014) |
| `by_qvalue(global_ledger) -> dict` | Benjamini-Yekutieli over the analytic HAC/LW p-values of every tested variant: sort p ascending, `q_(i) = min_{j>=i} p_(j) * m * c(m) / j`, `c(m) = sum_{k=1..m} 1/k` (SILENT). Multiplicity uses analytic p-values, or bootstrap with `B >= 20*M/alpha` (L2578) |
| `harvey_liu_haircut(z, M) -> float` | SILENT. Reading: `p1 = 1 - Phi(z)`; `p_adj = min(1, M*p1)`; `z_adj = Phi_inv(1 - p_adj)`; `haircut = 1 - max(z_adj, 0)/z`. Printed beside `live_sharpe_multiplier: 0.60`; never gated |
| `lo_adjusted_sr(x, lags) -> float` | Lo (2002): `eta(q) = q / sqrt(q + 2*sum_{k=1..q-1}(q-k)*rho_k)` with q = 252 and `rho_k = 0` for k > lags; annual SR = `eta * SR_daily`. Printed at 20 lags and at all lags; never gated; Sharpe ratios compared within one market only (L2590) |
| `pbo_cscv(configs, objective, S=16) -> {pbo, winner_loses_share, slope, n_configs}` | below |
| `pbo_null(n_configs>=10, T, S=16, seed) -> float` | The same CSCV on pure-noise configurations; printed beside the PBO |

**PBO (step 4)** (L2581-2589, L4763):
- Configuration set = family ledger union the frozen PC-6 grid of the card's rule type (`gate.card_p_v2.pc6_axes`). No card declares its own grid.
- S = 16 contiguous blocks (`np.array_split`), all C(16, 8) = 12,870 splits.
- Objective: CARD-O = paired Delta-SR vs overlay-off; CARD-P = block-wise Delta-ES95 of 21-session returns (windows never span a block join). **Never MDD on concatenated half-samples.**
- Per split: best configuration in sample; rank `r = #{obj_oos <= obj_oos[best]}`; `w = r/(G+1)`; logit `ln(w/(1-w))`; `pbo = share(logit < 0)` (this convention reproduces 0.535897 on QF3's noise recipe; identical to V:199-207).
- "The winner loses" = the in-sample best configuration's out-of-sample objective is below the comparator's (overlay-off, or S) in more than 10% of splits.
- `PBO > 0.2` and winner loses -> REJECT. Fewer than 10 configurations: print `"PBO not run (n < 10)"` and the reason; never imputed.
- Fast path: keep per-block sums and sums of squares; each split is then a matrix product (1.8 s for 200 panels).

### B3. `core/quant/cardp.py` — R-22 evaluation conventions

**`episodes(close, theta) -> list[Episode]`** (L2299-2317, verbatim):

```python
def episodes(close, theta):        # theta: 0.20 (KOSPI and the default); 0.15 for the S&P 500 and indices the frozen theta rule declares low-volatility
    state, peak, peak_d = "bull", close.iloc[0], close.index[0]
    for d, v in close.items():
        if state == "bull":
            if v > peak:
                peak, peak_d = v, d
            elif v <= peak * (1 - theta):
                state, trough, trough_d = "bear", v, d
        else:
            if v < trough:
                trough, trough_d = v, d
            elif v >= trough * (1 + theta):           # bear confirmed over by a theta rally
                emit(Episode(peak_d, trough_d, trough / peak - 1))
                state, peak, peak_d = "bull", v, d
    if state == "bear":
        emit(Episode(peak_d, trough_d, trough / peak - 1, open=True))
# episode window = from the first return after the peak close to the trough date
```

- Dating starts at the first close of the declared history file (L2318).
- theta: `{default: 0.20, KR: 0.20, US_SPX: 0.15}`; any other market: written in the registry before its first card run by the frozen rule "0.15 if long-run median SMA20 vol < 0.18 else 0.20" (L2319).
- Each episode carries the R-20 regime tags of its peak date (L2322).
- An open episode (`open=True`) is printed and never counts toward PC-4, PC-7 or a re-gate (L2323).
- A re-gate on a new objective episode runs on data ending at the episode's confirmation close + the 63-session post-trough window, fixed by rule (L2323).
- **Sep-2026 is not an episode in any market**: asserted on the builder's output, never coded as an override (L2324).
- Refused: episodes built from vendor-derived or provisional closes (L2394).
- Episode fields (L2385, L4031): `peak`, `trough`, `depth`, `window`, `benefit_vs_S`, `share`, `regime_tags`, `post_trough_63`, `open`.

| Function | Algorithm |
|---|---|
| `episode_benefits(x_rule, x_S, episodes)` | `B_e = prod_{t in e}(1 + x_rule,t) - prod_{t in e}(1 + x_S,t)` (L2320). PC-4 = count of `B_e > 0` and `max B_e / sum_{B_e>0} B_e` (L2321). Also `pc4_section_8_6 = {positive, n, max_share}` on the 8.6 named windows, printed only |
| `post_trough_window(x_rule, x_S, episode, n=63)` | Rule-vs-S return over the 63 sessions after the trough, same product difference. Printed, never gated. None of it enters PC-4 |
| `cost_episodes(x_rule, x_S)` | Fixed windows: `rebound_2009: ["2009-03-09", "2009-06-30"]`, `rebound_2020: ["2020-03-23", "2020-06-08"]` (KOSPI from 2020-03-19), `h1_2026: ["2026-01-02", "2026-06-30"]`. Printed |
| `shock_type_table(x_rule, x_S, market)` | The 15 named windows of L5116-5132 with their return-date conventions (returns after the start close, except four KOSPI windows that include the start-date return: Aug-2024, Apr-2025, Mar-2026, H1-2026; L5134-5142). Leave-one-crisis-out printed for six groups: credit recession, inflation tightening, policy shock, leverage unwind, oil / geopolitical, pandemic |
| `excess_returns(weights, r, cash)` | below |
| `start_band(header) -> list[date]` | below |
| `midpoint_halves(header) -> (split_date, h1, h2)` | Calendar midpoint of the fixed span; it follows from the history start and the fixed span end (L2342). KR: midpoint of [1997-04-01, 2026-10-02] = 2012-01-01. The split date is written in the header |
| `regime_lines(header)` | One line per R-20 regime (Korea: pre-ETF 1997 -> 2002-10; the ETF era; +/-30% limits from 2015-06-15). One declared primary out-of-sample line; R-06 KR's is the ETF-era line (gated); its 2002-10 -> 2015-12 pre-design line is printed (L2346-2347) |

**`excess_returns(weights, r, cash)`** (L2330-2337): `x_t = w_t * (r_t - c_t) - cost_t`.
- Annual-rate series (`BOK_CALL_RATE`; `DTB3` after its discount-basis conversion): `c_t = (latest rate dated on or before the previous session) * (calendar days since the previous session) / 365`. A day on which the rate's own calendar is closed carries the prior rate.
- Per-period return series (French daily `RF`; French monthly `RF` on monthly cards): `c_t` = the series' own return for period t, as published, no day count.
- The cash series has role `history`: read from the card's frozen data snapshot pinned at `knowledge_utc`; `available_at_utc` is recorded, never used as a filter.
- A missing cash day = a day of the series' own observation calendar without a value -> the card is refused. Never cash = 0.
- Zero-investment long/short series (French Mom) get no cash term. Price-index returns (^KS11) omit dividends; the card prints that.
- `returns: raw` (cash 0) exists only for reproduction tests; a raw-flag run never produces a card record (`cash_convention.returns` is const `excess`, L3970).
- Costs (L5016-5021): `|dw|` per day at the gate's per-side rate, charged on the day the new weight earns; tick floor `cost_side = max(table rate, commission + 0.5*tick/price + tax_side)`; buy-and-hold and S carry no cost; every card also runs at 2x.

**Start, span end, start band** (L2338-2344):
- Start = first available close of the declared history + estimator warm-up (20 sessions for SMA20). Never chosen. `gate.evaluation.history_start = {KR: "1997-04-01", default: first_close_of_frozen_fixture}`.
- Span end: drafted CARD-Ps -> `gate.evaluation.data_cutoff = {KR: "2026-10-02", US: "2026-10-01"}`; a card whose data file ends earlier (French files, 2026-08-31) ends at that file's last date, written in the fixture manifest; a header registered after the freeze ends at the last month-end official close before its commit.
- Band shapes (frozen; a card declares neither its band nor its pass share):
  - `default`: the monthly starts over the first 33 months of the span, pass share "2/3";
  - `R-06_KR`: the 32 monthly starts 1997-05 ... 1999-12, pass share "2/3";
  - `decade_spaced` (daily spans >= 80 years): the declared start, then the first session of January of each decade year at least 10 years before the span end (R-29: 1930 ... 2010, 10 starts), pass share "4/5".
- **Stability floor (integers, never floats):** no REJECT at any start; `3*n_pass >= 2*n_starts` (R-06 KR: >= 22 of 32) or `5*n_pass >= 4*n_starts` for decade-spaced (R-29: >= 8 of 10); no REJECT in either midpoint half. A miss caps the card at INSUFFICIENT DATA (`stability`).
- Result fields: `start_band_results = {starts[], verdicts[], n_pass, n_starts, n_reject, floor_pass}`, `midpoint_halves_results = {h1, h2}`, `regime_line_results[] = {line, span, verdict, numbers, gated}`.
- Printed: the PASS share, the range of Delta-MDD and Delta-ES across starts, rolling-decade results.

**Rule 6, risk layer inside card books** (L2348): on, off and S books apply the data invariants (R-01, R-19, R-20, R-26) and the bounds (R-02). They exclude the R-07 hard stop with its re-arm, the concentration caps and the semiconductor cap, except for a card whose claim concerns them (R-31 includes the hard stop). Each card prints a `with_risk_layer` line for its on and S books, never gated. Key `gate.evaluation.risk_layer_in_card_books`; a run with the convention flipped is refused (T-RLAYER-01).

Refusals (L2391-2394): header without `episode_rule_version`, `cash_convention` or `start`; an acting long-sample card without `start_band` or `midpoint_halves`; a cash series that does not cover the span.

### B4. `core/quant/cardp.py` — R-21 CARD-P checks

**Books** (L2139-2144, L4969-4973, L5187-5192), all on excess returns:
- `x_on` rule book; `x_off` overlay-off book; `m` multiplier series (the factor under test).
- **S**: `x_S = m_bar * x_off`, `m_bar = mean(m)` over the evaluated span; constant, same days, uncosted. For an incremental card, "overlay-off" is the book without the factor under test: the vol-targeted book (R-28), the declared book without the steps (R-31), the invariants-only book (stack card).
- Benchmarks, always all four: buy-and-hold; overlay-off; S; EWMA(0.94) de-risk (same target, cap 1.0; printed).

| Function | Algorithm |
|---|---|
| `es_h(x, h, level=0.95)` | `R_h(t) = prod_{j=t-h+1..t}(1 + x_j) - 1` (overlapping). `ES95_h = -mean(lowest 5% of R_h)`, a positive loss (L2148-2149) |
| `pc1_prime(x_rule, x_S, horizons=(21, 126), *, f, B=2000, mean_block=250, seed=11)` | `dES_h = ES95_h(S) - ES95_h(rule)`; positive = protection. Stationary bootstrap (Politis-Romano), mean block 250 sessions exactly ("another value is a new package version"): `p_h = #{dES*_h <= 0}/B` (uncentred percentile). `z_h = dES_h / SD*(dES_h)`, printed, never decides. Leg passes iff `dES_h > 0` and `p_h * f <= 0.10`. Monthly cards: h = 1 and 6 months. Run at 1x (gate) and 2x (REVISE path). Output `tests.PC1p = {legs: [{h, dES, z, p, p_adj, pass}], two_x: [...]}` |
| `tail_exposure_ratio(m, x_off, q=0.05, horizon=1)` | `TR = mean(m on the worst 5% of overlay-off days) / mean(m on all days)`. Pass iff `TR <= 0.90` (point, 1x). 90% bootstrap CI printed. Daily ratio always printed. Horizon-matched ratio (worst 5% of h-session windows at the rule's decision horizon; h = 21 for monthly rules) replaces the daily ratio for **every** CARD-P only if the acceptance test's 9(c) adopted it. Output `tests.PC2 = {ratio_daily, ratio_horizon, ci90, horizon_used, pass}` |
| `pc3_noninferiority(x_rule, x_S, delta=0.10, *, f)` | `dSR = SR(x_on) - SR(x_S)`. `p10` = `lw_studentized_boot(block=10, null=-delta).p_lw`; `pPW` = same with `block = max(21, pw_block_psi)`. `p_ni = max(p10, pPW)`. Pass iff `p_ni * f <= 0.10`. Point `dSR < -delta` at 1x -> REJECT; at 2x -> REVISE. Output `tests.PC3 = {dSR, p10, pPW, block_PW, p_ni, p_adj, point_2x, pass, p_lw, p_hac, block, n_blocks}`; `p_lw`, `block`, `n_blocks` are those of the leg whose p sets `p_ni` (L2613) |
| PC-4 | >= 3 objective episodes with `B_e > 0`, and `max_share <= 0.50`. Fewer than 3 positive -> REJECT; concentration alone -> INSUFFICIENT DATA (inconclusive) (L5203) |
| PC-5 | >= 60% of calendar years positive for the overlaid book; share of years lagging S printed. Failure -> REVISE (extend the history) |
| PC-6 | >= 50% of the neighbours keep >= half of the centre's `dES_21` and `dES_126`, and a PC-3 point >= -delta. Neighbours: the 8 Moore neighbours of a two-axis grid, or the 2 axis neighbours of a one-axis rule; axes from `gate.card_p_v2.pc6_axes` only. `V.plateau_share` is not reusable (it moves one parameter at a time). Failure -> REVISE (widen the grid) |
| PC-7 | Discrete rules: >= 30 onsets de-clustered at their own lookback (or a pooled-onset rule declared before any run). Continuous rules: >= 5 objective episodes. Both: >= 756 + 126 = 882 sessions. Failure -> INSUFFICIENT DATA (`sufficiency`), decided first |
| `gjr_null_percentile(header, n_paths=1000)` | Fit GJR-GARCH(1,1)-t with constant mean on the card's market over the declared span (reuse `core.quant.gjr.fit_gjr(returns, dist="t")`, which already returns `mean_daily`; the `arch` package is not installed). Simulate 1,000 paths (seed 11; extend `gjr.simulate_gjr_series` with the mean). Run the card's rule on each path. Report the observed `dMDD` and `dES_21` as percentiles of that null. Printed only. Appends no ledger row |
| `placebo_panel(header, n=20)` | 20 circular shifts at `tau_k = round(252 + k*(T - 504)/19)`, k = 0..19; prints `{n, passes}`. Appends no ledger row |
| `overlay_card_eval(card, ledger) -> CardResult` | Builds on/off/S books, runs the checks, step 3, the power line and the timing profile (L1090). CARD-O path uses steps 1-9 with R-23 and R-24 |

**Caps** (L2168-2171, L5214-5222). A cap only lowers a verdict; it never raises one and never creates a REJECT.

| Cap | Trigger | Caps at | Reason code |
|---|---|---|---|
| Do-no-harm | `dMDD < 0` **and** `dCDaR95 < 0` at 1x | INSUFFICIENT DATA | `do_no_harm` |
| Timing-fragile (R-34) | `FR > 0.5`, or Delta-SR changes sign by lag 2 | INSUFFICIENT DATA (Tier B; live, time-stamped feeds required) | `timing_fragile` |
| Claim line | The card misses a claim line declared in its header (R-28: stacked Delta-MDD on VT >= 3 pp) | INSUFFICIENT DATA | `claim_not_shown` |
| Stability floor | B3 floor fails | INSUFFICIENT DATA | `stability` |
| Estimator calibration (R-30) | SMA20 fails B5, or a challenger fails Stage 1 | REVISE; only fix "lengthen the holding period" (a counted revision) | `estimator_calibration` |

Sign conventions: `dMDD = MDD(rule) - MDD(S)` with MDD <= 0, so positive = shallower (L5985: "MDD(rule) - MDD(S) >= +3.0 pp"). `dCDaR95 = CDaR95(S) - CDaR95(rule)` with CDaR a positive loss; CDaR95 = mean of the worst 5% of the drawdown series `1 - eq_t/max_{s<=t} eq_s` (SILENT).

**`cardp_evaluate(header, books) -> CardPResult`: the verdict order, coded once** (L2173, L5228-5250):

```python
ORDER = {"REJECT": 0, "INSUFFICIENT_DATA": 1, "REVISE": 2, "PASS": 3}

def line_verdict(c, f):                     # c = checks of ONE gating line at 1x and 2x; f = selection factor
    # 1. INSUFFICIENT DATA (sufficiency)
    if not c.pc7.passed:                                   return "INSUFFICIENT_DATA", "sufficiency", None
    # 2. REJECT, at 1x, on any of
    if any(leg.dES <= 0 for leg in c.pc1p.legs):           return "REJECT", "PC1p", None
    if c.pc2.ratio_used > 0.90:                            return "REJECT", "PC2", None
    if c.pc3.dSR < -0.10:                                  return "REJECT", "PC3", None
    if c.pc4.positive < 3:                                 return "REJECT", "PC4", None
    if c.step4.ran and c.step4.pbo > 0.2 and c.step4.winner_loses:  return "REJECT", "step4", None
    # 3. INSUFFICIENT DATA (inconclusive or underpowered)
    if any(leg.p * f > 0.10 for leg in c.pc1p.legs) or c.pc4.max_share > 0.50:
                                                           return "INSUFFICIENT_DATA", "inconclusive", None
    if c.pc3.p_ni * f > 0.10:
        return "INSUFFICIENT_DATA", ("underpowered" if c.power.mde80 > 0.10 else "inconclusive"), None
    # 4. REVISE (everything holds at 1x)
    if any(not leg.passed for leg in c.pc1p.two_x) or c.pc3.point_2x < -0.10:
        v = ("REVISE", first_failed, "lengthen_holding")   # never lower the cost
    elif not c.pc6.passed:  v = ("REVISE", "PC6", "widen_grid")
    elif not c.pc5.passed:  v = ("REVISE", "PC5", "extend_history")
    else:                   v = ("PASS", None, None)
    # 5. caps: applied to a PASS or a REVISE, lowering only
    for name, level in caps_triggered(c):                  # table above
        if ORDER[level] < ORDER[v[0]]:
            v = (level, name, v[2]); c.caps_applied.append(name)
    # 6. PASS
    return v
```

- **Gating lines.** A header may declare several (`gating_lines`; R-06 KR: `full_span` and `etf_era` to 2025-12-31). The card receives the **worst** of its gating lines' verdicts. Printed lines never gate (L5226).
- `verdict_at_f1` and `verdict_at_f_neff` are both computed and printed; `verdict` is the one at the binding f (L4091).
- On PASS: the registered label is shown (default "protective: reduces tail losses vs a same-exposure static book; not expected to outperform"); the insurance premium is shown beside it (share of years lagging S, the timing return, the bull tax); build status = the header's `build_status_on_pass` (L5247-5250).
- `disposition in {RECOMMENDATION, BUILD_AS_INSURANCE}` iff `verdict = PASS` (L4089).
- Result fields: `verdict`, `verdict_reason`, `caps_applied[]`, `first_failed_check`, `permitted_fix in {null, widen_grid, lengthen_holding, extend_history, repair_rerun}`.
- **Printed, never gated** (L2189-2195, L5252-5261): `dMDD`, `dCDaR95`, daily `dES99`, each with a bootstrap band; the GJR-null percentile; the 20-shift placebo panel; time under water, worst-day coverage, CVaR(5%), re-entry lag; post-trough window and cost episodes; rolling 5-year block comparisons against S; DSR vs 0 and PSR vs S; the timing profile; execution variants and the stress-cost line; step 9: 60% of the Delta-ES legs and of Delta-MDD. `printed = {dMDD, dCDaR95, dES99, bands, placebo_panel: {n, passes}, tuw, reentry_lag, post_trough, rolling_5y, with_risk_layer, lo_sr_20, lo_sr_all, by_q, hl_haircut, ...}` (L4077-4081).
- **Fail closed** (L2242-2247): no CARD-P is evaluated before the package is frozen; a header citing another package version or md5 is refused; a failed bootstrap, comparator or episode list -> no card is written; a card without a power block or a timing profile is refused; a card whose statistics read a `synthetic_lookahead` row is refused.
- Class rules (L4851-4853, L5185): the class applies only to rules whose output never exceeds 1.0; the claim is a header field fixed before the run; a Sharpe or predictability claim on a protective rule is refused; a changed claim is a new card.

### B5. `timing_profile(card) -> TimingProfile` — R-34 (L3416-3432, verbatim core)

```python
for L in (-1, 0, 1, 2, 3, "strict"):
    book = run(card, lag=L)
    dSR[L] = SR(book) - SR(comparator(book))          # overlay-off (CARD-O) or S (CARD-P)
    dMDD[L], dES21[L] = drawdown_and_es_lines(book)   # printed
    ledger.append(card.family_id, {**card.config, "lag": L, "timing_class": "NON-COMPLIANT" if L in (-1, 0) else "COMPLIANT"})   # R-23
assert abs(dSR[1] - card.reported_dSR) < 1e-9          # harness integrity: the L = 1 row is the card's own result
LP = dSR[0] - dSR[1]                                   # look-ahead premium
LF = dSR[1] - dSR[2]                                   # lag fragility
FR = LF / dSR[1] if dSR[1] > 0 else None               # printed "n/m" when dSR[1] <= 0
fragile = (FR is not None and FR > 0.5) or (dSR[1] != 0 and sign(dSR[2]) == -sign(dSR[1]))
```

- L = sessions between the last information close used and the first session the weight earns. L = 1 is the honest convention; L = 0 same-session close (look-ahead); L = -1 next session's (gross look-ahead); "strict" = the publication-strict timing of R-19 for every published series.
- Timing-fragile cards: capped at INSUFFICIENT DATA; the header must name a live, time-stamped production feed for every acting input (`live_feeds`), else refused.
- **Positive control:** fixture `KR_SOX_KRW_gate_B3` (the R4 B3 inputs, SOX and USD/KRW closes, and the gate's thresholds and multiplier) must show `LP >= 0.20` (observed 0.28: L0 +0.317, L1 +0.035). If it does not trip, every card run is blocked.
- `fragility_ratio_max: 0.5` is declared once, before any card runs. Until the council answers the Sharpe-neutral question, every card prints FR with a paired-bootstrap 90% interval beside it, never gating (L5457).
- **`timing_probe` sandbox (C-4, L3432):** the L <= 0 rows and the positive control re-time inputs outside `pit_value`, inside `timing_profile` only. Everything they produce is tagged `synthetic_lookahead = true`, is written outside the production artifact directory, and is never a production artifact, book or card field other than `timing_profile.lags[]`. The lag audit records their violations in `timing_profile.lags[].lag_audit` instead of raising. Nothing but LP reads them. `lag_audit_violations` (schema const 0, L4082) counts the L >= 1 and strict rows only.
- Mechanism (proposed): a private `_run_lagged(card, L)` that asserts a `contextvars` flag set only inside `timing_profile()`; called with L <= 0 anywhere else it raises `TimingProbeForbidden`. No public switch exists. Static test: AST scan finds no reference to the probe outside `timing_profile()` and no import of it from `core/engine`, `core/ficc`, `core/skills`, `ui`.
- Output (result field, covered by `results_md5`, never in the header): `{lags: [{L, dSR, dMDD, dES21, lag_audit, timing_class}], strict: {...}, LP, LF, FR, label in {robust, timing_fragile}, live_feeds[]}`.

### B6. `core/quant/gate_package.py` — acceptance test, attempts log, manifest, freeze

**`gate_acceptance_test(families, controls) -> AcceptanceReport`** (R-21 rule 9, L2174-2188; L4814-4819). Runs once, before any card, on placebos and negative controls only. No real card's verdict is computed in it.

```python
def gate_acceptance_test(families, controls, *, store, attempts_log, seeds):
    verify_chain(attempts_log)
    fails = number of rows with outcome == "fail", counted across ALL 2.x versions (never reset)
    if fails >= 2: raise AcceptanceRefused("no_card_evaluated_under_v2")              # third attempt refused, also after a 2.x bump
    if fails == 1: require_redesign_record(...)                                       # below
    require owner_decisions.D6 recorded; require council answers recorded or "stands as written for 2.0.0"   # L5457
    for family in families:                              # population: drafted CARD-P headers R-06 KR, R-28, R-29, R-31
        for card in family.cards:                        # each on its declared book and span (end = data_cutoff); draft md5 cited
            books = build_books(card); T = len(books.x_off)
            f = step3(card).f                            # per row-set reading; max binds; printed with N_raw, N_clusters, N_equiv, E_sim
            taus_family = rng(seed).integers(252, T - 252, size=300, endpoint=True)   # tau uniform on [252, T - 252]
            taus_card   = [round(252 + k * (T - 504) / 19) for k in range(20)]
            passes_family += [placebo_passes(card, books, tau, f) for tau in taus_family]   # pooled across the family's cards
            passes_card[card] = sum(placebo_passes(card, books, tau, f) for tau in taus_card)
        family_ok = 10 * sum(passes_family) <= len(passes_family)                     # at most 10%
    cards_ok = all(n <= 2 for n in passes_card.values())                              # at most 2 of 20
    control_verdicts = {c: cardp_evaluate(c).verdict for c in controls}               # the five negative controls
    controls_ok = all(v in ("REJECT", "INSUFFICIENT_DATA") for v in control_verdicts.values())
    if not controls_ok: apply the recorded D6 rule (9(d)), print the three candidates' placebo results only, re-run;
                        if no candidate brings every control to REJECT or INSUFFICIENT_DATA: the attempt fails
    pc2_horizon_adopted = horizon_matched_decision(...)                               # 9(c): every pre-registered CARD-P + 20 placebos each; adopt iff false-pass <= 10%
    outcome = "pass" if family_ok_all and cards_ok and controls_ok else "fail"
    append_attempt(attempts_log, ...)                    # ALWAYS, passing or not
    return AcceptanceReport(...)

def placebo_passes(card, books, tau, f):                 # one definition for both counts (L2178)
    m_star = np.roll(books.m, tau)                       # multiplier circularly shifted against its returns (timing-free)
    x_on_star = rebuild on-book with m_star at 1x cost;  x_S = mean(m) * x_off
    legs = pc1_prime(x_on_star, x_S, f=f)
    return all(leg.dES > 0 and leg.p * f <= 0.10 for leg in legs)
```

- Negative controls (`gate.acceptance_test.negative_controls`): `US_VT_5d_50bp`, `US_VT_10d_50bp` (PX1), `post_shock_day_0p5`, `post_shock_week_0p5`, `VT_sigma_lag_252` (EX1). Allowed verdicts `[REJECT, INSUFFICIENT_DATA]`. Rule definitions are not in the spec (section F).
- Failure path (9(a)): a per-family or per-card count above its limit fails the test; the package is not frozen; no card runs. A per-card excess is resolved only by council question Q5, never by editing the tau grid, the placebo construction, the pass definition or the PC-1' definition.
- **Bounded redesign (R2-C3, L2181):** once per package version. The re-attempt may change only items of the frozen-items table (L4803-4810). Each change is recorded in the attempts log with the manifest diff and a rationale that cites the per-family panels and the negative controls only, never a named card's panel or its indicative numbers. Fresh placebo and control seeds are fixed and logged **before** the run; every panel and control is re-run. Any other diff, or seeds logged after the run, is refused. After a second failure, in any 2.x version: every card keeps `NOT_RUN` in every book, a `package_redesign` governance event is written and the owner is paged.
- **CDaR guard (9(d)):** added only if a control would pass. Calibration = D6, canonical key `gate.acceptance_test.cdar_guard.calibration`, default `lowest_placebo_false_pass_rule`: of the three candidates (`professors_bootstrap_one_sided_5pct`, `executives_placebo_p10_margin`, `qf_blind_margin`), the one with the lowest per-family placebo false-pass rate among those that bring every control to REJECT or INSUFFICIENT DATA; ties go to the Professors' test; placebo results only. An owner ruling is accepted only before the first attempt; a later change is a new package version and a counted trial in every family ledger. The fixed -5 pp margin is withdrawn.
- **Attempts log** `gate/acceptance_runs.jsonl`: append-only, hash-chained (`prev_row_md5`), `counts_as: package_trial`, listed in the report, printed beside every verdict produced later. Row fields are not enumerated by the spec; proposed: `attempt_no`, `utc`, `package_version`, `manifest_md5_at_attempt`, `seeds`, `d6_rule`, `draft_md5s`, `per_family {n, passes}`, `per_card {passes}`, `controls {id: verdict}`, `pc2_horizon_adopted`, `outcome`, `reason`, `redesign {diff, rationale} | null`, `prev_row_md5`.
- **AcceptanceReport** (`acceptance_report.json`; L2473, L4815, L5698): families, multiplier series, markets, spans, costs and fixtures; each draft's md5 (the header fields without the package citation); per-family and per-card counts with tau lists; each control's verdict and its printed numbers; the horizon-matched PC-2 decision; the D6 rule (and the three candidates' placebo results if triggered); f per row-set reading with `N_raw`, `N_clusters`, `N_equiv`, `E_sim`; `p_ni`; every attempt. It never contains a real card's verdict.
- **A CARD-P registered after the freeze** (a changed header, the generated stack card, another market's card) runs its own panels under the frozen rule 9(a) at its header commit: 300 shifted placebos (<= 10% passing) and 20 per-card placebos (<= 2 passing). An excess leaves that card `NOT_RUN` pending Q5; the panels' results are md5-frozen with its header; no package version is created (L4815). Expose as `card_placebo_panels(header)`.

**Freeze** (L4812-4828):

```python
def build_manifest(store, ledger_dir, fixtures) -> dict:      # md5 of its canonical JSON = definitions_md5
    return {
      "gate_blocks":      canonical JSON of every gate.* block,                                   # (a)
      "harness_sources":  {path: md5} for the files holding cardp_evaluate, episodes, family_ledger, n_eff, step3,
                          the bootstrap and block-length code, timing_profile, power_line, gate_acceptance_test,   # (b)
      "fixtures":         {path: md5} for every fixture the acceptance test reads,                # (c)
      "seeds":            {...},                                                                  # (d)
      "ledgers":          {family_id: ledger_hash}, "seed_files": {path: md5}, "diff_series": {path: md5},   # (e)
      "data_cutoff":      gate.evaluation.data_cutoff, "d6_rule": ..., "council_answers": {...},  # (f)
    }

def freeze(report) -> None:
    assert every pre-freeze harness test passed (list below) and report.outcome == "pass"
    write gate.package = {version: "2.0.0", definitions_md5, acceptance_report_md5, frozen_utc} to the rules store
    commit manifest + both md5s + acceptance report to the repository (external timestamped anchor) BEFORE any card runs
    governance_event(kind="package_freeze", actor="harness")
    adoption counts as one revision in every family ledger

def verify_package() -> None:     # called by docs/macro_overlay_study.py at EVERY card run, and by tests/run_all.py
    re-hash the manifest; raise PackageMismatch on any difference in a gate.* block, harness source file, acceptance fixture or seed   # T-CARD-02
```

- Order (L4813-4827): (1) harness tests pass: T-DSR-01/02, T-NEFF-01, T-STEP3-01/02, T-SEL-01, T-LEDGER-01, T-ES-01, T-DNH-01, T-ORDER-01, T-EPIS-01, T-EXCESS-01, T-BAND-01, T-POWER-01/02, T-UNDERPOW-01, T-PZERO-01, T-PBO-01, T-SE-01, T-PLACEBO-01/02, T-GATE-04, T-AVAIL-01, I-05; (2) acceptance test; (3) freeze; (4) commit every formal header blind (a CARD-P header must match its step-2 draft); (5) run the formal cards; (6) any later change is a new package version that re-runs every card and counts in every family ledger; no change may be justified by the card it flips.
- After the freeze, `tests/run_all.py` only re-verifies `acceptance_report_md5` and `definitions_md5`; it never re-runs the test (L2188, L5494-5496).
- Because the harness imports from `V` and `core/quant/gjr.py`, list those files in `harness_sources` too (fail closed on any edit).

### B7. Header drafts (TASK-M7-14)

All four use the 8.4 field set (L4878-4888) without the package citation; spans end at `gate.evaluation.data_cutoff`; `notional_nav` read from the owner-signed sleeve keys.

| card_id | Book, cost | Rule and key fields | Source |
|---|---|---|---|
| `MACRO-R06-KR-ETF` | `KRX_ETF_line`; futures cost class before the KODEX 200 listing, `krx_etf` after | Exactly the example header L4900-4964: `family_id: R-06`, `revision: 2`, `parameters: {estimator: sma, window: 20, target_ann: 0.20, cap: 1.0, floor: none}`, `searched_parameters: []`, `history_first_close: "1997-04-01"`, `data_span.end: "2026-10-02"`, `cash_convention: {returns: excess, cash_series: BOK_CALL_RATE, day_count: act_365}`, `episode_rule_version: "1"`, `gating_lines: {full_span, etf_era to "2025-12-31"}`, `start_band: {shape: R-06_KR, from: "1997-05", to: "1999-12", step: month, starts: 32, ...}`, `primary_oos_line: etf_era`, `build_status_on_pass: BUILD_AS_INSURANCE`, `tier: A`, `seed: 11` | 8.4 |
| `MACRO-R28-US-TREND` | `CME_micro_ES` (incremental on R-29's vt book, 5 bp), `rebalance: monthly`, `no_trade_band: 0.0`, `fill_model: NYSE_moc` | `rule: {signal: month_end_close_below_sma10m, multiplier_below: 0.5, multiplier_above: 1.0, decided: month_end_close, applies: next_month, composition: min, exposure_basis: total}`; claim verbatim "slow-bear protection via the volatility state"; `claim_lines`: stacked Delta-MDD on VT >= 3 pp (`claim_line_failure: cap_INSUFFICIENT`); `pooling_rule: {decluster_gap_months: 10, indices: [SPX, N225, HSI, DAX, FTSE100, TAIEX], own_market_veto: true, declared_before_any_run: true}`; `markets_refused: [KR]` | L3009-3030 |
| `MACRO-R06-US-FUT` (R-29) | `CME_micro_ES`, `cost_class: futures` (5 bp), `no_trade_band: 0.0`, `nav_fx: {series: USDKRW_1530_SNAPSHOT, history: ECOS_1530_CLOSE}` | `family: R-06`; `rule: {estimator: sma, window: 20, target_ann: 0.15, cap: 1.0, floor: none, rebalance: daily, exposure_basis: total}`; `episodes: {theta: 0.15}`; decade-spaced band | L3099-3119 |
| `MACRO-R31-KR-ETF` | The KR book | `steps: [{dd: -0.08, mult: 0.5}, {dd: -0.12, mult: 0.5, evaluator_block_new_entries: true}]`, `dwell_sessions: 21`, `hard_stop_level: {ref: risk_layer.drawdown.hard_stop.level}` (D2, never a literal); claim "protection in persistent drawdowns; time-boxed; no Sharpe claim"; judged incrementally on the declared book with the hard stop and every other factor, minus the steps | L3312-3329 |

---

## C. Schemas and config

### C1. Rules-store `gate` block (section 7, L4498-4619; verbatim; home: the M0 macro rules store, proposed `core/rules/macro_rules_v2.json`)

```yaml
gate:                                    # the existing nine-step gate plus the frozen v2 package (§8; R-21-R-24, R-34)
  package: {version: "2.0.0", definitions_md5: written_at_freeze, acceptance_report_md5: written_at_freeze, frozen_utc: written_at_freeze,
            manifest: [gate_blocks_canonical_json, harness_source_files, acceptance_fixture_md5s, seeds],
            anchor: repository_commit_before_any_card_run, rehash_at_every_card_run: true}   # §8.1.3; T-CARD-02
  frozen_before_first_card_run: true
  card_classes: [CARD-O, CARD-P]
  card_p_v2:                                         # R-21
    comparator: S_same_average_exposure              # m_bar x overlay-off; constant; same days; uncosted
    pc1_prime: {horizons_sessions: [21, 126], es_level: 0.95, overlapping: true, gate_cost: 1x,
                point_must_exceed: 0.0, p_max: 0.10, p_form: uncentred_bootstrap_percentile, z_printed: true, bootstrap: stationary, mean_block_sessions: 250,
                resamples: 2000, seed: 11, two_x: revise_path, monthly_cards_horizons_months: [1, 6]}
    pc2: {tail_quantile: 0.05, ratio_max: 0.90, default_horizon: daily, ci: printed,
          horizon_matched: {adopt_if_placebo_false_pass_max: 0.10, placebos_per_card: 20, decided_in: acceptance_test}}
    pc3: {delta: 0.10, p_max: 0.10, p_ni: "max(p_block10, p_block_max21_PWpsi)", point_below_minus_delta: {at_1x: REJECT, at_2x: REVISE}}
    pc4: {episodes: objective_market_own, min_positive: 3, max_share: 0.50}
    pc5: {years_positive_min: 0.60}
    pc6: {neighbourhood: moore_8_or_2_axis_neighbours, keep_share_min: 0.50}
    pc6_axes:                                        # frozen per rule type; a card never declares axes or steps (default, judgment)
      vol_target: {window_mult: [0.5, 1, 2], target_mult: [0.75, 1, 1.25]}           # R-06 KR: {10, 20, 40} x {0.15, 0.20, 0.25}
      threshold_rule: {threshold_mult: [0.75, 1, 1.25], lookback_or_dwell_mult: [0.5, 1, 2]}
      monthly_trend_rule: {lookback_months: [8, 10, 12]}                              # one axis, 2 neighbours (QF5)
    pc7: {discrete_min_onsets: 30, decluster_gap: own_lookback, continuous_min_objective_episodes: 5, min_sessions: 882}
    caps: {do_no_harm: INSUFFICIENT_DATA, timing_fragile: INSUFFICIENT_DATA, estimator_calibration_fail: REVISE}   # SMA20: B5; challenger: R-30 Stage 1
    underpowered: {applies_if_mde80_gt: 0.10, converts: [pc3_p_value], never_waives: [pc1_prime, pc2, pc3_point]}
    gjr_null: {paths: 1000, seed: 11, mean: constant}                 # printed only
  acceptance_test:
    placebo: {construction: circular_shift_of_multiplier, per_family: 300, per_family_false_pass_max: 0.10,
              tau_min_sessions: 252, per_card: 20, per_card_passes_max: 2, seed: 11,
              per_card_tau: "round(252 + k*(T - 504)/19), k = 0..19", pass: pc1_prime_both_legs_1x_with_f,
              population: drafted_card_p_headers, family_pooling: own_series_300_per_card, on_excess: acceptance_fails}   # Q5 open (§8.10)
    negative_controls: [US_VT_5d_50bp, US_VT_10d_50bp, post_shock_day_0p5, post_shock_week_0p5, VT_sigma_lag_252]
    controls_allowed_verdicts: [REJECT, INSUFFICIENT_DATA]
    cdar_guard: {added_only_if_a_control_passes: true, calibration: lowest_placebo_false_pass_rule, fixed_margin_minus_5pp: withdrawn}   # calibration: canonical key of D6, frozen with the package (R2-C2)
    attempts_log: {path: gate/acceptance_runs.jsonl, append_only: true, hash_chain: prev_row_md5, listed_in_report: true,
                   counts_as: package_trial, printed_beside_every_verdict: true}   # R2-C3
    redesign: {max_per_package_version: 1, changes_limited_to: frozen_items_table, rationale_cites: [family_panels, negative_controls],
               fresh_seeds_fixed_before_run: true, per_card_excess: council_q5_only, failure_count: across_all_2x_versions_never_reset,
               after_second_failure: no_card_evaluated_under_v2_owner_notified}   # R2-C3; T-GATE-04
  evaluation:                                        # R-22
    episode_rule: {name: alternating_bear_bull, version: "1", prices: own_official_closes,
                   theta: {default: 0.20, KR: 0.20, US_SPX: 0.15}, low_vol_declared: [US_SPX],
                   others: {rule: "0.15 if long-run median SMA20 vol < 0.18 else 0.20", written_before_first_run: true},
                   window: first_return_after_peak_close_to_trough, sep_2026: asserted_not_an_episode}
    shock_type_table: "§8.6 named windows (printed only)"
    post_trough_window_sessions: 63                  # printed, not gated
    cost_episodes: {rebound_2009: ["2009-03-09", "2009-06-30"], rebound_2020: ["2020-03-23", "2020-06-08"],
                    h1_2026: ["2026-01-02", "2026-06-30"]}
    returns: excess
    cash: {KR: BOK_CALL_RATE, US: US_RF, other: registry_before_first_run}
    cash_day_count: act_365                          # default, judgment
    cash_rate_date: latest_rate_dated_on_or_before_previous_session   # R-22 rule 3; a closed day of the rate's own calendar carries the prior rate
    cash_units: {annual_rate: act_365, per_period_return: as_published}   # French RF is a per-period return (R2-C5)
    cash_read: frozen_card_snapshot_available_at_recorded_never_filtered   # role history; a missing cash day refuses the card
    start: first_close_plus_estimator_warmup
    history_start: {KR: "1997-04-01", default: first_close_of_frozen_fixture}   # fixed before the freeze; a card never truncates it
    span_end: {drafted_cards: data_cutoff, later_cards: last_official_close_before_header_commit}
    data_cutoff: {KR: "2026-10-02", US: "2026-10-01"}   # the last official closes in the frozen reference data (§9.3.1), fixed now; in the manifest
    start_band_shapes:                               # frozen; a card declares neither its band nor its pass share
      default: {months: 33, step: month, pass_share_min: "2/3"}
      R-06_KR: {from: "1997-05", to: "1999-12", step: month, starts: 32, pass_share_min: "2/3"}   # Resolution 1
      decade_spaced: {min_span_years: 80, starts: declared_start_then_january_of_each_decade, last_start_min_years_before_end: 10, pass_share_min: "4/5"}   # R-29
    stability_floor: {no_reject_at_any_band_start: true, pass_share_min: from_band_shape, compare: integer_counts,
                      no_reject_in_midpoint_halves: true, applies_to_every_shape: true}
    midpoint_halves: {split: calendar_midpoint_of_fixed_span, split_date_in_header: true}
    regime_lines: from_R20_tags
    primary_oos_line: declare_on_card
    risk_layer_in_card_books: {hard_stop: excluded_printed, caps: excluded_printed, except: card_claim_concerns_them}   # rule 6
  step3:                                             # R-23
    ledger: {required: true, hash: md5_canonical_json, research_phase_included: true, timing_class_required: true,
             family_id: by_rule_QC_modules, filing_cluster_rho: 0.5, appended_by: harness_only, hash_chain: prev_row_md5,
             hash_at: [registration, run]}
    basis: difference_series                         # rule minus comparator (overlay-off for CARD-O, S for CARD-P)
    n_gate: "max(N_clusters, N_equiv)"
    emax: {simulated_draws: 200000, seed: 11, below_2: exact_integral, from_2: bldp_closed_form}
    clusters: {linkage: average, rho_min: 0.5}
    variance: {default: V_null, se_null: median_lw_hac_of_family_trials, use_trials_if_independent_ge: 30, print_both: true}
    card_o_bar: 0.95
    card_p: {gated: false, selection_factor: bonferroni_N_eff, factor_one_if: config_fixed_before_any_run_on_span,
             overlap_rule: any_overlap, computed_by: step3, declared_on_header: refused, print_both: [f_1, f_N_eff],
             holm_across_variants: printed}
    row_set: {unit: distinct_configuration, key: [rule, params, estimator, window, cap, book, rebalance, timing_class, start_convention], readings: [market_scoped, family_wide], combine: max,
              snapshot: ledger_hash_at_registration, excludes: [own_run_rows, null_distribution_runs]}   # R2-C1
    spec_versions: publication_utc_listed_in_manifest   # the f = 1 route (a published SPEC version)
    printed: [N_raw, N_hat_linear_eq9, N_clusters, N_equiv, N_eff, break_even_N, z_check_one_sided_2p50_le_8_cells, by_q_global, dsr_vs0, psr_vs_S]
    forbidden: [kish_design_effect, revision_count_as_N]
  stats:                                             # R-24
    bootstrap: {method: ledoit_wolf_studentized_circular_block, null_centred: true, resamples: 2000, seed: 11,
                p_zero_print: "< 1/B", hac_p_printed: true}
    block: {rule: politis_white_on_influence_function, floor_sessions: 21, pc3_also_block_10: true}
    se_ladder_blocks: [10, 21, 63, 126, 250]         # SE_plateau = max (incl. LW-HAC)
    power: {alpha_one_sided: 0.10, power: 0.80, mde_factor: 2.1232, deltas: [0.05, 0.10], t_years: sessions_over_252, se: se_plateau}
    underpowered: {mde80_gt: 0.10, converts: [step5_p_value, pc3_p_value]}
    multiplicity: {p_source: analytic_hac_lw, bootstrap_resamples_if_used: "20*M/alpha", by_q_from_global_ledger: true,
                   one_sided_z: {le_8_cells: 2.50, bonferroni_120: 3.34}}
    pbo: {configs: ledger_union_frozen_pc6_grid, min_configs: 10, cscv_blocks: 16,
          objective: {CARD_O: paired_dSR_vs_off, CARD_P: blockwise_dES95_21}, winner_loses_share_gt: 0.10,
          reject_if: "PBO > 0.2 and winner_loses", null_calibration: printed}
    lo_adjusted_sr: {lags: [20, all], printed: true, gated: false}
    live_sharpe_multiplier: 0.60                     # take 40% off; HL haircut printed beside it
  timing:                                            # R-34
    lags_sessions: [-1, 0, 1, 2, 3]
    plus_publication_strict: true
    honest_lag: 1
    fragility_ratio_max: 0.5                         # declared once, before any card runs
    sign_flip_by_lag: 2
    consequence: {verdict_cap: INSUFFICIENT_DATA, tier_cap: B, require_live_timestamped_feed: true}
    positive_control: {fixture: KR_SOX_KRW_gate_B3, contents: R4_B3_inputs_and_rule, look_ahead_premium_min: 0.20}   # observed 0.28
    every_lag_in_family_ledger: true
    lookahead_rows: {mode: timing_probe, scope: [tests, r34_sandbox], tag: synthetic_lookahead, ledger_timing_class: NON-COMPLIANT,
                     production_writes: forbidden}
  tiers: {A: {min_onsets_declustered: 30, decluster_gap: own_lookback, min_stress_episodes_in_sample: 3, min_oos_episodes: 1,
              pooled_rule: declare_before_any_market_is_run},
          A_provisional: closed,          # BL-C12 resolved; no pooled or A-provisional route for a card already run
          B: {bounds: [0.5, 1.0], external_params: true, verdict_from_backtest: INSUFFICIENT_DATA, forward_record: falsification_only},
          C: {allowed: false}}
  parameter_budget_searched: 8
  stress_report_window: ["2022-01-01", "2026-10-02"]      # reported, not a holdout
  locked_holdout_start: "2027-01-01"
  costs: read_from_gate                  # KRX ETF 3 bp, KRX stock 35 bp, US via KIS 50 bp, crypto 10, futures 5, FX 10; x2 stress
  card_header_required: [instrument_book, notional_nav, rebalance, no_trade_band, fill_model, cash_convention, episode_rule_version,
                         family_id, ledger_hash_at_registration, history_first_close, data_span]   # start_band, midpoint_halves: acting long-sample cards (R-22)
  card_result_required: [timing_profile, ledger_hash_at_run, selection_factor, results_md5]          # §6.5
```

Owner decision D6 (L4150-4152): `D6: {key: gate.acceptance_test.cdar_guard.calibration, value: lowest_placebo_false_pass_rule, default: lowest_placebo_false_pass_rule, options: [lowest_placebo_false_pass_rule, professors_bootstrap_one_sided_5pct, executives_placebo_p10_margin, qf_blind_margin], status: default, effective_from: null, rationale: null, refs: []}`.

### C2. Card result fields this area writes (`model_card.macro`, L3996-4084; schema owned by M0)

- Top level: `verdict`, `verdict_reason`, `caps_applied`, `verdict_at_f1`, `verdict_at_f_neff`, `disposition`, `first_failed_check`, `permitted_fix`, `ledger_hash_at_run`, `N_raw`, `N_clusters`, `N_equiv`, `N_hat_linear`, `N_eff`, `E_max_sim`, `V_null`, `V_trials`, `selection_factor {value, rule, alt_value}`, `power {se_hac, se_blk250, se_plateau, se_curve, mde80, power_at_0p05, power_at_0p10, pc3_power_at_0, years_to_detect_0p05, underpowered}`, `timing_profile {lags, strict, LP, LF, FR, label, live_feeds}`, `episodes[]`, `cost_episodes[]`, `pc4_section_8_6`, `start_band_results`, `midpoint_halves_results`, `regime_line_results[]`, `gjr_null_pct` (0-100 or null), `claim_line_results`, `lag_audit_violations` (const 0), `results_md5`.
- `tests`: `step1..step9`; `step3 {deflated_dSR, at_N_raw, at_N_hat_linear, borderline, break_even_N, z_check, by_q, dsr_vs0, psr_vs_S, selection_factor, pass}`; `step4 {pbo, winner_loses_share, pbo_null, slope, n_configs}`; `step2`/`step5` carry `{p_lw, p_hac, block, n_blocks}`; `PC1p`, `PC2`, `PC3`, `PC4 {positive, n, max_share}`, `PC5`, `PC6`, `PC7`. The key set is closed.
- Header fields this area reads (L3929-3933): `family_id`, `ledger_hash_at_registration`, `N_raw_at_registration`, `gate_package_version`, `gate_package_md5`, `cash_convention`, `history_first_close`, `data_span`, `episode_rule_version`, `start_band`, `midpoint_halves`, `gating_lines`, `regime_lines`, `primary_oos_line`, `comparator` (enum `S_same_average_exposure` | `overlay_off`), `benchmarks`, `claim_lines`, `pooling_rule`, `timing`, `live_feeds`, `seed`. Both schemas close with `unevaluatedProperties: false`: a header carrying `selection_factor`, `timing_profile` or any result field is refused.
- Non-finite numbers must be written as `null` (5 legacy cards hold bare `NaN`; a schema-validated card cannot).

### C3. Files this area owns

| File | Shape | Notes |
|---|---|---|
| `<ledger_dir>/<family_id>.jsonl` | B1 row, one per line | append-only, hash-chained; temp copy in tests |
| `tests/fixtures/macro/ledger_seed_<family>.csv` | row id, source file and row, market, span, run_utc, params, timing class, book, cost, results md5, stored difference series (L6020) | md5-listed in the manifest; a missing series is regenerated from its config before the freeze |
| `gate/acceptance_runs.jsonl` | B6 attempt row | append-only, hash-chained, package-level ledger |
| `acceptance_report.json` | B6 | its md5 = `gate.package.acceptance_report_md5` |
| `gate/definitions_manifest.json` | B6 `build_manifest` | its md5 = `gate.package.definitions_md5` |
| `governance_events.jsonl` (M0 appender) | kinds used here: `package_freeze`, `package_redesign`, `header_commit` (L4104) | `actor: harness` |

---

## D. Tests

Tolerances: Level 1 unless stated (L5734-5737): Sharpe +/-0.01; max DD +/-1 pp; p-values +/-0.01 (p >= 0.05), +/-0.005 (p < 0.05); z +/-0.05; ES, CDaR, Delta-ES +/-0.2 pp; deterministic counts exact; bootstrap-dependent counts +/-1; SE +/-0.005. A verdict derived from a statistic within tolerance of its threshold is asserted as a class, never as a point.

### D1. Before the freeze (`runs_from` M7, L5557)

| Test | Assertion and thresholds | Fixture | Class |
|---|---|---|---|
| T-LEDGER-01 (L2528) | A hand-edited row breaks the chain and the ledger is refused. A run of a registered rule's code path from a research script appends its row. A card whose `ledger_hash_at_run` differs from the stored ledger is not written | temp ledger, 3 synthetic rows | SYNTH |
| T-DSR-01 (L2522, L5659) | `delta_SR = 2.5/sqrt(250)`, `SE_obs = sqrt((1 + 3*SR + 9/4*SR^2)/(T - 1))`, T = 1,250, `SE_null*hurdle = sqrt(0.5/250)*e(N)` -> 0.9505 at N 46, 0.9004 at N 100 | inline numbers (checked here: 0.950502, 0.900397) | SYNTH |
| T-DSR-02 (L2523) | DSR on daily and on monthly data of the same card agree within 0.1; an annualised SR passed with a daily T raises | synthetic daily series, aggregated to months | SYNTH |
| T-NEFF-01 (L2524, L5660) | On QF3's 26-trial difference-series matrix, seed 11: `E_sim` 1.33 +/- 0.01; `N_equiv` 6.3 +/- 0.4; `N_clusters` 5; `N_hat_linear` 12.6 +/- 0.1; padding with 80 near-duplicates of R-03 (rho 0.99) moves `N_equiv` by < 0.5 (6.33 -> 6.59). A card without a ledger hash is refused; no code path computes the Kish N-hat. Row-count clause: QF3's 26 trials stay 26 rows in the R-03 seed | `QX_EX1_qf3_trial_corr_diff.csv` (absent; no local substitute) | REFDATA for the numbers; SYNTH for the refusal, the static scan, the `e()`/`n_equiv` round trip (`n_equiv(1.329)` = 6.31) and a padding property on a synthetic block-correlation matrix |
| T-STEP3-01 (L2525) | R-03 inputs `dSR 0.2729, SE_obs 0.0716, SE_null 0.0935`: 0.98 +/- 0.01 PASS; at `N_hat_linear` 0.947 +/- 0.01 flagged "step 3 borderline". R-04 `0.0724 / 0.0349 / 0.0349`: 0.77 +/- 0.02 FAIL | inline numbers with N 6.3 and 12.6 (checked: 0.9811, 0.9459, 0.7723) | SYNTH as a formula test; REFDATA end to end (N from the matrix) |
| T-STEP3-02 (L2526) | A card without a ledger hash is refused. A static scan finds no implementation of `M / (1 + (M - 1)*rho_bar)` | AST/regex scan of `core/` | SYNTH |
| T-SEL-01 (L2527) | (a) A and B run on 2016-26, then A's header is committed and A runs on 1997-2026: f = N_eff under `any_overlap`. (b) A configuration committed before any family row touches its span: f = 1 (anchored timestamps only, TASK-M7-05). (c) A header declaring `selection_factor` is refused. (d) Both verdicts printed. (f) A placebo, shift-panel or GJR-null run appends no row; the card's own lag rows do not enter its f. (g) Readings giving 1.3 and 2.9: binding f = 2.9. (h) Configurations differing only in target, threshold, multiplier or lag are two rows. Clause (e) (card-run f vs report f: larger binds, both printed, never refused) runs after the freeze (L5589) | synthetic ledger with synthetic difference series and anchors | SYNTH ((e) logic is SYNTH too; its placement is post-freeze) |
| T-ES-01 (L2259) | A continuous rule identical to S (>= 5 objective episodes, >= 882 sessions): `dES_21 = dES_126 = 0` -> REJECT (point not > 0). Halving exposure on the worst 5% of 21-session windows gives `dES_21 > 0` | synthetic close path with >= 5 bears of >= 20% | SYNTH |
| T-DNH-01 (L2257) | A synthetic card passing every gate with `dMDD < 0` and `dCDaR95 < 0` -> INSUFFICIENT DATA; with only `dMDD < 0` -> PASS; no drawdown-line value ever produces REJECT | injected check results into `line_verdict` | SYNTH |
| T-ORDER-01 (L2258) | 26 de-clustered onsets failing PC-2 -> INSUFFICIENT DATA (sufficiency first). 54 onsets with a PC-1' point <= 0 -> REJECT; both points > 0 and a `p*f > 0.10` -> INSUFFICIENT DATA (inconclusive). A timing-fragile card meeting a REJECT condition stays REJECT | injected check results | SYNTH |
| T-EPIS-01 (L2400) | 18 alternating >= 20% KOSPI episodes on 1997-2026, 12 with troughs before 2008; 4 on 2016-26; 16 S&P episodes at 15% on 1990-2026; no Sep-2026 episode in either market, builder run without any override. An open bear at the end of a synthetic series is printed with `open = true` and counts toward neither PC-4 nor PC-7 | KOSPI closes 1997-2026 and S&P 500 closes 1990-2026 (absent). Local cache has no KOSPI index history (`yf__KS200.csv` is 1 row; `yf_069500.KS.csv` is KODEX 200 from 2007) and `yf_SPY.csv` starts 1995 and is an adjusted ETF, so neither count can be asserted | REFDATA for the counts; SYNTH for the open-bear clause and the builder's logic on a hand-built path |
| T-EXCESS-01 (L2402) | v1.2-check mode on PX2's cash fixture (FRED `IRSTCI01KRM156N`, monthly, / 252, used from the month after): Delta-SR +0.006 and `p_ni` 0.078 +/- 0.01; raw flag reproduces +0.026 and 0.052. Frozen-convention values are computed, printed and md5-frozen at first run, never asserted against these. Units: call rate = latest rate dated <= t-1, x days/365; a US session on which the Fed is closed accrues at the prior DTB3 rate; French daily RF enters unchanged; no cash read is filtered by publication time; a missing cash day refuses the card | PX2 cash fixture + Yahoo ^KS11 (absent) | REFDATA for the reproduction; SYNTH for every unit clause and the refusal |
| T-ROLE-02 cash clause (L1969, L5580) | A missing cash day refuses the card, never cash = 0; a KRX session on a day the cash calendar is closed accrues the latest prior rate | synthetic rate series + two calendars | SYNTH |
| T-BAND-01 (L2404) | R-06 KR's band has 32 monthly starts 1997-05 ... 1999-12, asserted as a pair with `history_start` KR 1997-04-01; floor needs >= 22 PASS (`3*n_pass >= 2*n_starts`); the midpoint split date follows from the fixed span end. R-29's decade band has 10 starts and needs >= 8 with no REJECT. A band with one REJECT start fails even with PASS share >= 2/3. A REJECT in either midpoint half fails | config + synthetic verdict vectors + a synthetic session calendar | SYNTH |
| T-POWER-01 (L2628, L5661) | SE(Delta-SR) 0.061 +/- 0.005 (US VT15 vs S, 50 bp, 1990-2026) and 0.130 +/- 0.01 (KOSPI VT20 vs S, 3 bp, 2016-26). MDE80 0.13 / 0.28. Years to detect +0.05 inside 241-246 / 319-330, restated to a point before the freeze (section 9.4 item 11). PC-3 power at a true 0 for KOSPI 2016-26: 0.30 +/- 0.02 | French daily Mkt-RF + ^GSPC splice; ^KS11 (absent). `yf_SPY.csv` 1995-2026 can exercise the code but not the asserted values | REFDATA for the SEs; SYNTH for the arithmetic (0.061 -> MDE 0.1295; 0.130 -> 0.2760; power 0.3042; 10.4 y -> 316.9 years) |
| T-POWER-02 (L2629) | Every card prints SE (HAC and 250-block), MDE80 and power; a card without them is refused | synthetic card | SYNTH |
| T-UNDERPOW-01 (L2630) | With MDE80 > 0.10 a failed PC-3 p-value -> INSUFFICIENT DATA (`underpowered`); a PC-3 point below -0.10, a PC-1' failure or a PC-2 failure keep their REJECT or INSUFFICIENT path; applying the code elsewhere raises | injected results | SYNTH |
| T-PZERO-01 (L2631) | A resample count of 0 prints "< 1/B"; no card field holds p = 0 | series with a huge edge | SYNTH |
| T-PBO-01 (L2632) | Configuration set = ledger union the frozen PC-6 grid, on the card's own objective. The KOSPI VT grid's Sharpe-objective PBO (0.28) is printed; the protective-objective value is the one the step uses. Noise control: first draw of `numpy.random.default_rng(11)`, `normal(0, 0.01, size=(2600, 10))`, truncated to 2,592 rows, 16 contiguous blocks, Sharpe with ddof = 1: PBO 0.536 +/- 0.001. Over 200 such panels (child seeds of `SeedSequence(11)`): mean PBO in [0.45, 0.55]. A single panel is never asserted against [0.4, 0.6] | inline (checked here: 0.535897; 200-panel mean 0.4998) | SYNTH, except the 0.28 line (REFDATA: KOSPI) |
| T-SE-01 (L2633) | R-03 vs unscaled (50 bp): LW-HAC 0.072, 250-block 0.091 (+/- 0.005); z falls from 3.81 to 3.0 and still passes 2.50 | French daily Mom (absent) | REFDATA |
| T-PLACEBO-01 (L3461, L5662) | The look-ahead control is flagged in the sandbox: LP 0.28 >= 0.20 (L0 +0.317, L1 +0.035). R-12 is flagged (FR 0.74 / 0.75 > 0.5). R-03 (FR 0.03) and R-04 (FR ~ 0) pass. R-06 KR's 2016-26 raw-flag row and R-11's FR (0.49) are printed, not asserted. Every lag tried is written to the family ledger (temp copy), L <= 0 rows with `timing_class: NON-COMPLIANT` | `KR_SOX_KRW_gate_B3` (SOX, USD/KRW, KOSPI closes and the R4 B3 thresholds: absent, and the thresholds are not in the spec); R-12/R-03/R-04 fixtures (absent) | REFDATA; SYNTH for the FR arithmetic on the printed grid (R-12: (0.038 - 0.010)/0.038 = 0.737; R-03: (0.314 - 0.306)/0.314 = 0.025; control LP 0.282), for a synthetic same-day-sign look-ahead rule tripping LP >= 0.20, and for the ledger rows |
| T-PLACEBO-02 (L3462) | Static check: no call into `timing_probe` outside `timing_profile()`. Enabling it from the runtime or a book builder raises. A card whose gate statistics read an L <= 0 row is refused. Everything written in probe mode carries `synthetic_lookahead = true` and lands outside the production artifact directory. The positive control's L0 row is computed and its LP recorded | synthetic card | SYNTH |
| T-LAG-01 / T-LAG-02 M7 clauses (L5609-5610, L5582-5584) | A backtest with a look-ahead datum raises `LookAheadError` and refuses to write the card; inside `timing_probe` the violation is recorded in `timing_profile.lags[].lag_audit`, not raised; a deliberately earlier input inside the probe is recorded, not raised | synthetic store row with `available_at_utc > decision_utc` (needs M1's lag audit) | SYNTH |
| T-AVAIL-01 (L5619) | Golden availability table, exact match (DGS10 Fri 2015-01-02 -> KRX close Tue 2015-01-06; DEXKOUS week of 2026-10-05 -> KRX close Wed 2026-10-14; DGS10 2026-10-09 -> US close 2026-10-14; CSAT 2025-11-13 close 07:30Z); fails on an injected registry error (H.15 at D instead of D+1 16:15 ET) | M1 calendars | SYNTH (M1 deliverable; re-run in the freeze list) |
| T-GATE-04 (L2256) | On a synthetic panel that fails 9(a): nothing is frozen and no card runs. One redesign is accepted only if its manifest diff touches frozen-items-table items alone and its fresh seeds were logged before the run; any other diff, or seeds logged after the run, is refused. A second failure leaves every card NOT_RUN in every book, writes a `package_redesign` governance event and pages the owner. A third attempt is refused, also after a 2.x bump. Every attempt and its outcome is in `gate/acceptance_runs.jsonl` | synthetic families whose placebos pass by construction; temp store, temp log | SYNTH |
| T-HERM-02 (L5608) | After `tests/run_all.py`, `core/rules` and every family ledger are byte-identical to their pre-run state | temp copies | SYNTH |
| T-SCHEMA-02 / T-BOOK-01 header clauses (TASK-M7-14) | Each draft validates against `model_card_header.macro` and is refused with any required field removed; declares `instrument_book`, `rebalance`, `no_trade_band`, `notional_nav` and passes the granularity floor | the four drafts | SYNTH with typed placeholders; OWNER for the real `notional_nav` |
| I-05 (L5693) | Zero lag-audit violations across every backtest used for golden values flagged COMPLIANT in section 9.3 | all COMPLIANT golden fixtures (absent) | REFDATA |

### D2. The acceptance test and the freeze

| Test | Assertion | Needs | Class |
|---|---|---|---|
| I-08 pre-freeze part (L5698) | Run once, at most one bounded redesign, results md5-frozen, every attempt logged. <= 10% of 300 circular-shift placebos per family pass PC-1' (both legs: point > 0 and `p*f <= 0.10` at 1x) and <= 2 of 20 per card. Families, multiplier series, markets, spans, costs and fixtures listed in the report. The five negative controls return REJECT or INSUFFICIENT DATA; the 5-day VT is REJECTed by the PC-3 point (Delta-SR -0.29). Each attempt runs with the recorded D6 rule. `p_ni` is printed | KRX official closes from 1997 (R-06 KR, R-31); French daily Mkt-RF/RF 1926-07 -> 2026-08 (R-29, R-28 on R-29's book); ledger seeds; control rule scripts; `notional_nav`; ECOS code; an external anchor | REFDATA + OWNER |
| T-GATE-01 (L2253) | Same counts; the report's md5 is written to `core/rules` and cited by every card header | as above | REFDATA + OWNER |
| T-GATE-03 (L2255) | Each control's verdict in {REJECT, INSUFFICIENT DATA}. Printed, never asserted as points: 5-day Delta-SR -0.29; 10-day -0.106; post-shock-week ES21 z 1.278, Delta-SR -0.093, Delta-MDD -9.1 pp, Delta-CDaR -11.1 pp | as above | REFDATA |
| T-CARD-02 (L5664; after the freeze) | `docs/macro_overlay_study.py` re-hashes the manifest at every card run and refuses on a mismatch; an edit to any `gate.*` block, harness source file, acceptance fixture or seed after the freeze is detected | a temp store with a synthetic frozen package | SYNTH |
| T-REPRO-01b (L5667) | Same seed, rules-store hash, snapshot and package version give identical bootstrap and GJR-null outputs (relative difference <= 1e-12) | synthetic series | SYNTH |

### D3. After the freeze, cited by these rules (not in TASK-M7-01..17; listed so nothing is asserted early)

| Test | Assertion | Class |
|---|---|---|
| T-GATE-02 (L2254) | US VT15, US shares via KIS, 50 bp, daily (fixture `U1`, 1990-2026): v2 verdict INSUFFICIENT DATA as a class; ES21 +1.65 pp, ES126 +3.8 pp (+/- 0.2 pp); `p_ni` printed, not asserted against R4b's 0.146; 2x line Delta-SR -0.125; recorded label stays "REJECT (instrument: US shares via KIS, 50 bp, daily)"; the card is not re-run | REFDATA |
| T-ES-02 (L2260) | Korea 1997-04 -> 2026-10, ETF 3 bp, raw flag: daily Delta-ES99 +1.95 pp; Delta-ES95 of 21-day returns +2.9 pp; Delta-CDaR95 +7.1 pp; z values (4.3; 2.3) in reference mode only | REFDATA |
| T-EPIS-02 (L2401) | 14 of 18 objective episodes positive, max share 0.174 +/- 0.01; printed section 8.6 line 0.493 (4 of 11) | REFDATA |
| T-TROUGH-01 (L2403) | Every card prints a trough -> +63-session window per episode and the three cost episodes; Korea cell vs S: -6.9 / -15.5 / -31.5 pp; none enters PC-4 | REFDATA |
| T-RLAYER-01 (L2405) | `with_risk_layer` reproduces Check C2 (24 HALTs, MDD -56.4% vs -45.3%); a run with the convention flipped is refused | REFDATA; the refusal is SYNTH |
| G-DSR-01 / G-DSR-02 (L5947-5948) | 0.9505 / 0.9004; R-03 net: SR 0.6723, T 9,233, skew -0.687, kurtosis 6.948, Delta-SR +0.2729, HAC SE 0.0716 (NW-250 0.093) | SYNTH / REFDATA |
| G-PWR-01 / G-PWR-02 (L5972-5973) | SE and years ranges; P(REJECT) at a true 0 per cell | REFDATA |

Test tiers (L5496): `fast` (unit; <= 10 min total), `golden` (fixture reproductions; <= 2 h), `freeze` (I-08, formal runs, GJR-null paths, PBO). Use small B on synthetic fixtures; the whole suite is single-process.

---

## E. Interfaces

### E1. Needed from earlier milestones

| From | What | Used by |
|---|---|---|
| M0 (TASK-M0-05/06) | Macro rules store with the `gate.*` blocks and `owner_decisions` (`{ref}` resolution); read/write of `gate.package`; ledger hash per family; a temp-copy helper for tests | every module; freeze |
| M0 (TASK-M0-07) | Hash-chained governance appender; kinds `package_freeze`, `package_redesign`, `header_commit`; the owner page sink | freeze, redesign |
| M0 (TASK-M0-09/13) | `validate_card_header`, both card schemas, R-26 header checks, `sleeves.<market>.notional_nav` | drafts, refusals |
| M0 (TASK-M0-11) | `canonical_json` (UTF-8, sorted keys, floats by repr, no insignificant whitespace; L5616), md5 helper, artifact writer, `macro_artifact_dir()`, reproducibility record (`git_hash`, `config_hash`, `data_snapshot_id`, `knowledge_utc`) | ledger hash, manifest, cards |
| M1 (TASK-M1-11/21/22) | Official closes with `value_status` and `session_date`; frozen card snapshot at `knowledge_utc`; cash series `BOK_CALL_RATE`, `US_RF` with their observation calendars; fixtures + `tests/fixtures/macro/MANIFEST.csv` | books, episodes, cash leg |
| M1 (TASK-M1-04) | `regime_tags(date)` | episodes, regime lines |
| M1 (TASK-M1-19) | Independent lag audit, `LookAheadError`, the positional-shift linter | timing profile, I-05 |
| M2 (TASK-M2-06) | Costed engine: on/off books, turnover cost on the day the new weight earns, tick floor, 2x stress; `market_vol_target`; `compose()` | books, PC-6 grid, placebos |
| M3 | Estimator calibration status (SMA20 B5; challenger Stage 1); `ewma094` | estimator cap; benchmark 4 |
| M5 | `drawdown_ladder`, hard stop and caps | `with_risk_layer` line; R-31 book |

### E2. Exposed to later milestones

| Name | Shape | Consumer |
|---|---|---|
| `cardp_evaluate(header, books) -> CardPResult`, `overlay_card_eval(card, ledger) -> CardResult` | section B4 | `docs/macro_overlay_study.py` (TASK-M7-19), stack card (M7-29), R-28/R-29 (M8) |
| `step3(card) -> Step3Result`, `n_eff(ledger)`, `family_ledger(family_id)`, `ledger.append/hash` | B1 | every card run; R-04 on the R-03 ledger (M7-25) |
| `timing_profile(card) -> TimingProfile`, `power_line(...) -> PowerLine`, `episodes(...)`, `excess_returns(...)`, `start_band(...)`, `se_ladder`, `lw_studentized_boot` | B2-B5 | cards; R-30 Stage 3 CIs (M7-28); R-25 forward monitor (M8) |
| `verify_package() -> None` (raises `PackageMismatch`), `package_state() -> {"NOT_FROZEN", "FROZEN", "BLOCKED"}` | B6 | study runner (T-CARD-02), `verdict_filter` (R-35: `gate_package_md5`), Macro page |
| `card_placebo_panels(header)` | 300 + 20 under the frozen 9(a) | CARD-Ps registered after the freeze |
| `attempts()` | list of attempt rows | printed beside every verdict |
| `AcceptanceReport.f[card_id]` | f per reading | T-SEL-01 (e) at each card run |

---

## F. Ambiguities, contradictions, conservative readings

| # | Issue | Lines | Reading used (conservative: fail closed, no exposure change) |
|---|---|---|---|
| 1 | The acceptance population includes R-29 "on its declared book and span", and its decade band needs a >= 80-year daily span; the 1926+ French file was never fetched (HTTP 403) and the acquisition register dates it "M8" | L2179, L2341, L3080, L3126, L6028 | The freeze needs the 1926 file. Without it the acceptance test cannot run; do not substitute the 1990 file (L3126 forbids the fallback for the settling run). BLOCKER |
| 2 | "Repository commit" is the external anchor for the manifest, the md5s, headers and seed `run_utc`; the QUANTGEN folder is not a git repository | L4820, L6012 | `step3()` refuses unanchored timestamps, so f = 1 is unreachable and the freeze is refused until the owner initialises a repository or names another timestamped anchor. OWNER |
| 3 | The five negative controls are named only (`US_VT_5d_50bp`, `US_VT_10d_50bp`, `post_shock_day_0p5`, `post_shock_week_0p5`, `VT_sigma_lag_252`); shock threshold, market, target and cost of the EX1 rules are not stated | L2182-2185, L5268-5270 | Do not invent them. The control definitions come from PX1/EX1 scripts in the reference data. BLOCKER for I-08 |
| 4 | The three CDaR-guard candidates are named, not defined | L2187 | Needed only if a control passes. If triggered and undefined, the attempt fails (9(a)); nothing is frozen |
| 5 | The R4 B3 rule (thresholds, multiplier) of the positive control is "quoted from R4 B3", not in the spec | L3430 | T-PLACEBO-01's control is REFDATA. A failed or missing control blocks every card run (L3454) |
| 6 | CDaR95, time under water, worst-day coverage, re-entry lag, timing return, bull tax: no formula | L2190-2193, L5256 | CDaR95 = mean of the worst 5% of the drawdown series (it feeds the do-no-harm cap, so it is the only one that can change a verdict). The others are printed only; implement the plain definitions and label them "definition: harness" |
| 7 | "LW-HAC SE": kernel and bandwidth not stated; goldens quote both "NW10" and "QS" | L2463, L5972, L5948 | QS kernel with Andrews automatic bandwidth as `se_hac`; NW10 printed beside it. T-POWER-01's +/- 0.005 covers both |
| 8 | The studentized bootstrap's t*, the influence function and the Politis-White estimator are named, not written out | L2565, L2569 | Ledoit-Wolf (2008) delta-method psi and block-sum studentization; Patton-Politis-White (2009) for the circular bootstrap. Section B2 |
| 9 | PC-1' bootstrap: resample daily pairs and rebuild h-session windows, or resample the overlapping `R_h` series; whether `m_bar` is re-estimated per resample | L2154 | Resample paired daily rows of (x_rule, x_S) with one index path; `m_bar` fixed at its sample value |
| 10 | "Lowest 5%" count in ES and in the worst-5% sets of PC-2 | L2149, L2157 | `k = ceil(0.05*n)` lowest values |
| 11 | 2x leg failure: "points" at 2x (8.1.1 row 6) or the full leg with `p*f` (8.7 row PC-1', R-29 rule 4) | L4765, L5200, L3090 | Full leg (point > 0 and `p*f <= 0.10`) at 2x; a failure gives REVISE. Harder to PASS |
| 12 | Episodes "in the sample" for sub-spans, band starts and halves: builder re-run on the sub-span, or full-history episodes filtered | L2318, L2400 ("4 on 2016-26") | Date from the first close of the declared history (rule text), count only episodes whose whole window lies inside the evaluated span; the REFDATA test decides whether that reproduces "4" |
| 13 | A "monthly start": which session; whether the estimator may use closes before a band start | L2341 | First session of the month; closes before the start are not used and the warm-up is re-applied (the band tests sample dependence) |
| 14 | Verdict at each band start and half: with or without the caps | L2343, L5221 | Full `line_verdict` at the binding f, without the stability cap itself (no recursion) |
| 15 | De-clustering of onsets | L2167 | An onset = the multiplier leaving 1.0; keep it only if >= own lookback sessions after the previous kept onset |
| 16 | How the harness knows a rule is discrete or continuous, and which `pc6_axes` row applies; no header field | L2166-2167 | A rule-type map in the rules store keyed by `rule_id`, frozen with the package; never a header field |
| 17 | PBO for CARD-P: "within each CSCV block": pooled windows of a half, or the mean of per-block ES; each configuration's comparator | L2585 | Pool the within-block 21-session windows of the half; each configuration against its own S |
| 18 | `SE_null` vs `V_trials` when ">= 30 independent trials": "independent" undefined | L2464-2465, L2495 | Independent = `N_clusters >= 30`; then use `sqrt(V_trials)`; both printed. No v2 family reaches 30 |
| 19 | `selection_factor.alt_value` meaning; the cap of `p*f` at 1 | L2509, L4019 | `alt_value` = the non-binding one of {1, N_eff}; `p_adj = min(1, p*f)` |
| 20 | z-check "cells": how the pre-registered cell count is obtained | L2479 | Use 3.34 unless the header's pre-registered cell count is <= 8. Printed only |
| 21 | BY q-value, Harvey-Liu haircut, PSR vs S, DSR vs 0, Holm: no formulas | L2480, L2579, L2470 | Standard forms (B2); all printed, none gated |
| 22 | "A row not appended by the harness is refused": no detection mechanism beyond the chain | L2514 | `append` is the only writer; chain verification plus comparison with the committed family hash |
| 23 | "Adoption counts as one revision in every family ledger": a revision count is never N, and a ledger row is a distinct configuration | L4820, L2446 | Record it as the header `revision` increment and a `package_freeze` event; append no row for 2.0.0. A later package version's re-runs append rows through the harness |
| 24 | Draft md5 = "the header fields without the package citation": which fields are excluded | L4815 | Exclude `gate_package_version`, `gate_package_md5`, `header_md5`, `created_utc`; the committed header must match on everything else |
| 25 | Horizon-matched PC-2 adoption: pooled or per-card false-pass rate; what "false pass" tests | L2186 | Adopt only if the pooled rate and every card's rate are <= 10% on the horizon ratio; otherwise keep the daily ratio (the default) |
| 26 | `gjr_null_pct` is one number; the rule reports two percentiles (Delta-MDD, Delta-ES21) | L2191, L4045 | `gjr_null_pct` = the Delta-MDD percentile (R-28's "87th"); the Delta-ES21 percentile goes into `printed`. Schema owner: M0 |
| 27 | GJR-null paths: `fit_gjr` works on log returns; cash on simulated paths | L2191; gjr.py:130 | Fit on log returns, convert simulated paths to simple returns, subtract the card's own cash path by position |
| 28 | DTB3 discount-basis conversion: no formula | L1440, L2333 | M1 registry task; the harness consumes an annual rate and refuses a series without a declared unit |
| 29 | `round()` in the tau grid (Python rounds half to even) | L2177 | Use Python `round`; the choice is frozen with the harness source |
| 30 | REVISE sub-order when several REVISE checks fail | L5242-5245 | The listed order: 2x cost, PC-6, PC-5 |
| 31 | Source-file md5 on Windows: OneDrive sync or a later `autocrlf` can change bytes without changing code | L4820 | Hash with CRLF normalised to LF, documented in the manifest |
| 32 | Tech-fund XS-11 asks for `max(10, Politis-White on d and d^2)` on steps 2 and 5 "on every card"; the macro spec withdraws PW(d^2) and freezes PW(psi) with a 21-session floor | R3 L1299 vs L2569, L4991 | Package 2.0.0 follows the macro spec. Print the XS-11 block beside it as a non-gating line; adopting it is a package change to be decided before the freeze. Owner decision |
| 33 | Tech-fund XS-12 adds comparator `S_beta = beta_hat x market + (1 - beta_hat) x cash` for stock-level sleeves; the header enum has only `S_same_average_exposure` and `overlay_off`; the estimation window is open (OQ-03) | R3 L1300 vs L3982, L5185 | Not in 2.0.0. It needs a schema value and a frozen definition before the freeze, or a new package version. Owner decision |
| 34 | `prep/readlines.py` has a syntax error | — | Long lines were printed with an inline script; L2473 was read in full |

Not ambiguous, restated because they are easy to get wrong: T-EXCESS-01, T-GATE-02 and T-ES-02 assert research numbers only in v1.2-check or reference mode; the frozen-package values are computed at first run and md5-frozen, never asserted against the research numbers (L6011). Reference mode and v1.2-check mode are reachable only from `tests/reference/` and `docs/`; `core/` cannot import that code (L5992).

---

## G. DO-NOT-BUILD items and invariants that bind this area

- **P11 / red lines P2, E2, Q1 (L605-608):** one gate package, adopted once and blind. No gate rule, threshold or convention is chosen after seeing the card it decides. A change is a new package version, applied to every card, flips disclosed. No real card's verdict is computed before the freeze.
- **P12 / red lines P1, Q2 (L611-617):** single-path drawdown statistics never REJECT; through the do-no-harm cap they can at most cap at INSUFFICIENT DATA. Promotion needs objective episodes, no episode above 50% of the benefit, no REJECT at any band start or in either midpoint half, per-regime lines.
- **P13 and DNB 36 (L620-622, L6223, L6247):** every configuration is a ledger row; `N_eff = max(N_clusters, N_equiv)`; the Kish form is never computed anywhere; revision counts are never N; an N rule other than `gate.step3.n_gate` is refused.
- **P14 and DNB 35 (L625-627, L6219):** a forward record never raises a verdict; UNDERPOWERED converts only a failed step-5 or PC-3 p-value.
- **P5 with its single exception (L539):** point-in-time everywhere; the only look-ahead allowed is R-34's `timing_probe`, tagged `synthetic_lookahead`, never a production artifact, never feeding a verdict.
- **P10 and DNB 23, 32 (L579-602, L6170, L6211):** costs read from the gate, tick floor only raises, 2x run on every card, never lowered; an instrument book, rebalance, band or venue change is a new card, never a revision.
- **DNB 34 (L6216):** no pooled or A-provisional route for a card already run; a pooling rule is declared in the header before any market is run.
- **DNB 37 (L6224):** an R-28 instance with `market: KR` is refused; a horizon-matched PC-2 may never rescue KOSPI trend.
- **DNB 18 (L6147):** 2022-01-01 -> 2026-10-02 is a reported stress window, not a holdout; the locked holdout starts 2027-01-01.
- **DNB 2 / Tier C (L4864, L6077):** the CARD-P class applies only to rules whose output never exceeds 1.0; a multiplier above 1.0 is REJECT by construction and refused by the rules store. Cap-above-1 computations exist only in reference mode.
- **DNB 22 (L6163):** a non-PASS card's output never reaches the recommended book; nothing in this area writes to a book or to `engine_feed`.
- **DNB 21 / P0:** no order, cancel, withdrawal, deposit-address or transfer path; the harness is arithmetic on arrays and JSON files.
- **R2-C1 (L53, L4837):** R-06 KR is expected to read INSUFFICIENT DATA through f. No convention, window, cap, cash series or row set may be changed to rescue it.
- **R-21 9(a):** a per-card placebo excess is never fixed by editing the tau grid, the placebo construction, the pass definition or the PC-1' definition.
- **f is computed, never declared (C-2):** a header that declares `selection_factor` is refused.
- **A card never declares** its PC-6 axes or steps, its start band, its pass share, or its comparator definition; these are frozen in `gate.*`.
- **Hermetic tests (T-HERM-01/02):** no network; tests write only to temporary copies of the rules store, the ledgers, the attempts log and the artifact directory.
- **No fabricated freeze:** `gate.package` md5s, `acceptance_report.json` and attempt rows are written only by a real attempt on the frozen reference data. Until then the package state is NOT_FROZEN and every macro card is `NOT_RUN`.
