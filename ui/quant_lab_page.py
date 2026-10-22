"""Quant Lab — Monte Carlo simulation of a single instrument.

The operator names a symbol, a model, and a horizon; the lab calibrates on
daily history, draws the paths, and answers with the fan, the terminal
distribution, the risk numbers, and a written read of all three. Every result
states its data source — a SYNTHETIC series is flagged loudly, because a
simulation calibrated on simulated data is a toy and must look like one.

The drift defaults to the risk-premium view (rf + ERP, less each model's own
convexity correction): the out-of-sample study found the sample mean has no
forecasting power over one year. rf comes from FRED (DGS3MO) when reachable
and is assumed 3% otherwise; either way the chip row says which.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Callable, Optional

import flet as ft

from core.ficc import data as ficc_data
from core.quant.garch import LR_5PCT, NU_NORMAL
from core.quant.history import HistoryError, _looks_krx, load_history
from core.quant.montecarlo import MODELS, run_monte_carlo
from core.quant import insights
from core.theme import RADII, active
from ui.ai_panel import analysis_panel
from ui.components import card, chip, empty_state, notice, section, stat as _stat
import ui.qcharts as qcharts

_SOURCES = [("auto", "Auto (KIS for 6-digit, else FMP)"), ("fmp", "FMP"),
            ("kis", "KIS (KRX)"), ("synthetic", "Synthetic demo")]
_MODEL_LABELS = {"garch_t": "GARCH(1,1)-t (default)", "gbm": "GBM (lognormal)",
                 "jump": "Jump diffusion (Merton)",
                 "bootstrap": "Block bootstrap (empirical)"}
_DRIFTS = [("premium", "Risk premium: rf + ERP, less convexity (default)"),
           ("zero", "Zero (stress view)"),
           ("rf", "Risk-neutral: rf, less convexity"),
           ("sample", "Sample mean (noisy)")]
_DRIFT_LABELS = dict(_DRIFTS)
_DRIFT_SHORT = {"premium": "risk premium", "zero": "zero", "rf": "risk-neutral",
                "sample": "sample mean"}          # chip text; the dropdown carries the formula
_RF_ASSUMED = 0.03
FIT_CAPTION = ("Fit window: the last 504 daily closes (the history default); descriptive, not an R-16 graded fit. "
               "The graded lab line is the expanding-window grading (docs/quant_lab), shown below when stored.")
_GRADES = Path(__file__).resolve().parents[1] / "docs" / "quant_lab"
_GRADE_FILE = {"069500": "KODEX200", "069500.KS": "KODEX200", "^KS11": "KOSPI"}   # docs/quant_lab_grading.py names
_GRADE_STYLE = {"PASS": ("PASS", "success"), "FAIL": ("FAIL", "error"), "NOT_RUN": ("NOT RUN", "muted")}
_BASEL_TOKEN = {"green": "success", "yellow": "warning", "red": "error"}
SMOKE_CHIP = "SMOKE · vendor data, not an official close, not a card run · gates nothing"   # rulings section 1
_GRADE_LINES = (("var99_kupiec_p", "var99_kupiec_p_min", "Kupiec 99% VaR"),
                ("var99_cc_p", "var99_cc_p_min", "Christoffersen CC 99%"),
                ("es975_z2_p", "es975_z2_reject_level", "ES 97.5% Z2"),
                ("fan_pit_h21_chi2_p", "fan_pit_h21_chi2_p_min", "Fan PIT h21"))


def _fmt_sessions(x: float) -> str:
    return "inf" if x == float("inf") else f"{x:.0f}"


def _fmt_pct(x: float) -> str:
    return "n/a" if x != x else f"{x * 100:.1f}%"


def _fmt_nu(x: float) -> str:
    """An end of the nu interval: 'normal' when it reaches eta = 0, '>100' beyond
    the nu the sampler already treats as normal."""
    return "normal" if x == float("inf") else (f">{NU_NORMAL:.0f}" if x > NU_NORMAL else f"{x:.1f}")


def _with_interval(fit, name: str, value: str, fmt) -> str:
    """'value (low to high)': the tile's value with its 95 % Wald interval when
    the fit has one (B2), the value alone otherwise."""
    iv = fit.interval(name)
    return value if iv is None else f"{value} ({fmt(iv[0])} to {fmt(iv[1])})"


def _risk_free(symbol: str = "") -> tuple[float, ft.Control]:
    """The funding rate for the drift, as a decimal, plus the chip that says
    where it came from: the US 3-month bill (FRED DGS3MO) for everything except
    KRX codes, which get the KRW 3-month rate (FRED, monthly) - a USD bill on a
    KRW stock would be the wrong currency. Never raises: any failure, or a
    SYNTHETIC fallback, is the assumed 3% with an error-toned chip."""
    try:
        if _looks_krx(symbol):
            s = ficc_data.load_short_rate("KRW", source="auto")
            if s.source == "FRED":
                return s.last, chip(f"rf {s.last * 100:.2f}% (KRW 3m, FRED {s.last_date}, monthly)")
        else:
            s = ficc_data.load_series("DGS3MO", source="auto", days=30)
            if s.source == "FRED":
                rf = s.last / 100.0                     # FRED yields are percent
                return rf, chip(f"rf {rf * 100:.2f}% (FRED DGS3MO {s.last_date})")
    except Exception:
        pass
    return _RF_ASSUMED, chip(f"rf {_RF_ASSUMED * 100:.2f}% assumed (FRED unreachable)",
                             "error")


def _garch_blocks(fit, horizon_vol: float) -> list[ft.Control]:
    """Second stat strip + one chip per guardrail flag. Every flag is visible:
    the operator cannot judge a silent failure."""
    ab = set(fit.at_bound)
    wald = "95% Wald interval from the observed information (B2)"
    f3, f4 = (lambda x: f"{x:.3f}"), (lambda x: f"{x:.4f}")
    nu_txt = "normal" if fit.effectively_normal else f"{fit.nu:.1f}"
    if fit.nu_interval is not None:
        nu_txt += f" ({_fmt_nu(fit.nu_interval[0])} to {_fmt_nu(fit.nu_interval[1])})"
    hl_txt = _fmt_sessions(fit.half_life)
    if fit.half_life_interval is not None:
        hl_txt += " ({} to {})".format(*(_fmt_sessions(x) for x in fit.half_life_interval))
    strip = ft.Row([
        _stat("alpha", _with_interval(fit, "alpha", f"{fit.alpha:.3f}", f3),
              token="error" if "alpha" in ab else "text", tooltip=wald),
        _stat("beta", _with_interval(fit, "beta", f"{fit.beta:.3f}", f3),
              token="error" if "beta" in ab else "text", tooltip=wald),
        _stat("alpha+beta", _with_interval(fit, "persistence", f"{fit.persistence:.4f}", f4),
              token="error" if "stationarity" in ab else "text",
              tooltip=wald + ", delta method"),
        _stat("Half-life (sessions)", hl_txt,
              tooltip="the persistence interval mapped through the half-life"),
        _stat("nu (tail)", nu_txt, token="error" if "nu" in ab else ("muted" if "alpha" in ab else "text"),
              tooltip=("95% profile-likelihood interval: cut 1.92 inside, 1.35 at the normal "
                       "(the boundary null of the LR tile); 'normal' means the interval includes eta = 0"
                       + ("; greyed: alpha at its bound, the reference distribution is indicative only"
                          if "alpha" in ab else ""))),
        _stat("Cond vol (ann.)", _fmt_pct(fit.cond_vol_last)),
        _stat("Uncond vol (ann.)", _fmt_pct(fit.uncond_vol),
              token="error" if "omega" in ab else "text",
              tooltip="no interval: the delta method covers 42% to 100% depending on persistence (B2)"),
        _stat("Horizon vol (ann.)", _fmt_pct(horizon_vol)),
        _stat("LR t vs normal", f"{fit.lr_t_vs_normal:.1f}",
              token="success" if (fit.lr_t_vs_normal > LR_5PCT and "alpha" not in ab) else "muted",
              tooltip=(f"5% point of the boundary null (half delta-0, half chi-square(1)): {LR_5PCT}"
                       + ("; greyed: alpha at its bound, reference distribution indicative only"
                          if "alpha" in ab else ""))),
        _stat("dAIC vs GBM", f"{fit.delta_aic_vs_gbm:+.1f}",
              token="success" if fit.delta_aic_vs_gbm > 0 else "muted"),
    ], spacing=10, wrap=True)
    chips = [chip(f"at bound: {name}", "error") for name in fit.at_bound]
    if not fit.converged:
        chips.append(chip("solver did not converge", "error"))
    if not fit.se:
        chips.append(chip("SE undefined", "error", tooltip=fit.se_note))
    at_bound_iv = [n for n in fit.interval_at_bound if n != "persistence"]
    if at_bound_iv:
        chips.append(chip("interval touches a bound: " + ", ".join(at_bound_iv), "error",
                          tooltip="a 95% interval crosses a guardrail (0 or the cap for alpha and beta, "
                                  "nu = 2.5); a symmetric interval there is indicative only"))
    if not chips:                                        # same rule as the note's "no guardrail hit"
        chips.append(chip("GARCH guardrails clear", "success"))
    if fit.dist == "t" and fit.effectively_normal:      # eta = 0 is an answer, not a failure
        chips.append(chip("normal innovations", "muted",
                          tooltip="the t fit found no heavier tail than the normal (eta = 1/nu at 0)"))
    if "persistence" in fit.interval_at_bound:           # true of most two-year samples: muted, not an error
        chips.append(chip("persistence interval reaches 1", "muted",
                          tooltip="an integrated variance is not excluded at 95%: the sample "
                                  "cannot pin down where vol settles"))
    chips.extend(_study_chips())
    return [strip, ft.Row(chips, spacing=6, wrap=True)]


def _study_chips() -> list[ft.Control]:
    """What the asset-expansion study found about this fan out of sample
    (docs/asset_expansion/cards): the rolling one-day 5 % VaR breach rate on
    SPY and KODEX 200 and the verdict of the skewed-t challenger, so the
    operator sees the known miss next to the fit."""
    try:
        from core.quant.validate import load_cards
        from pathlib import Path
        cards = {c["card_id"]: c for c in load_cards(Path(__file__).resolve().parents[1] / "docs" / "asset_expansion" / "cards")}
    except Exception:
        return []
    out = []
    for cid, label in (("D_Q_garch_spy", "SPY"), ("D_Q_garch_kodex200", "KODEX 200")):
        c = cards.get(cid)
        if c and isinstance(c.get("stats", {}).get("exceed95"), (int, float)):
            out.append(chip(f"study {label}: 5 % VaR breached {c['stats']['exceed95']:.1%} of days → {c['decision']}",
                            "muted" if c["decision"] == "PASS" else "error",
                            tooltip=(c.get("lines") or [""])[0]))
    for cid, label in (("D_Q_skewt_spy", "skew-t on SPY"), ("D_Q_skewt_kodex200", "skew-t on KODEX 200")):
        c = cards.get(cid)
        if c:
            out.append(chip(f"{label}: {c['decision']}", "success" if c["decision"] == "PASS" else "muted",
                            tooltip=c.get("decision_reason", "")))
    return out


def _lab_grade(symbol: str) -> Optional[dict]:
    """The stored R-16 grading report for `symbol` (`docs/quant_lab/<name>.json`, `lab.grade_to_json`), else None."""
    s = (symbol or "").strip().upper()
    name = _GRADE_FILE.get(s, s)
    if not re.fullmatch(r"[A-Z0-9]+", name):
        return None
    try:
        return json.loads((_GRADES / f"{name}.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _grade_blocks(g) -> list[ft.Control]:
    """PASS / FAIL / NOT RUN chips for the M9 gate and its four statistics, from a `lab.LabGrade` or its JSON;
    [] when there is no grade. The words come from the report's own p-values and thresholds."""
    if g is None:
        return []
    gate = g.get("gate") if isinstance(g, dict) else getattr(g, "gate", None)
    if not isinstance(gate, dict) or not gate.get("status"):
        return []
    lines, th = gate.get("lines") or {}, gate.get("thresholds") or {}
    rep = g if isinstance(g, dict) else (getattr(g, "report", None) or {})
    note = rep.get("label")
    smoke = str(note or "").startswith("SMOKE")          # vendor data: gates nothing, so no chip may read as a pass
    tone = (lambda t: "muted") if smoke else (lambda t: t)
    label, tok = _GRADE_STYLE.get(gate["status"], (str(gate["status"]), "muted"))
    chips = [chip(SMOKE_CHIP, "error", tooltip=str(note))] if smoke else []
    chips.append(chip(f"M9 gate: {label}", tone(tok),
                      tooltip=str(gate.get("reason") or f"period {gate.get('period')}, n {gate.get('n')}")))
    zone = ((((rep.get("periods") or {}).get(gate.get("period")) or {}).get("basel") or {}).get("last_250"))
    for key, tkey, name in _GRADE_LINES:
        if key == "fan_pit_h21_chi2_p":                    # 02_ui_design order: ..., ES Z2, Basel zone, fan PIT
            chips.append(chip(f"Basel last 250: {zone or 'NOT RUN'}", tone(_BASEL_TOKEN.get(zone, "muted"))))
        p, t = lines.get(key), th.get(tkey)
        if isinstance(p, (int, float)) and isinstance(t, (int, float)):
            word, tok = _GRADE_STYLE["PASS" if p >= t else "FAIL"]
            chips.append(chip(f"{name}: {word} (p {p:.3f}, min {t:g})", tone(tok)))
        else:
            chips.append(chip(f"{name}: NOT RUN", "muted"))
    out: list[ft.Control] = [ft.Row(chips, spacing=6, wrap=True)]
    if note:
        out.append(ft.Text(str(note), size=11, color=active().muted, selectable=True))
    report_lines = g.get("lines") if isinstance(g, dict) else getattr(g, "lines", ())
    out += [ft.Text(f"• {s}", size=11, color=active().muted, selectable=True)   # incl. 'reported, not gated' and 1-day VaR
            for s in report_lines or () if s != note]
    return out


