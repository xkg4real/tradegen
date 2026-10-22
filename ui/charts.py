"""Bar charts for a step's component scores.

The scoring skills already break their verdict into weighted parts — market
breadth scores six components, uptrend participation five — and a column of
numbers buried in a transcript does not communicate that at a glance. A bar per
component does, which is the point: the operator should be able to see in one
look that breadth is strong and participation is weak, rather than reconstruct
it by reading.

Two deliberate choices:

  * **The bars are built from containers, not `ft.BarChart`.** Component labels
    are long ("S&P 500 vs Breadth Divergence") and there are up to twelve of
    them, which a vertical chart cannot label legibly. Horizontal rows also
    survive Flet's chart API changing under us, which it has.

  * **Width comes from `expand` weights, not pixels.** A score of 73 is a fill
    of `expand=73` against a remainder of `expand=27`, so the chart is correct
    at any pane width without measuring anything.

Colour is never the only channel. Every bar prints its score, and every band
has a word behind it in the tooltip, so the chart is readable without relying
on the red/amber/green distinction.
"""
from __future__ import annotations

from typing import Optional

import flet as ft

from core.skills.insights import Component, Insight
from core.theme import RADII, active
from ui.components import chip, colour_for

BAR_HEIGHT = 16
LABEL_WIDTH = 190


def _track(score: float, token: str) -> ft.Control:
    """One bar. `expand` weights keep it proportional at any width."""
    pal = active()
    filled = max(0, min(100, int(round(score))))
    parts: list[ft.Control] = []
    if filled:
        parts.append(ft.Container(expand=filled, bgcolor=colour_for(token),
                                  border_radius=RADII["sm"]))
    if 100 - filled:
        parts.append(ft.Container(expand=100 - filled))
    return ft.Container(
        content=ft.Row(parts, spacing=0),
        height=BAR_HEIGHT,
        bgcolor=pal.surface_2,
        border=ft.Border.all(1, pal.border),
        border_radius=RADII["sm"],
        expand=True,
    )


def component_bar(component: Component, *, show_signal: bool = True) -> ft.Control:
    pal = active()
    weight = f"{component.weight * 100:.0f}%" if component.weight else ""
    row = ft.Row([
        ft.Text(component.label, size=11, color=pal.text, width=LABEL_WIDTH,
                max_lines=2, tooltip=component.label),
        _track(component.score, component.band),
        ft.Text(f"{component.score:g}", size=11, width=30,
                color=colour_for(component.band), weight=ft.FontWeight.W_600,
                text_align=ft.TextAlign.RIGHT),
        ft.Text(weight, size=10, color=pal.muted, width=34,
                text_align=ft.TextAlign.RIGHT,
                tooltip="Weight in the composite score" if weight else None),
    ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER)

    if not (show_signal and component.signal):
        return ft.Container(row, tooltip=component.signal or None)
    return ft.Container(
        ft.Column([
            row,
            ft.Row([ft.Container(width=LABEL_WIDTH),
                    ft.Text(component.signal, size=10, color=pal.muted,
                            expand=True, max_lines=2)], spacing=8),
        ], spacing=2),
        tooltip=component.signal,
    )


def composite_bar(insight: Insight) -> ft.Control:
    """The headline score, drawn the same way as its parts so the two read
    against each other."""
    pal = active()
    if insight.score is None:
        return ft.Container()
    label = " · ".join(x for x in (insight.zone, insight.guidance) if x)
    return ft.Column([
        ft.Row([
            ft.Text("Composite", size=11, color=pal.text, width=LABEL_WIDTH,
                    weight=ft.FontWeight.W_600),
            _track(insight.score, insight.band),
            ft.Text(f"{insight.score:g}", size=12, width=30,
                    color=colour_for(insight.band), weight=ft.FontWeight.BOLD,
                    text_align=ft.TextAlign.RIGHT),
            ft.Container(width=34),
        ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        ft.Row([ft.Container(width=LABEL_WIDTH),
                ft.Text(label, size=10, color=pal.muted, expand=True)],
               spacing=8) if label else ft.Container(),
    ], spacing=2)


def insight_chart(insight: Insight, *, show_signal: bool = True) -> Optional[ft.Control]:
    """The full picture of one step: composite, components, warnings, facts.

    Returns None when the step produced nothing to draw, so callers can fall
    back to the transcript instead of rendering an empty box.
    """
    pal = active()
    if insight.empty:
        return None
    blocks: list[ft.Control] = []

    if insight.score is not None:
        blocks.append(composite_bar(insight))
    if insight.components:
        if insight.score is not None:
            blocks.append(ft.Divider(color=pal.border, height=9))
        blocks.extend(component_bar(c, show_signal=show_signal)
                      for c in insight.components)
    if insight.facts:
        blocks.append(ft.Row(
            [chip(f"{k}: {v}") for k, v in insight.facts if len(v) <= 40],
            spacing=6, wrap=True))
        long_facts = [(k, v) for k, v in insight.facts if len(v) > 40]
        blocks.extend(
            ft.Text(f"{k}: {v}", size=10, color=pal.muted, selectable=True)
            for k, v in long_facts)
    if insight.warnings:
        blocks.append(ft.Row(
            [chip(w, "error") for w in insight.warnings], spacing=6, wrap=True))
    if insight.quality:
        blocks.append(ft.Text(insight.quality, size=10, color=pal.muted))
    if not insight.components and insight.lines:
        # No structured report: the script's own closing lines, unedited.
        blocks.extend(ft.Text(line, size=11, color=pal.muted, selectable=True,
                              max_lines=2) for line in insight.lines)

    if not blocks:
        return None
    return ft.Column(blocks, spacing=6)
