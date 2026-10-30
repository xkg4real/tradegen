"""The no-edge models of the odds core (spec 7.2, 7.3; odds plan Q10, Q12, Q34): the copied constants, block length
and Sharpe (O1: each pinned against its original by tests/odds_models.py), the two-point bootstrap's row magnitudes,
block lengths, index generator, kernel and tilt, the market seed with its streams, and the GARCH-t copy with its
pilot checks (O1: pinned against core/quant/garch.py by tests/odds_garch.py). Pure: no clock, no file, no network."""
from __future__ import annotations

import hashlib
import math
from collections.abc import Iterator
from dataclasses import dataclass
from functools import lru_cache
from typing import TYPE_CHECKING

import numpy as np
from scipy import stats
from scipy.integrate import quad
from scipy.optimize import minimize
from scipy.signal import lfilter
from scipy.special import gammaln

from core.compliance import model

if TYPE_CHECKING:
    from core.odds import plan

# --------------------------------------------------------------------------- #
# Copied constants and pieces (contract 7.1)
# --------------------------------------------------------------------------- #
LIVE_SHARPE_MULTIPLIER = 0.60          # == core.quant.gate_stats.LIVE_SHARPE_MULTIPLIER
Z_BOUND = 22                           # == core.quant.garch.Z_BOUND
TRADING_DAYS = 252                     # == core.quant.garch.TRADING_DAYS == core.quant.validate.TRADING_DAYS
NU_NORMAL = 100.0                      # == core.quant.garch.NU_NORMAL


def _optimal_block_length(x) -> tuple[float, float]:
    """Copy of core.quant.gate_stats.optimal_block_length (bit-exact): the (stationary, circular) Politis-White
    block lengths of one series; NaN-free finite input, n >= 20."""
    x = np.asarray(x, dtype=float).ravel()
    if x.size < 20 or not np.all(np.isfinite(x)):
        raise ValueError("pw_block needs at least 20 finite observations")
    nobs = x.size
    eps = x - x.mean()
    b_max = math.ceil(min(3 * math.sqrt(nobs), nobs / 3))
    kn = max(5, int(math.log10(nobs)))
    m_max = int(math.ceil(math.sqrt(nobs))) + kn
    cv = 2 * math.sqrt(math.log10(nobs) / nobs)          # the conservative +/- 2 sqrt(log10 n / n) band
    acv = np.zeros(m_max + 1)
    abs_acorr = np.zeros(m_max + 1)
    opt_m = None
    for i in range(m_max + 1):
        v1 = eps[i + 1:] @ eps[i + 1:]
        v2 = eps[:-(i + 1)] @ eps[:-(i + 1)]
        cross = eps[i:] @ eps[:nobs - i]
        acv[i] = cross / nobs
        abs_acorr[i] = abs(cross) / math.sqrt(v1 * v2) if v1 > 0 and v2 > 0 else 0.0
        if i >= kn and opt_m is None and np.all(abs_acorr[i - kn:i] < cv):
            opt_m = i - kn                                  # first run of kn insignificant autocorrelations
    m = min(2 * max(opt_m, 1) if opt_m is not None else m_max, m_max)
    g, lr_acv = 0.0, acv[0]
    for k in range(1, m + 1):
        lam = 1.0 if k / m <= 0.5 else 2.0 * (1.0 - k / m)  # flat-top (trapezoid) kernel
        g += 2 * lam * k * acv[k]
        lr_acv += 2 * lam * acv[k]
    if lr_acv <= 0:
        return 1.0, 1.0
    b_sb = ((2 * g ** 2) / (2 * lr_acv ** 2)) ** (1 / 3) * nobs ** (1 / 3)
    b_cb = ((2 * g ** 2) / (4 / 3 * lr_acv ** 2)) ** (1 / 3) * nobs ** (1 / 3)
    return float(min(b_sb, b_max)), float(min(b_cb, b_max))


def pw_block(x) -> float:
    """The stationary Politis-White block length: gate_stats.pw_block(x, kind="stationary")."""
    return _optimal_block_length(x)[0]


def sharpe(daily) -> float:
    """Copy of core.quant.validate.sharpe: the annualised Sharpe ratio of the finite entries (nan under two)."""
    d = np.asarray(daily, dtype=float)
    d = d[np.isfinite(d)]
    if d.size < 2:
        return float("nan")
    sd = float(np.std(d, ddof=1))
    return float(np.mean(d) / sd * math.sqrt(TRADING_DAYS)) if sd > 0 else 0.0


