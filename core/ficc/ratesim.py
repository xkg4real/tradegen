"""Short-rate models: Vasicek, CIR and Hull-White — calibration from a rate
history, seeded Euler simulation with a percentile fan, closed-form zero-coupon
bonds, and the horizon P&L distribution of a bond or swap revalued on each
path's model curve.

Simplifications, on purpose:

  * Calibration is one OLS regression on the discretised SDE (Δr = a + b·r + ε
    for Vasicek/Hull-White; Δr/√r = a/√r + b·√r + ε for CIR). kappa is clamped
    at 0.01 — a series with no visible mean reversion still needs a finite
    long-run mean — and the note says when the clamp bit.
  * Hull-White's θ(t) comes from the curve handed to `simulate`/`zcb_price`:
    θ(t) = f'(0,t) + κ·f(0,t) + σ²/(2κ)·(1 − e^{−2κt}) with f = `curve.inst_fwd`.
    The f' term is integrated exactly over each Euler step (f(0,t) is piecewise
    constant under log-linear DF interpolation, so a sampled f' would count its
    knot jumps twice or not at all). The model's own r(0) is f(0,0), so `simulate`
    resets r0 to `curve.inst_fwd(0)` for Hull-White and says so; without a curve
    it uses a flat curve at the calibrated r0 (then Hull-White ≈ Vasicek).
  * Euler steps; CIR uses full truncation (drift and diffusion see max(r,0)) and
    reports max(r,0), so paths never go below zero.
  * The horizon revaluation builds a `YieldCurve` on KEY_TENORS from the model's
    ZCB prices for a subsample of ≤ 500 paths (evenly strided, which keeps the
    seeded order), prices the remaining instrument on it, and ignores
    reinvestment of cashflows that fall before the horizon (bond coupons paid
    before the horizon are added at face value; swap fixings before the
    horizon are dropped).
  * ACT/365F simple year fractions; every rate is a decimal.
  * SEP Table-2 error bands (R-16 rule (4)(e), TASK-M9-03): `sep_band_params` keeps
    kappa/theta/r0 and solves sigma from the closed-form terminal variance so the
    sd at the horizon equals band / Phi^-1((1 + coverage) / 2); `sep_band_paths`
    simulates it seeded. The fan centres on the model drift, not on SEP medians.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
from statistics import NormalDist
from typing import TYPE_CHECKING

import numpy as np

from core.ficc.common import KEY_TENORS, FICCError, tenor_label
from core.ficc.curves import YieldCurve, coupon_times, flat_curve

if TYPE_CHECKING:                                     # duck-typed at runtime
    from core.ficc.bonds import Bond
    from core.ficc.data import Series
    from core.ficc.swaps import Swap

MODELS = ("vasicek", "cir", "hull_white")
FAN_PERCENTILES = (5, 25, 50, 75, 95)
_KAPPA_MIN = 0.01
_MIN_OBS = 30
_MAX_REVAL_PATHS = 500


@dataclass(frozen=True)
class ShortRateParams:
    model: str
    kappa: float                      # mean-reversion speed (1/yr)
    theta: float                      # long-run mean (decimal); HW: regression mean only
    sigma: float                      # Vasicek/HW: absolute vol; CIR: vol of √r term
    r0: float                         # last observed short rate
    note: str = ""


@dataclass(frozen=True)
class RateSimResult:
    model: str
    params: ShortRateParams
    horizon: float
    n_paths: int
    fan: dict[int, np.ndarray] = field(repr=False, default_factory=dict)
    times: np.ndarray = field(repr=False, default=None)
    terminal: np.ndarray = field(repr=False, default=None)
    mean_terminal: float = 0.0
    p05: float = 0.0
    p95: float = 0.0
    prob_above: float | None = None   # P(terminal > threshold)
    threshold: float | None = None
    model_curve_at_horizon: tuple[tuple[float, float], ...] = ()   # (tenor, zero), median path
    note: str = ""


@dataclass(frozen=True)
class HorizonPV:
    pvs: np.ndarray = field(repr=False, default=None)   # instrument value at horizon, per path
    mean: float = 0.0
    p05: float = 0.0
    p95: float = 0.0
    var95: float = 0.0                # loss vs today's PV at the 95th percentile (>= 0)
    cvar95: float = 0.0
    note: str = ""


def _check_model(model: str) -> str:
    m = (model or "").lower()
    if m not in MODELS:
        raise ValueError(f"Unknown model {model!r}. One of {MODELS}.")
    return m


# --------------------------------------------------------------------------- #
# Calibration
# --------------------------------------------------------------------------- #
def calibrate(series: "Series", *, model: str = "vasicek", dt: float | None = None
              ) -> ShortRateParams:
    """OLS on the discretised SDE. `dt` is the observation step in years; None
    picks 1/12 when the series note says "monthly", else 1/252. Vasicek and
    Hull-White regress Δr on r; CIR regresses Δr/√r on 1/√r and √r (no
    intercept) so σ is the vol of the √r term. kappa is clamped at 0.01."""
    model = _check_model(model)
    r = np.asarray(series.array(), dtype=float)
    r = r[np.isfinite(r)]
    if r.size < _MIN_OBS:
        raise FICCError(f"Need at least {_MIN_OBS} observations to calibrate, got {r.size}.")
    if dt is None:
        dt = 1.0 / 12.0 if "monthly" in (series.note or "").lower() else 1.0 / 252.0
    if dt <= 0:
        raise ValueError(f"dt must be positive, got {dt}.")
    dr, lag = np.diff(r), r[:-1]
    notes = []
    if model == "cir":
        base = np.maximum(lag, 1e-6)                  # CIR needs r > 0
        sq = np.sqrt(base)
        X = np.column_stack([1.0 / sq, sq])           # Δr/√r = (κθ)/√r·dt − κ√r·dt + σ dW
        y = dr / sq
    else:
        X = np.column_stack([np.ones_like(lag), lag])   # Δr = κθ·dt − κr·dt + σ dW
        y = dr
    coef, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ coef
    a, b = float(coef[0]), float(coef[1])
    kappa = -b / dt
    if kappa < _KAPPA_MIN:
        notes.append(f"kappa clamped to {_KAPPA_MIN} (regression gave {kappa:.3f})")
        kappa = _KAPPA_MIN
        theta = float(np.mean(r))                     # no reversion seen: use the sample mean
    else:
        theta = a / (kappa * dt)
    sigma = float(np.std(resid, ddof=2)) / math.sqrt(dt)
    if not math.isfinite(sigma) or sigma <= 0:
        raise FICCError("Calibration produced a non-positive volatility.")
    if model == "cir":
        if theta <= 0:
            notes.append(f"theta {theta:.4f} <= 0; floored at sample mean")
            theta = max(float(np.mean(r)), 1e-4)
        if 2 * kappa * theta < sigma**2:
            notes.append("Feller condition 2κθ ≥ σ² fails; zero is attainable")
    if model == "hull_white":
        notes.append("θ(t) is fitted to the curve at simulation time; theta here is the "
                     "regression mean")
    notes.append(f"{r.size} obs, dt={dt:.4f}")
    return ShortRateParams(model=model, kappa=float(kappa), theta=float(theta),
                           sigma=float(sigma), r0=float(r[-1]), note="; ".join(notes))


# --------------------------------------------------------------------------- #
# Closed-form zero-coupon bonds:  P(t,T) = exp(lnA − B·r)
# --------------------------------------------------------------------------- #
def _zcb_ab(params: ShortRateParams, t: float, T: float,
            curve: YieldCurve | None) -> tuple[float, float]:
    """(lnA, B) with ln P(t,T) = lnA − B·r(t). Vasicek/CIR are affine in r;
    Hull-White needs the curve for P(0,·) and f(0,t)."""
    if T < t or t < 0:
        raise ValueError(f"need 0 <= t <= T, got t={t}, T={T}.")
    tau = T - t
    k, th, s = params.kappa, params.theta, params.sigma
    if tau == 0:
        return 0.0, 0.0
    if params.model == "cir":
        g = math.sqrt(k * k + 2 * s * s)
        e = math.exp(g * tau) - 1.0
        den = (k + g) * e + 2 * g
        B = 2 * e / den
        lnA = (2 * k * th / (s * s)) * math.log(2 * g * math.exp((k + g) * tau / 2) / den)
        return lnA, B
    B = (1.0 - math.exp(-k * tau)) / k
    if params.model == "vasicek":
        lnA = (th - s * s / (2 * k * k)) * (B - tau) - s * s * B * B / (4 * k)
        return lnA, B
    curve = curve if curve is not None else flat_curve(params.r0)
    lnA = (math.log(curve.df(T) / curve.df(t)) + B * curve.inst_fwd(t)
           - s * s / (4 * k) * B * B * (1.0 - math.exp(-2 * k * t)))
    return lnA, B


def zcb_price(params: ShortRateParams, r: float, t: float, T: float, *,
              curve: YieldCurve | None = None) -> float:
    """P(t,T) given the short rate r at t. Hull-White reproduces `curve.df(T)` at
    t=0 when r == curve.inst_fwd(0); without a curve it is flat at r0."""
    _check_model(params.model)
    lnA, B = _zcb_ab(params, t, T, curve)
    return float(math.exp(lnA - B * r))


def _model_curve(params: ShortRateParams, r: float, t: float, curve: YieldCurve | None,
                 *, ab: dict[float, tuple[float, float]] | None = None) -> YieldCurve:
    """YieldCurve at time t implied by the model with short rate r, on KEY_TENORS."""
    ab = ab if ab is not None else {tau: _zcb_ab(params, t, t + tau, curve) for tau in KEY_TENORS}
    zeros = tuple(-(lnA - B * r) / tau for tau, (lnA, B) in ab.items())
    return YieldCurve(date="", source=params.model.upper(), tenors=tuple(ab), zeros=zeros,
                      method="model", note=f"{params.model} curve at t={t:g}")


# --------------------------------------------------------------------------- #
# Simulation
# --------------------------------------------------------------------------- #
def _hw_drift(params: ShortRateParams, curve: YieldCurve, times: np.ndarray) -> np.ndarray:
    """∫θ(t)dt over each Euler step of `times`: the f' term exactly as
    f(0,t_{i+1}) − f(0,t_i), the rest at the step's left edge."""
    k, s = params.kappa, params.sigma
    f = np.array([curve.inst_fwd(float(t)) for t in times])
    t, dt = times[:-1], np.diff(times)
    return np.diff(f) + (k * f[:-1] + s * s / (2 * k) * (1.0 - np.exp(-2 * k * t))) * dt


