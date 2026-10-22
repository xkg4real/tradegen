# QUANTGEN round-2 index and governance lab: protective index rules and gate power

Run 2026-10-03 (data to 2026-09-29 KOSPI, 2021-03-31 SPY). Scripts `/home/claude/datalab/r2/idx/r2_idx_*.py` (`python3 r2_idx_run_all.py`; about 25 minutes on 2 shared CPUs, peak memory under 1 GB). Results `/home/claude/datalab/r2/idx/results/*.csv`, charts `/home/claude/datalab/r2/idx/charts/*.json`. Every number below is read from those files by `r2_idx_05_summary.py`. These are indicative verdicts on local data, not a run of QUANTGEN's gate.

Conventions: weight decided at the close of t, earned from t+1; cash 0%; price returns (rebuilt KOSPI price index, unadjusted SPY); cost per side on |dw|, charged on the earning day, initial entry free; Sharpe = daily mean / sd x sqrt(252). KOSPI 1996-09-02..2026-09-29 at the KRX ETF cost (3 bp; 2x = 6 bp). SPY 1999-05-03..2021-03-31 at US-shares-via-KIS cost (50 bp; 2x = 100 bp) and futures cost (5 bp; 2x = 10 bp). These windows are the first sessions at which every centre and neighbour rule exists; section 3 shows how the verdicts move with the start date.

## Bottom line

1. **The KOSPI 20% vol target is the one index rule that passes the protective class robustly.** 1996-2026 at 3 bp: max drawdown -51.4% vs -58.0% for the same-exposure static book S (+6.5 pp; +6.4 pp at 2x), tail-exposure ratio 0.70, Sharpe 0.42 vs 0.42 (non-inferiority p 0.051 with 186-session blocks), 6 of 13 episodes positive (largest 38%), 70% of years positive, plateau 1.00: **PASS**. Start-date sweep: PASS from the 1996-06, 1996-09, 1997, 1999, 2001, 2006 starts; INSUFFICIENT (inconclusive) from the 2011, 2016 starts (R4b's 2016-26 card is INSUFFICIENT DATA too). As an outperformance card it fails (dSR -0.001, step-5 p 0.51), exactly like QUANTGEN's E2 cards.
2. **Trend rules protect against slow bears, not fast crashes, and their KOSPI evidence lives in 1997-2001.** The multi-speed vote (ENS) gets PASS on the primary window, but only just: 18 of 30 years positive (threshold 60%). Start-date sweep: REVISE from the 1996-06 start; PASS from the 1996-09, 1997 starts; REVISE from the 1999 start; INSUFFICIENT (inconclusive) from the 2001, 2006 starts; REJECT from the 2011, 2016 starts; from 2011 its drawdown is worse than S's. ENS x VT20 is REVISE (57% of years positive) although every other check passes strongly. SMA200 and the 12-month sign are INSUFFICIENT DATA by tier (16 and 11 de-clustered onsets < 30) and would be REJECT / REVISE otherwise.
3. **No trend rule protected in the 2026 KOSPI crash** (2026-06-22..07-30 crash): buy-and-hold -38.6%, SMA200 -37.9%, 12-month sign -38.6%, ENS -31.3%; VT20 -12.2% and ENS x VT20 -9.8%.
4. **SPY at QUANTGEN's 50 bp per side: every rule fails** (trend turnover of 7.3 to 11.9 units a year costs 3.7 to 6.0% a year; VT15 dMDD +0.3 pp, in line with R4b's +0.2 pp on 1990-2026 US data). At futures cost (5 bp) the rules protect (dMDD +3.8 to +14.7 pp) but none passes: ENS, VT, ENSxVT are INSUFFICIENT DATA (inconclusive) with 53 to 56% of the benefit from the GFC, and the trend versions also miss non-inferiority (p 0.24 to 0.26); the 12-month sign has 2 of 5 episodes positive.
5. **Overlay vs sleeve.** Flooring the trend weight at 0.5 does not lower the drawdown gain measured against the overlay's own S (that S also holds more equity), but it gives back absolute protection in slow bears: KOSPI ENS max drawdown -34.1% as a sleeve vs -39.2% / -44.8% floored, and the tail ratio rises to 0.91 (PC-2 fails). Multiplied with VT20, the floored trend (clip to [0.5, 1]) passes every evaluated check, including the years test the sleeve fails (63% vs 57%); its plateau was not evaluated.
6. **The gate rarely passes a no-edge strategy; it rarely passes a realistic edge either.** At true Sharpe 0 the joint pass rate (steps 2, 3, 5, 8; N = 1) is 0.5% at 10 years and about 0 beyond 18 years. Step 8 alone passes 30% of zero-Sharpe strategies over 10 years (iid). A true Sharpe of 0.4 passes step 2 half the time after 16.9 years and 80% after 40.4 (iid); with 9 counted trials a Sharpe of 0.5 needs 39.5 years for a 50% chance at step 3. Against a 0.4-Sharpe benchmark, an IR of 0.3 passes step 5 half the time after about 18 years and 80% only after about 50.
7. **The 10-session blocks are too short for index-like returns.** In the specified KOSPI-bootstrap design (source variance ratio 1.23 at 126 sessions, 1.34 at 252) the step-2 false-pass rate is 6.9% instead of 5% and step 5's is 12.8% instead of 10%; with the dependence removed (sign-flip) both are on size. The macro cards' max(10, Politis-White) rule fixes this; the outperformance gate still uses 10.
8. **Shiller averages inflate monthly trend results.** On SPY 1999-2021 the month-average backtest raises the 12-month-sign Sharpe by +0.23 and the 10-month SMA by +0.10 (S&P 500 2000-2018: +0.25 / +0.19). The bias sits in the average-to-average returns, not in the signals (which agree in 93-98% of months).

## 1. Key numbers

| Item | Value |
|---|---|
| KOSPI VT20, 3 bp, 1996-09..2026-09: dMDD vs S / tail ratio / dSR (p_ni) / episodes / years | +6.5 pp / 0.70 / -0.001 (0.051, block 186) / 6 of 13 (largest 38%) / 70% -> PASS |
| KOSPI ENS (multi-speed trend), same | +8.9 pp / 0.77 / +0.186 (0.008) / 8 of 13 / 60.0% -> PASS |
| KOSPI ENS x VT20, same | +11.3 pp / 0.55 / +0.231 (0.007) / 11 of 13 / 57% -> REVISE |
| KOSPI SMA200: de-clustered onsets; dMDD vs S | 16 (< 30); +1.9 pp -> INSUFFICIENT DATA (sufficiency); if sufficient REJECT |
| KOSPI TSM12: de-clustered onsets; dMDD vs S | 11 (< 30); +4.7 pp -> INSUFFICIENT DATA (sufficiency); if sufficient REVISE |
| SPY US via KIS 50bp: verdicts | SMA200 INSUFFICIENT (sufficiency), ENS REJECT, TSM12 INSUFFICIENT (sufficiency), VT REJECT, ENSxVT REJECT |
| SPY Futures 5bp: verdicts | SMA200 INSUFFICIENT (sufficiency), ENS INSUFFICIENT (inconclusive), TSM12 INSUFFICIENT (sufficiency), VT INSUFFICIENT (inconclusive), ENSxVT INSUFFICIENT (inconclusive) |
| Outperformance test (gate step 5, 10-session CBB) p vs buy-and-hold, KOSPI SMA200 / ENS / TSM12 / VT20 / ENSxVT | 0.23 / 0.06 / 0.27 / 0.51 / 0.05 |
| Same, SPY at 5 bp | 0.58 / 0.48 / 0.29 / 0.39 / 0.44 |
| KOSPI 2026-01-02..06-22 melt-up: B&H / SMA200 / ENS / TSM12 / VT20 / ENSxVT | +116.2% / +116.2% / +98.6% / +116.2% / +55.2% / +50.9% |
| KOSPI 2026-06-22..07-30 crash: B&H / SMA200 / ENS / TSM12 / VT20 / ENSxVT | -38.6% / -37.9% / -31.3% / -38.6% / -12.2% / -9.8% |
| KOSPI 2026-07-31..09-29 rebound: B&H / SMA200 / ENS / TSM12 / VT20 / ENSxVT | +22.8% / +4.1% / +8.3% / +22.8% / +6.2% / +2.1% |
| Gate false pass at true Sharpe 0 (kospi_cbb126), 10 / 18 / 30 years: step 2; step 8; joint 2+3+5+8 (N=1, rho 0.5) | 8.0% / 6.9% / 6.8%; 23.8% / 10.2% / 4.7%; 0.5% / 0.1% / 0.0% |
| Gate false pass at true Sharpe 0 (kospi_cbb126_signflip), 10 / 18 / 30 years: step 2; step 8; joint 2+3+5+8 (N=1, rho 0.5) | 5.0% / 4.2% / 4.7%; 31.2% / 16.9% / 10.5%; 0.2% / 0.1% / 0.0% |
| Step 5 false pass when the strategy Sharpe equals the benchmark (0.4), rho 0.5, 18 years: KOSPI / sign-flip / iid | 12.8% / 9.0% / 8.2% |
| Years for 50% / 80% power, step 2, true Sharpe 0.3 / 0.5 / 0.8 (KOSPI bootstrap) | 28.7 / >50 ; 10.5 / 25.7 ; <=5 / 10.1 |
| Averaging inflation of trend Sharpe, SPY 1999-2021 (month-average minus month-end): SMA10 / TSM12 / buy-and-hold | +0.10 / +0.23 / +0.04 |

