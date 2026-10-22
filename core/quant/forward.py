"""R-25 forward-record monitoring and demotion v2 (TASK-M8-08; section 8.8 (a)-(e); P14; section 10 item 35).

A forward record is a falsification alarm and an integrity check only: it can lower a verdict and never raise one
(`ForwardRecordCannotRaise`; `monitoring.forward_record_can_raise_verdict: false`). Every statistical trigger reads
whole-book NAV: with the card at share `w_card` of the book, the whole book with the card on is
`w_card x r_on + (1 - w_card) x r_rest`, with the comparator substituted `w_card x r_cmp + (1 - w_card) x r_rest`,
so the paired difference is `w_card x (r_on - r_cmp)` (brief F-19) and sleeve NAV is never the denominator.

Triggers (L2672-2689): operational and integrity triggers demote immediately, outside the budget; the catastrophic
bound (CARD-P: all three of "forward dMDD vs S <= 0 = no protection", dES95-21 vs S <= 0, 12-month dSR vs S below
the design 2.5th percentile; CARD-O: either of the 6-month gap > 2 sigma or dSR below the 2.5th percentile) and the
monthly one-sided CUSUM (k 0.25, h bootstrap-calibrated for an in-control ARL >= 20 years) sit inside the D4 budget
(<= 10 % a year book-level, split equally across active cards, fixed at record start, verified on a 20-shift
circular placebo panel of the design sample; brief F-18 offset grid). Thresholds are calibrated once on the card's
full design sample and never recalibrated when cards are added.

The record (`ForwardRecord`) is append-only JSONL: it starts at the first decision the live workflow writes after
the header commit (never backfilled; a row dated at or before the last recorded session, or from a replay or
backtest run, is refused), gaps (late, missed, fail_closed, HALTED, DISARMED) are excluded from both sides of
every comparison, and alarm state resets only with a new card revision (`record_reset`). Demotion writes the
governance event and the family x market lockout; the demotion verdict never reads as a raise (brief F-22).

Nothing here reads a clock: every function takes `decision_utc` / `as_of` explicitly.
"""
from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass, field, replace
from datetime import date, datetime
from pathlib import Path
from typing import Callable, Mapping, Sequence

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from scipy import optimize, stats

from core.ficc.macro_schema import canonical_json
from core.quant import cardp
from core.quant import gate_stats as GS
from core.quant.validate import TRADING_DAYS, sharpe
from core.rules import governance as G

HONESTY_LINE = "12 months of forward record can only detect catastrophic decay."          # L2704, verbatim
CARD_P_TRIGGER_TEXT = "forward ΔMDD vs S ≤ 0 = no protection"                      # L2681, corrected sign
OPERATIONAL_TRIGGERS = ("lag_audit_violation", "acting_param_edit_outside_revision",
                        "provisional_or_stale_input_reached_acting_decision", "switches_gt_p99_poisson_negbin",
                        "operator_kill_of_forward_books", "decision_gaps_gt_10pct_rolling_12m")
CATASTROPHIC_P = ("fwd_dMDD_vs_S <= 0", "fwd_dES95_21_vs_S <= 0", "fwd_dSR_12m_vs_S < design_p2.5")
CATASTROPHIC_O = ("gap6m_comparator_minus_on_book_nav > 2 * sigma_design", "fwd_dSR_12m_vs_comparator < design_p2.5")
DEMOTION_VERDICT = {"operational_or_integrity": "REVISE", "catastrophic_or_cusum": "REJECT"}   # default, judgment
VERDICT_RANK = {**cardp.ORDER, "NOT_RUN": -1}        # a demotion never moves a verdict up this ranking
WINDOW_12M, WINDOW_6M, ES_HORIZON, ES_LEVEL = 252, 126, 21, 0.95
CUSUM_K, ARL_MIN_MONTHS, CUSUM_B, CUSUM_SEED, CUSUM_BLOCK = 0.25, 240, 2000, 11, 12
BUDGET_PER_YEAR, SHIFTS, MIN_OFFSET_SESSIONS, PANEL_SEED = 0.10, 20, 252, 11
GAP_SHARE_MAX, LOCKOUT_MONTHS, NEGBIN_LR_P = 0.10, 6, 0.05
GAP_FLAGS = ("late", "missed", "fail_closed", "halted", "disarmed")
RECORD_KINDS = ("start", "decision", "record_reset", "demotion", "kill")
CLASSES = ("CARD-P", "CARD-O")
COMPONENT = "core/quant/forward"


class ForwardRecordCannotRaise(ValueError):
    """Any attempt to use forward statistics to change a verdict upward raises (L2738; P14)."""


class RecordRefused(ValueError):
    """An append the integrity rules refuse: backfill, a non-live run, a record not started, a second start."""


class CalibrationRefused(ValueError):
    """The card's placebo panel cannot be brought under its split: no forward record may start (L2737)."""


# --------------------------------------------------------------------------- #
# Whole-book arithmetic
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class DesignSample:
    """The card's full design sample: the earning multiplier path `m` (NaN warm-up), the overlay-off daily excess
    returns, the rest of the book's daily return at its weights, the card's share of whole-book NAV and the
    pre-registered cost. `cls` picks the comparator: S (CARD-P) or overlay-off (CARD-O)."""
    dates: tuple
    m: np.ndarray
    off: np.ndarray
    rest: np.ndarray
    w_card: float
    cost_bp: float = 5.0
    cls: str = "CARD-P"

    def __post_init__(self) -> None:
        if self.cls not in CLASSES:
            raise ValueError(f"cls must be one of {CLASSES}")
        if not 0.0 < self.w_card <= 1.0:
            raise ValueError("w_card is the card's share of whole-book NAV in (0, 1]")
        n = len(self.dates)
        if not (len(self.m) == len(self.off) == len(self.rest) == n):
            raise ValueError("m, off, rest and dates must align")


