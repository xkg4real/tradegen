"""Rates — the yield curve, swap and swaption pricers, and short-rate simulation.

Four tools on one screen, switched by a dropdown so the input row only shows
what the chosen tool reads:

  * **Yield curve** — UST par history from FRED (or SYNTHETIC), bootstrapped or
    NS/NSS-fitted: descriptors, shape and regime, the curve table, tenor
    history and PCA.
  * **Swap pricer** — spot or forward-start IRS off the same curve: par, PV,
    DV01, key-rate DV01, carry and roll-down, the forward-swap grid.
  * **Swaption / cap-floor** — Bachelier or Black-76 on the forward swap rate
    or on each caplet's forward.
  * **Rate simulation** — Vasicek / CIR / Hull-White calibrated on SOFR, fanned
    out to a horizon, optionally revaluing a bond or swap there.

All computation runs in `page.run_thread`. The page never touches the network
itself — `core.ficc.data` does, and says which source answered. A SYNTHETIC
curve or rate series is announced with a loud notice, because a swaption priced
off simulated forwards is a demo, not a quote. Percent and basis-point
formatting happens here and nowhere in the core.
"""
from __future__ import annotations

import math
from typing import Callable, Optional

import flet as ft

from core.ficc import insights
from core.ficc.bonds import Bond
from core.ficc.common import BP, FICCError, parse_forward_tenor, parse_tenor, tenor_label
from core.ficc.curves import analyze_curve, curve_from_snapshot, curve_pca
from core.ficc.data import load_short_rate, load_treasury_curve
from core.ficc.ratesim import MODELS, calibrate, horizon_pv_distribution, simulate
from core.ficc.swaps import Swap, Swaption, analyze_swap, price_cap_floor, price_swaption
from core.theme import RADII
from ui.ai_panel import analysis_panel
from ui.components import card, chip, empty_state, notice, section, stat
import ui.fcharts as fcharts

_TOOLS = [("curve", "Yield curve"), ("swap", "Swap pricer"),
          ("option", "Swaption / cap-floor"), ("sim", "Rate simulation")]
_SOURCES = [("auto", "Auto (FRED, synthetic fallback)"), ("fred", "FRED"),
            ("synthetic", "Synthetic demo")]
_METHODS = [("bootstrap", "Bootstrap"), ("nelson_siegel", "Nelson-Siegel"),
            ("svensson", "Svensson")]
_MODEL_LABELS = {"vasicek": "Vasicek", "cir": "CIR", "hull_white": "Hull-White"}


# --------------------------------------------------------------------------- #
# Formatting and small helpers (UI only — the core stays in decimals)
# --------------------------------------------------------------------------- #
def _pct(x: float, d: int = 2) -> str:
    return f"{x * 100:.{d}f}%"


def _bp(x: float) -> str:
    return f"{x / BP:+.1f}bp"


def _money(x: float) -> str:
    return f"{x:,.0f}"


def _num(text: str | None, default: float | None, what: str) -> float | None:
    """Float from a text field; blank -> default; commas tolerated."""
    s = (text or "").strip().replace(",", "")
    if not s:
        return default
    try:
        return float(s)
    except ValueError:
        raise ValueError(f"{what}: cannot read {text!r} as a number.") from None


def _table(columns: list[str], rows: list[list[str]]) -> ft.Control:
    return ft.Row([ft.DataTable(
        columns=[ft.DataColumn(ft.Text(c, size=11)) for c in columns],
        rows=[ft.DataRow(cells=[ft.DataCell(ft.Text(v, size=11)) for v in r]) for r in rows],
        column_spacing=18, heading_row_height=34, data_row_max_height=34,
    )], scroll=ft.ScrollMode.AUTO)


def _synthetic_notice(source: str, note: str, what: str) -> list[ft.Control]:
    if source != "SYNTHETIC":
        return []
    return [notice(f"Synthetic {what}: {note}", "error", icon=ft.Icons.SCIENCE_OUTLINED)]


def _src_chip(label: str, source: str) -> ft.Control:
    return chip(f"{label}: {source}", "muted" if source == "SYNTHETIC" else "success")


def _curve(source: str, method: str = "bootstrap"):
    panel = load_treasury_curve(source=source)
    return panel, curve_from_snapshot(panel.latest(), method=method)


