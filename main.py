"""TRADEGEN — the operator's trading program (split off QUANTGEN 2026-10-23; no order path yet).

Built on the NEXTGEN base (its rule engine, simulated order book, KRX data
layer, and skill cockpit all survive intact) and upgraded with the thing the
client build was contractually forbidden from having: an opinion. Three new
equity surfaces —

  * **Quant Lab** — Monte Carlo simulation (GBM, Merton jump-diffusion, block
    bootstrap) calibrated on daily history, with VaR/CVaR and a percentile fan.
  * **Portfolio** — Markowitz optimization, risk parity, and the efficient
    frontier, solved with scipy on aligned histories.
  * **Signals** — a weighted technical composite with dissent shown, and a
    costed backtest of the same idea against buy-and-hold.

— and, for the FICC desk the operator is training for, five more:

  * **Macro** — the cross-asset sheet (curve, real yields, breakevens, credit,
    dollar, vol) with z-scores, a regime read, and the daily / weekly report.
  * **Rates** — Treasury curve bootstrap, Nelson-Siegel, PCA, swap and swaption
    pricing (Black-76 / Bachelier), short-rate simulation (Vasicek, CIR, HW).
  * **Bonds** — price/yield, duration, convexity, DV01, key-rate DV01, carry and
    roll-down, curve scenarios, futures hedge ratio.
  * **FX** — CIP forwards and basis, Garman-Kohlhagen Greeks, RR/BF smiles with
    a SABR fit, and a G10+KRW carry basket with a no-lookahead backtest.
  * **Structuring** — principal-protected notes, reverse convertibles,
    dual-currency deposits and steepener notes, each with a hedge sheet.

Every result carries two layers of written analysis: a deterministic local
narrative (always), and Claude deep analysis when ANTHROPIC_API_KEY is set.
gs_quant powers realized-vol/drawdown analytics offline and can open a Marquee
session when GS credentials exist. This is a personal build: not a client
deliverable, not for commercial distribution.

TWO FIXES INHERITED FROM NEXTGEN REMAIN LOAD-BEARING
----------------------------------------------------
1. `page.on_resize` — Flet 0.85 does not define `on_resized`; assigning it is
   silently accepted and never fires.
2. Views are built once and cached, so a running simulation or armed engine
   survives a tab switch.
"""
from __future__ import annotations

import flet as ft

import config
from core.skills import reload_all
from core.theme import BREAKPOINTS, RADII, TRANSITION_MS, active, set_mode
from core.engine.feed import QuoteFeed
from core.engine.runtime import EngineRuntime
from core.rules.store import RuleStore
from data.krx import KRXGateway
from ui.bonds_page import build_bonds_page
from ui.crypto_page import build_crypto_page
from ui.derivatives_page import build_derivatives_page
from ui.etf_page import build_etf_page
from ui.fx_page import build_fx_page
from ui.strategy_lab_page import build_strategy_lab_page
from ui.krx_page import build_krx_page
from ui.macro_page import build_macro_page
from ui.portfolio_page import build_portfolio_page
from ui.quant_lab_page import build_quant_lab_page
from ui.rates_page import build_rates_page
from ui.structuring_page import build_structuring_page
from ui.rules_page import build_rules_page
from ui.signals_page import build_signals_page
from ui.trading_page import build_trading_page
from ui.runs_page import build_runs_page
from ui.settings_page import build_settings_page
from ui.skills_page import build_skills_page
from ui.workflows_page import build_workflows_page

LOCALE = "en"

NAV = (
    ("macro", "Macro", ft.Icons.PUBLIC_OUTLINED),
    ("rates", "Rates", ft.Icons.SSID_CHART_ROUNDED),
    ("bonds", "Bonds", ft.Icons.RECEIPT_LONG_OUTLINED),
    ("fx", "FX", ft.Icons.CURRENCY_EXCHANGE_OUTLINED),
    ("structuring", "Structuring", ft.Icons.LAYERS_OUTLINED),
    ("derivatives", "Derivatives", ft.Icons.STACKED_LINE_CHART_OUTLINED),
    ("etf", "ETF", ft.Icons.INVENTORY_2_OUTLINED),
    ("crypto", "Crypto", ft.Icons.CURRENCY_BITCOIN),
    ("lab", "Strategy Lab", ft.Icons.SCIENCE_OUTLINED),
    ("quant", "Quant Lab", ft.Icons.TROUBLESHOOT_OUTLINED),
    ("portfolio", "Portfolio", ft.Icons.PIE_CHART_OUTLINE),
    ("signals", "Signals", ft.Icons.CANDLESTICK_CHART_OUTLINED),
    ("trading", "Execution", ft.Icons.SPEED_ROUNDED),
    ("rules", "Rules", ft.Icons.RULE_FOLDER_OUTLINED),
    ("workflows", "Workflows", ft.Icons.ACCOUNT_TREE_OUTLINED),
    ("skills", "Skills", ft.Icons.EXTENSION_OUTLINED),
    ("krx", "KRX", ft.Icons.SHOW_CHART_ROUNDED),
    ("runs", "Runs", ft.Icons.HISTORY),
    ("settings", "Settings", ft.Icons.SETTINGS_OUTLINED),
)


