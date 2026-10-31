"""Self-financing, long/cash fractional-share close-only research simulator.

Signal close t executes at close t+lag, and only earns after that close. Each
phase starts with cash and ends with paid liquidation. Cash earns zero. Target
caps apply when rebalancing; held weights can drift between scheduled trades.
This is a return model, not a limit-order/intraday/realized-account simulator.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from research_lab.candidates import Candidate


@dataclass(frozen=True)
class BacktestResult:
    returns: np.ndarray
    metrics: tuple[dict, ...]
    trace: dict[str, np.ndarray] | None


def _finite_or_none(value):
    return float(value) if np.isfinite(value) else None


def simulate_window(close, raw_signals, annual_vol, candidates, indices, *, annualization,
                    cost_per_side, lag=1, capture=False) -> BacktestResult:
    """Simulate all columns together; indices must be a contiguous phase window.

    Net returns include same-close fees after the marked price movement. Exact
    buy/sell equations solve target weight *after* costs, preventing borrowing.
    ``capture`` stores close weights/trades for selected-candidate diagnostics.
    """
    price = np.asarray(close, dtype=np.float64)
    signal = np.asarray(raw_signals)
    vol = np.asarray(annual_vol, dtype=np.float64)
    index = np.asarray(indices, dtype=np.int64)
    candidates = tuple(candidates)
    if (price.ndim != 1 or not len(price) or not np.isfinite(price).all() or np.any(price <= 0)
            or signal.ndim != 2 or signal.shape[0] != len(price) or signal.dtype != np.bool_
            or vol.shape != price.shape or len(index) < 2 or np.any(np.diff(index) != 1)
            or index[0] < lag or index[-1] >= len(price) or not candidates):
        raise ValueError("validated contiguous price/signal phase required")
    if annualization not in (252, 365) or type(lag) is not int or lag not in (1, 2):
        raise ValueError("declared calendar and execution lag required")
    if not np.isfinite(cost_per_side) or not 0 <= cost_per_side < 0.1:
        raise ValueError("bounded nonnegative per-side cost required")
    raw_index = np.array([c.raw_index for c in candidates], dtype=np.int64)
    period = np.array([c.rebalance_bars for c in candidates], dtype=np.int64)
    caps = np.array([c.target_cap for c in candidates], dtype=np.float64)
    targets = np.array([np.nan if c.volatility_target is None else c.volatility_target for c in candidates])
    if (np.any(raw_index < 0) or np.any(raw_index >= signal.shape[1]) or np.any(period < 1)
            or np.any(caps <= 0) or np.any(caps > 1)):
        raise ValueError("invalid candidate execution fields")
    n, count = len(index), len(candidates)
    cash = np.ones(count, dtype=np.float64)
    shares = np.zeros(count, dtype=np.float64)
    previous_equity = np.ones(count, dtype=np.float64)
    returns = np.empty((n, count), dtype=np.float64)
    equity_peak = np.ones(count, dtype=np.float64)
    drawdown = np.zeros(count, dtype=np.float64)
    turnover_sum = np.zeros(count, dtype=np.float64)
    exposure_sum = np.zeros(count, dtype=np.float64)
    roundtrips = np.zeros(count, dtype=np.int64)
    entries = np.zeros(count, dtype=np.int64)
    last_weight = np.zeros(count, dtype=np.float64)
    trace = {k: np.empty((n, count), dtype=np.float64) for k in
             ("gross_return", "position", "held_weight", "turnover", "cost")} if capture else None
    c = float(cost_per_side)
    for step, at in enumerate(index):
        p = price[at]
        asset_value = shares * p
        before = cash + asset_value
        gross = before / previous_equity - 1.0
        exposure_sum += last_weight
        if step == n - 1:
            # Do not create an unearned new position merely to liquidate it.
            target = np.zeros(count)
            scheduled = np.ones(count, dtype=np.bool_)
        else:
            decided = at - lag
            binary = signal[decided, raw_index]
            vol_cap = (np.minimum(caps, np.divide(targets, vol[decided],
                       out=np.zeros(count), where=np.isfinite(targets) & (vol[decided] > 0)))
                       if np.isfinite(vol[decided]) and vol[decided] > 0 else np.zeros(count))
            target = binary * np.where(np.isfinite(targets), vol_cap, caps)
            scheduled = (step % period) == 0
        wanted = target * before - asset_value
        buy = np.where(scheduled & (wanted > 0), wanted / (1.0 + c * target), 0.0)
        sell = np.where(scheduled & (wanted < 0), -wanted / (1.0 - c * target), 0.0)
        traded = buy + sell
        fee = c * traded
        was_held = shares > 0
        cash += sell - buy - fee
        shares += (buy - sell) / p
        flat = scheduled & (target == 0)
        shares[flat] = 0.0
        # Floating arithmetic may leave tiny signed residue after an all-cash
        # trade. It may never permit an economically negative cash balance.
        tolerance = np.maximum(before, 1.0) * 2e-13
        if np.any(cash < -tolerance) or np.any(shares < -tolerance / p):
            raise ArithmeticError("self-financing long/cash invariant violated")
        cash = np.maximum(cash, 0.0)
        shares = np.maximum(shares, 0.0)
        held = shares > 0
        entries += ~was_held & held
        roundtrips += was_held & ~held
        after = cash + shares * p
        if not np.isfinite(after).all() or np.any(after <= 0):
            raise ArithmeticError("nonpositive or nonfinite model equity")
        net = after / previous_equity - 1.0
        returns[step] = net
        turnover = traded / before
        turnover_sum += turnover
        weight = shares * p / after
        if np.any(weight > 1 + 1e-12):
            raise ArithmeticError("model leverage is forbidden")
        equity_peak = np.maximum(equity_peak, after)
        drawdown = np.minimum(drawdown, after / equity_peak - 1.0)
        if trace is not None:
            trace["gross_return"][step] = gross
            trace["position"][step] = weight
            trace["held_weight"][step] = last_weight
            trace["turnover"][step] = turnover
            trace["cost"][step] = fee / before
        last_weight = weight
        previous_equity = after
    mean = returns.mean(axis=0)
    std = returns.std(axis=0, ddof=1)
    sharpe = np.divide(mean * np.sqrt(annualization), std,
                       out=np.full(count, np.nan), where=std > 0)
    cagr = np.expm1(np.log(previous_equity) * annualization / n)
    metrics = tuple(dict(n=n, annualization=annualization, mean_daily=float(mean[i]),
                         annualized_mean=float(mean[i] * annualization), cagr=float(cagr[i]),
                         annual_vol=float(std[i] * np.sqrt(annualization)), sharpe=_finite_or_none(sharpe[i]),
                         max_drawdown=float(drawdown[i]), turnover=float(turnover_sum[i]),
                         entries=int(entries[i]), completed_trades=int(roundtrips[i]),
                         total_return=float(previous_equity[i] - 1.0),
                         avg_exposure=float(exposure_sum[i] / n), cost_per_side=c, lag=lag)
                    for i in range(count))
    return BacktestResult(returns, metrics, trace)


def buy_hold(close, indices, *, annualization, cost_per_side, capture=False):
    """Same close window, fee model and initial/terminal boundaries as strategies."""
    price = np.asarray(close, dtype=np.float64)
    candidate = Candidate("buy_hold", 0, "benchmark", (), len(indices) + 1, 1.0, None)
    return simulate_window(price, np.ones((len(price), 1), dtype=np.bool_), np.zeros(len(price)),
                           (candidate,), indices, annualization=annualization,
                           cost_per_side=cost_per_side, capture=capture)


def select_validation(candidates, metrics):
    """Frozen once: positive costed mean, at least 20 completed round trips."""
    eligible = [i for i, m in enumerate(metrics) if m["mean_daily"] > 0
                and m["completed_trades"] >= 20 and m["sharpe"] is not None]
    if not eligible:
        return None
    best = max(metrics[i]["sharpe"] for i in eligible)
    tied = [i for i in eligible if abs(metrics[i]["sharpe"] - best) <= 1e-12]
    return min(tied, key=lambda i: (metrics[i]["turnover"], candidates[i].candidate_id))
