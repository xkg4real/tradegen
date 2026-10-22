"""FX style premia beyond the carry basket: cross-sectional momentum, dollar
carry and the Fama regression. Same bookkeeping as `core.ficc.fx.carry_backtest`:
rank on information known at t, earn spot return plus the rate differential
from t+1, costs on turnover, no look-ahead.

  momentum_backtest   Menkhoff, Sarno, Schmeling & Schrimpf (2012, JFE 106):
                      rank currencies on the excess return of the past f months,
                      long the top third, short the bottom third, hold one month
  dollar_carry_backtest   Lustig, Roussanov & Verdelhan (2014, JFE 111): long an
                      equal-weight basket of foreign currencies against USD when
                      the average forward discount (≈ mean foreign rate − USD
                      rate) is positive, short it otherwise
  fama_regression     Fama (1984): Δs_{t+1} on (r_ccy − r_usd), HAC t-stat; a
                      slope below one is the forward-premium puzzle

User-material refs: Shreve II 9.3.16 p. 385 (PDF 401) for the domestic/foreign
measures behind the forward premium; 계량2 Ch. 2 (OLS asymptotics for the
Fama t-stat); the user's paper §6.9 and §7.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Sequence

import numpy as np

from core.ficc.common import BP, TRADING_DAYS, FICCError
from core.ficc.data import Series
from core.ficc.fx import CarryBacktest, _ffill_rates, _leg, _rate


def _panel(spots: dict[str, Series], rates: dict[str, Series]):
    legs = {pair: _leg(pair, s) for pair, s in spots.items()}
    if not legs:
        raise FICCError("No spot series given.")
    common = set.intersection(*(set(s.dates) for s in spots.values()))
    dates = sorted(common)
    ccys = [legs[p][0] for p in spots]
    P = np.column_stack([np.asarray(legs[p][2], dtype=float)[
        [i for i, d in enumerate(spots[p].dates) if d in common]] for p in spots])
    R = np.column_stack([_ffill_rates(_rate(rates, c), dates) for c in ccys])
    r_usd = _ffill_rates(_rate(rates, "USD"), dates)
    ok = np.isfinite(R).all(axis=1) & np.isfinite(r_usd)
    if not ok.any():
        raise FICCError("Rates are not known on any date.")
    i0 = int(np.argmax(ok))
    return dates, ccys, P, R, r_usd, i0


def _run(dates, ccys, P, R, r_usd, i0, *, weight_fn, rebalance_days: int, cost_bps: float,
         warmup: int, label: str) -> CarryBacktest:
    n = len(ccys)
    w = np.zeros(n)
    eq, bench, positions = [1.0], [1.0], []
    start = i0 + warmup
    if start >= len(dates) - 1:
        raise FICCError(f"Only {len(dates) - start} usable dates after warm-up for {label}.")
    for i in range(start, len(dates) - 1):
        if (i - start) % rebalance_days == 0:
            new_w, note = weight_fn(i)
            eq[-1] *= 1.0 - float(np.abs(new_w - w).sum()) * cost_bps * BP
            w = new_w
            longs = tuple(ccys[j] for j in np.where(w > 0)[0])
            shorts = tuple(ccys[j] for j in np.where(w < 0)[0])
            positions.append((dates[i], longs, shorts))
        ret = P[i + 1] / P[i] - 1.0 + (R[i] - r_usd[i]) / TRADING_DAYS
        eq.append(eq[-1] * (1.0 + float(w @ ret)))
        bench.append(bench[-1] * (1.0 + float(ret.mean())))
    equity, bench_eq = np.asarray(eq), np.asarray(bench)
    equity[0] = 1.0
    daily = np.diff(equity) / equity[:-1]
    m = daily.size
    ann_ret = float(equity[-1] ** (TRADING_DAYS / m) - 1.0) if equity[-1] > 0 else -1.0
    ann_vol = float(np.std(daily, ddof=1)) * math.sqrt(TRADING_DAYS) if m > 1 else 0.0
    mdd = float(np.min(equity / np.maximum.accumulate(equity) - 1.0))
    return CarryBacktest(dates=tuple(dates[start:]), equity=equity, bench_equity=bench_eq,
                         positions=tuple(positions), ann_return=ann_ret, ann_vol=ann_vol,
                         sharpe=ann_ret / ann_vol if ann_vol > 0 else 0.0, max_drawdown=mdd,
                         n_rebalances=len(positions), top_n=max(1, n // 3), cost_bps=cost_bps,
                         note=f"{label}; {n} ccys vs USD; {m} observations from {dates[start]}; no lookahead")


def momentum_backtest(spots: dict[str, Series], rates: dict[str, Series], *, formation_months: int = 3,
                      top_n: int | None = None, cost_bps: float = 10.0, rebalance_days: int = 21) -> CarryBacktest:
    """Rank on the past `formation_months` excess return (spot + carry accrual),
    long the top third and short the bottom third at ±1/k, monthly."""
    dates, ccys, P, R, r_usd, i0 = _panel(spots, rates)
    n = len(ccys)
    k = max(1, min(top_n or n // 3, n // 2))
    f = formation_months * 21

    def weight_fn(i):
        ex = np.log(P[i] / P[i - f]) + np.nansum((R[i - f:i] - r_usd[i - f:i, None]) / TRADING_DAYS, axis=0)
        order = np.argsort(-ex, kind="stable")
        w = np.zeros(n)
        w[order[:k]], w[order[-k:]] = 1.0 / k, -1.0 / k
        return w, ""
    return _run(dates, ccys, P, R, r_usd, i0, weight_fn=weight_fn, rebalance_days=rebalance_days,
                cost_bps=cost_bps, warmup=f, label=f"FX momentum {formation_months}-1, long/short {k}")


def dollar_carry_backtest(spots: dict[str, Series], rates: dict[str, Series], *, cost_bps: float = 5.0,
                          rebalance_days: int = 21) -> CarryBacktest:
    """AFD_t = mean_i(r_i − r_usd); long every foreign currency equally when
    AFD > 0 (short USD), short them when AFD < 0."""
    dates, ccys, P, R, r_usd, i0 = _panel(spots, rates)
    n = len(ccys)

    def weight_fn(i):
        afd = float(np.mean(R[i] - r_usd[i]))
        return (np.full(n, 1.0 / n) if afd > 0 else np.full(n, -1.0 / n)), f"AFD {afd:+.2%}"
    return _run(dates, ccys, P, R, r_usd, i0, weight_fn=weight_fn, rebalance_days=rebalance_days,
                cost_bps=cost_bps, warmup=1, label="dollar carry (LRV 2014)")


@dataclass(frozen=True)
class FamaRow:
    ccy: str
    slope: float                      # Δs on (r_ccy − r_usd), monthly; UIP says 1 in this convention? see note
    t_stat: float
    n_months: int
    mean_carry: float


def fama_regression(spots: dict[str, Series], rates: dict[str, Series], *, step: int = 21) -> list[FamaRow]:
    """Per currency: the next-month log spot change of the foreign currency in
    USD on its rate differential (r_ccy − r_usd). Uncovered interest parity
    predicts a slope of −1 (a higher-rate currency should depreciate by the
    differential); Fama's puzzle is a slope near zero or positive."""
    from core.quant.validate import newey_west_t
    dates, ccys, P, R, r_usd, i0 = _panel(spots, rates)
    out = []
    idx = np.arange(i0, len(dates) - step, step)
    for j, c in enumerate(ccys):
        x = (R[idx, j] - r_usd[idx]) * step / TRADING_DAYS
        y = np.log(P[idx + step, j] / P[idx, j])
        if x.size < 12 or np.std(x) == 0:
            continue
        X = np.column_stack([np.ones(x.size), x])
        beta, *_ = np.linalg.lstsq(X, y, rcond=None)
        resid = y - X @ beta
        # HAC t for the slope via the score series
        score = resid * (x - x.mean())
        t = newey_west_t(score, 1) * math.sqrt(x.size) / math.sqrt(np.sum((x - x.mean()) ** 2)) * np.std(score) if np.std(score) > 0 else float("nan")
        se = math.sqrt(np.sum(resid ** 2) / (x.size - 2) / np.sum((x - x.mean()) ** 2))
        out.append(FamaRow(ccy=c, slope=float(beta[1]), t_stat=float(beta[1] / se) if se > 0 else float("nan"),
                           n_months=int(x.size), mean_carry=float(np.mean(R[idx, j] - r_usd[idx]))))
    return out


