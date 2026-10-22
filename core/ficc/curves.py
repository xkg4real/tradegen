"""Yield curves: bootstrap, Nelson-Siegel/Svensson fits, shifts, descriptors, PCA.

One object, `YieldCurve`, carries continuously-compounded zero rates at a set of
knot tenors and answers every discounting question the rest of the FICC core
asks (DF, zero, forward, annuity, par rate). Builders turn a par-yield snapshot
into a curve; `analyze_curve` turns a history of par curves into the numbers
the rates page and the narrative state (slopes, flies, forwards, shape, the
20-session regime); `curve_pca` gives level/slope/curvature.

Simplifications, on purpose:

  * ACT/365F simple year fractions; tenors are plain floats in years.
  * Interpolation is log-linear in discount factors (linear in z·t) between
    knots, flat in the zero rate beyond both ends. The bootstrap uses the SAME
    interpolation for coupon dates that fall between knots, so `par_rate` of a
    bootstrapped curve reproduces its inputs exactly.
  * Tenors under one year are money-market instruments: DF = 1/(1 + y·t).
    From one year on, par yields are coupon bonds paying `freq` times a year.
  * Coupon dates are t_i = T − k/freq for k = 0..n−1, dropping t ≤ start; a
    short first stub still carries a full 1/freq weight in the annuity.
  * Single-curve: the same curve projects forwards and discounts.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING

import numpy as np
from scipy.optimize import brentq, least_squares

from core.ficc.common import BP, KEY_TENORS, FICCError, tenor_label

if TYPE_CHECKING:                                    # data.py owns these shapes
    from core.ficc.data import CurvePanel, CurveSnapshot

_FD_H = 1e-4                                          # finite-difference step (years)
_TABLE_KEYS = ("tenor", "label", "zero", "df", "par", "fwd_1y")


def coupon_times(maturity: float, freq: int = 2, start: float = 0.0) -> np.ndarray:
    """Cashflow times T − k/freq for k = 0..n−1 that lie in (start, T], ascending."""
    if maturity <= start:
        raise ValueError(f"maturity {maturity} must exceed start {start}.")
    if freq < 1:
        raise ValueError(f"freq must be >= 1, got {freq}.")
    n = int(math.ceil((maturity - start) * freq - 1e-9))
    return np.sort(maturity - np.arange(n) / freq)


# --------------------------------------------------------------------------- #
# The curve
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class YieldCurve:
    date: str
    source: str
    tenors: tuple[float, ...]
    zeros: tuple[float, ...]          # continuously compounded, decimals
    method: str = "bootstrap"         # bootstrap | nelson_siegel | svensson | flat | shifted
    note: str = ""
    params: tuple[float, ...] = ()    # NS/NSS parameters when fitted

    def __post_init__(self) -> None:
        ts = tuple(float(t) for t in self.tenors)
        zs = tuple(float(z) for z in self.zeros)
        if not ts or len(ts) != len(zs):
            raise ValueError("tenors and zeros must be non-empty and the same length.")
        if ts[0] <= 0 or any(b <= a for a, b in zip(ts, ts[1:])):
            raise ValueError("tenors must be positive and strictly ascending.")
        if not all(math.isfinite(z) for z in zs):
            raise ValueError("zeros must be finite.")
        object.__setattr__(self, "tenors", ts)
        object.__setattr__(self, "zeros", zs)

    # -- discounting ------------------------------------------------------- #
    def _log_df(self, t) -> np.ndarray:
        t = np.asarray(t, dtype=float)
        if np.any(t < 0):
            raise ValueError("t must be >= 0.")
        ts, zs = np.asarray(self.tenors), np.asarray(self.zeros)
        zt = np.interp(t, ts, ts * zs)                 # linear in z·t between knots
        zt = np.where(t < ts[0], zs[0] * t, zt)        # flat zero beyond the ends
        zt = np.where(t > ts[-1], zs[-1] * t, zt)
        return -zt

    def df(self, t) -> float | np.ndarray:
        out = np.exp(self._log_df(t))
        return float(out) if out.ndim == 0 else out

    def zero(self, t) -> float | np.ndarray:
        t = np.asarray(t, dtype=float)
        with np.errstate(divide="ignore", invalid="ignore"):
            z = np.where(t > 0, -self._log_df(t) / np.where(t > 0, t, 1.0), self.zeros[0])
        return float(z) if z.ndim == 0 else z

    def fwd(self, t1: float, t2: float) -> float:
        """Simple-compounded forward between t1 and t2: (DF1/DF2 − 1)/(t2 − t1)."""
        if t2 <= t1:
            raise ValueError(f"t2 ({t2}) must exceed t1 ({t1}).")
        return (self.df(t1) / self.df(t2) - 1.0) / (t2 - t1)

    def inst_fwd(self, t: float) -> float:
        """−d ln DF/dt by central finite difference (one-sided at t < h)."""
        h = _FD_H
        if t < h:
            return float(-(self._log_df(t + h) - self._log_df(t)) / h)
        return float(-(self._log_df(t + h) - self._log_df(t - h)) / (2 * h))

    def annuity(self, maturity: float, freq: int = 2, start: float = 0.0) -> float:
        """Σ DF(t_i)/freq over coupon dates in (start, T]."""
        return float(np.sum(self.df(coupon_times(maturity, freq, start))) / freq)

    def par_rate(self, maturity: float, freq: int = 2, start: float = 0.0) -> float:
        """(DF(start) − DF(T)) / annuity(start, T, freq)."""
        return (self.df(start) - self.df(maturity)) / self.annuity(maturity, freq, start)

    # -- bumps ------------------------------------------------------------- #
    def shifted(self, bp: float) -> YieldCurve:
        """Parallel shift of every zero by `bp` basis points."""
        zs = tuple(z + bp * BP for z in self.zeros)
        return replace(self, zeros=zs, method="shifted",
                       note=f"{self.note} parallel {bp:+.1f}bp".strip())

    def key_rate_shifted(self, tenor: float, bp: float, *,
                         key_tenors: tuple[float, ...] = KEY_TENORS) -> YieldCurve:
        """Triangular bump of `bp` centred at `tenor`, falling to zero at the
        adjacent key tenors and flat beyond the first/last key tenor. The bump
        tenor and its neighbours are added as knots (at their interpolated
        zeros, which leaves the curve unchanged) so the bump always bites."""
        lower = max((k for k in key_tenors if k < tenor), default=None)
        upper = min((k for k in key_tenors if k > tenor), default=None)
        xp = [k for k in (lower, tenor, upper) if k is not None]
        fp = [0.0 if k != tenor else 1.0 for k in xp]
        knots = sorted(set(self.tenors) | set(xp))
        zs = np.asarray(self.zero(np.asarray(knots)), dtype=float)
        zs = zs + np.interp(knots, xp, fp) * bp * BP
        return replace(self, tenors=tuple(knots), zeros=tuple(float(z) for z in zs),
                       method="shifted",
                       note=f"{self.note} {tenor_label(tenor)} {bp:+.1f}bp".strip())

    # -- presentation ------------------------------------------------------ #
    def table(self) -> list[dict]:
        """Rows {tenor, label, zero, df, par, fwd_1y}. `par` is the semi-annual
        par rate from 1y on and the money-market simple yield below 1y, matching
        the bootstrap convention so a bootstrapped curve's table echoes its inputs."""
        rows = []
        for t in self.tenors:
            d = self.df(t)
            par = self.par_rate(t, 2) if t >= 1.0 else (1.0 / d - 1.0) / t
            rows.append(dict(zip(_TABLE_KEYS, (t, tenor_label(t), self.zero(t), d, par,
                                               self.fwd(t, t + 1.0)))))
        return rows


