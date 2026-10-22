"""Out-of-sample fitness check of drift estimators for the Quant Lab Monte Carlo.

Run:  python docs/drift_study.py
Outputs: docs/drift_study/results.csv, results.md, fig_*.png
Prices are cached as CSV under CACHE so re-runs do not hit the network.
"""
from __future__ import annotations

import hashlib
import math
from pathlib import Path

import numpy as np
import pandas as pd

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "drift_study"
CACHE = Path.home() / ".tradegen" / "drift_prices"           # was a QUANTGEN session scratchpad
OUT.mkdir(parents=True, exist_ok=True)
CACHE.mkdir(parents=True, exist_ok=True)

TD = 252
HORIZONS = (21, 63, 126, 252)
STEP = 21                      # origin spacing in sessions
MIN_SESSIONS = 2000
TAU = 0.05                     # prior std of the drift (shrink)
ERP_EQ, ERP_BOND, ERP_FX = 0.04, 0.01, 0.0
CLIP_MOM = 0.3
Z90 = 1.645

CLASSES = {
    "equity": ["SPY", "QQQ", "IWM", "AAPL", "MSFT", "NVDA", "TSLA", "XOM", "JPM", "KO"],
    "bond_gold": ["TLT", "GLD"],
    "fx": ["EURUSD=X", "USDJPY=X", "USDKRW=X"],
    "korea": ["EWY", "005930.KS"],
}
TICKER_CLASS = {t: c for c, ts in CLASSES.items() for t in ts}
ERP = {t: {"equity": ERP_EQ, "bond_gold": ERP_BOND, "fx": ERP_FX, "korea": ERP_EQ}[c]
       for t, c in TICKER_CLASS.items()}
# CAPM needs a benchmark on the same calendar: US-listed equities/ETFs incl. EWY.
CAPM_OK = set(CLASSES["equity"]) | {"EWY"}
METHODS = ["sample_504", "sample_126", "sample_252", "sample_1260", "zero", "rf", "rf_erp",
           "shrink", "ewma_252", "capm", "momentum_12_1"]
SIGNED = [m for m in METHODS if m != "zero"]


# ----------------------------------------------------------------------------- data
def load_prices(ticker: str) -> pd.Series | None:
    f = CACHE / (ticker.replace("=", "_") + ".csv")
    if f.exists():
        s = pd.read_csv(f, index_col=0, parse_dates=True).iloc[:, 0]
    else:
        import yfinance as yf
        df = yf.download(ticker, start="2005-01-01", auto_adjust=True, progress=False)
        if df is None or df.empty:
            return None
        close = df["Close"]
        s = close.iloc[:, 0] if isinstance(close, pd.DataFrame) else close
        s = s.dropna()
        s.name = ticker
        s.to_csv(f)
    s = s.dropna()
    s = s[s > 0]
    return s if len(s) >= MIN_SESSIONS else None


def load_rf() -> tuple[pd.Series, str]:
    f = CACHE / "DGS3MO.csv"
    try:
        if f.exists():
            s = pd.read_csv(f, index_col=0, parse_dates=True).iloc[:, 0]
        else:
            import pandas_datareader.data as web
            s = web.DataReader("DGS3MO", "fred", "2004-01-01").iloc[:, 0]
            s.to_csv(f)
        s = (s.astype(float) / 100.0).ffill().dropna()
        return s, "FRED DGS3MO (3-month T-bill, forward-filled by date)"
    except Exception as e:  # network down and no cache
        idx = pd.bdate_range("2004-01-01", "2030-01-01")
        return pd.Series(0.03, index=idx), f"constant 0.03 (FRED unreachable: {e})"


# ----------------------------------------------------------------------------- forecasts
def newey_west_t(d: np.ndarray, lag: int) -> float:
    d = np.asarray(d, float)
    n = d.size
    if n < 5:
        return float("nan")
    m = d.mean()
    u = d - m
    s = (u @ u) / n
    for k in range(1, lag + 1):
        w = 1.0 - k / (lag + 1.0)
        s += 2.0 * w * (u[k:] @ u[:-k]) / n
    return float(m / math.sqrt(s / n)) if s > 0 else float("nan")


