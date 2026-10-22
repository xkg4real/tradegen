# Drift estimator fitness check

Script: `docs/drift_study.py`. Every number below is in `docs/drift_study/results.csv` (columns pass, section, method, h, group, metric, value).

Reproduce: `python docs/drift_study.py` (prices and DGS3MO are cached as CSV under the scratchpad `drift_prices/` folder; the script prints the md5 of results.csv, which is identical on a cached re-run).

## Universe and protocol

- Tickers kept (17): SPY (5453 sessions from 2005-01-03), QQQ (5453 sessions from 2005-01-03), IWM (5453 sessions from 2005-01-03), AAPL (5453 sessions from 2005-01-03), MSFT (5453 sessions from 2005-01-03), NVDA (5453 sessions from 2005-01-03), TSLA (4072 sessions from 2010-06-29), XOM (5453 sessions from 2005-01-03), JPM (5453 sessions from 2005-01-03), KO (5453 sessions from 2005-01-03), TLT (5453 sessions from 2005-01-03), GLD (5453 sessions from 2005-01-03), EURUSD=X (5624 sessions from 2005-01-03), USDJPY=X (5624 sessions from 2005-01-03), USDKRW=X (5622 sessions from 2005-01-03), EWY (5453 sessions from 2005-01-03), 005930.KS (5366 sessions from 2005-01-03)
- Dropped (< 2000 sessions): none
- Risk-free: FRED DGS3MO (3-month T-bill, forward-filled by date). The same USD rate is used for 005930.KS and the FX crosses (assumption: no local-currency curve in this study).
- ERP assumption: 0.04 for equities/ETFs (incl. EWY, 005930.KS), 0.01 for TLT/GLD, 0.00 for FX. CAPM beta vs SPY only where the calendar matches (US-listed names incl. EWY); skipped for 005930.KS, TLT, GLD and FX.
- Origins: every 21 SPY sessions; each ticker uses its last session on or before that date. pass_1260 requires 1260 prior returns and 252 forward sessions at every origin, so all methods and horizons share the same 3135 (ticker, origin) pairs. pass_504 relaxes the look-back to 504 (sample_1260 is then skipped where unavailable).
- Forecast F = mu*h/252; realised R = log(P[t+h]/P[t]); errors are F - R. Skill = 1 - MSE/MSE_zero. Band = F +/- 1.645*sigma_504*sqrt(h/252); coverage is the share of R inside it (target 0.90).
- Shrink: tau = 0.05, SE^2 = sigma^2/2; mean w = 0.151 overall bond_gold 0.185, equity 0.094, fx 0.362, korea 0.074.
- DM test: loss differential (squared error of method minus sample_504) averaged across tickers at each origin date, then Newey-West t-stat with lag h/21 on that time series (origins overlap for h > 21). |t| > 1.96 is the usual 5% line; negative t = method beats sample_504.

## Pooled results (pass_1260)

### h = 21

| method | n | rmse | mae | bias | skill_vs_zero | hit_rate | coverage_90 |
|---|---|---|---|---|---|---|---|
| sample_1260 | 3135 | 0.0704 | 0.0468 | -0.0007 | +0.016 | 0.560 | 0.925 |
| ewma_252 | 3135 | 0.0709 | 0.0472 | -0.0004 | +0.001 | 0.546 | 0.925 |
| zero | 3135 | 0.0710 | 0.0472 | -0.0101 | +0.000 |  | 0.922 |
| rf_erp | 3135 | 0.0712 | 0.0471 | -0.0094 | -0.007 | 0.545 | 0.921 |
| shrink | 3135 | 0.0716 | 0.0474 | -0.0111 | -0.017 | 0.500 | 0.922 |
| sample_504 | 3135 | 0.0716 | 0.0476 | -0.0003 | -0.018 | 0.546 | 0.922 |
| rf | 3135 | 0.0717 | 0.0475 | -0.0119 | -0.020 | 0.475 | 0.923 |
| momentum_12_1 | 3135 | 0.0718 | 0.0477 | -0.0028 | -0.023 | 0.525 | 0.921 |
| sample_252 | 3135 | 0.0727 | 0.0483 | +0.0003 | -0.050 | 0.535 | 0.922 |
| sample_126 | 3135 | 0.0754 | 0.0503 | -0.0001 | -0.130 | 0.539 | 0.908 |
| capm | 2002 | 0.0834 | 0.0570 | -0.0130 | -0.381 | 0.546 | 0.922 |

### h = 63

