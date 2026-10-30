"""The odds report (spec 7.5; odds plan contract section 10). This first part holds what the path engine fills: the
outcome ladder, the cost share of the COST_DOMINATED flag and the statistics of one simulated column. simulate
imports report, never the reverse. Pure: no clock, no file, no network."""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

LADDER = (1.10, 1.25, 2.0, 10.0)                  # x W0; then the target (simulate reads report.LADDER)
COST_DOMINATED_SHARE = 0.10                       # Q43 (simulate reads report.COST_DOMINATED_SHARE)


@dataclass(frozen=True, kw_only=True)
class ColumnStats:
    """One column: a member's model under one cost scenario, n paths (contract 10.1). Counts are paths; values are
    KRW. `brackets` holds arrays, so it stays out of ==, repr and the hash."""
    key: str
    member: str
    scenario: str
    n: int
    reached: int                  # first passage: liquidation value >= T at some check (the ceiling's quantity)
    reached_outcome: int          # moonshot REACHED outcomes (<= reached: a locked exit can miss T); 0 for compounding
    ended_at_or_above: int        # terminal value >= T
    at_floor: int
    running: int
    locked_at_horizon: int
    rungs: tuple[int, ...]        # counts of terminal value >= LADDER[i] x W0, then >= T
    median: float
    p5: float
    mean: float
    mean_se: float                # std(V_term, ddof 1) / sqrt(n)
    mean_cost: float
    g_se: float                   # std(V_term + cost_term, ddof 1) / sqrt(n): the SE of the average-line statistic
    kept_lo: float | None         # min and max terminal value of AT_FLOOR paths (None without one)
    kept_hi: float | None
    x_mean: float                 # HIDDEN_EDGE sample X = G_tau - W0 (ddof 1 variance) and its range R (section
    x_var: float                  # 10.3, fixed before the run; nan when no finite range was computed, inf unbounded)
    x_range: float
    wins: int                     # take-profit fills
    losses: int                   # stop fills
    unresolved: int               # brackets closed otherwise or still open at the horizon
    brackets: tuple[np.ndarray, np.ndarray] | None = field(default=None, compare=False, repr=False)
    # (r, d) of up to BRACKET_SAMPLE brackets of chunk 0; compare two columns through dataclasses.replace(col,
    # brackets=None, x_range=0.0 if math.isnan(col.x_range) else col.x_range) (contract 10.1 as Task 9 amends it)
    band_edge_share: float
    band_edge_sessions: int       # simulated sessions that opened at a band edge
    worst_gap: float              # the largest (stop - fill) / entry of a stop fill below its stop
    trades: int                   # paths with an entry fill
