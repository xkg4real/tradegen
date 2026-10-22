"""Derivatives — KOSPI200 futures basis, the option board, the volatility
surface, the risk-neutral density, the box-spread funding rate, and the
hedger's P&L simulation for the structuring pages.

Live data comes from the KIS asset domains (`data.kis_markets`): the whole
option chain of one expiry (paged), the front futures quote with KIS's own
theoretical price, the CD 91-day rate, and the KOSPI200 index history for the
GARCH fit. Without KIS the page runs on a synthetic board and says so.

Every quantity is computed by `core.ficc.equity_deriv` and printed here in
the desk's units: index points, vol points, basis points of notional.
"""
from __future__ import annotations

import math
from datetime import date
from typing import Callable, Optional

import flet as ft
import numpy as np

import config
from core.ficc import equity_deriv as ED
from core.ficc.common import BP, FICCError
from core.ficc.swaps import black76
from core.quant import insights
from core.theme import RADII, active
from ui.ai_panel import analysis_panel
from ui.components import card, chip, empty_state, notice, section, stat
import ui.xcharts as xc

_SOURCES = [("kis", "KIS live (KOSPI200 board)"), ("synthetic", "Synthetic demo board")]
_ENGINES = [("gbm", "GBM at the ATM vol"), ("garch_t", "GARCH(1,1)-t on the index history")]


def synthetic_board(F: float = 1126.0, T: float = 20 / 365, r: float = 0.032, seed: int = 3):
    """A smile-shaped board with two-sided quotes, for the demo and the tests."""
    rng = np.random.default_rng(seed)
    df = math.exp(-r * T)
    quotes = []
    for k in np.arange(round(F * 0.85 / 2.5) * 2.5, F * 1.15, 2.5):
        v = 0.17 + 0.5 * max(0.0, math.log(F / k)) + 0.8 * math.log(k / F) ** 2
        c, p = black76(F, k, T, v, df, True).price, black76(F, k, T, v, df, False).price
        sp = max(0.01, 0.02 * c ** 0.5) if k >= F else max(0.01, 0.02 * p ** 0.5)
        quotes.append(ED.Quote(strike=float(k), call_mid=c, put_mid=p, call_bid=max(c - sp, 0.01), call_ask=c + sp,
                               put_bid=max(p - sp, 0.01), put_ask=p + sp,
                               call_iv_exchange=v + rng.normal(0, 0.001), put_iv_exchange=v + rng.normal(0, 0.001)))
    return quotes


