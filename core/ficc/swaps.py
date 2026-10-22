"""Interest-rate swaps, forward swaps, swaptions and caps/floors.

`Swap` + `analyze_swap` cover the linear side (par rate, PV, DV01, key-rate
DV01s, one-year carry and roll-down, the forward-swap grid). `black76` and
`bachelier` price a single European option per unit of annuity; `Swaption`,
`price_swaption`, `price_cap_floor` and `atm_straddle` scale them by the
annuity and notional. Implied-vol inverters and the Black<->normal converters
sit alongside.

Simplifications, on purpose:

  * Single-curve: the `YieldCurve` both projects forwards and discounts, so a
    floating leg at inception is worth N·(DF(start) − DF(end)) and the payer
    PV is N·(DF(start) − DF(end)) − N·K·annuity.
  * ACT/365F simple year fractions, coupon dates T − k/freq per
    `curves.coupon_times`. Default `freq=1` mirrors SOFR OIS annual/annual.
  * DV01 and key-rate DV01s are central differences (±1bp) in currency, signed
    for the position: a payer gains when rates rise, so its DV01 is positive;
    a receiver's is negative. `dv01 ≈ Σ krd` because the key-rate bumps
    partition a parallel shift between the first and last key tenor.
  * Option `theta` is −∂price/∂T at fixed discount factor (per year, negative
    for a long option); the annuity's own time decay is not included.
  * The first caplet of a spot-start cap is dropped (its rate is already fixed).
  * No convexity or timing adjustments anywhere.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, replace

from scipy.optimize import brentq

from core.ficc.common import BP, KEY_TENORS, FICCError, tenor_label
from core.ficc.curves import YieldCurve, coupon_times

_SQRT2 = math.sqrt(2.0)
_SQRT2PI = math.sqrt(2.0 * math.pi)
_FWD_GRID = (("1y1y", 1.0, 1.0), ("2y1y", 2.0, 1.0), ("5y5y", 5.0, 5.0), ("10y10y", 10.0, 10.0))


def _ncdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / _SQRT2))


def _npdf(x: float) -> float:
    return math.exp(-0.5 * x * x) / _SQRT2PI


# --------------------------------------------------------------------------- #
# Swaps
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Swap:
    tenor: float                      # years from `start` to maturity
    fixed_rate: float | None = None   # None -> par at pricing time
    notional: float = 1_000_000.0
    pay_fixed: bool = True
    freq: int = 1                     # payments per year, both legs (OIS annual/annual)
    start: float = 0.0                # forward start in years (0 = spot)

    def __post_init__(self) -> None:
        if self.tenor <= 0 or self.notional <= 0 or self.freq < 1 or self.start < 0:
            raise ValueError("Swap needs tenor > 0, notional > 0, freq >= 1, start >= 0.")
        if self.fixed_rate is not None and not math.isfinite(self.fixed_rate):
            raise ValueError("fixed_rate must be finite.")

    @property
    def end(self) -> float:
        return self.start + self.tenor

    @property
    def label(self) -> str:
        side = "payer" if self.pay_fixed else "receiver"
        fwd = f"{tenor_label(self.start)}" if self.start > 0 else ""
        return f"{fwd}{tenor_label(self.tenor)} {side}"


def annuity(curve: YieldCurve, tenor: float, freq: int = 1, start: float = 0.0) -> float:
    """Σ DF(t_i)/freq over the swap's coupon dates — delegates to the curve."""
    return curve.annuity(start + tenor, freq, start)


def par_swap_rate(curve: YieldCurve, tenor: float, *, freq: int = 1, start: float = 0.0) -> float:
    """(DF(start) − DF(end)) / annuity: the fixed rate that prices the swap at zero."""
    return curve.par_rate(start + tenor, freq, start)


