"""Costed golden engine, research bootstrap, v1.2-check mode and the reference-mode guard
(TASK-M2-06, TASK-M2-07; spec section 9.3.1 L5720-5725, section 9.3.3 L5984-5992, section 8.5 L5016-5020, P10; R-26).

Conventions, verbatim from L5721-5725 and L5019-5020:
- simple daily returns; a weight built through the close of t-1 earns the return of t (`earning_weights` shifts);
- cost = rate per side x |dw| on the day the new weight earns; the initial entry is uncosted; buy-and-hold and S
  (the same-exposure static book) are uncosted; an L/S sleeve pays its overlay turnover on both legs (`legs=2`);
- every result is rerun at 2x (`stress=2.0`); a stress below 1x is a lowered cost and raises (L602);
- research bootstrap: circular 63-day blocks, 1,000 resamples, seed 20261002, paired (same blocks for both books);
  share = fraction of resamples with dSR* > 0 (= 1 - `validate.sharpe_diff_bootstrap(...)["p"]`);
- v1.2-check mode reproduces PC-1..PC-7 of `.v1.2_INTEGRATION_backup.md` section 8.7 as section 9.3.3 states them
  and returns the v1.2 verdict class in the order sufficiency -> REJECT -> inconclusive -> REVISE -> PASS. It is
  labelled "v1.2-check, never a verdict": nothing here is a card result, enters a book or an artifact.

Reference mode (L5992). Configurations the rules store refuses (a vol-target cap above 1.0, a weight path above
1.0, product stacks, the literal v1.2 ladder) are computed only when `reference_only=True` AND the first caller
outside `core/` is a module under `tests/reference/` or `docs/` (`reference_guard` inspects the stack). The
keyword defaults to False everywhere, so production code can never reach them, and `tests/reference/` is never
imported by `core/` (tests/macro_m2_costed.py checks statically). T-CAP-01 / T-DNB-01 apply to the store and
the books, not to this mode.

This module is research arithmetic on arrays. It reads no store, takes no clock and is not an acting path: the
acting vol target is `core/quant/risk_layer.market_vol_target` (reads through `pit_window`).
"""
from __future__ import annotations

import inspect
import math
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Optional, Sequence

import numpy as np

from core.quant import gate_stats as GS
from core.quant.validate import TRADING_DAYS, sharpe, sharpe_diff_bootstrap

ROOT = Path(__file__).resolve().parents[2]
REFERENCE_DIRS = (ROOT / "tests" / "reference", ROOT / "docs")
CORE_DIR = ROOT / "core"
SEED_RESEARCH_BOOTSTRAP = 20261002           # reproducibility.seed_research_bootstrap (L4680)
SEED_STUDY = 11                              # reproducibility.seed_study (L4680)
RESEARCH_BLOCK, RESEARCH_B = 63, 1000        # L5724
GATE_B = 2000                                # L5987
PC3_DELTA = 0.10                             # L5987
PC1_MIN_PP = 3.0                             # L5985
PC2_MAX_RATIO = 0.90                         # L5986
PC4_MIN_POSITIVE, PC4_MAX_SHARE = 3, 0.5     # L5988
PC5_MIN_YEARS = 0.60                         # L5989
PC6_MIN_KEEP = 0.5
PC7_MIN_ONSETS, PC7_MIN_WINDOWS, PC7_MIN_SESSIONS = 30, 5, 756 + 126   # L5989
V12_LABEL = "v1.2-check, never a verdict"
V12_CLASSES = ("INSUFFICIENT DATA (sufficiency)", "REJECT", "INSUFFICIENT DATA (inconclusive)", "REVISE", "PASS")
MIN_YEAR_SESSIONS = 126


class RefusedConfiguration(ValueError):
    """A configuration the rules store refuses was requested outside reference mode."""


# --------------------------------------------------------------------------- #
# Reference-mode guard
# --------------------------------------------------------------------------- #
def _under(path: Path, base: Path) -> bool:
    try:
        path.relative_to(base)
        return True
    except ValueError:
        return False


def reference_caller() -> Optional[Path]:
    """The file of the first stack frame outside `core/`, or None."""
    frame = inspect.currentframe()
    while frame is not None:
        path = Path(frame.f_code.co_filename)
        if path.is_absolute() and not _under(path.resolve(), CORE_DIR):
            return path.resolve()
        if not path.is_absolute():            # exec'd / interactive code: never a reference caller
            return None
        frame = frame.f_back
    return None


