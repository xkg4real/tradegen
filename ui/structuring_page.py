"""Structuring — pitchbook-style structured products, decomposed and hedged.

Four retail staples from `core.ficc.structured`: principal-protected note,
reverse convertible, dual-currency deposit, CMS steepener. The operator picks a
product, types the term sheet, and gets back fair value against issue price,
the legs a structurer would book, the payoff at maturity, whole-note Greeks and
the first-order hedge sheet — all off the latest US Treasury par curve
(bootstrapped), so a SYNTHETIC curve is flagged loudly because every number on
the screen inherits it.

Ponytail: one curve for everything. A KRW dual-currency deposit is discounted
on the UST curve here; the numbers are the mechanics, not a KRW quote.
"""
from __future__ import annotations

from dataclasses import replace
from typing import Callable, Optional

import flet as ft

from core.ficc import insights, structured
from core.ficc.common import BP, FICCError, parse_tenor, pct_text, tenor_label
from core.ficc.curves import curve_from_snapshot
from core.ficc.data import load_treasury_curve
from core.theme import RADII, active
from ui.ai_panel import analysis_panel
from ui.components import card, chip, empty_state, notice, section, stat
import ui.fcharts as fcharts

_TOOLS = [("ppn", "Principal-protected note"), ("rc", "Reverse convertible"),
          ("dcd", "Dual-currency deposit"), ("steep", "Steepener note")]
_SOURCES = [("auto", "Auto (FRED, synthetic fallback)"), ("fred", "FRED"),
            ("synthetic", "Synthetic demo")]
_DEFAULT_MATURITY = {"ppn": "3y", "rc": "1y", "dcd": "3m", "steep": "5y"}

# Per-product term sheet: (key, label, default text, width). Percent keys are
# typed in percent and handed to the pricer as decimals; blank optional keys
# mean "solve it" / "none".
_FIELDS: dict[str, list[tuple[str, str, str, int]]] = {
    "ppn": [("spot", "Spot", "1.10", 110), ("vol", "Vol (%)", "8", 100),
            ("r_for", "Foreign rate / dividend (%)", "2", 190),
            ("protection", "Protection (%)", "100", 130),
            ("issue", "Issue price", "100", 110), ("margin", "Margin (per 100)", "1.0", 140)],
    "rc": [("spot", "Spot", "1.10", 110), ("vol", "Vol (%)", "10", 100),
           ("r_for", "Foreign rate / dividend (%)", "2", 190),
           ("strike_pct", "Strike (% of spot)", "95", 150),
           ("coupon", "Coupon (%, blank = solve)", "", 190),
           ("issue", "Issue price", "100", 110), ("margin", "Margin (per 100)", "1.0", 140)],
    "dcd": [("base_ccy", "Base ccy", "USD", 100), ("quote_ccy", "Quote ccy", "KRW", 100),
            ("spot", "Spot", "1350", 110), ("strike", "Strike", "1300", 110),
            ("vol", "Vol (%)", "9", 100), ("r_for", "Base-ccy rate (%)", "4.5", 150),
            ("margin", "Margin (per 100)", "0.25", 140)],
    "steep": [("leverage", "Leverage (x)", "4", 110), ("floor", "Floor (%)", "0", 100),
              ("cap", "Cap (%, blank = none)", "", 170), ("freq", "Coupons / yr", "1", 110),
              ("issue", "Issue price", "100", 110)],
}
_PCT = {"vol", "r_for", "protection", "strike_pct", "coupon", "floor", "cap"}
_OPTIONAL = {"coupon", "cap"}
_TEXT = {"base_ccy", "quote_ccy"}
_GREEK_LABELS = {"delta": "Delta (per +1% spot)", "gamma": "Gamma (per +1%)",
                 "vega": "Vega (per vol-pt)", "dv01": "DV01 (per -1bp)",
                 "dv01_2s10s": "2s10s DV01 (per +1bp)"}


