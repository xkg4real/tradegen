"""Portfolio — Markowitz optimization, risk parity, and basket risk.

The operator lists symbols; the page aligns their histories, computes the
joint return statistics, solves all four objectives (so the frontier chart can
mark them against each other), and details the one selected: weights, risk
contributions, correlation structure, and the written read.

Weight and risk-contribution bars are drawn with the container technique the
rest of the app uses — a weight is a proportion, and `expand` weights render
proportions exactly at any pane width.
"""
from __future__ import annotations

from typing import Callable, Optional

import flet as ft
import numpy as np

from core.quant.history import HistoryError, convention_warning, load_history
from core.quant.optimize import OBJECTIVES, efficient_frontier, optimize_portfolio
from core.quant.risk import align_histories
from core.quant import insights
from core.theme import RADII, active
from ui.ai_panel import analysis_panel
from ui.components import card, chip, empty_state, notice, section
import ui.qcharts as qcharts

_OBJ_LABELS = {"max_sharpe": "Max Sharpe", "min_vol": "Minimum volatility",
               "risk_parity": "Risk parity", "equal_weight": "Equal weight"}
_SOURCES = [("auto", "Auto"), ("fmp", "FMP"), ("kis", "KIS (KRX)"),
            ("yfinance", "Yahoo (total return)"), ("synthetic", "Synthetic demo")]


def _bar(fraction: float, token: str) -> ft.Control:
    pal = active()
    filled = max(0, min(100, int(round(fraction * 100))))
    parts: list[ft.Control] = []
    if filled:
        parts.append(ft.Container(expand=filled,
                                  bgcolor=getattr(pal, token, pal.accent),
                                  border_radius=RADII["sm"]))
    if 100 - filled:
        parts.append(ft.Container(expand=100 - filled))
    return ft.Container(ft.Row(parts, spacing=0), height=14,
                        bgcolor=pal.surface_2,
                        border=ft.Border.all(1, pal.border),
                        border_radius=RADII["sm"], expand=True)