def _fixed_rate(swap: Swap, curve: YieldCurve) -> float:
    if swap.fixed_rate is not None:
        return float(swap.fixed_rate)
    return par_swap_rate(curve, swap.tenor, freq=swap.freq, start=swap.start)


def swap_pv(swap: Swap, curve: YieldCurve) -> float:
    """Payer: N·(DF(start) − DF(end)) − N·K·annuity. Receiver: the negative."""
    k = _fixed_rate(swap, curve)
    n = swap.notional
    pv = n * (curve.df(swap.start) - curve.df(swap.end)) - n * k * annuity(
        curve, swap.tenor, swap.freq, swap.start)
    return pv if swap.pay_fixed else -pv


def _pinned(swap: Swap, curve: YieldCurve) -> Swap:
    """The swap with its fixed rate resolved on `curve`, so bumps do not re-par it."""
    return replace(swap, fixed_rate=_fixed_rate(swap, curve))


def swap_dv01(swap: Swap, curve: YieldCurve) -> float:
    """Currency P&L of the position for a +1bp parallel move (central ±1bp
    difference); positive for a payer, negative for a receiver."""
    s = _pinned(swap, curve)
    return (swap_pv(s, curve.shifted(1.0)) - swap_pv(s, curve.shifted(-1.0))) / 2.0


def swap_krd(swap: Swap, curve: YieldCurve, *,
             key_tenors: tuple[float, ...] = KEY_TENORS) -> dict[float, float]:
    """Currency P&L per +1bp triangular bump at each key tenor (central ±1bp)."""
    s = _pinned(swap, curve)
    out = {}
    for k in key_tenors:
        up = swap_pv(s, curve.key_rate_shifted(k, 1.0, key_tenors=key_tenors))
        dn = swap_pv(s, curve.key_rate_shifted(k, -1.0, key_tenors=key_tenors))
        out[float(k)] = (up - dn) / 2.0
    return out


@dataclass(frozen=True)
class SwapReport:
    swap: Swap
    par_rate: float
    pv: float
    dv01: float
    krd: dict[float, float]
    annuity: float
    carry_1y: float                   # first coupon period's net accrual (1y for freq=1)
    rolldown_1y: float                # PV of the swap aged one year on today's curve, minus PV
    fwd_rates: dict[str, float]       # par forward swap rates: 1y1y, 2y1y, 5y5y, 10y10y
    note: str = ""


def _aged(swap: Swap, years: float) -> Swap | None:
    """The same swap seen `years` later: start moves back, then tenor shortens.
    None once it has matured."""
    start, tenor = swap.start - years, swap.tenor
    if start < 0:
        tenor, start = tenor + start, 0.0
    if tenor <= 1e-12:
        return None
    return replace(swap, start=start, tenor=tenor)


def analyze_swap(swap: Swap, curve: YieldCurve) -> SwapReport:
    """Par rate, PV, DV01/KRD, carry and roll-down, and the forward-swap grid.
    carry_1y = (K − first-period forward)·N/freq for a receiver (sign flipped for
    a payer): the net coupon the position accrues over its first period if
    the curve is realised, one year for freq=1. rolldown_1y re-prices the swap
    aged one year on the same curve (a 10y becomes a 9y at the old K) minus
    today's PV; it excludes the coupons paid in between (that is carry)."""
    s = _pinned(swap, curve)
    k = float(s.fixed_rate)
    period = 1.0 / swap.freq
    first_fwd = curve.fwd(swap.start, swap.start + min(period, swap.tenor))
    carry = (k - first_fwd) * swap.notional * period
    if swap.pay_fixed:
        carry = -carry
    pv = swap_pv(s, curve)
    aged = _aged(s, 1.0)
    rolldown = (swap_pv(aged, curve) if aged is not None else 0.0) - pv
    fwds = {name: par_swap_rate(curve, t, freq=swap.freq, start=e) for name, e, t in _FWD_GRID}
    note = (f"{s.label} K={k:.4%}, {curve.method} curve {curve.date or 'undated'} "
            f"({curve.source}); single-curve, ACT/365F, DV01 central +/-1bp.")
    return SwapReport(swap=swap, par_rate=par_swap_rate(curve, swap.tenor, freq=swap.freq,
                                                         start=swap.start),
                      pv=pv, dv01=swap_dv01(s, curve), krd=swap_krd(s, curve),
                      annuity=annuity(curve, swap.tenor, swap.freq, swap.start),
                      carry_1y=carry, rolldown_1y=rolldown, fwd_rates=fwds, note=note)


