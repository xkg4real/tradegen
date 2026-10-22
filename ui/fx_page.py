"""FX — spot/forward/carry, a vanilla option on a delta-quoted smile, and the
G10+KRW carry basket.

One page, three tools behind a dropdown, one Run button. Every result states
where its spot and rates came from; a SYNTHETIC series is flagged loudly, so
the numbers under it read as a demonstration of the maths, not a market read.

Simplifications the page adds on top of `core.ficc.fx`:
  * Rates are flat across tenors: the forward table prices every tenor off the
    same r_dom / r_for pair (typed as percent, or the latest short rate the
    data layer serves for each currency when the field is blank).
  * A delta-struck option ("25d") takes its strike at the ATM vol and is then
    priced at the SABR vol for that strike; RR/BF of zero collapse both to ATM.
  * Carry-basket rates come straight from the data layer; a SYNTHETIC monthly
    short rate is dated on month starts, so the demo backtest spans the whole
    window instead of a stub.
"""
from __future__ import annotations

import math
import re
from typing import Callable, Optional

import numpy as np

import flet as ft

from core.ficc import fx, insights
from core.ficc.common import BP, FICCError, parse_tenor, tenor_label
from core.ficc.data import (G10_KRW, Series, load_fx_spot, load_policy_rates,
                            load_short_rate)
from core.quant.validate import cost_bp
from core.theme import RADII, active
from ui.ai_panel import analysis_panel
from ui.components import card, chip, empty_state, notice, section, stat
import ui.fcharts as fcharts

_TOOLS = [("forward", "Spot, forward & carry"), ("option", "Option & smile"),
          ("carry", "Carry basket")]
_SOURCES = [("auto", "Auto (Yahoo spot, FRED rates)"), ("yfinance", "Yahoo"),
            ("synthetic", "Synthetic demo")]
_FWD_TENORS = ("1m", "3m", "6m", "1y", "2y")
_USD_FIRST = ("JPY", "KRW", "CAD", "CHF")            # quoted USDxxx in the carry universe


# --------------------------------------------------------------------------- #
# Small helpers — formatting and input parsing
# --------------------------------------------------------------------------- #
def _px(x: float) -> str:
    return f"{x:,.2f}" if x >= 20 else f"{x:.4f}"


def _num(field: ft.TextField, default: float | None = None) -> float | None:
    t = (field.value or "").strip()
    if not t:
        return default
    try:
        v = float(t)
    except ValueError:
        raise ValueError(f"{field.label}: {t!r} is not a number.") from None
    if not math.isfinite(v):
        raise ValueError(f"{field.label}: {t!r} is not a number.")
    return v


def _rate(field: ft.TextField, ccy: str, source: str) -> tuple[float, Series | None]:
    """A typed percent wins; otherwise the latest short rate the data layer serves."""
    v = _num(field)
    if v is not None:
        return v / 100.0, None
    s = load_short_rate(ccy, source="synthetic" if source == "synthetic" else "auto")
    return float(s.last), s


def _strike(text: str, S: float, T: float, rd: float, rf: float, vol: float,
            call: bool) -> float:
    """'1.12' -> that strike; '25d' -> the 25-delta strike at `vol`; blank/'ATM' ->
    the delta-neutral straddle strike F·exp(½σ²T)."""
    t = (text or "").strip().lower()
    if not t or t == "atm":
        return fx.forward(S, rd, rf, T) * math.exp(0.5 * vol * vol * T)
    m = re.fullmatch(r"(\d+(?:\.\d+)?)\s*d", t)
    if m:
        return fx.strike_from_delta(float(m.group(1)) / 100.0, S, T, rd, rf, vol, call=call)
    try:
        return float(t)
    except ValueError:
        raise ValueError(f"Strike: {text!r} is not a level, a delta like 25d, or ATM.") from None


