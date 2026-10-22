"""Narratives for the FICC screens, and the bridge to Claude deep analysis.

Same two-layer rule as `core.quant.insights`: a deterministic local paragraph
that states only numbers computed upstream (so every screen reads without a
key and the tests can assert on the text), and `deep_analysis`, a thin wrapper
around the equity module's Claude call — the HTTP code lives there, once.

Every `narrate_*` takes the result dataclass its page already has and returns
one paragraph. Rates are printed in percent, changes and spreads in basis
points, money with thousands separators and no decimals. Nothing here fetches
data; `narrate_weekly_strategy` is a strategist's read of the numbers it is
handed, not a forecast. `report_prompt(kind)` is the format instruction the
Daily/Weekly report buttons append to the operator's question.

Result types are duck-typed at runtime (TYPE_CHECKING imports only) so this
module imports even when a sibling pricer is missing.
"""
from __future__ import annotations

import math
from typing import TYPE_CHECKING

from core.ficc.common import BP, bp_text, pct_text, tenor_label
from core.quant.insights import Analysis, ai_ready  # noqa: F401  (re-exported for the UI)
from core.quant.insights import deep_analysis as _deep

if TYPE_CHECKING:                                    # pragma: no cover
    from core.ficc.bonds import BondAnalytics, ScenarioRow
    from core.ficc.curves import CurveReport, PCAResult
    from core.ficc.fx import CarryBacktest, CarryRow, GKReport, SABRFit, SmilePoint
    from core.ficc.macro import MacroSheet
    from core.ficc.ratesim import HorizonPV, RateSimResult
    from core.ficc.swaps import CapFloorReport, SwapReport, SwaptionReport

# --------------------------------------------------------------------------- #
# Formatting
# --------------------------------------------------------------------------- #
_NA = "n/a"


def _pct(x, decimals: int = 2) -> str:
    return _NA if x is None or not math.isfinite(x) else pct_text(x, decimals=decimals)


def _bp(x, signed: bool = True) -> str:
    return _NA if x is None or not math.isfinite(x) else bp_text(x, signed=signed)


def _money(x, signed: bool = False) -> str:
    if x is None or not math.isfinite(x):
        return _NA
    return f"{x:+,.0f}" if signed else f"{x:,.0f}"


def _px(x: float) -> str:
    """FX level: 2 decimals for JPY/KRW-style quotes, 4 otherwise."""
    return f"{x:,.2f}" if x > 20 else f"{x:.4f}"


def _pair(text: str) -> str:
    p = "".join(ch for ch in str(text).upper() if ch.isalpha())
    return f"{p[:3]}/{p[3:6]}" if len(p) >= 6 else str(text)


def _synthetic(source: str, what: str = "data") -> str:
    return (f" The {what} is SYNTHETIC (simulated), so these numbers describe the "
            "generator, not the market." if "SYNTHETIC" in str(source).upper() else "")


def _top(d: dict, key=abs):
    """(k, v) of the entry with the largest key(v)."""
    return max(d.items(), key=lambda kv: key(kv[1]))


# --------------------------------------------------------------------------- #
# Rates
# --------------------------------------------------------------------------- #
def narrate_curve(report: CurveReport, pca: PCAResult | None = None) -> str:
    d, c = report.descriptors, report.changes
    snap = report.snapshot
    lines = [
        f"The {snap.source} par curve of {snap.date} is {report.shape}: 2s10s "
        f"{_bp(d['2s10s'])}, 5s30s {_bp(d['5s30s'])}, 3m10y {_bp(d['3m10y'])}, with the "
        f"2s5s10s fly at {_bp(d['2s5s10s_fly'])} and the 2y/5y/10y level averaging "
        f"{_pct(d['level'])}.",
        f"Over the last {report.lookback} sessions the move reads as a {report.regime}: "
        f"2y {_bp(c.get('2y'))}, 10y {_bp(c.get('10y'))}, 2s10s {_bp(c.get('2s10s'))}.",
        f"Forwards price 1y1y at {_pct(d['1y1y'])}, 2y1y at {_pct(d['2y1y'])} and 5y5y at "
        f"{_pct(d['5y5y'])}; the 1y rate is priced to move {_bp(d['1y_fwd_1y_ahead'])} over "
        f"the next year.",
        f"The {report.ns.method.replace('_', '-')} fit misses the par points by "
        f"{report.ns.rmse / BP:.1f}bp rms ({report.curve.method} zeros used for pricing).",
    ]
    if pca is not None:
        ex = [float(e) for e in pca.explained]
        parts = ", ".join(f"{lbl} {e * 100:.0f}%" for lbl, e in zip(pca.labels, ex))
        lines.append(f"PCA on daily changes: {parts} of variance"
                     + (f"; the latest day scores {float(pca.latest_scores[0]):+.1f}bp on "
                        f"level and {float(pca.latest_scores[1]):+.1f}bp on slope."
                        if len(pca.latest_scores) >= 2 else "."))
    return " ".join(lines) + _synthetic(snap.source, "curve")


