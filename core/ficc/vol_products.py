"""VIX term structure, the hedged roll-down trade and the VIX-ETP drift monitor.

Keyless inputs from Yahoo: `^VIX` (spot), `^VIX3M` (the 93-day index, a term-
structure proxy for the second/third future), `VXX` (long 30-day constant-
maturity VX exposure), `SVXY` (−0.5× since 2018), `SPY`/`ES=F` for the hedge;
KIS `ovf_daily("VXV26", "CBOE")` for the live dated contract.

  term_structure       basis b = VIX3M/VIX − 1 (contango when positive)
  roll_down_backtest   Simon & Campasano (2014, J. Derivatives 21(3)): short the
                       front future when the basis is above a threshold, hedged
                       with an equity-index position sized by a rolling beta;
                       here the short VX1 leg is expressed as short VXX (which
                       rolls VX1 → VX2 daily), so the P&L includes the ETP's own
                       roll, which is the point of the trade
  etp_drift_monitor    Eraker & Wu (2017, JFE 125): the expected monthly drift
                       of a long VIX ETP ≈ −(roll yield) ≈ −b/2 per month for a
                       30-day constant-maturity position between VX1 and VX2;
                       regression of realised VXX returns on ΔVIX and Δbasis

User-material refs: the user's paper §5.1 (variance risk premium, p. 11) and
§5.5 (term structure, p. 13); 재무경제학 Ch. 6 (Sharpe ratio); 계량2 Ch. 1
(Ljung–Box on the strategy residuals).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional, Sequence

import numpy as np

from core.ficc.common import BP, TRADING_DAYS, FICCError
from core.quant.strategies import simulate, summary


def term_structure(vix: np.ndarray, vix3m: np.ndarray) -> np.ndarray:
    """b_t = VIX3M/VIX − 1: positive = contango."""
    v, v3 = np.asarray(vix, dtype=float), np.asarray(vix3m, dtype=float)
    if v.shape != v3.shape:
        raise ValueError("vix and vix3m must align")
    return v3 / v - 1.0


def rolling_beta(y: np.ndarray, x: np.ndarray, window: int = 60) -> np.ndarray:
    """β of y on x over the trailing window (NaN until filled); both daily returns."""
    y, x = np.asarray(y, dtype=float), np.asarray(x, dtype=float)
    out = np.full(y.size, np.nan)
    for t in range(window, y.size):
        xs, ys = x[t - window:t], y[t - window:t]
        vx = np.var(xs, ddof=1)
        out[t] = np.cov(xs, ys, ddof=1)[0, 1] / vx if vx > 0 else np.nan
    return out


@dataclass(frozen=True)
class RollDownResult:
    dates: tuple[str, ...]
    weights: np.ndarray = field(repr=False)          # T × 2 on [VXX, hedge]
    pnl: np.ndarray = field(repr=False)              # daily net
    pnl_unhedged: np.ndarray = field(repr=False)
    basis: np.ndarray = field(repr=False)
    stats: dict = field(default_factory=dict)
    stats_unhedged: dict = field(default_factory=dict)
    days_short: int = 0
    n_entries: int = 0
    worst_day: float = 0.0
    note: str = ""


def roll_down_positions(basis: np.ndarray, beta: np.ndarray, *, threshold: float = 0.05, exit: float = 0.02,
                        hedge: bool = True, size: float = 1.0, beta_step: float = 0.25) -> np.ndarray:
    """Weights on [VXX, hedge]: −size in VXX while the basis exceeds `threshold`
    until it falls below `exit`; the hedge leg is +size·β (β of VXX on the
    hedge index is negative, so the hedge is a short index position). The
    hedge weight is only reset when β has moved by more than `beta_step`, so
    the daily re-estimation does not turn into daily turnover."""
    T = basis.size
    W = np.zeros((T, 2))
    on = False
    b_used = np.nan
    for t in range(T):
        if not on and basis[t] > threshold and np.isfinite(beta[t]):
            on = True
            b_used = beta[t]
        elif on and basis[t] < exit:
            on = False
        if on:
            if np.isfinite(beta[t]) and abs(beta[t] - b_used) > beta_step:
                b_used = beta[t]
            W[t, 0] = -size
            W[t, 1] = size * b_used if hedge and np.isfinite(b_used) else 0.0
    return W


def roll_down_backtest(dates: Sequence[str], vix: np.ndarray, vix3m: np.ndarray, vxx: np.ndarray,
                       hedge_px: np.ndarray, *, threshold: float = 0.05, exit: float = 0.02,
                       beta_window: int = 60, cost_bps: float = 10.0, size: float = 1.0) -> RollDownResult:
    """Short VXX (a rolling long-VX1/VX2 position) hedged with the equity index
    while the term structure is in contango beyond `threshold`. Costs per
    unit turnover. The unhedged variant is reported alongside: Simon &
    Campasano's claim is that the hedged version has the smaller drawdown."""
    n = len(dates)
    b = term_structure(vix, vix3m)
    P = np.column_stack([np.asarray(vxx, dtype=float), np.asarray(hedge_px, dtype=float)])
    r = np.diff(np.log(P), axis=0)
    beta = np.concatenate([[np.nan], rolling_beta(r[:, 0], r[:, 1], beta_window)])
    W = roll_down_positions(b, beta, threshold=threshold, exit=exit, hedge=True, size=size)
    Wu = roll_down_positions(b, beta, threshold=threshold, exit=exit, hedge=False, size=size)
    pnl, _ = simulate(P, W, cost_bps=cost_bps)
    pnl_u, _ = simulate(P, Wu, cost_bps=cost_bps)
    entries = int(np.sum((W[1:, 0] < 0) & (W[:-1, 0] == 0)))
    return RollDownResult(dates=tuple(dates), weights=W, pnl=pnl, pnl_unhedged=pnl_u, basis=b,
                          stats=summary(pnl), stats_unhedged=summary(pnl_u),
                          days_short=int(np.sum(W[:, 0] < 0)), n_entries=entries,
                          worst_day=float(np.min(pnl)) if pnl.size else 0.0,
                          note=(f"short VXX when VIX3M/VIX − 1 > {threshold:.0%}, exit below {exit:.0%}; "
                                f"hedge β over {beta_window} sessions; {cost_bps:.0f} bp per unit turnover"))


