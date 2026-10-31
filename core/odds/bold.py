"""References on the odds card (spec 3, 7.4): the fair-game ceiling and its "1 in N", the KRX structural maximum of a
buy-and-hold leg (Q44), the brackets needed to tell a typed win rate from the no-edge one (spec 7.2), exact bold play
at even money (Dubins-Savage; regression tests only) and the estimated bracket reference (Q33; amber only).

Pure: no clock, no file, no network (Q42). Imports the standard library and numpy only."""
from __future__ import annotations

import fractions
import math
import numbers

import numpy as np

_Z_ALPHA = 1.645        # one-sided test at 5% (spec 7.2)
_Z_POWER = 0.842        # 80% power (spec 7.2)
_R_BINS = 32            # bracket_reference: equal-count bins of the net return per unit stake (contract 9.1)
_D_BINS = 4             # equal-count bins of the duration in checks
_NODES = 129            # wealth nodes from l_min to the target
_STAKES = 16            # stake choices: k/16 of the floor-protected room, k = 1..16
_HALF = fractions.Fraction(1, 2)


def _real(*values) -> bool:
    """True when every value is a finite real number (bool excluded)."""
    return all(isinstance(v, numbers.Real) and not isinstance(v, bool) and math.isfinite(v) for v in values)


def _span(w0, l_min, target) -> tuple[fractions.Fraction, fractions.Fraction]:
    """(W0 - L_min, T - L_min), exact from the float inputs; ValueError unless finite l_min < w0 < target."""
    if not (_real(w0, l_min, target) and l_min < w0 < target):
        raise ValueError(f"need finite l_min < w0 < target, got w0={w0!r}, l_min={l_min!r}, target={target!r}")
    low = fractions.Fraction(l_min)
    return fractions.Fraction(w0) - low, fractions.Fraction(target) - low


def ceiling(w0: float, l_min: float, target: float) -> float:
    """(W0 - L_min) / (T - L_min): no plan without a real edge that keeps the floor L_min beats it (Ville; spec 3,
    Q32). Computed exactly, then rounded once."""
    gain, span = _span(w0, l_min, target)
    return float(gain / span)


def ceiling_one_in(w0: float, l_min: float, target: float) -> int:
    """floor((T - L_min) / (W0 - L_min)), exactly: the N of "1 in N" for a ceiling below 1%. The ceiling is an upper
    bound, so N rounds down and never prints a smaller chance than the bound."""
    gain, span = _span(w0, l_min, target)
    return math.floor(span / gain)


def structural_max(limits: tuple[float, ...]) -> float:
    """(1 + l1)/(1 - l1) x prod(1 + li, i >= 2) over the dated daily price limits l1..ln of a leg's n KRX sessions
    (spec 3, 7.4; Q44): the most a position bought at the first open and held can multiply. Buy-and-hold KRX legs
    only; repeated intraday round trips, IPO days and special reference-price regimes are not bounded this way."""
    limits = tuple(limits)
    if not limits or not all(_real(v) and 0.0 < v < 1.0 for v in limits):
        raise ValueError(f"need one price limit in (0, 1) per session, got {limits!r}")
    first = limits[0]
    return (1.0 + first) / (1.0 - first) * math.prod(1.0 + v for v in limits[1:])


def brackets_needed(p: float, p0: float) -> float:
    """Resolved brackets needed to tell the typed win rate p from the no-edge p0, one-sided at 5% with 80% power,
    assuming independent brackets (spec 7.2): ceil(((1.645 sqrt(p0 (1 - p0)) + 0.842 sqrt(p (1 - p))) / |p - p0|)
    ** 2); math.inf when p == p0."""
    if not (_real(p, p0) and 0.0 <= p <= 1.0 and 0.0 <= p0 <= 1.0):
        raise ValueError(f"need win rates in [0, 1], got p={p!r}, p0={p0!r}")
    if p == p0:
        return math.inf
    root = (_Z_ALPHA * math.sqrt(p0 * (1.0 - p0)) + _Z_POWER * math.sqrt(p * (1.0 - p))) / abs(p - p0)
    return float(math.ceil(root * root))


