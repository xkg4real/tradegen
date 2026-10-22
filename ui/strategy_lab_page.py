"""Strategy Lab — the validation scorecard and a live run of any strategy
family through the same gate.

Section one reads the model cards the study wrote (`docs/asset_expansion/
cards/*.json`) and shows every verdict with its plain-language lines, so what
the app offers and what it refuses is visible in one table. Section two runs a
family (trend switch, vol target, cross-sectional momentum, TSMOM, crypto
trend, risk parity, pairs) on symbols the operator names, through the purged
walk-forward and the full gate, and shows the equity curve, the statistics and
the decision. N trials equals the grid size; the card ledger says so.
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Callable, Optional

import flet as ft
import numpy as np

from core.quant import insights
from core.quant import strategies as S
from core.quant import validate as V
from core.quant.history import HistoryError, convention_warning, load_history
from core.theme import RADII, active
from ui.ai_panel import analysis_panel
from ui.components import card, chip, empty_state, notice, section, stat
import ui.xcharts as xc

ROOT = Path(__file__).resolve().parents[1]
CARDS_DIR = ROOT / "docs" / "asset_expansion" / "cards"
_TOKEN = {"PASS": "success", "REVISE": "accent", "REJECT": "error", "INSUFFICIENT_DATA": "muted"}

FAMILIES = {
    "trend_switch": ("Trend switch (Faber SMA / MOP sign)", S.trend_switch,
                     S.grid_from(rule=["sma", "tsmom"], lookback=[126, 210, 252], step=[21, 42]), 21),
    "vol_target": ("Capped volatility target", S.vol_target, S.grid_from(target=[0.08, 0.10, 0.12, 0.15], window=[22, 44], step=[21]), 21),
    "xs_momentum": ("Cross-sectional momentum (long top third)", S.xs_momentum,
                    S.grid_from(lookback=[126, 189, 252], skip=[5, 21], top=[1 / 3], step=[21, 42], long_only=[True]), 21),
    "tsmom": ("Time-series momentum (MOP, long/short)", S.tsmom,
              S.grid_from(lookback=[63, 126, 252], vol_target_ann=[0.20, 0.40], cap=[1.0], step=[21, 42], long_only=[False]), 21),
    "crypto_trend": ("Crypto short-horizon trend (long/flat)", S.crypto_trend, S.grid_from(hysteresis=[0.05, 0.1, 0.2, 0.3, 0.4, 0.5]), 1),
    "risk_parity": ("Risk parity across sleeves", S.risk_parity, S.grid_from(window=[125, 250, 500, 750], step=[21, 63]), 63),
    "pairs": ("Pairs (Engle–Granger spread, y then x)", None,
              S.grid_from(formation=[126, 252], trading=[126], entry=[1.5, 2.0, 2.5, 3.0], exit=[0.0], long_only=[False]), 5),
}


# Card family of each Lab family (docs/asset_expansion/cards S_<family>_*), the trial ledger's family id.
FAMILY_ID = {"trend_switch": "E1", "vol_target": "E2", "risk_parity": "E3", "xs_momentum": "E5", "pairs": "E8",
             "crypto_trend": "C3", "tsmom": "B3"}
_MARKET = {"krx_etf": "KR", "krx_stock": "KR", "us": "US", "crypto": "CRYPTO", "fx": "FX", "futures": "FUTURES"}


def register_trials(family: str, symbols: list[str], grid: list[dict], cost_bps: float, dates, sources,
                    *, ledger_dir=None) -> Optional[int]:
    """Every configuration of a real-data Lab run is a trial of its card family in QUANTGEN's ledger, so a
    later card counts what was tried here. Synthetic runs are toys and register nothing. Returns the family's
    configuration count, or None."""
    if "SYNTHETIC" in sources:
        return None
    import json
    from datetime import datetime, timezone
    import config as QC
    from core.quant import gate_ledger as GL

    ledger = GL.family_ledger(FAMILY_ID[family], Path(ledger_dir) if ledger_dir else QC.macro_dir() / "ledgers")
    symbols = [s.strip().upper() for s in symbols]
    if family != "pairs":                     # pairs keep y-then-x order; elsewhere order is not a configuration
        symbols = sorted(symbols)
    markets = {_MARKET.get(V.cost_class(s) or "", "OTHER") for s in symbols}
    market = next(iter(markets)) if len(markets) == 1 else "MULTI"
    for theta in grid:
        GL.register_trial(ledger, dict(
            rule=FAMILY_ID[family], params=json.loads(json.dumps(dict(theta, symbols=list(symbols), cost_bps=cost_bps),
                                                                 default=str)),
            timing_class="COMPLIANT", span=[str(dates[0])[:10], str(dates[-1])[:10]],
            market=market,
            run_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), phase="research",
            run_kind="variant", run_utc_anchor=GL.repo_anchor(), source="Strategy Lab: " + ", ".join(sources)),
            script="ui/strategy_lab_page.py")
    return ledger.n_raw


def run_family(family: str, symbols: list[str], *, source: str = "auto", cost_bps: Optional[float] = None,
               days: int = 5000, bootstrap_B: int = 1000) -> dict:
    """`cost_bps=None` charges QUANTGEN's table rate. A typed cost below it still runs, as a cost sensitivity, but
    the PASS / REJECT verdict is withheld: the gate never lowers the cost assumption (validate.py)."""
    label, fn, grid, embargo = FAMILIES[family]
    if not symbols:
        raise ValueError("No symbols given.")
    floor, classes = V.cost_floor_bp(symbols)
    uncosted = [s for s, c in classes.items() if c is None]
    if cost_bps is None:
        if floor is None:
            raise ValueError(f"QUANTGEN has no cost row for {', '.join(uncosted)}; type a cost to run a sensitivity")
        cost_bps = floor
    withheld = ("" if floor is not None and cost_bps >= floor else
                f"No PASS / REJECT: QUANTGEN has no cost row for {', '.join(uncosted)}, so this run is a cost "
                f"sensitivity, not a gate verdict." if floor is None else
                f"No PASS / REJECT: {cost_bps:g} bp per side is below QUANTGEN's table rate for these symbols "
                f"({floor:g} bp; {', '.join(f'{s} {c}' for s, c in classes.items())}), so this run is a cost "
                f"sensitivity, not a gate verdict.")
    hists = [load_history(s, source=source, days=days) for s in symbols]
    pn = S.align_panel(hists)
    if family == "pairs":
        if pn.prices.shape[1] != 2:
            raise ValueError("pairs needs exactly two symbols: y then x")
        def fn(prices, **theta):
            W, _ = S.pairs(prices, **theta)
            return W
        fn.__name__ = "pairs"
    rf = 0.03 / 252
    M, Ms, Tv = S.pnl_matrix(pn.prices, fn, grid, cost_bps=cost_bps, cash_daily=rf)
    dates = pn.dates[1:]
    wf = V.walk_forward(M, dates, turnover=Tv, pnl_stress=Ms, embargo=embargo)
    # a run that computes is a trial; registered before it is scored, so a broken ledger blocks the verdict
    ledger_n = register_trials(family, [h.symbol for h in hists], grid, cost_bps, pn.dates, [h.source for h in hists])
    bench_all = (pn.prices[1:] / pn.prices[:-1] - 1.0).mean(axis=1) if family != "pairs" else None
    bench = None
    if bench_all is not None:
        bd = dict(zip(dates, bench_all))
        bench = np.array([bd[d] for d in wf.dates])
    saved_b = V.GATE["bootstrap_B"]
    V.GATE["bootstrap_B"] = bootstrap_B
    try:
        sc = V.score_strategy(wf, grid=grid, full_pnl=M, n_trials=len(grid), bench_daily=bench)
    finally:
        V.GATE["bootstrap_B"] = saved_b      # the gate is pre-registered: a Lab run must not leave it changed
    eq = S.equity_curve(wf.pnl)
    beq = S.equity_curve(bench) if bench is not None else None
    return {"family": family, "label": label, "symbols": [h.symbol for h in hists], "sources": [h.source for h in hists],
            "notes": [h.note for h in hists], "convention": convention_warning(hists),
            "panel": pn, "score": sc, "wf": wf, "equity": eq, "bench_equity": beq, "grid": grid,
            "chosen": grid[wf.chosen[-1]] if wf.chosen else {}, "cost_bps": cost_bps, "cost_floor": floor,
            "withheld": withheld, "ledger_n": ledger_n}


def narrative(r: dict) -> str:
    sc = r["score"]
    head = (f"{r['label']} on {', '.join(r['symbols'])} ({len(r['panel'])} shared sessions, {r['cost_bps']:.0f} bp per side, "
            f"{len(r['grid'])} configurations = {sc.n_trials} trials): "
            + (f"decision withheld — {r['withheld']} " if r.get("withheld") else f"decision {sc.decision} — {sc.reason}. ") +
            f"The last in-sample winner was {r['chosen']}.")
    return head + " " + " ".join(sc.lines)


def payload(r: dict) -> dict:
    sc = r["score"]
    hide = ("decision", "reason", "revise_target") if r.get("withheld") else ()   # no verdict leaks into analysis
    return {"family": r["family"], "symbols": r["symbols"], "sources": r["sources"], "cost_bps": r["cost_bps"], "grid_size": len(r["grid"]),
            "decision": "WITHHELD" if r.get("withheld") else sc.decision,
            "reason": r.get("withheld") or sc.reason, "revise_target": None if r.get("withheld") else sc.revise_target,
            "stats": {k: v for k, v in sc.__dict__.items() if isinstance(v, (int, float, str, bool, tuple)) and k not in hide},
            "regime": sc.regime, "lines": sc.lines, "walk_forward": r["wf"].note}


def build_strategy_lab_page(page: ft.Page, on_open_settings: Optional[Callable] = None) -> ft.Control:
    pal = active()
    cards = load_cards()
    # ---- section 1: scorecard --------------------------------------------------
    picker = ft.Dropdown(label="Card", width=360, value=cards[0]["card_id"] if cards else None,
                         options=[ft.dropdown.Option(c["card_id"], f"{c['card_id']} — {c['decision']}") for c in cards])
    detail = ft.Column(spacing=6)

    def show_card(e=None) -> None:
        c = next((x for x in cards if x["card_id"] == picker.value), None)
        detail.controls = []
        if c:
            detail.controls = [
                ft.Row([chip(c["decision"], _TOKEN.get(c["decision"], "muted")), chip(c["kind"]), chip(f"seed {c.get('seed')}"),
                        chip(f"results md5 {str(c.get('results_md5', ''))[:8]}")], spacing=6, wrap=True),
                ft.Text(c["hypothesis"], size=12, color=pal.text, italic=True, selectable=True),
                ft.Text(f"Decision: {c['decision_reason']}" + (f" → {c['revise_target']}" if c.get("revise_target") else ""),
                        size=12, color=pal.text, selectable=True),
            ] + [ft.Text("• " + ln, size=12, color=pal.text, selectable=True) for ln in c.get("lines", [])] + \
                [ft.Text("Sources: " + "; ".join(c.get("citations", [])), size=11, color=pal.muted, selectable=True)]
        page.update()

    picker.on_select = show_card
    counts = {}
    for c in cards:
        counts[c["decision"]] = counts.get(c["decision"], 0) + 1
    rows = []
    for c in cards:
        st = c.get("stats", {})
        key = (f"SR {st.get('sr_oos', float('nan')):.2f} · DSR {st.get('dsr', float('nan')):.2f} · PBO {st.get('pbo', float('nan')):.2f}"
               if isinstance(st.get("sr_oos"), (int, float)) else
               "; ".join(f"{k} {v:.3g}" for k, v in list(c.get("tests", {}).items())[:3] if isinstance(v, (int, float))))
        rows.append(ft.DataRow(cells=[
            ft.DataCell(ft.Text(c["card_id"], size=11, color=pal.text)),
            ft.DataCell(ft.Text(c["kind"], size=11, color=pal.muted)),
            ft.DataCell(chip(c["decision"], _TOKEN.get(c["decision"], "muted"))),
            ft.DataCell(ft.Text(c["decision_reason"][:70], size=11, color=pal.text)),
            ft.DataCell(ft.Text(key, size=11, color=pal.muted)),
        ]))
    table = ft.DataTable(columns=[ft.DataColumn(ft.Text(h, size=11, color=pal.muted)) for h in ("Card", "Kind", "Decision", "Reason", "Key numbers")],
                         rows=rows, column_spacing=14, heading_row_height=32, data_row_max_height=34) if rows else None
    scorecard = ft.Column([
        ft.Text("Validation scorecard", size=15, weight=ft.FontWeight.W_600, color=pal.text),
        notice("v2 macro model cards (CARD-O / CARD-P) are under Macro → Model cards; this scorecard lists the "
               "asset-expansion study cards only.", "accent"),
        ft.Row([chip(f"{k}: {v}", _TOKEN.get(k, "muted")) for k, v in sorted(counts.items())] +
               [chip(f"{len(cards)} cards from docs/asset_expansion/cards")], spacing=6, wrap=True),
        ft.Text("PASS is offered by default; REVISE is offered with its revise target shown; REJECT and INSUFFICIENT_DATA are "
                "listed so the refusal is visible. Every line states the number, the threshold and the sample behind it.",
                size=11, color=pal.muted),
        ft.Row([table], scroll=ft.ScrollMode.AUTO) if table else notice("No cards yet: run python docs/asset_expansion_study.py", "accent"),
        ft.Row([picker], spacing=10), detail,
    ], spacing=10)
    if cards:
        show_card()

    # ---- section 2: run a family ------------------------------------------------
    family = ft.Dropdown(label="Family", width=330, value="trend_switch",
                         options=[ft.dropdown.Option(k, v[0]) for k, v in FAMILIES.items()])
    symbols = ft.TextField(label="Symbols (comma)", value="SPY, QQQ, TLT, GLD", width=340, border_radius=RADII["md"],
                           hint_text="069500, 152380 · BTC-USD · KRW-BTC · 005935.KS, 005930.KS")
    source = ft.Dropdown(label="Source", width=180, value="auto",
                         options=[ft.dropdown.Option(k, k) for k in ("auto", "yfinance", "kis", "fmp", "crypto", "synthetic")])
    cost = ft.TextField(label="Cost bp/side", value="", hint_text="table", width=110, border_radius=RADII["md"],
                        tooltip="Blank charges QUANTGEN's table rate. A lower cost runs as a sensitivity with no verdict.")
    days = ft.TextField(label="Sessions", value="5000", width=100, border_radius=RADII["md"])
    busy = ft.ProgressRing(visible=False, width=20, height=20)
    host = ft.Column(spacing=14)

    def run(e=None) -> None:
        busy.visible = True; host.controls = []; page.update()

        def worker():
            try:
                syms = [s.strip() for s in (symbols.value or "").split(",") if s.strip()]
                r = run_family(family.value or "trend_switch", syms, source=source.value or "auto",
                               cost_bps=float(cost.value) if (cost.value or "").strip() else None,
                               days=int(float(days.value or "5000")))
            except (HistoryError, ValueError) as exc:
                host.controls = [notice(str(exc), "error", icon=ft.Icons.ERROR_OUTLINE)]; busy.visible = False; page.update(); return
            except Exception as exc:
                host.controls = [notice(f"{type(exc).__name__}: {exc}", "error", icon=ft.Icons.ERROR_OUTLINE)]
                busy.visible = False; page.update(); return
            sc = r["score"]
            blocks: list[ft.Control] = []
            if "SYNTHETIC" in r["sources"]:
                blocks.append(notice("Synthetic data in the panel: the verdict below is a toy.", "error", icon=ft.Icons.SCIENCE_OUTLINED))
            if r.get("convention"):
                blocks.append(notice(r["convention"], "error", icon=ft.Icons.ERROR_OUTLINE))
            if r["withheld"]:
                blocks.append(notice(r["withheld"], "error", icon=ft.Icons.ERROR_OUTLINE))
            verdict = ([chip("NO VERDICT", "muted"), chip(f"{r['cost_bps']:g} bp < table {r['cost_floor']:g} bp"
                                                          if r["cost_floor"] is not None else "no cost row")]
                       if r["withheld"] else [chip(sc.decision, _TOKEN.get(sc.decision, "muted")), chip(sc.reason[:80])])
            blocks.append(ft.Row(verdict + [
                                  chip(r["wf"].note, "muted")]
                                 + ([chip(f"{FAMILY_ID[r['family']]} ledger: {r['ledger_n']} configurations", "muted",
                                          tooltip="Every configuration ever run in this family. The deflated Sharpe "
                                                  "above counts only this run's grid.")]
                                    if r.get("ledger_n") else []) + [chip(f"{s}: {src}" + (" · cached" if "cached" in note else ""),
                                                                       "success" if src != "SYNTHETIC" else "muted", tooltip=note)
                                                                  for s, src, note in zip(r["symbols"], r["sources"], r["notes"])],
                                 spacing=6, wrap=True))
            blocks.append(ft.Row([
                stat("OOS Sharpe", f"{sc.sr_oos:.2f}", token="success" if sc.ci90[0] > 0 else "error",
                     tooltip=f"90 % block-bootstrap interval {sc.ci90[0]:.2f} to {sc.ci90[1]:.2f}"),
                stat("Deflated Sharpe", f"{sc.dsr:.2f}", token="success" if sc.dsr >= 0.95 else "error"),
                stat("PBO", f"{sc.pbo:.2f}", token="success" if sc.pbo <= 0.05 else "muted"),
                stat("OOS / IS", f"{sc.oos_is:.2f}"), stat("2× costs", f"{sc.sr_stress:.2f}", token="success" if sc.sr_stress > 0 else "error"),
                stat("Years positive", f"{sc.years_positive:.0%}"), stat("Plateau", f"{sc.plateau:.0%}{' (edge)' if sc.edge else ''}"),
                stat("Trades", f"{sc.n_trades}"), stat("Max DD", f"{sc.max_drawdown:.0%}"),
                stat("Benchmark SR", f"{sc.bench_sr:.2f}" if math.isfinite(sc.bench_sr) else "n/a",
                     tooltip=f"difference {sc.bench_diff:+.2f}, one-sided p {sc.bench_p:.2f}" if math.isfinite(sc.bench_p) else ""),
                stat("Haircut SR", f"{sc.haircut_sr:.2f}"),
            ], spacing=10, wrap=True))
            blocks.append(card(xc.equity_chart(r["wf"].dates, r["equity"], r["bench_equity"], title=f"{r['label']}: out-of-sample equity")))
            blocks.append(card(ft.Column([ft.Text("• " + ln, size=12, color=pal.text, selectable=True) for ln in sc.lines], spacing=4)))
            blocks.append(analysis_panel(page, kind="strategy_gate", narrative=narrative(r),
                                         payload_fn=lambda p=payload(r): p, deep_fn=insights.deep_analysis))
            host.controls = blocks; busy.visible = False; page.update()

        page.run_thread(worker)

    lab = ft.Column([
        ft.Text("Run a family through the gate", size=15, weight=ft.FontWeight.W_600, color=pal.text),
        ft.Row([family, symbols, source, cost, days, ft.Button("Run", icon=ft.Icons.PLAY_ARROW_ROUNDED, on_click=run), busy],
               spacing=10, wrap=True),
        host,
    ], spacing=10)
    host.controls = [empty_state("Pick a family and symbols", "Purged walk-forward (IS 756 / OOS 126), block-bootstrap Sharpe interval, "
                                 "deflated Sharpe, PBO, 2× costs, plateau, benchmark test — the same gate the study applied.",
                                 icon=ft.Icons.SCIENCE_OUTLINED)]
    return ft.Column([
        section("Strategy Lab", subtitle="What the validation study admitted, and a live run of any family through the same gate."),
        ft.Column([scorecard, ft.Divider(color=pal.border), lab], scroll=ft.ScrollMode.AUTO, expand=True, spacing=14),
    ], spacing=14, expand=True)


def _study_card(c: dict) -> dict:
    """A card with every key the page indexes, read with .get: a file of another shape (a v2 macro card, a header,
    a draft) shows as UNKNOWN instead of raising inside the page build."""
    def listed(k):
        v = c.get(k)
        return [str(x) for x in v] if isinstance(v, list) else []

    known = c.get("decision") in V.DECISIONS
    return {**c, "card_id": str(c.get("card_id") or "unnamed card"),
            "decision": c.get("decision") if known else "UNKNOWN",
            "kind": str(c.get("kind") or c.get("class") or "unknown"),
            "hypothesis": str(c.get("hypothesis") or c.get("claim") or ""),
            "decision_reason": str(c.get("decision_reason") or ("" if known else
                                   "not an asset-expansion study card (v2 macro cards: Macro → Model cards)")),
            "stats": {k: v for k, v in c["stats"].items() if isinstance(v, (int, float))} if isinstance(c.get("stats"), dict) else {},
            "tests": c.get("tests") if isinstance(c.get("tests"), dict) else {},
            "lines": listed("lines"), "citations": listed("citations")}


def load_cards() -> list[dict]:
    cards = [_study_card(c) for c in V.load_cards(CARDS_DIR) if isinstance(c, dict)]
    return sorted(cards, key=lambda c: ({"PASS": 0, "REVISE": 1, "REJECT": 2}.get(c["decision"], 3), c["card_id"]))


if __name__ == "__main__":
    r = run_family("trend_switch", ["AAA", "BBB", "CCC"], source="synthetic", cost_bps=5.0, days=1500, bootstrap_B=200)
    assert r["score"].decision in V.DECISIONS and r["equity"].size > 100 and len(r["score"].lines) >= 8
    assert "decision" in narrative(r) and payload(r)["grid_size"] == 12
    assert r["withheld"] and payload(r)["decision"] == "WITHHELD", "5 bp is below the 50 bp US row: no verdict"
    assert "decision" not in payload(r)["stats"] and payload(r)["revise_target"] is None, "no verdict in the payload"
    t = run_family("trend_switch", ["AAA", "BBB", "CCC"], source="synthetic", days=1500, bootstrap_B=200)
    assert t["cost_bps"] == 50.0 and not t["withheld"], "blank cost charges the table rate and keeps the verdict"
    p = run_family("pairs", ["AAA", "BBB"], source="synthetic", cost_bps=5.0, days=1500, bootstrap_B=200)
    assert p["bench_equity"] is None and p["score"].decision in V.DECISIONS
    print("ok", r["score"].decision, p["score"].decision)