## 2. Protective-class (CARD-P) verdicts, spec 8.7 order

S = buy-and-hold x the rule's average exposure (no cost); with 0% cash its Sharpe equals buy-and-hold's, so PC-3's dSR is also the dSR vs buy-and-hold. PC-3 p = one-sided circular-block-bootstrap p of dSR* <= -0.10, block = max(10, PW(d), PW(d^2)), 2,000 resamples, seed 11. Episodes: spec 8.6 drawdown windows inside the sample (KOSPI also 1997-06-14..1998-06-16 and 2000-01-04..2001-09-17; 13 in all; SPY 5). Years: calendar years with >= 126 sessions. Plateau: share of the declared neighbours (r2_idx_plateau_neighbours.csv) keeping half the centre's dMDD and dSR >= -0.10. Onsets: de-risk onsets of two-state rules, chain-merged within the rule's lookback (Tier A needs 30).

| Market / book | Rule | Avg exp. | Turn./yr | MDD rule / S / B&H | PC-1 dMDD 1x / 2x (pp) | PC-2 tail | PC-3 dSR (p, block) | PC-4 +/n (max share) | PC-5 years | PC-6 | Onsets | Verdict | Reason / if sufficient |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| KOSPI KRX ETF 3bp | SMA200 long/flat | 0.58 | 7.6 | -41% / -43% / -64% | +1.9 / -0.2 | 0.73 | +0.121 (0.051, 206) | 9/13 (30%) | 43% | 0.60 | 16 | INSUFFICIENT (sufficiency) | 16 de-clustered onsets < 30 (Tier A) -> if sufficient: REJECT (PC-1 at 1x (dMDD +1.9 pp)) |
| KOSPI KRX ETF 3bp | ENS multi-speed vote (20/60/120/250) | 0.58 | 12.0 | -34% / -43% / -64% | +8.9 / +8.4 | 0.77 | +0.186 (0.008, 178) | 8/13 (42%) | 60% | 0.75 | cont. | PASS |  |
| KOSPI KRX ETF 3bp | 12-month sign (monthly) | 0.58 | 1.4 | -39% / -43% / -64% | +4.7 / +4.6 | 0.88 | +0.082 (0.083, 211) | 8/13 (41%) | 63% | 0.20 | 11 | INSUFFICIENT (sufficiency) | 11 de-clustered onsets < 30 (Tier A) -> if sufficient: REVISE (PC-6 plateau 0.20 -> widen grid) |
| KOSPI KRX ETF 3bp | VT (SMA20 vol; KOSPI 20%, SPY 15%) | 0.85 | 2.6 | -51% / -58% / -64% | +6.5 / +6.4 | 0.70 | -0.001 (0.051, 186) | 6/13 (38%) | 70% | 1.00 | cont. | PASS |  |
| KOSPI KRX ETF 3bp | ENS x VT | 0.51 | 11.3 | -28% / -39% / -64% | +11.3 / +9.4 | 0.55 | +0.231 (0.007, 187) | 11/13 (32%) | 57% | 0.88 | cont. | REVISE | PC-5 years 57% -> extend history |
| KOSPI KRX ETF 3bp | ENS >=2 of 4 votes (binary) | 0.68 | 11.9 | -43% / -49% / -64% | +5.4 / +5.1 | 0.75 | +0.161 (0.017, 196) | 9/13 (38%) | 60% | n/e | 6 | INSUFFICIENT (sufficiency) | 6 de-clustered onsets < 30 (Tier A) -> if sufficient: PASS ((PC-6 not evaluated: no declared grid)) |
| KOSPI KRX ETF 3bp | EWMA(0.94) VT (benchmark 4) | 0.85 | 2.2 | -51% / -58% / -64% | +6.7 / +6.6 | 0.70 | -0.013 (0.079, 192) | 6/13 (36%) | 70% | n/e | cont. | PASS | (PC-6 not evaluated: no declared grid) |
| SPY US via KIS 50bp | SMA200 long/flat | 0.71 | 7.3 | -48% / -43% / -56% | -4.2 / -26.5 | 0.52 | -0.327 (0.863, 151) | 3/5 (75%) | 41% | 0.40 | 10 | INSUFFICIENT (sufficiency) | 10 de-clustered onsets < 30 (Tier A) -> if sufficient: REJECT (PC-1 at 1x (dMDD -4.2 pp); PC-3 point (dSR -0.327)) |
| SPY US via KIS 50bp | ENS multi-speed vote (20/60/120/250) | 0.68 | 11.9 | -53% / -42% / -56% | -10.7 / -44.3 | 0.54 | -0.530 (0.999, 146) | 5/5 (62%) | 45% | 0.00 | cont. | REJECT | PC-1 at 1x (dMDD -10.7 pp); PC-3 point (dSR -0.530) |
| SPY US via KIS 50bp | 12-month sign (monthly) | 0.74 | 0.8 | -34% / -45% / -56% | +11.0 / +11.0 | 0.64 | +0.055 (0.217, 170) | 2/5 (99%) | 64% | 0.60 | 6 | INSUFFICIENT (sufficiency) | 6 de-clustered onsets < 30 (Tier A) -> if sufficient: REJECT (PC-4 (2 of 5 episodes positive)) |
| SPY US via KIS 50bp | VT (SMA20 vol; KOSPI 20%, SPY 15%) | 0.86 | 2.9 | -50% / -51% / -56% | +0.3 / -3.9 | 0.76 | -0.071 (0.425, 130) | 4/5 (57%) | 68% | 0.50 | cont. | REJECT | PC-1 at 1x (dMDD +0.3 pp) |
| SPY US via KIS 50bp | ENS x VT | 0.63 | 11.1 | -47% / -39% / -56% | -7.9 / -43.9 | 0.47 | -0.541 (0.998, 147) | 5/5 (59%) | 50% | 0.00 | cont. | REJECT | PC-1 at 1x (dMDD -7.9 pp); PC-3 point (dSR -0.541) |
| SPY US via KIS 50bp | ENS >=2 of 4 votes (binary) | 0.77 | 10.8 | -58% / -47% / -56% | -11.9 / -36.3 | 0.57 | -0.365 (0.931, 149) | 4/5 (75%) | 50% | n/e | 5 | INSUFFICIENT (sufficiency) | 5 de-clustered onsets < 30 (Tier A) -> if sufficient: REJECT (PC-1 at 1x (dMDD -11.9 pp; not better than buy-and-hold); PC-3 point (dSR -0.365)) |
| SPY US via KIS 50bp | EWMA(0.94) VT (benchmark 4) | 0.86 | 2.6 | -49% / -51% / -56% | +1.6 / -2.7 | 0.76 | -0.054 (0.356, 136) | 4/5 (59%) | 68% | n/e | cont. | REJECT | PC-1 at 1x (dMDD +1.6 pp) |
| SPY Futures 5bp | SMA200 long/flat | 0.71 | 7.3 | -30% / -43% / -56% | +13.5 / +12.1 | 0.52 | -0.036 (0.428, 152) | 4/5 (72%) | 59% | 0.60 | 10 | INSUFFICIENT (sufficiency) | 10 de-clustered onsets < 30 (Tier A) -> if sufficient: INSUFFICIENT (inconclusive) (PC-3 p_ni 0.43 > 0.10; PC-4 concentration (72% from GFC)) |
| SPY Futures 5bp | ENS multi-speed vote (20/60/120/250) | 0.68 | 11.9 | -27% / -42% / -56% | +14.7 / +13.2 | 0.54 | +0.012 (0.257, 147) | 5/5 (55%) | 59% | 0.62 | cont. | INSUFFICIENT (inconclusive) | PC-3 p_ni 0.26 > 0.10; PC-4 concentration (55% from GFC) |
| SPY Futures 5bp | 12-month sign (monthly) | 0.74 | 0.8 | -34% / -45% / -56% | +11.0 / +11.0 | 0.64 | +0.082 (0.168, 170) | 2/5 (96%) | 64% | 1.00 | 6 | INSUFFICIENT (sufficiency) | 6 de-clustered onsets < 30 (Tier A) -> if sufficient: REJECT (PC-4 (2 of 5 episodes positive)) |
| SPY Futures 5bp | VT (SMA20 vol; KOSPI 20%, SPY 15%) | 0.86 | 2.9 | -47% / -51% / -56% | +3.8 / +3.4 | 0.76 | +0.025 (0.056, 129) | 4/5 (56%) | 68% | 1.00 | cont. | INSUFFICIENT (inconclusive) | PC-4 concentration (56% from GFC) |
| SPY Futures 5bp | ENS x VT | 0.63 | 11.1 | -25% / -39% / -56% | +14.3 / +12.8 | 0.47 | +0.027 (0.243, 148) | 5/5 (53%) | 59% | 0.88 | cont. | INSUFFICIENT (inconclusive) | PC-3 p_ni 0.24 > 0.10; PC-4 concentration (53% from GFC) |
| SPY Futures 5bp | ENS >=2 of 4 votes (binary) | 0.77 | 10.8 | -38% / -47% / -56% | +8.7 / +6.9 | 0.57 | +0.023 (0.264, 149) | 5/5 (62%) | 55% | n/e | 5 | INSUFFICIENT (sufficiency) | 5 de-clustered onsets < 30 (Tier A) -> if sufficient: INSUFFICIENT (inconclusive) (PC-3 p_ni 0.26 > 0.10; PC-4 concentration (62% from GFC)) |
| SPY Futures 5bp | EWMA(0.94) VT (benchmark 4) | 0.86 | 2.6 | -45% / -51% / -56% | +5.3 / +4.9 | 0.76 | +0.033 (0.035, 136) | 4/5 (57%) | 68% | n/e | cont. | INSUFFICIENT (inconclusive) | PC-4 concentration (57% from GFC) |

