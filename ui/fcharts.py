"""FICC charts, rendered by matplotlib into base64 data-URI `ft.Image`s.

Same machinery as `ui/qcharts.py` — Agg backend, palette from `core.theme`,
and `_fig/_style/_to_image/_thin_dates` imported from there rather than
copied. Every function takes a `core.ficc` result object and returns one
`ft.Image`; the pages wrap it in `card()`.

This is the one place the FICC core's decimals get scaled for humans: rates
in percent, spreads in bp, P&L in currency. Tenor axes are log-scaled so
1m/3m/6m do not collapse onto the 30y end. `payoff_chart` is duck-typed on
`ProductReport.payoff_grid` so this module imports without
`core.ficc.structured`.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Sequence

import numpy as np

import flet as ft

from core.ficc.bonds import Bond, modified_duration, price_from_yield
from core.ficc.common import BP, tenor_label
from core.ficc.curves import CurveReport, PCAResult, nelson_siegel, svensson
from core.theme import active
from ui.qcharts import _fig, _style, _thin_dates, _to_image

if TYPE_CHECKING:                                    # pragma: no cover
    from core.ficc.bonds import ScenarioRow
    from core.ficc.data import CurvePanel, Series
    from core.ficc.fx import CarryBacktest, CarryRow, SmilePoint
    from core.ficc.macro import MacroSheet
    from core.ficc.ratesim import HorizonPV, RateSimResult
    from core.ficc.swaps import CapFloorReport


def _legend(ax, pal, loc: str = "upper left", *args) -> None:
    ax.legend(*args, loc=loc, fontsize=8, facecolor=pal.surface_2,
              edgecolor=pal.border, labelcolor=pal.text)


def _twin_legend(ax, ax2, pal, loc: str) -> None:
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    _legend(ax, pal, loc, h1 + h2, l1 + l2)


def _tenor_axis(ax, tenors: Sequence[float]) -> None:
    ax.set_xscale("log")
    ax.set_xticks(list(tenors))
    ax.set_xticklabels([tenor_label(t) for t in tenors])
    ax.minorticks_off()


def _date_axis(ax, dates) -> None:
    idx, labels = _thin_dates(dates)
    ax.set_xticks(idx)
    ax.set_xticklabels(labels)


# --------------------------------------------------------------------------- #
# Curves
# --------------------------------------------------------------------------- #
def curve_chart(report: CurveReport) -> ft.Image:
    """Par, zero and 1y-forward curves off the fitted `YieldCurve`, the NS/NSS
    fit dotted, and the snapshot's par yields as markers."""
    pal = active()
    snap, curve = report.snapshot, report.curve
    lo, hi = min(snap.tenors), max(snap.tenors)
    t = np.geomspace(lo, hi, 160)
    # Par only on the semi-annual coupon grid (plus the money-market tenors):
    # the stub-free schedule T - k/2 saw-tooths between those points.
    tp = np.array(sorted({x for x in snap.tenors if x < 1.0} | set(np.arange(1.0, hi + 0.5, 0.5))))
    tp = tp[tp <= hi]
    par = np.array([curve.par_rate(x, 2) if x >= 1.0 else (1.0 / curve.df(x) - 1.0) / x
                    for x in tp])
    fwd = np.array([curve.fwd(x, x + 1.0) for x in t])
    fn = svensson if report.ns.method == "svensson" else nelson_siegel
    fig, ax = _fig(7.5, 3.2, pal)
    ax.plot(tp, par * 100, color=pal.accent, linewidth=1.6, label="Par (semi-annual)")
    ax.plot(t, curve.zero(t) * 100, color=pal.text, linewidth=1.2, label="Zero (cont.)")
    ax.plot(t, fwd * 100, "--", color=pal.success, linewidth=1.1, label="1y forward")
    ax.plot(t, fn(t, *report.ns.params) * 100, ":", color=pal.muted, linewidth=1.2,
            label=f"{report.ns.method.replace('_', '-')} fit, rmse {report.ns.rmse / BP:.1f}bp")
    ax.scatter(snap.tenors, np.asarray(snap.par_yields) * 100, color=pal.accent, s=18,
               zorder=5)
    _tenor_axis(ax, snap.tenors)
    ax.set_ylabel("%")
    _legend(ax, pal)
    ax.set_title(f"{snap.date} {snap.source} — {report.shape}, {report.regime} over "
                 f"{report.lookback} sessions", fontsize=10, loc="left")
    return _to_image(fig)