def reference_guard(reference_only: bool, what: str) -> None:
    """Raise `RefusedConfiguration` unless `reference_only` is True and the first caller outside `core/` lives
    under `tests/reference/` or `docs/` (L5992). Called by every function that can compute a refused shape."""
    if not reference_only:
        raise RefusedConfiguration(f"{what}: refused by the rules store (P2: nothing above 1.0, composition by min()); "
                                   "reference_only=True from tests/reference/ or docs/ is the only way to compute it")
    caller = reference_caller()
    if caller is None or not any(_under(caller, d) for d in REFERENCE_DIRS):
        raise RefusedConfiguration(f"{what}: reference_only=True is honoured only from tests/reference/ or docs/, "
                                   f"not from {caller}")


# --------------------------------------------------------------------------- #
# Engine
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class CostedPath:
    net: np.ndarray          # daily net return of the book
    gross: np.ndarray        # weight_earning x return
    cost: np.ndarray         # charge on each earning day (decimal)
    weights: np.ndarray      # the earning weights actually held (NaN warm-up -> 0)
    turnover: np.ndarray     # |dw| charged on each day (0 on the initial entry)
    cost_bp_per_side: float
    stress: float
    legs: int

    @property
    def turnover_per_year(self) -> float:
        return float(self.turnover.sum() / (self.net.size / TRADING_DAYS))

    @property
    def average_exposure(self) -> float:
        return float(np.mean(self.weights))


def earning_weights(weights_decided) -> np.ndarray:
    """`w_earning[t] = w_decided[t-1]`: a weight decided at the close of t earns from t+1 (L5723); the first day
    has no decided weight (NaN, not in the book)."""
    w = np.asarray(weights_decided, dtype=float)
    out = np.full(w.shape, np.nan)
    out[1:] = w[:-1]
    return out


def costed_path(weights_earning, returns, cost_bp_per_side: float, stress: float = 1.0, *, legs: int = 1,
                reference_only: bool = False) -> CostedPath:
    """Daily net returns of a weight path under the R4b cost convention. `weights_earning[t]` is the weight that
    earns `returns[t]` (use `earning_weights` on a decided path). A leading NaN run is warm-up (flat, uncosted);
    the first finite weight is the initial entry (uncosted); |dw| of every later day is charged at
    `cost_bp_per_side x stress x legs`. A weight path above 1.0 in absolute value is a refused configuration."""
    w = np.asarray(weights_earning, dtype=float)
    r = np.asarray(returns, dtype=float)
    if w.shape != r.shape or w.ndim != 1:
        raise ValueError("weights_earning and returns must be 1-d arrays of the same length")
    if not np.all(np.isfinite(r)):
        raise ValueError("returns must be finite")
    if not (math.isfinite(cost_bp_per_side) and cost_bp_per_side >= 0):
        raise ValueError("cost_bp_per_side must be a finite non-negative rate")
    if not (math.isfinite(stress) and stress >= 1.0):
        raise ValueError(f"stress {stress!r} below 1x lowers a pre-registered cost; never a permitted fix (L602)")
    if legs not in (1, 2):
        raise ValueError("legs is 1 (long-only) or 2 (an L/S sleeve pays both legs, L5019)")
    valid = np.isfinite(w)
    first = int(np.argmax(valid)) if valid.any() else w.size
    if not valid[first:].all():
        raise ValueError("weight path has a gap after the initial entry; a missing weight fails closed, it is not 0")
    if valid.any() and np.max(np.abs(w[valid])) > 1.0 + 1e-12:
        reference_guard(reference_only, f"weight path up to {np.max(np.abs(w[valid])):.4g} > 1.0")
    held = np.where(valid, w, 0.0)
    turnover = np.zeros(w.size)
    if first + 1 < w.size:
        turnover[first + 1:] = np.abs(np.diff(w[first:]))
    cost = turnover * (cost_bp_per_side * 1e-4 * stress * legs)
    gross = held * r
    return CostedPath(gross - cost, gross, cost, held, turnover, float(cost_bp_per_side), float(stress), int(legs))


