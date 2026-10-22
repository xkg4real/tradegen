# KRX round-2 data lab: momentum reconciliation, exclusion screens, crash controls (Korea)

QUANTGEN technical and fundamental signals project, round 2, Korea data lab (2026-10-03). One methodology, on the round-1 panel (marcap daily snapshots of every KRX-listed stock, 1995-05-02..2026-09-29, survivorship-free), the round-1 universe (ALL = eligible operating common shares, price >= 1,000 KRW, >= 200 valid days, traded at t, no beyond-limit move in the last 30 sessions, Marcap >= 20th percentile; LARGE = top 200 by Marcap) and the round-1 return cleaning. Monthly formation at the last close of each month (366 formations, 1996-03..2026-08), returns from t+1, buy-and-hold within the month, delisted names frozen as cash, halted holdings carried. Costs 35 bp per side on every unit of turnover (70 bp stress). Sharpe ratios use raw returns (no risk-free rate). Price returns (dividends excluded). All statistics are in-sample (IS); nothing here has passed QUANTGEN's gate (the gate runs below are indicative).

Scripts: `/home/claude/datalab/r2/kr/r2_kr_*.py` (`python3 r2_kr_run_all.py` reruns everything in about 5 minutes, peak resident memory about 2.6 GB incl. memory-mapped pages). Results: `r2/kr/results/*.csv`; charts: `r2/kr/charts/*.json`.

**Same panel as round 1:** the round-2 engine reproduces round-1 numbers exactly (26/26 checks; daily book series identical to round-1 caches to 0.0). MOM 12-1 long-short EW gross +9.3%/yr, Sharpe 0.45 (round 1: +9.3%, 0.45); drop-highest-turnover-quintile +3.62%/yr over the gross EW universe, t 5.63 (round 1: +3.6%, t 5.63); MOM 12-1 inside the high TURN_1M tercile +1.44%/month, t 3.41 (round 1: +1.44%, t 3.41). Validation: 16/16 tests passed (section 8).

## Headline verdicts

1. **Momentum conflicts are definitional, not data errors.** On one panel the round-1 lab, P6 and E7 claims reproduce under their own definitions (round 1 exactly, P6 and E7 within a few tenths); the Korean-journal (KJFS) headline does not, and E5 only partly (its equal-weighted Sharpe). Two things drive the apparent conflict. First, long-short and long-only answer different questions: inside the high-turnover tercile 12-1 winners beat losers (EW +11.6%/yr gross, t 3.3), yet the same winners trail the EW universe by 11.6%/yr net (t -4.2) because high-turnover stocks as a group lose. Second, the period: 2015-07..2024-12 is a bad decade for every momentum construction (EW long-short gross -2.7%/yr). The KJFS sign (high-turnover W-L about -6%/month) appears only when holding returns are taken from unadjusted closes in an all-caps universe (-11.4%/month, t -5.4); the whole effect comes from capital reductions / reverse splits that KRX adjusts in its base price (0.09% of stock-days). With KRX-adjusted returns the same design gives +1.43%/month (t 3.3).
2. **Exclusion screens: BUILD for equal-weighted / small-cap books, marginal for cap-weighted books, nothing for the top 200.** Removing the P6 lottery composite (F4, about 10% of names) from the EW universe adds +3.1%/yr net of 35 bp on both books (information ratio 1.53, bootstrap p 0.0005), dropping the highest-turnover quintile (F1) +4.3%/yr (IR 1.15); positive in all three sub-periods and in 90%+ of years; still positive at 70 bp. In the 12-1 momentum top quintile (B4) F1 adds +7.8%/yr (IR 1.02). Cap-weighted with a 5% cap (B2): +0.85%/yr (IR 0.68, p 0.001) but mostly from 1996-2005. Top 200 (B3): +0.49%/yr (IR 0.39), fails the overfitting checks. Indicative gate: B1 and B4 pass 7 of 8 steps (only the deflated Sharpe over all 176 pooled trials misses: 0.94 / 0.56), B2 REVISE, B3 REJECT.
3. **Crash controls:** own-volatility scaling was already cutting exposure before the 2026 crash (12-1 long-short weight 0.55 EW / 0.27 VW on 2026-06-22; E5 top-500 deciles 0.35 / 0.20, exactly as E5 reported); the Daniel-Moskowitz gate on the rebuilt KOSPI was off (KOSPI 24-month return strongly positive). Full-sample net Sharpe of 12-1 long-short: EW 0.20 static -> 0.31 with both; VW 0.25 -> 0.37. But in 2016-2026 the combined overlay lowered net Sharpe (EW -0.20 -> -0.28, VW 0.32 -> 0.25) because it cut exposure in the 2026 melt-up. Keep the controls as risk controls on any momentum sleeve; do not expect them to rescue Korean 12-1 momentum, which stays a BACKLOG item. Name-level 15% stops cut Sharpe in every variant (E5 confirmed).
4. **1-month reversal, value-weighted without microcaps, is close to zero gross and negative net** (ALL deciles +0.57%/month gross, t 0.9; -0.68% net; quintiles +0.08% gross). P1's flag is confirmed: the -2.95%/month literature figure is an equal-weighted, small-cap number.
5. **Low volatility is a protective card, not an alpha card.** Lowest VOL_3M quintile: beta 0.63 (EW) / 0.74 (VW) to the VW market; CAPM alpha net of 35 bp +2.2% (t 0.8) and +0.7% (t 0.3) with rf = 0, lower still once a short rate is charged; it beat the VW market in 6 (EW) and 7 (VW) of 7 crash windows (2026-06-22..07-30: +44.8% for the VW book) and lagged in 9 of 10 book-rebound windows (2026 melt-up -102.2%).

## 1. Key numbers (gross and net)

Annualised (monthly mean x 12); t = Newey-West (6 lags). LS = $1 long / $1 short, both legs pay costs. LO excess = long-only top quintile net of its costs minus the gross universe. Exclusion = filtered minus unfiltered book, both net.

| Long-short sleeve (1996-04..2026-09) | Gross /yr | Gross Sharpe | Net 35 /yr | Net 35 Sharpe | Net 70 Sharpe | Sharpe 2016-26 gross / net |
|---|---|---|---|---|---|---|
| MOM_12_1 LS, ALL, EW | +9.3% | 0.45 | +4.2% | 0.20 | -0.04 | 0.12 / -0.20 |
| MOM_12_1 LS, ALL, VW | +13.5% | 0.43 | +7.8% | 0.25 | 0.07 | 0.50 / 0.32 |
| MOM_12_7 LS, ALL, EW | +10.0% | 0.57 | +3.6% | 0.20 | -0.16 | 0.51 / -0.01 |
| MOM_12_7 LS, ALL, VW | +13.0% | 0.48 | +5.6% | 0.21 | -0.06 | 0.38 / 0.10 |
| MOM_12_1 LS, high-turnover tercile (TURN_12M), EW | +11.6% | 0.53 | +5.7% | 0.26 | -0.01 | 0.43 / 0.10 |
| MOM_12_1 LS, low-turnover tercile (TURN_12M), EW | +9.1% | 0.38 | +2.6% | 0.11 | -0.16 | 0.30 / -0.11 |

| Exclusion (base, filter) | Diff gross /yr | Diff net 35 | Diff net 70 | IR net 35 | t | Boot p | Years > 0 |
|---|---|---|---|---|---|---|---|
| B1 F1 | +4.78% | +4.28% | +3.78% | 1.15 | 6.6 | 0.0005 | 94% |
| B1 F2 | +3.94% | +3.64% | +3.35% | 1.00 | 5.7 | 0.0005 | 90% |
| B1 F4 | +3.39% | +3.08% | +2.76% | 1.53 | 8.3 | 0.0005 | 90% |
| B1 F7 | +5.85% | +4.78% | +3.71% | 0.96 | 5.4 | 0.0005 | 90% |
| B2 F1 | +1.12% | +0.90% | +0.68% | 0.44 | 2.7 | 0.0065 | 71% |
| B2 F2 | +1.42% | +1.23% | +1.04% | 0.45 | 2.8 | 0.0050 | 77% |
| B2 F4 | +0.99% | +0.85% | +0.72% | 0.68 | 3.9 | 0.0015 | 77% |
| B2 F7 | +1.49% | +0.71% | -0.07% | 0.19 | 1.2 | 0.1299 | 65% |
| B3 F1 | +0.51% | +0.36% | +0.21% | 0.19 | 1.2 | 0.1309 | 61% |
| B3 F2 | +0.90% | +0.76% | +0.61% | 0.27 | 1.8 | 0.0475 | 65% |
| B3 F4 | +0.57% | +0.49% | +0.40% | 0.39 | 2.3 | 0.0190 | 61% |
| B3 F7 | +0.82% | +0.12% | -0.57% | 0.03 | 0.2 | 0.4598 | 61% |
| B4 F1 | +8.62% | +7.81% | +7.00% | 1.02 | 6.2 | 0.0005 | 94% |
| B4 F2 | +7.24% | +6.49% | +5.74% | 0.65 | 3.5 | 0.0005 | 84% |
| B4 F4 | +6.76% | +6.13% | +5.50% | 1.24 | 7.5 | 0.0005 | 97% |
| B4 F7 | +9.18% | +7.56% | +5.94% | 0.63 | 3.4 | 0.0005 | 87% |

