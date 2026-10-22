"""Validation suite for the QUANTGEN US data lab.

1. No look-ahead: for every daily rule variant, perturbing all prices AFTER day t leaves the
   signal at t unchanged; the position on day t equals the signal at t-1; the first return
   used is t+1. Same check for the monthly Shiller rules and the valuation OOS regressions.
2. French data: decoded dates (first row 1926-07), contiguity, units; spot checks of known
   monthly market returns (Oct-1987, Sep/Oct-2008, Oct-1929); vintage agreement.
3. Raw data checks: SPY splits/anomalies (no split in 1998-2021; ratio to S&P 500 index),
   Shiller zeros-as-missing, VIX range.
4. Reproducibility: SPA p-values and the bootstrap draw identical across two runs with seed
   20261002; replica SPA = arch SPA (same p-values).
Writes us_validation.csv (test, series, period, cost_level, metric, value) with PASS/FAIL.
"""
import numpy as np
import pandas as pd

from us_common import (SEED, Results, load_ff_arch, load_ff_lm, load_shiller_raw, load_sp500_arch, load_spy_lean,
                       load_vix, shiller_monthly)
import us_A_shiller_timing as A
import us_B_daily_rules as B
import us_A4_valuation as A4

res = Results()
fails = []


def check(name, ok, detail=""):
    res.add("validation", name, "", "na", "result", "PASS" if ok else "FAIL")
    if detail != "":
        res.add("validation", name, "", "na", "detail", detail)
    if not ok:
        fails.append(name)
    print(("PASS " if ok else "FAIL ") + name + (f"  [{detail}]" if detail != "" else ""))


# ---------------------------------------------------------------- 1a. daily rules: causality
rng = np.random.default_rng(SEED)
spec = B.family_spec()
d = B.load_dataset("SPY")
S0 = B.build_signals(d, spec)
bad_cols = set()
for cut in [300, 1500, 3000, 4500, 5800]:
    d2 = d.copy()
    noise = np.exp(rng.normal(0, 0.05, size=len(d2) - cut - 1))
    for k in ["o", "h", "l", "c"]:
        d2.iloc[cut + 1:, d2.columns.get_loc(k)] = d2[k].values[cut + 1:] * noise
    S1 = B.build_signals(d2, spec)
    diff = np.where(np.abs(S0[: cut + 1] - S1[: cut + 1]).max(0) > 0)[0]
    bad_cols |= set(diff.tolist())
check("daily_signals_use_only_data_up_to_t (322 variants x 5 cut dates, future prices perturbed)", len(bad_cols) == 0,
      f"variants changed: {len(bad_cols)}")
W, dW = B.positions(S0)
check("daily_position_t_equals_signal_t_minus_1", np.array_equal(W[1:], S0[B.WARM:-1]), "")
# the return earned on the first evaluation day is the t+1 return of the day-t signal
rm = d["rm"].values
R = B.net_returns(W, dW, rm[B.WARM:], d["rf"].values[B.WARM:], 0.0)
j = 13  # SMA200
manual = S0[B.WARM - 1, j] * rm[B.WARM] + (1 - S0[B.WARM - 1, j]) * d["rf"].values[B.WARM]
check("daily_first_return_is_t_plus_1", np.isclose(R[0, j], manual), f"{R[0, j]:.6g} vs {manual:.6g}")
check("daily_eval_window_has_no_undefined_signals", not np.isnan(W).any(), "")
# burn-in: start the price history 100 sessions later; compare positions where BOTH runs have full
# 252-session lookback. Pure-window rules must be identical; state machines (RSI/Bollinger/Donchian/
# 52w-high entries-exits) and EMA/RSI rules are path dependent by design -> report flips and when they end.
d3 = d.iloc[100:].copy()
S3 = B.build_signals(d3, spec)
a0 = S0[B.WARM - 1 + 100:]
a3 = S3[B.WARM - 1:]
flips = (a0 != a3)
pure = [k for k, (r_, _) in enumerate(spec) if r_ in ("SMA_PRICE", "SMA_CROSS", "TSMOM")]
path = [k for k in range(len(spec)) if k not in pure]
check("daily_pure_window_rules_independent_of_start_date (SMA, SMA cross, TSMOM)", int(flips[:, pure].sum()) == 0,
      f"flips {int(flips[:, pure].sum())} over {len(pure)} variants")
