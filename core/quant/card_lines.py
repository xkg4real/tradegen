"""The printed lines of a card: R-26 rule 6 execution variants and attribution, turnover by regime, the stress-cost
line, futures roll-cost and ban-basis lines, the R-31 binding share and persistence check, the stack card's
low-exposure share and rebound capture (L2827-2832, L3305-3309, L5284-5289; TASK-M7-19, M7-27, M7-29).

Everything here is printed and never gated: no function returns a verdict or changes a weight. Arithmetic reuses
core.quant.costed (earning weights, costed paths, window returns) and core.quant.validate.sharpe; nothing is
re-implemented. Books are 1-d arrays of daily simple returns and decided weights; the cost rate comes from
core.quant.instruments.cost_per_side with the tick floor and is never lowered.

reading: variant B needs daily opens; without them it is reported as None with the reason (never fabricated).
reading: the stress line's sigma_median is the expanding median of sigma20 through t (causal; brief F-19).
reading: persistence_check (Kaminski-Lo) = mean next-`horizon`-session return after an activation vs the
unconditional mean of the same horizon (L3309).
"""
from __future__ import annotations

import math
from datetime import date
from typing import Mapping, Sequence

import numpy as np

from core.quant import costed as C
from core.quant.instruments import cost_per_side, stress, stress_cost_line as _stress_line
from core.quant.validate import sharpe


def _arr(x) -> np.ndarray:
    return np.asarray(x, dtype=float)


# --------------------------------------------------------------------------- #
# R-26 rule 6: execution variants A / B / C and the overnight / intraday attribution
# --------------------------------------------------------------------------- #
def exec_variants(closes, weights_decided, cost_bp: float, *, opens=None, stress_mult: float = 1.0, legs: int = 1) -> dict:
    """{A, B, C}: annualised Sharpe of the same decided weights under three executions (L2828).
    A: decided at the close of t, traded at that close, earns from t+1 (the card's own convention).
    B: traded at the open of t+1; the overnight gap close_t -> open_t+1 is earned at the old weight.
    C: traded at the close of t+1, earns from t+2 (one-session lag)."""
    p = _arr(closes)
    w = _arr(weights_decided)
    if p.shape != w.shape or p.ndim != 1 or p.size < 3:
        raise ValueError("closes and weights_decided must be 1-d arrays of the same length (>= 3)")
    r = np.zeros(p.size)
    r[1:] = p[1:] / p[:-1] - 1.0
    a = C.costed_path(C.earning_weights(w), r, cost_bp, stress_mult, legs=legs).net
    w_c = np.full(w.shape, np.nan)
    w_c[2:] = w[:-2]
    c = C.costed_path(w_c, r, cost_bp, stress_mult, legs=legs).net
    out = {"A": sharpe(a[1:]), "C": sharpe(c[2:]), "B": None, "B_reason": "opens absent: variant B needs daily opens with value_status and session_date (L2785)"}
    if opens is not None:
        o = _arr(opens)
        if o.shape != p.shape:
            raise ValueError("opens must align with closes")
        r_on = np.zeros(p.size)
        r_on[1:] = o[1:] / p[:-1] - 1.0            # close t-1 -> open t
        r_in = p / o - 1.0                          # open t -> close t
        w_old = C.earning_weights(C.earning_weights(w))   # w_dec[t-2] holds the overnight leg
        w_new = C.earning_weights(w)                       # w_dec[t-1] holds the intraday leg
        held_old = np.where(np.isfinite(w_old), w_old, 0.0)
        held_new = np.where(np.isfinite(w_new), w_new, 0.0)
        gross = (1.0 + held_old * r_on) * (1.0 + held_new * r_in) - 1.0
        cost = C.costed_path(w_new, r, cost_bp, stress_mult, legs=legs).cost
        b = gross - cost
        out["B"] = sharpe(b[2:])
        out["B_reason"] = None
    return out


def overnight_intraday_attribution(closes, opens, weights_decided) -> dict:
    """The book's return split into the close -> open and open -> close legs (sum of daily legs at the earning
    weight), plus the per-year open-to-close drift of the underlying ("Any KRX intraday long card must clear the
    -11% a year open-to-close drift", L2829)."""
    p, o, w = _arr(closes), _arr(opens), _arr(weights_decided)
    if not (p.shape == o.shape == w.shape) or p.ndim != 1 or p.size < 2:
        raise ValueError("closes, opens and weights_decided must align (1-d, >= 2)")
    r_on = np.zeros(p.size)
    r_on[1:] = o[1:] / p[:-1] - 1.0
    r_in = p / o - 1.0
    held = np.where(np.isfinite(C.earning_weights(w)), C.earning_weights(w), 0.0)
    years = p.size / C.TRADING_DAYS
    return {"overnight": float(np.sum(held * r_on)), "intraday": float(np.sum(held * r_in)),
            "underlying_overnight_per_year": float(np.sum(r_on) / years), "underlying_intraday_per_year": float(np.sum(r_in) / years),
            "sessions": int(p.size)}


