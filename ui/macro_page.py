"""Macro — a view selector over the cross-asset sheet and the v2 overlay state.

"Macro sheet" (default): pick a source, press Refresh, and the page shows the
descriptive-read chips (a descriptive read, not a regime model, P19), the headline levels, the indicator table (last, 1d/1w/1m changes, 1y z-score
and percentile), the z-score chart, and an analysis card. "Daily market
commentary" and "Weekly rates/FX strategy" swap that card for the report's
local narrative and a deep-analysis panel with the matching `kind`, routed
through `core.ficc.insights.deep_analysis` so the report-format instructions
are appended to whatever the operator asks.

Formatting happens here and nowhere else: the core hands over decimals, this
page prints percent, basis points, or raw levels according to each row's unit.
A sheet with SYNTHETIC rows says so loudly and hatches them in the chart.

"Overlay state" (`ui.macro_state_panel`), "Model cards" (`ui.macro_cards_view`) and
"Research register" (`ui.research_view`): the v2 views, each built on first selection
with its own Refresh; all four share the app's 180 ms switcher.
"""
from __future__ import annotations

from typing import Callable, Optional

import flet as ft

import config
from core.ficc import insights
from core.ficc.common import BP, FICCError
from core.ficc.macro import DESCRIPTIVE_READ_NOTE, MacroRow, MacroSheet, Regime, daily_brief, macro_sheet, weekly_brief
from core.theme import TRANSITION_MS, active
from ui.ai_panel import analysis_panel
from ui.components import card, chip, empty_state, notice, section, stat
import ui.fcharts as fcharts
from ui.macro_cards_view import build_cards_view
from ui.macro_state_panel import build_overlay_view
from ui.research_view import build_research_view

_SOURCES = [("auto", "Auto (FRED + Yahoo, synthetic fallback)"),
            ("fred", "Live only (FRED + Yahoo, no fallback)"),
            ("synthetic", "Synthetic demo")]
_HEADLINE = ("DGS2", "DGS10", "DGS30", "T10Y2Y", "DFII10", "T10YIE",
             "VIXCLS", "BAMLH0A0HYM2", "DTWEXBGS")
_REGIME_TOKEN = {"risk-on": "success", "risk-off": "error"}
_COLUMNS = ("Group", "Indicator", "Last", "1d", "1w", "1m", "3m", "z (1y)", "pct (1y)", "Source")
_VIEWS = (("sheet", "Macro sheet"), ("overlay", "Overlay state"), ("cards", "Model cards"),
          ("research", "Research register"))
_BUILDERS = {"overlay": build_overlay_view, "cards": build_cards_view,     # view key -> builder(page);
             "research": build_research_view}                             # "sheet" is built inline
DESCRIPTIVE_CAPTION = DESCRIPTIVE_READ_NOTE[:1].upper() + DESCRIPTIVE_READ_NOTE[1:]
_REPORTS = {
    "daily": ("Daily market commentary", "daily_market_commentary"),
    "weekly": ("Weekly rates/FX strategy", "weekly_fi_fx_strategy"),
}


def _level(r: MacroRow) -> str:
    if r.unit == "pct":
        return f"{r.last * 100:.2f}%"
    if r.unit == "bp":
        return f"{r.last / BP:.0f}bp"
    if r.unit == "fx" and r.last < 20:
        return f"{r.last:.4f}"
    return f"{r.last:,.2f}"


def _chg(r: MacroRow, chg: float | None) -> str:
    if chg is None:
        return "-"
    if r.unit in ("pct", "bp"):
        return f"{chg / BP:+.1f}bp"
    if r.unit == "fx" and r.last < 20:
        return f"{chg:+.4f}"
    return f"{chg:+.2f}"


def read_row(rg: Regime) -> ft.Row:
    """The rule-based read of the sheet, captioned as what it is (rulings 3.9; P19). Feeds nothing."""
    pal = active()
    return ft.Row([
        ft.Text(DESCRIPTIVE_CAPTION, size=11, color=pal.muted),
        chip(f"curve: {rg.curve}", "accent"),
        chip(f"risk: {rg.risk}", _REGIME_TOKEN.get(rg.risk, "accent")),
        chip(f"dollar: {rg.dollar}", "accent"),
        chip(f"breakevens: {rg.inflation}", "accent"),
        chip(f"real yields: {rg.real_rates}", "accent"),
    ], spacing=6, wrap=True)


