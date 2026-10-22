"""Block-bootstrap primitives for the gate package (R-24 carrier; M2 ships only the two pieces below).

- `pw_block(x)`: the Politis-White (2004) optimal block length with the Patton-Politis-White (2009) correction,
  ported from `arch.bootstrap.optimal_block_length` (rulings section 3.2: no `arch` dependency). Verified against
  arch 8.0.0 on AR(1), white-noise and heavy-tailed draws to 1e-9. `pw_block_floor(d)` is the card rule
  `max(10, ceil(PW(d)), ceil(PW(d^2)))` (spec L5987; tf_algorithms B.11).
- `block_indices(n, block, B, seed, kind)`: the seeded resampler. `circular` draws exactly the index matrix of
  `validate.sharpe_diff_bootstrap` / the labs' `boot_index` (same `default_rng(seed).integers` call), so a paired
  statistic computed here and there agrees to the last resample. `stationary` draws geometric block lengths of mean
  `block` with wrap-around (Politis-Romano), for the PC-1' ES legs of the frozen runs (L4992).

M7 (R-24, TASK-M7-06 / M7-07) adds the statistics and power harness below the M2 block: the Ledoit-Wolf
influence function of delta_SR and its HAC SE, the studentized circular-block bootstrap with a null-centred t*,
Politis-White on psi with the 21-session floor, the SE ladder, the power / MDE80 line and the UNDERPOWERED rule,
PBO by CSCV on the card's own objective, the BY q-value, the Harvey-Liu haircut, the Lo-adjusted Sharpe and the
unit-declared PSR / DSR. Every statistic the spec names without a formula carries a "reading:" line in its
docstring naming the textbook form used (spec_M7_gate_package section F). Pure numpy / scipy, seed-explicit; B,
block and seed are always parameters (never `validate.GATE`); nothing here reads data or a clock.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from itertools import combinations
from typing import Callable, Optional, Sequence

import numpy as np
from scipy import stats as sps

from core.quant import validate as V
from core.quant.validate import TRADING_DAYS

BLOCK_KINDS = ("circular", "stationary")
PC3_BLOCK_FLOOR = 10                 # L5987: p_ni = max(p at 10-session blocks, p at max(10, PW(d), PW(d^2)))


def optimal_block_length(x) -> tuple[float, float]:
    """(stationary, circular) optimal block lengths of one series; NaN-free finite input, n >= 20."""
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


def pw_block(x, kind: str = "circular") -> float:
    """Politis-White optimal block length (float, capped at ceil(min(3 sqrt(n), n/3)))."""
    if kind not in BLOCK_KINDS:
        raise ValueError(f"kind must be one of {BLOCK_KINDS}")
    sb, cb = optimal_block_length(x)
    return cb if kind == "circular" else sb


def pw_block_floor(d, floor: int = PC3_BLOCK_FLOOR) -> int:
    """`max(floor, ceil(PW(d)), ceil(PW(d^2)))`: the PC-3 block of a difference series (L5987)."""
    d = np.asarray(d, dtype=float)
    return int(max(floor, math.ceil(pw_block(d)), math.ceil(pw_block(d * d))))


def block_indices(n: int, block: int, B: int, seed: int, kind: str = "circular") -> np.ndarray:
    """(B, n) resample indices. `circular`: fixed blocks of `block` wrapped mod n, the validate / lab scheme.
    `stationary`: geometric block lengths with mean `block`, wrapped. Same seed, same matrix."""
    if kind not in BLOCK_KINDS:
        raise ValueError(f"kind must be one of {BLOCK_KINDS}")
    n, block, B = int(n), int(block), int(B)
    if n < 2 or block < 1 or B < 1:
        raise ValueError("block_indices needs n >= 2, block >= 1, B >= 1")
    rng = np.random.default_rng(seed)
    if kind == "circular":
        n_blocks = int(math.ceil(n / block))
        starts = rng.integers(0, n, size=(B, n_blocks))
        idx = (starts[:, :, None] + np.arange(block)[None, None, :]) % n
        return idx.reshape(B, -1)[:, :n]
    p = 1.0 / block
    out = np.empty((B, n), dtype=np.int64)
    for b in range(B):                                   # ponytail: per-row loop; vectorise if B x n grows past 1e8
        pos, start = 0, int(rng.integers(0, n))
        while pos < n:
            length = min(int(rng.geometric(p)), n - pos)
            out[b, pos:pos + length] = (start + np.arange(length)) % n
            pos += length
            start = int(rng.integers(0, n))
    return out


def row_sharpes(samples: np.ndarray) -> np.ndarray:
    """Annualised Sharpe of every row (ddof 1, sqrt(252); 0 where the row has no dispersion), as validate does."""
    m, s = samples.mean(axis=1), samples.std(axis=1, ddof=1)
    return np.where(s > 0, m / np.where(s > 0, s, 1.0), 0.0) * math.sqrt(TRADING_DAYS)


# =========================================================================== #
# M7 — R-24 statistics and power harness (TASK-M7-06, TASK-M7-07)
# =========================================================================== #
# Mirror of the shipped `gate.stats` block (data/macro/rules_v2.0.0.json); tests assert equality so the two
# cannot drift. The module stays a pure leaf: it never loads the store.
STATS = {
    "bootstrap": {"method": "ledoit_wolf_studentized_circular_block", "null_centred": True, "resamples": 2000,
                  "seed": 11, "p_zero_print": "< 1/B", "hac_p_printed": True},
    "block": {"rule": "politis_white_on_influence_function", "floor_sessions": 21, "pc3_also_block_10": True},
    "se_ladder_blocks": [10, 21, 63, 126, 250],
    "power": {"alpha_one_sided": 0.1, "power": 0.8, "mde_factor": 2.1232, "deltas": [0.05, 0.1],
              "t_years": "sessions_over_252", "se": "se_plateau"},
    "underpowered": {"mde80_gt": 0.1, "converts": ["step5_p_value", "pc3_p_value"]},
    "multiplicity": {"p_source": "analytic_hac_lw", "bootstrap_resamples_if_used": "20*M/alpha",
                     "by_q_from_global_ledger": True, "one_sided_z": {"le_8_cells": 2.5, "bonferroni_120": 3.34}},
    "pbo": {"configs": "ledger_union_frozen_pc6_grid", "min_configs": 10, "cscv_blocks": 16,
            "objective": {"CARD_O": "paired_dSR_vs_off", "CARD_P": "blockwise_dES95_21"},
            "winner_loses_share_gt": 0.1, "reject_if": "PBO > 0.2 and winner_loses", "null_calibration": "printed"},
    "lo_adjusted_sr": {"lags": [20, "all"], "printed": True, "gated": False},
    "live_sharpe_multiplier": 0.6,
}
SEED_STUDY = 11
B_DEFAULT = 2000
BLOCK_FLOOR = 21                     # L2569: PW(psi) floored at 21 sessions
BLOCK_FALLBACK = 250                 # L2620: used, and logged, when PW(psi) cannot be computed
SE_LADDER_BLOCKS = (10, 21, 63, 126, 250)
MDE_FACTOR = 2.1232                  # L2573: (z_0.90 + z_0.80), the store's literal
Z_ALPHA = 1.2816                     # L2574: z_0.90 one-sided, the store's literal
MDE80_UNDERPOWERED = 0.10            # L2576: MDE80 above the top of the de-risk base rate
UNDERPOWERED_CONVERTS = ("step5_p_value", "pc3_p_value")
UNDERPOWERED_NEVER_WAIVES = ("pc1_prime", "pc2", "pc3_point", "step3")
LIVE_SHARPE_MULTIPLIER = 0.60
PBO_MIN_CONFIGS = 10
PBO_WINNER_LOSES_SHARE = 0.10
P_FLOOR = "< 1/B"                    # L2567: a resample count of 0 prints "< 1/B" and compares as 1/B
PERIODS = {"daily": 252, "monthly": 12}
_FLOAT_TINY = float(np.finfo(float).tiny)


class StatsRefused(ValueError):
    """A harness call outside its rule: wrong units, UNDERPOWERED outside rule 4, a missing power block."""


class PowerBlockMissing(StatsRefused):
    """A card without the R-24 power fields is refused (L2619, T-POWER-02)."""


def spawn_seeds(seed: int, n: int) -> list[np.random.SeedSequence]:
    """`SeedSequence(seed).spawn(n)`: the child seeds of parallel workers and the T-PBO-01 panels (L5667)."""
    return list(np.random.SeedSequence(int(seed)).spawn(int(n)))


def pstr(count: int, B: int):
    """A bootstrap p from its resample count: the float count/B, or the string "< 1/B" for a count of 0 (L2567)."""
    count, B = int(count), int(B)
    if B < 1 or count < 0 or count > B:
        raise ValueError("pstr needs 0 <= count <= B, B >= 1")
    return P_FLOOR if count == 0 else count / B


def p_numeric(p, B: int) -> float:
    """The comparison value of a printed p: "< 1/B" compares as 1/B (L2567); a float is itself."""
    return 1.0 / int(B) if isinstance(p, str) else float(p)


def _analytic_p(t: float) -> float:
    """One-sided analytic p = 1 - Phi(t), floored at the smallest positive float: no card field holds p = 0."""
    return max(float(sps.norm.sf(t)), _FLOAT_TINY)


def _pair(x_a, x_b) -> tuple[np.ndarray, np.ndarray]:
    a, b = np.asarray(x_a, dtype=float).ravel(), np.asarray(x_b, dtype=float).ravel()
    if a.size != b.size:
        raise ValueError(f"paired books differ in length: {a.size} vs {b.size}")
    if a.size < 30 or not (np.all(np.isfinite(a)) and np.all(np.isfinite(b))):
        raise ValueError("paired books need >= 30 finite aligned daily excess returns")
    return a, b


# --------------------------------------------------------------------------- #
# Influence function and HAC SE of delta_SR (Ledoit-Wolf 2008)
# --------------------------------------------------------------------------- #
def delta_sr(x_a, x_b) -> float:
    """`delta_sr = SR(x_a) - SR(x_b)`, annualised, `validate.sharpe` on both (ddof 1). Named per L2437."""
    a, b = _pair(x_a, x_b)
    return float(V.sharpe(a) - V.sharpe(b))


def _lw_moments(a: np.ndarray, b: np.ndarray, axis: int = -1):
    """(mu_a, mu_b, gamma_a, gamma_b) and the delta-method gradient of SR_a - SR_b at them (LW 2008 eq. 3-4)."""
    mu_a, mu_b = a.mean(axis=axis), b.mean(axis=axis)
    g_a, g_b = (a * a).mean(axis=axis), (b * b).mean(axis=axis)
    va, vb = g_a - mu_a ** 2, g_b - mu_b ** 2
    if np.any(va <= 0) or np.any(vb <= 0):
        raise ValueError("influence function undefined: a book has zero variance")
    grad = (g_a / va ** 1.5, -g_b / vb ** 1.5, -0.5 * mu_a / va ** 1.5, 0.5 * mu_b / vb ** 1.5)
    return (mu_a, mu_b, g_a, g_b), grad


def influence_function_dsr(x_a, x_b) -> np.ndarray:
    """psi_t of delta_SR (per-period units), Ledoit-Wolf (2008) delta method.

    reading (L2565, L2569, section F-8): `y_t = (x_a, x_b, x_a^2, x_b^2)`, `v = mean(y)`, `psi_t = grad(v) . (y_t - v)`
    with `grad = (g_a/(g_a-mu_a^2)^1.5, -g_b/(g_b-mu_b^2)^1.5, -0.5 mu_a/(..)^1.5, 0.5 mu_b/(..)^1.5)`. psi sums to 0.
    """
    a, b = _pair(x_a, x_b)
    (mu_a, mu_b, g_a, g_b), grad = _lw_moments(a, b)
    return grad[0] * (a - mu_a) + grad[1] * (b - mu_b) + grad[2] * (a * a - g_a) + grad[3] * (b * b - g_b)


def _autocov(psi: np.ndarray) -> np.ndarray:
    """gamma_j = (1/T) sum_t psi_t psi_{t-j} for j = 0..T-1 (psi already mean zero); FFT, O(T log T)."""
    T = psi.size
    f = np.fft.rfft(psi, n=2 * T)
    return np.fft.irfft(f * np.conj(f), n=2 * T)[:T] / T


def lrv_qs_andrews(psi) -> tuple[float, float]:
    """(long-run variance, bandwidth) of a mean-zero series by the quadratic-spectral kernel with Andrews (1991)
    AR(1) automatic bandwidth.

    reading (L2463, section F-7): `alpha(2) = 4 rho^2 / (1 - rho)^4` from an OLS AR(1) fit, `S_T = 1.3221 (alpha(2) T)^(1/5)`,
    `k(x) = 25/(12 pi^2 x^2) (sin(6 pi x/5)/(6 pi x/5) - cos(6 pi x/5))`, `LRV = gamma_0 + 2 sum_j k(j/S_T) gamma_j`
    over every lag. A non-positive LRV (degenerate kernel sum) falls back to gamma_0.
    """
    psi = np.asarray(psi, dtype=float).ravel()
    T = psi.size
    if T < 10:
        raise ValueError("lrv needs >= 10 observations")
    g = _autocov(psi)
    if g[0] <= 0:
        return 0.0, 0.0
    x0, x1 = psi[:-1], psi[1:]
    den = float(x0 @ x0)
    rho = float(x0 @ x1) / den if den > 0 else 0.0
    rho = min(max(rho, -0.97), 0.97)                        # Andrews' AR(1) plug-in is unbounded at |rho| -> 1
    alpha2 = 4.0 * rho ** 2 / (1.0 - rho) ** 4
    bw = 1.3221 * (alpha2 * T) ** 0.2 if alpha2 > 0 else 0.0
    if bw <= 0:
        return float(g[0]), 0.0
    x = np.arange(1, T) / bw
    z = 6.0 * math.pi * x / 5.0
    k = 25.0 / (12.0 * math.pi ** 2 * x ** 2) * (np.sin(z) / z - np.cos(z))
    lrv = float(g[0] + 2.0 * (k * g[1:]).sum())
    return (lrv if lrv > 0 else float(g[0])), float(bw)


def lrv_bartlett(psi, lag: int = 10) -> float:
    """Newey-West long-run variance with Bartlett weights `1 - j/(lag+1)` (the "NW10" line printed beside QS)."""
    psi = np.asarray(psi, dtype=float).ravel()
    g = _autocov(psi)
    lag = min(int(lag), psi.size - 1)
    w = 1.0 - np.arange(1, lag + 1) / (lag + 1.0)
    lrv = float(g[0] + 2.0 * (w * g[1:lag + 1]).sum())
    return lrv if lrv > 0 else float(g[0])


@dataclass(frozen=True)
class HacSE:
    se: float                 # LW-HAC SE of delta_SR, annualised (QS kernel, Andrews bandwidth)
    se_nw10: float            # Bartlett 10-lag value printed beside it
    bandwidth: float
    T: int
    psi: np.ndarray = field(repr=False, compare=False)


def lw_hac_se(x_a, x_b) -> HacSE:
    """LW-HAC standard error of delta_SR: `sqrt(LRV(psi)/T) * sqrt(252)` (L2463, B2). `.psi` is the influence
    function for `pw_block_psi`; `.se_nw10` the Bartlett-10 companion (G-PWR-01 quotes both)."""
    psi = influence_function_dsr(x_a, x_b)
    T = psi.size
    lrv, bw = lrv_qs_andrews(psi)
    return HacSE(se=math.sqrt(lrv / T) * math.sqrt(TRADING_DAYS), se_nw10=math.sqrt(lrv_bartlett(psi) / T) * math.sqrt(TRADING_DAYS),
                 bandwidth=bw, T=T, psi=psi)


# --------------------------------------------------------------------------- #
# Studentized circular-block bootstrap (steps 2, 5, PC-3)
# --------------------------------------------------------------------------- #
def lw_studentized_boot(x_a, x_b, block: int, B: int = B_DEFAULT, seed: int = SEED_STUDY, null: float = 0.0,
                        *, level: float = 0.90) -> dict:
    """Ledoit-Wolf studentized circular-block bootstrap of delta_SR with a null-centred t* (L2565, B2).

    `t_obs = (dSR - null)/se_hac`; per resample (paired rows, same indices for both books, `block_indices`):
    `dSR*`, `se*` from the block-sum variance of `psi*` (LW 2008 section 3.2.2: psi* at the resample's own
    moments, `LRV* = mean(block sums^2)/block`, se* = sqrt(LRV*/T) annualised), `t* = (dSR* - dSR)/se*`.
    `p_lw = #{t* >= t_obs}/B` (printed "< 1/B" at a count of 0); `p_hac = 1 - Phi(t_obs)` printed beside it.
    Step 5 (CARD-O) uses `null = 0`; PC-3 `null = -delta`. `ci` = the studentized `level` interval of dSR.
    Returns {dSR, se, se_nw10, t_obs, p_lw, count, p_hac, block, n_blocks, B, seed, null, ci, level}.
    """
    a, b = _pair(x_a, x_b)
    block, B = int(block), int(B)
    T = a.size
    if block < 1 or block > T or B < 1:
        raise ValueError("lw_studentized_boot needs 1 <= block <= T and B >= 1")
    hac = lw_hac_se(a, b)
    d_sr = delta_sr(a, b)
    if hac.se <= 0:
        raise ValueError("HAC SE is zero: the studentized statistic is undefined")
    t_obs = (d_sr - float(null)) / hac.se
    idx = block_indices(T, block, B, seed, "circular")
    sa, sb = a[idx], b[idx]
    d_star = row_sharpes(sa) - row_sharpes(sb)
    (mu_a, mu_b, g_a, g_b), grad = _lw_moments(sa, sb, axis=1)
    psi_star = (grad[0][:, None] * (sa - mu_a[:, None]) + grad[1][:, None] * (sb - mu_b[:, None])
                + grad[2][:, None] * (sa * sa - g_a[:, None]) + grad[3][:, None] * (sb * sb - g_b[:, None]))
    n_full = T // block
    sums = psi_star[:, :n_full * block].reshape(B, n_full, block).sum(axis=2)
    lrv_star = (sums * sums).mean(axis=1) / block
    se_star = np.sqrt(np.maximum(lrv_star, 0.0) / T) * math.sqrt(TRADING_DAYS)
    se_star = np.where(se_star > 0, se_star, 1e-12)
    t_star = (d_star - d_sr) / se_star
    count = int(np.sum(t_star >= t_obs))
    alpha = (1.0 - level) / 2.0
    t_lo, t_hi = np.quantile(t_star, [alpha, 1.0 - alpha])
    return {"dSR": d_sr, "se": hac.se, "se_nw10": hac.se_nw10, "t_obs": float(t_obs), "p_lw": pstr(count, B),
            "count": count, "p_hac": _analytic_p(t_obs), "block": block, "n_blocks": int(math.ceil(T / block)),
            "B": B, "seed": int(seed), "null": float(null), "ci": (float(d_sr - t_hi * hac.se), float(d_sr - t_lo * hac.se)),
            "level": float(level)}


# --------------------------------------------------------------------------- #
# Block rule: Politis-White on psi, floor 21, fallback 250
# --------------------------------------------------------------------------- #
def pw_block_psi(x_a, x_b, *, floor: int = BLOCK_FLOOR, fallback: int = BLOCK_FALLBACK, log: Optional[list] = None) -> int:
    """Circular-bootstrap block length on the scalar influence function psi (never on d or d^2), floored at 21
    sessions (L2569). When PW cannot be computed (non-finite psi, zero variance) the 250-session block is used
    and the event is appended to `log` (L2620)."""
    try:
        psi = influence_function_dsr(x_a, x_b)
        pw = pw_block(psi, "circular")
        if not math.isfinite(pw):
            raise ValueError("non-finite Politis-White block")
    except ValueError as exc:
        if log is not None:
            log.append({"event": "pw_block_psi_fallback", "block": int(fallback), "reason": str(exc)})
        return int(fallback)
    return int(max(int(floor), math.ceil(pw)))


def pc3_blocks(x_a, x_b, *, log: Optional[list] = None) -> dict:
    """The two PC-3 legs (L2570): `{block_10: 10, block_pw: max(21, PW(psi)), pc3_also_block_10: True}`;
    `p_ni = max(p at block_10, p at block_pw)` is formed by the CARD-P evaluator."""
    return {"block_10": PC3_BLOCK_FLOOR, "block_pw": pw_block_psi(x_a, x_b, log=log),
            "pc3_also_block_10": STATS["block"]["pc3_also_block_10"]}


# --------------------------------------------------------------------------- #
# SE ladder and the power / MDE80 line
# --------------------------------------------------------------------------- #
def se_ladder(x_a, x_b, blocks: Sequence[int] = SE_LADDER_BLOCKS, *, B: int = B_DEFAULT, seed: int = SEED_STUDY) -> dict:
    """SE(delta_SR) from LW-HAC and from the circular block bootstrap at each block length (L2571).
    `se_by_block[b]` = SD (ddof 1) of dSR* over B resamples, annualised; `se_plateau = max(se_hac, *se_by_block)`;
    `n_blocks[b] = T/b` printed. Returns {se_hac, se_nw10, se_by_block, se_plateau, se_blk250, n_blocks, T, curve}."""
    a, b = _pair(x_a, x_b)
    T = a.size
    hac = lw_hac_se(a, b)
    by_block, n_blocks = {}, {}
    for blk in blocks:
        blk = int(blk)
        if blk < 1 or blk > T:
            raise ValueError(f"block {blk} outside [1, T={T}]")
        idx = block_indices(T, blk, B, seed, "circular")
        d_star = row_sharpes(a[idx]) - row_sharpes(b[idx])
        by_block[blk] = float(np.std(d_star, ddof=1))
        n_blocks[blk] = int(math.ceil(T / blk))
    plateau = max([hac.se] + list(by_block.values()))
    curve = {"hac": hac.se, "nw10": hac.se_nw10, **{str(k): v for k, v in by_block.items()}}
    return {"se_hac": hac.se, "se_nw10": hac.se_nw10, "se_by_block": by_block, "se_plateau": float(plateau),
            "se_blk250": by_block.get(250), "n_blocks": n_blocks, "T": T, "curve": curve, "B": int(B), "seed": int(seed)}


@dataclass(frozen=True)
class PowerLine:
    """`model_card.macro.power` (L2612) plus the UNDERPOWERED flag (rule 4) and the 50%-power years line."""
    se_hac: float
    se_blk250: Optional[float]
    se_plateau: float
    se_curve: dict
    mde80: float
    power_at_0p05: float
    power_at_0p10: float
    pc3_power_at_0: Optional[float]
    years_to_detect_0p05: float
    underpowered: bool
    sessions: int
    t_years: float
    card_class: str
    power_at: dict = field(default_factory=dict)
    years_to_detect_0p05_power50: Optional[float] = None
    delta_ni: float = 0.10

    def as_dict(self) -> dict:
        """The schema's power block: the nine L2612 fields plus `underpowered`."""
        return {"se_hac": self.se_hac, "se_blk250": self.se_blk250, "se_plateau": self.se_plateau, "se_curve": dict(self.se_curve),
                "mde80": self.mde80, "power_at_0p05": self.power_at_0p05, "power_at_0p10": self.power_at_0p10,
                "pc3_power_at_0": self.pc3_power_at_0, "years_to_detect_0p05": self.years_to_detect_0p05,
                "underpowered": self.underpowered}