def whole_book(design: DesignSample, m=None) -> tuple[np.ndarray, np.ndarray, np.ndarray, tuple]:
    """(book_on, book_cmp, w x (on - cmp), dates) on the finite rows: whole-book daily returns with the card on and
    with its comparator substituted; the rest of the book cancels in the paired difference."""
    books = cardp.build_books(design.m if m is None else m, design.off, design.cost_bp, design.dates, stress_2x=False)
    cmp_ = books.S if design.cls == "CARD-P" else books.off
    ok = np.isfinite(books.on) & np.isfinite(cmp_)
    w = design.w_card
    on, cmp_, rest = books.on[ok], cmp_[ok], np.asarray(design.rest, dtype=float)[ok]
    dates = tuple(d for d, k in zip(design.dates, ok) if k)
    return w * on + (1.0 - w) * rest, w * cmp_ + (1.0 - w) * rest, w * (on - cmp_), dates


def rolling_sharpe(x, w: int = WINDOW_12M) -> np.ndarray:
    v = sliding_window_view(np.asarray(x, dtype=float), w)
    sd = v.std(axis=1, ddof=1)
    return np.where(sd > 0, v.mean(axis=1) / np.where(sd > 0, sd, 1.0), 0.0) * math.sqrt(TRADING_DAYS)


def rolling_mdd(x, w: int = WINDOW_12M) -> np.ndarray:
    """Max drawdown (negative fraction) of every trailing window of `w` sessions."""
    eq = np.cumprod(1.0 + sliding_window_view(np.asarray(x, dtype=float), w), axis=1)
    return np.min(eq / np.maximum.accumulate(eq, axis=1) - 1.0, axis=1)


def rolling_es(x, w: int = WINDOW_12M, h: int = ES_HORIZON, q: float = ES_LEVEL) -> np.ndarray:
    """ES_q of the overlapping h-session returns ending inside each trailing window (positive loss; cardp.es)."""
    hr = cardp.horizon_returns(np.asarray(x, dtype=float), h)       # length n - h + 1, aligned to window ends
    v = sliding_window_view(hr, w - h + 1)
    k = int(math.ceil((1.0 - q) * v.shape[1]))
    return -np.mean(np.partition(v, k - 1, axis=1)[:, :k], axis=1)


def rolling_return(x, w: int) -> np.ndarray:
    return np.prod(1.0 + sliding_window_view(np.asarray(x, dtype=float), w), axis=1) - 1.0


def card_p_lines(book_on, book_cmp, w: int = WINDOW_12M) -> dict[str, np.ndarray]:
    """Per window end: dMDD (mdd_on - mdd_cmp, positive = protection), dES21 (es_cmp - es_on), dSR12 (sr_on - sr_cmp)."""
    return {"dMDD": rolling_mdd(book_on, w) - rolling_mdd(book_cmp, w),
            "dES21": rolling_es(book_cmp, w) - rolling_es(book_on, w),
            "dSR12": rolling_sharpe(book_on, w) - rolling_sharpe(book_cmp, w)}


def month_key(d: date) -> tuple[int, int]:
    return (d.year, d.month)


def monthly_paired(dates: Sequence[date], d_daily) -> tuple[list[tuple[int, int]], np.ndarray]:
    """d_m = the sum over each calendar month of w x (r_on - r_cmp) (brief F-19); months in order."""
    out: dict[tuple[int, int], float] = {}
    for d, x in zip(dates, np.asarray(d_daily, dtype=float)):
        out[month_key(d)] = out.get(month_key(d), 0.0) + float(x)
    keys = list(out)
    return keys, np.array([out[k] for k in keys], dtype=float)


# --------------------------------------------------------------------------- #
# CUSUM (L2688-2689)
# --------------------------------------------------------------------------- #
def cusum_path(z, k: float, h: float, s0: float = 0.0) -> tuple[np.ndarray, np.ndarray]:
    """One-sided CUSUM on standardised monthly differences: S_m = max(0, S_{m-1} - z_m - k); alarm when S_m >= h,
    after which S resets to 0. Works on a 1-D series or a (B, n) matrix (columns in time order)."""
    z = np.asarray(z, dtype=float)
    s = np.full(z.shape[:-1], float(s0))
    path, alarms = np.empty_like(z), np.zeros(z.shape, dtype=bool)
    for t in range(z.shape[-1]):
        s = np.maximum(0.0, s - z[..., t] - k)
        fired = s >= h
        path[..., t], alarms[..., t] = s, fired
        s = np.where(fired, 0.0, s)
    return path, alarms


def cusum_monitor(d_monthly: Sequence[float], th: "AlarmThresholds", s_prev: float = 0.0) -> tuple[float, bool]:
    """(S after the last month, alarm fired in the sequence) under the card's calibrated thresholds."""
    d = np.asarray(list(d_monthly), dtype=float)
    if d.size == 0:
        return float(s_prev), False
    z = (d - th.cusum_mu) / th.cusum_sigma
    path, alarms = cusum_path(z, th.cusum_k, th.cusum_h, s_prev)
    return float(path[-1]), bool(alarms.any())


def in_control_arl(z_design, h: float, *, k: float = CUSUM_K, B: int = CUSUM_B, seed: int = CUSUM_SEED,
                   mean_block: int = CUSUM_BLOCK, idx=None) -> float:
    """Months per alarm under a stationary bootstrap of the design monthly z (B resamples, mean block 12 months)."""
    z = np.asarray(z_design, dtype=float)
    if idx is None:
        idx = GS.block_indices(z.size, mean_block, B, seed, kind="stationary")
    _, alarms = cusum_path(z[idx], k, h)
    n_alarms = int(alarms.sum())
    return float(alarms.size) / n_alarms if n_alarms else math.inf


