"""Crypto — the kimchi premium, funding as carry, the market-regime score,
the app's GARCH(1,1)-t on Bitcoin, the ETH/BTC test, the weekday table and,
when an Upbit read-only key is configured, the holdings with their cost basis.

Everything is keyless public data (`data.crypto.crypto_client`) except the
balance read. Nothing here trades, and the page says so.
"""
from __future__ import annotations

import math
from typing import Callable, Optional

import flet as ft
import numpy as np

import config
from core.crypto import analytics as CA
from core.quant import insights
from core.theme import RADII, active
from ui.ai_panel import analysis_panel
from ui.components import card, chip, empty_state, notice, section, stat
import ui.xcharts as xc

MAJORS = ("ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT", "DOGEUSDT", "TRXUSDT", "LINKUSDT")
CRYPTO_DAYS = 365


def _synthetic() -> dict:
    rng = np.random.default_rng(6)
    n = 900
    ds = [str(np.datetime64("2024-04-01") + np.timedelta64(i, "D")) for i in range(n)]
    us = 60000 * np.exp(np.cumsum(rng.normal(0.0004, 0.03, n)))
    fx = 1380 + np.cumsum(rng.normal(0, 3, n))
    prem = np.zeros(n)
    for t in range(1, n):
        prem[t] = 0.92 * prem[t - 1] + rng.normal(0, 0.4)
    kr = us * fx * (1 + prem / 100)
    fund = rng.normal(0.0002, 0.0004, n)
    majors = {k: 100 * np.exp(np.cumsum(rng.normal(0.0005, 0.04, n))) for k in MAJORS}
    return {"dates": ds, "upbit": dict(zip(ds, kr)), "binance": dict(zip(ds, us)), "usdkrw": dict(zip(ds, fx)),
            "funding_daily": dict(zip(ds, fund)), "majors": majors, "eth": dict(zip(ds, majors["ETHUSDT"])),
            "volume": rng.random(n) * 100, "premium_index": {"premium_pct": 0.01, "last_funding_rate": 0.0001},
            "oi": [], "source": "SYNTHETIC"}


def _live(days: int) -> dict:
    from core.ficc.data import load_series
    from data.crypto.crypto_client import BinancePublic, UpbitPublic
    up = UpbitPublic().daily("KRW-BTC", days=days)
    bn = BinancePublic()
    btc = bn.daily("BTCUSDT", days=days)
    majors = {}
    for sym in MAJORS:
        try:
            majors[sym] = np.asarray(bn.daily(sym, days=400).close)
        except Exception:
            continue
    fund = bn.funding("BTCUSDT", days=min(days, 1500)).daily()
    fx = load_series("DEXKOUS", source="auto", days=days + 100)
    return {"dates": btc.dates, "upbit": dict(zip(up.dates, up.close)), "binance": dict(zip(btc.dates, btc.close)),
            "usdkrw": dict(zip(fx.dates, fx.values)), "usdkrw_source": fx.source, "funding_daily": fund, "majors": majors,
            "eth": dict(zip(*(lambda c: (c.dates, c.close))(bn.daily("ETHUSDT", days=days)))),
            "volume": np.asarray(btc.quote_volume), "premium_index": bn.premium_index("BTCUSDT"),
            "oi": bn.open_interest_hist("BTCUSDT"), "source": "LIVE"}