def same_exposure_static(weights_earning, off_returns) -> np.ndarray:
    """S, the CARD-P comparator: overlay-off x the mean multiplier, constant, same days, uncosted (L4972, L5187).
    The mean is over the days the overlay is in the book (finite weights)."""
    w = np.asarray(weights_earning, dtype=float)
    off = np.asarray(off_returns, dtype=float)
    if w.shape != off.shape:
        raise ValueError("weights_earning and off_returns must align")
    finite = np.isfinite(w)
    if not finite.any():
        raise ValueError("no finite weight: S is undefined")
    return float(np.mean(w[finite])) * off


def vt_weights(returns, target_ann: float, window: int = 20, cap: float = 1.0, *, reference_only: bool = False
               ) -> np.ndarray:
    """Research vol-target DECIDED weights on a return series: sigma_t = std(ddof 1) of the last `window`
    simple returns through t x sqrt(252); w_t = min(cap, target / sigma_t); NaN until `window` returns exist
    (tf_algorithms 'vt'; R-06 L1561-1562). `cap > 1.0` is a refused configuration (reference mode only).
    The acting path is `core/quant/risk_layer.market_vol_target` (# integration: provided by package A)."""
    r = np.asarray(returns, dtype=float)
    if not (math.isfinite(target_ann) and target_ann > 0) or window < 2:
        raise ValueError("target_ann must be positive and window >= 2")
    if not (math.isfinite(cap) and cap > 0):
        raise ValueError("cap must be a positive number")
    if cap > 1.0:
        reference_guard(reference_only, f"vol-target cap {cap} > 1.0")
    out = np.full(r.shape, np.nan)
    for t in range(window - 1, r.size):          # ponytail: O(T x window) loop; sliding_window_view if T > 1e6
        x = r[t - window + 1:t + 1]
        if not np.all(np.isfinite(x)):
            continue
        sig = float(np.std(x, ddof=1)) * math.sqrt(TRADING_DAYS)
        if sig > 0 and math.isfinite(sig):
            out[t] = min(cap, target_ann / sig)
    return out


# --------------------------------------------------------------------------- #
# Statistics
# --------------------------------------------------------------------------- #
def nav(daily) -> np.ndarray:
    return np.cumprod(1.0 + np.asarray(daily, dtype=float))


def max_drawdown(daily) -> float:
    """min(NAV / cummax(NAV) - 1) on the cumulative simple-return NAV (negative fraction)."""
    eq = nav(daily)
    return float(np.min(eq / np.maximum.accumulate(eq) - 1.0)) if eq.size else float("nan")


def _dates(dates) -> np.ndarray:
    d = np.asarray(dates)
    if d.dtype.kind != "M":
        d = np.array([np.datetime64(x) for x in dates], dtype="datetime64[D]")
    return d.astype("datetime64[D]")


def window_mask(dates, start: date, end: date, include_start: bool = False) -> np.ndarray:
    """Return dates of a window: after the start close through the end close; `include_start` adds the start
    date's own return (the four KOSPI windows of L5136-5140)."""
    d = _dates(dates)
    lo, hi = np.datetime64(start, "D"), np.datetime64(end, "D")
    return ((d >= lo) if include_start else (d > lo)) & (d <= hi)


def window_return(daily, dates, start: date, end: date, include_start: bool = False) -> float:
    """Cumulative simple return of a book over the window's return dates."""
    m = window_mask(dates, start, end, include_start)
    return float(np.prod(1.0 + np.asarray(daily, dtype=float)[m]) - 1.0)


def calendar_years(daily, dates, min_sessions: int = MIN_YEAR_SESSIONS) -> dict[int, float]:
    """Compounded return per calendar year with at least `min_sessions` sessions."""
    d, x = _dates(dates), np.asarray(daily, dtype=float)
    years = d.astype("datetime64[Y]").astype(int) + 1970
    out = {}
    for y in np.unique(years):
        m = years == y
        if m.sum() >= min_sessions:
            out[int(y)] = float(np.expm1(np.sum(np.log1p(x[m]))))
    return out


def tail_exposure_ratio(exposure, off_returns, q: float = 0.05) -> float:
    """PC-2: mean exposure on the worst ceil(q n) days of the overlay-off book over the mean exposure."""
    h, off = np.asarray(exposure, dtype=float), np.asarray(off_returns, dtype=float)
    k = int(math.ceil(q * off.size))
    worst = np.argsort(off, kind="stable")[:k]
    mean_h = float(np.mean(h))
    return float(np.mean(h[worst]) / mean_h) if mean_h > 0 else float("nan")


