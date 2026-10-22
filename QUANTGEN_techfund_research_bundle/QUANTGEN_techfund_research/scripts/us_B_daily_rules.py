"""B: daily technical rules on SPY (Lean, 1998-2021) and the S&P 500 index (arch, 1999-2018).

Conventions
- Signal s_t uses data up to the close of day t; position w_{t+1} = s_t (QUANTGEN rule 2).
- Equity leg: close-to-close price return + 1.8%/yr dividend accrual (both series are PRICE
  series: SPY Lean is unadjusted and arch's 'Adj Close' equals 'Close'). Flagged.
- Cash leg: 1-month T-bill (Ken French RF to 2018-11, approximate TB3MS after; flagged).
- Net return: w*r_m + (1-w)*rf - c*|dw|, c per side in COSTS (initial entry charged).
- Evaluation starts at session index WARM=253 (all 322 variants have a signal; max lookback 252).

SPA (Hansen 2005) via arch.bootstrap.SPA: benchmark loss = 0 (buy-and-hold), model loss
= -(net rule return - net buy-and-hold return); stationary bootstrap, mean block 15,
2,000 reps, seed 20261002. arch 8.0.0's SPA does not studentize (statistic = max raw mean
differential), so a studentized Hansen SPA using the same bootstrap draws is also reported.
"""
import time

import numpy as np
import pandas as pd

from us_common import (COSTS, DIV_ACCRUAL_ANNUAL, SEED, Results, daily_rf, fmt_date, load_sp500_arch,
                       load_spy_lean, load_vix, monthly_rf_for_daily, nw_tstat, perf_stats, save_json)

np.seterr(divide="ignore", invalid="ignore")
WARM = 253
ACC = DIV_ACCRUAL_ANNUAL / 252.0
BLOCK = 15
REPS = 2000
T0 = time.time()


def log(msg):
    print(f"[{time.time() - T0:7.1f}s] {msg}", flush=True)


# --------------------------------------------------------------------------------------
# Data
# --------------------------------------------------------------------------------------
def load_dataset(name):
    d = load_spy_lean() if name == "SPY" else load_sp500_arch()
    d = d[["o", "h", "l", "c"]].astype(float).copy()
    d["rf"] = daily_rf(d.index, monthly_rf_for_daily()).values
    d["rm"] = d["c"].pct_change() + ACC
    return d


# --------------------------------------------------------------------------------------
# Indicators (all causal: value at t uses data <= t)
# --------------------------------------------------------------------------------------
def sma(x, n):
    return x.rolling(n, min_periods=n).mean()


def ema(x, n):
    return x.ewm(span=n, adjust=False).mean()


def rsi(c, n):
    d = c.diff()
    up, dn = d.clip(lower=0), (-d).clip(lower=0)
    au = up.ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean()
    ad = dn.ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean()
    return 100.0 - 100.0 / (1.0 + au / ad)


def state_machine(entry, exit_):
    """Long/flat: flat -> long on entry (unless exit also true); long -> flat on exit."""
    entry = np.asarray(entry, dtype=bool)
    exit_ = np.asarray(exit_, dtype=bool)
    s = np.zeros(len(entry))
    st = 0
    for i in range(len(entry)):
        if st == 0:
            if entry[i] and not exit_[i]:
                st = 1
        elif exit_[i]:
            st = 0
        s[i] = st
    return s


# --------------------------------------------------------------------------------------
# Rule family (322 variants)
# --------------------------------------------------------------------------------------
def family_spec():
    spec = []
    for n in [5, 10, 15, 20, 30, 40, 50, 60, 75, 100, 120, 150, 175, 200, 225, 250]:
        spec.append(("SMA_PRICE", {"n": n}))
    for f in [5, 10, 20, 30, 40, 50, 60, 75, 100]:
        for s in [100, 125, 150, 175, 200, 225, 250]:
            if f < s:
                spec.append(("SMA_CROSS", {"f": f, "s": s}))
    for f in [8, 12, 19]:
        for s in [17, 26, 39]:
            if f < s:
                for g in [5, 9, 12]:
                    spec.append(("MACD_SIG", {"f": f, "s": s, "g": g}))
                spec.append(("MACD_ZERO", {"f": f, "s": s}))
    for n in [2, 3, 5, 7, 10, 14, 21]:
        for lo, hi in [(10, 90), (20, 80), (25, 75), (30, 70), (35, 65), (40, 60)]:
            spec.append(("RSI_CONTRA", {"n": n, "lo": lo, "hi": hi}))
    for n in [2, 3]:
        for thr in [5, 10, 15, 20, 25]:
            for tr in [0, 100, 200]:
                for ex in [5, 10]:
                    spec.append(("CONNORS", {"n": n, "thr": thr, "trend": tr, "exit": ex}))
    for n in [10, 15, 20, 30, 50]:
        for k in [1.0, 1.5, 2.0, 2.5]:
            for ex in ["mid", "upper"]:
                spec.append(("BOLL_MR", {"n": n, "k": k, "exit": ex}))
    for N in [10, 20, 30, 40, 55, 100, 150, 200]:
        for M in [5, 10, 20, 40, 50]:
            if M < N:
                spec.append(("DONCHIAN", {"N": N, "M": M}))
    for L in [63, 126, 189, 252]:
        for dd in [0.03, 0.05, 0.075, 0.10, 0.15, 0.20]:
            spec.append(("HIGH52", {"L": L, "d": dd}))
    for L in [10, 21, 42, 63, 84, 126, 168, 189, 210, 252]:
        spec.append(("TSMOM", {"L": L, "skip": 0}))
        if L >= 63:
            spec.append(("TSMOM", {"L": L, "skip": 21}))
    # de-duplicate (Donchian condition above may repeat N=55 entries)
    seen, out = set(), []
    for r, p in spec:
        key = (r, tuple(sorted(p.items())))
        if key not in seen:
            seen.add(key)
            out.append((r, p))
    return out


