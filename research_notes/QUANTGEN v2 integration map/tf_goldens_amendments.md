# tf_goldens_amendments — tech-fund golden values, corrected anchors, cross-spec amendments and open questions (digest for the QUANTGEN v2.0 build)

Refs: `R3:n` = `QUANTGEN_techfund_research_bundle/QUANTGEN_techfund_research/research_notes/R3_TF_neural_link.md` line n (read 896-1345 completely). `SPEC:n` = `QUANTGEN_Quant_Council_2026-10-03/claude_code/QUANTGEN_MACRO_INTEGRATION.md` line n (v2.0, 6,480 lines). `LAB:` = `QUANTGEN_techfund_research_bundle/QUANTGEN_techfund_research/datalab/`. `CODE:` = QUANTGEN repo path. `CR-nn` = coordinator rulings `R3:26-72`.

Status of every number here (R3:1335, R3:1337): KRX lab values are in-sample price returns without dividends, Sharpe with rf = 0; none is a run of QUANTGEN's gate; nothing in this note changes exposure. The tech-fund round read macro spec **v1.2**; Council v2.0 is later. Section C re-checks every amendment against v2.0.

---

## A. Golden values (R3 section 11, lines 896-1238)

### A.1 Files, schema, fingerprints

| File (LAB:results/r3/) | Bytes | sha256[:16] | Rows x cols | Notes |
|---|---|---|---|---|
| `r3_golden_values.csv` | 125250 | ca2dfc3fd78d81c3 | 523 x 13 | UTF-8, no BOM, LF; `gv_id` GV-001..GV-523 contiguous, unique |
| `r3_pair_share.csv` | 1774 | 66837d6562c7984c | 8 x 12 | 8 snapshot dates |
| `r3_pair_share_summary.csv` | 951 | 4a82a1199409f13b | 16 x 2 | `item`,`value` (value is text: numbers, dates, or `date / share`) |
| `r3_pair_share_2026_daily.csv` | 15983 | 669d359cb9cbe203 | 181 x 5 | 2026-01-02..2026-09-29 sessions |

Companion (not read): `charts/golden_values.json` (R3:898).

**`r3_golden_values.csv` columns (verbatim):** `gv_id`, `card_or_rule`, `decision`, `quantity`, `market`, `period`, `gross_net`, `value` (printed form, e.g. `+3.08%`, `1.53`, `2026-05-06`, `NOT TRACED`), `raw` (machine value where numeric, e.g. `0.0307644`; `NOT TRACED` otherwise), `source_file` (bundle-relative lab path), `line` (**1-based line in the CSV counting the header**: data row index = line − 2; R3:915 "file line = row + 1"; two-line cells use `;`, e.g. `13;11`), `status`, `note`.

**`status` vocabulary and counts (R3:898):** `traced` 497, `derived` 20, `not traced` 6. Tolerance proposal (R3:898): traced values to the printed precision (Level 1), derived within 1 bp, verdict strings exactly. (Council Level 1 for comparison: SPEC:5734 Sharpe ±0.01; max DD ±1 pp; window returns ±1 pp; weights ±0.02; bootstrap shares ±0.03; SPEC:5735 p ±0.01 (p ≥ 0.05) / ±0.005 (p < 0.05), deterministic counts exact.)

**`decision` vocabulary (24 strings; top):** `BUILD NOW` 146, `FORWARD-SIM (CR-02)` 45, `REFERENCE / BACKLOG` 40, `REFERENCE` 35, `BUILD NOW (macro R-06; protective workhorse, CR-02)` 30, `DO-NOT-BUILD at 50 bp (CR-02)` 24, `GOVERNANCE (CR-08)` 24, `INVARIANT (owner to confirm)` 22, `BUILD NOW (risk control; CR-05)` 22, `BUILD NOW (rule)` 20, `INVARIANT` 17, `REFERENCE (CR-02)` 15, `BUILD NOW (flags)` 9, `FORWARD-SIM (CR-05)` 9, `INVARIANT (CR-09)` 8, `BUILD NOW (macro R-06)` 8, `DO-NOT-BUILD (CR-03)` 6, `-` 6, `INVARIANT (data rule)` 6, `DROP (CR-06)` 4, `GOVERNANCE` 4, `SPEC BOOK ONLY (CR-05)` 1, `KEEP + governance (CR-10)` 1.

**`market`:** `KRX` 319, `KOSPI (rebuilt)` 135, `SPY` 32, `simulated` 13, `KOSPI` 10, `US` 7, `-` 6, `crypto` 1. **`gross_net` (23 strings):** `net 35 bp/side` 212, `net 3 bp/side (KRX ETF)` 45, `gross` 40, `net KRX ETF 3bp` 40, `as labelled` 30, `net US via KIS 50bp` 24, `market cap` 22, `net 3 bp/side` 20, `derived from gross diff and turnover` 12, `price index` 10, `net 70 bp/side (2x)` 10, `derived` 8, `net Futures 5bp` 8, others ≤ 6.

### A.2 Counts by `card_or_rule` (= R3 section) and status

| card_or_rule (verbatim) | GV range | n | traced / derived / not traced | R3 § |
|---|---|---|---|---|
| SCR-1 lottery composite exclusion (F4, worst decile of vol+MAX+turnover ranks) | GV-001..091 (interleaved with SCR-2) | 52 | 52/0/0 | 11.2 |
| SCR-2 dilution exclusion (F6, 252-session share growth > 10%) | GV-014..104 | 52 | 52/0/0 | 11.2 |
| SCR-1 lottery composite | GV-105..150 | 35 | 31/4/0 | 11.2 |
| F5 attention-fade monthly screen (DROP) | GV-106..115 | 4 | 0/4/0 | 11.2 |
| SCR-2 dilution screen | GV-107..122 | 7 | 3/4/0 | 11.2 |
| SCR-3 construction rule (F1, highest-turnover quintile excluded) | GV-151..170 | 20 | 20/0/0 | 11.2 |
| INV-2 limit-lock rule | GV-171..174 | 4 | 4/0/0 | 11.10 |
| R1 KRX panel regression (engine check) | GV-175..188 | 14 | 14/0/0 | 11.16 |
| GOV-7 break-even pre-gate screen | GV-189..196 | 8 | 0/8/0 | 11.15 |
| INV-1/INV-2 close fills and limit-lock rule | GV-197..202 | 6 | 6/0/0 | 11.10 |
| DATA-2 corporate-action-adjusted returns | GV-203..209 | 7 | 7/0/0 | 11.11 |
| DATA-5 Korean regime and event flags | GV-210..218 | 9 | 9/0/0 | 11.12 |
| RISK-1 pair-share series (R-07 pair cap) | GV-219..240 | 22 | 22/0/0 | 11.1 |
| MOM-1 R-03 own-vol scaling on KRX momentum sleeves | GV-241..262 | 22 | 22/0/0 | 11.7 |
| MOM-2 Daniel-Moskowitz gate (spec book only) | GV-263 | 1 | 1/0/0 | 11.7 |
| FS-2 constrained KRX momentum card | GV-264..272 | 9 | 9/0/0 | 11.13 |
| IDX-1 KOSPI VT20 (macro R-06) reproduction | GV-273..302 | 30 | 30/0/0 | 11.8 |
| IDX-1 index vol target | GV-303..310, 343..350 | 16 | 16/0/0 | 11.3 |
| IDX trend sleeve | GV-311..318, 351..358, 367..374 | 24 | 24/0/0 | 11.3 |
| IDX trend x vol target | GV-319..326, 359..366 | 16 | 16/0/0 | 11.3 |
| IDX SMA200 | GV-327..334 | 8 | 8/0/0 | 11.3 |
| IDX 12-month sign | GV-335..342 | 8 | 8/0/0 | 11.3 |
| FS-1 KOSPI floored trend x VT20 (primary) | GV-375..383 | 9 | 9/0/0 | 11.4 |
| FS-1 comparison cells | GV-384..419 | 36 | 36/0/0 | 11.4 |
| IDX start-date sensitivity | GV-420..434 | 15 | 15/0/0 | 11.5 |
| IDX crash window | GV-435..439 | 5 | 5/0/0 | 11.14 |
| DATA rebuilt KOSPI check | GV-440..449 | 10 | 10/0/0 | 11.11 |
| GOV-4 block length max(10, PW) for steps 2 and 5 | GV-450..459 (ex 456) | 9 | 9/0/0 | 11.15 |
| GOV-5 gate power and size | GV-456, 460..462 | 4 | 4/0/0 | 11.15 |
| DATA-3 month-end data rule (no Shiller averages) | GV-463..468 | 6 | 6/0/0 | 11.11 |
| FS-3 KRX low-vol descriptive sleeve vs S_beta | GV-469..489 | 21 | 21/0/0 | 11.6 |
| GOV-3 attribution block (low-vol example) | GV-490..495 | 6 | 6/0/0 | 11.15 |
| GOV-3 attribution block (SML check) | GV-496 | 1 | 1/0/0 | 11.15 |
| verification log reference | GV-497..502 | 6 | 6/0/0 | 11.18 |
| DNB-4 KRX stock-level short-term reversal (evidence) | GV-503..508 | 6 | 6/0/0 | 11.17 |
| INV-5 no name-level stops (evidence) | GV-509..516 | 8 | 8/0/0 | 11.9 |
| CRY-1 card C3 (keep PASS) | GV-517 | 1 | 1/0/0 | 11.17 |
| FS-1 floored trend x VT20 | GV-518 | 1 | 0/0/1 | 11.19 |
| FS-4 ridge / Fama-MacBeth challenger | GV-519 | 1 | 0/0/1 | 11.19 |
| CRY-1 C3 controls | GV-520 | 1 | 0/0/1 | 11.19 |
| RISK-2 ladder (owner decision) | GV-521..522 | 2 | 0/0/2 | 11.19 |
| SCR-1/SCR-2 step 9 | GV-523 | 1 | 0/0/1 | 11.19 |

R3:1238: 463 of 523 are printed in the note; items with no numeric golden: ML-1, DATA-4, DATA-6, FS-4, FS-5. 36 rows carry a verdict string in `value`.

### A.3 What exists locally (input data vs lab result files)