Notes. "n/e": no declared grid for a reference variant, so PC-6 is not evaluated. "cont.": graded rules (vote share, vol targets) are treated as continuous rules (episode-based sufficiency), as R4b did for VT20. Treated as a two-state switch (>= 2 of 4 votes) the trend vote has only 6 de-clustered onsets on KOSPI and 5 on SPY, i.e. INSUFFICIENT DATA by tier: with a 200-250-session lookback, 30 de-clustered onsets need more than 25 years of whipsaw-free history per market, so the Tier A count is close to unreachable for slow trend switches on one market; pooling markets "under a rule declared on the card" (spec 8.3) is the route.

KOSPI episode benefits vs S (rule minus S, cumulative return over the window, 3 bp):

| Episode (return dates) | B&H | SMA200 | ENS | TSM12 | VT | ENSxVT |
|---|---|---|---|---|---|---|
| 1997-98 (1997-06-16..1998-06-16) | -63.6% | +31.7% | +35.7% | +43.0% | +9.6% | +28.9% |
| 2000-01 (2000-01-05..2001-09-17) | -55.8% | +8.6% | +1.3% | +4.0% | +3.7% | +5.7% |
| GFC (2008-09-02..2009-03-09) | -24.2% | +13.4% | +8.2% | +13.5% | +9.2% | +8.3% |
| 2011 (2011-07-25..2011-09-30) | -18.5% | +3.8% | -1.4% | -7.6% | -0.5% | +0.0% |
| 2015-16 (2015-08-11..2016-02-11) | -6.9% | -0.3% | -0.2% | -1.8% | -1.3% | -0.7% |
| 2018Q4 (2018-09-21..2018-12-24) | -11.6% | +6.8% | +4.9% | +6.8% | -1.6% | +4.2% |
| 2020 crash (2020-02-20..2020-03-19) | -34.1% | +14.1% | +15.8% | +21.4% | +4.0% | +14.0% |
| 2022 (2022-01-04..2022-09-30) | -27.9% | +17.1% | +13.0% | +6.2% | -3.7% | +11.2% |
| Aug-2024 (2024-07-31..2024-08-09) | -5.5% | -7.8% | -3.0% | -2.4% | -3.3% | -3.3% |
| Dec-2024 (2024-12-04..2024-12-09) | -5.6% | +3.3% | +3.2% | +3.3% | -0.8% | +2.9% |
| Apr-2025 (2025-03-28..2025-04-09) | -12.0% | +5.2% | +3.8% | +7.1% | -1.4% | +3.0% |
| Mar-2026 (2026-02-27..2026-03-31) | -19.9% | -8.3% | -9.9% | -8.3% | +9.1% | +1.7% |
| Jul-2026 (2026-06-23..2026-07-30) | -38.6% | -13.8% | -7.5% | -14.5% | +21.5% | +11.5% |

## 3. How fragile are the verdicts? Start-date sensitivity

Same rules and checks, later starts (end fixed; spec windows straddling the start are truncated as R4b did; plateau taken from the primary run). Cells: verdict, with PC-1 dMDD (pp) and the step-5 p in brackets.

**KOSPI, KRX ETF 3bp**

| Start | SMA200 | ENS | TSM12 | VT | ENSxVT |
|---|---|---|---|---|---|
| 1996-06-03 | INSUFFICIENT (sufficiency) (+4.0; 0.18) | REVISE (+11.0; 0.05) | INSUFFICIENT (sufficiency) (+6.9; 0.26) | PASS (+5.7; 0.57) | REVISE (+13.3; 0.04) |
| 1996-09-02 | INSUFFICIENT (sufficiency) (+1.9; 0.23) | PASS (+8.9; 0.06) | INSUFFICIENT (sufficiency) (+4.7; 0.27) | PASS (+6.5; 0.51) | REVISE (+11.3; 0.05) |
| 1997-01-03 | INSUFFICIENT (sufficiency) (+1.9; 0.25) | PASS (+8.8; 0.07) | INSUFFICIENT (sufficiency) (+4.6; 0.34) | PASS (+9.5; 0.44) | REVISE (+11.2; 0.05) |
| 1999-01-04 | INSUFFICIENT (sufficiency) (-3.6; 0.43) | REVISE (+3.0; 0.20) | INSUFFICIENT (sufficiency) (+0.1; 0.51) | PASS (+4.4; 0.46) | REVISE (+6.2; 0.10) |
| 2001-01-02 | INSUFFICIENT (sufficiency) (-3.4; 0.73) | INSUFFICIENT (inconclusive) (+6.1; 0.37) | INSUFFICIENT (sufficiency) (+0.1; 0.61) | PASS (+10.6; 0.46) | REVISE (+7.2; 0.20) |
| 2006-01-02 | INSUFFICIENT (sufficiency) (-3.5; 0.70) | INSUFFICIENT (inconclusive) (+5.7; 0.42) | INSUFFICIENT (sufficiency) (-0.4; 0.58) | PASS (+11.6; 0.48) | INSUFFICIENT (inconclusive) (+7.3; 0.23) |
| 2011-01-03 | INSUFFICIENT (sufficiency) (-12.9; 0.84) | REJECT (-3.5; 0.68) | INSUFFICIENT (sufficiency) (-10.3; 0.72) | INSUFFICIENT (inconclusive) (+4.8; 0.65) | REJECT (-1.4; 0.41) |
| 2016-01-04 | INSUFFICIENT (sufficiency) (-12.4; 0.73) | REJECT (-2.9; 0.42) | INSUFFICIENT (sufficiency) (-10.9; 0.58) | INSUFFICIENT (inconclusive) (+4.4; 0.53) | REJECT (+0.9; 0.13) |

**SPY, Futures 5bp**

| Start | SMA200 | ENS | TSM12 | VT | ENSxVT |
|---|---|---|---|---|---|
| 1999-05-03 | INSUFFICIENT (sufficiency) (+13.5; 0.58) | INSUFFICIENT (inconclusive) (+14.7; 0.48) | INSUFFICIENT (sufficiency) (+11.0; 0.29) | INSUFFICIENT (inconclusive) (+3.8; 0.39) | INSUFFICIENT (inconclusive) (+14.3; 0.44) |
| 2001-01-02 | INSUFFICIENT (sufficiency) (+20.8; 0.38) | INSUFFICIENT (inconclusive) (+22.5; 0.32) | INSUFFICIENT (sufficiency) (+10.1; 0.26) | INSUFFICIENT (inconclusive) (+10.4; 0.30) | INSUFFICIENT (inconclusive) (+24.4; 0.30) |
| 2006-01-03 | INSUFFICIENT (sufficiency) (+24.0; 0.53) | INSUFFICIENT (inconclusive) (+25.0; 0.40) | INSUFFICIENT (sufficiency) (+13.9; 0.51) | INSUFFICIENT (inconclusive) (+15.2; 0.12) | INSUFFICIENT (inconclusive) (+26.8; 0.36) |
| 2011-01-03 | INSUFFICIENT (sufficiency) (+10.0; 0.79) | INSUFFICIENT (sufficiency) (+12.1; 0.75) | INSUFFICIENT (sufficiency) (-3.6; 0.99) | INSUFFICIENT (sufficiency) (+14.7; 0.39) | INSUFFICIENT (sufficiency) (+13.9; 0.72) |

**SPY, US via KIS 50bp**