def variant_id(rule, p):
    return rule + "(" + ",".join(f"{k}={v}" for k, v in p.items()) + ")"


CANONICAL = {
    "SMA200": ("SMA_PRICE", {"n": 200}),
    "SMA50/200 cross": ("SMA_CROSS", {"f": 50, "s": 200}),
    "MACD(12,26,9)": ("MACD_SIG", {"f": 12, "s": 26, "g": 9}),
    "RSI(14) 30/70 contrarian": ("RSI_CONTRA", {"n": 14, "lo": 30, "hi": 70}),
    "Connors RSI(2)<10 >SMA200, exit >SMA5": ("CONNORS", {"n": 2, "thr": 10, "trend": 200, "exit": 5}),
    "Bollinger(20,2) MR": ("BOLL_MR", {"n": 20, "k": 2.0, "exit": "mid"}),
    "Donchian 20/10": ("DONCHIAN", {"N": 20, "M": 10}),
    "52-week-high breakout (exit -10%)": ("HIGH52", {"L": 252, "d": 0.10}),
    "12-month momentum sign": ("TSMOM", {"L": 252, "skip": 0}),
}


class Indicators:
    """Caches indicator series for one price frame."""

    def __init__(self, d):
        self.c, self.h, self.l = d["c"], d["h"], d["l"]
        self._cache = {}

    def get(self, key, fn):
        if key not in self._cache:
            self._cache[key] = fn()
        return self._cache[key]

    def sma(self, n):
        return self.get(("sma", n), lambda: sma(self.c, n))

    def ema(self, n):
        return self.get(("ema", n), lambda: ema(self.c, n))

    def rsi(self, n):
        return self.get(("rsi", n), lambda: rsi(self.c, n))

    def std(self, n):
        return self.get(("std", n), lambda: self.c.rolling(n, min_periods=n).std(ddof=0))


def signal(ind, rule, p):
    c = ind.c
    if rule == "SMA_PRICE":
        return (c > ind.sma(p["n"])).values.astype(float)
    if rule == "SMA_CROSS":
        return (ind.sma(p["f"]) > ind.sma(p["s"])).values.astype(float)
    if rule == "MACD_SIG":
        m = ind.ema(p["f"]) - ind.ema(p["s"])
        return (m > m.ewm(span=p["g"], adjust=False).mean()).values.astype(float)
    if rule == "MACD_ZERO":
        return ((ind.ema(p["f"]) - ind.ema(p["s"])) > 0).values.astype(float)
    if rule == "RSI_CONTRA":
        r = ind.rsi(p["n"])
        return state_machine((r < p["lo"]).values, (r > p["hi"]).values)
    if rule == "CONNORS":
        r = ind.rsi(p["n"])
        entry = r < p["thr"]
        if p["trend"]:
            entry = entry & (c > ind.sma(p["trend"]))
        return state_machine(entry.values, (c > ind.sma(p["exit"])).values)
    if rule == "BOLL_MR":
        mid, sd = ind.sma(p["n"]), ind.std(p["n"])
        entry = c < mid - p["k"] * sd
        ex = c > mid if p["exit"] == "mid" else c > mid + p["k"] * sd
        return state_machine(entry.values, ex.values)
    if rule == "DONCHIAN":
        hi = ind.h.rolling(p["N"], min_periods=p["N"]).max().shift(1)
        lo = ind.l.rolling(p["M"], min_periods=p["M"]).min().shift(1)
        return state_machine((c > hi).values, (c < lo).values)
    if rule == "HIGH52":
        H = c.rolling(p["L"], min_periods=p["L"]).max()
        return state_machine((c >= H).values, (c < (1 - p["d"]) * H).values)
    if rule == "TSMOM":
        return ((c.shift(p["skip"]) / c.shift(p["L"]) - 1) > 0).values.astype(float)
    raise ValueError(rule)


