"""FX: forwards and carry, Garman-Kohlhagen vanillas, delta-quoted smiles, SABR,
and a no-lookahead G10+KRW carry backtest.

Quoting convention throughout: a pair "EURUSD" is S units of the QUOTE ccy
(USD, "dom") per one unit of the BASE ccy (EUR, "for"). Rates are decimals
p.a.; vols are decimals (0.10 = 10%); T is years.

Simplifications, on purpose:

  * ACT/365F simple year fractions; no holiday calendars, no spot lag.
  * Forwards are pure covered-interest-parity: F = S·exp((r_dom − r_for)·T).
    `implied_basis` is the annualised gap between a market forward and CIP.
  * Garman-Kohlhagen with flat rates and vol. Deltas are SPOT deltas, not
    premium-adjusted; `delta_fwd` is the undiscounted forward delta N(d1).
    Greeks are per one unit of base ccy, in quote ccy: `vega` per 1 vol-point
    (0.01), `gamma_1pct` = change in delta for a 1% spot move, `theta_1d` per
    calendar day (T/365), `rho_dom`/`rho_for` per 1.00 of rate (× 1e-4 per bp),
    `vanna` = dVega/dS per 1.00 vol, `volga` = dVega/dσ per 1.00 vol.
  * Smiles from ATM/RR/BF use the market approximation
    vol25c = atm + bf + rr/2, vol25p = atm + bf − rr/2 (no smile-consistent
    BF repricing); ATM is the delta-neutral straddle strike F·exp(½σ²T).
  * SABR is Hagan 2002's lognormal expansion, beta fixed (1.0 for FX).
  * Carry backtest: each currency's return vs USD is spot return + (r_ccy −
    r_usd)/252 per observation, rates taken from the last observation ON OR
    BEFORE the day they accrue. Series whose note says "monthly" (OECD period
    averages dated the 1st, published after month-end) enter with a ONE-
    OBSERVATION lag: on any day in March the February average is used. The
    backtest starts on the first date every currency has a rate; ranks use
    only data available at the rebalance date.
  * `carry_table` flags a rate as stale when its last observation is more
    than 45 days older than the spot's last observation.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from datetime import date
from typing import TYPE_CHECKING

import numpy as np
from scipy.optimize import brentq, least_squares
from scipy.stats import norm

from core.ficc.common import BP, TRADING_DAYS, FICCError

if TYPE_CHECKING:                                    # data.py owns this shape
    from core.ficc.data import Series

_DAYS_3M = 63
_STALE_DAYS = 45


# --------------------------------------------------------------------------- #
# Forwards and carry
# --------------------------------------------------------------------------- #
def forward(spot: float, r_dom: float, r_for: float, T: float) -> float:
    """CIP forward S·exp((r_dom − r_for)·T); dom = quote ccy, for = base ccy."""
    if spot <= 0 or T < 0:
        raise ValueError("spot must be positive and T >= 0.")
    return spot * math.exp((r_dom - r_for) * T)


def forward_points(spot: float, fwd: float, *, pip: float | None = None) -> float:
    """(F − S)/pip. pip defaults to 0.01 for big-figure quotes (spot > 20: JPY, KRW)
    and 0.0001 otherwise."""
    if pip is None:
        pip = 0.01 if spot > 20 else 0.0001
    if pip <= 0:
        raise ValueError("pip must be positive.")
    return (fwd - spot) / pip


def implied_basis(spot: float, fwd_market: float, r_dom: float, r_for: float,
                  T: float) -> float:
    """Annualised cross-currency basis implied by a market forward:
    ln(F/S)/T − (r_dom − r_for). Zero for a CIP forward."""
    if spot <= 0 or fwd_market <= 0 or T <= 0:
        raise ValueError("spot, forward must be positive and T > 0.")
    return math.log(fwd_market / spot) / T - (r_dom - r_for)


def carry(r_dom: float, r_for: float) -> float:
    """Carry of a long-base position, decimal p.a.: r_for − r_dom."""
    return r_for - r_dom


# --------------------------------------------------------------------------- #
# Garman-Kohlhagen
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class GKReport:
    spot: float
    strike: float
    expiry: float
    r_dom: float
    r_for: float
    vol: float
    call: bool
    forward: float
    price: float                      # quote ccy per 1 unit of base
    price_pct_spot: float             # price / spot (= premium as % of base notional)
    delta_spot: float                 # non-premium-adjusted spot delta
    delta_fwd: float                  # undiscounted forward delta, N(d1)
    gamma: float                      # dDelta/dS per 1 unit of spot
    gamma_1pct: float                 # dDelta for a 1% spot move
    vega: float                       # per 1 vol-point (0.01)
    theta_1d: float                   # per calendar day
    rho_dom: float                    # per 1.00 of r_dom
    rho_for: float                    # per 1.00 of r_for
    d1: float
    d2: float
    vanna: float                      # dVega/dS, vega per 1.00 vol
    volga: float                      # dVega/dσ, vega per 1.00 vol


def _check_gk(S: float, K: float, T: float, vol: float) -> None:
    if S <= 0 or K <= 0:
        raise ValueError("spot and strike must be positive.")
    if T <= 0:
        raise ValueError("T must be positive.")
    if vol <= 0:
        raise ValueError("vol must be positive.")


def garman_kohlhagen(S: float, K: float, T: float, r_dom: float, r_for: float, vol: float,
                     call: bool = True) -> GKReport:
    _check_gk(S, K, T, vol)
    sq = vol * math.sqrt(T)
    d1 = (math.log(S / K) + (r_dom - r_for + 0.5 * vol * vol) * T) / sq
    d2 = d1 - sq
    dfd, dff = math.exp(-r_dom * T), math.exp(-r_for * T)
    pdf = norm.pdf(d1)
    sgn = 1.0 if call else -1.0
    nd1, nd2 = norm.cdf(sgn * d1), norm.cdf(sgn * d2)
    price = sgn * (S * dff * nd1 - K * dfd * nd2)
    vega_raw = S * dff * pdf * math.sqrt(T)
    theta = (-S * dff * pdf * vol / (2 * math.sqrt(T))
             + sgn * (r_for * S * dff * nd1 - r_dom * K * dfd * nd2))
    gamma = dff * pdf / (S * sq)
    return GKReport(
        spot=S, strike=K, expiry=T, r_dom=r_dom, r_for=r_for, vol=vol, call=call,
        forward=forward(S, r_dom, r_for, T), price=price, price_pct_spot=price / S,
        delta_spot=sgn * dff * nd1, delta_fwd=sgn * nd1, gamma=gamma,
        gamma_1pct=gamma * S * 0.01, vega=vega_raw * 0.01, theta_1d=theta / 365.0,
        rho_dom=sgn * K * T * dfd * nd2, rho_for=-sgn * S * T * dff * nd1, d1=d1, d2=d2,
        vanna=-dff * pdf * d2 / vol, volga=vega_raw * d1 * d2 / vol)


def implied_vol_gk(price: float, S: float, K: float, T: float, r_dom: float, r_for: float,
                   call: bool = True) -> float:
    """Black-Scholes implied vol by brentq on [1e-4, 5]; FICCError outside no-arb bounds."""
    _check_gk(S, K, T, 1.0)
    fwd_leg, strike_leg = S * math.exp(-r_for * T), K * math.exp(-r_dom * T)
    lo = max(fwd_leg - strike_leg, 0.0) if call else max(strike_leg - fwd_leg, 0.0)
    hi = fwd_leg if call else strike_leg
    if not lo <= price <= hi:
        raise FICCError(f"Price {price:.6g} is outside the no-arbitrage band "
                        f"[{lo:.6g}, {hi:.6g}].")
    f = lambda v: garman_kohlhagen(S, K, T, r_dom, r_for, v, call).price - price
    if f(1e-4) > 0:
        return 1e-4
    if f(5.0) < 0:
        raise FICCError("Implied vol exceeds 500%.")
    return float(brentq(f, 1e-4, 5.0, xtol=1e-12))


def strike_from_delta(delta: float, S: float, T: float, r_dom: float, r_for: float,
                      vol: float, *, call: bool = True, forward_delta: bool = False) -> float:
    """Strike for a spot delta (non-premium-adjusted); put deltas may be given with
    either sign. K = F·exp(∓N⁻¹(|δ|·e^{r_for·T})·σ√T + ½σ²T); with
    `forward_delta=True` the e^{r_for·T} factor is dropped."""
    _check_gk(S, S, T, vol)
    d = abs(delta) * (1.0 if forward_delta else math.exp(r_for * T))
    if not 0.0 < d < 1.0:
        raise ValueError(f"delta {delta} is not attainable (|δ|·e^(r_for·T) = {d:.4f}).")
    sq = vol * math.sqrt(T)
    d1 = norm.ppf(d) if call else -norm.ppf(d)
    return forward(S, r_dom, r_for, T) * math.exp(-d1 * sq + 0.5 * sq * sq)


# --------------------------------------------------------------------------- #
# Smiles
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class SmileQuote:
    expiry: float
    atm: float
    rr25: float                       # 25d call vol − 25d put vol
    bf25: float


@dataclass(frozen=True)
class SmilePoint:
    label: str                        # "25d put" | "ATM" | "25d call"
    strike: float
    vol: float
    delta: float                      # spot delta of the option at that point


def smile_from_quotes(q: SmileQuote, S: float, r_dom: float, r_for: float
                      ) -> tuple[SmilePoint, ...]:
    """(25d put, ATM, 25d call) with vol25c = atm + bf + rr/2, vol25p = atm + bf − rr/2,
    each wing struck from its own vol; ATM is the delta-neutral straddle strike."""
    T = q.expiry
    vc, vp = q.atm + q.bf25 + 0.5 * q.rr25, q.atm + q.bf25 - 0.5 * q.rr25
    if min(vc, vp, q.atm) <= 0 or T <= 0:
        raise ValueError("smile vols and expiry must be positive.")
    kp = strike_from_delta(0.25, S, T, r_dom, r_for, vp, call=False)
    kc = strike_from_delta(0.25, S, T, r_dom, r_for, vc, call=True)
    ka = forward(S, r_dom, r_for, T) * math.exp(0.5 * q.atm * q.atm * T)
    pts = (("25d put", kp, vp, False), ("ATM", ka, q.atm, True), ("25d call", kc, vc, True))
    return tuple(SmilePoint(lbl, k, v, garman_kohlhagen(S, k, T, r_dom, r_for, v, c).delta_spot)
                 for lbl, k, v, c in pts)


def sabr_vol(F, K, T: float, alpha: float, beta: float, rho: float, nu: float
             ) -> float | np.ndarray:
    """Hagan (2002) lognormal SABR implied vol; the z/x(z) ratio → 1 at the money."""
    if alpha <= 0 or nu < 0 or not -1.0 < rho < 1.0 or T <= 0 or not 0.0 <= beta <= 1.0:
        raise ValueError("need alpha > 0, nu >= 0, |rho| < 1, T > 0, 0 <= beta <= 1.")
    F, K = np.asarray(F, dtype=float), np.asarray(K, dtype=float)
    if np.any(F <= 0) or np.any(K <= 0):
        raise ValueError("forward and strikes must be positive.")
    ob = 1.0 - beta
    fk = (F * K) ** (ob / 2.0)
    lfk = np.log(F / K)
    z = nu / alpha * fk * lfk
    with np.errstate(divide="ignore", invalid="ignore"):
        x = np.log((np.sqrt(1.0 - 2.0 * rho * z + z * z) + z - rho) / (1.0 - rho))
        zx = np.where(np.abs(z) < 1e-7, 1.0, z / x)
    denom = fk * (1.0 + ob**2 / 24.0 * lfk**2 + ob**4 / 1920.0 * lfk**4)
    corr = 1.0 + T * (ob**2 / 24.0 * alpha**2 / fk**2 + rho * beta * nu * alpha / (4.0 * fk)
                      + (2.0 - 3.0 * rho**2) / 24.0 * nu**2)
    v = alpha / denom * zx * corr
    return float(v) if v.ndim == 0 else v


@dataclass(frozen=True)
class SABRFit:
    alpha: float
    beta: float
    rho: float
    nu: float
    rmse: float                       # in vol units
    converged: bool


def calibrate_sabr(F: float, T: float, strikes, vols, *, beta: float = 1.0) -> SABRFit:
    """least_squares over (alpha, rho, nu) with beta fixed (1.0 FX, 0.5 rates);
    six deterministic starts (rho0 ∈ {−.3, 0, .3} × nu0 ∈ {.3, 1}), best kept."""
    K, v = np.asarray(strikes, dtype=float), np.asarray(vols, dtype=float)
    if K.size < 3 or K.size != v.size:
        raise FICCError(f"Need >= 3 strike/vol pairs of equal length, got {K.size}/{v.size}.")
    if F <= 0 or T <= 0 or np.any(K <= 0) or np.any(v <= 0):
        raise ValueError("forward, expiry, strikes and vols must be positive.")

    def resid(p):
        return sabr_vol(F, K, T, p[0], beta, p[1], p[2]) - v

    a0 = float(v[np.argmin(np.abs(K - F))]) * F ** (1.0 - beta)
    best = None
    for rho0 in (-0.3, 0.0, 0.3):
        for nu0 in (0.3, 1.0):
            res = least_squares(resid, x0=[a0, rho0, nu0], method="trf",
                                bounds=([1e-4, -0.999, 1e-4], [5.0, 0.999, 5.0]),
                                x_scale=[max(a0, 1e-3), 1.0, 1.0])
            if best is None or res.cost < best.cost:
                best = res
    a, r, n = (float(x) for x in best.x)
    rmse = float(math.sqrt(np.mean(best.fun**2)))
    return SABRFit(alpha=a, beta=beta, rho=r, nu=n, rmse=rmse, converged=bool(best.success))


def smile_curve(fit: SABRFit, F: float, T: float, strikes: np.ndarray) -> np.ndarray:
    return np.asarray(sabr_vol(F, strikes, T, fit.alpha, fit.beta, fit.rho, fit.nu), dtype=float)


# --------------------------------------------------------------------------- #
# Carry — table and backtest
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class CarryRow:
    pair: str
    ccy: str                          # the non-USD currency
    spot: float                       # as quoted
    rate_ccy: float
    rate_usd: float
    carry: float                      # r_ccy − r_usd, p.a., for long ccy vs USD
    vol_3m: float                     # realised, annualised, of the ccy-in-USD price
    carry_to_vol: float
    mom_3m: float                     # spot return of holding the ccy for 3m
    score: float                      # carry/vol + mom/vol
    rate_date: str = ""               # last_date of the ccy's rate series
    rate_stale: bool = False          # ccy or USD rate > 45 days older than the spot


@dataclass(frozen=True)
class CarryBacktest:
    dates: tuple[str, ...]
    equity: np.ndarray = field(repr=False)
    bench_equity: np.ndarray = field(repr=False)     # equal-weight long every ccy
    positions: tuple[tuple[str, tuple[str, ...], tuple[str, ...]], ...]
    ann_return: float
    ann_vol: float
    sharpe: float
    max_drawdown: float
    n_rebalances: int
    top_n: int
    cost_bps: float
    note: str = ""


def _pair(text: str) -> str:
    p = re.sub(r"[^A-Za-z]", "", text or "").upper()
    p = p[:-1] if p.endswith("X") and len(p) == 7 else p
    if len(p) != 6:
        raise FICCError(f"Cannot read FX pair {text!r}; use forms like EURUSD or USD/KRW.")
    return p


def _leg(pair: str, s: Series) -> tuple[str, bool, np.ndarray]:
    """(non-USD ccy, inverted?, price of one unit of that ccy in USD)."""
    p = _pair(pair)
    px = np.asarray(s.values, dtype=float)
    if np.any(px <= 0):
        raise FICCError(f"{p} spot has non-positive values.")
    if p[:3] == "USD":
        return p[3:], True, 1.0 / px
    if p[3:] == "USD":
        return p[:3], False, px
    raise FICCError(f"{p} is not a USD pair; the carry universe is quoted vs USD.")


def _rate(rates: dict[str, Series], ccy: str) -> Series:
    try:
        return rates[ccy]
    except KeyError:
        raise FICCError(f"No rate series for {ccy}.") from None


def _stale(rate_date: str, spot_date: str) -> bool:
    return (date.fromisoformat(spot_date) - date.fromisoformat(rate_date)).days > _STALE_DAYS


def carry_table(spots: dict[str, Series], rates: dict[str, Series]) -> list[CarryRow]:
    """One row per pair vs USD, sorted by score. Inverted quotes (USDJPY) are
    flipped so `carry`/`mom_3m` always describe being LONG the non-USD ccy.
    `rate_stale` is True when the ccy's or USD's rate is > 45 days older than spot."""
    usd = _rate(rates, "USD")
    r_usd = float(usd.last)
    rows = []
    for pair, s in spots.items():
        ccy, _, px = _leg(pair, s)
        rs = _rate(rates, ccy)
        if px.size < 22:
            raise FICCError(f"{_pair(pair)} needs >= 22 observations, got {px.size}.")
        m = min(_DAYS_3M, px.size - 1)
        r = np.diff(np.log(px[-m - 1:]))
        vol = float(np.std(r, ddof=1)) * math.sqrt(TRADING_DAYS)
        mom = float(px[-1] / px[-m - 1] - 1.0)
        cy = float(rs.last) - r_usd
        c2v = cy / vol if vol > 0 else 0.0
        rows.append(CarryRow(pair=_pair(pair), ccy=ccy, spot=float(s.last), rate_ccy=cy + r_usd,
                             rate_usd=r_usd, carry=cy, vol_3m=vol, carry_to_vol=c2v,
                             mom_3m=mom, score=c2v + (mom / vol if vol > 0 else 0.0),
                             rate_date=rs.last_date,
                             rate_stale=_stale(rs.last_date, s.last_date)
                             or _stale(usd.last_date, s.last_date)))
    return sorted(rows, key=lambda x: x.score, reverse=True)


def _ffill_rates(s: Series, dates: list[str]) -> np.ndarray:
    """Last observation on or before each date; NaN before the first one. A series
    whose note says "monthly" is a period average dated the 1st and published
    after month-end, so it is lagged one observation."""
    rd = np.asarray(s.dates)
    lag = 1 if "monthly" in s.note.lower() else 0
    idx = np.searchsorted(rd, np.asarray(dates), side="right") - 1 - lag
    out = np.asarray(s.values, dtype=float)[np.clip(idx, 0, None)]
    return np.where(idx < 0, np.nan, out)


def carry_backtest(spots: dict[str, Series], rates: dict[str, Series], *, top_n: int = 3,
                   cost_bps: float = 5.0, rebalance_days: int = 21) -> CarryBacktest:
    """Every `rebalance_days` observations rank currencies by r_ccy − r_usd known
    that day, go long the top_n and short the bottom_n at ±1/top_n each (each
    leg = 100% of equity), and earn spot return + rate differential/252 from the
    next observation on. Costs = turnover × cost_bps at each rebalance.
    Benchmark: equal-weight long every currency, no costs. No lookahead."""
    if top_n < 1 or rebalance_days < 1 or cost_bps < 0:
        raise ValueError("top_n, rebalance_days must be >= 1 and cost_bps >= 0.")
    legs = {pair: _leg(pair, s) for pair, s in spots.items()}
    if not legs:
        raise FICCError("No spot series given.")
    common = set.intersection(*(set(s.dates) for s in spots.values()))
    dates = sorted(common)
    if len(dates) < rebalance_days + 2:
        raise FICCError(f"Only {len(dates)} overlapping dates; need > {rebalance_days + 1}.")
    ccys = [legs[p][0] for p in spots]
    P = np.column_stack([np.asarray(legs[p][2], dtype=float)[
        [i for i, d in enumerate(spots[p].dates) if d in common]] for p in spots])
    R = np.column_stack([_ffill_rates(_rate(rates, c), dates) for c in ccys])
    r_usd = _ffill_rates(_rate(rates, "USD"), dates)
    ok = np.isfinite(R).all(axis=1) & np.isfinite(r_usd)
    if not ok.any() or int(np.argmax(ok)) >= len(dates) - 1:
        raise FICCError("Rates are not known on any date with a following spot observation.")
    i0 = int(np.argmax(ok))
    n_ccy = len(ccys)
    k = min(top_n, n_ccy // 2)
    if k < 1:
        raise FICCError(f"Need >= 2 currencies to go long/short, got {n_ccy}.")
    w = np.zeros(n_ccy)
    eq, bench = [1.0], [1.0]
    positions = []
    for i in range(i0, len(dates) - 1):
        if (i - i0) % rebalance_days == 0:
            order = np.argsort(-(R[i] - r_usd[i]), kind="stable")
            new_w = np.zeros(n_ccy)
            new_w[order[:k]], new_w[order[-k:]] = 1.0 / k, -1.0 / k
            eq[-1] *= 1.0 - float(np.abs(new_w - w).sum()) * cost_bps * BP
            w = new_w
            positions.append((dates[i], tuple(ccys[j] for j in order[:k]),
                              tuple(ccys[j] for j in order[-k:])))
        ret = P[i + 1] / P[i] - 1.0 + (R[i] - r_usd[i]) / TRADING_DAYS
        eq.append(eq[-1] * (1.0 + float(w @ ret)))
        bench.append(bench[-1] * (1.0 + float(ret.mean())))
    equity, bench_eq = np.asarray(eq), np.asarray(bench)
    equity[0] = 1.0                                   # the first cost shows from day 1 on
    daily = np.diff(equity) / equity[:-1]
    n = daily.size
    ann_ret = float(equity[-1] ** (TRADING_DAYS / n) - 1.0) if equity[-1] > 0 else -1.0
    ann_vol = float(np.std(daily, ddof=1)) * math.sqrt(TRADING_DAYS) if n > 1 else 0.0
    mdd = float(np.min(equity / np.maximum.accumulate(equity) - 1.0))
    note = (f"{n_ccy} ccys vs USD, long/short {k} each at ±1/{k}; {n} observations from "
            f"{dates[i0]} (first date every rate is known); rates ffilled by date, monthly "
            f"averages with a one-observation lag; accrual 1/{TRADING_DAYS} per observation; "
            f"no lookahead.")
    if k < top_n:
        note += f" top_n clipped from {top_n} to {k}."
    return CarryBacktest(dates=tuple(dates[i0:]), equity=equity, bench_equity=bench_eq,
                         positions=tuple(positions), ann_return=ann_ret, ann_vol=ann_vol,
                         sharpe=ann_ret / ann_vol if ann_vol > 0 else 0.0, max_drawdown=mdd,
                         n_rebalances=len(positions), top_n=k, cost_bps=cost_bps, note=note)


# --------------------------------------------------------------------------- #
# Self-check
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    S, K, T, rd, rf, v = 1.10, 1.12, 0.5, 0.045, 0.03, 0.09
    F = forward(S, rd, rf, T)
    assert abs(implied_basis(S, F, rd, rf, T)) < 1e-12
    assert abs(forward_points(S, F) - (F - S) / 1e-4) < 1e-9
    assert abs(forward_points(150.0, 149.0) + 100.0) < 1e-9
    assert carry(rd, rf) == rf - rd

    c, p = garman_kohlhagen(S, K, T, rd, rf, v, True), garman_kohlhagen(S, K, T, rd, rf, v, False)
    assert abs((c.price - p.price) - (S * math.exp(-rf * T) - K * math.exp(-rd * T))) < 1e-12
    assert 0 < c.delta_spot < 1 and -1 < p.delta_spot < 0 and c.gamma > 0 and c.vega > 0
    assert abs(garman_kohlhagen(S, 0.5, T, rd, rf, v).delta_spot - math.exp(-rf * T)) < 1e-6
    assert abs(implied_vol_gk(c.price, S, K, T, rd, rf) - v) < 1e-8
    assert abs(implied_vol_gk(p.price, S, K, T, rd, rf, call=False) - v) < 1e-8
    h = 1e-5                                          # greeks vs finite differences
    up, dn = garman_kohlhagen(S + h, K, T, rd, rf, v), garman_kohlhagen(S - h, K, T, rd, rf, v)
    assert abs((up.price - dn.price) / (2 * h) - c.delta_spot) < 1e-6
    assert abs((up.delta_spot - dn.delta_spot) / (2 * h) - c.gamma) < 1e-5
    vu = garman_kohlhagen(S, K, T, rd, rf, v + h).price
    assert abs((vu - c.price) / h * 0.01 - c.vega) < 1e-6
    tu = garman_kohlhagen(S, K, T - 1 / 365, rd, rf, v).price
    assert abs((tu - c.price) - c.theta_1d) < 1e-5
    ru = garman_kohlhagen(S, K, T, rd + h, rf, v).price
    assert abs((ru - c.price) / h - c.rho_dom) < 1e-5
    for call, sign in ((True, 1.0), (False, -1.0)):
        k25 = strike_from_delta(0.25, S, T, rd, rf, v, call=call)
        assert abs(garman_kohlhagen(S, k25, T, rd, rf, v, call).delta_spot - sign * 0.25) < 1e-10
    kf = strike_from_delta(0.25, S, T, rd, rf, v, forward_delta=True)
    assert abs(garman_kohlhagen(S, kf, T, rd, rf, v).delta_fwd - 0.25) < 1e-10

    pts = smile_from_quotes(SmileQuote(T, 0.09, 0.01, 0.003), S, rd, rf)
    assert [x.label for x in pts] == ["25d put", "ATM", "25d call"]
    assert pts[0].strike < pts[1].strike < pts[2].strike and pts[2].vol > pts[0].vol
    assert abs(pts[0].delta + 0.25) < 1e-9 and abs(pts[2].delta - 0.25) < 1e-9

    Ks = np.array([x.strike for x in pts])
    true = sabr_vol(F, Ks, T, 0.09, 1.0, -0.25, 0.8)
    atm_hagan = 0.09 * (1 + T * (-0.25 * 0.8 * 0.09 / 4 + (2 - 3 * 0.0625) / 24 * 0.64))
    assert abs(sabr_vol(F, F, T, 0.09, 1.0, -0.25, 0.8) - atm_hagan) < 1e-12
    fit = calibrate_sabr(F, T, Ks, true, beta=1.0)
    assert fit.rmse < 1e-4 and np.all(np.abs(smile_curve(fit, F, T, Ks) - true) < 1e-4)
    fit_q = calibrate_sabr(F, T, Ks, [x.vol for x in pts])
    assert fit_q.rmse < 1e-4 and fit_q.converged and fit_q.beta == 1.0

    from core.ficc.data import G10_KRW, synthetic_fx, synthetic_series
    pairs = {c: ("USD" + c if c in ("JPY", "KRW", "CAD", "CHF") else c + "USD")
             for c in G10_KRW if c != "USD"}
    spots = {p: synthetic_fx(p, days=400) for p in pairs.values()}
    rates = {c: synthetic_series(f"RATE_{c}", days=400, kind="rate") for c in G10_KRW}
    rows = carry_table(spots, rates)
    assert len(rows) == 7 and rows[0].score >= rows[-1].score
    jpy = next(r for r in rows if r.ccy == "JPY")
    assert jpy.pair == "USDJPY" and jpy.spot == spots["USDJPY"].last
    assert abs(jpy.carry - (rates["JPY"].last - rates["USD"].last)) < 1e-12
    assert abs(jpy.mom_3m - (spots["USDJPY"].values[-64] / jpy.spot - 1.0)) < 1e-12
    bt = carry_backtest(spots, rates, top_n=3, cost_bps=5.0)
    assert bt.equity[0] == 1.0 and bt.bench_equity[0] == 1.0
    assert not np.isnan(bt.equity).any() and len(bt.dates) == bt.equity.size == 400
    assert bt.n_rebalances == math.ceil(399 / 21) and bt.top_n == 3
    assert all(len(l) == 3 and len(s) == 3 and not set(l) & set(s) for _, l, s in bt.positions)
    free = carry_backtest(spots, rates, top_n=3, cost_bps=0.0)
    dear = carry_backtest(spots, rates, top_n=3, cost_bps=50.0)
    assert dear.equity[-1] < bt.equity[-1] < free.equity[-1]
    assert carry_backtest(spots, rates, top_n=3, cost_bps=5.0).equity.tolist() == bt.equity.tolist()
    monthly = {c: synthetic_series(f"M_{c}", days=19, kind="rate") for c in G10_KRW}
    late = carry_backtest(spots, monthly, cost_bps=0.0)
    assert late.dates[0] == monthly["USD"].dates[0] and late.equity.size == 19

    from datetime import timedelta
    from core.ficc.data import Series
    d0 = date(2025, 2, 20)
    days = [d0 + timedelta(i) for i in range(50)]
    ds = tuple(d.isoformat() for d in days if d.weekday() < 5)   # 2025-02-20 .. 2025-04-10
    mk = lambda id_, dts, vals, note="": Series(id_, id_, "SYNTHETIC", tuple(dts), tuple(vals),
                                                 note)
    tiny_spots = {"EURUSD": mk("EURUSD", ds, [1.1] * len(ds)),
                  "USDJPY": mk("USDJPY", ds, [150.0] * len(ds))}
    eur_m = mk("EUR", ("2025-02-01", "2025-03-01"), (0.01, 0.10), "monthly; 3m interbank")
    tiny_rates = {"USD": mk("USD", ds, [0.03] * len(ds)), "EUR": eur_m,
                  "JPY": mk("JPY", ds, [0.05] * len(ds))}
    # monthly average dated 2025-03-01 is not knowable in March: lagged one observation
    assert np.isnan(_ffill_rates(eur_m, ["2025-02-28"])[0])
    assert _ffill_rates(eur_m, ["2025-03-01", "2025-03-15"]).tolist() == [0.01, 0.01]
    assert _ffill_rates(mk("EUR", eur_m.dates, eur_m.values), ["2025-03-15"])[0] == 0.10
    tb = carry_backtest(tiny_spots, tiny_rates, cost_bps=0.0, rebalance_days=5)
    assert tb.dates[0] == "2025-03-03"                # first weekday on/after 2025-03-01
    assert all(l == ("JPY",) and s == ("EUR",) for _, l, s in tb.positions), tb.positions
    # staleness: rate's last_date 60 days before spot's last_date flips the flag
    fresh = carry_table(tiny_spots, tiny_rates)
    assert all(not r.rate_stale for r in fresh)
    assert next(r for r in fresh if r.ccy == "EUR").rate_date == "2025-03-01"
    stale_eur = dict(tiny_rates, EUR=mk("EUR", ("2025-01-10", "2025-02-09"), (0.01, 0.10)))
    flags = {r.ccy: r.rate_stale for r in carry_table(tiny_spots, stale_eur)}
    assert flags == {"EUR": True, "JPY": False}, flags
    stale_usd = dict(tiny_rates, USD=mk("USD", ("2025-02-09",), (0.03,)))
    assert all(r.rate_stale for r in carry_table(tiny_spots, stale_usd))
    print("ok")