def build_macro_page(page: ft.Page,
                     on_open_settings: Optional[Callable] = None) -> ft.Control:
    pal = active()
    source = ft.Dropdown(label="Data source", width=300, value="auto",
                         options=[ft.dropdown.Option(k, v) for k, v in _SOURCES])
    busy = ft.ProgressRing(visible=False, width=20, height=20)
    result_host = ft.Column(spacing=14)
    analysis_host = ft.Column(spacing=14)

    def provider_bar() -> ft.Control:
        chips = [chip(f"{s['id']}: " + ("ready" if s.get("ready") else "not installed"),
                      "success" if s.get("ready") else "muted", tooltip=s.get("note", ""))
                 for s in config.ficc_provider_status()]
        return ft.Row(chips, spacing=6, wrap=True)

    def cell(text: str, *, token: str = "text") -> ft.DataCell:
        return ft.DataCell(ft.Text(text, size=11, color=getattr(pal, token)))

    def sign_token(x: float | None) -> str:
        return "text" if not x else ("success" if x > 0 else "error")

    def table(sheet: MacroSheet) -> ft.Control:
        rows = []
        for r in sheet.rows:
            rows.append(ft.DataRow(cells=[
                cell(r.group, token="muted"), cell(r.label),
                cell(_level(r)),
                cell(_chg(r, r.chg_1d), token=sign_token(r.chg_1d)),
                cell(_chg(r, r.chg_1w), token=sign_token(r.chg_1w)),
                cell(_chg(r, r.chg_1m), token=sign_token(r.chg_1m)),
                cell(_chg(r, r.chg_3m), token=sign_token(r.chg_3m)),
                cell(f"{r.z_1y:+.2f}", token="error" if abs(r.z_1y) >= 2 else "text"),
                cell(f"{r.pct_1y * 100:.0f}%"),
                cell(r.source, token="error" if r.source == "SYNTHETIC" else "muted"),
            ]))
        dt = ft.DataTable(
            columns=[ft.DataColumn(ft.Text(c, size=11, color=pal.muted),
                                   numeric=i >= 2 and c != "Source")
                     for i, c in enumerate(_COLUMNS)],
            rows=rows, column_spacing=16, heading_row_height=34, data_row_max_height=32)
        return ft.Row([dt], scroll=ft.ScrollMode.AUTO)

    def sheet_analysis(sheet: MacroSheet) -> ft.Control:
        payload = daily_brief(sheet)
        return analysis_panel(page, kind="macro_sheet",
                              narrative=insights.narrate_macro(sheet),
                              payload_fn=lambda p=payload: p,
                              deep_fn=insights.deep_analysis)

    def report(sheet: MacroSheet, which: str) -> None:
        title, kind = _REPORTS[which]
        if which == "daily":
            text, payload = insights.narrate_daily_brief(sheet), daily_brief(sheet)
        else:
            text, payload = insights.narrate_weekly_strategy(sheet), weekly_brief(sheet)
        prompt = insights.report_prompt(kind)
        analysis_host.controls = [
            ft.Row([ft.Text(title, size=15, weight=ft.FontWeight.W_600, color=pal.text),
                    chip(f"kind: {kind}", "accent"), chip(sheet.as_of)], spacing=8, wrap=True),
            ft.Text("Deep-analysis format: " + prompt, size=11, color=pal.muted),
            analysis_panel(page, kind=kind, narrative=text, payload_fn=lambda p=payload: p,
                           deep_fn=insights.deep_analysis),
        ]
        page.update()

    def render(sheet: MacroSheet) -> list[ft.Control]:
        blocks: list[ft.Control] = []
        if sheet.synthetic_ids:
            blocks.append(notice("Synthetic data: " + sheet.note, "error",
                                 icon=ft.Icons.SCIENCE_OUTLINED))
        elif sheet.note:
            blocks.append(notice(sheet.note, "muted"))
        rg = sheet.regime
        blocks.append(ft.Row([chip(f"as of {sheet.as_of}")]
                             + [chip(f"{src}: {n}", "error" if src == "SYNTHETIC" else "success")
                                for src, n in sheet.sources.items()], spacing=6, wrap=True))
        blocks.append(read_row(rg))
        blocks.append(ft.Text(rg.summary, size=12, color=pal.muted, selectable=True))
        tiles = [stat(r.label, _level(r), tooltip=f"1d {_chg(r, r.chg_1d)}, z {r.z_1y:+.2f}",
                      token="error" if abs(r.z_1y) >= 2 else "text")
                 for r in (sheet.row(i) for i in _HEADLINE) if r is not None]
        blocks.append(ft.Row(tiles, spacing=10, wrap=True))
        blocks.append(table(sheet))
        blocks.append(card(ft.Column([
            ft.Text(f"1y z-scores · {DESCRIPTIVE_READ_NOTE}", size=12, color=pal.muted),
            fcharts.macro_z_chart(sheet)], spacing=6)))
        blocks.append(ft.Row([
            ft.Button(_REPORTS["daily"][0], icon=ft.Icons.TODAY_OUTLINED,
                      on_click=lambda e: report(sheet, "daily")),
            ft.Button(_REPORTS["weekly"][0], icon=ft.Icons.DATE_RANGE_OUTLINED,
                      on_click=lambda e: report(sheet, "weekly")),
        ], spacing=10, wrap=True))
        analysis_host.controls = [sheet_analysis(sheet)]
        blocks.append(analysis_host)
        return blocks

    def refresh(e=None) -> None:
        busy.visible = True
        result_host.controls = []
        analysis_host.controls = []
        page.update()

        def worker():
            try:
                sheet = macro_sheet(source=source.value or "auto")
                result_host.controls = render(sheet)
            except (FICCError, ValueError) as exc:
                result_host.controls = [notice(str(exc), "error",
                                               icon=ft.Icons.ERROR_OUTLINE)]
            except Exception as exc:
                result_host.controls = [notice(f"{type(exc).__name__}: {exc}", "error",
                                               icon=ft.Icons.ERROR_OUTLINE)]
            busy.visible = False
            page.update()

        page.run_thread(worker)

    result_host.controls = [empty_state(
        "Press Refresh to load the macro sheet",
        "Treasuries, real and breakeven yields, policy rates, IG/HY spreads, the dollar, "
        "VIX, WTI, the 10y future and gold - FRED and Yahoo are keyless; without them the "
        "sheet runs on clearly labeled synthetic series.",
        icon=ft.Icons.PUBLIC_OUTLINED,
        action=ft.Button("Open Settings", on_click=lambda e: on_open_settings())
        if on_open_settings else None)]

    sheet_view = ft.Column([
        provider_bar(),
        ft.Row([source, ft.Button("Refresh", icon=ft.Icons.REFRESH, on_click=refresh), busy],
               spacing=10, wrap=True),
        ft.Column([result_host], scroll=ft.ScrollMode.AUTO, expand=True),
    ], spacing=14, expand=True)
    views: dict[str, ft.Control] = {"sheet": sheet_view}
    switcher = ft.AnimatedSwitcher(content=sheet_view, duration=TRANSITION_MS,
                                   reverse_duration=TRANSITION_MS, expand=True)

    def switch(e=None) -> None:
        key = view.value or "sheet"
        if key not in views:                    # built on first selection; reads artifacts on its own Refresh
            views[key] = _BUILDERS[key](page)
        switcher.content = views[key]
        page.update()

    view = ft.Dropdown(label="View", width=220, value="sheet", on_select=switch,
                       options=[ft.dropdown.Option(k, v) for k, v in _VIEWS])
    return ft.Column([
        section("Macro", subtitle="Cross-asset sheet (descriptive read), the v2 overlay state, model cards, "
                                  "the research register, and the daily / weekly rates-FX report inputs."),
        view,
        switcher,
    ], spacing=14, expand=True)