def snapshot(*, source: str = "kis", expiry: str = "", rate_pct: Optional[float] = None, engine: str = "gbm",
             n_paths: int = 3000, horizon_days: Optional[int] = None) -> dict:
    """Everything the page shows, as plain numbers. Raises FICCError with a
    readable reason when the board cannot be used."""
    out: dict = {"source": source}
    if source == "kis":
        if not config.kis_ready():
            raise FICCError("KIS_APP_KEY / KIS_APP_SECRET are not configured; choose the synthetic board.")
        from data.kis_markets import KISMarkets, front_contract
        km = KISMarkets()
        expiries = km.option_expiries()
        exp = expiry.strip() or (expiries[0] if expiries else "")
        if not exp:
            raise FICCError("KIS returned no option expiries.")
        code = front_contract("KOSPI200") or "A01612"
        fq = km.futures_quote(code)
        # the board endpoint stops at its highest 100 strikes; quote the chain series by series around spot
        board = km.option_chain(exp, float(fq["underlying_level"]), width=0.10, step_pts=2.5, include_book=True)
        ys = km.krw_yields_snapshot()
        cd = next((y["yield_pct"] for y in ys if y["code"] == "Y0112"), None)
        rate = (rate_pct / 100.0) if rate_pct is not None else (cd / 100.0 if cd else 0.03)
        quotes = ED.board_quotes(board)
        idx = km.index_daily("2001", days=600)
        # with the market closed every last print and KIS IV belongs to the last session: measure T from it
        sess = idx.dates[-1]
        T = max((date.fromisoformat(board.expiry_date) - date.fromisoformat(sess)).days, 1) / 365.0
        live = any(x.bid and x.ask for x in board.calls + board.puts)
        out.update(expiry=exp, expiry_date=board.expiry_date, expiries=expiries, as_of=board.as_of, session=sess, live_quotes=live,
                   rate=rate, rate_source=("CD 91d (KIS)" if rate_pct is None and cd else "input"), T=T,
                   futures=fq, index_dates=idx.dates, index_close=np.asarray(idx.close),
                   n_calls=len(board.calls), n_puts=len(board.puts))
    else:
        T = 20 / 365
        rate = (rate_pct / 100.0) if rate_pct is not None else 0.032
        quotes = synthetic_board(1126.0, T, rate)
        rng = np.random.default_rng(1)
        px = 1126.0 * np.exp(np.cumsum(rng.normal(0, 0.011, 600)) - 0.3)
        px = px / px[-1] * 1126.0
        out.update(expiry="DEMO", expiry_date=(date.today()).isoformat(), expiries=["DEMO"], as_of="synthetic",
                   session="synthetic", live_quotes=True, rate=rate, rate_source="assumed", T=T,
                   futures={"code": "DEMO", "name": "synthetic front", "price": 1126.0 * (1 + rate * T) + 0.8,
                            "theo": 1126.0 * (1 + rate * T), "underlying_level": 1126.0, "days_left": 20, "basis": 0.8},
                   index_dates=tuple(f"d{i}" for i in range(600)), index_close=px, n_calls=len(quotes), n_puts=len(quotes))
    F, k0 = ED.implied_forward(quotes, rate, T)
    pts = ED.chain_implied_vols(quotes, F, T, rate, quoted_only=True, max_moneyness=0.15)
    if len(pts) < 5:                                   # no two-sided book (after hours): fall back to last prints
        pts = ED.chain_implied_vols(quotes, F, T, rate, quoted_only=False, max_moneyness=0.10)
        out["quotes_note"] = "no two-sided quotes; implied vols from last prints"
    if len(pts) < 5:
        raise FICCError(f"only {len(pts)} usable quotes within ±15 % of the forward; the chain is too thin right now.")
    rec = ED.reconcile_iv(pts)
    par = ED.parity_residuals(quotes, F, T, rate)
    arb = ED.static_arbitrage(quotes, quoted_only=True, F=F, max_moneyness=0.15)
    fit = ED.fit_svi([p.log_moneyness for p in pts], [p.iv for p in pts], T,
                     weights=[1.0 / max(p.spread or 0.05, 0.01) for p in pts])
    atm = min(pts, key=lambda p: abs(p.log_moneyness))
    try:
        mv = ED.mfiv(quotes, F, T, rate)
    except FICCError as exc:
        mv = {"vol": float("nan"), "n_strikes": 0, "error": str(exc)}
    rnd = ED.rnd_from_svi(fit, F, rate)
    box = None
    try:
        below = max(q.strike for q in quotes if q.strike <= F)
        above = min(q.strike for q in quotes if q.strike > F)
        # a box from closed-market last prints is four stale prices: not a rate
        box = ED.box_rate(quotes, T, k1=below, k2=above) if out.get("live_quotes", True) else None
    except (FICCError, ValueError):
        box = None
    fq = out["futures"]
    basis = ED.basis_report(fq["price"], fq["underlying_level"], rate, max(fq.get("days_left") or 1, 1) / 365.0,
                            exchange_theo=fq.get("theo"))
    # hedge P&L simulation: short an ATM option at the SVI ATM vol, hedged daily
    hz = int(horizon_days or max(round(T * 252), 5))
    sigma_h = float(ED.svi_vol(fit, np.array([0.0]))[0])
    spot = float(fq["underlying_level"])
    garch_fit = None
    if engine == "garch_t":
        from core.quant.garch import fit_garch
        r = np.diff(np.log(out["index_close"]))
        garch_fit = fit_garch(r, dist="t", profile=False)
    sim = ED.hedge_pnl_simulation(spot=spot, strike=round(F / 2.5) * 2.5, horizon_days=hz, sigma_hedge=sigma_h,
                                  rate=rate, engine=engine, garch_fit=garch_fit, n_paths=n_paths, seed=7)
    out.update(F=F, k0=k0, points=pts, reconcile=rec, parity=par, arbitrage=arb, svi=fit, atm=atm, mfiv=mv, rnd=rnd,
               box=box, basis=basis, sigma_h=sigma_h, hedge=sim, garch=garch_fit, n_quotes=len(quotes))
    return out