# --------------------------------------------------------------------------- #
# Options on a forward rate: Black-76 and Bachelier
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class OptionValue:
    price: float                      # per unit notional and unit annuity
    delta: float                      # dP/dF
    gamma: float                      # d2P/dF2
    vega: float                       # dP/dvol per 1.00 of vol (Black) or nvol (Bachelier)
    theta: float                      # -dP/dT per year at fixed df
    d1: float
    d2: float


def _check(F: float, K: float, T: float, vol: float, df: float) -> None:
    if T < 0 or vol < 0 or df <= 0:
        raise ValueError(f"Need T >= 0, vol >= 0, df > 0; got T={T}, vol={vol}, df={df}.")
    if not all(math.isfinite(x) for x in (F, K, T, vol, df)):
        raise ValueError("Option inputs must be finite.")


def _intrinsic(F: float, K: float, df: float, call: bool) -> OptionValue:
    itm = F > K if call else F < K
    sign = 1.0 if call else -1.0
    price = df * max(sign * (F - K), 0.0)
    return OptionValue(price, df * sign if itm else 0.0, 0.0, 0.0, 0.0,
                       math.inf * sign if F != K else 0.0, math.inf * sign if F != K else 0.0)


def black76(F: float, K: float, T: float, vol: float, df: float = 1.0,
            call: bool = True) -> OptionValue:
    """Black-76 on a forward: df·(F·N(d1) − K·N(d2)). Greeks with respect to F;
    vega per 1.00 of vol; theta = −∂P/∂T at fixed df. T·vol² = 0 → intrinsic."""
    _check(F, K, T, vol, df)
    if F <= 0 or K <= 0:
        raise ValueError(f"Black-76 needs F > 0 and K > 0 (got F={F}, K={K}); use bachelier.")
    sd = vol * math.sqrt(T)
    if sd < 1e-12:
        return _intrinsic(F, K, df, call)
    d1 = (math.log(F / K) + 0.5 * sd * sd) / sd
    d2 = d1 - sd
    pdf = _npdf(d1)
    if call:
        price = df * (F * _ncdf(d1) - K * _ncdf(d2))
        delta = df * _ncdf(d1)
    else:
        price = df * (K * _ncdf(-d2) - F * _ncdf(-d1))
        delta = -df * _ncdf(-d1)
    gamma = df * pdf / (F * sd)
    vega = df * F * pdf * math.sqrt(T)
    theta = -df * F * pdf * vol / (2.0 * math.sqrt(T))
    return OptionValue(price, delta, gamma, vega, theta, d1, d2)


def bachelier(F: float, K: float, T: float, nvol: float, df: float = 1.0,
              call: bool = True) -> OptionValue:
    """Normal model: df·[(F − K)·N(d) + nvol·√T·φ(d)], d = (F − K)/(nvol·√T).
    nvol in decimal rate units (0.0080 = 80bp/yr); vega per 1.00 of nvol.
    Handles negative F/K and T → 0 (intrinsic)."""
    _check(F, K, T, nvol, df)
    sd = nvol * math.sqrt(T)
    if sd < 1e-12:
        return _intrinsic(F, K, df, call)
    d = (F - K) / sd
    pdf = _npdf(d)
    if call:
        price = df * ((F - K) * _ncdf(d) + sd * pdf)
        delta = df * _ncdf(d)
    else:
        price = df * ((K - F) * _ncdf(-d) + sd * pdf)
        delta = -df * _ncdf(-d)
    gamma = df * pdf / sd
    vega = df * math.sqrt(T) * pdf
    theta = -df * nvol * pdf / (2.0 * math.sqrt(T))
    return OptionValue(price, delta, gamma, vega, theta, d, d)


