"""Pitchbook-style structured products and the hedge sheet behind them.

Four retail/private-bank staples, each decomposed into the legs a structurer
would actually book, priced off the package's own curve and vanilla pricers,
and handed back with a payoff grid, note-level Greeks and a hedge sheet:

  * `principal_protected_note`  — zero-coupon bond + participation × ATM call.
  * `reverse_convertible`       — annual coupon bond − put struck at `strike_pct`.
  * `dual_currency_deposit`     — deposit − FX put on the alternate currency.
  * `steepener_note`            — principal + leveraged CMS 10y−2y coupons, floored/capped.

`hedge_sheet` turns a report's Greeks into the first-order hedge: spot/forward
for delta, an ATM/strike vanilla for vega, a par swap (and optionally bond
futures) for DV01, and a DV01-neutral 2s10s swap spread for the steepener.

Conventions and simplifications, on purpose:

  * Everything is per 100 of notional; `fair_value`, `issue_price`, `margin`
    and every `Leg.value` are per 100. Greeks are in the note's currency for
    the full `notional`: `delta` = P&L for a +1% spot move, `gamma` = change
    in that delta for a further +1% move, `vega` = P&L per +1 vol-point,
    `dv01` = P&L for a −1bp parallel shift (positive when the note behaves
    like a long bond, matching the bond/receiver convention in this package).
    Greeks are central finite differences of a full revaluation with the
    solved parameter (participation, coupon, enhanced yield) pinned.
  * The domestic rate for an option is the curve's continuous zero to the
    option expiry; `r_for_or_div` is the foreign rate (FX) or dividend yield
    (EQ) as a flat decimal. Vanillas come from `fx.garman_kohlhagen`, which is
    Black-Scholes with two carries — the same formula prices an equity call.
  * The distributor margin is `issue_price − fair_value` per 100. Where a
    parameter is solved (participation, coupon, enhanced yield) it is solved
    so fair = issue − margin exactly; where nothing is solved (steepener)
    margin is simply reported.
  * Payoff grids are undiscounted terminal payoffs per 100, coupons summed at
    face; FX/EQ grids run 50%–150% of spot, the steepener grid over the
    realised 10y−2y spread held flat for every period.
  * The steepener coupon is the FORWARD CMS spread read off the single curve,
    with NO convexity or timing adjustment; the report's note says so loudly.
  * ACT/365F simple year fractions, single-curve discounting, no credit
    spread on the issuer's zero (add one by shifting the curve).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, replace
from typing import Callable

from core.ficc.bonds import Bond, cashflows, price_from_curve
from core.ficc.common import BP, FICCError, tenor_label
from core.ficc.curves import YieldCurve, coupon_times
from core.ficc.fx import garman_kohlhagen
from core.ficc.swaps import Swap, par_swap_rate, swap_dv01

_LEVELS = tuple(round(0.5 + 0.05 * i, 2) for i in range(21))     # payoff grid, × spot
_SPREADS_BP = tuple(range(-100, 301, 20))                          # steepener grid, bp
_EPS = 1e-9

Valuer = Callable[[YieldCurve, float | None, float | None], float]


@dataclass(frozen=True)
class Leg:
    name: str
    kind: str                         # zcb | coupon_bond | option | swap
    value: float                      # per 100 of notional, signed for the holder
    detail: str


@dataclass(frozen=True)
class HedgeLine:
    """quantity is signed: + buy / pay fixed / long futures, − sell / receive / short."""
    instrument: str
    quantity: float
    unit: str
    rationale: str


@dataclass(frozen=True)
class ProductReport:
    product: str
    notional: float
    currency: str
    maturity: float
    legs: tuple[Leg, ...]
    fair_value: float                 # per 100 of notional
    issue_price: float
    margin: float                     # issue − fair, per 100
    participation: float | None
    coupon: float | None              # decimal p.a.
    payoff_grid: tuple[tuple[float, float], ...]   # (underlying at maturity, payoff per 100)
    greeks: dict[str, float]          # delta, gamma, vega, dv01 [, dv01_2s10s] in currency
    hedge: tuple[HedgeLine, ...]
    note: str = ""
    underlying: str = ""              # "FX" | "EQ" | "CMS 10y-2y"
    spot: float | None = None         # option inputs kept so hedge_sheet can size vanillas
    strike: float | None = None
    vol: float | None = None
    r_for: float = 0.0


# --------------------------------------------------------------------------- #
# Shared pieces
# --------------------------------------------------------------------------- #
def _check(*, maturity: float, notional: float, issue_price: float = 100.0,
           spot: float = 1.0, vol: float = 0.1) -> None:
    if not all(math.isfinite(x) for x in (maturity, notional, issue_price, spot, vol)):
        raise ValueError("Product inputs must be finite.")
    if maturity <= 0 or notional <= 0 or issue_price <= 0:
        raise ValueError("maturity, notional and issue_price must be positive.")
    if spot <= 0 or vol <= 0:
        raise ValueError("spot and vol must be positive.")


def _vanilla(curve: YieldCurve, spot: float, strike: float, vol: float, r_for: float,
             T: float, call: bool):
    """GK vanilla with the domestic rate = the curve's continuous zero to T."""
    return garman_kohlhagen(spot, strike, T, float(curve.zero(T)), r_for, vol, call)