# --------------------------------------------------------------------------- #
# Self-check (synthetic only - no network, no running Flet page)
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    from core.ficc.data import Series
    from core.ficc.macro import _row, INDICATORS

    def _fred(ind, values):
        dates = tuple(f"2025-01-{i + 1:02d}" for i in range(len(values)))
        return _row(ind, Series(ind.id, ind.label, "FRED", dates, tuple(values)))

    ten = _fred(INDICATORS[1], [4.0, 4.1, 4.3])                 # DGS10, pct
    assert _level(ten) == "4.30%" and _chg(ten, ten.chg_1d) == "+20.0bp"
    hy = _fred(INDICATORS[9], [3.2, 3.5])                        # HY OAS, bp
    assert _level(hy) == "350bp" and _chg(hy, hy.chg_1d) == "+30.0bp"
    eur = _fred(INDICATORS[11], [1.08, 1.0850])                  # EUR/USD, fx < 20
    assert _level(eur) == "1.0850" and _chg(eur, eur.chg_1d) == "+0.0050"
    jpy = _fred(INDICATORS[12], [150.0, 149.5])                  # USD/JPY, fx >= 20
    assert _level(jpy) == "149.50" and _chg(jpy, jpy.chg_1d) == "-0.50"
    vix = _fred(INDICATORS[14], [18.0, 20.25])                   # level
    assert _level(vix) == "20.25" and _chg(vix, vix.chg_3m) == "-"
    assert _chg(vix, 1234.5) == "+1234.50"

    sheet = macro_sheet(source="synthetic", days=300)
    for r in sheet.rows:
        assert _level(r) and _chg(r, r.chg_1d)
    for which, (title, kind) in _REPORTS.items():
        assert insights.report_prompt(kind), kind
    assert build_macro_page.__name__ == "build_macro_page"
    print("ok")