- **Raw inputs cited (`/home/claude/data_raw/marcap/data/marcap-2023..2026.parquet`, the rebuilt KOSPI, KRX all-stock panel, French files) are NOT on this machine.** No subsection can be recomputed from raw data.
- **Lab result CSVs ARE local** under `LAB:results/` with a path remap: `r2/kr/results/X` → `LAB:results/r2_kr/X`; `r2/idx/results/X` → `LAB:results/r2_idx/X`; `kr/results/X` → `LAB:results/kr/X`; `us/results/X` → `LAB:results/us/X`; `r2/verification/X` → `LAB:verification/X`; `r3/results/X` → `LAB:results/r3/X`. Present: all `r2_kr_*` and `r2_idx_*` files cited, `kr_key_numbers.csv`, `kr_validation.csv`, `us_C_factors.csv`, `exec_verification_log.csv`, `prof_verification_log.csv`, `prof_v04_weekly_reversal.csv`. **Absent:** `kr/results/kr_index_sanity.csv` (GV-440..449) and `r2/verification/exec_chair_checks/c12_lowvol_samebeta.csv` (GV-469..489) — those 31 values exist only in `r3_golden_values.csv`. Script `scripts/r3/r3_01_pair_share.py` is present (R3:902).
- **QUANTGEN cache** `CODE:docs/asset_expansion/cache/` (46 CSVs): `yf_SPY.csv` 1995-01-03..2026-09-25 (7,986 rows), `yf__VIX.csv`, `yf__VIX3M.csv`, `yf_005930.KS.csv` 2000-01-04..2026-09-23, `yf_005935.KS.csv`, `yf_069500.KS.csv` 2007-01-29.., `upbit_KRW-BTC.csv` 2017-09-25..2026-09-25, `binance_BTCUSDT.csv`; `yf__KS200.csv` has 1 row (unusable). No `000660`, no `^KS11`, no shares outstanding.
- Consequence: an acceptance test in QUANTGEN can (a) **assert frozen reference constants** read from `r3_golden_values.csv` (and cross-check them against the local lab CSV cell named by `source_file`/`line`), and (b) **recompute derived quantities** from local CSV columns. Only 11.11 (SPY averaging bias / autocorrelation) and 11.17 GV-517 (C3) have raw inputs locally.

### A.4 Per subsection: assertable values, computation, availability

Notation: **FROZEN** = assert the constant (source CSV cell local unless stated); **RECOMP(csv)** = recomputable from local lab CSV columns; **RECOMP(raw)** = recomputable from local raw data.

**11.1 Pair share for CR-07 (R3:900-938; GV-219..240).** Definition (CR-07, R3:50; R3:904): numerator = market cap of `005930 + 005935 + 000660`; denominator = all KOSPI-listed lines in the KRX daily all-stock file; common lines = codes ending in `0`. Columns of `r3_pair_share.csv` (verbatim): `date, n_kospi_lines, n_common_lines, samsung_common_krw, samsung_pref_krw, skhynix_krw, kospi_all_lines_krw, kospi_common_only_krw, CR07_pair_incl_pref_over_all_lines, alt_pair_common_over_all_lines, alt_pair_common_over_common_only, alt_pair_incl_pref_over_common_plus_pref`. Daily file columns: `Date, cr07_pair_share, alt_pair_common_over_all_lines, alt_pair_common_over_common_only, alt_pair_incl_pref_over_common_plus_pref`.

| Date | lines / common | CR-07 | common/all | common/common | incl.pref/(common+pref) |
|---|---|---|---|---|---|
| 2023-12-28 | 953 / 839 | 0.292943 (29.29%) | 0.268834 | 0.277938 | 0.295498 |
| 2024-12-30 | 961 / 848 | 0.244770 | 0.226244 | 0.232828 | 0.247180 |
| 2025-12-30 | 958 / 847 | 0.361281 | 0.340353 | 0.350526 | 0.364229 |
| 2026-05-07 | 948 / 838 | 0.474864 | 0.450629 | 0.464692 | 0.477744 |
| 2026-06-22 | 946 / 836 | 0.580806 | 0.556680 | 0.573100 | 0.583446 |
| 2026-06-25 | 946 / 836 | 0.596875 (peak) | 0.571082 | 0.588825 | 0.599477 |
| 2026-06-30 | 945 / 835 | 0.578887 | 0.554340 | 0.570955 | 0.581535 |
| 2026-09-29 | 942 / 831 | 0.537062 (53.71%) | 0.508202 | 0.525874 | 0.539622 |

RECOMP(csv), verified here: `CR07 = (samsung_common_krw+samsung_pref_krw+skhynix_krw)/kospi_all_lines_krw`; `alt1 = (samsung_common_krw+skhynix_krw)/kospi_all_lines_krw`; `alt2 = (samsung_common_krw+skhynix_krw)/kospi_common_only_krw`; `alt3 = (samsung_common_krw+samsung_pref_krw+skhynix_krw)/(kospi_common_only_krw+samsung_pref_krw)`; max |diff| 1.1e-16. Summary (R3:917-934; `r3_pair_share_summary.csv` lines 2-17) RECOMP(csv) from the daily file, verified: CR-07 share on 2026-09-29 `0.537062`; first session > 0.45 in 2026 `2026-05-06` at `0.470159`; 2026 peak `2026-06-25` / `0.596875`; sessions > 0.45 `99` of `181`; `alt_pair_common_over_all_lines` first `2026-05-07` (0.450629), peak 0.571082, count `98`; `alt_pair_common_over_common_only` first `2026-05-06`, peak 0.588825, count `99`; `alt_pair_incl_pref_over_common_plus_pref` first `2026-05-06`, peak 0.599477, count `99`. R3:936: the executives' "first above 0.45 on 7 May 2026" belongs to common/all-lines; under CR-07 the cap first binds 2026-05-06. Raw KRX marcap panel absent → component market caps are FROZEN; everything downstream is RECOMP(csv). Exposure effect: none (v2.0 removed the 0.45 trigger; section C XS-07/XS-22).

**11.2 Screens SCR-1 / SCR-2 / SCR-3 / F5 (R3:940-961; GV-001..170).** Books: B1 = EW ALL; B2 = VW ALL 5%-capped; B3 = top-200 VW 5%-capped; B4 = 12-1 momentum top quintile EW. KRX, 366 monthly formations 1996-03..2026-09, filtered minus unfiltered, %/yr. Local source `LAB:results/r2_kr/r2_kr_excl_summary.csv` (528 x 28; columns `base, filter, family, primary, cost, ann_diff, te, ir, nw_t, sharpe_filtered, sharpe_unfiltered, cagr_filtered, cagr_unfiltered, cagr_diff, maxdd_filtered, maxdd_unfiltered, maxdd_diff, turnover_filtered, turnover_unfiltered, n_months, boot_p, boot_p_perc, boot_ci90_lo, boot_ci90_hi, pct_years_pos, n_years, excl_share_names, excl_share_weight`; `cost` ∈ {`gross`,`net35`,`net70`}), `r2_kr_excl_long.csv` (sub-periods), `r2_kr_excl_gate.csv` (8 x 41; `steps_passed`, `verdict`, `g3_dsr`, `g9_haircut_ann_diff`, `g9_haircut_ir`), `r2_kr_excl_dsr_best.csv`.

| Screen/book | gross | net35 | net70 | IR | NW t | years+ | dMDD | break-even bp/side | sub-periods 96-05/06-15/16-26 | indicative gate | GV |
|---|---|---|---|---|---|---|---|---|---|---|---|
| SCR-1 F4 B1 | +3.39% (raw 0.0338837) | +3.08% (0.0307644) | +2.76% (0.0276451) | 1.53 (1.52953) | 8.34 (8.33514) | 0.90 | +1.70% | 380 | +4.31/+2.81/+2.20 | 7/8 REVISE, DSR 0.939 | GV-001..005,007,010,105,117..119,126..128 |
| SCR-1 F4 B2 | +0.99% | +0.85% | +0.72% | 0.68 | 3.87 | 0.77 | +1.03% | 255 | - | 7/8 REVISE, DSR 0.001 | GV-027..031,033,036,108,132..134 |
| SCR-1 F4 B3 | +0.57% | +0.49% | +0.40% | 0.39 | 2.32 | 0.61 | +0.76% | 234 | - | 6/8 REJECT, DSR 0.000 | GV-053..057,059,062,111,138..140 |
| SCR-1 F4 B4 | +6.76% | +6.13% | +5.50% | 1.24 | 7.53 | 0.97 | +2.93% | 375 | +6.82/+6.65/+5.01 | 7/8 REVISE, DSR 0.563 | GV-079..083,085,088,114,123..125,144..146 |
| SCR-2 F6 B1 | +2.42% | +2.34% | +2.26% | 0.65 | 3.93 | 0.81 | +0.36% | 1057 | +2.92/+2.83/+1.34 | - | GV-014..018,020,023,107,120..122 |
| SCR-2 F6 B2 | +0.79% | +0.69% | +0.58% | 0.15 | 0.83 | 0.81 | +0.22% | 265 | - | - | GV-040..044,046,049,110 |
| SCR-2 F6 B3 | +0.41% | +0.29% | +0.18% | 0.06 | 0.32 | 0.61 | -0.13% | 124 | - | - | GV-066..070,072,075,113 |
| SCR-2 F6 B4 | +4.41% | +4.23% | +4.05% | 0.57 | 3.31 | 0.90 | +1.88% | 862 | - | - | GV-092..096,098,101,116 |
| SCR-3 F1 B1 | +4.78% | +4.28% | +3.78% | 1.15 | 6.62 | 0.94 | +2.41% | - | - | 7/8 REVISE, DSR 0.410 | GV-151..160 |
| SCR-3 F1 B4 | +8.62% | +7.81% | +7.00% | 1.02 | 6.20 | 0.94 | +6.38% | - | - | 7/8 REVISE, DSR 0.209 | GV-161..170 |
| F5 DROP B1/B2/B3/B4 | - | - | - | - | - | - | - | 68 / 21 / 10 / 76 | - | - | GV-106/109/112/115 |

Other B1/F4 cells: one-sided bootstrap p `0.0005` (GV-006), Sharpe filtered `0.33` vs unfiltered `0.22` (GV-008/009), turnover/yr `2.78` vs `1.89` (GV-011/012), names excluded `0.10` (GV-013). Best of 176 trials (B1, F4 at 5% cut): pooled DSR `0.979` (GV-150; `r2_kr_excl_dsr_best.csv` line 2). Break-even (status `derived`): `ann_diff(gross) / (turnover_filtered − turnover_unfiltered)` in bp per side; pre-gate screen rejects if < 70 bp (GV-105 note) → RECOMP(csv) (check: 0.0338837/(2.78−1.89) ≈ 381 bp ≈ 380). All other cells FROZEN. **Step-9 caution (R3:961, CA-21):** `g9_haircut_ann_diff` in `r2_kr_excl_gate.csv` is 0.4 × diff (B1/F4 0.012306 = +1.23%/yr); the spec convention is 0.6 × OOS (+1.85%/yr) — never assert the lab's g9 column as a golden (GV-131/137/143/149 notes).

**11.3 Index protective scorecards vs same-exposure S (R3:963-975; GV-303..374).** Source `LAB:results/r2_idx/r2_idx_protective_scorecard.csv` (21 x 93; key columns `pc1_dmdd_pp_1x, pc1_dmdd_pp_2x, pc2_tail_ratio, dsr_vs_S_1x, pc3_p_ni, pc5_share_years_positive, pc6_share_keep, verdict, pw_d, pw_d2, pc3_block`). FROZEN (rebuilt KOSPI / SPY lab series absent; `yf_SPY.csv` exists but the lab's SPY cells end 2021-03-31 and use the lab's own S construction).

