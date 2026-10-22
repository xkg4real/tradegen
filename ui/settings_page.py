"""Settings: credential presence, repository location, and a real KRX probe.

Presence only — no value is ever read into a widget, and there is no field to
type a key into. Credentials come from `.env` or the process environment, which
keeps them out of NEXTGEN's own state and out of any screenshot.

The KRX row is a live probe rather than a presence check, because a KRX_API_KEY
that exists and a KRX_API_KEY that the exchange accepts are different things,
and the difference is worth one HTTP call.
"""
from __future__ import annotations

from typing import Callable, Optional

import flet as ft

import config
from core.skills.index import all_skills
from core.skills.readiness import State, summarize
from core.theme import RADII, active
from data.krx.krx_market_client import KRXMarketClient
from ui.components import chip, key_value, notice, section

_SIGNUP = {
    "fred": "fred.stlouisfed.org (no key needed)",
    "yfinance": "finance.yahoo.com (no key needed)",
    "fmp": "financialmodelingprep.com",
    "finviz": "elite.finviz.com",
    "alpaca": "alpaca.markets",
    "fxmacrodata": "fxmacrodata.com",
    "kis": "apiportal.koreainvestment.com",
    "opendart": "opendart.fss.or.kr",
    "krx": "data.krx.co.kr",
    "upbit": "docs.upbit.com (no key needed)",
    "binance": "developers.binance.com (no key needed)",
    "upbit_account": "upbit.com → Open API 관리 (자산조회 only)",
}


def _ficc_status() -> list[dict]:
    fn = getattr(config, "ficc_provider_status", None)
    if fn is None:
        return [{"id": "fred", "label": "FRED (St. Louis Fed)", "ready": False,
                 "vars": (), "note": "config.ficc_provider_status is missing."}]
    try:
        return fn()
    except Exception as exc:
        return [{"id": "fred", "label": "FRED (St. Louis Fed)", "ready": False,
                 "vars": (), "note": f"{type(exc).__name__}: {exc}"}]