def _greeks(value: Valuer, curve: YieldCurve, spot: float | None, vol: float | None,
            scale: float) -> dict[str, float]:
    """Central differences of `value` (per 100) scaled to currency; see module doc."""
    v0 = value(curve, spot, vol)
    g = {"delta": 0.0, "gamma": 0.0, "vega": 0.0}
    if spot is not None and vol is not None:
        up, dn = value(curve, spot * 1.01, vol), value(curve, spot * 0.99, vol)
        g["delta"] = (up - dn) / 2.0 * scale
        g["gamma"] = (up - 2.0 * v0 + dn) * scale
        lo = max(vol - 0.01, 1e-4)
        g["vega"] = ((value(curve, spot, vol + 0.01) - value(curve, spot, lo))
                     / (vol + 0.01 - lo) * 0.01 * scale)
    g["dv01"] = (value(curve.shifted(-1.0), spot, vol)
                 - value(curve.shifted(1.0), spot, vol)) / 2.0 * scale
    return g


def _finish(report: ProductReport, curve: YieldCurve) -> ProductReport:
    return replace(report, hedge=hedge_sheet(report, curve=curve))


# --------------------------------------------------------------------------- #
# Products
# --------------------------------------------------------------------------- #
def principal_protected_note(curve: YieldCurve, *, spot: float, vol: float,
                             r_for_or_div: float = 0.0, maturity: float,
                             notional: float = 1_000_000.0, protection: float = 1.0,
                             issue_price: float = 100.0, underlying: str = "FX",
                             margin: float = 1.0, currency: str = "USD") -> ProductReport:
    """ZCB paying `protection`×100 at maturity plus `participation` × an ATM call on
    the underlying (notional/spot units), participation solved so that
    fair = issue_price − margin. FICCError when the zero already costs more than
    the issue price less margin (no option budget)."""
    _check(maturity=maturity, notional=notional, issue_price=issue_price, spot=spot, vol=vol)
    if protection <= 0:
        raise ValueError("protection must be positive (1.0 = full principal protection).")
    T, r = maturity, r_for_or_div
    df = float(curve.df(T))
    zcb = protection * 100.0 * df
    call = _vanilla(curve, spot, spot, vol, r, T, True)
    call_per_100 = 100.0 * call.price / spot
    budget = issue_price - margin - zcb
    if budget <= 0:
        raise FICCError(f"No option budget: the {protection:.0%} zero costs {zcb:.2f} per 100 "
                        f"against {issue_price - margin:.2f} available; lower protection, "
                        f"lengthen maturity or cut the margin.")
    part = budget / call_per_100

    def value(c: YieldCurve, s: float | None, v: float | None) -> float:
        opt = _vanilla(c, s, spot, v, r, T, True).price
        return protection * 100.0 * c.df(T) + part * 100.0 * opt / spot

    fair = value(curve, spot, vol)
    grid = tuple((lvl * spot, protection * 100.0 + part * 100.0 * max(lvl - 1.0, 0.0))
                 for lvl in _LEVELS)
    legs = (
        Leg("Zero-coupon bond", "zcb", zcb,
            f"{protection:.0%} of principal at {tenor_label(T)}, DF {df:.4f} "
            f"(zero {float(curve.zero(T)):.2%})"),
        Leg("ATM call", "option", part * call_per_100,
            f"{part:.2f} × call K={spot:g} (fwd {call.forward:.4g}, vol {vol:.1%}) "
            f"= {call_per_100:.2f} per 100 each"),
    )
    note = (f"{tenor_label(T)} {underlying} principal-protected note: {protection:.0%} "
            f"protection, {part:.2f}× participation in upside from {spot:g}; fair "
            f"{fair:.2f} = zero {zcb:.2f} + option {part * call_per_100:.2f}, distributor "
            f"margin {issue_price - fair:.2f} per 100. Single-curve, no issuer credit spread.")
    rep = ProductReport(
        product=f"Principal-protected note ({underlying})", notional=notional,
        currency=currency, maturity=T, legs=legs, fair_value=fair, issue_price=issue_price,
        margin=issue_price - fair, participation=part, coupon=None, payoff_grid=grid,
        greeks=_greeks(value, curve, spot, vol, notional / 100.0), hedge=(), note=note,
        underlying=underlying, spot=spot, strike=spot, vol=vol, r_for=r)
    return _finish(rep, curve)