def etp_drift_monitor(vix: np.ndarray, vix3m: np.ndarray, vxx: np.ndarray) -> dict:
    """Expected monthly drift of a long 30-day VIX ETP from the term structure,
    −b/2 per month (a 30-day position rolls halfway up a linear VX1→VX2 curve
    whose 60-day slope is proxied by VIX3M − VIX), against the realised VXX
    drift; plus the regression of daily VXX returns on ΔVIX/VIX and Δb."""
    v, v3, x = (np.asarray(a, dtype=float) for a in (vix, vix3m, vxx))
    b = v3 / v - 1.0
    rv = np.diff(np.log(v))
    rb = np.diff(b)
    rx = np.diff(np.log(x))
    X = np.column_stack([np.ones(rv.size), rv, rb])
    beta, *_ = np.linalg.lstsq(X, rx, rcond=None)
    fitted = X @ beta
    r2 = 1.0 - float(np.sum((rx - fitted) ** 2) / np.sum((rx - rx.mean()) ** 2))
    n_months = rx.size / 21.0
    return {"basis_last": float(b[-1]), "basis_mean": float(np.nanmean(b)),
            "expected_monthly_drift": float(-b[-1] / 2.0),
            "realised_monthly_drift": float(np.mean(rx) * 21.0),
            "beta_vix": float(beta[1]), "beta_basis": float(beta[2]), "alpha_daily": float(beta[0]),
            "r2": r2, "n_sessions": int(rx.size), "months": n_months}


# --------------------------------------------------------------------------- #
# Self-check (synthetic)
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    rng = np.random.default_rng(9)
    T = 1500
    # A VIX that mean-reverts around 18 with occasional spikes, contango most of the time.
    v = np.empty(T); v[0] = 18.0
    for t in range(1, T):
        v[t] = max(9.0, v[t - 1] + 0.05 * (18 - v[t - 1]) + rng.normal(0, 0.8) + (10.0 if rng.random() < 0.02 else 0.0))
    # contango of ~5 % at VIX 18 that flips to backwardation above ~23 (the empirical shape)
    v3 = v * (1.0 + np.clip(0.05 - 0.01 * (v - 18), -0.15, 0.2))
    b = term_structure(v, v3)
    assert b.shape == v.shape and 0.4 < np.mean(b > 0.02) < 0.95
    # VXX loses the roll each day in contango and jumps with VIX; SPY drifts up and anti-correlates.
    spy = 300 * np.exp(np.cumsum(rng.normal(0.0003, 0.01, T)))
    r_spy = np.diff(np.log(spy))
    r_vxx = -0.6 * r_spy * 4 + np.diff(np.log(v)) * 0.5 - b[1:] / 42.0 + rng.normal(0, 0.01, T - 1)
    vxx = 100 * np.exp(np.concatenate([[0.0], np.cumsum(r_vxx)]))
    dates = [f"{2020 + i // 252}-{(i // 21) % 12 + 1:02d}-{i % 21 + 1:02d}" for i in range(T)]
    res = roll_down_backtest(dates, v, v3, vxx, spy, threshold=0.04, exit=0.0)
    assert 200 < res.days_short < T - 100 and res.n_entries > 3, (res.days_short, res.n_entries)
    assert np.all(np.isfinite(res.pnl)) and res.pnl.size == T - 1 and res.stats["sessions"] == T - 1
    # the hedge leg only resets when β moves by more than beta_step: far fewer changes than sessions
    changes = int(np.sum(np.abs(np.diff(res.weights[:, 1])) > 1e-12))
    assert changes < res.days_short / 3, (changes, res.days_short)
    W_no = roll_down_positions(term_structure(v, v3), np.full(T, -2.0), threshold=0.04, exit=0.0, hedge=False)
    assert np.all(W_no[:, 1] == 0.0) and np.all(W_no[:, 0] <= 0.0)
    beta = rolling_beta(r_vxx, r_spy, 60)
    assert np.nanmean(beta) < -1.0
    mon = etp_drift_monitor(v, v3, vxx)
    assert abs(mon["expected_monthly_drift"] + b[-1] / 2.0) < 1e-12 and mon["realised_monthly_drift"] < 0
    assert mon["r2"] > 0.3 and mon["beta_vix"] > 0, (mon["r2"], mon["beta_vix"])
    print("ok")