def curve_history_chart(panel: CurvePanel,
                        tenors: Sequence[float] = (2.0, 10.0, 30.0)) -> ft.Image:
    pal = active()
    grid = np.asarray(panel.tenors, dtype=float)
    fig, ax = _fig(7.5, 2.9, pal)
    x = np.arange(len(panel))
    for tenor, colour in zip(tenors, (pal.accent, pal.text, pal.success, pal.error, pal.muted)):
        k = int(np.argmin(np.abs(grid - tenor)))
        ax.plot(x, panel.yields[:, k] * 100, color=colour, linewidth=1.3,
                label=tenor_label(grid[k]))
    _date_axis(ax, panel.dates)
    ax.set_ylabel("%")
    _legend(ax, pal)
    ax.set_title(f"Par yields — {len(panel)} sessions ({panel.source})",
                 fontsize=10, loc="left")
    return _to_image(fig)


def pca_chart(pca: PCAResult) -> ft.Image:
    pal = active()
    fig, ax = _fig(7.5, 2.9, pal)
    colours = (pal.accent, pal.success, pal.error, pal.muted)
    for j, label in enumerate(pca.labels):
        ax.plot(pca.tenors, pca.loadings[:, j], marker="o", markersize=3, linewidth=1.3,
                color=colours[j % len(colours)],
                label=f"{label} ({pca.explained[j] * 100:.0f}%)")
    ax.axhline(0, color=pal.border, linewidth=0.8)
    _tenor_axis(ax, pca.tenors)
    ax.set_ylabel("Loading")
    _legend(ax, pal, "upper right")
    ax.set_title(f"PCA of daily curve changes — {pca.explained.sum() * 100:.0f}% explained by "
                 f"{len(pca.labels)} factors", fontsize=10, loc="left")
    return _to_image(fig)


# --------------------------------------------------------------------------- #
# Bonds & swaps
# --------------------------------------------------------------------------- #
def krd_chart(krd: dict[float, float], title: str = "Key-rate DV01") -> ft.Image:
    pal = active()
    tenors = sorted(krd)
    vals = np.array([krd[t] for t in tenors], dtype=float)
    fig, ax = _fig(7.5, 2.7, pal)
    ax.bar(range(len(tenors)), vals, color=[pal.accent if v >= 0 else pal.error for v in vals],
           edgecolor=pal.surface)
    ax.set_xticks(range(len(tenors)))
    ax.set_xticklabels([tenor_label(t) for t in tenors])
    ax.axhline(0, color=pal.border, linewidth=0.8)
    ax.set_ylabel("per bp")
    ax.set_title(f"{title} — total {vals.sum():,.0f} per bp", fontsize=10, loc="left")
    return _to_image(fig)


def scenario_chart(rows: Sequence[ScenarioRow]) -> ft.Image:
    pal = active()
    pnl = np.array([r.pnl for r in rows], dtype=float)
    fig, ax = _fig(7.5, max(2.4, 0.32 * len(rows) + 1.0), pal)
    y = np.arange(len(rows))
    ax.barh(y, pnl, color=[pal.success if v >= 0 else pal.error for v in pnl],
            edgecolor=pal.surface)
    ax.set_yticks(y)
    ax.set_yticklabels([r.name for r in rows], fontsize=8)
    ax.invert_yaxis()
    ax.axvline(0, color=pal.border, linewidth=0.8)
    for yi, r in zip(y, rows):
        ax.text(r.pnl, yi, f" {r.pnl:,.0f} ({r.pnl_pct * 100:+.2f}%) ", va="center",
                ha="left" if r.pnl >= 0 else "right", fontsize=7, color=pal.text)
    ax.margins(x=0.3)
    ax.set_xlabel("P&L on notional")
    ax.set_title("Scenario P&L — full revaluation, z-spread held", fontsize=10, loc="left")
    return _to_image(fig)


