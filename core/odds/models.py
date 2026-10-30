"""The no-edge models of the odds core, part 1 (spec 7.2, 7.3; odds plan Q10, Q12, Q34): the copied constants, block
length and Sharpe (O1: each pinned against its original by tests/odds_models.py), the two-point bootstrap's row
magnitudes, block lengths, index generator, kernel and tilt, and the market seed with its streams. Pure: no clock,
no file, no network."""
from __future__ import annotations

import hashlib
import math
from collections.abc import Iterator
from typing import TYPE_CHECKING

import numpy as np

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