| 12-1 momentum, net 35 Sharpe (max DD) | Static | Own-vol scaling | D&M gate | Both |
|---|---|---|---|---|
| LS_EW (ALL quintiles) | 0.20 (-64%) | 0.27 (-60%) | 0.25 (-66%) | 0.31 (-61%) |
| LS_VW (ALL quintiles) | 0.25 (-74%) | 0.31 (-44%) | 0.32 (-65%) | 0.37 (-42%) |
| LO_EW excess (Q5 vs EW univ) | -0.11 (-64%) | -0.12 (-61%) | -0.10 (-62%) | -0.11 (-61%) |
| LO_VW excess (Q5 vs VW univ) | 0.11 (-47%) | 0.16 (-41%) | 0.10 (-50%) | 0.17 (-43%) |

## 2. Task 1: Korean momentum reconciliation

### 2.1 The standardised grid (12-1 momentum, turnover = 12-month average daily Amount/Marcap, independent sorts)

ALL universe; signal quintiles and turnover terciles are each formed over the whole universe at the formation close and intersected. Annualised mean (NW t). The full grid (4 signals x {all, low, mid, high} x 2 turnover definitions x EW/VW x 7 legs x 5 periods) is in `results/r2_kr_mom_grid_long.csv` and `charts/r2_kr_chart_b_mom_grid_heatmap.json`.

| Wt | Turnover tercile | Leg | full | 1996-2005 | 2006-2015 | 2015-07..2024-12 | 2016-01..2026-09 |
|---|---|---|---|---|---|---|---|
| EW | all | LS gross | +9.3 (2.7) | +15.0 (1.9) | +11.9 (2.3) | -2.7 (-0.7) | +1.9 (0.5) |
| EW | all | LS net 35 | +4.2 (1.2) | +9.5 (1.2) | +6.8 (1.3) | -7.6 (-2.0) | -3.0 (-0.8) |
| EW | all | LO - EW univ, net | -1.3 (-0.6) | +1.6 (0.3) | -2.2 (-0.9) | -6.5 (-2.4) | -3.2 (-1.2) |
| EW | all | LO - VW univ, net | -3.8 (-1.1) | +1.4 (0.2) | +0.2 (0.0) | -7.4 (-2.1) | -12.1 (-2.2) |
| EW | low | LS gross | +9.1 (2.0) | +12.2 (1.1) | +11.1 (1.8) | -0.3 (-0.1) | +4.6 (1.0) |
| EW | low | LS net 35 | +2.6 (0.6) | +5.2 (0.5) | +4.8 (0.8) | -6.5 (-1.4) | -1.7 (-0.4) |
| EW | low | LO - EW univ, net | +9.7 (2.8) | +18.6 (2.2) | +7.4 (1.5) | -0.1 (-0.0) | +3.7 (1.0) |
| EW | low | LO - VW univ, net | +7.3 (1.9) | +18.4 (2.5) | +9.8 (1.9) | -1.0 (-0.2) | -5.2 (-0.9) |
| EW | mid | LS gross | +14.0 (3.9) | +19.0 (2.8) | +16.4 (2.4) | +2.4 (0.6) | +7.2 (1.8) |
| EW | mid | LS net 35 | +7.8 (2.2) | +12.2 (1.8) | +10.6 (1.5) | -3.4 (-0.9) | +1.3 (0.3) |
| EW | mid | LO - EW univ, net | +6.3 (2.7) | +7.1 (1.4) | +7.6 (2.0) | +1.0 (0.3) | +4.3 (1.6) |
| EW | mid | LO - VW univ, net | +3.8 (1.1) | +6.9 (1.0) | +9.9 (1.9) | +0.1 (0.0) | -4.6 (-0.9) |
| EW | high | LS gross | +11.6 (3.3) | +14.3 (1.6) | +13.4 (3.0) | +2.8 (0.7) | +7.5 (1.8) |
| EW | high | LS net 35 | +5.7 (1.6) | +7.9 (0.9) | +7.7 (1.7) | -3.0 (-0.7) | +1.7 (0.4) |
| EW | high | LO - EW univ, net | -11.6 (-4.2) | -13.8 (-2.0) | -12.7 (-4.0) | -11.7 (-3.4) | -8.5 (-2.5) |
| EW | high | LO - VW univ, net | -14.0 (-3.2) | -14.0 (-1.4) | -10.3 (-1.7) | -12.6 (-2.8) | -17.4 (-2.8) |
| VW | all | LS gross | +13.5 (2.4) | +16.3 (1.6) | +9.5 (1.1) | +2.0 (0.4) | +14.6 (1.5) |
| VW | all | LS net 35 | +7.8 (1.4) | +10.3 (1.0) | +3.7 (0.4) | -3.4 (-0.7) | +9.4 (1.0) |
| VW | all | LO - EW univ, net | +4.0 (0.9) | +0.9 (0.1) | +0.7 (0.1) | -2.9 (-0.7) | +10.0 (1.1) |
| VW | all | LO - VW univ, net | +1.6 (0.6) | +0.7 (0.2) | +3.1 (0.6) | -3.8 (-1.2) | +1.1 (0.3) |
| VW | low | LS gross | +7.5 (1.0) | +8.9 (0.5) | +4.6 (0.4) | -1.8 (-0.3) | +9.0 (0.9) |
| VW | low | LS net 35 | +0.3 (0.0) | +1.4 (0.1) | -2.9 (-0.3) | -8.6 (-1.4) | +2.3 (0.2) |
| VW | low | LO - EW univ, net | +6.3 (1.1) | +9.8 (0.9) | +3.3 (0.5) | -5.4 (-1.0) | +5.8 (0.6) |
| VW | low | LO - VW univ, net | +3.8 (1.1) | +9.6 (1.4) | +5.7 (0.9) | -6.3 (-1.5) | -3.1 (-0.6) |
| VW | mid | LS gross | +18.5 (3.2) | +9.1 (1.0) | +19.8 (2.1) | +11.5 (2.1) | +25.9 (2.4) |
| VW | mid | LS net 35 | +12.2 (2.1) | +2.2 (0.2) | +13.4 (1.4) | +5.7 (1.0) | +20.2 (1.9) |
| VW | mid | LO - EW univ, net | +6.9 (1.2) | -8.7 (-0.9) | +6.7 (0.9) | +6.1 (1.1) | +21.2 (2.1) |
| VW | mid | LO - VW univ, net | +4.5 (1.1) | -9.0 (-1.1) | +9.1 (1.5) | +5.2 (1.1) | +12.3 (2.2) |
| VW | high | LS gross | +14.3 (2.3) | +14.9 (1.0) | +10.8 (1.3) | +10.1 (1.3) | +17.1 (2.2) |
| VW | high | LS net 35 | +8.8 (1.4) | +8.7 (0.6) | +5.4 (0.6) | +4.9 (0.6) | +12.0 (1.5) |
| VW | high | LO - EW univ, net | -12.7 (-2.8) | -22.7 (-2.5) | -17.0 (-3.8) | -7.3 (-0.9) | +0.4 (0.0) |
| VW | high | LO - VW univ, net | -15.1 (-3.2) | -22.9 (-2.2) | -14.7 (-2.8) | -8.1 (-1.0) | -8.5 (-1.1) |

Reading: (i) the long-short spread is positive in every turnover tercile over the full sample (EW gross: low +9.1%, mid +14.0%, high +11.6%; with 1-month turnover terciles the high tercile is the strongest, +19.8%, t 4.8); (ii) the long-only winners of the high-turnover tercile lose to the EW universe in every period (-11.6%/yr net) because high turnover is the strongest negative predictor in Korea (round 1: highest-turnover quintile -22.4%/yr vs the EW universe); (iii) low- and mid-turnover winners beat the EW universe over the full sample (+9.7%, t 2.8; +6.3%, t 2.7) but not in 2015-07..2024-12 (-0.1%, +1.0%); (iv) 2015-2024 is weak for every momentum book; (v) 12-7 has the highest EW gross Sharpe (0.57) but its turnover leaves the same net Sharpe as 12-1 (0.20 vs 0.20); 6-1 is negative net.

### 2.2 Reconciliation table