# --------------------------------------------------------------------------- #
# Turnover by regime, stress cost, futures lines (printed only)
# --------------------------------------------------------------------------- #
def turnover_by_regime(weights_decided, dates: Sequence[date], regime_tags: Mapping[date, Mapping] | None = None) -> dict:
    """sum |dw| per calendar year and, when R-20 tags are given, per (tag, value) line (L2830)."""
    w = _arr(weights_decided)
    if len(dates) != w.size:
        raise ValueError("dates must align with weights_decided")
    finite = np.isfinite(w)
    first = int(np.argmax(finite)) if finite.any() else w.size
    dw = np.zeros(w.size)
    if first + 1 < w.size:
        dw[first + 1:] = np.abs(np.diff(w[first:]))          # warm-up flat; the initial entry is not turnover (costed)
    by_year: dict[int, float] = {}
    for d, x in zip(dates, dw):
        by_year[d.year] = by_year.get(d.year, 0.0) + float(x)
    by_tag: dict[str, float] = {}
    for d, x in zip(dates, dw):
        for tag, val in (regime_tags or {}).get(d, {}).items():
            key = f"{tag}={val}"
            by_tag[key] = by_tag.get(key, 0.0) + float(x)
    return {"by_year": by_year, "by_regime": by_tag, "total": float(dw.sum())}


def stress_cost_line(returns, base_bp: float, *, window: int = 20, etf_close_fill: bool = True) -> dict:
    """cost x clip(sigma20 / sigma_median, 1, 5) + 10 bp on ETF close fills when |r| >= 3% (L2831); sigma_median is
    the expanding median of sigma20 through t (causal); printed, never gated, never below `base_bp`."""
    r = _arr(returns)
    if r.size < window + 1:
        raise ValueError(f"stress line needs more than {window} returns")
    sig = np.array([float(np.std(r[t - window + 1:t + 1], ddof=1)) for t in range(window - 1, r.size)]) * math.sqrt(C.TRADING_DAYS)
    lines = []
    for i, s in enumerate(sig):
        med = float(np.median(sig[:i + 1]))
        lines.append(_stress_line(base_bp, s, med, etf_close_fill=etf_close_fill, abs_ret=abs(float(r[window - 1 + i]))))
    arr = np.array(lines)
    return {"base_bp": float(base_bp), "mean_bp": float(arr.mean()), "max_bp": float(arr.max()), "share_above_base": float(np.mean(arr > base_bp)),
            "gated": False, "calibrated_on_kis_snapshots": False}


def roll_cost_line(roll_dates: Sequence[date], cost_bp: float, *, sessions: int) -> dict:
    """Futures books only: one round trip (both sides) per fixed-calendar roll before expiry (L2832)."""
    n = len(roll_dates)
    return {"rolls": n, "cost_bp_per_roll": 2.0 * float(cost_bp), "bp_per_year": 2.0 * float(cost_bp) * n / max(sessions / C.TRADING_DAYS, 1e-9),
            "calendar": [d.isoformat() for d in roll_dates], "gated": False}


def ban_basis_line(returns, ban_mask) -> dict:
    """Mean daily return inside vs outside short-sale-ban periods (R-20 tags), printed for futures books (L2832)."""
    r, m = _arr(returns), np.asarray(ban_mask, dtype=bool)
    if r.shape != m.shape:
        raise ValueError("ban_mask must align with returns")
    return {"sessions_in_ban": int(m.sum()), "mean_in_ban": float(r[m].mean()) if m.any() else None,
            "mean_outside": float(r[~m].mean()) if (~m).any() else None, "gated": False}


# --------------------------------------------------------------------------- #
# R-31 lines
# --------------------------------------------------------------------------- #
def binding_share(step_mult) -> float:
    """n_bind / n_sessions, n_bind = sessions with step_mult < 1 (L3305); an all-ones path is 0.0."""
    m = _arr(step_mult)
    if m.size == 0:
        raise ValueError("binding_share of an empty path")
    if np.any(m > 1.0 + 1e-12) or np.any(m < 0.0):
        raise ValueError("a step multiplier above 1.0 or below 0 is refused (P2)")
    return float(np.mean(m < 1.0 - 1e-12))