| Start | SMA200 | ENS | TSM12 | VT | ENSxVT |
|---|---|---|---|---|---|
| 1999-05-03 | INSUFFICIENT (sufficiency) (-4.2; 0.95) | REJECT (-10.7; 1.00) | INSUFFICIENT (sufficiency) (+11.0; 0.36) | REJECT (+0.3; 0.82) | REJECT (-7.9; 1.00) |
| 2001-01-02 | INSUFFICIENT (sufficiency) (+12.2; 0.86) | REJECT (+3.9; 1.00) | INSUFFICIENT (sufficiency) (+10.1; 0.33) | INSUFFICIENT (inconclusive) (+7.4; 0.69) | REJECT (+8.2; 0.99) |
| 2006-01-03 | INSUFFICIENT (sufficiency) (+17.7; 0.87) | REJECT (+16.0; 0.99) | INSUFFICIENT (sufficiency) (+13.9; 0.59) | INSUFFICIENT (inconclusive) (+12.8; 0.36) | REJECT (+18.9; 0.98) |
| 2011-01-03 | INSUFFICIENT (sufficiency) (+1.5; 0.95) | INSUFFICIENT (sufficiency) (+5.1; 1.00) | INSUFFICIENT (sufficiency) (-3.6; 1.00) | INSUFFICIENT (sufficiency) (+14.0; 0.60) | INSUFFICIENT (sufficiency) (+4.4; 1.00) |

Reading: the KOSPI vol target keeps PC-1 in the range +4.4 to +11.6 pp across all starts; the trend rules lose their drawdown advantage over S once 1997-2001 drops out (dMDD first negative from the 1999 start for SMA200, 2006 for the 12-month sign, 2011 for ENS, 2011 for ENS x VT20). The maximum drawdown is a single-episode statistic, so PC-1 swings with small changes of start date (SMA200: +4.0 pp from 1996-06-03, +1.9 pp from 1996-09-02).

## 4. The same rules judged as OUTPERFORMANCE cards (why the existing gate rejected E1 and E2)

| Market / book | Rule | Sharpe rule / B&H | dSR | Step 5 p (10-sess.) | Step 5 p (PW block) | Step 2 SR 90% CI | Years + | CARD-O |
|---|---|---|---|---|---|---|---|---|
| KOSPI KRX ETF 3bp | SMA200 long/flat | 0.54 / 0.42 | +0.121 | 0.230 | 0.203 | [0.24, 0.85] | 43% | REJECT (step 5) |
| KOSPI KRX ETF 3bp | ENS multi-speed vote (20/60/120/250) | 0.60 / 0.42 | +0.186 | 0.061 | 0.064 | [0.30, 0.90] | 60% | steps 2/5/6/8 pass |
| KOSPI KRX ETF 3bp | 12-month sign (monthly) | 0.50 / 0.42 | +0.082 | 0.265 | 0.275 | [0.22, 0.80] | 63% | REJECT (step 5) |
| KOSPI KRX ETF 3bp | VT (SMA20 vol; KOSPI 20%, SPY 15%) | 0.42 / 0.42 | -0.001 | 0.509 | 0.535 | [0.11, 0.75] | 70% | REJECT (step 5) |
| KOSPI KRX ETF 3bp | ENS x VT | 0.65 / 0.42 | +0.231 | 0.048 | 0.046 | [0.33, 0.96] | 57% | REVISE (step 2/6/8) |
| SPY US via KIS 50bp | SMA200 long/flat | 0.03 / 0.35 | -0.327 | 0.955 | 0.942 | [-0.33, 0.40] | 41% | REJECT (step 5) |
| SPY US via KIS 50bp | ENS multi-speed vote (20/60/120/250) | -0.18 / 0.35 | -0.530 | 0.999 | 1.000 | [-0.51, 0.15] | 45% | REJECT (step 5) |
| SPY US via KIS 50bp | 12-month sign (monthly) | 0.41 / 0.35 | +0.055 | 0.362 | 0.409 | [0.10, 0.74] | 64% | REJECT (step 5) |
| SPY US via KIS 50bp | VT (SMA20 vol; KOSPI 20%, SPY 15%) | 0.28 / 0.35 | -0.071 | 0.821 | 0.841 | [-0.05, 0.62] | 68% | REJECT (step 5) |
| SPY US via KIS 50bp | ENS x VT | -0.19 / 0.35 | -0.541 | 0.998 | 1.000 | [-0.53, 0.14] | 50% | REJECT (step 5) |
| SPY Futures 5bp | SMA200 long/flat | 0.32 / 0.35 | -0.036 | 0.579 | 0.629 | [-0.02, 0.67] | 59% | REJECT (step 5) |
| SPY Futures 5bp | ENS multi-speed vote (20/60/120/250) | 0.37 / 0.35 | +0.012 | 0.479 | 0.534 | [0.04, 0.69] | 59% | REJECT (step 5) |
| SPY Futures 5bp | 12-month sign (monthly) | 0.43 / 0.35 | +0.082 | 0.294 | 0.356 | [0.12, 0.77] | 64% | REJECT (step 5) |
| SPY Futures 5bp | VT (SMA20 vol; KOSPI 20%, SPY 15%) | 0.38 / 0.35 | +0.025 | 0.392 | 0.450 | [0.05, 0.71] | 68% | REJECT (step 5) |
| SPY Futures 5bp | ENS x VT | 0.38 / 0.35 | +0.027 | 0.440 | 0.500 | [0.05, 0.70] | 59% | REJECT (step 5) |

A protective rule earns at most a few tenths of Sharpe over buy-and-hold, and a one-sided test at 10% needs about 1.3 standard errors (the bootstrap SE of dSR is 0.06 to 0.18 here). The vol targets have dSR of about 0 (step-5 p 0.39 to 0.82): they cut risk and return together, so they cannot pass step 5 however well they protect. That is QUANTGEN's E2 (SPY 0.63 vs 0.56, p 0.18; KODEX 200 0.53 vs 0.66). The trend rules pass step 5 only on KOSPI samples that start before 1998 (ENS and ENS x VT20 p 0.04 to 0.07); from 2001 the trend p-values are 0.13 to 0.84, and on SPY 0.29 to 1.00. QUANTGEN's E1 out-of-sample windows are post-2009, where the gate saw 0.84 vs 0.95 (US, p 0.75) and 0.52 vs 0.74 (KRX). The protective class asks a different question (drawdown vs S with a -0.10 Sharpe margin), and the KOSPI vol target can answer it with 30 years of data.

## 5. KOSPI 2026 windows (net 3 bp; returns dated after the start close through the end close)

| Window | buy-and-hold | SMA200 | ENS | TSM12 | VT | ENSxVT |
|---|---|---|---|---|---|---|
| 2026-01-02..06-22 melt-up (2026-01-02..2026-06-22) | +116.2% (w 1.00) | +116.2% (w 1.00) | +98.6% (w 0.97) | +116.2% (w 1.00) | +55.2% (w 0.50) | +50.9% (w 0.49) |
| 2026-06-22..07-30 crash (2026-06-23..2026-07-30) | -38.6% (w 1.00) | -37.9% (w 0.96) | -31.3% (w 0.79) | -38.6% (w 1.00) | -12.2% (w 0.27) | -9.8% (w 0.21) |
| 2026-07-31..09-29 rebound (2026-07-31..2026-09-29) | +22.8% (w 1.00) | +4.1% (w 0.97) | +8.3% (w 0.62) | +22.8% (w 1.00) | +6.2% (w 0.35) | +2.1% (w 0.23) |
| spec cost episode: H1-2026 bull (2026-01-02..2026-06-30) | +101.1% (w 1.00) | +101.1% (w 1.00) | +84.3% (w 0.97) | +101.1% (w 1.00) | +51.6% (w 0.49) | +47.3% (w 0.48) |
| spec cost episode: 2020 rebound (2020-03-20..2020-06-08) | +49.8% (w 1.00) | +7.5% (w 0.15) | +9.1% (w 0.25) | +0.0% (w 0.00) | +25.8% (w 0.64) | +8.3% (w 0.21) |
| PC-4 episode: Mar-2026 (2026-02-27..2026-03-31) | -19.9% (w 1.00) | -19.9% (w 1.00) | -21.3% (w 0.91) | -19.9% (w 1.00) | -7.9% (w 0.29) | -8.5% (w 0.26) |

w = average held exposure in the window. The melt-up and the rebound are the insurance premium: the vol target held about half the market through the melt-up and a third of it through the rebound; SMA200 sat out most of the +17.9% day of 2026-07-31.

## 6. Overlay vs sleeve: the same trend rule floored at 0.5