def narrate_bond(a: BondAnalytics, scenarios: list[ScenarioRow] | None = None) -> str:
    b, cr = a.bond, a.carry_roll
    name = b.name or f"{_pct(b.coupon)} {tenor_label(b.maturity)} bond"
    lines = [
        f"The {name} (coupon paid {b.freq}x a year) prices at {a.price:.3f} per {b.face:g} for "
        f"a yield of {_pct(a.ytm, 3)}: Macaulay duration {a.macaulay:.2f}y, modified "
        f"{a.modified:.2f}, convexity {a.convexity:.1f}.",
        f"On {_money(b.notional)} notional the DV01 is {_money(a.dv01)} per bp; a +100bp "
        f"parallel move costs roughly {_money(a.dv01 * 100)} before convexity.",
    ]
    if a.krd:
        t, v = _top(a.krd)
        share = v / sum(a.krd.values()) if sum(a.krd.values()) else 0.0
        lines.append(f"Key-rate risk is concentrated at {tenor_label(t)} ({_money(v)} per bp, "
                     f"{share * 100:.0f}% of the total).")
    lines.append(f"Against the curve the bond trades at a z-spread of {_bp(a.z_spread)} "
                 f"(curve price {a.curve_price:.3f}).")
    # breakeven_bp has the sign of total: negative carry+roll needs a rally to break even.
    be = (f"yields can rise {cr.breakeven_bp:.1f}bp before the position loses money"
          if cr.total >= 0 else
          f"carry and roll are negative and yields must fall {abs(cr.breakeven_bp):.1f}bp "
          f"over the horizon just to break even")
    lines.append(f"Over a {tenor_label(cr.horizon)} horizon carry is {cr.carry:+.3f} and "
                 f"roll-down {cr.rolldown:+.3f} per {b.face:g}, {cr.total:+.3f} in total, so "
                 f"{be}.")
    if scenarios:
        worst = min(scenarios, key=lambda r: r.pnl)
        best = max(scenarios, key=lambda r: r.pnl)
        lines.append(f"Of {len(scenarios)} scenarios the worst is '{worst.name}' at "
                     f"{_money(worst.pnl, signed=True)} ({worst.pnl_pct * 100:+.2f}%) and the "
                     f"best '{best.name}' at {_money(best.pnl, signed=True)} "
                     f"({best.pnl_pct * 100:+.2f}%).")
    if a.note:
        lines.append(a.note)
    return " ".join(lines)


def narrate_swap(r: SwapReport) -> str:
    s = r.swap
    k = r.par_rate if s.fixed_rate is None else s.fixed_rate
    side = "pays" if s.pay_fixed else "receives"
    lines = [
        f"The {s.label} {side} {_pct(k, 3)} fixed on {_money(s.notional)} against a par rate of "
        f"{_pct(r.par_rate, 3)}, so it is worth {_money(r.pv, signed=True)} today "
        f"(annuity {r.annuity:.3f}).",
        f"DV01 is {_money(r.dv01, signed=True)} per bp for a +1bp parallel move"
        + (f", concentrated at {tenor_label(_top(r.krd)[0])} "
           f"({_money(_top(r.krd)[1], signed=True)} per bp)." if r.krd else "."),
        f"If the curve is realised the position accrues {_money(r.carry_1y, signed=True)} of "
        f"carry over its first period and {_money(r.rolldown_1y, signed=True)} of roll-down "
        f"over one year.",
        "Forward swap rates: " + ", ".join(f"{n} {_pct(v, 3)}" for n, v in r.fwd_rates.items())
        + ".",
    ]
    return " ".join(lines)


def narrate_swaption(r: SwaptionReport) -> str:
    s = r.swaption
    kind = "payer" if s.payer else "receiver"
    model = "Bachelier" if r.model == "bachelier" else "Black-76"
    vol = (f"{r.vol / BP:.0f}bp normal vol" if r.model == "bachelier"
           else f"{r.vol * 100:.1f}% Black vol")
    moneyness = (r.strike - r.forward) / BP
    lines = [
        f"A {tenor_label(s.expiry)}x{tenor_label(s.tenor)} {kind} swaption struck at "
        f"{_pct(r.strike, 3)} against a forward of {_pct(r.forward, 3)} "
        f"({moneyness:+.0f}bp from ATM) costs {_money(r.premium)} on {_money(s.notional)} "
        f"({r.premium_bp:.1f}bp of notional) under {model} at {vol}.",
        f"Delta is {_money(r.delta, signed=True)} per bp of forward, gamma "
        f"{_money(r.gamma, signed=True)} per bp squared, vega {_money(r.vega)} {r.vega_unit}, "
        f"and it bleeds {_money(-r.theta_1d)} a day.",
    ]
    if math.isfinite(r.other_model_vol):
        other = (f"{r.other_model_vol * 100:.1f}% Black" if r.model == "bachelier"
                 else f"{r.other_model_vol / BP:.0f}bp normal")
        lines.append(f"The same premium is {other} vol in the other model.")
    if r.note:
        lines.append(r.note)
    return " ".join(lines)