def price_yield_chart(bond: Bond, ytm: float) -> ft.Image:
    """Price against yield ±300bp with the duration tangent at `ytm`; the gap
    between curve and tangent is the convexity."""
    pal = active()
    ys = np.linspace(ytm - 0.03, ytm + 0.03, 121)
    ys = ys[1.0 + ys / bond.freq > 0]
    p0, mdur = price_from_yield(bond, ytm), modified_duration(bond, ytm)
    prices = np.array([price_from_yield(bond, y) for y in ys])
    fig, ax = _fig(7.5, 2.9, pal)
    ax.plot(ys * 100, prices, color=pal.accent, linewidth=1.6, label="Price")
    ax.plot(ys * 100, p0 * (1.0 - mdur * (ys - ytm)), "--", color=pal.muted, linewidth=1.0,
            label=f"Duration tangent (mod. dur. {mdur:.2f})")
    ax.scatter([ytm * 100], [p0], color=pal.text, s=30, zorder=5,
               label=f"{ytm * 100:.2f}% -> {p0:.3f}")
    ax.set_xlabel("Yield (%)")
    ax.set_ylabel(f"Price per {bond.face:g}")
    _legend(ax, pal, "upper right")
    name = bond.name or f"{bond.coupon * 100:.2f}% {bond.maturity:g}y"
    ax.set_title(f"{name} — price / yield", fontsize=10, loc="left")
    return _to_image(fig)


def caplet_chart(report: CapFloorReport) -> ft.Image:
    pal = active()
    c = np.asarray(report.caplets, dtype=float).reshape(-1, 4)
    starts, ends, fwds, prem = c.T
    kind = "Caplet" if report.cap else "Floorlet"
    fig, ax = _fig(7.5, 2.9, pal)
    ax.bar(starts, prem, width=(ends - starts) * 0.8, align="edge", color=pal.accent,
           alpha=0.85, edgecolor=pal.surface, label=f"{kind} premium")
    ax.set_xlabel("Period start (years)")
    ax.set_ylabel("Premium")
    ax2 = ax.twinx()
    _style(ax2, pal, grid=False)
    ax2.plot((starts + ends) / 2, fwds * 100, color=pal.text, marker="o", markersize=3,
             linewidth=1.1, label="Forward (%)")
    ax2.axhline(report.strike * 100, color=pal.error, linestyle="--", linewidth=1.0,
                label=f"Strike {report.strike * 100:.2f}%")
    ax2.axhline(report.atm_strike * 100, color=pal.muted, linestyle=":", linewidth=1.0,
                label=f"ATM {report.atm_strike * 100:.2f}%")
    ax2.set_ylabel("%")
    _twin_legend(ax, ax2, pal, "upper left")
    ax.set_title(f"{'Cap' if report.cap else 'Floor'} — {len(c)} periods, {report.model}, "
                 f"premium {report.premium:,.0f} ({report.premium_bp:.1f}bp)",
                 fontsize=10, loc="left")
    return _to_image(fig)


# --------------------------------------------------------------------------- #
# FX
# --------------------------------------------------------------------------- #
def smile_chart(strikes, vols, points: Sequence[SmilePoint], forward: float) -> ft.Image:
    pal = active()
    fig, ax = _fig(7.5, 2.9, pal)
    ax.plot(np.asarray(strikes, dtype=float), np.asarray(vols, dtype=float) * 100,
            color=pal.accent, linewidth=1.5, label="SABR")
    for p in points:
        ax.scatter([p.strike], [p.vol * 100], color=pal.text, s=28, zorder=5)
        ax.annotate(f"{p.label} {p.vol * 100:.2f}%", (p.strike, p.vol * 100),
                    textcoords="offset points", xytext=(0, 7), ha="center", fontsize=7,
                    color=pal.text)
    ax.axvline(forward, color=pal.muted, linestyle="--", linewidth=1.0,
               label=f"Forward {forward:.4f}")
    ax.set_xlabel("Strike")
    ax.set_ylabel("Vol (%)")
    _legend(ax, pal, "upper center")
    ax.set_title("Volatility smile — market points and SABR fit", fontsize=10, loc="left")
    return _to_image(fig)


