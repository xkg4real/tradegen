# QA recomputation of the techfund headline numbers (v1.0.1 review)

**Date.** 2026-10-03. **Reviewer.** Independent QA (did not see how the deliverables were produced).

**Method.** Every number below was recomputed from the raw files (`/home/claude/data_raw/marcap/data/marcap-YYYY.parquet`, `/home/claude/data_raw/us/`) with code written for this review in `/home/claude/qa/` (no project lab function imported or called). Lab outputs were read only to compare results and, in three labelled diagnostics, to locate the cause of a difference.

| Script | What it does |
|---|---|
| `qa01_load.py` | Reads all marcap files (13,953,730 rows, 7,913 dates 1995-05-02..2026-09-29, 4,301 codes after zero-padding) |
| `qa02_panel.py` | Spec §4.2 cleaning (segments, transfer resets, steps 2a/2b/2b′/2c, VALID, DIL inputs) |
| `qa03_index.py` | Spec §4.8 rebuilt KOSPI (variants A = finite r, B = VALID) and VT20 vs S |
| `qa04_names.py`, `qa05_books.py` | Operating-company classifier; §4.3 universe and features; SCR-1 (F4) and SCR-2 (F6) on B1 with the §4.3 book engine |
| `qa06_weekly.py`, `qa06b_weekly_variants.py` | Weekly 5-day reversal L/S (REV_1W) under three statistics conventions |
| `qa11_kospiH1.py`, `qa12_fs1.py`, `qa13_pair.py` | Page chart A windows; FS-1 floored trend × VT20; pair share and alternatives |
| `qa07*_diag.py` | Diagnostics only: own engine on the lab's saved universe / DIL_LIT arrays to locate differences |

**Tolerances** are the spec's Level 1 (§9.3): Sharpe/IR ±0.01; MDD/ΔMDD ±1 pp; window returns ±1 pp; shares and tail ratios ±0.03; annualised returns "the printed precision" (read here as ±0.005 pp around a two-decimal print); pair shares and index ratios at the printed precision; derived values within 1 bp.

## Results