last_flip = [int(np.where(flips[:, k])[0].max()) for k in path if flips[:, k].any()]
check("daily_path_dependent_rules_converge_within_1y_of_eval_start", (max(last_flip) if last_flip else 0) < 252,
      f"{len(last_flip)} of {len(path)} path-dependent variants differ at some date; total flips {int(flips[:, path].sum())} of {flips[:, path].size}; last flip at eval day {max(last_flip) if last_flip else 0}")

# ---------------------------------------------------------------- 1b. monthly rules: causality
df, meta = shiller_monthly()
s_sma, s_mom = A.signals(df)
df2 = df.copy()
cut = df.index.get_loc(pd.Period("1990-06", "M"))
pert = np.exp(rng.normal(0, 0.1, size=len(df2) - cut - 1))
df2.iloc[cut + 1:, df2.columns.get_loc("P")] = df2["P"].values[cut + 1:] * pert
df2["R"] = (df2["P"] + df2["D"] / 12.0) / df2["P"].shift(1) - 1.0
s_sma2, s_mom2 = A.signals(df2)
ok = s_sma.iloc[: cut + 1].equals(s_sma2.iloc[: cut + 1]) and s_mom.iloc[: cut + 1].equals(s_mom2.iloc[: cut + 1])
check("monthly_signals_use_only_data_up_to_t (future Shiller prices perturbed)", ok, "")
w = s_sma.shift(1)
check("monthly_position_t_equals_signal_t_minus_1", w.iloc[1:].equals(s_sma.iloc[:-1].set_axis(w.index[1:])), "")

# ---------------------------------------------------------------- 1c. valuation OOS uses realised outcomes only
dv, _ = A4.build()
y, x = dv["y10"], dv["log_cape"]
f = A4.oos(y.loc["1881-01":"2013-09"], x.loc["1881-01":"2013-09"], 120, start="1950-01", end="1950-12")
# manual recompute for the first origin with the training sample restricted to s <= t-120
t0 = f.index[0]
tr = pd.DataFrame({"y": y, "x": x}).dropna().loc[: t0 - 120]
b, _, _ = A4.ols(tr["y"].values, tr["x"].values)
check("valuation_oos_training_ends_at_t_minus_horizon", np.isclose(f.iloc[0]["f_model"], b[0] + b[1] * x[t0]) and tr.index[-1] == t0 - 120,
      f"origin {t0}, last training start {tr.index[-1]}")

# ---------------------------------------------------------------- 2. French data
ff = load_ff_arch()
check("french_arch_first_month_is_1926-07", str(ff.index[0]) == "1926-07", str(ff.index[0]))
check("french_arch_last_month_is_2018-11", str(ff.index[-1]) == "2018-11", str(ff.index[-1]))
check("french_arch_months_contiguous", len(ff) == (ff.index[-1] - ff.index[0]).n + 1, f"{len(ff)} months")
spot = {"1987-10": -23.24, "2008-09": -9.24, "2008-10": -17.23, "1929-10": -20.12}
for m, v in spot.items():
    got = ff.at[pd.Period(m, "M"), "MktRF"] * 100
    check(f"french_MktRF_{m}_equals_{v}%", abs(got - v) < 0.005, f"{got:.2f}%")
lm = load_ff_lm()
check("linearmodels_french_units_are_decimals", abs(lm.at[pd.Period("1987-10", "M"), "MktRF"] + 0.2324) < 1e-9,
      f"{lm.at[pd.Period('1987-10', 'M'), 'MktRF']}")
check("linearmodels_french_range_1949-01_2017-03", str(lm.index[0]) == "1949-01" and str(lm.index[-1]) == "2017-03", "")
jj = ff.join(lm[["MktRF"]], rsuffix="_lm", how="inner")
check("french_vintages_agree_on_MktRF (max abs diff < 0.05pp)", ((jj["MktRF"] - jj["MktRF_lm"]).abs().max() * 100) < 0.05,
      f"{(jj['MktRF'] - jj['MktRF_lm']).abs().max() * 100:.3f}pp")
