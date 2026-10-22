"""Risk and performance statistics for a single price series or a basket.

Where gs_quant's offline timeseries library covers a measure (realized
volatility, max drawdown, annualization) it is used and the result is labeled
`engine="gs_quant"`; everything else is computed with numpy and labeled
`engine="local"`. The two agree on the overlap — `tests/quant_acceptance.py`
checks that — but keeping the label means a number can always be traced to
the code that produced it.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from core.quant.history import History, TRADING_DAYS

try:                                                  # optional, offline-capable
    import pandas as _pd
    import gs_quant.timeseries as _gts
    _GS_OK = True
except Exception:                                     # pragma: no cover
    _pd = None
    _gts = None
    _GS_OK = False


def gs_quant_available() -> bool:
    return _GS_OK


@dataclass(frozen=True)
class RiskReport:
    symbol: str
    sessions: int
    first_date: str
    last_date: str
    last_price: float
    engine: str                       # "gs_quant" | "local"
    ann_return: float                 # annualized log return
    ann_vol: float                    # annualized volatility
    sharpe: float                     # (ann_return - rf) / ann_vol
    sortino: float
    max_drawdown: float               # negative fraction, e.g. -0.23
    calmar: float
    var_1d: float                     # 1-day historical VaR at var_level (+fraction)
    cvar_1d: float                    # 1-day historical CVaR
    var_level: float
    skew: float
    kurtosis: float                   # excess kurtosis
    best_day: float
    worst_day: float
    positive_days: float              # fraction of up days
    rf_rate: float


def _drawdown_curve(prices: np.ndarray) -> np.ndarray:
    peak = np.maximum.accumulate(prices)
    return prices / peak - 1.0


def analyze_history(history: History, *, rf_rate: float = 0.03,
                    var_level: float = 0.95) -> RiskReport:
    px = history.prices()
    r = history.log_returns()
    if r.size < 20:
        raise ValueError("Need at least 21 sessions to compute risk statistics.")

    engine = "local"
    if _GS_OK:
        try:
            # annualize() infers its factor from the index spacing, so the
            # series needs real dates; business-day spacing = factor 252.
            idx = _pd.bdate_range(end=_pd.Timestamp.today().normalize(), periods=px.size)
            s = _pd.Series(px, index=idx)
            # Log returns, explicitly — gs_quant defaults to simple returns,
            # and the rest of this module (and the MC calibration) is log-based.
            log_r = _gts.returns(s, 1, _gts.Returns.LOGARITHMIC)
            ann_vol = float(_gts.annualize(_gts.std(log_r, _gts.Window(None, 0))).iloc[-1])
            mdd = float(_gts.max_drawdown(s, _gts.Window(None, 0)).iloc[-1])
            engine = "gs_quant"
        except Exception:
            ann_vol = float(np.std(r, ddof=1)) * math.sqrt(TRADING_DAYS)
            mdd = float(np.min(_drawdown_curve(px)))
    else:
        ann_vol = float(np.std(r, ddof=1)) * math.sqrt(TRADING_DAYS)
        mdd = float(np.min(_drawdown_curve(px)))

    ann_ret = float(np.mean(r)) * TRADING_DAYS
    sharpe = (ann_ret - rf_rate) / ann_vol if ann_vol > 0 else 0.0
    downside = r[r < 0]
    down_vol = (float(np.std(downside, ddof=1)) * math.sqrt(TRADING_DAYS)
                if downside.size > 1 else 0.0)
    sortino = (ann_ret - rf_rate) / down_vol if down_vol > 0 else 0.0
    calmar = ann_ret / abs(mdd) if mdd < 0 else 0.0

    losses = -r
    var = float(np.percentile(losses, var_level * 100))
    tail = losses[losses >= var]
    cvar = float(np.mean(tail)) if tail.size else var

    mean, std = float(np.mean(r)), float(np.std(r, ddof=1))
    z = (r - mean) / std if std > 0 else np.zeros_like(r)
    skew = float(np.mean(z**3))
    kurt = float(np.mean(z**4)) - 3.0

    return RiskReport(
        symbol=history.symbol, sessions=len(history),
        first_date=history.first_date, last_date=history.last_date,
        last_price=history.last, engine=engine,
        ann_return=ann_ret, ann_vol=ann_vol, sharpe=sharpe, sortino=sortino,
        max_drawdown=mdd, calmar=calmar,
        var_1d=max(0.0, var), cvar_1d=max(0.0, cvar), var_level=var_level,
        skew=skew, kurtosis=kurt,
        best_day=float(np.max(r)), worst_day=float(np.min(r)),
        positive_days=float(np.mean(r > 0)), rf_rate=rf_rate,
    )


# --------------------------------------------------------------------------- #
# Basket statistics
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class BasketStats:
    symbols: tuple[str, ...]
    sessions: int                     # overlapping sessions used
    mean_returns: np.ndarray = field(repr=False, default=None)   # annualized, per asset
    cov: np.ndarray = field(repr=False, default=None)            # annualized covariance
    corr: np.ndarray = field(repr=False, default=None)
    returns: np.ndarray = field(repr=False, default=None)        # (T, N) daily log returns


def align_histories(histories: list[History]) -> BasketStats:
    """Intersect on shared dates and compute the joint return statistics every
    optimizer input needs. Raises if fewer than 30 sessions overlap — a
    covariance estimated on less is noise wearing a matrix."""
    if len(histories) < 2:
        raise ValueError("Need at least two assets.")
    common = set(histories[0].dates)
    for h in histories[1:]:
        common &= set(h.dates)
    dates = sorted(common)
    if len(dates) < 31:
        raise ValueError(f"Only {len(dates)} overlapping sessions across "
                         f"{[h.symbol for h in histories]}; need at least 31.")
    cols = []
    for h in histories:
        lookup = dict(zip(h.dates, h.closes))
        px = np.array([lookup[d] for d in dates], dtype=float)
        cols.append(np.diff(np.log(px)))
    R = np.column_stack(cols)                          # (T-1, N)
    mean = R.mean(axis=0) * TRADING_DAYS
    cov = np.cov(R, rowvar=False, ddof=1) * TRADING_DAYS
    sd = np.sqrt(np.clip(np.diag(cov), 1e-12, None))
    corr = cov / np.outer(sd, sd)
    np.fill_diagonal(corr, 1.0)
    return BasketStats(symbols=tuple(h.symbol for h in histories),
                       sessions=len(dates), mean_returns=mean, cov=cov,
                       corr=corr, returns=R)


def portfolio_point(weights: np.ndarray, stats: BasketStats,
                    *, rf_rate: float = 0.03) -> tuple[float, float, float]:
    """(annual return, annual vol, sharpe) of a weight vector on a basket."""
    w = np.asarray(weights, dtype=float)
    ret = float(w @ stats.mean_returns)
    vol = float(np.sqrt(max(w @ stats.cov @ w, 0.0)))
    sharpe = (ret - rf_rate) / vol if vol > 0 else 0.0
    return ret, vol, sharpe


# --------------------------------------------------------------------------- #
# v2 risk layer (M2; rulings section 2): the names live in core/quant/risk_layer.py and are re-exported here so
# `core.quant.risk.market_vol_target` resolves (spec section 3.5). The statistics above are untouched (log returns);
# the vol target uses simple returns and is not interchangeable with `analyze_history`.
# --------------------------------------------------------------------------- #
from core.quant.risk_layer import (  # noqa: E402,F401
    ActingFailure, BookVT, ComposeResult, CompositionError, ConcentrationBound, HedgeState, LadderState, VSResult,
    VTResult, apply_hedge_state, compose, compose_detail, corr63, covariance_carry, display_label_abs,
    display_label_rel, ewma_vol, guard_acting, hedge_state, label_of, market_vol_target, risk_layer, sigma_history,
    sma_vol, verify_composition, vt_for_book,
)