# --------------------------------------------------------------------------- #
# Builders
# --------------------------------------------------------------------------- #
def flat_curve(rate: float, *, tenors: tuple[float, ...] = KEY_TENORS, date: str = "",
               source: str = "FLAT") -> YieldCurve:
    return YieldCurve(date=date, source=source, tenors=tuple(tenors),
                      zeros=tuple(float(rate) for _ in tenors), method="flat")


def bootstrap_par_curve(tenors, par_yields, *, freq: int = 2, date: str = "", source: str = "",
                        note: str = "") -> YieldCurve:
    """Sequential bootstrap. Tenors < 1y are money-market: DF = 1/(1 + y·t). From
    1y on, each knot's zero solves 1 = y/freq·Σ DF(t_i) + DF(T) with brentq, where
    DFs on coupon dates between knots come from the curve's own interpolation
    over the knots solved so far plus the candidate. Works with any subset of
    tenors (a grid missing 1m or 6m simply extrapolates flat below its first knot)."""
    pairs = sorted((float(t), float(y)) for t, y in zip(tenors, par_yields))
    if len(pairs) != len(par_yields) or not pairs:
        raise ValueError("tenors and par_yields must be non-empty and the same length.")
    if pairs[0][0] <= 0 or any(b[0] <= a[0] for a, b in zip(pairs, pairs[1:])):
        raise ValueError("tenors must be positive and unique.")
    if not all(math.isfinite(y) for _, y in pairs):
        raise ValueError("par yields must be finite.")
    kt: list[float] = []
    kz: list[float] = []
    for t, y in pairs:
        if t < 1.0:
            if 1.0 + y * t <= 0:
                raise FICCError(f"Money-market yield {y} at {tenor_label(t)} is not positive.")
            z = math.log1p(y * t) / t
        else:
            times = coupon_times(t, freq)

            def gap(cand: float) -> float:
                c = YieldCurve(date, source, tuple(kt) + (t,), tuple(kz) + (cand,))
                return y / freq * float(np.sum(c.df(times))) + c.df(t) - 1.0

            lo, hi = -0.2, 1.0
            if gap(lo) * gap(hi) > 0:
                raise FICCError(f"Bootstrap cannot bracket a zero rate at {tenor_label(t)} "
                                f"for par yield {y:.4%}.")
            z = float(brentq(gap, lo, hi, xtol=1e-14, rtol=1e-14, maxiter=200))
        kt.append(t)
        kz.append(z)
    return YieldCurve(date=date, source=source, tenors=tuple(kt), zeros=tuple(kz),
                      method="bootstrap", note=note)