POWER_FIELDS = ("se_hac", "se_blk250", "se_plateau", "se_curve", "mde80", "power_at_0p05", "power_at_0p10",
                "pc3_power_at_0", "years_to_detect_0p05")


def _power(delta: float, se: float) -> float:
    return float(sps.norm.cdf(delta / se - Z_ALPHA))


def power_line(se, *, sessions: int, card_class: str = "CARD-P", deltas: Sequence[float] = (0.05, 0.10),
               delta_ni: float = 0.10) -> PowerLine:
    """The power line printed on every card (L2572-2576). `se` is an `se_ladder` dict or a bare SE (then every
    SE field is that number). `mde80 = 2.1232 * se_plateau`; `power at D = Phi(D/se - 1.2816)`; CARD-P adds
    `pc3_power_at_0 = Phi(delta_ni/se - 1.2816)`; `years_to_detect_0p05 = T_years * (2.1232 * se / 0.05)^2` with
    `T_years = sessions/252` and `se = se_plateau`; `underpowered = mde80 > 0.10`. reading (task M7-06 line): the
    50%-power years line uses `z_0.90 + z_0.50 = 1.2816` in place of 2.1232; printed only."""
    if card_class not in ("CARD-O", "CARD-P"):
        raise StatsRefused(f"card_class must be CARD-O or CARD-P, got {card_class!r}")
    sessions = int(sessions)
    if sessions < 1:
        raise ValueError("sessions must be >= 1")
    if isinstance(se, dict):
        se_hac, se_plateau = float(se["se_hac"]), float(se["se_plateau"])
        se_blk250 = se.get("se_blk250")
        if se_blk250 is None and 250 in (se.get("se_by_block") or {}):
            se_blk250 = se["se_by_block"][250]
        curve = dict(se.get("curve") or {})
    else:
        se_hac = se_plateau = float(se)
        se_blk250, curve = float(se), {"hac": float(se), "250": float(se)}
    if not (se_plateau > 0 and math.isfinite(se_plateau)):
        raise ValueError("se_plateau must be a positive finite number")
    if se_blk250 is not None:
        se_blk250 = float(se_blk250)
    t_years = sessions / TRADING_DAYS
    power_at = {float(d): _power(float(d), se_plateau) for d in deltas}
    mde80 = MDE_FACTOR * se_plateau
    return PowerLine(se_hac=se_hac, se_blk250=se_blk250, se_plateau=se_plateau, se_curve=curve, mde80=float(mde80),
                     power_at_0p05=power_at.get(0.05, _power(0.05, se_plateau)),
                     power_at_0p10=power_at.get(0.10, _power(0.10, se_plateau)),
                     pc3_power_at_0=_power(float(delta_ni), se_plateau) if card_class == "CARD-P" else None,
                     years_to_detect_0p05=float(t_years * (MDE_FACTOR * se_plateau / 0.05) ** 2),
                     underpowered=bool(mde80 > MDE80_UNDERPOWERED), sessions=sessions, t_years=float(t_years),
                     card_class=card_class, power_at=power_at,
                     years_to_detect_0p05_power50=float(t_years * (Z_ALPHA * se_plateau / 0.05) ** 2), delta_ni=float(delta_ni))