def reverse_convertible(curve: YieldCurve, *, spot: float, vol: float,
                        r_for_or_div: float = 0.0, maturity: float,
                        notional: float = 1_000_000.0, strike_pct: float = 1.0,
                        coupon: float | None = None, issue_price: float = 100.0,
                        margin: float = 1.0, currency: str = "USD",
                        underlying: str = "FX") -> ProductReport:
    """Annual-coupon bond minus a put struck at strike_pct×spot on notional/K units
    (below K the holder is repaid in the underlying at K). coupon=None solves the
    coupon so that fair = issue_price − margin: c = (issue − margin + put −
    100·DF(T)) / (100·annuity)."""
    _check(maturity=maturity, notional=notional, issue_price=issue_price, spot=spot, vol=vol)
    if strike_pct <= 0:
        raise ValueError("strike_pct must be positive.")
    T, r = maturity, r_for_or_div
    K = strike_pct * spot
    put = _vanilla(curve, spot, K, vol, r, T, False)
    put_per_100 = 100.0 * put.price / K
    ann, df = curve.annuity(T, 1), float(curve.df(T))
    if coupon is None:
        coupon = (issue_price - margin + put_per_100 - 100.0 * df) / (100.0 * ann)
        if coupon <= 0:
            raise FICCError(f"Solved coupon {coupon:.2%} is not positive: the {tenor_label(T)} "
                            f"put at K={K:g} ({put_per_100:.2f} per 100) does not cover the "
                            f"margin {margin:.2f} under this curve.")
    elif coupon < 0:
        raise ValueError("coupon must be non-negative.")
    bond = Bond(coupon=coupon, maturity=T, freq=1, face=100.0, notional=notional)

    def value(c: YieldCurve, s: float | None, v: float | None) -> float:
        return price_from_curve(bond, c) - 100.0 * _vanilla(c, s, K, v, r, T, False).price / K

    fair = value(curve, spot, vol)
    bond_px = price_from_curve(bond, curve)
    coupons = float(cashflows(bond)[1].sum()) - 100.0
    grid = tuple((lvl * spot, min(100.0, 100.0 * lvl * spot / K) + coupons) for lvl in _LEVELS)
    legs = (
        Leg("Coupon bond", "coupon_bond", bond_px,
            f"{coupon:.2%} annual, {tenor_label(T)}; par rate {curve.par_rate(T, 1):.2%}"),
        Leg("Short put", "option", -put_per_100,
            f"K={K:g} ({strike_pct:.0%} of spot), vol {vol:.1%}, fwd {put.forward:.4g}; "
            f"{100.0 / K:.4g} units per 100"),
    )
    note = (f"{tenor_label(T)} {underlying} reverse convertible: {coupon:.2%} coupon against "
            f"a put at {strike_pct:.0%} of spot ({K:g}); fair {fair:.2f} = bond {bond_px:.2f} "
            f"− put {put_per_100:.2f}, margin {issue_price - fair:.2f} per 100. Below {K:g} the "
            f"holder takes the underlying at {K:g}. Single-curve, no issuer credit spread.")
    rep = ProductReport(
        product=f"Reverse convertible ({underlying})", notional=notional, currency=currency,
        maturity=T, legs=legs, fair_value=fair, issue_price=issue_price,
        margin=issue_price - fair, participation=None, coupon=coupon, payoff_grid=grid,
        greeks=_greeks(value, curve, spot, vol, notional / 100.0), hedge=(), note=note,
        underlying=underlying, spot=spot, strike=K, vol=vol, r_for=r)
    return _finish(rep, curve)