def bold_even(x: fractions.Fraction, p: fractions.Fraction) -> fractions.Fraction:
    """Exact P(reach 1 from x) under bold play at even money with win chance p (Dubins-Savage): f(0) = 0, f(1) = 1,
    f(1/2) = p, f(x) = p f(2x) below 1/2 and p + (1 - p) f(2x - 1) above it. The doubling orbit of a rational x ends
    at 0, 1/2 or 1, or comes back to a point it has visited; the repeat closes a linear equation, solved exactly.
    Regression tests only (spec 7.4)."""
    for v in (x, p):
        if isinstance(v, bool) or not isinstance(v, (int, fractions.Fraction)):
            raise TypeError(f"bold_even takes exact fractions.Fraction values, got {v!r}")
    x, p = fractions.Fraction(x), fractions.Fraction(p)
    if not (0 <= x <= 1 and 0 <= p <= 1):
        raise ValueError(f"need 0 <= x <= 1 and 0 <= p <= 1, got x={x}, p={p}")
    a, b, seen = fractions.Fraction(0), fractions.Fraction(1), {}
    while True:                                  # invariant: f(start) = a + b f(x)
        if b == 0 or x == 0:
            return a
        if x == 1:
            return a + b
        if x == _HALF:
            return a + b * p
        if x in seen:                            # a0 + b0 f(x) = a + b f(x), so f(x) = (a - a0) / (b0 - b)
            a0, b0 = seen[x]
            return a0 + b0 * (a - a0) / (b0 - b)
        seen[x] = (a, b)
        if x < _HALF:
            b, x = b * p, 2 * x
        else:
            a, b, x = a + b * p, b * (1 - p), 2 * x - 1


def _bins(v: np.ndarray, k: int) -> tuple[np.ndarray, list[np.ndarray]]:
    """Equal-count bins of v by rank: (the bin of each value, the indices in each non-empty bin)."""
    parts = [part for part in np.array_split(np.argsort(v, kind="stable"), k) if part.size]
    label = np.empty(v.size, dtype=np.int64)
    for i, part in enumerate(parts):
        label[part] = i
    return label, parts


def bracket_reference(r, d, *, w0, l_min, target, n_checks, kappa, phi_buy, phi_sell, r_exit) -> float:
    """An ESTIMATED reference (Q33, contract 9.1), never a certified bound and never a red flag: the best chance of
    reaching the target within n_checks checks when each bracket stakes k/16 of the floor-protected room
    max(0, w - l_min - phi_buy - r_exit) / (1 + kappa) on the binned joint law of (r, d). r is the net return per unit
    stake (exit proceeds net of the proportional exit charge, minus the stake and its proportional entry charge, over
    the stake), d the checks from entry to exit fill. Dynamic programme over (wealth on 129 nodes from l_min to the
    target, checks left); interpolation is clamped at both grid ends. kappa is the buy side's base rate at p0."""
    r = np.asarray(r, dtype=float)
    d = np.asarray(d, dtype=float)
    if (r.ndim != 1 or r.shape != d.shape or r.size == 0 or not (np.isfinite(r).all() and np.isfinite(d).all())
            or d.min() < 1.0):
        raise ValueError("need equal-length non-empty 1-d arrays: finite r, and durations d >= 1")
    if isinstance(n_checks, bool) or not isinstance(n_checks, numbers.Integral) or n_checks < 0:
        raise ValueError(f"need a whole number of checks >= 0, got {n_checks!r}")
    if not (_real(w0, l_min, target, kappa, phi_buy, phi_sell, r_exit) and l_min < target and kappa >= 0.0
            and min(phi_buy, phi_sell, r_exit) >= 0.0):
        raise ValueError("need finite w0, l_min < target, kappa >= 0 and charges >= 0")
    r_label, r_parts = _bins(r, _R_BINS)
    d_label, d_parts = _bins(d, _D_BINS)
    r_value = np.array([r[part].mean() for part in r_parts])
    d_value = np.array([math.ceil(d[part].mean()) for part in d_parts])
    width = len(d_parts)
    counts = np.bincount(r_label * width + d_label, minlength=len(r_parts) * width)
    cells = np.flatnonzero(counts)                                    # cells with weight 0 dropped
    weight, cell_r, cell_d = counts[cells] / r.size, r_value[cells // width], d_value[cells % width]
    grid = np.linspace(l_min, target, _NODES)
    top = (grid >= target).astype(float)
    room = np.maximum(0.0, grid - l_min - phi_buy - r_exit) / (1.0 + kappa)
    stakes = np.arange(1, _STAKES + 1)[:, None] / _STAKES * room[None, :]          # (stake choice, node)
    groups = []                                   # per duration: (checks, wealth after the bracket, cell weights)
    for checks in np.unique(cell_d):
        pick = cell_d == checks
        after = grid + stakes[:, None, :] * cell_r[pick][None, :, None] - phi_buy - phi_sell   # (stake, cell, node)
        groups.append((int(checks), after, weight[pick][None, :, None]))
    value = [top]                                 # value[t]: the chance of reaching the target with t checks left
    for t in range(1, int(n_checks) + 1):
        bet = sum((np.interp(after, grid, value[max(t - checks, 0)]) * w).sum(axis=1) for checks, after, w in groups)
        value.append(np.maximum(np.maximum(top, value[t - 1]), bet.max(axis=0)))
    return float(np.interp(w0, grid, value[int(n_checks)]))