def check_power_block(power) -> None:
    """Refuse a card without its power block (L2619, T-POWER-02): every L2612 field present and the SEs finite."""
    if isinstance(power, PowerLine):
        power = power.as_dict()
    if not isinstance(power, dict):
        raise PowerBlockMissing("card has no power block")
    missing = [k for k in POWER_FIELDS if k not in power]
    if missing:
        raise PowerBlockMissing(f"power block lacks {missing}")
    for k in ("se_hac", "se_plateau", "mde80"):
        v = power[k]
        if v is None or not math.isfinite(float(v)) or float(v) <= 0:
            raise PowerBlockMissing(f"power.{k} is not a positive finite number: {v!r}")


def apply_underpowered(check_id: str, failed: bool, power) -> tuple[Optional[str], Optional[str]]:
    """Rule 4 (L2576): a failed step-5 (CARD-O) or PC-3 (CARD-P) p-value maps to INSUFFICIENT_DATA with reason
    `underpowered` when MDE80 > 0.10, else `inconclusive`. Any other check id raises (L2622): it never waives
    PC-1', PC-2, the PC-3 point REJECT or step 3. Returns (verdict, reason) or (None, None) when the check passed."""
    if check_id not in UNDERPOWERED_CONVERTS:
        raise StatsRefused(f"UNDERPOWERED applies only to {UNDERPOWERED_CONVERTS}, not {check_id!r} (L2576, L2622)")
    if not failed:
        return None, None
    mde80 = power.mde80 if isinstance(power, PowerLine) else float(power["mde80"])
    return "INSUFFICIENT_DATA", ("underpowered" if mde80 > MDE80_UNDERPOWERED else "inconclusive")


