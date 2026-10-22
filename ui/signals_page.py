"""Signals — the technical read on one instrument, and the backtest that
keeps it honest.

Top half: the composite signal with its components drawn as signed bars
(bullish fills right in green, bearish fills left in red — the sign is
spatial, not just chromatic). Bottom half: the selected rule strategy run
against the same history with costs, next to buy-and-hold, because a signal
whose strategy loses to its own underlying should have to say so on the same
screen that painted it green.
"""
from __future__ import annotations

from typing import Callable, Optional

import flet as ft

from core.quant.backtest import STRATEGIES, run_backtest
from core.quant.history import HistoryError, load_history
from core.quant.signals import SignalReport, compute_signals
from core.quant import insights
from core.theme import RADII, active
from ui.ai_panel import analysis_panel
from ui.components import card, chip, empty_state, notice, section
import ui.qcharts as qcharts

_SOURCES = [("auto", "Auto"), ("fmp", "FMP"), ("kis", "KIS (KRX)"),
            ("synthetic", "Synthetic demo")]
SIGNALS_NOTICE = "Context only — not a v2 signal (DO-NOT-BUILD TF-12). Nothing here feeds a book."
_STRAT_LABELS = {"ma_cross": "MA cross (fast/slow)",
                 "momentum": "Momentum (lookback)",
                 "rsi_revert": "RSI mean reversion"}


def _signed_bar(score: float) -> ft.Control:
    """A bar centered at zero: [-100..0] fills leftward red, [0..100] rightward
    green. Both halves are 100 expand-units wide, so scale is identical."""
    pal = active()
    s = max(-100.0, min(100.0, score))
    left_fill = int(round(-s)) if s < 0 else 0
    right_fill = int(round(s)) if s > 0 else 0
    left = ft.Row([
        ft.Container(expand=100 - left_fill),
        ft.Container(expand=left_fill, bgcolor=pal.error,
                     border_radius=RADII["sm"]) if left_fill else ft.Container(),
    ], spacing=0, expand=True)
    right = ft.Row([
        ft.Container(expand=right_fill, bgcolor=pal.success,
                     border_radius=RADII["sm"]) if right_fill else ft.Container(),
        ft.Container(expand=100 - right_fill),
    ], spacing=0, expand=True)
    return ft.Container(
        ft.Row([left,
                ft.Container(width=2, bgcolor=pal.border),
                right], spacing=0),
        height=14, bgcolor=pal.surface_2, border=ft.Border.all(1, pal.border),
        border_radius=RADII["sm"], expand=True)