def simulate(params: ShortRateParams, *, horizon: float = 1.0, n_paths: int = 5000,
             steps_per_year: int = 252, seed: int = 7, threshold: float | None = None,
             curve: YieldCurve | None = None) -> RateSimResult:
    """Euler paths of the short rate. CIR: full truncation. Hull-White: θ(t)
    from `curve` (flat at r0 when None) and r0 := curve.inst_fwd(0)."""
    model = _check_model(params.model)
    if horizon <= 0:
        raise ValueError(f"horizon must be positive, got {horizon}.")
    n_paths = int(max(100, min(n_paths, 100_000)))
    steps = max(1, int(round(horizon * steps_per_year)))
    dt = horizon / steps
    times = np.linspace(0.0, horizon, steps + 1)
    k, th, s = params.kappa, params.theta, params.sigma
    notes = [f"{n_paths} paths, {steps} Euler steps, seed {seed}"]
    if model == "hull_white":
        if curve is None:
            curve = flat_curve(params.r0)
            notes.append("no curve given: flat at r0, so θ(t) is constant")
        r0 = curve.inst_fwd(0.0)
        if abs(r0 - params.r0) > 1e-12:
            notes.append(f"r0 reset to the curve's f(0,0)={r0:.4%} (observed {params.r0:.4%})")
        params = replace(params, r0=float(r0))
        drift = _hw_drift(params, curve, times)
    else:
        r0 = params.r0
    rng = np.random.default_rng(seed)
    z = rng.normal(size=(n_paths, steps)) * math.sqrt(dt)
    paths = np.empty((n_paths, steps + 1))
    paths[:, 0] = r0
    r = np.full(n_paths, r0, dtype=float)
    for i in range(steps):
        if model == "cir":
            pos = np.maximum(r, 0.0)
            r = r + k * (th - pos) * dt + s * np.sqrt(pos) * z[:, i]
            paths[:, i + 1] = np.maximum(r, 0.0)
        elif model == "vasicek":
            r = r + k * (th - r) * dt + s * z[:, i]
            paths[:, i + 1] = r
        else:
            r = r + drift[i] - k * r * dt + s * z[:, i]
            paths[:, i + 1] = r
    if model == "cir":
        paths = np.maximum(paths, 0.0)
        notes.append("full-truncation Euler; reported rates are max(r, 0)")
    terminal = paths[:, -1].copy()
    fan = {p: np.percentile(paths, p, axis=0) for p in FAN_PERCENTILES}
    r_med = float(np.median(terminal))
    mc = _model_curve(params, r_med, horizon, curve)
    return RateSimResult(
        model=model, params=params, horizon=float(horizon), n_paths=n_paths,
        fan=fan, times=times, terminal=terminal,
        mean_terminal=float(np.mean(terminal)),
        p05=float(np.percentile(terminal, 5)), p95=float(np.percentile(terminal, 95)),
        prob_above=(float(np.mean(terminal > threshold)) if threshold is not None else None),
        threshold=threshold,
        model_curve_at_horizon=tuple(zip(mc.tenors, mc.zeros)),
        note="; ".join(notes),
    )