def _table(columns: list[str], rows: list[list[str]]) -> ft.Control:
    table = ft.DataTable(
        columns=[ft.DataColumn(ft.Text(c, size=11)) for c in columns],
        rows=[ft.DataRow(cells=[ft.DataCell(ft.Text(v, size=11)) for v in r]) for r in rows],
        column_spacing=18, heading_row_height=34, data_row_max_height=34)
    return ft.Row([table], scroll=ft.ScrollMode.AUTO)


def _chips(*series: Series | None) -> list[ft.Control]:
    return [chip(f"{s.label}: {s.source} · {s.last_date}",
                 "muted" if s.source == "SYNTHETIC" else "success", tooltip=s.note)
            for s in series if s is not None]


def _synthetic_notice(*series: Series | None) -> ft.Control | None:
    syn = [s for s in series if s is not None and s.source == "SYNTHETIC"]
    if not syn:
        return None
    return notice("Synthetic data: " + ", ".join(s.label for s in syn) + ". " + syn[0].note,
                  "error", icon=ft.Icons.SCIENCE_OUTLINED)


def _pair_of(spot: Series) -> tuple[str, str, str]:
    """('EURUSD', base 'EUR', quote 'USD') from the data layer's '<PAIR>=X' id."""
    p = spot.id[:6]
    return p, p[:3], p[3:]


