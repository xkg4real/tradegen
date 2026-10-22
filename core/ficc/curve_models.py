"""Curve models beyond the static fit: Diebold–Li dynamic Nelson–Siegel, the
PCA-neutral butterfly, Koijen et al. bond carry, and the KRW curve from KIS.

  dns_factors     daily (β₁, β₂, β₃) by OLS on the Nelson–Siegel loadings with
                  λ FIXED at Diebold–Li's 0.0609 per month (0.7308 per year)
  dns_study       monthly sampling, direct-h AR(1) per factor, recursive out-of-
                  sample forecasts at h = 6 and 12 months, RMSE against the
                  random walk per maturity and a Diebold–Mariano test
                  (Diebold & Li 2006, J. Econometrics 130; NBER w10048 pp. 12–16)
  butterfly_weights   (w₂, 1, w₁₀) with zero loading on the first two curve
                  PCs (Litterman & Scheinkman 1991) from `core.ficc.curves.curve_pca`
  butterfly_signal    z-score of the fly, entry |z| > 2, exit 0 or 60 sessions,
                  half-life and ADF from `core.quant.strategies`
  bond_carry      Koijen, Moskowitz, Pedersen & Vrugt (2018) eq. (15):
                  carry = (y_T − r_short) + D_mod·(y_T − y_{T−h}) (slope + roll-down)
  krw_curve_panel CD 91d + KTB 1/3/5/10/20/30y par yields from the KIS chart
                  endpoint (percent → decimals), as a `CurvePanel`

Citations to the user's materials: Berkeley TS lecture 6 §1.1 (AR(1) forecast,
half-life); 계량2 §2.4.1, §2.4.3 (forecast evaluation), §5.3 (unit roots);
Lay §7.1/§7.5 (eigenvectors, PCA); Meucci §3.5.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional, Sequence

import numpy as np

from core.ficc.common import BP, FICCError
from core.ficc.curves import PCAResult, _loading, curve_pca, nelson_siegel
from core.ficc.data import CurvePanel

DL_LAMBDA_MONTHLY = 0.0609            # Diebold–Li, per month with τ in months
DL_LAMBDA_YEARLY = DL_LAMBDA_MONTHLY * 12.0


# --------------------------------------------------------------------------- #
# Dynamic Nelson–Siegel
# --------------------------------------------------------------------------- #
def dns_loadings(tenors_years: Sequence[float], lam: float = DL_LAMBDA_YEARLY) -> np.ndarray:
    t = np.asarray(tenors_years, dtype=float)
    s, c = _loading(t, 1.0 / lam)
    return np.column_stack([np.ones(t.size), s, c])


def dns_factors(panel: CurvePanel, *, lam: float = DL_LAMBDA_YEARLY) -> tuple[np.ndarray, np.ndarray]:
    """(betas T×3, rmse T) by OLS of each day's yields on the fixed loadings."""
    X = dns_loadings(panel.tenors, lam)
    Y = np.asarray(panel.yields, dtype=float)
    B, *_ = np.linalg.lstsq(X, Y.T, rcond=None)
    fitted = (X @ B).T
    rmse = np.sqrt(np.mean((fitted - Y) ** 2, axis=1))
    return B.T, rmse


def _month_ends(dates: Sequence[str]) -> np.ndarray:
    idx = []
    for i in range(len(dates) - 1):
        if dates[i][:7] != dates[i + 1][:7]:
            idx.append(i)
    idx.append(len(dates) - 1)
    return np.asarray(idx)


@dataclass(frozen=True)
class DNSStudy:
    horizons: tuple[int, ...]
    tenors: tuple[float, ...]
    n_forecasts: dict[int, int]
    rmse_dns: dict[int, np.ndarray] = field(repr=False)     # per horizon, per tenor (decimal yields)
    rmse_rw: dict[int, np.ndarray] = field(repr=False)
    dm_t: dict[int, np.ndarray] = field(repr=False)          # negative favours DNS
    ar_coefficients: np.ndarray = field(repr=False)           # last-fit γ per factor per horizon (H×3)
    latest_forecast: dict[int, np.ndarray] = field(repr=False)   # forecast curve per horizon
    latest_factors: tuple[float, float, float] = (0.0, 0.0, 0.0)
    fit_rmse_bp: float = 0.0
    note: str = ""

    def beats_rw(self, h: int) -> int:
        return int(np.sum(self.rmse_dns[h] < self.rmse_rw[h]))