| method | n | rmse | mae | bias | skill_vs_zero | hit_rate | coverage_90 |
|---|---|---|---|---|---|---|---|
| sample_1260 | 3135 | 0.1223 | 0.0816 | -0.0030 | +0.049 | 0.607 | 0.927 |
| ewma_252 | 3135 | 0.1247 | 0.0836 | -0.0020 | +0.012 | 0.585 | 0.920 |
| zero | 3135 | 0.1254 | 0.0850 | -0.0312 | +0.000 |  | 0.927 |
| rf_erp | 3135 | 0.1266 | 0.0844 | -0.0293 | -0.018 | 0.569 | 0.928 |
| shrink | 3135 | 0.1286 | 0.0862 | -0.0341 | -0.050 | 0.491 | 0.923 |
| rf | 3135 | 0.1291 | 0.0868 | -0.0366 | -0.059 | 0.447 | 0.923 |
| momentum_12_1 | 3135 | 0.1292 | 0.0870 | -0.0095 | -0.062 | 0.549 | 0.904 |
| sample_504 | 3135 | 0.1295 | 0.0867 | -0.0018 | -0.065 | 0.566 | 0.909 |
| sample_252 | 3135 | 0.1334 | 0.0896 | -0.0001 | -0.131 | 0.556 | 0.895 |
| sample_126 | 3135 | 0.1439 | 0.0983 | -0.0013 | -0.316 | 0.542 | 0.874 |
| capm | 2002 | 0.1474 | 0.1019 | -0.0398 | -0.380 | 0.571 | 0.929 |

### h = 126

| method | n | rmse | mae | bias | skill_vs_zero | hit_rate | coverage_90 |
|---|---|---|---|---|---|---|---|
| sample_1260 | 3135 | 0.1816 | 0.1187 | -0.0071 | +0.081 | 0.637 | 0.918 |
| ewma_252 | 3135 | 0.1881 | 0.1233 | -0.0053 | +0.015 | 0.614 | 0.904 |
| zero | 3135 | 0.1895 | 0.1273 | -0.0636 | +0.000 |  | 0.912 |
| rf_erp | 3135 | 0.1920 | 0.1259 | -0.0598 | -0.027 | 0.586 | 0.918 |
| shrink | 3135 | 0.1972 | 0.1302 | -0.0695 | -0.084 | 0.486 | 0.906 |
| momentum_12_1 | 3135 | 0.1982 | 0.1328 | -0.0202 | -0.094 | 0.565 | 0.873 |
| rf | 3135 | 0.1986 | 0.1316 | -0.0744 | -0.099 | 0.442 | 0.909 |
| sample_504 | 3135 | 0.2022 | 0.1329 | -0.0049 | -0.139 | 0.582 | 0.890 |
| sample_252 | 3135 | 0.2102 | 0.1386 | -0.0013 | -0.231 | 0.568 | 0.865 |
| capm | 2002 | 0.2221 | 0.1519 | -0.0808 | -0.375 | 0.593 | 0.933 |
| sample_126 | 3135 | 0.2387 | 0.1592 | -0.0038 | -0.587 | 0.561 | 0.825 |

### h = 252

| method | n | rmse | mae | bias | skill_vs_zero | hit_rate | coverage_90 |
|---|---|---|---|---|---|---|---|
| sample_1260 | 3135 | 0.2826 | 0.1795 | -0.0183 | +0.114 | 0.667 | 0.903 |
| zero | 3135 | 0.3003 | 0.1968 | -0.1314 | +0.000 |  | 0.885 |
| ewma_252 | 3135 | 0.3005 | 0.1929 | -0.0146 | -0.001 | 0.639 | 0.874 |
| rf_erp | 3135 | 0.3048 | 0.1932 | -0.1237 | -0.030 | 0.618 | 0.899 |
| shrink | 3135 | 0.3181 | 0.2049 | -0.1430 | -0.122 | 0.473 | 0.882 |
| rf | 3135 | 0.3218 | 0.2086 | -0.1529 | -0.148 | 0.419 | 0.879 |
| momentum_12_1 | 3135 | 0.3240 | 0.2141 | -0.0445 | -0.164 | 0.588 | 0.821 |
| sample_504 | 3135 | 0.3351 | 0.2172 | -0.0138 | -0.244 | 0.604 | 0.850 |
| capm | 2002 | 0.3482 | 0.2340 | -0.1655 | -0.344 | 0.641 | 0.912 |
| sample_252 | 3135 | 0.3602 | 0.2349 | -0.0067 | -0.439 | 0.590 | 0.806 |
| sample_126 | 3135 | 0.4196 | 0.2769 | -0.0117 | -0.952 | 0.567 | 0.737 |