# --------------------------------------------------------------------------- #
# The two-point bootstrap (contract 7.2)
# --------------------------------------------------------------------------- #
def rows(series: plan.Series) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(m_o, m_i, r) for t = 1..n-1: the overnight move m_o = |ln(open_t / close_{t-1})|, the intraday move
    m_i = |ln(close_t / open_t)| and the close-to-close log return r = ln(close_t / close_{t-1}) (spec 7.2)."""
    o = np.asarray(series.open, dtype=float)
    c = np.asarray(series.close, dtype=float)
    return np.abs(np.log(o[1:] / c[:-1])), np.abs(np.log(c[1:] / o[1:])), np.log(c[1:] / c[:-1])


def block_length(r: np.ndarray) -> float:
    """The mean block b = max(1, pw(r), pw(r^2)) (spec 7.2 "Blocks"; floored at 1 because pw_block falls below 1 on
    white noise, Q10)."""
    r = np.asarray(r, dtype=float)
    return float(max(1.0, pw_block(r), pw_block(r * r)))


def variant_block(b: float, mult: float, n_rows: int) -> float:
    """A sensitivity block: max(1, floor(mult * b + 0.5)), capped at the history length (Q10: round half up;
    Python's round() rounds half to even, so it is never used here)."""
    return float(min(max(1, math.floor(mult * b + 0.5)), n_rows))


def indices(rng: np.random.Generator, n_rows: int, n_paths: int, block: float) -> Iterator[np.ndarray]:
    """An endless generator of (n_paths,) row indices, one array per step: the Politis-Romano stationary bootstrap,
    vectorised over paths. Step 0 is uniform; each later step restarts a path at a fresh uniform row with
    probability 1 / block, else moves it to the next row mod n_rows. Both draws are made at every step, the restart
    first, so the stream never depends on the outcome. The mean block is exactly `block`."""
    if not (math.isfinite(block) and block >= 1.0):
        raise ValueError(f"the mean block must be a finite number >= 1, got {block!r}")
    return _steps(rng, n_rows, n_paths, 1.0 / block)


def _steps(rng: np.random.Generator, n_rows: int, n_paths: int, restart_p: float) -> Iterator[np.ndarray]:
    idx = rng.integers(0, n_rows, n_paths)
    while True:
        yield idx
        restart = rng.random(n_paths) < restart_p
        fresh = rng.integers(0, n_rows, n_paths)
        idx = np.where(restart, fresh, (idx + 1) % n_rows)


def tilt(q: np.ndarray, theta: float) -> np.ndarray:
    """The assumed-edge tilt q' = q e^theta / (q e^theta + 1 - q) (spec 7.2). Theta 0 gives q back bit for bit
    (exp(0.0) is 1.0 and q + (1 - q) rounds to 1.0 for every q in [0, 1]), so the no-edge kernel is untouched; every
    theta keeps q = 0 and q = 1."""
    q = np.asarray(q, dtype=float)
    w = q * math.exp(theta)
    return w / (w + (1.0 - q))


def _points(p, m, d_edge, u_edge) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(x_u, x_d, q) of the kernel: x_u = min(p e^m, U), x_d = max(p e^-m, D), q = (p - x_d) / (x_u - x_d) where
    x_u > x_d, else 0 (there x_u = x_d = p)."""
    p, m = np.asarray(p, dtype=float), np.asarray(m, dtype=float)
    x_u = np.minimum(p * np.exp(m), u_edge)
    x_d = np.maximum(p * np.exp(-m), d_edge)
    gap = x_u - x_d
    q = np.divide(p - x_d, gap, out=np.zeros(gap.shape), where=gap > 0)
    return x_u, x_d, q


def kernel(p, m, d_edge, u_edge, u, theta: float = 0.0) -> np.ndarray:
    """One check of the no-edge law (spec 7.2 "The kernel"): x_u where u < tilt(q, theta), else x_d. With theta 0,
    q x_u + (1 - q) x_d == p to rounding, so the price is a conditional martingale; it never leaves [D, U], and a
    price at an edge stays there (q is 1 at U and 0 at D)."""
    x_u, x_d, q = _points(p, m, d_edge, u_edge)
    return np.where(u < tilt(q, theta), x_u, x_d)


# --------------------------------------------------------------------------- #
# Seeds and streams (contract 7.2; spec 7.3; Q12, Q34)
# --------------------------------------------------------------------------- #
STREAMS = {"index": 1, "sign": 2, "garch": 3, "pilot": 4, "tilt": 5, "kelly": 6, "refit": 7, "replay": 8,
           "refit_series": 9, "replay_sign": 10}
SEED_TAG = b"tradegen-odds/seed/1\x00"


def _input_md5(rep: plan.ReplayInput) -> str:
    """md5 of the canonical JSON {symbol, source, dates, close} of the replay's input closes (contract 7.5
    `input_md5`)."""
    text = model.canonical_json({"symbol": rep.input_symbol, "source": rep.input_source,
                                 "dates": list(rep.input_dates), "close": list(rep.input_close)})
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def _array_md5(values) -> str:
    """md5 of the little-endian float64 bytes of `values` (contract 7.5 `pnl_md5`, `turnover_md5`)."""
    return hashlib.md5(np.ascontiguousarray(values, dtype="<f8").tobytes()).hexdigest()


def data_hashes(series: plan.Series, replay: plan.ReplayInput | None) -> tuple[str, ...]:
    """The data hashes that enter the market seed, sorted: the series md5 and every component md5, plus for a
    replay leg the input md5 and the pnl md5 (recomputed here; verify_replay requires both to equal their pins)."""
    hashes = [series.md5, *(md5 for _, md5 in series.components)]
    if replay is not None:
        hashes += [_input_md5(replay), _array_md5(replay.oos_pnl)]
    return tuple(sorted(hashes))


def market_seed(data_hashes, calendar_digest: str, comparison_id: str, run_counter: int) -> bytes:
    """The 32-byte market seed of spec 7.3 in the byte layout of Q34. No plan field enters it, so every plan on the
    same data in one comparison shares every stream, and the owner never chooses it. ValueError unless every part is
    a string with no NUL (a NUL would let two different inputs share bytes) and the run counter an int in
    [0, 2**64). One str for data_hashes, no hash, or an empty hash is refused too: each would share bytes with
    another input (the sorted characters of an md5; () and ("",))."""
    if isinstance(data_hashes, str):
        raise ValueError("market_seed needs an iterable of hashes, not one string")
    hashes = tuple(data_hashes)
    if not hashes or not all(type(x) is str and x for x in hashes):
        raise ValueError("market_seed needs one or more hashes, each a non-empty string")
    if not all(type(x) is str and "\x00" not in x for x in (*hashes, calendar_digest, comparison_id)):
        raise ValueError("market_seed needs strings with no NUL character")
    if type(run_counter) is not int or not 0 <= run_counter < 2 ** 64:
        raise ValueError(f"market_seed needs a run counter in [0, 2**64), got {run_counter!r}")
    return hashlib.sha256(SEED_TAG + "\x00".join(sorted(hashes)).encode("ascii") + b"\x00"
                          + calendar_digest.encode("ascii") + b"\x00" + comparison_id.encode("utf-8") + b"\x00"
                          + run_counter.to_bytes(8, "big")).digest()


def seed_sequence(seed: bytes, chunk: int, name: str, *extra: int) -> np.random.SeedSequence:
    """The SeedSequence of stream `name` in chunk `chunk` (spec 7.3): entropy int.from_bytes(seed, "big"), spawn_key
    (chunk, STREAMS[name], *extra). The copied GARCH code calls default_rng(seed) and takes it directly."""
    return np.random.SeedSequence(int.from_bytes(seed, "big"), spawn_key=(chunk, STREAMS[name], *extra))


def stream(seed: bytes, chunk: int, name: str, *extra: int) -> np.random.Generator:
    """The Generator of stream `name`: np.random.default_rng(seed_sequence(seed, chunk, name, *extra)), a PCG64
    (default_rng passes a SeedSequence through)."""
    return np.random.default_rng(seed_sequence(seed, chunk, name, *extra))


# --------------------------------------------------------------------------- #
# GARCH-t copy (contract 7.3; O1: copied from core/quant/garch.py and pinned against it by tests/odds_garch.py)
# --------------------------------------------------------------------------- #
_SIG_LO, _SIG_HI = 1e-6, 0.25          # == garch._SIG_LO, garch._SIG_HI: the correction table's daily-sigma grid
_BOUNDS: dict[str, tuple[float, float]] = {   # == garch.BOUNDS on the four fitted coordinates
    "omega": (1e-12, math.inf),        # daily variance units
    "alpha": (0.0, 0.5),
    "beta": (0.0, 0.999),
    "eta": (0.0, 0.4),                 # the tail is fitted as eta = 1/nu; eta = 0 IS the normal
}
_STATIONARITY_MAX = 0.9995             # == garch.STATIONARITY_MAX
_ETA_EPS = 1e-10                       # == garch._ETA_EPS: below this eta the density IS the normal
_PENALTY = 1e10                        # == garch._PENALTY
_MIN_OBS = 100                         # == garch._MIN_OBS
_OMEGA_SCALE = 1e6                     # == garch._OMEGA_SCALE


@dataclass(frozen=True, kw_only=True)
class GarchParams:
    """The fields of garch.GarchFit that the odds engine runs on: GARCH(1,1) with Student-t innovations, mu fixed at
    the sample mean of the daily log returns. nu is inf when the fitted eta is 0 (the t is the normal);
    cond_vol_last is the annualised (TRADING_DAYS) next-session forecast sqrt(sigma^2_{T+1} * 252)."""
    dist: str
    omega: float
    alpha: float
    beta: float
    nu: float
    mean_daily: float
    n_obs: int
    cond_vol_last: float
    converged: bool
    at_bound: tuple[str, ...]


def _variance_path(eps2: np.ndarray, omega: float, alpha: float, beta: float, s2_init: float) -> np.ndarray:
    """Copy of garch._variance_path: sigma^2_1..sigma^2_{T+1} (length T+1), the IIR filter y_t = x_t + beta y_{t-1}
    with x_1 = s2_init and x_t = omega + alpha eps^2_{t-1}."""
    x = np.empty(eps2.size + 1)
    x[0] = s2_init
    x[1:] = omega + alpha * eps2
    return lfilter([1.0], [1.0, -beta], x)


def _t_const(nu: float) -> float:
    """Copy of garch._t_const: ln of the unit-variance t density's normalising constant (the Stirling expansion
    beyond nu = 1e4, where the two gammaln terms cancel catastrophically)."""
    if nu > 1e4:
        return 0.5 * math.log(nu / (2.0 * math.pi * (nu - 2.0))) - 1.0 / (4.0 * nu)
    return gammaln((nu + 1) / 2) - gammaln(nu / 2) - 0.5 * math.log(math.pi * (nu - 2))


def _loglik(params: np.ndarray, eps: np.ndarray, eps2: np.ndarray, s2_init: float, dist: str) -> float:
    """Copy of garch._loglik: the GARCH(1,1) log-likelihood, -_PENALTY past the stationarity cap or for a
    non-positive variance path."""
    omega, alpha, beta = params[:3]
    if alpha + beta > _STATIONARITY_MAX:
        return -_PENALTY
    s2 = _variance_path(eps2, omega, alpha, beta, s2_init)[:-1]
    if not np.all(np.isfinite(s2)) or np.any(s2 <= 0):
        return -_PENALTY
    if dist == "t" and params[3] >= _ETA_EPS:
        nu = 1.0 / params[3]
        ll = _t_const(nu) - 0.5 * np.log(s2) - ((nu + 1) / 2) * np.log1p(eps2 / ((nu - 2) * s2))
    else:                                                # normal, or a t with eta = 0
        ll = -0.5 * math.log(2 * math.pi) - 0.5 * np.log(s2) - eps2 / (2 * s2)
    return float(np.sum(ll))


def _fit(eps: np.ndarray, dist: str, extra_starts=(), default_starts: bool = True):
    """Copy of garch._fit: L-BFGS-B over (omega, alpha, beta[, eta]) from the three deterministic starts (unless
    `default_starts` is False) plus `extra_starts`, omega optimised in units of 1e-6. Returns (p, loglik,
    converged, at_bound, s2_path)."""
    eps2 = eps ** 2
    var = float(np.var(eps))
    names = ("omega", "alpha", "beta") + (("eta",) if dist == "t" else ())
    scale = np.ones(len(names))
    scale[0] = _OMEGA_SCALE
    bounds = [(_BOUNDS["omega"][0] * _OMEGA_SCALE, None)] + [_BOUNDS[n] for n in names[1:]]
    starts = ([[var * (1 - 0.05 - beta0), 0.05, beta0] + ([1.0 / 8.0] if dist == "t" else [])
               for beta0 in (0.80, 0.90, 0.94)] if default_starts else []) + [list(s) for s in extra_starts]
    best = None
    for x0 in starts:
        res = minimize(lambda p: -_loglik(p / scale, eps, eps2, var, dist), np.array(x0) * scale,
                       method="L-BFGS-B", bounds=bounds)
        if best is None or res.fun < best.fun:
            best = res
    p = best.x / scale
    at = []
    for name, val in zip(names, p):
        lo, hi = _BOUNDS[name]
        tol = 1e-4
        if name == "eta":                                # eta = 0 is the normal, not a failure
            if abs(val - hi) <= tol * abs(hi):
                at.append("nu")                          # nu at its lower bound 2.5
            continue
        if abs(val - lo) <= (tol if lo == 0 else tol * abs(lo)):
            at.append(name)
        elif math.isfinite(hi) and abs(val - hi) <= tol * abs(hi):
            at.append(name)
    if p[1] + p[2] > 0.995:
        at.append("stationarity")
    s2_path = _variance_path(eps2, p[0], p[1], p[2], var)
    return p, float(-best.fun), bool(best.success), tuple(at), s2_path


def _fit_t(eps: np.ndarray):
    """Copy of garch._fit_t with no extra starts: the normal first, the t from the normal's optimum (eta = 0), the
    normal re-fitted from the t's (omega, alpha, beta), and one more t pass if that normal climbs past the t.
    Returns (p, loglik, converged, at_bound, s2_path)."""
    p_n, _, _, _, _ = _fit(eps, "normal")
    p, ll, converged, at_bound, s2_path = _fit(eps, "t", extra_starts=[[*p_n[:3], 0.0]])
    p_n2, ll_n2, _, _, _ = _fit(eps, "normal", extra_starts=[list(p[:3])], default_starts=False)
    if ll_n2 > ll:
        t2 = _fit(eps, "t", extra_starts=[[*p_n2[:3], 0.0]], default_starts=False)
        if t2[1] >= ll:
            p, ll, converged, at_bound, s2_path = t2
    return p, ll, converged, at_bound, s2_path


def fit_garch_t(returns: np.ndarray) -> GarchParams:
    """GARCH(1,1)-t on daily log returns: the path of garch.fit_garch(returns, dist="t", profile=False) without the
    standard errors, the likelihood ratios and the note. ValueError under 100 observations."""
    r = np.asarray(returns, dtype=float)
    if r.size < _MIN_OBS:
        raise ValueError(f"Need at least {_MIN_OBS} observations to fit GARCH; got {r.size}.")
    mu = float(np.mean(r))
    p, _, converged, at_bound, s2_path = _fit_t(r - mu)
    eta = float(p[3])
    return GarchParams(dist="t", omega=float(p[0]), alpha=float(p[1]), beta=float(p[2]),
                       nu=math.inf if eta < _ETA_EPS else 1.0 / eta, mean_daily=mu, n_obs=r.size,
                       cond_vol_last=math.sqrt(s2_path[-1] * TRADING_DAYS), converged=converged, at_bound=at_bound)


def _t_scale(nu: float) -> float:
    """Copy of garch._t_scale: the unit-variance scaling of a standard t draw."""
    return math.sqrt((nu - 2.0) / nu)


def t_density(z, nu: float) -> np.ndarray:
    """Copy of garch.t_density: the density of the unit-variance Student-t (the normal density above NU_NORMAL)."""
    z = np.asarray(z, dtype=float)
    if nu > NU_NORMAL:
        return np.exp(-0.5 * z ** 2) / math.sqrt(2 * math.pi)
    return math.exp(_t_const(nu)) * (1.0 + z ** 2 / (nu - 2.0)) ** (-(nu + 1) / 2)


def _draw_z(rng, nu: float, dist: str, size, bound: float | None = Z_BOUND) -> np.ndarray:
    """Copy of garch._draw_z: unit-variance innovations; with a `bound` (t only) every draw beyond it is replaced by
    one from the t restricted to [-bound, bound] via the inverse CDF. A t with nu above NU_NORMAL is drawn as a
    normal."""
    if dist != "t" or nu > NU_NORMAL:
        return rng.standard_normal(size=size)
    s = _t_scale(nu)
    z = rng.standard_t(nu, size=size) * s
    if bound is None:
        return z
    out = np.abs(z) > bound
    n_out = int(np.count_nonzero(out))
    if n_out:
        d = stats.t(nu)
        lo, hi = d.cdf(-bound / s), d.cdf(bound / s)
        z[out] = s * d.ppf(lo + rng.random(n_out) * (hi - lo))
    return z


def _log_mgf(sig: np.ndarray, z: np.ndarray, wt: np.ndarray) -> np.ndarray:
    """Copy of garch._log_mgf: ln sum_i wt_i exp(sig z_i) for each sig, computed stably."""
    e = np.outer(sig, z)
    m = e.max(axis=1, keepdims=True)
    return m[:, 0] + np.log((wt[None, :] * np.exp(e - m)).sum(axis=1))


@lru_cache(maxsize=32)
def _correction_table(nu: float, bound: float):
    """Copy of garch._correction_table: Gauss-Legendre nodes and normalised weights of the t restricted to
    [-bound, bound] (three panels), and c(sigma)/sigma^2 on a 4,000-point geometric daily-sigma grid up to _SIG_HI.
    martingale_correction looks this name up at call time, so the corruption test of tests/odds_garch.py reaches
    every caller."""
    x, w = np.polynomial.legendre.leggauss(600)
    edges = (-bound, -1.0, 1.0, bound) if bound > 1.0 else (-bound, bound)
    z = np.concatenate([0.5 * (b - a) * x + 0.5 * (b + a) for a, b in zip(edges[:-1], edges[1:])])
    wt = np.concatenate([0.5 * (b - a) * w for a, b in zip(edges[:-1], edges[1:])]) * t_density(z, nu)
    wt = wt / wt.sum()
    sig = np.geomspace(_SIG_LO, _SIG_HI, 4000)
    c = np.concatenate([_log_mgf(s, z, wt) for s in np.array_split(sig, 16)])
    return z, wt, sig, c / sig ** 2


def martingale_correction(sigma_daily, nu: float, dist: str, bound: float | None = Z_BOUND) -> np.ndarray:
    """Copy of garch.martingale_correction: c(sigma) = ln E[exp(sigma z)] per step for the innovation law that is
    simulated (sigma^2/2 for a normal z; the interpolated table of the bounded t, direct sums above the grid). An
    unbounded t has no such correction and raises."""
    sig = np.atleast_1d(np.asarray(sigma_daily, dtype=float))
    if dist != "t" or nu > NU_NORMAL:                    # normal, or a t drawn as one
        return 0.5 * sig ** 2
    if bound is None:
        raise ValueError("exp(sigma z) has no finite expectation under an unbounded t; no correction exists")
    z, wt, grid, ratio = _correction_table(float(nu), float(bound))
    out = np.interp(sig, grid, ratio) * sig ** 2
    big = sig > grid[-1]
    if np.any(big):
        out[big] = _log_mgf(sig[big], z, wt)
    return out


def simulate_garch(fit: GarchParams, *, n_paths: int, horizon: int, seed) -> tuple[np.ndarray, np.ndarray]:
    """(ret, sigma), each (n_paths, horizon): the body of garch.simulate_returns(fit, rate_daily=0.0, bound=Z_BOUND)
    with the conditional daily sigma of every step kept. Each step's log return is -c(sigma_t) + sigma_t z_t, so
    exp(cumulative return) has mean 1 at every step: the no-edge law. `seed` goes to np.random.default_rng (a
    SeedSequence from seed_sequence, or a Generator)."""
    rng = np.random.default_rng(seed)
    z = _draw_z(rng, fit.nu, fit.dist, (n_paths, horizon), Z_BOUND)
    ret = np.empty((n_paths, horizon))
    sigma = np.empty((n_paths, horizon))
    s2 = np.full(n_paths, fit.cond_vol_last ** 2 / TRADING_DAYS)
    for h in range(horizon):
        sig = np.sqrt(s2)
        eps = sig * z[:, h]
        c = martingale_correction(sig, fit.nu, fit.dist, Z_BOUND)
        ret[:, h] = 0.0 - c + eps
        sigma[:, h] = sig
        s2 = fit.omega + fit.alpha * eps ** 2 + fit.beta * s2
    return ret, sigma


def simulate_garch_series(omega: float, alpha: float, beta: float, nu: float, *, n: int, seed,
                          dist: str = "t") -> np.ndarray:
    """Copy of garch.simulate_garch_series: zero-mean synthetic GARCH(1,1) returns with the full (unbounded) tail and
    a 500-session burn-in (the refit member's synthetic series)."""
    rng = np.random.default_rng(seed)
    burn = 500
    z = _draw_z(rng, nu, dist, n + burn, bound=None)
    eps = np.empty(n + burn)
    s2 = omega / (1 - alpha - beta) if alpha + beta < 1 else omega * 100
    for t in range(n + burn):
        eps[t] = math.sqrt(s2) * z[t]
        s2 = omega + alpha * eps[t] ** 2 + beta * s2
    return eps[burn:]


# --------------------------------------------------------------------------- #
# GARCH pilot checks (contract 7.4; Q10)
# --------------------------------------------------------------------------- #
PILOT_PATHS = 20_000
PILOT_NODES = 512
PILOT_STEP_TOL = 1e-7
PILOT_SUM_TOL = 1e-6
PILOT_SE = 4.0


@lru_cache(maxsize=32)
def _t_mass(nu: float, bound: float) -> float:
    """The quad mass of the unit-variance t density on [-bound, bound] over c_quad's three panels."""
    return sum(quad(lambda x: t_density(x, nu), a, b, limit=400)[0] for a, b in ((-bound, -1.0), (-1.0, 1.0),
                                                                                (1.0, bound)))


def c_quad(sigma: float, nu: float, bound: float = Z_BOUND) -> float:
    """The exact per-step correction ln E[exp(sigma z)] of the t restricted to [-bound, bound], by scipy quad over
    the panels (-bound, -1), (-1, 1), (1, bound) as garch's own self-check does, so it shares no node with the
    table; sigma^2/2 for a t drawn as a normal (nu > NU_NORMAL)."""
    if nu > NU_NORMAL:
        return 0.5 * sigma ** 2
    num = sum(quad(lambda x: math.exp(sigma * x) * t_density(x, nu), a, b, limit=400)[0]
              for a, b in ((-bound, -1.0), (-1.0, 1.0), (1.0, bound)))
    return math.log(num / _t_mass(float(nu), float(bound)))


def _deterministic_gap(fit: GarchParams, sigma: np.ndarray) -> tuple[float, float]:
    """Check 1's two statistics on the pilot's sigma: (max over the nodes of |expm1(c_quad - c_table)|, max over
    paths of the summed |c_quad - c_table| over the horizon). The nodes are the distinct quantiles of every pilot
    sigma at PILOT_NODES levels; each sigma takes its nearest node's error."""
    nodes = np.unique(np.quantile(sigma.ravel(), np.linspace(0.0, 1.0, PILOT_NODES)))
    nu = fit.nu if fit.dist == "t" else math.inf         # a normal fit: c = sigma^2/2 exactly
    gap = np.array([c_quad(float(s), nu) for s in nodes]) - martingale_correction(nodes, fit.nu, fit.dist)
    hi = np.clip(np.searchsorted(nodes, sigma), 0, nodes.size - 1)
    lo = np.maximum(hi - 1, 0)
    near = np.where(np.abs(nodes[lo] - sigma) <= np.abs(nodes[hi] - sigma), lo, hi)
    return float(np.max(np.abs(np.expm1(gap)))), float(np.max(np.abs(gap)[near].sum(axis=1)))


def _statistical_z(ret: np.ndarray) -> float:
    """Check 2's statistic: max over steps h of |mean(e_h) - 1| / (std(e_h, ddof=1) / sqrt(rows)), e = exp of the
    cumulative log return. NaN when a return is not finite, which fails the check."""
    e = np.exp(np.cumsum(ret, axis=1))
    return float(np.max(np.abs(e.mean(axis=0) - 1.0) / (e.std(axis=0, ddof=1) / math.sqrt(e.shape[0]))))


def pilot_checks(fit: GarchParams, horizon: int, seed: bytes) -> tuple[bool, str]:
    """The two GARCH pilot checks (spec 7.2 "GarchT"; Q10) on PILOT_PATHS paths of the "pilot" stream:
    1 (deterministic) the table's correction against quad, PILOT_STEP_TOL per step and PILOT_SUM_TOL summed over
    the horizon on every path; 2 (statistical) exp(cumulative return) within PILOT_SE standard errors of 1 at every
    step. (True, "") or (False, the first failing check). Each test fails closed on NaN."""
    ret, sigma = simulate_garch(fit, n_paths=PILOT_PATHS, horizon=horizon, seed=seed_sequence(seed, 0, "pilot"))
    step, summed = _deterministic_gap(fit, sigma)
    if not (step <= PILOT_STEP_TOL and summed <= PILOT_SUM_TOL):
        return False, "deterministic"
    if not _statistical_z(ret) <= PILOT_SE:
        return False, "statistical"
    return True, ""


# --------------------------------------------------------------------------- #
# Part 3 (Task 17): the D13 pins and their check, Kelly, the replay's moves and their block growth (Q9, Q38)
# --------------------------------------------------------------------------- #
CARD_ID = "S_C3_crypto_trend_krwbtc"
REPLAY_PINS = {
    "input_symbol": "KRW-BTC", "input_source": "UPBIT", "n_input": 3288,
    "input_first": "2017-09-25", "input_last": "2026-09-25",
    "input_md5": "18ec83bdfe158efe4d648caf45ff849f",     # md5 of canonical_json({"symbol", "source", "dates", "close"})
    "lookbacks": (7, 14, 21, 28), "mas": (10, 20, 50, 100, 200), "grid": (0.0, 0.222, 0.444, 0.667, 0.889),
    "cost_bps_per_side": 10.0, "embargo": 1, "n_trials": 11, "seed": 11, "domain": (0.0, 0.889),
    "protocol": {"w_is": 756, "w_oos": 126, "min_is": 504, "ci_level": 0.9, "bootstrap_B": 2000, "block": 10},
    "n_oos": 2530, "oos_first": "2019-10-23", "oos_last": "2026-09-25",
    "pnl_md5": "bbdcf17ca9462567fe351c54644bef0c",       # md5 of np.ascontiguousarray(oos_pnl, dtype="<f8").tobytes()
    "turnover_md5": "2d4edeb2f042c87fd1750d9c68e275f7",  # the same bytes md5 of oos_turnover (values 0 or 1)
    "results_md5": "ca757e25f508b588cb2f361719ec83cd", "card_md5": "40b1e7bfadf6d16246e0012495064704",
    "sr_oos": 1.216, "sr_tol": 0.02, "decision": "PASS", "chosen_last": 0.667,
    "bench_sr": 0.788830441182887, "bench_diff": 0.4271945783845257,
    "bench_ci": (0.03344352887529298, 0.8346050647267628), "haircut_sr": 0.7296150117404476,
    "n_trades": 138, "n_sessions": 2530}                  # the card's own stats (cards/S_C3_crypto_trend_krwbtc.json)
KELLY_B = 2_000
KELLY_BLOCK = 10.0
KELLY_Q = 0.05


def _bench_sr(rep: plan.ReplayInput) -> float:
    """The core's own buy-and-hold Sharpe: simple close-to-close returns over consecutive input dates, taken on the
    out-of-sample dates (the card's bench_sr, recomputed from the passed closes)."""
    close = np.asarray(rep.input_close, dtype=float)
    simple = dict(zip(rep.input_dates[1:], close[1:] / close[:-1] - 1.0))
    return sharpe(np.array([simple[d] for d in rep.oos_dates]))


def verify_replay(rep: plan.ReplayInput) -> str | None:
    """None when the passed replay reproduces the validated card; else the name of the first item that does not, in
    the order: card id, inputs and protocol, digests, shape, statistics, the core's own bench_sr. Never raises: the
    replay comes from unsigned code, so any other object fails its first item. The results and card md5s are of
    file bytes unsigned code read: they are compared with the pins, never recomputed here."""
    pins, st = REPLAY_PINS, getattr(rep, "stats", None)
    checks = (
        ("card_id", lambda: rep.card_id == CARD_ID),
        ("input_symbol", lambda: rep.input_symbol == pins["input_symbol"]),
        ("input_source", lambda: rep.input_source == pins["input_source"]),
        ("n_input", lambda: len(rep.input_dates) == len(rep.input_close) == pins["n_input"]),
        ("input_first", lambda: rep.input_dates[0] == pins["input_first"]),
        ("input_last", lambda: rep.input_dates[-1] == pins["input_last"]),
        ("lookbacks", lambda: tuple(rep.lookbacks) == pins["lookbacks"]),
        ("mas", lambda: tuple(rep.mas) == pins["mas"]),
        ("grid", lambda: tuple(rep.grid) == pins["grid"]),
        ("cost_bps_per_side", lambda: rep.cost_bps_per_side == pins["cost_bps_per_side"]),
        ("embargo", lambda: rep.embargo == pins["embargo"]),
        ("n_trials", lambda: rep.n_trials == pins["n_trials"]),
        ("seed", lambda: rep.seed == pins["seed"]),
        ("domain", lambda: tuple(rep.domain) == pins["domain"]),
        ("protocol", lambda: dict(rep.protocol) == pins["protocol"]),
        ("gate_protocol", lambda: dict(rep.gate_protocol) == pins["protocol"]),
        ("input_md5", lambda: _input_md5(rep) == pins["input_md5"]),
        ("pnl_md5", lambda: _array_md5(rep.oos_pnl) == pins["pnl_md5"]),
        ("turnover_md5", lambda: _array_md5(rep.oos_turnover) == pins["turnover_md5"]),
        ("results_md5", lambda: rep.results_md5 == pins["results_md5"]),
        ("card_md5", lambda: rep.card_md5 == pins["card_md5"]),
        ("n_oos", lambda: len(rep.oos_dates) == len(rep.oos_pnl) == pins["n_oos"]),
        ("oos_first", lambda: rep.oos_dates[0] == pins["oos_first"]),
        ("oos_last", lambda: rep.oos_dates[-1] == pins["oos_last"]),
        ("oos_turnover", lambda: len(rep.oos_turnover) == len(rep.oos_pnl)),   # 7.5; turnover_md5 fires first
        ("sr_oos", lambda: sharpe(rep.oos_pnl) == st["sr_oos"]
         and abs(st["sr_oos"] - pins["sr_oos"]) <= pins["sr_tol"]),
        ("decision", lambda: st["decision"] == pins["decision"]),
        ("chosen_last", lambda: st["chosen_last"] == pins["chosen_last"]),
        ("haircut_rule", lambda: abs(st["haircut_sr"] - LIVE_SHARPE_MULTIPLIER * st["sr_oos"]) <= 1e-12),
        ("haircut_sr", lambda: st["haircut_sr"] == pins["haircut_sr"]),
        ("bench_sr", lambda: st["bench_sr"] == pins["bench_sr"]),
        ("bench_diff", lambda: st["bench_diff"] == pins["bench_diff"]),
        ("bench_ci", lambda: tuple(st["bench_ci"]) == pins["bench_ci"]),
        ("n_trades", lambda: st["n_trades"] == pins["n_trades"]),
        ("n_sessions", lambda: st["n_sessions"] == pins["n_sessions"]),
        ("bench_recompute", lambda: _bench_sr(rep) == pins["bench_sr"]),
    )
    for name, ok in checks:
        try:
            if not ok():
                return name
        except (AttributeError, KeyError, IndexError, TypeError, ValueError, OverflowError):
            return name
    return None


def mu_lb(r: np.ndarray, rng: np.random.Generator) -> float:
    """Kelly's mu_lb: the KELLY_Q quantile of KELLY_B stationary-bootstrap means of r (mean block KELLY_BLOCK)."""
    r = np.asarray(r, dtype=float)
    gen = indices(rng, r.size, KELLY_B, KELLY_BLOCK)
    total = np.zeros(KELLY_B)
    for _ in range(r.size):
        total += r[next(gen)]
    return float(np.quantile(total / r.size, KELLY_Q))


def kelly_fstar(r: np.ndarray, lb: float) -> float:
    """argmax over [0, 1] of mean ln(1 + f rc), rc = r - mean(r) + LIVE_SHARPE_MULTIPLIER lb (spec 7.1); 0.0 when
    lb <= 0. The log is concave, so the upper end is decided by the sign of the derivative there and an interior
    maximum by 60 bisection steps; the upper end is 0.999 / max(-rc) when some rc is at or below -1."""
    if not lb > 0.0:
        return 0.0
    r = np.asarray(r, dtype=float)
    rc = r - r.mean() + LIVE_SHARPE_MULTIPLIER * lb

    def slope(f: float) -> float:
        return float(np.mean(rc / (1.0 + f * rc)))

    f_hi = 1.0 if float(rc.min()) > -1.0 else 0.999 / float(np.max(-rc))
    if slope(f_hi) >= 0.0:
        return f_hi
    lo, hi = 0.0, f_hi
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if slope(mid) >= 0.0:
            lo = mid
        else:
            hi = mid
    return lo


def replay_returns(rep: plan.ReplayInput) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(a, c, R1) of Q38: the no-edge magnitudes |G - mean G| with G = pnl + c (signed later by the replay_sign
    stream), the card's own cost c on each out-of-sample day, and the tested returns with their mean scaled by
    LIVE_SHARPE_MULTIPLIER. ValueError unless max a + 2 max c < 1 and min R1 > -1, so no sleeve goes below 0."""
    pnl = np.asarray(rep.oos_pnl, dtype=float)
    c = rep.cost_bps_per_side * 1e-4 * np.asarray(rep.oos_turnover, dtype=float)
    gross = pnl + c
    a = np.abs(gross - gross.mean())
    r1 = pnl - pnl.mean() + LIVE_SHARPE_MULTIPLIER * pnl.mean()
    if not (float(a.max()) + 2.0 * float(c.max()) < 1.0 and float(r1.min()) > -1.0):
        raise ValueError(f"replay: a daily move could empty the sleeve (max a {a.max():.4f}, max c {c.max():.4f}, "
                         f"min R1 {r1.min():.4f})")
    return a, c, r1


def block_growth(r: np.ndarray, block: float, h: int) -> float:
    """Exact E[prod over h steps of (1 + r[I_t])] under the stationary bootstrap of `indices` (I_0 uniform; each
    later step moves to (I + 1) mod n with probability 1 - 1/block, else restarts uniformly), in O(h n); 1.0 for
    h = 0 (a sleeve that never moves)."""
    if h == 0:
        return 1.0
    r = np.asarray(r, dtype=float)
    v = 1.0 + r
    for _ in range(h - 1):
        v = (1.0 + r) * ((1.0 - 1.0 / block) * np.roll(v, -1) + (1.0 / block) * v.mean())
    return float(v.mean())