def dual_currency_deposit(curve_dom: YieldCurve, *, spot: float, vol: float, r_for: float,
                          maturity: float, notional: float = 1_000_000.0, strike: float,
                          base_ccy: str, quote_ccy: str, margin: float = 0.25) -> ProductReport:
    """Deposit in `quote_ccy` (the curve's currency) at an enhanced simple yield;
    if spot (quote per base) fixes below `strike` at maturity, principal and
    interest are repaid in `base_ccy` converted at `strike` — the depositor is
    short a base-ccy put on (1 + y·T)·notional/strike units. y solves
    fair = 100 − margin. margin defaults to 0.25 per 100 (short-dated product) and
    is capped at the put premium on a plain-deposit redemption (100/df units),
    so y >= the plain deposit rate by construction; the note says when it binds."""
    _check(maturity=maturity, notional=notional, spot=spot, vol=vol)
    if strike <= 0:
        raise ValueError("strike must be positive.")
    if margin < 0:
        raise ValueError("margin must be non-negative.")
    T = maturity
    df = float(curve_dom.df(T))
    dep_rate = (1.0 / df - 1.0) / T
    put = _vanilla(curve_dom, spot, strike, vol, r_for, T, False)
    unit_value = df - put.price / strike          # today's value of 1 quote-ccy of redemption
    if unit_value <= 0:
        raise FICCError(f"The {base_ccy} put at {strike:g} is worth more than the deposit "
                        f"itself; no yield solves this DCD.")
    premium = 100.0 * put.price / (strike * df)   # put on 100/df units, per 100 of notional
    capped = margin > premium
    if capped:
        margin = premium
    growth = (100.0 - margin) / (100.0 * unit_value)          # 1 + y·T
    y = (growth - 1.0) / T
    redemption = 100.0 * growth

    def value(c: YieldCurve, s: float | None, v: float | None) -> float:
        return redemption * (c.df(T) - _vanilla(c, s, strike, v, r_for, T, False).price / strike)

    fair = value(curve_dom, spot, vol)
    grid = tuple((lvl * spot, redemption * min(1.0, lvl * spot / strike)) for lvl in _LEVELS)
    legs = (
        Leg(f"{quote_ccy} deposit", "zcb", redemption * df,
            f"{y:.2%} simple for {tenor_label(T)} vs plain deposit {dep_rate:.2%}; "
            f"redeems {redemption:.2f}"),
        Leg(f"Short {base_ccy} put", "option", -redemption * put.price / strike,
            f"K={strike:g}, spot {spot:g}, fwd {put.forward:.4g}, vol {vol:.1%}; "
            f"{redemption / strike:.4g} {base_ccy} per 100"),
    )
    pair = f"{base_ccy}{quote_ccy}"
    note = (f"{tenor_label(T)} dual-currency deposit in {quote_ccy}: enhanced yield {y:.2%} "
            f"against a plain {quote_ccy} deposit at {dep_rate:.2%} (simple). If {pair} fixes "
            f"below {strike:g} the {redemption:.2f} redemption is paid in {base_ccy} at "
            f"{strike:g}. Fair {fair:.2f}, margin {100.0 - fair:.2f} per 100."
            + (f" Put premium {premium:.2f} per 100 covers only {premium:.2f} of the "
               f"requested margin; margin reduced, no yield enhancement." if capped else ""))
    rep = ProductReport(
        product=f"Dual-currency deposit {pair} K={strike:g}", notional=notional,
        currency=quote_ccy, maturity=T, legs=legs, fair_value=fair, issue_price=100.0,
        margin=100.0 - fair, participation=None, coupon=y, payoff_grid=grid,
        greeks=_greeks(value, curve_dom, spot, vol, notional / 100.0), hedge=(), note=note,
        underlying="FX", spot=spot, strike=strike, vol=vol, r_for=r_for)
    return _finish(rep, curve_dom)