def calibrate_h(z_design, *, k: float = CUSUM_K, arl_min: float = ARL_MIN_MONTHS, B: int = CUSUM_B,
                seed: int = CUSUM_SEED, mean_block: int = CUSUM_BLOCK, step: float = 0.05, h_max: float = 60.0) -> float:
    """The smallest h (to `step`) whose in-control ARL is >= `arl_min` months; ARL is monotone in h (bisection).
    The naive h = 8 is never hard-coded (L2689)."""
    z = np.asarray(z_design, dtype=float)
    idx = GS.block_indices(z.size, mean_block, B, seed, kind="stationary")
    lo, hi = 0.0, step
    while in_control_arl(z, hi, k=k, idx=idx) < arl_min:
        lo, hi = hi, hi * 2.0
        if hi > h_max:
            raise CalibrationRefused(f"no CUSUM h <= {h_max} reaches an in-control ARL of {arl_min} months")
    while hi - lo > step:
        mid = (lo + hi) / 2.0
        if in_control_arl(z, mid, k=k, idx=idx) >= arl_min:
            hi = mid
        else:
            lo = mid
    return float(math.ceil(hi / step) * step)


# --------------------------------------------------------------------------- #
# Switch model (L2678; default poisson, negbin if the LR test at 5 % prefers it)
# --------------------------------------------------------------------------- #
def switch_counts(m, dates: Sequence[date], window: int = WINDOW_12M, step: int = 21) -> np.ndarray:
    """Multiplier switches per trailing 12-month window of the design path (one window every `step` sessions)."""
    mm = np.asarray(m, dtype=float)
    ok = np.isfinite(mm)
    mm = mm[ok]
    if mm.size <= window:
        return np.array([int(np.sum(np.diff(mm) != 0))])
    sw = (np.diff(mm) != 0).astype(int)
    v = sliding_window_view(sw, window - 1)[::step]
    return v.sum(axis=1)


def fit_switch_model(counts) -> tuple[str, float, dict]:
    """(model, p99, fit): Poisson unless the LR test (chi2, 1 df) at NEGBIN_LR_P prefers the negative binomial."""
    c = np.asarray(counts, dtype=float)
    lam = float(c.mean()) if c.size else 0.0
    fit = {"poisson_lambda": lam, "n_windows": int(c.size)}
    ll_p = float(stats.poisson.logpmf(c, max(lam, 1e-12)).sum())
    model, p99 = "poisson", float(stats.poisson.ppf(0.99, lam))
    if c.size >= 10 and c.var(ddof=1) > lam > 0:
        def nll(log_r):
            r = math.exp(log_r)
            return -float(stats.nbinom.logpmf(c, r, r / (r + lam)).sum())
        res = optimize.minimize_scalar(nll, bounds=(-6.0, 8.0), method="bounded")
        ll_nb = -float(res.fun)
        p_lr = float(stats.chi2.sf(2.0 * (ll_nb - ll_p), 1))
        fit.update({"negbin_r": math.exp(res.x), "lr_p": p_lr})
        if p_lr < NEGBIN_LR_P:
            r = math.exp(res.x)
            model, p99 = "negbin", float(stats.nbinom.ppf(0.99, r, r / (r + lam)))
    return model, p99, fit


# --------------------------------------------------------------------------- #
# Thresholds, triggers, budget
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class AlarmThresholds:
    cls: str
    dsr12_p2_5: float                 # design 2.5th percentile of rolling 12-month dSR (vs S / vs comparator)
    gap6m_sigma: float | None         # CARD-O: sigma of the 6-month (comparator - on) gap on book NAV
    cusum_mu: float
    cusum_sigma: float
    cusum_k: float
    cusum_h: float
    switch_model: str
    switch_p99: float
    split_per_year: float | None      # the card's equal split of D4 (None: no active card -> unallocated)
    panel_offsets: int
    panel_alarms_per_year: float
    label: str = "default"            # "default" (grid of L2692) | "judgment" (tightened to meet the split)
    tightened: tuple[str, ...] = ()
    switch_fit: dict = field(default_factory=dict)
    design_sessions: int = 0

    def as_dict(self) -> dict:
        return {k: (list(v) if isinstance(v, tuple) else v) for k, v in vars(self).items()}


@dataclass(frozen=True)
class Triggers:
    catastrophic: np.ndarray          # per window end (session index >= 251): the class condition holds
    cusum_alarms: np.ndarray          # per month: the CUSUM fired (state reset after)
    lines: dict
    months: list

    @property
    def episodes(self) -> int:
        """Alarm episodes: rising edges of the catastrophic flag plus every CUSUM alarm."""
        c = self.catastrophic.astype(int)
        rising = int(c[0]) + int(np.sum(np.diff(c) == 1)) if c.size else 0
        return rising + int(self.cusum_alarms.sum())


def trigger_lines(book_on, book_cmp, cls: str) -> dict[str, np.ndarray]:
    """The per-window statistics every trigger reads (whole-book series): CARD-P lines, plus gap6m for a CARD-O."""
    on, cm = np.asarray(book_on, dtype=float), np.asarray(book_cmp, dtype=float)
    lines = card_p_lines(on, cm)
    if cls == "CARD-O":
        lines["gap6m"] = (rolling_return(cm, WINDOW_6M) - rolling_return(on, WINDOW_6M))[WINDOW_12M - WINDOW_6M:]
    return lines


def catastrophic_flag(lines: Mapping[str, np.ndarray], th: AlarmThresholds) -> np.ndarray:
    if th.cls == "CARD-P":
        return (lines["dMDD"] <= 0.0) & (lines["dES21"] <= 0.0) & (lines["dSR12"] < th.dsr12_p2_5)
    return (lines["gap6m"] > 2.0 * (th.gap6m_sigma if th.gap6m_sigma is not None else math.inf)) | (lines["dSR12"] < th.dsr12_p2_5)


def triggers_from_lines(lines: Mapping[str, np.ndarray], months: list, d_m, th: AlarmThresholds) -> Triggers:
    _, alarms = cusum_path((np.asarray(d_m, dtype=float) - th.cusum_mu) / th.cusum_sigma, th.cusum_k, th.cusum_h)
    return Triggers(catastrophic_flag(lines, th), alarms, dict(lines), list(months))