# --------------------------------------------------------------------------- #
# Multiplicity lines (printed, never gated): BY q, Harvey-Liu haircut, Lo-adjusted Sharpe
# --------------------------------------------------------------------------- #
def by_qvalue(pvalues: Sequence[float]) -> np.ndarray:
    """Benjamini-Yekutieli q-values of the analytic HAC/LW p-values of every tested variant (L2579, B2).

    reading (section F-21): sort ascending, `q_(i) = min_{j>=i} p_(j) * m * c(m) / j`, `c(m) = sum_{k<=m} 1/k`,
    capped at 1; returned in the input order. The runner collects the variants' analytic HAC p-values and passes
    them to `gate_ledger.step3(pvalues=)`, which prints `by_q` and `holm` beside the step-3 lines."""
    p = np.asarray(pvalues, dtype=float).ravel()
    m = p.size
    if m == 0:
        return p
    if np.any(~np.isfinite(p)) or np.any(p < 0) or np.any(p > 1):
        raise ValueError("p-values must lie in [0, 1]")
    order = np.argsort(p, kind="stable")
    c_m = float(np.sum(1.0 / np.arange(1, m + 1)))
    adj = p[order] * m * c_m / np.arange(1, m + 1)
    q_sorted = np.minimum(1.0, np.minimum.accumulate(adj[::-1])[::-1])
    q = np.empty(m)
    q[order] = q_sorted
    return q