def _cms_coupons(curve: YieldCurve, T: float, freq: int, leverage: float, floor: float,
                 cap: float | None) -> list[tuple[float, float, float, float]]:
    """(t_start, t_end, forward 10y−2y spread, coupon) per period, spread fixed at
    t_start off the forward curve."""
    ends = coupon_times(T, freq)
    starts = [0.0] + [float(t) for t in ends[:-1]]
    rows = []
    for t0, t1 in zip(starts, ends):
        spread = (par_swap_rate(curve, 10.0, freq=1, start=t0)
                  - par_swap_rate(curve, 2.0, freq=1, start=t0))
        cpn = max(leverage * spread, floor)
        if cap is not None:
            cpn = min(cpn, cap)
        rows.append((t0, float(t1), spread, cpn))
    return rows


def steepener_note(curve: YieldCurve, *, maturity: float, notional: float = 1_000_000.0,
                   leverage: float = 4.0, floor: float = 0.0, cap: float | None = None,
                   freq: int = 1, issue_price: float = 100.0,
                   currency: str = "USD") -> ProductReport:
    """Principal at maturity plus coupons clip(leverage·(CMS10y − CMS2y), floor, cap)
    per period, the CMS rates being the FORWARD par swap rates off `curve` at each
    period start. NO convexity adjustment: forward CMS rates are used as if they
    were martingales under the payment measure, which overstates the value of a
    long-CMS coupon. Nothing is solved; margin = issue_price − fair is reported."""
    _check(maturity=maturity, notional=notional, issue_price=issue_price)
    if leverage <= 0 or freq < 1 or (cap is not None and cap < floor):
        raise ValueError("Need leverage > 0, freq >= 1 and cap >= floor.")
    T = maturity
    rows = _cms_coupons(curve, T, freq, leverage, floor, cap)

    def value(c: YieldCurve, *_: float | None) -> float:
        cpns = _cms_coupons(c, T, freq, leverage, floor, cap)
        return 100.0 * c.df(T) + sum(100.0 * cpn / freq * c.df(t1) for _, t1, _, cpn in cpns)

    fair = value(curve)
    df = float(curve.df(T))
    coupon_pv = fair - 100.0 * df
    n = len(rows)
    def clip(x: float) -> float:
        return max(x, floor) if cap is None else min(max(x, floor), cap)

    grid = tuple((s / 1e4, 100.0 + 100.0 * clip(leverage * s / 1e4) * n / freq)
                 for s in _SPREADS_BP)
    sched = ", ".join(f"{tenor_label(t1)}: {cpn:.2%} (spread {sp / BP:+.0f}bp)"
                      for _, t1, sp, cpn in rows)
    legs = (
        Leg("Principal", "zcb", 100.0 * df, f"100 at {tenor_label(T)}, DF {df:.4f}"),
        Leg("CMS 10y−2y coupons", "swap", coupon_pv,
            f"{leverage:g}× spread, floor {floor:.2%}, cap "
            f"{'none' if cap is None else f'{cap:.2%}'}; {sched}"),
    )
    greeks = _greeks(value, curve, None, None, notional / 100.0)
    steep = curve.key_rate_shifted(10.0, 0.5).key_rate_shifted(2.0, -0.5)
    greeks["dv01_2s10s"] = (value(steep) - fair) * notional / 100.0
    avg = sum(cpn for *_, cpn in rows) / n
    note = (f"{tenor_label(T)} CMS steepener: coupon = clip({leverage:g} × (10y − 2y), "
            f"{floor:.2%}, {'none' if cap is None else f'{cap:.2%}'}), first coupon "
            f"{rows[0][3]:.2%}, average projected {avg:.2%}; fair {fair:.2f} = principal "
            f"{100.0 * df:.2f} + coupons {coupon_pv:.2f}, margin {issue_price - fair:.2f} per 100. "
            f"WARNING: coupons are priced off the FORWARD curve with NO convexity adjustment "
            f"(CMS forwards taken as unbiased), so the coupon leg is overstated; a "
            f"replication-based CMS convexity correction is not applied.")
    rep = ProductReport(
        product="CMS 10y-2y steepener note", notional=notional, currency=currency, maturity=T,
        legs=legs, fair_value=fair, issue_price=issue_price, margin=issue_price - fair,
        participation=leverage, coupon=rows[0][3], payoff_grid=grid, greeks=greeks, hedge=(),
        note=note, underlying="CMS 10y-2y")
    return _finish(rep, curve)