# --------------------------------------------------------------------------- #
# SEP Table-2 short-rate error band -> rate-path uncertainty (R-16 rule (4)(e))
# --------------------------------------------------------------------------- #
SEP_RMSE_COVERAGE = 0.70     # "an RMSE band of about 70% coverage" (Council L1747 (4)); brief F-18


def _terminal_var_per_sigma2(params: ShortRateParams, h: float) -> float:
    """Var[r(h) | r0] / sigma^2. Vasicek and Hull-White: the OU part; CIR: the exact conditional variance."""
    k = params.kappa
    if params.model == "cir":
        return (params.r0 / k * (math.exp(-k * h) - math.exp(-2 * k * h))
                + params.theta / (2 * k) * (1.0 - math.exp(-k * h)) ** 2)
    return (1.0 - math.exp(-2 * k * h)) / (2 * k)


def sep_band_params(band_pp: float, horizon_years: float, model: ShortRateParams, *,
                    coverage: float = SEP_RMSE_COVERAGE, vintage: str = "") -> ShortRateParams:
    """The SEP Table-2 short-rate error band (+-`band_pp` percentage points at `horizon_years`, an RMSE band of
    `coverage`) as parameters of `model`, the calibrated base of one of MODELS: kappa, theta and r0 are kept and
    sigma is solved so the closed-form terminal sd equals (band_pp / 100) / Phi^-1((1 + coverage) / 2)
    (1.4 pp -> 1.351 pp, whose 90% half-width 2.22 pp is the spec's "about +-2.2 pp"). Brief F-18 reading."""
    _check_model(model.model)
    h = float(horizon_years)
    if not (math.isfinite(band_pp) and band_pp > 0 and math.isfinite(h) and h > 0 and 0.0 < coverage < 1.0):
        raise ValueError(f"need band_pp > 0, horizon_years > 0, 0 < coverage < 1; got {band_pp}, {horizon_years}, {coverage}.")
    if not model.kappa > 0:
        raise FICCError(f"kappa must be positive to map a band onto {model.model}, got {model.kappa}.")
    sd = band_pp / 100.0 / NormalDist().inv_cdf((1.0 + coverage) / 2.0)
    unit = _terminal_var_per_sigma2(model, h)
    if not (math.isfinite(unit) and unit > 0):
        raise FICCError(f"{model.model} terminal variance is not positive at h={h:g} (r0 {model.r0}, theta {model.theta}).")
    note = (f"SEP band +-{band_pp:g} pp at {h:g}y ({coverage:.0%} RMSE band{', vintage ' + vintage if vintage else ''}):"
            f" terminal sd {sd:.4%}, sigma solved, kappa/theta/r0 kept")
    return replace(model, sigma=sd / math.sqrt(unit), note="; ".join(x for x in (model.note, note) if x))