def _signal_block(report: SignalReport) -> ft.Control:
    pal = active()
    stance_token = ("success" if report.composite > 15
                    else "error" if report.composite < -15 else "muted")
    rows: list[ft.Control] = [ft.Row([
        ft.Text("Composite", size=12, color=pal.text, width=170,
                weight=ft.FontWeight.W_600),
        _signed_bar(report.composite),
        ft.Text(f"{report.composite:+.0f}", size=13, width=44,
                color=getattr(pal, stance_token), weight=ft.FontWeight.BOLD,
                text_align=ft.TextAlign.RIGHT),
        chip(report.stance, stance_token),
    ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        ft.Divider(color=pal.border, height=9)]
    for c in report.components:
        rows.append(ft.Column([
            ft.Row([
                ft.Text(c.label, size=11, color=pal.text, width=170,
                        max_lines=2, tooltip=c.value or c.label),
                _signed_bar(c.score),
                ft.Text(f"{c.score:+.0f}", size=11, width=44,
                        color=pal.success if c.score > 0 else
                        (pal.error if c.score < 0 else pal.muted),
                        weight=ft.FontWeight.W_600,
                        text_align=ft.TextAlign.RIGHT),
                ft.Text(f"{c.weight * 100:.0f}%", size=10, color=pal.muted,
                        width=32, text_align=ft.TextAlign.RIGHT,
                        tooltip="Weight in the composite"),
            ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ft.Row([ft.Container(width=170),
                    ft.Text(c.reason, size=10, color=pal.muted, expand=True,
                            max_lines=2)], spacing=8),
        ], spacing=2))
    return ft.Column(rows, spacing=6)


def build_signals_page(page: ft.Page,
                       on_open_settings: Optional[Callable] = None) -> ft.Control:
    pal = active()

    symbol = ft.TextField(label="Symbol", hint_text="AAPL or 005930", width=160,
                          border_radius=RADII["md"], value="AAPL")
    source = ft.Dropdown(label="Data source", width=180, value="auto",
                         options=[ft.dropdown.Option(k, v) for k, v in _SOURCES])
    strategy = ft.Dropdown(label="Backtest strategy", width=220, value="ma_cross",
                           options=[ft.dropdown.Option(s, _STRAT_LABELS[s])
                                    for s in STRATEGIES])
    p_fast = ft.TextField(label="Fast/lookback", width=120, value="20",
                          border_radius=RADII["md"],
                          tooltip="ma_cross: fast SMA · momentum: lookback · "
                                  "rsi_revert: RSI period")
    p_slow = ft.TextField(label="Slow/exit", width=110, value="50",
                          border_radius=RADII["md"],
                          tooltip="ma_cross: slow SMA · rsi_revert: exit-above "
                                  "RSI level · momentum: unused")
    cost = ft.TextField(label="Cost (bps)", width=100, value="10",
                        border_radius=RADII["md"])
    busy = ft.ProgressRing(visible=False, width=20, height=20)
    result_host = ft.Column(spacing=14)

    def _params(strat: str) -> dict:
        a = float(p_fast.value or "20")
        b = float(p_slow.value or "50")
        if strat == "ma_cross":
            return {"fast": int(a), "slow": int(b)}
        if strat == "momentum":
            return {"lookback": int(a)}
        return {"period": int(a), "buy_below": 30.0, "exit_above": b}

    def run(e=None) -> None:
        busy.visible = True
        result_host.controls = []
        page.update()

        def worker():
            try:
                strat = strategy.value or "ma_cross"
                hist = load_history(symbol.value, source=source.value or "auto")
                report = compute_signals(hist)
                bt = run_backtest(hist, strategy=strat, params=_params(strat),
                                  cost_bps=float(cost.value or "10"))
            except (HistoryError, ValueError) as exc:
                result_host.controls = [notice(str(exc), "error",
                                               icon=ft.Icons.ERROR_OUTLINE)]
                busy.visible = False
                page.update()
                return
            except Exception as exc:
                result_host.controls = [notice(f"{type(exc).__name__}: {exc}",
                                               "error", icon=ft.Icons.ERROR_OUTLINE)]
                busy.visible = False
                page.update()
                return

            blocks: list[ft.Control] = []
            if hist.source == "SYNTHETIC":
                blocks.append(notice("Synthetic data: " + hist.note, "error",
                                     icon=ft.Icons.SCIENCE_OUTLINED))
            blocks.append(card(qcharts.price_chart(hist)))
            blocks.append(card(_signal_block(report)))
            wr = (f"{bt.win_rate * 100:.0f}%" if bt.win_rate is not None else "—")
            blocks.append(ft.Row([
                chip(f"{_STRAT_LABELS[bt.strategy]}", "accent"),
                chip(f"strategy {bt.total_return * 100:+.1f}%",
                     "success" if bt.beat_benchmark else "error"),
                chip(f"buy & hold {bt.bench_return * 100:+.1f}%"),
                chip(f"Sharpe {bt.sharpe:.2f}"),
                chip(f"max DD {bt.max_drawdown * 100:.1f}%"),
                chip(f"exposure {bt.exposure * 100:.0f}%"),
                chip(f"{bt.n_trades} trades · win {wr}"),
            ] + ([chip(f"{hist.source}: {hist.note}")]
                 if hist.note and hist.source != "SYNTHETIC" else []), spacing=6, wrap=True))
            blocks.append(card(qcharts.equity_chart(bt)))

            payload = {
                "symbol": report.symbol, "data_source": hist.source,
                "last_price": report.last_price,
                "composite": report.composite, "stance": report.stance,
                "components": [{"label": c.label, "score": c.score,
                                "weight": c.weight, "reason": c.reason}
                               for c in report.components],
                "backtest": {
                    "strategy": bt.strategy, "params": bt.params,
                    "total_return": bt.total_return,
                    "benchmark_return": bt.bench_return,
                    "ann_vol": bt.ann_vol, "sharpe": bt.sharpe,
                    "max_drawdown": bt.max_drawdown,
                    "benchmark_max_drawdown": bt.bench_max_drawdown,
                    "exposure": bt.exposure, "n_trades": bt.n_trades,
                    "win_rate": bt.win_rate, "cost_bps": bt.cost_bps,
                },
            }
            narrative = (insights.narrate_signals(report) + " " +
                         insights.narrate_backtest(bt))
            blocks.append(analysis_panel(page, kind="signals_and_backtest",
                                         narrative=narrative,
                                         payload_fn=lambda p=payload: p))
            result_host.controls = blocks
            busy.visible = False
            page.update()

        page.run_thread(worker)

    result_host.controls = [empty_state(
        "Read a chart, then make the read prove itself",
        "The composite signal and its components render above the backtest of "
        "the same idea on the same history, with costs.",
        icon=ft.Icons.CANDLESTICK_CHART_OUTLINED)]

    return ft.Column([
        section("Signals", subtitle="Technical composite with dissent shown, and a "
                                    "costed backtest against buy-and-hold."),
        notice(SIGNALS_NOTICE, "accent", icon=ft.Icons.LOCK_OUTLINE),
        ft.Row([symbol, source, strategy, p_fast, p_slow, cost,
                ft.Button("Analyze", icon=ft.Icons.PLAY_ARROW_ROUNDED, on_click=run),
                busy], spacing=10, wrap=True),
        ft.Column([result_host], scroll=ft.ScrollMode.AUTO, expand=True),
    ], spacing=14, expand=True)
