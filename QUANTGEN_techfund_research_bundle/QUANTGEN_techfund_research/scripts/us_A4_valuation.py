"""A4 valuation-based market timing and A5 Fed model on Shiller data.

Dependent variables (start month t, Shiller monthly average prices):
  y10_t = (RTRI_{t+120}/RTRI_t)^(1/10) - 1,  RTRI = total-return index / CPI   (starts 1881-01..2013-09)
  y1_t  = RTRI_{t+12}/RTRI_t - 1                                               (starts 1881-01..2022-09)
  y5_t  = 5-year annualised real total return (context)
  rel10_t = 10y annualised NOMINAL total return - GS10_t/100 (stock minus a 10y bond held to maturity)
Predictors: log CAPE (PE10), log dividend yield log(D/P), trailing earnings yield E/P, and the Fed model
spread E/P - GS10/100.
In-sample OLS with Newey-West t-stats (Bartlett, lags = horizon in months; overlapping observations).
Out-of-sample: expanding window, forecasts from 1950-01; at origin t only pairs whose outcome is
fully realised by t are used (s + h <= t). Benchmark = historical mean of the same realised sample
(Goyal-Welch 2008). R2_OS = 1 - SSE_model / SSE_mean.
"""
import numpy as np
import pandas as pd

from us_common import Results, nw_tstat, save_json, shiller_monthly

TEST = "A4_valuation"


def build():
    df, meta = shiller_monthly()
    rtri = df["TRI"] / df["CPI"]
    ntri = df["TRI"]
    out = pd.DataFrame(index=df.index)
    for h, lab in [(12, "y1"), (60, "y5"), (120, "y10")]:
        g = rtri.shift(-h) / rtri
        out[lab] = g - 1.0 if h == 12 else g ** (12.0 / h) - 1.0
    out["rel10"] = (ntri.shift(-120) / ntri) ** 0.1 - 1.0 - df["GS10_raw"] / 100.0
    out["log_cape"] = np.log(df["CAPE"])
    out["log_dy"] = np.log(df["D_raw"] / df["P"])
    out["ey"] = df["E"] / df["P"]
    out["fed_spread"] = out["ey"] - df["GS10_raw"] / 100.0
    out["cape"] = df["CAPE"]
    out["gs10"] = df["GS10_raw"]
    # flag: outcomes that touch imputed dividends (after 2023-06)
    out["y10_uses_imputed_div"] = [int(p + 120 > pd.Period(meta["last_dividend_month"], "M")) for p in df.index]
    return out, meta


def ols(y, x):
    X = np.column_stack([np.ones(len(x)), x])
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    e = y - X @ b
    r2 = 1.0 - (e @ e) / ((y - y.mean()) @ (y - y.mean()))
    return b, e, r2


def nw_se_slope(y, x, lags):
    X = np.column_stack([np.ones(len(x)), x])
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    e = y - X @ b
    n = len(y)
    XtX_inv = np.linalg.inv(X.T @ X)
    u = X * e[:, None]
    S = u.T @ u
    for L in range(1, lags + 1):
        w = 1.0 - L / (lags + 1.0)
        G = u[L:].T @ u[:-L]
        S += w * (G + G.T)
    V = XtX_inv @ S @ XtX_inv
    return b, np.sqrt(np.diag(V))


def oos(y, x, h, start="1950-01", end=None):
    """Expanding-window OOS forecasts. y, x indexed by start month (PeriodIndex)."""
    d = pd.DataFrame({"y": y, "x": x}).dropna()
    idx = d.index
    origins = idx[(idx >= pd.Period(start, "M"))]
    if end is not None:
        origins = origins[origins <= pd.Period(end, "M")]
    rows = []
    for t in origins:
        train = d.loc[: t - h]  # outcomes realised by t
        if len(train) < 120:
            continue
        b, _, _ = ols(train["y"].values, train["x"].values)
        rows.append((t, d.at[t, "y"], b[0] + b[1] * d.at[t, "x"], train["y"].mean(), b[1]))
    f = pd.DataFrame(rows, columns=["t", "y", "f_model", "f_mean", "slope"]).set_index("t")
    return f


def r2os(f):
    sse_m = ((f["y"] - f["f_model"]) ** 2).sum()
    sse_b = ((f["y"] - f["f_mean"]) ** 2).sum()
    return 1.0 - sse_m / sse_b