# --------------------------------------------------------------------------- #
# Page
# --------------------------------------------------------------------------- #
def build_fx_page(page: ft.Page, on_open_settings: Optional[Callable] = None) -> ft.Control:
    pal = active()

    tool = ft.Dropdown(label="Tool", width=230, value="forward",
                       options=[ft.dropdown.Option(k, v) for k, v in _TOOLS])
    source = ft.Dropdown(label="Data source", width=250, value="auto",
                         options=[ft.dropdown.Option(k, v) for k, v in _SOURCES])
    pair = ft.TextField(label="Pair", value="EURUSD", hint_text="EURUSD or USD/KRW",
                        width=130, border_radius=RADII["md"])
    r_dom = ft.TextField(label="Quote-ccy rate %", hint_text="blank = short rate", width=150,
                         border_radius=RADII["md"], tooltip="USD for EURUSD; KRW for USDKRW")
    r_for = ft.TextField(label="Base-ccy rate %", hint_text="blank = short rate", width=150,
                         border_radius=RADII["md"], tooltip="EUR for EURUSD; USD for USDKRW")
    busy = ft.ProgressRing(visible=False, width=20, height=20)
    result_host = ft.Column(spacing=14)

    # Spot, forward & carry
    tenor = ft.TextField(label="Tenor", value="3m", width=90, border_radius=RADII["md"])
    mkt_fwd = ft.TextField(label="Market forward (optional)", hint_text="outright, e.g. 1.1050",
                           width=190, border_radius=RADII["md"])
    row_forward = ft.Row([tenor, mkt_fwd], spacing=10, wrap=True)

    # Option & smile
    expiry = ft.TextField(label="Expiry", value="3m", width=90, border_radius=RADII["md"])
    strike = ft.TextField(label="Strike", value="ATM", hint_text="1.12, 25d or ATM", width=130,
                          border_radius=RADII["md"])
    side = ft.Dropdown(label="Side", width=110, value="call",
                       options=[ft.dropdown.Option("call", "Call"),
                                ft.dropdown.Option("put", "Put")])
    atm = ft.TextField(label="ATM vol %", value="8", width=100, border_radius=RADII["md"])
    rr = ft.TextField(label="25d RR %", value="0.5", width=100, border_radius=RADII["md"],
                      tooltip="25d call vol minus 25d put vol")
    bf = ft.TextField(label="25d BF %", value="0.3", width=100, border_radius=RADII["md"])
    row_option = ft.Row([expiry, strike, side, atm, rr, bf], spacing=10, wrap=True)

    # Carry basket
    top_n = ft.TextField(label="Top n", value="3", width=80, border_radius=RADII["md"])
    cost_bps = ft.TextField(label="Cost (bp)", value=f"{cost_bp('fx'):g}", width=90, border_radius=RADII["md"],
                            tooltip="Per side; defaults to QUANTGEN's FX table rate")
    rebal = ft.TextField(label="Rebalance (sessions)", value="21", width=150,
                         border_radius=RADII["md"])
    n_days = ft.TextField(label="History (sessions)", value="504", width=140,
                          border_radius=RADII["md"])
    row_carry = ft.Row([top_n, cost_bps, rebal, n_days], spacing=10, wrap=True)

    rows = {"forward": row_forward, "option": row_option, "carry": row_carry}

    def switch(e=None) -> None:
        k = tool.value or "forward"
        for key, row in rows.items():
            row.visible = key == k
        for f in (pair, r_dom, r_for):
            f.visible = k != "carry"
        if e is not None:                       # a real switch, not the initial layout
            result_host.controls = []           # the old tool's results would mislead
        page.update()

    tool.on_select = switch
    switch()

    # ----------------------------------------------------------------- tools
    def do_forward() -> list[ft.Control]:
        src = source.value or "auto"
        spot_s = load_fx_spot(pair.value, source=src)
        p, base, quote = _pair_of(spot_s)
        S, T = float(spot_s.last), parse_tenor(tenor.value or "3m")
        rd, rd_s = _rate(r_dom, quote, src)
        rf, rf_s = _rate(r_for, base, src)
        F = fx.forward(S, rd, rf, T)
        pts, cy = fx.forward_points(S, F), fx.carry(rd, rf)
        pip = 0.01 if S > 20 else 0.0001
        mf = _num(mkt_fwd)
        basis = fx.implied_basis(S, mf, rd, rf, T) if mf is not None else None
        curve = {parse_tenor(t): fx.forward(S, rd, rf, parse_tenor(t)) for t in _FWD_TENORS}
        curve[T] = F
        curve_pts = sorted(curve.items())

        blocks: list[ft.Control] = []
        syn = _synthetic_notice(spot_s, rd_s, rf_s)
        if syn is not None:
            blocks.append(syn)
        stats = [
            stat("Spot", _px(S)),
            stat(f"Forward {tenor_label(T)}", _px(F)),
            stat("Points", f"{pts:+.1f}", tooltip=f"pip = {pip:g}"),
            stat(f"Carry, long {base}", f"{cy * 100:+.2f}% p.a.",
                 token="success" if cy >= 0 else "error"),
            stat(f"{quote} rate", f"{rd * 100:.2f}%"),
            stat(f"{base} rate", f"{rf * 100:.2f}%"),
        ]
        if basis is not None:
            stats.append(stat("Implied basis", f"{basis / BP:+.1f}bp",
                              token="error" if abs(basis) >= 5 * BP else "text",
                              tooltip=f"market forward {_px(mf)} vs CIP {_px(F)}"))
        blocks.append(ft.Row(stats, spacing=10, wrap=True))
        blocks.append(ft.Row(_chips(spot_s, rd_s, rf_s)
                             + [chip("flat rates across tenors")], spacing=6, wrap=True))
        blocks.append(card(fcharts.fx_spot_chart(spot_s, curve_pts)))
        blocks.append(card(_table(
            ["Tenor", "Forward", "Points"],
            [[tenor_label(t), _px(f), f"{fx.forward_points(S, f):+.1f}"] for t, f in curve_pts])))
        payload = {
            "pair": p, "spot": S, "spot_source": spot_s.source, "spot_date": spot_s.last_date,
            "tenor_years": T, "r_dom": rd, "r_for": rf,
            "rate_sources": {quote: rd_s.source if rd_s else "typed",
                             base: rf_s.source if rf_s else "typed"},
            "forward": F, "forward_points": pts, "pip": pip, "carry_pa_long_base": cy,
            "market_forward": mf, "implied_basis": basis,
            "forward_curve": [{"tenor": tenor_label(t), "forward": f} for t, f in curve_pts],
        }
        blocks.append(analysis_panel(
            page, kind="fx_forward",
            narrative=insights.narrate_fx_forward(p, S, F, pts, cy, basis),
            payload_fn=lambda d=payload: d))
        return blocks

    def do_option() -> list[ft.Control]:
        src = source.value or "auto"
        spot_s = load_fx_spot(pair.value, source=src)
        p, base, quote = _pair_of(spot_s)
        S, T = float(spot_s.last), parse_tenor(expiry.value or "3m")
        rd, rd_s = _rate(r_dom, quote, src)
        rf, rf_s = _rate(r_for, base, src)
        v_atm = _num(atm, 8.0) / 100.0
        quote_v = fx.SmileQuote(T, v_atm, _num(rr, 0.0) / 100.0, _num(bf, 0.0) / 100.0)
        call = (side.value or "call") == "call"
        F = fx.forward(S, rd, rf, T)
        pts = fx.smile_from_quotes(quote_v, S, rd, rf)
        fit = fx.calibrate_sabr(F, T, [x.strike for x in pts], [x.vol for x in pts], beta=1.0)
        K = _strike(strike.value, S, T, rd, rf, v_atm, call)
        vol_k = float(fx.smile_curve(fit, F, T, np.array([K]))[0])
        gk = fx.garman_kohlhagen(S, K, T, rd, rf, vol_k, call)
        grid = np.linspace(min(pts[0].strike, K) * 0.98, max(pts[-1].strike, K) * 1.02, 80)
        vols = fx.smile_curve(fit, F, T, grid)

        blocks: list[ft.Control] = []
        syn = _synthetic_notice(spot_s, rd_s, rf_s)
        if syn is not None:
            blocks.append(syn)
        blocks.append(ft.Row([
            stat(f"Premium ({quote} per {base})", f"{gk.price:.5f}"),
            stat("% of spot", f"{gk.price_pct_spot * 100:.3f}%"),
            stat(f"Premium / 1m {base}", f"{gk.price * 1e6:,.0f} {quote}"),
            stat("Spot / forward", f"{_px(S)} / {_px(F)}"),
            stat("Strike", _px(K)),
            stat("Vol used", f"{vol_k * 100:.2f}%", tooltip="SABR vol at the strike"),
            stat("Delta (spot)", f"{gk.delta_spot:+.3f}", tooltip=f"forward {gk.delta_fwd:+.3f}"),
            stat("Gamma / 1%", f"{gk.gamma_1pct:+.4f}"),
            stat("Vega / vol-pt", f"{gk.vega:.5f}"),
            stat("Theta / day", f"{gk.theta_1d:+.6f}"),
            stat(f"Rho {quote} / bp", f"{gk.rho_dom * BP:+.6f}"),
            stat(f"Rho {base} / bp", f"{gk.rho_for * BP:+.6f}"),
        ], spacing=10, wrap=True))
        blocks.append(ft.Row(_chips(spot_s, rd_s, rf_s) + [
            chip(f"{'call' if call else 'put'} {tenor_label(T)}", "accent"),
            chip(f"SABR rho {fit.rho:+.2f} · nu {fit.nu:.2f} · rmse {fit.rmse * 100:.3f} vp",
                 "accent" if fit.converged else "error",
                 tooltip="Hagan lognormal SABR, beta fixed at 1"),
        ], spacing=6, wrap=True))
        blocks.append(card(fcharts.smile_chart(grid, vols, pts, F)))
        blocks.append(card(_table(
            ["Point", "Strike", "Vol", "Spot delta"],
            [[x.label, _px(x.strike), f"{x.vol * 100:.2f}%", f"{x.delta:+.3f}"] for x in pts])))
        payload = {
            "pair": p, "spot": S, "spot_source": spot_s.source, "forward": F,
            "expiry_years": T, "strike": K, "call": call, "r_dom": rd, "r_for": rf,
            "vol_used": vol_k, "price": gk.price, "price_pct_spot": gk.price_pct_spot,
            "delta_spot": gk.delta_spot, "delta_fwd": gk.delta_fwd, "gamma_1pct": gk.gamma_1pct,
            "vega_per_volpt": gk.vega, "theta_1d": gk.theta_1d,
            "rho_dom_per_bp": gk.rho_dom * BP, "rho_for_per_bp": gk.rho_for * BP,
            "smile": [{"label": x.label, "strike": x.strike, "vol": x.vol, "delta": x.delta}
                      for x in pts],
            "quotes": {"atm": quote_v.atm, "rr25": quote_v.rr25, "bf25": quote_v.bf25},
            "sabr": {"alpha": fit.alpha, "beta": fit.beta, "rho": fit.rho, "nu": fit.nu,
                     "rmse": fit.rmse, "converged": fit.converged},
        }
        blocks.append(analysis_panel(
            page, kind="fx_option", narrative=insights.narrate_fx_option(gk, pts, fit),
            payload_fn=lambda d=payload: d))
        return blocks

    def do_carry() -> list[ft.Control]:
        src = source.value or "auto"
        days = int(_num(n_days, 504.0))
        top, cost = int(_num(top_n, 3.0)), float(_num(cost_bps, cost_bp('fx')))
        reb = int(_num(rebal, 21.0))
        pairs = {c: ("USD" + c if c in _USD_FIRST else c + "USD") for c in G10_KRW if c != "USD"}
        spots = {pr: load_fx_spot(pr, source=src, days=days) for pr in pairs.values()}
        rates = load_policy_rates(list(G10_KRW), days=days,
                                  source="synthetic" if src == "synthetic" else "auto")
        table_rows = fx.carry_table(spots, rates)
        bt = fx.carry_backtest(spots, rates, top_n=top, cost_bps=cost, rebalance_days=reb)
        best, hi = table_rows[0], max(table_rows, key=lambda r: r.carry)
        bench = float(bt.bench_equity[-1]) - 1.0
        every = list(spots.values()) + list(rates.values())

        blocks: list[ft.Control] = []
        syn = _synthetic_notice(*every)
        if syn is not None:
            blocks.append(syn)
        blocks.append(ft.Row([
            stat("Best score", f"{best.ccy} {best.score:+.2f}"),
            stat("Highest carry", f"{hi.ccy} {hi.carry * 100:+.2f}%"),
            stat("Basket return", f"{float(bt.equity[-1]) - 1:+.1%}",
                 token="success" if bt.equity[-1] >= bt.bench_equity[-1] else "error"),
            stat("Ann. return", f"{bt.ann_return * 100:+.1f}%"),
            stat("Ann. vol", f"{bt.ann_vol * 100:.1f}%"),
            stat("Sharpe", f"{bt.sharpe:.2f}"),
            stat("Max drawdown", f"{bt.max_drawdown * 100:.1f}%", token="error"),
            stat("Equal-weight long", f"{bench:+.1%}"),
        ], spacing=10, wrap=True))
        _, longs, shorts = bt.positions[-1]
        blocks.append(ft.Row([
            chip("spots: " + ", ".join(sorted({s.source for s in spots.values()})),
                 "muted" if any(s.source == "SYNTHETIC" for s in spots.values()) else "success"),
            chip("rates: " + ", ".join(sorted({s.source for s in rates.values()})),
                 "muted" if any(s.source == "SYNTHETIC" for s in rates.values()) else "success"),
            chip(f"{bt.dates[0]} → {bt.dates[-1]} · {len(bt.dates)} sessions"),
            chip(f"{bt.n_rebalances} rebalances · {bt.cost_bps:g}bp"),
            chip(f"long {', '.join(longs)}", "success"),
            chip(f"short {', '.join(shorts)}", "error"),
        ], spacing=6, wrap=True))
        blocks.append(card(fcharts.carry_bar_chart(table_rows)))
        blocks.append(card(_table(
            ["Pair", "Ccy", "Spot", "Rate", "USD rate", "Carry", "3m vol", "Carry/vol",
             "3m mom", "Score"],
            [[r.pair, r.ccy, _px(r.spot), f"{r.rate_ccy * 100:.2f}%", f"{r.rate_usd * 100:.2f}%",
              f"{r.carry * 100:+.2f}%", f"{r.vol_3m * 100:.1f}%", f"{r.carry_to_vol:+.2f}",
              f"{r.mom_3m * 100:+.1f}%", f"{r.score:+.2f}"] for r in table_rows])))
        blocks.append(card(fcharts.carry_equity_chart(bt)))
        payload = {
            "universe": [r.ccy for r in table_rows], "vs": "USD",
            "sources": {s.id: s.source for s in every},
            "rows": [{"pair": r.pair, "ccy": r.ccy, "spot": r.spot, "rate_ccy": r.rate_ccy,
                      "rate_usd": r.rate_usd, "carry": r.carry, "vol_3m": r.vol_3m,
                      "carry_to_vol": r.carry_to_vol, "mom_3m": r.mom_3m, "score": r.score}
                     for r in table_rows],
            "backtest": {"top_n": bt.top_n, "cost_bps": bt.cost_bps, "rebalance_days": reb,
                         "sessions": len(bt.dates), "from": bt.dates[0], "to": bt.dates[-1],
                         "total_return": float(bt.equity[-1]) - 1.0, "bench_return": bench,
                         "ann_return": bt.ann_return, "ann_vol": bt.ann_vol,
                         "sharpe": bt.sharpe, "max_drawdown": bt.max_drawdown,
                         "n_rebalances": bt.n_rebalances,
                         "latest_long": list(longs), "latest_short": list(shorts),
                         "note": bt.note},
        }
        blocks.append(analysis_panel(
            page, kind="fx_carry", narrative=insights.narrate_carry(table_rows, bt),
            payload_fn=lambda d=payload: d))
        return blocks

    tools = {"forward": do_forward, "option": do_option, "carry": do_carry}

    def run(e=None) -> None:
        busy.visible = True
        result_host.controls = []
        page.update()

        def worker():
            try:
                result_host.controls = tools[tool.value or "forward"]()
            except (FICCError, ValueError) as exc:
                result_host.controls = [notice(str(exc), "error", icon=ft.Icons.ERROR_OUTLINE)]
            except Exception as exc:
                result_host.controls = [notice(f"{type(exc).__name__}: {exc}", "error",
                                               icon=ft.Icons.ERROR_OUTLINE)]
            busy.visible = False
            page.update()

        page.run_thread(worker)

    result_host.controls = [empty_state(
        "Pick a tool and press Run",
        "Forwards and carry, a vanilla on the smile, or the carry basket. Blank rate "
        "fields pull the latest short rate; without providers everything runs on a "
        "clearly labeled synthetic series.",
        icon=ft.Icons.CURRENCY_EXCHANGE)]

    return ft.Column([
        section("FX", subtitle="Forwards, carry, Garman-Kohlhagen on a SABR smile, and a "
                               "no-lookahead G10+KRW carry backtest."),
        ft.Row([tool, source, pair, r_dom, r_for,
                ft.Button("Run", icon=ft.Icons.PLAY_ARROW_ROUNDED, on_click=run), busy],
               spacing=10, wrap=True),
        row_forward, row_option, row_carry,
        ft.Column([result_host], scroll=ft.ScrollMode.AUTO, expand=True),
    ], spacing=14, expand=True)