def _weight_rows(symbols, weights, risk_contrib) -> ft.Control:
    pal = active()
    rows: list[ft.Control] = [ft.Row([
        ft.Container(width=80),
        ft.Text("Weight", size=10, color=pal.muted, expand=True),
        ft.Container(width=46),
        ft.Text("Risk contribution", size=10, color=pal.muted, expand=True),
        ft.Container(width=46),
    ], spacing=8)]
    order = np.argsort(-np.asarray(weights))
    for i in order:
        w, rc = float(weights[i]), float(risk_contrib[i])
        rows.append(ft.Row([
            ft.Text(symbols[i], size=12, color=pal.text, width=80,
                    weight=ft.FontWeight.W_600),
            _bar(w, "accent"),
            ft.Text(f"{w * 100:.1f}%", size=11, color=pal.text, width=46,
                    text_align=ft.TextAlign.RIGHT),
            _bar(rc, "error"),
            ft.Text(f"{rc * 100:.1f}%", size=11, color=pal.text, width=46,
                    text_align=ft.TextAlign.RIGHT),
        ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER))
    return ft.Column(rows, spacing=6)


def build_portfolio_page(page: ft.Page,
                         on_open_settings: Optional[Callable] = None) -> ft.Control:
    pal = active()

    symbols = ft.TextField(label="Symbols (comma separated)",
                           hint_text="AAPL, MSFT, NVDA, TLT, GLD",
                           value="AAPL, MSFT, NVDA, TLT", expand=True,
                           border_radius=RADII["md"])
    source = ft.Dropdown(label="Data source", width=180, value="auto",
                         options=[ft.dropdown.Option(k, v) for k, v in _SOURCES])
    objective = ft.Dropdown(label="Objective", width=200, value="max_sharpe",
                            options=[ft.dropdown.Option(o, _OBJ_LABELS[o])
                                     for o in OBJECTIVES])
    max_w = ft.TextField(label="Max weight/asset", width=140, value="1.0",
                         border_radius=RADII["md"])
    rf = ft.TextField(label="Risk-free %", width=110, value="3.0",
                      border_radius=RADII["md"])
    busy = ft.ProgressRing(visible=False, width=20, height=20)
    result_host = ft.Column(spacing=14)

    def run(e=None) -> None:
        busy.visible = True
        result_host.controls = []
        page.update()

        def worker():
            try:
                syms = [s.strip().upper() for s in (symbols.value or "").split(",")
                        if s.strip()]
                if len(syms) < 2:
                    raise ValueError("List at least two symbols, comma separated.")
                if len(syms) > 15:
                    raise ValueError("At most 15 symbols — the covariance of more "
                                     "is not estimable on two years of dailies.")
                rf_rate = float(rf.value or "3.0") / 100.0
                cap = float(max_w.value or "1.0")
                hists = [load_history(s, source=source.value or "auto") for s in syms]
                stats = align_histories(hists)
                ports = {o: optimize_portfolio(stats, objective=o, rf_rate=rf_rate,
                                               max_weight=cap if o == (objective.value or "max_sharpe") else 1.0)
                         for o in OBJECTIVES}
                chosen = ports[objective.value or "max_sharpe"]
                frontier = efficient_frontier(stats, rf_rate=rf_rate)
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

            synth = [h.symbol for h in hists if h.source == "SYNTHETIC"]
            blocks: list[ft.Control] = []
            if synth:
                blocks.append(notice(
                    f"Synthetic data for {', '.join(synth)} — no provider is "
                    "configured for them. Weights on simulated series are a "
                    "demonstration, not an allocation.", "error",
                    icon=ft.Icons.SCIENCE_OUTLINED))
            mixed = convention_warning(hists)
            if mixed:
                blocks.append(notice(mixed, "error", icon=ft.Icons.ERROR_OUTLINE))
            blocks.append(ft.Row([
                chip(f"{h.symbol}: {h.source}" + (" · cached" if "cached" in h.note else ""),
                     "muted" if h.source == "SYNTHETIC" else "success", tooltip=h.note)
                for h in hists], spacing=6, wrap=True))
            blocks.append(ft.Row([
                chip(f"{_OBJ_LABELS[chosen.objective]}", "accent"),
                chip(f"return {chosen.ann_return * 100:+.1f}%/yr"),
                chip(f"vol {chosen.ann_vol * 100:.1f}%"),
                chip(f"Sharpe {chosen.sharpe:.2f}",
                     "success" if chosen.sharpe > 1 else "muted"),
                chip(f"{stats.sessions} shared sessions"),
            ] + ([chip("solver did not converge", "error")]
                 if not chosen.converged else []), spacing=6, wrap=True))
            blocks.append(card(_weight_rows(chosen.symbols, chosen.weights,
                                            chosen.risk_contrib)))

            # All four objectives, side by side.
            comparison = [ft.Row([
                ft.Text("Objective", size=10, color=pal.muted, width=150),
                ft.Text("Return", size=10, color=pal.muted, width=70),
                ft.Text("Vol", size=10, color=pal.muted, width=70),
                ft.Text("Sharpe", size=10, color=pal.muted, width=70),
            ], spacing=8)]
            for o in OBJECTIVES:
                p = ports[o]
                em = ft.FontWeight.W_600 if o == chosen.objective else ft.FontWeight.W_400
                comparison.append(ft.Row([
                    ft.Text(_OBJ_LABELS[o], size=12, color=pal.text, width=150, weight=em),
                    ft.Text(f"{p.ann_return * 100:+.1f}%", size=12, color=pal.text, width=70, weight=em),
                    ft.Text(f"{p.ann_vol * 100:.1f}%", size=12, color=pal.text, width=70, weight=em),
                    ft.Text(f"{p.sharpe:.2f}", size=12, color=pal.text, width=70, weight=em),
                ], spacing=8))
            blocks.append(card(ft.Column(comparison, spacing=6)))

            blocks.append(card(qcharts.frontier_chart(frontier, list(ports.values()))))
            blocks.append(card(qcharts.corr_heatmap(stats.corr, stats.symbols)))

            payload = {
                "objective": chosen.objective,
                "symbols": list(chosen.symbols),
                "weights": [round(float(w), 4) for w in chosen.weights],
                "risk_contributions": [round(float(x), 4) for x in chosen.risk_contrib],
                "ann_return": chosen.ann_return, "ann_vol": chosen.ann_vol,
                "sharpe": chosen.sharpe, "converged": chosen.converged,
                "rf_rate": rf_rate, "shared_sessions": stats.sessions,
                "correlation": [[round(float(c), 3) for c in row] for row in stats.corr],
                "alternatives": {o: {"return": ports[o].ann_return,
                                     "vol": ports[o].ann_vol,
                                     "sharpe": ports[o].sharpe} for o in OBJECTIVES},
                "synthetic_symbols": synth,
            }
            blocks.append(analysis_panel(page, kind="portfolio_optimization",
                                         narrative=insights.narrate_portfolio(chosen),
                                         payload_fn=lambda p=payload: p))
            result_host.controls = blocks
            busy.visible = False
            page.update()

        page.run_thread(worker)

    result_host.controls = [empty_state(
        "Build a portfolio",
        "List symbols and pick an objective. All four objectives are computed "
        "and marked on the frontier so the trade-offs are visible, not implied.",
        icon=ft.Icons.PIE_CHART_OUTLINE)]

    return ft.Column([
        section("Portfolio", subtitle="Mean-variance optimization, risk parity, and the "
                                      "efficient frontier — solved with scipy on aligned "
                                      "daily histories."),
        ft.Row([symbols, source, objective, max_w, rf,
                ft.Button("Optimize", icon=ft.Icons.PLAY_ARROW_ROUNDED, on_click=run),
                busy], spacing=10, wrap=True),
        ft.Column([result_host], scroll=ft.ScrollMode.AUTO, expand=True),
    ], spacing=14, expand=True)
