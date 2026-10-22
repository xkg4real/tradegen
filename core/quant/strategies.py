"""Daily strategy engine and the strategy families the validation study runs.

Every strategy is a function `prices (T×N) → weights (T×N)` where the weight
row at t is decided from prices up to and including t and HELD over t → t+1.
`simulate` turns weights into a costed daily P&L; `pnl_matrix` runs a grid of
configurations and returns the T−1 × G matrix `core.quant.validate.walk_forward`
consumes. No strategy here looks ahead: signals use `prices[:t+1]` only, and
parameter estimates (hedge ratios, spreads, volatilities) are rolled.

Families (source in each docstring; the research notes carry the full record):
  trend_switch      Faber 10-month SMA / MOP 12-month sign, per sleeve, cash otherwise
  vol_target        Moreira–Muir capped w = min(cap, σ*/σ̂), 21-session steps, ±band
  xs_momentum       Jegadeesh–Titman 12-1 cross-sectional ranks, top third
  tsmom             Moskowitz–Ooi–Pedersen sign(12m) × (40 % / σ̂) per instrument
  pairs             Gatev–Goetzmann–Rouwenhorst / Engle–Granger spread with a frozen
                    formation-window hedge ratio, z-score entry/exit, OU half-life
  crypto_trend      short-horizon sign votes + price/MA ratios, long/flat with hysteresis
  risk_parity       the app's equal-risk-contribution solver on a rolling covariance

Costs are per unit of turnover (cost_bps × |Δw|), charged on the session the
weight changes, so a 5 bp round trip on a KRX ETF is `cost_bps=5` and a full
switch in and out costs 10 bp. Cash earns `cash_daily` (a rate/252 array or 0).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable, Optional, Sequence

import numpy as np

from core.quant.history import History, TRADING_DAYS

BP = 1e-4


# --------------------------------------------------------------------------- #
# Panel and simulator
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Panel:
    dates: tuple[str, ...]
    symbols: tuple[str, ...]
    prices: np.ndarray = field(repr=False)        # T × N, aligned on shared dates
    sources: tuple[str, ...] = ()

    def __len__(self) -> int:
        return len(self.dates)


def align_panel(histories: Sequence[History]) -> Panel:
    """Intersect on shared dates (the FX carry page's convention)."""
    if not histories:
        raise ValueError("no histories")
    common = set(histories[0].dates)
    for h in histories[1:]:
        common &= set(h.dates)
    dates = sorted(common)
    if len(dates) < 60:
        raise ValueError(f"only {len(dates)} shared sessions across {[h.symbol for h in histories]}")
    cols = []
    for h in histories:
        lookup = dict(zip(h.dates, h.closes))
        cols.append(np.array([lookup[d] for d in dates], dtype=float))
    return Panel(dates=tuple(dates), symbols=tuple(h.symbol for h in histories),
                 prices=np.column_stack(cols), sources=tuple(h.source for h in histories))


def simulate(prices: np.ndarray, weights: np.ndarray, *, cost_bps: float = 5.0,
             cash_daily: np.ndarray | float = 0.0) -> tuple[np.ndarray, np.ndarray]:
    """Daily net P&L (T−1,) and turnover (T−1,) of a weight path. Weight row t
    is held over t → t+1; turnover |Δw| at t is charged on that session; the
    unallocated fraction of a long-only book earns `cash_daily`."""
    P = np.asarray(prices, dtype=float)
    W = np.asarray(weights, dtype=float)
    if P.ndim == 1:
        P = P[:, None]
    if W.ndim == 1:
        W = W[:, None]
    if P.shape != W.shape:
        raise ValueError(f"prices {P.shape} and weights {W.shape} differ")
    ret = P[1:] / P[:-1] - 1.0
    held = W[:-1]
    gross_long = np.clip(held, 0, None).sum(axis=1)
    cash_w = np.where(held.min(axis=1) >= 0, 1.0 - gross_long, 0.0)
    cash = np.broadcast_to(np.asarray(cash_daily, dtype=float), (P.shape[0],))[:-1] if np.ndim(cash_daily) else cash_daily
    gross = (held * ret).sum(axis=1) + cash_w * cash
    turnover = np.abs(np.diff(np.vstack([np.zeros((1, W.shape[1])), W]), axis=0)).sum(axis=1)   # T
    pnl = gross - turnover[:-1] * cost_bps * BP
    return pnl, turnover[:-1]


def equity_curve(pnl: np.ndarray) -> np.ndarray:
    return np.concatenate([[1.0], np.cumprod(1.0 + np.asarray(pnl))])


def summary(pnl: np.ndarray) -> dict:
    p = np.asarray(pnl, dtype=float)
    eq = equity_curve(p)
    n = p.size
    vol = float(np.std(p, ddof=1)) * math.sqrt(TRADING_DAYS) if n > 1 else 0.0
    return {"total_return": float(eq[-1] - 1.0),
            "ann_return": float(eq[-1] ** (TRADING_DAYS / max(n, 1)) - 1.0) if eq[-1] > 0 else -1.0,
            "ann_vol": vol, "sharpe": float(np.mean(p) * TRADING_DAYS / vol) if vol > 0 else 0.0,
            "max_drawdown": float(np.min(eq / np.maximum.accumulate(eq) - 1.0)), "sessions": n}


# --------------------------------------------------------------------------- #
# Rolling helpers (all causal)
# --------------------------------------------------------------------------- #
def _sma(x: np.ndarray, n: int) -> np.ndarray:
    out = np.full_like(x, np.nan, dtype=float)
    if x.shape[0] >= n:
        c = np.cumsum(np.vstack([np.zeros((1,) + x.shape[1:]), x]), axis=0)
        out[n - 1:] = (c[n:] - c[:-n]) / n
    return out


def realised_vol(prices: np.ndarray, window: int = 22) -> np.ndarray:
    """Annualised trailing realised vol of log returns, aligned with prices (NaN early)."""
    P = np.asarray(prices, dtype=float)
    r = np.diff(np.log(P), axis=0)
    out = np.full(P.shape, np.nan)
    for t in range(window, P.shape[0]):
        out[t] = np.std(r[t - window:t], axis=0, ddof=1) * math.sqrt(TRADING_DAYS)
    return out


def ewma_vol(prices: np.ndarray, com: float = 60.0) -> np.ndarray:
    """MOP (2012) eq. (1): σ̂² = 261·Σ(1−δ)δ^i (r − r̄)², δ/(1−δ) = com (centre of mass)."""
    P = np.asarray(prices, dtype=float)
    r = np.diff(np.log(P), axis=0)
    delta = com / (1.0 + com)
    var = np.full(P.shape, np.nan)
    v = np.var(r[:22], axis=0) if r.shape[0] >= 22 else np.var(r, axis=0)
    m = np.mean(r[:22], axis=0) if r.shape[0] >= 22 else np.mean(r, axis=0)
    for t in range(1, P.shape[0]):
        x = r[t - 1]
        m = delta * m + (1 - delta) * x
        v = delta * v + (1 - delta) * (x - m) ** 2
        if t >= 22:
            var[t] = v * 261.0
    return np.sqrt(var)


def _rebalance_days(T: int, step: int, start: int) -> np.ndarray:
    return np.arange(start, T, step)


def _hold(weights_at: dict[int, np.ndarray], T: int, N: int) -> np.ndarray:
    W = np.zeros((T, N))
    keys = sorted(weights_at)
    for i, t in enumerate(keys):
        end = keys[i + 1] if i + 1 < len(keys) else T
        W[t:end] = weights_at[t]
    return W


# --------------------------------------------------------------------------- #
# Families
# --------------------------------------------------------------------------- #
def trend_switch(prices: np.ndarray, *, rule: str = "sma", lookback: int = 210, step: int = 21,
                 cash_rate_daily: np.ndarray | float = 0.0, vol_cap: Optional[float] = None) -> np.ndarray:
    """Faber (2007): hold sleeve i when P > SMA(lookback sessions ≈ 10 months);
    MOP (2012) sign rule (`rule="tsmom"`): hold when the trailing `lookback`
    excess return is positive. Evaluated every `step` sessions, 1/N per sleeve,
    the rest in cash. `vol_cap` = σ* for the optional min(1, σ*/σ̂) sizing."""
    P = np.asarray(prices, dtype=float)
    if P.ndim == 1:
        P = P[:, None]
    T, N = P.shape
    sma = _sma(P, lookback) if rule == "sma" else None
    rf = np.broadcast_to(np.asarray(cash_rate_daily, dtype=float), (T,))
    vol = realised_vol(P, 22) if vol_cap else None
    at: dict[int, np.ndarray] = {}
    for t in _rebalance_days(T, step, lookback):
        if rule == "sma":
            on = P[t] > sma[t]
        else:
            ex = P[t] / P[t - lookback] - 1.0 - float(np.sum(rf[t - lookback:t]))
            on = ex > 0
        w = on.astype(float) / N
        if vol_cap:
            scale = np.where(np.isfinite(vol[t]) & (vol[t] > 0), np.minimum(1.0, vol_cap / np.where(vol[t] > 0, vol[t], 1)), 1.0)
            w = w * scale
        at[t] = w
    return _hold(at, T, N)


def vol_target(prices: np.ndarray, *, target: float, window: int = 22, step: int = 21, cap: float = 1.0,
               band: float = 0.10) -> np.ndarray:
    """Moreira–Muir (2017) in the real-time, capped form Cederburg et al. (2020)
    evaluate: w = min(cap, σ*/σ̂_t) with σ̂ the trailing realised vol, updated
    every `step` sessions and only when it moves by more than `band`."""
    P = np.asarray(prices, dtype=float)
    if P.ndim == 1:
        P = P[:, None]
    T, N = P.shape
    vol = realised_vol(P, window)
    at: dict[int, np.ndarray] = {}
    last = np.full(N, np.nan)
    for t in _rebalance_days(T, step, window + 1):
        v = vol[t]
        w = np.where(np.isfinite(v) & (v > 0), np.minimum(cap, target / np.where(v > 0, v, 1)), 0.0)
        keep = np.isfinite(last) & (np.abs(w - last) <= band * np.maximum(last, 1e-9))
        w = np.where(keep, last, w)
        at[t] = w
        last = w
    return _hold(at, T, N)


def xs_momentum(prices: np.ndarray, *, lookback: int = 252, skip: int = 21, top: float = 1 / 3,
                step: int = 21, long_only: bool = True) -> np.ndarray:
    """Jegadeesh–Titman 12-1: rank on the return over [t − lookback, t − skip],
    equal-weight the top `top` fraction (short the bottom fraction when
    `long_only=False`), rebalanced every `step` sessions."""
    P = np.asarray(prices, dtype=float)
    T, N = P.shape
    k = max(1, int(round(N * top)))
    at: dict[int, np.ndarray] = {}
    for t in _rebalance_days(T, step, lookback):
        score = P[t - skip] / P[t - lookback] - 1.0
        order = np.argsort(-score, kind="stable")
        w = np.zeros(N)
        w[order[:k]] = 1.0 / k
        if not long_only:
            w[order[-k:]] -= 1.0 / k
        at[t] = w
    return _hold(at, T, N)


def tsmom(prices: np.ndarray, *, lookback: int = 252, vol_target_ann: float = 0.40, com: float = 60.0,
          step: int = 21, cap: float = 1.0, long_only: bool = False,
          cash_rate_daily: np.ndarray | float = 0.0) -> np.ndarray:
    """MOP (2012) eq. (5): position = sign(r_{t−lookback,t} − rf) × (vol_target / σ̂_{t−1}),
    σ̂ the EWMA with a 60-day centre of mass; per-instrument weight capped at
    `cap` and divided by N so an unlevered sleeve never exceeds 100 %."""
    P = np.asarray(prices, dtype=float)
    if P.ndim == 1:
        P = P[:, None]
    T, N = P.shape
    vol = ewma_vol(P, com)
    rf = np.broadcast_to(np.asarray(cash_rate_daily, dtype=float), (T,))
    at: dict[int, np.ndarray] = {}
    for t in _rebalance_days(T, step, max(lookback, 30)):
        ex = P[t] / P[t - lookback] - 1.0 - float(np.sum(rf[t - lookback:t]))
        sign = np.sign(ex)
        if long_only:
            sign = np.clip(sign, 0, 1)
        size = np.where(np.isfinite(vol[t]) & (vol[t] > 0), vol_target_ann / np.where(vol[t] > 0, vol[t], 1), 0.0)
        at[t] = sign * np.minimum(size, cap) / N
    return _hold(at, T, N)


def half_life(x: np.ndarray) -> float:
    """OU / AR(1) half-life −ln 2 / ln φ from x_t = c + φ x_{t−1} (Berkeley TS
    lecture 6 §1.1; 계량2 §2.1.1). inf when φ ≥ 1."""
    x = np.asarray(x, dtype=float)
    if x.size < 10:
        return math.inf
    X = np.column_stack([np.ones(x.size - 1), x[:-1]])
    phi = float(np.linalg.lstsq(X, x[1:], rcond=None)[0][1])
    return math.inf if phi >= 1.0 or phi <= 0.0 else -math.log(2) / math.log(phi)


def adf_pvalue(x: np.ndarray) -> float:
    try:
        from statsmodels.tsa.stattools import adfuller
        return float(adfuller(np.asarray(x, dtype=float), autolag="AIC")[1])
    except Exception:
        return float("nan")


@dataclass(frozen=True)
class PairsDiagnostics:
    formation_ends: tuple[int, ...]
    hedge_ratios: tuple[float, ...]
    adf_p: tuple[float, ...]
    half_lives: tuple[float, ...]

    @property
    def share_cointegrated(self) -> float:
        p = [x for x in self.adf_p if math.isfinite(x)]
        return float(np.mean([x < 0.05 for x in p])) if p else float("nan")


def pairs(prices: np.ndarray, *, formation: int = 252, trading: int = 126, entry: float = 2.0,
          exit: float = 0.0, max_hold: Optional[int] = None, long_only: bool = False,
          gross: float = 1.0) -> tuple[np.ndarray, PairsDiagnostics]:
    """Two columns (y, x). At each formation end fit ln y = a + b ln x (Engle–
    Granger step 1), record the ADF p-value and the OU half-life of the
    residual, freeze (a, b, μ, σ), and trade the next `trading` sessions on
    z = (resid − μ)/σ: open when |z| > entry, close when z crosses `exit` (or
    after `max_hold`). Long/short is dollar-neutral (±gross/2 per leg, x leg
    scaled by b); `long_only` holds only the cheap leg (retail KRX form)."""
    P = np.asarray(prices, dtype=float)
    if P.ndim != 2 or P.shape[1] != 2:
        raise ValueError("pairs needs exactly two price columns (y, x)")
    T = P.shape[0]
    ly, lx = np.log(P[:, 0]), np.log(P[:, 1])
    W = np.zeros((T, 2))
    ends, hrs, adfs, hls = [], [], [], []
    t0 = formation
    while t0 < T - 1:
        X = np.column_stack([np.ones(formation), lx[t0 - formation:t0]])
        a, b = np.linalg.lstsq(X, ly[t0 - formation:t0], rcond=None)[0]
        resid = ly[t0 - formation:t0] - (a + b * lx[t0 - formation:t0])
        mu, sd = float(resid.mean()), float(resid.std(ddof=1))
        ends.append(t0); hrs.append(float(b)); adfs.append(adf_pvalue(resid)); hls.append(half_life(resid))
        pos, opened = 0, -1
        for t in range(t0, min(t0 + trading, T)):
            z = ((ly[t] - (a + b * lx[t])) - mu) / sd if sd > 0 else 0.0
            if pos == 0 and z > entry:
                pos, opened = -1, t                      # y rich: short y, long x
            elif pos == 0 and z < -entry:
                pos, opened = 1, t                       # y cheap: long y, short x
            elif pos != 0 and ((pos == -1 and z <= exit) or (pos == 1 and z >= -exit)
                               or (max_hold and t - opened >= max_hold)):
                pos = 0
            if pos == 0:
                W[t] = 0.0 if not long_only else np.array([0.5, 0.5]) * gross
            elif long_only:
                W[t] = np.array([1.0, 0.0]) * gross if pos == 1 else np.array([0.0, 1.0]) * gross
            else:
                W[t] = np.array([pos, -pos * b]) * gross / (1.0 + abs(b))
        t0 += trading
    return W, PairsDiagnostics(tuple(ends), tuple(hrs), tuple(adfs), tuple(hls))


def crypto_trend(prices: np.ndarray, *, lookbacks: Sequence[int] = (7, 14, 21, 28),
                 mas: Sequence[int] = (10, 20, 50, 100, 200), hysteresis: float = 0.2) -> np.ndarray:
    """Liu–Tsyvinski (2021) short-horizon momentum + Detzel et al. (2021) price-to-
    MA ratios as sign votes; composite in [−1, 1]; long when it crosses
    +hysteresis, flat when it crosses −hysteresis (long/flat for a spot account)."""
    P = np.asarray(prices, dtype=float)
    if P.ndim == 1:
        P = P[:, None]
    T, N = P.shape
    warm = max(max(lookbacks), max(mas))
    smas = {n: _sma(P, n) for n in mas}
    W = np.zeros((T, N))
    state = np.zeros(N)
    for t in range(warm, T):
        votes = [np.sign(P[t] - P[t - k]) for k in lookbacks] + [np.sign(P[t] - smas[n][t]) for n in mas]
        comp = np.mean(votes, axis=0)
        state = np.where(comp > hysteresis, 1.0, np.where(comp < -hysteresis, 0.0, state))
        W[t] = state
    return W


def risk_parity(prices: np.ndarray, *, window: int = 250, step: int = 63) -> np.ndarray:
    """Equal risk contribution on a rolling covariance (the Portfolio page's solver)."""
    from core.quant.optimize import optimize_portfolio
    from core.quant.risk import BasketStats
    P = np.asarray(prices, dtype=float)
    T, N = P.shape
    r = np.diff(np.log(P), axis=0)
    at: dict[int, np.ndarray] = {}
    for t in _rebalance_days(T, step, window):
        R = r[t - window:t]
        cov = np.cov(R, rowvar=False, ddof=1) * TRADING_DAYS
        sd = np.sqrt(np.clip(np.diag(cov), 1e-12, None))
        stats = BasketStats(symbols=tuple(str(i) for i in range(N)), sessions=window,
                            mean_returns=R.mean(axis=0) * TRADING_DAYS, cov=cov,
                            corr=cov / np.outer(sd, sd), returns=R)
        at[t] = optimize_portfolio(stats, objective="risk_parity").weights
    return _hold(at, T, N)


# --------------------------------------------------------------------------- #
# Grid runner for the gate
# --------------------------------------------------------------------------- #
FAMILIES: dict[str, Callable] = {
    "trend_switch": trend_switch, "vol_target": vol_target, "xs_momentum": xs_momentum,
    "tsmom": tsmom, "crypto_trend": crypto_trend, "risk_parity": risk_parity,
}


def pnl_matrix(prices: np.ndarray, fn: Callable, grid: Sequence[dict], *, cost_bps: float,
               cash_daily: np.ndarray | float = 0.0, stress: float = 2.0) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(pnl T−1×G, pnl at stress×costs, turnover T−1×G) for every configuration."""
    cols, cols_s, turns = [], [], []
    for theta in grid:
        out = fn(prices, **theta)
        W = out[0] if isinstance(out, tuple) else out
        p, tv = simulate(prices, W, cost_bps=cost_bps, cash_daily=cash_daily)
        ps, _ = simulate(prices, W, cost_bps=cost_bps * stress, cash_daily=cash_daily)
        cols.append(p); cols_s.append(ps); turns.append(tv)
    return np.column_stack(cols), np.column_stack(cols_s), np.column_stack(turns)


def grid_from(**axes) -> list[dict]:
    """grid_from(lookback=[126, 210, 252], step=[21]) → every combination."""
    keys = list(axes)
    out: list[dict] = [{}]
    for k in keys:
        out = [dict(g, **{k: v}) for g in out for v in axes[k]]
    return out


# --------------------------------------------------------------------------- #
# Self-check (synthetic, seeded)
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    rng = np.random.default_rng(5)
    T = 1500
    up = 100 * np.exp(np.cumsum(rng.normal(0.0006, 0.01, T)))                  # trending sleeve
    flat = 100 * np.exp(np.cumsum(rng.normal(0.0, 0.01, T)))
    P = np.column_stack([up, flat])
    # simulate: buy-and-hold one asset reproduces its return; costs only hurt.
    W = np.zeros((T, 2)); W[:, 0] = 1.0
    p0, tv = simulate(P, W, cost_bps=0.0)
    assert abs(equity_curve(p0)[-1] - up[-1] / up[0]) < 1e-9 and tv.sum() == 1.0
    p5, _ = simulate(P, W, cost_bps=5.0)
    assert equity_curve(p5)[-1] < equity_curve(p0)[-1]
    # trend switch holds the trending sleeve most of the time and the flat one less.
    Wt = trend_switch(P, rule="sma", lookback=210, step=21)
    assert Wt[210:, 0].mean() > 0.35 and 0 <= Wt.max() <= 0.5 and np.all(Wt[:210] == 0)
    Wm = trend_switch(P, rule="tsmom", lookback=252, step=21)
    assert Wm[252:, 0].mean() > 0.35
    # vol target caps at 1 and scales inversely with realised vol.
    calm = 100 * np.exp(np.cumsum(rng.normal(0, 0.005, T)))
    wild = 100 * np.exp(np.cumsum(rng.normal(0, 0.03, T)))
    Wv = vol_target(np.column_stack([calm, wild]), target=0.16)
    assert Wv[300:, 0].mean() > Wv[300:, 1].mean() and Wv.max() <= 1.0
    # cross-sectional momentum picks the trending name; long-short is dollar-neutral.
    P3 = np.column_stack([up, flat, 100 * np.exp(np.cumsum(rng.normal(-0.0006, 0.01, T)))])
    Wx = xs_momentum(P3, lookback=252, skip=21, top=1 / 3)
    assert Wx[252:, 0].mean() > Wx[252:, 2].mean() and np.allclose(Wx[300].sum(), 1.0)
    Wls = xs_momentum(P3, long_only=False)
    assert abs(Wls[300].sum()) < 1e-12
    # TSMOM: long the up-trend, short the down-trend, sized by vol; long_only clips.
    Wts = tsmom(P3, lookback=252, vol_target_ann=0.40, cap=1.0)
    assert Wts[300:, 0].mean() > 0 > Wts[300:, 2].mean() and np.all(np.abs(Wts) <= 1.0 / 3 + 1e-12)
    assert np.all(tsmom(P3, long_only=True) >= 0)
    # Pairs on a cointegrated synthetic pair: ADF rejects, half-life short, trades happen.
    x = np.exp(np.cumsum(rng.normal(0, 0.01, T)) + 4.6)
    spread = np.zeros(T)
    for t in range(1, T):
        spread[t] = 0.9 * spread[t - 1] + rng.normal(0, 0.01)
    y = x * np.exp(0.1 + spread)
    Wp, diag = pairs(np.column_stack([y, x]), formation=252, trading=126, entry=2.0, exit=0.0)
    assert diag.share_cointegrated > 0.6, diag.adf_p
    assert 3 < np.median(diag.half_lives) < 15, diag.half_lives
    assert np.any(Wp != 0) and np.all(np.abs(Wp).sum(axis=1) <= 1.0 + 1e-9)
    pp, _ = simulate(np.column_stack([y, x]), Wp, cost_bps=5.0)
    assert summary(pp)["sharpe"] > 1.0, summary(pp)
    Wpl, _ = pairs(np.column_stack([y, x]), long_only=True)
    assert np.all(Wpl >= 0)
    # Crypto trend: long/flat only, warm-up flat.
    Wc = crypto_trend(up[:, None])
    assert set(np.unique(Wc)) <= {0.0, 1.0} and Wc[:200].sum() == 0 and Wc[200:].mean() > 0.5
    # Risk parity weights sum to one and overweight the calm asset.
    Wr = risk_parity(np.column_stack([calm, wild]), window=250, step=63)
    assert np.allclose(Wr[300].sum(), 1.0) and Wr[300, 0] > Wr[300, 1]
    # Grid runner shape and the half-life estimator.
    grid = grid_from(lookback=[126, 210], step=[21])
    M, Ms, Tv = pnl_matrix(P, trend_switch, grid, cost_bps=5.0)
    assert M.shape == (T - 1, 2) == Ms.shape == Tv.shape and np.all(Ms.sum(axis=0) <= M.sum(axis=0) + 1e-12)
    ar = np.zeros(2000)
    for t in range(1, 2000):
        ar[t] = 0.8 * ar[t - 1] + rng.normal()
    assert abs(half_life(ar) - (-math.log(2) / math.log(0.8))) < 1.0
    hist = [History("A", "SYNTHETIC", tuple(f"2024-{i // 28 % 12 + 1:02d}-{i % 28 + 1:02d}" for i in range(100)),
                    tuple(float(v) for v in up[:100])),
            History("B", "SYNTHETIC", tuple(f"2024-{i // 28 % 12 + 1:02d}-{i % 28 + 1:02d}" for i in range(100)),
                    tuple(float(v) for v in flat[:100]))]
    assert align_panel(hist).prices.shape == (100, 2)
    print("ok")
