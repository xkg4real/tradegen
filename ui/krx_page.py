"""KRX: the Korean coverage the skill library does not have.

Every one of the 72 skills targets US equities, crypto or CME futures — a grep
for KOSPI/KOSDAQ/KRX across the whole repository returns nothing. This page is
NEXTGEN's own read-only Korean data surface, sitting on KIS, OpenDART and the
KRX Open API.

The rule this page follows, which the old EODHD build did not: **an empty result
must state which provider was asked and why it declined.** A screen of dashes
that could equally mean "market is closed", "you have no key", or "the endpoint
is blocked" is worse than an error message.
"""
from __future__ import annotations

from typing import Callable, Optional

import flet as ft

from core.numfmt import format_compact, format_number, format_price
from core.theme import RADII, active
from data.krx import KRXGateway
from ui.components import chip, empty_state, key_value, notice, section

_LOOKUPS = [
    ("quote", "Quote"),
    ("daily", "Daily OHLCV"),
    ("filings", "Disclosures (DART)"),
    ("financials", "Financials (DART)"),
    ("snapshot", "Whole-market snapshot"),
    ("indices", "Index levels"),
]


def build_krx_page(page: ft.Page, gateway: KRXGateway, *, locale: str = "en",
                   on_open_settings: Optional[Callable] = None) -> ft.Control:
    pal = active()
    ticker = ft.TextField(label="KRX code", hint_text="005930", width=180,
                          border_radius=RADII["md"])
    lookup = ft.Dropdown(label="Data", width=230, value="quote",
                         options=[ft.dropdown.Option(k, v) for k, v in _LOOKUPS])
    busy = ft.ProgressRing(visible=False, width=20, height=20)
    result_host = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO, expand=True)

    statuses = gateway.status()
    ready_names = [s["provider"] for s in statuses if s.get("ready")]

    def provider_bar() -> ft.Control:
        chips = []
        for s in statuses:
            chips.append(chip(f"{s['provider']}: " + ("ready" if s.get("ready") else "not set"),
                              "success" if s.get("ready") else "muted",
                              tooltip=s.get("reason") or s.get("detail") or ""))
        return ft.Row(chips, spacing=6, wrap=True)

    def show_empty() -> None:
        if ready_names:
            result_host.controls = [empty_state(
                "Choose a dataset and press Run",
                "Results always carry the provider that produced them.",
                icon=ft.Icons.QUERY_STATS)]
        else:
            result_host.controls = [empty_state(
                "No Korean data provider is configured",
                "KIS needs KIS_APP_KEY + KIS_APP_SECRET, OpenDART needs "
                "OPENDART_API_KEY, and the KRX Open API needs KRX_API_KEY. "
                "All three are free to register; KRX's keyless export is blocked.",
                icon=ft.Icons.KEY_OFF_OUTLINED,
                action=ft.Button("Open Settings",
                                 on_click=lambda e: on_open_settings and on_open_settings())
                if on_open_settings else None)]

    def render_rows(rows: list[dict], columns: list[tuple[str, str]], source: str) -> None:
        head = ft.Row([ft.Text(f"Source: {source}", size=11, color=pal.muted),
                       ft.Text(f"{len(rows)} rows", size=11, color=pal.muted)], spacing=14)
        table = ft.DataTable(
            columns=[ft.DataColumn(ft.Text(label, size=11)) for _, label in columns],
            rows=[ft.DataRow(cells=[ft.DataCell(ft.Text(_cell(r.get(k)), size=11))
                                    for k, _ in columns]) for r in rows[:300]],
            column_spacing=18, heading_row_height=34, data_row_max_height=34,
        )
        result_host.controls = [head, ft.Row([table], scroll=ft.ScrollMode.AUTO)]

    def _cell(value) -> str:
        if value is None or value == "":
            return "—"
        if isinstance(value, float):
            return format_number(value, locale, 2)
        return str(value)

    def run(e=None) -> None:
        code = (ticker.value or "").strip()
        kind = lookup.value or "quote"
        busy.visible = True
        result_host.controls = []
        page.update()

        def worker():
            try:
                if kind == "quote":
                    answer = gateway.quote(code)
                    if answer.ok and answer.data is not None:
                        q = answer.data
                        result_host.controls = [
                            ft.Text(f"{q.name or q.ticker} ({q.ticker})", size=18,
                                    weight=ft.FontWeight.BOLD, color=pal.text),
                            ft.Text(format_price(q.price, q.currency, locale) if q.price
                                    else "—", size=30, weight=ft.FontWeight.BOLD,
                                    color=pal.text),
                            ft.Column([
                                key_value("Change", _cell(q.change)),
                                key_value("Change %", _cell(q.change_pct)),
                                key_value("Open / High / Low",
                                          f"{_cell(q.open)} / {_cell(q.high)} / {_cell(q.low)}"),
                                key_value("Volume", format_compact(q.volume, locale, 1)
                                          if q.volume else "—"),
                                key_value("Market cap", format_compact(q.market_cap, locale, 1)
                                          if q.market_cap else "—"),
                                key_value("Source", f"{answer.source} · as of {q.as_of}"),
                            ], spacing=6),
                        ]
                    else:
                        result_host.controls = [notice(answer.reason, "error",
                                                       icon=ft.Icons.CLOUD_OFF_OUTLINED)]
                elif kind == "daily":
                    answer = gateway.daily(code)
                    if answer.ok and answer.data:
                        render_rows(answer.data,
                                    [("date", "Date"), ("open", "Open"), ("high", "High"),
                                     ("low", "Low"), ("close", "Close"), ("volume", "Volume")],
                                    answer.source)
                    else:
                        result_host.controls = [notice(answer.reason, "error",
                                                       icon=ft.Icons.CLOUD_OFF_OUTLINED)]
                elif kind == "filings":
                    answer = gateway.filings(code)
                    if answer.ok and answer.data:
                        render_rows(answer.data,
                                    [("date", "Date"), ("title", "Report"),
                                     ("filer", "Filer"), ("receipt_no", "Receipt")],
                                    answer.source)
                    else:
                        result_host.controls = [notice(answer.reason, "error",
                                                       icon=ft.Icons.CLOUD_OFF_OUTLINED)]
                elif kind == "financials":
                    answer = gateway.financials(code)
                    if answer.ok and answer.data:
                        render_rows(answer.data,
                                    [("statement", "Statement"), ("account", "Account"),
                                     ("this_term", "This term"), ("prev_term", "Prev term")],
                                    answer.source)
                    else:
                        result_host.controls = [notice(answer.reason, "error",
                                                       icon=ft.Icons.CLOUD_OFF_OUTLINED)]
                elif kind == "snapshot":
                    answer = gateway.market_snapshot()
                    if answer.ok and answer.data:
                        render_rows(answer.data,
                                    [("ticker", "Code"), ("name", "Name"), ("market", "Market"),
                                     ("close", "Close"), ("change_pct", "Chg %"),
                                     ("volume", "Volume"), ("market_cap", "Mkt cap")],
                                    answer.source)
                    else:
                        result_host.controls = [notice(answer.reason, "error",
                                                       icon=ft.Icons.CLOUD_OFF_OUTLINED)]
                else:
                    answer = gateway.indices()
                    if answer.ok and answer.data:
                        render_rows(answer.data,
                                    [("name", "Index"), ("level", "Level"),
                                     ("change", "Change"), ("change_pct", "Chg %")],
                                    answer.source)
                    else:
                        result_host.controls = [notice(answer.reason, "error",
                                                       icon=ft.Icons.CLOUD_OFF_OUTLINED)]
            except Exception as exc:
                result_host.controls = [notice(f"{type(exc).__name__}: {exc}", "error",
                                               icon=ft.Icons.ERROR_OUTLINE)]
            busy.visible = False
            page.update()

        page.run_thread(worker)

    show_empty()

    return ft.Column([
        section("KRX", subtitle="Read-only Korean market data. Quotes and OHLCV from KIS, "
                                "disclosures from OpenDART, snapshots from the KRX Open API."),
        provider_bar(),
        notice("The skill library has no KRX coverage; this page is NEXTGEN's own. "
               "No order or account-mutation path exists in this build.",
               "muted", icon=ft.Icons.INFO_OUTLINE),
        ft.Row([ticker, lookup,
                ft.Button("Run", icon=ft.Icons.PLAY_ARROW_ROUNDED, on_click=run), busy],
               spacing=10, wrap=True),
        ft.Container(result_host, padding=14, bgcolor=pal.surface,
                     border=ft.Border.all(1, pal.border), border_radius=RADII["lg"],
                     expand=True),
    ], spacing=14, expand=True)