| Cell | Period | Cost | PC-1 1x / 2x (pp) | PC-2 tail | PC-3 dSR | p non-inf | PC-5 | PC-6 | Verdict | GV | csv line |
|---|---|---|---|---|---|---|---|---|---|---|---|
| KOSPI VT20 | 1996-09-02..2026-09-29 | net KRX ETF 3bp | +6.5 / +6.4 | 0.70 | -0.001 | 0.051 | 0.70 | 1.00 | PASS | GV-303..310 | 5 |
| KOSPI multi-speed trend sleeve | same | 3bp | +8.9 / +8.4 | 0.77 | 0.186 | 0.008 | 0.60 | 0.75 | PASS | GV-311..318 | 3 |
| KOSPI unbounded trend x VT20 | same | 3bp | +11.3 / +9.4 | 0.55 | 0.231 | 0.007 | 0.57 | 0.88 | REVISE | GV-319..326 | 6 |
| KOSPI SMA200 | same | 3bp | +1.9 / -0.2 | 0.73 | 0.121 | 0.051 | 0.43 | 0.60 | INSUFFICIENT DATA (sufficiency) | GV-327..334 | 2 |
| KOSPI 12-month sign | same | 3bp | +4.7 / +4.6 | 0.88 | 0.082 | 0.083 | 0.63 | 0.20 | INSUFFICIENT DATA (sufficiency) | GV-335..342 | 4 |
| SPY VT15 at 50 bp | 1999-05-03..2021-03-31 | net US via KIS 50bp | +0.3 / -3.9 | 0.76 | -0.071 | 0.425 | 0.68 | 0.50 | REJECT | GV-343..350 | 12 |
| SPY trend sleeve at 50 bp | same | 50bp | -10.7 / -44.3 | 0.54 | -0.530 | 0.999 | 0.45 | 0.00 | REJECT | GV-351..358 | 10 |
| SPY trend x VT15 at 50 bp | same | 50bp | -7.9 / -43.9 | 0.47 | -0.541 | 0.998 | 0.50 | 0.00 | REJECT | GV-359..366 | 13 |
| SPY trend sleeve at 5 bp | same | net Futures 5bp | +14.7 / +13.2 | 0.54 | 0.012 | 0.257 | 0.59 | 0.62 | INSUFFICIENT DATA (inconclusive) | GV-367..374 | 17 |

Verdict strings to assert exactly: `PASS`, `REVISE`, `REJECT`, `INSUFFICIENT DATA (sufficiency)`, `INSUFFICIENT DATA (inconclusive)`.

**11.4 FS-1 floored trend x VT20 and comparison cells (R3:977-987; GV-375..419).** Source `LAB:results/r2_idx/r2_idx_overlay_vs_sleeve.csv` lines 12/11/13/2/3. KOSPI rebuilt 1996-09-02..2026-09-29, net 3 bp per side. FROZEN.

| Cell | avg exposure | max DD | PC-1 vs own S (pp) | PC-2 | dSR | years+ | verdict | 1997-98 | 2026 crash | GV |
|---|---|---|---|---|---|---|---|---|---|---|
| KOSPI ENSxVT overlay clip[0.5,1] (primary) | 0.61 | -29.39% | +15.4 | 0.64 | 0.156 | 0.63 | PASS | -28.62% | -9.78% | GV-375..383 |
| KOSPI ENSxVT sleeve (0 allowed) | 0.51 | -27.72% | +11.3 | 0.55 | 0.231 | 0.57 | REVISE | -9.68% | -9.78% | GV-384..392 |
| KOSPI ENSxVT overlay 0.5+0.5x (E3 long/half) | 0.68 | -36.19% | +13.0 | 0.65 | 0.115 | 0.67 | PASS | -30.84% | -11.02% | GV-393..401 |
| KOSPI ENS sleeve (0 allowed) | 0.58 | -34.15% | +8.9 | 0.77 | 0.186 | 0.60 | PASS | -6.89% | -31.30% | GV-402..410 |
| KOSPI ENS overlay clip[0.5,1] | 0.70 | -39.16% | +10.8 | 0.91 | 0.124 | 0.67 | REJECT | -39.16% | -31.30% | GV-411..419 |

Not evaluated: PC-6 plateau and start-date sweep of the floored product (GV-518, not traced); R3:987 "The first FORWARD-SIM release must add the plateau (PC-6) and the start-date sweep for the primary cell."

**11.5 Start-date sensitivity (R3:989-997; GV-420..434).** Source `r2_idx_start_date_sensitivity.csv`. FROZEN; assert verdict string + PC-1 pp.

| Start | KOSPI VT20 | KOSPI trend sleeve | KOSPI unbounded trend x VT20 | GV | lines |
|---|---|---|---|---|---|
| 1996-06-03 | PASS (+5.7) | REVISE (+11.0) | REVISE (+13.3) | GV-420..422 | 5/3/6 |
| 2001-01-02 | PASS (+10.6) | INSUFFICIENT DATA (inconclusive) (+6.1) | REVISE (+7.2) | GV-423..425 | 25/23/26 |
| 2006-01-02 | PASS (+11.6) | INSUFFICIENT DATA (inconclusive) (+5.7) | INSUFFICIENT DATA (inconclusive) (+7.3) | GV-426..428 | 30/28/31 |
| 2011-01-03 | INSUFFICIENT DATA (inconclusive) (+4.8) | REJECT (-3.5) | REJECT (-1.4) | GV-429..431 | 35/33/36 |
| 2016-01-04 | INSUFFICIENT DATA (inconclusive) (+4.4) | REJECT (-2.9) | REJECT (+0.9) | GV-432..434 | 40/38/41 |

**11.6 FS-3 Korean low-vol vs S_beta (R3:999-1005; GV-469..489).** `S_beta = beta_hat x market + (1 - beta_hat) x cash` (CR-01, R3:26). KRX 1996-2026, net 35, rf 0. Source `c12_lowvol_samebeta.csv` lines 2/6/10 — **ABSENT locally**; FROZEN from `r3_golden_values.csv` only.

| Comparison | beta | max DD book | max DD S_beta | dMDD pp | Sharpe book | Sharpe S_beta | tail ratio | GV |
|---|---|---|---|---|---|---|---|---|
| low-vol Q1 EW vs VW ALL | 0.631 | -73.87% | -51.50% | -22.4 | 0.412 | 0.357 | 0.985 | GV-469..475 |
| low-vol Q1 VW vs VW ALL | 0.742 | -64.88% | -57.76% | -7.1 | 0.331 | 0.357 | 0.978 | GV-476..482 |
| low-vol Q1 EW vs EW ALL | 0.702 | -73.87% | -61.64% | -12.2 | 0.412 | 0.244 | 0.967 | GV-483..489 |

Use: the negative control for any future stock-level CARD-P (PC-1 fails, PC-2 fails) — specification book only.

**11.7 MOM-1 (R-03 on KRX momentum) and MOM-2 (R3:1007-1032; GV-241..263).** Sources `r2_kr_crash_controls.csv`, `r2_kr_crash_windows.csv`, `r2_kr_crash_exposure_2026.csv`, `r2_kr_dm_gate_onsets.csv` (all local). FROZEN. Net-35 Sharpe, ALL quintiles: LS_EW static `0.20` / 2016-26 `-0.20` (GV-251/252); LS_EW VS (own vol, 12%, cap 1) `0.27` / `-0.24` (GV-253/254); LS_EW VS x DM `0.31` / `-0.28` (GV-255/256); LS_VW static `0.25` / `0.32` (GV-257/258); LS_VW VS `0.31` / `0.23` (GV-259/260); LS_VW VS x DM `0.37` / `0.25` (GV-261/262). Crash window 2026-06-22..07-30 net 35: 12-1 L/S VW static `-40.29%` (GV-241), own-vol scaled `-10.52%` (GV-242), static at same average exposure 0.53 `-22.95%` (GV-243); EW static `-24.77%` (GV-244), EW scaled `-12.55%` (GV-245); long-only EW excess scaled `-13.73%` (GV-246). R-03 weight on 2026-06-22: LS_EW `0.55`, LS_VW `0.27`, E5 top500 D10-D1 EW `0.35`, VW `0.20` (GV-247..250). D-M gate onsets on rebuilt KOSPI 1996-2026: `9` (GV-263; CA-27: 3 since 2000 — 2001-01-04, 2008-10-31, 2020-03-20 — on 4.1% of days; off on 2026-06-22).

**11.8 IDX-1 KOSPI VT20 reproduction of the macro spec's goldens (R3:1034-1062; GV-273..302).** Rebuilt KOSPI 2016-01-04..2026-09-29; source `r2_idx_golden_values.csv` (30 x 8: `item, ours, spec, gap, level1_tol, level2_tol, within_level1, within_level2`; level1_tol 0.01 for Sharpe). FROZEN; the comparison is against **v1.2** spec values.

| GV | Quantity | TF value | v1.2 spec | v2.0 post-patch (SPEC:5826, ^KS11 to 2026-10-02) |
|---|---|---|---|---|
| GV-273 | VT20 Sharpe gross | 0.6329 | 0.638 | **0.641** (gap 0.008, inside Level-1 ±0.01) |
| GV-274 | buy-and-hold Sharpe | 0.6284 | 0.634 | 0.637 (SPEC:5825) |
| GV-275 | VT20 max DD gross | -0.3700 | -0.368 | -36.8% |
| GV-276 | buy-and-hold max DD | -0.4405 | -0.439 | -43.9% |
| GV-277 | VT20 avg exposure | 0.9255 | 0.925 | 0.925 (SPEC:5773) |
| GV-278 | static S max DD | -0.4145 | -0.413 | -41.3% |
| GV-279 | dMDD VT20 vs S gross (pp) | 4.4581 | 4.5 | +4.5 |
| GV-280 | VT20 Sharpe net 3 bp | 0.6301 | 0.635 | 0.638 |
| GV-281 | VT20 Sharpe net 6 bp | 0.6274 | 0.632 | 0.635 |
| GV-282 | dMDD net 3 bp (pp) | 4.4281 | 4.4 | +4.4 |
| GV-283 | dSR VT20 − B&H gross | 0.0045 | 0.004 | +0.004 (SPEC:5772) |
| GV-300/301/302 | weight earning 2026-06-22 / 06-23 / 07-30 | 0.3025 / 0.3310 / 0.2485 | 0.3024 / 0.3309 / 0.2484 | 0.30 / 0.33 / 0.25 (SPEC:5775) |

Windows (VT20 / buy-and-hold; `r2_idx_golden_values.csv` 13-28): Jul-2026 crash -0.1224 / -0.3861 (GV-284/285); Mar-2026 -0.0791 / -0.1988; Aug-2024 -0.0788 / -0.0546; Apr-2025 -0.1167 / -0.1201; 2020 crash -0.2582 / -0.3405; 2020 rebound 0.2584 / 0.4980; H1-2026 0.5170 / 1.0108; 30 Jul-30 Sep 2026 0.0619 / 0.2282 (GV-298/299). Council's own fixture (`^KS11`, KRX official closes) is the v2 golden source (SPEC:5766-5775, G-KR-01..04); the TF rebuilt-KOSPI values are a second, independent reproduction. **Do not substitute one for the other in `tests/`.** Local ^KS11 absent from the cache; the Council manifest lists it (SPEC:6018).