def build_forecasts(prices: dict[str, pd.Series], rf: pd.Series, min_window: int) -> pd.DataFrame:
    """One row per (ticker, origin, horizon, method) with forecast F and realised R."""
    spy = prices["SPY"]
    spy_r = np.log(spy).diff()
    cal = spy.index
    origin_dates = cal[::STEP]
    rows = []
    for tk, px in prices.items():
        lp = np.log(px.values)
        r = np.diff(lp)                                    # r[i] = log P[i+1]/P[i]
        rs = pd.Series(r, index=px.index[1:])
        ewma = rs.ewm(halflife=252, adjust=True).mean().values * TD
        rf_tk = rf.reindex(px.index, method="ffill").values
        spy_al = spy_r.reindex(px.index).values if tk in CAPM_OK else None
        n = len(px)
        pos = np.searchsorted(px.index.values, origin_dates.values, side="right") - 1
        pos = np.unique(pos[pos >= 0])
        for p in pos:                                      # p = price index of the origin
            nr = p                                          # returns available: r[0..p-1]
            if nr < min_window or p + max(HORIZONS) >= n:
                continue
            w504 = r[p - 504:p]
            sigma = float(np.std(w504, ddof=1)) * math.sqrt(TD)
            rft = float(rf_tk[p]) if np.isfinite(rf_tk[p]) else 0.03
            mu = {}
            for wlen in (126, 252, 504, 1260):
                mu[f"sample_{wlen}"] = float(np.mean(r[p - wlen:p])) * TD if nr >= wlen else np.nan
            mu["zero"] = 0.0
            mu["rf"] = rft - 0.5 * sigma**2
            mu["rf_erp"] = rft + ERP[tk] - 0.5 * sigma**2
            se2 = sigma**2 / 2.0
            w = TAU**2 / (TAU**2 + se2)
            mu["shrink"] = w * mu["sample_504"] + (1 - w) * mu["rf"]
            mu["ewma_252"] = float(ewma[p - 1])
            if spy_al is not None:
                x, y = spy_al[p - 504 + 1:p + 1], r[p - 504:p]   # align: r[i] ends at px index i+1
                ok = np.isfinite(x)
                beta = float(np.cov(x[ok], y[ok])[0, 1] / np.var(x[ok], ddof=1)) if ok.sum() > 100 else np.nan
                mu["capm"] = rft + beta * ERP_EQ - 0.5 * sigma**2
            else:
                beta = np.nan
                mu["capm"] = np.nan
            mu["momentum_12_1"] = float(np.clip(np.mean(r[p - 252:p - 21]) * TD, -CLIP_MOM, CLIP_MOM))
            for h in HORIZONS:
                R = lp[p + h] - lp[p]
                band = Z90 * sigma * math.sqrt(h / TD)
                for m in METHODS:
                    F = mu[m]
                    if not np.isfinite(F):
                        continue
                    Fh = F * h / TD
                    rows.append((tk, TICKER_CLASS[tk], px.index[p], p, h, m, Fh, R, sigma, w, beta,
                                 rft, abs(R - Fh) <= band))
    return pd.DataFrame(rows, columns=["ticker", "cls", "date", "pos", "h", "method", "F", "R",
                                       "sigma", "w", "beta", "rf", "inband"])


# ----------------------------------------------------------------------------- metrics
def metrics(g: pd.DataFrame, mse_zero: float) -> dict:
    e = g["F"] - g["R"]
    out = {"n": len(g), "rmse": math.sqrt(np.mean(e**2)), "mae": float(np.mean(np.abs(e))),
           "bias": float(e.mean()), "skill_vs_zero": 1.0 - float(np.mean(e**2)) / mse_zero,
           "coverage_90": float(g["inband"].mean())}
    if g["method"].iloc[0] in SIGNED:
        out["hit_rate"] = float((np.sign(g["F"]) == np.sign(g["R"])).mean())
    else:
        out["hit_rate"] = np.nan
    return out


