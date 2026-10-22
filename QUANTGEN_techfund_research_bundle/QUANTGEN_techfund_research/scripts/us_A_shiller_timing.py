"""A1-A3: monthly index timing on Shiller S&P 500 data, 1871-2026.

A1 10-month SMA (Faber): w_{t+1} = 1 if P_t > mean(P_{t-9..t}).
A2 12-month time-series momentum: w_{t+1} = 1 if the 12-month total return to t exceeds
   the 12-month cash return (Moskowitz-Ooi-Pedersen sign of the excess return).
A3 combination: COMBO_AVG = 0.5*A1 + 0.5*A2 (positions 0/0.5/1); COMBO_AND = A1*A2.
Returns: R_t = (P_t + D_t/12)/P_{t-1} - 1 (Shiller monthly AVERAGE prices); cash = GS10/12 - 1pp
(floored at 0) or 0%. Costs per side on |dw| at 0/5/10/50/100 bp.

Robustness: (i) signal lagged one extra month (removes the overlap between the averaged
price used for the signal and the next month's averaged-price return); (ii) the same SMA10
rule on Ken French month-end CRSP total returns, 1926-2018.
"""
import numpy as np
import pandas as pd

from us_common import (COSTS, ERAS, Results, fmt_date, load_ff_arch, perf_stats, save_json,
                       shiller_monthly)

TEST = "A_timing"
EVAL_START = pd.Period("1872-03", "M")  # first month every rule (incl. lag1 variants) has a position

EPISODES = [  # (label, first return month, last return month, note)
    ("1929-1932 crash (peak-trough)", "1929-10", "1932-06", "avg-price peak 1929-09, trough 1932-06"),
    ("1929-1932 calendar", "1929-01", "1932-12", ""),
    ("1932-33 rebound (12m after trough)", "1932-07", "1933-06", ""),
    ("1973-74 bear (peak-trough)", "1973-02", "1974-12", "peak 1973-01, trough 1974-12"),
    ("1975 rebound (12m after trough)", "1975-01", "1975-12", ""),
    ("1987 crash (peak-trough)", "1987-09", "1987-12", "peak 1987-08, trough 1987-12"),
    ("1987 calendar", "1987-01", "1987-12", ""),
    ("1988 rebound (12m after trough)", "1988-01", "1988-12", ""),
    ("2000-2002 bear (peak-trough)", "2000-09", "2003-02", "peak 2000-08, trough 2003-02"),
    ("2003-04 rebound (12m after trough)", "2003-03", "2004-02", ""),
    ("2008-2009 GFC (peak-trough)", "2007-11", "2009-03", "peak 2007-10, trough 2009-03"),
    ("2009-10 rebound (12m after trough)", "2009-04", "2010-03", ""),
    ("2010-2019 bull (whipsaw decade)", "2010-01", "2019-12", ""),
    ("2020 Feb-Apr (COVID)", "2020-02", "2020-04", ""),
    ("2020 May-Dec (rebound)", "2020-05", "2020-12", ""),
    ("2022 calendar", "2022-01", "2022-12", ""),
]


def signals(df):
    P = df["P"]
    sma10 = P.rolling(10).mean()
    s_sma = (P > sma10).astype(float).where(sma10.notna())
    lr = np.log1p(df["R"])
    lc = np.log1p(df["cash"])
    tr12 = lr.rolling(12).sum()
    c12 = lc.rolling(12).sum()
    s_mom = (tr12 > c12).astype(float).where(tr12.notna() & c12.notna())
    return s_sma, s_mom


def backtest(w, R, cash, c):
    """w = position held during the month (already lagged). Cost on |dw| charged in the month the new position is held."""
    w = w.astype(float)
    dw = w.diff().abs()
    dw.iloc[0] = abs(w.iloc[0])  # start from cash
    r = w * R + (1.0 - w) * cash - c * dw
    return r, dw