def build_quant_lab_page(page: ft.Page,
                         on_open_settings: Optional[Callable] = None) -> ft.Control:
    pal = active()

    symbol = ft.TextField(label="Symbol", hint_text="AAPL or 005930", width=160,
                          border_radius=RADII["md"], value="AAPL")
    source = ft.Dropdown(label="Data source", width=250, value="auto",
                         options=[ft.dropdown.Option(k, v) for k, v in _SOURCES])
    model = ft.Dropdown(label="Model", width=230, value="garch_t",
                        options=[ft.dropdown.Option(m, _MODEL_LABELS[m]) for m in MODELS])
    erp = ft.TextField(label="ERP %", value="4.0", width=90,
                       helper="equity 4 / bonds-gold 1 / FX 0",
                       border_radius=RADII["md"])

    def on_drift(e=None) -> None:
        erp.visible = drift.value == "premium"
        page.update()

    drift = ft.Dropdown(label="Drift", width=260, value="premium", on_select=on_drift,
                        options=[ft.dropdown.Option(k, v) for k, v in _DRIFTS])
    horizon = ft.TextField(label="Horizon (sessions)", width=140, value="126",
                           border_radius=RADII["md"])
    paths = ft.TextField(label="Paths", width=120, value="5000",
                         border_radius=RADII["md"])
    target = ft.TextField(label="Target price (optional)", width=170,
                          border_radius=RADII["md"])
    busy = ft.ProgressRing(visible=False, width=20, height=20)
    result_host = ft.Column(spacing=14)

    def run(e=None) -> None:
        busy.visible = True
        result_host.controls = []
        page.update()

        def worker():
            try:
                hz = int(float(horizon.value or "126"))
                np_ = int(float(paths.value or "5000"))
                tgt = float(target.value) if (target.value or "").strip() else None
                mode = drift.value or "premium"
                erp_dec = 0.0
                if mode == "premium":
                    try:
                        erp_dec = float(erp.value or "0") / 100.0
                    except ValueError:
                        raise ValueError(f"ERP % is not a number: {erp.value!r}")
                rf, rf_chip = (_risk_free(symbol.value or "") if mode in ("premium", "rf")
                               else (0.0, None))
                hist = load_history(symbol.value, source=source.value or "auto")
                mc = run_monte_carlo(hist, model=model.value or "garch_t",
                                     n_paths=np_, horizon_days=hz, target=tgt,
                                     drift=mode, rf_rate=rf, erp=erp_dec)
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

            blocks: list[ft.Control] = []
            if hist.source == "SYNTHETIC":
                blocks.append(notice("Synthetic data: " + hist.note, "error",
                                     icon=ft.Icons.SCIENCE_OUTLINED))
            blocks.append(ft.Row([
                _stat("Spot", f"{mc.spot:,.2f}"),
                _stat("Median terminal", f"{mc.median_terminal:,.2f}"),
                _stat("90% range", f"{mc.p05:,.0f} – {mc.p95:,.0f}"),
                _stat("P(loss)", f"{mc.prob_loss * 100:.0f}%",
                      token="error" if mc.prob_loss > 0.5 else "text"),
                _stat(f"VaR {mc.var_level * 100:.0f}", f"{mc.var_pct * 100:.1f}%"),
                _stat("CVaR", f"{mc.cvar_pct * 100:.1f}%"),
                _stat("Drift (ann.)", f"{mc.mu_annual * 100:+.1f}%"),
                _stat("Vol (ann.)", f"{mc.sigma_annual * 100:.1f}%"),
            ] + ([_stat("P(target)", f"{mc.prob_target * 100:.0f}%",
                        token="success")] if mc.prob_target is not None else []),
                spacing=10, wrap=True))
            blocks.append(ft.Text(mc.drift_note, size=11, color=pal.muted))
            blocks.append(ft.Row([
                chip(f"source: {hist.source}",
                     "muted" if hist.source == "SYNTHETIC" else "success",
                     tooltip=hist.note),
            ] + ([chip(hist.note)] if hist.note and hist.source != "SYNTHETIC" else []) + [
                chip(f"{hist.first_date} → {hist.last_date}"),
                chip(f"{mc.n_paths:,} paths"),
                chip(_MODEL_LABELS[mc.model]),
                chip(f"drift: {_DRIFT_SHORT.get(mc.drift_mode, mc.drift_mode)}", "accent"),
            ] + ([rf_chip] if rf_chip is not None else []), spacing=6, wrap=True))
            blocks.append(ft.Text(FIT_CAPTION, size=11, color=pal.muted))
            blocks.extend(_grade_blocks(_lab_grade(symbol.value or "")))
            fit = getattr(mc, "garch", None)
            if fit is not None:
                blocks.extend(_garch_blocks(fit, mc.garch_horizon_vol))
                blocks.append(card(qcharts.cond_vol_chart(hist, fit)))
            blocks.append(card(qcharts.fan_chart(hist, mc)))
            blocks.append(card(qcharts.terminal_histogram(mc)))
            payload = {
                "symbol": mc.symbol, "data_source": hist.source,
                "model": mc.model, "n_paths": mc.n_paths,
                "horizon_days": mc.horizon_days, "spot": mc.spot,
                "drift_annual": mc.mu_annual, "vol_annual": mc.sigma_annual,
                "median_terminal": mc.median_terminal,
                "mean_terminal": mc.mean_terminal,
                "p05": mc.p05, "p95": mc.p95, "prob_loss": mc.prob_loss,
                "prob_target": mc.prob_target, "target": mc.target,
                "var_level": mc.var_level, "var_pct": mc.var_pct,
                "cvar_pct": mc.cvar_pct, "jump_note": mc.jump_note,
                "drift_mode": mc.drift_mode, "drift_note": mc.drift_note,
                "rf_rate": mc.rf_rate, "erp": mc.erp,
                "convexity_correction_annual": mc.correction_annual, "z_bound": mc.z_bound,
                "bound_note": mc.bound_note,
            }
            if fit is not None:
                payload["garch"] = {
                    "dist": fit.dist, "omega": fit.omega, "alpha": fit.alpha,
                    "beta": fit.beta, "nu": fit.nu, "persistence": fit.persistence,
                    "half_life_sessions": fit.half_life,
                    "cond_vol_annual": fit.cond_vol_last,
                    "uncond_vol_annual": fit.uncond_vol,
                    "horizon_vol_annual": mc.garch_horizon_vol,
                    "loglik": fit.loglik, "loglik_normal": fit.loglik_normal,
                    "loglik_gbm": fit.loglik_gbm, "aic": fit.aic, "bic": fit.bic,
                    "lr_t_vs_normal": fit.lr_t_vs_normal,
                    "delta_aic_vs_gbm": fit.delta_aic_vs_gbm,
                    "converged": fit.converged, "at_bound": list(fit.at_bound),
                    "note": fit.note,
                    "se": fit.se, "se_note": fit.se_note,
                    "nu_interval_95": fit.nu_interval,
                    "half_life_interval_95": fit.half_life_interval,
                    "interval_at_bound": list(fit.interval_at_bound),
                }
            blocks.append(analysis_panel(page, kind="monte_carlo",
                                         narrative=insights.narrate_monte_carlo(mc),
                                         payload_fn=lambda p=payload: p))
            result_host.controls = blocks
            busy.visible = False
            page.update()

        page.run_thread(worker)

    result_host.controls = [empty_state(
        "Calibrate and simulate",
        "Pick a symbol and a model — GARCH(1,1)-t is the default, so volatility "
        "clustering and fat tails are in the fan from the first run. The drift "
        "defaults to the risk-premium view (rf + ERP, less each model's convexity correction): in the "
        "out-of-sample study the trailing sample mean had no forecasting power "
        "over one year, so it is offered only for transparency. Without API "
        "keys the lab runs on a clearly labeled synthetic series, so every control "
        "here works immediately.",
        icon=ft.Icons.TROUBLESHOOT_OUTLINED)]

    return ft.Column([
        section("Quant Lab", subtitle="Monte Carlo simulation — calibrated on daily "
                                      "history, seeded and reproducible."),
        ft.Row([symbol, source, model, drift, erp, horizon, paths, target,
                ft.Button("Simulate", icon=ft.Icons.PLAY_ARROW_ROUNDED, on_click=run),
                busy], spacing=10, wrap=True),
        ft.Column([result_host], scroll=ft.ScrollMode.AUTO, expand=True),
    ], spacing=14, expand=True)