# --------------------------------------------------------------------------- #
# Tool workers: inputs in, result blocks out. Module-level so the self-check
# can drive them without a Flet page.
# --------------------------------------------------------------------------- #
def _run_curve(page, *, source: str, method: str, lookback: int) -> list[ft.Control]:
    panel = load_treasury_curve(source=source)
    report = analyze_curve(panel, lookback=lookback, method=method)
    try:
        pca = curve_pca(panel)
    except FICCError:                                 # panel too short for PCA
        pca = None
    d, curve = report.descriptors, report.curve
    blocks = _synthetic_notice(panel.source, panel.note, "curve")
    blocks.append(ft.Row([
        stat("Shape", report.shape), stat("Regime", report.regime, token="accent"),
        stat("2s10s", _bp(d["2s10s"])), stat("5s30s", _bp(d["5s30s"])),
        stat("3m10y", _bp(d["3m10y"])), stat("2s5s10s fly", _bp(d["2s5s10s_fly"])),
        stat("Level (2/5/10y)", _pct(d["level"])),
        stat("1y1y", _pct(d["1y1y"])), stat("2y1y", _pct(d["2y1y"])),
        stat("5y5y", _pct(d["5y5y"])),
        stat("1y fwd vs 1y", _bp(d["1y_fwd_1y_ahead"])),
    ], spacing=10, wrap=True))
    blocks.append(ft.Row([
        _src_chip("source", panel.source), chip(f"as of {report.snapshot.date}"),
        chip(f"{len(panel)} sessions"), chip(f"method: {curve.method}"),
        chip(f"{report.ns.method} rmse {report.ns.rmse / BP:.1f}bp"),
        chip(f"changes over {report.lookback} sessions"),
    ], spacing=6, wrap=True))
    blocks.append(card(fcharts.curve_chart(report)))
    rows = []
    for r in curve.table():
        chg = report.changes.get(r["label"])
        rows.append([r["label"], _pct(r["zero"], 3), f"{r['df']:.4f}", _pct(r["par"], 3),
                     _pct(r["fwd_1y"], 3), _bp(chg) if chg is not None else "—"])
    blocks.append(_table(["Tenor", "Zero", "DF", "Par", "1y fwd", f"Chg {report.lookback}d"],
                         rows))
    blocks.append(card(fcharts.curve_history_chart(panel)))
    if pca is not None:
        blocks.append(card(fcharts.pca_chart(pca)))
    payload = {
        "as_of": report.snapshot.date, "source": panel.source, "method": curve.method,
        "shape": report.shape, "regime": report.regime, "lookback": report.lookback,
        "descriptors": {k: float(v) for k, v in d.items()},
        "changes": {k: float(v) for k, v in report.changes.items()},
        "ns": {"method": report.ns.method, "params": [float(x) for x in report.ns.params],
               "rmse": float(report.ns.rmse)},
        "pca_explained": ([float(x) for x in pca.explained] if pca is not None else None),
        "table": [{k: (float(v) if isinstance(v, float) else v) for k, v in r.items()}
                  for r in curve.table()],
        "note": panel.note,
    }
    blocks.append(analysis_panel(page, kind="rates_curve",
                                 narrative=insights.narrate_curve(report, pca),
                                 payload_fn=lambda p=payload: p))
    return blocks