# --------------------------------------------------------------------------- #
# Hedge sheet
# --------------------------------------------------------------------------- #
def hedge_sheet(report: ProductReport, *, curve: YieldCurve,
                futures_dv01_per_contract: float | None = None) -> tuple[HedgeLine, ...]:
    """First-order hedges for the holder's Greeks: delta → units of the
    underlying spot/forward, vega → units of a vanilla at the note's strike and
    expiry, dv01 → par swap notional (swaps.swap_dv01) and, when
    `futures_dv01_per_contract` is given, bond futures contracts; a steepener adds
    a DV01-neutral 2s10s flattener. Quantities are signed (+ buy/pay fixed)."""
    g, T, ccy = report.greeks, report.maturity, report.currency
    unit = "shares" if report.underlying == "EQ" else "base ccy units"
    lines: list[HedgeLine] = []
    if report.spot and abs(g.get("delta", 0.0)) > _EPS:
        units = g["delta"] / (0.01 * report.spot)
        lines.append(HedgeLine(
            "Underlying spot/forward", -units, unit,
            f"note delta {g['delta']:,.0f} {ccy} per +1% spot = {units:,.0f} {unit}; "
            f"{'sell' if units > 0 else 'buy'} {abs(units):,.0f} to flatten"))
    if report.spot and report.vol and abs(g.get("vega", 0.0)) > _EPS:
        van = _vanilla(curve, report.spot, report.strike, report.vol, report.r_for, T, True)
        units = g["vega"] / van.vega
        lines.append(HedgeLine(
            f"{tenor_label(T)} vanilla K={report.strike:g}", -units, unit,
            f"note vega {g['vega']:,.0f} {ccy} per vol-pt vs {van.vega:.4g} per unit; "
            f"{'sell' if units > 0 else 'buy'} {abs(units):,.0f} {unit} of options"))
    if abs(g.get("dv01", 0.0)) > _EPS:
        per_mm = swap_dv01(Swap(tenor=T, notional=1e6), curve)      # payer, per 1mm
        notional = g["dv01"] / per_mm * 1e6
        side = "payer" if notional > 0 else "receiver"
        lines.append(HedgeLine(
            f"{tenor_label(T)} {side} swap", notional, ccy,
            f"note DV01 {g['dv01']:,.0f} {ccy} vs {per_mm:,.0f} per 1mm payer; "
            f"{'pay' if notional > 0 else 'receive'} fixed on {abs(notional):,.0f}"))
        if futures_dv01_per_contract:
            if futures_dv01_per_contract <= 0:
                raise ValueError("futures_dv01_per_contract must be positive.")
            n = g["dv01"] / futures_dv01_per_contract
            lines.append(HedgeLine(
                "Bond futures", -n, "contracts",
                f"{'sell' if n > 0 else 'buy'} {abs(n):,.1f} contracts at "
                f"{futures_dv01_per_contract:,.0f} DV01 each (alternative to the swap)"))
    if abs(g.get("dv01_2s10s", 0.0)) > _EPS:
        d10 = swap_dv01(Swap(tenor=10.0, notional=1e6), curve)
        d2 = swap_dv01(Swap(tenor=2.0, notional=1e6), curve)
        n10, n2 = g["dv01_2s10s"] / d10 * 1e6, g["dv01_2s10s"] / d2 * 1e6
        lines.append(HedgeLine(
            "2s10s flattener: 10y receiver", -n10, ccy,
            f"note gains {g['dv01_2s10s']:,.0f} {ccy} per +1bp 2s10s steepening; receive "
            f"10y on {abs(n10):,.0f}"))
        lines.append(HedgeLine(
            "2s10s flattener: 2y payer", n2, ccy,
            f"pay 2y on {abs(n2):,.0f} so the spread trade is DV01-neutral"))
    return tuple(lines)