def dns_study(panel: CurvePanel, *, horizons: Sequence[int] = (6, 12), first_forecast_month: int = 120,
              lam: float = DL_LAMBDA_YEARLY) -> DNSStudy:
    """Recursive out-of-sample study: at every month-end m ≥ first_forecast_month,
    fit β_{t+h} = c + γ β_t on all months ≤ m (direct-h, per factor), forecast
    the curve h months ahead, and compare with the random walk (no change).
    RMSE per maturity in decimal yield; DM on squared errors with lag h − 1."""
    from core.quant.validate import newey_west_t
    betas, fit_rmse = dns_factors(panel, lam=lam)
    me = _month_ends(panel.dates)
    if me.size < first_forecast_month + max(horizons) + 12:
        raise FICCError(f"need ≥ {first_forecast_month + max(horizons) + 12} months of curves, "
                        f"got {me.size}")
    Bm = betas[me]                       # monthly factors
    Ym = np.asarray(panel.yields)[me]     # monthly curves
    X = dns_loadings(panel.tenors, lam)
    rmse_dns, rmse_rw, dm_t, n_fc, latest, gam = {}, {}, {}, {}, {}, []
    for h in horizons:
        err_d, err_r = [], []
        g_last = np.zeros(3)
        for m in range(first_forecast_month, Bm.shape[0] - h):
            fc = np.zeros(3)
            for j in range(3):
                x, y = Bm[:m - h + 1, j], Bm[h:m + 1, j]
                A = np.column_stack([np.ones(x.size), x])
                c, g = np.linalg.lstsq(A, y, rcond=None)[0]
                fc[j] = c + g * Bm[m, j]
                g_last[j] = g
            y_hat = X @ fc
            err_d.append(y_hat - Ym[m + h])
            err_r.append(Ym[m] - Ym[m + h])
        E_d, E_r = np.asarray(err_d), np.asarray(err_r)
        rmse_dns[h] = np.sqrt(np.mean(E_d ** 2, axis=0))
        rmse_rw[h] = np.sqrt(np.mean(E_r ** 2, axis=0))
        dm_t[h] = np.array([newey_west_t(E_d[:, k] ** 2 - E_r[:, k] ** 2, h - 1) for k in range(E_d.shape[1])])
        n_fc[h] = int(E_d.shape[0])
        gam.append(g_last.copy())
        # latest forecast from the full sample
        fc = np.zeros(3)
        for j in range(3):
            x, y = Bm[:-h, j], Bm[h:, j]
            A = np.column_stack([np.ones(x.size), x])
            c, g = np.linalg.lstsq(A, y, rcond=None)[0]
            fc[j] = c + g * Bm[-1, j]
        latest[h] = X @ fc
    return DNSStudy(horizons=tuple(horizons), tenors=tuple(panel.tenors), n_forecasts=n_fc, rmse_dns=rmse_dns,
                    rmse_rw=rmse_rw, dm_t=dm_t, ar_coefficients=np.asarray(gam), latest_forecast=latest,
                    latest_factors=tuple(float(b) for b in betas[-1]), fit_rmse_bp=float(np.mean(fit_rmse) / BP),
                    note=f"λ fixed at {lam:.4f}/yr (Diebold–Li 0.0609/month); {me.size} month-ends; "
                         f"first forecast at month {first_forecast_month}; direct-h AR(1) per factor")


# --------------------------------------------------------------------------- #
# PCA-neutral butterfly
# --------------------------------------------------------------------------- #
def butterfly_weights(pca: PCAResult, tenors: Sequence[float] = (2.0, 5.0, 10.0)) -> np.ndarray:
    """Weights (w_short, 1, w_long) on the three tenors such that the fly has zero
    exposure to the level and slope loadings: two equations, two unknowns."""
    idx = [list(pca.tenors).index(t) for t in tenors]
    L = pca.loadings[idx, :2]                    # 3 × 2 (level, slope)
    # w_s·L[0] + L[1] + w_l·L[2] = 0  (for both PCs)
    A = np.column_stack([L[0], L[2]])            # 2 × 2
    b = -L[1]
    ws, wl = np.linalg.solve(A, b)
    return np.array([ws, 1.0, wl])


def fly_series(panel: CurvePanel, weights: np.ndarray, tenors: Sequence[float] = (2.0, 5.0, 10.0)) -> np.ndarray:
    idx = [list(panel.tenors).index(t) for t in tenors]
    return np.asarray(panel.yields)[:, idx] @ weights / BP          # in bp