def fx_spot_chart(series: Series, forward_points_line=None) -> ft.Image:
    """`forward_points_line`: a forward outright (float) drawn as a dashed level,
    or (tenor_years, forward) pairs drawn as the forward curve extending past
    the last spot at 252 sessions per year."""
    pal = active()
    px = series.array()
    fig, ax = _fig(7.5, 2.9, pal)
    ax.plot(np.arange(px.size), px, color=pal.accent, linewidth=1.4, label="Spot")
    if forward_points_line is not None:
        if np.isscalar(forward_points_line):
            f = float(forward_points_line)
            ax.axhline(f, color=pal.success, linestyle="--", linewidth=1.0,
                       label=f"Forward {f:.4f}")
        else:
            pts = sorted((float(t), float(f)) for t, f in forward_points_line)
            ax.plot([px.size - 1] + [px.size - 1 + t * 252 for t, _ in pts],
                    [px[-1]] + [f for _, f in pts], "--o", color=pal.success,
                    linewidth=1.2, markersize=3, label="Forward curve")
    _date_axis(ax, series.dates)
    _legend(ax, pal)
    ax.set_title(f"{series.label} — {len(series)} sessions ({series.source}), "
                 f"last {series.last:.4f}", fontsize=10, loc="left")
    return _to_image(fig)


def carry_equity_chart(bt: CarryBacktest) -> ft.Image:
    pal = active()
    fig, ax = _fig(7.5, 3.0, pal)
    x = np.arange(bt.equity.size)
    ax.plot(x, bt.bench_equity, color=pal.muted, linewidth=1.1, label="Equal-weight long all")
    ax.plot(x, bt.equity, color=pal.accent, linewidth=1.5,
            label=f"Carry top {bt.top_n} / bottom {bt.top_n}")
    pos = {d: i for i, d in enumerate(bt.dates)}
    for d, _, _ in bt.positions:
        if d in pos:
            ax.axvline(pos[d], color=pal.border, linewidth=0.5, alpha=0.7)
    _date_axis(ax, bt.dates)
    _legend(ax, pal)
    ax.set_title(f"Carry basket — {bt.ann_return * 100:+.1f}% p.a., vol {bt.ann_vol * 100:.1f}%, "
                 f"Sharpe {bt.sharpe:.2f}, max DD {bt.max_drawdown * 100:.1f}%, "
                 f"{bt.cost_bps:g}bp cost (lines: rebalances)", fontsize=10, loc="left")
    return _to_image(fig)


def carry_bar_chart(rows: Sequence[CarryRow]) -> ft.Image:
    pal = active()
    x = np.arange(len(rows))
    carry = np.array([r.carry for r in rows], dtype=float) * 100
    fig, ax = _fig(7.5, 2.8, pal)
    ax.bar(x, carry, color=[pal.success if v >= 0 else pal.error for v in carry],
           edgecolor=pal.surface, label="Carry vs USD (% p.a.)")
    ax.set_xticks(x)
    ax.set_xticklabels([r.ccy for r in rows])
    ax.axhline(0, color=pal.border, linewidth=0.8)
    ax.set_ylabel("Carry (% p.a.)")
    ax2 = ax.twinx()
    _style(ax2, pal, grid=False)
    ax2.plot(x, [r.score for r in rows], color=pal.text, marker="D", markersize=4,
             linewidth=0, label="Score (carry/vol + mom/vol)")
    ax2.set_ylabel("Score")
    _twin_legend(ax, ax2, pal, "upper right")
    ax.set_title("Carry ranking — long the currency against USD", fontsize=10, loc="left")
    return _to_image(fig)