| Market / book | Trend | Form | Avg exp. | Max DD | dMDD vs own S | Tail | dSR | Years + | Verdict | 1997-98 | GFC | 2022 | Jul-2026 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| KOSPI KRX ETF 3bp | ENS | sleeve (0 allowed) | 0.58 | -34.1% | +8.9 | 0.77 | +0.186 | 60% | PASS | -6.9% | -5.1% | -3.9% | -31.3% |
| KOSPI KRX ETF 3bp | ENS | overlay clip[0.5,1] | 0.70 | -39.2% | +10.8 | 0.91 | +0.124 | 67% | REJECT | -39.2% | -11.4% | -15.1% | -31.3% |
| KOSPI KRX ETF 3bp | ENS | overlay 0.5+0.5x (E3 long/half) | 0.79 | -44.8% | +9.9 | 0.92 | +0.098 | 67% | REJECT | -40.4% | -13.8% | -16.5% | -35.0% |
| KOSPI KRX ETF 3bp | SMA200 | sleeve (0 allowed) | 0.58 | -41.5% | +1.9 | 0.73 | +0.121 | 43% | INSUFFICIENT (sufficiency) | -11.2% | +0.0% | +0.0% | -37.9% |
| KOSPI KRX ETF 3bp | SMA200 | overlay clip[0.5,1] | 0.79 | -41.5% | +13.4 | 0.90 | +0.091 | 57% | REVISE | -41.5% | -11.4% | -14.8% | -38.2% |
| KOSPI KRX ETF 3bp | SMA200 | overlay 0.5+0.5x (E3 long/half) | 0.79 | -41.5% | +13.4 | 0.90 | +0.091 | 57% | REVISE | -41.5% | -11.4% | -14.8% | -38.2% |
| KOSPI KRX ETF 3bp | TSM12 | sleeve (0 allowed) | 0.58 | -38.8% | +4.7 | 0.88 | +0.082 | 63% | INSUFFICIENT (sufficiency) | +0.0% | +0.0% | -10.9% | -38.6% |
| KOSPI KRX ETF 3bp | TSM12 | overlay clip[0.5,1] | 0.79 | -43.7% | +11.2 | 0.95 | +0.068 | 67% | REJECT | -37.9% | -11.4% | -19.6% | -38.6% |
| KOSPI KRX ETF 3bp | TSM12 | overlay 0.5+0.5x (E3 long/half) | 0.79 | -43.7% | +11.2 | 0.95 | +0.068 | 67% | REJECT | -37.9% | -11.4% | -19.6% | -38.6% |
| KOSPI KRX ETF 3bp | ENSxVT | sleeve (0 allowed) | 0.51 | -27.7% | +11.3 | 0.55 | +0.231 | 57% | REVISE | -9.7% | -3.4% | -3.9% | -9.8% |
| KOSPI KRX ETF 3bp | ENSxVT | overlay clip[0.5,1] | 0.61 | -29.4% | +15.4 | 0.64 | +0.156 | 63% | PASS | -28.6% | -5.4% | -15.1% | -9.8% |
| KOSPI KRX ETF 3bp | ENSxVT | overlay 0.5+0.5x (E3 long/half) | 0.68 | -36.2% | +13.0 | 0.65 | +0.115 | 67% | PASS | -30.8% | -7.1% | -16.6% | -11.0% |

| Market / book | Trend | Form | Avg exp. | Max DD | dMDD vs own S | Tail | dSR | Years + | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| SPY Futures 5bp | ENS | sleeve (0 allowed) | 0.68 | -27.2% | +14.7 | 0.54 | +0.012 | 59% | INSUFFICIENT (inconclusive) |
| SPY Futures 5bp | ENS | overlay clip[0.5,1] | 0.76 | -36.1% | +9.9 | 0.79 | -0.017 | 64% | INSUFFICIENT (inconclusive) |
| SPY Futures 5bp | ENS | overlay 0.5+0.5x (E3 long/half) | 0.84 | -38.5% | +11.1 | 0.81 | +0.032 | 64% | INSUFFICIENT (inconclusive) |
| SPY Futures 5bp | SMA200 | sleeve (0 allowed) | 0.71 | -30.0% | +13.5 | 0.52 | -0.036 | 59% | INSUFFICIENT (sufficiency) |
| SPY Futures 5bp | SMA200 | overlay clip[0.5,1] | 0.85 | -37.7% | +12.5 | 0.80 | +0.026 | 64% | INSUFFICIENT (inconclusive) |
| SPY Futures 5bp | SMA200 | overlay 0.5+0.5x (E3 long/half) | 0.85 | -37.7% | +12.5 | 0.80 | +0.026 | 64% | INSUFFICIENT (inconclusive) |
| SPY Futures 5bp | TSM12 | sleeve (0 allowed) | 0.74 | -34.1% | +11.0 | 0.64 | +0.082 | 64% | INSUFFICIENT (sufficiency) |
| SPY Futures 5bp | TSM12 | overlay clip[0.5,1] | 0.87 | -36.8% | +14.2 | 0.85 | +0.064 | 68% | REJECT |
| SPY Futures 5bp | TSM12 | overlay 0.5+0.5x (E3 long/half) | 0.87 | -36.8% | +14.2 | 0.85 | +0.064 | 68% | REJECT |
| SPY Futures 5bp | ENSxVT | sleeve (0 allowed) | 0.63 | -25.2% | +14.3 | 0.47 | +0.027 | 59% | INSUFFICIENT (inconclusive) |
| SPY Futures 5bp | ENSxVT | overlay clip[0.5,1] | 0.68 | -33.3% | +8.9 | 0.62 | -0.015 | 64% | INSUFFICIENT (inconclusive) |
| SPY Futures 5bp | ENSxVT | overlay 0.5+0.5x (E3 long/half) | 0.75 | -35.9% | +9.4 | 0.64 | +0.044 | 64% | INSUFFICIENT (inconclusive) |
| SPY US via KIS 50bp | ENS | sleeve (0 allowed) | 0.68 | -52.7% | -10.7 | 0.54 | -0.530 | 45% | REJECT |
| SPY US via KIS 50bp | ENS | overlay clip[0.5,1] | 0.76 | -52.0% | -6.0 | 0.79 | -0.310 | 59% | REJECT |
| SPY US via KIS 50bp | ENS | overlay 0.5+0.5x (E3 long/half) | 0.84 | -50.7% | -1.0 | 0.81 | -0.165 | 59% | REJECT |
| SPY US via KIS 50bp | SMA200 | sleeve (0 allowed) | 0.71 | -47.7% | -4.2 | 0.52 | -0.327 | 41% | INSUFFICIENT (sufficiency) |
| SPY US via KIS 50bp | SMA200 | overlay clip[0.5,1] | 0.85 | -44.9% | +5.4 | 0.80 | -0.094 | 59% | INSUFFICIENT (inconclusive) |
| SPY US via KIS 50bp | SMA200 | overlay 0.5+0.5x (E3 long/half) | 0.85 | -44.9% | +5.4 | 0.80 | -0.094 | 59% | INSUFFICIENT (inconclusive) |
| SPY US via KIS 50bp | TSM12 | sleeve (0 allowed) | 0.74 | -34.1% | +11.0 | 0.64 | +0.055 | 64% | INSUFFICIENT (sufficiency) |
| SPY US via KIS 50bp | TSM12 | overlay clip[0.5,1] | 0.87 | -36.9% | +14.1 | 0.85 | +0.052 | 68% | REJECT |
| SPY US via KIS 50bp | TSM12 | overlay 0.5+0.5x (E3 long/half) | 0.87 | -36.9% | +14.1 | 0.85 | +0.052 | 68% | REJECT |
| SPY US via KIS 50bp | ENSxVT | sleeve (0 allowed) | 0.63 | -47.4% | -7.9 | 0.47 | -0.541 | 50% | REJECT |
| SPY US via KIS 50bp | ENSxVT | overlay clip[0.5,1] | 0.68 | -47.9% | -5.7 | 0.62 | -0.427 | 55% | REJECT |
| SPY US via KIS 50bp | ENSxVT | overlay 0.5+0.5x (E3 long/half) | 0.75 | -44.0% | +1.3 | 0.64 | -0.235 | 59% | REJECT |

Protection lost by the floor (KOSPI, 3 bp). Absolute max drawdown: ENS -34.1% -> -39.2% (clip) / -44.8% (0.5 + 0.5x), i.e. 5.0 / 10.7 pp; ENS x VT20 -27.7% -> -29.4% / -36.2% (1.7 / 8.5 pp). In the 1997-98 crash the ENS sleeve lost -6.9% and the floored versions -39.2% / -40.4%. The fast Jul-2026 crash is unchanged (-31.3%), because trend was fully long. Measured against each version's own S, the floored overlay shows a LARGER dMDD (+8.9 -> +10.8 / +9.9 pp) because its S is more exposed; the PC-1 metric therefore does not register the lost protection, PC-2 does (tail 0.77 -> 0.91). Spec P2 (overlay multipliers in [0.5, 1]) would turn the trend sleeve into this weaker object; E3's reading of trend as a signal family (0 allowed) keeps the protection. With VT20 on top, the floored version passes every check including years (63% vs 57%), so a floored trend x VT20 is the candidate that fits both P2 and the protective class (its plateau was not evaluated).