@dataclass(frozen=True)
class FlySignal:
    weights: tuple[float, float, float]
    fly_bp: np.ndarray = field(repr=False)
    z: np.ndarray = field(repr=False)
    position: np.ndarray = field(repr=False)         # +1 long belly (fly expected to fall), −1, 0
    pnl_bp: np.ndarray = field(repr=False)           # per session, position × −Δfly
    half_life: float = 0.0
    adf_p: float = 1.0
    n_trades: int = 0
    hit_rate: float = 0.0
    mean_pnl_per_trade_bp: float = 0.0


def butterfly_signal(panel: CurvePanel, *, window: int = 250, entry: float = 2.0, exit: float = 0.0,
                     max_hold: int = 60, pca_window: int = 250, pca_step: int = 21,
                     tenors: Sequence[float] = (2.0, 5.0, 10.0)) -> FlySignal:
    """Rolling PCA (re-estimated every `pca_step` sessions on the trailing
    `pca_window`), fly = w·y in bp, z over `window`, long the belly when z < −entry
    (belly cheap), short when z > entry, exit at `exit` or after `max_hold`."""
    from core.quant.strategies import adf_pvalue, half_life
    T = len(panel)
    if T < pca_window + window + 10:
        raise FICCError(f"butterfly needs ≥ {pca_window + window + 10} curve dates, got {T}")
    Y = np.asarray(panel.yields)
    fly = np.full(T, np.nan)
    w_last = None
    for t in range(pca_window, T):
        if w_last is None or (t - pca_window) % pca_step == 0:
            sub = CurvePanel(source=panel.source, dates=panel.dates[t - pca_window:t], tenors=panel.tenors,
                             yields=Y[t - pca_window:t])
            w_last = butterfly_weights(curve_pca(sub), tenors)
        idx = [list(panel.tenors).index(x) for x in tenors]
        fly[t] = Y[t, idx] @ w_last / BP
    z = np.full(T, np.nan)
    pos = np.zeros(T)
    pnl = np.zeros(T)
    state, opened = 0, -1
    trades, wins, per_trade = 0, 0, []
    entry_level = 0.0
    for t in range(pca_window + window, T):
        win = fly[t - window:t]
        mu, sd = float(np.nanmean(win)), float(np.nanstd(win, ddof=1))
        z[t] = (fly[t] - mu) / sd if sd > 0 else 0.0
        if state != 0:
            pnl[t] = state * -(fly[t] - fly[t - 1])
        if state == 0 and z[t] < -entry:
            state, opened, entry_level = 1, t, fly[t]
        elif state == 0 and z[t] > entry:
            state, opened, entry_level = -1, t, fly[t]
        elif state != 0 and ((state == 1 and z[t] >= -exit) or (state == -1 and z[t] <= exit) or t - opened >= max_hold):
            gain = state * -(fly[t] - entry_level)
            trades += 1; wins += gain > 0; per_trade.append(gain)
            state = 0
        pos[t] = state
    valid = ~np.isnan(fly)
    return FlySignal(weights=tuple(float(x) for x in w_last), fly_bp=fly, z=z, position=pos, pnl_bp=pnl,
                     half_life=half_life(fly[valid]), adf_p=adf_pvalue(fly[valid]), n_trades=trades,
                     hit_rate=(wins / trades if trades else float("nan")),
                     mean_pnl_per_trade_bp=(float(np.mean(per_trade)) if per_trade else float("nan")))


# --------------------------------------------------------------------------- #
# Bond carry (Koijen et al. 2018)
# --------------------------------------------------------------------------- #
def bond_carry(y_long: np.ndarray, r_short: np.ndarray, y_roll: np.ndarray, *, d_mod: float) -> np.ndarray:
    """carry = (y_T − r_short) + D_mod·(y_T − y_{T−h}): the yield pickup over
    funding plus the roll-down over the horizon, all annualised decimals."""
    return (np.asarray(y_long) - np.asarray(r_short)) + d_mod * (np.asarray(y_long) - np.asarray(y_roll))


def carry_timing_positions(carry: np.ndarray, *, window: int = 60, step: int = 21) -> np.ndarray:
    """Long when carry exceeds its trailing `window`-observation mean (monthly
    sampling handled by `step` in sessions); 0 otherwise. Causal."""
    c = np.asarray(carry, dtype=float)
    pos = np.zeros(c.size)
    for t in range(step, c.size, step):
        hist = c[max(0, t - window * step):t:step]
        if hist.size >= 12:
            pos[t:t + step] = 1.0 if c[t] > np.nanmean(hist) else 0.0
    return pos