# --------------------------------------------------------------------------- #
# Nelson-Siegel / Svensson
# --------------------------------------------------------------------------- #
def _loading(t: np.ndarray, tau: float) -> tuple[np.ndarray, np.ndarray]:
    """Slope and curvature loadings with the t→0 limit handled."""
    x = t / tau
    safe = np.where(x > 1e-12, x, 1.0)
    slope = np.where(x > 1e-12, (1.0 - np.exp(-safe)) / safe, 1.0)
    return slope, slope - np.exp(-x)


def nelson_siegel(t, beta0: float, beta1: float, beta2: float, tau: float):
    t = np.asarray(t, dtype=float)
    s, c = _loading(t, tau)
    return beta0 + beta1 * s + beta2 * c


def svensson(t, b0: float, b1: float, b2: float, b3: float, tau1: float, tau2: float):
    t = np.asarray(t, dtype=float)
    s, c1 = _loading(t, tau1)
    _, c2 = _loading(t, tau2)
    return b0 + b1 * s + b2 * c1 + b3 * c2


@dataclass(frozen=True)
class NSFit:
    params: tuple[float, ...]
    fitted: np.ndarray = field(repr=False)
    rmse: float = 0.0
    method: str = "nelson_siegel"


def fit_nelson_siegel(tenors, yields, *, svensson: bool = False) -> NSFit:
    """Least squares on the par yields; betas bounded to ±0.5, tau to [0.1, 30].
    Deterministic start (β0 = long yield, β1 = short − long, β2 = 0, τ = 2y)."""
    t = np.asarray(tenors, dtype=float)
    y = np.asarray(yields, dtype=float)
    need = 6 if svensson else 4
    if t.size != y.size or t.size < need:
        raise FICCError(f"Need at least {need} points to fit "
                        f"{'Svensson' if svensson else 'Nelson-Siegel'}, got {t.size}.")
    if not np.all(np.isfinite(y)):
        raise ValueError("yields must be finite.")
    b = 0.5
    if svensson:
        fn, x0 = globals()["svensson"], [y[-1], y[0] - y[-1], 0.0, 0.0, 2.0, 8.0]
        bounds = ([-b, -b, -b, -b, 0.1, 0.1], [b, b, b, b, 30.0, 30.0])
    else:
        fn, x0 = nelson_siegel, [y[-1], y[0] - y[-1], 0.0, 2.0]
        bounds = ([-b, -b, -b, 0.1], [b, b, b, 30.0])
    x0 = np.clip(np.asarray(x0, dtype=float), bounds[0], bounds[1])
    res = least_squares(lambda p: fn(t, *p) - y, x0, bounds=bounds, method="trf")
    fitted = fn(t, *res.x)
    return NSFit(params=tuple(float(p) for p in res.x), fitted=fitted,
                 rmse=float(np.sqrt(np.mean((fitted - y) ** 2))),
                 method="svensson" if svensson else "nelson_siegel")