## 7. Gate false-pass rates and power (Task 2)

Design: daily strategy returns with true annualised Sharpe SR at 15% vol; innovations = circular block bootstrap (126-session blocks) of de-meaned rebuilt-KOSPI returns (skew -0.07, kurtosis 10.4), plus a sign-flipped variant (same volatility clustering, no serial dependence in the mean) and iid normal; benchmark Sharpe 0.4 with correlation rho; 2,000 paths per cell (1,000 iid), 500 bootstrap resamples per path and test (the gate uses 2,000); Monte Carlo SE <= 1.1 pp. Step 2 = 90% CBB interval (10-session blocks) above 0; step 3 = deflated Sharpe >= 0.95 with N independent zero-edge trials (skew and kurtosis in the PSR); step 5 = paired CBB p <= 0.10 for dSR vs the benchmark; step 8 = >= 60% of 252-session years positive (compounded). Steps 1, 4, 6, 7 and 9 need a search or costs and are not simulated.

**False passes (true Sharpe 0), pass rate in %, years 10 / 18 / 30**

| Check | KOSPI bootstrap | sign-flip | iid normal |
|---|---|---|---|
| Step 2 (CBB 90% interval) | 8.0 / 6.9 / 6.8 | 5.0 / 4.2 / 4.7 | 3.9 / 4.8 / 5.0 |
| Step 2 (Lo iid SE) | 7.8 / 6.5 / 6.6 | 4.5 / 4.0 / 4.3 | 4.2 / 4.3 / 4.6 |
| Step 3, N = 1 | 7.7 / 6.4 / 6.6 | 4.6 / 4.0 / 4.3 | 4.2 / 4.3 / 4.6 |
| Step 3, N = 9 | 0.1 / 0.2 / 0.2 | 0.1 / 0.1 / 0.0 | 0.0 / 0.0 / 0.0 |
| Step 5, rho 0 (vs 0.4 benchmark) | 2.8 / 1.1 / 0.7 | 1.1 / 0.8 / 0.2 | 0.8 / 0.5 / 0.4 |
| Step 5, rho 0.9 | 0.0 / 0.0 / 0.0 | 0.0 / 0.0 / 0.0 | 0.0 / 0.0 / 0.0 |
| Step 8 (60% of years) | 23.8 / 10.2 / 4.7 | 31.2 / 16.9 / 10.5 | 29.5 / 16.9 / 10.1 |
| Steps 2+3+8, N = 1 (no benchmark) | 6.3 / 3.5 / 2.5 | 4.1 / 3.4 / 2.6 | 3.0 / 3.4 / 3.2 |
| Joint 2+3+5+8, N = 1, rho 0.5 | 0.5 / 0.1 / 0.0 | 0.2 / 0.1 / 0.0 | 0.0 / 0.1 / 0.0 |
| Step 5 with NO edge vs the benchmark (SR 0.4 = benchmark), rho 0.5 | 13.7 / 12.8 / 13.2 | 9.8 / 9.0 / 9.3 | 7.9 / 8.2 / 8.1 |
| Joint 2+3+5+8 with NO edge vs the benchmark (SR 0.4), N = 1, rho 0.5 | 9.4 / 9.8 / 10.9 | 6.2 / 7.0 / 8.3 | 5.6 / 7.1 / 7.2 |

Step 8 alone at Sharpe 0 (iid) by sample length: 5 y 43%, 8 y 28%, 10 y 30%, 12 y 13%, 15 y 22%, 20 y 16%, 30 y 10% (the jumps come from rounding 60% of Y up to whole years).

**Power (pass rate in %, KOSPI bootstrap design), years 10 / 18 / 30**

| True Sharpe | Step 2 | Step 3, N = 9 | Step 3, N = 27 | Step 5, rho 0.5 | Step 5, rho 0.9 | Step 8 | Joint, N = 1, rho 0.5 | Joint, N = 9, rho 0.9 |
|---|---|---|---|---|---|---|---|---|
| 0.3 | 28 / 39 / 51 | 3 / 4 / 8 | 1 / 2 / 3 | 8 / 7 / 5 | 3 / 2 / 1 | 54 / 43 / 42 | 5 / 5 / 4 | 0 / 0 / 0 |
| 0.5 | 49 / 68 / 85 | 9 / 17 / 36 | 4 / 8 / 20 | 21 / 22 / 26 | 34 / 41 / 48 | 76 / 74 / 80 | 16 / 19 / 23 | 5 / 9 / 20 |
| 0.8 | 80 / 95 / 100 | 30 / 59 / 86 | 17 / 41 / 74 | 52 / 66 / 80 | 93 / 98 / 100 | 94 / 96 / 99 | 45 / 63 / 79 | 29 / 58 / 86 |

**Years needed for 50% / 80% power (KOSPI bootstrap design; ">50" = not reached within 50 years)**

| True Sharpe | Step 2 | Step 3, N = 9 | Step 3, N = 100 | Step 5, rho 0 | Step 5, rho 0.5 | Step 5, rho 0.9 | Joint, N = 1, rho 0.5 |
|---|---|---|---|---|---|---|---|
| 0.3 | 28.7 / >50 | >50 / >50 | >50 / >50 | >50 / >50 | >50 / >50 | >50 / >50 | >50 / >50 |
| 0.4 | 15.8 / 40.3 | >50 / >50 | >50 / >50 | >50 / >50 | >50 / >50 | >50 / >50 | >50 / >50 |
| 0.5 | 10.5 / 25.7 | 39.5 / >50 | >50 / >50 | >50 / >50 | >50 / >50 | 31.9 / >50 | >50 / >50 |
| 0.6 | 7.0 / 17.9 | 27.9 / 48.0 | 48.4 / >50 | >50 / >50 | 38.8 / >50 | 6.6 / 24.0 | 41.5 / >50 |
| 0.8 | <=5 / 10.1 | 15.4 / 26.5 | 27.3 / 41.3 | 20.4 / >50 | 9.0 / 30.1 | <=5 / 6.0 | 12.5 / 31.2 |

IR 0.3 against the 0.4 benchmark (strategy Sharpe 0.4 + 0.3 x sqrt(2(1 - rho)), equal vols), step 5:

| rho | Strategy SR | Pass at 18 y (KOSPI / iid) | Years 50% / 80% | Pass at 50 y (iid) |
|---|---|---|---|---|
| 0.0 | 0.824 | 50% / 49% | 18.0 / >50 | 79% |
| 0.5 | 0.700 | 51% / 50% | 17.3 / >50 | 79% |
| 0.9 | 0.534 | 52% / 50% | 16.5 / >50 | 79% |

Reading. (i) The gate's false-pass rate is low because steps 2 and 3 are one-sided 5% tests and step 5 compares with a positive benchmark: a strategy with no edge at all almost never clears everything. (ii) Step 8 is the weak step: on its own it passes a quarter to a third of zero-Sharpe strategies over 8-10 years. (iii) Power is the binding problem: the gate's own trial count (step 3) and the benchmark test (step 5) push the 50%-power horizon for realistic edges (Sharpe 0.3-0.5, IR 0.1-0.3) past 20-50 years. (iv) Step-5 calibration at zero relative edge (r2_idx_gate_step5_calibration.csv): 13.3% rejections at a nominal 10% in the KOSPI design, 9.4% sign-flip, 8.5% iid (500 resamples, percentile p).

## 8. Shiller averaging bias and the adjustment to the long-history US conclusions (Task 3)