# --------------------------------------------------------------------------- #
# Pure pieces (module-level so the self-check can drive them without a page)
# --------------------------------------------------------------------------- #
def _parse(raw: dict[str, tuple[str, str]]) -> dict:
    """{key: (label, text)} -> {key: float | str | None}; ValueError names the field."""
    out: dict = {}
    for key, (label, text) in raw.items():
        text = (text or "").strip()
        if key in _TEXT:
            if not text:
                raise ValueError(f"{label} is required.")
            out[key] = text.upper()
            continue
        if not text:
            if key in _OPTIONAL:
                out[key] = None
                continue
            raise ValueError(f"{label} is required.")
        try:
            x = float(text)
        except ValueError:
            raise ValueError(f"{label}: cannot read {text!r}.") from None
        out[key] = x / 100.0 if key in _PCT else x
    return out


def _price(tool: str, curve, *, maturity: float, notional: float, underlying: str,
           v: dict) -> structured.ProductReport:
    if tool == "ppn":
        return structured.principal_protected_note(
            curve, spot=v["spot"], vol=v["vol"], r_for_or_div=v["r_for"], maturity=maturity,
            notional=notional, protection=v["protection"], issue_price=v["issue"],
            underlying=underlying, margin=v["margin"])
    if tool == "rc":
        return structured.reverse_convertible(
            curve, spot=v["spot"], vol=v["vol"], r_for_or_div=v["r_for"], maturity=maturity,
            notional=notional, strike_pct=v["strike_pct"], coupon=v["coupon"],
            issue_price=v["issue"], margin=v["margin"], underlying=underlying)
    if tool == "dcd":
        return structured.dual_currency_deposit(
            curve, spot=v["spot"], vol=v["vol"], r_for=v["r_for"], maturity=maturity,
            notional=notional, strike=v["strike"], base_ccy=v["base_ccy"],
            quote_ccy=v["quote_ccy"], margin=v["margin"])
    if tool == "steep":
        return structured.steepener_note(
            curve, maturity=maturity, notional=notional, leverage=v["leverage"],
            floor=v["floor"], cap=v["cap"], freq=int(v["freq"]), issue_price=v["issue"])
    raise FICCError(f"Unknown product {tool!r}.")


def _qty(x: float) -> str:
    return f"{x:+,.2f}" if abs(x) < 100 else f"{x:+,.0f}"


def _table(columns: list[str], rows: list[list]) -> ft.Control:
    last = len(columns) - 1

    def cell(i: int, v) -> ft.DataCell:
        return ft.DataCell(ft.Text(str(v), size=11, width=460 if i == last else None))

    return ft.Row([ft.DataTable(
        columns=[ft.DataColumn(ft.Text(c, size=11)) for c in columns],
        rows=[ft.DataRow(cells=[cell(i, v) for i, v in enumerate(r)]) for r in rows],
        column_spacing=18, heading_row_height=34, data_row_min_height=34,
        data_row_max_height=88,
    )], scroll=ft.ScrollMode.AUTO)


