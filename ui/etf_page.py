"""ETF — NAV and premium, the basket, leveraged-fund drag, and the sleeve
rules (trend switch, volatility target) with the study's verdict beside them.

KRX ETFs come from the KIS ETF domain (`data.kis_markets`): quote with NAV,
tracking error and LP holdings, the daily price-versus-NAV history with the
premium, and the constituent basket. US ETFs come through the history router
(FMP closes adjusted for splits and dividends) without NAV. The sleeve rules
never run on the raw NAV-series close: for a KRX fund they use KIS 수정주가, so
a unit split is not booked as a crash. The leveraged-fund drag uses the app's
GARCH(1,1)-t variance term structure on the KOSPI200 index (Avellaneda–Zhang).
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Callable, Optional

import flet as ft
import numpy as np

import config
from core.ficc.common import BP
from core.ficc.equity_deriv import letf_drag
from core.quant import insights
from core.quant import strategies as S
from core.quant.history import HistoryError, load_history, synthetic_history
from core.quant.validate import load_cards
from core.theme import RADII, active
from ui.ai_panel import analysis_panel
from ui.components import card, chip, empty_state, notice, section, stat
import ui.xcharts as xc

ROOT = Path(__file__).resolve().parents[1]
LETF = {"122630": (2.0, "KODEX 레버리지", 0.0064), "252670": (-2.0, "KODEX 200선물인버스2X", 0.0064),
        "114800": (-1.0, "KODEX 인버스", 0.0064), "233740": (2.0, "KODEX 코스닥150레버리지", 0.0064),
        "251340": (-1.0, "KODEX 코스닥150선물인버스", 0.0064)}
_CARD_FOR = {"trend": ("S_E1_trend_krx", "S_E1_trend_us"), "vol": ("S_E2_voltarget_kodex200", "S_E2_voltarget_spy")}


def _clean(code: str) -> str:
    c = (code or "").strip().upper()
    return c.split(".")[0] if c.endswith((".KS", ".KQ")) else c


def analyze(code: str, *, days: int = 504, source: str = "auto") -> dict:
    out: dict = {"code": code, "source": source, "is_krx": _clean(code).isdigit() and len(_clean(code)) == 6}
    km = None
    if out["is_krx"] and source in ("auto", "kis") and config.kis_ready():
        from data.kis_markets import KISMarkets
        km = KISMarkets()
        q = km.etf_quote(_clean(code))
        nav = km.etf_nav_daily(_clean(code), days=days)
        comps = km.etf_components(_clean(code))
        out.update(quote=q, dates=nav.dates, price=np.asarray(nav.close), nav=np.asarray(nav.extra["nav"]),
                   premium_pct=np.asarray(nav.extra["premium_pct"]), components=comps, data_source="KIS")
    else:
        h = load_history(code, source=("synthetic" if source == "synthetic" else source), days=days)
        out.update(quote=None, dates=h.dates, price=h.prices(), nav=None, premium_pct=None, components=[],
                   data_source=h.source, note=h.note)
    px, out["sleeve_dates"], out["sleeve_basis"] = out["price"], out["dates"], out.get("note") or out["data_source"]
    if km is not None:
        # The NAV series carries the raw close — it has to, the premium is raw price against raw NAV — so an
        # ETF split or consolidation would read as a one-day crash in the sleeve statistics. Those run on
        # KIS 수정주가 (split-adjusted) instead; the premium chart above keeps the raw pair.
        try:
            adj = load_history(_clean(code), source="kis", days=days)
            px, out["sleeve_dates"], out["sleeve_basis"] = adj.prices(), adj.dates, adj.note
        except Exception as exc:
            # Quote, premium and basket are already in hand (a fund listed for
            # under 30 sessions lands here). Losing the adjusted series must
            # not lose them: keep the raw close and say so.
            out["sleeve_basis"] = f"raw NAV-series close, NOT split-adjusted (KIS 수정주가 unavailable: {exc})"
    if out.get("premium_pct") is not None and out["premium_pct"].size > 60:
        prem = out["premium_pct"]
        out["premium_stats"] = {"last": float(prem[-1]), "mean": float(prem.mean()), "sd": float(prem.std(ddof=1)),
                                "z": float((prem[-1] - prem.mean()) / prem.std(ddof=1)) if prem.std(ddof=1) > 0 else 0.0,
                                "adf_p": S.adf_pvalue(prem), "half_life": S.half_life(prem),
                                "abs_mean": float(np.abs(prem).mean())}
    # sleeve rules on the fund's own history, with a costed summary
    if px.size > 300:
        rf = 0.03 / 252
        W_t = S.trend_switch(px[:, None], rule="sma", lookback=210, step=21, cash_rate_daily=rf)
        W_v = S.vol_target(px[:, None], target=0.12, window=22, step=21)
        cost = 3.0 if out["is_krx"] else 50.0
        pt, _ = S.simulate(px[:, None], W_t, cost_bps=cost, cash_daily=rf)
        pv, _ = S.simulate(px[:, None], W_v, cost_bps=cost, cash_daily=rf)
        bh = px[1:] / px[:-1] - 1.0
        out["sleeves"] = {"trend": S.summary(pt), "vol_target": S.summary(pv), "buy_hold": S.summary(bh),
                          "equity_trend": S.equity_curve(pt), "equity_bh": S.equity_curve(bh), "cost_bps": cost,
                          "exposure_trend": float(W_t[210:].mean()) if px.size > 210 else float("nan")}
    # leveraged-fund drag from the index's GARCH variance term structure
    c = _clean(code)
    if c in LETF:
        beta, name, fee = LETF[c]
        try:
            if km is not None:
                idx = km.index_daily("2001", days=600)
                r = np.diff(np.log(np.asarray(idx.close)))
                src = "KOSPI200 (KIS)"
            else:
                h = synthetic_history("KOSPI200", days=600)
                r = h.log_returns()
                src = "synthetic index"
            from core.quant.garch import fit_garch, forecast_variance
            fit = fit_garch(r, dist="t", profile=False)
            rows = []
            for n in (21, 63, 252):
                d = letf_drag(beta, forecast_variance(fit, n), fee=fee)
                rows.append({"sessions": n, "drag_bp": d["drag_bp"], "variance_bp": d["variance_term"] / BP,
                             "fee_bp": d["financing_term"] / BP})
            # the study (M_E4_letf_drag) found the last quarter's realised variance the better quarterly
            # reference (MAE 91 bp against 136 bp for the GARCH path): both are shown, the realised one first
            last_q = letf_drag(beta, np.full(63, float(np.var(r[-63:]))), fee=fee)
            out["letf"] = {"beta": beta, "name": name, "fee": fee, "rows": rows, "cond_vol": fit.cond_vol_last,
                           "uncond_vol": fit.uncond_vol, "nu": fit.nu, "index_source": src, "converged": fit.converged,
                           "last_quarter_drag_bp": last_q["drag_bp"], "last_quarter_vol": float(np.sqrt(np.var(r[-63:]) * 252))}
        except Exception as exc:
            out["letf"] = {"beta": beta, "name": name, "error": f"{type(exc).__name__}: {exc}"}
    # the study's verdict for the sleeve families
    cards = {c["card_id"]: c for c in load_cards(ROOT / "docs" / "asset_expansion" / "cards")}
    pick = 0 if out["is_krx"] else 1
    out["verdicts"] = {fam: cards.get(ids[pick], {}).get("decision", "not run") for fam, ids in _CARD_FOR.items()}
    out["verdict_reasons"] = {fam: cards.get(ids[pick], {}).get("decision_reason", "") for fam, ids in _CARD_FOR.items()}
    if "letf" in out:
        lc = cards.get("M_E4_letf_drag", {})
        out["letf"]["verdict"] = lc.get("decision", "not run")
        out["letf"]["verdict_reason"] = (lc.get("lines") or [lc.get("decision_reason", "")])[0]
    return out


def narrative(a: dict) -> str:
    parts = []
    q = a.get("quote")
    if q:
        parts.append(f"{a['code']} trades at {q['price']:,.0f} against an NAV of {q['nav']:,.2f}, a premium of "
                     f"{q['premium_pct']:+.2f} % with tracking error {q['tracking_error_pct']:.2f} %, "
                     f"{q['cu_units']:,.0f} shares per creation unit and LPs holding {q['lp_holding_pct']:.1f} %.")
    ps = a.get("premium_stats")
    if ps:
        parts.append(f"Over {len(a['dates'])} sessions the premium averaged {ps['mean']:+.2f} % (|premium| {ps['abs_mean']:.2f} %), "
                     f"today's reading sits {ps['z']:+.1f} standard deviations from that mean; ADF p = {ps['adf_p']:.3f} and "
                     f"the half-life is {ps['half_life']:.0f} sessions, so " +
                     ("a discount reverts within days, which is why the flagship trackers carry no tradeable premium after a 4–5 bp round trip."
                      if ps["half_life"] < 5 else "the deviation is slow-moving enough to matter for entry timing."))
    sl = a.get("sleeves")
    if sl:
        parts.append(f"On this fund's own history the 10-month trend switch earned Sharpe {sl['trend']['sharpe']:.2f} "
                     f"(max drawdown {sl['trend']['max_drawdown']:.0%}, {sl['exposure_trend']:.0%} invested) against buy-and-hold "
                     f"{sl['buy_hold']['sharpe']:.2f} ({sl['buy_hold']['max_drawdown']:.0%}); the 12 % vol target earned "
                     f"{sl['vol_target']['sharpe']:.2f}. These are in-sample descriptive numbers; the validation study's verdict "
                     f"for this family is trend: {a['verdicts']['trend']}, vol target: {a['verdicts']['vol']}. "
                     f"Price basis for these sleeve numbers: {a.get('sleeve_basis', a.get('data_source'))}.")
    lt = a.get("letf")
    if lt and "rows" in lt:
        r63 = next(r for r in lt["rows"] if r["sessions"] == 63)
        parts.append(f"{lt['name']} is a {lt['beta']:+.0f}× fund: at the last quarter's realised vol ({lt['last_quarter_vol']:.1%}) the "
                     f"Avellaneda–Zhang drag versus {lt['beta']:+.0f}× the index is {lt['last_quarter_drag_bp']:+.0f} bp a quarter; the "
                     f"GARCH-t variance term structure (conditional vol {lt['cond_vol']:.1%}, ν {lt['nu']:.1f}) puts it at "
                     f"{r63['drag_bp']:+.0f} bp ({r63['variance_bp']:+.0f} bp from variance, {r63['fee_bp']:+.0f} bp from the fee), "
                     f"{next(r for r in lt['rows'] if r['sessions'] == 252)['drag_bp']:+.0f} bp over a year: the price of daily rebalancing. "
                     f"The validation study's verdict on the GARCH forecast is {lt.get('verdict', 'not run')}: the realised last quarter "
                     f"is the better guide, which is why it is quoted first.")
    if a.get("data_source") == "SYNTHETIC":
        parts.append("The series is SYNTHETIC; nothing above is market data.")
    return " ".join(parts) or "No history could be loaded."


def payload(a: dict) -> dict:
    return {"code": a["code"], "data_source": a.get("data_source"), "sleeve_price_basis": a.get("sleeve_basis"),
            "quote": a.get("quote"),
            "premium_stats": a.get("premium_stats"), "letf": a.get("letf"),
            "sleeves": {k: v for k, v in (a.get("sleeves") or {}).items() if not k.startswith("equity")},
            "verdicts": a.get("verdicts"), "top_components": (a.get("components") or [])[:10]}


def build_etf_page(page: ft.Page, on_open_settings: Optional[Callable] = None) -> ft.Control:
    pal = active()
    code = ft.TextField(label="ETF code", value="069500", hint_text="069500, 122630, SPY", width=160, border_radius=RADII["md"])
    days = ft.TextField(label="Sessions", value="504", width=110, border_radius=RADII["md"])
    source = ft.Dropdown(label="Source", width=220, value="auto",
                         options=[ft.dropdown.Option("auto", "Auto (KIS for KRX codes)"), ft.dropdown.Option("synthetic", "Synthetic demo")])
    busy = ft.ProgressRing(visible=False, width=20, height=20)
    host = ft.Column(spacing=14)

    def run(e=None) -> None:
        busy.visible = True; host.controls = []; page.update()

        def worker():
            try:
                a = analyze(code.value or "069500", days=int(float(days.value or "504")), source=source.value or "auto")
            except (HistoryError, ValueError) as exc:
                host.controls = [notice(str(exc), "error", icon=ft.Icons.ERROR_OUTLINE)]; busy.visible = False; page.update(); return
            except Exception as exc:
                host.controls = [notice(f"{type(exc).__name__}: {exc}", "error", icon=ft.Icons.ERROR_OUTLINE)]
                busy.visible = False; page.update(); return
            blocks: list[ft.Control] = []
            if a.get("data_source") == "SYNTHETIC":
                blocks.append(notice("Synthetic data: " + a.get("note", ""), "error", icon=ft.Icons.SCIENCE_OUTLINED))
            q = a.get("quote")
            if q:
                blocks.append(ft.Row([
                    stat("Price", f"{q['price']:,.0f}"), stat("NAV", f"{q['nav']:,.2f}"),
                    stat("Premium", f"{q['premium_pct']:+.2f}%", token="error" if abs(q["premium_pct"] or 0) > 0.5 else "text"),
                    stat("Tracking error", f"{q['tracking_error_pct']:.2f}%"), stat("AUM", f"{(q['aum'] or 0) / 1e8:,.0f}억"),
                    stat("CU shares", f"{q['cu_units']:,.0f}"), stat("LP holding", f"{q['lp_holding_pct']:.1f}%"),
                    stat("Listed", q["listed"]),
                ], spacing=10, wrap=True))
            ps = a.get("premium_stats")
            if ps:
                blocks.append(ft.Row([chip(f"premium z {ps['z']:+.2f}", "accent"), chip(f"|premium| mean {ps['abs_mean']:.2f}%"),
                                      chip(f"half-life {ps['half_life']:.0f} sessions"), chip(f"ADF p {ps['adf_p']:.3f}"),
                                      chip(f"source: {a['data_source']}", "success" if a["data_source"] != "SYNTHETIC" else "muted")],
                                     spacing=6, wrap=True))
                blocks.append(card(xc.premium_chart(a["dates"], a["price"], a["nav"], a["premium_pct"],
                                                    title=f"{a['code']} price vs NAV")))
            lt = a.get("letf")
            if lt and "rows" in lt:
                blocks.append(ft.Row([stat(f"{lt['name']} drag, last-quarter vol", f"{lt['last_quarter_drag_bp']:+.0f} bp / qtr",
                                           token="error", tooltip=f"realised vol {lt['last_quarter_vol']:.1%}: the study's better reference")] +
                                     [stat(f"GARCH drag {r['sessions']}d", f"{r['drag_bp']:+.0f} bp",
                                           tooltip=f"variance {r['variance_bp']:+.0f} bp, fee {r['fee_bp']:+.0f} bp")
                                      for r in lt["rows"]] + [stat("Index cond. vol", f"{lt['cond_vol']:.1%}"),
                                                              stat("ν", f"{lt['nu']:.1f}"),
                                                              stat("Study verdict: GARCH drag", lt.get("verdict", "not run"),
                                                                   token="success" if lt.get("verdict") == "PASS" else "error",
                                                                   tooltip=lt.get("verdict_reason", ""))], spacing=10, wrap=True))
            sl = a.get("sleeves")
            if sl:
                blocks.append(ft.Row([
                    stat("Trend switch Sharpe", f"{sl['trend']['sharpe']:.2f}"), stat("Trend MDD", f"{sl['trend']['max_drawdown']:.0%}"),
                    stat("Vol-target Sharpe", f"{sl['vol_target']['sharpe']:.2f}"), stat("Buy & hold Sharpe", f"{sl['buy_hold']['sharpe']:.2f}"),
                    stat("B&H MDD", f"{sl['buy_hold']['max_drawdown']:.0%}"),
                    stat("Study verdict: trend", a["verdicts"]["trend"], token="success" if a["verdicts"]["trend"] == "PASS" else "error",
                         tooltip=a["verdict_reasons"]["trend"]),
                    stat("Study verdict: vol target", a["verdicts"]["vol"], token="success" if a["verdicts"]["vol"] == "PASS" else "error",
                         tooltip=a["verdict_reasons"]["vol"]),
                ], spacing=10, wrap=True))
                blocks.append(card(xc.equity_chart(a.get("sleeve_dates", a["dates"]), sl["equity_trend"], sl["equity_bh"],
                                                   title=f"10-month trend switch vs buy-and-hold ({sl['cost_bps']:.0f} bp per side)")))
            comps = a.get("components") or []
            if comps:
                top = sorted(comps, key=lambda c: -(c["weight_pct"] or 0))[:10]
                blocks.append(card(ft.Column([ft.Text("Top constituents", size=13, weight=ft.FontWeight.W_600, color=pal.text)] +
                                             [ft.Text(f"{c['code']}  {c['name']}  {c['weight_pct']:.2f}%", size=12, color=pal.text)
                                              for c in top], spacing=3)))
            blocks.append(analysis_panel(page, kind="etf_structure", narrative=narrative(a),
                                         payload_fn=lambda p=payload(a): p, deep_fn=insights.deep_analysis))
            host.controls = blocks; busy.visible = False; page.update()

        page.run_thread(worker)

    host.controls = [empty_state("Pick an ETF", "NAV premium and its half-life, the basket, the leveraged-fund drag "
                                 "from the GARCH variance term structure, and the trend / vol-target sleeve rules with "
                                 "the validation study's verdict.", icon=ft.Icons.INVENTORY_2_OUTLINED,
                                 action=ft.Button("Open Settings", on_click=lambda e: on_open_settings()) if on_open_settings else None)]
    return ft.Column([
        section("ETF", subtitle="NAV premium, basket, leveraged-fund drag, sleeve rules."),
        ft.Row([code, days, source, ft.Button("Analyze", icon=ft.Icons.PLAY_ARROW_ROUNDED, on_click=run), busy], spacing=10, wrap=True),
        ft.Column([host], scroll=ft.ScrollMode.AUTO, expand=True),
    ], spacing=14, expand=True)


if __name__ == "__main__":
    a = analyze("122630", days=504, source="synthetic")
    assert a["data_source"] == "SYNTHETIC" and "sleeves" in a and "letf" in a
    assert "rows" in a["letf"] and a["letf"]["rows"][0]["drag_bp"] < 0
    t = narrative(a)
    assert "SYNTHETIC" in t and "drag" in t and payload(a)["letf"]["beta"] == 2.0
    print("ok")