def sep_band_paths(model: str, params: ShortRateParams, seed: int, n_paths: int = 5000, horizon: float = 1.0, *,
                   steps_per_year: int = 252, curve: YieldCurve | None = None) -> RateSimResult:
    """Seeded short-rate paths of the SEP-band parameters through `simulate` (a rate model, never a log-return
    price model). `model` must name the model of `params`."""
    if _check_model(model) != params.model:
        raise ValueError(f"params are {params.model!r}, not {model!r}.")
    return simulate(params, horizon=horizon, n_paths=n_paths, steps_per_year=steps_per_year, seed=seed, curve=curve)


# --------------------------------------------------------------------------- #
# Horizon revaluation
# --------------------------------------------------------------------------- #
def _bond_value(bond: "Bond", curve: YieldCurve, h: float) -> float:
    """Currency value at time h: remaining coupons + face discounted on `curve`
    (whose t=0 is the horizon), plus coupons already paid at face value."""
    times = coupon_times(bond.maturity, bond.freq)
    c = bond.coupon / bond.freq * bond.face
    paid = float(np.sum(times <= h)) * c
    left = times[times > h] - h
    pv = float(np.sum(c * curve.df(left))) + bond.face * curve.df(bond.maturity - h)
    return (pv + paid) * bond.notional / bond.face