def evaluate_triggers(book_on, book_cmp, d_daily, dates, th: AlarmThresholds) -> Triggers:
    """The calibrated statistical triggers on whole-book series (no recalibration)."""
    on = np.asarray(book_on, dtype=float)
    if on.size < WINDOW_12M:
        empty = np.zeros(0, dtype=bool)
        return Triggers(empty, empty, {}, [])
    months, d_m = monthly_paired(dates, d_daily)
    return triggers_from_lines(trigger_lines(on, book_cmp, th.cls), months, d_m, th)


def panel_offsets(T: int, shifts: int = SHIFTS, min_offset: int = MIN_OFFSET_SESSIONS) -> list[int]:
    """Brief F-18: n = 20 if T >= 20 x 252 else floor(T / 252); tau_k = round((k + 1/2) T / n), never 0 or T."""
    n = shifts if T >= shifts * min_offset else T // min_offset
    if n < 1:
        raise CalibrationRefused(f"design sample of {T} sessions is shorter than one offset of {min_offset}")
    return [int(round((k + 0.5) * T / n)) for k in range(n)]


@dataclass(frozen=True)
class ShiftedRecord:
    offset: int
    lines: dict
    months: list
    d_m: np.ndarray
    sessions: int


def placebo_panel(design: DesignSample, *, shifts: int = SHIFTS, min_offset: int = MIN_OFFSET_SESSIONS) -> list[ShiftedRecord]:
    """L2692, literal: the card's design-sample paired series `w x (r_on - r_cmp)` circularly shifted by the
    evenly spaced offsets against the whole book (`book_on_k = book_cmp + shift(d, tau_k)`), so each shifted
    record keeps the design distribution of the attribution (in control) with its timing decoupled from the
    book's path. Computed once; the thresholds are applied by `panel_rate`."""
    on, cm, d, dates = whole_book(design)
    out = []
    for tau in panel_offsets(on.size, shifts, min_offset):
        dk = np.roll(d, tau)
        months, d_m = monthly_paired(dates, dk)
        out.append(ShiftedRecord(tau, trigger_lines(cm + dk, cm, design.cls), months, d_m, int(on.size)))
    return out


@dataclass(frozen=True)
class PanelResult:
    alarms_per_year: float
    n_offsets: int
    offsets: tuple
    alarms: tuple
    record_years: float


def panel_rate(panel: Sequence[ShiftedRecord], th: AlarmThresholds) -> PanelResult:
    alarms = [triggers_from_lines(r.lines, r.months, r.d_m, th).episodes for r in panel]
    years = sum(r.sessions for r in panel) / TRADING_DAYS
    return PanelResult(sum(alarms) / years if years else math.inf, len(panel), tuple(r.offset for r in panel),
                       tuple(alarms), years)


def false_demotion_rate(design: DesignSample, th: AlarmThresholds, *, shifts: int = SHIFTS,
                        min_offset: int = MIN_OFFSET_SESSIONS, panel: Sequence[ShiftedRecord] | None = None) -> PanelResult:
    """Alarms per record-year of the calibrated triggers on the 20-shift placebo panel (seed 11 sits inside the
    CUSUM calibration; the panel itself is deterministic). Must be <= the card's split (T-DEMOTE-03)."""
    return panel_rate(placebo_panel(design, shifts=shifts, min_offset=min_offset) if panel is None else panel, th)


def calibrate_alarms(design: DesignSample, *, split: float | None, max_tightenings: int = 60,
                     shifts: int = SHIFTS) -> AlarmThresholds:
    """Thresholds on the card's full design sample, fixed at record start (L2679-2692). A card whose panel exceeds
    its split tightens h, then its quantile thresholds, until it passes (label `judgment`); a card that cannot be
    brought under its split is refused (no forward record, L2737). A FORWARD-SIM card (split None, brief F-23) is
    calibrated as if active at the full budget and never tightened."""
    on, cm, d, dates = whole_book(design)
    if on.size < 2 * WINDOW_12M:
        raise CalibrationRefused("a design sample needs at least two years of finite whole-book returns")
    lines = card_p_lines(on, cm)
    dsr_q = float(np.quantile(lines["dSR12"], 0.025))
    gap_sigma = None
    if design.cls == "CARD-O":
        gap_sigma = float(np.std(rolling_return(cm, WINDOW_6M) - rolling_return(on, WINDOW_6M), ddof=1))
    _, d_m = monthly_paired(dates, d)
    mu, sigma = float(d_m.mean()), float(d_m.std(ddof=1))
    if not sigma > 0:
        raise CalibrationRefused("monthly paired differences have no dispersion: the card never acts")
    h = calibrate_h((d_m - mu) / sigma)
    model, p99, fit = fit_switch_model(switch_counts(design.m, design.dates))
    th = AlarmThresholds(design.cls, dsr_q, gap_sigma, mu, sigma, CUSUM_K, h, model, p99, split,
                         0, math.nan, switch_fit=fit, design_sessions=int(on.size))
    target = split if split is not None else BUDGET_PER_YEAR
    panel = placebo_panel(design, shifts=shifts)
    tightened: list[str] = []
    for _ in range(max_tightenings + 1):
        res = panel_rate(panel, th)
        th = replace(th, panel_offsets=res.n_offsets, panel_alarms_per_year=res.alarms_per_year,
                     tightened=tuple(tightened), label="judgment" if tightened else "default")
        if res.alarms_per_year <= target + 1e-12 or split is None:
            return th
        if len(tightened) < 10:                                   # h first (L2691)
            th = replace(th, cusum_h=th.cusum_h + 1.0)
            tightened.append(f"cusum_h -> {th.cusum_h:.2f}")
        else:                                                    # then the quantile thresholds
            th = replace(th, dsr12_p2_5=th.dsr12_p2_5 - 0.05,
                         gap6m_sigma=None if th.gap6m_sigma is None else th.gap6m_sigma * 1.1)
            tightened.append(f"dsr12_p2_5 -> {th.dsr12_p2_5:.3f}")
    raise CalibrationRefused(f"panel rate {th.panel_alarms_per_year:.4f}/yr stays above the split {target}; "
                             "the card cannot start a forward record")