| Claim | Exact definition (as stated) | Round-2 reproduction | Verdict | Reason |
|---|---|---|---|---|
| Brief / KJFS (Eom et al. 2020) | Korea, 2000-07..2019-06, EW, gross; turnover top/bottom 30% (formation-period average), highest-volatility decile dropped, momentum quintiles inside each group; high-turnover W-L -6.13%/month (t -4.76), losers +6.85%/month | Same design on the panel: all caps +1.43%/month (t 3.3), losers -0.91%; ex-bottom-20% +1.66% (t 4.5). Unadjusted closes, all caps: -11.4% (t -5.4), losers +12.4%/month; cleaned returns except unadjusted corporate-action days: -11.3%; unadjusted signal + adjusted holding: +1.83% | NOT REPRODUCED | With KRX-adjusted returns the sign is positive. The paper's sign and loser returns are reproduced only when holding returns ignore KRX base-price adjustments in an all-caps universe: capital reductions / reverse splits of distressed, high-turnover losers (mostly executed during trading halts; the 40 largest contributions are raw one-day jumps of x11.5 to x115) - 0.09% of stock-days carry the whole effect, and it vanishes once the bottom 20% of caps is removed. This is a hypothesis about the source data (not verifiable without it), but the claim should not set Korean weights. |
| P6 (approximate Eom replication) | Same window; P6 approximation (p6_eom_x01.py): all caps +0.58%/month (t 1.50), ex-bottom-20% +1.42% (t 3.52) | +1.43% (t 3.3) / +1.66% (t 4.5) | PARTLY | Sign and the ex-microcap size confirmed; the all-caps number is larger here (round-1 eligibility: >= 200 valid days, no recent beyond-limit move; P6 required next-month survival, a look-ahead filter, and set all beyond-limit days to missing). |
| P6 decile sorts | ALL-like universe, D10-D1, holding 2001-02..2026-09: 12-1 EW 0.76%/month (t 2.37), net-35 Sharpe 0.18 (2x -0.09); 12-7 EW 1.30% (t 4.91), net Sharpe 0.54 (2x 0.10); VW 12-1 1.66% (t 2.71), net Sharpe 0.39 | 12-1 EW 0.89% (t 2.75), net Sharpe 0.24 (2x -0.06); 12-7 EW 1.40% (t 5.10), net 0.60 (2x 0.14); VW 12-1 1.80% (t 2.92), net 0.46 | CONFIRMED | Within about 0.15%/month and 0.06 Sharpe; P6 measured turnover against target (not drifted) weights and used calendar-month returns with a survival filter. |
| Round-1 lab | ALL, EW, quintiles, 1996-2026: 12-1 LS +9.3%/yr gross (Sharpe 0.45), net 0.20; high TURN_1M tercile (dependent sort) +1.44%/month | +9.3%/yr, Sharpe 0.45, net 0.20; high tercile 1.44%/month (t 3.41); independent TURN_12M high tercile +11.6%/yr | CONFIRMED | Identical panel and engine (26/26 checks). True for long-short spreads over the full sample; it says nothing about long-only winners (see E7) and 2016-2026 is much weaker (EW gross Sharpe 0.12). |
| E7 | 2015-07..2024-12; liquid universe (Marcap >= 100bn, ADV20 >= 1bn, price >= 1,000, ex-관리/투자주의환기, ex-SPAC); 12-month turnover terciles ranked over all listed stocks; top-quintile winners vs month-formed EW benchmark, legs re-weighted daily; net 35: all -4.4%/yr, high -10.9%, low +3.1% (t 0.8) | S0 exact: -4.5%, -11.2%, +2.9% (t 0.8); monthly buy-and-hold engine: -5.0%, -11.9%, +2.7%; terciles inside the universe: high -12.9%, low +2.4%; ALL universe grid cell: -6.5%, -11.7% (t -3.4), -0.1% | CONFIRMED | Reproduced within 0.3 pp and robust to engine, tercile and universe choices. It measures long-only winners against an EW benchmark, which mixes momentum with the turnover effect (high-turnover stocks lose as a group), in a decade when the long-short spread itself was about zero. Not in conflict with round 1 / P6. |
| E5 | Top 500 by Marcap, price >= 1,000, D10-D1, 2000-01..2026-09: Sharpe gross/net EW 0.43/0.20, VW 0.52/0.36; VW net 0.36 -> 0.41 with own-vol scaling (EW 0.20 -> 0.31); Jul-2026 WML -24.8% EW / -29.6% VW; VS weights 0.35 EW / 0.20 VW on 22 Jun 2026 | EW 0.26/0.04, VW 0.44/0.28; with scaling VW net 0.27 -> 0.31, EW 0.04 -> 0.20; Jul-2026 -30.0% EW / -29.8% VW; VS weights 22 Jun 0.35 / 0.20 | PARTLY | VW numbers, the July-2026 VW month, the scaling weights and the direction/size of the scaling gain reproduce; the EW Sharpe (0.43) does not under the stated definition (top-500 quintiles give 0.39, a looser top-500 without validity screens 0.26). E5's scripts were not saved, so the EW construction difference cannot be identified. |
| P2 | Top 500, 2026-07: WML -27.2% (EW, gross) | Deciles -30.0%, quintiles -29.3%; ALL quintiles -17.2% | PARTLY | Same order of magnitude; the exact figure depends on deciles vs quintiles and the universe. |

Decomposition of the KJFS result (all caps, high-turnover W-L, %/month, NW t): adjusted signal + adjusted returns +1.43 (3.3); unadjusted signal + adjusted returns +1.83 (4.5); adjusted signal + unadjusted returns -11.01 (-5.5); unadjusted both -11.37; cleaned returns except unadjusted corporate-action days -11.33 (-5.4). The holding-return measurement, not the signal, flips the sign. Top contributing events: `results/r2_kr_mom_kjfs_events.csv`.

## 3. Task 2: exclusion-screen horse race (long-only)

Filters flag names at the formation close using data through t; breakpoints are formed in the ALL universe; flagged names leave the base book, which keeps its weighting rule. Difference = filtered minus unfiltered monthly return, both net of their own costs, same holding days. IR = mean/sd of the monthly difference x sqrt(12); TE = sd x sqrt(12). Bootstrap: paired circular block bootstrap, 3-month blocks, 2,000 resamples, seed 20261002, one-sided p for mean > 0 (null-centred).

Definitions: F1 highest TURN_1M quintile; F2 highest VOL_3M quintile; F3 highest MAX_1M quintile; F4 P6 lottery composite (bottom decile of pct-rank(-VOL_3M)+pct-rank(-MAX_1M)+pct-rank(-TURN_1M), from p6_exclusion.py); F5 E7 attention-fade events in the last 20 sessions (volume >= 5x the previous 20-day average with r >= +5%; locked limit-up close, >= 29.5% from 2015-06-15 and >= 14.5% before, close = high; +50% in 20 days; from e7_checks_part2.py and E7 DC2); F6 252-session share growth > 10% ignoring split-like days (shares x/÷ by > 5% with the raw close moving by the inverse ratio within +-5% on the same day); F7 = F1|F2|F3; F8 = F4|F5|F6. Bases: B1 EW ALL; B2 VW ALL, 5% cap (iterative pro-rata redistribution); B3 top-200 VW, 5% cap; B4 12-1 momentum top quintile EW.