def curve_from_snapshot(snap: CurveSnapshot, *, method: str = "bootstrap") -> YieldCurve:
    """bootstrap: the par yields as given. nelson_siegel / svensson: fit the par
    curve, evaluate it on KEY_TENORS ∪ input tenors, then bootstrap that."""
    if method == "bootstrap":
        return bootstrap_par_curve(snap.tenors, snap.par_yields, date=snap.date,
                                   source=snap.source, note=snap.note)
    if method not in ("nelson_siegel", "svensson"):
        raise FICCError(f"Unknown curve method {method!r}.")
    fit = fit_nelson_siegel(snap.tenors, snap.par_yields, svensson=method == "svensson")
    grid = np.array(sorted(set(KEY_TENORS) | set(float(t) for t in snap.tenors)))
    fn = svensson if method == "svensson" else nelson_siegel
    curve = bootstrap_par_curve(grid, fn(grid, *fit.params), date=snap.date, source=snap.source)
    note = f"{snap.note} {fit.method} fit, rmse {fit.rmse / BP:.1f}bp".strip()
    return replace(curve, method=method, params=fit.params, note=note)


# --------------------------------------------------------------------------- #
# Curve report
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class CurveReport:
    curve: YieldCurve
    snapshot: CurveSnapshot
    descriptors: dict[str, float]
    shape: str                        # normal | flat | inverted | humped
    regime: str                       # bull/bear steepener/flattener, parallel up/down, unchanged
    changes: dict[str, float]         # Δ par yield over `lookback` per tenor label, plus 2s10s
    ns: NSFit
    lookback: int


def _par_at(snap, t: float) -> float:
    """Par yield at tenor t, linearly interpolated over the snapshot grid
    (clamped at the ends, so a grid ending at 20y reports its 20y as '30y')."""
    return float(np.interp(t, np.asarray(snap.tenors, dtype=float),
                           np.asarray(snap.par_yields, dtype=float)))


def _shape(snap) -> str:
    p2, p30 = _par_at(snap, 2.0), _par_at(snap, 30.0)
    s = _par_at(snap, 10.0) - p2
    if s > 25 * BP:
        return "normal"
    if s < -10 * BP:
        return "inverted"
    mids = [y for t, y in zip(snap.tenors, snap.par_yields) if 2.0 < t < 30.0]
    if any(m > p2 + 10 * BP and m > p30 + 10 * BP for m in mids):
        return "humped"
    return "flat"


def _regime(d10: float, d2: float, dslope: float) -> str:
    """bull/bear = 10y down/up ≥ 5bp. If the slope moved ≥ 5bp while the 10y
    stayed within 5bp, bull/bear follows the sign of the 2y-10y average move."""
    if abs(dslope) >= 5 * BP:
        move = d10 if abs(d10) >= 5 * BP else (d10 + d2) / 2
        tone = "bull" if move < 0 else "bear"
        return f"{tone} {'steepener' if dslope > 0 else 'flattener'}"
    if abs(d10) >= 5 * BP:
        return "parallel up" if d10 > 0 else "parallel down"
    return "unchanged"


def analyze_curve(panel: CurvePanel, *, lookback: int = 20,
                  method: str = "bootstrap") -> CurveReport:
    """Latest snapshot → curve + descriptors + shape; `lookback` sessions back →
    regime and per-tenor changes. Descriptors: 2s10s, 5s30s, 3m10y, 2s5s10s_fly
    (2·5y − 2y − 10y), level (mean of 2y/5y/10y) from par yields; 1y1y, 2y1y,
    5y5y are simple forwards off the curve; 1y_fwd_1y_ahead = 1y1y − 1y par,
    i.e. the move the curve prices into the 1y rate over the next year."""
    if len(panel) < 2:
        raise FICCError("Need at least two curve dates to analyze.")
    lookback = max(1, min(int(lookback), len(panel) - 1))
    snap = panel.latest()
    prev = panel.at(len(panel) - 1 - lookback)
    curve = curve_from_snapshot(snap, method=method)
    ns = fit_nelson_siegel(snap.tenors, snap.par_yields, svensson=method == "svensson")
    p = {t: _par_at(snap, t) for t in (0.25, 1.0, 2.0, 5.0, 10.0, 30.0)}
    descriptors = {
        "2s10s": p[10.0] - p[2.0],
        "5s30s": p[30.0] - p[5.0],
        "3m10y": p[10.0] - p[0.25],
        "2s5s10s_fly": 2 * p[5.0] - p[2.0] - p[10.0],
        "level": (p[2.0] + p[5.0] + p[10.0]) / 3,
        "1y1y": curve.fwd(1.0, 2.0),
        "2y1y": curve.fwd(2.0, 3.0),
        "5y5y": curve.fwd(5.0, 10.0),
        "1y_fwd_1y_ahead": curve.fwd(1.0, 2.0) - p[1.0],
    }
    changes = {tenor_label(t): float(y_now - y_then) for t, y_now, y_then
               in zip(snap.tenors, snap.par_yields, prev.par_yields)}
    d2 = p[2.0] - _par_at(prev, 2.0)
    d10 = p[10.0] - _par_at(prev, 10.0)
    changes["2s10s"] = d10 - d2
    return CurveReport(curve=curve, snapshot=snap, descriptors=descriptors, shape=_shape(snap),
                       regime=_regime(d10, d2, d10 - d2), changes=changes, ns=ns,
                       lookback=lookback)


