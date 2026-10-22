"""Shared loaders, metrics and output helpers for the QUANTGEN US data lab.

Conventions (QUANTGEN rule 2): a signal formed with data up to the close of period t
sets the position held over period t+1. Costs are charged on every unit of turnover
(|change in position|) at a per-side rate; levels are pre-registered in COSTS.
"""
import os

for _v in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import io
import json
import zipfile

import numpy as np
import pandas as pd

RAW = "/home/claude/data_raw/us"
OUT = "/home/claude/datalab/us"
RES = f"{OUT}/results"
CHT = f"{OUT}/charts"
SEED = 20261002

# Pre-registered per-side cost levels (QUANTGEN context, section 1) + 2x stress.
COSTS = {
    "gross": 0.0,
    "futures_5bp": 0.0005,
    "futures_5bp_x2": 0.0010,
    "kis_50bp": 0.0050,
    "kis_50bp_x2": 0.0100,
}

ERAS = [
    ("1871-1925", "1871-01", "1925-12"),
    ("1926-1945", "1926-01", "1945-12"),
    ("1946-1989", "1946-01", "1989-12"),
    ("1990-2009", "1990-01", "2009-12"),
    ("2010-2026", "2010-01", "2026-09"),
]

DIV_ACCRUAL_ANNUAL = 0.018  # approximate SPY / S&P 500 dividend yield used for daily tests (flagged)

# Approximate 3-month T-bill rates (FRED TB3MS, % p.a.) typed from memory because the
# shell has no network; used ONLY for the daily cash leg 2018-12..2021-03, after the
# local Ken French RF series ends (2018-11). Flagged in the summary.
TB3MS_APPROX = {
    "2018-12": 2.37, "2019-01": 2.37, "2019-02": 2.39, "2019-03": 2.40, "2019-04": 2.38,
    "2019-05": 2.35, "2019-06": 2.17, "2019-07": 2.10, "2019-08": 1.95, "2019-09": 1.89,
    "2019-10": 1.65, "2019-11": 1.54, "2019-12": 1.54, "2020-01": 1.52, "2020-02": 1.52,
    "2020-03": 0.29, "2020-04": 0.14, "2020-05": 0.13, "2020-06": 0.16, "2020-07": 0.13,
    "2020-08": 0.10, "2020-09": 0.11, "2020-10": 0.10, "2020-11": 0.09, "2020-12": 0.09,
    "2021-01": 0.08, "2021-02": 0.04, "2021-03": 0.03,
}


# --------------------------------------------------------------------------------------
# Output helpers
# --------------------------------------------------------------------------------------
class Results:
    """Collects rows in the required long format: test, series, period, cost_level, metric, value."""

    def __init__(self):
        self.rows = []

    def add(self, test, series, period, cost_level, metric, value):
        if isinstance(value, (np.floating, np.integer)):
            value = value.item()
        if isinstance(value, pd.Period):
            value = str(value)
        if isinstance(value, pd.Timestamp):
            value = value.strftime("%Y-%m-%d")
        self.rows.append((test, series, period, cost_level, metric, value))

    def add_dict(self, test, series, period, cost_level, d):
        for k, v in d.items():
            self.add(test, series, period, cost_level, k, v)

    def frame(self):
        return pd.DataFrame(self.rows, columns=["test", "series", "period", "cost_level", "metric", "value"])

    def save(self, name):
        os.makedirs(RES, exist_ok=True)
        df = self.frame()
        df.to_csv(f"{RES}/{name}", index=False)
        return df


def save_json(obj, name):
    os.makedirs(CHT, exist_ok=True)

    def _default(o):
        if isinstance(o, (np.floating,)):
            return None if not np.isfinite(o) else float(o)
        if isinstance(o, (np.integer,)):
            return int(o)
        if isinstance(o, (pd.Period, pd.Timestamp)):
            return str(o)
        if isinstance(o, np.ndarray):
            return o.tolist()
        raise TypeError(type(o))

    def _clean(x):
        if isinstance(x, dict):
            return {k: _clean(v) for k, v in x.items()}
        if isinstance(x, (list, tuple)):
            return [_clean(v) for v in x]
        if isinstance(x, float) and not np.isfinite(x):
            return None
        return x

    with open(f"{CHT}/{name}", "w") as f:
        json.dump(_clean(obj), f, default=_default, separators=(",", ":"))


def fmt_date(x):
    if x is None:
        return None
    if isinstance(x, str):
        return x
    if isinstance(x, pd.Period):
        return str(x)
    if isinstance(x, pd.Timestamp):
        return x.strftime("%Y-%m-%d")
    return str(x)


