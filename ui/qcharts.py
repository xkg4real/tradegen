"""Quant charts, rendered by matplotlib into base64 data-URI images.

Flet 0.85 ships no chart controls (`ft.LineChart` and `ft.BarChart` are gone
from this build — probed, not assumed), and the container-bar technique that
draws NEXTGEN's score bars cannot draw a percentile fan or a scatter cloud.
matplotlib can, deterministically, and `ft.Image` renders the PNG. `src`
accepts a data URI in 0.85; `src_base64` was removed.

Every figure is painted with the active QUANTGEN palette so the charts sit in
the app instead of on top of it. The Agg backend is forced before pyplot is
imported: this module runs inside worker threads, and a GUI backend would
try to touch the main thread and die.
"""
from __future__ import annotations

import base64
import io

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import flet as ft

from core.quant.backtest import BacktestResult
from core.quant.garch import TRADING_DAYS, GarchFit
from core.quant.history import History
from core.quant.montecarlo import MCResult
from core.quant.optimize import Frontier, OptimizedPortfolio
from core.theme import active

DPI = 110


def _style(ax, pal, *, grid: bool = True) -> None:
    ax.set_facecolor(pal.surface)
    for spine in ax.spines.values():
        spine.set_color(pal.border)
    ax.tick_params(colors=pal.muted, labelsize=8)
    if grid:
        ax.grid(True, color=pal.border, alpha=0.35, linewidth=0.6)
    ax.title.set_color(pal.text)
    ax.xaxis.label.set_color(pal.muted)
    ax.yaxis.label.set_color(pal.muted)


def _fig(w: float, h: float, pal):
    fig, ax = plt.subplots(figsize=(w, h), dpi=DPI)
    fig.patch.set_facecolor(pal.surface)
    _style(ax, pal)
    return fig, ax


def _to_image(fig, *, expand: bool = True) -> ft.Image:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight",
                facecolor=fig.get_facecolor())
    plt.close(fig)
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return ft.Image(src=f"data:image/png;base64,{b64}",
                    fit=ft.BoxFit.CONTAIN, expand=expand)


def _thin_dates(dates, n_ticks: int = 6):
    if not dates:
        return [], []
    idx = np.linspace(0, len(dates) - 1, min(n_ticks, len(dates))).astype(int)
    return idx, [dates[i] for i in idx]


# --------------------------------------------------------------------------- #
def price_chart(history: History, *, sma_windows: tuple[int, ...] = (50, 200)) -> ft.Image:
    pal = active()
    px = history.prices()
    fig, ax = _fig(7.5, 2.9, pal)
    x = np.arange(px.size)
    ax.plot(x, px, color=pal.accent, linewidth=1.4, label="Close")
    from core.quant.signals import sma
    for n, style in zip(sma_windows, ("--", ":")):
        if px.size >= n:
            ax.plot(x, sma(px, n), style, color=pal.muted, linewidth=1.0,
                    label=f"SMA{n}")
    idx, labels = _thin_dates(history.dates)
    ax.set_xticks(idx)
    ax.set_xticklabels(labels, rotation=0)
    ax.legend(loc="upper left", fontsize=8, facecolor=pal.surface_2,
              edgecolor=pal.border, labelcolor=pal.text)
    ax.set_title(f"{history.symbol} — {len(history)} sessions ({history.source})",
                 fontsize=10, loc="left")
    return _to_image(fig)