# --------------------------------------------------------------------------- #
# Structured, simulation, macro
# --------------------------------------------------------------------------- #
def payoff_chart(product) -> ft.Image:
    """Duck-typed on ProductReport: `payoff_grid` of (underlying level, payoff
    per 100), plus `product`, `issue_price` and `fair_value` when present."""
    pal = active()
    grid = np.asarray(product.payoff_grid, dtype=float).reshape(-1, 2)
    if grid.size == 0:
        raise ValueError("payoff_grid is empty.")
    x, y = grid[:, 0], grid[:, 1]
    issue = float(getattr(product, "issue_price", 100.0))
    fig, ax = _fig(7.5, 2.9, pal)
    ax.plot(x, y, color=pal.accent, linewidth=1.7, label="Payoff at maturity (per 100)")
    ax.axhline(issue, color=pal.muted, linestyle="--", linewidth=1.0,
               label=f"Issue price {issue:g}")
    ax.fill_between(x, issue, y, where=y >= issue, color=pal.success, alpha=0.15,
                    interpolate=True)
    ax.fill_between(x, issue, y, where=y < issue, color=pal.error, alpha=0.15,
                    interpolate=True)
    ax.set_xlabel("Underlying at maturity")
    ax.set_ylabel("per 100")
    _legend(ax, pal)
    title = str(getattr(product, "product", "Structured note"))
    fair = getattr(product, "fair_value", None)
    if fair is not None:
        title += f" — fair {fair:.2f} vs issue {issue:g}"
    ax.set_title(title, fontsize=10, loc="left")
    return _to_image(fig)


def rate_fan_chart(sim: RateSimResult) -> ft.Image:
    pal = active()
    fig, ax = _fig(7.5, 3.0, pal)
    t = sim.times
    ax.fill_between(t, sim.fan[5] * 100, sim.fan[95] * 100, color=pal.accent, alpha=0.16,
                    label="5–95%")
    ax.fill_between(t, sim.fan[25] * 100, sim.fan[75] * 100, color=pal.accent, alpha=0.30,
                    label="25–75%")
    ax.plot(t, sim.fan[50] * 100, color=pal.accent, linewidth=1.6, label="Median")
    if sim.model != "hull_white":          # HW's theta is a regression mean, not a level
        ax.axhline(sim.params.theta * 100, color=pal.muted, linestyle=":", linewidth=1.0,
                   label=f"Long-run mean {sim.params.theta * 100:.2f}%")
    if sim.threshold is not None:
        ax.axhline(sim.threshold * 100, color=pal.error, linestyle="--", linewidth=1.0,
                   label=f"Threshold {sim.threshold * 100:.2f}% "
                         f"(P above {sim.prob_above * 100:.0f}%)")
    ax.set_xlabel("Years")
    ax.set_ylabel("%")
    _legend(ax, pal)
    ax.set_title(f"{sim.model} — {sim.n_paths:,} paths, {sim.horizon:g}y; terminal mean "
                 f"{sim.mean_terminal * 100:.2f}% [{sim.p05 * 100:.2f}%, {sim.p95 * 100:.2f}%]",
                 fontsize=10, loc="left")
    return _to_image(fig)


def horizon_pv_hist(hpv: HorizonPV) -> ft.Image:
    pal = active()
    fig, ax = _fig(7.5, 2.6, pal)
    ax.hist(hpv.pvs, bins=40, color=pal.accent, alpha=0.85, edgecolor=pal.surface)
    ax.axvline(hpv.mean, color=pal.text, linewidth=1.2, label=f"Mean {hpv.mean:,.0f}")
    ax.axvline(hpv.p05, color=pal.error, linewidth=1.2, linestyle="--",
               label=f"p05 {hpv.p05:,.0f}")
    ax.axvline(hpv.p95, color=pal.success, linewidth=1.2, linestyle="--",
               label=f"p95 {hpv.p95:,.0f}")
    _legend(ax, pal, "upper right")
    ax.set_title(f"Horizon PV over {hpv.pvs.size} paths — VaR95 {hpv.var95:,.0f}, "
                 f"CVaR95 {hpv.cvar95:,.0f}", fontsize=10, loc="left")
    return _to_image(fig)