## Diebold-Mariano tests (pass_1260)

Negative t = method has lower squared error than the baseline. CAPM rows use the equity/EWY sample only.

### baseline = sample_504

| h | method | mean_dloss | dm_t_nw | n_origins | n_pairs |
|---|---|---|---|---|---|
| 63 | sample_1260 | -0.00210 | -4.49 | 203 | 3135 |
| 63 | ewma_252 | -0.00132 | -4.19 | 203 | 3135 |
| 63 | zero | -0.00125 | -1.41 | 203 | 3135 |
| 63 | rf_erp | -0.00106 | -1.08 | 203 | 3135 |
| 63 | capm | -0.00102 | -0.67 | 188 | 2002 |
| 63 | shrink | -0.00052 | -0.50 | 203 | 3135 |
| 63 | rf | -0.00041 | -0.38 | 203 | 3135 |
| 63 | momentum_12_1 | +0.00022 | +0.32 | 203 | 3135 |
| 63 | sample_252 | +0.00122 | +1.59 | 203 | 3135 |
| 63 | sample_126 | +0.00387 | +3.97 | 203 | 3135 |
| 252 | sample_1260 | -0.03178 | -4.00 | 203 | 3135 |
| 252 | ewma_252 | -0.02093 | -3.90 | 203 | 3135 |
| 252 | zero | -0.02094 | -1.33 | 203 | 3135 |
| 252 | rf_erp | -0.01900 | -1.16 | 203 | 3135 |
| 252 | capm | -0.02729 | -1.07 | 188 | 2002 |
| 252 | shrink | -0.01037 | -0.60 | 203 | 3135 |
| 252 | rf | -0.00798 | -0.45 | 203 | 3135 |
| 252 | momentum_12_1 | -0.00051 | -0.04 | 203 | 3135 |
| 252 | sample_252 | +0.02363 | +2.26 | 203 | 3135 |
| 252 | sample_126 | +0.06037 | +3.79 | 203 | 3135 |

### baseline = zero

| h | method | mean_dloss | dm_t_nw | n_origins | n_pairs |
|---|---|---|---|---|---|
| 63 | sample_1260 | -0.00085 | -1.26 | 203 | 3135 |
| 63 | ewma_252 | -0.00007 | -0.09 | 203 | 3135 |
| 63 | capm | +0.00026 | +0.96 | 188 | 2002 |
| 63 | rf_erp | +0.00020 | +1.06 | 203 | 3135 |
| 63 | sample_504 | +0.00125 | +1.41 | 203 | 3135 |
| 63 | sample_252 | +0.00247 | +2.39 | 203 | 3135 |
| 63 | momentum_12_1 | +0.00148 | +2.42 | 203 | 3135 |
| 63 | shrink | +0.00073 | +2.97 | 203 | 3135 |
| 63 | rf | +0.00084 | +3.21 | 203 | 3135 |
| 63 | sample_126 | +0.00513 | +3.89 | 203 | 3135 |
| 252 | sample_1260 | -0.01084 | -1.02 | 203 | 3135 |
| 252 | ewma_252 | +0.00001 | +0.00 | 203 | 3135 |
| 252 | capm | +0.00155 | +0.40 | 188 | 2002 |
| 252 | rf_erp | +0.00194 | +0.70 | 203 | 3135 |
| 252 | sample_504 | +0.02094 | +1.33 | 203 | 3135 |
| 252 | momentum_12_1 | +0.02043 | +2.39 | 203 | 3135 |
| 252 | shrink | +0.01057 | +2.91 | 203 | 3135 |
| 252 | sample_252 | +0.04456 | +3.04 | 203 | 3135 |
| 252 | rf | +0.01296 | +3.45 | 203 | 3135 |
| 252 | sample_126 | +0.08131 | +3.89 | 203 | 3135 |

## Per-asset-class (pass_1260), h = 63 and 252

CAPM is only computed for US-listed names, so its n differs from the rest of the class (korea = EWY only).

### equity, h = 63

