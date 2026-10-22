"""Bonds — calculator & risk, curve scenarios, futures hedge.

One bullet bond, described by coupon / maturity / frequency and quoted by
price or yield. The curve behind the key-rate DV01s, the z-spread, carry/roll
and the scenarios is the latest UST par curve from FRED (keyless), bootstrapped
as-is; when FRED cannot answer, the page runs on a loudly flagged synthetic
curve so every control works with zero keys. Percent and basis-point
formatting happens here and nowhere else — the core speaks decimals.
"""
from __future__ import annotations

import math
from typing import Callable, Optional

import flet as ft

from core.ficc import insights
from core.ficc.bonds import Bond, analyze_bond, futures_hedge_ratio, scenario_pnl
from core.ficc.common import FICCError, bp_text, pct_text, tenor_label
from core.ficc.curves import curve_from_snapshot
from core.ficc.data import load_treasury_curve
from core.theme import RADII, active
from ui import fcharts
from ui.ai_panel import analysis_panel
from ui.components import card, chip, empty_state, notice, section, stat

_TOOLS = [("calc", "Calculator & risk"), ("scenarios", "Scenarios"),
          ("hedge", "Futures hedge")]
_SOURCES = [("auto", "Auto (FRED, else synthetic)"), ("fred", "FRED"),
            ("synthetic", "Synthetic demo")]
_FREQS = [("1", "Annual"), ("2", "Semi-annual"), ("4", "Quarterly")]


def _money(x: float, *, signed: bool = False) -> str:
    return f"{x:{'+' if signed else ''},.0f}"


def _num(field: ft.TextField, default: Optional[float] = None) -> Optional[float]:
    """Blank -> default; anything unparsable names the field in the ValueError."""
    raw = (field.value or "").strip().replace(",", "")
    if not raw:
        return default
    try:
        v = float(raw)
    except ValueError:
        v = float("nan")
    if not math.isfinite(v):                      # rejects 'abc', 'nan', 'inf', '1e400'
        raise ValueError(f"{field.label}: {raw!r} is not a number.")
    return v


def _shock_text(shock) -> str:
    if isinstance(shock, (int, float)):
        return f"{shock:+.0f}bp parallel"
    return " / ".join(f"{tenor_label(t)} {shock[t]:+.0f}" for t in (0.25, 2.0, 5.0, 10.0, 30.0)
                      if t in shock)