def _invert(fn, price: float, F: float, K: float, T: float, df: float, call: bool,
            lo: float, hi: float, label: str) -> float:
    if T <= 0:
        raise FICCError(f"Cannot imply a {label} vol at T={T}.")
    intrinsic = df * max((F - K) if call else (K - F), 0.0)
    if price <= intrinsic + 1e-14:
        raise FICCError(f"Price {price:.6g} is at or below intrinsic {intrinsic:.6g}; "
                        f"no {label} vol reproduces it.")
    if price > fn(F, K, T, hi, df, call).price:
        raise FICCError(f"Price {price:.6g} exceeds the {label}-model price at vol {hi}; "
                        f"outside no-arbitrage bounds.")
    return float(brentq(lambda v: fn(F, K, T, v, df, call).price - price, lo, hi,
                        xtol=1e-12, rtol=1e-12, maxiter=200))


def implied_black_vol(price: float, F: float, K: float, T: float, df: float = 1.0,
                      call: bool = True) -> float:
    """brentq on [1e-4, 5]; FICCError when the price sits outside no-arb bounds."""
    if F <= 0 or K <= 0:
        raise FICCError(f"Black vol undefined for F={F}, K={K}.")
    return _invert(black76, price, F, K, T, df, call, 1e-4, 5.0, "Black")


def implied_normal_vol(price: float, F: float, K: float, T: float, df: float = 1.0,
                       call: bool = True) -> float:
    """brentq on [1e-6, 0.5] (0.5 = 5000bp/yr)."""
    return _invert(bachelier, price, F, K, T, df, call, 1e-6, 0.5, "normal")


def normal_from_black(F: float, K: float, T: float, black_vol: float) -> float:
    """The normal vol that reproduces the Black-76 price (price match, df=1)."""
    return implied_normal_vol(black76(F, K, T, black_vol).price, F, K, T)


def black_from_normal(F: float, K: float, T: float, nvol: float) -> float:
    """The Black vol that reproduces the Bachelier price (price match, df=1)."""
    return implied_black_vol(bachelier(F, K, T, nvol).price, F, K, T)


# --------------------------------------------------------------------------- #
# Swaptions and caps/floors
# --------------------------------------------------------------------------- #
_MODELS = ("bachelier", "black")


def _option(model: str, F: float, K: float, T: float, vol: float, call: bool) -> OptionValue:
    if model not in _MODELS:
        raise FICCError(f"Unknown option model {model!r}; use one of {_MODELS}.")
    return (bachelier if model == "bachelier" else black76)(F, K, T, vol, 1.0, call)


@dataclass(frozen=True)
class Swaption:
    expiry: float                     # years to option expiry = swap start
    tenor: float                      # underlying swap length in years
    strike: float | None = None       # None -> ATM (the forward swap rate)
    payer: bool = True                # payer swaption = call on the swap rate
    notional: float = 1_000_000.0
    freq: int = 1

    def __post_init__(self) -> None:
        if self.expiry <= 0 or self.tenor <= 0 or self.notional <= 0 or self.freq < 1:
            raise ValueError("Swaption needs expiry > 0, tenor > 0, notional > 0, freq >= 1.")


@dataclass(frozen=True)
class SwaptionReport:
    swaption: Swaption
    forward: float
    strike: float
    annuity: float                    # discounted, per unit notional
    model: str
    vol: float                        # as passed: normal vol (decimal) or Black vol
    premium: float                    # currency
    premium_bp: float                 # premium / notional in bp
    delta: float                      # currency per +1bp move in the forward
    gamma: float                      # currency per bp^2
    vega: float                       # currency per unit in `vega_unit`
    vega_unit: str
    theta_1d: float                   # currency per calendar day
    other_model_vol: float            # implied vol in the other model (nan if undefined)
    note: str = ""