def _render(page: ft.Page, tool: str, r: structured.ProductReport, panel,
            curve) -> list[ft.Control]:
    pal = active()
    cms = r.underlying.startswith("CMS")
    synthetic = panel.source == "SYNTHETIC"
    blocks: list[ft.Control] = []
    if synthetic:
        blocks.append(notice("Synthetic data: " + (panel.note or "simulated curve panel."),
                             "error", icon=ft.Icons.SCIENCE_OUTLINED))

    stats = [stat("Fair value", f"{r.fair_value:.2f}"),
             stat("Issue price", f"{r.issue_price:.2f}"),
             stat("Margin (per 100)", f"{r.margin:+.2f}",
                  token="success" if r.margin >= 0 else "error")]
    if r.participation is not None:
        stats.append(stat("Leverage", f"{r.participation:g}x") if cms else
                     stat("Participation", f"{r.participation * 100:.0f}%"))
    if r.coupon is not None:
        stats.append(stat("Enhanced yield (simple)" if tool == "dcd" else "Coupon (p.a.)",
                          pct_text(r.coupon)))
    stats += [stat("Maturity", tenor_label(r.maturity)),
              stat("Notional", f"{r.notional:,.0f} {r.currency}")]
    blocks.append(ft.Row(stats, spacing=10, wrap=True))

    chips = [chip(f"curve: {panel.source}", "muted" if synthetic else "success"),
             chip(f"as of {curve.date}"), chip(f"{curve.method} zeros"), chip(r.underlying)]
    if r.spot is not None:
        chips.append(chip(f"spot {r.spot:g}"))
    if r.strike is not None:
        chips.append(chip(f"strike {r.strike:g}"))
    if r.vol is not None:
        chips.append(chip(f"vol {pct_text(r.vol, decimals=1)}"))
    blocks.append(ft.Row(chips, spacing=6, wrap=True))

    blocks.append(ft.Row([stat(_GREEK_LABELS.get(k, k), f"{v:,.0f} {r.currency}")
                          for k, v in r.greeks.items()], spacing=10, wrap=True))

    # The chart plots the grid as given; the steepener grid is a spread in decimals.
    src = replace(r, payoff_grid=tuple((x / BP, y) for x, y in r.payoff_grid)) if cms else r
    chart: list[ft.Control] = [fcharts.payoff_chart(src)]
    if cms:
        chart.append(ft.Text("x-axis: realised 10y-2y spread in bp, held flat for every "
                             "coupon period", size=11, color=pal.muted))
    blocks.append(card(ft.Column(chart, spacing=6)))

    blocks.append(card(ft.Column([
        ft.Text("Legs (per 100 of notional, signed for the holder)", size=13,
                weight=ft.FontWeight.W_600, color=pal.text),
        _table(["Leg", "Kind", "Value", "Detail"],
               [[leg.name, leg.kind, f"{leg.value:+.2f}", leg.detail] for leg in r.legs]),
    ], spacing=8)))

    hedge_rows = [[h.instrument, _qty(h.quantity), h.unit, h.rationale] for h in r.hedge]
    blocks.append(card(ft.Column([
        ft.Text("Hedge sheet (+ buy / pay fixed, - sell / receive)", size=13,
                weight=ft.FontWeight.W_600, color=pal.text),
        _table(["Instrument", "Quantity", "Unit", "Rationale"], hedge_rows) if hedge_rows
        else ft.Text("No first-order hedge: every Greek is zero.", size=12, color=pal.muted),
    ], spacing=8)))

    payload = {
        "product": r.product, "underlying": r.underlying, "currency": r.currency,
        "notional": r.notional, "maturity_years": r.maturity, "fair_value_per_100":
        r.fair_value, "issue_price": r.issue_price, "margin_per_100": r.margin,
        "participation": r.participation, "coupon": r.coupon, "spot": r.spot,
        "strike": r.strike, "vol": r.vol, "r_for": r.r_for,
        "legs": [{"name": l.name, "kind": l.kind, "value_per_100": l.value,
                  "detail": l.detail} for l in r.legs],
        "greeks_currency": dict(r.greeks),
        "hedge": [{"instrument": h.instrument, "quantity": h.quantity, "unit": h.unit,
                   "rationale": h.rationale} for h in r.hedge],
        "payoff_grid": [list(p) for p in r.payoff_grid], "note": r.note,
        "curve": {"source": panel.source, "date": curve.date, "method": curve.method,
                  "note": panel.note},
    }
    blocks.append(analysis_panel(page, kind="structured_product",
                                 narrative=insights.narrate_structured(r),
                                 payload_fn=lambda p=payload: p))
    return blocks