def declustered_onsets(exposure, gap: int, threshold: float = 0.5) -> int:
    """Onsets where h[t-1] >= threshold and h[t] < threshold, chains merged within `gap` sessions (the labs' rule)."""
    h = np.asarray(exposure, dtype=float)
    on = np.flatnonzero((h[:-1] >= threshold) & (h[1:] < threshold)) + 1
    if on.size == 0:
        return 0
    return int(1 + np.sum(np.diff(on) > gap))


# --------------------------------------------------------------------------- #
# Bootstraps
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class BootShare:
    share: float             # fraction of resamples with dSR* > 0
    dsr: float               # point SR(rule) - SR(comparator)
    p: float                 # fraction with dSR* <= 0 (validate's p)
    ci: tuple[float, float]  # 90% percentile interval of dSR*
    block: int
    B: int
    seed: int


def research_bootstrap(rule, comparator, *, block: int = RESEARCH_BLOCK, B: int = RESEARCH_B,
                       seed: int = SEED_RESEARCH_BOOTSTRAP) -> BootShare:
    """The section 9.3.1 research bootstrap (L5724) through `validate.sharpe_diff_bootstrap`: paired circular
    blocks, the share of resamples whose Sharpe difference is positive. A difference series alone cannot give
    dSR*, so both books are required."""
    a, b = np.asarray(rule, dtype=float), np.asarray(comparator, dtype=float)
    if a.shape != b.shape or a.ndim != 1 or a.size < 2 * block:
        raise ValueError("rule and comparator must be aligned 1-d series with at least two blocks")
    out = sharpe_diff_bootstrap(a, b, block=block, B=B, level=0.90, seed=seed)
    return BootShare(1.0 - out["p"], float(out["diff"]), float(out["p"]), tuple(out["ci"]), block, B, seed)


def gate_boot(rule, comparator, *, block: int, B: int = GATE_B, seed: int = SEED_STUDY,
              delta: float = PC3_DELTA) -> float:
    """R4b's percentile `gate_boot`: P(dSR* <= -delta) on paired circular blocks (L5987)."""
    a, b = np.asarray(rule, dtype=float), np.asarray(comparator, dtype=float)
    if a.shape != b.shape or a.ndim != 1 or a.size < 2 * block:
        raise ValueError("rule and comparator must be aligned 1-d series with at least two blocks")
    idx = GS.block_indices(a.size, block, B, seed, "circular")
    d = GS.row_sharpes(a[idx]) - GS.row_sharpes(b[idx])
    return float(np.mean(d <= -delta))


# --------------------------------------------------------------------------- #
# v1.2-check mode
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class V12Result:
    label: str
    verdict_class: str
    pc1: bool
    pc2: bool
    pc3: bool
    pc4: bool
    pc5: bool
    pc6: Optional[bool]      # None when no neighbour grid was declared (n/e)
    pc7: bool
    dmdd_1x_pp: float
    dmdd_2x_pp: float
    mdd_on: float
    mdd_off: float
    mdd_S: float
    tail_ratio: float
    dsr_1x: float
    dsr_2x: float
    p10: float
    p_pw: float
    p_ni: float
    pw_block_d: float
    pw_block_d2: float
    block: int
    bonferroni: int
    n_sessions: int
    n_windows: int
    n_positive: int
    largest_share: float
    years_positive_share: float
    onsets: Optional[int]
    neighbours_kept: Optional[float]