| method | n | rmse | bias | skill_vs_zero | hit_rate | coverage_90 |
|---|---|---|---|---|---|---|
| sample_1260 | 1814 | 0.1451 | -0.0043 | +0.062 | 0.663 | 0.933 |
| ewma_252 | 1814 | 0.1478 | -0.0024 | +0.027 | 0.641 | 0.922 |
| zero | 1814 | 0.1498 | -0.0455 | +0.000 |  | 0.928 |
| capm | 1814 | 0.1507 | -0.0430 | -0.012 | 0.578 | 0.929 |
| rf_erp | 1814 | 0.1516 | -0.0441 | -0.023 | 0.587 | 0.928 |
| momentum_12_1 | 1814 | 0.1526 | -0.0139 | -0.036 | 0.594 | 0.911 |
| sample_504 | 1814 | 0.1537 | -0.0019 | -0.052 | 0.625 | 0.910 |
| shrink | 1814 | 0.1540 | -0.0505 | -0.057 | 0.483 | 0.922 |
| rf | 1814 | 0.1548 | -0.0541 | -0.067 | 0.402 | 0.921 |
| sample_252 | 1814 | 0.1581 | +0.0011 | -0.113 | 0.597 | 0.898 |
| sample_126 | 1814 | 0.1707 | -0.0005 | -0.297 | 0.574 | 0.880 |

### bond_gold, h = 63

| method | n | rmse | bias | skill_vs_zero | hit_rate | coverage_90 |
|---|---|---|---|---|---|---|
| shrink | 376 | 0.0723 | -0.0113 | +0.038 | 0.519 | 0.926 |
| rf_erp | 376 | 0.0726 | -0.0106 | +0.030 | 0.606 | 0.926 |
| rf | 376 | 0.0730 | -0.0131 | +0.019 | 0.532 | 0.926 |
| sample_1260 | 376 | 0.0734 | +0.0002 | +0.009 | 0.574 | 0.915 |
| ewma_252 | 376 | 0.0736 | -0.0014 | +0.002 | 0.561 | 0.910 |
| zero | 376 | 0.0737 | -0.0133 | +0.000 |  | 0.920 |
| sample_504 | 376 | 0.0747 | -0.0026 | -0.028 | 0.527 | 0.896 |
| sample_252 | 376 | 0.0777 | -0.0021 | -0.110 | 0.503 | 0.886 |
| momentum_12_1 | 376 | 0.0778 | -0.0022 | -0.113 | 0.476 | 0.891 |
| sample_126 | 376 | 0.0850 | -0.0018 | -0.331 | 0.524 | 0.840 |

### fx, h = 63

| method | n | rmse | bias | skill_vs_zero | hit_rate | coverage_90 |
|---|---|---|---|---|---|---|
| rf_erp | 569 | 0.0427 | -0.0008 | +0.008 | 0.517 | 0.923 |
| rf | 569 | 0.0427 | -0.0008 | +0.008 | 0.517 | 0.923 |
| zero | 569 | 0.0428 | -0.0027 | +0.000 |  | 0.923 |
| shrink | 569 | 0.0432 | -0.0009 | -0.017 | 0.518 | 0.917 |
| sample_1260 | 569 | 0.0441 | -0.0015 | -0.059 | 0.497 | 0.914 |
| ewma_252 | 569 | 0.0451 | -0.0012 | -0.109 | 0.492 | 0.921 |
| sample_504 | 569 | 0.0455 | -0.0012 | -0.131 | 0.480 | 0.916 |
| sample_252 | 569 | 0.0486 | -0.0009 | -0.289 | 0.508 | 0.893 |
| momentum_12_1 | 569 | 0.0491 | -0.0010 | -0.315 | 0.510 | 0.896 |
| sample_126 | 569 | 0.0542 | -0.0007 | -0.601 | 0.483 | 0.882 |

### korea, h = 63

| method | n | rmse | bias | skill_vs_zero | hit_rate | coverage_90 |
|---|---|---|---|---|---|---|
| capm | 188 | 0.1097 | -0.0092 | +0.179 | 0.505 | 0.931 |
| zero | 376 | 0.1211 | -0.0236 | +0.000 |  | 0.936 |
| rf_erp | 376 | 0.1213 | -0.0198 | -0.004 | 0.521 | 0.934 |
| sample_1260 | 376 | 0.1219 | -0.0018 | -0.014 | 0.537 | 0.926 |
| rf | 376 | 0.1233 | -0.0298 | -0.038 | 0.471 | 0.934 |
| shrink | 376 | 0.1235 | -0.0283 | -0.040 | 0.463 | 0.934 |
| ewma_252 | 376 | 0.1256 | -0.0020 | -0.076 | 0.481 | 0.920 |
| sample_504 | 376 | 0.1308 | -0.0016 | -0.168 | 0.449 | 0.910 |
| momentum_12_1 | 376 | 0.1316 | -0.0086 | -0.181 | 0.468 | 0.896 |
| sample_252 | 376 | 0.1352 | -0.0025 | -0.247 | 0.484 | 0.896 |
| sample_126 | 376 | 0.1432 | -0.0055 | -0.398 | 0.497 | 0.864 |

