"""Charts for the version-3 surfaces (Derivatives, ETF, Crypto, Strategy Lab),
rendered with the same matplotlib-to-data-URI path as `qcharts`."""
from __future__ import annotations

from typing import Optional, Sequence

import numpy as np
import flet as ft

from core.theme import active
from ui.qcharts import _fig, _thin_dates, _to_image, plt


def lines_chart(dates: Sequence[str], series: dict[str, np.ndarray], *, title: str = "", ylabel: str = "",
                hlines: Optional[dict[str, float]] = None, height: float = 3.2, pct: bool = False) -> ft.Image:
    pal = active()
    fig, ax = _fig(9.5, height, pal)
    colours = [pal.accent, pal.text, pal.success, pal.error, pal.muted]
    x = np.arange(len(dates))
    for i, (label, y) in enumerate(series.items()):
        y = np.asarray(y, dtype=float)
        ax.plot(x[-y.size:], y, color=colours[i % len(colours)], linewidth=1.2, label=label)
    for label, v in (hlines or {}).items():
        ax.axhline(v, color=pal.muted, linewidth=0.8, linestyle="--")
        ax.text(x[0] if len(x) else 0, v, f" {label}", color=pal.muted, fontsize=7, va="bottom")
    idx, labels = _thin_dates(list(dates))
    ax.set_xticks(idx); ax.set_xticklabels(labels, rotation=0)
    if pct:
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.1f}%"))
    ax.set_title(title, fontsize=10, loc="left"); ax.set_ylabel(ylabel, fontsize=8)
    ax.legend(loc="upper left", fontsize=7, frameon=False, labelcolor=pal.text)
    return _to_image(fig)


def smile_chart(points, fit=None, F: float = 0.0, *, title: str = "Implied volatility") -> ft.Image:
    """App IV (Black-76 inversion) vs the exchange's IV per strike, with the SVI curve."""
    from core.ficc.equity_deriv import svi_vol
    pal = active()
    fig, ax = _fig(9.5, 3.4, pal)
    ks = np.array([p.strike for p in points])
    ax.scatter(ks, [p.iv * 100 for p in points], s=14, color=pal.accent, label="app (Black-76 on mids)", zorder=3)
    ex = [(p.strike, p.iv_exchange * 100) for p in points if p.iv_exchange]
    if ex:
        ax.scatter([e[0] for e in ex], [e[1] for e in ex], s=14, marker="x", color=pal.text, label="exchange IV", zorder=3)
    if fit is not None and F > 0 and ks.size:
        grid = np.linspace(ks.min(), ks.max(), 120)
        ax.plot(grid, svi_vol(fit, np.log(grid / F)) * 100, color=pal.success, linewidth=1.3,
                label=f"SVI (ρ {fit.rho:+.2f}, RMSE {fit.rmse_volpts:.2f} pts)")
    if F > 0:
        ax.axvline(F, color=pal.muted, linewidth=0.8, linestyle="--")
        ax.text(F, ax.get_ylim()[1], " F", color=pal.muted, fontsize=7, va="top")
    ax.set_title(title, fontsize=10, loc="left"); ax.set_xlabel("strike", fontsize=8); ax.set_ylabel("vol (%)", fontsize=8)
    ax.legend(loc="upper right", fontsize=7, frameon=False, labelcolor=pal.text)
    return _to_image(fig)


def density_chart(rnd: dict, *, p_samples: Optional[np.ndarray] = None, title: str = "Risk-neutral density") -> ft.Image:
    pal = active()
    fig, ax = _fig(9.5, 3.0, pal)
    K, f = rnd["strikes"], rnd["density"]
    ax.plot(K, f, color=pal.accent, linewidth=1.3, label=f"f_Q (∫ = {rnd['integral']:.3f})")
    ax.axvline(rnd["F"], color=pal.muted, linewidth=0.8, linestyle="--")
    if p_samples is not None and len(p_samples) > 50:
        from scipy.stats import gaussian_kde
        kde = gaussian_kde(np.asarray(p_samples, dtype=float))
        ax.plot(K, kde(K), color=pal.success, linewidth=1.1, linestyle="-", label="f_P (GARCH-t terminal)")
    ax.set_title(title, fontsize=10, loc="left"); ax.set_xlabel("terminal level", fontsize=8)
    ax.legend(loc="upper right", fontsize=7, frameon=False, labelcolor=pal.text)
    return _to_image(fig)