@dataclass(frozen=True)
class BudgetSplit:
    budget_per_year: float
    n_active: int
    per_card: float | None
    allocated: dict
    unallocated: float

    def as_dict(self) -> dict:
        return {"budget_per_year": self.budget_per_year, "n_active": self.n_active, "per_card": self.per_card,
                "allocated": dict(self.allocated), "unallocated": self.unallocated, "book_level_total": self.budget_per_year}


def budget_split(active_cards: Sequence[str], budget: float = BUDGET_PER_YEAR) -> BudgetSplit:
    """D4: equal split across active cards (disposition RECOMMENDATION or BUILD_AS_INSURANCE with a running
    record). Zero active cards -> nothing allocated, the whole budget reported as unallocated. The owner may only
    tighten (`value <= 0.10`)."""
    if not 0.0 < budget <= BUDGET_PER_YEAR:
        raise ValueError(f"D4 budget {budget!r} must be in (0, 0.10]: the owner may only tighten (tighten_only_le_0p10)")
    ids = list(dict.fromkeys(active_cards))
    if not ids:
        return BudgetSplit(budget, 0, None, {}, budget)
    per = budget / len(ids)
    return BudgetSplit(budget, len(ids), per, {c: per for c in ids}, 0.0)


# --------------------------------------------------------------------------- #
# The record (append-only; section 8.8 integrity rules)
# --------------------------------------------------------------------------- #
def _iso(x) -> str | None:
    if x is None:
        return None
    if isinstance(x, datetime):
        return G.iso_utc(x)
    return x.isoformat() if isinstance(x, date) else str(x)


class ForwardRecord:
    """`<path>`: one canonical-JSON row per line (binary append, fsync, raises). Rows: a `start` row, `decision`
    rows (strictly increasing session dates, live runs only), `record_reset` (new revision), `kill`, `demotion`."""

    def __init__(self, path) -> None:
        self.path = Path(path)

    def rows(self) -> list[dict]:
        if not self.path.exists():
            return []
        out = []
        for raw in self.path.read_bytes().split(b"\n"):
            if raw:
                out.append(json.loads(raw.decode("utf-8")))
        return out

    def _append(self, *rows: dict) -> None:
        """Binary append of one or more canonical-JSON lines, one flush and fsync; raises, never swallows."""
        data = b"".join(canonical_json(r).encode("utf-8") + b"\n" for r in rows)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "ab") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())

    @property
    def meta(self) -> dict | None:
        rows = self.rows()
        return rows[0] if rows and rows[0]["kind"] == "start" else None

    def decisions(self) -> list[dict]:
        return [r for r in self.rows() if r["kind"] == "decision"]

    def last_session(self) -> date | None:
        dec = self.decisions()
        return date.fromisoformat(dec[-1]["session_date"]) if dec else None

    def start(self, card_id: str, *, first_registered_utc: datetime, decision_utc: datetime, session_date: date,
              thresholds: AlarmThresholds, split: float | None, revision: int, run_mode: str = "live",
              market: str | None = None, family: str | None = None) -> dict:
        """The first row: at the first live decision after the header commit (8.8 (a)); never a replay or backtest."""
        if self.rows():
            raise RecordRefused(f"{self.path.name}: already started; a record is never restarted or backfilled")
        if run_mode != "live":
            raise RecordRefused(f"run_mode {run_mode!r}: a forward record starts only from the live workflow")
        if decision_utc < first_registered_utc:
            raise RecordRefused("a record never starts before the header commit (no backfill)")
        row = {"kind": "start", "card_id": card_id, "market": market, "family": family, "revision": int(revision),
               "first_registered_utc": _iso(first_registered_utc), "start_utc": _iso(decision_utc),
               "start_session": _iso(session_date), "split_per_year": split, "thresholds": thresholds.as_dict(),
               "honesty_line": HONESTY_LINE, "design_sample_m_bar": None}
        self._append(row)
        return row

    def decision_row(self, *, session_date: date, decision_utc: datetime, w_card: float, r_on: float | None,
                     r_cmp: float | None, r_rest: float | None, m: float | None, run_mode: str = "live",
                     late: bool = False, missed: bool = False, fail_closed: bool = False, halted: bool = False,
                     disarmed: bool = False, lag_audit_violation: bool = False, provisional_or_stale: bool = False,
                     extras: Mapping | None = None, last: date | None = None, meta: Mapping | None = None) -> dict:
        """Validate one decision against the integrity rules without writing it (`last` / `meta` let `extend`
        validate a batch in order). Refused: a record not started, a non-live run (replays are audits only), a
        session at or before the last recorded one (no backfill). A gap row (late / missed / fail_closed / HALTED /
        DISARMED or a NAV that is unavailable) is kept for the counts and excluded from both sides of every comparison."""
        meta = self.meta if meta is None else meta
        if meta is None:
            raise RecordRefused(f"{self.path.name}: not started")
        if run_mode != "live":
            raise RecordRefused(f"run_mode {run_mode!r}: replays and backtests are audits only; never appended")
        last = self.last_session() if last is None else last
        if last is not None and session_date <= last:
            raise RecordRefused(f"no backfill: {session_date} is not after the last recorded session {last}")
        if session_date < date.fromisoformat(meta["start_session"]):
            raise RecordRefused("no backfill: a session before the record start")
        flags = {"late": bool(late), "missed": bool(missed), "fail_closed": bool(fail_closed), "halted": bool(halted),
                 "disarmed": bool(disarmed)}
        nav_ok = all(x is not None and math.isfinite(float(x)) for x in (r_on, r_cmp, r_rest))
        row = {"kind": "decision", "session_date": _iso(session_date), "decision_utc": _iso(decision_utc),
               "w_card": float(w_card), "r_on": r_on, "r_cmp": r_cmp, "r_rest": r_rest, "m": m, **flags,
               "nav_available": nav_ok, "gap": any(flags.values()) or not nav_ok,
               "lag_audit_violation": bool(lag_audit_violation), "provisional_or_stale": bool(provisional_or_stale),
               "extras": dict(extras or {})}
        return row

    def append(self, **kw) -> dict:
        """One live decision, validated by `decision_row`, appended and fsynced."""
        row = self.decision_row(**kw)
        self._append(row)
        return row

    def extend(self, rows: Sequence[Mapping]) -> list[dict]:
        """Several decisions in session order under the same rules, one fsync; nothing is written when any row is
        refused (the workflow appends one row per decision; replays never reach here)."""
        meta, last, out = self.meta, self.last_session(), []
        for kw in rows:
            row = self.decision_row(**kw, last=last, meta=meta)
            last = date.fromisoformat(row["session_date"])
            out.append(row)
        if out:
            self._append(*out)
        return out

    def reset(self, *, revision: int, decision_utc: datetime, reason: str) -> dict:
        """A new card revision resets the alarm state (CUSUM, windows, counts); the age still counts from
        first_registered_utc (8.8; governance `record_reset` is appended by the caller with this row's md5)."""
        if self.meta is None:
            raise RecordRefused("not started")
        row = {"kind": "record_reset", "revision": int(revision), "utc": _iso(decision_utc), "reason": reason}
        self._append(row)
        return row

    def mark_kill(self, *, decision_utc: datetime, operator: str, books: Sequence[str]) -> dict:
        row = {"kind": "kill", "utc": _iso(decision_utc), "operator": operator, "books": list(books)}
        self._append(row)
        return row

    def mark_demotion(self, *, decision_utc: datetime, reason: str, old: str, new: str, kind: str) -> dict:
        row = {"kind": "demotion", "utc": _iso(decision_utc), "reason": reason, "old": old, "new": new, "demotion_kind": kind}
        self._append(row)
        return row

    @property
    def demoted(self) -> dict | None:
        rows = [r for r in self.rows() if r["kind"] == "demotion"]
        return rows[-1] if rows else None

    def killed(self) -> bool:
        return any(r["kind"] == "kill" for r in self.rows())

    def active_decisions(self) -> list[dict]:
        """Decision rows after the last reset (the alarm state's scope) that are not gaps."""
        rows, since = self.rows(), 0
        for i, r in enumerate(rows):
            if r["kind"] == "record_reset":
                since = i
        return [r for r in rows[since:] if r["kind"] == "decision" and not r["gap"]]