def build_signals(d, spec):
    ind = Indicators(d)
    S = np.empty((len(d), len(spec)))
    for j, (r, p) in enumerate(spec):
        S[:, j] = signal(ind, r, p)
    return S


# --------------------------------------------------------------------------------------
# Backtest
# --------------------------------------------------------------------------------------
def positions(S):
    """w_t = s_{t-1}; evaluation rows WARM..end; initial position counted as a trade from 0."""
    W = np.vstack([np.full((1, S.shape[1]), np.nan), S[:-1]])[WARM:]
    prev = np.vstack([np.zeros((1, S.shape[1])), W[:-1]])
    return W, np.abs(W - prev)


def net_returns(W, dW, rm, rf, c):
    return W * rm[:, None] + (1.0 - W) * rf[:, None] - c * dW


def nanargmax(x):
    """argmax ignoring NaN/inf (np.argmax returns the first NaN, which picked never-invested variants)."""
    x = np.asarray(x, float)
    return int(np.argmax(np.where(np.isfinite(x), x, -np.inf)))


def family_metrics(R, rf, rbh, W, dW):
    T = R.shape[0]
    ex = R - rf[:, None]
    lg = np.log1p(R)
    cum = np.cumsum(lg, 0)
    runmax = np.maximum.accumulate(np.vstack([np.zeros((1, R.shape[1])), cum]), 0)[1:]
    mdd = np.expm1(cum - runmax).min(0)
    yrs = T / 252.0
    sd = ex.std(0, ddof=1)
    return {
        "sharpe": np.where(sd > 1e-12, ex.mean(0) / np.where(sd > 1e-12, sd, 1.0) * np.sqrt(252), np.nan),
        "cagr": np.expm1(lg.sum(0) / yrs),
        "vol": R.std(0, ddof=1) * np.sqrt(252),
        "max_dd": mdd,
        "excess_vs_bh_ann": (R - rbh[:, None]).mean(0) * 252,
        "switches_per_year": (dW > 1e-12).sum(0) / yrs,
        "time_in_market": W.mean(0),
    }


# --------------------------------------------------------------------------------------
# SPA helpers
# --------------------------------------------------------------------------------------
def kernel_variance(D, block):
    """Politis-Romano stationary-bootstrap long-run variance (same formula as arch SPA), via FFT."""
    T, K = D.shape
    p = 1.0 / block
    i = np.arange(T)
    kappa = (1 - i / T) * (1 - p) ** i + (i / T) * (1 - p) ** (T - i)
    kappa[0] = 0.5  # gamma_0 counted once below (2*0.5)
    out = np.empty(K)
    nfft = 1 << int(np.ceil(np.log2(2 * T)))
    for a in range(0, K, 128):
        X = D[:, a:a + 128] - D[:, a:a + 128].mean(0)
        F = np.fft.rfft(X, nfft, axis=0)
        ac = np.fft.irfft(F * np.conj(F), nfft, axis=0)[:T] / T
        out[a:a + 128] = 2.0 * (kappa[:, None] * ac).sum(0)
    return out


def spa_fast(Ds, block, reps, seed):
    """SPA p-values for several T x K loss-differential matrices sharing one bootstrap stream.

    Returns per matrix: arch-equivalent (non-studentized) and Hansen studentized p-values.
    """
    from arch.bootstrap import StationaryBootstrap
    T = Ds[0].shape[0]
    big = np.hstack(Ds)
    sizes = np.cumsum([0] + [D.shape[1] for D in Ds])
    dbar = big.mean(0)
    var = np.concatenate([kernel_variance(D, block) for D in Ds])
    omega = np.sqrt(np.maximum(var, 1e-300))
    valid = dbar >= -np.sqrt(var / T * 2 * np.log(np.log(T)))
    m = {"lower": np.maximum(dbar, 0.0), "consistent": np.where(valid, dbar, 0.0), "upper": dbar}
    bs = StationaryBootstrap(block, np.zeros(T), seed=seed)
    sims_raw = {k: np.empty((reps, len(Ds))) for k in m}
    sims_stu = {k: np.empty((reps, len(Ds))) for k in m}
    for b, _ in enumerate(bs.bootstrap(reps)):
        cnt = np.bincount(bs.index, minlength=T).astype(float)
        mstar = cnt @ big / T
        for k, mu in m.items():
            z = mstar - mu
            zs = np.sqrt(T) * z / omega
            for j in range(len(Ds)):
                sl = slice(sizes[j], sizes[j + 1])
                sims_raw[k][b, j] = z[sl].max()
                sims_stu[k][b, j] = max(zs[sl].max(), 0.0)
    out = []
    for j in range(len(Ds)):
        sl = slice(sizes[j], sizes[j + 1])
        stat_raw = dbar[sl].max()
        stat_stu = max((np.sqrt(T) * dbar[sl] / omega[sl]).max(), 0.0)
        r = {"stat_raw_max_mean_diff": stat_raw, "stat_studentized": stat_stu,
             "best_idx": int(np.argmax(dbar[sl])), "best_t_idx": int(np.argmax(dbar[sl] / omega[sl]))}
        for k in m:
            r[f"p_raw_{k}"] = float((sims_raw[k][:, j] > stat_raw).mean())
            r[f"p_stud_{k}"] = float((sims_stu[k][:, j] > stat_stu).mean())
        out.append(r)
    return out


