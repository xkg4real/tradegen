"""Technical signal engine: indicators, per-component scores, one composite.

Unlike the NEXTGEN client build — which was contractually forbidden from
recommending anything — QUANTGEN is the operator's personal instrument, and
this module's whole job is to hold an opinion. Each indicator contributes a
score in [-100, +100] (negative bearish, positive bullish) with a one-line
reason; the composite is the weighted mean, mapped to a stance word.

The composite is an *aggregation of indicators*, not a prophecy. The weights
are stated in the output so a disagreement between components is visible
rather than averaged into false confidence.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from core.quant.history import History


@dataclass(frozen=True)
class SignalComponent:
    key: str
    label: str
    score: float                      # -100 .. +100
    weight: float
    reason: str
    value: str = ""                   # display value, e.g. "RSI 61.3"
    family: str = ""                  # v2.0 family tag (section 3.7); "" = untagged, no family overlay (M4)


@dataclass(frozen=True)
class SignalReport:
    symbol: str
    last_price: float
    composite: float                  # -100 .. +100
    stance: str                       # strong sell .. strong buy
    components: tuple[SignalComponent, ...]

    @property
    def direction(self) -> int:
        return 1 if self.composite > 15 else (-1 if self.composite < -15 else 0)


def sma(px: np.ndarray, n: int) -> np.ndarray:
    if px.size < n:
        return np.full(px.size, np.nan)
    c = np.convolve(px, np.ones(n) / n, mode="valid")
    return np.concatenate([np.full(n - 1, np.nan), c])


def ema(px: np.ndarray, n: int) -> np.ndarray:
    alpha = 2.0 / (n + 1)
    out = np.empty_like(px)
    out[0] = px[0]
    for i in range(1, px.size):
        out[i] = alpha * px[i] + (1 - alpha) * out[i - 1]
    return out


def rsi(px: np.ndarray, n: int = 14) -> float:
    if px.size < n + 1:
        return 50.0
    delta = np.diff(px)
    gains = np.clip(delta, 0, None)
    losses = np.clip(-delta, 0, None)
    avg_gain = gains[:n].mean()
    avg_loss = losses[:n].mean()
    for i in range(n, delta.size):
        avg_gain = (avg_gain * (n - 1) + gains[i]) / n
        avg_loss = (avg_loss * (n - 1) + losses[i]) / n
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - 100.0 / (1.0 + rs)


def macd(px: np.ndarray) -> tuple[float, float]:
    """(MACD line, signal line) at the last bar, standard 12/26/9."""
    line = ema(px, 12) - ema(px, 26)
    sig = ema(line, 9)
    return float(line[-1]), float(sig[-1])


def _clamp(x: float) -> float:
    return float(max(-100.0, min(100.0, x)))


def compute_signals(history: History) -> SignalReport:
    px = history.prices()
    last = float(px[-1])
    comps: list[SignalComponent] = []

    # --- Trend: price vs 50/200-day SMA -------------------------------------
    s50 = sma(px, 50)
    s200 = sma(px, 200)
    if not np.isnan(s50[-1]):
        gap50 = (last / s50[-1] - 1.0) * 100
        score = _clamp(gap50 * 8)
        above = "above" if gap50 >= 0 else "below"
        comps.append(SignalComponent(
            "trend50", "Price vs 50-day SMA", score, 0.20,
            f"Price is {abs(gap50):.1f}% {above} its 50-day average.",
            f"SMA50 {s50[-1]:,.2f}"))
    if not np.isnan(s200[-1]):
        gap200 = (last / s200[-1] - 1.0) * 100
        score = _clamp(gap200 * 5)
        above = "above" if gap200 >= 0 else "below"
        comps.append(SignalComponent(
            "trend200", "Price vs 200-day SMA", score, 0.20,
            f"Price is {abs(gap200):.1f}% {above} its 200-day average — "
            f"the long trend is {'up' if gap200 >= 0 else 'down'}.",
            f"SMA200 {s200[-1]:,.2f}"))

    # --- Momentum: 3-month rate of change -----------------------------------
    if px.size >= 64:
        roc = (last / px[-64] - 1.0) * 100
        comps.append(SignalComponent(
            "momentum", "3-month momentum", _clamp(roc * 4), 0.20,
            f"Price moved {roc:+.1f}% over the last 63 sessions.",
            f"ROC63 {roc:+.1f}%"))

    # --- RSI: overbought/oversold, mean-reversion flavored -------------------
    r = rsi(px)
    if r >= 70:
        rsi_score, why = _clamp(-(r - 70) * 3.3), f"RSI {r:.0f} is overbought — stretched to the upside."
    elif r <= 30:
        rsi_score, why = _clamp((30 - r) * 3.3), f"RSI {r:.0f} is oversold — stretched to the downside."
    else:
        rsi_score, why = _clamp((r - 50) * 1.2), f"RSI {r:.0f} is in the neutral band."
    comps.append(SignalComponent("rsi", "RSI (14)", rsi_score, 0.15, why, f"RSI {r:.1f}"))

    # --- MACD ----------------------------------------------------------------
    line, sig_line = macd(px)
    hist_val = line - sig_line
    scale = max(last * 0.005, 1e-9)                    # 0.5% of price ≈ full score
    macd_score = _clamp(hist_val / scale * 100)
    comps.append(SignalComponent(
        "macd", "MACD (12/26/9)", macd_score, 0.15,
        f"MACD line is {'above' if hist_val >= 0 else 'below'} its signal line "
        f"by {abs(hist_val):.3f}.", f"hist {hist_val:+.3f}"))

    # --- Volatility posture: 20-day realized vs 100-day ----------------------
    lr = np.diff(np.log(px))
    if lr.size >= 100:
        v20 = float(np.std(lr[-20:], ddof=1))
        v100 = float(np.std(lr[-100:], ddof=1))
        ratio = v20 / v100 if v100 > 0 else 1.0
        vol_score = _clamp((1.0 - ratio) * 120)        # calm = mild positive
        comps.append(SignalComponent(
            "vol", "Volatility regime", vol_score, 0.10,
            f"20-day volatility is {ratio:.2f}× its 100-day level — "
            f"{'compressed' if ratio < 0.9 else ('elevated' if ratio > 1.1 else 'normal')}.",
            f"σ20/σ100 {ratio:.2f}"))

    total_w = sum(c.weight for c in comps)
    composite = sum(c.score * c.weight for c in comps) / total_w if total_w else 0.0

    if composite >= 50:
        stance = "strong bullish"
    elif composite >= 15:
        stance = "bullish"
    elif composite > -15:
        stance = "neutral"
    elif composite > -50:
        stance = "bearish"
    else:
        stance = "strong bearish"

    return SignalReport(symbol=history.symbol, last_price=last,
                        composite=float(composite), stance=stance,
                        components=tuple(comps))
