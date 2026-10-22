"""Equity-index derivatives: futures fair value and basis, the option board,
the implied-volatility surface, model-free variance, the risk-neutral density,
the box-spread funding rate, the hedger's P&L identity, and leveraged-ETF drag.

Conventions follow the FICC core: rates as decimals, T in years (ACT/365),
vols as decimals; the UI prints percent, vol points and basis points. Every
pricer reuses `core.ficc.swaps.black76` and its Brent inverter, so the option
board and the swaption page never disagree about a Black price.

  fair_value / implied_repo   F* = (S − D)e^{rT} (continuous) or the KRX
                              convention S(1 + r·τ/365) − D (Shreve II §5.6;
                              Mirae 2003 note for the CD-based KRX form)
  implied_forward             Cboe rule: the strike where |C − P| is smallest,
                              F = K + e^{rT}(C − P) (VIX methodology §2)
  chain_implied_vols          Black-76 inversion of OTM mids, reconciled with
                              the exchange's IV (research candidate O1)
  parity_residuals / static_arbitrage   put–call parity within the spread;
                              vertical and butterfly inequalities on mids
  fit_svi / svi_g             Gatheral (2004) raw SVI, Gatheral–Jacquier (2014)
                              butterfly condition g(k) ≥ 0
  mfiv                        Cboe strip σ² = (2/T)Σ(ΔK/K²)e^{rT}Q(K) − (1/T)(F/K₀ − 1)²
  rnd_from_svi                Breeden–Litzenberger f_Q = e^{rT} ∂²C/∂K²
  box_rate                    r = −ln(B/(K₂ − K₁))/T from a long box
  hedge_pnl_simulation        Π_T = e^{rT}V₀ − payoff + Σ hedge gains; identity
                              ½Σe^{r(T−t)}ΓS²(σ_h² − r²/Δ)Δ (the user's paper §6.7)
  letf_drag                   Avellaneda–Zhang (2010) eq. (10): the +2× fund
                              loses 1×, the −2× fund 3×, the integrated variance
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional, Sequence

import numpy as np
from scipy.optimize import least_squares
from scipy.stats import gaussian_kde

from core.ficc.common import BP, FICCError
from core.ficc.swaps import black76, implied_black_vol

TRADING_DAYS = 252


# --------------------------------------------------------------------------- #
# Futures
# --------------------------------------------------------------------------- #
def fair_value(spot: float, rate: float, T: float, *, div_pts: float = 0.0, convention: str = "krx") -> float:
    """krx: S·(1 + r·T) − D (simple, ACT/365 with T in years); cont: (S − D)e^{rT}."""
    if convention == "krx":
        return spot * (1.0 + rate * T) - div_pts
    return (spot - div_pts) * math.exp(rate * T)


def implied_repo(F: float, spot: float, T: float, *, div_pts: float = 0.0) -> float:
    """The simple rate that makes S·(1 + r·T) − D = F."""
    if T <= 0 or spot <= 0:
        raise FICCError("implied repo needs T > 0 and spot > 0")
    return ((F + div_pts) / spot - 1.0) / T


@dataclass(frozen=True)
class BasisReport:
    futures: float
    spot: float
    rate: float
    T: float
    div_pts: float
    fair: float
    basis_pts: float                  # F − S
    mispricing_bp: float              # (F − F*)/S in bp
    implied_rate: float
    exchange_theo: Optional[float] = None
    theo_gap_pts: Optional[float] = None

    @property
    def rich(self) -> bool:
        return self.mispricing_bp > 0


def basis_report(F: float, spot: float, rate: float, T: float, *, div_pts: float = 0.0,
                 exchange_theo: Optional[float] = None, convention: str = "krx") -> BasisReport:
    fv = fair_value(spot, rate, T, div_pts=div_pts, convention=convention)
    return BasisReport(futures=F, spot=spot, rate=rate, T=T, div_pts=div_pts, fair=fv, basis_pts=F - spot,
                       mispricing_bp=(F - fv) / spot / BP, implied_rate=implied_repo(F, spot, T, div_pts=div_pts),
                       exchange_theo=exchange_theo,
                       theo_gap_pts=(fv - exchange_theo) if exchange_theo is not None else None)


# --------------------------------------------------------------------------- #
# The board: quotes → implied vols
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Quote:
    strike: float
    call_mid: Optional[float] = None
    put_mid: Optional[float] = None
    call_bid: Optional[float] = None
    call_ask: Optional[float] = None
    put_bid: Optional[float] = None
    put_ask: Optional[float] = None
    call_iv_exchange: Optional[float] = None
    put_iv_exchange: Optional[float] = None


def board_quotes(board) -> list[Quote]:
    """Merge a `data.kis_markets.OptionBoard` into per-strike quotes."""
    calls = {q.strike: q for q in board.calls}
    puts = {q.strike: q for q in board.puts}
    out = []
    for k in sorted(set(calls) | set(puts)):
        c, p = calls.get(k), puts.get(k)
        out.append(Quote(strike=k,
                         call_mid=c.mid if c else None, put_mid=p.mid if p else None,
                         call_bid=c.bid if c else None, call_ask=c.ask if c else None,
                         put_bid=p.bid if p else None, put_ask=p.ask if p else None,
                         call_iv_exchange=c.iv if c else None, put_iv_exchange=p.iv if p else None))
    return out


def implied_forward(quotes: Sequence[Quote], rate: float, T: float) -> tuple[float, float]:
    """(F, K₀): F from put–call parity at the strike with the smallest |C − P|."""
    best = None
    for q in quotes:
        if q.call_mid is None or q.put_mid is None:
            continue
        gap = abs(q.call_mid - q.put_mid)
        if best is None or gap < best[0]:
            best = (gap, q)
    if best is None:
        raise FICCError("no strike has both a call and a put mid; cannot imply the forward")
    q = best[1]
    F = q.strike + math.exp(rate * T) * (q.call_mid - q.put_mid)
    strikes = [x.strike for x in quotes]
    if not (min(strikes) <= F <= max(strikes)):
        raise FICCError(f"the board ({min(strikes):.1f}–{max(strikes):.1f}) does not bracket the implied forward "
                        f"{F:.1f}; the chain is truncated or the quotes are stale")
    k0 = max(x for x in strikes if x <= F)
    return F, k0


@dataclass(frozen=True)
class IVPoint:
    strike: float
    kind: str                         # "call" | "put" (the OTM side used)
    mid: float
    iv: float                         # Black-76 implied, decimal
    iv_exchange: Optional[float]
    log_moneyness: float              # ln(K/F)
    spread: Optional[float]           # ask − bid of the side used


def chain_implied_vols(quotes: Sequence[Quote], F: float, T: float, rate: float, *,
                       min_premium: float = 0.05, quoted_only: bool = False,
                       max_moneyness: float | None = None) -> list[IVPoint]:
    """Invert Black-76 on the OTM side (puts below F, calls above) of every
    strike with a usable mid; prices at or below intrinsic are skipped.
    `quoted_only` keeps only strikes with a live bid AND ask on the side used
    (a stale last print on a far wing is not a quote); `max_moneyness` limits
    |ln(K/F)|."""
    df = math.exp(-rate * T)
    out = []
    for q in quotes:
        use_call = q.strike >= F
        mid = q.call_mid if use_call else q.put_mid
        if mid is None or mid < min_premium:
            continue
        if max_moneyness is not None and abs(math.log(q.strike / F)) > max_moneyness:
            continue
        if quoted_only:
            bid, ask = (q.call_bid, q.call_ask) if use_call else (q.put_bid, q.put_ask)
            if not bid or not ask or bid <= 0 or ask <= 0 or ask < bid:
                continue
        try:
            iv = implied_black_vol(mid, F, q.strike, T, df, call=use_call)
        except (FICCError, ValueError):
            continue
        bid, ask = (q.call_bid, q.call_ask) if use_call else (q.put_bid, q.put_ask)
        out.append(IVPoint(strike=q.strike, kind="call" if use_call else "put", mid=mid, iv=iv,
                           iv_exchange=q.call_iv_exchange if use_call else q.put_iv_exchange,
                           log_moneyness=math.log(q.strike / F),
                           spread=(ask - bid) if bid is not None and ask is not None and ask >= bid else None))
    return out


def reconcile_iv(points: Sequence[IVPoint]) -> dict:
    """Median and 90th percentile of |σ_app − σ_exchange| in vol points (candidate O1's gate)."""
    gaps = [abs(p.iv - p.iv_exchange) * 100 for p in points if p.iv_exchange]
    if not gaps:
        return {"n": 0, "median_volpts": float("nan"), "p90_volpts": float("nan"), "ok": False}
    g = np.asarray(gaps)
    return {"n": int(g.size), "median_volpts": float(np.median(g)), "p90_volpts": float(np.percentile(g, 90)),
            "ok": bool(np.median(g) <= 0.5 and np.percentile(g, 90) <= 1.5)}


def parity_residuals(quotes: Sequence[Quote], F: float, T: float, rate: float, *, band: float = 0.10) -> list[dict]:
    """ρ_K = C − P − e^{−rT}(F − K); flagged when |ρ| exceeds half the summed spread."""
    df = math.exp(-rate * T)
    out = []
    for q in quotes:
        if q.call_mid is None or q.put_mid is None or abs(q.strike / F - 1.0) > band:
            continue
        resid = q.call_mid - q.put_mid - df * (F - q.strike)
        spread = None
        if None not in (q.call_bid, q.call_ask, q.put_bid, q.put_ask):
            spread = (q.call_ask - q.call_bid) + (q.put_ask - q.put_bid)
        out.append({"strike": q.strike, "residual": resid, "half_spread_sum": (spread / 2 if spread is not None else None),
                    "within": (abs(resid) <= spread / 2) if spread is not None else None})
    return out


def static_arbitrage(quotes: Sequence[Quote], *, quoted_only: bool = False, F: float | None = None,
                     max_moneyness: float | None = None) -> dict:
    """Counts of vertical (monotonicity) and butterfly (convexity) violations on
    mids, optionally restricted to strikes with a live two-sided quote and to
    |ln(K/F)| ≤ max_moneyness."""
    def keep(q: Quote, call: bool) -> bool:
        if F is not None and max_moneyness is not None and abs(math.log(q.strike / F)) > max_moneyness:
            return False
        if not quoted_only:
            return True
        bid, ask = (q.call_bid, q.call_ask) if call else (q.put_bid, q.put_ask)
        return bool(bid and ask and bid > 0 and ask >= bid)
    calls = [(q.strike, q.call_mid) for q in quotes if q.call_mid is not None and keep(q, True)]
    puts = [(q.strike, q.put_mid) for q in quotes if q.put_mid is not None and keep(q, False)]

    def check(series, increasing: bool):
        vert, fly = 0, 0
        for (k1, p1), (k2, p2) in zip(series, series[1:]):
            if (p2 > p1 + 1e-9) if not increasing else (p2 < p1 - 1e-9):
                vert += 1
        for (k1, p1), (k2, p2), (k3, p3) in zip(series, series[1:], series[2:]):
            lam = (k3 - k2) / (k3 - k1)
            if p2 > lam * p1 + (1 - lam) * p3 + 1e-9:
                fly += 1
        return vert, fly
    cv, cf = check(calls, increasing=False)
    pv, pf = check(puts, increasing=True)
    return {"call_vertical": cv, "call_butterfly": cf, "put_vertical": pv, "put_butterfly": pf,
            "n_calls": len(calls), "n_puts": len(puts)}


# --------------------------------------------------------------------------- #
# SVI
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class SVIFit:
    a: float
    b: float
    rho: float
    m: float
    sigma: float
    T: float
    rmse_volpts: float
    rmse_near_volpts: float           # |k| ≤ 0.15
    min_g: float                      # Gatheral–Jacquier butterfly function minimum on the fitted range
    converged: bool
    n_points: int
    k_range: tuple[float, float]

    @property
    def params(self) -> tuple[float, float, float, float, float]:
        return self.a, self.b, self.rho, self.m, self.sigma

    @property
    def arbitrage_free(self) -> bool:
        return self.min_g >= -1e-9 and self.b >= 0 and abs(self.rho) < 1 and \
            self.a + self.b * self.sigma * math.sqrt(1 - self.rho ** 2) >= -1e-12


def svi_w(k, a: float, b: float, rho: float, m: float, sigma: float):
    """Raw SVI total variance w(k) = a + b[ρ(k − m) + √((k − m)² + σ²)]."""
    k = np.asarray(k, dtype=float)
    return a + b * (rho * (k - m) + np.sqrt((k - m) ** 2 + sigma ** 2))


def svi_g(k, a: float, b: float, rho: float, m: float, sigma: float):
    """Gatheral–Jacquier (2014) g(k) = (1 − k w'/(2w))² − (w'²/4)(1/w + 1/4) + w''/2;
    g ≥ 0 everywhere is the no-butterfly-arbitrage condition."""
    k = np.asarray(k, dtype=float)
    w = svi_w(k, a, b, rho, m, sigma)
    root = np.sqrt((k - m) ** 2 + sigma ** 2)
    w1 = b * (rho + (k - m) / root)
    w2 = b * sigma ** 2 / root ** 3
    return (1 - k * w1 / (2 * w)) ** 2 - (w1 ** 2 / 4) * (1 / w + 0.25) + w2 / 2


def fit_svi(log_moneyness: Sequence[float], vols: Sequence[float], T: float, *,
            weights: Optional[Sequence[float]] = None) -> SVIFit:
    """Least squares on total variance w = σ²T (weighted by 1/spread when given),
    bounds b ≥ 0, |ρ| < 1, σ > 0, and the no-negative-variance start."""
    k = np.asarray(log_moneyness, dtype=float)
    v = np.asarray(vols, dtype=float)
    if k.size < 5:
        raise FICCError(f"SVI needs at least 5 strikes, got {k.size}")
    if T <= 0 or np.any(v <= 0):
        raise ValueError("T must be positive and vols positive")
    w = v ** 2 * T
    wt = np.ones_like(w) if weights is None else np.asarray(weights, dtype=float)
    wt = wt / wt.mean()
    x0 = [float(w.min()) * 0.9, 0.1, -0.3, 0.0, 0.1]
    lo = [-1.0, 0.0, -0.999, -1.0, 1e-4]
    hi = [1.0, 5.0, 0.999, 1.0, 2.0]

    def resid(p):
        return np.sqrt(wt) * (svi_w(k, *p) - w)
    res = least_squares(resid, x0, bounds=(lo, hi), method="trf", max_nfev=5000)
    a, b, rho, m, sig = (float(x) for x in res.x)
    fitted = np.sqrt(np.clip(svi_w(k, a, b, rho, m, sig), 1e-12, None) / T)
    err = (fitted - v) * 100
    near = np.abs(k) <= 0.15
    grid = np.linspace(k.min() - 0.05, k.max() + 0.05, 201)
    return SVIFit(a=a, b=b, rho=rho, m=m, sigma=sig, T=T, rmse_volpts=float(np.sqrt(np.mean(err ** 2))),
                  rmse_near_volpts=float(np.sqrt(np.mean(err[near] ** 2))) if near.any() else float("nan"),
                  min_g=float(np.min(svi_g(grid, a, b, rho, m, sig))), converged=bool(res.success),
                  n_points=int(k.size), k_range=(float(k.min()), float(k.max())))


def svi_vol(fit: SVIFit, log_moneyness) -> np.ndarray:
    return np.sqrt(np.clip(svi_w(log_moneyness, *fit.params), 1e-12, None) / fit.T)


def calendar_crossing(near: SVIFit, far: SVIFit, *, k_grid=np.linspace(-0.3, 0.3, 61)) -> float:
    """Share of the grid where total variance falls with maturity (must be 0)."""
    w_near = svi_w(k_grid, *near.params)
    w_far = svi_w(k_grid, *far.params)
    return float(np.mean(w_far < w_near - 1e-12))


# --------------------------------------------------------------------------- #
# Model-free implied variance and the risk-neutral density
# --------------------------------------------------------------------------- #
def mfiv(quotes: Sequence[Quote], F: float, T: float, rate: float, *, k0: Optional[float] = None) -> dict:
    """Cboe strip: OTM puts below K₀, OTM calls above, the average at K₀, ΔK the
    half-distance between neighbours, truncation after two consecutive zero
    (missing) bids on each side. Returns σ² (annualised) and σ."""
    qs = sorted(quotes, key=lambda q: q.strike)
    strikes = [q.strike for q in qs]
    if not qs or not (strikes[0] <= F <= strikes[-1]):
        raise FICCError("model-free variance needs strikes on both sides of the forward")
    if k0 is None:
        k0 = max(k for k in strikes if k <= F)

    def usable(q: Quote, call: bool) -> Optional[float]:
        bid = q.call_bid if call else q.put_bid
        mid = q.call_mid if call else q.put_mid
        if mid is None or mid <= 0:
            return None
        if bid is not None and bid <= 0:
            return None
        return mid
    below = [q for q in qs if q.strike < k0]
    above = [q for q in qs if q.strike > k0]
    at = next((q for q in qs if q.strike == k0), None)
    sel: list[tuple[float, float]] = []
    zeros = 0
    for q in reversed(below):
        p = usable(q, call=False)
        if p is None:
            zeros += 1
            if zeros >= 2:
                break
            continue
        zeros = 0
        sel.append((q.strike, p))
    zeros = 0
    for q in above:
        c = usable(q, call=True)
        if c is None:
            zeros += 1
            if zeros >= 2:
                break
            continue
        zeros = 0
        sel.append((q.strike, c))
    if at is not None and at.call_mid is not None and at.put_mid is not None:
        sel.append((k0, 0.5 * (at.call_mid + at.put_mid)))
    if len(sel) < 4:
        raise FICCError("too few usable OTM quotes for a model-free variance")
    sel.sort()
    ks = np.array([s[0] for s in sel])
    qv = np.array([s[1] for s in sel])
    dk = np.empty_like(ks)
    dk[1:-1] = (ks[2:] - ks[:-2]) / 2
    dk[0] = ks[1] - ks[0]
    dk[-1] = ks[-1] - ks[-2]
    var = (2.0 / T) * float(np.sum(dk / ks ** 2 * math.exp(rate * T) * qv)) - (1.0 / T) * (F / k0 - 1.0) ** 2
    return {"variance": var, "vol": math.sqrt(max(var, 0.0)), "n_strikes": int(ks.size), "k0": k0,
            "k_min": float(ks.min()), "k_max": float(ks.max())}


def interpolate_30d(var_near: float, T_near: float, var_far: float, T_far: float, *, target_days: float = 30.0) -> float:
    """Cboe 30-day interpolation of total variance, returned as an annualised vol."""
    t = target_days / 365.0
    if T_far <= T_near:
        raise ValueError("far expiry must be later than near")
    w = (T_far - t) / (T_far - T_near)
    total = (T_near * var_near * w + T_far * var_far * (1 - w)) / t
    return math.sqrt(max(total, 0.0))


def rnd_from_svi(fit: SVIFit, F: float, rate: float, *, n: int = 401, width: float = 0.6) -> dict:
    """Breeden–Litzenberger on the SVI-smoothed call curve: f_Q(K) = e^{rT}∂²C/∂K²,
    by central differences on a fine strike grid. Returns the grid, the
    density, its integral and the implied mean (should be F)."""
    T = fit.T
    K = F * np.exp(np.linspace(-width, width, n))
    df = math.exp(-rate * T)
    vols = svi_vol(fit, np.log(K / F))
    C = np.array([black76(F, k, T, float(v), df).price for k, v in zip(K, vols)])
    d2 = np.gradient(np.gradient(C, K), K)
    dens = np.clip(d2 / df, 0.0, None)
    integral = float(np.trapezoid(dens, K)) if hasattr(np, "trapezoid") else float(np.trapz(dens, K))
    mean = float(np.trapezoid(K * dens, K) / integral) if integral > 0 else float("nan")
    return {"strikes": K, "density": dens, "integral": integral, "mean": mean, "F": F,
            "negative_share": float(np.mean(d2 < -1e-12))}


def pricing_kernel(rnd: dict, terminal_samples: np.ndarray) -> dict:
    """Z(K) = f_Q(K)/f_P(K) with f_P a Gaussian KDE of P-terminal prices (the user's
    paper §3.4 eq. 18): the empirical pricing kernel on the RND grid."""
    kde = gaussian_kde(np.asarray(terminal_samples, dtype=float))
    fp = kde(rnd["strikes"])
    with np.errstate(divide="ignore", invalid="ignore"):
        z = np.where(fp > 1e-12, rnd["density"] / fp, np.nan)
    return {"strikes": rnd["strikes"], "f_p": fp, "kernel": z}


# --------------------------------------------------------------------------- #
# Box spread
# --------------------------------------------------------------------------- #
def box_rate(quotes: Sequence[Quote], T: float, *, k1: float, k2: float) -> dict:
    """Long box = +C(K₁) − C(K₂) + P(K₂) − P(K₁) pays K₂ − K₁; r = −ln(B/(K₂−K₁))/T."""
    if k2 <= k1 or T <= 0:
        raise ValueError("need k2 > k1 and T > 0")
    by = {q.strike: q for q in quotes}
    a, b = by.get(k1), by.get(k2)
    if not a or not b or None in (a.call_mid, a.put_mid, b.call_mid, b.put_mid):
        raise FICCError("box needs call and put mids at both strikes")
    B = a.call_mid - b.call_mid + b.put_mid - a.put_mid
    if B <= 0:
        raise FICCError("box price is not positive; quotes are stale or crossed")
    return {"box": B, "payoff": k2 - k1, "rate": -math.log(B / (k2 - k1)) / T, "T": T}


# --------------------------------------------------------------------------- #
# Hedger's P&L identity
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class HedgeSim:
    n_paths: int
    horizon: int
    spot: float
    strike: float
    sigma_hedge: float
    rate: float
    call: bool
    premium: float                    # V₀(σ_h)
    pnl: np.ndarray = field(repr=False)              # Π_T per path (currency per unit spot)
    realised_vol: np.ndarray = field(repr=False)     # per path, annualised
    gamma_term: np.ndarray = field(repr=False)       # ½Σe^{r(T−t)}ΓS²(σ_h² − r²/Δ)Δ per path
    mean_pnl_bp: float = 0.0          # of notional (= spot)
    se_bp: float = 0.0
    cvar95_bp: float = 0.0
    breakeven_vol: float = 0.0        # gamma-weighted realised vol at which mean Π = 0
    identity_slope: float = 0.0       # regression of Π on the gamma term
    identity_r2: float = 0.0
    engine: str = "gbm"
    note: str = ""


def hedge_pnl_simulation(*, spot: float, strike: float, horizon_days: int, sigma_hedge: float, rate: float,
                         call: bool = True, engine: str = "gbm", sigma_true: Optional[float] = None,
                         garch_fit=None, n_paths: int = 5000, seed: int = 7, drift_daily: float | None = None,
                         cost_bps: float = 0.0) -> HedgeSim:
    """Short one option priced at σ_h, delta-hedged daily with Black-76 delta on
    the forward; Π_T = e^{rT}V₀ − payoff + Σ_t Δ_t(S_{t+1} − S_t e^{rΔ})e^{r(T−t_{t+1})}.
    P-paths from GBM at σ_true (default σ_h) or the fitted GARCH-t
    (`core.quant.garch.simulate_returns`, bounded innovations, seeded)."""
    if horizon_days < 2 or spot <= 0 or strike <= 0 or sigma_hedge <= 0:
        raise ValueError("need horizon ≥ 2, positive spot/strike/σ_h")
    dt = 1.0 / TRADING_DAYS
    T = horizon_days * dt
    rng = np.random.default_rng(seed)
    if engine == "garch_t":
        if garch_fit is None:
            raise ValueError("engine='garch_t' needs garch_fit")
        from core.quant.garch import simulate_returns
        shocks, _ = simulate_returns(garch_fit, n_paths=n_paths, horizon=horizon_days, seed=seed,
                                     drift_daily=(drift_daily if drift_daily is not None else 0.0),
                                     rate_daily=None if drift_daily is not None else None)
        note = "GARCH-t P-paths (bounded innovations), zero drift unless given"
    else:
        s = sigma_true or sigma_hedge
        mu = (drift_daily if drift_daily is not None else (rate - 0.5 * s * s) * dt)
        shocks = rng.normal(mu, s * math.sqrt(dt), size=(n_paths, horizon_days))
        note = f"GBM P-paths at σ_true {s:.2%}"
    S = spot * np.exp(np.hstack([np.zeros((n_paths, 1)), np.cumsum(shocks, axis=1)]))
    steps = np.arange(horizon_days + 1)
    tau = T - steps * dt                                  # time to expiry at each step
    df = np.exp(-rate * tau)
    V0 = black76(spot * math.exp(rate * T), strike, T, sigma_hedge, math.exp(-rate * T), call).price
    pnl = np.full(n_paths, V0 * math.exp(rate * T))
    gamma_term = np.zeros(n_paths)
    w_sum = 0.0                                          # Σ e^{r(T−t)} Γ S² Δ, gamma weights
    wr_sum = 0.0                                         # the same weights × realised r²/Δ
    prev_delta = np.zeros(n_paths)
    from scipy.stats import norm
    for t in range(horizon_days):
        Ft = S[:, t] * np.exp(rate * tau[t])
        sd = sigma_hedge * math.sqrt(tau[t])
        d1 = (np.log(Ft / strike) + 0.5 * sd * sd) / sd
        delta = (df[t] * norm.cdf(d1) if call else -df[t] * norm.cdf(-d1)) * np.exp(rate * tau[t])   # spot delta
        gamma = norm.pdf(d1) / (S[:, t] * sd) if sd > 0 else 0.0
        growth = math.exp(rate * tau[t + 1])
        gain = delta * (S[:, t + 1] - S[:, t] * math.exp(rate * dt)) * growth
        cost = cost_bps * BP * S[:, t] * np.abs(delta - prev_delta)
        prev_delta = delta
        pnl += gain - cost
        r2 = np.log(S[:, t + 1] / S[:, t]) ** 2 / dt
        w = 0.5 * growth * gamma * S[:, t] ** 2 * dt
        gamma_term += w * (sigma_hedge ** 2 - r2)
        w_sum += float(np.mean(w)); wr_sum += float(np.mean(w * r2))
    payoff = np.maximum(S[:, -1] - strike, 0.0) if call else np.maximum(strike - S[:, -1], 0.0)
    pnl -= payoff
    rv = np.sqrt(np.sum(np.log(S[:, 1:] / S[:, :-1]) ** 2, axis=1) / T)
    bp = pnl / spot / BP
    tail = np.sort(bp)[: max(1, int(0.05 * n_paths))]
    X = np.column_stack([np.ones(n_paths), gamma_term])
    beta, *_ = np.linalg.lstsq(X, pnl, rcond=None)
    fitted = X @ beta
    ss_res = float(np.sum((pnl - fitted) ** 2))
    ss_tot = float(np.sum((pnl - pnl.mean()) ** 2))
    # The identity in expectation: mean Π = ½E[Σw](σ_h² − σ_be²) with σ_be² the
    # gamma-weighted realised variance, so σ_be is the hedge vol that breaks even.
    breakeven = math.sqrt(wr_sum / w_sum) if w_sum > 0 else sigma_hedge
    return HedgeSim(n_paths=n_paths, horizon=horizon_days, spot=spot, strike=strike, sigma_hedge=sigma_hedge,
                    rate=rate, call=call, premium=V0, pnl=pnl, realised_vol=rv, gamma_term=gamma_term,
                    mean_pnl_bp=float(bp.mean()), se_bp=float(bp.std(ddof=1) / math.sqrt(n_paths)),
                    cvar95_bp=float(tail.mean()), breakeven_vol=float(breakeven),
                    identity_slope=float(beta[1]), identity_r2=(1.0 - ss_res / ss_tot) if ss_tot > 0 else 0.0,
                    engine=engine, note=note)


# --------------------------------------------------------------------------- #
# Leveraged ETFs
# --------------------------------------------------------------------------- #
def letf_drag(beta: float, daily_variances: Sequence[float], *, rate: float = 0.0, fee: float = 0.0) -> dict:
    """Avellaneda–Zhang (2010) eq. (10): ln(L_T/L_0) − β ln(S_T/S_0)
    = ((β − β²)/2)Σσ²Δ + ((1 − β)r − f)T. Returns the expected log drag over the
    horizon (negative = the fund lags β× the index), split into the variance
    term and the financing/fee term, from a daily variance forecast path."""
    v = np.asarray(daily_variances, dtype=float)
    N = v.size
    var_term = (beta - beta ** 2) / 2.0 * float(np.sum(v))
    fin_term = ((1.0 - beta) * rate - fee) * N / TRADING_DAYS
    return {"beta": beta, "sessions": N, "variance_term": var_term, "financing_term": fin_term,
            "drag": var_term + fin_term, "drag_bp": (var_term + fin_term) / BP,
            "annualised_variance": float(np.sum(v)) * TRADING_DAYS / N}


def letf_realised_drag(letf_prices: Sequence[float], index_prices: Sequence[float], beta: float) -> float:
    L, S = np.asarray(letf_prices, dtype=float), np.asarray(index_prices, dtype=float)
    return float(math.log(L[-1] / L[0]) - beta * math.log(S[-1] / S[0]))


# --------------------------------------------------------------------------- #
# Self-check
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    F, r, T = 1126.0, 0.032, 0.05
    df = math.exp(-r * T)
    # Futures: fair value and implied repo round-trip; KRX vs continuous agree to first order.
    fv = fair_value(1120.0, r, T, div_pts=1.0)
    assert abs(implied_repo(fv, 1120.0, T, div_pts=1.0) - r) < 1e-12
    assert abs(fair_value(1120.0, r, T, convention="cont") - fv - 1.0) < 0.05
    rep = basis_report(fv + 1.12, 1120.0, r, T, div_pts=1.0, exchange_theo=fv)
    assert abs(rep.mispricing_bp - 10.0) < 1e-6 and rep.rich and abs(rep.theo_gap_pts) < 1e-12
    # A synthetic board from a smile; inversion recovers it and parity holds.
    strikes = np.arange(1000, 1260, 10.0)
    smile = lambda k: 0.18 + 0.4 * max(0.0, math.log(F / k)) ** 1 + 0.6 * math.log(k / F) ** 2   # noqa: E731
    quotes = []
    for k in strikes:
        v = smile(k)
        c, p = black76(F, k, T, v, df, True).price, black76(F, k, T, v, df, False).price
        quotes.append(Quote(strike=k, call_mid=c, put_mid=p, call_bid=c - 0.05, call_ask=c + 0.05,
                            put_bid=p - 0.05, put_ask=p + 0.05, call_iv_exchange=v, put_iv_exchange=v))
    Fi, k0 = implied_forward(quotes, r, T)
    assert abs(Fi - F) < 1e-6 and k0 == 1120.0, (Fi, k0)
    pts = chain_implied_vols(quotes, F, T, r)
    assert len(pts) > 15 and all(abs(p.iv - smile(p.strike)) < 1e-6 for p in pts)
    rec = reconcile_iv(pts)
    assert rec["ok"] and rec["median_volpts"] < 1e-4
    par = parity_residuals(quotes, F, T, r)
    assert par and all(abs(x["residual"]) < 1e-9 and x["within"] for x in par)
    arb = static_arbitrage(quotes)
    assert arb["call_vertical"] == 0 and arb["put_vertical"] == 0
    # SVI reproduces its own surface and is arbitrage-free there.
    ks = np.linspace(-0.25, 0.25, 21)
    true = (0.0005, 0.08, -0.4, 0.02, 0.15)
    w_true = svi_w(ks, *true)
    fit = fit_svi(ks, np.sqrt(w_true / T), T)
    assert fit.rmse_volpts < 1e-3 and fit.converged and fit.arbitrage_free, (fit.rmse_volpts, fit.min_g)
    assert np.all(np.abs(svi_vol(fit, ks) - np.sqrt(w_true / T)) < 1e-4)
    far = fit_svi(ks, np.sqrt(svi_w(ks, 0.0006, 0.08, -0.4, 0.02, 0.15) / (2 * T) * 2.2), 2 * T)
    assert calendar_crossing(fit, far) == 0.0
    # Model-free variance on a flat-vol board equals the flat vol (to a small strip error).
    flat = 0.20
    fq = [Quote(strike=k, call_mid=black76(F, k, T, flat, df, True).price, put_mid=black76(F, k, T, flat, df, False).price,
                call_bid=0.01, put_bid=0.01) for k in np.arange(700, 1700, 2.5)]
    mv = mfiv(fq, F, T, r)
    assert abs(mv["vol"] - flat) < 0.003, mv["vol"]
    assert abs(interpolate_30d(0.04, 20 / 365, 0.04, 50 / 365) - 0.2) < 1e-12
    # RND integrates to one with mean F; the box implies the rate.
    rnd = rnd_from_svi(fit_svi(ks, np.full(ks.size, flat), T), F, r)
    assert 0.99 < rnd["integral"] < 1.01 and abs(rnd["mean"] / F - 1.0) < 0.002 and rnd["negative_share"] == 0.0
    kern = pricing_kernel(rnd, F * np.exp(np.random.default_rng(1).normal(-0.5 * flat ** 2 * T, flat * math.sqrt(T), 20000)))
    assert np.nanmax(kern["kernel"]) > 0
    bx = box_rate(quotes, T, k1=1100.0, k2=1150.0)
    assert abs(bx["rate"] - r) < 1e-9, bx
    # Hedge P&L: σ_h = σ_true → mean ≈ 0 within SE; σ_h < σ_true loses; identity slope near 1.
    hs = hedge_pnl_simulation(spot=1120.0, strike=1120.0, horizon_days=42, sigma_hedge=0.20, rate=r, n_paths=4000, seed=3)
    assert abs(hs.mean_pnl_bp) < 3 * hs.se_bp + 1.0, (hs.mean_pnl_bp, hs.se_bp)
    lo = hedge_pnl_simulation(spot=1120.0, strike=1120.0, horizon_days=42, sigma_hedge=0.15, rate=r, sigma_true=0.25, n_paths=4000, seed=3)
    assert lo.mean_pnl_bp < -5 * lo.se_bp and 0.22 < lo.breakeven_vol < 0.28, (lo.mean_pnl_bp, lo.breakeven_vol)
    assert 0.18 < hs.breakeven_vol < 0.22, hs.breakeven_vol
    assert 0.8 < lo.identity_slope < 1.2 and lo.identity_r2 > 0.8, (lo.identity_slope, lo.identity_r2)
    # LETF drag: +2× loses 1×∫σ², −2× loses 3×∫σ².
    v = np.full(252, (0.20 ** 2) / 252)
    d2, dm2 = letf_drag(2.0, v), letf_drag(-2.0, v)
    assert abs(d2["variance_term"] + 0.04) < 1e-12 and abs(dm2["variance_term"] + 0.12) < 1e-12
    assert abs(letf_drag(2.0, v, fee=0.0064)["financing_term"] + 0.0064) < 1e-12
    print("ok")