def run_arch_spa(D, block=BLOCK, reps=REPS, seed=SEED, studentize=True):
    from arch.bootstrap import SPA
    spa = SPA(np.zeros(D.shape[0]), -D, block_size=block, reps=reps, bootstrap="stationary",
              studentize=studentize, seed=seed)
    spa.compute()
    pv = spa.pvalues
    return {"p_consistent": float(pv["consistent"]), "p_lower": float(pv["lower"]), "p_upper": float(pv["upper"])}


def ols_nw(y, x, lags):
    X = np.column_stack([np.ones(len(x)), x])
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    e = y - X @ b
    XtX_inv = np.linalg.inv(X.T @ X)
    u = X * e[:, None]
    S = u.T @ u
    for L in range(1, lags + 1):
        G = u[L:].T @ u[:-L]
        S += (1.0 - L / (lags + 1.0)) * (G + G.T)
    V = XtX_inv @ S @ XtX_inv
    return b, np.sqrt(np.diag(V))


def boot_p_single(x, block=BLOCK, reps=REPS, seed=SEED):
    """One-sided stationary-bootstrap p-value for mean(x) > 0 (centred bootstrap)."""
    from arch.bootstrap import StationaryBootstrap
    bs = StationaryBootstrap(block, np.zeros(len(x)), seed=seed)
    xbar = x.mean()
    cnt_means = np.empty(reps)
    for b, _ in enumerate(bs.bootstrap(reps)):
        cnt_means[b] = x[bs.index].mean()
    return float(((cnt_means - xbar) >= xbar).mean())


# --------------------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------------------
EPISODES_D = [
    ("2000-03-24..2002-10-09 dot-com bear", "2000-03-27", "2002-10-09"),
    ("2007-10-09..2009-03-09 GFC bear", "2007-10-10", "2009-03-09"),
    ("2009-03-10..2010-03-09 rebound", "2009-03-10", "2010-03-09"),
    ("2010-2019 bull", "2010-01-04", "2019-12-31"),
    ("2015-08..2016-02 whipsaw", "2015-08-01", "2016-02-29"),
    ("2018-09-21..2018-12-24 Q4 drop", "2018-09-21", "2018-12-24"),
    ("2020-02-20..2020-03-23 COVID crash", "2020-02-20", "2020-03-23"),
    ("2020-03-24..2020-12-31 rebound", "2020-03-24", "2020-12-31"),
]