**11.9 INV-5 name-level stops (R3:1064-1069; GV-509..516).** `r2_kr_stoploss.csv` lines 3/5/7/9 and 11/13/15/17. KRX top-500 12-1 deciles 2000-01..2026-09, net 35 Sharpe. EW: no stop `0.04`; 15% stop exit next close `-0.15`; 15% same close `-0.11`; 10% next close `-0.19`. VW: `0.28` / `0.07` / `0.08` / `0.01`. FROZEN; evidence for INVARIANT "no name-level stops" (CR-09).

**11.10 INV-1 / INV-2 execution invariants (R3:1071-1084; GV-171..174, 197..202).** `r2_kr_excl_limitlock.csv` lines 2-3: B1 none entries at locked limit-up close `6.30%`, exits at locked limit-down `2.06%`; B1 F4 `1.94%` / `1.39%`. `exec_verification_log.csv` lines 83-87, 22: locked limit-up next-open entry excess vs EW liquid universe t+5 / t+20 `-394 / -579 bp`, t `-14.6 / -11.2`, n `11,186`; overnight `+328 bp`; E7 pipeline reproduces `-98.4 bp` (GV-197); locked limit-down t+1/t+5/t+20 `-630 / -722 / -1,036 bp`, n `815` (GV-198); volume spike (>= 5x, r >= +5%) t+5/t+20 `-43 / -93 bp`, t `-4.9 / -6.5` (GV-199); 20-day run-up >= +50% t+20 `-95 bp` (median `-757`) (GV-200); KRX top-500 EW 12-1 D10-D1 overnight `+18.4%/yr (t 8.7)` vs intraday `-7.9%/yr (t -1.8)`; 2015-26 `+26.0%` vs `-21.9%` (GV-201); eligibility lagged one day benchmark `+0.5%/yr` (GV-202). FROZEN (verification-log text cells; assert as strings or parsed numbers).