def narrative(s: dict) -> str:
    fq, b, fit, sim = s["futures"], s["basis"], s["svi"], s["hedge"]
    par_within = [x["within"] for x in s["parity"] if x["within"] is not None]
    within = (sum(par_within) / len(par_within)) if par_within else float("nan")
    mv = s["mfiv"]
    txt = [
        f"Board {s['expiry']} (expires {s['expiry_date']}, {s['T'] * 365:.0f} days) with {s['n_quotes']} strikes; the "
        f"parity-implied forward is {s['F']:.2f} against a {fq.get('name', 'front future')} at {fq['price']:.2f} and the index "
        f"at {fq['underlying_level']:.2f}.",
        f"The front future trades {b.basis_pts:+.2f} points over spot; cost-of-carry fair value at {s['rate']:.2%} "
        f"({s['rate_source']}) is {b.fair:.2f}, so the contract is {'rich' if b.rich else 'cheap'} by "
        f"{abs(b.mispricing_bp):.0f} bp of spot (implied simple funding {b.implied_rate:.2%})"
        + (f"; KIS's own theoretical price {fq['theo']:.2f} differs by {b.theo_gap_pts:+.2f} points, the dividend-point convention."
           if b.theo_gap_pts is not None else "."),
        f"ATM implied vol {s['atm'].iv:.1%} from the app's Black-76 inversion; the exchange's IV agrees within a median "
        f"{s['reconcile']['median_volpts']:.2f} vol points on {s['reconcile']['n']} quoted strikes"
        f"{' (within the 0.5-point gate)' if s['reconcile']['ok'] else ' (outside the 0.5-point gate: check the convention)'}. "
        f"SVI fits the smile with RMSE {fit.rmse_volpts:.2f} vol points, skew ρ {fit.rho:+.2f}"
        f"{', arbitrage-free' if fit.arbitrage_free else ', with a butterfly-arbitrage region'}.",
        (f"Model-free implied vol {mv['vol']:.1%} over {mv['n_strikes']} strikes (VKOSPI-style strip)."
         if mv.get("n_strikes") else f"Model-free variance not computed: {mv.get('error', '')}"),
        f"Put–call parity holds within half the summed spread on {within:.0%} of near strikes; butterfly violations on quoted "
        f"mids: {s['arbitrage']['call_butterfly']} calls, {s['arbitrage']['put_butterfly']} puts.",
        (f"The ATM box implies a KRW funding rate of {s['box']['rate']:.2%} against {s['rate']:.2%} "
         f"({(s['box']['rate'] - s['rate']) / BP:+.0f} bp)." if s["box"] else "No ATM box could be priced from the mids."),
        f"Hedge simulation ({sim.engine}, {sim.n_paths:,} paths, {sim.horizon} sessions): selling the ATM option at σ_h = "
        f"{sim.sigma_hedge:.1%} and delta-hedging daily earns {sim.mean_pnl_bp:+.0f} bp of notional on average "
        f"(SE {sim.se_bp:.0f} bp), CVaR95 {sim.cvar95_bp:+.0f} bp; the hedge breaks even at a realised vol of "
        f"{sim.breakeven_vol:.1%}. The identity ½Σe^{{r(T−t)}}ΓS²(σ_h² − r²/Δ)Δ explains the P&L with slope "
        f"{sim.identity_slope:.2f} and R² {sim.identity_r2:.2f}.",
    ]
    if s.get("garch") is not None:
        g = s["garch"]
        txt.append(f"GARCH-t on the index: ν {g.nu:.1f}, persistence {g.persistence:.3f}, conditional vol "
                   f"{g.cond_vol_last:.1%} (guardrails: {', '.join(g.at_bound) or 'clear'}"
                   f"{'' if g.converged else '; solver did not converge'}).")
    return " ".join(txt)


def payload(s: dict) -> dict:
    fit, sim, b = s["svi"], s["hedge"], s["basis"]
    return {"source": s["source"], "expiry": s["expiry"], "expiry_date": s["expiry_date"], "T_years": s["T"],
            "rate": s["rate"], "forward": s["F"], "k0": s["k0"], "futures": s["futures"],
            "basis": {"basis_pts": b.basis_pts, "fair": b.fair, "mispricing_bp": b.mispricing_bp,
                      "implied_rate": b.implied_rate, "theo_gap_pts": b.theo_gap_pts},
            "atm_iv": s["atm"].iv, "mfiv": s["mfiv"].get("vol"), "iv_reconcile": s["reconcile"],
            "svi": {"a": fit.a, "b": fit.b, "rho": fit.rho, "m": fit.m, "sigma": fit.sigma, "rmse_volpts": fit.rmse_volpts,
                    "min_g": fit.min_g, "arbitrage_free": fit.arbitrage_free},
            "static_arbitrage": s["arbitrage"], "box_rate": s["box"]["rate"] if s["box"] else None,
            "rnd": {"integral": s["rnd"]["integral"], "mean": s["rnd"]["mean"]},
            "hedge": {"engine": sim.engine, "sigma_hedge": sim.sigma_hedge, "mean_pnl_bp": sim.mean_pnl_bp, "se_bp": sim.se_bp,
                      "cvar95_bp": sim.cvar95_bp, "breakeven_vol": sim.breakeven_vol, "identity_slope": sim.identity_slope,
                      "identity_r2": sim.identity_r2},
            "smile": [{"strike": p.strike, "iv": p.iv, "iv_exchange": p.iv_exchange, "kind": p.kind} for p in s["points"]]}