def holm_adjusted(pvalues: Sequence[float]) -> np.ndarray:
    """Holm step-down adjusted p-values of the same variant p-values (printed beside BY q, never gated).

    reading: sort ascending, `p_adj_(i) = max_{j<=i} (m - j + 1) p_(j)`, capped at 1; returned in the input order."""
    p = np.asarray(pvalues, dtype=float).ravel()
    m = p.size
    if m == 0:
        return p
    if np.any(~np.isfinite(p)) or np.any(p < 0) or np.any(p > 1):
        raise ValueError("p-values must lie in [0, 1]")
    order = np.argsort(p, kind="stable")
    adj = np.minimum(1.0, np.maximum.accumulate(p[order] * (m - np.arange(m))))
    out = np.empty(m)
    out[order] = adj
    return out


def sharpe_z(sr_annual: float, sessions: int) -> float:
    """z of an annualised Sharpe over `sessions` daily observations: `SR_ann * sqrt(T/252)` (iid form)."""
    return float(sr_annual) * math.sqrt(int(sessions) / TRADING_DAYS)


def harvey_liu_haircut(z: float, M: int) -> dict:
    """Harvey-Liu (2015) haircut of a Sharpe t-statistic for M trials, printed beside `live_sharpe_multiplier`.

    reading (section F-21, B2): `p1 = 1 - Phi(z)`, `p_adj = min(1, M * p1)` (Bonferroni), `z_adj = Phi_inv(1 - p_adj)`,
    `haircut = 1 - max(z_adj, 0)/z` (1.0 when z <= 0). Never gated."""
    z, M = float(z), int(M)
    if M < 1:
        raise ValueError("M must be >= 1")
    p1 = _analytic_p(z)
    p_adj = min(1.0, M * p1)
    z_adj = float(sps.norm.ppf(1.0 - p_adj)) if p_adj < 1.0 else 0.0
    haircut = 1.0 if z <= 0 else 1.0 - max(z_adj, 0.0) / z
    return {"z": z, "M": M, "p1": p1, "p_adj": p_adj, "z_adj": z_adj, "haircut": float(haircut),
            "sharpe_multiplier": float(1.0 - haircut), "live_sharpe_multiplier": LIVE_SHARPE_MULTIPLIER}