# --------------------------------------------------------------------------- #
# Self-check: drive the page headless on synthetic data (no network)
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    from types import SimpleNamespace

    errors: list[str] = []
    _real_notice = notice

    def _spy(text, token="accent", **kw):
        if token == "error" and not text.startswith("Synthetic data"):
            errors.append(text)
        return _real_notice(text, token, **kw)

    notice = _spy                                     # the worker resolves it at call time

    def walk(c):
        yield c
        for ch in list(getattr(c, "controls", None) or []) + [getattr(c, "content", None)]:
            if ch is not None:
                yield from walk(ch)

    fake = SimpleNamespace(update=lambda: None, run_thread=lambda fn: fn())
    root = build_fx_page(fake)
    fields = {c.label: c for c in walk(root) if isinstance(c, (ft.TextField, ft.Dropdown))}
    run_btn = next(c for c in walk(root) if isinstance(c, ft.Button))
    host = next(c for c in walk(root) if isinstance(c, ft.Column) and c.scroll).controls[0]
    labels = lambda: [c.value for c in walk(host) if isinstance(c, ft.Text)]
    row_of = {id(c): r for r in walk(root) if isinstance(r, ft.Row) for c in r.controls}
    shown = lambda label: fields[label].visible and row_of[id(fields[label])].visible

    fields["Data source"].value = "synthetic"
    run_btn.on_click(None)
    assert not errors and len(host.controls) >= 6, (errors, len(host.controls))
    assert "Implied basis" not in labels() and "Spot" in labels()
    assert shown("Market forward (optional)") and not shown("Top n")
    fields["Market forward (optional)"].value = "1.2"
    fields["Pair"].value = "USD/KRW"
    run_btn.on_click(None)
    assert not errors and "Implied basis" in labels() and "KRW rate" in labels()
    fields["Market forward (optional)"].value = ""
    fields["Pair"].value = "EUR"
    run_btn.on_click(None)
    assert errors and "pair" in errors[-1].lower()
    errors.clear()
    fields["Pair"].value = "EURUSD"

    fields["Tool"].value = "option"
    fields["Tool"].on_select(None)
    assert shown("Strike") and not shown("Tenor") and shown("Pair")
    for k in ("ATM", "25d", "1.15"):
        fields["Strike"].value = k
        run_btn.on_click(None)
        assert not errors and "Vol used" in labels(), (k, errors)
    fields["Side"].value = "put"
    fields["Strike"].value = "25d"
    run_btn.on_click(None)
    assert not errors and "put 3m" in labels()
    fields["Strike"].value = "abc"
    run_btn.on_click(None)
    assert errors and "Strike" in errors[-1]
    errors.clear()
    fields["Strike"].value = "ATM"
    fields["Quote-ccy rate %"].value = "x"
    run_btn.on_click(None)
    assert errors and "Quote-ccy rate %" in errors[-1]
    errors.clear()
    fields["Quote-ccy rate %"].value = "4.5"
    fields["Base-ccy rate %"].value = "3"
    run_btn.on_click(None)
    assert not errors, errors
    assert not any("short rate" in str(v) for v in labels())   # typed rates: no source chip
    fields["Quote-ccy rate %"].value = fields["Base-ccy rate %"].value = ""

    fields["Tool"].value = "carry"
    fields["Tool"].on_select(None)
    assert not shown("Pair") and shown("Top n") and not shown("Strike")
    fields["History (sessions)"].value = "300"
    run_btn.on_click(None)
    assert not errors and "Sharpe" in labels() and "Best score" in labels(), errors
    assert any(str(v).startswith("Synthetic data") for v in labels())
    # Monthly synthetic rates enter with a one-observation lag, so the backtest
    # starts a month into the window: most of the 300 sessions, not all of them.
    sessions = [int(m.group(1)) for v in labels()
                for m in [re.search(r"(\d+) sessions", str(v))] if m]
    assert sessions and max(sessions) >= 240, sessions
    fields["Top n"].value = "0"
    run_btn.on_click(None)
    assert errors
    print("ok")