# --------------------------------------------------------------------------- #
# Page
# --------------------------------------------------------------------------- #
def build_structuring_page(page: ft.Page,
                           on_open_settings: Optional[Callable] = None) -> ft.Control:
    pal = active()
    tool = ft.Dropdown(label="Product", width=250, value="ppn",
                       options=[ft.dropdown.Option(k, v) for k, v in _TOOLS])
    source = ft.Dropdown(label="Curve source", width=250, value="auto",
                         options=[ft.dropdown.Option(k, v) for k, v in _SOURCES])
    underlying = ft.Dropdown(label="Underlying", width=120, value="FX",
                             options=[ft.dropdown.Option("FX", "FX"),
                                      ft.dropdown.Option("EQ", "Equity")])
    maturity = ft.TextField(label="Maturity", width=110, value=_DEFAULT_MATURITY["ppn"],
                            hint_text="3y, 6m", border_radius=RADII["md"])
    notional = ft.TextField(label="Notional", width=130, value="1000000",
                            border_radius=RADII["md"])
    futures = ft.TextField(label="Futures DV01 / contract (optional)", width=220,
                           border_radius=RADII["md"])
    busy = ft.ProgressRing(visible=False, width=20, height=20)
    result_host = ft.Column(spacing=14)

    fields = {k: {key: ft.TextField(label=label, value=default, width=width,
                                    border_radius=RADII["md"])
                  for key, label, default, width in spec}
              for k, spec in _FIELDS.items()}
    rows = {k: ft.Row(list(f.values()), spacing=10, wrap=True, visible=k == "ppn")
            for k, f in fields.items()}

    def switch(e=None) -> None:
        k = tool.value or "ppn"
        for name, row in rows.items():
            row.visible = name == k
        underlying.visible = k in ("ppn", "rc")
        if maturity.value in _DEFAULT_MATURITY.values():
            maturity.value = _DEFAULT_MATURITY[k]
        if e is not None:                       # a real switch, not the initial layout
            result_host.controls = []           # the old product's results would mislead
        page.update()

    tool.on_select = switch

    def run(e=None) -> None:
        k = tool.value or "ppn"
        busy.visible = True
        result_host.controls = []
        page.update()

        def worker():
            try:
                v = _parse({key: (f.label, f.value) for key, f in fields[k].items()})
                T = parse_tenor(maturity.value or _DEFAULT_MATURITY[k])
                N = _parse({"n": ("Notional", notional.value)})["n"]
                fut = _parse({"f": ("Futures DV01 / contract", futures.value)})["f"] \
                    if (futures.value or "").strip() else None
                panel = load_treasury_curve(source=source.value or "auto")
                curve = curve_from_snapshot(panel.latest())
                report = _price(k, curve, maturity=T, notional=N,
                                underlying=underlying.value or "FX", v=v)
                if fut is not None:
                    report = replace(report, hedge=structured.hedge_sheet(
                        report, curve=curve, futures_dv01_per_contract=fut))
                result_host.controls = _render(page, k, report, panel, curve)
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
        "Structure a product",
        "Pick a product and type the term sheet. Without FRED the note prices off a "
        "clearly labeled synthetic curve, so every control here works immediately.",
        icon=ft.Icons.ARCHITECTURE_OUTLINED)]

    return ft.Column([
        section("Structuring", subtitle="Structured products decomposed into legs, priced "
                                        "off the latest UST par curve, with Greeks and the "
                                        "first-order hedge sheet."),
        ft.Row([tool, source, underlying, maturity, notional, futures,
                ft.Button("Price", icon=ft.Icons.PLAY_ARROW_ROUNDED, on_click=run), busy],
               spacing=10, wrap=True),
        *rows.values(),
        ft.Column([result_host], scroll=ft.ScrollMode.AUTO, expand=True),
    ], spacing=14, expand=True)


# --------------------------------------------------------------------------- #
# Self-check (synthetic curve, no page, no network)
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    from types import SimpleNamespace

    fake = SimpleNamespace(update=lambda: None, run_thread=lambda fn: fn())
    panel = load_treasury_curve(source="synthetic")
    curve = curve_from_snapshot(panel.latest())
    for k, _ in _TOOLS:
        v = _parse({key: (label, default) for key, label, default, _ in _FIELDS[k]})
        rep = _price(k, curve, maturity=parse_tenor(_DEFAULT_MATURITY[k]), notional=1e6,
                     underlying="FX", v=v)
        blocks = _render(fake, k, rep, panel, curve)
        assert rep.fair_value > 0 and len(blocks) == 8, (k, len(blocks))   # synthetic notice
        assert isinstance(blocks[0], ft.Container) and isinstance(blocks[-1], ft.Container)
    try:
        _parse({"spot": ("Spot", "abc")})
        raise AssertionError("expected ValueError")
    except ValueError as exc:
        assert "Spot" in str(exc)
    assert _parse({"coupon": ("Coupon", ""), "vol": ("Vol", "8")}) == {"coupon": None,
                                                                       "vol": 0.08}
    # Drive the real handler once with a synchronous "thread".
    col = build_structuring_page(fake)
    assert isinstance(col, ft.Column)
    inputs = col.controls[1]
    next(c for c in inputs.controls if isinstance(c, ft.Dropdown)
         and c.label == "Curve source").value = "synthetic"
    next(c for c in inputs.controls if isinstance(c, ft.TextField)
         and c.label.startswith("Futures")).value = "65"
    next(c for c in inputs.controls if isinstance(c, ft.Button)).on_click(None)
    host = col.controls[-1].controls[0]
    assert len(host.controls) == 8, len(host.controls)
    print("ok")