| Base | Filter | Diff /yr net 35 | net 70 | Sharpe filt. | Sharpe unfilt. | Max DD filt. - unfilt. (+ = shallower) | TE | IR | Boot p | Years > 0 | Excluded names / weight | Turnover/yr filt. / unfilt. |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| B1 | F1 | +4.28% | +3.78% | 0.38 | 0.22 | +2.4% | 3.7% | 1.15 | 0.0005 | 94% | 20% / 20% | 3.3 / 1.9 |
| B1 | F2 | +3.64% | +3.35% | 0.36 | 0.22 | +2.5% | 3.6% | 1.00 | 0.0005 | 90% | 20% / 20% | 2.7 / 1.9 |
| B1 | F3 | +2.43% | +1.36% | 0.31 | 0.22 | +1.7% | 2.6% | 0.92 | 0.0005 | 84% | 20% / 20% | 4.9 / 1.9 |
| B1 | F4 | +3.08% | +2.76% | 0.33 | 0.22 | +1.7% | 2.0% | 1.53 | 0.0005 | 90% | 10% / 10% | 2.8 / 1.9 |
| B1 | F5 | +1.40% | -0.08% | 0.27 | 0.22 | -0.8% | 2.9% | 0.49 | 0.0095 | 71% | 23% / 23% | 6.1 / 1.9 |
| B1 | F6 | +2.34% | +2.26% | 0.31 | 0.22 | +0.4% | 3.6% | 0.65 | 0.0005 | 81% | 19% / 19% | 2.1 / 1.9 |
| B1 | F7 | +4.78% | +3.71% | 0.41 | 0.22 | +4.4% | 5.0% | 0.96 | 0.0005 | 90% | 34% / 34% | 4.9 / 1.9 |
| B1 | F8 | +3.53% | +2.07% | 0.37 | 0.22 | +0.4% | 5.3% | 0.67 | 0.0005 | 84% | 37% / 37% | 6.1 / 1.9 |
| B2 | F1 | +0.90% | +0.68% | 0.33 | 0.29 | +1.5% | 2.0% | 0.44 | 0.0065 | 71% | 20% / 6% | 1.0 / 0.4 |
| B2 | F2 | +1.23% | +1.04% | 0.34 | 0.29 | +1.1% | 2.7% | 0.45 | 0.0050 | 77% | 20% / 7% | 0.9 / 0.4 |
| B2 | F3 | +0.02% | -0.74% | 0.30 | 0.29 | +1.1% | 2.6% | 0.01 | 0.5062 | 61% | 20% / 10% | 2.6 / 0.4 |
| B2 | F4 | +0.85% | +0.72% | 0.32 | 0.29 | +1.0% | 1.2% | 0.68 | 0.0015 | 77% | 10% / 3% | 0.8 / 0.4 |
| B2 | F5 | -0.35% | -1.23% | 0.28 | 0.29 | -0.3% | 3.6% | -0.10 | 0.7246 | 52% | 23% / 11% | 2.9 / 0.4 |
| B2 | F6 | +0.69% | +0.58% | 0.32 | 0.29 | +0.2% | 4.7% | 0.15 | 0.2414 | 81% | 19% / 13% | 0.7 / 0.4 |
| B2 | F7 | +0.71% | -0.07% | 0.33 | 0.29 | +1.7% | 3.8% | 0.19 | 0.1299 | 65% | 34% / 15% | 2.6 / 0.4 |
| B2 | F8 | +0.60% | -0.29% | 0.32 | 0.29 | -0.5% | 6.1% | 0.10 | 0.3198 | 68% | 37% / 21% | 3.0 / 0.4 |
| B3 | F1 | +0.36% | +0.21% | 0.32 | 0.30 | +1.1% | 1.9% | 0.19 | 0.1309 | 61% | 8% / 4% | 0.9 / 0.5 |
| B3 | F2 | +0.76% | +0.61% | 0.33 | 0.30 | +0.4% | 2.8% | 0.27 | 0.0475 | 65% | 9% / 5% | 0.9 / 0.5 |
| B3 | F3 | -0.30% | -0.98% | 0.29 | 0.30 | +0.9% | 2.7% | -0.11 | 0.7551 | 48% | 12% / 8% | 2.4 / 0.5 |
| B3 | F4 | +0.49% | +0.40% | 0.32 | 0.30 | +0.8% | 1.2% | 0.39 | 0.0190 | 61% | 4% / 2% | 0.8 / 0.5 |
| B3 | F5 | -0.54% | -1.28% | 0.28 | 0.30 | -0.3% | 3.8% | -0.14 | 0.7986 | 48% | 13% / 9% | 2.6 / 0.5 |
| B3 | F6 | +0.29% | +0.18% | 0.31 | 0.30 | -0.1% | 5.1% | 0.06 | 0.4143 | 61% | 15% / 12% | 0.9 / 0.5 |
| B3 | F7 | +0.12% | -0.57% | 0.31 | 0.30 | +0.8% | 3.9% | 0.03 | 0.4598 | 61% | 19% / 12% | 2.5 / 0.5 |
| B3 | F8 | +0.12% | -0.66% | 0.31 | 0.30 | -1.3% | 6.4% | 0.02 | 0.4953 | 55% | 24% / 18% | 2.7 / 0.5 |
| B4 | F1 | +7.81% | +7.00% | 0.45 | 0.18 | +6.4% | 7.6% | 1.02 | 0.0005 | 94% | 36% / 36% | 9.2 / 6.9 |
| B4 | F2 | +6.49% | +5.74% | 0.41 | 0.18 | +3.4% | 9.9% | 0.65 | 0.0005 | 84% | 39% / 39% | 9.1 / 6.9 |
| B4 | F3 | +4.29% | +2.81% | 0.31 | 0.18 | +1.0% | 5.1% | 0.84 | 0.0005 | 84% | 29% / 29% | 11.2 / 6.9 |
| B4 | F4 | +6.13% | +5.50% | 0.38 | 0.18 | +2.9% | 4.9% | 1.24 | 0.0005 | 97% | 20% / 20% | 8.7 / 6.9 |
| B4 | F5 | +1.70% | +0.23% | 0.23 | 0.18 | -4.3% | 5.9% | 0.29 | 0.0590 | 71% | 28% / 28% | 11.1 / 6.9 |
| B4 | F6 | +4.23% | +4.05% | 0.32 | 0.18 | +1.9% | 7.5% | 0.57 | 0.0005 | 90% | 25% / 25% | 7.4 / 6.9 |
| B4 | F7 | +7.56% | +5.94% | 0.46 | 0.18 | +4.6% | 12.1% | 0.63 | 0.0005 | 87% | 54% / 54% | 11.5 / 6.9 |
| B4 | F8 | +6.64% | +5.04% | 0.40 | 0.18 | +3.8% | 10.4% | 0.64 | 0.0005 | 81% | 48% / 48% | 11.5 / 6.9 |

Sub-periods (difference /yr net 35 bp, IR in brackets):

| Base | Filter | 1996-2005 | 2006-2015 | 2016-2026-09 |
|---|---|---|---|---|
| B1 | F1 | +5.90% (1.10) | +4.27% (1.67) | +2.82% (1.07) |
| B1 | F2 | +3.90% (0.76) | +3.83% (1.42) | +3.24% (1.22) |
| B1 | F4 | +4.31% (1.68) | +2.81% (1.72) | +2.20% (1.30) |
| B1 | F5 | +2.35% (0.60) | +1.35% (0.61) | +0.60% (0.28) |
| B1 | F6 | +2.92% (0.47) | +2.83% (1.95) | +1.34% (1.43) |
| B1 | F7 | +7.40% (1.04) | +4.22% (1.24) | +2.94% (0.80) |
| B2 | F1 | +1.90% (0.67) | +0.48% (0.43) | +0.38% (0.21) |
| B2 | F2 | +2.97% (0.84) | +0.42% (0.32) | +0.41% (0.14) |
| B2 | F4 | +1.77% (1.14) | +0.29% (0.58) | +0.54% (0.39) |
| B2 | F5 | -0.15% (-0.03) | -0.19% (-0.13) | -0.69% (-0.20) |
| B2 | F6 | +1.49% (0.18) | +0.31% (0.38) | +0.31% (0.28) |
| B2 | F7 | +1.52% (0.33) | +0.31% (0.16) | +0.35% (0.08) |
| B3 | F1 | +1.23% (0.45) | -0.02% (-0.02) | -0.07% (-0.04) |
| B3 | F2 | +2.62% (0.73) | -0.04% (-0.03) | -0.20% (-0.07) |
| B3 | F4 | +1.36% (0.87) | -0.07% (-0.18) | +0.21% (0.16) |
| B3 | F5 | -0.43% (-0.08) | -0.33% (-0.22) | -0.83% (-0.22) |
| B3 | F6 | +0.91% (0.10) | -0.07% (-0.08) | +0.07% (0.05) |
| B3 | F7 | +0.61% (0.13) | -0.13% (-0.07) | -0.08% (-0.02) |
| B4 | F1 | +7.19% (0.69) | +8.73% (1.42) | +7.52% (1.29) |
| B4 | F2 | +2.44% (0.17) | +8.81% (1.28) | +8.00% (1.26) |
| B4 | F4 | +6.82% (1.09) | +6.65% (1.53) | +5.01% (1.21) |
| B4 | F5 | -0.56% (-0.07) | +3.22% (0.65) | +2.35% (0.65) |
| B4 | F6 | +6.29% (0.50) | +4.24% (1.33) | +2.37% (1.05) |
| B4 | F7 | +4.36% (0.25) | +9.41% (1.11) | +8.75% (1.09) |

Event windows (filtered minus unfiltered cumulative return, net 35 bp, percentage points):

| Base | Filter | 2008-06..2009-03 GFC | 2020-02-17..03-19 COVID crash | 2020-03-20..06-30 COVID rebound | 2022 full year | 2026-01-02..06-22 melt-up | 2026-06-22..07-30 crash | 2026-07-31..09-29 after crash |
|---|---|---|---|---|---|---|---|---|
| B1 | F1 | +2.5 | +0.4 | -0.9 | +3.5 | -0.6 | +4.4 | -3.5 |
| B1 | F2 | +3.0 | +0.5 | -1.4 | +4.8 | -0.7 | +4.7 | -5.3 |
| B1 | F4 | +2.3 | -0.2 | +1.0 | +2.7 | -0.6 | +2.5 | -2.6 |
| B1 | F7 | +3.0 | +1.0 | -3.0 | +4.8 | -2.2 | +7.0 | -7.0 |
| B2 | F1 | -0.1 | +0.1 | -0.1 | +1.2 | +0.4 | +4.2 | -3.8 |
| B2 | F2 | -0.5 | +0.1 | -0.5 | +1.7 | -1.2 | +7.4 | -7.8 |
| B2 | F4 | -0.3 | -0.1 | +0.2 | +0.9 | +1.6 | +3.7 | -3.0 |
| B2 | F7 | +0.2 | +0.6 | +0.7 | +1.8 | -10.4 | +12.3 | -9.4 |
| B3 | F1 | -0.4 | -0.1 | +0.2 | +0.5 | +0.2 | +4.1 | -3.5 |
| B3 | F2 | -1.0 | -0.1 | +0.1 | +1.0 | -2.3 | +7.4 | -7.9 |
| B3 | F4 | -0.6 | -0.2 | +0.1 | +0.4 | +1.7 | +3.8 | -3.0 |
| B3 | F7 | -0.2 | +0.4 | +1.9 | +1.1 | -11.6 | +12.5 | -9.1 |
| B4 | F1 | +1.9 | -0.6 | +2.7 | +8.8 | +4.0 | +5.6 | -9.4 |
| B4 | F2 | +4.2 | +0.2 | -0.4 | +10.0 | +9.8 | +6.1 | -15.3 |
| B4 | F4 | +2.8 | -1.7 | +1.5 | +5.7 | +3.3 | +3.3 | -8.9 |
| B4 | F7 | +2.3 | +1.1 | +0.6 | +10.3 | +4.7 | +10.4 | -17.3 |