### equity, h = 252

| method | n | rmse | bias | skill_vs_zero | hit_rate | coverage_90 |
|---|---|---|---|---|---|---|
| sample_1260 | 1814 | 0.3242 | -0.0217 | +0.152 | 0.777 | 0.926 |
| ewma_252 | 1814 | 0.3441 | -0.0143 | +0.044 | 0.745 | 0.907 |
| zero | 1814 | 0.3520 | -0.1864 | +0.000 |  | 0.894 |
| capm | 1814 | 0.3546 | -0.1766 | -0.015 | 0.647 | 0.912 |
| rf_erp | 1814 | 0.3608 | -0.1810 | -0.050 | 0.654 | 0.910 |
| momentum_12_1 | 1814 | 0.3634 | -0.0600 | -0.066 | 0.661 | 0.862 |
| shrink | 1814 | 0.3768 | -0.2066 | -0.146 | 0.483 | 0.892 |
| rf | 1814 | 0.3824 | -0.2210 | -0.180 | 0.351 | 0.881 |
| sample_504 | 1814 | 0.3892 | -0.0122 | -0.223 | 0.713 | 0.881 |
| sample_252 | 1814 | 0.4143 | -0.0001 | -0.385 | 0.660 | 0.833 |
| sample_126 | 1814 | 0.4880 | -0.0066 | -0.922 | 0.620 | 0.764 |

### bond_gold, h = 252

| method | n | rmse | bias | skill_vs_zero | hit_rate | coverage_90 |
|---|---|---|---|---|---|---|
| shrink | 376 | 0.1566 | -0.0419 | +0.109 | 0.513 | 0.846 |
| rf_erp | 376 | 0.1566 | -0.0389 | +0.108 | 0.649 | 0.859 |
| rf | 376 | 0.1593 | -0.0489 | +0.076 | 0.574 | 0.848 |
| zero | 376 | 0.1658 | -0.0499 | +0.000 |  | 0.830 |
| sample_1260 | 376 | 0.1660 | +0.0043 | -0.002 | 0.569 | 0.851 |
| ewma_252 | 376 | 0.1680 | -0.0022 | -0.027 | 0.561 | 0.814 |
| sample_504 | 376 | 0.1827 | -0.0071 | -0.214 | 0.527 | 0.785 |
| sample_252 | 376 | 0.1829 | -0.0050 | -0.217 | 0.577 | 0.827 |
| momentum_12_1 | 376 | 0.1837 | -0.0055 | -0.227 | 0.545 | 0.816 |
| sample_126 | 376 | 0.2339 | -0.0038 | -0.990 | 0.545 | 0.710 |

### fx, h = 252

| method | n | rmse | bias | skill_vs_zero | hit_rate | coverage_90 |
|---|---|---|---|---|---|---|
| rf_erp | 569 | 0.0817 | -0.0064 | +0.024 | 0.510 | 0.907 |
| rf | 569 | 0.0817 | -0.0064 | +0.024 | 0.510 | 0.907 |
| zero | 569 | 0.0827 | -0.0140 | +0.000 |  | 0.902 |
| shrink | 569 | 0.0864 | -0.0068 | -0.092 | 0.459 | 0.895 |
| sample_1260 | 569 | 0.0941 | -0.0093 | -0.296 | 0.462 | 0.889 |
| ewma_252 | 569 | 0.0983 | -0.0082 | -0.413 | 0.460 | 0.852 |
| sample_504 | 569 | 0.1045 | -0.0081 | -0.599 | 0.427 | 0.847 |
| sample_252 | 569 | 0.1227 | -0.0069 | -1.202 | 0.487 | 0.766 |
| momentum_12_1 | 569 | 0.1258 | -0.0072 | -1.317 | 0.492 | 0.752 |
| sample_126 | 569 | 0.1520 | -0.0063 | -2.382 | 0.473 | 0.701 |

### korea, h = 252