def _run_swap(page, *, source: str, tenor_text: str, fixed_pct: float | None,
              notional: float, pay_fixed: bool) -> list[ft.Control]:
    panel, curve = _curve(source)
    try:
        start, tenor = parse_forward_tenor(tenor_text)     # "5y5y"
    except FICCError:
        start, tenor = 0.0, parse_tenor(tenor_text)        # "10y"
    swap = Swap(tenor=tenor, fixed_rate=None if fixed_pct is None else fixed_pct / 100.0,
                notional=notional, pay_fixed=pay_fixed, start=start)
    rep = analyze_swap(swap, curve)
    k = rep.par_rate if swap.fixed_rate is None else swap.fixed_rate
    blocks = _synthetic_notice(panel.source, panel.note, "curve")
    blocks.append(ft.Row([
        stat("Par rate", _pct(rep.par_rate, 3)),
        stat("Fixed", _pct(k, 3) + (" (par)" if swap.fixed_rate is None else "")),
        stat("PV", _money(rep.pv), token="success" if rep.pv >= 0 else "error"),
        stat("DV01 (+1bp P&L)", _money(rep.dv01)),
        stat("Annuity", f"{rep.annuity:.4f}"),
        stat("Carry (first period)", _money(rep.carry_1y)),
        stat("Roll-down 1y", _money(rep.rolldown_1y)),
    ], spacing=10, wrap=True))
    blocks.append(ft.Row([
        chip(swap.label, "accent"), _src_chip("curve", panel.source),
        chip(f"curve {curve.date}"), chip(f"notional {_money(swap.notional)}"),
        chip(f"{swap.freq}/yr both legs"),
    ], spacing=6, wrap=True))
    blocks.append(card(fcharts.krd_chart(rep.krd, f"Key-rate DV01 — {swap.label}")))
    blocks.append(_table(["Forward swap", "Par rate"],
                         [[n, _pct(v, 3)] for n, v in rep.fwd_rates.items()]))
    payload = {
        "swap": swap.label, "tenor": tenor, "start": start, "pay_fixed": pay_fixed,
        "notional": notional, "fixed_rate": k, "par_rate": rep.par_rate, "pv": rep.pv,
        "dv01": rep.dv01, "annuity": rep.annuity, "carry_first_period": rep.carry_1y,
        "rolldown_1y": rep.rolldown_1y,
        "krd": {tenor_label(t): float(v) for t, v in rep.krd.items()},
        "fwd_rates": dict(rep.fwd_rates), "curve_date": curve.date,
        "curve_source": panel.source, "note": rep.note,
    }
    blocks.append(analysis_panel(page, kind="rates_swap",
                                 narrative=insights.narrate_swap(rep),
                                 payload_fn=lambda p=payload: p))
    return blocks


