"""C: CAPM and factor-model tests on Ken French data.

C1 Security market line (linearmodels French data, 1949-2017, decimals). The dataset has 12
   industry columns (NoDur..Other). Primary set = 28 portfolios as requested: 10 industries
   (NoDur, Durbl, Manuf, Enrgy, Chems, BusEq, Telcm, Utils, Shops, Hlth; Money and Other
   excluded) + 9 size/value + 9 size/momentum; the 30-portfolio set (all 12 industries) is a
   robustness row. Rolling 60-month betas on months t-59..t; Fama-MacBeth cross-section of
   month t+1 excess returns on beta_t; first slope 1954-01 (60 months from 1949-01).
C2 GRS (Gibbons-Ross-Shanken 1989) + linearmodels TradedFactorModel J-test for CAPM, FF3,
   FF3+Mom on 9 size/value and 9 size/momentum portfolios, 1949-01..2017-03.
C3 Factor history: Mkt-RF, SMB, HML 1926-07..2018-11 (arch French) and Mom 1949-01..2017-03.
"""
import numpy as np
import pandas as pd
from scipy import stats

from us_common import (INDUSTRIES, SIZE_MOM, SIZE_VALUE, Results, fmt_date, load_ff_arch, load_ff_lm,
                       max_drawdown, nw_tstat, save_json)

TEST = "C_factors"
IND10 = ["NoDur", "Durbl", "Manuf", "Enrgy", "Chems", "BusEq", "Telcm", "Utils", "Shops", "Hlth"]


# --------------------------------------------------------------------------------------
# C1 helpers
# --------------------------------------------------------------------------------------
def rolling_betas(ex, mkt, win=60):
    """beta_t from months t-win+1..t (inclusive). Returns DataFrame aligned to t."""
    out = pd.DataFrame(index=ex.index, columns=ex.columns, dtype=float)
    m = mkt.values
    X = ex.values
    for i in range(win - 1, len(ex)):
        mm = m[i - win + 1:i + 1]
        xx = X[i - win + 1:i + 1]
        mc = mm - mm.mean()
        out.iloc[i] = (mc @ (xx - xx.mean(0))) / (mc @ mc)
    return out


def fama_macbeth(ex, betas):
    """Cross-section each month t+1: ex_{t+1} = g0 + g1 * beta_t."""
    rows = []
    idx = ex.index
    for i in range(len(idx) - 1):
        b = betas.iloc[i]
        if b.isna().any():
            continue
        y = ex.iloc[i + 1].values
        X = np.column_stack([np.ones(len(b)), b.values])
        g, *_ = np.linalg.lstsq(X, y, rcond=None)
        rows.append((idx[i + 1], g[0], g[1]))
    return pd.DataFrame(rows, columns=["month", "g0", "g1"]).set_index("month")


def fm_summary(fm, mkt, a, b):
    f = fm.loc[a:b]
    m = mkt.reindex(f.index)
    n = len(f)
    out = {"n_months": n,
           "avg_slope_g1_monthly": f["g1"].mean(), "avg_slope_g1_ann": f["g1"].mean() * 12,
           "g1_t_fm": f["g1"].mean() / (f["g1"].std(ddof=1) / np.sqrt(n)), "g1_t_nw6": nw_tstat(f["g1"].values, 6),
           "avg_intercept_g0_monthly": f["g0"].mean(), "avg_intercept_g0_ann": f["g0"].mean() * 12,
           "g0_t_fm": f["g0"].mean() / (f["g0"].std(ddof=1) / np.sqrt(n)),
           "avg_mkt_excess_monthly": m.mean(), "avg_mkt_excess_ann": m.mean() * 12,
           "slope_minus_mkt_ann": (f["g1"].mean() - m.mean()) * 12}
    dd = f["g1"] - m
    out["slope_minus_mkt_t"] = dd.mean() / (dd.std(ddof=1) / np.sqrt(n))
    return out