def analyze(*, days: int = 730, source: str = "live") -> dict:
    d = _live(days) if source == "live" else _synthetic()
    out: dict = {"source": d["source"], "usdkrw_source": d.get("usdkrw_source", "synthetic")}
    out["kimchi"] = CA.kimchi_premium(d["upbit"], d["binance"], d["usdkrw"])
    try:
        out["funding"] = CA.funding_carry(d["funding_daily"], d["binance"])
    except ValueError as exc:
        out["funding"] = None; out["funding_error"] = str(exc)
    btc = np.array([d["binance"][k] for k in sorted(d["binance"])])
    fa = out["funding"].last_ann_pct if out["funding"] else None
    out["regime"] = CA.regime_score(btc, d["majors"], funding_ann_pct=fa)
    out["ethbtc"] = CA.eth_btc_test(d["eth"], d["binance"])
    out["weekday"] = CA.weekday_table(sorted(d["binance"]), btc, np.asarray(d["volume"])[-btc.size:])
    from core.quant.garch import fit_garch
    r = np.diff(np.log(btc))[-730:]
    fit = fit_garch(r, dist="t", profile=False)
    out["garch"] = {"nu": fit.nu, "alpha": fit.alpha, "beta": fit.beta, "persistence": fit.persistence,
                    "half_life": fit.half_life, "cond_vol_365": fit.cond_vol_last / math.sqrt(252) * math.sqrt(CRYPTO_DAYS),
                    "uncond_vol_365": fit.uncond_vol / math.sqrt(252) * math.sqrt(CRYPTO_DAYS) if math.isfinite(fit.uncond_vol) else float("nan"),
                    "converged": fit.converged, "at_bound": list(fit.at_bound), "n": int(r.size)}
    out["premium_index"] = d["premium_index"]; out["oi"] = d["oi"]
    out["btc_dates"] = sorted(d["binance"]); out["btc"] = btc
    out["balances"] = None
    if config.upbit_ready() and source == "live":
        try:
            from data.crypto.crypto_client import UpbitAccount, UpbitPublic
            bal = UpbitAccount().balances()
            tick = {t["market"]: t["price"] for t in UpbitPublic().ticker([f"KRW-{b['currency']}" for b in bal if b["currency"] != "KRW"])} if bal else {}
            for b in bal:
                b["krw_value"] = b["total"] if b["currency"] == "KRW" else b["total"] * tick.get(f"KRW-{b['currency']}", 0.0)
            out["balances"] = bal
        except Exception as exc:
            out["balances_error"] = f"{type(exc).__name__}: {exc}"
    from core.quant.validate import load_cards
    from pathlib import Path
    cards = {c["card_id"]: c for c in load_cards(Path(__file__).resolve().parents[1] / "docs" / "asset_expansion" / "cards")}
    out["verdicts"] = {k: cards.get(k, {}).get("decision", "not run") for k in
                       ("M_C1_kimchi", "M_C4_funding", "S_C3_crypto_trend_btcusd", "S_C3_crypto_trend_krwbtc",
                        "D_C2_garch_btc", "D_C2_skewt_btc", "M_C8_ethbtc")}
    return out


def narrative(a: dict) -> str:
    kp, fc, rs, g = a["kimchi"], a["funding"], a["regime"], a["garch"]
    parts = [
        f"Korea pays {kp.last_pct:+.2f} % against the world price for bitcoin ({kp.last_z:+.1f} standard deviations from its one-year mean; "
        f"average {kp.mean_pct:+.2f} %, peak {kp.max_pct:.1f} % since {kp.dates[0]}); the premium's half-life is {kp.half_life_days:.0f} days "
        f"(ADF p = {kp.adf_p:.3f}). It is a signal, not a trade: remittance limits, the Travel Rule and the 2027 tax close the arbitrage"
        + (f", and its predictive slope on next-week returns is {kp.pred_slope:+.4f} (t {kp.pred_t:+.1f})." if math.isfinite(kp.pred_t) else "."),
    ]
    if fc:
        parts.append(f"Perpetual funding runs {fc.last_ann_pct:+.1f} % a year on the 7-day mean, the {fc.percentile:.0%} percentile since "
                     f"{fc.dates[0]} ({fc.flag}); after top-decile funding the next 30 days returned {fc.top_decile_fwd30:+.1%} against "
                     f"{fc.bottom_decile_fwd30:+.1%} after bottom-decile funding (bootstrap p {fc.bootstrap_p:.2f}).")
    live = [c for c in rs.components if c.score is not None]
    parts.append(f"The regime score is {rs.score:.0f}/100 ({rs.zone}) from {len(live)} components: " +
                 "; ".join(f"{c.label} {c.score:.0f} ({c.signal})" for c in live) + ". " + rs.note)
    parts.append(f"GARCH(1,1)-t on {g['n']} days of BTCUSDT: ν {g['nu']:.1f}, persistence {g['persistence']:.3f} "
                 f"(half-life {g['half_life']:.0f} days), conditional vol {g['cond_vol_365']:.0%} on a 365-day basis"
                 f"{'' if g['converged'] else '; the solver did not converge'}"
                 f"{'; at bound: ' + ', '.join(g['at_bound']) if g['at_bound'] else ''}. The validation study's verdict for this fan on "
                 f"Bitcoin is {a['verdicts']['D_C2_garch_btc']}.")
    parts.append(f"ln(ETH/BTC): {a['ethbtc']['verdict']} (ADF p {a['ethbtc']['adf_p']:.3f}, half-life {a['ethbtc']['half_life_days']:.0f} days).")
    if a["source"] == "SYNTHETIC":
        parts.append("All series are SYNTHETIC.")
    return " ".join(parts)