def price_swaption(swaption: Swaption, curve: YieldCurve, *, vol: float,
                   model: str = "bachelier") -> SwaptionReport:
    """Premium = N·annuity·option(F, K, expiry); annuity is discounted to today.
    Bachelier vega is per 1bp of normal vol, Black vega per 1 vol-point (0.01)."""
    F = par_swap_rate(curve, swaption.tenor, freq=swaption.freq, start=swaption.expiry)
    K = F if swaption.strike is None else float(swaption.strike)
    A = annuity(curve, swaption.tenor, swaption.freq, swaption.expiry)
    T = swaption.expiry
    opt = _option(model, F, K, T, vol, swaption.payer)
    scale = swaption.notional * A
    note = f"{'payer' if swaption.payer else 'receiver'} {model}"
    if model == "bachelier":
        vega, unit = opt.vega * scale * BP, "per 1bp normal vol"
        if F > 0 and K > 0:
            other = black_from_normal(F, K, T, vol)
        else:
            other, note = math.nan, note + "; Black vol undefined (non-positive forward)"
    else:
        vega, unit = opt.vega * scale * 0.01, "per 1 vol-pt Black vol"
        other = normal_from_black(F, K, T, vol)
    return SwaptionReport(swaption=swaption, forward=F, strike=K, annuity=A, model=model,
                          vol=vol, premium=opt.price * scale,
                          premium_bp=opt.price * A / BP, delta=opt.delta * scale * BP,
                          gamma=opt.gamma * scale * BP * BP, vega=vega, vega_unit=unit,
                          theta_1d=opt.theta * scale / 365.0, other_model_vol=other,
                          note=note + "; single-curve, annuity discounted to today.")


@dataclass(frozen=True)
class CapFloorReport:
    strike: float
    premium: float                    # currency
    premium_bp: float                 # premium / notional in bp
    caplets: tuple[tuple[float, float, float, float], ...]   # (t_start, t_end, forward, premium)
    atm_strike: float                 # par swap rate over the period
    model: str
    vol: float
    notional: float
    cap: bool = True
    note: str = ""


def price_cap_floor(curve: YieldCurve, tenor: float, strike: float | None, *, vol: float,
                    model: str = "bachelier", freq: int = 4, cap: bool = True,
                    notional: float = 1_000_000.0, start: float = 0.0) -> CapFloorReport:
    """Sum of caplets (floorlets) on the simple forward of each period, each an
    option expiring at the period start, paid at the period end:
    N·τ·DF(t_end)·option(fwd, K, t_start). strike=None → ATM = par swap rate
    over [start, start + tenor]. Caplets whose rate is already fixed
    (t_start = 0) are dropped."""
    if tenor <= 0 or start < 0 or notional <= 0 or freq < 1:
        raise ValueError("Need tenor > 0, start >= 0, notional > 0, freq >= 1.")
    atm = par_swap_rate(curve, tenor, freq=freq, start=start)
    K = atm if strike is None else float(strike)
    ends = coupon_times(start + tenor, freq, start)
    starts = [start] + [float(t) for t in ends[:-1]]
    rows = []
    for t0, t1 in zip(starts, ends):
        if t0 <= 1e-12:
            continue
        fwd = curve.fwd(t0, t1)
        prem = notional * (t1 - t0) * curve.df(t1) * _option(model, fwd, K, t0, vol, cap).price
        rows.append((float(t0), float(t1), float(fwd), float(prem)))
    total = sum(r[3] for r in rows)
    return CapFloorReport(strike=K, premium=total, premium_bp=total / notional / BP,
                          caplets=tuple(rows), atm_strike=atm, model=model, vol=vol,
                          notional=notional, cap=cap,
                          note=f"{'cap' if cap else 'floor'} {model}, {len(rows)} "
                               f"{'caplets' if cap else 'floorlets'}"
                               + ("; first period dropped (rate fixed)" if start <= 1e-12
                                  else "") + "; single-curve, no convexity adjustment.")