| method | n | rmse | bias | skill_vs_zero | hit_rate | coverage_90 |
|---|---|---|---|---|---|---|
| capm | 188 | 0.2791 | -0.0589 | +0.332 | 0.590 | 0.910 |
| rf_erp | 376 | 0.3351 | -0.1098 | +0.037 | 0.572 | 0.878 |
| zero | 376 | 0.3415 | -0.1249 | +0.000 |  | 0.872 |
| sample_1260 | 376 | 0.3437 | -0.0376 | -0.013 | 0.543 | 0.870 |
| rf | 376 | 0.3503 | -0.1498 | -0.052 | 0.452 | 0.862 |
| shrink | 376 | 0.3507 | -0.1435 | -0.055 | 0.407 | 0.854 |
| ewma_252 | 376 | 0.3725 | -0.0385 | -0.190 | 0.476 | 0.811 |
| sample_504 | 376 | 0.3942 | -0.0370 | -0.332 | 0.423 | 0.774 |
| momentum_12_1 | 376 | 0.4250 | -0.0648 | -0.549 | 0.420 | 0.731 |
| sample_252 | 376 | 0.4447 | -0.0402 | -0.696 | 0.426 | 0.715 |
| sample_126 | 376 | 0.4787 | -0.0523 | -0.965 | 0.471 | 0.694 |

## Pooled results (pass_504, look-back requirement relaxed to 504; sample_1260 excluded)

### h = 63

| method | n | rmse | mae | bias | skill_vs_zero | hit_rate | coverage_90 |
|---|---|---|---|---|---|---|---|
| zero | 3745 | 0.1368 | 0.0915 | -0.0291 | +0.000 |  | 0.913 |
| ewma_252 | 3745 | 0.1380 | 0.0910 | -0.0010 | -0.018 | 0.574 | 0.909 |
| rf_erp | 3745 | 0.1388 | 0.0916 | -0.0279 | -0.028 | 0.550 | 0.914 |
| shrink | 3745 | 0.1405 | 0.0933 | -0.0329 | -0.055 | 0.487 | 0.911 |
| rf | 3745 | 0.1409 | 0.0938 | -0.0352 | -0.061 | 0.454 | 0.911 |
| momentum_12_1 | 3745 | 0.1412 | 0.0943 | -0.0097 | -0.065 | 0.548 | 0.895 |
| sample_504 | 3745 | 0.1428 | 0.0944 | -0.0011 | -0.088 | 0.552 | 0.898 |
| sample_252 | 3745 | 0.1475 | 0.0975 | -0.0012 | -0.161 | 0.552 | 0.887 |
| sample_126 | 3745 | 0.1586 | 0.1060 | -0.0014 | -0.344 | 0.550 | 0.864 |
| capm | 2398 | 0.1624 | 0.1113 | -0.0371 | -0.408 | 0.543 | 0.911 |

### h = 252

| method | n | rmse | mae | bias | skill_vs_zero | hit_rate | coverage_90 |
|---|---|---|---|---|---|---|---|
| zero | 3745 | 0.3155 | 0.2067 | -0.1169 | +0.000 |  | 0.873 |
| rf_erp | 3745 | 0.3254 | 0.2081 | -0.1121 | -0.064 | 0.575 | 0.885 |
| ewma_252 | 3745 | 0.3369 | 0.2160 | -0.0046 | -0.140 | 0.604 | 0.850 |
| shrink | 3745 | 0.3373 | 0.2188 | -0.1319 | -0.143 | 0.462 | 0.870 |
| rf | 3745 | 0.3400 | 0.2214 | -0.1413 | -0.161 | 0.418 | 0.869 |
| momentum_12_1 | 3745 | 0.3523 | 0.2345 | -0.0391 | -0.247 | 0.567 | 0.803 |
| sample_504 | 3745 | 0.3654 | 0.2389 | -0.0047 | -0.342 | 0.569 | 0.829 |
| capm | 2398 | 0.3769 | 0.2548 | -0.1459 | -0.427 | 0.575 | 0.889 |
| sample_252 | 3745 | 0.4049 | 0.2626 | -0.0052 | -0.647 | 0.569 | 0.781 |
| sample_126 | 3745 | 0.4739 | 0.3058 | -0.0060 | -1.256 | 0.561 | 0.719 |

## How noisy is the sample drift?

Theory: SE(sample mean over 2 years) = sigma/sqrt(2) -> 0.141 for a 20% vol name, 0.283 for a 40% vol name. Empirical: standard deviation of the annualised sample_504 drift across origins, per ticker (annualised mu = F at h=252). The empirical figure is a little below theory because consecutive windows overlap, but it is the same order of magnitude as the vol itself.

