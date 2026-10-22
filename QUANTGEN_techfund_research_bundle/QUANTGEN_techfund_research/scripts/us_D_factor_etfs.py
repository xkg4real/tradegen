"""D (optional): 1-year returns of SPY, MTUM, QUAL, USMV, IWM (VLUE unavailable) to 2026-10-01.

Source: Stocklake MCP get_stock_history(symbol, days=365), pulled 2026-10-02 in the agent session
(the shell has no network). The closes used are transcribed into
/home/claude/datalab/us/results/us_D_stocklake_closes_raw.csv (anchor dates + month-ends).

DATA PROBLEM (flagged): the Stocklake series is a splice. Bars up to mid-June 2026 look
dividend-ADJUSTED (fractional closes), bars from 2026-06-15/18 look RAW (2-decimal closes), and the
volume units change on 2026-07-21/22 (an 'ibkr' source from 2026-08-12). The 1-year change
close(2026-10-01)/close(2025-10-01) - 1 therefore mixes an adjusted start with a raw end:
it is neither a clean price return nor a clean total return. Because the adjusted start is
LOWER than the raw price by roughly the dividends paid between the start and the adjustment
date, the ratio is close to a TOTAL return for dividends paid before mid-June 2026 and a PRICE
return for later dividends (SPY Sept-2026 ex-dividend ~0.15-0.2% not included). Treat the
numbers as approximate (+/- ~0.5pp for SPY/QUAL/USMV, more for USMV/IWM yield).
"""
import pandas as pd

from us_common import RES, Results

SRC = "/tmp/claude-0/-home-claude/b6e9e1fb-8824-58da-9d2f-b07436463a9f/scratchpad/stocklake_closes.csv"


def main():
    raw = pd.read_csv(SRC)
    raw.to_csv(f"{RES}/us_D_stocklake_closes_raw.csv", index=False)
    px = raw.dropna(subset=["date"]).copy()
    px["date"] = pd.to_datetime(px["date"])
    px = px.drop_duplicates(["symbol", "date"]).pivot(index="date", columns="symbol", values="close").sort_index()
    res = Results()
    rows = []
    a, b = pd.Timestamp("2025-10-01"), pd.Timestamp("2026-10-01")
    for sym in ["SPY", "MTUM", "QUAL", "USMV", "IWM"]:
        r1 = px.at[b, sym] / px.at[a, sym] - 1
        rows.append((sym, r1))
        res.add("D_factor_etfs", sym, "2025-10-01:2026-10-01", "na", "one_year_return_spliced", float(r1))
        # calendar sub-windows from month-end closes
        for s, e in [("2025-09-30", "2025-12-31"), ("2025-12-31", "2026-03-31"), ("2026-03-31", "2026-06-30"), ("2026-06-30", "2026-09-30")]:
            s_, e_ = pd.Timestamp(s), pd.Timestamp(e)
            if pd.notna(px.at[s_, sym]) and pd.notna(px.at[e_, sym]):
                res.add("D_factor_etfs", sym, f"{s}:{e}", "na", "quarter_return_spliced", float(px.at[e_, sym] / px.at[s_, sym] - 1))
    spy = dict(rows)["SPY"]
    for sym, r1 in rows:
        if sym != "SPY":
            res.add("D_factor_etfs", f"{sym}-SPY", "2025-10-01:2026-10-01", "na", "relative_return_vs_SPY", float(r1 - spy))
            res.add("D_factor_etfs", f"{sym}/SPY", "2025-10-01:2026-10-01", "na", "relative_wealth_ratio_minus_1", float((1 + r1) / (1 + spy) - 1))
    res.add("D_factor_etfs", "VLUE", "2025-10-01:2026-10-01", "na", "one_year_return_spliced", "unavailable (Stocklake: history_not_found)")
    res.add("D_factor_etfs", "ALL", "flag", "na", "data_warning",
            "Stocklake splice: adjusted closes to mid-Jun-2026, raw closes after; volume units change 2026-07-21/22; returns approximate")
    out = res.save("us_D_factor_etfs.csv")
    print(out[out.metric.isin(["one_year_return_spliced", "relative_return_vs_SPY"])])


if __name__ == "__main__":
    main()