| Comparison | Rule | Sharpe avg / month-end | B&H avg / month-end | Sharpe inflation | Timing benefit avg / month-end | Max DD avg / month-end |
|---|---|---|---|---|---|---|
| SPY 1999-03..2021-03 | SMA10 | 0.83 / 0.73 | 0.46 / 0.43 | +0.10 | +0.36 / +0.30 | -19% / -17% |
| S&P 500 2000-03..2018-12 | SMA10 | 0.93 / 0.75 | 0.32 / 0.30 | +0.19 | +0.61 / +0.45 | -11% / -15% |
| Shiller avg vs SPY month-end 1999-2021 | SMA10 | 0.83 / 0.73 | 0.47 / 0.43 | +0.10 | +0.36 / +0.30 | -19% / -17% |
| SPY avg LAG1 vs month-end | SMA10 | 0.67 / 0.73 | 0.46 / 0.43 | -0.06 | +0.21 / +0.30 | -19% / -17% |
| SPY hybrid vs month-end | SMA10 | 0.71 / 0.73 | 0.43 / 0.43 | -0.02 | +0.29 / +0.30 | -20% / -17% |
| SPY 1999-03..2021-03 | TSM12 | 0.79 / 0.56 | 0.46 / 0.43 | +0.23 | +0.32 / +0.13 | -19% / -20% |
| S&P 500 2000-03..2018-12 | TSM12 | 0.80 / 0.56 | 0.32 / 0.30 | +0.25 | +0.48 / +0.26 | -12% / -17% |
| Shiller avg vs SPY month-end 1999-2021 | TSM12 | 0.79 / 0.56 | 0.47 / 0.43 | +0.23 | +0.32 / +0.13 | -19% / -20% |
| SPY avg LAG1 vs month-end | TSM12 | 0.69 / 0.56 | 0.46 / 0.43 | +0.13 | +0.23 / +0.13 | -19% / -20% |
| SPY hybrid vs month-end | TSM12 | 0.60 / 0.56 | 0.43 / 0.43 | +0.04 | +0.17 / +0.13 | -20% / -20% |
| SPY 1999-03..2021-03 | TSM12 L/S | 0.63 / 0.37 | 0.46 / 0.43 | +0.26 | +0.17 / -0.06 | -31% / -41% |
| S&P 500 2000-03..2018-12 | TSM12 L/S | 0.67 / 0.44 | 0.32 / 0.30 | +0.23 | +0.35 / +0.14 | -31% / -38% |
| Shiller avg vs SPY month-end 1999-2021 | TSM12 L/S | 0.63 / 0.37 | 0.47 / 0.43 | +0.27 | +0.17 / -0.06 | -31% / -41% |
| SPY avg LAG1 vs month-end | TSM12 L/S | 0.51 / 0.37 | 0.46 / 0.43 | +0.14 | +0.05 / -0.06 | -33% / -41% |
| SPY hybrid vs month-end | TSM12 L/S | 0.44 / 0.37 | 0.43 / 0.43 | +0.08 | +0.01 / -0.06 | -41% / -41% |