def narrate_cap_floor(r: CapFloorReport) -> str:
    what = "cap" if r.cap else "floor"
    model = "Bachelier" if r.model == "bachelier" else "Black-76"
    vol = f"{r.vol / BP:.0f}bp normal" if r.model == "bachelier" else f"{r.vol * 100:.1f}% Black"
    lines = [f"The {what} struck at {_pct(r.strike, 3)} (ATM {_pct(r.atm_strike, 3)}, "
             f"{(r.strike - r.atm_strike) / BP:+.0f}bp) costs {_money(r.premium)} on "
             f"{_money(r.notional)}, {r.premium_bp:.1f}bp of notional, under {model} at "
             f"{vol} vol across {len(r.caplets)} {what}lets."]
    if r.caplets:
        t0, t1, fwd, prem = max(r.caplets, key=lambda c: c[3])
        lines.append(f"The dearest {what}let covers {tenor_label(t0)}-{tenor_label(t1)} on a "
                     f"forward of {_pct(fwd, 3)} at {_money(prem)}; forwards run from "
                     f"{_pct(r.caplets[0][2], 3)} to {_pct(r.caplets[-1][2], 3)}.")
    if r.note:
        lines.append(r.note)
    return " ".join(lines)


# --------------------------------------------------------------------------- #
# FX
# --------------------------------------------------------------------------- #
def narrate_fx_forward(pair: str, spot: float, fwd: float, points: float, carry: float,
                       basis: float | None = None) -> str:
    p = _pair(pair)
    base = p[:3]
    lines = [
        f"{p} spot {_px(spot)} against a CIP forward of {_px(fwd)}, {points:+.1f} points "
        f"({(fwd / spot - 1) * 100:+.2f}%).",
        f"Being long {base} {'earns' if carry >= 0 else 'pays'} {_pct(abs(carry))} a year of "
        f"carry (the {base} rate minus the {p[4:]} rate), which the forward hands back "
        f"one-for-one: the forward is a rate differential, not a forecast.",
    ]
    if basis is not None:
        lines.append(f"The market forward implies a cross-currency basis of {_bp(basis)} p.a. "
                     f"versus covered interest parity"
                     + (", within noise." if abs(basis) < 5 * BP else
                        f", a real funding premium on {base if basis < 0 else p[4:]}."))
    return " ".join(lines)


def narrate_fx_option(gk: GKReport, smile_points: tuple[SmilePoint, ...] | None = None,
                      sabr: SABRFit | None = None) -> str:
    kind = "call" if gk.call else "put"
    lines = [
        f"A {tenor_label(gk.expiry)} {kind} struck at {_px(gk.strike)} on spot {_px(gk.spot)} "
        f"(forward {_px(gk.forward)}) at {gk.vol * 100:.1f}% vol is worth {gk.price:.5f} per "
        f"unit of base, {gk.price_pct_spot * 100:.2f}% of spot.",
        f"Spot delta {gk.delta_spot:+.3f} (forward delta {gk.delta_fwd:+.3f}), gamma "
        f"{gk.gamma_1pct:+.4f} per 1% spot move, vega {gk.vega:.5f} per vol point, theta "
        f"{gk.theta_1d:+.6f} per day; rho {gk.rho_dom * BP:+.6f} / {gk.rho_for * BP:+.6f} "
        f"per bp of the quote / base rate.",
    ]
    if smile_points:
        pts = {p.label: p for p in smile_points}
        put, call = pts.get("25d put"), pts.get("25d call")
        if put and call:
            skew = (call.vol - put.vol) * 100
            lean = "calls" if skew > 0 else "puts"
            lines.append("Smile: " + ", ".join(f"{p.label} {p.vol * 100:.2f}% at {_px(p.strike)}"
                                               for p in smile_points)
                         + f"; the 25d risk reversal is {skew:+.2f} vol points, so the market "
                           f"pays up for {lean}.")
    if sabr is not None:
        lines.append(f"SABR (beta {sabr.beta:g}) fits with alpha {sabr.alpha:.4f}, rho "
                     f"{sabr.rho:+.2f}, nu {sabr.nu:.2f}, rmse {sabr.rmse * 100:.3f} vol points"
                     + ("." if sabr.converged else "; the solver did not converge."))
    return " ".join(lines)


def narrate_carry(rows: list[CarryRow], backtest: CarryBacktest | None = None) -> str:
    if not rows:
        return "No carry rows to read."
    ranked = sorted(rows, key=lambda r: r.score, reverse=True)
    top, bottom = ranked[0], ranked[-1]
    hi = max(rows, key=lambda r: r.carry)
    lines = [
        f"Across {len(rows)} currencies versus USD the best carry-plus-momentum score is "
        f"{top.ccy} ({top.score:+.2f}: carry {_pct(top.carry)} p.a. on {top.vol_3m * 100:.1f}% "
        f"3m vol, momentum {top.mom_3m * 100:+.1f}%) and the worst is {bottom.ccy} "
        f"({bottom.score:+.2f}: carry {_pct(bottom.carry)}, momentum "
        f"{bottom.mom_3m * 100:+.1f}%).",
        f"The highest raw carry is {hi.ccy} at {_pct(hi.carry)} ({hi.pair} spot "
        f"{_px(hi.spot)}), a carry-to-vol of {hi.carry_to_vol:+.2f}; carry and momentum are "
        f"quoted for a long position in the currency, so inverted USD-first quotes are "
        f"already flipped.",
    ]
    if backtest is not None:
        b = backtest
        bench = float(b.bench_equity[-1]) - 1 if len(b.bench_equity) else float("nan")
        lines.append(
            f"A top-{b.top_n} long/short carry basket rebalanced {b.n_rebalances} times at "
            f"{b.cost_bps:.0f}bp per turnover made {float(b.equity[-1]) - 1:+.1%} over "
            f"{len(b.dates)} sessions ({_pct(b.ann_return, 1)} annualised, "
            f"{b.ann_vol * 100:.1f}% vol, Sharpe {b.sharpe:.2f}, max drawdown "
            f"{b.max_drawdown * 100:.1f}%) against {bench:+.1%} for an equal-weight long of "
            f"every currency.")
        if b.positions:
            _, longs, shorts = b.positions[-1]
            lines.append(f"Latest basket: long {', '.join(longs)}; short {', '.join(shorts)}.")
        if b.note:
            lines.append(b.note)
    # OECD monthly policy rates lag: name the rows whose carry rests on a stale observation.
    stale = [r for r in rows if getattr(r, "rate_stale", False) and getattr(r, "rate_date", "")]
    if stale:
        lines.append("Carry for " + ", ".join(f"{r.ccy} ({r.rate_date})" for r in stale)
                     + " is computed from a rate observed on that date (the OECD monthly "
                       "series lags), not today's.")
    return " ".join(lines)