| ticker | n | mean_sigma | mu_mean | mu_std | theory_se |
|---|---|---|---|---|---|
| EURUSD=X | 190 | 0.093 | -0.016 | 0.046 | 0.066 |
| USDJPY=X | 190 | 0.100 | +0.025 | 0.075 | 0.071 |
| USDKRW=X | 189 | 0.117 | +0.009 | 0.047 | 0.083 |
| TLT | 188 | 0.152 | +0.025 | 0.104 | 0.108 |
| GLD | 188 | 0.160 | +0.061 | 0.120 | 0.113 |
| KO | 188 | 0.174 | +0.090 | 0.058 | 0.123 |
| SPY | 188 | 0.178 | +0.122 | 0.077 | 0.126 |
| QQQ | 188 | 0.208 | +0.168 | 0.098 | 0.147 |
| IWM | 188 | 0.228 | +0.095 | 0.101 | 0.162 |
| XOM | 188 | 0.246 | +0.060 | 0.170 | 0.174 |
| EWY | 188 | 0.263 | +0.042 | 0.135 | 0.186 |
| MSFT | 188 | 0.264 | +0.201 | 0.117 | 0.187 |
| 005930.KS | 188 | 0.274 | +0.134 | 0.138 | 0.194 |
| AAPL | 188 | 0.287 | +0.248 | 0.161 | 0.203 |
| JPM | 188 | 0.305 | +0.137 | 0.128 | 0.216 |
| NVDA | 188 | 0.456 | +0.371 | 0.369 | 0.322 |
| TSLA | 122 | 0.552 | +0.290 | 0.471 | 0.390 |

## Figures

- `fig1_rmse_by_horizon.png` pooled RMSE by horizon per method
- `fig2_scatter_h252.png` sample_504 forecast vs realised at h=252 with the 45-degree line
- `fig3_shrink_weight.png` shrinkage weight w versus trailing vol

## Reading

1. **The trailing 2-year mean carries no forecast information.** Its correlation with the realised 12-month return is -0.010 (R^2 = 0.0001, fig2). Theory says its standard error is 14.1% a year for a 20%-vol name and 28.3% for a 40%-vol name; the per-ticker table shows the estimate moving with a standard deviation of 11.7% (median) against a median vol of 22.8%. NVDA's 2-year drift moved with a standard deviation of 36.9% a year.
2. **Today's method loses to a flat zero at every horizon.** Pooled RMSE, sample_504 vs zero: h=21 0.0716 vs 0.0710, h=63 0.1295 vs 0.1254, h=252 0.3351 vs 0.3003 (skill -0.244). The DM test against zero gives t = -1.33 at h=252 and -1.41 at h=63: the direction is consistent but not significant at 5%, so the honest statement is 'no better than zero, probably worse'. Shorter windows are strictly worse and significantly so (sample_126 t = +3.79, sample_252 t = +2.26).
3. **Longer memory helps; it is the only thing with a lower RMSE than zero, and even that is not significant.** sample_1260 has the lowest RMSE at every horizon (h=252: 0.2826, skill +0.114; DM vs sample_504 t = -4.00, vs zero t = -1.02). ewma_252 (half-life one year, all history) is next: h=252 RMSE 0.3005, t = -3.90 vs sample_504 and +0.00 vs zero. Both gains come from the equity block (equity h=252 RMSE: sample_1260 0.3242, ewma 0.3441, zero 0.3520); in FX and Korea both lose to zero (fx: 0.0941 / 0.0983 vs 0.0827). A 5-year mean over 2010-2025 mostly learned that US equities went up; that is a regime, not a forecasting rule.
4. **The structural estimators are all within noise of zero, and of each other.** h=252 RMSE: rf_erp 0.3048 (skill -0.030, DM vs zero t = +0.70), shrink 0.3181, rf 0.3218, capm 0.3482 on its equity-only sample (equity-class comparison: capm 0.3546, rf_erp 0.3608, zero 0.3520). rf_erp is the best full-sample method in FX (0.0817) and Korea (0.3351) and ties for first in bond/gold (0.1566 vs shrink 0.1566); it is never the worst anywhere. Pure rf and shrink are significantly worse than zero (DM vs zero t = +3.45 and +2.91) while rf_erp is not: the ERP is doing the work. Pure rf (risk-neutral) forecasts a negative drift for high-vol names (rf - sigma^2/2), which is why its h=252 hit rate is only 0.419: it is a pricing measure, not a forecast.
5. **Shrinkage as specified collapses onto rf.** With tau = 0.05 the mean weight on the sample mean is 0.15 (equity 0.09, FX 0.36; fig3), so shrink tracks rf (h=252 RMSE 0.3181 vs rf 0.3218). Shrinking toward rf+ERP instead was not tested.
6. **Direction and bias.** Every method has a negative bias at h=252 (forecast below realised) because the period was an equity bull market: zero -0.1314, rf_erp -0.1237, sample_504 -0.0138. Hit rates above 0.5 for positive-drift methods (rf_erp 0.618, sample_1260 0.667) come from that up-drift, not from timing; momentum_12_1 (0.588, RMSE 0.3240) adds nothing.
7. **Band coverage barely depends on the drift.** Share inside the 5-95% band at h=252: zero 0.885, rf_erp 0.899, sample_1260 0.903, sample_504 0.850, sample_126 0.737 (target 0.90). Only the noisy short windows push coverage down; the rest sit within a few points of target, which is the vol model's job.
8. **Relaxing the history requirement (pass_504, origins from 2007, includes 2008) does not change the order:** h=252 RMSE zero 0.3155, rf_erp 0.3254, ewma_252 0.3369, sample_504 0.3654.