def _swap_value(swap: "Swap", curve: YieldCurve, h: float, fixed: float) -> float:
    """Payer PV at time h of the remaining swap: N·(DF(s) − DF(e)) − N·K·annuity."""
    s, e = max(swap.start - h, 0.0), swap.start + swap.tenor - h
    pv = swap.notional * ((curve.df(s) - curve.df(e)) - fixed * curve.annuity(e, swap.freq, s))
    return pv if swap.pay_fixed else -pv


def horizon_pv_distribution(params: ShortRateParams, sim: RateSimResult, *, kind: str = "bond",
                            bond: "Bond | None" = None, swap: "Swap | None" = None,
                            curve: YieldCurve | None = None) -> HorizonPV:
    """Revalue a bond or swap at `sim.horizon` on each path's model curve (≤ 500
    paths, evenly strided). Losses are measured against today's PV on `curve`
    (flat at r0 when None); var95/cvar95 are positive loss numbers."""
    if kind not in ("bond", "swap"):
        raise ValueError(f"kind must be bond|swap, got {kind!r}.")
    if curve is None:
        curve = flat_curve(sim.params.r0)
    h = sim.horizon
    if kind == "bond":
        if bond is None:
            raise FICCError("kind='bond' needs a Bond.")
        if bond.maturity <= h:
            raise FICCError(f"Bond matures at {bond.maturity:g}y, before the {h:g}y horizon.")
        today = _bond_value(bond, curve, 0.0)
        value = lambda c: _bond_value(bond, c, h)           # noqa: E731
        what = f"{bond.coupon:.2%} {tenor_label(bond.maturity)} bond"
    else:
        if swap is None:
            raise FICCError("kind='swap' needs a Swap.")
        end = swap.start + swap.tenor
        if end <= h:
            raise FICCError(f"Swap ends at {end:g}y, before the {h:g}y horizon.")
        fixed = (swap.fixed_rate if swap.fixed_rate is not None
                 else curve.par_rate(end, swap.freq, swap.start))
        today = _swap_value(swap, curve, 0.0, fixed)
        value = lambda c: _swap_value(swap, c, h, fixed)     # noqa: E731
        what = f"{'payer' if swap.pay_fixed else 'receiver'} {tenor_label(swap.tenor)} swap"
    stride = max(1, sim.terminal.size // _MAX_REVAL_PATHS)
    rates = sim.terminal[::stride][:_MAX_REVAL_PATHS]
    ab = {tau: _zcb_ab(sim.params, h, h + tau, curve) for tau in KEY_TENORS}
    pvs = np.array([value(_model_curve(sim.params, float(r), h, curve, ab=ab)) for r in rates])
    losses = today - pvs
    var = float(np.percentile(losses, 95))
    tail = losses[losses >= var]
    cvar = float(np.mean(tail)) if tail.size else var
    return HorizonPV(pvs=pvs, mean=float(np.mean(pvs)),
                     p05=float(np.percentile(pvs, 5)), p95=float(np.percentile(pvs, 95)),
                     var95=max(0.0, var), cvar95=max(0.0, cvar),
                     note=(f"{what} revalued at {h:g}y on {rates.size} of {sim.terminal.size} "
                           f"{sim.model} paths; today's PV {today:,.0f}; cashflows before the "
                           f"horizon are not reinvested"))


if __name__ == "__main__":
    from core.ficc.data import load_short_rate, load_treasury_curve
    from core.ficc.curves import curve_from_snapshot

    hist = load_short_rate("USD", source="synthetic", days=756)
    crv = curve_from_snapshot(load_treasury_curve(source="synthetic", days=60).latest())

    v = calibrate(hist, model="vasicek")
    assert v.kappa >= _KAPPA_MIN and v.sigma > 0
    sv = simulate(v, horizon=30.0, n_paths=2000, steps_per_year=52)
    assert abs(sv.mean_terminal - v.theta) <= 0.10 * abs(v.theta), (sv.mean_terminal, v.theta)
    assert simulate(v, n_paths=500).terminal[3] == simulate(v, n_paths=500).terminal[3]

    c = calibrate(hist, model="cir")
    sc = simulate(c, horizon=2.0, n_paths=2000)
    assert float(np.min(sc.fan[5])) >= 0.0 and float(np.min(sc.terminal)) >= 0.0

    hw = calibrate(hist, model="hull_white")
    r0 = crv.inst_fwd(0.0)
    for T in (0.5, 2.0, 10.0, 30.0):
        assert abs(zcb_price(hw, r0, 0.0, T, curve=crv) - crv.df(T)) < 1e-6, T
    sh = simulate(hw, horizon=1.0, n_paths=1000, curve=crv)
    assert abs(sh.params.r0 - r0) < 1e-12 and len(sh.model_curve_at_horizon) == len(KEY_TENORS)
    # E[r(h)] = f(0,h) + σ²/(2κ²)(1 − e^{−κh})²: the f' term must integrate the curve's knot jumps
    for h, spy in ((1.0, 252), (3.0, 52)):
        big = simulate(hw, horizon=h, n_paths=20000, steps_per_year=spy, curve=crv)
        want = crv.inst_fwd(h) + hw.sigma**2 / (2 * hw.kappa**2) * (1 - math.exp(-hw.kappa * h))**2
        assert abs(big.mean_terminal - want) < 3e-4, (h, big.mean_terminal, want)

    # Vasicek ZCB is consistent with the model's zero curve at t=0
    assert abs(zcb_price(v, v.r0, 0.0, 5.0) - _model_curve(v, v.r0, 0.0, None).df(5.0)) < 1e-12

    from types import SimpleNamespace as _NS
    bond = _NS(coupon=0.04, maturity=10.0, freq=2, face=100.0, notional=1e6)
    swap = _NS(tenor=10.0, fixed_rate=None, notional=1e6, pay_fixed=True, freq=1, start=0.0)
    hb = horizon_pv_distribution(hw, sh, kind="bond", bond=bond, curve=crv)
    hs = horizon_pv_distribution(hw, sh, kind="swap", swap=swap, curve=crv)
    assert hb.pvs.size == 500 and np.all(np.isfinite(hb.pvs)) and hb.var95 >= 0
    assert hs.pvs.size == 500 and np.all(np.isfinite(hs.pvs)) and hs.cvar95 >= hs.var95
    print("ok")