# --------------------------------------------------------------------------- #
# Self-check
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    from core.ficc.common import UST_TENORS
    from core.ficc.curves import bootstrap_par_curve

    par = [0.035, 0.036, 0.037, 0.038, 0.040, 0.041, 0.043, 0.044, 0.045, 0.047, 0.046]
    c = bootstrap_par_curve(UST_TENORS, par, date="2026-09-04", source="TEST")

    # PPN: fair = issue − margin, participation > 0, payoff kinks at spot.
    ppn = principal_protected_note(c, spot=1.10, vol=0.08, r_for_or_div=0.02, maturity=3.0)
    assert abs(ppn.fair_value - 99.0) < 1e-9 and ppn.participation > 0
    assert ppn.fair_value <= ppn.issue_price and abs(ppn.margin - 1.0) < 1e-9
    at, up = dict(ppn.payoff_grid)[1.10], dict(ppn.payoff_grid)[1.10 * 1.5]
    assert abs(at - 100.0) < 1e-9 and abs(up - (100 + ppn.participation * 50)) < 1e-9
    assert abs(sum(l.value for l in ppn.legs) - ppn.fair_value) < 1e-9
    g = ppn.greeks
    assert g["delta"] > 0 and g["gamma"] > 0 and g["vega"] > 0 and g["dv01"] > 0, g
    kinds = [h.instrument for h in ppn.hedge]
    assert len(ppn.hedge) == 3 and "3y payer swap" in kinds, kinds
    assert ppn.hedge[0].quantity < 0 and ppn.hedge[1].quantity < 0   # sell spot, sell calls
    assert abs(ppn.hedge[0].quantity + g["delta"] / (0.01 * 1.10)) < 1e-6
    fut = hedge_sheet(ppn, curve=c, futures_dv01_per_contract=65.0)
    assert any(h.unit == "contracts" and abs(h.quantity + g["dv01"] / 65.0) < 1e-9 for h in fut)
    eq = principal_protected_note(c, spot=100.0, vol=0.25, r_for_or_div=0.015, maturity=5.0,
                                  protection=0.9, underlying="EQ")
    assert eq.participation > 0 and eq.hedge[0].unit == "shares"
    assert dict(eq.payoff_grid)[50.0] == 90.0                          # 90% floor
    try:
        principal_protected_note(c, spot=1.1, vol=0.08, maturity=0.25, margin=5.0)
        raise AssertionError("expected FICCError (no option budget)")
    except FICCError:
        pass

    # Reverse convertible: solved coupon beats the par rate, put shows in the payoff.
    rc = reverse_convertible(c, spot=1.10, vol=0.10, r_for_or_div=0.02, maturity=1.0,
                             strike_pct=0.95)
    assert abs(rc.fair_value - 99.0) < 1e-9 and rc.coupon > c.par_rate(1.0, 1)
    pay = dict(rc.payoff_grid)
    assert abs(pay[1.10] - (100 + rc.coupon * 100)) < 1e-9
    assert pay[1.10 * 0.5] < pay[1.10 * 0.9] < pay[1.10] == pay[1.10 * 1.5]
    assert rc.greeks["delta"] > 0 and rc.greeks["vega"] < 0 and rc.legs[1].value < 0
    assert rc.hedge[1].quantity > 0                                   # buy puts back
    fixed = reverse_convertible(c, spot=1.10, vol=0.10, r_for_or_div=0.02, maturity=1.0,
                                strike_pct=0.95, coupon=rc.coupon + 0.01)
    assert fixed.fair_value > rc.fair_value and fixed.margin < 1.0

    # DCD: enhanced yield above the plain deposit, conversion below strike.
    dcd = dual_currency_deposit(c, spot=1350.0, vol=0.09, r_for=0.045, maturity=0.25,
                                strike=1300.0, base_ccy="USD", quote_ccy="KRW")
    dep = (1.0 / c.df(0.25) - 1.0) / 0.25
    assert dcd.coupon > dep and abs(dcd.fair_value - 99.75) < 1e-9 and dcd.currency == "KRW"
    pay = dict(dcd.payoff_grid)
    red = 100.0 * (1.0 + dcd.coupon * 0.25)
    assert abs(pay[1350.0] - red) < 1e-9 and abs(pay[1350.0 * 0.9] - red * 1215.0 / 1300.0) < 1e-6
    assert "USDKRW" in dcd.note and dcd.greeks["delta"] > 0
    assert "margin reduced" not in dcd.note
    # Far-OTM short-dated put worth less than the margin: yield never drops below the deposit.
    otm = dual_currency_deposit(c, spot=1.10, vol=0.07, r_for=0.02, maturity=0.25,
                                strike=1.10 * 0.92, base_ccy="EUR", quote_ccy="USD")
    assert otm.coupon >= dep - 1e-12 and otm.margin < 0.25, (otm.coupon, dep, otm.margin)
    assert "margin reduced" in otm.note and abs(otm.margin - (100.0 - otm.fair_value)) < 1e-9

    # Steepener: forward-curve coupons, convexity warning, slope exposure hedged.
    st = steepener_note(c, maturity=5.0, leverage=4.0, floor=0.0, cap=0.06)
    assert "convexity" in st.note.lower() and st.participation == 4.0
    assert 0.0 <= st.coupon <= 0.06 and st.margin == 100.0 - st.fair_value
    assert abs(sum(l.value for l in st.legs) - st.fair_value) < 1e-9
    pay = dict(st.payoff_grid)
    assert pay[-0.01] == 100.0 and pay[0.01] > pay[0.0]
    assert abs(pay[0.03] - (100.0 + 100.0 * 0.06 * 5)) < 1e-9
    assert st.greeks["delta"] == 0.0 and st.greeks["dv01"] > 0 and st.greeks["dv01_2s10s"] > 0
    names = [h.instrument for h in st.hedge]
    assert names[0] == "5y payer swap" and any("10y receiver" in n for n in names), names
    uncapped = steepener_note(c, maturity=5.0, leverage=4.0)
    assert uncapped.fair_value >= st.fair_value
    print("ok")