def summarise(fc: pd.DataFrame, label: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    pooled, bycls, dm = [], [], []
    for h in HORIZONS:
        fh = fc[fc.h == h]
        mse0 = float(np.mean((fh[fh.method == "zero"].F - fh[fh.method == "zero"].R) ** 2))
        for m in METHODS:
            g = fh[fh.method == m]
            if g.empty:
                continue
            pooled.append({"pass": label, "h": h, "method": m, **metrics(g, mse0)})
        if h in (63, 252):
            for c in CLASSES:
                fc_c = fh[fh.cls == c]
                z = fc_c[fc_c.method == "zero"]
                mse0c = float(np.mean((z.F - z.R) ** 2))
                for m in METHODS:
                    g = fc_c[fc_c.method == m]
                    if g.empty:
                        continue
                    bycls.append({"pass": label, "h": h, "cls": c, "method": m, **metrics(g, mse0c)})
            # Diebold-Mariano: loss differential vs sample_504, averaged across tickers at each
            # origin date, then a Newey-West t-stat with lag h/21 on that single time series.
            for baseline in ("sample_504", "zero"):
                base = fh[fh.method == baseline].set_index(["ticker", "date"])
                base_se = (base.F - base.R) ** 2
                for m in METHODS:
                    if m == baseline:
                        continue
                    g = fh[fh.method == m].set_index(["ticker", "date"])
                    if g.empty:
                        continue
                    se = (g.F - g.R) ** 2
                    d = (se - base_se.reindex(se.index)).dropna()
                    dt = d.groupby(level="date").mean().sort_index()
                    dm.append({"pass": label, "h": h, "baseline": baseline, "method": m,
                               "mean_dloss": float(dt.mean()),
                               "dm_t_nw": newey_west_t(dt.values, h // STEP), "n_origins": len(dt),
                               "n_pairs": len(d)})
    return pd.DataFrame(pooled), pd.DataFrame(bycls), pd.DataFrame(dm)


def se_table(fc: pd.DataFrame) -> pd.DataFrame:
    g = fc[(fc.method == "sample_504") & (fc.h == 252)]
    t = g.groupby("ticker").agg(mean_sigma=("sigma", "mean"), mu_std=("F", "std"),
                                mu_mean=("F", "mean"), n=("F", "size")).reset_index()
    t["theory_se"] = t["mean_sigma"] / math.sqrt(2)
    return t


def md_table(df: pd.DataFrame, cols: list[str], fmt: dict | None = None) -> str:
    fmt = fmt or {}
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for _, r in df.iterrows():
        cells = []
        for c in cols:
            v = r[c]
            if isinstance(v, float):
                cells.append("" if not np.isfinite(v) else fmt.get(c, "{:.4f}").format(v))
            else:
                cells.append(str(v))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


# ----------------------------------------------------------------------------- figures
def figures(fc: pd.DataFrame, pooled: pd.DataFrame) -> None:
    p = pooled[pooled["pass"] == "pass_1260"]
    fig, ax = plt.subplots(figsize=(8, 5))
    for m in METHODS:
        g = p[p.method == m].sort_values("h")
        ax.plot(g.h, g.rmse, marker="o", lw=2.2 if m in ("sample_504", "zero") else 1.2, label=m)
    ax.set_xlabel("horizon (sessions)"); ax.set_ylabel("RMSE of horizon log return")
    ax.set_title("Drift estimators: pooled RMSE by horizon (pass_1260)")
    ax.set_xticks(HORIZONS); ax.grid(alpha=.3); ax.legend(fontsize=8, ncol=2)
    fig.tight_layout(); fig.savefig(OUT / "fig1_rmse_by_horizon.png", dpi=130); plt.close(fig)

    g = fc[(fc["pass"] == "pass_1260") & (fc.method == "sample_504") & (fc.h == 252)]
    r2 = float(np.corrcoef(g.F, g.R)[0, 1] ** 2)
    fig, ax = plt.subplots(figsize=(6.5, 6))
    ax.scatter(g.F, g.R, s=6, alpha=.35)
    lim = [min(g.F.min(), g.R.min()), max(g.F.max(), g.R.max())]
    ax.plot(lim, lim, "k--", lw=1, label="45-degree line")
    ax.axhline(0, color="grey", lw=.6); ax.axvline(0, color="grey", lw=.6)
    ax.set_xlabel("sample_504 forecast, 252-session log return")
    ax.set_ylabel("realised 252-session log return")
    ax.set_title(f"Forecast vs realised at h=252 (R^2 = {r2:.3f}, n = {len(g)})")
    ax.legend(); ax.grid(alpha=.3)
    fig.tight_layout(); fig.savefig(OUT / "fig2_scatter_h252.png", dpi=130); plt.close(fig)

    g = fc[(fc["pass"] == "pass_1260") & (fc.method == "shrink") & (fc.h == 21)]
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for c in CLASSES:
        gc = g[g.cls == c]
        ax.scatter(gc.sigma, gc.w, s=8, alpha=.5, label=c)
    sg = np.linspace(0.03, 1.0, 200)
    ax.plot(sg, TAU**2 / (TAU**2 + sg**2 / 2), "k-", lw=1, label="w = tau^2/(tau^2 + sigma^2/2)")
    ax.set_xlabel("trailing-504 annualised vol"); ax.set_ylabel("weight on sample mean, w")
    ax.set_title(f"Shrinkage weight vs vol (tau = {TAU})"); ax.grid(alpha=.3); ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(OUT / "fig3_shrink_weight.png", dpi=130); plt.close(fig)


# ----------------------------------------------------------------------------- main
def main() -> None:
    rf, rf_note = load_rf()
    prices, dropped = {}, []
    for tk in TICKER_CLASS:
        s = load_prices(tk)
        if s is None:
            dropped.append(tk)
        else:
            prices[tk] = s
    print(f"rf source: {rf_note}")
    print(f"tickers kept: {len(prices)}; dropped (<{MIN_SESSIONS} sessions or empty): {dropped or 'none'}")
    for tk, s in prices.items():
        print(f"  {tk:10s} {len(s):5d} sessions  {s.index[0].date()} .. {s.index[-1].date()}")

    frames, tables = [], {}
    for label, mw in (("pass_1260", 1260), ("pass_504", 504)):
        fc = build_forecasts(prices, rf, mw)
        if mw < 1260:                      # keep every method on the same sample within a pass
            fc = fc[fc.method != "sample_1260"]
        fc["pass"] = label
        frames.append(fc)
        tables[label] = summarise(fc, label)
        print(f"{label}: {fc[fc.method == 'zero'].groupby('h').size().iloc[0]} (ticker, origin) pairs, "
              f"origins {fc.date.min().date()} .. {fc.date.max().date()}")
    fc = pd.concat(frames, ignore_index=True)
    pooled = pd.concat([tables[k][0] for k in tables], ignore_index=True)
    bycls = pd.concat([tables[k][1] for k in tables], ignore_index=True)
    dm = pd.concat([tables[k][2] for k in tables], ignore_index=True)
    se = se_table(fc[fc["pass"] == "pass_1260"])
    wbar = (fc[(fc["pass"] == "pass_1260") & (fc.method == "shrink") & (fc.h == 21)]
            .groupby("cls")["w"].mean())
    w_all = float(fc[(fc["pass"] == "pass_1260") & (fc.method == "shrink") & (fc.h == 21)]["w"].mean())

    # ---- results.csv (long form, every quoted number lives here)
    long = []
    for _, r in pooled.iterrows():
        for k in ("n", "rmse", "mae", "bias", "skill_vs_zero", "hit_rate", "coverage_90"):
            long.append((r["pass"], "pooled", r["method"], r["h"], "all", k, r[k]))
    for _, r in bycls.iterrows():
        for k in ("n", "rmse", "mae", "bias", "skill_vs_zero", "hit_rate", "coverage_90"):
            long.append((r["pass"], "by_class", r["method"], r["h"], r["cls"], k, r[k]))
    for _, r in dm.iterrows():
        for k in ("mean_dloss", "dm_t_nw", "n_origins", "n_pairs"):
            long.append((r["pass"], "dm_vs_" + r["baseline"], r["method"], r["h"], "all", k, r[k]))
    for _, r in se.iterrows():
        for k in ("mean_sigma", "mu_std", "mu_mean", "theory_se", "n"):
            long.append(("pass_1260", "se_sample_504", "sample_504", 252, r["ticker"], k, r[k]))
    for c, v in wbar.items():
        long.append(("pass_1260", "shrink_weight", "shrink", 21, c, "mean_w", v))
    long.append(("pass_1260", "shrink_weight", "shrink", 21, "all", "mean_w", w_all))
    for s_ in (0.2, 0.4):
        long.append(("theory", "se_theory", "sample_504", 0, f"vol_{int(s_*100)}", "sigma_over_sqrt2", s_ / math.sqrt(2)))
    res = pd.DataFrame(long, columns=["pass", "section", "method", "h", "group", "metric", "value"])
    res["value"] = res["value"].astype(float).round(6)
    res.to_csv(OUT / "results.csv", index=False, lineterminator="\n")
    figures(fc, pooled)
    write_md(prices, dropped, rf_note, pooled, bycls, dm, se, wbar, w_all, fc)
    digest = hashlib.md5((OUT / "results.csv").read_bytes()).hexdigest()
    print(f"results.csv md5 {digest}")
    print(f"wrote {OUT / 'results.csv'}, results.md, 3 figures")


def write_md(prices, dropped, rf_note, pooled, bycls, dm, se, wbar, w_all, fc) -> None:
    f4 = {"rmse": "{:.4f}", "mae": "{:.4f}", "bias": "{:+.4f}", "skill_vs_zero": "{:+.3f}",
          "hit_rate": "{:.3f}", "coverage_90": "{:.3f}", "n": "{:.0f}"}
    P = pooled[pooled["pass"] == "pass_1260"]
    B = bycls[bycls["pass"] == "pass_1260"]
    D = dm[dm["pass"] == "pass_1260"]
    P2 = pooled[pooled["pass"] == "pass_504"]

    n_origins = fc[(fc["pass"] == "pass_1260") & (fc.method == "zero") & (fc.h == 21)].shape[0]
    lines = []
    A = lines.append
    A("# Drift estimator fitness check\n")
    A(f"Script: `docs/drift_study.py`. Every number below is in `docs/drift_study/results.csv` "
      f"(columns pass, section, method, h, group, metric, value).\n")
    A("Reproduce: `python docs/drift_study.py` (prices and DGS3MO are cached as CSV under the scratchpad "
      "`drift_prices/` folder; the script prints the md5 of results.csv, which is identical on a cached re-run).\n")
    A("## Universe and protocol\n")
    A(f"- Tickers kept ({len(prices)}): " + ", ".join(f"{t} ({len(s)} sessions from {s.index[0].date()})"
                                                       for t, s in prices.items()))
    A(f"- Dropped (< 2000 sessions): {', '.join(dropped) if dropped else 'none'}")
    A(f"- Risk-free: {rf_note}. The same USD rate is used for 005930.KS and the FX crosses "
      f"(assumption: no local-currency curve in this study).")
    A(f"- ERP assumption: {ERP_EQ:.2f} for equities/ETFs (incl. EWY, 005930.KS), {ERP_BOND:.2f} for TLT/GLD, "
      f"{ERP_FX:.2f} for FX. CAPM beta vs SPY only where the calendar matches (US-listed names incl. EWY); "
      f"skipped for 005930.KS, TLT, GLD and FX.")
    A(f"- Origins: every {STEP} SPY sessions; each ticker uses its last session on or before that date. "
      f"pass_1260 requires 1260 prior returns and 252 forward sessions at every origin, so all methods and "
      f"horizons share the same {n_origins} (ticker, origin) pairs. pass_504 relaxes the look-back to 504 "
      f"(sample_1260 is then skipped where unavailable).")
    A(f"- Forecast F = mu*h/{TD}; realised R = log(P[t+h]/P[t]); errors are F - R. Skill = 1 - MSE/MSE_zero. "
      f"Band = F +/- {Z90}*sigma_504*sqrt(h/{TD}); coverage is the share of R inside it (target 0.90).")
    A(f"- Shrink: tau = {TAU}, SE^2 = sigma^2/2; mean w = {w_all:.3f} overall "
      + ", ".join(f"{c} {v:.3f}" for c, v in wbar.items()) + ".")
    A(f"- DM test: loss differential (squared error of method minus sample_504) averaged across tickers "
      f"at each origin date, then Newey-West t-stat with lag h/{STEP} on that time series "
      f"(origins overlap for h > {STEP}). |t| > 1.96 is the usual 5% line; negative t = method beats sample_504.\n")

    A("## Pooled results (pass_1260)\n")
    for h in HORIZONS:
        A(f"### h = {h}\n")
        A(md_table(P[P.h == h].sort_values("rmse"),
                   ["method", "n", "rmse", "mae", "bias", "skill_vs_zero", "hit_rate", "coverage_90"], f4))
        A("")
    A("## Diebold-Mariano tests (pass_1260)\n")
    A("Negative t = method has lower squared error than the baseline. CAPM rows use the equity/EWY sample only.\n")
    for baseline in ("sample_504", "zero"):
        A(f"### baseline = {baseline}\n")
        Db = D[D.baseline == baseline]
        A(md_table(Db.sort_values(["h", "dm_t_nw"]), ["h", "method", "mean_dloss", "dm_t_nw", "n_origins", "n_pairs"],
                   {"mean_dloss": "{:+.5f}", "dm_t_nw": "{:+.2f}", "n_origins": "{:.0f}", "n_pairs": "{:.0f}"}))
        A("")
    A("## Per-asset-class (pass_1260), h = 63 and 252\n")
    A("CAPM is only computed for US-listed names, so its n differs from the rest of the class (korea = EWY only).\n")
    for h in (63, 252):
        for c in CLASSES:
            A(f"### {c}, h = {h}\n")
            A(md_table(B[(B.h == h) & (B.cls == c)].sort_values("rmse"),
                       ["method", "n", "rmse", "bias", "skill_vs_zero", "hit_rate", "coverage_90"], f4))
            A("")
    A("## Pooled results (pass_504, look-back requirement relaxed to 504; sample_1260 excluded)\n")
    for h in (63, 252):
        A(f"### h = {h}\n")
        A(md_table(P2[P2.h == h].sort_values("rmse"),
                   ["method", "n", "rmse", "mae", "bias", "skill_vs_zero", "hit_rate", "coverage_90"], f4))
        A("")
    A("## How noisy is the sample drift?\n")
    A(f"Theory: SE(sample mean over 2 years) = sigma/sqrt(2) -> {0.2/math.sqrt(2):.3f} for a 20% vol name, "
      f"{0.4/math.sqrt(2):.3f} for a 40% vol name. Empirical: standard deviation of the annualised sample_504 "
      f"drift across origins, per ticker (annualised mu = F at h=252). The empirical figure is a little below "
      f"theory because consecutive windows overlap, but it is the same order of magnitude as the vol itself.\n")
    A(md_table(se.sort_values("mean_sigma"), ["ticker", "n", "mean_sigma", "mu_mean", "mu_std", "theory_se"],
               {"mean_sigma": "{:.3f}", "mu_mean": "{:+.3f}", "mu_std": "{:.3f}", "theory_se": "{:.3f}", "n": "{:.0f}"}))
    A("")
    A("## Figures\n")
    A("- `fig1_rmse_by_horizon.png` pooled RMSE by horizon per method")
    A("- `fig2_scatter_h252.png` sample_504 forecast vs realised at h=252 with the 45-degree line")
    A("- `fig3_shrink_weight.png` shrinkage weight w versus trailing vol\n")

    # ---- plain-English reading; numbers pulled from the tables above
    def val(df, m, h, col):
        return float(df[(df.method == m) & (df.h == h)][col].iloc[0])

    def dmt(m, h, baseline):
        return float(D[(D.method == m) & (D.h == h) & (D.baseline == baseline)]["dm_t_nw"].iloc[0])

    def cls_rmse(c, m, h):
        return float(B[(B.cls == c) & (B.method == m) & (B.h == h)]["rmse"].iloc[0])

    g = fc[(fc["pass"] == "pass_1260") & (fc.method == "sample_504") & (fc.h == 252)]
    corr = float(np.corrcoef(g.F, g.R)[0, 1])
    sk = {m: val(P, m, 252, "skill_vs_zero") for m in METHODS}
    rm = {m: val(P, m, 252, "rmse") for m in METHODS}
    A("## Reading\n")
    A(f"1. **The trailing 2-year mean carries no forecast information.** Its correlation with the realised "
      f"12-month return is {corr:+.3f} (R^2 = {corr**2:.4f}, fig2). Theory says its standard error is "
      f"{0.2/math.sqrt(2):.1%} a year for a 20%-vol name and {0.4/math.sqrt(2):.1%} for a 40%-vol name; the "
      f"per-ticker table shows the estimate moving with a standard deviation of {se.mu_std.median():.1%} "
      f"(median) against a median vol of {se.mean_sigma.median():.1%}. NVDA's 2-year drift moved with a "
      f"standard deviation of {float(se[se.ticker=='NVDA'].mu_std.iloc[0]):.1%} a year.")
    A(f"2. **Today's method loses to a flat zero at every horizon.** Pooled RMSE, sample_504 vs zero: "
      f"h=21 {val(P,'sample_504',21,'rmse'):.4f} vs {val(P,'zero',21,'rmse'):.4f}, h=63 "
      f"{val(P,'sample_504',63,'rmse'):.4f} vs {val(P,'zero',63,'rmse'):.4f}, h=252 {rm['sample_504']:.4f} vs "
      f"{rm['zero']:.4f} (skill {sk['sample_504']:+.3f}). The DM test against zero gives t = "
      f"{dmt('zero',252,'sample_504'):+.2f} at h=252 and {dmt('zero',63,'sample_504'):+.2f} at h=63: the "
      f"direction is consistent but not significant at 5%, so the honest statement is 'no better than zero, "
      f"probably worse'. Shorter windows are strictly worse and significantly so (sample_126 t = "
      f"{dmt('sample_126',252,'sample_504'):+.2f}, sample_252 t = {dmt('sample_252',252,'sample_504'):+.2f}).")
    A(f"3. **Longer memory helps; it is the only thing with a lower RMSE than zero, and even that is not "
      f"significant.** sample_1260 has the lowest RMSE at every horizon (h=252: {rm['sample_1260']:.4f}, skill {sk['sample_1260']:+.3f}; DM vs sample_504 t = "
      f"{dmt('sample_1260',252,'sample_504'):+.2f}, vs zero t = {dmt('sample_1260',252,'zero'):+.2f}). ewma_252 "
      f"(half-life one year, all history) is next: h=252 RMSE {rm['ewma_252']:.4f}, t = "
      f"{dmt('ewma_252',252,'sample_504'):+.2f} vs sample_504 and {dmt('ewma_252',252,'zero'):+.2f} vs zero. "
      f"Both gains come from the equity block (equity h=252 RMSE: sample_1260 {cls_rmse('equity','sample_1260',252):.4f}, "
      f"ewma {cls_rmse('equity','ewma_252',252):.4f}, zero {cls_rmse('equity','zero',252):.4f}); in FX and Korea "
      f"both lose to zero (fx: {cls_rmse('fx','sample_1260',252):.4f} / {cls_rmse('fx','ewma_252',252):.4f} vs "
      f"{cls_rmse('fx','zero',252):.4f}). A 5-year mean over 2010-2025 mostly learned that US equities went up; "
      f"that is a regime, not a forecasting rule.")
    A(f"4. **The structural estimators are all within noise of zero, and of each other.** h=252 RMSE: rf_erp "
      f"{rm['rf_erp']:.4f} (skill {sk['rf_erp']:+.3f}, DM vs zero t = {dmt('rf_erp',252,'zero'):+.2f}), shrink "
      f"{rm['shrink']:.4f}, rf {rm['rf']:.4f}, capm {rm['capm']:.4f} on its equity-only sample (equity-class "
      f"comparison: capm {cls_rmse('equity','capm',252):.4f}, rf_erp {cls_rmse('equity','rf_erp',252):.4f}, zero "
      f"{cls_rmse('equity','zero',252):.4f}). rf_erp is the best full-sample method in FX "
      f"({cls_rmse('fx','rf_erp',252):.4f}) and Korea ({cls_rmse('korea','rf_erp',252):.4f}) and ties for first in "
      f"bond/gold ({cls_rmse('bond_gold','rf_erp',252):.4f} vs shrink {cls_rmse('bond_gold','shrink',252):.4f}); "
      f"it is never the worst anywhere. Pure rf and shrink are significantly worse than zero (DM vs zero t = "
      f"{dmt('rf',252,'zero'):+.2f} and {dmt('shrink',252,'zero'):+.2f}) while rf_erp is not: the ERP is doing the work. Pure rf (risk-neutral) forecasts a negative drift for high-vol names "
      f"(rf - sigma^2/2), which is why its h=252 hit rate is only {val(P,'rf',252,'hit_rate'):.3f}: it is a "
      f"pricing measure, not a forecast.")
    A(f"5. **Shrinkage as specified collapses onto rf.** With tau = {TAU} the mean weight on the sample "
      f"mean is {w_all:.2f} (equity {wbar['equity']:.2f}, FX {wbar['fx']:.2f}; fig3), so shrink tracks rf "
      f"(h=252 RMSE {rm['shrink']:.4f} vs rf {rm['rf']:.4f}). Shrinking toward rf+ERP instead was not tested.")
    A(f"6. **Direction and bias.** Every method has a negative bias at h=252 (forecast below realised) because "
      f"the period was an equity bull market: zero {val(P,'zero',252,'bias'):+.4f}, rf_erp "
      f"{val(P,'rf_erp',252,'bias'):+.4f}, sample_504 {val(P,'sample_504',252,'bias'):+.4f}. Hit rates above "
      f"0.5 for positive-drift methods (rf_erp {val(P,'rf_erp',252,'hit_rate'):.3f}, sample_1260 "
      f"{val(P,'sample_1260',252,'hit_rate'):.3f}) come from that up-drift, not from timing; momentum_12_1 "
      f"({val(P,'momentum_12_1',252,'hit_rate'):.3f}, RMSE {rm['momentum_12_1']:.4f}) adds nothing.")
    A(f"7. **Band coverage barely depends on the drift.** Share inside the 5-95% band at h=252: zero "
      f"{val(P,'zero',252,'coverage_90'):.3f}, rf_erp {val(P,'rf_erp',252,'coverage_90'):.3f}, sample_1260 "
      f"{val(P,'sample_1260',252,'coverage_90'):.3f}, sample_504 {val(P,'sample_504',252,'coverage_90'):.3f}, "
      f"sample_126 {val(P,'sample_126',252,'coverage_90'):.3f} (target 0.90). Only the noisy short windows push "
      f"coverage down; the rest sit within a few points of target, which is the vol model's job.")
    A(f"8. **Relaxing the history requirement (pass_504, origins from 2007, includes 2008) does not change the "
      f"order:** h=252 RMSE zero {val(P2,'zero',252,'rmse'):.4f}, rf_erp {val(P2,'rf_erp',252,'rmse'):.4f}, "
      f"ewma_252 {val(P2,'ewma_252',252,'rmse'):.4f}, sample_504 {val(P2,'sample_504',252,'rmse'):.4f}.\n")

    A("## Recommendation for the Quant Lab\n")
    A("Expose four drift modes. Default to the risk-premium drift. Statistically it is a tie with zero (DM t "
      f"{dmt('rf_erp',252,'zero'):+.2f}), so zero is an equally defensible default; the case for rf+ERP is that it is "
      f"never the worst method in any asset class, its centre has an economic reading the operator can argue with, and "
      f"it degrades to zero for FX where the ERP is 0.\n")
    A("| mode | formula (annualised log drift) | inputs | evidence (pass_1260, h=252 unless noted) |\n|---|---|---|---|")
    A(f"| **Risk premium** (default) | rf_t + ERP - sigma^2/2 | rf from FRED DGS3MO (one cached pull, forward-filled); "
      f"ERP assumption shown in the UI: {ERP_EQ:.0%} equity/ETF, {ERP_BOND:.0%} bond/gold, 0 FX | "
      f"RMSE {rm['rf_erp']:.4f}, skill {sk['rf_erp']:+.3f} (tie with zero, DM t {dmt('rf_erp',252,'zero'):+.2f}); "
      f"beats sample_504 ({rm['sample_504']:.4f}) at every horizon; best full-sample method in FX and Korea; "
      f"coverage {val(P,'rf_erp',252,'coverage_90'):.3f}; the only mode whose centre has an economic reading |")
    A(f"| **Risk neutral** | rf_t - sigma^2/2 | rf only | RMSE {rm['rf']:.4f}; hit rate {val(P,'rf',252,'hit_rate'):.3f} "
      f"(negative drift for high-vol names). Offer it because it is the pricing measure for the structuring pages, "
      f"not because it forecasts |")
    A(f"| **Zero** | 0 | none | RMSE {rm['zero']:.4f}; nothing beats it significantly (closest challenger sample_1260, "
      f"DM t {dmt('sample_1260',252,'zero'):+.2f}); use for stress tests and FX |")
    A(f"| **Historical (long memory)** | EWMA of daily log returns, half-life 252 sessions, x252; or the plain "
      f"mean when >= 1260 sessions are loaded | price history only | ewma_252 RMSE {rm['ewma_252']:.4f} "
      f"(DM vs sample_504 t {dmt('ewma_252',252,'sample_504'):+.2f}); sample_1260 RMSE {rm['sample_1260']:.4f} "
      f"(skill {sk['sample_1260']:+.3f}). Caveat: the study's EWMA used all history since 2005 (effective span "
      f"~730 sessions); on the app's 504-session window it will sit between sample_504 and this figure. Label it "
      f"'historical, noisy' |")
    A("\nRetire the trailing 504-session sample mean as a mode (RMSE "
      f"{rm['sample_504']:.4f}, skill {sk['sample_504']:+.3f}; DM vs zero t {dmt('zero',252,'sample_504'):+.2f} in "
      f"zero's favour). If it must stay for continuity, keep it under the historical mode with the 'noisy' label.\n")
    A("Not worth a dropdown slot: sample_126 / sample_252 (significantly worse than sample_504), momentum_12_1 "
      f"(RMSE {rm['momentum_12_1']:.4f}, no directional edge), shrink as specified (tracks rf; mean w = "
      f"{w_all:.2f}), CAPM (equity-only, needs a benchmark series per market, and its equity-class RMSE "
      f"{cls_rmse('equity','capm',252):.4f} vs rf_erp {cls_rmse('equity','rf_erp',252):.4f} is inside noise).\n")
    A("Implementation notes:")
    A("- `core/quant/montecarlo.py::_calibrate` returns mu = mean(log r)*252 and `_simulate_gbm` uses "
      "(mu - 0.5*sigma^2)*dt as the log-step mean. mu is already a log-return mean, so the half-variance is "
      "subtracted twice today. Whatever the mode, define mu as the annualised log drift (as in this study, "
      "F = mu*h/252) and use mu*dt as the log-step mean; the -sigma^2/2 belongs inside the rf modes only.")
    A("- rf: FRED DGS3MO in percent -> decimal, forward-filled; cache it; if unreachable fall back to a constant "
      "and say so in the calibration row.")
    A("- ERP: an assumption, not an estimate; show it next to 'Drift (ann.)' so the operator can see and override it.")
    A("- FX: the theoretically right drift is the rate differential (r_d - r_f), not rf_usd - sigma^2/2; this "
      "study used the spec's formula and FX still came out best on rf/rf_erp (both ~0 there). Use zero or the "
      "differential for FX pairs.")
    A("- CAPM would need a benchmark on the same calendar (SPY for US names, KOSPI for .KS names); skipped here "
      "for 005930.KS, TLT, GLD and FX.")
    A("- The fan's width comes from the vol model; the drift choice moves the centre by roughly (ERP x horizon), "
      "and the study shows that centre is within noise of zero for most names.\n")
    (OUT / "results.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