def build_settings_page(page: ft.Page, *, on_reload: Optional[Callable] = None) -> ft.Control:
    pal = active()
    root = config.skills_root()
    valid = config.skills_root_valid(root)
    skills = all_skills()
    counts = summarize(skills) if skills else {}

    probe_host = ft.Row(spacing=8)

    def provider_row(entry: dict) -> ft.Container:
        ready = bool(entry.get("ready"))
        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text(entry["label"], size=13, weight=ft.FontWeight.W_600,
                            color=pal.text, expand=True),
                    chip("configured" if ready else "not set",
                         "success" if ready else "muted"),
                ], spacing=8),
                ft.Text(entry.get("note", ""), size=11, color=pal.muted),
                ft.Row([ft.Text(" · ".join(entry["vars"]), size=11, color=pal.muted,
                                selectable=True, expand=True),
                        ft.Text(_SIGNUP.get(entry["id"], ""), size=11, color=pal.accent,
                                selectable=True)], spacing=8),
            ], spacing=5),
            padding=12, bgcolor=pal.surface_2,
            border=ft.Border.all(1, pal.border), border_radius=RADII["md"],
        )

    def run_probe(e=None) -> None:
        probe_host.controls = [ft.ProgressRing(width=16, height=16),
                               ft.Text("contacting KRX…", size=12, color=pal.muted)]
        page.update()

        def worker():
            result = KRXMarketClient().probe()
            probe_host.controls = [
                chip("reachable" if result["ready"] else "unavailable",
                     "success" if result["ready"] else "error"),
                ft.Text(f"path: {result['path']}", size=11, color=pal.muted),
                ft.Text(result["reason"], size=11, color=pal.muted, selectable=True,
                        expand=True),
            ]
            page.update()
        page.run_thread(worker)

    probe_host.controls = [ft.Button("Test KRX access", icon=ft.Icons.NETWORK_CHECK,
                                     on_click=run_probe)]

    ficc_probe_host = ft.Row(spacing=8, wrap=True)

    def run_ficc_probe(e=None) -> None:
        ficc_probe_host.controls = [ft.ProgressRing(width=16, height=16),
                                    ft.Text("contacting FRED and Yahoo…", size=12,
                                            color=pal.muted)]
        page.update()

        def worker():
            try:
                from core.ficc.data import probe as ficc_probe
                result = ficc_probe()
            except Exception as exc:                       # never take the page down
                result = {"fred": {"ok": False, "detail": f"{type(exc).__name__}: {exc}"},
                          "yfinance": {"ok": False, "detail": "probe failed"}}
            rows = []
            for key, label in (("fred", "FRED"), ("yfinance", "Yahoo Finance")):
                r = result.get(key) or {}
                rows.append(chip(f"{label}: " + ("reachable" if r.get("ok") else "unavailable"),
                                 "success" if r.get("ok") else "error"))
                rows.append(ft.Text(str(r.get("detail", "")), size=11, color=pal.muted,
                                    selectable=True))
            ficc_probe_host.controls = rows
            page.update()
        page.run_thread(worker)

    ficc_probe_host.controls = [ft.Button("Test FICC data access", icon=ft.Icons.NETWORK_CHECK,
                                          on_click=run_ficc_probe)]

    kis_probe_host = ft.Row(spacing=8, wrap=True)

    def run_kis_probe(e=None) -> None:
        kis_probe_host.controls = [ft.ProgressRing(width=16, height=16),
                                   ft.Text("one read-only call per KIS asset domain…", size=12, color=pal.muted)]
        page.update()

        def worker():
            try:
                from data.kis_markets import KISMarkets
                result = KISMarkets().probe()
            except Exception as exc:
                result = {"kis": {"ok": False, "detail": f"{type(exc).__name__}: {exc}"}}
            rows = []
            for key, r in result.items():
                rows.append(chip(f"{key}: " + ("ok" if r.get("ok") else "no"), "success" if r.get("ok") else "error",
                                 tooltip=str(r.get("detail", ""))))
            kis_probe_host.controls = rows
            page.update()
        page.run_thread(worker)

    kis_probe_host.controls = [ft.Button("Test KIS asset domains", icon=ft.Icons.NETWORK_CHECK, on_click=run_kis_probe)]

    crypto_probe_host = ft.Row(spacing=8, wrap=True)

    def run_crypto_probe(e=None) -> None:
        crypto_probe_host.controls = [ft.ProgressRing(width=16, height=16),
                                      ft.Text("contacting Upbit and Binance…", size=12, color=pal.muted)]
        page.update()

        def worker():
            try:
                from data.crypto.crypto_client import probe as cprobe
                result = cprobe()
            except Exception as exc:
                result = {"crypto": {"ok": False, "detail": f"{type(exc).__name__}: {exc}"}}
            rows = []
            for key, r in result.items():
                rows.append(chip(f"{key}: " + ("reachable" if r.get("ok") else "unavailable"),
                                 "success" if r.get("ok") else "error"))
                rows.append(ft.Text(str(r.get("detail", "")), size=11, color=pal.muted, selectable=True))
            crypto_probe_host.controls = rows
            page.update()
        page.run_thread(worker)

    crypto_probe_host.controls = [ft.Button("Test crypto data access", icon=ft.Icons.NETWORK_CHECK, on_click=run_crypto_probe)]

    repo_block = ft.Column([
        key_value("Repository", str(root)),
        key_value("Index", "skills-index.yaml found" if valid else "NOT FOUND"),
        key_value("Skills", str(len(skills))),
        key_value("Runnable now", str(counts.get(State.READY, 0))),
        key_value("Needs input", str(counts.get(State.NEEDS_INPUT, 0))),
        key_value("Key required", str(counts.get(State.MISSING_KEY, 0))),
        key_value("Reference only", str(counts.get(State.DOC_ONLY, 0))),
        key_value("Runs directory", str(config.runs_dir())),
        key_value("Interpreter", config.skill_python()),
        key_value("Run timeout", f"{config.SKILL_TIMEOUT_SECONDS:.0f}s"),
    ], spacing=6)

    env_help = (
        "# .env — NEXTGEN reads these from this machine only.\n"
        "NEXTGEN_SKILLS_ROOT=\n"
        "FMP_API_KEY=\n"
        "FINVIZ_API_KEY=\n"
        "ALPACA_API_KEY=\nALPACA_SECRET_KEY=\n"
        "FXMACRODATA_API_KEY=\n"
        "KIS_APP_KEY=\nKIS_APP_SECRET=\n"
        "OPENDART_API_KEY=\n"
        "KRX_API_KEY=\n"
        "UPBIT_ACCESS_KEY=\nUPBIT_SECRET_KEY=\n"
        "ANTHROPIC_API_KEY=\n"
        "QUANTGEN_AI_MODEL=claude-sonnet-5\n"
        "GS_CLIENT_ID=\nGS_CLIENT_SECRET=\n"
    )

    controls: list[ft.Control] = [
        section("Settings", subtitle="Credential presence only. No key is ever displayed here."),
    ]
    if not valid:
        controls.append(notice(
            f"No skills-index.yaml under {root}. Set NEXTGEN_SKILLS_ROOT in .env "
            "and restart.", "error", icon=ft.Icons.FOLDER_OFF_OUTLINED))

    def gs_row() -> ft.Control:
        from core.quant import gsq
        st = gsq.status()
        bits = []
        bits.append(chip(f"gs-quant {st.version}" if st.installed else "not installed",
                         "success" if st.installed else "error"))
        bits.append(chip("offline analytics " + ("active" if st.offline_analytics else "unavailable"),
                         "success" if st.offline_analytics else "muted"))
        bits.append(chip("Marquee session " + ("active" if st.session_active else "off"),
                         "success" if st.session_active else "muted"))
        return ft.Column([ft.Row(bits, spacing=6, wrap=True),
                          ft.Text(st.detail, size=11, color=pal.muted)], spacing=6)

    controls += [
        ft.Text("Quant analysis providers", size=15, weight=ft.FontWeight.W_600,
                color=pal.text),
        ft.ResponsiveRow([ft.Container(provider_row(p), col={"xs": 12, "md": 6})
                          for p in config.quant_provider_status()],
                         spacing=10, run_spacing=10),
        gs_row(),

        ft.Text("FICC data providers", size=15, weight=ft.FontWeight.W_600, color=pal.text),
        notice("The Rates, Bonds, FX, Macro and Structuring pages read the Treasury "
               "curve, SOFR, credit spreads and FX fixings from FRED and Yahoo Finance. "
               "Both are keyless; fetches are cached on disk for a few hours.",
               "accent", icon=ft.Icons.INFO_OUTLINE),
        ft.ResponsiveRow([ft.Container(provider_row(p), col={"xs": 12, "md": 6})
                          for p in _ficc_status()],
                         spacing=10, run_spacing=10),
        ft.Container(ficc_probe_host, padding=ft.Padding(0, 4, 0, 4)),

        ft.Text("Skill providers", size=15, weight=ft.FontWeight.W_600, color=pal.text),
        ft.ResponsiveRow([ft.Container(provider_row(p), col={"xs": 12, "md": 6})
                          for p in config.skill_provider_status()],
                         spacing=10, run_spacing=10),

        ft.Text("Korean market providers", size=15, weight=ft.FontWeight.W_600, color=pal.text),
        notice("KRX closed its keyless CSV export; a free KRX_API_KEY is now required "
               "for whole-market snapshots. KIS and OpenDART registration is also free.",
               "accent", icon=ft.Icons.INFO_OUTLINE),
        ft.ResponsiveRow([ft.Container(provider_row(p), col={"xs": 12, "md": 6})
                          for p in config.krx_provider_status()],
                         spacing=10, run_spacing=10),
        ft.Container(probe_host, padding=ft.Padding(0, 4, 0, 4)),
        notice("The same KIS key serves ETF NAV, KOSPI200 / KTB / USD futures, the option board, overseas stocks, "
               "KRW benchmark yields and exchange-traded bonds — quotations only, no derivatives account needed "
               "(probed 2026-09-25). CME ES/NQ/ZN/6E/GC/CL history answers HTTP 500 on a stock-account key.",
               "accent", icon=ft.Icons.INFO_OUTLINE),
        ft.Container(kis_probe_host, padding=ft.Padding(0, 4, 0, 4)),

        ft.Text("Crypto providers", size=15, weight=ft.FontWeight.W_600, color=pal.text),
        notice("Upbit and Binance public data are keyless. An Upbit key is optional and must be issued with 자산조회 "
               "(balance) scope only; QUANTGEN never submits orders, withdrawals or transfers and never holds a wallet key.",
               "accent", icon=ft.Icons.LOCK_OUTLINE),
        ft.ResponsiveRow([ft.Container(provider_row(p), col={"xs": 12, "md": 6})
                          for p in config.crypto_provider_status()],
                         spacing=10, run_spacing=10),
        ft.Container(crypto_probe_host, padding=ft.Padding(0, 4, 0, 4)),

        ft.Divider(color=pal.border),
        ft.Text("Repository", size=15, weight=ft.FontWeight.W_600, color=pal.text),
        repo_block,
        ft.Row([ft.Button("Reload catalogue", icon=ft.Icons.REFRESH,
                          on_click=lambda e: on_reload and on_reload())], spacing=8),

        ft.Divider(color=pal.border),
        ft.Text("Environment template", size=15, weight=ft.FontWeight.W_600, color=pal.text),
        ft.Container(ft.Text(env_help, size=11, color=pal.muted, selectable=True,
                             font_family="Consolas, monospace"),
                     padding=12, bgcolor=pal.bg, border=ft.Border.all(1, pal.border),
                     border_radius=RADII["md"]),
    ]

    return ft.Column(controls, spacing=14, expand=True, scroll=ft.ScrollMode.AUTO)