def _run_option(page, *, source: str, kind: str, expiry_text: str, tenor_text: str,
                strike_pct: float | None, payer: bool, model: str, vol_in: float,
                notional: float) -> list[ft.Control]:
    """kind: swaption | cap | floor. `vol_in` is bp for Bachelier, % for Black."""
    panel, curve = _curve(source)
    vol = vol_in * BP if model == "bachelier" else vol_in / 100.0
    vol_text = f"{vol_in:g}bp normal" if model == "bachelier" else f"{vol_in:g}% Black"
    strike = None if strike_pct is None else strike_pct / 100.0
    tenor = parse_tenor(tenor_text)
    blocks = _synthetic_notice(panel.source, panel.note, "curve")
    if kind == "swaption":
        sw = Swaption(expiry=parse_tenor(expiry_text), tenor=tenor, strike=strike,
                      payer=payer, notional=notional)
        rep = price_swaption(sw, curve, vol=vol, model=model)
        if not math.isfinite(rep.other_model_vol):
            other = "n/a"
        elif model == "bachelier":
            other = f"{_pct(rep.other_model_vol, 1)} Black"
        else:
            other = f"{rep.other_model_vol / BP:.0f}bp normal"
        side = "payer" if payer else "receiver"
        label = f"{tenor_label(sw.expiry)}x{tenor_label(sw.tenor)} {side}"
        blocks.append(ft.Row([
            stat("Forward", _pct(rep.forward, 3)),
            stat("Strike", _pct(rep.strike, 3) + (" (ATM)" if strike is None else "")),
            stat("Premium", _money(rep.premium)), stat("Premium", f"{rep.premium_bp:.1f}bp"),
            stat("Delta (per +1bp fwd)", _money(rep.delta)),
            stat("Gamma (per bp²)", f"{rep.gamma:,.2f}"),
            stat(f"Vega ({rep.vega_unit})", _money(rep.vega)),
            stat("Theta (1d)", _money(rep.theta_1d)),
            stat("Other-model vol", other),
        ], spacing=10, wrap=True))
        blocks.append(ft.Row([
            chip(label, "accent"), chip(f"{model}: {vol_text}"),
            _src_chip("curve", panel.source), chip(f"curve {curve.date}"),
            chip(f"annuity {rep.annuity:.4f}"),
        ], spacing=6, wrap=True))
        if rep.note:
            blocks.append(notice(rep.note, "muted"))
        payload = {
            "instrument": label, "expiry": sw.expiry, "tenor": sw.tenor, "payer": payer,
            "notional": notional, "model": model, "vol": vol, "forward": rep.forward,
            "strike": rep.strike, "annuity": rep.annuity, "premium": rep.premium,
            "premium_bp": rep.premium_bp, "delta_per_bp": rep.delta, "gamma": rep.gamma,
            "vega": rep.vega, "vega_unit": rep.vega_unit, "theta_1d": rep.theta_1d,
            "other_model_vol": (rep.other_model_vol if math.isfinite(rep.other_model_vol)
                                else None),
            "curve_date": curve.date, "curve_source": panel.source, "note": rep.note,
        }
        blocks.append(analysis_panel(page, kind="rates_swaption",
                                     narrative=insights.narrate_swaption(rep),
                                     payload_fn=lambda p=payload: p))
        return blocks

    rep = price_cap_floor(curve, tenor, strike, vol=vol, model=model, cap=kind == "cap",
                          notional=notional)
    dearest = max(rep.caplets, key=lambda c: c[3]) if rep.caplets else None
    blocks.append(ft.Row([
        stat("Strike", _pct(rep.strike, 3) + (" (ATM)" if strike is None else "")),
        stat("ATM (par swap)", _pct(rep.atm_strike, 3)),
        stat("Premium", _money(rep.premium)), stat("Premium", f"{rep.premium_bp:.1f}bp"),
        stat("Caplets", str(len(rep.caplets))),
        stat("Dearest caplet",
             f"{tenor_label(dearest[0])}-{tenor_label(dearest[1])}: {_money(dearest[3])}"
             if dearest else "—"),
    ], spacing=10, wrap=True))
    blocks.append(ft.Row([
        chip(f"{tenor_label(tenor)} {kind}", "accent"), chip(f"{model}: {vol_text}"),
        _src_chip("curve", panel.source), chip(f"curve {curve.date}"),
        chip(f"notional {_money(rep.notional)}"),
    ], spacing=6, wrap=True))
    blocks.append(card(fcharts.caplet_chart(rep)))
    blocks.append(_table(["Start", "End", "Forward", "Premium"],
                         [[f"{a:.2f}y", f"{b:.2f}y", _pct(f, 3), _money(p)]
                          for a, b, f, p in rep.caplets]))
    if rep.note:
        blocks.append(notice(rep.note, "muted"))
    payload = {
        "instrument": f"{tenor_label(tenor)} {kind}", "tenor": tenor, "notional": notional,
        "model": model, "vol": vol, "strike": rep.strike, "atm_strike": rep.atm_strike,
        "premium": rep.premium, "premium_bp": rep.premium_bp,
        "caplets": [{"start": a, "end": b, "forward": f, "premium": p}
                    for a, b, f, p in rep.caplets],
        "curve_date": curve.date, "curve_source": panel.source, "note": rep.note,
    }
    blocks.append(analysis_panel(page, kind="rates_cap_floor",
                                 narrative=insights.narrate_cap_floor(rep),
                                 payload_fn=lambda p=payload: p))
    return blocks