def lo_adjusted_sr(x, lags: int, *, q: int = TRADING_DAYS) -> dict:
    """Lo (2002) autocorrelation-adjusted annual Sharpe (L2590; printed at 20 lags and at all lags, never gated).

    reading (B2): `eta(q) = q / sqrt(q + 2 sum_{k=1}^{q-1} (q-k) rho_k)`, q = 252, `rho_k = 0` for k > lags;
    `lo_sr = eta * SR_daily`. `eta_ratio = eta/sqrt(q)` is 1 under iid (QF3-A21 quotes 0.838 / 0.951).
    `se_lo` is `validate.lo_se` (the iid SE of the annual Sharpe), printed beside it."""
    d = np.asarray(x, dtype=float).ravel()
    d = d[np.isfinite(d)]
    if d.size < 30:
        raise ValueError("lo_adjusted_sr needs >= 30 observations")
    lags = int(min(int(lags), q - 1, d.size - 2))
    if lags < 0:
        raise ValueError("lags must be >= 0")
    u = d - d.mean()
    g0 = float(u @ u)
    rho = np.array([float(u[k:] @ u[:-k]) / g0 for k in range(1, lags + 1)]) if g0 > 0 and lags > 0 else np.zeros(0)
    s = 2.0 * float(np.sum((q - np.arange(1, lags + 1)) * rho))
    eta = q / math.sqrt(q + s) if q + s > 0 else float("nan")
    sr_daily = V.sharpe(d) / math.sqrt(TRADING_DAYS)
    return {"sr_annual_iid": V.sharpe(d), "lo_sr": float(eta * sr_daily), "eta": float(eta),
            "eta_ratio": float(eta / math.sqrt(q)), "lags": lags, "q": int(q), "se_lo": V.lo_se(d)}