# --------------------------------------------------------------------------- #
# PCA
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class PCAResult:
    tenors: tuple[float, ...]
    loadings: np.ndarray = field(repr=False)     # K x n
    explained: np.ndarray = field(repr=False)    # n, fractions of variance
    scores: np.ndarray = field(repr=False)       # T-1 x n (T x n on levels)
    latest_scores: np.ndarray = field(repr=False)
    labels: tuple[str, ...] = ("level", "slope", "curvature")


def curve_pca(panel: CurvePanel, *, n: int = 3, use_changes: bool = True) -> PCAResult:
    """SVD of demeaned daily changes (bp) — or demeaned levels in bp when
    use_changes=False. PC1 is signed so its loadings are positive, PC2 so the
    long end loads positive, later PCs so their largest loading is positive."""
    if len(panel) < 60:
        raise FICCError(f"Need at least 60 curve dates for PCA, got {len(panel)}.")
    y = np.asarray(panel.yields, dtype=float) / BP
    x = np.diff(y, axis=0) if use_changes else y
    x = x - x.mean(axis=0)
    n = max(1, min(int(n), x.shape[1]))
    _, s, vt = np.linalg.svd(x, full_matrices=False)
    loadings = vt[:n].T.copy()
    for j in range(n):
        pivot = (loadings[:, 0].mean() if j == 0 else loadings[-1, 1] if j == 1
                 else loadings[np.argmax(np.abs(loadings[:, j])), j])
        if pivot < 0:
            loadings[:, j] *= -1
    scores = x @ loadings
    explained = (s[:n] ** 2) / np.sum(s ** 2)
    names = ("level", "slope", "curvature")
    labels = tuple(names[j] if j < 3 else f"pc{j + 1}" for j in range(n))
    return PCAResult(tenors=tuple(float(t) for t in panel.tenors), loadings=loadings,
                     explained=explained, scores=scores, latest_scores=scores[-1].copy(),
                     labels=labels)