def _run_sim(page, *, source: str, model: str, horizon: float, n_paths: int,
             threshold_pct: float | None, instrument: str, instr_tenor_text: str,
             coupon_pct: float) -> list[ft.Control]:
    """instrument: none | bond | swap — what to revalue at the horizon."""
    series = load_short_rate("USD", source=source)
    panel, curve = _curve(source)
    params = calibrate(series, model=model)
    thr = None if threshold_pct is None else threshold_pct / 100.0
    sim = simulate(params, horizon=horizon, n_paths=n_paths, threshold=thr, curve=curve)
    hpv, what = None, "none"
    if instrument == "bond":
        bond = Bond(coupon=coupon_pct / 100.0, maturity=parse_tenor(instr_tenor_text))
        hpv = horizon_pv_distribution(params, sim, kind="bond", bond=bond, curve=curve)
        what = f"{_pct(bond.coupon)} {tenor_label(bond.maturity)} bond"
    elif instrument == "swap":
        swap = Swap(tenor=parse_tenor(instr_tenor_text))
        hpv = horizon_pv_distribution(params, sim, kind="swap", swap=swap, curve=curve)
        what = swap.label
    p = sim.params
    sigma = f"{p.sigma:.3f} (sqrt-r)" if model == "cir" else f"{p.sigma / BP:.0f}bp/yr"
    blocks = (_synthetic_notice(series.source, series.note, "short rate")
              + _synthetic_notice(panel.source, panel.note, "curve"))
    blocks.append(ft.Row([
        stat("Model", _MODEL_LABELS.get(model, model)),
        stat("kappa", f"{p.kappa:.2f}/yr"),
        stat("Half-life", f"{math.log(2) / p.kappa:.1f}y"),
        stat("theta", _pct(p.theta)), stat("sigma", sigma), stat("r0", _pct(p.r0)),
        stat(f"Mean at {horizon:g}y", _pct(sim.mean_terminal)),
        stat("90% range", f"{_pct(sim.p05)} – {_pct(sim.p95)}"),
    ] + ([stat(f"P(> {_pct(thr)})", f"{sim.prob_above * 100:.0f}%", token="accent")]
         if sim.prob_above is not None else []), spacing=10, wrap=True))
    blocks.append(ft.Row([
        _src_chip(series.id, series.source), chip(f"{series.first_date} → {series.last_date}"),
        chip(f"{len(series)} obs"), _src_chip("curve", panel.source),
        chip(f"{sim.n_paths:,} paths"), chip("seed 7"),
    ], spacing=6, wrap=True))
    blocks.append(card(fcharts.rate_fan_chart(sim)))
    blocks.append(_table(["Tenor", f"Model zero at {horizon:g}y (median path)"],
                         [[tenor_label(t), _pct(z, 3)] for t, z in sim.model_curve_at_horizon]))
    if hpv is not None:
        blocks.append(ft.Row([
            stat("Revalued", what, token="accent"),
            stat("Mean PV", _money(hpv.mean)),
            stat("90% range", f"{_money(hpv.p05)} – {_money(hpv.p95)}"),
            stat("VaR 95 (loss)", _money(hpv.var95), token="error" if hpv.var95 > 0 else "text"),
            stat("CVaR 95", _money(hpv.cvar95)),
        ], spacing=10, wrap=True))
        blocks.append(card(fcharts.horizon_pv_hist(hpv)))
    payload = {
        "model": model, "horizon": horizon, "n_paths": sim.n_paths,
        "params": {"kappa": p.kappa, "theta": p.theta, "sigma": p.sigma, "r0": p.r0,
                   "note": p.note},
        "series": {"id": series.id, "source": series.source, "first": series.first_date,
                   "last": series.last_date, "n": len(series), "note": series.note},
        "mean_terminal": sim.mean_terminal, "p05": sim.p05, "p95": sim.p95,
        "threshold": thr, "prob_above": sim.prob_above,
        "model_curve_at_horizon": {tenor_label(t): float(z)
                                   for t, z in sim.model_curve_at_horizon},
        "revalued": what,
        "horizon_pv": ({"mean": hpv.mean, "p05": hpv.p05, "p95": hpv.p95,
                        "var95": hpv.var95, "cvar95": hpv.cvar95, "note": hpv.note}
                       if hpv is not None else None),
        "curve_source": panel.source, "note": sim.note,
    }
    blocks.append(analysis_panel(page, kind="rates_simulation",
                                 narrative=insights.narrate_ratesim(sim, hpv),
                                 payload_fn=lambda p=payload: p))
    return blocks