def persistence_check(returns, activations, horizon: int = 21) -> dict:
    """Kaminski-Lo: mean next-`horizon`-session return after an activation vs the unconditional mean (L3309)."""
    r, a = _arr(returns), np.asarray(activations, dtype=bool)
    if r.shape != a.shape or r.size <= horizon:
        raise ValueError("returns and activations must align and exceed the horizon")
    fwd = np.array([np.prod(1.0 + r[t + 1:t + 1 + horizon]) - 1.0 for t in range(r.size - horizon)])
    act = a[:r.size - horizon]
    return {"horizon": int(horizon), "n_activations": int(act.sum()), "after_activation": float(fwd[act].mean()) if act.any() else None,
            "unconditional": float(fwd.mean()), "gated": False}


# --------------------------------------------------------------------------- #
# Stack-card lines
# --------------------------------------------------------------------------- #
def low_exposure_share(total_exposure, level: float = 0.25) -> float:
    """Share of days at <= `level` x total exposure (L5284)."""
    e = _arr(total_exposure)
    if e.size == 0:
        raise ValueError("empty exposure path")
    return float(np.mean(e <= level + 1e-12))


def rebound_capture(book_returns, bh_returns, dates: Sequence[date], cost_episodes: Mapping[str, Sequence[str]]) -> dict:
    """Book vs buy-and-hold window returns in gate.evaluation.cost_episodes (L5284-5289); printed."""
    out = {}
    for name, (start, end) in cost_episodes.items():
        s, e = date.fromisoformat(start), date.fromisoformat(end)
        if not C.window_mask(dates, s, e).any():       # window outside the sample: printed as absent, never invented
            out[name] = {"book": None, "buy_and_hold": None, "reason": f"{start}..{end} outside the sample"}
            continue
        out[name] = {"book": C.window_return(book_returns, dates, s, e), "buy_and_hold": C.window_return(bh_returns, dates, s, e)}
    return out


# --------------------------------------------------------------------------- #
# The printed block of one card (T-BOOK-01 printed-line clause)
# --------------------------------------------------------------------------- #
def cost_lines(instrument_book: str, price: float | None = None, *, on: date | None = None, nav_fx=None) -> dict:
    """costs_per_side {table_bp, floor_bp, applied_bp, stress_line (2x)} from the gate's table with the tick floor."""
    q = cost_per_side(instrument_book, price, nav_fx, on=on)
    return {"table_bp": q.table_bp, "floor_bp": q.floor_bp, "applied_bp": q.bp, "source": q.source,
            "stress_line": {"multiplier": 2.0, "bp": stress(q.bp)}}


def card_lines(header: Mapping, closes, weights_decided, *, opens=None, dates: Sequence[date] | None = None,
               regime_tags: Mapping[date, Mapping] | None = None, price: float | None = None, on: date | None = None,
               nav_fx=None, legs: int = 1) -> dict:
    """Every printed line of one card: the instrument book, notional, rebalance rule, band, cost with the tick floor
    and the 2x line, execution variants A/B/C, the attribution, turnover by regime, the stress-cost line, the futures
    lines when the book is a futures line. Never gated."""
    costs = cost_lines(header["instrument_book"], price, on=on, nav_fx=nav_fx)
    bp = costs["applied_bp"]
    r = np.zeros(len(closes))
    p = _arr(closes)
    r[1:] = p[1:] / p[:-1] - 1.0
    lines = {
        "instrument_book": header["instrument_book"], "notional_nav": header.get("notional_nav"),
        "rebalance": header.get("rebalance"), "no_trade_band": header.get("no_trade_band"),
        "costs_per_side": costs, "exec_variants": exec_variants(closes, weights_decided, bp, opens=opens, legs=legs),
        "exec_variants_2x": exec_variants(closes, weights_decided, bp, opens=opens, stress_mult=2.0, legs=legs),
        "overnight_intraday": overnight_intraday_attribution(closes, opens, weights_decided) if opens is not None
        else {"reason": "opens absent (L2785)"},
        "stress_cost": stress_cost_line(r, bp, etf_close_fill=header["instrument_book"].endswith("ETF_line")),
        "gated": False,
    }
    if dates is not None:
        lines["turnover_by_regime"] = turnover_by_regime(weights_decided, dates, regime_tags)
    return lines