# --------------------------------------------------------------------------------------
# C2 helpers
# --------------------------------------------------------------------------------------
def grs(ex, F):
    """GRS F-test; ex: T x N test-asset excess returns, F: T x L factor excess returns."""
    T, N = ex.shape
    L = F.shape[1]
    X = np.column_stack([np.ones(T), F])
    B, *_ = np.linalg.lstsq(X, ex, rcond=None)
    E = ex - X @ B
    alpha = B[0]
    Sigma = E.T @ E / (T - L - 1)
    mu = F.mean(0)
    Om = np.atleast_2d(np.cov(F, rowvar=False, ddof=1)) if L > 1 else np.array([[F.var(ddof=1)]])
    q = float(mu @ np.linalg.solve(Om, mu)) if L > 1 else float(mu[0] ** 2 / Om[0, 0])
    a_s_a = float(alpha @ np.linalg.solve(Sigma, alpha))
    stat = (T - N - L) / N * a_s_a / (1.0 + q)
    p = 1.0 - stats.f.cdf(stat, N, T - N - L)
    # per-portfolio alpha t-stats (OLS)
    XtX_inv = np.linalg.inv(X.T @ X)
    se_a = np.sqrt(np.diag(Sigma) * XtX_inv[0, 0])
    r2 = 1 - (E ** 2).sum(0) / ((ex - ex.mean(0)) ** 2).sum(0)
    return {"grs_F": stat, "grs_p": p, "alpha": alpha, "alpha_t": alpha / se_a, "betas": B[1:], "r2": r2,
            "mean_abs_alpha_ann": float(np.abs(alpha).mean() * 12), "sh2_factors": q, "sh2_alpha": a_s_a}


def lm_jtest(ex, F):
    from linearmodels.asset_pricing import TradedFactorModel
    mod = TradedFactorModel(ex, F).fit(cov_type="robust")
    return float(mod.j_statistic.stat), float(mod.j_statistic.pval), mod


# --------------------------------------------------------------------------------------
# C3 helpers
# --------------------------------------------------------------------------------------
def fstats(x):
    x = x.dropna()
    n = len(x)
    out = {"n_months": n, "mean_ann": x.mean() * 12, "vol_ann": x.std(ddof=1) * np.sqrt(12),
           "sharpe_ann": x.mean() / x.std(ddof=1) * np.sqrt(12), "t_stat": x.mean() / (x.std(ddof=1) / np.sqrt(n)),
           "share_months_positive": float((x > 0).mean())}
    mdd, pk, tr, rec = max_drawdown(x)
    out.update({"max_dd": mdd, "dd_peak": fmt_date(pk), "dd_trough": fmt_date(tr), "dd_recovery": fmt_date(rec) if rec is not None else "not recovered"})
    return out