# --------------------------------------------------------------------------- #
# Page
# --------------------------------------------------------------------------- #
def build_rates_page(page: ft.Page, on_open_settings: Optional[Callable] = None) -> ft.Control:
    def tf(label: str, width: int, value: str = "", hint: str = "", helper: str = ""):
        return ft.TextField(label=label, width=width, value=value, hint_text=hint or None,
                            helper=helper or None, border_radius=RADII["md"])

    def dd(label: str, width: int, value: str, options: list[tuple[str, str]]):
        return ft.Dropdown(label=label, width=width, value=value,
                           options=[ft.dropdown.Option(k, v) for k, v in options])

    source = dd("Curve source", 250, "auto", _SOURCES)
    # Yield curve
    method = dd("Method", 170, "bootstrap", _METHODS)
    lookback = tf("Lookback (sessions)", 150, "20")
    curve_row = ft.Row([method, lookback], spacing=10, wrap=True)
    # Swap pricer
    swap_tenor = tf("Tenor", 140, "10y", hint="10y or 5y5y")
    swap_fixed = tf("Fixed rate %", 140, hint="blank = par")
    swap_notional = tf("Notional", 150, "1000000")
    swap_side = dd("Side", 160, "pay", [("pay", "Pay fixed"), ("receive", "Receive fixed")])
    swap_row = ft.Row([swap_tenor, swap_fixed, swap_notional, swap_side], spacing=10, wrap=True,
                      visible=False)
    # Swaption / cap-floor
    opt_kind = dd("Instrument", 150, "swaption",
                  [("swaption", "Swaption"), ("cap", "Cap"), ("floor", "Floor")])
    opt_expiry = tf("Expiry", 110, "1y", helper="swaption only")
    opt_tenor = tf("Tenor", 110, "5y", helper="swap or cap length")
    opt_strike = tf("Strike %", 130, hint="blank = ATM")
    opt_side = dd("Side", 140, "payer", [("payer", "Payer"), ("receiver", "Receiver")])
    opt_model = dd("Model", 170, "bachelier",
                   [("bachelier", "Bachelier (normal)"), ("black", "Black-76")])
    opt_vol = tf("Vol", 130, "80", helper="bp (Bachelier) or % (Black)")
    opt_notional = tf("Notional", 150, "1000000")
    opt_row = ft.Row([opt_kind, opt_expiry, opt_tenor, opt_strike, opt_side, opt_model, opt_vol,
                      opt_notional], spacing=10, wrap=True, visible=False)
    # Rate simulation
    sim_model = dd("Model", 160, "vasicek", [(m, _MODEL_LABELS[m]) for m in MODELS])
    sim_horizon = tf("Horizon (years)", 130, "1")
    sim_paths = tf("Paths", 110, "5000")
    sim_threshold = tf("Threshold % (optional)", 170)
    sim_instr = dd("Revalue", 150, "none", [("none", "Nothing"), ("bond", "Bond"),
                                            ("swap", "Payer swap")])
    sim_tenor = tf("Instrument tenor", 140, "10y")
    sim_coupon = tf("Bond coupon %", 130, "4")
    sim_row = ft.Row([sim_model, sim_horizon, sim_paths, sim_threshold, sim_instr, sim_tenor,
                      sim_coupon], spacing=10, wrap=True, visible=False)
    rows = {"curve": curve_row, "swap": swap_row, "option": opt_row, "sim": sim_row}

    def switch(e=None) -> None:
        for key, row in rows.items():
            row.visible = key == (tool.value or "curve")
        if e is not None:                       # a real switch, not the initial layout
            result_host.controls = []           # the old tool's results would mislead
        page.update()

    tool = ft.Dropdown(label="Tool", width=220, value="curve", on_select=switch,
                       options=[ft.dropdown.Option(k, v) for k, v in _TOOLS])
    busy = ft.ProgressRing(visible=False, width=20, height=20)
    result_host = ft.Column(spacing=14)

    def compute() -> list[ft.Control]:
        src, which = source.value or "auto", tool.value or "curve"
        if which == "curve":
            return _run_curve(page, source=src, method=method.value or "bootstrap",
                              lookback=int(_num(lookback.value, 20, "Lookback")))
        if which == "swap":
            return _run_swap(page, source=src, tenor_text=swap_tenor.value or "10y",
                             fixed_pct=_num(swap_fixed.value, None, "Fixed rate"),
                             notional=_num(swap_notional.value, 1e6, "Notional"),
                             pay_fixed=(swap_side.value or "pay") == "pay")
        if which == "option":
            model = opt_model.value or "bachelier"
            return _run_option(page, source=src, kind=opt_kind.value or "swaption",
                               expiry_text=opt_expiry.value or "1y",
                               tenor_text=opt_tenor.value or "5y",
                               strike_pct=_num(opt_strike.value, None, "Strike"),
                               payer=(opt_side.value or "payer") == "payer", model=model,
                               vol_in=_num(opt_vol.value, 80.0 if model == "bachelier" else 30.0,
                                           "Vol"),
                               notional=_num(opt_notional.value, 1e6, "Notional"))
        return _run_sim(page, source=src, model=sim_model.value or "vasicek",
                        horizon=_num(sim_horizon.value, 1.0, "Horizon"),
                        n_paths=int(_num(sim_paths.value, 5000, "Paths")),
                        threshold_pct=_num(sim_threshold.value, None, "Threshold"),
                        instrument=sim_instr.value or "none",
                        instr_tenor_text=sim_tenor.value or "10y",
                        coupon_pct=_num(sim_coupon.value, 4.0, "Coupon"))

    def run(e=None) -> None:
        busy.visible = True
        result_host.controls = []
        page.update()

        def worker():
            try:
                blocks = compute()
            except (FICCError, ValueError) as exc:
                blocks = [notice(str(exc), "error", icon=ft.Icons.ERROR_OUTLINE)]
            except Exception as exc:
                blocks = [notice(f"{type(exc).__name__}: {exc}", "error",
                                 icon=ft.Icons.ERROR_OUTLINE)]
            result_host.controls = blocks
            busy.visible = False
            page.update()

        page.run_thread(worker)

    result_host.controls = [empty_state(
        "Pick a tool and press Run",
        "The curve comes from FRED (keyless); with no connection every tool runs on a "
        "clearly labeled synthetic curve, so everything here works immediately.",
        icon=ft.Icons.SSID_CHART_OUTLINED)]

    return ft.Column([
        section("Rates", subtitle="Yield curve, swaps, swaptions and caps, short-rate "
                                  "simulation — single-curve, ACT/365F, decimals inside."),
        ft.Row([tool, source, ft.Button("Run", icon=ft.Icons.PLAY_ARROW_ROUNDED, on_click=run),
                busy], spacing=10, wrap=True),
        curve_row, swap_row, opt_row, sim_row,
        ft.Column([result_host], scroll=ft.ScrollMode.AUTO, expand=True),
    ], spacing=14, expand=True)