def build_bonds_page(page: ft.Page,
                     on_open_settings: Optional[Callable] = None) -> ft.Control:
    pal = active()

    coupon = ft.TextField(label="Coupon %", width=110, value="4.50",
                          border_radius=RADII["md"])
    maturity = ft.TextField(label="Maturity (years)", width=140, value="10",
                            border_radius=RADII["md"])
    freq = ft.Dropdown(label="Coupons / year", width=150, value="2",
                       options=[ft.dropdown.Option(k, v) for k, v in _FREQS])
    price = ft.TextField(label="Price (per 100)", width=140, hint_text="blank = from yield",
                         border_radius=RADII["md"])
    ytm = ft.TextField(label="Yield %", width=120, value="4.50", hint_text="blank = from price",
                       border_radius=RADII["md"])
    notional = ft.TextField(label="Notional", width=140, value="1000000",
                            border_radius=RADII["md"])
    source = ft.Dropdown(label="Curve source", width=240, value="auto",
                         options=[ft.dropdown.Option(k, v) for k, v in _SOURCES])
    ctd_dv01 = ft.TextField(label="CTD DV01 / contract", width=170, value="65",
                            border_radius=RADII["md"])
    cf = ft.TextField(label="Conversion factor", width=150, value="0.8",
                      border_radius=RADII["md"])
    pos_dv01 = ft.TextField(label="Position DV01 (blank = calculator)", width=250,
                            border_radius=RADII["md"])
    hedge_row = ft.Row([ctd_dv01, cf, pos_dv01], spacing=10, wrap=True, visible=False)
    busy = ft.ProgressRing(visible=False, width=20, height=20)
    result_host = ft.Column(spacing=14)

    def on_tool(e=None) -> None:
        hedge_row.visible = tool.value == "hedge"
        page.update()

    tool = ft.Dropdown(label="Tool", width=200, value="calc", on_select=on_tool,
                       options=[ft.dropdown.Option(k, v) for k, v in _TOOLS])

    def run(e=None) -> None:
        busy.visible = True
        result_host.controls = []
        page.update()

        def fail(text: str) -> None:
            result_host.controls = [notice(text, "error", icon=ft.Icons.ERROR_OUTLINE)]
            busy.visible = False
            page.update()

        def worker():
            kind = tool.value or "calc"
            try:
                bond = Bond(coupon=_num(coupon, 0.0) / 100.0, maturity=_num(maturity, 10.0),
                            freq=int(freq.value or "2"), notional=_num(notional, 1e6))
                y = _num(ytm)
                panel = load_treasury_curve(source=source.value or "auto")
                curve = curve_from_snapshot(panel.latest())
                a = analyze_bond(bond, price=_num(price), ytm=None if y is None else y / 100.0,
                                 curve=curve)
                rows = scenario_pnl(bond, curve, a.price) if kind == "scenarios" else None
                hedge = None
                if kind == "hedge":
                    pos, ctd, c = _num(pos_dv01, a.dv01), _num(ctd_dv01, 65.0), _num(cf, 1.0)
                    hedge = (pos, ctd, c, futures_hedge_ratio(pos, ctd, c))
                cr = a.carry_roll
                synthetic = panel.source == "SYNTHETIC"
                blocks: list[ft.Control] = []
                if synthetic:
                    blocks.append(notice("Synthetic data: " + panel.note, "error",
                                         icon=ft.Icons.SCIENCE_OUTLINED))
                blocks.append(ft.Row([
                    chip(f"curve: {curve.source} {curve.date}", "muted" if synthetic else "success"),
                    chip(f"{curve.method}, {len(panel)} sessions"),
                    chip(f"{bond.freq}x coupons"),
                    chip(f"notional {_money(bond.notional)}"),
                ], spacing=6, wrap=True))
                blocks.append(ft.Row([
                    stat("Price", f"{a.price:.3f}"),
                    stat("Yield", pct_text(a.ytm, decimals=3)),
                    stat("Macaulay", f"{a.macaulay:.2f}y"),
                    stat("Modified", f"{a.modified:.2f}"),
                    stat("Convexity", f"{a.convexity:.1f}"),
                    stat("DV01", _money(a.dv01), tooltip="Currency per bp, positive for a long"),
                    stat("z-spread", bp_text(a.z_spread), tooltip=f"Curve price {a.curve_price:.3f}"),
                ], spacing=10, wrap=True))
                narrative = insights.narrate_bond(a, rows)
                payload = {
                    "tool": kind, "data_source": panel.source,
                    "bond": {"coupon": bond.coupon, "maturity": bond.maturity, "freq": bond.freq,
                             "notional": bond.notional},
                    "curve": {"source": curve.source, "date": curve.date, "method": curve.method,
                              "note": curve.note},
                    "price": a.price, "ytm": a.ytm, "macaulay": a.macaulay, "modified": a.modified,
                    "convexity": a.convexity, "dv01": a.dv01, "z_spread": a.z_spread,
                    "curve_price": a.curve_price,
                    "krd": {tenor_label(t): v for t, v in a.krd.items()},
                    "carry_roll": {"horizon": cr.horizon, "carry": cr.carry,
                                   "rolldown": cr.rolldown, "total": cr.total,
                                   "breakeven_bp": cr.breakeven_bp},
                }
                if kind == "calc":
                    blocks.append(ft.Row([
                        stat(f"Carry ({tenor_label(cr.horizon)})", f"{cr.carry:+.3f}",
                             token="success" if cr.carry >= 0 else "error"),
                        stat("Roll-down", f"{cr.rolldown:+.3f}",
                             token="success" if cr.rolldown >= 0 else "error"),
                        stat("Carry + roll", f"{cr.total:+.3f}",
                             token="success" if cr.total >= 0 else "error"),
                        stat("Breakeven", f"{cr.breakeven_bp:+.1f}bp",
                             tooltip="Yield rise that wipes out carry + roll"),
                    ], spacing=10, wrap=True))
                    blocks.append(card(fcharts.price_yield_chart(bond, a.ytm)))
                    blocks.append(card(fcharts.krd_chart(
                        a.krd, title=f"Key-rate DV01, z-spread {bp_text(a.z_spread)} held")))
                elif kind == "scenarios":
                    worst, best = min(rows, key=lambda r: r.pnl), max(rows, key=lambda r: r.pnl)
                    blocks.append(ft.Row([
                        stat("Worst", f"{worst.name}: {_money(worst.pnl, signed=True)}",
                             token="error"),
                        stat("Best", f"{best.name}: {_money(best.pnl, signed=True)}",
                             token="success"),
                    ], spacing=10, wrap=True))
                    blocks.append(card(fcharts.scenario_chart(rows)))
                    table = ft.DataTable(
                        columns=[ft.DataColumn(ft.Text(h, size=11)) for h in
                                 ("Scenario", "Shock", "New price", "P&L", "P&L %")],
                        rows=[ft.DataRow(cells=[ft.DataCell(ft.Text(v, size=11)) for v in (
                            r.name, _shock_text(r.shock_bp), f"{r.new_price:.3f}",
                            _money(r.pnl, signed=True), f"{r.pnl_pct * 100:+.2f}%")])
                            for r in rows],
                        column_spacing=18, heading_row_height=34, data_row_max_height=34,
                    )
                    blocks.append(ft.Row([table], scroll=ft.ScrollMode.AUTO))
                    payload["scenarios"] = [{"name": r.name, "shock_bp": _shock_text(r.shock_bp),
                                             "new_price": r.new_price, "pnl": r.pnl,
                                             "pnl_pct": r.pnl_pct} for r in rows]
                else:
                    pos, ctd, c, n = hedge
                    blocks.append(ft.Row([
                        stat("Position DV01", _money(pos),
                             tooltip="From the calculator unless overridden"),
                        stat("CTD DV01 / contract", f"{ctd:,.2f}"),
                        stat("Conversion factor", f"{c:.4f}"),
                        stat("Futures DV01", f"{ctd / c:,.2f}", tooltip="CTD DV01 / CF"),
                        stat("Contracts to sell", f"{n:,.2f}", token="accent"),
                        stat("Rounded", f"{round(n):,d}"),
                    ], spacing=10, wrap=True))
                    blocks.append(notice(
                        f"contracts = position DV01 x CF / CTD DV01 = {_money(pos)} x {c:.4f} / "
                        f"{ctd:,.2f} = {n:,.2f}. Sell that many to flatten a long position; the "
                        f"residual after rounding is {_money(pos - round(n) * ctd / c, signed=True)}"
                        f" per bp.", "muted", icon=ft.Icons.INFO_OUTLINE))
                    narrative += (f" Hedging {_money(pos)} per bp of DV01 with a future whose CTD "
                                  f"has DV01 {ctd:,.2f} per contract and conversion factor "
                                  f"{c:.4f} takes {n:,.2f} contracts sold ({round(n):,d} rounded).")
                    payload["hedge"] = {"position_dv01": pos, "ctd_dv01_per_contract": ctd,
                                        "conversion_factor": c, "contracts": n}
                if a.note:
                    blocks.append(notice(a.note, "muted", icon=ft.Icons.INFO_OUTLINE))
                blocks.append(analysis_panel(page, kind=f"bond_{kind}", narrative=narrative,
                                             payload_fn=lambda p=payload: p))
                result_host.controls = blocks
                busy.visible = False
                page.update()
            except (FICCError, ValueError) as exc:
                fail(str(exc))
            except Exception as exc:
                fail(f"{type(exc).__name__}: {exc}")

        page.run_thread(worker)

    result_host.controls = [empty_state(
        "Describe a bond and press Run",
        "Quote it by price or by yield (leave the other blank). The curve comes from "
        "FRED without a key; without a connection the page runs on a labeled synthetic "
        "curve.", icon=ft.Icons.REQUEST_QUOTE_OUTLINED)]

    return ft.Column([
        section("Bonds", subtitle="Price, yield, duration and convexity; key-rate DV01s, "
                                  "z-spread and carry/roll off the UST curve; curve "
                                  "scenarios; a Treasury-futures hedge."),
        ft.Row([tool, coupon, maturity, freq, price, ytm, notional, source,
                ft.Button("Run", icon=ft.Icons.PLAY_ARROW_ROUNDED, on_click=run), busy],
               spacing=10, wrap=True),
        hedge_row,
        ft.Column([result_host], scroll=ft.ScrollMode.AUTO, expand=True),
    ], spacing=14, expand=True)