def paired_series(rows: Sequence[Mapping]) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[date]]:
    """(book_on, book_cmp, w x (r_on - r_cmp), dates) of non-gap decision rows: whole-book NAV returns."""
    rows = [r for r in rows if not r.get("gap")]
    w = np.array([r["w_card"] for r in rows], dtype=float)
    on = np.array([r["r_on"] for r in rows], dtype=float)
    cm = np.array([r["r_cmp"] for r in rows], dtype=float)
    rest = np.array([r["r_rest"] for r in rows], dtype=float)
    return w * on + (1 - w) * rest, w * cm + (1 - w) * rest, w * (on - cm), [date.fromisoformat(r["session_date"]) for r in rows]


# --------------------------------------------------------------------------- #
# Operational and integrity triggers (immediate, outside the budget)
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Alarm:
    kind: str                       # operational | catastrophic | cusum
    trigger: str                    # OPERATIONAL_TRIGGERS entry, CARD_P_TRIGGER_TEXT, "cusum"
    demotion_kind: str              # operational_or_integrity | catastrophic_or_cusum
    detail: str = ""
    value: float | None = None

    def as_dict(self) -> dict:
        return dict(vars(self))


def decision_gaps(rows: Sequence[Mapping], as_of: date, scheduled_12m: int, *, max_share: float = GAP_SHARE_MAX) -> tuple[float, bool]:
    """8.8 (b): the share of the market's scheduled decisions in the trailing 12 calendar months that were late,
    missed, failed closed, HALTED or DISARMED (one count per decision however many books it hit); strict `>`.
    The denominator is the market's scheduled count (brief F-20), the numerator the record's flagged decisions."""
    if scheduled_12m <= 0:
        raise ValueError("scheduled_12m is the market's scheduled decision count in the trailing 12 months")
    lo = date(as_of.year - 1, as_of.month, min(as_of.day, 28))
    n = sum(1 for r in rows if r.get("kind") == "decision" and lo < date.fromisoformat(r["session_date"]) <= as_of
            and any(r.get(f) for f in GAP_FLAGS))
    share = n / scheduled_12m
    return share, share > max_share + 1e-12


@dataclass(frozen=True)
class Integrity:
    """What the workflow knows that the record rows do not: rules-store edits (each `{key, revision}`; `revision`
    None = outside a card revision), the operator kill (books.Kill.integrity_trigger), lag-audit hits."""
    acting_param_edits: tuple = ()
    operator_kill: bool = False
    lag_audit_violations: int = 0
    provisional_or_stale: int = 0
    switches_12m: int | None = None
    nav_unavailable: bool = False


def operational_alarms(rows: Sequence[Mapping], integ: Integrity, *, as_of: date, scheduled_12m: int,
                       th: AlarmThresholds | None = None) -> list[Alarm]:
    dec = [r for r in rows if r.get("kind") == "decision"]
    out = []
    n_lag = integ.lag_audit_violations + sum(1 for r in dec if r.get("lag_audit_violation"))
    if n_lag:
        out.append(Alarm("operational", "lag_audit_violation", "operational_or_integrity", f"{n_lag} violation(s) in the record", n_lag))
    edits = [e for e in integ.acting_param_edits if e.get("revision") is None]
    if edits:
        out.append(Alarm("operational", "acting_param_edit_outside_revision", "operational_or_integrity",
                         "edited outside a revision: " + ", ".join(str(e.get("key")) for e in edits), len(edits)))
    n_ps = integ.provisional_or_stale + sum(1 for r in dec if r.get("provisional_or_stale"))
    if n_ps:
        out.append(Alarm("operational", "provisional_or_stale_input_reached_acting_decision", "operational_or_integrity", "", n_ps))
    if integ.operator_kill or any(r.get("kind") == "kill" for r in rows):
        out.append(Alarm("operational", "operator_kill_of_forward_books", "operational_or_integrity",
                         "the three books are killed together; the gap stays excluded"))
    share, tripped = decision_gaps(rows, as_of, scheduled_12m)
    if tripped:
        out.append(Alarm("operational", "decision_gaps_gt_10pct_rolling_12m", "operational_or_integrity",
                         f"{share:.1%} of {scheduled_12m} scheduled decisions", share))
    sw = integ.switches_12m
    if sw is None and dec:
        ms = [r["m"] for r in dec[-WINDOW_12M:] if r.get("m") is not None and not r.get("gap")]
        sw = int(np.sum(np.diff(np.asarray(ms, dtype=float)) != 0)) if len(ms) > 1 else 0
    if th is not None and sw is not None and sw > th.switch_p99:
        out.append(Alarm("operational", "switches_gt_p99_poisson_negbin", "operational_or_integrity",
                         f"{sw} switches > p99 {th.switch_p99:.1f} ({th.switch_model})", sw))
    return out