Filter overlap inside the ALL universe (mean Jaccard over formations) and average share of the universe flagged:

|  | F1 | F2 | F3 | F4 | F5 | F6 | F7 | F8 | Share flagged |
|---|---|---|---|---|---|---|---|---|---|
| F1 | 1.00 | 0.45 | 0.36 | 0.45 | 0.33 | 0.18 | 0.59 | 0.37 | 20% |
| F2 | 0.45 | 1.00 | 0.38 | 0.45 | 0.30 | 0.20 | 0.59 | 0.35 | 20% |
| F3 | 0.36 | 0.38 | 1.00 | 0.42 | 0.50 | 0.16 | 0.59 | 0.43 | 20% |
| F4 | 0.45 | 0.45 | 0.42 | 1.00 | 0.32 | 0.13 | 0.29 | 0.29 | 10% |
| F5 | 0.33 | 0.30 | 0.50 | 0.32 | 1.00 | 0.15 | 0.43 | 0.61 | 23% |
| F6 | 0.18 | 0.20 | 0.16 | 0.13 | 0.15 | 1.00 | 0.22 | 0.49 | 19% |
| F7 | 0.59 | 0.59 | 0.59 | 0.29 | 0.43 | 0.22 | 1.00 | 0.50 | 34% |
| F8 | 0.37 | 0.35 | 0.43 | 0.29 | 0.61 | 0.49 | 0.50 | 1.00 | 37% |

F6 note: 20% of the name-months flagged by the literal split rule are not confirmed by net issuance measured with KRX's own adjustment factor (bonus issues and some splits are adjusted on the ex-date, weeks before the new shares are listed, so a same-day rule misses them). The net-issuance version (F6b) is in the trial set.

Cross-check against the three analyses that proposed the screen: round 1 (drop the highest-turnover quintile, EW, +3.6%/yr over the GROSS EW universe) reproduces exactly (+3.62%, t 5.63; panel check at the top) and becomes +4.28%/yr when the unfiltered EW book also pays its own 1.9x/yr rebalancing cost; P6's lottery composite (p6_excl2.py: EW +0.23%/month, t 8.25; VW 5%-cap +0.04%/month, t 3.46) reproduces as +0.26%/month (t 8.3) and +0.07%/month (t 3.9); P6's composite uses calendar-month MAX and month-sum turnover, here the 21-session equivalents (rank-equivalent up to missing days). E7's attention-fade events (strong 5-20 day effects in E7's event study) do not carry over to a monthly exclusion book (F5).

### 3.1 Indicative QUANTGEN gate (best two primary filters per base, by IR at 35 bp)

| Base | Filter | Diff /yr | IR | 1 WF-selected OOS IR | 2 Lo / boot 90% CI of IR | 3 DSR pooled / per-base / null | 4 PBO primary / all (IS winner loses) | 5 p | 6 Sharpe @70 / IR @70 | 7 plateau | 8 years>0 | 9 x0.4 haircut | Steps, verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| B1 | F4 | +3.08% | 1.53 | 1.51 | [1.13, 1.72] / [1.29, 1.95] | 0.94 / 1.00 / 1.00 | 0.05 / 0.06 (loses 0%) | 0.0005 | 0.30 / 1.37 | 1.00 | 90% | +1.23% | 7/8 REVISE |
| B1 | F1 | +4.28% | 1.15 | 1.51 | [0.89, 1.53] / [0.95, 1.63] | 0.41 / 0.93 / 1.00 | 0.05 / 0.06 (loses 0%) | 0.0005 | 0.34 / 1.02 | 1.00 | 94% | +1.71% | 7/8 REVISE |
| B2 | F4 | +0.85% | 0.68 | 0.51 | [0.39, 0.99] / [0.36, 0.96] | 0.00 / 0.71 / 0.87 | 0.04 / 0.01 (loses 0%) | 0.0015 | 0.31 / 0.58 | 0.75 | 77% | +0.34% | 7/8 REVISE |
| B2 | F2 | +1.23% | 0.45 | 0.51 | [0.17, 0.86] / [0.17, 0.80] | 0.00 / 0.22 / 0.41 | 0.04 / 0.01 (loses 0%) | 0.0050 | 0.33 / 0.38 | 1.00 | 77% | +0.49% | 7/8 REVISE |
| B3 | F4 | +0.49% | 0.39 | 0.09 | [0.10, 0.72] / [0.08, 0.67] | 0.00 / 0.47 / 0.28 | 0.30 / 0.39 (loses 26%) | 0.0190 | 0.31 / 0.33 | 0.50 | 61% | +0.20% | 6/8 REJECT |
| B3 | F2 | +0.76% | 0.27 | 0.09 | [-0.03, 0.68] / [-0.01, 0.60] | 0.00 / 0.23 / 0.11 | 0.30 / 0.39 (loses 26%) | 0.0475 | 0.32 / 0.22 | 0.83 | 65% | +0.30% | 5/8 REJECT |
| B4 | F4 | +6.13% | 1.24 | 1.13 | [1.04, 1.73] / [1.11, 1.76] | 0.56 / 1.00 / 1.00 | 0.10 / 0.10 (loses 0%) | 0.0005 | 0.28 / 1.11 | 1.00 | 97% | +2.45% | 7/8 REVISE |
| B4 | F1 | +7.81% | 1.02 | 1.13 | [0.86, 1.58] / [0.80, 1.47] | 0.21 / 0.93 / 0.99 | 0.10 / 0.10 (loses 0%) | 0.0005 | 0.34 / 0.92 | 1.00 | 94% | +3.12% | 7/8 REVISE |

Step definitions: (1) walk-forward selection among the 8 primary filters on daily differences, 756-session in-sample, 21-session embargo, 126-session out-of-sample blocks; IR of the stitched OOS selections; (2) Lo (2002) SE with serial-correlation adjustment and a 2,000 x 10-session block bootstrap of the daily difference; both 90% intervals must clear zero; (3) deflated Sharpe with all 176 trials (variance of trial IRs pooled over bases; per-base variance with 44 trials; and the null variance 1/(T-1)); >= 0.95 required on the pooled version; (4) CSCV, 16 blocks: PBO <= 0.05 or the in-sample winner loses in <= 10% of splits; (5) one-sided paired bootstrap p <= 0.10; (6) filtered book Sharpe and difference IR > 0 at 70 bp; (7) >= 50% of neighbouring configurations (other cut levels / windows of the same family) keep half the IR; (8) >= 60% of calendar years positive; (9) 60% haircut, reported only.

Deflated Sharpe of the best of all 176 trials (B1|F4_cut5, IR 1.65, monthly SR 0.476): 0.979 with the pooled variance of the trial IRs (expected maximum monthly SR under the null 0.348, i.e. 1.21 annualised), 1.000 with the per-base variance (44 trials, SR0 0.81 annualised) and 1.000 with the null variance (SR0 0.49). The pooled version is conservative because B1/B4 and B2/B3 trials have genuinely different IR levels.

**Exclusion-screen verdicts.**
- **B1 (EW universe): BUILD-candidate as a filter.** F4 (P6 composite, ~10% of names) +3.08%/yr net (IR 1.53), F1 (highest-turnover quintile) +4.28%/yr (IR 1.15), F7 union +4.78%/yr (IR 0.96); positive in every sub-period; 7/8 gate steps; it paid in the 2026 crash and gave some back in the rebound. Recommended rule for a card: F4 at 10% (best IR, smallest exclusion, lowest extra turnover); F1/F7 when the larger mean matters more than tracking error.
- **B4 (momentum winners): BUILD as a construction rule for any long-only momentum or small-cap sleeve.** F1 +7.81%/yr, F4 +6.13%/yr (IR 1.24); the screen removes the high-turnover winners that drive the E7 underperformance.
- **B2 (cap-weighted, 5% cap): REVISE.** +0.85%/yr (F4) to +1.23%/yr (F2), significant by bootstrap but concentrated in 1996-2005 and failing the deflated Sharpe; excluded weight is only 3-7%. Worth carrying as a default hygiene filter (it does no harm net of costs), not as an alpha claim.
- **B3 (top 200, KOSPI200-like): REJECT.** Best +0.49%/yr (F4); PBO 0.30-0.39 with the in-sample winner losing out of sample in 16-26% of splits; walk-forward OOS IR 0.09; nothing after 2005.
- **F5 (E7 attention fade) does not work as a monthly exclusion** on B2/B3 and is the weakest filter on B1; its events are short-horizon (E7 measured 5-20 day effects), and a month-end screen with a 20-session memory flags ~23% of names, raising turnover sharply. **F6 (dilution)** helps B1/B4 modestly (+2.3% / +4.2%), little elsewhere.
- Limit-lock audit: 6.3% of B1 entries would be bought at a locked limit-up close and 2.1% of exits sold at a locked limit-down close (not fillable at the close); with F4 1.9% / 1.4%. Fills are not modelled; the screens reduce the problem rather than create it.