# --------------------------------------------------------------------------- #
# KRW curve from KIS
# --------------------------------------------------------------------------- #
def krw_curve_panel(*, days: int = 504) -> CurvePanel:
    """CD 91d and KTB 1/3/5/10/20/30y par yields from the KIS chart endpoint,
    intersected on shared dates, percent → decimal."""
    from data.kis_markets import KISMarkets, KRW_CURVE_TENORS
    km = KISMarkets()
    series = {}
    for code, tenor in KRW_CURVE_TENORS:
        b = km.krw_yield_daily(code, days=days)
        series[tenor] = dict(zip(b.dates, b.close))
    common = sorted(set.intersection(*(set(s) for s in series.values())))
    if len(common) < 30:
        raise FICCError(f"only {len(common)} shared dates across the KRW yield series")
    tenors = tuple(t for _, t in KRW_CURVE_TENORS)
    Y = np.array([[series[t][d] / 100.0 for t in tenors] for d in common])
    return CurvePanel(source="KIS", dates=tuple(common), tenors=tenors, yields=Y,
                      note="KRW par grid: CD 91d + KTB 1/3/5/10/20/30y (KIS chart endpoint, percent → decimal)")


# --------------------------------------------------------------------------- #
# Self-check (synthetic NS panel)
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    from core.ficc.common import UST_TENORS
    rng = np.random.default_rng(2)
    T = 252 * 25
    b = np.array([0.05, -0.02, 0.01])
    rows, dates = [], []
    d0 = np.datetime64("2001-01-01")
    for i in range(T):
        # factors mean-revert with a half-life of about 70 sessions, as Diebold–Li's do at monthly frequency
        b = b + rng.normal(0, [0.0002, 0.0003, 0.0004]) - 0.01 * (b - np.array([0.05, -0.02, 0.01]))
        rows.append(nelson_siegel(np.array(UST_TENORS), b[0], b[1], b[2], 1.0 / DL_LAMBDA_YEARLY) + rng.normal(0, 0.0001, len(UST_TENORS)))
        dates.append(str(d0 + np.timedelta64(int(i * 365.25 / 252), "D")))
    panel = CurvePanel(source="SYNTHETIC", dates=tuple(dates), tenors=UST_TENORS, yields=np.asarray(rows))
    betas, rmse = dns_factors(panel)
    assert betas.shape == (T, 3) and rmse.mean() < 3 * BP
    assert abs(betas[-1, 0] - b[0]) < 0.002 and abs(betas[-1, 1] - b[1]) < 0.003
    st = dns_study(panel, horizons=(6, 12), first_forecast_month=120)
    assert st.n_forecasts[12] > 100 and st.rmse_dns[12].shape == (len(UST_TENORS),)
    # mean-reverting factors: DNS beats the random walk at 12 months on most tenors
    assert st.beats_rw(12) >= 6, (st.rmse_dns[12], st.rmse_rw[12])
    assert np.all(st.ar_coefficients < 1.0) and st.latest_forecast[6].shape == (len(UST_TENORS),)
    pca = curve_pca(panel)
    w = butterfly_weights(pca)
    idx = [list(panel.tenors).index(t) for t in (2.0, 5.0, 10.0)]
    assert np.allclose(pca.loadings[idx, 0] @ w, 0.0, atol=1e-10) and np.allclose(pca.loadings[idx, 1] @ w, 0.0, atol=1e-10)
    assert w[1] == 1.0 and w[0] < 0 and w[2] < 0, w
    fs = butterfly_signal(panel, window=250, entry=2.0)
    assert fs.n_trades > 5 and math.isfinite(fs.half_life) and fs.adf_p < 0.05, (fs.n_trades, fs.half_life, fs.adf_p)
    assert set(np.unique(fs.position)) <= {-1.0, 0.0, 1.0}
    c = bond_carry(np.array([0.045, 0.046]), np.array([0.03, 0.03]), np.array([0.044, 0.045]), d_mod=8.0)
    assert np.allclose(c, [0.015 + 8 * 0.001, 0.016 + 8 * 0.001])
    pos = carry_timing_positions(np.sin(np.arange(2000) / 100) + 1.0)
    assert set(np.unique(pos)) <= {0.0, 1.0} and 0.2 < pos[500:].mean() < 0.8
    print("ok")