def main():
    res = Results()
    lm = load_ff_lm()
    ff = load_ff_arch()

    # ---------------- Validation of French data ----------------
    res.add(TEST + "_validation", "arch_frenchdata", "decoded", "na", "first_month", str(ff.index[0]))
    res.add(TEST + "_validation", "arch_frenchdata", "decoded", "na", "last_month", str(ff.index[-1]))
    res.add(TEST + "_validation", "arch_frenchdata", "decoded", "na", "n_months", len(ff))
    res.add(TEST + "_validation", "arch_frenchdata", "decoded", "na", "months_contiguous",
            bool((ff.index[1:] - ff.index[:-1]).map(lambda x: x.n).unique().tolist() == [1]))
    for mth in ["1987-10", "2008-09", "1929-10", "1931-09", "1932-07", "2008-10"]:
        res.add(TEST + "_validation", "arch_frenchdata", mth, "na", "MktRF_pct", float(ff.at[pd.Period(mth, "M"), "MktRF"] * 100))
        res.add(TEST + "_validation", "arch_frenchdata", mth, "na", "Mkt_total_pct", float((ff.at[pd.Period(mth, "M"), "MktRF"] + ff.at[pd.Period(mth, "M"), "RF"]) * 100))
    res.add(TEST + "_validation", "linearmodels_french", "units", "na", "units", "decimals (MktRF 1987-10 = %.4f)" % lm.at[pd.Period("1987-10", "M"), "MktRF"])
    j = ff.join(lm[["MktRF", "SMB", "HML", "RF"]], rsuffix="_lm", how="inner")
    for k in ["MktRF", "SMB", "HML", "RF"]:
        dd = (j[k] - j[k + "_lm"]) * 100
        res.add(TEST + "_validation", f"vintage_diff_{k}", f"{j.index[0]}:{j.index[-1]}", "na", "max_abs_diff_pct", float(dd.abs().max()))
        res.add(TEST + "_validation", f"vintage_diff_{k}", f"{j.index[0]}:{j.index[-1]}", "na", "corr", float(j[k].corr(j[k + "_lm"])))
    # portfolio returns are total (not excess) returns: avg of industries ~ Mkt total
    tot = lm[INDUSTRIES].mean(axis=1)
    res.add(TEST + "_validation", "linearmodels_french", "1949-2017", "na", "mean_EW_industry_minus_Mkt_total_ann",
            float((tot - lm["MktRF"] - lm["RF"]).mean() * 12))
    res.add(TEST + "_validation", "linearmodels_french", "1949-2017", "na", "corr_EW_industry_vs_Mkt_total",
            float(tot.corr(lm["MktRF"] + lm["RF"])))

    # ---------------- C1 Security market line ----------------
    sets = {"28 (10 ind + 9 SV + 9 SM)": IND10 + SIZE_VALUE + SIZE_MOM,
            "30 (12 ind + 9 SV + 9 SM)": INDUSTRIES + SIZE_VALUE + SIZE_MOM,
            "10 industries": IND10, "9 size/value": SIZE_VALUE, "9 size/momentum": SIZE_MOM}
    ex_all = lm[INDUSTRIES + SIZE_VALUE + SIZE_MOM].sub(lm["RF"], axis=0)
    mkt = lm["MktRF"]
    betas_all = rolling_betas(ex_all, mkt, 60)
    subp = [("1954-01", "2017-03"), ("1954-01", "1969-12"), ("1970-01", "1989-12"), ("1990-01", "2017-03"),
            ("1954-01", "1985-12"), ("1986-01", "2017-03"), ("2000-01", "2017-03")]
    fm_store = {}
    for sname, cols in sets.items():
        fm = fama_macbeth(ex_all[cols], betas_all[cols])
        fm_store[sname] = fm
        for a, b in subp:
            res.add_dict(TEST + "_C1_famamacbeth", sname, f"{a}:{b}", "na", fm_summary(fm, mkt, a, b))
    # full-period time-series betas and average excess returns (SML chart) -- 28 set, 1954-2017
    cols28 = sets["28 (10 ind + 9 SV + 9 SM)"]
    sml = []
    for a, b in [("1954-01", "2017-03"), ("1949-01", "2017-03")]:
        e = ex_all.loc[a:b, cols28]
        m = mkt.loc[a:b]
        for c in cols28:
            beta = np.cov(e[c], m, ddof=1)[0, 1] / m.var(ddof=1)
            mu = e[c].mean() * 12
            sh = e[c].mean() / e[c].std(ddof=1) * np.sqrt(12)
            alpha = (e[c].mean() - beta * m.mean()) * 12
            res.add_dict(TEST + "_C1_sml_points", c, f"{a}:{b}", "na", {"beta_full_period": beta, "avg_excess_ann": mu, "sharpe": sh, "capm_alpha_ann": alpha})
            if a == "1954-01":
                grp = "industry" if c in INDUSTRIES else ("size/value" if c in SIZE_VALUE else "size/momentum")
                sml.append({"portfolio": c, "group": grp, "beta": round(float(beta), 4), "avg_excess_ann_pct": round(float(mu * 100), 3),
                            "sharpe": round(float(sh), 3), "capm_alpha_ann_pct": round(float(alpha * 100), 3)})
    mk_ann = mkt.loc["1954-01":"2017-03"].mean() * 12
    xs = np.array([p["beta"] for p in sml])
    ys = np.array([p["avg_excess_ann_pct"] for p in sml]) / 100
    sml_fit = np.polyfit(xs, ys, 1)
    res.add_dict(TEST + "_C1_sml_fit", "28 portfolios, full-period betas", "1954-01:2017-03", "na",
                 {"xs_slope_ann": sml_fit[0], "xs_intercept_ann": sml_fit[1], "mkt_excess_ann": mk_ann,
                  "xs_r2": float(np.corrcoef(xs, ys)[0, 1] ** 2)})

    # beta terciles (rolling beta_t sorts, next-month returns), equal-weight across portfolios
    for sname in ["28 (10 ind + 9 SV + 9 SM)", "30 (12 ind + 9 SV + 9 SM)"]:
        cols = sets[sname]
        b = betas_all[cols]
        e = ex_all[cols]
        recs = []
        for i in range(len(b) - 1):
            bt = b.iloc[i]
            if bt.isna().any():
                continue
            ranks = bt.rank(method="first")
            k = len(cols)
            terc = np.ceil(ranks / (k / 3.0)).clip(1, 3)
            nxt = e.iloc[i + 1]
            recs.append((e.index[i + 1], *[nxt[terc == q].mean() for q in (1, 2, 3)], *[bt[terc == q].mean() for q in (1, 2, 3)]))
        tdf = pd.DataFrame(recs, columns=["month", "r1", "r2", "r3", "b1", "b2", "b3"]).set_index("month")
        for a, bnd in [("1954-01", "2017-03"), ("1954-01", "1985-12"), ("1986-01", "2017-03")]:
            t = tdf.loc[a:bnd]
            for q in (1, 2, 3):
                x = t[f"r{q}"]
                res.add_dict(TEST + "_C1_beta_terciles", f"{sname}|T{q} ({['low','mid','high'][q-1]} beta)", f"{a}:{bnd}", "na",
                             {"avg_ex_ante_beta": t[f"b{q}"].mean(), "avg_excess_ann": x.mean() * 12, "vol_ann": x.std(ddof=1) * np.sqrt(12),
                              "sharpe": x.mean() / x.std(ddof=1) * np.sqrt(12),
                              "capm_alpha_ann": (x.mean() - np.cov(x, mkt.reindex(t.index), ddof=1)[0, 1] / mkt.reindex(t.index).var(ddof=1) * mkt.reindex(t.index).mean()) * 12})
            hl = t["r3"] - t["r1"]
            res.add_dict(TEST + "_C1_beta_terciles", f"{sname}|T3-T1", f"{a}:{bnd}", "na",
                         {"avg_excess_ann": hl.mean() * 12, "t_stat": hl.mean() / (hl.std(ddof=1) / np.sqrt(len(hl))),
                          "beta_spread": (t["b3"] - t["b1"]).mean(),
                          "capm_implied_ann": (t["b3"] - t["b1"]).mean() * mkt.reindex(t.index).mean() * 12})

    # ---------------- C2 time-series tests ----------------
    F_all = lm[["MktRF", "SMB", "HML", "Mom"]]
    models = {"CAPM": ["MktRF"], "FF3": ["MktRF", "SMB", "HML"], "FF3+Mom": ["MktRF", "SMB", "HML", "Mom"]}
    for tname, cols in [("9 size/value", SIZE_VALUE), ("9 size/momentum", SIZE_MOM), ("18 combined", SIZE_VALUE + SIZE_MOM)]:
        for a, b in [("1949-01", "2017-03"), ("1949-01", "1982-12"), ("1983-01", "2017-03")]:
            ex = ex_all.loc[a:b, cols]
            for mname, fc in models.items():
                F = F_all.loc[a:b, fc]
                g = grs(ex.values, F.values)
                J, Jp, _ = lm_jtest(ex, F)
                res.add_dict(TEST + "_C2_grs", f"{tname}|{mname}", f"{a}:{b}", "na",
                             {"grs_F": g["grs_F"], "grs_p": g["grs_p"], "lm_J_robust": J, "lm_J_p": Jp,
                              "mean_abs_alpha_ann": g["mean_abs_alpha_ann"], "n_months": len(ex),
                              "avg_r2": float(np.mean(g["r2"]))})
                if (a, b) == ("1949-01", "2017-03"):
                    for k, c in enumerate(cols):
                        res.add_dict(TEST + "_C2_alphas", f"{tname}|{mname}|{c}", f"{a}:{b}", "na",
                                     {"alpha_ann": g["alpha"][k] * 12, "alpha_t": g["alpha_t"][k], "r2": g["r2"][k],
                                      **{f"beta_{fc[i]}": g["betas"][i][k] for i in range(len(fc))}})

    # ---------------- C3 factor history ----------------
    fac = {"Mkt-RF": ff["MktRF"], "SMB": ff["SMB"], "HML": ff["HML"], "Mom": lm["Mom"]}
    for fname, x in fac.items():
        res.add_dict(TEST + "_C3_factor", fname, f"{x.index[0]}:{x.index[-1]}", "na", fstats(x))
        decs = sorted(set((p.year // 10) * 10 for p in x.index))
        for dcd in decs:
            xx = x.loc[f"{dcd}-01":f"{dcd + 9}-12"]
            if len(xx) < 12:
                continue
            res.add_dict(TEST + "_C3_factor_decade", fname, f"{dcd}s ({xx.index[0]}:{xx.index[-1]})", "na", fstats(xx))
        for a, b in [("1926-07", "1962-12"), ("1963-07", "1990-12"), ("1991-01", "2018-11"), ("1963-07", "1981-12"), ("1982-01", "2018-11"),
                     ("1990-01", "2017-03"), ("2008-01", "2017-03"), ("2007-01", "2018-11")]:
            xx = x.loc[a:b]
            if len(xx) < 24:
                continue
            res.add_dict(TEST + "_C3_factor_subperiod", fname, f"{xx.index[0]}:{xx.index[-1]}", "na", fstats(xx))
    # specific episodes
    hml = ff["HML"]
    hml07 = hml.loc["2007-01":]
    mdd, pk, tr, rec = max_drawdown(hml07)
    res.add_dict(TEST + "_C3_episode", "HML drawdown from 2007", f"2007-01:{hml.index[-1]}", "na",
                 {"max_dd": mdd, "peak": fmt_date(pk), "trough": fmt_date(tr), "recovery": fmt_date(rec) if rec else "not recovered by 2018-11",
                  "cum_return": float(np.prod(1 + hml07) - 1), "mean_ann": hml07.mean() * 12, "sharpe": hml07.mean() / hml07.std(ddof=1) * np.sqrt(12)})
    # HML drawdown from its pre-2007 peak (end-2006) to the 2018 end
    cum = (1 + hml).cumprod()
    pk06 = cum.loc[:"2006-12"].idxmax()
    res.add_dict(TEST + "_C3_episode", "HML from all-time peak to 2018-11", f"{pk06}:{hml.index[-1]}", "na",
                 {"peak_month": str(pk06), "dd_to_2018_11": float(cum.iloc[-1] / cum.loc[pk06] - 1),
                  "min_since_peak": float(cum.loc[pk06:].min() / cum.loc[pk06] - 1), "min_month": str(cum.loc[pk06:].idxmin())})
    mom = lm["Mom"]
    for a, b, lab in [("2009-03", "2009-05", "Mom crash Mar-May 2009"), ("2009-01", "2009-12", "Mom calendar 2009"),
                      ("2009-04", "2009-04", "Mom Apr 2009"), ("1932-07", "1932-08", "n/a")]:
        if lab == "n/a":
            continue
        xx = mom.loc[a:b]
        res.add_dict(TEST + "_C3_episode", lab, f"{a}:{b}", "na", {"cum_return": float(np.prod(1 + xx) - 1), "months": len(xx),
                                                                 "worst_month": float(xx.min()), "worst_month_date": str(xx.idxmin())})
    mm = max_drawdown(mom)
    res.add_dict(TEST + "_C3_episode", "Mom max drawdown 1949-2017", f"{mom.index[0]}:{mom.index[-1]}", "na",
                 {"max_dd": mm[0], "peak": fmt_date(mm[1]), "trough": fmt_date(mm[2]), "recovery": fmt_date(mm[3]) if mm[3] else "not recovered by 2017-03"})
    # worst months of Mom and the market state (rebound after bear)
    mk_lm = lm["MktRF"]
    past24 = (1 + mk_lm + lm["RF"]).rolling(24).apply(np.prod, raw=True) - 1
    for p in mom.nsmallest(5).index:
        res.add_dict(TEST + "_C3_mom_worst_months", "Mom", str(p), "na", {"mom_return": float(mom[p]), "mkt_excess_same_month": float(mk_lm[p]),
                                                                       "mkt_total_past24m_to_prev_month": float(past24.shift(1)[p])})
    smb = ff["SMB"]
    for a, b in [("1926-07", "1980-12"), ("1981-01", "2018-11"), ("1981-01", "1999-12"), ("2000-01", "2018-11")]:
        res.add_dict(TEST + "_C3_episode", "SMB before/after 1981 (Banz 1981 publication)", f"{a}:{b}", "na", fstats(smb.loc[a:b]))
    # correlations HML vs Mom
    hm = pd.concat([lm["HML"], lm["Mom"]], axis=1).dropna()
    res.add(TEST + "_C3_corr", "corr(HML, Mom) linearmodels", f"{hm.index[0]}:{hm.index[-1]}", "na", "corr", float(hm["HML"].corr(hm["Mom"])))
    for a, b in [("1949-01", "1979-12"), ("1980-01", "1999-12"), ("2000-01", "2017-03")]:
        sub = hm.loc[a:b]
        res.add(TEST + "_C3_corr", "corr(HML, Mom) linearmodels", f"{a}:{b}", "na", "corr", float(sub["HML"].corr(sub["Mom"])))
    # 50/50 HML+Mom combo
    combo = 0.5 * lm["HML"] + 0.5 * lm["Mom"]
    res.add_dict(TEST + "_C3_factor", "50/50 HML+Mom", f"{combo.index[0]}:{combo.index[-1]}", "na", fstats(combo))
    for a, b in [("1949-01", "1989-12"), ("1990-01", "2017-03"), ("2008-01", "2017-03")]:
        res.add_dict(TEST + "_C3_factor_subperiod", "50/50 HML+Mom", f"{a}:{b}", "na", fstats(combo.loc[a:b]))

    # rolling 10-year Sharpe
    roll = {}
    for fname, x in fac.items():
        r = x.rolling(120).mean() / x.rolling(120).std(ddof=1) * np.sqrt(12)
        roll[fname] = r
        rr = r.dropna()
        res.add_dict(TEST + "_C3_rolling10y_sharpe", fname, f"{rr.index[0]}:{rr.index[-1]}", "na",
                     {"min": rr.min(), "min_end_month": str(rr.idxmin()), "max": rr.max(), "max_end_month": str(rr.idxmax()),
                      "last": rr.iloc[-1], "last_month": str(rr.index[-1]), "share_windows_negative": float((rr < 0).mean())})
    res.save("us_C_factors.csv")

    # ---------------- Charts ----------------
    save_json({"title": "Security market line, 28 US portfolios (10 industries, 9 size/value, 9 size/momentum), 1954-01..2017-03",
               "x_label": "Full-period CAPM beta", "y_label": "Average excess return, % p.a.",
               "capm_line": {"intercept_pct": 0.0, "slope_pct": round(float(mk_ann * 100), 3),
                             "points": [{"beta": 0.0, "ret": 0.0}, {"beta": 1.6, "ret": round(float(mk_ann * 160), 3)}]},
               "fitted_line": {"intercept_pct": round(float(sml_fit[1] * 100), 3), "slope_pct": round(float(sml_fit[0] * 100), 3)},
               "fama_macbeth_rolling_beta": {k: round(float(v), 5) for k, v in fm_summary(fm_store["28 (10 ind + 9 SV + 9 SM)"], mkt, "1954-01", "2017-03").items()},
               "points": sml,
               "notes": ["CAPM line: E[R]-rf = beta x average market excess return (same months).",
                         "Fama-MacBeth block uses rolling 60-month betas and next-month returns."]},
              "us_chart3_security_market_line.json")
    idx = sorted(set().union(*[set(v.dropna().index) for v in roll.values()]))
    save_json({"title": "Rolling 10-year (120-month) Sharpe ratio of US factors",
               "notes": ["Mkt-RF, SMB, HML: Ken French via arch (1926-07..2018-11); Mom: linearmodels French (1949-01..2017-03).",
                         "Value at month t uses months t-119..t; annualised (x sqrt(12))."],
               "dates": [str(p) for p in idx],
               "series": {k: [None if (p not in v.index or np.isnan(v.get(p, np.nan))) else round(float(v[p]), 4) for p in idx] for k, v in roll.items()}},
              "us_chart4_factor_rolling_10y_sharpe.json")
    print("C done", len(res.rows))


if __name__ == "__main__":
    main()
