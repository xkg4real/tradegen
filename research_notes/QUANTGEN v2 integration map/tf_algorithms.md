# tf_algorithms — portable algorithm definitions from the tech-fund data labs

Digest for the QUANTGEN v2.0 build. Every definition below is transcribed from the local lab files so an implementer can re-implement it as a library function and test it on a synthetic panel without opening the sources. Field names, bounds, thresholds and status strings are verbatim. "Conservative reading" = no exposure change, specification book only, fail closed.

Source abbreviations (all under `C:/Users/whydi/OneDrive/Desktop/QUANTGEN/QUANTGEN_techfund_research_bundle/QUANTGEN_techfund_research/`):

| Abbr | File |
|---|---|
| KR | datalab/KR_datalab_summary.md |
| R2KR | datalab/R2_KR_summary.md |
| R2IDX | datalab/R2_IDX_summary.md |
| US | datalab/US_datalab_summary.md |
| KC | scripts/kr_common.py |
| K02 | scripts/kr_02_signals.py |
| K03 | scripts/kr_03_portfolios.py |
| K04 | scripts/kr_04_stats.py |
| K05 | scripts/kr_05_index_timing.py |
| RC | scripts/r2_kr_common.py |
| R01 | scripts/r2_kr_01_build_extra.py (supporting: defines the `X[...]` inputs the assigned scripts consume) |
| R03 | scripts/r2_kr_03_momentum.py |
| R04 | scripts/r2_kr_04_exclusion.py |
| R05 | scripts/r2_kr_05_crash_controls.py |
| R06 | scripts/r2_kr_06_reversal_lowvol.py |
| IC | scripts/r2_idx_common.py |
| I01 | scripts/r2_idx_01_protective.py |
| I02 | scripts/r2_idx_02_gate_sim.py |
| I03 | scripts/r2_idx_03_averaging.py |
| R3P | scripts/r3/r3_01_pair_share.py |
| V | C:/Users/whydi/OneDrive/Desktop/QUANTGEN/core/quant/validate.py |
| RES | datalab/results/{kr,r2_kr,r2_idx,r3,us}/*.csv (local copies of the lab outputs) |

Citations are `ABBR line` or `ABBR a-b`.

---

## A. Data conventions of the labs

### A.1 Panel layout (KR stock labs)

| Item | Definition | Source |
|---|---|---|
| Storage | wide `(T dates x N codes)` float32/bool `.npy`, memory-mapped | KC 6 |
| Daily matrices (round 1) | `cumlog` (CL = cumulative log price from cleaned returns), `ret` (R), `valid`, `exists` (E), `close`, `high`, `amount` (AMT), `marcap` (MCAP), `namecls` (NCLS), `traded` (TR = Volume_t > 0), `beyond_nonca` (BNC), `mkt` (MK: KOSPI 1, KOSDAQ 2, KOSDAQ GLOBAL 2) | K02 55-57; KC 24 |
| Daily matrices (round 2 extra) | `volume`, `cr` (raw ChangesRatio/100), `low` (0 -> Close), `stocks` (shares outstanding, f8), `chgcode` (ChangeCode 4/5 = old KRX limit-up/limit-down codes, 0 otherwise), `admin` (Dept carries the KOSDAQ administrative / investment-caution designation), `raw_ret` (unadjusted Close_t/Close_{t-1}-1 on consecutive listed days) | R01 6-10 |
| Return | `r = ChangesRatio/100` (KRX base-price change, split-adjusted, dividends excluded) | KC 5; KR 5; R2KR 3 |
| Timing | decide at the close of t with data through t; returns earned from t+1 | KC 4; KR 5; RC 8 |
| Limit regime change | `LIMIT_CHANGE_DATE = 2015-06-15` (daily limit +-15% -> +-30%) | KC 25 |
| Liquidation window | `LIQ_WINDOW = 30` trading days before a delisting | KC 28 |
| Seeds | KR labs `SEED = 20261002` (KC 21); index lab `SEED = 11` (= QUANTGEN study seed, IC 57) | |

Return cleaning (summary only; not an assigned script): first day of each listing segment missing; beyond-limit returns kept when in the last 30 sessions before a delisting or on the first trade after a >= 5-session halt; other cases per KR 289. "Strict" sensitivity variant KR 290.

### A.2 Formation calendars

```
month_end_idx(dates): last trading-day index of each (year, month)                              # KC 98-100
week_end_idx(dates):  last trading day with weekday <= 4 (Mon..Fri) of each ISO (year, week)    # KC 103-108
monthly formations:   me[(me >= 252) & (me < T-1)]   (LOOKBACK = 252)                            # K02 37, 213-215
```
366 monthly formations 1996-03..2026-08 (R2KR 3).

### A.3 Eligibility and universes at formation t (close of t; all rows <= t)

```
nvalid = #valid days in t-251..t        (valid = finite return and Volume > 0)
npos   = #days with Amount > 0 in t-4..t
nbnc   = #beyond-limit-without-corporate-action days in t-29..t
base = E[t] & (NCLS[t] == 0) & (CLOSE[t] >= 1000) & (MCAP[t] > 0) & (nvalid >= 200) & (npos >= 4)
elig = base & TR[t] & (nbnc == 0)                                                   # K02 94-96
ALL   = elig & (MCAP[t] >= quantile(MCAP[t][elig], 0.20))                            # K02 99-101
LARGE = top 200 of elig by MCAP[t]  (np.argsort(-mcap, kind='stable'))               # K02 102-106
```
NCLS == 0 means operating company; classes SPAC / REIT / INFRA_FUND / FUND / DR_ETN are excluded by regex (KC 61-84; a literal substring rule was deliberately not used, KR 293). Common share = code ends in '0' (R01 4; R3P 12-13).
Round-2 extra universes: `top500` = top 500 of round-1 eligible by Marcap_t (R01 34, 298-305); `broad` (no price floor, no microcap cut), `broad_cut` (R01 35-37); `liq_e7 = e & tr & (mcap >= 100e9) & (ADV20 >= 1e9) & (close >= 1000) & ~ADMIN & (namecls != 1)` (R01 314).

Note on the brief's phrase "eligibility on t-1": the labs decide membership from data through the close of t and trade at the close of t (KC 4; K02 11-12 "traded on day t itself"). See Ambiguity 1.

### A.4 Costs (per side, on every unit of turnover)

| Venue | Base / 2x stress | Source |
|---|---|---|
| KRX single stocks | `COST = {'gross': 0.0, 'net35': 0.0035, 'net70': 0.0070}` | KC 26; RC 36 |
| KRX ETF index timing (round 1) | `INDEX_COST = {'gross': 0.0, 'net3': 0.0003, 'net6': 0.0006}` | KC 27; K05 27 |
| KOSPI (r2_idx) | `books={'KRX ETF 3bp': (0.0003, 0.0006)}`, `vt_target=0.20`, window 1996-09-02..2026-09-29 | IC 96-98 |
| SPY (r2_idx) | `books={'US via KIS 50bp': (0.0050, 0.0100), 'Futures 5bp': (0.0005, 0.0010)}`, `vt_target=0.15`, window 1999-05-03..2021-03-31, `primary_book='US via KIS 50bp'` | IC 99-101 |
| US daily lab | futures 5 bp (2x 10), US shares via KIS 50 bp (2x 100), including the first entry | US 4 |

Cost timing differs between labs: the KR stock labs charge `cost_k = c * turnover_k` once per period inside the period's value path (K04 5-8; RC 13 "charged at the formation close") and the first formation counts the initial purchase (turnover 1, K03 22-23). The index lab charges `c * |w_t - w_{t-1}|` on the day the new weight earns and does NOT charge the initial entry (IC 7-8, 284-293). See Ambiguity 2.

### A.5 Book mechanics (round-1 engine, reused unchanged in round 2: RC 26)

```
class Book:  v = value vector (N), started
rebalance(members, base_w, E_t, TR_t):                                   # K03 81-96
    stuck     = (v > 0) & E_t & ~TR_t          # held, listed, halted at the formation close
    stuck_val = v[stuck].sum() if started else 0
    w = 0; w[members] = (1 - stuck_val) * base_w
    ns = ~stuck & E_t
    turnover = sum |w[ns] - v[ns]|             # delisted positions are cash -> only the buy side is counted
    w[stuck] = v[stuck]; v = w; return turnover, n_stuck
hold(G):                                                                 # K03 98-109
    vals = v[idx] * G[:, idx]; pv = vals.sum(1); prev = [v.sum(), pv[:-1]]
    r_d = pv/prev - 1; v = vals[-1]/pv[-1]      (weights drift; buy-and-hold inside the period)
Period k (formation t = fidx[k], te = fidx[k+1] or T-1):                 # K03 186-191; RC 172-177
    Rb = nan_to_num(R[t+1:te+1]); A = cumprod(E[t+1:te+1])  (alive without gap since t)
    G  = cumprod(1 + Rb * A)                   # a delisted name's value freezes (cash, 0%)
```
Delisting classification: `distressed` if BNC any in the last 30 listed days, else `other` (K03 11-13, 193-199). Halted at a rebalance: carried, sold at the first rebalance where it trades (K03 18-20). Members with a missing signal stay in the NOTQ books (K03 225).

Weights: `EW = 1/n`; `VW = Marcap_t / sum` (K03 112-116); `VWcap5 = cap_weights(marcap, 0.05)`:
```
cap_weights(base, cap=0.05):                                             # RC 129-146
    w = base/sum; if n*cap < 1 - 1e-12: return 1/n     (cap infeasible, < 20 names)
    repeat: free = ~capped; room = 1 - cap*capped.sum(); w = where(capped, cap, base*room/base[free].sum())
            new = free & (w > cap + 1e-15); stop when none; capped |= new
```

Quintile assignment (K03 46-71):
```
quantile_groups(s, U, nq, k):
    m = U & isfinite(s); n = m.sum(); if n < nq*5: nothing assigned (group 0)
    r  = rankdata(s[m], method='average'); g = floor((r - 0.5)/n * nq) + 1
    if min group count < 0.5*n/nq: ties broken by u = default_rng(SEED + k).random(N)[m], lexsort((u, x)), ordinal ranks
```
Quintile numbering: 1 = lowest value, 5 = highest. Breakpoints are formed inside the universe only (KR 284).

### A.6 Series construction (period k, days t_k+1..t_{k+1}, C_0 = 1)

```
LO:        C_d = V_L,d - c*TO_L,k                                       # K04 6; RC 228
LS:        C_d = 1 - c*(TO_L,k + TO_S,k) + V_L,d - V_S,d                 # K04 7-8 ($1 long / $1 short, cash 0%)
LO_xs_B:   C_d = 1 - c*TO_L,k + V_L,d - (V_B,d - cb*TO_B,k)              # RC 210-213 (cb = 0 -> gross benchmark = round-1 convention)
daily_d = C_d / C_{d-1} - 1;  period_k = C_last - 1                     # K04 10; RC 233-235
diff_series(X, Y, c) = series(X, B=Y, c=c, cb=c)   (filtered minus unfiltered, both net)   # RC 239-241
LS turnover (cost base) = TO_L + TO_S                                    # K04 12-13; RC 223-225
```
Leg labels in `kr_signal_stats_long.csv`: `LS`, `LO`, `LO_xs_UEW`, `LO_xs_UVW`, `LO_excl_worst`, `LO_excl_worst_xs_UEW/UVW`, `Q1..Q5` (K04 184-231; KR 310).

### A.7 Statistics conventions

| Item | Monthly | Weekly | Index (daily) | Source |
|---|---|---|---|---|
| Annualisation | x12, sqrt(12) | x52, sqrt(52) | sqrt(252) (IC); `af = n_days / years` (K05) | K04 42; IC 10, 302-305; K05 195-206 |
| Newey-West lags | 6 | 4 | 10 (excess vs B&H) | K04 43; K05 247, 275 |
| Sharpe | mean/sd(ddof=1) of raw period returns, rf = 0 | | | K04 15-17; IC 10 |
| Max drawdown | daily series, start capital = first peak | | | KC 128-136; IC 308-310 |
| CAGR (KR) | `(1+total_return)**(ANN/n_periods) - 1` | | `tot**(1/yrs) - 1` | K04 106; RC 265; K05 201 |
| Positive years | years with >= 60 daily obs, compounded | | years with >= 126 sessions | K04 112-117; RC 271-276; IC 62, 337-342 |
| Period membership | by calendar date of the FIRST holding day | | | K04 15-16; RC 108-110 |
| Hit rate | share of periods > 0 | | | K04 109 |

Sub-periods: `SUBPERIODS = full / 1996-2005 / 2006-2015 / 2016-2026` (KC 29-32); `GRID_PERIODS` adds `2015-07..2024-12` and `2016-01..2026-09` (RC 43-47); `SUB3` (RC 48-51). Event windows compound over trading days d with `start_close < d <= end_close` (KC 35-40; K04 170-174): `EVENT_WINDOWS` KC 41-52; `EXCL_WINDOWS` RC 54-60; `CRASH_WINDOWS` RC 61-67; `LV_WINDOWS` (7 crash + 5 rebound) R06 22-35.

### A.8 Base books B1-B4 (exclusion horse race)

```
momq5[k] = quantile_groups(MOM_12_1[k], univ_all[k], 5, k) == 5
base_mem = {'B1': (univ_all, 'EW'), 'B2': (univ_all, 'VWcap5'), 'B3': (univ_large, 'VWcap5'), 'B4': (momq5, 'EW')}   # R04 132-135
BASES labels: B1 'EW ALL universe', B2 'VW ALL capped 5%', B3 'top-200 VW capped 5%', B4 'MOM 12-1 top quintile EW'    # R04 36
filtered book at k: members = mem[k] & ~flag[k]; if that is empty the filter is suspended for that month (members = mem[k])   # R04 140-147
```
Both books pay their own turnover at the same `c`; the statistic is the paired monthly difference `d_k = R_filtered,k - R_unfiltered,k` on identical holding days (R04 20-21).

### A.9 Rebuilt KOSPI (index-lab input)

```
ret_d = sum_i Marcap_{i,d-1} * r_{i,d} / sum_i Marcap_{i,d-1}
  over lines with E[d-1] & MK[d-1]==1 & E[d] & isfinite(r) & Marcap_{d-1} > 0   (include_vehicles=True -> NCLS ignored)
level = cumprod(1+ret) scaled so level(2007-10-31) = 2064.85                   # K05 35-57; used version K05 213
```
Sanity ratios rebuilt/official within 0.23% (KR 204-217). `r[0] = NaN` when loaded (IC 108-109).

---

## B. Exact algorithms

### B.1 Signal definitions at formation t (K02 110-173; R01 223-248)

All use rows <= t; `CL[i]` = cumulative log price; result NaN unless `E[t]` and finite (K02 155-157).

| Name | Formula | Min obs / condition | Source |
|---|---|---|---|
| `MOM_12_1` | `expm1(CL[t-21] - CL[t-252])` | `E[t-252]` | K02 117 |
| `MOM_6_1` | `expm1(CL[t-21] - CL[t-126])` | `E[t-126]` | K02 118 |
| `MOM_12_7` | `expm1(CL[t-126] - CL[t-252])` | `E[t] & E[t-252]` | R01 22, 223 |
| `REV_1M` | `expm1(CL[t] - CL[t-21])` | | K02 119 |
| `HIGH52` | `exp(CL[t] - max_{tau in t-251..t, E[tau]} (log(High_tau/Close_tau) + CL[tau]))` | max finite | K02 120-128 |
| `VOL_3M` | `nanstd(ddof=1)` of valid returns over t-62..t | `>= 40` valid | K02 130-134 |
| `MAX_1M` | max valid return over t-20..t | `>= 15` | K02 135-136 |
| `TURN_1M` | `nanmean(Amount/Marcap)` over t-20..t where `E & Marcap > 0` | `>= 15` | K02 138-142 |
| `SIZE` | `log(Marcap_t)` | | K02 143 |
| `PMA200` | `1 / nanmean(exp(CL[tau] - CL[t]))` over t-199..t | `>= 180` listed | K02 145-147 |
| `BBPCTB` | `rel = exp(CL[tau]-CL[t])` last 20; `m20 = mean`, `s20 = std(ddof=0)`; `%B = (1 - (m20 - 2*s20)) / (4*s20)` | all 20 listed and `s20 > 1e-12` | K02 149-153 |
| `RSI14` | Wilder, `a = 1/14`: `dp = exp(prev_cl) * r`; `au += a*(max(dp,0) - au)`; `ad += a*(max(-dp,0) - ad)`; `rsi = 100 - 100/(1 + au/ad)` (`100` if `ad == 0 < au`); state frozen on non-listed days; `prev_cl` updated only when listed | `nobs >= 3*14 = 42` | K02 176-199 |
| `REV_1W` | `expm1(CL[t] - CL[t-5])` (weekly) | | K02 164 |
| `VSPIKE` | `a5 / a60`; `a5 = mean Amount over listed days t-4..t`; `a60 = mean over t-59..t` | `n60 >= 40`, `a60 > 0` | K02 165-170 |
| `TURN_12M` | mean Amount/Marcap over listed days t-251..t | `>= 120` | R01 22, 226-228 |
| `TURN_3M` | same over t-62..t | `>= 40` | R01 23, 226-228 |
| `VOL_1M` / `VOL_6M` | std of valid returns t-20..t / t-125..t | `>= 15` / `>= 80` | R01 23, 229-232 |
| `MAX_3M` | max valid return t-62..t | `>= 40` | R01 24, 233 |
| `ADV20` | mean Amount t-19..t | `>= 15` rows | R01 33, 236-237 |
| `SD12M` | `std(ddof=1)` of the last 12 month-end-to-month-end returns `expm1(diff(CL[me]))` | listed at all 13 month-ends | R01 38, 239-244 |
| `MOM_E7` | `cum_e7[t-21] - cum_e7[t-252]` with E7 cleaning (`r <= 0.305` from 2015-06-15 else `0.155`, Volume > 0) | | R01 197-200, 245 |

Sort directions (`label -> (freq, book key, long quintile, short quintile)`, K04 27-37):
`MOM_12_1 (5,1)`, `MOM_6_1 (5,1)`, `REV_1M (1,5)`, `HIGH52 (5,1)`, `VOL_3M (1,5)`, `MAX_1M (1,5)`, `TURN_1M_LOW (1,5)`, `TURN_1M_HIGH (5,1)`, `SIZE (1,5)`, `PMA200 (5,1)`, `RSI14_CON (1,5)`, `RSI14_MOM (5,1)`, `BBPCTB_CON (1,5)`, `BBPCTB_MOM (5,1)`, `REV_1W (1,5)`, `REV_1W_VSlow/VSmid/VShigh (1,5)`.
Weekly volume-tercile books: `ter = quantile_groups(VSPIKE, U & isfinite(REV_1W), 3)`, then `quantile_groups(REV_1W, U & (ter == j), 5)` for j in 1..3 (K03 138-144).

### B.2 Exclusion screens F1..F8 and their input flags

Ranking helper (R04 39-48):
```
top_frac(x, U, frac): m = U & isfinite(x); n = m.sum(); if n < 25: none
    r = rankdata(x[m], 'average'); flag[m] = (r - 0.5)/n >= 1 - frac      # frac = 0.20 == quantile_groups(...) == 5
```

Primary filters (R04 6-14, 81-88); every flag is ANDed with `univ_all[k]` (R04 76-80):
```
F1 = quantile_groups(TURN_1M[k], U[k], 5, k) == 5
F2 = quantile_groups(VOL_3M[k],  U[k], 5, k) == 5
F3 = quantile_groups(MAX_1M[k],  U[k], 5, k) == 5
F4 = p6_composite(F, k, U[k], frac=0.10)
F5 = X['F5'][k]                      # any attention-fade event in t-19..t
F6 = nan_to_num(X['DIL_LIT'][k]) > 0.10
F7 = F1 | F2 | F3
F8 = F4 | F5 | F6
```

**F4 lottery composite (P6)** (R04 51-67; R2KR 117):
```
p6_composite(F, k, U, frac=0.10):
    for s in ('VOL_3M', 'MAX_1M', 'TURN_1M'):
        m_s = U & isfinite(x_s);  r_s[m_s] = rankdata(-x_s[m_s], 'average') / m_s.sum()      # pct-rank of -x, average ties
    comp = r_VOL + r_MAX + r_TURN                       # NaN unless all three finite
    m = U & isfinite(comp); order = idx[argsort(comp[idx], kind='stable')]   # ascending composite = most lottery-like first
    q = (1..n)/n;  flag[order[q <= frac]] = True        # ordinal cut: exactly floor(frac*n) names (pandas method='first' equivalent)
```
Cut variants `F4_cut5/15/20/25` (R04 99-100). Average share flagged about 10% (R2KR 211).

**F5 attention-fade (E7)** — daily event flags (R01 11-20, 155-170), formation flag = any event in the last 20 sessions (R01 25, 249):
```
vavg_d   = mean(Volume over the 20 PREVIOUS listed rows), requires >= 15 rows (rolling(20, min 15).mean().shift(1))
vspike_d = E & (VOL > 0) & (VOL >= 5 * vavg) & (R >= 0.05)                                  # R01 159-161
r20_d    = E & E[d-20] & (exp(CL_d - CL_{d-20}) - 1 >= 0.5)                                  # R01 162-164
lu_e7_d  = E & TR & (CLOSE >= HIGH) & (CR >= thr),  thr = 0.295 if d >= 2015-06-15 else 0.145   # R01 165-167 (E7 written definition DC2)
f5ev_d   = vspike | lu_e7 | r20      ;  f5ev_reg = vspike | lu_lock | r20 (variant)          # R01 168-169
F5[k]    = E[t] & (sum f5ev over t-19..t > 0) ; F5_w{5,10,40,60} other windows; F5_vspike / F5_lu / F5_r20 / F5_lureg components; F5_reg   # R01 249-254
```

**F6 dilution** (R01 27-32, 178-191, 234-235):
```
s_d = STK_d / STK_{d-1} on consecutive listed days with both > 0 (else 1);  p_d = CLOSE_d / CLOSE_{d-1} (else 1)
chg_d       = |s_d - 1| > 0.001
splitlike_d = chg_d & (|s_d - 1| > 0.05) & (|s_d * p_d - 1| <= 0.05)       # shares multiplied AND raw close moved by the inverse ratio within +-5%
lit_d       = log(s_d) if chg_d & ~splitlike_d else 0
DIL_LIT[k]  = expm1( sum_{d = t-251..t} lit_d )                              # 252-session share growth ignoring split-like days
a_d  = (1 + CR_d) / p_d  (KRX base-price adjustment factor); a_d := 1 unless |a_d - 1| > 0.005
ni_d = (log(s_d) if chg_d else 0) - log(a_d)
DIL_NI[k]   = expm1( sum_{t-251..t} ni_d )                                   # net issuance (F6b)
F6 = DIL_LIT > 0.10 ; F6_gt5/20/30 thresholds 0.05/0.20/0.30 ; F6b_netissuance = DIL_NI > 0.10      # R04 86, 107-109
```
Diagnostic: 20.3% of literal flags are not confirmed by net issuance (RES r2_kr/r2_kr_excl_f6_diagnostic.csv line 2: `71689,61557,57109,14580,4448,0.203378`; R2KR 217).

Neighbour / variant list (36 variants + 8 primary = 44 definitions, 4 bases -> 176 trials; R04 89-118; R2KR 348): `F1_cut10/15/25/30`, `F2_cut..`, `F3_cut..` (via `top_frac`), `F1_TURN3M`, `F2_VOL1M`, `F2_VOL6M`, `F3_MAX3M` (frac 0.20), `F4_cut5/15/20/25`, `F5_w5/10/40/60`, `F5_reglock`, `F5_vspike_only`, `F5_lock_only`, `F5_r20_only`, `F6_gt5/20/30`, `F6b_netissuance`, `F7_cut10/30`, `F8_F6b`, `F8_reglock`. Each variant belongs to its primary's family (R04 116-118).

Jaccard overlap per formation = `|A & B| / |A | B|`, mean over formations; `share_of_ALL_a = mean(A.sum/U.sum)` (R04 236-243; table R2KR 206-215).

### B.3 Locked limit-up / limit-down detection from OHLC (R01 12-15, 155-158)

```
L_d = daily price limit (%) of the stock's market on day d:
   KOSPI : 6 before 1996-11-25; 8 from 1996-11-25; 12 from 1998-03-02; 15 from 1998-12-07; 30 from 2015-06-15
   KOSDAQ: 8 before 1998-05-25; 12 from 1998-05-25; 15 from 2005-03-28; 30 from 2015-06-15
lu_lock_d = E & TR & (CLOSE >= HIGH) & (CR > 0) & ((ChangeCode == 4) | (CR*100 >= L_d - 0.5))
ld_lock_d = E & TR & (CLOSE <= LOW)  & (CR < 0) & ((ChangeCode == 5) | (CR*100 <= -(L_d - 0.5)))
LU_LOCK_T[k] = lu_lock[t_k];  LD_LOCK_T[k] = ld_lock[t_k]                                        # R01 256-257
```
`CR` = raw ChangesRatio/100; `LOW` 0 -> Close. Audit (R04 326-339): for consecutive formations `new = mem[k] & ~mem[k-1]`, `out = mem[k-1] & ~mem[k]`; `share_entries_locked = (new & LU[k]).sum()/new.sum()`, `share_exits_locked = (out & LD[k]).sum()/out.sum()`. Fills at locked closes are assumed filled in every book (R2KR 244, 378).

### B.4 Screen-versus-unscreened excess-return test (R04 182-222; R2KR 115)

```
d  = diff_series(P, X_filtered, U_base, c)[0]       # monthly, both net of own costs at c
x  = d[pm] finite
ann_diff = mean(x)*12 ; te = std(x, ddof=1)*sqrt(12) ; ir = mean/std*sqrt(12) ; nw_t = nw_tstat(x, 6)
sharpe_filtered / sharpe_unfiltered from stats() on the LO series of each book
maxdd_diff = maxdd_filtered - maxdd_unfiltered  (+ = shallower)
full period only: boot_pvalue(x) -> boot_p (= p_null), boot_p_perc, boot_ci90_lo/hi (x12)
pct_years_pos = share of calendar years (>= 60 days) with (year_filtered - year_unfiltered) > 0
excl_share_names = mean over k of flagged share of base members; excl_share_weight = mean of base weight flagged
```
Bootstrap (RC 301-328): circular block bootstrap, `block = BOOT_BLOCK = 3` months, `B = BOOT_B = 2000`, seed 20261002, one common index matrix per series length (paired across filters):
```
boot_index(n, block, B, seed): nb = ceil(n/block); st = rng.integers(0, n, (B, nb)); idx = ((st[:,:,None] + arange(block)) % n).reshape(B, nb*block)[:, :n]
mb = x[idx].mean(1); mu = x.mean()
p_null = (1 + #{mb - mu >= mu}) / (B + 1)        # H0 re-centred, one-sided mean > 0   <- reported as boot_p
p_perc = (1 + #{mb <= 0}) / (B + 1)
ci90   = quantile(mb, [0.05, 0.95])
```
Round-1 form of the same test: `LO_excl_worst_xs_UEW/UVW` = NOTQ{worst} book (net c) minus the universe book GROSS (K04 209-221). Cross-check: round-1 "+3.62%/yr, t 5.63" (gross benchmark) becomes "+4.28%/yr" when the unfiltered EW book pays its own 1.9x/yr cost (R2KR 219).

Indicative gate on the paired difference (R04 252-322; step text R2KR 234):
```
n_trials = 176 ; var_sr = var(ddof=1) of monthly SR (= mean/std of d) over all (base, filter) pairs  -> 0.0163254 (RES r2_kr_excl_gate.csv line 2)
g1 walk-forward: daily diffs of the 8 primary filters; IS 756 sessions, embargo 21, OOS 126; pick argmax IS IR (mean/std daily); stitched OOS IR*sqrt(252) > 0
g2 Lo SE with eta(q) (RC 340-353): SR_ann - 1.645*SE_ann > 0  AND  10-session CBB (B 2000) 5% quantile of daily-diff IR > 0
g3 deflated_sharpe(x, 176, var_sr) >= 0.95   (also reported: null variance 1/(T-1); per-base variance with 44 trials)
g4 CSCV S=16 on monthly diffs: (pbo_primary8 <= 0.05 or winner_loses_primary8 <= 0.10) AND same for all 44 variants
g5 boot_p <= 0.10
g6 at net70: sharpe_filtered > 0 and ir > 0
g7 plateau: share of same-family neighbours with ir >= 0.5*centre ir  >= 0.5
g8 pct_years_pos >= 0.6
g9 haircut (reported only): 0.4 * ann_diff, 0.4 * ir
verdict: 'PASS' if 8/8 else 'REJECT' if ((not g5 and not g2) or (pbo_all > 0.2 and winner_loses_all > 0.10) or not g6) else 'REVISE'
```

### B.5 Break-even cost per side

Not a function in the scripts; derived from the reported numbers (KR 12, 303): `break_even_per_side = gross_annual_LS_mean / LS_turnover_per_year` with turnover = both legs. Check: REV_1W EW `0.199 / 159.5 = 12.5 bp`; VW `0.387 / 174.5 = 22.2 bp` (KR 38, 62). Linear in cost because `net = gross - c * turnover` (A.6). Report next to the venue cost (35 bp KRX stock, 3 bp ETF, 5 bp futures, 50 bp KIS); a signal whose break-even is below the venue cost is DROP (KR 303-304).

### B.6 Momentum constructions

Independent double sort (R03 3-10, 71-99): `q5 = quantile_groups(sig[k], U[k], 5, k)`, `t3 = quantile_groups(tdef[k], U[k], 3, k)` each over the whole ALL universe; cell = `(q5 == q) & (t3 == j)`; signals `MOM_12_1, MOM_12_7, MOM_6_1, HIGH52`; turnover definitions `TURN_12M` (primary) and `TURN_1M`; legs LS (Q5-Q1) gross/net35/net70 and LO_xs_UEW / LO_xs_UVW with gross benchmark (`cb=0.0`, R03 300-303).
Dependent sort (round 1, R03 100-109): `ter = quantile_groups(TURN_1M, U & isfinite(MOM_12_1), 3)`, then `quantile_groups(MOM_12_1, U & (ter == j), 5)`.
Deciles (P6): `quantile_groups(sig, U, 10)` D10-D1, holding 2001-02..2026-09 (R03 110-114, 415-422).
Top-500 (E5/P2): deciles and quintiles inside `top500`; looser `TOP500L` (listed, traded, operating, price >= 1000, finite MOM, Marcap > 0, no 200-day/limit screens) (R03 116-132).
E7 exact engine (R03 179-226): tercile by `avg_pct(TURN12_E7)` over all listed non-SPAC; top quintile = `pd.qcut(s.rank(method='first'), 5, labels=False) == 4`; legs and benchmark re-weighted EW every day (`nanmean` of E7-cleaned returns); cost `2 * tau * 0.0035` on the first day, `tau = 1 - |L & prev| / |L|`; iid daily t.
Eom/KJFS design (R03 136-157): formations 2000-06-30..2019-05-31 excluding 2000-12; drop `avg_pct(SD12M) > 0.9`; turnover groups `avg_pct(TURN_12M) > 0.7` (high) / `<= 0.3` (low); winners `ordinal_pct(mom) > 0.8`, losers `<= 0.2`; EW gross. Verdicts R2KR 101-109: KJFS NOT REPRODUCED (its sign appears only with unadjusted holding returns).

**R-03 own-volatility scaling** (R05 11, 52-59; R2KR 248):
```
sigma126_t = rolling(126, min_periods=126).std(ddof=1)(x_t) * sqrt(252)   # x = unit-sleeve gross daily return through t
s_t = min(1.0, 0.12 / sigma126_t) if finite and > 0 else 1.0 ; applied to day t+1
```
**R-04 Daniel-Moskowitz gate** (R05 12-13, 62-78):
```
sig_t = rolling(126, min 126).std(ddof=1)(KOSPI r) * sqrt(252)
q_t   = expanding(min_periods=252).quantile(2/3)(sig)      ; hivol_t = isfinite(q_t) & (sig_t > q_t)
j = last month-end index <= t ; if j >= 24: r24_t = level[me[j]] / level[me[j-24]] - 1 ; bear_t = r24_t < 0
dm_t = 0.5 if (bear_t & hivol_t) else 1.0
```
On 9.8% of days; 9 raw onsets (RES r2_kr/r2_kr_dm_gate_onsets.csv lines 2-10): 1997-05-31, 1997-10-08, 1997-10-11, 1999-04-19, 1999-04-21, 1999-04-29, 2001-01-04, 2008-10-31, 2020-03-20.

**Overlay application and costs** (R05 15-17, 36-49, 81-105):
```
LS sleeve:  x = series(Q5, S=Q1, c=0) daily ; to = TO_L + TO_S ; D = 2
LO sleeve:  x = series(Q5, B=U, c=0, cb=0) daily ; D_k = sum |w_Q5 - w_U| at formation
for day d in period k (a..b-1): sd = s[d-1]
    cost = 0
    if d == a:  cost += c*sd*to[k]   (LS)   |   c*((1-sd)*TO_U[k] + sd*TO_Q5[k])   (LO: book is (1-s)U + s Q5)
    if prev_s is not None and d != first_day: cost += c * D[k] * |sd - prev_s|
    out[d] = sd * x[d] - cost ; pos[d] = sd ; prev_s = sd
controls: 'static' s=1 ; 'VS (own vol, 12%, cap 1)' ; 'DM gate (KOSPI, floor 0.5)' ; 'VS x DM' = s_vs * dm
same-exposure static comparator = apply_overlay with constant s = mean(pos)   (R05 233-242)
```

### B.7 Name-level stop test (E5 DC-02) (R05 18-22, 117-179)

```
stoploss_book(members_fn, rule, mc, stop, side, exit_lag):
  per period: w = weights (stuck holdings carried as in Book); TO[k] = 1 (k==0) else sum |w - v_prev|[tradable]
  G = cumprod(1 + Rb[:, idx]*A[:, idx])  (growth since the formation close)
  trig = G <= 1 - stop  (side 'long')  |  G >= 1 + stop  (side 'short')
  dexit = first trigger index + exit_lag ; exit only if dexit <= nd-1
  Gi[dexit+1:, j] = Gi[dexit, j]   (proceeds frozen in cash after the exit close; the position earns the exit day when exit_lag = 1)
  sold[dexit] += w_j * Gi[dexit, j] ; cash carried to the next rebalance
ls_from_legs(L, S, c): cc_d = c*(TO_L + TO_S) + c*cumsum(exits_L + exits_S)_d ; C_d = 1 + (V_L - 1) - (V_S - 1) - cc_d
variants: (None, 1, 'no stop'), (0.15, 1, '15% stop, exit next close'), (0.15, 0, '15% stop, exit same close'), (0.10, 1, '10% stop, exit next close')   # R05 270-271
```
Engine check: the no-stop custom engine must equal `run_books` Sharpe to 4 decimals (R05 288-298; R2KR 372).

### B.8 Low-vol book vs the CAPM / S_beta comparator (R06 8-12, 38-56, 104-139)

```
ols_nw(y, x, lags=6): OLS y = a + b x ; Bartlett-NW covariance S = sum e^2 X X' + sum_l w_l (G_l + G_l') ; V = (X'X)^-1 S (X'X)^-1 ; returns a, b, t_a, t_b, r2
book = lowest VOL_3M quintile of ALL, EW and VW, gross and net35 ; markets: 'VW ALL universe (gross)', 'EW ALL universe (gross)', 'rebuilt KOSPI' (monthly compounded)
beta = b ; alpha_ann_rf0 = a*12 ; alpha_t = t_a ; alpha_ann_if_rf2pct = a*12 - (1-b)*0.02 ; alpha_ann_if_rf4pct = a*12 - (1-b)*0.04
excess_vs_mkt_ann = mean(book - mkt)*12 ; excess_t = nw_tstat(book - mkt, 6)
up_capture = mean(book[mkt > 0]) / mean(mkt[mkt > 0]) ; down_capture = mean(book[mkt < 0]) / mean(mkt[mkt < 0])
windows: LV_WINDOWS (7 crash 'C ...', 5 rebound 'R ...'); book_minus_vw, book_minus_ew
```
The assigned files never name an "S_beta" object; the comparator realised here is the fitted CAPM line (`S_beta,t = b * r_mkt,t`, alpha = `mean(book - S_beta)` with rf = 0). Verdict rule used: judge on "drawdown-first, Sharpe-non-inferiority terms (E7's K-LV framing), not on alpha" (R2KR 344). See Ambiguity 6.

### B.9 Index rules

Weight builders (IC 219-281; all decided at the close of t from prices/returns <= t; NaN while undefined; assertion `0 <= w <= 1`):
```
'bh'      w = 1
'sma'     m = rolling(n, min n).mean(p); band 0: w = (p > m) ; band b > 0: state machine enter p > m(1+b), exit p < m(1-b) (IC 188-201)
'ens'     votes_L = (p / p[t - round(L*scale)] - 1 > 0) for L in lbs ; map 'share': w = mean(votes) (NaN until all lookbacks exist) ; 'binary2': w = (sum votes >= 2)
          centre ENS = dict(kind='ens', lbs=(20, 60, 120, 250), scale=1.0, map='share')   (I01 34)
'tsm_m'   me = last session of each month ; sig = (me / me.shift(months) - 1 > 0) ; ffill (held from the next session to the next month-end)   (IC 204-212)
'tsm_d'   w = (p / p[t-days] - 1 > 0)
'vt'      sig = rolling(window, min window).std(ddof=1)(r) * sqrt(252) ; w = min(cap=1.0, target / sig)   ; centre VT: window 20, target KOSPI 0.20 / SPY 0.15
'ewma_vt' v = ewm(alpha = 1 - lam, adjust=False).mean(r^2), v[:21] = NaN ; w = min(1, target / (sqrt(v)*sqrt(252))) ; lam 0.94
'prod'    w = build(a) * build(b)                       # ENS x VT: elementwise product, no floor
'ovl'     b = build(base) ; how 'clip': w = clip(b, 0.5, 1.0) ; how 'lin': w = 0.5 + 0.5*b
engine    h = w[i0-1:i1] ; net = h * r[i0:i1+1] ; net[1:] -= c * |diff(h)|   (initial entry not charged)   (IC 284-293)
```
Declared neighbour grids (I01 37-61): SMA200 `window {150,200,250} x band {0, 0.01}` (5); ENS `lbs {(20,60), (20,60,120,250), (60,120,250)} x scale {0.75, 1, 1.25}` (8); TSM12 `months {9, 15}` + `tsm_d days {189, 252, 315}` (5); VT `window {10,20,40} x target {-0.05, 0, +0.05}` (8); ENSxVT `ENS scale {0.75,1,1.25} x VT target shift {-0.05,0,+0.05}` (8). Binary onset gaps: SMA200 200, TSM12 252, ENS >=2/4 250 (I01 40, 47, 58). Overlay forms (I01 64-76): 'sleeve (0 allowed)', 'overlay clip[0.5,1]', 'overlay 0.5+0.5x (E3 long/half)'; with VT the overlay multiplies the VT weight.

Round-1 KOSPI timing (K05 79-141, 188-192), evaluation 1996-06-03..2026-09-29, cash 0%:
```
sma(p,n) rolling mean ; ema(p,n) ewm(span=n, adjust=False) ; rsi_wilder(p,n): ewm(alpha=1/n, adjust=False, ignore_na) of up/down moves, first n NaN
state_machine(enter, exit): pos 1 from an entry close until an exit close
monthly_pos: fn on month-end closes, decision held to the next month-end
core rules: 'SMA200 (close > SMA200)' ; '10M_SMA (monthly)' m > rolling(10).mean ; 'SMA50 > SMA200' ; 'MACD(12,26,9) > signal' ;
  'Connors RSI(2)<10 & >SMA200, exit >SMA5' ; 'Bollinger(20,2) MR: buy < lower, exit > middle' (sd ddof=0) ;
  'Donchian 20-high entry / 10-low exit' (hi/lo of shifted closes) ; 'TSMOM 12M sign (monthly)' m/m.shift(12) - 1 > 0
strat_returns(pos, r, c): pp = [0, pos[:-1]] ; chg = |diff([0, 0, pos[:-1]])| ; ret = pp*r - c*chg   (cost on t+1)
```
Family of 303 variants (K05 144-184): `P>SMA{5..250 step 5}`, `P>EMA{10..250 step 10}`, `P>SMA{50,100,150,200,250} band{1,2,3}%`, SMA/EMA crosses fast {5,10,20,30,50,75,100,150} x slow {50,100,150,200,250} (fast < slow), MACD 10 triplets (c=1 -> `m > 0`), Connors `RSI{2,3,4,5,7,14}<{5..30}&>SMA200 exitSMA5`, `RSI{2,5,14}>50 (momentum)`, `BB({10,15,20,30,40,50},{1.5,2.0,2.5}) MR / breakout`, `Donchian{en}/{ex}` (en in {10,20,40,55,100,150,200,250}, ex in {5,10,20,40,50,100}, ex < en), `TSMOM{1,2,3,6,9,12}M monthly`, `TSMOM{20..240 step 20}d daily`, `{3..12}M_SMA monthly`.

### B.10 CARD-P protective scorecard versus the same-exposure static book S (IC 15-29, 585-748; R2IDX 42)

```
net1, h = book(spec, c1) ; net2 = book(spec, c2) ; rbh = buy-and-hold returns ; xbar = mean(h) ; S = xbar * rbh (no cost)
PC-1  pc1_dmdd_pp_1x = (mdd(net1) - mdd(S))*100 ; pass_1x = dmdd >= 3.0 and mdd(net1) > mdd(rbh) ; same at 2x
PC-2  pc2_tail_ratio = mean(h[worst k days of rbh]) / mean(h), k = ceil(0.05*n), argsort stable ; pass <= 0.90
PC-3  d = net1 - S ; blk = max(10, ceil(PW_circ(d)), ceil(PW_circ(d^2)))            (B.11)
      Bp = paired CBB Sharpes of [net1, S] with block blk, 2000 reps, seed 11 (arch CircularBlockBootstrap indices)
      dp = SR*(net1) - SR*(S) ; pc3_p_ni = mean(dp <= -0.10) ; pass = p_ni <= 0.10 and dSR_1x >= -0.10 ; pc3_point_pass_2x = dSR_2x >= -0.10
      also: pc3_dsr_ci90_lo/hi = quantile(dp, .05/.95) ; pc3_share_beats_S = mean(dp > 0)
PC-4  episodes = drawdown_episodes(mk) ; benefit = cum(net1[ep]) - cum(S[ep]) ; pass = n_positive >= 3 and max(pos)/sum(pos) <= 0.5
PC-5  year_table (years with >= 126 sessions, compounded via log1p) ; pass = share(year > 0) >= 0.60 ; also share of years lagging S
PC-6  neighbours: keep if (mdd(n1) - mdd(S_n))*100 >= 0.5 * pc1_dmdd_pp_1x and sharpe(n1) - sharpe(S_n) >= -0.10 ; pass = share_keep >= 0.5 (n/e if no grid)
PC-7  n_sessions >= 882 (756+126) ; n_episodes >= 5 ; binary rules: declustered onsets (chain-merged within gap) >= 30
CARD-O from the same bootstrap at block 10: o_step5_p_block10 = mean(d10 <= 0) (pass <= 0.10) ; o_step2 = 5% quantile of SR*(net1) > 0 ; o_step3_psr0 = PSR(net1, 0) ; o_step6 = sharpe(net2) > 0
verdict order (IC 708-748): 'INSUFFICIENT DATA (sufficiency)' if PC-7 fails -> 'REJECT' if PC-1(1x) or PC-2 or dSR_1x < -0.10 or PC-4 n_positive < 3
   -> 'INSUFFICIENT DATA (inconclusive)' if p_ni > 0.10 or largest share > 0.5 -> 'REVISE' if PC-1/PC-3 at 2x, PC-6, or PC-5 fail -> 'PASS'
   verdict_if_sufficient = same with PC-7 waived ; cardO_verdict in {'REJECT (step 5)', 'steps 2/5/6/8 pass', 'REVISE (step 2/6/8)'}
```
Other metrics: `cvar5`, `time_under_water(depth 0.10)`, `exposure_on_20_worst_days`, `turnover_per_year = sum|diff(h)| / years` (IC 325-359, 567-571, 605-619).
Episodes: `SPEC_EPISODES` (IC 389-405: GFC 2008-09-01..2009-03-09; 2011 07-22..10-03; 2015-16 08-10..2016-02-11; 2018Q4 09-20..12-24; 2020 crash 02-19..03-19 KOSPI / 03-23 SPY; 2022 01-03..09-30 KOSPI / 10-12 SPY; Aug-2024 07-31..08-09 KOSPI (include_start True) / 07-16..08-05 SPY; Dec-2024 12-03..12-09 KOSPI; Apr-2025 03-28..04-09 KOSPI (True) / 02-19..04-08 SPY; Mar-2026 02-27..03-31 KOSPI (True); Jul-2026 06-22..07-30; Sep-2026 08-31..09-30 SPY only) plus KOSPI peak-to-trough 1997-98 and 2000-01 computed from the data (IC 428-434, 443-447). `include_start=False`: returns dated after the start close through the end close (IC 418-425). `SPEC_COST_EPISODES`: 2009 rebound 03-09..06-30; 2020 rebound 03-19 KOSPI / 03-23 SPY..06-08; H1-2026 bull 01-02..06-30 KOSPI (IC 407-411). Under-water episodes (E3 style) IC 479-504. `declustered_onsets(h, gap)`: onsets where `h[t-1] >= 0.5 & h[t] < 0.5`; the chain count increments when `on[k] - on[k-1] > gap` (IC 507-522).
Start-date sweep (I01 79-81, 139-160): `SWEEP_STARTS KOSPI = 1996-06-03, 1996-09-02, 1997-01-03, 1999-01-04, 2001-01-02, 2006-01-02, 2011-01-03, 2016-01-04 ; SPY = 1999-05-03, 2001-01-02, 2006-01-03, 2011-01-03`; `pc4_truncate=True`; `pc6_override` = plateau from the primary run.

### B.11 Politis-White block length (IC 363-366, 624-627)

```
pw_block(x) = arch.bootstrap.optimal_block_length(x)['circular'].iloc[0]
pc3_block   = int(max(10, ceil(pw_block(d)), ceil(pw_block(d**2))))
```
Observed blocks (RES r2_idx/r2_idx_protective_scorecard.csv `pc3_block`): SMA200 206, ENS 178, TSM12 211, VT 186, ENSxVT 187 (lines 2-6). Finding: 10-session blocks are too short for index returns (step-2 false pass 6.9% vs 5%, step-5 12.8% vs 10%); the macro cards' `max(10, Politis-White)` rule fixes this (R2IDX 15).

### B.12 Hansen SPA family test (K05 13-14, 269-277, 332-350; US 78, 178-179)

```
spa = arch.bootstrap.SPA(L_b = -r_bh[mask], L_m = -Rn[mask] (net 3 bp), block_size=15, reps=2000, bootstrap='stationary', studentize=True, seed=20261002)
spa.compute(); pvalues 'lower', 'consistent', 'upper'            # d_k = r_rule - r_B&H ; H0: no rule beats buy-and-hold on mean daily return
best rule = argmax Newey-West t (10 lags) of the daily excess ; time split: select on 1996-06-03..2012-12-31, evaluate 2013-01-01.. (by excess t and by Sharpe)
exposure-matched (supplementary): Lm = -(Rn - rbh * xk), xk = mean exposure of rule k ; benchmark loss = 0 ; SPA(np.zeros, Lm, ...)  (K05 332-350)
```
US settings: 322 variants, stationary bootstrap block 15 (10 and 20 checked), 2000 reps, seed 20261002; loss = -(net rule return - net buy-and-hold return) (US 78). Implementation caveat: `arch 8.0.0` SPA does NOT studentize (the flag only labels output); the US lab reports arch p-values as produced plus Hansen's studentized SPA from the same draws; its replica reproduces arch exactly at the same seed (US 178-179).

### B.13 Bootstrap false-pass (gate size) simulation (I02 3-33, 43-156)

```
VOL = 0.15 ; BSR = 0.40 ; GEN_BLOCK = 126 ; BOOT_BLOCK = 10 ; RBOOT = 500 ; YEARS = [5,8,10,12,15,18,20,25,30,40,50]
SR_GRID = [0,0.2,0.3,0.4,0.5,0.6,0.7,0.8] ; IR03 = {rho 0: 0.4+0.3*sqrt(2), 0.5: 0.7, 0.9: 0.4+0.3*sqrt(0.2)} ; RHOS = [0,0.5,0.9] ; NTRIALS = [1,9,27,100]
source z = de-meaned rebuilt-KOSPI daily returns rescaled to 15%/yr ; path = circular block bootstrap of z with 126-session blocks, 50*252 sessions
generators: 'kospi' ; 'kospi_sign' (independent random sign per day) ; 'iid' (normal)
seeds: data default_rng([11, pid, 1]) ; bootstrap default_rng([11, pid, 2])
strategy x = z + SR*0.15/252 ; benchmark b = rho*z + sqrt(1-rho^2)*w + 0.4*0.15/252 (w independent path)
step2: 10-session CBB (RBOOT resamples) 5% quantile of SR*(x) > 0 ; step2_lo: srd - 1.6448536269514722*sqrt((1+0.5 srd^2)/T) > 0
step3: DSR = Phi((srd - sr0)*sqrt(T-1)/den) >= 0.95, sr0 = z_n(N)*sqrt(1/(T-1)), z_n(N) = (1-gamma)*Phi^-1(1-1/N) + gamma*Phi^-1(1-1/(N e)), z_n(1) = 0, den = sqrt(1 - g3 srd + (g4-1)/4 srd^2)
step5: paired resamples; p5 = mean(SR*(x) - SR*(b) <= 0) ; pass p5 <= 0.10
step8: share of the Y consecutive 252-session years with compounded return > 0  >= 0.6
joint = step2 & step3 & step5 & step8 ; MC SE = sqrt(p(1-p)/NPATH)
analytic iid (I02 186-204): step2 Phi(SR*sqrt(Y) - 1.645) ; step3 Phi(SR*sqrt(Y) - z_n(N) - 1.645) ; step5 Phi((SR-0.4)*sqrt(Y)/sqrt(2(1-rho)) - 1.2816) ; step8 Binom.sf(ceil(0.6Y)-1, Y, Phi((SR*0.15 - 0.15^2/2)/0.15))
years_for_power: linear interpolation of pass_rate vs years to 50% / 80% ('>50' if never reached, '<=5' if at the first point)   (I02 207-229)
```

### B.14 Averaging-bias test (Shiller monthly averages) (I03 3-16, 25-78, 113-136)

```
monthly_from_daily(s): me = last close per month ; avg = mean of daily closes per month
signals(X): SMA10 = X > rolling(10).mean (needs 10 obs) ; TSM12 = X/X.shift(12) - 1 > 0 ; 'TSM12 L/S' = 2*TSM12 - 1
evaluate(sig_X, ret, window, lag): pos = sig.shift(lag) (lag 1 standard, lag 2 = LAG1) ; rr = pos*ret ; stats monthly: mean*12, sd*sqrt(12), sharpe, cagr, max_dd, acf1, time_in_market, switches_per_year
sources: 'SPY month-end' (me, r_me) ; 'SPY month-average' (avg, r_avg) ; 'SPY month-average LAG1' ; 'SPY HYBRID (avg signal, month-end returns)' ; Shiller price / total return (D/12 added; dividends after the last reported month imputed at the last 12-month yield)
bias rows: sharpe_inflation = sharpe_avg - sharpe_me ; timing_benefit_* = sharpe_rule - sharpe_bh ; timing_benefit_inflation ; mdd_understatement_pp = (mdd_avg - mdd_me)*100
windows W_SPY = 1999-03..2021-03 ; W_ARCH = 2000-03..2018-12
```
Rules of thumb for Shiller-based monthly trend results: take the LAG1 Sharpe for the 10-month SMA; LAG1 minus about 0.13 for the 12-month sign; drawdowns from averages understated by up to 5.2 pp (R2IDX 295).

### B.15 Pair-share computation (CR-07) (R3P 1-25, 30-36)

```
d = KRX marcap rows with Market == 'KOSPI' (all lines, incl. preferred) ; common = Code[-1] == '0'
CR07_pair_incl_pref_over_all_lines = (Marcap['005930'] + Marcap['005935'] + Marcap['000660']) / sum Marcap(all KOSPI lines)
alt_pair_common_over_all_lines           = (005930 + 000660) / all lines
alt_pair_common_over_common_only         = (005930 + 000660) / common lines
alt_pair_incl_pref_over_common_plus_pref = (005930 + 005935 + 000660) / (common lines + 005935)
threshold 0.45 ; report first session > 0.45 in 2026, peak date/share, sessions > 0.45
```

---

## C. Statistics helpers vs `core/quant/validate.py`

| Lab helper (source) | validate.py counterpart (lines) | Same? / difference |
|---|---|---|
| `nw_tstat(x, lags)` KC 111-125 | `newey_west_t(d, lag)` V 216-228 | Identical Bartlett form; guards differ (`n < lags+3` vs `n < 5`). Reuse. |
| `sharpe(x)` IC 302-305; `stats()['sharpe']` RC 258 | `sharpe(daily)` V 80-86 | Same (ddof=1, sqrt(252)); lab returns NaN when sd = 0, validate 0.0. Monthly Sharpe needs sqrt(12): no parameter in validate. |
| `max_drawdown` KC 128-136; `mdd` IC 308-310 | none in validate (`backtest.mdd`, `strategies.py` inline) | Same definition (start capital first peak). |
| `lo_sharpe_se(x, ann)` RC 340-353 (iid SE x Lo eta(q) serial-correlation factor) | `lo_se(daily)` V 89-96 (iid only) | Not equivalent; eta(q) missing. |
| `boot_sharpe_ci` RC 331-337 (percentile CBB, block 10, seed 20261002) | `block_bootstrap_ci` V 106-126 (studentised, seed 11) | Different interval type. |
| `boot_sharpes` IC 369-381 (paired CBB via arch indices; dp = SR*a - SR*b) | `sharpe_diff_bootstrap(a, b)` V 129-151 | Same concept; validate returns only `p = mean(d <= 0)` and the CI. PC-3 needs `mean(d <= -0.10)` and the PW block: extend with a `margin` argument and `block` from B.11. Index generator differs (arch vs numpy) -> bootstrap p-values match only to tolerance. |
| `deflated_sharpe(x, n_trials, var_trials_sr)` RC 356-370 | `deflated_sharpe(daily, n_trials, sr_sd_daily)` + `expected_max_sharpe` V 154-180 | Same formula; lab `N = max(n_trials, 2)` (SR0 > 0 even for one trial) vs validate `n == 1 -> 0`; lab pandas skew/kurt (bias-corrected) vs scipy (biased). The gate sim uses `z_n(1) = 0` (I02 61-64), i.e. validate's convention. |
| `psr(x, sr0_ann)` IC 345-355 | `deflated_sharpe(..., n_trials=1)` | Equivalent. |
| `pbo_cscv(M, S=16)` RC 373-407 | `pbo_cscv(pnl, S=8)` V 183-208 (S=16 when T >= 2000, V 442) | Same CSCV; lab default S=16 on 366 monthly rows; lab `winner_loses_share` = validate `prob_loss`; validate adds `slope`. |
| `boot_pvalue` RC 314-328 (null-centred mean p, paired common index) | none | New helper needed (used for g5 / `boot_p`). |
| walk-forward loop R04 265-279 (IS 756, embargo 21, OOS 126, select by daily IR) | `walk_forward(pnl, dates, w_is=756, w_oos=126, embargo=0, min_is=504)` V 288-324 | Same mechanics; pass `embargo=21`; selection metric is Sharpe of daily columns (`_col_sharpe`) = lab IR up to sqrt(252). |
| plateau R04 296-299 (same-family neighbours keep >= 0.5 x centre IR) | `plateau_share(grid, sharpes, best, domain)` V 327-361 (+-1-step grid neighbours) | Neighbour set differs (family list vs adjacent grid points); PC-6 keep rule (IC 671) adds dSR >= -0.10. |
| years >= 60 days compounded K04 112-117; `year_table` >= 126 sessions IC 337-342 | `year_stats(dates, pnl)` V 364-371 (summed, no min-days filter) | Different; align per card. |
| `ols_nw` R06 38-56 | none | New (CAPM beta/alpha with NW SE). |
| Hansen SPA (arch) K05 271 | none | External dependency; see Ambiguity 9. |
| `pw_block` IC 363-366 | none (`GATE['block'] = 10` fixed, V 54) | New; arch `optimal_block_length`. |
| `tail_ratio`, `cvar`, `time_under_water`, `declustered_onsets`, `underwater_episodes`, `window_slice` IC 325-359, 418-522, 567-571 | none | New (CARD-P package). |
| `cap_weights` RC 129-146; `quantile_groups` K03 46-71; `top_frac` R04 39-48; `p6_composite` R04 51-67 | none | New (sleeve construction). |
| `dm_test` V 230-238 | no lab equivalent | unchanged. |

GATE constants already in validate (V 51-73): `w_is 756, w_oos 126, min_is 504, ci_level 0.90, bootstrap_B 2000, block 10, dsr_min 0.95, pbo_max 0.05, pbo_reject 0.20, oos_is_min 0.5, years_pos_min 0.60, plateau_min 0.5, trades_min 100, trades_floor 30, oos_years_min 5, haircut 0.6, cost_stress 2.0, pbo_min_configs 8, prob_loss_max 0.10, bench_p_max 0.10`. The lab's g9 haircut multiplies by 0.4 (= 1 - 0.6 haircut, R04 316) and the lab's g4 rule mirrors `pbo_max` / `prob_loss_max`.

---

## D. Reference constants for acceptance tests (file, line, value)

All paths relative to `datalab/results/` unless marked. Deterministic quantities (returns, weights, drawdowns) can be matched exactly on the same panel; bootstrap p-values only to tolerance (Ambiguity 10).

**Round-1 reproduction (r2_kr/r2_kr_reproduce_r1.csv)** — tol 0.0 on the same panel:

| Line | Item | Value |
|---|---|---|
| 2-6 | MOM_12_1 LS EW gross: ann_mean / sharpe / nw_t / max_dd / turnover_per_year | 0.09337 / 0.44716 / 2.66631 / -0.55088 / 14.65560 |
| 7-10 | MOM_12_1 LS EW net35: ann_mean / sharpe / nw_t / max_dd | 0.04208 / 0.20132 / 1.19781 / -0.64378 |
| 12-14 | TURN_1M_LOW exclude-worst xs UEW net35: ann_mean / nw_t / pct_pos_years | 0.03617 / 5.62866 / 0.87097 |
| 15-17 | VOL_3M exclude-worst xs UEW net35 | 0.02982 / 4.66743 / 0.83871 |
| 18-19 | UNIV ALL EW net35 ann_mean; turnover/yr | 0.06641; 1.89331 |
| 20-21 | MOM_12_1 Q5-Q1 in high TURN_1M tercile, mean %/month; NW t | 1.43671; 3.41451 |

**Exclusion screens (r2_kr/r2_kr_excl_summary.csv, cost net35)**: header line 1 = `base,filter,family,primary,cost,ann_diff,te,ir,nw_t,sharpe_filtered,sharpe_unfiltered,cagr_filtered,cagr_unfiltered,cagr_diff,maxdd_filtered,maxdd_unfiltered,maxdd_diff,turnover_filtered,turnover_unfiltered,n_months,boot_p,boot_p_perc,boot_ci90_lo,boot_ci90_hi,pct_years_pos,n_years,excl_share_names,excl_share_weight`.

| Line | base,filter | ann_diff | te | ir | nw_t | sharpe filt/unfilt | maxdd_diff | turnover filt/unfilt | boot_p | pct_years_pos | excl_share_names/weight |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2 | B1,F1 | 0.0427971 | 0.0371621 | 1.15163 | 6.61561 | 0.382019 / 0.222031 | 0.0240942 | 3.30882 / 1.89331 | 0.00049975 | 0.935484 | 0.200007 / 0.200007 |
| 11 | B1,F4 | 0.0307644 | 0.0201137 | 1.52953 | 8.33514 | 0.332198 / 0.222031 | 0.0169892 | 2.78453 / 1.89331 | 0.00049975 | 0.903226 | 0.0993712 / 0.0993712 |
| 143 | B2,F4 | 0.00850299 | 0.0124225 | 0.684482 | 3.86861 | 0.323787 / 0.289931 | 0.010324 | 0.795056 / 0.408877 | 0.00149925 | 0.774194 | 0.0993712 / 0.029592 |
| 275 | B3,F4 | 0.00488066 | 0.0123647 | 0.394724 | 2.3193 | 0.317271 / 0.297292 | 0.00763113 | 0.766342 / 0.52142 | 0.0189905 | 0.612903 | 0.0361612 / 0.0170934 |
| 398 | B4,F1 | 0.0780939 | 0.0764387 | 1.02165 | 6.20327 | 0.450065 / 0.179048 | 0.0638435 | 9.23037 / 6.91713 | 0.00049975 | 0.935484 | 0.356977 / 0.356977 |
| 407 | B4,F4 | 0.0612758 | 0.0494944 | 1.23803 | 7.5345 | 0.37653 / 0.179048 | 0.0292913 | 8.7218 / 6.91713 | 0.00049975 | 0.967742 | 0.197744 / 0.197744 |

n_months 366, n_years 31 (all rows). Full primary table in prose: R2KR 119-152; sub-periods R2KR 156-181; windows R2KR 185-202; Jaccard R2KR 206-215.

**Indicative gate (r2_kr/r2_kr_excl_gate.csv)**: line 2 B1 F4: `steps_passed 7, verdict REVISE, g1 1.51291, g2_lo_ir 1.42445 se 0.17666, g2_boot_ci90 [1.29, 1.95], g3_dsr 0.939134, g3_sr0_monthly 0.34798, g3_dsr_nullvar 1, g3_sr0_nullvar 0.142553, g3_dsr_per_base 0.999712, g4_pbo primary 0.0480186 / all 0.0575758, winner_loses 0 / 0`; `n_trials 176, var_trial_sr_monthly 0.0163254` (all rows). Lines 3-9: B1 F1 REVISE (g3 0.410306); B2 F4 REVISE (g3 0.00103008, pbo 0.0394716/0.01087); B2 F2 REVISE; B3 F4 REJECT (6/8; g1 0.0861292; pbo 0.299456/0.387); B3 F2 REJECT (5/8); B4 F4 REVISE (g3 0.563422, pbo 0.101943/0.0991453); B4 F1 REVISE (g3 0.209004). Prose: R2KR 225-236.

**Limit-lock audit (r2_kr/r2_kr_excl_limitlock.csv)**: line 2 `B1,none,14597,920,0.0630266,13275,273,0.020565`; line 3 `B1,F4,29313,568,0.0193771,28122,390,0.0138681`; line 6 `B3,none,3310,144,0.0435045,3310,75,0.0226586`; line 8 `B4,none,20702,403,0.0194667,20439,137,0.00670287`.

**Crash controls (r2_kr/r2_kr_crash_controls.csv, cost net35, period 'full 1996-04..2026-09')**:

| Sleeve | control | sharpe (line) | max_dd (line) | avg_exposure (line) |
|---|---|---|---|---|
| LS_EW (ALL quintiles) | static | 0.2007 (44) | -0.6427 (48) | 1.0000 (52) |
| | VS (own vol, 12%, cap 1) | 0.2664 (158) | -0.5977 (162) | 0.8187 (166) |
| | DM gate (KOSPI, floor 0.5) | 0.2491 (272) | -0.6626 (276) | 0.9511 (280) |
| | VS x DM | 0.3120 (386) | -0.6136 (390) | 0.7918 (394) |
| LS_VW (ALL quintiles) | static | 0.2498 (500) | -0.7419 (504) | 1.0000 (508) |
| | VS | 0.3117 (614) | -0.4361 (618) | 0.5267 (622) |
| | DM gate | 0.3211 (728) | -0.6540 (732) | 0.9511 (736) |
| | VS x DM | 0.3685 (842) | -0.4193 (846) | 0.5105 (850) |

Exposure into the 2026 crash (r2_kr/r2_kr_crash_exposure_2026.csv): line 3 LS_EW VS `s_on_2026_06_22 0.5531, s_on_2026_06_30 0.5379, first_cut_in_2026 2026-01-02, sigma126_on_2026_06_22 0.2169`; line 7 LS_VW VS `0.2738, 0.2511, 2026-01-02, 0.4382`; line 19 E5 top500 EW VS `0.3510, 0.3320, 0.3419`; line 23 E5 VW `0.2034, 0.1897, 0.5900`; DM gate rows all `1.0000` (no cut). Full window table R2KR 250-275.

**Stop-loss (r2_kr/r2_kr_stoploss.csv, E5 top500 deciles, gross, 2000-01..2026-09)**: line 2 EW no stop `sharpe 0.2581, ann_mean 0.0709, max_dd -0.7892, worst_month -0.2996, turnover 16.9099`; line 4 EW 15% next close `0.1652, -0.7672, -0.2510, stops_long 5349, stops_short 4618`; line 6 EW 15% same close `0.2017`; line 8 EW 10% `0.1904, stops 8178/6924`; line 10 VW no stop `0.4396`; line 12 VW 15% next close `0.3006`.

**Reversal (r2_kr/r2_kr_reversal.csv, ALL, period full, mean %/month (NW t), Sharpe, turnover/yr)**: line 2 VW quintiles gross `0.079 (0.177), 0.032, 40.428`; line 7 VW quintiles net35 `-1.100 (-2.464), -0.450`; line 17 VW deciles gross `0.573 (0.940), 0.191, 42.984`; line 22 VW deciles net35 `-0.681 (-1.122)`; line 32 EW quintiles gross `0.936 (2.664), 0.452, 37.883`; line 47 EW deciles gross `1.431 (3.057), 0.527, 41.207`; line 52 EW deciles net35 `0.229 (0.491), 0.084`.

**DM gate onsets (r2_kr/r2_kr_dm_gate_onsets.csv lines 2-10)**: the 9 dates in B.6; gate on 9.8% of days (R2KR 248).

**Round-1 key numbers (kr/kr_key_numbers.csv)**: line 2 MOM_12_1 ALL EW `ls_gross_ann 0.093369, ls_gross_sharpe 0.447161, ls_gross_nw_t 2.666310, ls_net35_sharpe 0.201321, ls_net70_sharpe -0.044070, lo_net35_ann 0.059645, lo_xs_net35_ann -0.013387 (t -0.630295), excl_xs_net35_ann 0.009391 (t 2.076680), ls_turnover_yr 14.65560, lo_turnover_yr 6.91713, ls_pos_years 0.677419`; line 10 VOL_3M ALL EW `0.186574, 0.757889, 4.573060, 0.564725, 0.371363, excl_xs 0.029819 (4.667430), turnover 13.60250`; line 6 REV_1M ALL EW `0.112280, 0.451756, 2.664300, -0.081744, turnover 37.88300`. Full tables KR 22-42 (EW), 46-66 (VW), 70-89 (LARGE), 95-114 (sub-period Sharpe), 183-196 (LS correlations).

**KOSPI SPA (kr/kr_index_spa.csv)**: line 2 `n_variants 303`; line 5 `best_rule MACD(12,26,1)`; line 6 `best_rule_nw_t_excess 0.3404923656726329`; line 7 `best_rule_mean_excess_ann 0.01160225561550082`; line 8 cagr `0.10675264590971634`; line 11 sharpe `0.674867306064785`; line 12 max_dd `-0.3308224489855982`; line 16 n_days `7593`; line 17 buyhold_cagr `0.07198444926473968`; line 20 buyhold_sharpe `0.394992054209299`; line 21 buyhold_max_dd `-0.6706330840236572`; line 26 spa_p_lower `0.737`; consistent 0.880, upper 0.890 (KR 253). Round-1 KOSPI rule table KR 221-231; US SPA table US 80-89.

**CARD-P scorecard, KOSPI KRX ETF 3bp, 1996-09-02..2026-09-29 (r2_idx/r2_idx_protective_scorecard.csv; 93 columns, header at line 1)**:

| Line | rule_id | avg_exposure | turnover/yr | sharpe 1x / S | mdd 1x / S / B&H | pc1 1x / 2x (pp) | pc2 tail | dSR | pc3_block | pc3_p_ni | pc4 +/n (largest) | pc5 years | pc6 | onsets | verdict | o_step5_p_block10 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2 | SMA200 | 0.5826 | 7.6142 | 0.5381 / 0.4167 | -0.4148 / -0.4341 / -0.6445 | 1.9302 / -0.1739 | 0.7258 | 0.1214 | 206 | 0.0510 | 9/13 (0.3048) | 0.4333 | 0.600 | 16 | INSUFFICIENT DATA (sufficiency) | 0.2295 |
| 3 | ENS | 0.5767 | 11.9700 | 0.6029 / 0.4167 | -0.3415 / -0.4306 / -0.6445 | 8.9149 / 8.4461 | 0.7678 | 0.1862 | 178 | 0.0080 | 8/13 (0.4150) | 0.6000 | 0.750 | n/a | PASS | 0.0610 |
| 4 | TSM12 | 0.5835 | 1.4298 | 0.4985 / 0.4167 | -0.3879 / -0.4347 / -0.6445 | 4.6815 / 4.6449 | 0.8751 | 0.0818 | 211 | 0.0830 | 8/13 (0.4084) | 0.6333 | 0.200 | 11 | INSUFFICIENT DATA (sufficiency) | 0.2650 |
| 5 | VT | 0.8541 | 2.5744 | 0.4160 / 0.4167 | -0.5142 / -0.5795 / -0.6445 | 6.5352 / 6.4441 | 0.7048 | -0.0006 | 186 | 0.0505 | 6/13 (0.3771) | 0.7000 | 1.000 | n/a | PASS | 0.5090 |
| 6 | ENSxVT | 0.5108 | 11.2979 | 0.6480 / 0.4167 | -0.2772 / -0.3900 / -0.6445 | 11.2812 / 9.4159 | 0.5477 | 0.2314 | 187 | 0.0070 | 11/13 (0.3166) | 0.5667 | 0.875 | n/a | REVISE | 0.0480 |
| 7 | ENS >=2/4 binary | 0.6758 | 11.9367 | 0.5778 / 0.4167 | -0.4340 / -0.4878 | 5.3827 / 5.0595 | 0.7516 | 0.1611 | 196 | 0.0170 | 9/13 (0.3826) | 0.6000 | n/e | 6 | INSUFFICIENT DATA (sufficiency) | 0.1125 |
| 8 | EWMA(0.94) VT | 0.8494 | 2.1628 | 0.4032 / 0.4167 | -0.5100 / -0.5773 | 6.7280 / 6.6445 | 0.6971 | -0.0135 | 192 | 0.0785 | 6/13 (0.3643) | 0.7000 | n/e | n/a | PASS | 0.5895 |

Full scorecard incl. SPY books R2IDX 44-66; episodes R2IDX 72-86; start-date sweep R2IDX 94-121; CARD-O R2IDX 127-143; overlay vs sleeve R2IDX 162-202; 2026 windows R2IDX 149-156.

**Spec 9.3 golden values, KOSPI VT20 2016-01-04..2026-09-29 (r2_idx/r2_idx_golden_values.csv: item, ours, spec, gap, level1_tol, level2_tol)**: line 2 VT20 Sharpe gross `0.63291 vs 0.638 (tol 0.01/0.03)`; 3 B&H Sharpe `0.62845 vs 0.634`; 4 VT20 max DD `-0.36995 vs -0.368 (0.01/0.02)`; 5 B&H max DD `-0.44049 vs -0.439`; 6 VT20 average exposure `0.92554 vs 0.925 (0.02)`; 7 Static S max DD `-0.41453 vs -0.413`; 8 dMDD VT20 vs S gross (pp) `4.45807 vs 4.5 (1.00/1.50)`; 9 VT20 Sharpe net 3 bp `0.63015 vs 0.635`; 10 net 6 bp `0.62739 vs 0.632`; 11 dMDD net 3 bp `4.42809 vs 4.4`; 12 dSR VT20 - B&H gross `0.00446 vs 0.004`; 13-14 Jul-2026 crash VT20 `-0.12240 vs -0.122`, B&H `-0.38606 vs -0.386`; 15-16 Mar-2026 `-0.07905 / -0.19884`; 17-18 Aug-2024 `-0.07877 / -0.05457`; 19-20 Apr-2025 `-0.11674 / -0.12008`; 21-22 2020 crash `-0.25821 / -0.34054`; 23-24 2020 rebound `0.25835 / 0.49804`; 25-26 H1-2026 `0.51704 / 1.01075`; 27-28 30 Jul-30 Sep 2026 `0.06186 vs 0.059 / 0.22823 vs 0.222`; 29 VT20 weight earning on 2026-06-22 `0.30250 vs 0.3024 (tol 0.02)`; 30 on 2026-06-23 `0.33098 vs 0.3309`; 31 on 2026-07-30 `0.24850 vs 0.2484`. 30/30 within Level-1 (R2IDX 322, 330).

**Gate simulation (r2_idx/r2_idx_gate_step5_calibration.csv, 18 years, share_p_le_0p10 at SR = benchmark 0.4)**: lines 17-19 kospi_cbb126 rho 0/0.5/0.9 `0.1270 / 0.1275 / 0.1305`; lines 50-52 sign-flip `0.0890 / 0.0900 / 0.0965`; lines 83-85 iid `0.0860 / 0.0820 / 0.0790`. False-pass and power tables R2IDX 210-252 (e.g. step 2 at SR 0, 10/18/30 y: 8.0/6.9/6.8 % KOSPI, 5.0/4.2/4.7 sign-flip, 3.9/4.8/5.0 iid; step 8: 23.8/10.2/4.7; joint 2+3+5+8 N=1 rho 0.5: 0.5/0.1/0.0; years for 50%/80% power at SR 0.4 step 2: 15.8/40.3).

**Averaging bias (r2_idx/r2_idx_averaging_autocorr.csv)**: line 2 SPY 1998-02..2021-03 `acf1_month_end 0.0571, acf1_month_average 0.2064, acf1_shiller_price 0.2065, vol_month_end 0.1538, vol_month_average 0.1323`; line 5 Shiller 1872-2026 price `acf1 0.2740`; line 6 signal agreement SMA10 `0.9283`; line 7 TSM12 `0.9811`. Sharpe inflation table R2IDX 258-274 (SPY SMA10 +0.10, TSM12 +0.23, TSM12 L/S +0.26); long-history LAG1 table R2IDX 280-293; round-1 Shiller table US 19-43, French check US 167-172.

**Pair share (r3/r3_pair_share_summary.csv)**: line 2 CR-07 share on 2026-09-29 `0.537062`; 3 first session > 0.45 in 2026 `2026-05-06`; 4 share then `0.470159`; 5 peak date `2026-06-25`; 6 peak share `0.596875`; 7 sessions > 0.45 `99`; 8 sessions in file `181`; 9-17 alternatives (common/all lines first > 0.45 `2026-05-07`, peak `0.571082`, sessions 98). Snapshots (r3/r3_pair_share.csv): line 2 2023-12-28 `953 lines, 839 common, CR07 0.292943`; 3 2024-12-30 `0.244770`; 4 2025-12-30 `0.361281`; 5 2026-05-07 `0.474864`; 6 2026-06-22 `0.580806`; 7 2026-06-25 `0.596875`; 8 2026-06-30 `0.578887`; 9 2026-09-29 `0.537062` (942 lines, 831 common).

**Low-vol protective (prose, R2KR 306-342)**: low-vol Q1 EW full beta `0.63`, alpha rf0 `+2.2% (t 0.8)`, Sharpe `0.37` vs market `0.35`, up/down capture `0.71/0.66`; VW beta `0.74`, alpha `+0.7% (0.3)`, capture `0.77/0.75`; crash window 2026-06-22..07-30 EW book `-2.1%` vs VW universe `-38.5%` (+36.4), VW book `+6.3%` (+44.8); melt-up EW `-5.2%` vs `+104.9%`.

---

## Ambiguities (conservative reading in brackets)

1. **Decision time vs "eligibility on t-1".** Labs form the universe from data through the close of t and trade at that close (KC 4; K02 11-12 `traded on day t itself`; IC 6). The brief's "eligibility on t-1" is not what the scripts do. [Implement the lab definition as `as_of = close(t)`; in QUANTGEN the PIT contract decides whether close-of-t fields are available at the decision time; if not, decisions shift to t+1 and the reference constants no longer apply. Specification book only.]
2. **Cost timing and initial entry.** KR stock labs: cost once per period at the formation (K04 5-8; RC 13), initial purchase counted (K03 22-23). Index lab: cost on the earning day, initial entry free (IC 7-8, 292); US lab charges the first entry (US 4). [Expose `charge_initial_entry` and `cost_timing in {'period_start', 'earning_day'}` as explicit parameters; acceptance tests fix them per lab.]
3. **Gross vs costed benchmark in excess series.** Round 1 and the momentum grid use a gross benchmark (`cb = 0`, R03 8-9, 300-303); the exclusion test uses `cb = c` (RC 239-241). Same screen: +3.62% (gross benchmark) vs +4.28% (costed) (R2KR 219). [Always state `cb`; default to the costed benchmark for filtered-vs-unfiltered and gross for signal-vs-universe.]
4. **F4 tie handling.** The composite cut is ordinal in code order (`argsort(kind='stable')`, R04 64-66); on a synthetic panel the flagged set depends on column order when composites tie. [Tests avoid exact ties or assert only the count `floor(frac*n)` and set membership up to ties.]
5. **F6 definition.** Literal split rule vs KRX net issuance disagree on 20.3% of flags (R2KR 217; f6_diagnostic). [Implement both `DIL_LIT` and `DIL_NI`; neither is a BUILD on its own (F6 B1 +2.34%, IR 0.65, R2KR 126, 243); record only.]
6. **"S_beta" is not named in the assigned files.** R06 computes CAPM beta/alpha vs the VW universe (rf = 0). [Define `S_beta,t = beta_hat * r_mkt,t` with full-sample NW OLS; report alpha and t, never as an alpha claim; verdict on drawdown-first, Sharpe non-inferiority (R2KR 344).]
7. **Product composition vs v2 min().** The index lab composes `ENS x VT` as an elementwise product and floors overlays at 0.5 before multiplying (IC 266-275). QUANTGEN v2's risk layer composes by `min()` and never above 1.0. The "floored trend x VT20 passes every check" finding (R2IDX 204) is defined with the product. [Keep the product form in the research harness only; a `min()` version is untested -> no exposure change.]
8. **Exposure-matched SPA** is "supplementary (not the pre-specified test)" (KR 255; K05 332-350). [Report only.]
9. **SPA studentisation.** `arch 8.0.0` ignores `studentize=True` (US 178); the KR SPA call passes it (K05 271). [If re-implemented, provide both the naive and the Hansen-studentised p and label which one the constants in D correspond to (the arch values).]
10. **Seeds and index generators.** KR labs seed 20261002 with numpy `default_rng`; index lab seed 11 with arch `CircularBlockBootstrap`; gate sim per-path seeds `[11, k, 1]` / `[11, k, 2]` (I02 24-25). [Bootstrap p-values and CIs are reproducible only with the same generator; acceptance tolerance about 0.01 for p, exact for deterministic quantities.]
11. **DSR trial-count convention.** RC 366 uses `N = max(n_trials, 2)`; validate and the gate sim use SR0 = 0 for N = 1 (V 157-158; I02 61-64). [Use validate's convention; the exclusion gate (N = 176) is unaffected.]
12. **CSCV block count.** Lab S = 16 on 366 monthly diffs (R04 264); validate S = 8 unless T >= 2000 (V 442). [Pass S explicitly in tests.]
13. **Year filters.** >= 60 days (K04 115), >= 126 sessions (IC 62), none in `validate.year_stats` (V 364-371, summed not compounded). [Per card: PC-5 uses 126 sessions compounded.]
14. **Annualisation of the round-1 index lab** uses `af = n_days / calendar years` (K05 197-200), not 252. [Constants in kr_index_spa.csv / kr_index_timing.csv use this; r2_idx uses 252.]
15. **DM gate onsets are raw** (daily toggles; clustered 1997-10-08/11 and 1999-04-19/21/29, R05 255-262), not de-clustered as in IC 507-522. [Report both counts.]
16. **Break-even cost** is a derived linear approximation (B.5), not a lab function. [Label as approximate.]
17. **F5 regime-limit lock variant** flagged 51% of the 1990s universe (R2KR 348); primary F5 uses E7's written thresholds. [F5 is DO-NOT-BUILD as a monthly exclusion (R2KR 243); keep the definition for the audit only.]
18. **No Korean risk-free series** offline (R06 10-11; R2KR 344, 379): all Sharpe and alpha with rf = 0. [Any QUANTGEN re-run with a short rate will not match the constants in D for absolute long-only books.]