def equity_chart(dates: Sequence[str], equity: np.ndarray, bench: Optional[np.ndarray] = None, *,
                 title: str = "Equity", labels: tuple[str, str] = ("strategy", "benchmark")) -> ft.Image:
    pal = active()
    fig, ax = _fig(9.5, 3.2, pal)
    x = np.arange(len(dates))
    eq = np.asarray(equity, dtype=float)
    ax.plot(x[-eq.size:], eq, color=pal.accent, linewidth=1.3, label=labels[0])
    if bench is not None:
        b = np.asarray(bench, dtype=float)
        ax.plot(x[-b.size:], b, color=pal.muted, linewidth=1.0, label=labels[1])
    idx, lab = _thin_dates(list(dates))
    ax.set_xticks(idx); ax.set_xticklabels(lab)
    ax.set_title(title, fontsize=10, loc="left")
    ax.legend(loc="upper left", fontsize=7, frameon=False, labelcolor=pal.text)
    return _to_image(fig)


def bars_chart(labels: Sequence[str], values: Sequence[float], *, title: str = "", vmax: float = 100.0,
               annotate: Optional[Sequence[str]] = None) -> ft.Image:
    pal = active()
    fig, ax = _fig(9.5, 0.45 * len(labels) + 0.8, pal)
    y = np.arange(len(labels))
    vals = [0.0 if v is None or not np.isfinite(v) else float(v) for v in values]
    colours = [pal.success if v >= 70 else pal.accent if v >= 40 else pal.error for v in vals]
    ax.barh(y, vals, color=colours, height=0.6)
    ax.set_yticks(y); ax.set_yticklabels(labels, fontsize=8, color=pal.text)
    ax.set_xlim(0, vmax); ax.invert_yaxis()
    if annotate:
        for i, txt in enumerate(annotate):
            ax.text(min(vals[i] + 1, vmax * 0.98), i, txt, va="center", fontsize=7, color=pal.muted,
                    ha="left" if vals[i] < vmax * 0.6 else "right")
    ax.set_title(title, fontsize=10, loc="left")
    return _to_image(fig)


def premium_chart(dates: Sequence[str], price: np.ndarray, nav: np.ndarray, premium_pct: np.ndarray,
                  *, title: str = "Price vs NAV") -> ft.Image:
    pal = active()
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(9.5, 4.2), dpi=110, sharex=True,
                                 gridspec_kw={"height_ratios": [2, 1]})
    fig.patch.set_facecolor(pal.surface)
    from ui.qcharts import _style
    for ax in (a1, a2):
        _style(ax, pal)
    x = np.arange(len(dates))
    a1.plot(x, price, color=pal.accent, linewidth=1.2, label="price")
    a1.plot(x, nav, color=pal.text, linewidth=0.9, linestyle="--", label="NAV")
    a1.legend(loc="upper left", fontsize=7, frameon=False, labelcolor=pal.text)
    a1.set_title(title, fontsize=10, loc="left")
    a2.bar(x, premium_pct, color=[pal.success if v >= 0 else pal.error for v in premium_pct], width=1.0)
    a2.axhline(0, color=pal.muted, linewidth=0.6)
    a2.set_ylabel("premium %", fontsize=8)
    idx, lab = _thin_dates(list(dates))
    a2.set_xticks(idx); a2.set_xticklabels(lab)
    return _to_image(fig)