| Quantity | Claimed | Yours | Within tolerance? | Note |
|---|---|---|---|---|
| **(a) SCR-1** F4 on B1, net 35, %/yr | +3.08 | **+3.079** | Yes | 366 formations 1996-03..2026-09; monthly period returns ×12. Gross +3.395 (printed +3.39), net 70 +2.763 (+2.76). On the lab's saved ALL universe: 3.072 |
| SCR-1 IR, net 35 | 1.53 | **1.532** | Yes | Monthly period differences, ×√12. With the exact definitions added to spec §4.3–§4.4 and the lab's additive cost convention: 3.0764%/yr and IR 1.5295, the lab's values to four decimals (`qa17d_costconv.py`). Daily basis (the gate's, spec §8.4): +3.12%/yr, IR 1.64 |
| SCR-1 extras | Sharpe 0.33 vs 0.22; ΔMDD 1.70 pp; turnover 2.78 vs 1.89; 90% of years; sub-periods +4.31 / +2.81 / +2.20; break-even 380 bp | 0.333 vs 0.223; 1.70 pp; 2.783 vs 1.893; 90.3% (compounded); 4.31 / 2.82 / 2.20; 381.5 bp | Yes, except 2006–15 (0.01 pp high) | Break-even on the lab's inputs 380.2 bp; my 381.5 bp follows from my own gross and turnover |
| **(b) SCR-2** F6 on B1, net 35, %/yr | +2.34 | **+2.346** (first build); **2.3363** (exact definitions) | Yes under the coordinator's ±0.10 pp band; the first build was 0.001 pp outside the old printed-precision band (2.335–2.345) | With the lab's ALL and the lab's float32 DIL_LIT my engine gives exactly 2.336. Causes: four formations with DIL_LIT exactly 0.10 (s = 1.1); IHQ (003560) 5:1 reverse split on 2003-12-19 sits on the 5% split-like boundary (s × p = 0.95), DIL −0.579 vs lab +1.107 for 2004-08..11; ~530 extra fund/REIT memberships my name regex kept. Spec-level ambiguity, not a document error |
| SCR-2 IR, net 35 | 0.65 | **0.648** (first build); **0.6453** (exact definitions) | Yes | Gross 2.427 / IR 0.669 (printed +2.42); net 70 2.265 (printed +2.26); break-even 1,060 bp (printed 1,057). Daily basis (the gate's): +2.48%/yr, IR 1.03 |
| **(c) Rebuilt KOSPI** 2020-03-19 | official 1,457.64 | **1,457.46** (ratio 0.99988) | Yes | Variant A (finite cleaned r, lagged Marcap, all KOSPI common lines, scaled to 2,064.85 on 2007-10-31). Spec OQ-07 range 0.9987–1.0023 |
| Rebuilt KOSPI 2026-06-22 | official 9,114.55 | **9,120.19** (1.00062) | Yes | Equals `kr_index_sanity.csv` |
| Rebuilt KOSPI 2026-07-30 | official 5,593.56 | **5,599.30** (1.00103) | Yes | — |
| Change 22 Jun → 30 Jul 2026 | about −38.6% (official −38.63%) | **−38.605%** | Yes | Variant B (VALID only) gives −38.634% and 1,450.51 / 9,089.28 / 5,577.72: "valid cleaned return" in §4.8 is ambiguous (open finding) |
| **(d) VT20 vs S**, ΔMDD, 1996-09-02..2026-09-29, 3 bp | +6.5 pp | **+6.54 pp** (2×: +6.44) | Yes | MDD rule −51.42%, S −57.95%, buy-and-hold −64.45%; average exposure 0.854; ΔSR −0.0006 |
| VT20 tail ratio | 0.70 | **0.705** | Yes | Mean weight on the worst 5% of buy-and-hold days ÷ mean weight |
| VT20 extras | crash −12.2% vs −38.6%; 2016–26 gross Sharpe 0.633 vs 0.628, MDD −37.0% vs −44.1%, S −41.5%, ΔMDD 4.46 | −12.25% vs −38.61%; 0.6329 vs 0.6284; −37.00% vs −44.05%; −41.45%; 4.46 | Yes | Variant B: ΔMDD +6.25, tail 0.703 |
| **(e) Weekly 5-day reversal** L/S, EW ALL, gross Sharpe | 0.99 (lab 0.992) | **0.999** (weekly periods ×√52); 1.014 (daily) | Yes | 1,593 weekly formations 1996-03-08..2026-09-29; average ALL 1,182 names; REV_1W = exp(CL[t] − CL[t−5]) − 1; long Q1, short Q5 |
| Weekly reversal net-35 Sharpe | −1.78 | **−1.780** | Yes | Only on weekly period returns ×√52 (the R1 lab convention). Daily-return basis: −1.684 (cost on the first day) or −1.876 (cost spread); the spec did not state the convention (fixed in §9.3) |
| Weekly reversal break-even per side | 12.5 bp | **12.35–12.57 bp** | Yes (within 1 bp) | Turnover 159.8 a year both legs (lab 159.5); net 70 −4.541 (lab −4.539) |
| Weekly reversal gross mean | +19.9%/yr (lab 19.93) | 20.08 (weekly ×52); 19.73 (daily ×252) | **No** (0.15 pp at printed precision) | Small construction difference not resolved (open finding, low priority) |
| **(f) Pair share** CR-07 on 2026-09-29 | 53.71% | **53.7062%** | Yes | (005930 + 005935 + 000660) / all KOSPI lines. Also 29.2943% on 2023-12-28; alternatives 50.82 / 52.59 / 53.96 and 26.88 / 27.79; first > 0.45 on 2026-05-06 (common-lines definition 2026-05-07); 99 of 181 sessions; peak 59.69% on 2026-06-25 — all exact |

## Additional recomputations (page and spec figures)

| Quantity | Claimed | Yours | Within tolerance? |
|---|---|---|---|
| Buy-and-hold 2025-12-30 → 2026-06-22 (page chart A) | +116.2% | +116.20% | Yes |
| VT20 same window, net 3 bp | +55.2% | +55.20% | Yes |
| ENS trend / floored ENS × VT20, same window (page JSON) | 0.9865 / 0.5092 | 98.65% / 50.92% | Yes |
| Crash window: trend / VT20 / floored | −31.3% / −12.2% / −9.8% | −31.30% / −12.25% / −9.78% | Yes |
| FS-1 floored trend × VT20 vs its own S, 1996–2026 | ΔMDD +15.4 pp, tail 0.64 | +15.35 pp, 0.639 | Yes |
| ENS vote share vs S (scorecard) | ΔMDD 8.91, tail 0.768 | 8.91, 0.768 | Yes |
| Panel check value (§4.2, GV-209) | 12,186 of 13,949,140 = 0.0874% | 12,186 of 13,949,153 = 0.0874% | Numerator and ratio exact; denominator +13 rows (0.0001%) unexplained, my implementation |

## Coordinator follow-up: exact definitions and the daily basis

After the coordinator's decisions (F1 basis, F2 tie rules and tolerance, F3 index definition), the screens were re-run with the definitions now written into spec §4.2–§4.4 (`qa17_exact.py`: the transcribed name classifier, float32 Close and Marcap for the eligibility tests and the 20th-percentile cut, DIL_LIT stored as float32 and flagged iff > 0.10, the split-like test with p computed first) and the cost conventions of spec §4.3 (`qa17d_costconv.py`: monthly R_net = R_gross − c × turnover; daily, c × turnover on the first earning session).

| Check | Result |
|---|---|
| ALL universe vs the lab's saved `univ_all`, 366 formations | 0 differences |
| F6 flags vs the lab's `DIL_LIT > 0.10`, inside ALL | 71,689 = 71,689; 0 differences (368 members sit exactly at float32 0.1 and are flagged) |
| SCR-1 B1/F4, monthly basis: gross / net 35 / net 70 %/yr; IR net 35 | 3.3884 / 3.0764 / 2.7645; 1.5295 (lab 3.3884 / 3.0764 / 2.76 printed; IR 1.5295): exact |
| SCR-2 B1/F6, monthly basis | 2.4164 / 2.3363 / 2.2563; 0.6453 (lab 2.42 / 2.3363 / 2.26 printed; IR 0.6453): exact |
| SCR-1 B1/F4, daily basis (the gate's) | +3.43 / +3.12 / +2.80 %/yr (mean daily difference × 252); IR 1.82 / 1.64 / 1.47 |
| SCR-2 B1/F6, daily basis | +2.56 / +2.48 / +2.40 %/yr; IR 1.07 / 1.03 / 1.00 |
| Sensitivity of the daily IRs | 1.646 / 1.036 on the first build (own classifier, multiplicative cost): inside the ±0.02 band |

## Definitions that could not be reproduced from the spec text alone (status after the coordinator's decisions)

1. **Statistics basis.** Resolved (F1): spec §8.4 states that screen cards are gated on daily differences; the lab's golden rows are labelled "monthly basis (R2 lab)" and daily-basis rows G-TF-SCR-15..16 were added.
2. **REV_1W.** Resolved: defined in spec §4.3 (v1.0.1).
3. **Code padding.** Resolved: spec §4.2 (v1.0.1), now citing `kr_01_build_panel.py` line 56.
4. **Name classifier.** Resolved (F2): the five patterns are written into spec §4.3.
5. **Exact-threshold ties.** Resolved (F2): spec §4.4 defines the DIL_LIT float32 comparison (a 10.0% increase is flagged) and the split-like boundary (inclusive, p computed first).
6. **"Valid cleaned return" (§4.8).** Resolved (F3): finite cleaned r, zero-volume days included, per `kr_05_index_timing.py` lines 35–56.