def main():
    res = Results()
    fam = Results()
    spec = family_spec()
    ids = [variant_id(r, p) for r, p in spec]
    canon_idx = {k: ids.index(variant_id(*v)) for k, v in CANONICAL.items()}
    log(f"family size {len(spec)}")
    vix = load_vix()
    chart5 = {}
    cost_levels = list(COSTS.keys())

    for ds in ["SPY", "SP500"]:
        d = load_dataset(ds)
        S = build_signals(d, spec)
        W, dW = positions(S)
        assert not np.isnan(W).any(), "signals undefined inside evaluation window"
        dates = d.index[WARM:]
        rm, rf = d["rm"].values[WARM:], d["rf"].values[WARM:]
        T = len(dates)
        is_mask = dates <= pd.Timestamp("2009-12-31")
        oos_mask = ~is_mask
        periods = {"full": np.ones(T, bool), "IS_to_2009": is_mask, "OOS_from_2010": oos_mask}
        plabel = {k: f"{dates[m][0].date()}:{dates[m][-1].date()}" for k, m in periods.items()}
        log(f"{ds}: T={T} eval {dates[0].date()}..{dates[-1].date()}")
        res.add("B_data", ds, "eval", "na", "eval_start", fmt_date(dates[0]))
        res.add("B_data", ds, "eval", "na", "eval_end", fmt_date(dates[-1]))
        res.add("B_data", ds, "eval", "na", "n_days", T)

        Rs, Rbh, Dmat = {}, {}, {}
        for clab, c in COSTS.items():
            R = net_returns(W, dW, rm, rf, c)
            rbh = rm.copy()
            rbh[0] -= c
            Rs[clab], Rbh[clab] = R, rbh
            Dmat[clab] = R - rbh[:, None]  # loss differential (model better if > 0)
            for plab, msk in periods.items():
                mtx = family_metrics(R[msk], rf[msk], rbh[msk], W[msk], dW[msk])
                for j, vid in enumerate(ids):
                    for mk, mv in mtx.items():
                        fam.add("B_family", f"{ds}|{vid}", plabel[plab], clab, mk, float(mv[j]))
                bst = perf_stats(pd.Series(rbh[msk], index=dates[msk]), rf[msk], 252)
                for mk in ["cagr", "vol", "sharpe", "max_dd", "dd_peak", "dd_trough"]:
                    res.add("B_bh", f"{ds}|buy_and_hold", plabel[plab], clab, mk, bst[mk])
                share = float((mtx["excess_vs_bh_ann"] > 0).mean())
                res.add("B_family_summary", ds, plabel[plab], clab, "share_variants_mean_above_bh", share)
                fin = np.isfinite(mtx["sharpe"])
                res.add("B_family_summary", ds, plabel[plab], clab, "share_variants_sharpe_above_bh",
                        float((mtx["sharpe"][fin] > bst["sharpe"]).mean()))
                res.add("B_family_summary", ds, plabel[plab], clab, "median_sharpe_minus_bh",
                        float(np.median(mtx["sharpe"][fin] - bst["sharpe"])))
                res.add("B_family_summary", ds, plabel[plab], clab, "n_variants_never_invested", int((~fin).sum()))
        log(f"{ds}: returns + family metrics done")

        # ---------------- canonical rules ----------------
        for name, j in canon_idx.items():
            for clab in cost_levels:
                R, rbh = Rs[clab], Rbh[clab]
                for plab, msk in periods.items():
                    st = perf_stats(pd.Series(R[msk, j], index=dates[msk]), rf[msk], 252,
                                    w=W[msk, j], dw=dW[msk, j])
                    stb = perf_stats(pd.Series(rbh[msk], index=dates[msk]), rf[msk], 252)
                    st["excess_vs_bh_ann"] = float((R[msk, j] - rbh[msk]).mean() * 252)
                    st["excess_vs_bh_nw_t"] = nw_tstat(R[msk, j] - rbh[msk], 10)
                    st["sharpe_minus_bh"] = st["sharpe"] - stb["sharpe"]
                    st["cagr_minus_bh"] = st["cagr"] - stb["cagr"]
                    st["bh_sharpe"], st["bh_cagr"], st["bh_max_dd"] = stb["sharpe"], stb["cagr"], stb["max_dd"]
                    yrs = msk.sum() / 252.0
                    st["years_positive_share"] = float(
                        (pd.Series(R[msk, j], index=dates[msk]).groupby(dates[msk].year).apply(lambda x: np.prod(1 + x) - 1) > 0).mean())
                    res.add_dict("B_canonical", f"{ds}|{name}", plabel[plab], clab, st)
                for elab, a, b in EPISODES_D:
                    msk = (dates >= pd.Timestamp(a)) & (dates <= pd.Timestamp(b))
                    if msk.sum() < 5:
                        continue
                    cr = float(np.prod(1 + R[msk, j]) - 1)
                    cb = float(np.prod(1 + rbh[msk]) - 1)
                    res.add("B_canonical_episode", f"{ds}|{name}", elab, clab, "cum_return", cr)
                    res.add("B_canonical_episode", f"{ds}|{name}", elab, clab, "bh_cum_return", cb)
                    res.add("B_canonical_episode", f"{ds}|{name}", elab, clab, "minus_bh", cr - cb)
                    if clab == "gross":
                        res.add("B_canonical_episode", f"{ds}|{name}", elab, clab, "switches", int((dW[msk, j] > 0).sum()))
                        res.add("B_canonical_episode", f"{ds}|{name}", elab, clab, "time_in_market", float(W[msk, j].mean()))
        # robustness: trade at the NEXT OPEN instead of the signal close
        o, c_ = d["o"].values, d["c"].values
        r_on = o[1:] / c_[:-1] - 1.0            # close(t-1) -> open(t)
        r_id = c_[1:] / o[1:] - 1.0             # open(t) -> close(t)
        r_on = np.concatenate([[np.nan], r_on])[WARM:]
        r_id = np.concatenate([[np.nan], r_id])[WARM:]
        for name, j in canon_idx.items():
            s_ = S[:, j]
            w_new = np.concatenate([[np.nan], s_[:-1]])[WARM:]          # held open(t)->close(t): signal at close t-1, traded at open t
            w_old = np.concatenate([[np.nan, np.nan], s_[:-2]])[WARM:]  # held close(t-1)->open(t): previous position
            w_old[0] = 0.0  # evaluation starts flat
            assert not np.isnan(w_new).any() and not np.isnan(w_old).any()
            for clab in ["gross", "kis_50bp"]:
                cc = COSTS[clab]
                dwn = np.abs(w_new - w_old)
                gross_m = (1 + w_old * (r_on + ACC)) * (1 + w_new * r_id) - 1
                rr = gross_m + (1 - w_new) * rf - cc * dwn
                st = perf_stats(pd.Series(rr, index=dates), rf, 252, w=w_new, dw=dwn)
                stc = perf_stats(pd.Series(Rs[clab][:, j], index=dates), rf, 252)
                res.add_dict("B_canonical_nextopen", f"{ds}|{name}", plabel["full"], clab,
                             {"sharpe_next_open": st["sharpe"], "cagr_next_open": st["cagr"], "max_dd_next_open": st["max_dd"],
                              "sharpe_signal_close": stc["sharpe"], "cagr_signal_close": stc["cagr"],
                              "sharpe_loss_from_delay": stc["sharpe"] - st["sharpe"]})
        log(f"{ds}: canonical done")

        # ---------------- SPA: arch (official) + fast replication / studentized ----------------
        spa_fast_full = spa_fast([Dmat[c] for c in cost_levels], BLOCK, REPS, SEED)
        log(f"{ds}: fast SPA done")
        for ci, clab in enumerate(cost_levels):
            D = Dmat[clab]
            t1 = time.time()
            pa = run_arch_spa(D)
            log(f"{ds} {clab}: arch SPA {pa} ({time.time() - t1:.0f}s)")
            fr = spa_fast_full[ci]
            jb = int(np.argmax(D.mean(0)))
            st = perf_stats(pd.Series(Rs[clab][:, jb], index=dates), rf, 252, w=W[:, jb], dw=dW[:, jb])
            row = {
                "family_size": D.shape[1], "block": BLOCK, "reps": REPS, "seed": SEED,
                "arch_p_consistent": pa["p_consistent"], "arch_p_lower": pa["p_lower"], "arch_p_upper": pa["p_upper"],
                "replica_p_raw_consistent": fr["p_raw_consistent"], "replica_p_raw_lower": fr["p_raw_lower"],
                "replica_p_raw_upper": fr["p_raw_upper"],
                "studentized_p_consistent": fr["p_stud_consistent"], "studentized_p_lower": fr["p_stud_lower"],
                "studentized_p_upper": fr["p_stud_upper"],
                "best_variant": ids[jb], "best_excess_vs_bh_ann": float(D[:, jb].mean() * 252),
                "best_sharpe": st["sharpe"], "best_cagr": st["cagr"], "best_max_dd": st["max_dd"],
                "best_switches_per_year": st["switches_per_year"],
                "best_naive_nw_t": nw_tstat(D[:, jb], 10),
                "best_naive_boot_p": boot_p_single(D[:, jb]),
                "best_by_t_variant": ids[fr["best_t_idx"]],
                "bh_sharpe": perf_stats(pd.Series(Rbh[clab], index=dates), rf, 252)["sharpe"],
            }
            fm_all = family_metrics(Rs[clab], rf, Rbh[clab], W, dW)
            jsr = nanargmax(fm_all["sharpe"])
            row["best_sharpe_variant"] = ids[jsr]
            row["best_sharpe_value"] = float(fm_all["sharpe"][jsr])
            row["best_sharpe_time_in_market"] = float(fm_all["time_in_market"][jsr])
            act = np.where(fm_all["time_in_market"] >= 0.10, fm_all["sharpe"], np.nan)
            jsa = nanargmax(act)
            row["best_sharpe_variant_min10pct_invested"] = ids[jsa]
            row["best_sharpe_value_min10pct_invested"] = float(fm_all["sharpe"][jsa])
            res.add_dict("B_SPA", ds, plabel["full"], clab, row)
            if ds == "SPY" and clab in ("gross", "kis_50bp"):
                chart5[clab] = {"best_idx": jb, "best_id": ids[jb]}

        # Sharpe-type SPA (vol-matched excess returns), fast implementation only
        Dsh = []
        for clab in cost_levels:
            R, rbh = Rs[clab], Rbh[clab]
            exk = R - rf[:, None]
            exb = rbh - rf
            sdk = exk.std(0, ddof=1)
            scale = np.where(sdk > 1e-12, exb.std(ddof=1) / np.where(sdk > 1e-12, sdk, 1.0), 0.0)
            Dsh.append(exk * scale[None, :] - exb[:, None])
        for ci, r in enumerate(spa_fast(Dsh, BLOCK, REPS, SEED)):
            res.add_dict("B_SPA_volmatched", ds, plabel["full"], cost_levels[ci], {
                "studentized_p_consistent": r["p_stud_consistent"], "studentized_p_lower": r["p_stud_lower"],
                "studentized_p_upper": r["p_stud_upper"], "raw_p_consistent": r["p_raw_consistent"],
                "best_variant": ids[r["best_idx"]],
                "best_volmatched_excess_ann": float(Dsh[ci][:, r["best_idx"]].mean() * 252)})
        log(f"{ds}: vol-matched SPA done")

        # Block-size sensitivity (fast, studentized and raw)
        for blk in [10, 20]:
            for ci, r in enumerate(spa_fast([Dmat[c] for c in cost_levels], blk, REPS, SEED)):
                res.add_dict("B_SPA_block_sensitivity", ds, plabel["full"], cost_levels[ci],
                             {"block": blk, "raw_p_consistent": r["p_raw_consistent"],
                              "studentized_p_consistent": r["p_stud_consistent"],
                              "studentized_p_lower": r["p_stud_lower"], "studentized_p_upper": r["p_stud_upper"]})
        log(f"{ds}: block sensitivity done")

        # ---------------- Time split: select on IS, test OOS ----------------
        for clab in cost_levels:
            R, rbh = Rs[clab], Rbh[clab]
            mis = family_metrics(R[is_mask], rf[is_mask], rbh[is_mask], W[is_mask], dW[is_mask])
            moos = family_metrics(R[oos_mask], rf[oos_mask], rbh[oos_mask], W[oos_mask], dW[oos_mask])
            bis = perf_stats(pd.Series(rbh[is_mask], index=dates[is_mask]), rf[is_mask], 252)
            boos = perf_stats(pd.Series(rbh[oos_mask], index=dates[oos_mask]), rf[oos_mask], 252)
            for crit in ["sharpe", "excess_vs_bh_ann", "sharpe_min10pct_invested"]:
                if crit == "sharpe_min10pct_invested":
                    j = nanargmax(np.where(mis["time_in_market"] >= 0.10, mis["sharpe"], np.nan))
                    key = "sharpe"
                else:
                    j = nanargmax(mis[crit])
                    key = crit
                fin = np.isfinite(moos[key])
                rank_oos = float((moos[key][fin] < moos[key][j]).mean())
                x = R[oos_mask, j] - rbh[oos_mask]
                row = {"selected_variant": ids[j], "is_sharpe": float(mis["sharpe"][j]), "is_cagr": float(mis["cagr"][j]),
                       "is_excess_vs_bh_ann": float(mis["excess_vs_bh_ann"][j]), "is_bh_sharpe": bis["sharpe"],
                       "oos_sharpe": float(moos["sharpe"][j]), "oos_cagr": float(moos["cagr"][j]),
                       "oos_max_dd": float(moos["max_dd"][j]), "oos_excess_vs_bh_ann": float(moos["excess_vs_bh_ann"][j]),
                       "oos_bh_sharpe": boos["sharpe"], "oos_bh_cagr": boos["cagr"], "oos_bh_max_dd": boos["max_dd"],
                       "oos_switches_per_year": float(moos["switches_per_year"][j]),
                       "oos_percentile_rank_in_family": rank_oos,
                       "is_time_in_market": float(mis["time_in_market"][j]), "oos_time_in_market": float(moos["time_in_market"][j]),
                       "oos_excess_boot_p": boot_p_single(x), "oos_excess_nw_t": nw_tstat(x, 10),
                       "spearman_is_oos_across_family": float(pd.Series(mis[key]).rank().corr(pd.Series(moos[key]).rank()))}
                res.add_dict("B_timesplit", ds, f"select_on={crit}|IS {plabel['IS_to_2009']}|OOS {plabel['OOS_from_2010']}", clab, row)
                if ds == "SPY" and clab in ("gross", "kis_50bp") and crit == "sharpe":
                    chart5.setdefault(clab, {})["is_sel_idx"] = j
                    chart5[clab]["is_sel_id"] = ids[j]
        # OOS family SPA (does anything beat BH after 2010?)
        Doos = [Dmat[c][oos_mask] for c in cost_levels]
        for ci, r in enumerate(spa_fast(Doos, BLOCK, REPS, SEED)):
            res.add_dict("B_SPA_oos_family", ds, plabel["OOS_from_2010"], cost_levels[ci], {
                "studentized_p_consistent": r["p_stud_consistent"], "raw_p_consistent": r["p_raw_consistent"],
                "studentized_p_lower": r["p_stud_lower"], "studentized_p_upper": r["p_stud_upper"],
                "best_oos_variant": ids[r["best_idx"]], "best_oos_excess_ann": float(Doos[ci][:, r["best_idx"]].mean() * 252)})
        log(f"{ds}: time split done")

        # ---------------- VIX regimes ----------------
        v = vix.reindex(d.index).ffill()
        med = v.rolling(252, min_periods=252).median()
        hi_t = (v > med).astype(float).where(med.notna())
        reg = hi_t.shift(1).values[WARM:]  # regime known at t-1 applies to day-t return
        okr = ~np.isnan(reg)
        for name, j in list(canon_idx.items()) + [("buy_and_hold", None)]:
            for clab in ["gross", "kis_50bp"]:
                R = Rbh[clab] if j is None else Rs[clab][:, j]
                rbh = Rbh[clab]
                for rlab, rv in [("VIX_above_1y_median", 1.0), ("VIX_below_1y_median", 0.0)]:
                    msk = okr & (reg == rv)
                    ex = R[msk] - rf[msk]
                    row = {"n_days": int(msk.sum()), "mean_ann": float(R[msk].mean() * 252),
                           "vol_ann": float(R[msk].std(ddof=1) * np.sqrt(252)),
                           "sharpe": float(ex.mean() / ex.std(ddof=1) * np.sqrt(252)),
                           "excess_vs_bh_ann": float((R[msk] - rbh[msk]).mean() * 252),
                           "time_in_market": float(1.0 if j is None else W[msk, j].mean())}
                    res.add_dict("B_vix_regime", f"{ds}|{name}", rlab, clab, row)
                if j is not None:
                    x = (R - rbh)[okr]
                    b, se = ols_nw(x, reg[okr], 10)
                    res.add("B_vix_regime", f"{ds}|{name}", "high_minus_low", clab, "excess_vs_bh_diff_ann", float(b[1] * 252))
                    res.add("B_vix_regime", f"{ds}|{name}", "high_minus_low", clab, "diff_nw_t", float(b[1] / se[1]))
        res.add("B_vix_regime", ds, "share_days_high", "na", "share", float(np.nanmean(reg)))
        log(f"{ds}: VIX regimes done")

        # ---------------- Chart 5 data (SPY only) ----------------
        if ds == "SPY":
            j200 = canon_idx["SMA200"]
            curves = {"dates": [str(x.date()) for x in dates],
                      "bh_gross": np.cumprod(1 + Rbh["gross"]).round(5).tolist(),
                      "bh_kis_50bp": np.cumprod(1 + Rbh["kis_50bp"]).round(5).tolist()}
            for clab in ["gross", "kis_50bp"]:
                curves[f"sma200_{clab}"] = np.cumprod(1 + Rs[clab][:, j200]).round(5).tolist()
                jb = chart5[clab]["best_idx"]
                curves[f"best_spa_variant_{clab}"] = np.cumprod(1 + Rs[clab][:, jb]).round(5).tolist()
                curves[f"best_spa_variant_{clab}_id"] = chart5[clab]["best_id"]
                js = chart5[clab]["is_sel_idx"]
                curves[f"is_selected_variant_{clab}"] = np.cumprod(1 + Rs[clab][:, js]).round(5).tolist()
                curves[f"is_selected_variant_{clab}_id"] = chart5[clab]["is_sel_id"]
            curves["sma200_state"] = W[:, j200].astype(int).tolist()
            curves["title"] = "SPY 1999-2021: buy-and-hold vs close>SMA200 vs best SPA-family variant (growth of $1)"
            curves["notes"] = ["Price return + 1.8%/yr dividend accrual (approximation); cash earns T-bills.",
                               "best_spa_variant = highest full-sample mean net excess over buy-and-hold at that cost level (in-sample pick; SPA p-values in us_B_daily.csv).",
                               "is_selected_variant = best Sharpe on 1999-2009, held unchanged in 2010-2021 (the honest out-of-sample curve).",
                               "Signals at the close of t, position from t+1; costs per side on turnover."]
            save_json(curves, "us_chart5_spy_daily_equity_curves.json")

    res.save("us_B_daily.csv")
    fam.save("us_B_family.csv")
    log("saved")


if __name__ == "__main__":
    main()