def main():
    res = Results()
    d, meta = build()
    horizons = {"y10": (120, "1881-01", "2013-09"), "y5": (60, "1881-01", "2018-09"), "y1": (12, "1881-01", "2022-09")}
    preds = ["log_cape", "log_dy", "ey", "fed_spread"]

    # ---------------- In-sample regressions ----------------
    insample_fits = {}
    for ylab, (h, a, b) in horizons.items():
        for xlab in preds:
            sub = d.loc[a:b, [ylab, xlab]].dropna()
            y, x = sub[ylab].values, sub[xlab].values
            bb, se = nw_se_slope(y, x, h)
            _, e, r2 = ols(y, x)
            insample_fits[(ylab, xlab)] = (bb, sub.index)
            ser = f"{ylab}~{xlab}"
            per = f"{sub.index[0]}:{sub.index[-1]}"
            res.add_dict(TEST + "_insample", ser, per, "na", {
                "n_obs": len(y), "independent_obs_approx": len(y) / h, "intercept": bb[0], "slope": bb[1],
                "slope_nw_t": bb[1] / se[1], "r2": r2, "corr": float(np.corrcoef(x, y)[0, 1]),
                "mean_y": float(y.mean()), "sd_y": float(y.std(ddof=1))})
        # bivariate log_cape + log_dy for completeness
        sub = d.loc[a:b, [ylab, "log_cape", "log_dy"]].dropna()
        X = np.column_stack([np.ones(len(sub)), sub[["log_cape", "log_dy"]].values])
        bb, *_ = np.linalg.lstsq(X, sub[ylab].values, rcond=None)
        e = sub[ylab].values - X @ bb
        r2 = 1 - e @ e / ((sub[ylab] - sub[ylab].mean()) ** 2).sum()
        res.add_dict(TEST + "_insample", f"{ylab}~log_cape+log_dy", f"{sub.index[0]}:{sub.index[-1]}", "na",
                     {"n_obs": len(sub), "b_log_cape": bb[1], "b_log_dy": bb[2], "r2": r2})

    # ---------------- Sub-period in-sample (stability of the CAPE relation) ----------------
    for ylab, (h, a, b) in horizons.items():
        for xlab in ["log_cape", "ey"]:
            for pa, pb in [("1881-01", "1949-12"), ("1950-01", b), ("1881-01", "1989-12"), ("1990-01", b)]:
                sub = d.loc[pa:pb, [ylab, xlab]].dropna()
                if len(sub) < 2 * h:
                    continue
                y, x = sub[ylab].values, sub[xlab].values
                bb, se = nw_se_slope(y, x, h)
                _, _, r2 = ols(y, x)
                res.add_dict(TEST + "_insample_sub", f"{ylab}~{xlab}", f"{sub.index[0]}:{sub.index[-1]}", "na",
                             {"n_obs": len(y), "slope": bb[1], "slope_nw_t": bb[1] / se[1], "r2": r2})

    # ---------------- Out-of-sample (Goyal-Welch) ----------------
    oos_store = {}
    for ylab, (h, a, b) in horizons.items():
        for xlab in preds:
            f = oos(d.loc[a:b, ylab], d.loc[a:b, xlab], h, start="1950-01", end=b)
            oos_store[(ylab, xlab)] = f
            for wa, wb in [("1950-01", b), ("1950-01", "1989-12"), ("1990-01", b)]:
                ff = f.loc[wa:wb]
                if len(ff) < 12:
                    continue
                err_m = ff["y"] - ff["f_model"]
                err_b = ff["y"] - ff["f_mean"]
                res.add_dict(TEST + "_oos", f"{ylab}~{xlab}", f"{ff.index[0]}:{ff.index[-1]}", "na", {
                    "r2_oos": r2os(ff), "n_forecasts": len(ff),
                    "rmse_model": float(np.sqrt((err_m ** 2).mean())), "rmse_hist_mean": float(np.sqrt((err_b ** 2).mean())),
                    "mean_error_model": float(err_m.mean()), "mean_error_hist_mean": float(err_b.mean()),
                    "share_months_model_closer": float((err_m.abs() < err_b.abs()).mean()),
                    "slope_first": float(ff["slope"].iloc[0]), "slope_last": float(ff["slope"].iloc[-1])})

    # ---------------- Residuals 1990-2013 (y10 ~ log CAPE) ----------------
    bb, _ = insample_fits[("y10", "log_cape")]
    f10 = oos_store[("y10", "log_cape")]
    sub = d.loc["1990-01":"2013-09", ["y10", "log_cape", "cape", "y10_uses_imputed_div"]].dropna()
    fitted = bb[0] + bb[1] * sub["log_cape"]
    resid = sub["y10"] - fitted
    for p in sub.index:
        if p.month == 1 or p == sub.index[-1]:
            res.add_dict(TEST + "_resid_1990_2013", "y10~log_cape", str(p), "na", {
                "cape": sub.at[p, "cape"], "actual_y10": sub.at[p, "y10"], "fitted_insample": fitted[p],
                "resid_insample": resid[p], "oos_forecast": f10.at[p, "f_model"], "oos_error": sub.at[p, "y10"] - f10.at[p, "f_model"],
                "hist_mean_forecast": f10.at[p, "f_mean"]})
    for wa, wb in [("1990-01", "1999-12"), ("2000-01", "2009-12"), ("2009-01", "2013-09"), ("1990-01", "2013-09")]:
        r = resid.loc[wa:wb]
        e = (sub["y10"] - f10["f_model"].reindex(sub.index)).loc[wa:wb]
        res.add_dict(TEST + "_resid_1990_2013", "y10~log_cape", f"{wa}:{wb}", "na",
                     {"mean_resid_insample": float(r.mean()), "share_positive_resid": float((r > 0).mean()),
                      "mean_oos_error": float(e.mean()), "mean_cape": float(sub.loc[wa:wb, "cape"].mean())})
    # full-sample residual autocorrelation (overlap) and share of 1990-2013 starts with positive residual
    res.add(TEST + "_resid_1990_2013", "y10~log_cape", "1881-01:2013-09", "na", "insample_fit_intercept", bb[0])
    res.add(TEST + "_resid_1990_2013", "y10~log_cape", "1881-01:2013-09", "na", "insample_fit_slope", bb[1])

    # ---------------- A5 Fed model: splits ----------------
    for ylab, (h, a, b) in [("y1", horizons["y1"]), ("y10", horizons["y10"]), ("rel10", (120, "1881-01", "2013-09"))]:
        for xlab in ["fed_spread", "ey", "log_cape"]:
            for pa, pb, lab in [(a, b, "full"), (a, "1964-12", "pre-1965"), ("1965-01", b, "post-1965"),
                                ("1965-01", "1999-12" if ylab == "y1" else "1989-12", "1965-1999(y1)/1965-1989(10y)")]:
                sub = d.loc[pa:pb, [ylab, xlab]].dropna()
                y, x = sub[ylab].values, sub[xlab].values
                bb2, se = nw_se_slope(y, x, h)
                _, _, r2 = ols(y, x)
                res.add_dict(TEST + "_fedmodel", f"{ylab}~{xlab}", f"{lab} {sub.index[0]}:{sub.index[-1]}", "na",
                             {"n_obs": len(y), "slope": bb2[1], "slope_nw_t": bb2[1] / se[1], "r2": r2})
    for pa, pb in [("1881-01", "1964-12"), ("1965-01", "1999-12"), ("2000-01", "2023-06"), ("1965-01", "2023-06"), ("1881-01", "2023-06")]:
        sub = d.loc[pa:pb, ["ey", "gs10"]].dropna()
        res.add(TEST + "_fedmodel", "corr(E/P, GS10)", f"{pa}:{pb}", "na", "corr", float(sub["ey"].corr(sub["gs10"])))
        res.add(TEST + "_fedmodel", "mean_fed_spread", f"{pa}:{pb}", "na", "mean", float((sub["ey"] - sub["gs10"] / 100).mean()))

    # ---------------- Current reading (each predictor's last valid month) ----------------
    last = d["cape"].last_valid_index()
    for xlab in ["log_cape", "log_dy", "ey", "fed_spread"]:
        bb3, _ = insample_fits[("y10", xlab)]
        lx = d[xlab].last_valid_index()
        xv = d.at[lx, xlab]
        res.add(TEST + "_latest", f"y10~{xlab}", str(lx), "na", "x_value", float(xv))
        res.add(TEST + "_latest", f"y10~{xlab}", str(lx), "na", "implied_10y_real_return_insample", float(bb3[0] + bb3[1] * xv))
    res.add(TEST + "_latest", "price_change_since_last_cape", f"{last}:2026-09", "na", "value",
            float(shiller_monthly()[0]["P"].iloc[-1] / shiller_monthly()[0].at[last, "P"] - 1))

    # ---------------- Valuation timing as a trading rule (point-in-time, expanding percentiles) ----------------
    sm, _ = shiller_monthly()
    cape = sm["CAPE"]
    pct = pd.Series(np.nan, index=sm.index)
    cv = cape.values
    for i in range(len(cv)):
        if np.isnan(cv[i]):
            continue
        hist = cv[: i + 1]
        hist = hist[~np.isnan(hist)]
        if len(hist) >= 120:
            pct.iloc[i] = (hist <= cv[i]).mean()
    pct_ff = pct.ffill()  # after 2023-09 the last state is held (flagged): price +70% since then, so CAPE only rose
    rules = {
        "VAL_OUT90 (cash if CAPE > expanding 90th pct)": (pct_ff <= 0.90).astype(float),
        "VAL_HALF80 (0.5x if CAPE > expanding 80th pct; QUANTGEN [0.5,1] overlay)": np.where(pct_ff > 0.80, 0.5, 1.0),
        "VAL_HALF90 (0.5x if CAPE > expanding 90th pct)": np.where(pct_ff > 0.90, 0.5, 1.0),
    }
    from us_common import COSTS, perf_stats
    for name, sig in rules.items():
        sig = pd.Series(sig, index=sm.index).where(pct_ff.notna())
        w = sig.shift(1)
        for a, b, plab in [("1891-02", "2023-09", "1891-02:2023-09 (CAPE observed)"), ("1891-02", "2026-09", "1891-02:2026-09 (last CAPE state held after 2023-09)"),
                           ("1950-01", "2023-09", "1950-01:2023-09"), ("1990-01", "2023-09", "1990-01:2023-09")]:
            ww = w.loc[a:b]
            R, cash = sm["R"].loc[a:b], sm["cash"].loc[a:b]
            stb = perf_stats(R, cash, 12)
            for clab in ["gross", "futures_5bp", "kis_50bp"]:
                dw = ww.diff().abs(); dw.iloc[0] = abs(ww.iloc[0])
                r = ww * R + (1 - ww) * cash - COSTS[clab] * dw
                st = perf_stats(r, cash, 12, w=ww, dw=dw)
                st["cagr_minus_bh"] = st["cagr"] - stb["cagr"]
                st["sharpe_minus_bh"] = st["sharpe"] - stb["sharpe"]
                st["bh_cagr"], st["bh_sharpe"], st["bh_max_dd"] = stb["cagr"], stb["sharpe"], stb["max_dd"]
                res.add_dict(TEST + "_timing_rule", name, plab, clab, st)
        # months out of the market by decade (gross)
        for dec in range(1890, 2030, 10):
            ww = w.loc[f"{max(dec,1891)}-01":f"{dec+9}-12"].dropna()
            if len(ww):
                res.add(TEST + "_timing_rule", name, f"{dec}s", "gross", "avg_exposure", float(ww.mean()))
    res.add(TEST + "_latest", "cape", str(last), "na", "value", float(d.at[last, "cape"]))
    res.add(TEST + "_latest", "cape_percentile_1881_2023", str(last), "na", "value",
            float((d["cape"].dropna() <= d.at[last, "cape"]).mean()))

    res.save("us_A4_valuation.csv")

    # ---------------- Chart 2: CAPE vs subsequent 10y real return ----------------
    sub = d.loc["1881-01":"2013-09", ["cape", "y10"]].dropna()
    bb, _ = insample_fits[("y10", "log_cape")]
    grid = np.linspace(sub["cape"].min(), sub["cape"].max(), 60)
    chart = {
        "title": "Shiller CAPE vs subsequent 10-year annualised real total return, start dates 1881-2013",
        "x_label": "CAPE (PE10) at start month", "y_label": "Subsequent 10-year real total return, % p.a.",
        "notes": ["Monthly start dates; label = start year (January points carry labels).",
                  f"In-sample fit: y = {bb[0]:.4f} + {bb[1]:.4f} * ln(CAPE).",
                  "Start dates 2013-07..2013-09 use 1-3 months of dividends imputed at the last known yield."],
        "points": [{"date": str(p), "year": p.year, "cape": round(float(sub.at[p, "cape"]), 2),
                    "ret10_real": round(float(sub.at[p, "y10"]) * 100, 3), "label": str(p.year) if p.month == 1 else None}
                   for p in sub.index],
        "fit_line": [{"cape": round(float(c), 2), "ret10_real": round(float(bb[0] + bb[1] * np.log(c)) * 100, 3)} for c in grid],
        "highlight_1990_2013": "points with year >= 1990",
    }
    save_json(chart, "us_chart2_cape_vs_10y_real_return.json")
    print("done", len(res.rows))


if __name__ == "__main__":
    main()