def whipsaw_spells(w, R, cash, c):
    """Out-spells of a 0/1 rule: market TR vs cash while out. Whipsaw = market beat cash while the rule was out."""
    out = []
    w = w.astype(float)
    in_spell, start = False, None
    idx = list(w.index)
    for i, d in enumerate(idx):
        if w.iloc[i] == 0 and not in_spell:
            in_spell, start = True, i
        if in_spell and (w.iloc[i] != 0 or i == len(idx) - 1):
            end = i - 1 if w.iloc[i] != 0 else i
            completed = w.iloc[i] != 0
            seg = slice(start, end + 1)
            mkt = float(np.prod(1 + R.iloc[seg].values) - 1)
            csh = float(np.prod(1 + cash.iloc[seg].values) - 1)
            out.append({"exit_first_month_out": str(idx[start]), "last_month_out": str(idx[end]),
                        "months_out": end - start + 1, "mkt_ret": mkt, "cash_ret": csh,
                        "whipsaw": mkt > csh, "completed": completed,
                        "round_trip_cost": 2 * c})
            in_spell = False
    return out


def main():
    res = Results()
    df, meta = shiller_monthly()
    s_sma, s_mom = signals(df)
    p12 = df["P"] / df["P"].shift(12) - 1
    s_mom_px = (p12 > 0).astype(float).where(p12.notna())
    base = {"SMA10": s_sma, "MOM12": s_mom, "COMBO_AVG": 0.5 * s_sma + 0.5 * s_mom, "COMBO_AND": s_sma * s_mom,
            "MOM12_price": s_mom_px}
    W = {"BH": pd.Series(1.0, index=df.index)}
    for k, s in base.items():
        W[k] = s.shift(1)            # standard: signal on month-t average price -> month t+1 avg-to-avg return
        W[k + "_lag1"] = s.shift(2)  # honest: skips the half-month overlap of averaged prices
    ev = df.loc[EVAL_START:].copy()
    for k in W:
        W[k] = W[k].loc[EVAL_START:]
        assert W[k].notna().all(), k

    cash_sets = {"tbill_proxy": ev["cash"], "cash0": ev["cash0"]}
    nets = {}
    for cname, cash in cash_sets.items():
        for strat, w in W.items():
            for clab, c in COSTS.items():
                if strat == "BH" and clab != "gross":
                    continue
                r, dw = backtest(w, ev["R"], cash, c)
                nets[(cname, strat, clab)] = (r, dw)
                rf_sh = ev["cash"]  # Sharpe always measured over the T-bill proxy (opportunity cost)
                periods = [("full_1872-03_2026-09", ev.index[0], ev.index[-1])] + \
                          [(lab, pd.Period(a, "M"), pd.Period(b, "M")) for lab, a, b in ERAS]
                for plab, a, b in periods:
                    a = max(a, ev.index[0])
                    sl = slice(a, b)
                    st = perf_stats(r.loc[sl], rf_sh.loc[sl], 12, w=w.loc[sl], dw=dw.loc[sl])
                    st["period_start"], st["period_end"] = str(a), str(b)
                    if strat != "BH":
                        rb = nets[(cname, "BH", "gross")][0].loc[sl]
                        stb = perf_stats(rb, rf_sh.loc[sl], 12)
                        st["cagr_minus_bh"] = st["cagr"] - stb["cagr"]
                        st["sharpe_minus_bh"] = st["sharpe"] - stb["sharpe"]
                        st["maxdd_minus_bh"] = st["max_dd"] - stb["max_dd"]
                    res.add_dict(TEST, f"{strat}|cash={cname}", plab, clab, st)

    # ---------------- Episodes (T-bill proxy cash) ----------------
    cash = ev["cash"]
    for lab, a, b, note in EPISODES:
        a, b = pd.Period(a, "M"), pd.Period(b, "M")
        sl = slice(a, b)
        rb = nets[("tbill_proxy", "BH", "gross")][0].loc[sl]
        bh_ret = float(np.prod(1 + rb.values) - 1)
        res.add(TEST + "_episode", "BH", lab, "gross", "cum_return", bh_ret)
        res.add(TEST + "_episode", "BH", lab, "gross", "max_dd_in_window", perf_stats(rb, cash.loc[sl], 12)["max_dd"])
        if note:
            res.add(TEST + "_episode", "BH", lab, "gross", "window_note", note)
        for strat in [k for k in W if k != "BH"]:
            w = W[strat].loc[sl]
            for clab in ["gross", "futures_5bp", "kis_50bp", "kis_50bp_x2"]:
                r, dw = nets[("tbill_proxy", strat, clab)]
                rr = r.loc[sl]
                res.add(TEST + "_episode", strat, lab, clab, "cum_return", float(np.prod(1 + rr.values) - 1))
                res.add(TEST + "_episode", strat, lab, clab, "cum_return_minus_bh", float(np.prod(1 + rr.values) - 1) - bh_ret)
                if clab == "gross":
                    res.add(TEST + "_episode", strat, lab, clab, "max_dd_in_window", perf_stats(rr, cash.loc[sl], 12)["max_dd"])
                    res.add(TEST + "_episode", strat, lab, clab, "switches", int((dw.loc[sl] > 1e-12).sum()))
                    res.add(TEST + "_episode", strat, lab, clab, "months_fully_out", int((w == 0).sum()))
                    res.add(TEST + "_episode", strat, lab, clab, "months_in_window", int(len(w)))
                    outm = [str(p) for p in w.index[w == 0]]
                    res.add(TEST + "_episode", strat, lab, clab, "months_out_list", ";".join(outm) if len(outm) <= 24 else f"{len(outm)} months")

    # ---------------- Whipsaw accounting 2010-2019 and full sample ----------------
    for strat in ["SMA10", "MOM12", "COMBO_AND", "SMA10_lag1", "MOM12_lag1", "COMBO_AND_lag1"]:
        for wlab, a, b in [("2010-2019", "2010-01", "2019-12"), ("full_1872-03_2026-09", str(EVAL_START), "2026-09")]:
            a, b = pd.Period(a, "M"), pd.Period(b, "M")
            w = W[strat]
            spells = whipsaw_spells(w, ev["R"], cash, 0.0)
            spells = [s for s in spells if pd.Period(s["exit_first_month_out"], "M") >= a
                      and pd.Period(s["exit_first_month_out"], "M") <= b]
            nsp = len(spells)
            nws = sum(s["whipsaw"] for s in spells)
            missed = sum(np.log1p(s["mkt_ret"]) - np.log1p(s["cash_ret"]) for s in spells if s["whipsaw"])
            saved = sum(np.log1p(s["cash_ret"]) - np.log1p(s["mkt_ret"]) for s in spells if not s["whipsaw"])
            ser = f"{strat}"
            res.add(TEST + "_whipsaw", ser, wlab, "gross", "out_spells", nsp)
            res.add(TEST + "_whipsaw", ser, wlab, "gross", "whipsaw_spells", int(nws))
            res.add(TEST + "_whipsaw", ser, wlab, "gross", "whipsaw_share", nws / nsp if nsp else np.nan)
            res.add(TEST + "_whipsaw", ser, wlab, "gross", "missed_log_excess_in_whipsaws", float(missed))
            res.add(TEST + "_whipsaw", ser, wlab, "gross", "saved_log_excess_in_good_exits", float(saved))
            for clab in ["futures_5bp", "kis_50bp", "kis_50bp_x2"]:
                c = COSTS[clab]
                res.add(TEST + "_whipsaw", ser, wlab, clab, "trading_cost_log_all_spells", float(nsp * 2 * np.log1p(c)))
            if wlab == "2010-2019":
                for s in spells:
                    res.add(TEST + "_whipsaw_spell", ser, f"{s['exit_first_month_out']}..{s['last_month_out']}", "gross",
                            "mkt_minus_cash_while_out", s["mkt_ret"] - s["cash_ret"])
                rb = nets[("tbill_proxy", "BH", "gross")][0].loc[a:b]
                for clab in ["gross", "futures_5bp", "kis_50bp"]:
                    rr = nets[("tbill_proxy", strat, clab)][0].loc[a:b]
                    gap = np.log(np.prod(1 + rb.values)) - np.log(np.prod(1 + rr.values))
                    res.add(TEST + "_whipsaw", ser, wlab, clab, "log_return_shortfall_vs_bh", float(gap))

    # ---------------- Robustness: averaging bias, Shiller vs French month-end 1927-2018 ----------------
    ff = load_ff_arch()
    mkt = ff["MktRF"] + ff["RF"]
    tri_f = (1 + mkt).cumprod()
    s_f = (tri_f > tri_f.rolling(10).mean()).astype(float).where(tri_f.rolling(10).mean().notna())
    a, b = pd.Period("1927-06", "M"), pd.Period("2018-11", "M")
    rf = ff["RF"].loc[a:b]
    rows = {}
    # French month-end
    w_f = s_f.shift(1).loc[a:b]
    w_f2 = s_f.shift(2).loc[a:b]
    rows["French_monthend_SMA10_on_TRI"] = (w_f, mkt.loc[a:b])
    rows["French_monthend_SMA10_on_TRI_lag1"] = (w_f2, mkt.loc[a:b])
    # Shiller avg-price
    s_sh_tri = (df["TRI"] > df["TRI"].rolling(10).mean()).astype(float).where(df["TRI"].rolling(10).mean().notna())
    rows["Shiller_avg_SMA10_on_price"] = (s_sma.shift(1).loc[a:b], df["R"].loc[a:b])
    rows["Shiller_avg_SMA10_on_price_lag1"] = (s_sma.shift(2).loc[a:b], df["R"].loc[a:b])
    rows["Shiller_avg_SMA10_on_TRI"] = (s_sh_tri.shift(1).loc[a:b], df["R"].loc[a:b])
    bh_sets = {"French": mkt.loc[a:b], "Shiller": df["R"].loc[a:b]}
    for name, (w, R) in rows.items():
        src = name.split("_")[0]
        rbh = bh_sets[src]
        stb = perf_stats(rbh, rf, 12)
        for clab in ["gross", "futures_5bp", "kis_50bp"]:
            r, dw = backtest(w, R, rf, COSTS[clab])
            st = perf_stats(r, rf, 12, w=w, dw=dw)
            st["cagr_minus_bh"] = st["cagr"] - stb["cagr"]
            st["sharpe_minus_bh"] = st["sharpe"] - stb["sharpe"]
            st["bh_cagr"], st["bh_sharpe"], st["bh_max_dd"] = stb["cagr"], stb["sharpe"], stb["max_dd"]
            res.add_dict(TEST + "_robust_avgprice", name + "|cash=French_RF", "1927-06:2018-11", clab, st)
    # episodes on French month-end data (the averaging-free check of crash avoidance)
    ep_f = [("1929-1932 crash", "1929-09", "1932-06"), ("1973-74 bear", "1973-01", "1974-09"),
            ("1987 Sep-Nov", "1987-09", "1987-11"), ("1987 Oct only", "1987-10", "1987-10"),
            ("2000-2002 bear", "2000-09", "2002-09"), ("2008-2009 GFC", "2007-11", "2009-02"),
            ("2008 Sep-Oct", "2008-09", "2008-10"), ("2010-2018 bull", "2010-01", "2018-11")]
    for lab, a2, b2 in ep_f:
        sl = slice(pd.Period(a2, "M"), pd.Period(b2, "M"))
        bh = float(np.prod(1 + mkt.loc[sl].values) - 1)
        res.add(TEST + "_robust_episode_monthend", "French_BH", lab, "gross", "cum_return", bh)
        for nm, ww in [("French_monthend_SMA10", w_f), ("French_monthend_SMA10_lag1", w_f2)]:
            r_, dw_ = backtest(ww, mkt.loc[a:b], rf, 0.0)
            res.add(TEST + "_robust_episode_monthend", nm, lab, "gross", "cum_return", float(np.prod(1 + r_.loc[sl].values) - 1))
            res.add(TEST + "_robust_episode_monthend", nm, lab, "gross", "months_out", int((ww.loc[sl] == 0).sum()))
            res.add(TEST + "_robust_episode_monthend", nm, lab, "gross", "months", int(len(ww.loc[sl])))
    # agreement of the monthly states (Shiller price-signal vs French TRI-signal)
    agree = float((s_sma.shift(1).loc[a:b] == w_f).mean())
    res.add(TEST + "_robust_avgprice", "state_agreement_Shiller_price_vs_French_TRI", "1927-06:2018-11", "gross", "share_months_same_state", agree)
    # first-order autocorrelation of monthly returns: averaging (Working 1960) effect
    res.add(TEST + "_robust_avgprice", "Shiller_R", "1927-06:2018-11", "gross", "autocorr_lag1", float(df["R"].loc[a:b].autocorr(1)))
    res.add(TEST + "_robust_avgprice", "French_Mkt", "1927-06:2018-11", "gross", "autocorr_lag1", float(mkt.loc[a:b].autocorr(1)))

    # ---------------- data flags ----------------
    for k, v in meta.items():
        res.add(TEST + "_data", "shiller", "meta", "na", k, v)
    res.add(TEST + "_data", "shiller", "meta", "na", "months_dividend_imputed", int(df["div_imputed"].sum()))
    res.add(TEST + "_data", "shiller", "meta", "na", "months_rate_carried_forward", int(df["rate_imputed"].sum()))
    res.add(TEST + "_data", "shiller", "meta", "na", "months_cash_floor_binding", int(((df["GS10"].shift(1) - 1) < 0).sum()))
    res.add(TEST + "_data", "shiller", "meta", "na", "eval_start", str(EVAL_START))

    out = res.save("us_A_timing.csv")

    # ---------------- Chart 1: log TR curves + in/out state ----------------
    def logcurve(r):
        return np.log(np.cumprod(1 + r.values))

    chart = {
        "title": "S&P 500 1872-2026: buy-and-hold vs 10-month SMA rule (Shiller monthly data)",
        "notes": ["Log of cumulative total return (start = 0 at 1872-01 end).",
                  "Shiller monthly AVERAGE prices; dividends imputed at the last known yield after 2023-06; cash = GS10/12 - 1pp (floored at 0), GS10 carried forward after 2023-09.",
                  "state = 1 when the rule holds the index during that month (decided at the previous month's end).",
                  "sma10 = standard Shiller backtest (signal on the month-t AVERAGE price, return avg(t)->avg(t+1): overlaps ~half a month before the decision, biased up). sma10_lag1 = signal applied one month later (no overlap, biased down). Month-end CRSP check 1927-2018: the truth is close to sma10_lag1."],
        "dates": [str(p) for p in ev.index],
        "bh_log_tr": logcurve(nets[("tbill_proxy", "BH", "gross")][0]).round(5).tolist(),
        "sma10_log_tr_gross": logcurve(nets[("tbill_proxy", "SMA10", "gross")][0]).round(5).tolist(),
        "sma10_log_tr_net_futures_5bp": logcurve(nets[("tbill_proxy", "SMA10", "futures_5bp")][0]).round(5).tolist(),
        "sma10_log_tr_net_kis_50bp": logcurve(nets[("tbill_proxy", "SMA10", "kis_50bp")][0]).round(5).tolist(),
        "sma10_lag1_log_tr_gross": logcurve(nets[("tbill_proxy", "SMA10_lag1", "gross")][0]).round(5).tolist(),
        "sma10_state": W["SMA10"].astype(int).tolist(),
        "sma10_lag1_state": W["SMA10_lag1"].astype(int).tolist(),
        "div_imputed": ev["div_imputed"].astype(int).tolist(),
    }
    save_json(chart, "us_chart1_sma10_vs_bh_1871_2026.json")
    print(out.shape)


if __name__ == "__main__":
    main()