# --------------------------------------------------------------------------- #
# Unit-declared PSR / DSR (T-DSR-01, T-DSR-02)
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Sharpe:
    """A Sharpe ratio with its unit, so an annualised value can never be read as a per-period one."""
    value: float
    units: str          # daily | monthly | annual

    def __post_init__(self):
        if self.units not in ("daily", "monthly", "annual"):
            raise StatsRefused(f"Sharpe.units must be daily, monthly or annual, got {self.units!r}")


def psr(sr, T: int, *, units: str, sr0: float = 0.0, skew: float = 0.0, kurt: float = 3.0) -> float:
    """Probabilistic Sharpe ratio (BLdP 2014) of a per-period Sharpe `sr` over `T` periods of the declared unit:
    `Phi((sr - sr0) sqrt(T - 1) / sqrt(1 - skew sr + (kurt - 1)/4 sr^2))`, `sr0` the hurdle in the same unit
    (the deflated Sharpe when `sr0 = SE_null * e(N)`, L2522). `units` in {daily, monthly}; a `Sharpe` whose unit
    differs from `units` (an annualised SR with a daily T) raises (T-DSR-02)."""
    if units not in PERIODS:
        raise StatsRefused(f"units must be one of {sorted(PERIODS)}, got {units!r}")
    if isinstance(sr, Sharpe):
        if sr.units != units:
            raise StatsRefused(f"a {sr.units} Sharpe ratio was passed with a {units} T; one declared unit only (T-DSR-02)")
        sr = sr.value
    sr, T = float(sr), int(T)
    if T < 3:
        raise ValueError("T must be >= 3")
    denom = 1.0 - skew * sr + (kurt - 1.0) / 4.0 * sr ** 2
    if denom <= 0:
        return float("nan")
    return float(sps.norm.cdf((sr - float(sr0)) * math.sqrt(T - 1) / math.sqrt(denom)))


def dsr_vs_zero(x, *, units: str, n_trials: int, sr_sd_annual: float) -> float:
    """DSR vs 0 of a per-period series in the declared unit through `validate.deflated_sharpe`: the trials'
    Sharpe dispersion is converted from annual to the unit (`/ sqrt(periods per year)`). The same card on daily
    and on monthly data agrees within 0.1 (T-DSR-02)."""
    if units not in PERIODS:
        raise StatsRefused(f"units must be one of {sorted(PERIODS)}, got {units!r}")
    return V.deflated_sharpe(np.asarray(x, dtype=float), n_trials=int(n_trials),
                             sr_sd_daily=float(sr_sd_annual) / math.sqrt(PERIODS[units]))


# --------------------------------------------------------------------------- #
# PBO by CSCV on the card's own objective (step 4)
# --------------------------------------------------------------------------- #
def _sharpe_from_sums(s1, s2, n):
    """Annualised Sharpe (ddof 1) of a union of blocks from per-block sums and sums of squares."""
    n = np.asarray(n, dtype=float)
    mean = s1 / n[:, None] if s1.ndim == 2 else s1 / n
    var = (s2 - n[:, None] * mean ** 2) / (n[:, None] - 1.0) if s1.ndim == 2 else (s2 - n * mean ** 2) / (n - 1.0)
    ok = var > 0
    return np.where(ok, mean / np.sqrt(np.where(ok, var, 1.0)), 0.0) * math.sqrt(TRADING_DAYS)


def _windows(x: np.ndarray, h: int) -> np.ndarray:
    """Overlapping h-period compounded returns inside one block (never spanning a join)."""
    if x.shape[0] < h:
        return np.zeros((0,) + x.shape[1:])
    c = np.cumprod(1.0 + x, axis=0)
    out = np.empty((x.shape[0] - h + 1,) + x.shape[1:])
    out[0] = c[h - 1] - 1.0
    out[1:] = c[h:] / c[:-h] - 1.0
    return out


def _es(windows: np.ndarray, level: float) -> np.ndarray:
    """ES at `level` as a positive loss per column: -mean of the lowest ceil((1-level) n) values (section F-10)."""
    n = windows.shape[0]
    k = max(1, int(math.ceil((1.0 - level) * n)))
    part = np.partition(windows, k - 1, axis=0)[:k]
    return -part.mean(axis=0)