# --------------------------------------------------------------------------------------
# Loaders
# --------------------------------------------------------------------------------------
def load_shiller_raw():
    df = pd.read_csv(f"{RAW}/shiller_sp500_monthly.csv", parse_dates=["Date"]).set_index("Date")
    df.index = df.index.to_period("M")
    df = df.astype(float).replace(0.0, np.nan)  # zeros = missing (task spec)
    return df.rename(columns={
        "SP500": "P", "Dividend": "D", "Earnings": "E", "Consumer Price Index": "CPI",
        "Long Interest Rate": "GS10", "PE10": "CAPE",
    })


def shiller_monthly():
    """Monthly Shiller panel with total returns and the T-bill proxy.

    R_t   = (P_t + D_t/12) / P_{t-1} - 1   (P = monthly AVERAGE price, D = annualised dividend)
    After the last dividend observation (2023-06) D_t = last known 12m yield x P_t (flagged).
    cash_t = (GS10_{t-1} - 1pp)/12, floored at 0; GS10 carried forward after 2023-09 (flagged).
    """
    raw = load_shiller_raw()
    df = pd.DataFrame(index=raw.index)
    P, D = raw["P"], raw["D"]
    last_d = D.last_valid_index()
    dy_last = float(D[last_d] / P[last_d])
    imp = np.asarray(raw.index > last_d)
    D_f = D.copy()
    D_f[imp] = dy_last * P[imp]
    df["P"] = P
    df["D_raw"] = D
    df["D"] = D_f
    df["div_imputed"] = imp.astype(int)
    df["E"] = raw["E"]
    df["CAPE"] = raw["CAPE"]
    df["CPI"] = raw["CPI"]
    gs = raw["GS10"]
    last_r = gs.last_valid_index()
    df["GS10_raw"] = gs
    df["GS10"] = gs.ffill()
    df["rate_imputed"] = np.asarray(raw.index > last_r).astype(int)
    df["R"] = (P + D_f / 12.0) / P.shift(1) - 1.0
    df["Rp"] = P / P.shift(1) - 1.0
    df["cash"] = ((df["GS10"].shift(1) - 1.0) / 1200.0).clip(lower=0.0)
    df["cash0"] = 0.0
    df["TRI"] = (1.0 + df["R"].fillna(0.0)).cumprod()
    meta = {"dy_last": dy_last, "last_dividend_month": str(last_d), "last_rate_month": str(last_r),
            "last_cpi_month": str(raw["CPI"].last_valid_index()),
            "last_cape_month": str(raw["CAPE"].last_valid_index())}
    return df, meta


def load_spy_lean():
    """SPY daily OHLCV, QuantConnect Lean format (prices x 10,000, not dividend adjusted)."""
    with zipfile.ZipFile(f"{RAW}/spy_lean_daily.zip") as z:
        raw = z.read("spy.csv")
    df = pd.read_csv(io.BytesIO(raw), header=None, names=["dt", "o", "h", "l", "c", "v"])
    assert (df["dt"].str[8:] == " 00:00").all()
    df.index = pd.to_datetime(df["dt"].str[:8], format="%Y%m%d")
    df.index.name = "date"
    df = df.drop(columns="dt")
    for k in "ohlc":
        df[k] = df[k] / 1e4
    return df


def load_sp500_arch():
    import arch.data.sp500 as s
    d = s.load()
    d = d.rename(columns={"Open": "o", "High": "h", "Low": "l", "Close": "close_raw", "Adj Close": "c", "Volume": "v"})
    d.index = pd.DatetimeIndex(d.index).as_unit("ns")
    d.index.name = "date"
    return d[["o", "h", "l", "c", "v", "close_raw"]]


def load_vix():
    v = pd.read_csv(f"{RAW}/vix_daily.csv", parse_dates=["DATE"]).set_index("DATE")
    v.index = pd.DatetimeIndex(v.index).as_unit("ns")
    v.index.name = "date"
    return v["CLOSE"].astype(float)