# --------------------------------------------------------------------------- #
# Self-check
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    from core.ficc.common import UST_TENORS

    # Flat 5% semi-annual par curve → continuous zero 2·ln(1.025) from 1y on.
    flat = bootstrap_par_curve(UST_TENORS, [0.05] * len(UST_TENORS))
    z_cont = 2 * math.log1p(0.025)
    for t, z in zip(flat.tenors, flat.zeros):
        if t >= 1.0:
            assert abs(z - z_cont) < 1e-6, (t, z, z_cont)
        assert abs(flat.par_rate(t) - 0.05) < 1e-8 if t >= 1 else True
    assert flat.df(0.0) == 1.0
    grid = np.linspace(0.0, 40.0, 401)
    assert np.all(np.diff(flat.df(grid)) < 0), "DF must fall with tenor"

    # Round-trip on a sloped, kinked par curve; missing 1m/6m must still work.
    par = [0.052, 0.051, 0.050, 0.047, 0.044, 0.043, 0.042, 0.043, 0.044, 0.047, 0.046]
    c = bootstrap_par_curve(UST_TENORS, par, date="2026-09-04", source="TEST")
    for t, y in zip(UST_TENORS, par):
        got = c.par_rate(t) if t >= 1.0 else (1.0 / c.df(t) - 1.0) / t
        assert abs(got - y) < 1e-8, (t, got, y)
    sparse = bootstrap_par_curve([1.0, 2.0, 5.0, 10.0, 30.0], [0.047, 0.044, 0.042, 0.044, 0.046])
    assert abs(sparse.par_rate(30.0) - 0.046) < 1e-8
    assert all(k in c.table()[3] for k in _TABLE_KEYS)

    # Bumps: parallel moves every zero; a key-rate bump bites only near its tenor.
    up = c.shifted(10.0)
    assert all(abs((zu - z0) - 10 * BP) < 1e-12 for zu, z0 in zip(up.zeros, c.zeros))
    kr = c.key_rate_shifted(5.0, 10.0)
    assert abs(kr.zero(5.0) - c.zero(5.0) - 10 * BP) < 1e-12
    assert abs(kr.zero(10.0) - c.zero(10.0)) < 1e-12 and abs(kr.zero(3.0) - c.zero(3.0)) < 1e-12
    # between knots the bump interpolates in z·t: 10bp·5/(2·6) at 6y
    assert abs(kr.zero(6.0) - c.zero(6.0) - 10 * BP * 5 / 12) < 1e-12
    edge = c.key_rate_shifted(30.0, 10.0)
    assert abs(edge.zero(40.0) - c.zero(40.0) - 10 * BP) < 1e-12, "flat beyond the last key"
    assert abs(c.fwd(1.0, 2.0) - (c.df(1.0) / c.df(2.0) - 1.0)) < 1e-14
    assert abs(c.inst_fwd(4.0) - c.zero(4.0)) < 0.02

    # Nelson-Siegel reproduces its own shape; a fit on a panel is tight.
    ns_par = nelson_siegel(np.array(UST_TENORS), 0.045, -0.01, 0.02, 2.0)
    fit = fit_nelson_siegel(UST_TENORS, ns_par)
    assert fit.rmse < 1e-6, fit.rmse
    assert fit_nelson_siegel(UST_TENORS, ns_par, svensson=True).rmse < 1e-6

    try:
        from core.ficc.data import synthetic_curve_panel
        panel = synthetic_curve_panel(days=200)
    except ImportError:                              # data.py not built yet: local stand-in
        from types import SimpleNamespace as _NS
        rng = np.random.default_rng(7)
        b = np.array([0.045, -0.01, 0.01, 2.0])
        rows = []
        for _ in range(200):
            b = b + rng.normal(0, [0.0004, 0.0006, 0.0008, 0.0], 4)
            rows.append(nelson_siegel(np.array(UST_TENORS), *b) + rng.normal(0, 0.0002, 11))
        ys = np.array(rows)
        dates = tuple(f"D{i:03d}" for i in range(200))

        def _snap(i: int):
            return _NS(date=dates[i], source="SYNTHETIC", tenors=UST_TENORS,
                       par_yields=tuple(float(v) for v in ys[i]), note="stand-in")

        panel = _NS(source="SYNTHETIC", dates=dates, tenors=UST_TENORS, yields=ys, note="",
                    latest=lambda: _snap(199), at=_snap)
        panel.__class__.__len__ = lambda self: 200
    snap = panel.latest()
    assert fit_nelson_siegel(snap.tenors, snap.par_yields).rmse < 5 * BP
    for m in ("bootstrap", "nelson_siegel", "svensson"):
        rep = analyze_curve(panel, lookback=20, method=m)
        assert rep.curve.method == m
        assert rep.shape in ("normal", "flat", "inverted", "humped")
        assert rep.regime in ("bull steepener", "bear steepener", "bull flattener",
                              "bear flattener", "parallel up", "parallel down", "unchanged")
        assert set(rep.descriptors) >= {"2s10s", "5s30s", "3m10y", "2s5s10s_fly", "level",
                                        "1y1y", "2y1y", "5y5y", "1y_fwd_1y_ahead"}
        assert "2s10s" in rep.changes and "10y" in rep.changes
    assert _regime(-8 * BP, -20 * BP, 12 * BP) == "bull steepener"
    assert _regime(8 * BP, 0.0, 8 * BP) == "bear steepener"
    assert _regime(8 * BP, 0.0, 0.0) == "parallel up"
    assert _regime(1 * BP, 0.0, 0.0) == "unchanged"

    pca = curve_pca(panel)
    assert pca.explained[0] > 0.5 and np.all(pca.loadings[:, 0] > 0)
    assert pca.loadings[-1, 1] > 0 and pca.scores.shape == (len(panel) - 1, 3)
    assert abs(float(np.sum(pca.explained))) <= 1.0 + 1e-12
    print("ok")