## 4. Task 3: momentum crash controls (12-1)

R-03 own-volatility scaling: s_t = min(1, 12% / sigma126_t) from the sleeve's own unit daily returns through t, applied to t+1. R-04 Daniel-Moskowitz gate on the rebuilt KOSPI: 0.5 when the 24-month KOSPI return to the last month-end is negative AND KOSPI sigma126 is above its expanding 2/3 quantile (>= 252 obs), else 1. Costs include the overlay's own exposure changes (both legs). The D&M gate was on 9.8% of days with 9 onsets (1997-05-31, 1997-10-08, 1997-10-11, 1999-04-19, 1999-04-21, 1999-04-29, 2001-01-04, 2008-10-31, 2020-03-20).

| Sleeve | Control | Sharpe gross | Sharpe net 35 | net 70 | Max DD net | Sharpe 2016-26 net | Avg exposure | GFC 08-06..09-03 | Mar-May 2009 | COVID crash | COVID rebound | 2026-06-22..07-30 | Exposure 2026-06-22 (cut before Jul?) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| LS_EW (ALL quintiles) | static | 0.45 | 0.20 | -0.05 | -64% | -0.20 | 1.00 | -18.3% | -13.2% | -1.9% | -0.2% | -24.8% | 1.00 (no) |
| LS_EW (ALL quintiles) | VS (own vol, 12%, cap 1) | 0.59 | 0.27 | -0.06 | -60% | -0.24 | 0.82 | -14.6% | -7.8% | -1.8% | -0.8% | -12.5% | 0.55 (yes) |
| LS_EW (ALL quintiles) | DM gate (KOSPI, floor 0.5) | 0.52 | 0.25 | -0.02 | -66% | -0.25 | 0.95 | -7.4% | -6.7% | -1.9% | +0.2% | -24.8% | 1.00 (no) |
| LS_EW (ALL quintiles) | VS x DM | 0.65 | 0.31 | -0.03 | -61% | -0.28 | 0.79 | -5.5% | -3.9% | -1.8% | -0.1% | -12.5% | 0.55 (yes) |
| LS_VW (ALL quintiles) | static | 0.43 | 0.25 | 0.07 | -74% | 0.32 | 1.00 | -29.3% | -32.1% | +11.2% | -12.4% | -40.3% | 1.00 (no) |
| LS_VW (ALL quintiles) | VS (own vol, 12%, cap 1) | 0.57 | 0.31 | 0.05 | -44% | 0.23 | 0.53 | -5.6% | -8.6% | +7.1% | -7.9% | -10.5% | 0.27 (yes) |
| LS_VW (ALL quintiles) | DM gate (KOSPI, floor 0.5) | 0.52 | 0.32 | 0.12 | -65% | 0.33 | 0.95 | -8.2% | -17.2% | +11.2% | -6.6% | -40.3% | 1.00 (no) |
| LS_VW (ALL quintiles) | VS x DM | 0.64 | 0.37 | 0.09 | -42% | 0.25 | 0.51 | +1.3% | -4.4% | +7.1% | -4.2% | -10.5% | 0.27 (yes) |
| LO_EW excess (Q5 vs EW univ) | static | 0.09 | -0.11 | -0.30 | -64% | -0.33 | 1.00 | -13.1% | -4.2% | -3.3% | +4.3% | -19.5% | 1.00 (no) |
| LO_EW excess (Q5 vs EW univ) | VS (own vol, 12%, cap 1) | 0.11 | -0.12 | -0.35 | -61% | -0.36 | 0.96 | -13.1% | -4.2% | -3.3% | +4.3% | -13.7% | 0.80 (yes) |
| LO_EW excess (Q5 vs EW univ) | DM gate (KOSPI, floor 0.5) | 0.12 | -0.10 | -0.31 | -62% | -0.39 | 0.95 | -8.5% | -2.2% | -3.3% | +2.4% | -19.5% | 1.00 (no) |
| LO_EW excess (Q5 vs EW univ) | VS x DM | 0.15 | -0.11 | -0.36 | -61% | -0.43 | 0.92 | -8.5% | -2.2% | -3.3% | +2.4% | -13.7% | 0.80 (yes) |
| LO_VW excess (Q5 vs VW univ) | static | 0.27 | 0.11 | -0.06 | -47% | 0.08 | 1.00 | -12.1% | -10.5% | +3.6% | -0.2% | -8.6% | 1.00 (no) |
| LO_VW excess (Q5 vs VW univ) | VS (own vol, 12%, cap 1) | 0.37 | 0.16 | -0.04 | -41% | 0.12 | 0.85 | -9.0% | -7.3% | +3.6% | -0.2% | -7.2% | 0.89 (yes) |
| LO_VW excess (Q5 vs VW univ) | DM gate (KOSPI, floor 0.5) | 0.28 | 0.10 | -0.08 | -50% | 0.06 | 0.95 | -4.0% | -5.3% | +3.6% | -0.1% | -8.6% | 1.00 (no) |
| LO_VW excess (Q5 vs VW univ) | VS x DM | 0.39 | 0.17 | -0.05 | -43% | 0.10 | 0.81 | -2.4% | -3.7% | +3.6% | -0.1% | -7.2% | 0.89 (yes) |
| E5 top500 D10-D1 EW | static | 0.27 | 0.08 | -0.12 | -81% | -0.14 | 1.00 | -24.5% | -26.2% | +6.0% | -0.4% | -42.1% | 1.00 (no) |
| E5 top500 D10-D1 EW | VS (own vol, 12%, cap 1) | 0.45 | 0.20 | -0.06 | -54% | -0.21 | 0.55 | -14.1% | -10.3% | +3.1% | -0.2% | -14.1% | 0.35 (yes) |
| E5 top500 D10-D1 EW | DM gate (KOSPI, floor 0.5) | 0.32 | 0.11 | -0.09 | -80% | -0.18 | 0.95 | -13.3% | -13.8% | +6.0% | +0.3% | -42.1% | 1.00 (no) |
| E5 top500 D10-D1 EW | VS x DM | 0.49 | 0.23 | -0.03 | -56% | -0.25 | 0.54 | -8.2% | -5.2% | +3.1% | +0.1% | -14.1% | 0.35 (yes) |
| E5 top500 D10-D1 VW | static | 0.37 | 0.22 | 0.06 | -90% | 0.25 | 1.00 | -43.0% | -41.0% | +9.1% | +16.6% | -47.9% | 1.00 (no) |
| E5 top500 D10-D1 VW | VS (own vol, 12%, cap 1) | 0.45 | 0.24 | 0.02 | -45% | 0.12 | 0.40 | -13.0% | -10.9% | +4.4% | +6.8% | -9.9% | 0.20 (yes) |
| E5 top500 D10-D1 VW | DM gate (KOSPI, floor 0.5) | 0.42 | 0.26 | 0.10 | -83% | 0.22 | 0.95 | -23.0% | -22.5% | +9.1% | +8.9% | -47.9% | 1.00 (no) |
| E5 top500 D10-D1 VW | VS x DM | 0.49 | 0.27 | 0.05 | -47% | 0.09 | 0.38 | -6.2% | -5.5% | +4.4% | +3.6% | -9.9% | 0.20 (yes) |