def v12_check(on, off, S, *, on_2x, exposure, dates, windows: Sequence[tuple] = (), neighbours=None,
              discrete: bool = False, onset_gap: int = 250, bonferroni: int = 1, B: int = GATE_B,
              seed: int = SEED_STUDY) -> V12Result:
    """PC-1..PC-7 (L5985-5990) on daily books: `on` (rule, 1x costs), `on_2x` (2x), `off` (overlay-off),
    `S` (same-exposure static, uncosted), `exposure` (the earning multiplier path), `dates` (return dates),
    `windows` [(start, end, include_start)], `neighbours` [(on_n, S_n)] for PC-6 (None = n/e). Returns the v1.2
    class in the order sufficiency -> REJECT -> inconclusive -> REVISE -> PASS. Labelled, never a verdict."""
    on, off, S, on_2x = (np.asarray(x, dtype=float) for x in (on, off, S, on_2x))
    h = np.asarray(exposure, dtype=float)
    n = on.size
    if not (off.shape == S.shape == on_2x.shape == h.shape == (n,)):
        raise ValueError("on, off, S, on_2x and exposure must align")
    if bonferroni < 1:
        raise ValueError("bonferroni is a count of configurations searched, >= 1")
    mdd_on, mdd_off, mdd_S, mdd_2x = max_drawdown(on), max_drawdown(off), max_drawdown(S), max_drawdown(on_2x)
    dmdd_1x, dmdd_2x = (mdd_on - mdd_S) * 100.0, (mdd_2x - mdd_S) * 100.0
    pc1_1x = dmdd_1x >= PC1_MIN_PP and mdd_on > mdd_off
    pc1_2x = dmdd_2x >= PC1_MIN_PP and mdd_2x > mdd_off
    pc1 = pc1_1x and pc1_2x
    tail = tail_exposure_ratio(h, off)
    pc2 = tail <= PC2_MAX_RATIO
    d = on - S
    pw_d, pw_d2 = GS.pw_block(d), GS.pw_block(d * d)
    block = int(max(GS.PC3_BLOCK_FLOOR, math.ceil(pw_d), math.ceil(pw_d2)))
    p10 = gate_boot(on, S, block=GS.PC3_BLOCK_FLOOR, B=B, seed=seed)
    p_pw = gate_boot(on, S, block=block, B=B, seed=seed)
    p_ni = min(1.0, max(p10, p_pw) * bonferroni)
    dsr_1x, dsr_2x = sharpe(on) - sharpe(S), sharpe(on_2x) - sharpe(S)
    pc3 = p_ni <= 0.10 and dsr_1x >= -PC3_DELTA
    pc3_point_2x = dsr_2x >= -PC3_DELTA
    benefits = []
    for start, end, include_start in windows:
        m = window_mask(dates, start, end, include_start)
        if m.any():
            benefits.append(float(np.prod(1 + on[m]) - np.prod(1 + S[m])))
    positive = [b for b in benefits if b > 0]
    n_positive, largest = len(positive), (max(positive) / sum(positive) if positive else 0.0)
    pc4 = n_positive >= PC4_MIN_POSITIVE and largest <= PC4_MAX_SHARE
    years = calendar_years(on, dates)
    years_share = float(np.mean([v > 0 for v in years.values()])) if years else 0.0
    pc5 = years_share >= PC5_MIN_YEARS
    kept = None
    if neighbours:
        keep = [((max_drawdown(a) - max_drawdown(b)) * 100.0 >= 0.5 * dmdd_1x) and (sharpe(a) - sharpe(b) >= -PC3_DELTA)
                for a, b in neighbours]
        kept = float(np.mean(keep))
    pc6 = None if kept is None else kept >= PC6_MIN_KEEP
    onsets = declustered_onsets(h, onset_gap) if discrete else None
    pc7 = n >= PC7_MIN_SESSIONS and len(benefits) >= PC7_MIN_WINDOWS and (not discrete or onsets >= PC7_MIN_ONSETS)
    if not pc7:
        cls = V12_CLASSES[0]
    elif not pc1_1x or not pc2 or dsr_1x < -PC3_DELTA or n_positive < PC4_MIN_POSITIVE:
        cls = V12_CLASSES[1]
    elif p_ni > 0.10 or largest > PC4_MAX_SHARE:
        cls = V12_CLASSES[2]
    elif not pc1_2x or not pc3_point_2x or pc6 is False or not pc5:
        cls = V12_CLASSES[3]
    else:
        cls = V12_CLASSES[4]
    return V12Result(V12_LABEL, cls, pc1, pc2, pc3, pc4, pc5, pc6, pc7, dmdd_1x, dmdd_2x, mdd_on, mdd_off, mdd_S,
                     tail, dsr_1x, dsr_2x, p10, p_pw, p_ni, pw_d, pw_d2, block, int(bonferroni), n, len(benefits),
                     n_positive, largest, years_share, onsets, kept)