Monthly long/flat (TSM12 L/S long/short), 0% cash, gross. "avg" = monthly average of daily closes with average-to-average returns (what Shiller's column is); "LAG1" = signal one month older; "hybrid" = average-price signal, month-end returns. Lag-1 autocorrelation of monthly returns, SPY 1998-2021: 0.057 month-end vs 0.206 average; Shiller 1872-2026 0.274.

Long history (Shiller total return, 0% cash), standard vs LAG1:

| Period | Rule | Sharpe standard | Sharpe LAG1 | Max DD standard / LAG1 |
|---|---|---|---|---|
| 1872-2026 | buy-and-hold | 0.71 | 0.71 | -82% / -82% |
| 1872-2026 | SMA10 | 1.00 | 0.85 | -46% / -51% |
| 1872-2026 | TSM12 | 0.90 | 0.77 | -38% / -44% |
| 1872-2026 | TSM12 L/S | 0.54 | 0.34 | -59% / -80% |
| 1927-2018 | buy-and-hold | 0.69 | 0.69 | -82% / -82% |
| 1927-2018 | SMA10 | 1.01 | 0.87 | -46% / -51% |
| 1927-2018 | TSM12 | 0.92 | 0.78 | -38% / -44% |
| 1927-2018 | TSM12 L/S | 0.56 | 0.35 | -59% / -80% |
| 2010-2026 | buy-and-hold | 1.24 | 1.24 | -19% / -19% |
| 2010-2026 | SMA10 | 1.25 | 0.99 | -19% / -19% |
| 2010-2026 | TSM12 | 1.15 | 1.04 | -19% / -19% |
| 2010-2026 | TSM12 L/S | 0.86 | 0.68 | -27% / -28% |

How to adjust the round-1 long-history (1871-2026) conclusions. Measured where both are available, the averaged-price backtest overstates the rule's Sharpe by 0.10-0.19 (10-month SMA) and 0.23-0.25 (12-month sign), and its advantage over buy-and-hold by 0.06-0.16 and 0.19-0.22. The LAG1 fix is about right for the 10-month SMA (-0.06 vs month-end on SPY) but still too generous for the 12-month sign (+0.13). Rules of thumb for Shiller-based monthly trend results: take the LAG1 number for the 10-month SMA (month-end minus LAG1: +0.06 on SPY; round 1's French 1927-2018 check: -0.10), and LAG1 minus about 0.13 for 12-month momentum; treat drawdowns from averages as understated by up to 5.2 pp (S&P 2000-2018). Applied to round 1 (us_A_timing.csv, 1872-2026, T-bill-proxy cash): SMA10 0.78 standard / 0.61 LAG1 vs buy-and-hold 0.46, so the advantage falls from +0.31 to about +0.15 (round 1's French month-end check for 1927-2018 gives 0.55 vs the Shiller 0.79 standard and 0.64 LAG1, i.e. lower again); MOM12 0.67 standard / 0.52 LAG1, and LAG1 minus 0.13 gives about 0.39, i.e. no advantage over buy-and-hold (-0.07). The drawdown cut (about -82% to -45/-50%) survives on month-end data (French 1927-2018 SMA10 -43%). Round 1's bottom line ("a drawdown tool, not a return tool") stands and was, if anything, generous to 12-month momentum.

## 9. Verification of the E3 / E1 / P4 / P1 / E4 claims

| Id | Claim | Claimed | Ours | Status | Reason |
|---|---|---|---|---|---|
| E3-a | KOSPI multi-speed long/flat: Sharpe 0.60 vs 0.41 for the static book S; max drawdown -35% vs -48% | 0.60 vs 0.41; -35.3% vs -48.1% | 0.58 vs 0.40; -34.5% vs -45.2% (1996-06-03 start, 5 bp); primary window -34.5% vs -43.1% | CONFIRMED | Within tolerance on the window closest to E3's. The gap to S is +10.7 pp here (E3 +12.8) and +8.9 pp on the primary window at 3 bp: S's drawdown depends on the start and on the proxy (rebuilt buy-and-hold -67.1% from 1996-06, E3's -69.8%). |
| E3-b | KOSPI trend x VT20 beat S in 8 of 8 drawdowns; Sharpe 0.65 vs 0.41; max drawdown -26.7% vs -43.9% | 8/8; 0.65 vs 0.41; -26.7% vs -43.9% | 8/8; largest 34%; 0.61 vs 0.40; -29.0% vs -41.0% | CONFIRMED | 8 of 8 buy-and-hold under-water spells deeper than -20% (both windows) and the Sharpe reproduce, each drawdown within 3 pp; the gap to S is +12.0 pp rather than E3's +17.2 pp, and +11.3 pp on the primary window. On the spec 8.6 episode set it is 10/13 positive; largest 32%. |
| E3-c | No trend protection in the 22 Jun-30 Jul 2026 KOSPI crash (multi-speed trend -30.7% vs -38.0%) | -30.7% vs -38.0% | -31.3% vs -38.6% (exposure 1.00 on the first crash day) | CONFIRMED | Trend was fully long at the 22 Jun peak; VT20 alone gave -12.2% and trend x VT20 -9.8%. |
| E3-d | As an overlay floored at 0.5 the trend x VT20 drawdown improvement falls from +17.3 to +8.1 pp | +17.3 -> +8.1 pp | +13.3 -> +15.2 pp (vs own S) [1996-06 start]; +11.3 -> +13.0 pp (vs own S) [primary]; absolute max DD -27.7% -> -36.4%; overlay MDD vs the sleeve's S +4.6 pp; tail ratio 0.55 -> 0.65; KOSPI 3 bp | NOT REPRODUCED | Measured against its own same-exposure S, the floored overlay improves MORE (S also carries more exposure). What the floor costs is absolute protection: max drawdown and the slow-bear episodes (see section 6). |
| E3-e | Shiller monthly averages inflate trend Sharpe (SPY lag-1 autocorrelation 0.206 vs 0.057; 12m L/S 0.62 vs 0.35; 10m SMA 0.82 vs 0.70) | 0.206 vs 0.057; 0.62 vs 0.35; 0.82 vs 0.70 | 0.206 vs 0.057; 0.63 vs 0.37; 0.83 vs 0.73 | CONFIRMED | SPY 1998-02..2021-03 for the autocorrelation; rules 1999-03..2021-03. |
| E1-a | 12-month long/flat rule, return/vol 1.32 vs 0.81 (1992-2014) but 1.02 vs 1.16 (2015-2026), Shiller | 1.32 vs 0.81; 1.02 vs 1.16 | Shiller: 1.32 vs 0.81; 1.02 vs 1.16. Month-end SPY 2015-01..2021-03: 0.44 vs 0.78 (price), 0.56 vs 0.90 (+1.8% dividends); Shiller same months 0.77 vs 1.07 | CONFIRMED | Exact on Shiller (signal = 12-month change of the average price, total-return P&L, flat = 0). The post-2015 shortfall is larger on month-end SPY. The pre-2015 level is averaging-inflated: on 1999-03..2014-12 month-end SPY gives 0.62 vs 0.29 where Shiller averages give 1.04 vs 0.44. |
| P4-a | A strategy with no edge passes the 60%-of-years rule 36-38% of the time over 8-10 years | 36% (8 y), 38% (10 y) | true Sharpe 0, 15% vol: 28% / 30% (iid), 29% / 31% (KOSPI sign-flip), 24% / 24% (KOSPI bootstrap); 12 y 13%, 20 y 16% (iid) | PARTLY | 36-38% is the binomial value for P(year > 0) = 0.5, i.e. a zero MEDIAN year (Sharpe about +0.075 at 15% vol). At zero Sharpe the compounding drag gives P(year > 0) = 0.47 (lognormal formula 30% / 31%), and KOSPI-like volatility clustering lowers it further. The rate also jumps with the year count (rounding of 60%). |
| P1-a | A true Sharpe of 0.4 needs about 18 out-of-sample years for its 90% interval to exclude zero | about 18 years | pass rate at 18 y: 52% (iid), 53% (sign-flip), 54% (KOSPI bootstrap); years for 50% / 80%: 16.9 / 40.4 (iid), 16.2 / 37.4 (sign-flip), 15.8 / 40.3 (KOSPI) | PARTLY | 18 years is the coin-flip horizon (about 50% power, the expected-value calculation with the Lo SE); passing reliably (80%) needs roughly 37-43 years. |
| E4-a | An IR of 0.3 needs about 18 years to pass the benchmark step (gate step 5) | about 18 years | rho 0.0 (strategy SR 0.82): pass at 18 y 50% (KOSPI) / 49% (iid), 50% at 18.0 y, 80% at >50 y; rho 0.5 (strategy SR 0.70): pass at 18 y 51% (KOSPI) / 50% (iid), 50% at 17.3 y, 80% at >50 y; rho 0.9 (strategy SR 0.53): pass at 18 y 52% (KOSPI) / 50% (iid), 50% at 16.5 y, 80% at >50 y | PARTLY | 18 years gives about a 50% chance of passing step 5 (the analytic median horizon (1.2816 / 0.3)^2 = 18.2); 80% power needs about 50 years (79% at 50 years, iid). |

## 10. Validation

| Test | What | Passed | Detail |
|---|---|---|---|
| V1 | KOSPI: weights at t unchanged when prices after t are perturbed | True | 265/265 spec x cut-date pairs (53 specs, 5 cuts) |
| V1b | KOSPI: the same test detects a planted look-ahead rule | True | 5/5 cut dates |
| V1 | SPY: weights at t unchanged when prices after t are perturbed | True | 265/265 spec x cut-date pairs (53 specs, 5 cuts) |
| V1b | SPY: the same test detects a planted look-ahead rule | True | 5/5 cut dates |
| V2 | weight decided at the close of t earns only r_{t+1} | True | [ 0.   -0.    0.03  0.   -0.    0.  ] |
| V2b | cost = c x |dw| charged on the earning day; initial entry not charged | True | [0. 0. 0. 0. 0. 0.] |
| V2c | engine held weight = decided weight lagged one session (KOSPI SMA200) | True | 7518 sessions compared |
| V3 | macro spec 9.3 KOSPI VT20 golden values on the rebuilt KOSPI (2016-01-04..2026-09-29) | True | 30/30 within Level-1 tolerance, 30/30 within Level-2 |
| V4 | R4b's Korea VT20 protective card (spec 8.9) reproduced by this harness | True | 12/12 items within tolerance; verdict INSUFFICIENT DATA (inconclusive) |
| V5 | bootstrap p-values identical on re-run (seed 11) | True | pc3_p_ni=0.0070, pc3_p_ni_block10=0.0085, o_step5_p_block10=0.0480, pc3_dsr_ci90_lo=0.0047, o_step2_sr_ci90_lo=0.3290 |
| V5b | gate simulation identical on re-run; per-path seeds reproduce a subset | True | rerun identical=True, subset identical=True |
| V6 | E1's Shiller 12-month-sign table reproduced (rounding tolerance) | True | 1927-01..1991-12: R/V 0.82 vs 0.66; 1992-01..2014-12: R/V 1.32 vs 0.81; 2015-01..2026-09: R/V 1.02 vs 1.16 |
| V7 | iid-normal simulated pass rates vs analytic normal approximations (steps 2, 3, 5) | True | share of 880 cells within 3 MC SE: 0.993; max abs gap 0.044 |
| V7b | iid-normal step-8 pass rates vs the lognormal-binomial formula | True | max abs gap 0.034 |

Golden values (spec 9.3, KOSPI VT20, rebuilt KOSPI 2016-01-04..2026-09-29 vs ^KS11 to 2026-10-02): 30 of 30 within Level-1 tolerance. Largest gaps: dMDD VT20 vs S, gross (pp) 4.458 vs 4.500; dMDD VT20 vs S, net 3 bp (pp) 4.428 vs 4.400; window 30 Jul-30 Sep 2026: buy-and-hold 0.228 vs 0.222; Buy-and-hold Sharpe 0.628 vs 0.634. The Sharpe gaps (-0.005) come from the 3 missing sessions (30 Sep-2 Oct) and the rebuilt index; the 30 Jul-30 Sep window ends one session early. R4b's Korea VT20 card (spec 8.9) is reproduced item by item (r2_idx_r4b_crosscheck.csv: dMDD +4.4 pp, tail 0.82, PW block 101, p_ni 0.21 / 0.24, 3 of 9 episodes, Jul-2026 59%, years 73%, plateau 0.63, INSUFFICIENT DATA). SHA-256 of every result file: r2_idx_validation.csv (test V8).

## 11. Caveats

- **Indicative, in-sample, full-history verdicts.** No walk-forward, no PBO (nothing was searched); the centre rules and grids come from QUANTGEN's prior design, E3 and the macro spec. The start-date sweep (section 3) is the honest error bar: several verdicts flip with the window.
- **Price returns, 0% cash.** Dividends (KOSPI about 1-2%, SPY about 1.8% a year) and T-bill income are excluded; with 0% cash S and buy-and-hold have the same Sharpe. Adding both would lower every trend rule's Sharpe gap slightly in high-yield years and leave the drawdown checks almost unchanged.
- **Rebuilt KOSPI.** Within 0.23% of official closes at the 2007-2026 check dates; before 2007 unchecked. The 1997-98 and 2000-01 KOSPI windows were declared from buy-and-hold highs and lows (1997-06-14..1998-06-16, 2000-01-04..2001-09-17); KRX Saturday sessions before 1998-12 count as sessions.
- **Classification choices that move verdicts:** treating the vote share as continuous (no onset count) and excluding Sep-2026 from the KOSPI episode set (it is a US rates episode; KOSPI rose 0.7% in that window) were declared before the run. PC-4 counts a benefit vs S, not vs buy-and-hold.
- **Gate simulation.** 500 resamples per path (not 2,000), percentile p-values, one benchmark (Sharpe 0.4, equal vol), N treated as independent trials (correlated revisions would deflate less), calendar years = 252-session blocks. Steps 1, 4, 6, 7, 9 are not simulated, so real false-pass rates of a searched card would be higher than the joint numbers here.
- **Averaging study** covers 1999-2021 only (daily data); the long-history adjustment extrapolates that ratio and the round-1 French month-end comparison.

## 12. Files

- Scripts: `r2_idx_common.py` (loaders, rules, engine, CARD-P checks), `r2_idx_01_protective.py` (Task 1), `r2_idx_02_gate_sim.py` (Task 2), `r2_idx_03_averaging.py` (Task 3), `r2_idx_04_validation.py`, `r2_idx_05_summary.py`, `r2_idx_run_all.py` (runner; `--skip-sim` reuses the simulation).
- Results: `r2_idx_protective_scorecard.csv`, `r2_idx_protective_episodes.csv`, `r2_idx_plateau_neighbours.csv`, `r2_idx_start_date_sensitivity.csv`, `r2_idx_outperformance.csv`, `r2_idx_windows.csv`, `r2_idx_overlay_vs_sleeve.csv`, `r2_idx_e3_checks.csv`, `r2_idx_gate_sim.csv` (long: innovations, years, true_sr, rho, n_trials, step, pass_rate, mc_se, analytic_iid), `r2_idx_gate_power_years.csv`, `r2_idx_gate_step5_calibration.csv`, `r2_idx_gate_source_diagnostics.csv`, `r2_idx_averaging_rules.csv`, `r2_idx_averaging_bias.csv`, `r2_idx_averaging_autocorr.csv`, `r2_idx_e1_checks.csv`, `r2_idx_golden_values.csv`, `r2_idx_r4b_crosscheck.csv`, `r2_idx_claims.csv`, `r2_idx_key_numbers.csv`, `r2_idx_validation.csv`.
- Charts (JSON): `r2_idx_chart_a_kospi_2024_2026.json` (daily NAV and exposure: buy-and-hold, trend, VT20, trend x VT20, SMA200), `r2_idx_chart_b_scorecard.json` (PC-1..PC-7 and verdict per rule, market and book), `r2_idx_chart_c_gate_pass_rates.json` (pass rate vs years by true Sharpe; SR 0 highlighted).