**Crash-control verdict.** (i) Own-volatility scaling is the only control that was de-risked before July 2026 (it had been cutting since January 2026 because the sleeves' own volatility rose in the melt-up); the D&M gate never fires in a bull-market crash and fired 9 times in 30 years, mostly in 1997-99, 2001, 2008 and March 2020. (ii) Full-sample net Sharpe improves with each control and most with both, and the max drawdown of the VW long-short sleeves falls by 30-45 points, but the gain comes from 1997-2009; in 2016-2026 the combined overlay lowered net Sharpe for every long-short sleeve, and the only post-2016 gains are small (the D&M gate alone on the VW long-short, +0.01; scaling alone or combined on the VW long-only excess, +0.02 to +0.04). (iii) In the 2026 crash window scaling beat a static book with the same average exposure (12-1 LS VW: -10.5% vs -22.9%), confirming E5. (iv) For long-only momentum the controls do not fix the sign: the EW winners-minus-universe sleeve stays negative net under every control. Recommendation: keep R-03 (and R-04 in the spec book) as mandatory risk controls on any Korean momentum sleeve; they do not turn Korean 12-1 into a PASS candidate.

**E5 stop-loss re-run** (top-500 D10-D1, 2000-01..2026-09, 15% stop from the formation close, close trigger, exit at the next close, cash to the next rebalance): EW gross Sharpe 0.26 -> 0.17 (net 0.04 -> -0.15), VW 0.44 -> 0.30 (net 0.28 -> 0.07); worst month EW -30.0% -> -25.1%. Exiting at the trigger close instead: EW 0.20; 10% stop: 0.19. **Reproduced in direction and proportion** (E5: 0.43 -> 0.26, about -40%; here about -35%); the level differs because the static EW Sharpe differs (see E5 row above). ALL quintiles behave the same way (`results/r2_kr_stoploss.csv`).

## 5. Task 4: 1-month reversal, value-weighted, microcaps excluded (P1's flag)

| Universe | Wt | Sort | Cost | Full | 1996-2005 | 2006-2015 | 2016-2026-09 | 1999-2021 | Sharpe full |
|---|---|---|---|---|---|---|---|---|---|
| ALL | VW | deciles | gross | +0.57 (0.9) | +2.56 (1.9) | +0.17 (0.3) | -0.86 (-1.0) | +0.61 (1.1) | 0.19 |
| ALL | VW | deciles | net35 | -0.68 (-1.1) | +1.33 (1.0) | -1.12 (-1.8) | -2.10 (-2.4) | -0.65 (-1.1) | -0.23 |
| ALL | VW | quintiles | gross | +0.08 (0.2) | +1.44 (1.4) | -0.61 (-1.1) | -0.51 (-0.8) | +0.04 (0.1) | 0.03 |
| ALL | VW | quintiles | net35 | -1.10 (-2.5) | +0.25 (0.3) | -1.80 (-3.4) | -1.68 (-2.7) | -1.14 (-2.6) | -0.45 |
| ALL | EW | deciles | gross | +1.43 (3.1) | +3.09 (2.6) | +0.69 (1.5) | +0.62 (1.4) | +1.41 (2.5) | 0.53 |
| ALL | EW | deciles | net35 | +0.23 (0.5) | +1.87 (1.6) | -0.53 (-1.2) | -0.56 (-1.3) | +0.20 (0.4) | 0.08 |
| ALL | EW | quintiles | gross | +0.94 (2.7) | +2.11 (2.3) | +0.36 (1.1) | +0.40 (1.2) | +0.89 (2.2) | 0.45 |
| ALL | EW | quintiles | net35 | -0.17 (-0.5) | +0.99 (1.1) | -0.75 (-2.2) | -0.68 (-2.0) | -0.21 (-0.5) | -0.08 |
| LARGE | VW | deciles | gross | +0.20 (0.3) | +2.02 (1.3) | -0.23 (-0.4) | -1.06 (-1.1) | +0.20 (0.3) | 0.06 |
| LARGE | VW | deciles | net35 | -1.06 (-1.6) | +0.79 (0.5) | -1.52 (-2.3) | -2.31 (-2.4) | -1.06 (-1.7) | -0.33 |
| LARGE | VW | quintiles | gross | +0.07 (0.1) | +1.49 (1.2) | -0.51 (-0.9) | -0.69 (-1.0) | -0.22 (-0.5) | 0.03 |
| LARGE | VW | quintiles | net35 | -1.10 (-2.1) | +0.32 (0.3) | -1.68 (-2.9) | -1.85 (-2.8) | -1.38 (-3.0) | -0.41 |
| LARGE | EW | deciles | gross | +0.87 (1.5) | +2.93 (2.1) | +0.07 (0.1) | -0.25 (-0.4) | +0.73 (1.3) | 0.29 |
| LARGE | EW | deciles | net35 | -0.36 (-0.6) | +1.71 (1.2) | -1.19 (-2.4) | -1.46 (-2.5) | -0.50 (-0.9) | -0.12 |
| LARGE | EW | quintiles | gross | +0.65 (1.5) | +2.20 (2.0) | -0.01 (-0.0) | -0.15 (-0.3) | +0.42 (1.0) | 0.28 |
| LARGE | EW | quintiles | net35 | -0.47 (-1.1) | +1.07 (1.0) | -1.13 (-2.7) | -1.26 (-2.9) | -0.70 (-1.6) | -0.20 |

Losers minus winners, %/month (NW t). Turnover is about 40x a year (both legs). **Verdict:** confirmed. Value-weighted and without microcaps, 1-month reversal is not distinguishable from zero gross after 2005 and is negative net of 35 bp in every sub-period after 2005, in both ALL and the top 200; the equal-weighted decile spread (+1.43%/month full sample) is the only version that resembles the literature, and even it nets about zero. Keep Korean short-term reversal at 0-1 for cash equities (round-1 conclusion stands).

## 6. Task 5: low volatility as protection, not alpha

| Book (net 35) | Period | Beta to VW market | CAPM alpha rf=0 (t) | Alpha if rf=4% | Sharpe | Market Sharpe | Max DD | Market max DD | Up capture | Down capture |
|---|---|---|---|---|---|---|---|---|---|---|
| low-vol Q1 EW | full | 0.63 | +2.2% (0.8) | +0.8% | 0.37 | 0.35 | -74% | -70% | 0.71 | 0.66 |
| low-vol Q1 EW | 1996-2005 | 0.72 | +4.8% (0.7) | +3.6% | 0.37 | 0.26 | -74% | -70% | 0.78 | 0.68 |
| low-vol Q1 EW | 2006-2015 | 0.81 | +5.3% (2.0) | +4.6% | 0.55 | 0.28 | -52% | -55% | 0.90 | 0.67 |
| low-vol Q1 EW | 2016-2026-09 | 0.35 | -0.8% (-0.2) | -3.4% | 0.26 | 0.55 | -46% | -46% | 0.48 | 0.60 |
| low-vol Q1 VW | full | 0.74 | +0.7% (0.3) | -0.3% | 0.32 | 0.35 | -65% | -70% | 0.77 | 0.75 |
| low-vol Q1 VW | 1996-2005 | 0.91 | +6.6% (1.8) | +6.2% | 0.42 | 0.26 | -65% | -70% | 0.98 | 0.84 |
| low-vol Q1 VW | 2006-2015 | 0.65 | -3.9% (-1.9) | -5.3% | -0.04 | 0.28 | -43% | -55% | 0.63 | 0.82 |
| low-vol Q1 VW | 2016-2026-09 | 0.41 | +3.2% (0.8) | +0.8% | 0.51 | 0.55 | -48% | -46% | 0.58 | 0.53 |

| Book | Window | Kind | Book (net 35) | VW universe | EW universe | Book - VW |
|---|---|---|---|---|---|---|
| low-vol Q1 EW | C 1997-11..1998-06 Asian crisis | crash | -42.2% | -33.1% | -55.6% | -9.1% |
| low-vol Q1 EW | C 2000-03..2000-12 dot-com bust | crash | -13.6% | -44.1% | -46.7% | +30.5% |
| low-vol Q1 EW | C 2008-06..2009-03 GFC | crash | -30.0% | -34.2% | -32.6% | +4.1% |
| low-vol Q1 EW | C 2020-02-17..03-19 COVID crash | crash | -33.1% | -35.3% | -41.0% | +2.2% |
| low-vol Q1 EW | C 2022 full year | crash | -13.9% | -26.3% | -24.9% | +12.4% |
| low-vol Q1 EW | C 2024-07-11..08-05 Aug-2024 crash | crash | -9.8% | -16.0% | -15.6% | +6.2% |
| low-vol Q1 EW | C 2026-06-22..07-30 crash | crash | -2.1% | -38.5% | -18.2% | +36.4% |
| low-vol Q1 EW | R 1998-07..1999-06 post-crisis rebound | rebound | +178.0% | +191.6% | +232.4% | -13.6% |
| low-vol Q1 EW | R 2009-03..2009-12 post-GFC rebound | rebound | +47.5% | +56.6% | +57.4% | -9.1% |
| low-vol Q1 EW | R 2020-03-20..06-30 COVID rebound | rebound | +39.5% | +47.8% | +68.0% | -8.2% |
| low-vol Q1 EW | R 2026-01-02..06-22 melt-up | rebound | -5.2% | +104.9% | +0.8% | -110.1% |
| low-vol Q1 EW | R 2026-07-31..09-29 after crash | rebound | +5.1% | +23.6% | +20.5% | -18.6% |
| low-vol Q1 VW | C 1997-11..1998-06 Asian crisis | crash | -16.5% | -33.1% | -55.6% | +16.6% |
| low-vol Q1 VW | C 2000-03..2000-12 dot-com bust | crash | -24.8% | -44.1% | -46.7% | +19.3% |
| low-vol Q1 VW | C 2008-06..2009-03 GFC | crash | -25.4% | -34.2% | -32.6% | +8.8% |
| low-vol Q1 VW | C 2020-02-17..03-19 COVID crash | crash | -35.1% | -35.3% | -41.0% | +0.1% |
| low-vol Q1 VW | C 2022 full year | crash | -22.4% | -26.3% | -24.9% | +3.9% |
| low-vol Q1 VW | C 2024-07-11..08-05 Aug-2024 crash | crash | -2.3% | -16.0% | -15.6% | +13.8% |
| low-vol Q1 VW | C 2026-06-22..07-30 crash | crash | +6.3% | -38.5% | -18.2% | +44.8% |
| low-vol Q1 VW | R 1998-07..1999-06 post-crisis rebound | rebound | +201.0% | +191.6% | +232.4% | +9.5% |
| low-vol Q1 VW | R 2009-03..2009-12 post-GFC rebound | rebound | +30.3% | +56.6% | +57.4% | -26.3% |
| low-vol Q1 VW | R 2020-03-20..06-30 COVID rebound | rebound | +37.6% | +47.8% | +68.0% | -10.2% |
| low-vol Q1 VW | R 2026-01-02..06-22 melt-up | rebound | +2.7% | +104.9% | +0.8% | -102.2% |
| low-vol Q1 VW | R 2026-07-31..09-29 after crash | rebound | +2.4% | +23.6% | +20.5% | -21.3% |

No Korean short-rate series is available offline, so alphas use rf = 0; with a short rate the CAPM alpha of a beta-below-1 book falls by (1 - beta) x rf (the "rf = 4%" column is an assumption for scale, not data). **Verdict: protective card.** Beta 0.63-0.74, down capture below up capture, large outperformance in most crash windows (dot-com, 2022, Aug-2024, Jun-Jul 2026), but an EW max drawdown no better than the market (the 1997-98 crisis hit small low-vol stocks hard) and a heavy bull-market tax (it lagged in 9 of 10 rebound windows across the two books, including the 2026 melt-up). Net CAPM alpha is insignificant in the full sample (t below 1 against the VW market) and switches sign across sub-periods, so it should be judged on drawdown-first, Sharpe-non-inferiority terms (E7's K-LV framing), not on alpha.

## 7. Trial count and multiple testing

- Exclusion horse race: **176 trials** = 44 filter definitions x 4 bases (8 primary filters, 36 neighbours / variants: cut levels 10/15/25/30% for F1-F3, TURN_3M, VOL_1M, VOL_6M, MAX_3M, F4 cuts 5/15/20/25%, F5 windows 5/10/40/60, F5 regime-limit lock, F5 components alone, F6 thresholds 5/20/30%, F6 net issuance, F7 at 10/30% cuts, F8 with F6b or the regime lock), each at three cost levels (cost levels are stresses of the same trial, not extra trials). Two definition fixes were made before any performance was computed, after inspecting flag rates: the split-like rule requires a share change of more than 5% (otherwise every small convertible-bond conversion counted as a split), and F5's lock component follows E7's written spec (the regime-limit lock flagged 51% of the 1990s universe and is kept as a variant).
- Momentum grid: 56 sleeves (4 signals x 7 turnover cells x 2 weightings) x 7 legs x 5 periods (descriptive, no selection) plus 28 claim-reproduction books; crash controls: 6 sleeves x 4 controls x 3 cost levels plus 18 same-exposure statics; stop-loss: 2 sleeve sets x 2 weightings x 4 variants x 2 cost levels; reversal: 2 universes x 2 weightings x 2 sorts x 3 cost levels; low-vol: 2 books. One exploratory check outside these scripts (E5 looser top-500 universe) was folded into r2_kr_03.

## 8. Validation

| Test | Item | Result | Passed |
|---|---|---|---|
| W0 | round-1 reproduction checks (r2_kr_02) | 26/26 | yes |
| W1 | round-2 formation arrays recomputed from data truncated at 2008-06-30 (400 random codes) | 1,657,600/1,657,600 identical | yes |
| W1 | round-2 formation arrays recomputed from data truncated at 2015-06-30 (400 random codes) | 2,598,400/2,598,400 identical | yes |
| W1 | round-2 formation arrays recomputed from data truncated at 2026-06-30 (400 random codes) | 4,076,800/4,076,800 identical | yes |
| W2 | period returns recomputed by hand from days t+1..t_next (12 random periods) | max abs error 0.00e+00 | yes |
| W2 | same recomputation including day t differs (test has power) | all differ | yes |
| W2 | book series are missing on and before the first formation close | True | yes |
| W3 | filter flags assigned outside the ALL universe (all 44 definitions) | 0 | yes |
| W3 | quintiles unchanged when non-members get extreme signal values; none assigned outside | True | yes |
| W3 | quintile sizes = 20% +- 1 name (TURN_1M, VOL_3M, MOM_12_1; 25 random formations) | True | yes |
| W3 | top-200 (B3) and MOM 12-1 top quintile (B4) are subsets of the ALL universe | True, True | yes |
| W3 | F4 composite unchanged when non-members get extreme inputs | True | yes |
| W4 | filtered and unfiltered books: identical non-missing days, first day = formation+1, last = 2026-09-29 | 180/180 books | yes |
| W4 | rebalance dates shared by construction (one formation calendar, Panel.fidx) | 366 formations | yes |
| W5 | bootstrap and CSCV reproducible with fixed seeds | p 0.4803/0.4803; PBO 0.1918/0.1918 | yes |
| W6 | E7 exact construction reproduces E7's printed long-only excess (all/high/low) | all -4.50% vs -4.4%, high -11.20% vs -10.9%, low +2.93% vs +3.1% | yes |

SHA-256 checksums of every result file are written last by the runner (`results/r2_kr_hashes.csv`). The round-1 reproduction checks are listed in `results/r2_kr_reproduce_r1.csv`; the crash-control and stop-loss engines agree with the main engine to four decimals of Sharpe (`results/r2_kr_stoploss_engine_check.csv`).

## 9. Caveats

- **Price returns, no dividends.** Low-vol, low-turnover and large-cap books are understated by roughly their dividend yield (about 1-2% a year in Korea). The screens remove high-turnover, high-volatility names that pay little or no dividend, so total returns would most likely raise the filtered-minus-unfiltered differences slightly; long-short and excess figures are affected only by the yield gap between the legs.
- **Delistings**: a disappearing stock is held at its last price as cash (round-1 rule; bias bound about 1.4%/yr for the worst quintile book, smaller for the screened books, which hold fewer distressed names).
- **Limit-lock fills are not modelled** (orders at a locked limit-up/limit-down close are assumed filled); the audit above counts them. Market impact is not modelled; EW books hold small caps.
- **No risk-free rate** (CAPM alphas use rf = 0; Sharpe ratios are raw).
- **Shorting** is a research benchmark only (bans 2008-09, 2011, 2020-21, 2023-11..2025-03); only long-only results are implementable.
- **E5 and P2 scripts were not saved**, so their EW constructions could not be matched exactly; the E7 and P6 scripts were read and their constructions replicated; the KJFS paper was not available, so the unadjusted-price explanation is a tested hypothesis about its data, not a finding about the paper.
- **F5 and F6 depend on definitions** that differ from the literature (see section 3); the regime-limit and net-issuance variants are reported.
- Everything is in-sample. The indicative gate uses the walk-forward, bootstrap, DSR and CSCV machinery on the realised series; it is not QUANTGEN's code path.

## 10. Files

- Scripts: `r2_kr_common.py` (engine reuse, statistics, bootstrap, DSR, CSCV), `r2_kr_01_build_extra.py` (volume, shares, ChangeCode, Dept, limit locks, F5/F6 inputs, new signals, universes), `r2_kr_02_reproduce_r1.py`, `r2_kr_03_momentum.py`, `r2_kr_04_exclusion.py`, `r2_kr_05_crash_controls.py`, `r2_kr_06_reversal_lowvol.py`, `r2_kr_07_validation.py`, `r2_kr_08_charts_summary.py`, `r2_kr_run_all.py`.
- Results: `r2_kr_mom_grid_long.csv`, `r2_kr_mom_claims_long.csv`, `r2_kr_mom_e7_ladder.csv`, `r2_kr_mom_kjfs_events.csv`, `r2_kr_excl_summary.csv`, `r2_kr_excl_long.csv`, `r2_kr_excl_windows.csv`, `r2_kr_excl_years.csv`, `r2_kr_excl_jaccard.csv`, `r2_kr_excl_gate.csv`, `r2_kr_excl_trials.csv`, `r2_kr_excl_dsr_best.csv`, `r2_kr_excl_limitlock.csv`, `r2_kr_excl_f6_diagnostic.csv`, `r2_kr_excl_thin_books.csv`, `r2_kr_crash_controls.csv`, `r2_kr_crash_windows.csv`, `r2_kr_crash_exposure_2026.csv`, `r2_kr_dm_gate_onsets.csv`, `r2_kr_dm_gate_sample.csv`, `r2_kr_stoploss.csv`, `r2_kr_stoploss_engine_check.csv`, `r2_kr_reversal.csv`, `r2_kr_lowvol.csv`, `r2_kr_lowvol_windows.csv`, `r2_kr_reproduce_r1.csv`, `r2_kr_validation.csv`, `r2_kr_hashes.csv`.
- Charts: `r2_kr_chart_a_excl_cum_excess.json`, `r2_kr_chart_b_mom_grid_heatmap.json`, `r2_kr_chart_c_crash_windows.json`, `r2_kr_chart_d_b2_2025_2026.json`.