# --------------------------------------------------------------------------- #
# Short-rate simulation
# --------------------------------------------------------------------------- #
def narrate_ratesim(sim: RateSimResult, horizon_pv: HorizonPV | None = None) -> str:
    p = sim.params
    name = {"vasicek": "Vasicek", "cir": "CIR", "hull_white": "Hull-White"}.get(sim.model,
                                                                                 sim.model)
    sigma = (f"sigma {p.sigma:.4f} on sqrt(r)" if sim.model == "cir"
             else f"sigma {p.sigma / BP:.0f}bp a year")
    lines = [
        f"{name} calibrated with kappa {p.kappa:.2f} (half-life {math.log(2) / p.kappa:.1f}y), "
        f"long-run mean {_pct(p.theta)}, {sigma}, from r0 {_pct(p.r0)}.",
        f"Over {tenor_label(sim.horizon)} on {sim.n_paths:,} paths the short rate averages "
        f"{_pct(sim.mean_terminal)} with a 90% band of {_pct(sim.p05)} to {_pct(sim.p95)}.",
    ]
    if sim.prob_above is not None and sim.threshold is not None:
        lines.append(f"The model puts {sim.prob_above * 100:.0f}% odds on the rate finishing "
                     f"above {_pct(sim.threshold)}.")
    if sim.model_curve_at_horizon:
        (t0, z0), (t1, z1) = sim.model_curve_at_horizon[0], sim.model_curve_at_horizon[-1]
        lines.append(f"The median path's curve at the horizon runs from {_pct(z0)} at "
                     f"{tenor_label(t0)} to {_pct(z1)} at {tenor_label(t1)}.")
    if horizon_pv is not None:
        h = horizon_pv
        lines.append(f"Revalued on those paths the instrument is worth {_money(h.mean)} on "
                     f"average ({_money(h.p05)} to {_money(h.p95)}), a 95% horizon VaR of "
                     f"{_money(h.var95)} and expected shortfall of {_money(h.cvar95)}.")
    for note in (p.note, sim.note):
        if note:
            lines.append(note + ("." if not note.endswith(".") else ""))
    return " ".join(lines)


# --------------------------------------------------------------------------- #
# Macro
# --------------------------------------------------------------------------- #
def _level(row) -> str:
    if row is None:
        return _NA
    if row.unit == "pct":
        return _pct(row.last)
    if row.unit == "bp":
        return f"{row.last / BP:.0f}bp"
    return f"{row.last:,.2f}"


def _chg(row, n: str = "chg_1d") -> str:
    """A change in the row's own unit: bp for rates and spreads, % for levels."""
    if row is None or getattr(row, n) is None:
        return _NA
    c = getattr(row, n)
    if row.unit in ("pct", "bp"):
        return _bp(c)
    prev = row.last - c
    return f"{c / prev * 100:+.1f}%" if prev else _NA


def _where(row) -> str:
    return f"z {row.z_1y:+.1f}, {row.pct_1y * 100:.0f}th percentile of the year"


def narrate_macro(sheet: MacroSheet) -> str:
    r = sheet.row
    lines = [
        f"As of {sheet.as_of}: UST 2y {_level(r('DGS2'))}, 10y {_level(r('DGS10'))}, 30y "
        f"{_level(r('DGS30'))}, 2s10s {_level(r('T10Y2Y'))}; 10y real {_level(r('DFII10'))} "
        f"and breakeven {_level(r('T10YIE'))}; SOFR {_level(r('SOFR'))}.",
        f"Credit: IG OAS {_level(r('BAMLC0A0CM'))}, HY OAS {_level(r('BAMLH0A0HYM2'))}. "
        f"Dollar index {_level(r('DTWEXBGS'))}, VIX {_level(r('VIXCLS'))}, WTI "
        f"{_level(r('DCOILWTICO'))}.",
        sheet.regime.summary,
    ]
    if sheet.rows:
        s = max(sheet.rows, key=lambda x: abs(x.z_1y))
        lines.append(f"The most stretched series is {s.label} at {_level(s)} ({_where(s)}).")
    if sheet.synthetic_ids:
        lines.append(f"{len(sheet.synthetic_ids)} of {len(sheet.rows)} rows are SYNTHETIC "
                     f"({', '.join(sheet.synthetic_ids[:6])}"
                     f"{', ...' if len(sheet.synthetic_ids) > 6 else ''}): simulated, not "
                     "market data.")
    return " ".join(lines)