def fan_chart(history: History, mc: MCResult, *, tail_sessions: int = 90) -> ft.Image:
    pal = active()
    px = history.prices()[-tail_sessions:]
    fig, ax = _fig(7.5, 3.2, pal)
    hx = np.arange(-px.size + 1, 1)
    fx = np.arange(0, mc.horizon_days + 1)
    ax.plot(hx, px, color=pal.text, linewidth=1.3)
    # Sample paths: faint spaghetti behind the fan.
    if mc.sample_paths is not None:
        for row in mc.sample_paths:
            ax.plot(fx, row, color=pal.muted, linewidth=0.35, alpha=0.25)
    ax.fill_between(fx, mc.fan[5], mc.fan[95], color=pal.accent, alpha=0.16,
                    label="5–95%")
    ax.fill_between(fx, mc.fan[25], mc.fan[75], color=pal.accent, alpha=0.30,
                    label="25–75%")
    ax.plot(fx, mc.fan[50], color=pal.accent, linewidth=1.6, label="Median")
    if mc.target:
        ax.axhline(mc.target, color=pal.success, linewidth=1.0, linestyle="--",
                   label=f"Target {mc.target:,.0f}")
    ax.axvline(0, color=pal.border, linewidth=0.8)
    ax.legend(loc="upper left", fontsize=8, facecolor=pal.surface_2,
              edgecolor=pal.border, labelcolor=pal.text)
    ax.set_title(f"{mc.symbol} — {mc.n_paths:,} {mc.model.upper()} paths, "
                 f"{mc.horizon_days} sessions", fontsize=10, loc="left")
    ax.set_xlabel("Sessions from today")
    return _to_image(fig)


def terminal_histogram(mc: MCResult) -> ft.Image:
    pal = active()
    fig, ax = _fig(7.5, 2.6, pal)
    ax.hist(mc.terminal, bins=60, color=pal.accent, alpha=0.85,
            edgecolor=pal.surface)
    ax.axvline(mc.spot, color=pal.text, linewidth=1.2, label=f"Spot {mc.spot:,.0f}")
    var_price = mc.spot * (1 - mc.var_pct)
    ax.axvline(var_price, color=pal.error, linewidth=1.2, linestyle="--",
               label=f"VaR{mc.var_level * 100:.0f} {var_price:,.0f}")
    if mc.target:
        ax.axvline(mc.target, color=pal.success, linewidth=1.2, linestyle="--",
                   label=f"Target {mc.target:,.0f}")
    ax.legend(loc="upper right", fontsize=8, facecolor=pal.surface_2,
              edgecolor=pal.border, labelcolor=pal.text)
    ax.set_title("Terminal price distribution", fontsize=10, loc="left")
    return _to_image(fig)


def equity_chart(bt: BacktestResult) -> ft.Image:
    pal = active()
    fig, ax = _fig(7.5, 3.0, pal)
    x = np.arange(bt.equity.size)
    ax.plot(x, bt.bench_equity, color=pal.muted, linewidth=1.1, label="Buy & hold")
    ax.plot(x, bt.equity, color=pal.accent, linewidth=1.5,
            label=f"{bt.strategy}")
    # Shade the periods the strategy is in the market.
    inmkt = bt.position > 0
    ax.fill_between(x, 0, 1, where=inmkt, transform=ax.get_xaxis_transform(),
                    color=pal.success, alpha=0.06)
    idx, labels = _thin_dates(bt.dates)
    ax.set_xticks(idx)
    ax.set_xticklabels(labels)
    ax.legend(loc="upper left", fontsize=8, facecolor=pal.surface_2,
              edgecolor=pal.border, labelcolor=pal.text)
    ax.set_title(f"{bt.symbol} — growth of 1.0 (shaded: in market)",
                 fontsize=10, loc="left")
    return _to_image(fig)


