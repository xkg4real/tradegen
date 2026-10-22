"""Bond analytics: price/yield, duration, convexity, DV01, key-rate DV01s,
z-spread, carry & roll-down, curve scenarios and a futures hedge ratio.

A `Bond` is a plain fixed-coupon bullet. Yield analytics use the street
convention (discrete compounding at `freq`, fractional-period exponent t·freq);
curve analytics discount each cashflow with `YieldCurve.df` times exp(−z·t) for
a z-spread. Everything is per `face` (100 by default); currency numbers scale
by `notional / face`.

Simplifications, on purpose:

  * ACT/365F simple year fractions; no settlement date, no accrued interest —
    `maturity` is time to maturity in years and prices are clean-ish "per 100"
    numbers off the cashflow schedule t_i = T − k/freq (t_i > 0).
  * DV01 is reported POSITIVE for a long bond: dv01 = −dP/dy · 1bp · notional/face.
    Key-rate DV01s are central differences of ±1bp triangular zero bumps with
    the z-spread held fixed; their sum is the parallel *zero* DV01, which sits
    a factor (1 + y/freq) above the yield DV01 (continuous vs discrete shift).
  * Carry funds the full price at the curve's zero rate to the horizon; roll-down
    reprices the bond with maturity − horizon off the unchanged curve, z-spread
    held. Both are per `face` over the horizon, not annualized.
  * Single-curve: the same curve projects and discounts.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, replace

import numpy as np
from scipy.optimize import brentq

from core.ficc.common import BP, KEY_TENORS, FICCError
from core.ficc.curves import YieldCurve, coupon_times, flat_curve

_YTM_LO, _YTM_HI = -0.5, 2.0                          # brentq bracket for yields
_SPREAD_LO, _SPREAD_HI = -0.5, 2.0                    # and for z-spreads


@dataclass(frozen=True)
class Bond:
    coupon: float                     # annual coupon rate, decimal
    maturity: float                   # years
    freq: int = 2
    face: float = 100.0
    notional: float = 1_000_000.0
    name: str = ""

    def __post_init__(self) -> None:
        if not math.isfinite(self.coupon) or self.coupon < 0:
            raise ValueError(f"coupon must be a finite non-negative decimal, got {self.coupon}.")
        if not math.isfinite(self.maturity) or self.maturity <= 0:
            raise ValueError(f"maturity must be positive years, got {self.maturity}.")
        if int(self.freq) < 1:
            raise ValueError(f"freq must be >= 1, got {self.freq}.")
        if self.face <= 0 or self.notional <= 0:
            raise ValueError("face and notional must be positive.")
        object.__setattr__(self, "freq", int(self.freq))


# --------------------------------------------------------------------------- #
# Cashflows, price <-> yield
# --------------------------------------------------------------------------- #
def cashflow_times(bond: Bond) -> np.ndarray:
    return coupon_times(bond.maturity, bond.freq)


def cashflows(bond: Bond) -> tuple[np.ndarray, np.ndarray]:
    """(times, amounts per `face`): coupon/freq each date, plus face at maturity."""
    t = cashflow_times(bond)
    cf = np.full(t.size, bond.coupon * bond.face / bond.freq)
    cf[-1] += bond.face
    return t, cf


def _check_ytm(bond: Bond, ytm: float) -> None:
    if not math.isfinite(ytm) or 1.0 + ytm / bond.freq <= 0:
        raise ValueError(f"yield {ytm} is not usable with freq {bond.freq}.")


def _pv_terms(bond: Bond, ytm: float) -> tuple[np.ndarray, np.ndarray]:
    """(times, PV of each cashflow) under street-convention discrete compounding."""
    _check_ytm(bond, ytm)
    t, cf = cashflows(bond)
    return t, cf * (1.0 + ytm / bond.freq) ** (-t * bond.freq)


def price_from_yield(bond: Bond, ytm: float) -> float:
    """Σ cf_i / (1 + y/f)^(t_i·f), per `face`."""
    return float(np.sum(_pv_terms(bond, ytm)[1]))


def yield_from_price(bond: Bond, price: float) -> float:
    """brentq on [-0.5, 2.0]."""
    if not math.isfinite(price) or price <= 0:
        raise ValueError(f"price must be positive, got {price}.")
    f = lambda y: price_from_yield(bond, y) - price      # noqa: E731
    if f(_YTM_LO) * f(_YTM_HI) > 0:
        raise FICCError(f"No yield in [{_YTM_LO}, {_YTM_HI}] reproduces price {price:.4f}.")
    return float(brentq(f, _YTM_LO, _YTM_HI, xtol=1e-14, rtol=1e-14, maxiter=200))


def price_from_curve(bond: Bond, curve: YieldCurve, *, spread: float = 0.0) -> float:
    """Σ cf_i · DF(t_i) · exp(−spread·t_i), per `face`."""
    t, cf = cashflows(bond)
    return float(np.sum(cf * curve.df(t) * np.exp(-spread * t)))


def z_spread(bond: Bond, curve: YieldCurve, price: float) -> float:
    """Constant continuously-compounded spread over the curve that reprices `price`."""
    if not math.isfinite(price) or price <= 0:
        raise ValueError(f"price must be positive, got {price}.")
    f = lambda s: price_from_curve(bond, curve, spread=s) - price      # noqa: E731
    if f(_SPREAD_LO) * f(_SPREAD_HI) > 0:
        raise FICCError(f"No z-spread in [{_SPREAD_LO}, {_SPREAD_HI}] reproduces {price:.4f}.")
    return float(brentq(f, _SPREAD_LO, _SPREAD_HI, xtol=1e-14, rtol=1e-14, maxiter=200))


# --------------------------------------------------------------------------- #
# Risk
# --------------------------------------------------------------------------- #
def macaulay_duration(bond: Bond, ytm: float) -> float:
    t, pv = _pv_terms(bond, ytm)
    return float(np.sum(t * pv) / np.sum(pv))


def modified_duration(bond: Bond, ytm: float) -> float:
    return macaulay_duration(bond, ytm) / (1.0 + ytm / bond.freq)


def convexity(bond: Bond, ytm: float) -> float:
    """(1/P)·d²P/dy² = Σ t_i (t_i + 1/f) PV_i / ((1 + y/f)² P)."""
    t, pv = _pv_terms(bond, ytm)
    return float(np.sum(t * (t + 1.0 / bond.freq) * pv) / ((1.0 + ytm / bond.freq) ** 2
                                                           * np.sum(pv)))


def dv01(bond: Bond, ytm: float) -> float:
    """Currency P&L of a −1bp yield move on `notional` (positive for a long bond):
    modified_duration · price/face · notional · 1bp."""
    return modified_duration(bond, ytm) * price_from_yield(bond, ytm) / bond.face \
        * bond.notional * BP


def key_rate_dv01(bond: Bond, curve: YieldCurve, *, spread: float = 0.0,
                  key_tenors: tuple[float, ...] = KEY_TENORS) -> dict[float, float]:
    """Currency per bp at each key tenor: (P(−1bp) − P(+1bp))/2 · notional/face,
    with `spread` (the z-spread that matches the market price) held fixed. The
    triangular bumps partition unity, so the sum is the parallel zero DV01."""
    scale = bond.notional / bond.face
    out = {}
    for k in key_tenors:
        dn = price_from_curve(bond, curve.key_rate_shifted(k, -1.0, key_tenors=key_tenors),
                              spread=spread)
        up = price_from_curve(bond, curve.key_rate_shifted(k, +1.0, key_tenors=key_tenors),
                              spread=spread)
        out[float(k)] = (dn - up) / 2.0 * scale
    return out


@dataclass(frozen=True)
class CarryRoll:
    carry: float                      # per face over the horizon
    rolldown: float
    total: float
    breakeven_bp: float               # yield rise that wipes out `total`
    horizon: float = 0.25


def carry_roll(bond: Bond, curve: YieldCurve, price: float, *,
               horizon: float = 0.25) -> CarryRoll:
    """Horizon P&L (per `face`) with the curve unchanged, split the desk's way.

    carry     = coupon accrued over h − funding, funding = curve.zero(h)·price·h
                (the whole price financed at the curve's zero rate to h).
    rolldown  = clean price of the AGED bond − price. The aged bond is this bond
                h later: the same cashflows, each h closer, discounted off today's
                curve with the z-spread held; its dirty price less the coupon
                accrued over h is its clean price. Shifting the whole schedule is
                what keeps accrual out of roll-down — repricing a (maturity − h)
                bond on the unshifted T − k/f grid would hand it a full coupon at
                h and count three months of carry as curve roll.
    breakeven_bp = total / (modified_duration · price) in bp: the parallel yield
                rise that wipes the horizon P&L out.
    A bond that matures inside the horizon rolls to face.
    """
    if horizon <= 0:
        raise ValueError(f"horizon must be positive, got {horizon}.")
    ytm = yield_from_price(bond, price)
    h = min(horizon, bond.maturity)
    accrued = bond.coupon * bond.face * h
    funding = float(curve.zero(h)) * price * h
    if bond.maturity - horizon > 1e-9:
        z = z_spread(bond, curve, price)
        times, amounts = cashflows(bond)
        keep = times > horizon + 1e-12
        t_aged = times[keep] - horizon
        dirty_aged = float(np.sum(amounts[keep] * curve.df(t_aged) * np.exp(-z * t_aged)))
        # Coupons that fall inside the horizon are cash in hand, not accrual.
        paid = float(np.sum(amounts[~keep])) - (bond.face if not keep.any() else 0.0)
        clean_aged = dirty_aged + paid - accrued
    else:
        clean_aged = bond.face
    carry = accrued - funding
    rolldown = clean_aged - price
    total = carry + rolldown
    slope = modified_duration(bond, ytm) * price          # dP per 1.00 of yield
    return CarryRoll(carry=carry, rolldown=rolldown, total=total,
                     breakeven_bp=total / slope / BP if slope > 0 else 0.0, horizon=horizon)


# --------------------------------------------------------------------------- #
# Full analysis
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class BondAnalytics:
    bond: Bond
    price: float
    ytm: float
    macaulay: float
    modified: float
    convexity: float
    dv01: float
    krd: dict[float, float]
    z_spread: float
    carry_roll: CarryRoll
    curve_price: float
    engine: str = "local"
    note: str = ""


def analyze_bond(bond: Bond, *, price: float | None = None, ytm: float | None = None,
                 curve: YieldCurve | None = None, horizon: float = 0.25) -> BondAnalytics:
    """Exactly one of price/ytm. Without a curve, a flat curve at the continuous
    equivalent of the yield (z = f·ln(1 + y/f)) stands in, so curve_price == price
    and the z-spread is ~0; `note` says so."""
    if (price is None) == (ytm is None):
        raise ValueError("Give exactly one of price or ytm.")
    if ytm is None:
        ytm = yield_from_price(bond, price)
    else:
        price = price_from_yield(bond, ytm)
    note = ""
    if curve is None:
        curve = flat_curve(bond.freq * math.log1p(ytm / bond.freq), source="FLAT@YTM")
        note = "No curve supplied: flat curve at the bond's own yield; z-spread is trivially 0."
    z = z_spread(bond, curve, price)
    return BondAnalytics(
        bond=bond, price=price, ytm=ytm,
        macaulay=macaulay_duration(bond, ytm), modified=modified_duration(bond, ytm),
        convexity=convexity(bond, ytm), dv01=dv01(bond, ytm),
        krd=key_rate_dv01(bond, curve, spread=z), z_spread=z,
        carry_roll=carry_roll(bond, curve, price, horizon=horizon),
        curve_price=price_from_curve(bond, curve), note=note,
    )


# --------------------------------------------------------------------------- #
# Scenarios
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class ScenarioRow:
    name: str
    shock_bp: dict[float, float] | float
    new_price: float
    pnl: float                        # currency on notional
    pnl_pct: float                    # new_price / price − 1


def _ramp(t0: float, bp0: float, t1: float, bp1: float) -> dict[float, float]:
    """bp0 at/below t0, bp1 at/above t1, linear in tenor between, on KEY_TENORS."""
    return {k: float(np.interp(k, [t0, t1], [bp0, bp1])) for k in KEY_TENORS}


SCENARIO_SHOCKS: dict[str, dict[float, float] | float] = {
    "+25bp parallel": 25.0,
    "-25bp parallel": -25.0,
    "+100bp parallel": 100.0,
    "-100bp parallel": -100.0,
    "bear steepener": _ramp(2.0, 0.0, 30.0, 50.0),
    "bull steepener": _ramp(0.25, -50.0, 30.0, 0.0),
    "bear flattener": _ramp(0.25, 50.0, 30.0, 0.0),
    "bull flattener": _ramp(2.0, 0.0, 30.0, -50.0),
    "2y-5y-10y fly": {k: {2.0: -12.5, 5.0: 25.0, 10.0: -12.5}.get(k, 0.0) for k in KEY_TENORS},
}
DEFAULT_SCENARIOS: tuple[str, ...] = tuple(SCENARIO_SHOCKS)


def shocked_curve(curve: YieldCurve, shock: dict[float, float] | float) -> YieldCurve:
    """Parallel shift for a float; for a per-tenor dict the bp shocks are linearly
    interpolated across the curve's own knots (flat beyond the shock's ends)."""
    if isinstance(shock, (int, float)):
        return curve.shifted(float(shock))
    keys = sorted(shock)
    bps = np.interp(np.asarray(curve.tenors), keys, [shock[k] for k in keys])
    zs = tuple(float(z + b * BP) for z, b in zip(curve.zeros, bps))
    return replace(curve, zeros=zs, method="shifted", note=f"{curve.note} scenario".strip())


def scenario_pnl(bond: Bond, curve: YieldCurve, price: float, *,
                 scenarios=None) -> list[ScenarioRow]:
    """Full revaluation off the shocked curve with the z-spread held fixed, so
    convexity shows up naturally. `scenarios`: names from DEFAULT_SCENARIOS, or a
    {name: shock} dict (float bp or {tenor: bp}); None = all defaults."""
    if scenarios is None:
        shocks = SCENARIO_SHOCKS
    elif isinstance(scenarios, dict):
        shocks = scenarios
    else:
        unknown = [s for s in scenarios if s not in SCENARIO_SHOCKS]
        if unknown:
            raise FICCError(f"Unknown scenario(s) {unknown}; choose from {DEFAULT_SCENARIOS}.")
        shocks = {s: SCENARIO_SHOCKS[s] for s in scenarios}
    z = z_spread(bond, curve, price)
    scale = bond.notional / bond.face
    rows = []
    for name, shock in shocks.items():
        new = price_from_curve(bond, shocked_curve(curve, shock), spread=z)
        rows.append(ScenarioRow(name=name, shock_bp=shock, new_price=new,
                                pnl=(new - price) * scale, pnl_pct=new / price - 1.0))
    return rows


def futures_hedge_ratio(position_dv01: float, ctd_dv01_per_contract: float,
                        conversion_factor: float) -> float:
    """Contracts to sell against a long position: position_dv01 × CF / ctd_dv01
    (the future's DV01 is the CTD's DV01 divided by its conversion factor)."""
    if ctd_dv01_per_contract <= 0 or conversion_factor <= 0:
        raise ValueError("CTD DV01 per contract and conversion factor must be positive.")
    return position_dv01 * conversion_factor / ctd_dv01_per_contract


# --------------------------------------------------------------------------- #
# Self-check
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    b = Bond(coupon=0.05, maturity=10.0)
    assert abs(price_from_yield(b, 0.05) - 100.0) < 1e-9, "par bond must price at 100"
    assert abs(yield_from_price(b, 100.0) - 0.05) < 1e-12
    p = price_from_yield(b, 0.06)
    assert abs(yield_from_price(b, p) - 0.06) < 1e-12
    frac = Bond(coupon=0.04, maturity=7.3, freq=2)    # short first stub, fractional exponent
    assert abs(yield_from_price(frac, price_from_yield(frac, 0.045)) - 0.045) < 1e-12

    # Macaulay ≈ −dP/dy·(1+y/f)/P by central difference; convexity ≈ d²P/dy²/P.
    y, h = 0.05, 1e-5
    p0, pu, pd = (price_from_yield(b, v) for v in (y, y + h, y - h))
    num_mac = -(pu - pd) / (2 * h) * (1 + y / b.freq) / p0
    assert abs(macaulay_duration(b, y) - num_mac) < 1e-6, (macaulay_duration(b, y), num_mac)
    num_cvx = (pu - 2 * p0 + pd) / h ** 2 / p0
    assert convexity(b, y) > 0 and abs(convexity(b, y) - num_cvx) < 1e-3
    assert abs(dv01(b, y) - modified_duration(b, y) * 100.0) < 1e-9   # 1e6 · 1bp · P/100

    # Flat curve at the continuous equivalent of the yield reprices the bond.
    zc = b.freq * math.log1p(y / b.freq)
    flat = flat_curve(zc)
    assert abs(price_from_curve(b, flat) - p0) < 1e-9
    assert abs(z_spread(b, flat, p0)) < 1e-10
    assert abs(price_from_curve(b, flat, spread=z_spread(b, flat, 95.0)) - 95.0) < 1e-9

    # KRD sum ≈ dv01 on a par bond (zero vs yield shift differ by 1 + y/f ≈ 2.5%).
    krd = key_rate_dv01(b, flat)
    assert set(krd) == set(KEY_TENORS)
    tot = sum(krd.values())
    assert abs(tot / dv01(b, y) - 1.0) < 0.03, (tot, dv01(b, y))
    assert krd[10.0] > krd[2.0] > 0 and abs(krd[30.0]) < 1e-6

    # Analytics, carry/roll and scenarios on a sloped curve.
    from core.ficc.curves import bootstrap_par_curve
    curve = bootstrap_par_curve([0.25, 1, 2, 3, 5, 7, 10, 20, 30],
                                [0.052, 0.050, 0.046, 0.044, 0.043, 0.044, 0.045, 0.048, 0.047])
    a = analyze_bond(b, price=98.0, curve=curve)
    assert abs(price_from_curve(b, curve, spread=a.z_spread) - 98.0) < 1e-9
    assert a.engine == "local" and a.note == ""
    assert abs(sum(a.krd.values()) / a.dv01 - 1.0) < 0.05
    cr = a.carry_roll
    assert abs(cr.total - cr.carry - cr.rolldown) < 1e-12 and cr.horizon == 0.25
    assert abs(cr.carry - (1.25 - float(curve.zero(0.25)) * 98.0 * 0.25)) < 1e-12
    assert cr.carry < 0                                # 5.10% running yield < 5.17% funding
    flat_a = analyze_bond(b, ytm=0.05)
    assert "flat" in flat_a.note and abs(flat_a.z_spread) < 1e-10
    assert abs(flat_a.curve_price - 100.0) < 1e-9
    try:
        analyze_bond(b)
    except ValueError:
        pass
    else:
        raise AssertionError("analyze_bond needs exactly one of price/ytm")

    rows = scenario_pnl(b, curve, 98.0)
    assert [r.name for r in rows] == list(DEFAULT_SCENARIOS)
    by = {r.name: r for r in rows}
    assert by["+25bp parallel"].pnl < 0 < by["-25bp parallel"].pnl
    # convexity: a +100bp loss is smaller than 100·dv01, a −100bp gain is larger
    assert by["+100bp parallel"].pnl > -100 * a.dv01
    assert by["-100bp parallel"].pnl > 100 * a.dv01
    assert by["bear steepener"].pnl < 0 < by["bull flattener"].pnl
    fly5 = {r.name: r for r in scenario_pnl(Bond(0.05, 5.0), curve, 100.0)}["2y-5y-10y fly"]
    # +25 at 5y hurts a 5y bond; −12.5 at 10y helps a 10y bond
    assert fly5.pnl < 0 < by["2y-5y-10y fly"].pnl
    assert abs(scenario_pnl(b, curve, 98.0, scenarios={"zero": 0.0})[0].pnl) < 1e-6
    assert len(scenario_pnl(b, curve, 98.0, scenarios=("+25bp parallel",))) == 1
    assert abs(futures_hedge_ratio(a.dv01, 65.0, 0.8) - a.dv01 * 0.8 / 65.0) < 1e-12
    print("ok")