def payload(a: dict) -> dict:
    kp, fc, rs = a["kimchi"], a["funding"], a["regime"]
    return {"source": a["source"], "kimchi": {"last_pct": kp.last_pct, "z": kp.last_z, "mean_pct": kp.mean_pct, "max_pct": kp.max_pct,
                                              "half_life_days": kp.half_life_days, "adf_p": kp.adf_p, "pred_t": kp.pred_t, "n": kp.n},
            "funding": ({"last_ann_pct": fc.last_ann_pct, "percentile": fc.percentile, "flag": fc.flag, "top_decile_fwd30": fc.top_decile_fwd30,
                         "bottom_decile_fwd30": fc.bottom_decile_fwd30, "bootstrap_p": fc.bootstrap_p} if fc else None),
            "premium_index": a["premium_index"], "regime": {"score": rs.score, "zone": rs.zone, "components":
                                                            [{"key": c.key, "score": c.score, "signal": c.signal} for c in rs.components]},
            "garch": a["garch"], "ethbtc": a["ethbtc"], "weekday": a["weekday"], "verdicts": a["verdicts"],
            "holdings": [{k: v for k, v in b.items()} for b in (a.get("balances") or [])]}


def build_crypto_page(page: ft.Page, on_open_settings: Optional[Callable] = None) -> ft.Control:
    pal = active()
    source = ft.Dropdown(label="Source", width=260, value="live",
                         options=[ft.dropdown.Option("live", "Upbit + Binance (keyless)"), ft.dropdown.Option("synthetic", "Synthetic demo")])
    days = ft.TextField(label="Days", value="730", width=100, border_radius=RADII["md"])
    busy = ft.ProgressRing(visible=False, width=20, height=20)
    host = ft.Column(spacing=14)

    def run(e=None) -> None:
        busy.visible = True; host.controls = []; page.update()

        def worker():
            try:
                a = analyze(days=int(float(days.value or "730")), source=source.value or "live")
            except Exception as exc:
                host.controls = [notice(f"{type(exc).__name__}: {exc}", "error", icon=ft.Icons.ERROR_OUTLINE)]
                busy.visible = False; page.update(); return
            kp, fc, rs, g = a["kimchi"], a["funding"], a["regime"], a["garch"]
            blocks: list[ft.Control] = []
            blocks.append(notice("Read-only: QUANTGEN never submits crypto orders, never holds a wallet key, and never assumes an "
                                 "account on an unregistered foreign exchange. Binance is public data only.", "accent",
                                 icon=ft.Icons.LOCK_OUTLINE))
            if a["source"] == "SYNTHETIC":
                blocks.append(notice("Synthetic data: every series here is simulated.", "error", icon=ft.Icons.SCIENCE_OUTLINED))
            blocks.append(ft.Row([chip(f"source: {a['source']}", "success" if a["source"] == "LIVE" else "muted"),
                                  chip(f"USD/KRW: {a['usdkrw_source']}"), chip(f"{kp.n} premium days")] +
                                 [chip(f"{k.split('_', 2)[-1]}: {v}", "success" if v == "PASS" else "muted") for k, v in a["verdicts"].items()],
                                 spacing=6, wrap=True))
            blocks.append(ft.Row([
                stat("Kimchi premium", f"{kp.last_pct:+.2f}%", token="error" if abs(kp.last_pct) > 3 else "text"),
                stat("Premium z (1y)", f"{kp.last_z:+.2f}"), stat("Half-life", f"{kp.half_life_days:.0f} d"),
                stat("Funding (ann.)", f"{fc.last_ann_pct:+.1f}%" if fc else "n/a", token="error" if fc and fc.flag != "normal" else "text",
                     tooltip=fc.flag if fc else ""),
                stat("Funding pct", f"{fc.percentile:.0%}" if fc else "n/a"),
                stat("Perp premium", f"{a['premium_index'].get('premium_pct', 0):+.3f}%"),
                stat("Regime", f"{rs.score:.0f} · {rs.zone}", token="success" if rs.zone == "RISK_ON" else "error" if rs.zone == "RISK_OFF" else "text"),
                stat("BTC cond. vol (365d)", f"{g['cond_vol_365']:.0%}"), stat("ν", f"{g['nu']:.1f}", token="error" if g["at_bound"] else "text"),
            ], spacing=10, wrap=True))
            blocks.append(card(xc.lines_chart(kp.dates, {"kimchi premium %": kp.premium_pct}, title="Kimchi premium (Upbit KRW-BTC vs Binance × USD/KRW)",
                                              hlines={"0": 0.0}, pct=True)))
            if fc:
                blocks.append(card(xc.lines_chart(fc.dates, {"funding (ann. %)": fc.carry_ann_pct}, title="Perpetual funding, 7-day mean annualised",
                                                  hlines={"0": 0.0}, pct=True)))
            blocks.append(card(xc.bars_chart([c.label for c in rs.components], [c.score for c in rs.components],
                                             title=f"Regime components (score {rs.score:.0f}, {rs.zone})",
                                             annotate=[c.signal for c in rs.components])))
            px = a["btc"]
            sma50 = np.convolve(px, np.ones(50) / 50, mode="valid"); sma200 = np.convolve(px, np.ones(200) / 200, mode="valid")
            blocks.append(card(xc.lines_chart(a["btc_dates"], {"BTCUSDT": px, "SMA50": np.concatenate([np.full(49, np.nan), sma50]),
                                                              "SMA200": np.concatenate([np.full(199, np.nan), sma200])}, title="BTCUSDT with 50/200-day averages")))
            wt = a["weekday"]
            blocks.append(card(ft.Column([ft.Text("Weekday table (returns %, vol %, mean quote volume)", size=13, weight=ft.FontWeight.W_600, color=pal.text)] +
                                         [ft.Text(f"{r['day']}  n {r['n']}  mean {r['mean_ret_pct']:+.3f}  vol {r['vol_pct']:.2f}  volume {r['mean_volume']:,.0f}",
                                                  size=12, color=pal.text, font_family="Consolas, monospace") for r in wt["rows"]] +
                                         [ft.Text(f"weekday effect p (Bonferroni) {wt['return_effect_p_bonferroni']:.2f}; weekend volume ratio "
                                                  f"{wt['weekend_volume_ratio']:.2f} (p {wt['weekend_volume_p']:.1e})", size=11, color=pal.muted)], spacing=3)))
            if a.get("balances"):
                total = sum(b["krw_value"] for b in a["balances"])
                blocks.append(card(ft.Column([ft.Text(f"Upbit holdings (read-only): ₩{total:,.0f}", size=13, weight=ft.FontWeight.W_600, color=pal.text)] +
                                             [ft.Text(f"{b['currency']}  {b['total']:.6f}  avg buy {b['avg_buy_price']:,.0f}  value ₩{b['krw_value']:,.0f}",
                                                      size=12, color=pal.text, font_family="Consolas, monospace") for b in a["balances"]] +
                                             [ft.Text("avg_buy_price is the cost-basis record for the 2027 virtual-asset tax; this page computes no tax.",
                                                      size=11, color=pal.muted)], spacing=3)))
            elif a.get("balances_error"):
                blocks.append(notice(f"Upbit balance read failed: {a['balances_error']}", "error"))
            elif not config.upbit_ready():
                blocks.append(ft.Text("Set UPBIT_ACCESS_KEY / UPBIT_SECRET_KEY (자산조회 scope only) to show holdings.", size=11, color=pal.muted))
            blocks.append(analysis_panel(page, kind="crypto_market", narrative=narrative(a),
                                         payload_fn=lambda p=payload(a): p, deep_fn=insights.deep_analysis))
            host.controls = blocks; busy.visible = False; page.update()

        page.run_thread(worker)

    host.controls = [empty_state("Refresh the crypto sheet", "Kimchi premium, perpetual funding as carry, the six-component regime "
                                 "score, GARCH-t on Bitcoin, the ETH/BTC test and the weekday table, all from keyless Upbit and "
                                 "Binance data; Upbit holdings when a read-only key is set.", icon=ft.Icons.CURRENCY_BITCOIN,
                                 action=ft.Button("Open Settings", on_click=lambda e: on_open_settings()) if on_open_settings else None)]
    return ft.Column([
        section("Crypto", subtitle="Kimchi premium, funding carry, regime, GARCH-t on Bitcoin — read-only."),
        ft.Row([source, days, ft.Button("Refresh", icon=ft.Icons.REFRESH, on_click=run), busy], spacing=10, wrap=True),
        ft.Column([host], scroll=ft.ScrollMode.AUTO, expand=True),
    ], spacing=14, expand=True)


if __name__ == "__main__":
    a = analyze(source="synthetic")
    assert a["source"] == "SYNTHETIC" and a["kimchi"].n > 800 and a["regime"].zone in ("RISK_ON", "NEUTRAL", "RISK_OFF")
    assert a["garch"]["n"] == 730 and len(a["weekday"]["rows"]) == 7
    t = narrative(a)
    assert "Korea pays" in t and "regime score" in t and "SYNTHETIC" in t
    p = payload(a)
    assert p["regime"]["components"] and p["kimchi"]["n"] == a["kimchi"].n
    print("ok")