def main(page: ft.Page) -> None:
    page.title = "TRADEGEN"
    page.padding = 0
    page.theme_mode = ft.ThemeMode.DARK
    page.window.min_width = 420
    page.window.min_height = 620
    set_mode("dark")
    pal = active()
    page.bgcolor = pal.bg

    gateway = KRXGateway()

    # Trading system. Constructed here so the engine outlives page navigation:
    # a rule set and a running evaluation loop must not be torn down because
    # the operator looked at another tab.
    rule_store = RuleStore()
    engine = EngineRuntime(rule_store, QuoteFeed(gateway))

    current = {"page": "macro"}
    cache: dict[str, ft.Control] = {}

    content = ft.AnimatedSwitcher(
        content=ft.Container(), duration=TRANSITION_MS,
        reverse_duration=TRANSITION_MS, expand=True,
    )

    # ------------------------------------------------------------------ views
    def build(name: str, **kwargs) -> ft.Control:
        ficc = {"macro": build_macro_page, "rates": build_rates_page,
                "bonds": build_bonds_page, "fx": build_fx_page,
                "structuring": build_structuring_page,
                "derivatives": build_derivatives_page, "etf": build_etf_page,
                "crypto": build_crypto_page, "lab": build_strategy_lab_page}
        if name in ficc:
            return ficc[name](page, on_open_settings=lambda: navigate("settings"))
        if name == "quant":
            return build_quant_lab_page(page,
                                        on_open_settings=lambda: navigate("settings"))
        if name == "portfolio":
            return build_portfolio_page(page,
                                        on_open_settings=lambda: navigate("settings"))
        if name == "signals":
            return build_signals_page(page,
                                      on_open_settings=lambda: navigate("settings"))
        if name == "trading":
            return build_trading_page(page, engine,
                                      on_open_rules=lambda: navigate("rules"),
                                      on_open_settings=lambda: navigate("settings"))
        if name == "rules":
            return build_rules_page(page, rule_store,
                                    on_changed=lambda: cache.pop("trading", None))
        if name == "workflows":
            return build_workflows_page(page, on_open_settings=lambda: navigate("settings"),
                                        on_open_skill=lambda sid: navigate("skills", focus=sid))
        if name == "skills":
            return build_skills_page(page, on_open_settings=lambda: navigate("settings"),
                                     focus_skill=kwargs.get("focus", ""))
        if name == "krx":
            return build_krx_page(page, gateway, locale=LOCALE,
                                  on_open_settings=lambda: navigate("settings"))
        if name == "runs":
            return build_runs_page(page)
        return build_settings_page(page, on_reload=reload_catalogue)

    def navigate(name: str, *, focus: str = "", rebuild: bool = False) -> None:
        # Runs and Skills-with-focus must reflect state that changed elsewhere;
        # everything else keeps its live view so a pipeline survives a tab switch.
        if rebuild or name in ("runs", "trading") or (name == "skills" and focus):
            cache.pop(name, None)
        if name not in cache:
            cache[name] = build(name, focus=focus)
        current["page"] = name
        content.content = ft.Container(cache[name], padding=24, expand=True)
        render_nav()
        page.update()

    def reload_catalogue() -> None:
        reload_all()
        cache.clear()
        navigate("settings", rebuild=True)

    # -------------------------------------------------------------------- nav
    logo = ft.Container(
        content=ft.Text("T", size=20, weight=ft.FontWeight.BOLD, color=pal.on_accent),
        width=38, height=38, bgcolor=pal.accent, border_radius=RADII["md"],
        alignment=ft.Alignment.CENTER,
    )
    brand = ft.Column([
        ft.Text("TRADEGEN", weight=ft.FontWeight.BOLD, color=pal.text, size=14),
        ft.Text("rates · FX · derivatives · ETF · crypto", size=10, color=pal.muted),
    ], spacing=0)
    nav_host = ft.Column(spacing=4)
    state = {"compact": False}

    def render_nav() -> None:
        compact = state["compact"]
        nav_host.controls = []
        for name, label, icon in NAV:
            selected = current["page"] == name
            row = [ft.Icon(icon, size=18,
                           color=pal.on_accent if selected else pal.muted)]
            if not compact:
                row.append(ft.Text(label, size=13,
                                   weight=ft.FontWeight.W_600 if selected else ft.FontWeight.W_400,
                                   color=pal.on_accent if selected else pal.text))
            nav_host.controls.append(ft.Container(
                content=ft.Row(row, spacing=10,
                               alignment=ft.MainAxisAlignment.CENTER if compact
                               else ft.MainAxisAlignment.START),
                padding=ft.Padding(12, 10, 12, 10),
                bgcolor=pal.accent if selected else None,
                border_radius=RADII["md"],
                ink=True,
                tooltip=label if compact else None,
                on_click=lambda e, n=name: navigate(n),
            ))

    rail = ft.Container(
        content=ft.Column([
            ft.Row([logo, brand], spacing=10),
            ft.Divider(color=pal.border),
            nav_host,
        ], spacing=12, scroll=ft.ScrollMode.AUTO),
        width=220, padding=14, bgcolor=pal.surface,
    )

    def resize(e=None) -> None:
        compact = (page.width or 1200) < BREAKPOINTS["compact"]
        if compact == state["compact"] and e is not None:
            return                       # nothing to redraw on same-side resizes
        state["compact"] = compact
        rail.width = 68 if compact else 220
        rail.padding = 8 if compact else 14
        brand.visible = not compact
        render_nav()
        page.update()

    # Flet 0.85 names this `on_resize`; the previous build used `on_resized`,
    # which is silently accepted and never fires.
    page.on_resize = resize

    page.add(ft.Row(
        [rail, ft.VerticalDivider(width=1, color=pal.border), content],
        expand=True, spacing=0, vertical_alignment=ft.CrossAxisAlignment.STRETCH,
    ))

    resize()
    navigate(current["page"])
    # v2 M8: governance-chain check + missed decisions, once per process, off the UI thread (rulings 3.13; T-OBS-02/05).
    try:
        __import__("core.skills.macro_daily", fromlist=["on_app_start"]).on_app_start(background=True)
    except Exception:
        pass


if __name__ == "__main__":
    ft.run(main, assets_dir="assets")