def narrate_daily_brief(sheet: MacroSheet) -> str:
    rows = list(sheet.rows)
    by_z = sorted(rows, key=lambda x: abs(x.z_1y), reverse=True)[:3]
    by_1d = sorted((x for x in rows if x.chg_1d is not None),
                   key=lambda x: abs(x.chg_1d / (x.last - x.chg_1d)) if x.last != x.chg_1d
                   else 0.0, reverse=True)[:3]
    r = sheet.row
    lines = [
        f"Daily read for {sheet.as_of}. Rates: 2y {_level(r('DGS2'))} ({_chg(r('DGS2'))} on "
        f"the day, {_chg(r('DGS2'), 'chg_1w')} on the week), 10y {_level(r('DGS10'))} "
        f"({_chg(r('DGS10'))}, {_chg(r('DGS10'), 'chg_1w')}), 2s10s {_level(r('T10Y2Y'))} "
        f"({_chg(r('T10Y2Y'))}); the 20-session curve read (descriptive, not a regime model, P19) is a "
        f"{sheet.regime.curve}.",
        f"The risk read is {sheet.regime.risk} with VIX {_level(r('VIXCLS'))} ({_chg(r('VIXCLS'))}) and "
        f"HY OAS {_level(r('BAMLH0A0HYM2'))} ({_chg(r('BAMLH0A0HYM2'))}); the dollar is "
        f"{sheet.regime.dollar} at {_level(r('DTWEXBGS'))} ({_chg(r('DTWEXBGS'), 'chg_1m')} "
        f"over a month); breakevens are {sheet.regime.inflation} and real yields "
        f"{sheet.regime.real_rates}.",
    ]
    if by_1d:
        lines.append("Biggest moves on the day: "
                     + "; ".join(f"{x.label} {_chg(x)} to {_level(x)}" for x in by_1d) + ".")
    if by_z:
        lines.append("Most extended versus the past year: "
                     + "; ".join(f"{x.label} ({_where(x)})" for x in by_z) + ".")
    if sheet.synthetic_ids:
        lines.append(f"Caveat: {len(sheet.synthetic_ids)} series are SYNTHETIC.")
    return " ".join(lines)


def narrate_weekly_strategy(sheet: MacroSheet, curve_report: CurveReport | None = None,
                            carry_rows: list[CarryRow] | None = None) -> str:
    """Sell-side tone: a duration, a curve and an FX view, each hung on a number.
    Rules are deliberately simple and stated with the number that drives them."""
    r = sheet.row
    ten, slope = r("DGS10"), r("T10Y2Y")
    lines = [f"Weekly rates/FX strategy, data to {sheet.as_of}. {sheet.regime.summary}"]

    # Duration: where the 10y sits in its 1y range decides the lean.
    if ten is not None:
        z, lvl, w = ten.z_1y, _level(ten), _chg(ten, "chg_1w")
        if z > 1.0:
            view = (f"Duration: lean long. The 10y at {lvl} is {z:+.1f} sigma above its 1y "
                    f"mean after {w} on the week; the entry is the level, the risk is a "
                    f"rising-breakeven trend (breakevens are currently "
                    f"{sheet.regime.inflation}).")
        elif z < -1.0:
            view = (f"Duration: stay short or underweight. The 10y at {lvl} is {z:+.1f} sigma "
                    f"below its 1y mean ({w} on the week); rallies from here need a risk-off "
                    f"tape to persist; the tape is currently {sheet.regime.risk}.")
        else:
            view = (f"Duration: neutral. The 10y at {lvl} sits {z:+.1f} sigma from its 1y "
                    f"mean ({w} on the week), not enough to pay for a directional position.")
        lines.append(view)

    # Curve: the regime and the level of 2s10s.
    if curve_report is not None:
        s10 = curve_report.descriptors["2s10s"]
        ds = curve_report.changes.get("2s10s", 0.0)
        regime, win = curve_report.regime, f"{curve_report.lookback} sessions"
    elif slope is not None:
        s10, ds = slope.last, (slope.chg_1m or 0.0)
        regime, win = sheet.regime.curve, "a month"
    else:
        s10 = None
    if s10 is not None:
        if "steepener" in regime:
            trade = "run steepeners"
        elif "flattener" in regime:
            trade = "run flatteners"
        else:
            trade = "no curve trade"
        line = (f"Curve: {trade}. 2s10s at {s10 / BP:+.0f}bp has moved {_bp(ds)} over {win}, "
                f"a {regime}")
        if curve_report is not None:
            d = curve_report.descriptors
            term = ("still carries a term premium" if d["5y5y"] > d["level"]
                    else "is priced for cuts")
            line += (f"; 5y5y at {_pct(d['5y5y'])} against a 2y/5y/10y level of "
                     f"{_pct(d['level'])} says the long end {term}")
        lines.append(line + ".")

    # FX: the dollar regime, then the carry ranking if there is one.
    usd = r("DTWEXBGS")
    if usd is not None:
        lean = {"strong": "USD longs against low-yielders",
                "weak": "fading dollar strength into high-carry currencies"
                }.get(sheet.regime.dollar, "range trades rather than trend")
        lines.append(f"FX: the broad dollar is {sheet.regime.dollar} at {_level(usd)} "
                     f"({_chg(usd, 'chg_1m')} over a month, z {usd.z_1y:+.1f}); in a "
                     f"{sheet.regime.risk} tape that favours {lean}.")
    if carry_rows:
        # A carry trade is named by its carry: the long is the best carry-to-vol
        # among positive-carry currencies, the funder the most negative carry.
        # The carry-plus-momentum score is reported beside it, never instead of it.
        by_ctv = sorted(carry_rows, key=lambda x: x.carry_to_vol, reverse=True)
        positive = [x for x in by_ctv if x.carry > 0]
        top = positive[0] if positive else by_ctv[0]
        low = min(carry_rows, key=lambda x: x.carry)
        best = max(carry_rows, key=lambda x: x.score)
        if positive:
            head = (f"Carry: long {top.ccy} ({_pct(top.carry)} p.a., carry-to-vol "
                    f"{top.carry_to_vol:+.2f}) funded in {low.ccy} ({_pct(low.carry)})")
        else:
            head = (f"Carry: no currency in the basket earns positive carry against USD; "
                    f"the least negative is {top.ccy} ({_pct(top.carry)} p.a.), the funder "
                    f"of choice {low.ccy} ({_pct(low.carry)})")
        tail = (f"; size for {top.vol_3m * 100:.0f}% realised vol"
                + (" and cut if risk turns off." if sheet.regime.risk != "risk-off"
                   else ", and keep it small while risk is off."))
        if best.ccy != top.ccy:
            tail += (f" On carry plus momentum the top score is {best.ccy} "
                     f"({best.score:+.2f}, momentum {best.mom_3m * 100:+.1f}%), a trend "
                     f"call rather than a carry call.")
        lines.append(head + tail)
    if sheet.synthetic_ids:
        lines.append(f"Caveat: {len(sheet.synthetic_ids)} inputs are SYNTHETIC; the views "
                     "above describe simulated data.")
    return " ".join(lines)