def build_derivatives_page(page: ft.Page, on_open_settings: Optional[Callable] = None) -> ft.Control:
    pal = active()
    source = ft.Dropdown(label="Board", width=260, value="kis" if config.kis_ready() else "synthetic",
                         options=[ft.dropdown.Option(k, v) for k, v in _SOURCES])
    expiry = ft.TextField(label="Expiry YYYYMM", hint_text="blank = nearest", width=150, border_radius=RADII["md"])
    rate = ft.TextField(label="Rate % (blank = CD 91d)", width=170, border_radius=RADII["md"])
    engine = ft.Dropdown(label="Hedge-sim engine", width=260, value="gbm",
                         options=[ft.dropdown.Option(k, v) for k, v in _ENGINES])
    paths = ft.TextField(label="Paths", value="3000", width=100, border_radius=RADII["md"])
    busy = ft.ProgressRing(visible=False, width=20, height=20)
    host = ft.Column(spacing=14)

    def run(e=None) -> None:
        busy.visible = True
        host.controls = []
        page.update()

        def worker():
            try:
                rp = float(rate.value) if (rate.value or "").strip() else None
                s = snapshot(source=source.value or "kis", expiry=expiry.value or "", rate_pct=rp,
                             engine=engine.value or "gbm", n_paths=int(float(paths.value or "3000")))
            except (FICCError, ValueError) as exc:
                host.controls = [notice(str(exc), "error", icon=ft.Icons.ERROR_OUTLINE)]
                busy.visible = False; page.update(); return
            except Exception as exc:
                host.controls = [notice(f"{type(exc).__name__}: {exc}", "error", icon=ft.Icons.ERROR_OUTLINE)]
                busy.visible = False; page.update(); return
            b, fit, sim, rec = s["basis"], s["svi"], s["hedge"], s["reconcile"]
            blocks: list[ft.Control] = []
            if s["source"] != "kis":
                blocks.append(notice("Synthetic board: a smile-shaped demo chain, not market quotes.", "error",
                                     icon=ft.Icons.SCIENCE_OUTLINED))
            if not s.get("live_quotes", True):
                blocks.append(notice(f"Market closed: these are the last prints of {s['session']}, struck at different moments, "
                                     "not quotes. The parity, butterfly and reconciliation figures are indicative until the "
                                     "09:00–15:45 KST session.", "error", icon=ft.Icons.NIGHTLIGHT_OUTLINED))
            blocks.append(ft.Row([chip(f"expiry {s['expiry']} → {s['expiry_date']}"), chip(f"as of {s['as_of']}"),
                                  chip(f"prices of {s.get('session', '?')}"), chip(f"rate {s['rate']:.2%} ({s['rate_source']})"),
                                  chip(f"{s['n_quotes']} strikes"),
                                  chip(f"{len(s['points'])} {'quoted' if s.get('live_quotes', True) else 'last-print'} near-ATM", "accent")],
                                 spacing=6, wrap=True))
            blocks.append(ft.Row([
                stat("Forward (parity)", f"{s['F']:.2f}"), stat("Front future", f"{s['futures']['price']:.2f}"),
                stat("Basis (pts)", f"{b.basis_pts:+.2f}"), stat("Fair value", f"{b.fair:.2f}"),
                stat("Mispricing", f"{b.mispricing_bp:+.0f} bp", token="error" if abs(b.mispricing_bp) > 20 else "text"),
                stat("Implied funding", f"{b.implied_rate:.2%}"),
                stat("KIS theo gap", f"{b.theo_gap_pts:+.2f} pts" if b.theo_gap_pts is not None else "n/a"),
            ], spacing=10, wrap=True))
            blocks.append(ft.Row([
                stat("ATM IV", f"{s['atm'].iv:.1%}"),
                stat("MFIV", f"{s['mfiv'].get('vol', float('nan')):.1%}" if s["mfiv"].get("n_strikes") else "n/a"),
                stat("SVI ρ", f"{fit.rho:+.2f}"), stat("SVI RMSE", f"{fit.rmse_volpts:.2f} pts",
                                                       token="error" if fit.rmse_volpts > 1.0 else "text"),
                stat("IV gap vs KIS", f"{rec['median_volpts']:.2f} pts", token="success" if rec["ok"] else "error",
                     tooltip="median |σ_app − σ_KIS| on quoted strikes within ±15 % of F; gate 0.5"),
                stat("Butterfly viol.", f"{s['arbitrage']['call_butterfly'] + s['arbitrage']['put_butterfly']}",
                     token="error" if s["arbitrage"]["call_butterfly"] + s["arbitrage"]["put_butterfly"] else "success"),
                stat("Box rate", f"{s['box']['rate']:.2%}" if s["box"] else "n/a"),
                stat("RND ∫", f"{s['rnd']['integral']:.3f}"),
            ], spacing=10, wrap=True))
            blocks.append(card(xc.smile_chart(s["points"], fit, s["F"], title=f"KOSPI200 {s['expiry']} smile")))
            p_samples = None
            if s.get("garch") is not None:
                from core.quant.garch import simulate_returns
                shocks, _ = simulate_returns(s["garch"], n_paths=3000, horizon=max(int(round(s["T"] * 252)), 2), seed=3,
                                             drift_daily=0.0)
                p_samples = s["futures"]["underlying_level"] * np.exp(shocks.sum(axis=1))
            blocks.append(card(xc.density_chart(s["rnd"], p_samples=p_samples)))
            blocks.append(ft.Row([
                stat("Hedge P&L (mean)", f"{sim.mean_pnl_bp:+.0f} bp", token="success" if sim.mean_pnl_bp > 0 else "error",
                     tooltip="short the ATM option at σ_h, delta-hedged daily; bp of notional"),
                stat("SE", f"{sim.se_bp:.0f} bp"), stat("CVaR95", f"{sim.cvar95_bp:+.0f} bp", token="error"),
                stat("σ_h", f"{sim.sigma_hedge:.1%}"), stat("Break-even realised vol", f"{sim.breakeven_vol:.1%}"),
                stat("Identity slope / R²", f"{sim.identity_slope:.2f} / {sim.identity_r2:.2f}"),
                stat("Engine", sim.engine),
            ], spacing=10, wrap=True))
            blocks.append(analysis_panel(page, kind="kospi200_derivatives", narrative=narrative(s),
                                         payload_fn=lambda p=payload(s): p, deep_fn=insights.deep_analysis))
            host.controls = blocks
            busy.visible = False
            page.update()

        page.run_thread(worker)

    host.controls = [empty_state("Load the board",
                                 "The nearest KOSPI200 expiry from KIS (or a synthetic demo): futures basis and fair value, "
                                 "the Black-76 smile against the exchange's IV, an SVI fit with the butterfly check, the "
                                 "model-free variance, the risk-neutral density, the box-spread funding rate, and a hedge "
                                 "P&L simulation in bp of notional.", icon=ft.Icons.STACKED_LINE_CHART_OUTLINED,
                                 action=ft.Button("Open Settings", on_click=lambda e: on_open_settings())
                                 if on_open_settings else None)]
    return ft.Column([
        section("Derivatives", subtitle="KOSPI200 futures basis, option surface, risk-neutral density, box rate, hedge P&L."),
        ft.Row([source, expiry, rate, engine, paths, ft.Button("Load", icon=ft.Icons.PLAY_ARROW_ROUNDED, on_click=run), busy],
               spacing=10, wrap=True),
        ft.Column([host], scroll=ft.ScrollMode.AUTO, expand=True),
    ], spacing=14, expand=True)


if __name__ == "__main__":
    s = snapshot(source="synthetic", n_paths=800)
    assert abs(s["F"] - 1126.0) < 0.5 and s["reconcile"]["ok"] and s["svi"].rmse_volpts < 0.3
    assert 0.99 < s["rnd"]["integral"] < 1.01 and s["box"] and abs(s["box"]["rate"] - s["rate"]) < 1e-6
    assert abs(s["mfiv"]["vol"] - s["atm"].iv) < 0.05
    text = narrative(s)
    assert "forward" in text and "Hedge simulation" in text and payload(s)["svi"]["rmse_volpts"] < 0.3
    print("ok")
