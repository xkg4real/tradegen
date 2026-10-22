"""Vectorized backtests of simple rule strategies against a price history.

Three built-in strategies:

  * **ma_cross** — long when the fast SMA is above the slow SMA, flat otherwise.
  * **momentum** — long when the N-day return is positive, flat otherwise.
  * **rsi_revert** — long after RSI dips below the oversold line, exit when it
    recovers past the midline. Mean reversion, the opposite temperament of the
    other two.

Execution honesty, in order of how often naive backtests cheat on it:

  1. Signals computed on close *t* earn the return from *t+1* — the position
     array is shifted one bar before it meets the returns.
  2. Every position change pays `cost_bps` of the traded notional.
  3. The benchmark is buy-and-hold of the same series over the same window,
     reported side by side. A strategy that loses to its own underlying has
     no business existing, and the report should make that impossible to miss.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from core.quant.history import History, TRADING_DAYS
from core.quant.signals import sma

STRATEGIES = ("ma_cross", "momentum", "rsi_revert")


@dataclass(frozen=True)
class BacktestResult:
    symbol: str
    strategy: str
    params: dict
    sessions: int
    n_trades: int
    cost_bps: float
    # Curves (aligned to dates)
    dates: tuple[str, ...] = field(repr=False, default=())
    equity: np.ndarray = field(repr=False, default=None)       # strategy, starts at 1.0
    bench_equity: np.ndarray = field(repr=False, default=None) # buy & hold, starts at 1.0
    position: np.ndarray = field(repr=False, default=None)     # 0/1 per bar
    # Stats
    total_return: float = 0.0
    bench_return: float = 0.0
    ann_return: float = 0.0
    ann_vol: float = 0.0
    sharpe: float = 0.0
    max_drawdown: float = 0.0
    bench_max_drawdown: float = 0.0
    exposure: float = 0.0             # fraction of bars in the market
    win_rate: float | None = None     # per-trade, None when no closed trades

    @property
    def beat_benchmark(self) -> bool:
        return self.total_return > self.bench_return


def _rsi_series(px: np.ndarray, n: int = 14) -> np.ndarray:
    out = np.full(px.size, 50.0)
    if px.size < n + 1:
        return out
    delta = np.diff(px)
    gains = np.clip(delta, 0, None)
    losses = np.clip(-delta, 0, None)
    avg_gain = gains[:n].mean()
    avg_loss = losses[:n].mean()
    for i in range(n, delta.size):
        avg_gain = (avg_gain * (n - 1) + gains[i]) / n
        avg_loss = (avg_loss * (n - 1) + losses[i]) / n
        out[i + 1] = 100.0 if avg_loss == 0 else 100.0 - 100.0 / (1.0 + avg_gain / avg_loss)
    return out


def _positions(px: np.ndarray, strategy: str, params: dict) -> np.ndarray:
    if strategy == "ma_cross":
        fast = int(params.get("fast", 20))
        slow = int(params.get("slow", 50))
        if fast >= slow:
            raise ValueError("ma_cross needs fast < slow.")
        f, s = sma(px, fast), sma(px, slow)
        pos = np.where(np.isnan(f) | np.isnan(s), 0.0, (f > s).astype(float))
        return pos
    if strategy == "momentum":
        lb = int(params.get("lookback", 63))
        pos = np.zeros(px.size)
        pos[lb:] = (px[lb:] > px[:-lb]).astype(float)
        return pos
    if strategy == "rsi_revert":
        buy_below = float(params.get("buy_below", 30))
        exit_above = float(params.get("exit_above", 55))
        r = _rsi_series(px, int(params.get("period", 14)))
        pos = np.zeros(px.size)
        holding = 0.0
        for i in range(1, px.size):
            if holding == 0.0 and r[i] < buy_below:
                holding = 1.0
            elif holding == 1.0 and r[i] > exit_above:
                holding = 0.0
            pos[i] = holding
        return pos
    raise ValueError(f"Unknown strategy {strategy!r}. One of {STRATEGIES}.")


def run_backtest(history: History, *, strategy: str = "ma_cross",
                 params: dict | None = None, cost_bps: float = 10.0) -> BacktestResult:
    params = dict(params or {})
    px = history.prices()
    if px.size < 60:
        raise ValueError("Need at least 60 sessions to backtest.")
    pos = _positions(px, strategy, params)

    daily = px[1:] / px[:-1] - 1.0                     # simple returns, length T-1
    held = pos[:-1]                                    # decide on close t, earn t+1
    trades = np.abs(np.diff(np.concatenate([[0.0], pos])))
    costs = trades[:-1] * (cost_bps / 10_000.0)        # charged when position changes
    strat_daily = held * daily - costs

    equity = np.concatenate([[1.0], np.cumprod(1.0 + strat_daily)])
    bench = np.concatenate([[1.0], np.cumprod(1.0 + daily)])

    def mdd(curve: np.ndarray) -> float:
        peak = np.maximum.accumulate(curve)
        return float(np.min(curve / peak - 1.0))

    n_years = max(strat_daily.size / TRADING_DAYS, 1e-9)
    total = float(equity[-1] - 1.0)
    ann_ret = float((equity[-1]) ** (1.0 / n_years) - 1.0) if equity[-1] > 0 else -1.0
    vol = float(np.std(strat_daily, ddof=1)) * np.sqrt(TRADING_DAYS)
    sharpe = (float(np.mean(strat_daily)) * TRADING_DAYS) / vol if vol > 0 else 0.0

    # Per-trade wins: segment the position array into holding periods.
    wins, closed = 0, 0
    entry = None
    for i in range(1, pos.size):
        if pos[i] == 1.0 and pos[i - 1] == 0.0:
            entry = px[i]
        elif pos[i] == 0.0 and pos[i - 1] == 1.0 and entry is not None:
            closed += 1
            if px[i] > entry:
                wins += 1
            entry = None
    win_rate = wins / closed if closed else None

    return BacktestResult(
        symbol=history.symbol, strategy=strategy, params=params,
        sessions=px.size, n_trades=int(trades.sum() // 1), cost_bps=cost_bps,
        dates=history.dates, equity=equity, bench_equity=bench, position=pos,
        total_return=total, bench_return=float(bench[-1] - 1.0),
        ann_return=ann_ret, ann_vol=vol, sharpe=sharpe,
        max_drawdown=mdd(equity), bench_max_drawdown=mdd(bench),
        exposure=float(np.mean(held)), win_rate=win_rate,
    )