def frontier_chart(frontier: Frontier,
                   marked: list[OptimizedPortfolio] | None = None) -> ft.Image:
    pal = active()
    fig, ax = _fig(7.5, 3.4, pal)
    sc = ax.scatter(frontier.cloud_vols * 100, frontier.cloud_rets * 100,
                    c=frontier.cloud_sharpes, cmap="viridis", s=6, alpha=0.5)
    cbar = fig.colorbar(sc, ax=ax, fraction=0.04, pad=0.02)
    cbar.set_label("Sharpe", color=pal.muted, fontsize=8)
    cbar.ax.tick_params(colors=pal.muted, labelsize=7)
    cbar.outline.set_edgecolor(pal.border)
    if frontier.vols.size:
        ax.plot(frontier.vols * 100, frontier.rets * 100, color=pal.text,
                linewidth=1.6, label="Efficient frontier")
    markers = {"max_sharpe": ("*", pal.success, 180),
               "min_vol": ("D", pal.accent, 60),
               "risk_parity": ("s", pal.error, 60),
               "equal_weight": ("o", pal.muted, 60)}
    for p in marked or []:
        m, c, s = markers.get(p.objective, ("o", pal.text, 60))
        ax.scatter([p.ann_vol * 100], [p.ann_return * 100], marker=m, s=s,
                   color=c, edgecolors=pal.surface, zorder=5,
                   label=p.objective.replace("_", " "))
    ax.set_xlabel("Annualized volatility (%)")
    ax.set_ylabel("Annualized return (%)")
    ax.legend(loc="lower right", fontsize=8, facecolor=pal.surface_2,
              edgecolor=pal.border, labelcolor=pal.text)
    ax.set_title("Risk / return — random portfolios and the frontier",
                 fontsize=10, loc="left")
    return _to_image(fig)


def corr_heatmap(corr: np.ndarray, symbols: tuple[str, ...]) -> ft.Image:
    pal = active()
    n = len(symbols)
    fig, ax = _fig(max(3.4, 0.65 * n + 1.6), max(2.8, 0.55 * n + 1.2), pal)
    ax.grid(False)
    im = ax.imshow(corr, cmap="RdYlGn_r", vmin=-1, vmax=1)
    ax.set_xticks(range(n)); ax.set_xticklabels(symbols, rotation=45, ha="right")
    ax.set_yticks(range(n)); ax.set_yticklabels(symbols)
    for i in range(n):
        for j in range(n):
            ax.text(j, i, f"{corr[i, j]:.2f}", ha="center", va="center",
                    fontsize=8, color="#111111")
    cbar = fig.colorbar(im, ax=ax, fraction=0.045, pad=0.03)
    cbar.ax.tick_params(colors=pal.muted, labelsize=7)
    cbar.outline.set_edgecolor(pal.border)
    ax.set_title("Return correlation", fontsize=10, loc="left")
    return _to_image(fig, expand=False)


def cond_vol_chart(history: History, fit: GarchFit, *, window: int = 20) -> ft.Image:
    """Annualised GARCH conditional vol against rolling realised vol, with the
    unconditional level dashed. Both series are aligned on the return dates."""
    pal = active()
    ann = np.sqrt(TRADING_DAYS)
    cond = np.asarray(fit.cond_vol, dtype=float) * ann * 100
    r = history.log_returns()[-cond.size:]
    fig, ax = _fig(7.5, 2.9, pal)
    x = np.arange(cond.size)
    if r.size >= window:
        real = np.lib.stride_tricks.sliding_window_view(r, window).std(axis=1, ddof=1) * ann * 100
        ax.plot(x[window - 1:], real, color=pal.muted, linewidth=1.0,
                label=f"Realised {window}d")
    ax.plot(x, cond, color=pal.accent, linewidth=1.4, label="GARCH conditional")
    if np.isfinite(fit.uncond_vol):
        ax.axhline(fit.uncond_vol * 100, color=pal.text, linewidth=1.0,
                   linestyle="--", label=f"Unconditional {fit.uncond_vol * 100:.1f}%")
    idx, labels = _thin_dates(list(history.dates[-cond.size:]))
    ax.set_xticks(idx)
    ax.set_xticklabels(labels)
    ax.set_ylabel("Annualised vol (%)")
    ax.legend(loc="upper left", fontsize=8, facecolor=pal.surface_2,
              edgecolor=pal.border, labelcolor=pal.text)
    half = f"{fit.half_life:.0f}" if np.isfinite(fit.half_life) else "inf"
    ax.set_title(f"{history.symbol} — GARCH(1,1)-{fit.dist} conditional vol, "
                 f"persistence {fit.persistence:.3f}, half-life {half} sessions",
                 fontsize=10, loc="left")
    return _to_image(fig)