# --------------------------------------------------------------------------- #
# Structured products (duck-typed ProductReport from core.ficc.structured)
# --------------------------------------------------------------------------- #
def narrate_structured(p) -> str:
    # CMS products: `participation` is the coupon leverage and grid x is the spread in decimals.
    cms = str(getattr(p, "underlying", "")).startswith("CMS")
    ux = (lambda x: f"{x / BP:+.0f}bp") if cms else (lambda x: f"{x:g}")
    lines = [
        f"{p.product} on {_money(p.notional)} {p.currency} maturing in {tenor_label(p.maturity)}"
        f": fair value {p.fair_value:.2f} per 100 against an issue price of "
        f"{p.issue_price:.2f}, a {p.margin:+.2f}-point margin to the issuer.",
    ]
    if p.legs:
        lines.append("Legs: " + "; ".join(f"{leg.name} ({leg.kind}) {leg.value:+.2f}"
                                          for leg in p.legs) + ".")
    if getattr(p, "participation", None) is not None:
        lines.append(f"Coupon leverage is {p.participation:g}x the 10y-2y spread." if cms else
                     f"Participation is {p.participation * 100:.0f}% of the upside.")
    if getattr(p, "coupon", None) is not None:
        lines.append(f"The coupon is {_pct(p.coupon)} a year.")
    g = dict(getattr(p, "greeks", {}) or {})
    if g:
        lines.append("Whole-note risk: " + ", ".join(
            f"{k} {_money(v, signed=True)}" if k == "dv01" else f"{k} {v:+.4g}"
            for k, v in g.items()) + ".")
    if getattr(p, "payoff_grid", ()):
        lo, hi = p.payoff_grid[0], p.payoff_grid[-1]
        lines.append(f"Payoff at maturity runs from {lo[1]:.2f} per 100 with the underlying at "
                     f"{ux(lo[0])} to {hi[1]:.2f} at {ux(hi[0])}.")
    if getattr(p, "hedge", ()):
        lines.append("Hedge: " + "; ".join(f"{h.quantity:,.2f} {h.unit} {h.instrument}"
                                           for h in p.hedge) + ".")
    if getattr(p, "note", ""):
        lines.append(p.note)
    return " ".join(lines)