def macro_z_chart(sheet: MacroSheet) -> ft.Image:
    """Horizontal bars of 1y z-scores, coloured by group; synthetic rows hatched."""
    pal = active()
    colours = {"rates": pal.accent, "credit": pal.error, "fx": pal.success, "risk": pal.muted}
    rows = list(sheet.rows)
    fig, ax = _fig(7.5, max(2.6, 0.28 * len(rows) + 1.0), pal)
    y = np.arange(len(rows))
    seen: set[str] = set()
    for yi, r in zip(y, rows):
        ax.barh(yi, r.z_1y, color=colours.get(r.group, pal.text), edgecolor=pal.surface,
                hatch="//" if r.id in sheet.synthetic_ids else None,
                label=None if r.group in seen else r.group)
        seen.add(r.group)
    ax.set_yticks(y)
    ax.set_yticklabels([r.label for r in rows], fontsize=8)
    ax.invert_yaxis()
    ax.axvline(0, color=pal.border, linewidth=0.8)
    for v in (-2, 2):
        ax.axvline(v, color=pal.muted, linewidth=0.8, linestyle="--")
    ax.set_xlabel("1y z-score (hatched = synthetic)")
    _legend(ax, pal, "lower right")
    rg = sheet.regime
    ax.set_title(f"Macro sheet {sheet.as_of} — descriptive read, not a regime model (P19)\ncurve {rg.curve}, risk {rg.risk}, USD "
                 f"{rg.dollar}, inflation {rg.inflation}", fontsize=10, loc="left")
    return _to_image(fig)


# --------------------------------------------------------------------------- #
# Self-check
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    from types import SimpleNamespace

    from core.ficc import data, fx, ratesim, swaps
    from core.ficc.bonds import analyze_bond, scenario_pnl
    from core.ficc.curves import analyze_curve, curve_pca
    from core.ficc.macro import macro_sheet

    panel = data.synthetic_curve_panel(days=120)
    report = analyze_curve(panel, method="nelson_siegel")
    curve = report.curve
    bond = Bond(coupon=0.04, maturity=10.0, name="4% 10y")
    ba = analyze_bond(bond, ytm=0.045, curve=curve)
    pts = fx.smile_from_quotes(fx.SmileQuote(0.5, 0.10, 0.01, 0.003), 1.10, 0.045, 0.03)
    F = fx.forward(1.10, 0.045, 0.03, 0.5)
    fit = fx.calibrate_sabr(F, 0.5, [p.strike for p in pts], [p.vol for p in pts])
    ks = np.linspace(pts[0].strike * 0.97, pts[-1].strike * 1.03, 60)
    params = ratesim.calibrate(data.load_short_rate("USD", source="synthetic", days=300))
    sim = ratesim.simulate(params, horizon=1.0, n_paths=300, threshold=0.05)
    hpv = ratesim.horizon_pv_distribution(params, sim, kind="bond", bond=bond, curve=curve)
    pairs = ("EURUSD", "USDJPY", "GBPUSD", "AUDUSD", "USDCAD", "USDCHF", "USDKRW")
    spots = {p: data.synthetic_fx(p, days=300) for p in pairs}
    rates = {c: data.synthetic_series(f"RATE_{c}", days=300, kind="rate") for c in data.G10_KRW}
    product = SimpleNamespace(
        product="Test PPN", issue_price=100.0, fair_value=98.5,
        payoff_grid=tuple((s, 100.0 + max(s - 100.0, 0.0) * 0.8) for s in range(60, 141, 5)))
    images = [
        curve_chart(report), curve_history_chart(panel), pca_chart(curve_pca(panel)),
        krd_chart(ba.krd, "Bond KRD"), scenario_chart(scenario_pnl(bond, curve, ba.price)),
        price_yield_chart(bond, ba.ytm),
        smile_chart(ks, fx.smile_curve(fit, F, 0.5, ks), pts, F),
        payoff_chart(product), rate_fan_chart(sim), horizon_pv_hist(hpv),
        fx_spot_chart(spots["EURUSD"], ((0.25, 1.105), (1.0, 1.12))),
        fx_spot_chart(spots["USDJPY"], 148.0),
        carry_equity_chart(fx.carry_backtest(spots, rates)),
        carry_bar_chart(fx.carry_table(spots, rates)),
        macro_z_chart(macro_sheet(source="synthetic", days=300)),
        caplet_chart(swaps.price_cap_floor(curve, 5.0, None, vol=0.008)),
    ]
    assert len(images) == 16
    for img in images:
        assert img.src.startswith("data:image/png;base64,"), "chart must inline its PNG"
        assert len(img.src) > 1000, "suspiciously empty chart"
    print("ok")