## Recommendation for the Quant Lab

Expose four drift modes. Default to the risk-premium drift. Statistically it is a tie with zero (DM t +0.70), so zero is an equally defensible default; the case for rf+ERP is that it is never the worst method in any asset class, its centre has an economic reading the operator can argue with, and it degrades to zero for FX where the ERP is 0.

| mode | formula (annualised log drift) | inputs | evidence (pass_1260, h=252 unless noted) |
|---|---|---|---|
| **Risk premium** (default) | rf_t + ERP - sigma^2/2 | rf from FRED DGS3MO (one cached pull, forward-filled); ERP assumption shown in the UI: 4% equity/ETF, 1% bond/gold, 0 FX | RMSE 0.3048, skill -0.030 (tie with zero, DM t +0.70); beats sample_504 (0.3351) at every horizon; best full-sample method in FX and Korea; coverage 0.899; the only mode whose centre has an economic reading |
| **Risk neutral** | rf_t - sigma^2/2 | rf only | RMSE 0.3218; hit rate 0.419 (negative drift for high-vol names). Offer it because it is the pricing measure for the structuring pages, not because it forecasts |
| **Zero** | 0 | none | RMSE 0.3003; nothing beats it significantly (closest challenger sample_1260, DM t -1.02); use for stress tests and FX |
| **Historical (long memory)** | EWMA of daily log returns, half-life 252 sessions, x252; or the plain mean when >= 1260 sessions are loaded | price history only | ewma_252 RMSE 0.3005 (DM vs sample_504 t -3.90); sample_1260 RMSE 0.2826 (skill +0.114). Caveat: the study's EWMA used all history since 2005 (effective span ~730 sessions); on the app's 504-session window it will sit between sample_504 and this figure. Label it 'historical, noisy' |

Retire the trailing 504-session sample mean as a mode (RMSE 0.3351, skill -0.244; DM vs zero t -1.33 in zero's favour). If it must stay for continuity, keep it under the historical mode with the 'noisy' label.

Not worth a dropdown slot: sample_126 / sample_252 (significantly worse than sample_504), momentum_12_1 (RMSE 0.3240, no directional edge), shrink as specified (tracks rf; mean w = 0.15), CAPM (equity-only, needs a benchmark series per market, and its equity-class RMSE 0.3546 vs rf_erp 0.3608 is inside noise).

Implementation notes:
- `core/quant/montecarlo.py::_calibrate` returns mu = mean(log r)*252 and `_simulate_gbm` uses (mu - 0.5*sigma^2)*dt as the log-step mean. mu is already a log-return mean, so the half-variance is subtracted twice today. Whatever the mode, define mu as the annualised log drift (as in this study, F = mu*h/252) and use mu*dt as the log-step mean; the -sigma^2/2 belongs inside the rf modes only.
- rf: FRED DGS3MO in percent -> decimal, forward-filled; cache it; if unreachable fall back to a constant and say so in the calibration row.
- ERP: an assumption, not an estimate; show it next to 'Drift (ann.)' so the operator can see and override it.
- FX: the theoretically right drift is the rate differential (r_d - r_f), not rf_usd - sigma^2/2; this study used the spec's formula and FX still came out best on rf/rf_erp (both ~0 there). Use zero or the differential for FX pairs.
- CAPM would need a benchmark on the same calendar (SPY for US names, KOSPI for .KS names); skipped here for 005930.KS, TLT, GLD and FX.
- The fan's width comes from the vol model; the drift choice moves the centre by roughly (ERP x horizon), and the study shows that centre is within noise of zero for most names.