# --------------------------------------------------------------------------- #
# Claude
# --------------------------------------------------------------------------- #
REPORT_PROMPTS: dict[str, str] = {
    "daily_market_commentary": (
        "Write a daily market commentary in this format: a one-line headline; a 'Rates' "
        "paragraph (levels in percent, 1d and 1w changes in bp, the curve regime); an 'FX' "
        "paragraph (broad dollar, the majors, the risk regime); then 'Positioning ideas': two "
        "or three trades, each with an entry level, a stop and a target given as numbers taken "
        "from the payload (e.g. a stop one week's move beyond the entry, a target at the 1y "
        "mean implied by the z-score), and the observation that would invalidate it. Date the "
        "note to as_of and flag any ids listed under synthetic_ids as simulated."),
    "weekly_fi_fx_strategy": (
        "Write a weekly fixed-income and FX strategy note in this format: a one-line headline; "
        "'Duration view', 'Curve view' and 'FX view' paragraphs, each anchored to a number in "
        "the payload (10y level and z-score, 2s10s and its change, 5y5y, the dollar's 1m change, "
        "the carry ranking); a 'Positioning' list of two to four trades with entry, stop and "
        "target as numbers derived from the payload and the size rationale; and 'Risks to the "
        "view' naming the data that would flip each call. Date it to as_of and flag any "
        "synthetic_ids as simulated."),
}


def report_prompt(kind: str) -> str:
    """Format instruction appended to the operator's question for report kinds."""
    return REPORT_PROMPTS.get(kind, "")


def deep_analysis(kind: str, payload: dict, *, question: str = "") -> Analysis:
    """`core.quant.insights.deep_analysis` with the report format appended for the
    two report kinds (idempotent: a question that already carries it is left alone)."""
    extra = report_prompt(kind)
    if extra and extra not in question:
        question = f"{question.strip()}\n\n{extra}".strip()
    return _deep(kind, payload, question=question)