def pbo_on_claim(configs, comparator, *, objective="sharpe", S: int = 16, min_configs: int = PBO_MIN_CONFIGS,
                 winner_loses_share_gt: float = PBO_WINNER_LOSES_SHARE, horizon: int = 21, level: float = 0.95) -> dict:
    """PBO by CSCV (Bailey et al. 2017) on the card's own claim (L2581-2589, B2).

    `configs`: (T, G) daily excess returns of every configuration (family ledger union the frozen PC-6 grid; the
    runner assembles the set from `gate_ledger.FamilyLedger.difference_series` and the PC-6 runs); `comparator`: (T,) the
    overlay-off book (CARD-O) or S (CARD-P). S = 16 contiguous blocks (`np.array_split`), all C(S, S/2) splits.
    Objective per half: `"sharpe"` = paired delta_SR vs the comparator (CARD-O); `"des95_21"` = ES95 of the
    pooled within-block 21-session windows of the comparator minus the configuration's (CARD-P; windows never
    span a block join, section F-17); or a callable `(rows_configs, rows_comparator) -> (G,)`. Per split: best
    in sample, rank `r = #{obj_oos <= obj_oos[best]}`, `w = r/(G+1)`, `pbo = share(logit(w) < 0)` (the
    `validate.pbo_cscv` convention; reproduces 0.535897 on QF3's noise recipe). `winner_loses` = the in-sample
    best's out-of-sample objective below the comparator's (< 0) in more than 10% of splits. Fewer than
    `min_configs` configurations: `{"pbo": None, "note": "PBO not run (n < 10)", ...}`, never imputed.
    Sharpe fast path: per-block sums and sums of squares, one matrix product per split set."""
    M = np.asarray(configs, dtype=float)
    if M.ndim != 2:
        raise ValueError("configs must be a (T, G) matrix")
    c = np.asarray(comparator, dtype=float).ravel()
    T, G = M.shape
    if c.size != T:
        raise ValueError("comparator length differs from configs")
    S = int(S)
    base = {"n_configs": int(G), "S": S, "objective": objective if isinstance(objective, str) else "callable",
            "winner_loses_share_gt": float(winner_loses_share_gt)}
    if G < min_configs:
        return {**base, "pbo": None, "winner_loses_share": None, "winner_loses": None, "slope": None, "n_splits": 0,
                "note": f"PBO not run (n < {min_configs})", "reason": f"{G} configurations; the step needs >= {min_configs}"}
    if T < 2 * S or S % 2:
        raise ValueError("CSCV needs an even S and T >= 2 S")
    blocks = np.array_split(np.arange(T), S)
    splits = list(combinations(range(S), S // 2))
    A = np.zeros((len(splits), S))
    for i, tr in enumerate(splits):
        A[i, list(tr)] = 1.0
    if objective == "sharpe":
        s1 = np.array([M[b].sum(axis=0) for b in blocks]); s2 = np.array([(M[b] ** 2).sum(axis=0) for b in blocks])
        c1 = np.array([c[b].sum() for b in blocks]); c2 = np.array([(c[b] ** 2).sum() for b in blocks])
        n = np.array([len(b) for b in blocks], dtype=float)
        obj = []
        for mask in (A, 1.0 - A):
            sr_cfg = _sharpe_from_sums(mask @ s1, mask @ s2, mask @ n)
            sr_cmp = _sharpe_from_sums(mask @ c1, mask @ c2, mask @ n)
            obj.append(sr_cfg - sr_cmp[:, None])
        obj_is, obj_oos = obj
    else:
        if objective == "des95_21":
            w_cfg = [_windows(M[b], horizon) for b in blocks]
            w_cmp = [_windows(c[b], horizon) for b in blocks]

            def _obj(tr):
                pooled = np.concatenate([w_cfg[j] for j in tr]); pooled_c = np.concatenate([w_cmp[j] for j in tr])
                if pooled.shape[0] < 2:
                    raise ValueError("a CSCV half holds fewer than two windows; use a longer sample or a smaller S")
                return _es(pooled_c[:, None], level)[0] - _es(pooled, level)
        elif callable(objective):
            def _obj(tr):
                rows = np.concatenate([blocks[j] for j in tr])
                return np.asarray(objective(M[rows], c[rows]), dtype=float)
        else:
            raise ValueError("objective must be 'sharpe', 'des95_21' or a callable")
        obj_is = np.array([_obj(tr) for tr in splits])
        obj_oos = np.array([_obj(tuple(j for j in range(S) if j not in tr)) for tr in splits])
    best = np.argmax(np.where(np.isfinite(obj_is), obj_is, -np.inf), axis=1)
    rows = np.arange(len(splits))
    oos_best = obj_oos[rows, best]
    rank = (obj_oos <= oos_best[:, None]).sum(axis=1).astype(float)
    w = rank / (G + 1.0)
    logits = np.log(w / (1.0 - w))
    is_best = obj_is[rows, best]
    slope = float(np.polyfit(is_best, oos_best, 1)[0]) if np.unique(is_best).size > 1 else float("nan")
    share = float(np.mean(oos_best < 0.0))
    return {**base, "pbo": float(np.mean(logits < 0)), "winner_loses_share": share,
            "winner_loses": bool(share > winner_loses_share_gt), "slope": slope, "n_splits": int(len(splits))}


def pbo_null(n_configs: int, T: int, *, S: int = 16, seed: int = SEED_STUDY, objective="sharpe", sigma: float = 0.01) -> float:
    """The null-calibrated PBO printed beside the card's (L2589): the same CSCV on `n_configs` >= 10 pure-noise
    configurations `N(0, sigma)` against a noise comparator, `default_rng(seed)`."""
    if int(n_configs) < PBO_MIN_CONFIGS:
        raise ValueError(f"pbo_null needs >= {PBO_MIN_CONFIGS} configurations")
    rng = np.random.default_rng(seed)
    M = rng.normal(0.0, sigma, size=(int(T), int(n_configs)))
    c = rng.normal(0.0, sigma, size=int(T))
    return float(pbo_on_claim(M, c, objective=objective, S=S)["pbo"])


# --------------------------------------------------------------------------- #
# Class-near-threshold helper (L5738: a verdict within tolerance of its threshold is a class, never a point)
# --------------------------------------------------------------------------- #
def verdict_class(stat: float, threshold: float, tol: float, *, at_or_above: str, below: str) -> frozenset:
    """The set of verdicts a statistic supports: both when `|stat - threshold| <= tol`, else the one its side names.
    The caller names the two verdicts (e.g. p_ni vs 0.10: at_or_above="INSUFFICIENT_DATA", below="PASS")."""
    stat, threshold, tol = float(stat), float(threshold), float(tol)
    if abs(stat - threshold) <= tol + 1e-12:
        return frozenset({at_or_above, below})
    return frozenset({at_or_above}) if stat >= threshold else frozenset({below})