# --------------------------------------------------------------------------- #
# Self-check: drive the page with a stand-in for ft.Page, synthetic curve only.
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    from types import SimpleNamespace

    def walk(c):
        yield c
        for attr in ("controls", "rows", "cells", "columns"):
            for child in getattr(c, attr, None) or []:
                yield from walk(child)
        for attr in ("content", "label"):
            child = getattr(c, attr, None)
            if child is not None and not isinstance(child, str):
                yield from walk(child)

    fake = SimpleNamespace(run_thread=lambda fn: fn(), update=lambda: None)
    root = build_bonds_page(fake)
    controls = list(walk(root))
    dd = {d.label: d for d in controls if isinstance(d, ft.Dropdown)}
    tf = {t.label: t for t in controls if isinstance(t, ft.TextField)}
    run_btn = next(b for b in controls if isinstance(b, ft.Button))
    dd["Curve source"].value = "synthetic"

    def texts() -> list[str]:
        return [t.value for t in walk(root) if isinstance(t, ft.Text) and t.value]

    for kind, n_img in (("calc", 2), ("scenarios", 1), ("hedge", 0)):
        dd["Tool"].value = kind
        run_btn.on_click(None)
        found = texts()
        assert not any(t.startswith(("ValueError", "FICCError", "TypeError")) for t in found), \
            (kind, found[:3])
        assert "DV01" in found and any(t.startswith("Synthetic data") for t in found), kind
        assert sum(isinstance(c, ft.Image) for c in walk(root)) == n_img, kind
        assert any(t.startswith("Analysis") for t in found), kind
    assert any(t.startswith("Contracts to sell") for t in texts())
    assert any(isinstance(c, ft.DataTable) for c in walk(root)) is False   # hedge has no table

    dd["Tool"].value = "scenarios"
    run_btn.on_click(None)
    assert any(isinstance(c, ft.DataTable) for c in walk(root))
    assert any(t == "2y-5y-10y fly" for t in texts())

    tf["Price (per 100)"].value = "98"                    # both price and yield -> error
    run_btn.on_click(None)
    assert any("exactly one" in t for t in texts())
    tf["Yield %"].value = ""
    tf["Coupon %"].value = "abc"
    run_btn.on_click(None)
    assert any("Coupon %" in t and "not a number" in t for t in texts())
    tf["Coupon %"].value = "4"
    dd["Tool"].value = "calc"
    run_btn.on_click(None)
    assert "98.000" in texts() and "DV01" in texts()

    ring = next(c for c in controls if isinstance(c, ft.ProgressRing))
    for bad in ("nan", "inf", "1e400"):             # non-finite -> notice, not an exception
        tf["Notional"].value = bad
        run_btn.on_click(None)
        assert any("Notional" in t and "not a number" in t for t in texts()), bad
        assert ring.visible is False
    tf["Notional"].value = "1000000"

    def boom(*a, **k):                              # render helper failure -> same notice path
        raise RuntimeError("chart exploded")
    saved, fcharts.price_yield_chart = fcharts.price_yield_chart, boom
    try:
        run_btn.on_click(None)
    finally:
        fcharts.price_yield_chart = saved
    assert any(t == "RuntimeError: chart exploded" for t in texts()), texts()[:3]
    assert ring.visible is False
    run_btn.on_click(None)
    assert "98.000" in texts() and ring.visible is False
    print("ok")