# --------------------------------------------------------------------------- #
# Self-check (synthetic only — no network)
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    from types import SimpleNamespace

    import config
    from core.ficc import data, fx, macro, ratesim
    from core.ficc.bonds import Bond, analyze_bond, scenario_pnl
    from core.ficc.curves import analyze_curve, curve_pca
    from core.ficc.swaps import Swap, Swaption, analyze_swap, price_cap_floor, price_swaption

    def clean(text: str) -> str:
        assert "None" not in text and "nan" not in text.split() and len(text) > 80, text
        return text

    panel = data.synthetic_curve_panel(days=200)
    rep = analyze_curve(panel)
    t = clean(narrate_curve(rep, curve_pca(panel)))
    assert rep.shape in t and rep.regime in t and bp_text(rep.descriptors["2s10s"]) in t
    assert "SYNTHETIC" in t and "PCA" in t

    bond = Bond(coupon=0.04, maturity=10.0)
    ba = analyze_bond(bond, price=98.5, curve=rep.curve)
    rows = scenario_pnl(bond, rep.curve, 98.5)
    t = clean(narrate_bond(ba, rows))
    assert f"{ba.dv01:,.0f}" in t and "98.500" in t and min(rows, key=lambda r: r.pnl).name in t

    sr = analyze_swap(Swap(tenor=10.0), rep.curve)
    t = clean(narrate_swap(sr))
    assert f"{sr.dv01:+,.0f}" in t and pct_text(sr.par_rate, decimals=3) in t and "5y5y" in t

    swn = price_swaption(Swaption(expiry=1.0, tenor=5.0), rep.curve, vol=0.0080)
    t = clean(narrate_swaption(swn))
    assert f"{swn.premium:,.0f}" in t and "80bp normal" in t and "1yx5y payer" in t

    cf = price_cap_floor(rep.curve, 5.0, None, vol=0.0080)
    t = clean(narrate_cap_floor(cf))
    assert f"{cf.premium:,.0f}" in t and f"{len(cf.caplets)} caplets" in t

    fwd = fx.forward(1.10, 0.05, 0.03, 0.5)
    t = clean(narrate_fx_forward("EURUSD", 1.10, fwd, fx.forward_points(1.10, fwd),
                                 fx.carry(0.05, 0.03), basis=-0.0012))
    assert "EUR/USD" in t and "-12.0bp" in t and "2.00%" in t

    gk = fx.garman_kohlhagen(1.10, 1.12, 0.5, 0.05, 0.03, 0.09)
    pts = fx.smile_from_quotes(fx.SmileQuote(0.5, 0.09, 0.01, 0.003), 1.10, 0.05, 0.03)
    fit = fx.calibrate_sabr(gk.forward, 0.5, [p.strike for p in pts], [p.vol for p in pts])
    t = clean(narrate_fx_option(gk, pts, fit))
    assert f"{gk.delta_spot:+.3f}" in t and "pays up for calls" in t and "SABR" in t

    spots = {f"USD{c}" if c in ("JPY", "KRW", "CAD", "CHF") else f"{c}USD":
             data.synthetic_fx(f"USD{c}" if c in ("JPY", "KRW", "CAD", "CHF") else f"{c}USD",
                               days=300)
             for c in data.G10_KRW if c != "USD"}
    rates = {c: data.synthetic_series(f"R_{c}", days=300, kind="rate") for c in data.G10_KRW}
    crows = fx.carry_table(spots, rates)
    bt = fx.carry_backtest(spots, rates)
    t = clean(narrate_carry(crows, bt))
    assert max(crows, key=lambda r: r.score).ccy in t and f"Sharpe {bt.sharpe:.2f}" in t

    prm = ratesim.calibrate(data.synthetic_series("SOFR", days=300, kind="rate"))
    sim = ratesim.simulate(prm, n_paths=500, threshold=0.05)
    hp = ratesim.horizon_pv_distribution(prm, sim, kind="bond", bond=bond, curve=rep.curve)
    t = clean(narrate_ratesim(sim, hp))
    assert pct_text(sim.mean_terminal) in t and "Vasicek" in t and f"{hp.var95:,.0f}" in t

    sheet = macro.macro_sheet(source="synthetic", days=300)
    t = clean(narrate_macro(sheet))
    assert sheet.as_of in t and "SYNTHETIC" in t and pct_text(sheet.row("DGS10").last) in t
    t = clean(narrate_daily_brief(sheet))
    assert sheet.regime.curve in t and "Biggest moves" in t
    t = clean(narrate_weekly_strategy(sheet, rep, crows))
    assert "Duration:" in t and "Curve:" in t and "FX:" in t and "Carry:" in t
    assert f"{rep.descriptors['2s10s'] / BP:+.0f}bp" in t
    clean(narrate_weekly_strategy(sheet))                # without the optional inputs

    prod = SimpleNamespace(
        product="Principal-protected note", notional=1e6, currency="USD", maturity=3.0,
        legs=(SimpleNamespace(name="ZCB", kind="zcb", value=86.5, detail=""),
              SimpleNamespace(name="ATM call", kind="option", value=12.5, detail="")),
        fair_value=99.0, issue_price=100.0, margin=1.0, participation=1.08, coupon=None,
        payoff_grid=((0.5, 100.0), (1.5, 154.0)), greeks={"delta": 0.55, "dv01": 260.0},
        hedge=(SimpleNamespace(instrument="EURUSD spot", quantity=550000.0, unit="EUR",
                               rationale="delta"),), note="No convexity adjustment.")
    t = clean(narrate_structured(prod))
    assert "99.00" in t and "108%" in t and "550,000.00 EUR" in t and "convexity" in t

    # (1) steepener: participation is leverage, grid x is the spread in decimals.
    cms = SimpleNamespace(
        product="Steepener note", notional=1e6, currency="USD", maturity=5.0, legs=(),
        fair_value=98.0, issue_price=100.0, margin=2.0, participation=4.0, coupon=0.02,
        payoff_grid=((-0.005, 100.0), (0.015, 106.0)), greeks={}, hedge=(), note="",
        underlying="CMS 10y-2y")
    t = clean(narrate_structured(cms))
    assert "Coupon leverage is 4x the 10y-2y spread" in t and "400%" not in t
    assert "at -50bp" in t and "at +150bp" in t

    # (2) negative carry+roll must read as a required rally, never a permissible rise.
    neg = SimpleNamespace(
        bond=SimpleNamespace(name="", coupon=0.01, maturity=10.0, freq=2, face=100.0,
                             notional=1e6),
        price=95.0, ytm=0.015, macaulay=9.0, modified=8.9, convexity=90.0, dv01=850.0,
        krd={}, z_spread=0.001, curve_price=95.0, note="",
        carry_roll=SimpleNamespace(carry=-0.2, rolldown=-0.1, total=-0.3, breakeven_bp=-3.5,
                                   horizon=0.25))
    t = clean(narrate_bond(neg))
    assert "yields must fall 3.5bp" in t and "rise -3.5bp" not in t and "-0.300" in t

    # (3) regime labels never supply the direction of a causal sentence.
    def _sheet(z: float, risk: str, inflation: str):
        row = SimpleNamespace(last=0.04, unit="pct", z_1y=z, pct_1y=0.5, chg_1d=0.0,
                              chg_1w=0.0, chg_1m=0.0)
        reg = SimpleNamespace(summary="Regime.", risk=risk, inflation=inflation,
                              dollar="strong", real_rates="rising", curve="bear steepener")
        return SimpleNamespace(as_of="2026-01-01", regime=reg, synthetic_ids=(),
                               row=lambda i: row if i == "DGS10" else None)
    t = narrate_weekly_strategy(_sheet(-1.5, "risk-on", "falling"))
    assert "need a risk-off tape to persist; the tape is currently risk-on" in t
    assert "need risk-on" not in t
    t = narrate_weekly_strategy(_sheet(1.5, "risk-on", "falling"))
    assert "a rising-breakeven trend (breakevens are currently falling)" in t
    assert "falling breakeven trend" not in t

    # (4) stale OECD rate dates are named; absent fields are ignored.
    stale = [SimpleNamespace(**{**vars(r), "rate_date": "2025-12-01", "rate_stale": True})
             for r in crows[:1]] + list(crows[1:])
    t = clean(narrate_carry(stale))
    assert f"{crows[0].ccy} (2025-12-01)" in t and "OECD" in t
    assert "OECD" not in narrate_carry(crows)

    assert report_prompt("daily_market_commentary") and report_prompt("weekly_fi_fx_strategy")
    assert report_prompt("bond") == ""
    saved = config.anthropic_key
    config.anthropic_key = lambda: ""                   # never reach the network here
    try:
        a = deep_analysis("weekly_fi_fx_strategy", {"x": 1}, question="views?")
        assert a.error and a.text == "" and a.engine == "none"
    finally:
        config.anthropic_key = saved
    q = "views?\n\n" + report_prompt("daily_market_commentary")
    assert q.count("headline") == 1                      # idempotent append
    print("ok")