# Mom crash Apr-2009 (known about -34.6% in the 2017 vintage)
check("french_Mom_2009-04_crash", abs(lm.at[pd.Period("2009-04", "M"), "Mom"] + 0.3458) < 1e-6, f"{lm.at[pd.Period('2009-04', 'M'), 'Mom']}")

# ---------------------------------------------------------------- 3. raw data checks
spy = load_spy_lean()
r = spy["c"].pct_change()
check("spy_no_split_like_jumps (|daily ret| < 15%)", r.abs().max() < 0.15, f"max |ret| {r.abs().max():.4f} on {r.abs().idxmax().date()}")
check("spy_ohlc_consistent", bool(((spy["h"] >= spy[["o", "c"]].max(axis=1) - 1e-9) & (spy["l"] <= spy[["o", "c"]].min(axis=1) + 1e-9)).all()), "")
sp = load_sp500_arch()
jx = pd.DataFrame({"spy": spy["c"], "spx": sp["c"]}).dropna()
ratio = jx["spy"] / (jx["spx"] / 10)
check("spy_to_spx_ratio_within_3pct (no split/scale break)", ratio.between(0.97, 1.03).all(), f"range {ratio.min():.4f}..{ratio.max():.4f}")
dlr = np.log(ratio).diff().abs()
res.add("validation", "spy_vs_spx_largest_daily_ratio_moves", "", "na", "detail",
        "; ".join(f"{k.date()}:{v:.4f}" for k, v in dlr.nlargest(4).items()))
check("sp500_arch_adjclose_equals_close (price index, dividends NOT included)", bool(np.allclose(sp["c"], sp["close_raw"])), "")
check("spy_row_count_and_volume_plausible", len(spy) == 5849 and spy["v"].between(1e6, 1e9).all(),
      f"{len(spy)} rows; volume {spy['v'].min():.3g}..{spy['v'].max():.3g}; file lacks a trailing newline (harmless)")
gaps = spy.index.to_series().diff().dt.days
res.add("validation", "spy_calendar_gaps_over_4_days", "", "na", "detail", "; ".join(f"{k.date()}:{int(v)}d" for k, v in gaps[gaps > 4].items()))
raw = load_shiller_raw()
check("shiller_zeros_treated_as_missing", raw["D"].loc["2023-07":].isna().all() and raw["CAPE"].loc["2023-10":].isna().all(), "")
vix = load_vix()
check("vix_range_plausible", vix.min() > 8 and vix.max() < 90, f"{vix.min():.2f}..{vix.max():.2f}")

# ---------------------------------------------------------------- 4. reproducibility
dd = B.load_dataset("SP500")
S = B.build_signals(dd, spec[:40])
W2, dW2 = B.positions(S)
Rx = B.net_returns(W2, dW2, dd["rm"].values[B.WARM:], dd["rf"].values[B.WARM:], 0.0)
D = Rx - dd["rm"].values[B.WARM:][:, None]
p1 = B.spa_fast([D], 15, 300, SEED)[0]
p2 = B.spa_fast([D], 15, 300, SEED)[0]
check("spa_reproducible_with_seed_20261002", p1 == p2, f"p_stud_consistent {p1['p_stud_consistent']}")
pa = B.run_arch_spa(D, block=15, reps=300, seed=SEED)
check("replica_spa_matches_arch_spa (non-studentized p-values)",
      np.isclose(pa["p_consistent"], p1["p_raw_consistent"]) and np.isclose(pa["p_lower"], p1["p_raw_lower"]) and np.isclose(pa["p_upper"], p1["p_raw_upper"]),
      f"arch {pa} vs replica {p1['p_raw_consistent']},{p1['p_raw_lower']},{p1['p_raw_upper']}")

res.add("validation", "summary", "", "na", "n_fail", len(fails))
res.save("us_validation.csv")
print("FAILS:", fails)