**11.11 DATA-2, DATA-3, rebuilt-KOSPI check (R3:1086-1112; GV-203..209, 440..449, 463..468).** `r2_kr_mom_claims_long.csv`: Eom design adjusted all caps high-turnover W-L `+1.43 %/month`, NW t `3.26` (GV-203/204); unadjusted closes `-11.37`, t `-5.42` (GV-205/206); ex-bottom-20% caps `+1.66`, t `4.50` (GV-207/208) — KRX 2000-07..2019-06 gross. `kr_validation.csv` line 15: kept daily returns with |Close/prevClose−1 − r| > 0.5%: `12,186 of 13,949,140 = 0.0874%` (GV-209). `r2_idx_averaging_bias.csv`: SPY 1999-03..2021-03 SMA10 `+0.10`, TSM12 `+0.23`; S&P 500 2000-03..2018-12 SMA10 `+0.19`, TSM12 `+0.25` (GV-463..466; Sharpe inflation from month-average prices). `r2_idx_averaging_autocorr.csv` line 2: SPY monthly lag-1 autocorr `acf1_month_end 0.057`, `acf1_month_average 0.206` (GV-467/468) — **RECOMP(raw) candidates** from `CODE:docs/asset_expansion/cache/yf_SPY.csv` (1995..2026; adjusted close; the lab's exact convention — month-end vs month-average price, 1998-02..2021-03 — must be followed; treat as a reference check, not a golden). Rebuilt/official KOSPI change ratios (`kr_index_sanity.csv`, ABSENT): 2007-10-31..2020-03-19 `0.9999`; ..2021-07-06 `0.9987`; ..2026-06-22 `1.0006`; ..2026-07-30 `1.0010`; 2020-03-19..2021-07-06 `0.9989`; ..2026-06-22 `1.0007`; ..2026-07-30 `1.0011`; 2021-07-06..2026-06-22 `1.0019`; ..2026-07-30 `1.0023`; 2026-06-22..2026-07-30 `1.0004` (GV-440..449). FROZEN.

**11.12 DATA-5 regime flags (R3:1114-1126; GV-210..218).** Dates/rates to encode as effective-dated calendar/regime tags (fits SPEC R-20 regime tags) — FROZEN constants, sources `prof_verification_log.csv` 62/63/96, `exec_verification_log.csv` 19/25/79, chair-resolution md text:
- Short-sale ban regimes (GV-216): `1 Oct 2008-31 May 2009; 11 Aug-9 Nov 2011; 16 Mar 2020 (partial lift 3 May 2021); 6 Nov 2023-30 Mar 2025`. GV-217: `2020-03-16..2021-05-02 full, then index stocks only until 2023-11-05; full ban 2023-11-06..2025-03-30; resumed 2025-03-31`. GV-210: ban announced `2023-11-03` (first ban day `2023-11-06`); resumption `2025-03-31`; `NSDS, 105%, 90 days/12 months`.
- Sell tax (GV-211/213): `0.20%` on KOSPI (`0.05 + 0.15 rural`) and KOSDAQ from `2026-01-01`; `0.15%` in 2025; about `0.30%` in 2019; by year `0.18 / 0.15 / 0.20%` incl. rural special tax. (Feeds SPEC R-26 `tax_side`; SPEC:1727 cites the 0.20% sell tax.)
- KOSDAQ up-limit closes per 10,000 stock-days (GV-212): `51.1 (2026); 24.5 (2024); 26.8 (2025); KOSPI 27.5 (2026)`.
- Daily price limit widened to ±30%: `15 Jun 2015` (GV-214). KOSPI return on 2025-03-31: `-3.00%` (GV-215; CA-23). Value-up regime split: `2024-02-26` (GV-218).

**11.13 FS-2 constrained KRX momentum (R3:1128-1140; GV-264..272).** `r2_kr_mom_grid_long.csv` lines 1120/1123/2856/2859/1158/6144/6194/68/118, net 35: low-turnover 12-1 winners minus EW universe `+9.69%/yr`, NW t `2.77`; high-turnover winners `-11.57%/yr`, t `-4.18`; low-turnover 2015-07..2024-12 `-0.08%`; 12-7 L/S quintiles EW Sharpe `0.20` (full) / `-0.01` (2016-01..2026-09); 12-1 L/S EW `0.20` / `-0.20`. FROZEN.

**11.14 Index crash window 2026-06-22..07-30 (R3:1142-1150; GV-435..439).** `r2_idx_windows.csv` lines 3/83/103/23/43, rebuilt KOSPI, returns 2026-06-23..2026-07-30, net 3 bp: buy-and-hold `-38.61%` (CA-30; Council prints −38.6%, SPEC:1567, 6441); VT `-12.25%`; ENSxVT `-9.78%`; SMA200 `-37.86%`; ENS `-31.30%`. FROZEN.

**11.15 GOV-3 attribution, GOV-4/GOV-5 gate harness, GOV-7 break-even (R3:1152-1183).** `r2_kr_lowvol.csv` 14/38: low-vol Q1 EW beta `0.63`, CAPM alpha rf 0 `+2.23%`, alpha t `0.80`; VW `0.74`, `+0.73%`, `0.34` (GV-490..495; the "factor tilt" example for OQ-15). `us_C_factors.csv` 31: US Fama-MacBeth beta slope `+0.46%/yr` (28 portfolios, 1954-01..2017-03) (GV-496). `r2_idx_gate_sim.csv` (simulated; recipe/script not local → FROZEN): false-pass at true Sharpe 0, 10 years, 10-session blocks — kospi_cbb126 step2 `8.0%` (522), step8 `23.8%` (524); signflip step2 `5.0%`, step8 `31.2%`; iid_normal step2 `3.9%`, step8 `29.5%`; step-5 pass with NO edge (SR 0.4 = benchmark 0.4, rho 0.5, nominal 10%) `13.7%` (10y), `12.8%` (18y), `13.2%` (30y); joint steps 2+3+5+8 false pass `0.5%` (GV-456). `r2_idx_gate_power_years.csv` 337/363/389: years to 50% / 80% power at step 2 — true Sharpe 0.3 `28.7 / >50`; 0.4 `15.8 / 40.3`; 0.5 `10.5 / 25.7` (GV-460..462). GOV-7 break-even (status `derived`, RECOMP(csv) from `kr_key_numbers.csv` columns `ls_gross_ann / ls_turnover_yr` → bp per side, both legs): REV_1W EW `12.5`, VW `22.2`, REV_1M EW `29.6`, MOM_12_1 EW `63.7`, HIGH52 EW `56.4`, VOL_3M EW `137.2`, TURN_1M_LOW EW `141.8`, MAX_1M EW `61.2` (GV-189..196).

**11.16 R1 KRX engine regression (R3:1185-1202; GV-175..188).** `kr_key_numbers.csv` (36 x 21; columns `signal, universe, weighting, ls_gross_ann, ls_gross_sharpe, ls_gross_nw_t, ls_net35_sharpe, ls_net70_sharpe, lo_net35_ann, lo_net35_sharpe, lo_net35_maxdd, lo_xs_net35_ann, lo_xs_net35_t, lo_xs_net70_ann, excl_xs_net35_ann, excl_xs_net35_t, ls_turnover_yr, lo_turnover_yr, ls_pos_years, large_vw_ls_gross_sharpe, large_vw_lo_xs_net35_ann`). KRX 1996-03..2026-09: TURN_1M_LOW EW excl. highest-turnover quintile excess `+3.62%`, t `5.63`; VOL_3M EW excl. most volatile `+2.98%`, t `4.67`; MOM_12_1 EW L/S gross `+9.34%` (raw 0.093369), gross Sharpe `0.447`, net-35 Sharpe `0.201`, long-only top quintile excess `-1.34%`; REV_1W EW net-35 Sharpe `-1.782`, VW `-0.825`; REV_1M EW `-0.082`, VW `-0.450`; VOL_3M EW low-vol long-only excess `+1.08%`, VW `-1.78%`. FROZEN (these pin a rebuilt KRX engine; the raw panel is absent, so they can only be asserted against the CSV).

**11.17 DROP evidence and CRY-1 (R3:1204-1214; GV-503..508, 517).** `r2_kr_reversal.csv` 17/22/47/52/7/82, 1-month reversal losers minus winners %/month (NW t): ALL VW deciles gross `+0.57 (0.9)`, net35 `-0.68 (-1.1)`; ALL EW deciles gross `+1.43 (3.1)`, net35 `+0.23 (0.5)`; ALL VW quintiles net35 `-1.10 (-2.5)`; LARGE VW deciles net35 `-1.06 (-1.6)`. GV-517 (C3 KRW-BTC, QUANTGEN's own 2026-09-27 study): OOS Sharpe `1.22 [0.62, 1.77]` vs buy-and-hold `0.79`; p `0.04`; `1.17` at 2x; turnover `13.7x/yr` — **already a QUANTGEN result** (`CODE:docs/asset_expansion/results.md:181`, `ASSET_EXPANSION_SPEC.md:133`); RECOMP(raw) via the existing Strategy Lab harness on `upbit_KRW-BTC.csv`.

**11.18 Chair verification references (R3:1216-1225; GV-497..502).** Text cells from `prof_verification_log.csv` lines 3/92/48/112/113/116 (KR Fama-MacBeth slope `+1.1%/yr (t 0.19)`; chair lottery composite `+0.236 (t 7.65)` from 2001, `+0.248 (t 8.02)` from 1996; KR-ISS net35 IR `0.48-0.54`; R2 lottery EW `+3.08%/yr` IR 1.53 bootstrap p 0.0005; issuance B1 `+2.34%/yr`; reversal VW ex-microcap). FROZEN strings.

**11.19 Not traced (R3:1227-1236; GV-518..523).** Cannot be asserted: GV-518 (FS-1 plateau/start sweep), GV-519 (FS-4, no lab test), GV-520 (C3 controls: vol-scaled long-only, 2024-01-10 split, ETH; no local crypto data in the lab — but QUANTGEN's cache has `upbit_KRW-BTC.csv`, `binance_BTCUSDT.csv`, `binance_ETHUSDT.csv`, so the controls are buildable in QUANTGEN), GV-521/522 (E5 sigma ladder KOSPI VT20 Sharpe 0.40, MDD -37.4%, 1 halt; SPY cumulative vs non-cumulative 0.41 → 0.02; scripts not saved), GV-523 (0.6 × 3.08% = 1.85%/yr is arithmetic: assert the formula `expected_live = 0.6 * oos`, not the value as a lab output).

---

## B. Corrected anchors CA-01..CA-38 (R3:1240-1281): what must not propagate, and where it is carried

Repo grep (README.md, docs/, core/, ui/, tests/) for every anchor number: **no QUANTGEN code or doc carries any of the 38 wrong numbers.** Coincidental hits only: `0.84` = card E1 OOS Sharpe / KRX DSR (`docs/asset_expansion/results.md:9-10,49,66`, `docs/ASSET_EXPANSION_SPEC.md:137`), `-49%` = KRW-BTC drawdown (`docs/ASSET_EXPANSION_SPEC.md:133`), `2.95` = option IV gap (`docs/asset_expansion/results.md:41,474`), `2.93%` = TIPS yield (SPEC:6343). The carriers are the **Council v2.0 spec and reports** (inputs to this build), listed below.

| ID | Wrong number (where it circulated) | Correct value / reading (R3 line) | Carried in v2.0 inputs? |
|---|---|---|---|
| CA-01 | Korean 1-month reversal "-2.95%/month (t -3.77)" as a spread | Fama-MacBeth slope on r(-1), Jan-1999..Feb-2021: about -0.30% next month per +10% last month. Spreads: EW quintiles 0.52%/month gross (2001-26), 0.08% (2020-26), negative net; KRX EW deciles 1999-2021 +1.41% gross, +0.20% net 35; VW ex-microcap deciles 1996-04..2026-09 +0.57% gross (t 0.9), -0.68% net 35 (R3:1244) | SPEC:684, SPEC:1727 already label −2.950 "a regression slope, not a strategy return"; backlog :1121, :1647 same. **Already corrected.** |
| CA-02 | Korean momentum "-6.13%/month in high-turnover stocks" | Not reproduced: +1.43%/month (t 3.26) all caps, +1.66% (t 4.50) ex-bottom-20% (KRX 2000-07..2019-06, adjusted); sign appears only with unadjusted closes (-11.37%, t -5.42); long-only high-turnover winners lag -11.57%/yr (t -4.18) (R3:1245) | none |
| CA-03 | KR-ISS long-only net IR 0.84 (P3) | 0.48-0.54 full sample net 35; 0.35-0.38 in 2017-26; about 0 at 70 bp (R3:1246) | none |
| CA-04 | Ilmanen per-factor OOS haircuts value -49%, momentum -23%, multifactor -18% (macro R-15, §7 `prior_haircuts`, §13 N-60) | Only a 30% average OOS drop is verifiable; use planning haircuts 0.5 / 0.3 / 0.75 and measured local decay (GOV-8) (R3:1247) | **YES:** SPEC:703, SPEC:1738, SPEC:4329 `prior_haircuts: {value: 0.49, momentum: 0.23, carry: 0.25, defensive: 0.0, multifactor: 0.18}`, SPEC:6440 ("priors use the factor-specific figures"); macro report :170 → XS-05 |
| CA-05 | Average anomaly "8 bp/month net" | 4 bp/month (204 anomalies; Chen-Velikov 2023) (R3:1248) | none |
| CA-06 | Step-8 false pass "36-38% at 8-10 years" (P4) | 23.8% (KOSPI bootstrap), 29.5% (iid), 31.2% (sign-flip) at true Sharpe 0, 10 years; joint 2+3+5+8 0.5% (R3:1249) | none (v2.0 has its own G-PWR-02, SPEC:5973) |
| CA-07 | "18 OOS years for Sharpe 0.4" (P1); "IR 0.3 needs 18 years" (E4) | 50%-power horizon: Sharpe 0.4 → 15.8 y (50%), 40.3 y (80%) at step 2; step 5 about 50 y for 80% (R3:1250) | none |
| CA-08 | Jeon-Byun "max drawdown -23.7% vs -74.1%" | Worst monthly returns, not drawdowns (R3:1251) | none |
| CA-09 | P4 "SE 0.188" (Sharpe 1.5, 60 months) | Annualised SE about 0.47 (R3:1252) | none |
| CA-10 | Volume-filtered weekly reversal 0.44%/week (P2), 0.03%/week (P6) | -0.05 to +0.31%/week gross (2001-26); 0.14-0.26 top-500; always negative net (-0.92 to -1.33%/week net 35) (R3:1253) | none |
| CA-11 | Corwin-Schultz KRX spreads 39-79 bp | 22-57 bp (cap buckets) or 99-117 bp (negatives zeroed), Jan-2024..Sep-2026; not a calibration source (R3:1254) | none |
| CA-12 | "Samsung + SK hynix = 55.5% of KOSPI" (undated; macro R-07) and "22% at end-2023" | Always date + denominator. CR-07: 53.71% (2026-09-29), 59.69% peak (2026-06-25), 29.29% (2023-12-28); 2026-09-29 alternatives 50.82% / 52.59% / 53.96%; end-2023 26.88% / 27.79%, not 22%; MSCI Korea free float Aug-2026 60.8% (R3:1255) | **YES:** SPEC:1588 "The pair was 55.5% of KOSPI market cap (22% at end-2023)"; SPEC:6310 "55.5% reported in 2026"; SPEC:6407 "Pair 55.5% of KOSPI"; macro report :49 → XS-06 |
| CA-13 | Korea 52-week high "+0.34%/month net (t 2.31)" | +0.33% (t 2.14) from 2001-03; +0.13% (t 0.81) from 1996-03; state the start (R3:1256) | none |
| CA-14 | Korea 12-7 momentum "net-35 Sharpe 0.54" | 0.60 (deciles, from 2001); 0.19-0.20 from 1996; -0.01 in 2016-26; negative at 70 bp after 2010 (R3:1257) | none |
| CA-15 | CAPE 1-year OOS R2 "-2.4% (1950-) / -11.1% (1990-)" | -4.8% / -16.5% (prof chair), -4% / -18% (US lab); all negative (R3:1258) | none |
| CA-16 | P6 VW low-risk tilt "-20.3 points in 2025" | Single-signal VW top quintiles lost 35-40 points in 2025 (R3:1259) | none |
| CA-17 | "US 12-1 momentum Sharpe 0.02 since 2008" | -0.16 for 2008..2017-03 (French WML; local file ends 2017-03); not verifiable to 2026 (R3:1260) | **YES:** SPEC:684 "US 12-1 SR 0.33 since 1990, 0.02 since 2008" |
| CA-18 | "ChatGPT strategy unprofitable at 20 bp" | 20 bp round trip (10 bp per side) (R3:1261) | none |
| CA-19 | "Trend following 2010-18: 0.4%/yr" | Excess over T-bills (AQR 2019); total return 1.6%/yr (R3:1262) | none |
| CA-20 | Dynamic momentum "roughly quadruples" Sharpe | "Approximately doubles": JFE Table 7 0.682 → 1.041 → 1.194; static WML 0.71 (R3:1263) | SPEC:6405, SPEC:6439 carry the correct 0.682 → 1.041 → 1.194. **Already corrected.** |
| CA-21 | Step 9 as "x 0.4" (R2 KR gate column g9 = 0.4 x diff, B1/F4 +1.23%/yr) | Expected live Sharpe = 0.6 x OOS ("take 40% off"); B1/F4 0.6 x 3.08% = +1.85%/yr (R3:1264) | v2.0 consistent: `live_sharpe_multiplier: 0.60` (SPEC:476, 2579, 2608, 4596, 4768); `CODE:core/quant/validate.py:57` `"haircut": 0.6`. **Wrong value lives only in `LAB:results/r2_kr/r2_kr_excl_gate.csv` column `g9_haircut_ann_diff`/`g9_haircut_ir`.** |
| CA-22 | KOSPI 24-month return "+235%" on 2026-06-22 | +227% (daily) / +222% (month-end) (R3:1265) | none |
| CA-23 | KOSPI on 2025-03-31 "-2.93%" | -3.00% (R3:1266; GV-215) | none |
| CA-24 | MTUM IT weight "54.3%" (2026-06-30 factsheet) | 53.22%; 54.3% is the 2026-09-29 page (R3:1267) | none |
| CA-25 | Korean top-500 12-1 WML Sharpe 0.43 EW (E5) | EW 0.26-0.30 gross / 0.04-0.07 net 35 (deciles, 2000-26); VW 0.44-0.48 / 0.28-0.30; 2016-26 EW net -0.13, VW 0.30 (0.02 with 5% cap); July 2026 -30.0% EW / -29.8% VW (R3:1268) | none |
| CA-26 | Bounding trend to [0.5, 1] "keeps about half the protection" | PC-1 vs own S rises +11.3 → +13.0 / +15.4 pp; absolute max DD -27.7% → -36.2% / -29.4% (R3:1269; section 11.4) | none |
| CA-27 | D-M gate protects Korean momentum crashes | 3 onsets since 2000 (2001-01-04, 2008-10-31, 2020-03-20), 4.1% of days; 9 onsets 1996-2026; off on 2026-06-22 (R3:1270) | SPEC:1541 "Untested on KRX stock data" — consistent |
| CA-28 | Insider buys "82 bp/month" as a long-only 126-day overlay | Long-short, one-month hold, five-factor alpha 82 bp VW (t 2.15) / 180 bp EW (t 6.07), 1986-2007 (R3:1271) | none |
| CA-29 | GS high-beta momentum basket "-37% in July 2026" | Unverified; only "worst month since November 2000" verifiable (R3:1272) | none |
| CA-30 | KOSPI crash 2026-06-22..07-30 "-38.0%" | -38.61% (R3:1273; GV-435) | v2.0 prints −38.6% (SPEC:1567, 6407, 6441) — consistent |
| CA-31 | Korean low-turnover momentum long-only excess "+2.9%" | +2.9% (E7 universe, 2015-24); -0.1% (ALL, 2015-24); +9.69%/yr (t 2.77; ALL 1996-2026 net 35) (R3:1274) | none |
| CA-32 | "Korean low volatility is a crash hedge" | Beta 0.63 (EW) / 0.74 (VW); vs S_beta max DD worse by 7.1-22.4 pp, tail ratio 0.97-0.99 (R3:1275) | none |
| CA-33 | KOSPI trend protection as a full-sample property | Concentrated in 1997-2001: multi-speed sleeve REJECT from 2011/2016 starts (PC-1 -3.5 / -2.9 pp); VT20 alone PASS from every start 1996-2006 (+4.4 to +11.6 pp) (R3:1276) | SPEC:1703-1705 KOSPI trend context only — consistent |
| CA-34 | Nominal sizes of steps 2 and 5 with 10-session blocks | Step 2 false pass 6.9-8.0% (nominal 5%); step 5 12.8-13.7% (nominal 10%) (R3:1277) | none; `CODE:core/quant/validate.py:54` still `"block": 10` (XS-11) |
| CA-35 | Vol-scaled sizing "+0.1 to +0.3 Sharpe on nearly every strategy" | Robust only for momentum: Korean reversal EW net -0.29 → -0.59 scaled; KOSPI VT20 long-only 0.38 vs S 0.40 (R3:1278) | SPEC:700 already "MODIFY — Robust only for momentum". **Already corrected.** |
| CA-36 | AQMIX as evidence of a 1.2-Sharpe trend book | 10-year 5.44% vs T-bills 2.42%, vol 9.96%: Sharpe about 0.30 (R3:1279) | none |
| CA-37 | KRX limit-up event return "-308 bp" (chair first pass) | Chair's benchmark error; E7's -394 / -579 bp stand (R3:1280; GV-197) | none |
| CA-38 | US single-index trend weight 3 (prior; macro R-14) | At 50 bp all multi-speed cells REJECT (PC-1 -10.7 pp); at 5 bp INSUFFICIENT DATA (+14.7 pp, 53-56% of the benefit from the GFC) (R3:1281) | **YES:** SPEC:699 "US 3 (keep)", SPEC:1724 R-15 US TS trend `3` → XS-09 |

Action: a `docs/` corrected-anchors register (or a test that greps `docs/` and `core/` for the strings `55.5%`, `22% at end-2023`, `-6.13`, `0.4 x diff`) keeps them out of QUANTGEN; the Council-spec carriers are flagged to the owner under XS-04/05/06/09.

---

## C. Cross-spec amendments XS-01..XS-22 (R3:1283-1310) against Council v2.0

Types (R3:1285): Supersession, Correction, Proposal, Tightening, Clarification, Information, Conflict. Status key: **ADOPTED** = v2.0 already contains the substance; **CONFLICT** = v2.0 states the opposite or a different rule; **OPEN** = v2.0 silent. Exposure note = effect on any book if the amendment were applied as written (conservative default: none).

| ID | Macro target (v1.2) | Amendment (R3) | Type | v2.0 status and line evidence | Exposure |
|---|---|---|---|---|---|
| XS-01 | §2.2 KEEP Korea flow 3; R-15 flow prior | Korea investor flow 3 → 1; log final investor-type flows with timestamps now (DATA-6); no direction rule; t-1 history before an open-leg test; foreigners sold KRW148.3tn net in H1-2026 while KOSPI rose about 101% (R3:1289) | Supersession | **CONFLICT (prior) / ADOPTED (rest).** SPEC:1718 "flow takes §2.2's prior where one exists (Korea 3)"; SPEC:698 "Flow weight stays, but with no flow-conditioned multiplier"; SPEC:6141-6143 DNB item 14 bans flow as a direction signal; SPEC:1412 investor flows logged "C (log from day one; backlog BL-C06)". Integer stays 3. | None: in v2.0 the integer is an admissibility filter (SPEC:1717) and no flow sleeve exists. Ambiguity A-8. |
| XS-02 | R-15 Korea ST reversal 3; §2.2 "Korea keeps 1-5-day reversal" | 3 → 0 for daily/weekly; monthly reversal only as a conditioning guard of weight 1 (FS-5); net-of-cost test fails (weekly L/S net-35 Sharpe -1.78, break-even 12.5 bp; 1-month VW ex-microcap -0.68%/month net 35); delete the 1-5-day sentence (R3:1290) | Supersession | **CONFLICT.** v2.0 moved the prior 3 → **1 (UNVERIFIED)** "until BL-U02 runs net of 35 bp plus the 0.20% sell tax" (SPEC:698, 1727); R-05 keeps the family at 1.0x with its own net-of-cost card pending (SPEC:1552). v2.0 treats the test as not yet run; TF treats it as run and failed (price returns, no tax: tax makes it worse). The "1-5-day" sentence is absent from v2.0 (grep: no hit). | None: prior 1 vs 0 changes admissibility of a reversal family only if a Korea reversal sleeve is registered; none exists. Owner confirms 1 → 0. |
| XS-03 | §2.2 volume-spike reversal "KEEP as signal spec; UNTESTED" | DROP: volume-filtered weekly reversal -0.05 to +0.31%/week gross, -0.92 to -1.33%/week net 35; volume-spike buying -43 / -93 bp at t+5 / t+20 (R3:1291) | Proposal | **OPEN.** SPEC:701 still "KEEP as signal spec; UNTESTED — Not evaluated by either panel". | None (never built). Conservative: do not build; record TF evidence in the backlog row. |
| XS-04 | R-05 reversal and quality at 1.0x; reversal card must clear 35 bp and stay positive at 70 bp | Record that reversal fails its own test; 1.0x stays for a future sleeve on a venue ≤ 5 bp (DC-E2-09); vol scaling hurts reversal (KR STR EW net -0.29 → -0.59) (R3:1292) | Information | **OPEN.** R-05 unchanged (SPEC:1548 "Unchanged"; SPEC:1552 requirement text intact, no failure recorded). Vol-scaling point consistent with SPEC:700. | None. |
| XS-05 | R-15 prior calibration; §7 YAML `prior_haircuts`; §13 N-60 | Replace per-factor Ilmanen haircuts with one per stage: planning 0.5 in sample, 0.3 post-publication, 0.75 drift-like, replaced by measured local decay where 20+ years exist (GOV-8); withdraw N-60 (R3:1293; CA-04) | Correction | **CONFLICT.** v2.0 retains them: SPEC:703, 1738 ("value −49%, momentum −23% (not significant), carry ≈ −25%, defensive no decline, multifactor −18%"), SPEC:4329 `prior_haircuts: {value: 0.49, momentum: 0.23, carry: 0.25, defensive: 0.0, multifactor: 0.18}`, SPEC:6440 "priors use the factor-specific figures" while conceding the ≈ 30% average. | None in v2.0 (haircuts only shape 0-3 priors = admissibility/display). Owner decides; fail closed = keep v2.0 key, add TF stage haircuts as printed lines. |
| XS-06 | R-07 evidence text "55.5% of KOSPI (22% at end-2023)" | Dated, denominated values: 53.71% on 2026-09-29 and 29.29% on 2023-12-28 under CR-07; end-2023 alternatives 26.88% / 27.79%, not 22% (R3:1294) | Correction | **CONFLICT (text not corrected).** SPEC:1588 still carries "55.5% of KOSPI market cap (22% at end-2023)"; v2.0 adds its own dated anchors: "On 2 Oct 2026 ≈ 51% (51.2% Sedaily anchor, 53.6% on the 25-Oct-2024 KRX-weight anchor; re-anchor monthly to an official KRX figure), ≈ 54% of KODEX 200 on look-through (53.8%)" (SPEC:1588, 6310). 53.6% ≈ CR-07's 53.71%; "22%" is wrong under every definition. | None (evidence text). |
| XS-07 | R-07 pair-share denominator (undefined) | CR-07: (005930 + 005935 + 000660) over all KOSPI lines; 53.71% on 2026-09-29; first > 0.45 on 2026-05-06 (0.4702); 99/181 sessions > 0.45; peak 59.69% on 2026-06-25; alternatives 50.82 / 52.59 / 53.96% (R3:1295; section 11.1) | Proposal | **OPEN.** v2.0 defines no KOSPI-share formula; `macro_state` carries `pair_share_kospi` and `pair_lookthrough_share` (SPEC:3595; example 0.51 / 0.538 SPEC:3683) and says "re-anchor monthly to an official KRX figure" (SPEC:1588). The acting caps use **look-through of the ETF basket** (SPEC:1585 (1)-(5)), and the 0.45 trigger is removed ("without v1.2's 0.45 trigger", SPEC:1585). | None: under v2.0 the KOSPI pair share is a reported field. Conservative: compute `pair_share_kospi` per CR-07 (all four definitions printed) as display; never a trigger. |
| XS-08 | R-07 ladder open points (cumulative steps; re-arm reference) | Steps non-cumulative; total book NAV only; re-arm at 0.5 with the reference peak reset (never the all-time HWM); thresholds unchanged. Evidence KOSPI CW 2000-26 net 35: Sharpe 0.42 → 0.40, max DD -55.8% → -41.3%, 0.69 halts/yr; all-time-peak reference 22.8 halts/yr, Sharpe -1.65; per-sleeve ladder on VW WML 0.38 → 0.16 (R3:1296) | Proposal | **ADOPTED.** SPEC:92 "non-cumulative steps … explicit re-arm, steps time-boxed at 21 sessions"; SPEC:1586 hard stop −15% of book NAV from the HWM since the last re-arm, re-arm refused 10 sessions then automatic, references reset to NAV at re-arm, `post_rearm_cap = 0.5` in `min()` for 10 sessions; SPEC:1587 / 3316 `steps: [{dd: -0.08, mult: 0.5}, {dd: -0.12, mult: 0.5, evaluator_block_new_entries: true}]   # totals, non-cumulative`; SPEC:3277 "Levels are in % of whole-book NAV"; SPEC:4349-4351 `hard_stop: {level: -0.15, alt: "-1.5*sigma_book", reference: hwm_since_last_rearm, … rearm_refused_sessions: 10, … rearm_resets: [hwm_hard, ref_step], post_rearm_cap: 0.5, post_rearm_sessions: 10}`; SPEC:2671 sleeve NAV never the denominator. v2.0 goes further (21-session time-box, R-31 CARD-P). | None beyond v2.0. Evidence sign differs between labs (Ambiguity A-2); v2.0's own fixture numbers govern (T-RLAYER-01, SPEC:2405). |
| XS-09 | R-14 TS trend sleeve (CARD-O; 12-1 sign monthly; US weight 3) | Add a CARD-P cell (single-index trend judged PC-1..PC-7 vs S; never CARD-O) and a speed cell (KOSPI 3 bp: 12-month sign PC-1 +4.7 pp INSUFFICIENT vs multi-speed +8.9 pp PASS); US single-index trend protective 0 at 50 bp (REJECT, PC-1 -10.7 pp), 1 at futures cost (BACKLOG) (R3:1297) | Proposal | **ADOPTED (CARD-P cell) / CONFLICT (KOSPI and weight).** CARD-P cell exists as **R-28** "Trend-axis protective card (US and non-Korean sleeves): monthly SMA10m, 0.5× below trend, FORWARD-SIM · CARD-P" (SPEC:2964-2975), claim "protection only" (SPEC:2970); R-14 stays CARD-O diversification (SPEC:1702). Speed cell: not adopted (SMA10m fixed). KOSPI: "A KOSPI trend card that acts" is DNB item 37 (SPEC:6224-6226); an R-28 instance with `market: KR` is refused by rules-store validation (SPEC:6248, T-DNB-01); KOSPI trend state CONTEXT-ONLY (SPEC:1705, 6259). US TS trend prior `3` kept (SPEC:699, 1724). | TF FS-1 (KOSPI floored trend × VT20, FORWARD-SIM) cannot be an R-28 instance; if built it must be a separate FORWARD-SIM rule id and never reach the recommended book (both programmes agree it never acts). |
| XS-10 | R-03 scope | R-03 applies to every momentum sleeve in every market, KRX stock sleeves included, as a risk control, not a return claim; on KRX it lowered 2016-26 Sharpe (EW L/S -0.20 → -0.24; VW 0.32 → 0.23) (R3:1298) | Clarification | **ADOPTED (scope) / CONFLICT (claim type).** SPEC:1515 "Size every cross-sectional momentum sleeve by its own risk"; SPEC:1517 long-only sleeves: vs on the long-only active budget, computed on the paper unit-gross L/S series; formula SPEC:1518 `vs = min(1.0, 0.12 / σ126(t))`. But v2.0 R-03 is **CARD-O (indicative PASS on French data; step 3 borderline)** (SPEC:1510), i.e. an outperformance claim. | None. KRX values (section 11.7) are the negative-control line for the KRX sleeve's own card. |
| XS-11 | §8.5 blocks (macro cards) vs §8.1 step 2 (10-session blocks) | max(10, Politis-White on d and d²) for steps 2 and 5 on every card; 10-session blocks gave false passes 8.0% at nominal 5% (step 2) and 13.7% at nominal 10% (step 5) (R3:1299) | Tightening | **ADOPTED, superseded by a stricter rule (formula CONFLICT).** R-24: steps 2, 5 and PC-3 use a Ledoit–Wolf studentized circular-block bootstrap with block = Politis–White on the influence function ψ of ΔSR, **floor 21** (SPEC:2564-2570, 4761); `block: {rule: politis_white_on_influence_function, floor_sessions: 21, pc3_also_block_10: true}` (SPEC:2598); "v1.2 computed Politis–White on dₜ and dₜ². That rule is withdrawn" (SPEC:4991). v1.2-check mode keeps `max(10, PW(d), PW(d²))` for reproduction only (SPEC:5987). Current code: `CODE:core/quant/validate.py:54` `"block": 10`, `:106-142` 10-session circular block bootstrap. | None (governance). Build R-24's rule; keep the TF false-pass rates (GV-450..459) as a calibration fixture only. |
| XS-12 | §8.7 CARD-P comparator ("applies only to rules whose output never exceeds 1.0") | Add S_beta = beta_hat x market + (1 - beta_hat) x cash, beta_hat pre-registered, as the CARD-P comparator for stock-level sleeves (window: OQ-03) (R3:1300) | Proposal | **OPEN.** SPEC:5185 sentence present verbatim; comparator S defined only as x_S = m̄ · x_off (SPEC:2143, 5187); no `S_beta`/`beta_hat` anywhere in v2.0. | None (no stock-level CARD-P exists in v2.0). Conservative: specify S_beta in the gate package only when a stock-level protective card is registered (GOV-11). |
| XS-13 | §8.1 step-9 wording; context brief "60% live haircut" | One wording: expected live Sharpe = 0.6 x OOS ("take 40% off"); fix harness prints using 0.4 x (R3:1301; CA-21) | Correction | **ADOPTED.** `live_sharpe_multiplier: 0.60` "take 40% off" (SPEC:476, 2579, 2608, 4596, 4768); `CODE:core/quant/validate.py:57` `"haircut": 0.6`. The 0.4× print is in the TF lab only (`r2_kr_excl_gate.csv` g9 columns). | None. |
| XS-14 | R-08 market stress gauges | Do not count R-08 as factor-crash protection: VIX was 12.9-25.8 at 19 factor-crash onsets (R3:1302) | Information | **ADOPTED in effect.** R-08 demoted to CONVENTION, "REJECT as a CARD-P" (SPEC:1592), "No book's weights change" (SPEC:1601), PC-1/PC-2 fail 10 of 10 cells (SPEC:1603). The factor-crash statistic itself is not in v2.0. | None. |
| XS-15 | R-04 Daniel-Moskowitz gate scope | Specification book only; no extension to earnings-momentum or revision sleeves; KOSPI 9 onsets 1996-2026, off on 2026-06-22 (R3:1303) | Information | **ADOPTED.** "SPECIFICATION BOOK ONLY" (SPEC:1528, 1534); recommended-book builder refuses it (I-03, SPEC:1542); DNB item 22 (SPEC:6165); "Untested on KRX stock data" (SPEC:1541). Extension to other sleeves not mentioned (conservative: none). | None. |
| XS-16 | R-15 US XS momentum "2 if vol-scaled + D-M, else 1" | Final weight 1 (professors 1, executives 2, rule W3; no US stock sleeve at 50 bp; French WML Sharpe -0.16 in 2008..2017-03) (R3:1304) | Conflict (OQ-06) | **CONFLICT.** SPEC:694, 1724 keep "2 if vol-scaled with the D&M gate, else 1". | None: 1 and 2 are both admissible (SPEC:1713); R-04 is spec-book only so the "2" condition cannot hold in the recommended book; base weight identical. Display integer only. |
| XS-17 | R-15 crypto ST reversal 2 | 2 → 0 (short-horizon crypto evidence is momentum) (R3:1305; CR-10) | Supersession | **CONFLICT.** SPEC:1732 Crypto ST reversal `2 (prior)`. | Prior 2 keeps a crypto reversal family admissible (NOT_RUN stays admissible, SPEC:1718); no such sleeve exists (C3 is trend). Conservative: register none until the owner rules. |
| XS-18 | R-15 Korea 12-7 / residual momentum 1 (UNVERIFIED) | Replace with FS-2 constrained momentum (weight 1, FORWARD-SIM: Q5 12-1 or 12-7 excluding lottery/highest-turnover names, R-03, 5% cap, long-only); 12-7 L/S EW net-35 Sharpe 0.20 / -0.01 (2016-26); residual untested (R3:1306) | Supersession | **OPEN.** SPEC:697, 1727 "12-1: 0; 12-7 / residual: 1 (UNVERIFIED)"; no FS-2 or screen-constrained card in v2.0. | None: FORWARD-SIM never reaches the recommended book in either programme. |
| XS-19 | §10 DO-NOT-BUILD (items 1-26) | Add DNB-TF-01..17 (R3 §6). Overlaps: DNB-TF-06 = item 14 (flow direction); DNB-TF-11 = item 26 ("value timing presented as compliant"); DNB-TF-14/15 extend item 11; clarify item 13: the aggregate issuance-timing ban does not cover the firm-level dilution screen SCR-2 (R3:1307) | Proposal | **OPEN, with one mis-mapping (CONFLICT).** v2.0 §10 has 37 items (SPEC:6072-6227), none from TF. Item 14 (SPEC:6141-6143) = flow direction: overlap correct. Item 11 split into 11a/11b/11c (SPEC:6118-6129). Item 13 (SPEC:6137) "aggregate issuance or IPO-window multipliers, buyback-blackout multipliers, Korean issuance volume as sentiment" — silent on firm-level SCR-2 (clarification still needed). **Item 26 (SPEC:6182) is "Value-timing golden values presented as compliant" = publication-lag (value-date) timing of H.10/H.15 series, NOT valuation timing (CAPE); DNB-TF-11 (valuation timing CONTEXT, CR-12) matches no v2.0 item.** Enforcement rows are per-item predicates (SPEC:6229-6252): DNB-TF entries need either a predicate row or the "design prohibition" class. | None. |
| XS-20 | R-06 Korea card evidence (indicative INSUFFICIENT DATA on the 2016-26 card) | R2: PASS on 1996-09..2026-09 (PC-1 +6.5 pp, tail 0.70) and from every start 1996-2006; INSUFFICIENT from 2011/2016; 2016-26 goldens reproduce; owner declares the judged history (OQ-07) (R3:1308) | Information | **ADOPTED (v2.0 judges the long history).** R-06 KR "BUILD-AS-INSURANCE (Korea, on a formal PASS)" (SPEC:1554); definitive cell 1997-04-01 → 2026-10-02, KRX ETF 3 bp: ΔMDD +12.7 pp, tail ratio 0.68, p_ni 0.052, indicative PASS; 2016-26 INSUFFICIENT; 2016-25 REJECT (SPEC:1569); PASS requires (i) full span, (ii) ETF-era line from Oct-2002 listing to 2025-12, (iii) no REJECT at any of 32 monthly starts 1997-05..1999-12 with 3·n_pass ≥ 2·n_starts, (iv) no REJECT in either calendar-midpoint half (SPEC:1574); `gate.evaluation.history_start` 1997-04-01. | None. Series differ (TF rebuilt KOSPI from 1996-09-02 vs ^KS11/official from 1997-04-01); TF PC-1 +6.5 pp vs Council ΔMDD +12.7 pp are not interchangeable goldens (Ambiguity A-1). |
| XS-21 | R-15 0-3 normalisation into base_weight (open point) | base_weight = w / 3 (3 = 1.0x; never above 1.0); one-sided (*) cells cannot feed any book until a card passes (R3:1309) | Proposal | **CONFLICT (superseded by v2.0's own rule).** `base_weight(m, f) = IV_m × 1/K_m` over admissible families (prior ≥ 1 and card not REJECT) (SPEC:95, 861, 1712-1715; T-PRIOR-01 SPEC:5648); the integers are "admissibility filters and display scores only" (SPEC:1717); "A family whose card is NOT_RUN stays admissible" (SPEC:1718) vs TF "cannot feed any book until a card passes"; tilts only after a PASS (SPEC:1719). Both bound every weight ≤ 1.0. | None if v2.0's rule is built; the TF one-sided clause is stricter and can be honoured by giving one-sided (*) families prior 0 until their card passes (owner decision). |
| XS-22 | R-07 caps: 0.05 single name vs 0.35 pair (open point) | By book type: 0.05 single name in selection sleeves (VW legs capped at 5% of leg); 0.35 pair cap on look-through for market/ETF books when the pair share exceeds 0.45; semis ≤ 0.50. Pair cap on KOSPI CW cost -15.0 pp in the H1-2026 melt-up, saved +4.6 pp in the crash, -2.2 pp 2026 YTD (R3:1310) | Proposal | **CONFLICT (part ADOPTED).** v2.0 R-07 (SPEC:1585): (2) **active** single-name cap `w_i − g·b̃_i ≤ 0.05 of NAV` (an absolute 0.05 "cannot be met at all" on an ETF book, SPEC:1588); (3) default template **MSCI 25/50** (owner decision D1), alternative (c) "a 35% pair cap (Samsung + SK hynix ≤ 35% of the Korea long book), **without v1.2's 0.45 trigger**"; (5) semiconductor cap ≤ 0.50 of Korea sleeve NAV on look-through (ADOPTED); acceptance T-CAPS-01, I-04, I-04b (SPEC:1582). The 0.45 trigger "was set inside the regime it targets" (SPEC:1588). | Changes exposure if applied (pair cap binds); keep v2.0 default (D1) and the active cap; TF's 0.35/0.45 variant only as alternative (c) on owner ruling. |

Summary: ADOPTED 6 (XS-08, 11 [stricter formula], 13, 14, 15, 20); PART adopted / part conflict 2 (XS-09, XS-10); CONFLICT 8 (XS-01, 02, 05, 06, 16, 17, 21, 22); OPEN 6 (XS-03, 04, 07, 12, 18, 19). None of the 22 changes exposure in v2.0 as it stands; XS-22's pair cap would if adopted as written.

---

## D. Open questions for the owner (R3:1312-1328) and gaps (R3:1330-1344)

| OQ | Question (R3) | What v2.0 already fixes | Conservative default |
|---|---|---|---|
| OQ-01 | Ladder threshold units (CR-07): fixed -8 / -12 / -15%, book-vol units (-1.0 / -1.5 / -1.9 sigma), or a book-vol ceiling of 8% where they coincide; Brownian check at Sharpe 0.5: P(-15% within 10 y) = 0.97 at 12% book vol, 0.66 at 8%; E5 sigma ladder not re-run. Suggested: FORWARD-SIM both (R3:1314) | D2 default −15% of book NAV, option (b) −1.5 σ_book (SPEC:70, 1586, 4349 `alt: "-1.5*sigma_book"`); steps −8/−12 fixed (SPEC:1587) | Keep D2 default; sigma variant specification book only |
| OQ-02 | Confirm CR-07 denominator (preferred line in numerator, all KOSPI lines in denominator); first binds 2026-05-06 (CR-07) vs 2026-05-07 (common/all) (R3:1315) | Not defined; `pair_share_kospi` is a reported field; 0.45 trigger removed (XS-07) | Display all four definitions; no trigger |
| OQ-03 | S_beta beta_hat window: OLS beta of daily returns on the declared market over the prior 252 sessions, frozen in the card header at each formation; full-period beta descriptive only (c12 used full-period monthly OLS betas 0.631-0.742) (R3:1316) | No S_beta (XS-12) | Specify in gate package only when needed |
| OQ-04 | Step 8 stays (CR-08). Add "positive in at least 2 of 3 sub-periods" and a short-sale-regime split as extra checks (both tighten)? (R3:1317) | Step 8 ≥ 60% of years (SPEC:4767); CARD-P PC-5; R-22 declared start band and regime lines (SPEC:2276) | Print, do not gate, until owner rules |
| OQ-05 | Professors' Jensen-alpha step-5 variant not adopted (loosens for beta < 1); print as a report line only? (R3:1318) | Not in v2.0 | Report line only |
| OQ-06 | US stock momentum prior: 1 (TF) or R-15's "2 if vol-scaled + D-M"? (R3:1319) | v2.0 keeps 2-if (XS-16); no exposure difference | Display 1 (D&M is spec-book only) |
| OQ-07 | R-06 Korea card judged from 1996-09 (PASS) or 2016-01 (INSUFFICIENT DATA)? (R3:1320) | **Answered:** long history, `history_start` 1997-04-01, start-band conditions (SPEC:1574; XS-20) | Follow v2.0 |
| OQ-08 | Build order of data stores: OpenDART PIT, FMP/EDGAR PIT, KIS quote snapshots, t-1 investor flows (R3:1321) | v2.0 register (SPEC:6024-6033) has KRX closes, KODEX PDF, French, ECOS, calendars; investor flows logged from day one (SPEC:1412); no OpenDART/FMP PIT | Flows logging first (already v2.0); PIT fundamentals outside v2.0 scope |
| OQ-09 | Crypto C3 prior 2 (macro R-15, executives) or 3 (prior design, professors)? Card PASS governs; only base_weight changes (R3:1322) | SPEC:699 "crypto 3 → 2 with BTC's own vol cap"; SPEC:1732 TS trend `2` | Keep 2 (admissible either way) |
| OQ-10 | Tiered t-hurdles: Tier A t ≥ 2.0; new signals t ≥ 3.0 plus SPA; > 100 configurations or TradingView-sourced t ≥ 3.4-3.8. Adopt as tightening? (R3:1323) | v2.0 one-sided z 2.50 (≤ 8 cells) / 3.34 (Bonferroni-120) (SPEC:2580) | Keep v2.0; print tiered hurdle |
| OQ-11 | Statistical review triggers: forward drawdown beyond the 95th simulated percentile, or 12-month Sharpe below its 90% CI → review, never automatic liquidation. Governance option? (R3:1324) | R-25 calibrated alarms on whole-book NAV; alarms demote verdicts, never raise (SPEC:2654, 2671); no liquidation path exists (read-only) | Add as printed alarm under the D4 budget |
| OQ-12 | CR-06 adopted only "never enter at a locked limit-up close". Add the five-session no-new-long window after locked limit-ups or volume spikes once BL-TF-02 tests it? (R3:1325) | R-27: a stock at its daily limit is non-fillable at the close; order carries (SPEC:2914, T-FILL-02 SPEC:2953) | No window until tested |
| OQ-13 | KOSDAQ trend: keep macro R-14's 0 until a KOSDAQ index rebuild and test exist? (R3:1326) | KOSDAQ TS trend 0 (SPEC:699, 1727) | Keep 0 |
| OQ-14 | SCR-1 primary definition: F4 10% cut (IR 1.53, smallest exclusion) or F1 highest-turnover quintile (+4.28%/yr net 35 on B1, IR 1.15)? One combined screen or two cards (overlap Jaccard 0.13)? (R3:1327) | Screens absent from v2.0 | Two cards, F4 primary (per R3 §11.2 GV ids) |
| OQ-15 | Attribution block "factor tilt" threshold. Proposal: Newey-West alpha t below 2.0 after attribution (R3:1328) | No attribution block in v2.0 | Print; label only |

**Gaps (R3:1332-1344, verbatim substance):** no PIT fundamentals locally (OpenDART, FMP/EDGAR) → KR-VQ, US-VQ, Korean drift, value, quality, insiders, IPO screen untested; no KIS quote history → flat 35 / 70 bp per side throughout; no t-1 investor-flow history; no local crypto, futures or US single-stock panels in the lab (C3 controls, CTREND-lite, diversified futures trend, US stock cards, US low-vol vs S_beta untested); KRX lab returns are price returns without dividends, rf = 0 (low-vol, value, low-beta understated ≈ 1-2%/yr); no price-impact model (capacity is a rule ≤ 1-2% of ADV20); all lab verdicts in sample 1996-2026, holdout treated as used, FORWARD-SIM incubation from 2026-10-01 is the clean test; floored trend × VT20 has no plateau or start-date sweep; no local test of the L0 composite or ridge challenger; 52-week-high-neutral and capped momentum crash tests not run; gate-size simulation covers steps 2, 3, 5, 8 only (1, 4, 7 and CPCV untested); E5 sigma-ladder and SPY cumulative-step results not re-run; R2 KR gate harness prints step 9 as 0.4 × diff; 94 professor claims and part of the executive ledger unverified; India not reviewed; "US 12-1 momentum Sharpe 0.02 since 2008" not checkable past 2017-03.

---

## Ambiguities (conservative readings)

- **A-1 (11.8 vs Council goldens).** TF reproduction targets v1.2 values (0.638 / 0.635 / 0.632; R3:1038-1051); v2.0 post-patch G-KR-02 is 0.641 / 0.638 / 0.609 / 0.635 / 0.576 (SPEC:5826) on ^KS11 to 2026-10-02, and R-06 KR's long-history cell (ΔMDD +12.7 pp, SPEC:1569) is on official closes from 1997-04-01, while TF's is the rebuilt KOSPI from 1996-09-02 (PC-1 +6.5 pp). All TF Sharpe gaps are inside Level 1 (±0.01), but the series differ. Reading: the Council fixture is the v2 golden; TF values are a second reproduction asserted only against `r2_idx_golden_values.csv`.
- **A-2 (XS-08 evidence).** TF: ladder with reset on KOSPI CW 2000-26 improved max DD (-55.8% → -41.3%); Council Check C2: hard stop with re-arm on KOSPI VT20 1997-2026 worsened it (-45.3% → -56.4%, 24 HALTs; SPEC:1589) and T-RLAYER-01 asserts those numbers (SPEC:2405). Different books and rules; not reconciled. Reading: build and assert v2.0's numbers; carry TF's as a note, no exposure claim.
- **A-3 (XS-19 item 26).** TF maps DNB-TF-11 (valuation timing) to v2.0 item 26, which is publication-lag "value timing" (SPEC:6182). Reading: no v2.0 item covers valuation timing; add DNB-TF-11 as a new design prohibition (CONTEXT display only), do not merge with item 26.
- **A-4 (`line` column).** 1-based CSV line counting the header (R3:915, R3:938 "lines 2-9"); data row = line − 2. Tests must use this convention.
- **A-5 (GV-523).** Arithmetic, not a lab output (R3:1236). Assert the rule `expected_live_sharpe = 0.6 × oos` only.
- **A-6 (window labels).** GV-435..439 period is "2026-06-23..2026-07-30 returns" (R3:1146) for the window named "2026-06-22..07-30": close of 06-22 to close of 07-30. Same for 11.7 and 11.8 crash windows.
- **A-7 (XS-02 test status).** TF "the required net-of-cost test fails" (price returns, 35 bp, no tax) vs v2.0 "UNVERIFIED until BL-U02 runs net of 35 bp plus the 0.20% sell tax" (SPEC:1727). Reading: no reversal sleeve is built in either case; prior stays as v2.0 stores it (1, UNVERIFIED) until the owner rules on XS-02.
- **A-8 (flow admissibility).** SPEC:1718 keeps "flow" at prior 3 and admits NOT_RUN families, which in principle gives a flow family base weight IV_m × 1/K_m; DNB item 14 forbids flow as a direction signal. Reading: no flow sleeve exists, so K_m excludes it; a build must not count "flow" in K_m without an owner ruling.
- **A-9 (absent lab files).** GV-440..449 (`kr_index_sanity.csv`) and GV-469..489 (`c12_lowvol_samebeta.csv`) cannot be cross-checked against a lab file; they are constants from `r3_golden_values.csv` only.
- **A-10 (lab vs gate).** Every `indicative_gate`/verdict string in section 11 is a lab verdict on in-sample price returns (R3:1337); never a QUANTGEN verdict; never an input to the recommended book.