# --------------------------------------------------------------------------- #
# Monitor (statistical triggers on the record) and the card block
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class MonitorResult:
    alarms: tuple
    statistics: dict
    suspended: bool                 # whole-book NAV unavailable: statistical triggers suspended and alerted
    months: float
    switches: int | None

    @property
    def demotion(self) -> Alarm | None:
        """The alarm that demotes: operational first (immediate), then catastrophic / CUSUM."""
        for kind in ("operational", "catastrophic", "cusum"):
            for a in self.alarms:
                if a.kind == kind:
                    return a
        return None


def forward_monitor(record: ForwardRecord, th: AlarmThresholds, *, as_of: date, scheduled_12m: int,
                    integrity: Integrity = Integrity()) -> MonitorResult:
    """R-25 alarms on whole-book NAV. Operational and integrity triggers are live always; the catastrophic bound
    and the CUSUM need 12 months of non-gap decisions and an available NAV."""
    rows = record.rows()
    alarms = operational_alarms(rows, integrity, as_of=as_of, scheduled_12m=scheduled_12m, th=th)
    act = record.active_decisions()
    on, cm, d, dates = paired_series(act)
    suspended = integrity.nav_unavailable or (bool(rows) and rows[-1].get("kind") == "decision" and not rows[-1].get("nav_available", True))
    months = len({month_key(dd) for dd in dates})
    stats_: dict = {"dSR_vs_S": None, "dES21": None, "dMDD": None, "cusum_S": None, "gap6m": None, "months": months,
                    "sessions": int(on.size), "window_sessions": int(min(on.size, WINDOW_12M)),
                    "attribution_sum": float(d.sum()) if d.size else None, "threshold_2_5pct": th.dsr12_p2_5,
                    "trigger_text": CARD_P_TRIGGER_TEXT if th.cls == "CARD-P" else "; ".join(CATASTROPHIC_O)}
    switches = None
    if act:
        ms = [r["m"] for r in act[-WINDOW_12M:] if r.get("m") is not None]
        switches = int(np.sum(np.diff(np.asarray(ms, dtype=float)) != 0)) if len(ms) > 1 else 0
    if not suspended and on.size >= WINDOW_12M:
        w_on, w_cm = on[-WINDOW_12M:], cm[-WINDOW_12M:]
        dmdd = float(cardp.mdd(w_on) - cardp.mdd(w_cm))
        des = float(cardp.es(w_cm, horizon=ES_HORIZON) - cardp.es(w_on, horizon=ES_HORIZON))
        dsr = float(sharpe(w_on) - sharpe(w_cm))
        stats_.update({"dMDD": dmdd, "dES21": des, "dSR_vs_S": dsr})
        if th.cls == "CARD-P":
            fired = dmdd <= 0.0 and des <= 0.0 and dsr < th.dsr12_p2_5
            detail = f"dMDD {dmdd:+.4f} dES21 {des:+.5f} dSR12 {dsr:+.3f} < {th.dsr12_p2_5:+.3f}"
            text = CARD_P_TRIGGER_TEXT
        else:
            gap = float(np.prod(1 + cm[-WINDOW_6M:]) - np.prod(1 + on[-WINDOW_6M:]))
            stats_["gap6m"] = gap
            fired = (th.gap6m_sigma is not None and gap > 2.0 * th.gap6m_sigma) or dsr < th.dsr12_p2_5
            detail = f"gap6m {gap:+.4f} vs 2 sigma {2 * (th.gap6m_sigma or math.nan):.4f}; dSR12 {dsr:+.3f}"
            text = "CARD-O: " + " or ".join(CATASTROPHIC_O)
        if fired:
            alarms.append(Alarm("catastrophic", text, "catastrophic_or_cusum", detail, dsr))
        keys, d_m = monthly_paired(dates, d)
        complete = [i for i, k in enumerate(keys) if k < month_key(as_of)]          # the running month is excluded
        s_last, fired_c = cusum_monitor(d_m[complete], th)
        stats_["cusum_S"] = s_last
        if fired_c:
            alarms.append(Alarm("cusum", "cusum", "catastrophic_or_cusum", f"S reached h {th.cusum_h:.2f} (k {th.cusum_k})", s_last))
    return MonitorResult(tuple(alarms), stats_, suspended, months, switches)