def atm_straddle(curve: YieldCurve, expiry: float, tenor: float, *, vol: float,
                 model: str = "bachelier", notional: float = 1_000_000.0) -> float:
    """Premium of an ATM payer plus an ATM receiver swaption (currency)."""
    total = 0.0
    for payer in (True, False):
        sw = Swaption(expiry=expiry, tenor=tenor, payer=payer, notional=notional)
        total += price_swaption(sw, curve, vol=vol, model=model).premium
    return total


# --------------------------------------------------------------------------- #
# Self-check
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    from core.ficc.common import UST_TENORS
    from core.ficc.curves import bootstrap_par_curve, flat_curve

    par = [0.052, 0.051, 0.050, 0.047, 0.044, 0.043, 0.042, 0.043, 0.044, 0.047, 0.046]
    c = bootstrap_par_curve(UST_TENORS, par, date="2026-09-04", source="TEST")

    # At-par swap: PV 0; payer DV01 > 0, receiver the mirror; KRD sums to DV01.
    payer = Swap(tenor=10.0)
    assert abs(swap_pv(payer, c)) < 1e-6
    rep = analyze_swap(payer, c)
    assert rep.dv01 > 0 and abs(rep.pv) < 1e-6
    recv = analyze_swap(Swap(tenor=10.0, pay_fixed=False), c)
    assert abs(recv.dv01 + rep.dv01) < 1e-6
    assert abs(sum(rep.krd.values()) - rep.dv01) < 0.01 * rep.dv01, (sum(rep.krd.values()),
                                                                       rep.dv01)
    assert set(rep.fwd_rates) == {"1y1y", "2y1y", "5y5y", "10y10y"}
    assert 500 < rep.dv01 < 1000, rep.dv01       # ~ annuity(8y) * 1e6 * 1bp = ~800
    # Off-market payer: PV = -(K - par)·A·N.
    off = Swap(tenor=5.0, fixed_rate=rep.par_rate + 0.01)
    a5 = annuity(c, 5.0)
    assert abs(swap_pv(off, c) + 1e6 * (off.fixed_rate - par_swap_rate(c, 5.0)) * a5) < 1e-6
    # Forward swap 5y5y: par rate equals fwd-implied; aged swap shortens correctly.
    f55 = par_swap_rate(c, 5.0, start=5.0)
    assert abs(f55 - rep.fwd_rates["5y5y"]) < 1e-14
    assert _aged(Swap(tenor=5.0, start=0.5), 1.0) == Swap(tenor=4.5, start=0.0)
    assert _aged(Swap(tenor=1.0), 1.0) is None
    # Receiver in an inverted front end: carry sign follows K vs first forward.
    assert abs(recv.carry_1y - (recv.par_rate - c.fwd(0.0, 1.0)) * 1e6) < 1e-6

    # Options: Black vs Bachelier ATM agree when nvol = vol·F; parity; Greeks.
    F, K, T, vol = 0.04, 0.04, 2.0, 0.25
    b = black76(F, K, T, vol)
    n = bachelier(F, K, T, vol * F)
    assert abs(b.price / n.price - 1.0) < 0.02, (b.price, n.price)
    assert abs(b.price - (black76(F, K, T, vol, call=False).price + (F - K))) < 1e-14
    assert abs(bachelier(F, 0.03, T, 0.008).price - bachelier(F, 0.03, T, 0.008, call=False).price
               - (F - 0.03)) < 1e-14
    assert 0 < b.delta < 1 and b.gamma > 0 and b.vega > 0 and b.theta < 0
    assert bachelier(-0.001, 0.0, 1.0, 0.005).price > 0          # negative rates are fine
    assert black76(F, K, 0.0, vol).price == 0.0
    assert abs(bachelier(0.05, 0.04, 0.0, 0.01).price - 0.01) < 1e-14
    # Numerical Greeks agree with the analytic ones.
    h = 1e-6
    assert abs((black76(F + h, K, T, vol).price - black76(F - h, K, T, vol).price) / (2 * h)
               - b.delta) < 1e-6
    assert abs((bachelier(F, K, T, 0.008 + h).price - bachelier(F, K, T, 0.008 - h).price)
               / (2 * h) - bachelier(F, K, T, 0.008).vega) < 1e-6
    # Implied vols round-trip; conversions are inverse; no-arb violations raise.
    assert abs(implied_black_vol(b.price, F, K, T) - vol) < 1e-6
    assert abs(implied_normal_vol(n.price, F, K, T) - vol * F) < 1e-6
    assert abs(black_from_normal(F, 0.045, T, normal_from_black(F, 0.045, T, 0.3)) - 0.3) < 1e-6
    for bad in (0.0, F * 2):
        try:
            implied_black_vol(bad, F, K, T)
            raise AssertionError("expected FICCError")
        except FICCError:
            pass

    # Swaptions: put-call parity, ATM straddle = payer + receiver, unit checks.
    sp = price_swaption(Swaption(expiry=1.0, tenor=5.0, strike=0.05), c, vol=0.008)
    sr = price_swaption(Swaption(expiry=1.0, tenor=5.0, strike=0.05, payer=False), c, vol=0.008)
    assert abs((sp.premium - sr.premium) - sp.annuity * (sp.forward - 0.05) * 1e6) < 1e-6
    assert sp.vega_unit == "per 1bp normal vol" and sp.delta > 0 > sr.delta and sp.theta_1d < 0
    assert abs(sp.premium_bp - sp.premium / 1e6 / BP) < 1e-9
    assert 0 < sp.other_model_vol < 5
    sb = price_swaption(Swaption(expiry=1.0, tenor=5.0), c, vol=0.30, model="black")
    assert sb.strike == sb.forward and sb.vega_unit == "per 1 vol-pt Black vol"
    assert abs(price_swaption(Swaption(expiry=1.0, tenor=5.0), c, vol=sb.other_model_vol).premium
               - sb.premium) < 1e-6
    two = atm_straddle(c, 1.0, 5.0, vol=0.008, notional=1e6)
    atm_p = price_swaption(Swaption(expiry=1.0, tenor=5.0), c, vol=0.008).premium
    assert abs(two - 2 * atm_p) < 1e-6 * two            # ATM normal: payer == receiver
    try:
        price_swaption(Swaption(expiry=1.0, tenor=5.0), c, vol=0.3, model="sabr")
        raise AssertionError("expected FICCError")
    except FICCError:
        pass

    # Caps: sum of caplets, ATM strike = par swap rate, cap − floor = swap value.
    cap = price_cap_floor(c, 5.0, None, vol=0.008)
    assert abs(cap.premium - sum(r[3] for r in cap.caplets)) < 1e-9
    assert len(cap.caplets) == 19 and abs(cap.strike - par_swap_rate(c, 5.0, freq=4)) < 1e-14
    flo = price_cap_floor(c, 5.0, cap.strike, vol=0.008, cap=False)
    swap_val = sum((r[1] - r[0]) * c.df(r[1]) * (r[2] - cap.strike) * 1e6 for r in cap.caplets)
    assert abs((cap.premium - flo.premium) - swap_val) < 1e-6
    black_cap = price_cap_floor(flat_curve(0.04), 2.0, 0.05, vol=0.3, model="black")
    assert black_cap.premium > 0 and black_cap.premium_bp > 0
    print("ok")
