# Choosing Z_BOUND: the sweep

952 paired simulations: parameter sets ['worked', 'typical'] x horizons [21, 126, 252] x nu [2.5, 3.1, 4.0, 6.0, 8.0, 12.0, 30.0] x integer bounds 3..100; 50,000 paths each, rf 3%, seed 7. Statistics' standard errors are at the app's default 5,000 paths.

Selection rule: the floor is the smallest A with at most 0.1 out-of-bound days per year at every nu (reproducibility) and every paired change below one 5,000-path standard error for nu >= 4 (invisibility where the tail is estimable); the top is the largest A, contiguously from the floor, at which the seed-averaged signed shortfall of the mean stays inside the 5,000-path standard error in every stage-2 configuration (the martingale property holds at the app's resolution). Z_BOUND = the midpoint of the band.

**Chosen: Z_BOUND = 22** (band 14..30: floor from stage 1, top from stage 2)

## Stage 2: seed-averaged shortfall of the mean, in 5,000-path standard errors

| A | worked h=126 nu=2.5 | worked h=126 nu=3.1 | typical h=126 nu=2.5 | typical h=126 nu=3.1 | worked h=252 nu=2.5 | worked h=252 nu=3.1 | passes |
|---|---|---|---|---|---|---|---|
| 12 | +0.05 (±0.06) | +0.03 (±0.03) | +0.05 (±0.06) | +0.03 (±0.05) | +0.01 (±0.11) | +0.00 (±0.19) | yes |
| 14 | +0.07 (±0.05) | +0.02 (±0.04) | +0.05 (±0.06) | +0.05 (±0.05) | -0.02 (±0.12) | +0.02 (±0.20) | yes |
| 16 | +0.03 (±0.04) | -0.06 (±0.06) | +0.02 (±0.04) | +0.01 (±0.08) | -0.09 (±0.14) | -0.06 (±0.19) | yes |
| 18 | +0.03 (±0.06) | -0.05 (±0.07) | +0.04 (±0.06) | +0.01 (±0.08) | -0.09 (±0.15) | -0.07 (±0.19) | yes |
| 20 | -0.04 (±0.05) | -0.10 (±0.07) | +0.04 (±0.06) | -0.03 (±0.09) | -0.16 (±0.14) | -0.13 (±0.17) | yes |
| 22 | -0.08 (±0.06) | -0.12 (±0.07) | +0.05 (±0.05) | -0.04 (±0.09) | -0.23 (±0.14) | -0.19 (±0.16) | yes |
| 24 | -0.14 (±0.05) | -0.15 (±0.06) | +0.02 (±0.04) | -0.08 (±0.09) | -0.31 (±0.15) | -0.23 (±0.15) | yes |
| 26 | -0.19 (±0.06) | -0.19 (±0.07) | +0.03 (±0.04) | -0.09 (±0.10) | -0.39 (±0.16) | -0.28 (±0.15) | yes |
| 28 | -0.28 (±0.07) | -0.22 (±0.07) | -0.02 (±0.05) | -0.08 (±0.10) | -0.51 (±0.16) | -0.32 (±0.15) | yes |
| 30 | -0.38 (±0.08) | -0.26 (±0.07) | -0.05 (±0.05) | -0.09 (±0.10) | -0.63 (±0.16) | -0.36 (±0.15) | yes |
| 35 | -0.64 (±0.07) | -0.37 (±0.06) | -0.19 (±0.05) | -0.12 (±0.11) | -1.01 (±0.16) | -0.53 (±0.15) | no |
| 40 | -0.96 (±0.06) | -0.52 (±0.06) | -0.29 (±0.05) | -0.19 (±0.11) | -1.47 (±0.15) | -0.75 (±0.15) | no |

A cell is (mean over 5 seeds of mean(P_T)/spot - exp(rf T)) / SE_5000, ± its own seed standard error in the same units; a negative value is the shortfall a heavy right tail produces in a finite sample. The martingale test holds at the app's resolution while |cell| < 1.

## Stage 1: worst case over all configurations, per bound

| A | gap_se (max, all nu) | d_max (max, nu >= 4) | d_cvar95 (nu = 3.1) | d_cvar95 (nu = 2.5) | out-of-bound days/yr (nu = 2.5) | var_in (nu = 3.1) | var_in (nu = 2.5) | se5k_mean (max) | ref_gap_se (max) | feasible |
|---|---|---|---|---|---|---|---|---|---|---|
| 3 | 2.82 | 32.18 | 37.0 | 51.3 | 2.951 | 0.633 | 0.460 | 0.0047 | 10.6 | no |
| 4 | 2.43 | 15.98 | 22.3 | 33.6 | 1.471 | 0.721 | 0.527 | 0.0049 | 7.8 | no |
| 5 | 2.55 | 14.99 | 18.8 | 23.2 | 0.851 | 0.777 | 0.575 | 0.0050 | 6.0 | no |
| 6 | 2.42 | 5.36 | 13.0 | 18.4 | 0.543 | 0.815 | 0.610 | 0.0050 | 5.2 | no |
| 8 | 2.55 | 3.15 | 9.5 | 14.9 | 0.266 | 0.864 | 0.661 | 0.0050 | 5.2 | no |
| 10 | 2.39 | 1.71 | 7.8 | 12.8 | 0.153 | 0.893 | 0.697 | 0.0051 | 3.5 | no |
| 11 | 2.44 | 1.46 | 7.7 | 12.7 | 0.120 | 0.903 | 0.711 | 0.0051 | 2.7 | no |
| 12 | 2.69 | 1.35 | 7.1 | 12.1 | 0.097 | 0.912 | 0.723 | 0.0051 | 2.0 | no |
| 13 | 2.32 | 1.04 | 6.1 | 12.7 | 0.079 | 0.919 | 0.734 | 0.0052 | 1.8 | no |
| 14 | 2.44 | 0.93 | 5.8 | 11.7 | 0.066 | 0.925 | 0.743 | 0.0052 | 1.8 | yes |
| 15 | 2.49 | 0.93 | 5.0 | 10.7 | 0.056 | 0.931 | 0.752 | 0.0052 | 1.8 | yes |
| 16 | 2.78 | 0.93 | 5.3 | 10.6 | 0.047 | 0.936 | 0.760 | 0.0052 | 1.8 | yes |
| 17 | 2.73 | 0.66 | 4.7 | 10.4 | 0.041 | 0.940 | 0.767 | 0.0052 | 1.8 | yes |
| 18 | 2.73 | 0.54 | 4.5 | 9.7 | 0.035 | 0.943 | 0.773 | 0.0052 | 1.9 | yes |
| 19 | 2.66 | 0.40 | 4.2 | 9.1 | 0.031 | 0.947 | 0.779 | 0.0052 | 2.2 | yes |
| 20 | 2.80 | 0.39 | 3.6 | 8.8 | 0.027 | 0.949 | 0.785 | 0.0052 | 2.6 | yes |
| 21 | 2.95 | 0.35 | 3.0 | 7.9 | 0.024 | 0.952 | 0.790 | 0.0052 | 2.8 | yes |
| 22 | 3.01 | 0.35 | 2.8 | 7.8 | 0.021 | 0.954 | 0.795 | 0.0052 | 3.1 | yes |
| 23 | 2.95 | 0.31 | 2.6 | 7.7 | 0.019 | 0.957 | 0.800 | 0.0052 | 3.4 | yes |
| 24 | 3.21 | 0.29 | 2.6 | 6.4 | 0.017 | 0.959 | 0.804 | 0.0052 | 3.7 | yes |
| 26 | 3.20 | 0.19 | 2.3 | 7.0 | 0.014 | 0.962 | 0.811 | 0.0052 | 4.5 | yes |
| 28 | 3.57 | 0.17 | 1.7 | 6.8 | 0.012 | 0.965 | 0.818 | 0.0052 | 5.4 | yes |
| 30 | 3.92 | 0.16 | 1.5 | 8.3 | 0.010 | 0.968 | 0.824 | 0.0052 | 6.2 | yes |
| 35 | 5.02 | 0.14 | 1.2 | 9.2 | 0.007 | 0.973 | 0.837 | 0.0051 | 8.0 | yes |
| 40 | 6.71 | 0.15 | 1.2 | 8.6 | 0.005 | 0.976 | 0.848 | 0.0051 | 9.8 | yes |
| 50 | 11.15 | 0.10 | 0.7 | 3.1 | 0.003 | 0.982 | 0.864 | 0.0050 | 13.4 | yes |
| 60 | 15.70 | 0.03 | 0.4 | 1.4 | 0.002 | 0.985 | 0.876 | 0.0050 | 17.3 | yes |
| 80 | 25.20 | 0.00 | 0.1 | 0.5 | 0.001 | 0.989 | 0.892 | 0.0050 | 25.8 | yes |
| 100 | 35.02 | 0.00 | 0.1 | 0.2 | 0.000 | 0.991 | 0.904 | 0.0050 | 35.4 | yes |

## Per nu at the chosen bound (worked-fit parameters, 126 sessions)

| nu | gap_se | d_median | d_q05 | d_q95 | d_ploss | d_var95 | d_cvar95 | out/yr | var_in | se5k_mean | ref_gap_se |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2.5 | 3.01 | 0.17 | 1.60 | 0.84 | 0.14 | 1.60 | 3.59 | 0.021 | 0.795 | 0.0028 | 3.1 |
| 3.1 | 2.41 | 0.05 | 0.76 | 0.48 | 0.05 | 0.76 | 2.25 | 0.008 | 0.954 | 0.0033 | 2.4 |
| 4.0 | 1.52 | 0.00 | 0.09 | 0.06 | 0.00 | 0.09 | 0.28 | 0.002 | 0.994 | 0.0035 | 1.5 |
| 6.0 | 0.57 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.000 | 1.000 | 0.0034 | 0.6 |
| 8.0 | 0.21 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.000 | 1.000 | 0.0034 | 0.2 |
| 12.0 | 0.32 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.000 | 1.000 | 0.0034 | 0.3 |
| 30.0 | 0.05 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.000 | 1.000 | 0.0034 | 0.0 |

Columns: gap_se = |mean(P_T)/spot - exp(rf T)| in MC standard errors with the exact bounded correction; d_<stat> = paired change versus the unbounded draw, in that statistic's 5,000-path standard errors; out/yr = expected days per year beyond the bound under the fitted t; var_in = variance of the bounded innovation; se5k_mean = relative standard error of the mean at 5,000 paths; ref_gap_se = the unbounded run's own gap (no exact correction exists for it).

Reading the tables: stage 2 caps the bound (estimability of the mean at the app's resolution); reproducibility floors it; for nu >= 4 the bound is invisible inside the band; for nu < 4 the bound lowers CVaR95 by the once-a-century days it refuses and the fan's long-run vol by sqrt(var_in (1-alpha-beta)/(1-alpha var_in-beta)), both stated in the Quant Lab's bound note. gap_se in stage 1 is a single-seed max over 28 cells and is reported, not used: it sits on its noise plateau (2.3-3.0) up to about A = 23 and rises only beyond.