def forward_record_block(record: ForwardRecord, th: AlarmThresholds, result: MonitorResult, *, as_of: date) -> dict:
    """`model_card.macro.forward_record` (C.6): alarms only; the age counts from first_registered_utc."""
    meta = record.meta or {}
    rows = record.rows()
    dec = [r for r in rows if r["kind"] == "decision"]
    gaps = [{"session_date": r["session_date"], "flags": [f for f in GAP_FLAGS if r.get(f)] + ([] if r.get("nav_available", True) else ["nav_unavailable"])}
            for r in dec if r.get("gap")]
    first = meta.get("first_registered_utc")
    months = 0.0
    if first:
        f = datetime.fromisoformat(first.replace("Z", "+00:00")).date()
        months = max(0.0, (as_of - f).days / 30.4375)
    dem = record.demoted
    return {"start_utc": meta.get("start_utc"), "first_registered_utc": first, "months": round(months, 3),
            "dSR_vs_S": result.statistics.get("dSR_vs_S"), "dES21": result.statistics.get("dES21"),
            "dMDD": result.statistics.get("dMDD"), "cusum_S": result.statistics.get("cusum_S"),
            "alarms": [a.as_dict() for a in result.alarms], "switches": result.switches, "switch_p99": th.switch_p99,
            "lag_audit_violations": sum(1 for r in dec if r.get("lag_audit_violation")),
            "demoted": dem is not None, "demotion_reason": dem["reason"] if dem else None,
            "honesty_line": HONESTY_LINE, "missed_decisions": sum(1 for r in dec if r.get("missed")), "gaps": gaps}


# --------------------------------------------------------------------------- #
# Demotion, lockout, the no-raise rule
# --------------------------------------------------------------------------- #
def verdict_after_forward(old: str, proposed: str) -> str:
    """A forward record moves a verdict down or leaves it: PASS -> REVISE / REJECT; any -> REJECT on a catastrophic
    or CUSUM trigger; a non-PASS card under an operational trigger keeps its verdict (REVISE would read as a raise,
    brief F-22). Upward is refused."""
    if VERDICT_RANK.get(proposed, -1) > VERDICT_RANK.get(old, -1):
        raise ForwardRecordCannotRaise(f"forward statistics cannot raise {old} to {proposed} "
                                       "(forward_record_can_raise_verdict: false; P14; section 10 item 35)")
    return proposed


def demotion_verdict(old: str, kind: str) -> str:
    new = DEMOTION_VERDICT[kind]
    if VERDICT_RANK.get(new, -1) > VERDICT_RANK.get(old, -1):
        return old                                                    # F-22: never read as a raise
    return verdict_after_forward(old, new)


def raise_verdict(card: Mapping, new: str, *, from_forward: bool = True) -> None:
    """The only entry that could move a verdict up from forward statistics: it raises, always (L2738)."""
    old = card.get("verdict", "NOT_RUN")
    if from_forward:
        raise ForwardRecordCannotRaise(f"no forward record raises a verdict ({old} -> {new}); re-gate upward only on "
                                       "new history (regate_up_only_on_new_history) as a counted revision")
    verdict_after_forward(old, new)


def lockout_until(decision_utc: datetime, months: int = LOCKOUT_MONTHS) -> datetime:
    y, m = decision_utc.year, decision_utc.month + months
    y, m = y + (m - 1) // 12, (m - 1) % 12 + 1
    return decision_utc.replace(year=y, month=m, day=min(decision_utc.day, 28))


@dataclass(frozen=True)
class Demotion:
    card_id: str
    old: str
    new: str
    kind: str
    reason: str
    lockout_until: datetime
    event_md5: str
    changed: bool


def demote(card: Mapping, record: ForwardRecord, alarm: Alarm, *, governance_log, decision_utc: datetime,
           clock: Callable[[], datetime] | None = None) -> Demotion:
    """The card's output leaves the recommended book: governance `demotion` event (old / new verdict, lockout in
    refs), the record's demotion row, a 6-month family x market lockout. A new revision with a new header is
    required to return; risk-layer invariants are untouched (never written here)."""
    old = card.get("verdict", "NOT_RUN")
    new = demotion_verdict(old, alarm.demotion_kind)
    until = lockout_until(decision_utc)
    market = card.get("market") or (record.meta or {}).get("market") or "UNKNOWN"
    family = card.get("family_id") or (record.meta or {}).get("family") or card.get("family") or "UNKNOWN"
    event = {"kind": "demotion", "book_id": f"recommended:{market}", "rule_id": card.get("rule_id"), "key": "verdict",
             "old": old, "new": new, "actor": "runtime", "utc": _iso(clock() if clock else decision_utc),
             "reason": f"{alarm.demotion_kind}: {alarm.trigger}" + (f" ({alarm.detail})" if alarm.detail else ""),
             "refs": [f"card:{card.get('card_id')}", f"family:{family}", f"market:{market}",
                      f"lockout_until:{_iso(until)}", f"record:{record.path.name}", f"trigger:{alarm.trigger}"]}
    md5 = G.append_event(Path(governance_log), event)
    record.mark_demotion(decision_utc=decision_utc, reason=alarm.trigger, old=old, new=new, kind=alarm.demotion_kind)
    return Demotion(str(card.get("card_id")), old, new, alarm.demotion_kind, alarm.trigger, until, md5, new != old)


def locked_out(governance_log, family: str, market: str, utc: datetime) -> bool:
    """family x market lockout from the governance log's demotion events (no new card, revision, instrument book or
    R-18 re-anchoring of that family in that market enters the recommended book while it runs)."""
    path = Path(governance_log)
    if not path.exists():
        return False
    for ev in G.read_events(path):
        if ev.get("kind") != "demotion":
            continue
        refs = {r.split(":", 1)[0]: r.split(":", 1)[1] for r in ev.get("refs", []) if ":" in r}
        if refs.get("family") == family and refs.get("market") == market:
            until = datetime.fromisoformat(refs["lockout_until"].replace("Z", "+00:00"))
            if utc < until:
                return True
    return False


# Wired (Sprint 6): core/skills/macro_daily.py `_forward_monitor` calls `forward_monitor(record, th, as_of=,
# scheduled_12m=<sessions in the trailing 12 months>)` on every started record under <macro_dir>/forward/ and
# `demote(card, record, result.demotion, ...)` when `result.demotion` is not None (live runs only); `default_services`
# passes `lockouts=lambda f, m, t: locked_out(<macro_dir>/governance_events.jsonl, f, m, t)` to `admissions`.
# Not wired: decision rows (`record.append`) need the card's forward on / off / S books, which exist only after a
# header commit (none possible before the freeze); `Integrity.acting_param_edits` needs a rules-store edit history.