if __name__ == "__main__":
    class _Page:                                      # enough of ft.Page for the workers
        def update(self) -> None:
            pass

        def run_thread(self, fn) -> None:
            fn()

    pg = _Page()

    def _is_error(block) -> bool:
        return (isinstance(block, ft.Container) and isinstance(block.content, ft.Row)
                and getattr(block.content.controls[0], "icon", "") == ft.Icons.ERROR_OUTLINE)

    results = [
        _run_curve(pg, source="synthetic", method="nelson_siegel", lookback=20),
        _run_swap(pg, source="synthetic", tenor_text="5y5y", fixed_pct=None, notional=1e6,
                  pay_fixed=True),
        _run_swap(pg, source="synthetic", tenor_text="10y", fixed_pct=4.0, notional=2.5e6,
                  pay_fixed=False),
        _run_option(pg, source="synthetic", kind="swaption", expiry_text="1y", tenor_text="5y",
                    strike_pct=None, payer=True, model="bachelier", vol_in=80, notional=1e6),
        _run_option(pg, source="synthetic", kind="cap", expiry_text="1y", tenor_text="5y",
                    strike_pct=4.5, payer=True, model="black", vol_in=30, notional=1e6),
        _run_sim(pg, source="synthetic", model="vasicek", horizon=1.0, n_paths=500,
                 threshold_pct=5.0, instrument="bond", instr_tenor_text="10y", coupon_pct=4.0),
        _run_sim(pg, source="synthetic", model="hull_white", horizon=0.5, n_paths=300,
                 threshold_pct=None, instrument="swap", instr_tenor_text="5y", coupon_pct=4.0),
    ]
    for i, blocks in enumerate(results):
        assert len(blocks) >= 4, len(blocks)
        assert not any(_is_error(b) for b in blocks)
        first = blocks[0].content.controls[1].value       # the loud synthetic notice
        assert first.startswith("Synthetic"), first
        assert isinstance(blocks[-1], ft.Container)        # analysis panel closes every result
        if i != 3:                                         # the swaption has no chart of its own
            assert any(isinstance(getattr(b, "content", None), ft.Image) for b in blocks), i
    # Bad numbers surface as ValueError (caught by the page), never a crash.
    try:
        _num("abc", None, "Notional")
        raise AssertionError("expected ValueError")
    except ValueError:
        pass
    # Wiring: the built page runs end to end on the fake page with the synthetic source.
    col = build_rates_page(pg)
    top = col.controls[1].controls                        # [tool, source, Run, busy]
    top[1].value = "synthetic"
    top[0].value = "swap"
    top[2].on_click(None)
    host = col.controls[-1].controls[0]
    assert len(host.controls) >= 4 and not _is_error(host.controls[0]), host.controls
    top[0].value = "curve"
    col.controls[3].controls[1].value = "abc"             # swap tenor is irrelevant now
    col.controls[2].controls[1].value = "abc"             # lookback: bad number
    top[2].on_click(None)
    assert _is_error(host.controls[0])
    print("ok")