if __name__ == "__main__":
    # Headless driver: no network. FRED is forced off so the "assumed" chip path runs.
    from types import SimpleNamespace

    def _boom(*a, **k):
        raise RuntimeError("network off in driver")
    ficc_data.load_series = _boom

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
    root = build_quant_lab_page(fake)
    controls = list(walk(root))
    dd = {d.label: d for d in controls if isinstance(d, ft.Dropdown)}
    tf = {t.label: t for t in controls if isinstance(t, ft.TextField)}
    run_btn = next(b for b in controls if isinstance(b, ft.Button))
    dd["Data source"].value = "synthetic"
    tf["Paths"].value = "500"

    def texts() -> list[str]:
        return [t.value for t in walk(root) if isinstance(t, ft.Text) and t.value]

    assert dd["Drift"].value == "premium" and tf["ERP %"].visible
    for mode, needs_rf in (("premium", True), ("zero", False), ("sample", False)):
        dd["Drift"].value = mode
        dd["Drift"].on_select(None)
        assert tf["ERP %"].visible == (mode == "premium"), mode
        run_btn.on_click(None)
        found = texts()
        assert not any(t.startswith(("ValueError", "RuntimeError", "TypeError")) for t in found), \
            (mode, found[:3])
        assert f"drift: {_DRIFT_SHORT[mode]}" in found, (mode, found)
        assert any(t.startswith(("risk premium:", "zero:", "sample mean")) for t in found), mode
        assert any("assumed (FRED unreachable)" in t for t in found) == needs_rf, mode
        print(f"{mode}: ok")

    dd["Drift"].value = "premium"
    tf["ERP %"].value = "abc"
    run_btn.on_click(None)
    assert any("ERP % is not a number" in t for t in texts())
    print("driver ok")