def _decode_arch_french_index(idx):
    """arch's frenchdata index stores YYYYMM as nanoseconds since 1970 -> decode to monthly periods."""
    vals = pd.DatetimeIndex(idx).as_unit("ns").asi8
    return pd.PeriodIndex([pd.Period(year=int(v // 100), month=int(v % 100), freq="M") for v in vals])


def load_ff_arch():
    """Ken French Mkt-RF, SMB, HML, RF in DECIMALS, monthly 1926-07..2018-11."""
    import arch.data.frenchdata as fd
    ff = fd.load()
    ff.index = _decode_arch_french_index(ff.index)
    ff = ff / 100.0
    ff.columns = ["MktRF", "SMB", "HML", "RF"]
    return ff


def load_ff_lm():
    """linearmodels French dataset (decimals): factors, Mom, 10 industries, 9 size/value, 9 size/mom."""
    import linearmodels.datasets.french as lf
    d = lf.load()
    d.index = pd.PeriodIndex(d["dates"], freq="M")
    return d.drop(columns="dates").astype(float)


INDUSTRIES = ["NoDur", "Durbl", "Manuf", "Enrgy", "Chems", "BusEq", "Telcm", "Utils", "Shops", "Hlth", "Money", "Other"]
SIZE_VALUE = ["S1V1", "S1V3", "S1V5", "S3V1", "S3V3", "S3V5", "S5V1", "S5V3", "S5V5"]
SIZE_MOM = ["S1M1", "S1M3", "S1M5", "S3M1", "S3M3", "S3M5", "S5M1", "S5M3", "S5M5"]


def monthly_rf_for_daily():
    """Monthly 1-month T-bill return (decimal): French RF through 2018-11, then TB3MS_APPROX/12."""
    rf = load_ff_arch()["RF"].copy()
    extra = pd.Series({pd.Period(k, "M"): v / 1200.0 for k, v in TB3MS_APPROX.items()})
    extra = extra[extra.index > rf.index.max()]
    return pd.concat([rf, extra]).sort_index()


def daily_rf(dates, rf_m):
    per = pd.DatetimeIndex(dates).to_period("M")
    cnt = pd.Series(1, index=dates).groupby(per).transform("count").values
    m = rf_m.reindex(per).values
    if np.isnan(m).any():
        raise ValueError("missing monthly RF for some dates")
    return pd.Series((1.0 + m) ** (1.0 / cnt) - 1.0, index=dates)


# --------------------------------------------------------------------------------------
# Metrics
# --------------------------------------------------------------------------------------
def max_drawdown(r):
    """Max drawdown of the compounded curve (starting capital 1 counts as the first peak)."""
    r = pd.Series(r).astype(float).fillna(0.0)
    if len(r) == 0:
        return np.nan, None, None, None
    eq = np.cumprod(1.0 + r.values)
    run_max = np.maximum.accumulate(np.concatenate([[1.0], eq]))[1:]
    dd = eq / run_max - 1.0
    i_tr = int(np.argmin(dd))
    mdd = float(dd[i_tr])
    if mdd >= 0:
        return 0.0, None, None, None
    pk_val = run_max[i_tr]
    cand = np.where(np.abs(eq[: i_tr + 1] - pk_val) <= 1e-12 * max(1.0, pk_val))[0]
    pk = r.index[cand[-1]] if len(cand) else "start"
    rec = np.where(eq[i_tr:] >= pk_val * (1 - 1e-12))[0]
    rec_d = r.index[i_tr + rec[0]] if len(rec) else None
    return mdd, pk, r.index[i_tr], rec_d


def perf_stats(r, rf, ppy, w=None, dw=None):
    """CAGR, vol, Sharpe (excess over rf), max DD with dates, switches/turnover/time-in-market."""
    r = pd.Series(r).astype(float)
    rf = pd.Series(rf, index=r.index).astype(float) if not np.isscalar(rf) else pd.Series(rf, index=r.index)
    n = int(r.notna().sum())
    yrs = n / ppy
    g = float(np.prod(1.0 + r.dropna().values))
    ex = r - rf
    sd = ex.std(ddof=1)
    out = {
        "cagr": g ** (1.0 / yrs) - 1.0 if yrs > 0 and g > 0 else np.nan,
        "vol": float(r.std(ddof=1) * np.sqrt(ppy)),
        "sharpe": float(ex.mean() / sd * np.sqrt(ppy)) if sd > 0 else np.nan,
        "mean_excess_ann": float(ex.mean() * ppy),
        "total_return": g - 1.0,
        "n_periods": n,
    }
    mdd, pk, tr, rec = max_drawdown(r)
    out.update({"max_dd": mdd, "dd_peak": fmt_date(pk), "dd_trough": fmt_date(tr), "dd_recovery": fmt_date(rec)})
    if w is not None:
        w = pd.Series(w).astype(float)
        out["time_in_market"] = float(w.mean())
    if dw is not None:
        dw = pd.Series(dw).astype(float)
        out["switches_per_year"] = float((dw > 1e-12).sum() / yrs)
        out["turnover_per_year"] = float(dw.sum() / yrs)
    return out


def nw_tstat(x, lags):
    """Newey-West t-statistic of the mean of x."""
    x = np.asarray(x, float)
    x = x[~np.isnan(x)]
    n = len(x)
    u = x - x.mean()
    s = u @ u / n
    for L in range(1, lags + 1):
        w = 1.0 - L / (lags + 1.0)
        s += 2.0 * w * (u[L:] @ u[:-L]) / n
    return float(x.mean() / np.sqrt(s / n)) if s > 0 else np.nan