# --------------------------------------------------------------------------- #
# Self-check (synthetic)
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    from core.ficc.data import G10_KRW, synthetic_fx, synthetic_series
    pairs = {c: ("USD" + c if c in ("JPY", "KRW", "CAD", "CHF") else c + "USD") for c in G10_KRW if c != "USD"}
    spots = {p: synthetic_fx(p, days=800) for p in pairs.values()}
    rates = {c: synthetic_series(f"RATE_{c}", days=800, kind="rate") for c in G10_KRW}
    bt = momentum_backtest(spots, rates, formation_months=3)
    assert bt.equity[0] == 1.0 and not np.isnan(bt.equity).any() and bt.n_rebalances > 20
    assert all(len(l) == 2 and len(s) == 2 and not set(l) & set(s) for _, l, s in bt.positions)
    dc = dollar_carry_backtest(spots, rates)
    assert dc.n_rebalances > 30 and all((len(l) == 7 and not s) or (len(s) == 7 and not l) for _, l, s in dc.positions)
    dear = momentum_backtest(spots, rates, formation_months=3, cost_bps=100.0)
    assert dear.equity[-1] < bt.equity[-1]
    # A currency that trends up with a high rate: momentum longs it, dollar carry sign follows AFD.
    rows = fama_regression(spots, rates)
    assert len(rows) == 7 and all(math.isfinite(r.slope) for r in rows)
    print("ok")
