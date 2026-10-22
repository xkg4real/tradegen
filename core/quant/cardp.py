"""CARD-P gate v2 (R-21), evaluation conventions (R-22), timing-fragility gate (R-34) and the gate-acceptance test
(R-21 rule 9); M7 work package C. Spec: QUANTGEN_MACRO_INTEGRATION.md L2115-2262 (R-21), L2290-2410 (R-22),
L3395-3478 (R-34), L5116-5143 (section 8.6 shock-type table), L5187-5262 (section 8.7 verdict order).

Research arithmetic on aligned 1-D arrays of daily simple excess returns plus their session dates. It reads no
store, no clock, no network; every seed and B is an explicit parameter (reproducibility block, seed_study 11,
B 2,000); `validate.GATE` is never read. Nothing here writes a book, an artifact or a verdict file: the study
runner (TASK-M7-19) does that after the freeze, which this machine cannot execute (rulings section 1).

Verdict vocabulary: PASS | REVISE | REJECT | INSUFFICIENT_DATA; worst-of order REJECT < INSUFFICIENT_DATA <
REVISE < PASS (L2168, L5226). Reason codes (L4779): sufficiency | inconclusive | underpowered | do_no_harm |
timing_fragile | stability | claim_not_shown | estimator_calibration | <check id>.

Statistics the spec names without a formula carry a "reading:" line in their docstring (brief section F).

Integration seams (shared names, never duplicated here):
- `core.quant.costed`: `costed_path`, `same_exposure_static` (S), `max_drawdown`, `window_mask`, `calendar_years`,
  `tail_exposure_ratio`, `declustered_onsets`, `gate_boot`;
- `core.quant.gate_stats` (R-24): `block_indices`, `pw_block`, `row_sharpes`; PC-3 takes its blocks from
  `pc3_blocks` and its p-values from `lw_studentized_boot` (`p_form: lw_studentized`), the power block is checked
  by `check_power_block` and the UNDERPOWERED rule is `apply_underpowered`;
- `core.quant.gate_ledger` (R-23): `register_trial` is the `ledger_append` callback of `timing_profile` (the
  runner binds the ledger); `step3()` supplies the selection factor f that `cardp_evaluate` receives as `ledger_f`;
- `core.rules.governance.append_event` writes the `package_redesign` event; `core.quant.cards.chain_append` /
  `read_chain` hash-chain the attempts log rows (the reader `gate_package` uses).
"""
from __future__ import annotations

import contextvars
import inspect
import itertools
import json
import math
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Callable, Optional, Sequence

import numpy as np

from core.ficc.pit import MissingInput
from core.quant import costed as C
from core.quant import gate_stats as GS
from core.quant.validate import TRADING_DAYS, sharpe

ROOT = Path(__file__).resolve().parents[2]
CORE_DIR = ROOT / "core"
SANDBOX_DIRS = (ROOT / "tests", ROOT / "docs")            # timing_probe callers (L3432: tests or the R-34 sandbox)
RUNTIME_PREFIXES = ("core/engine", "core/skills", "core/ficc", "ui")
_STORE = ROOT / "data" / "macro" / "rules_v2.0.0.json"

with _STORE.open(encoding="utf-8") as _fh:
    GATE_CFG = json.load(_fh)["gate"]                     # the frozen gate.* blocks (read-only shipped store)
_P = GATE_CFG["card_p_v2"]
HORIZONS = tuple(int(h) for h in _P["pc1_prime"]["horizons_sessions"])          # (21, 126)
ES_LEVEL = float(_P["pc1_prime"]["es_level"])                                   # 0.95
P_MAX = float(_P["pc1_prime"]["p_max"])                                         # 0.10
MEAN_BLOCK = int(_P["pc1_prime"]["mean_block_sessions"])                        # 250, exactly (L2154)
PC2_RATIO_MAX = float(_P["pc2"]["ratio_max"])                                   # 0.90
PC2_Q = float(_P["pc2"]["tail_quantile"])                                       # 0.05
PC3_DELTA = float(_P["pc3"]["delta"])                                           # 0.10
PC3_BLOCK_FLOOR = int(GATE_CFG["stats"]["block"]["floor_sessions"])             # 21 (PW(psi) floor)
PC4_MIN_POSITIVE, PC4_MAX_SHARE = int(_P["pc4"]["min_positive"]), float(_P["pc4"]["max_share"])
PC5_MIN_YEARS = float(_P["pc5"]["years_positive_min"])                          # 0.60
PC6_KEEP = float(_P["pc6"]["keep_share_min"])                                   # 0.50
# ponytail: the smallest frozen grid (2, one-axis rule); a per-rule count (8 Moore) needs a header rule-type field
PC6_MIN_NEIGHBOURS = min(math.prod(len(v) for v in ax.values()) - 1 for ax in _P["pc6_axes"].values())
PC7_MIN_ONSETS = int(_P["pc7"]["discrete_min_onsets"])                          # 30
PC7_MIN_EPISODES = int(_P["pc7"]["continuous_min_objective_episodes"])          # 5
PC7_MIN_SESSIONS = int(_P["pc7"]["min_sessions"])                               # 882
UNDERPOWERED_MDE80 = float(_P["underpowered"]["applies_if_mde80_gt"])           # 0.10
THETA = GATE_CFG["evaluation"]["episode_rule"]["theta"]                         # {default 0.20, KR 0.20, US_SPX 0.15}
POST_TROUGH = int(GATE_CFG["evaluation"]["post_trough_window_sessions"])        # 63
HISTORY_START = GATE_CFG["evaluation"]["history_start"]
DATA_CUTOFF = GATE_CFG["evaluation"]["data_cutoff"]
BAND_SHAPES = GATE_CFG["evaluation"]["start_band_shapes"]
_A = GATE_CFG["acceptance_test"]
PLACEBO_PER_FAMILY, PLACEBO_FAMILY_MAX = int(_A["placebo"]["per_family"]), float(_A["placebo"]["per_family_false_pass_max"])
PLACEBO_PER_CARD, PLACEBO_CARD_MAX = int(_A["placebo"]["per_card"]), int(_A["placebo"]["per_card_passes_max"])
TAU_MIN = int(_A["placebo"]["tau_min_sessions"])                                # 252
NEGATIVE_CONTROLS = tuple(_A["negative_controls"])
CONTROL_VERDICTS = tuple(_A["controls_allowed_verdicts"])
D6_OPTIONS = ("lowest_placebo_false_pass_rule", "professors_bootstrap_one_sided_5pct",
              "executives_placebo_p10_margin", "qf_blind_margin")
CDAR_CANDIDATES = D6_OPTIONS[1:]
FR_MAX = float(GATE_CFG["timing"]["fragility_ratio_max"])                       # 0.5
LP_MIN = float(GATE_CFG["timing"]["positive_control"]["look_ahead_premium_min"])  # 0.20
LAGS = tuple(int(x) for x in GATE_CFG["timing"]["lags_sessions"])              # (-1, 0, 1, 2, 3)
HONEST_LAGS = tuple(L for L in LAGS if L >= 1)
LOOKAHEAD_LAGS = tuple(L for L in LAGS if L <= 0)
# The frozen-items table (L4803-4810): the gate.* blocks a bounded redesign may touch, nothing else.
FROZEN_ITEMS = ("card_p_v2", "acceptance_test", "evaluation", "step3", "stats", "timing", "tiers")

VERDICTS = ("PASS", "REVISE", "REJECT", "INSUFFICIENT_DATA")
ORDER = {"REJECT": 0, "INSUFFICIENT_DATA": 1, "REVISE": 2, "PASS": 3}
REASON_CODES = ("sufficiency", "inconclusive", "underpowered", "do_no_harm", "timing_fragile", "stability",
                "claim_not_shown", "estimator_calibration")
FIXES = (None, "widen_grid", "lengthen_holding", "extend_history", "repair_rerun")
KR_ETF_LISTING = date(2002, 10, 14)       # KODEX 200 listing: pre-ETF regime ends (R-20; L2346)
KR_LIMITS_30 = date(2015, 6, 15)          # +/-30% price limits (R-20)
KR_PRE_DESIGN_END = date(2015, 12, 31)    # R-06 KR's printed 2002-10 -> 2015-12 pre-design line (L2347)

# Section 8.6 shock-type table (L5116-5132): name -> (group, US window, KR window); a window is
# (start, end, include_start). Six leave-one-crisis-out groups (L5143). Printed only; never PC-4 or PC-7.
_W = lambda s, e, inc=False: (date.fromisoformat(s), date.fromisoformat(e), inc)   # noqa: E731
SHOCK_TABLE = {
    "GFC":         ("credit_recession",     _W("2008-09-01", "2009-03-09"), _W("2008-09-01", "2009-03-09")),
    "2011":        ("policy_shock",         _W("2011-07-22", "2011-10-03"), _W("2011-07-22", "2011-10-03")),
    "2015-16":     ("oil_geopolitical",     _W("2015-08-10", "2016-02-11"), _W("2015-08-10", "2016-02-11")),
    "2018Q4":      ("policy_shock",         _W("2018-09-20", "2018-12-24"), _W("2018-09-20", "2018-12-24")),
    "2020_crash":  ("pandemic",             _W("2020-02-19", "2020-03-23"), _W("2020-02-19", "2020-03-19")),
    "2022":        ("inflation_tightening", _W("2022-01-03", "2022-10-12"), _W("2022-01-03", "2022-09-30")),
    "Aug-2024":    ("leverage_unwind",      _W("2024-07-16", "2024-08-05"), _W("2024-07-31", "2024-08-09", True)),
    "Dec-2024":    ("policy_shock",         None,                            _W("2024-12-03", "2024-12-09")),
    "Apr-2025":    ("policy_shock",         _W("2025-02-19", "2025-04-08"), _W("2025-03-28", "2025-04-09", True)),
    "Mar-2026":    ("oil_geopolitical",     _W("2026-02-27", "2026-03-31"), _W("2026-02-27", "2026-03-31", True)),
    "Jul-2026":    ("leverage_unwind",      _W("2026-06-22", "2026-07-30"), _W("2026-06-22", "2026-07-30")),
    "Sep-2026":    (None,                   _W("2026-08-31", "2026-09-30"), _W("2026-08-31", "2026-09-30")),  # not an episode
}
SHOCK_GROUPS = ("credit_recession", "inflation_tightening", "policy_shock", "leverage_unwind",
                "oil_geopolitical", "pandemic")
COST_EPISODES = {
    "rebound_2009": (_W("2009-03-09", "2009-06-30"), _W("2009-03-09", "2009-06-30")),
    "rebound_2020": (_W("2020-03-23", "2020-06-08"), _W("2020-03-19", "2020-06-08")),
    "h1_2026":      (_W("2026-01-02", "2026-06-30"), _W("2026-01-02", "2026-06-30", True)),
}


class CardRefused(ValueError):
    """A card run is refused; nothing is written (L2242-2247, L2390-2394)."""


class TimingProbeForbidden(RuntimeError):
    """A look-ahead row was requested outside the timing_probe sandbox (C-4, L3432)."""


class AcceptanceRefused(RuntimeError):
    """The acceptance attempt is refused before it runs (R2-C3, L2181)."""


# --------------------------------------------------------------------------- #
# Books and statistics
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Books:
    """Aligned daily excess-return books (L2139-2143): the rule book, overlay-off, the comparator S, the earning
    multiplier path and the return dates. `on_2x` is the rule book at 2x cost; `synthetic_lookahead` marks
    probe output that no verdict path may read."""
    on: np.ndarray
    off: np.ndarray
    S: np.ndarray
    m: np.ndarray
    dates: tuple
    on_2x: Optional[np.ndarray] = None
    synthetic_lookahead: bool = False


def comparator_S(weights_earning, off_returns) -> np.ndarray:
    """S = mean(m) x overlay-off, constant, same days, uncosted (L2143): `costed.same_exposure_static`."""
    return C.same_exposure_static(weights_earning, off_returns)


def build_books(m_earning, off_excess, cost_bp_per_side: float, dates, *, stress_2x: bool = True) -> Books:
    """on = costed m x off at 1x (and 2x), S = comparator_S; m is the earning multiplier path (NaN warm-up)."""
    m = np.asarray(m_earning, dtype=float)
    off = np.asarray(off_excess, dtype=float)
    on = C.costed_path(m, off, cost_bp_per_side).net
    on2 = C.costed_path(m, off, cost_bp_per_side, 2.0).net if stress_2x else None
    return Books(on, off, comparator_S(m, off), np.where(np.isfinite(m), m, 0.0), tuple(dates), on2)


def _k_lowest(n: int, q: float) -> int:
    """reading: 'lowest 5%' = the ceil(q n) lowest values (brief F-10)."""
    return max(1, int(math.ceil(q * n)))


def horizon_returns(x, h: int) -> np.ndarray:
    """R_h(t) = prod_{j=t-h+1..t}(1 + x_j) - 1, overlapping, for a 1-D series or a (B, n) matrix (L2148)."""
    x = np.asarray(x, dtype=float)
    cs = np.cumsum(np.log1p(x), axis=-1)
    if h == 1:
        return x
    head = cs[..., h - 1:]
    tail = np.concatenate([np.zeros(cs.shape[:-1] + (1,)), cs[..., :-h]], axis=-1)
    return np.exp(head - tail) - 1.0


def es(series, q: float = ES_LEVEL, horizon: int = 1) -> float:
    """ES_q at horizon h: minus the mean of the lowest (1-q) share of overlapping h-session returns, a positive
    loss (L2149); rows of a matrix give one value each."""
    r = horizon_returns(series, horizon)
    k = _k_lowest(r.shape[-1], 1.0 - q)
    low = np.partition(r, k - 1, axis=-1)[..., :k]
    return -np.mean(low, axis=-1)


def mdd(series) -> float:
    """Maximum drawdown (negative fraction) on the simple-return NAV: `costed.max_drawdown`."""
    return C.max_drawdown(series)


def drawdown_series(x) -> np.ndarray:
    """dd_t = 1 - eq_t / max_{s<=t} eq_s on a 1-D series or on each row of a matrix."""
    eq = np.cumprod(1.0 + np.asarray(x, dtype=float), axis=-1)
    return 1.0 - eq / np.maximum.accumulate(eq, axis=-1)


def cdar(series, q: float = ES_LEVEL) -> float:
    """CDaR_q: mean of the worst (1-q) share of the drawdown series, a positive loss.
    reading: the spec names CDaR95 without a formula (L2169, L2190); brief F-6 fixes this definition."""
    dd = drawdown_series(series)
    k = _k_lowest(dd.shape[-1], 1.0 - q)
    return np.mean(-np.partition(-dd, k - 1, axis=-1)[..., :k], axis=-1)


def tail_ratio(m, x_off, q: float = PC2_Q, horizon: int = 1) -> float:
    """PC-2 tail-exposure ratio (L2157): mean(m on the worst q share of overlay-off days) / mean(m). Horizon h:
    the worst q share of overlapping h-session overlay-off windows, their days pooled (L2159)."""
    m, off = np.asarray(m, dtype=float), np.asarray(x_off, dtype=float)
    if horizon == 1:
        return C.tail_exposure_ratio(m, off, q)
    r = horizon_returns(off, horizon)
    k = _k_lowest(r.size, q)
    ends = np.argsort(r, kind="stable")[:k] + horizon - 1
    days = np.unique(np.concatenate([np.arange(e - horizon + 1, e + 1) for e in ends]))
    mean_m = float(np.mean(m))
    return float(np.mean(m[days]) / mean_m) if mean_m > 0 else float("nan")


def _p_print(count: int, B: int) -> tuple[float, str]:
    """A resample count of 0 is stored as 1/B and printed '< 1/B' (T-PZERO-01, L2154)."""
    return (1.0 / B, "< 1/B") if count == 0 else (count / B, f"{count / B:.4f}")


def _stationary(n: int, B: int, seed: int, block: int = MEAN_BLOCK) -> np.ndarray:
    return GS.block_indices(n, block, B, seed, "stationary")


def pc1_prime(x_rule, x_S, *, f: float, B: int, seed: int, horizons: Sequence[int] = HORIZONS,
              level: float = ES_LEVEL, mean_block: int = MEAN_BLOCK, idx: Optional[np.ndarray] = None) -> list[dict]:
    """PC-1' legs (L2152-2155): dES_h = ES_h(S) - ES_h(rule) (positive = protection); p_h = share of B stationary
    bootstrap resamples (Politis-Romano, mean block 250 exactly, paired daily rows, one index path; brief F-9) with
    dES*_h <= 0 (uncentred percentile); z_h = dES_h / SD*(dES*_h) printed only. A leg passes iff dES_h > 0 and
    p_h x f <= 0.10. `p_adj = min(1, p x f)` (brief F-19)."""
    a, s = np.asarray(x_rule, dtype=float), np.asarray(x_S, dtype=float)
    if a.shape != s.shape or a.ndim != 1:
        raise CardRefused("PC-1': rule and S must be aligned 1-D series")
    if idx is None:
        idx = _stationary(a.size, B, seed, mean_block)
    legs = []
    for h in horizons:
        if a.size < 2 * h:
            raise CardRefused(f"PC-1': {a.size} sessions cannot carry the {h}-session leg")
        d = float(es(s, level, h) - es(a, level, h))
        d_star = es(s[idx], level, h) - es(a[idx], level, h)
        sd = float(np.std(d_star, ddof=1))
        p, printed = _p_print(int(np.sum(d_star <= 0.0)), idx.shape[0])
        p_adj = min(1.0, p * f)
        legs.append({"h": int(h), "dES": d, "z": d / sd if sd > 0 else None, "p": p, "p_print": printed,
                     "p_adj": p_adj, "pass": bool(d > 0.0 and p_adj <= P_MAX),
                     "point_pass": bool(d > 0.0), "B": int(idx.shape[0]), "mean_block": int(mean_block)})
    return legs


def pc2(m, x_off, *, B: int, seed: int, q: float = PC2_Q, horizon_used: str = "daily", rule_horizon: int = 21,
        idx: Optional[np.ndarray] = None) -> dict:
    """PC-2 (L2157-2159): daily ratio always printed; the horizon-matched ratio replaces it for every card only
    if the acceptance test adopted it (`horizon_used = "horizon"`). 90% bootstrap CI of the used ratio printed.
    reading: the CI uses the PC-1' stationary bootstrap of paired (m, x_off) rows."""
    m, off = np.asarray(m, dtype=float), np.asarray(x_off, dtype=float)
    daily = tail_ratio(m, off, q, 1)
    horizon = tail_ratio(m, off, q, rule_horizon)
    used = horizon if horizon_used == "horizon" else daily
    if idx is None:
        idx = _stationary(m.size, B, seed)
    h_used = rule_horizon if horizon_used == "horizon" else 1
    stars = np.array([tail_ratio(m[row], off[row], q, h_used) for row in idx])   # ponytail: B python calls; fine at 2000
    lo, hi = np.nanpercentile(stars, [5, 95])
    return {"ratio_daily": daily, "ratio_horizon": horizon, "ci90": (float(lo), float(hi)), "horizon_used": horizon_used,
            "ratio_used": used, "pass": bool(used <= PC2_RATIO_MAX)}


def _boot_p(x_rule, x_S, *, block: int, B: int, seed: int, delta: float) -> dict:
    """One-sided p of {dSR* <= -delta}: R-24's studentized circular-block bootstrap (`gate_stats.lw_studentized_boot`,
    L2552); a resample count of 0 prints the store's "< 1/B" and compares as 1/B (`gate_stats.p_numeric`)."""
    try:
        out = GS.lw_studentized_boot(x_rule, x_S, block, B=B, seed=seed, null=-delta)
    except ValueError as exc:
        # reading: a zero HAC SE (the rule book is S itself) leaves the studentized statistic undefined; fail
        # closed with p = 1 (non-inferiority not shown), never a PASS from a degenerate PC-3. Any other cause
        # (a zero-variance book, a block longer than T) is labelled `degenerate` with the real message in `detail`.
        form = "degenerate_se_zero" if "HAC SE is zero" in str(exc) else "degenerate"
        return {"p": 1.0, "p_print": "1.0000 (degenerate)", "p_hac": None, "p_form": form,
                "block": int(block), "n_blocks": int(math.ceil(np.asarray(x_rule).size / block)), "detail": str(exc)}
    p = GS.p_numeric(out["p_lw"], B)
    return {"p": p, "p_print": out["p_lw"] if isinstance(out["p_lw"], str) else f"{p:.4f}", "p_hac": out.get("p_hac"),
            "p_form": "lw_studentized", "block": int(block), "n_blocks": out.get("n_blocks")}


def pc3_noninferiority(x_rule, x_S, *, f: float, B: int, seed: int, delta: float = PC3_DELTA,
                       x_rule_2x=None) -> dict:
    """PC-3 (L2160-2162): dSR = SR(on) - SR(S); p_ni = max(p_10, p_max(21, PW(psi))) x f <= 0.10 passes; a point
    dSR < -delta at 1x is REJECT, at 2x REVISE. The two block lengths are `gate_stats.pc3_blocks` (PW on the
    Ledoit-Wolf influence function, floored at 21, 250 when PW cannot be computed, L2620)."""
    a, s = np.asarray(x_rule, dtype=float), np.asarray(x_S, dtype=float)
    block_log: list = []                                     # the L2620 fallback event ("used, and logged")
    block_pw = int(GS.pc3_blocks(a, s, log=block_log)["block_pw"])
    b10 = _boot_p(a, s, block=10, B=B, seed=seed, delta=delta)
    bpw = _boot_p(a, s, block=block_pw, B=B, seed=seed, delta=delta)
    p10, ppw = max(b10["p"], 1.0 / B), max(bpw["p"], 1.0 / B)
    deciding = b10 if p10 >= ppw else bpw
    p_ni = max(p10, ppw)
    dsr = float(sharpe(a) - sharpe(s))
    dsr_2x = float(sharpe(np.asarray(x_rule_2x, dtype=float)) - sharpe(s)) if x_rule_2x is not None else dsr
    return {"dSR": dsr, "p10": p10, "pPW": ppw, "block_PW": block_pw, "p_ni": p_ni, "p_adj": min(1.0, p_ni * f),
            "point_2x": dsr_2x, "pass": bool(dsr >= -delta and p_ni * f <= P_MAX), "p_lw": deciding["p"],
            "p_hac": deciding["p_hac"], "block": deciding["block"], "n_blocks": deciding["n_blocks"],
            "p_form": deciding["p_form"], "detail": deciding.get("detail"), "block_log": block_log}


def pc5(x_on, x_S, dates) -> dict:
    """PC-5 (L2165): >= 60% of calendar years positive for the overlaid book; share of years lagging S printed."""
    on_y, s_y = C.calendar_years(x_on, dates), C.calendar_years(x_S, dates)
    years = sorted(on_y)
    if not years:
        return {"years": 0, "share_positive": 0.0, "share_lagging_S": None, "pass": False}
    pos = float(np.mean([on_y[y] > 0 for y in years]))
    lag = float(np.mean([on_y[y] < s_y.get(y, 0.0) for y in years]))
    return {"years": len(years), "share_positive": pos, "share_lagging_S": lag, "pass": bool(pos >= PC5_MIN_YEARS)}


def pc6(centre: dict, neighbours: Optional[Sequence[dict]], delta: float = PC3_DELTA) -> dict:
    """PC-6 (L2166): >= 50% of the neighbours keep >= half of the centre's dES_21 and dES_126 and a PC-3 point
    >= -delta. `neighbours` = [{dES_21, dES_126, dSR}] on the frozen pc6_axes grid; None = no grid (printed n/e,
    not a failure: the axes come from gate.card_p_v2.pc6_axes, never from the card)."""
    if not neighbours:
        return {"kept_share": None, "n": 0, "pass": None}
    keep = [n["dES_21"] >= 0.5 * centre["dES_21"] and n["dES_126"] >= 0.5 * centre["dES_126"] and n["dSR"] >= -delta
            for n in neighbours]
    share = float(np.mean(keep))
    return {"kept_share": share, "n": len(keep), "pass": bool(share >= PC6_KEEP)}


def pc7(kind: str, *, n_sessions: int, n_episodes: int, onsets: Optional[int] = None) -> dict:
    """PC-7 sufficiency (L2167): discrete >= 30 de-clustered onsets, continuous >= 5 objective (closed)
    episodes; both >= 882 sessions. Decided first."""
    if kind not in ("discrete", "continuous"):
        raise CardRefused(f"PC-7: rule kind {kind!r} must be discrete or continuous (rules-store rule-type map)")
    enough = n_sessions >= PC7_MIN_SESSIONS
    if kind == "discrete":
        if onsets is None:
            raise CardRefused("PC-7: a discrete rule needs its de-clustered onset count")
        ok = enough and onsets >= PC7_MIN_ONSETS
    else:
        ok = enough and n_episodes >= PC7_MIN_EPISODES
    return {"kind": kind, "n_sessions": int(n_sessions), "n_episodes": int(n_episodes), "onsets": onsets, "pass": bool(ok)}


def printed_lines(x_on, x_S, *, B: int, seed: int, idx: Optional[np.ndarray] = None) -> dict:
    """Printed, never gated (L2189-2195): dMDD = MDD(rule) - MDD(S) (positive = shallower), dCDaR95 = CDaR(S) -
    CDaR(rule), daily dES99 = ES99(S) - ES99(rule), each with a 90% stationary-bootstrap band; time under water
    and re-entry lag (reading: definition harness, brief F-6). Only dMDD and dCDaR95 can change a verdict, through
    the do-no-harm cap."""
    a, s = np.asarray(x_on, dtype=float), np.asarray(x_S, dtype=float)
    if idx is None:
        idx = _stationary(a.size, B, seed)
    out = {"mdd": float(mdd(a)), "mdd_S": float(mdd(s)), "cdar95": float(cdar(a)), "cdar95_S": float(cdar(s)),
           "es99": float(es(a, 0.99)), "es99_S": float(es(s, 0.99))}
    out["dMDD"] = out["mdd"] - out["mdd_S"]
    out["dCDaR95"] = out["cdar95_S"] - out["cdar95"]
    out["dES99"] = out["es99_S"] - out["es99"]
    ra, rs = a[idx], s[idx]
    eq_a, eq_s = np.cumprod(1 + ra, axis=1), np.cumprod(1 + rs, axis=1)
    dmdd = np.min(eq_a / np.maximum.accumulate(eq_a, axis=1) - 1, axis=1) - np.min(eq_s / np.maximum.accumulate(eq_s, axis=1) - 1, axis=1)
    dcdar = cdar(rs) - cdar(ra)
    des99 = es(rs, 0.99) - es(ra, 0.99)
    out["bands"] = {k: tuple(float(v) for v in np.percentile(x, [5, 95])) for k, x in
                    (("dMDD", dmdd), ("dCDaR95", dcdar), ("dES99", des99))}
    dd = drawdown_series(a)
    under = dd > 0
    out["tuw"] = {"share_sessions_under_water": float(np.mean(under)),
                  "longest_sessions": int(max((len(list(g)) for k, g in itertools.groupby(under) if k), default=0))}
    out["reentry_lag"] = None                     # reading: sessions from a trough to the rule's return above S; printed when a book path carries it
    out["do_no_harm"] = bool(out["dMDD"] < 0 and out["dCDaR95"] < 0)
    return out


# --------------------------------------------------------------------------- #
# R-22: episodes, cash leg, bands, regime lines
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Episode:
    start: date                     # peak close date
    trough: date
    end: Optional[date]             # confirmation close (trough x (1 + theta)); None while open
    depth: float                    # trough / peak - 1 (negative)
    shock_type: str                 # section 8.6 name overlapping the window, else "unnamed"
    open: bool
    regime_tags: dict = field(default_factory=dict)

    @property
    def window(self) -> tuple[date, date]:
        """Return dates after the peak close through the trough (L2316)."""
        return (self.start, self.trough)


def _named_window(peak: date, trough: date, market: str) -> str:
    col = 2 if market == "KR" else 1
    best, best_days = "unnamed", 0
    for name, row in SHOCK_TABLE.items():
        w = row[col]
        if w is None or row[0] is None:
            continue
        lo, hi = max(peak, w[0]), min(trough, w[1])
        days = (hi - lo).days
        if days > best_days:
            best, best_days = name, days
    return best


def episodes(closes, dates=None, rule: str = "bear_bull_own_closes", threshold: float = THETA["default"], *,
             market: str = "KR", value_status: str = "official_close", regime_tags_fn: Optional[Callable] = None
             ) -> list[Episode]:
    """Objective market-own episodes: the alternating bear/bull builder on the market's own official closes,
    verbatim L2299-2316. `closes` is a sequence of (date, close) pairs or an array with `dates`. Dating starts at
    the first close given (L2318; the caller passes the declared history from its first close). Onsets are
    de-clustered by construction: a bear ends only on a theta rally, so no second onset can fall inside it.
    Each episode carries its peak date's R-20 regime tags (`regime_tags_fn(date) -> dict`, L2322) and the
    section 8.6 shock type of the named window it overlaps most (printed; brief). An open bear is emitted with
    open=True (L2323). Closes that are not official are refused (L2394). No override of any date exists:
    Sep-2026 is an assertion on this output (L2324)."""
    if rule != "bear_bull_own_closes":
        raise CardRefused(f"episode rule {rule!r} is not the frozen alternating_bear_bull rule")
    if value_status != "official_close":
        raise CardRefused(f"episodes built from {value_status!r} closes are refused (R-01, L2394)")
    if dates is None:
        pairs = list(closes)
        dates, values = [d for d, _ in pairs], np.array([float(v) for _, v in pairs])
    else:
        dates, values = list(dates), np.asarray(closes, dtype=float)
    if values.size == 0 or not np.all(np.isfinite(values)) or np.any(values <= 0):
        raise CardRefused("episodes: closes must be finite and positive")
    theta = float(threshold)
    tags = regime_tags_fn or (lambda d: {})
    out: list[Episode] = []
    state, peak, peak_d = "bull", values[0], dates[0]
    trough, trough_d = peak, peak_d
    for d, v in zip(dates, values):
        if state == "bull":
            if v > peak:
                peak, peak_d = v, d
            elif v <= peak * (1 - theta):
                state, trough, trough_d = "bear", v, d
        else:
            if v < trough:
                trough, trough_d = v, d
            elif v >= trough * (1 + theta):
                out.append(Episode(peak_d, trough_d, d, float(trough / peak - 1), _named_window(peak_d, trough_d, market),
                                   False, tags(peak_d)))
                state, peak, peak_d = "bull", v, d
    if state == "bear":
        out.append(Episode(peak_d, trough_d, None, float(trough / peak - 1), _named_window(peak_d, trough_d, market),
                           True, tags(peak_d)))
    return out


def theta_for(market: str, median_sma20_vol: Optional[float] = None) -> float:
    """theta per market: KR 0.20, US_SPX 0.15; any other market by the frozen rule written before its first run:
    0.15 if its long-run median SMA20 vol < 0.18 else 0.20 (L2319)."""
    if market in THETA:
        return float(THETA[market])
    if median_sma20_vol is None:
        raise CardRefused(f"theta for {market!r} is not in the registry; write it by the frozen rule before the first run")
    return 0.15 if median_sma20_vol < 0.18 else 0.20


def closed_in_span(eps: Sequence[Episode], start: Optional[date] = None, end: Optional[date] = None) -> list[Episode]:
    """Closed episodes whose whole window lies inside [start, end] (brief F-12); open ones never count."""
    return [e for e in eps if not e.open and (start is None or e.start >= start) and (end is None or e.trough <= end)]


def episode_benefits(x_rule, x_S, dates, eps: Sequence[Episode]) -> list[float]:
    """B_e = prod_{t in e}(1 + x_rule,t) - prod_{t in e}(1 + x_S,t) over the returns after the peak close through
    the trough (L2320). Open episodes are printed by the caller and get no benefit here."""
    a, s = np.asarray(x_rule, dtype=float), np.asarray(x_S, dtype=float)
    out = []
    for e in eps:
        m = C.window_mask(dates, e.start, e.trough)
        out.append(float(np.prod(1 + a[m]) - np.prod(1 + s[m])) if m.any() else 0.0)
    return out


def pc4(benefits: Sequence[float]) -> dict:
    """PC-4 (L2164, L2321): count of B_e > 0 and max B_e / sum of the positive B_e; >= 3 positive and share <= 0.5."""
    pos = [b for b in benefits if b > 0]
    share = max(pos) / sum(pos) if pos else 0.0
    return {"positive": len(pos), "n": len(benefits), "max_share": float(share),
            "pass": bool(len(pos) >= PC4_MIN_POSITIVE and share <= PC4_MAX_SHARE)}


def post_trough_window(x_rule, x_S, dates, episode: Episode, n: int = POST_TROUGH) -> Optional[float]:
    """Rule-vs-S product difference over the n sessions after the trough (L2327); printed, never gated."""
    d = C._dates(dates)
    i = int(np.searchsorted(d, np.datetime64(episode.trough, "D"), side="right"))
    if i >= d.size:
        return None
    a, s = np.asarray(x_rule, dtype=float)[i:i + n], np.asarray(x_S, dtype=float)[i:i + n]
    return float(np.prod(1 + a) - np.prod(1 + s))


def _window_diff(x_rule, x_S, dates, w) -> Optional[float]:
    m = C.window_mask(dates, w[0], w[1], w[2])
    if not m.any():
        return None
    a, s = np.asarray(x_rule, dtype=float), np.asarray(x_S, dtype=float)
    return float(np.prod(1 + a[m]) - np.prod(1 + s[m]))


def cost_episodes(x_rule, x_S, dates, market: str = "KR") -> dict:
    """The three cost episodes (L2328), rule vs S in return-fraction units; printed, never PC-4."""
    col = 1 if market == "KR" else 0
    return {k: _window_diff(x_rule, x_S, dates, v[col]) for k, v in COST_EPISODES.items()}


def shock_type_table(x_rule, x_S, dates, market: str = "KR") -> dict:
    """Section 8.6 named windows with their return-date conventions (L5116-5142), rule vs S, plus
    leave-one-crisis-out over the six shock groups (L5143): the summed window difference with that group's
    windows left out. Printed only; Sep-2026 is listed with group None."""
    col = 2 if market == "KR" else 1
    rows = {}
    for name, (group, us, kr) in SHOCK_TABLE.items():
        w = kr if col == 2 else us
        rows[name] = {"group": group, "window": None if w is None else (w[0].isoformat(), w[1].isoformat(), w[2]),
                      "rule_minus_S": None if w is None else _window_diff(x_rule, x_S, dates, w)}
    named = {k: v for k, v in rows.items() if v["group"] and v["rule_minus_S"] is not None}
    loco = {g: float(sum(v["rule_minus_S"] for k, v in named.items() if v["group"] != g)) for g in SHOCK_GROUPS}
    return {"windows": rows, "leave_one_crisis_out": loco}


@dataclass(frozen=True)
class CashLeg:
    """A cash series read from the card's frozen snapshot (role history): `unit` annual_rate (pct per year,
    act/365) or per_period (a return per observation, as published); `rates` keyed by observation date;
    `calendar` = the series' own observation calendar over the span (a listed date without a value = a missing
    cash day); `zero_investment` series get no cash term (L2334)."""
    series_id: str
    unit: str
    rates: dict
    calendar: tuple = ()
    zero_investment: bool = False
    available_at_recorded: bool = True


def cash_leg_from_registry(registry, series_id: str, rates: Optional[dict] = None, calendar=(),
                           *, unit: Optional[str] = None) -> "CashLeg | MissingInput":
    """Build the cash leg named by the card's `cash_convention.cash_series` from the registry row. BOK_CALL_RATE's
    ECOS statistic code and observation calendar are owner inputs (registry channel "OWNER input before the M7
    freeze"): until they are written the leg is a typed `MissingInput` (role history, detail "OWNER: ...") that
    the caller reports as blocked, never cash = 0 (L2333, rulings section 1)."""
    s = registry.series.get(series_id) if hasattr(registry, "series") else None
    if s is None:
        return MissingInput(series_id, "missing", "history", (), f"{series_id} is not a registry series")
    if "OWNER" in str(s.get("channel", "")) or not s.get("ecos_code", True):
        return MissingInput(series_id, "missing", "history", (),
                            f"OWNER: ECOS statistic code and observation calendar of {series_id} (registry channel)")
    u = unit or ("per_period" if s.get("source") == "French" else "annual_rate")
    if rates is None:
        return MissingInput(series_id, "missing", "history", (), f"{series_id}: no snapshot rows handed to the harness")
    return CashLeg(series_id, u, dict(rates), tuple(calendar))


def daily_cash(dates, cash: CashLeg, *, prev_session: date) -> np.ndarray:
    """c_t by the cash series' unit (L2333): annual_rate -> latest rate dated on or before the previous session
    (a closed day of the rate's own calendar carries the prior rate) x calendar days since the previous session
    / 365; per_period -> the series' own value for t as published. A day of the series' own observation calendar
    without a value, or a span the series does not cover, refuses the card; never cash = 0."""
    if cash.unit not in ("annual_rate", "per_period"):
        raise CardRefused(f"cash series {cash.series_id}: unit {cash.unit!r} must be annual_rate or per_period")
    missing = [d for d in cash.calendar if d not in cash.rates]
    if missing:
        raise CardRefused(f"cash series {cash.series_id}: missing cash day {missing[0].isoformat()} "
                          f"({len(missing)} days of its own calendar without a value); never cash = 0")
    ds = list(dates)
    out = np.empty(len(ds))
    if cash.unit == "per_period":
        for i, d in enumerate(ds):
            if d not in cash.rates:
                raise CardRefused(f"cash series {cash.series_id}: no published value for {d.isoformat()}")
            out[i] = float(cash.rates[d])
        return out
    keys = sorted(cash.rates)
    kd = np.array([np.datetime64(k, "D") for k in keys])
    prev = prev_session
    for i, d in enumerate(ds):
        j = int(np.searchsorted(kd, np.datetime64(prev, "D"), side="right")) - 1
        if j < 0:
            raise CardRefused(f"cash series {cash.series_id} does not cover {prev.isoformat()} (span start)")
        out[i] = float(cash.rates[keys[j]]) / 100.0 * (d - prev).days / 365.0
        prev = d
    return out


def excess_returns(returns, dates, weights, cash: Optional[CashLeg], *, prev_session: date, cost=None,
                   raw: bool = False) -> np.ndarray:
    """x_t = w_t (r_t - c_t) - cost_t (L2331). `cash=None` is allowed only for a zero-investment series or a
    reproduction run flagged `raw=True` (cash 0; never a card record, L2337). `weights` is the earning path."""
    r, w = np.asarray(returns, dtype=float), np.asarray(weights, dtype=float)
    if r.shape != w.shape or r.ndim != 1 or len(dates) != r.size:
        raise CardRefused("excess_returns: returns, weights and dates must align")
    if cash is None or cash.zero_investment:
        if cash is None and not raw:
            raise CardRefused("excess_returns: no cash leg; a formal card never runs on raw returns (L2337)")
        c = np.zeros(r.size)
    else:
        c = daily_cash(dates, cash, prev_session=prev_session)
    cost_arr = np.zeros(r.size) if cost is None else np.asarray(cost, dtype=float)
    return np.where(np.isfinite(w), w, 0.0) * (r - c) - cost_arr


def _first_session(sessions, y: int, m: int) -> date:
    if sessions is None:
        return date(y, m, 1)
    for d in sessions:
        if (d.year, d.month) >= (y, m):
            return d
    raise CardRefused(f"no session on or after {y}-{m:02d}")


def start_band(shape: str, *, history_start: date, span_end: date, sessions=None, declared_start: Optional[date] = None
               ) -> list[date]:
    """The frozen band shapes (L2341, gate.evaluation.start_band_shapes); a card declares neither its band nor
    its pass share. `default`: the monthly starts over the first 33 months of the span; `R-06_KR`: the 32 monthly
    starts 1997-05 .. 1999-12, asserted as a pair with history_start KR 1997-04-01; `decade_spaced` (daily spans
    >= 80 years): the declared start, then the first session of January of each decade year at least 10 years
    before the span end. reading: a monthly start is the first session of the month (brief F-13)."""
    if shape == "default":
        n = int(BAND_SHAPES["default"]["months"])
        y, m = history_start.year, history_start.month
        out = []
        for _ in range(n):
            out.append(_first_session(sessions, y, m))
            y, m = (y + 1, 1) if m == 12 else (y, m + 1)
        return out
    if shape == "R-06_KR":
        if history_start != date.fromisoformat(HISTORY_START["KR"]):
            raise CardRefused(f"R-06_KR band pairs with history_start {HISTORY_START['KR']}, not {history_start}")
        cfg = BAND_SHAPES["R-06_KR"]
        (fy, fm), (ty, tm) = (int(x) for x in cfg["from"].split("-")), (int(x) for x in cfg["to"].split("-"))
        out, y, m = [], fy, fm
        while (y, m) <= (ty, tm):
            out.append(_first_session(sessions, y, m))
            y, m = (y + 1, 1) if m == 12 else (y, m + 1)
        if len(out) != int(cfg["starts"]):
            raise CardRefused(f"R-06_KR band has {len(out)} starts, not {cfg['starts']}")
        return out
    if shape == "decade_spaced":
        start = declared_start or history_start
        if (span_end - start).days < 80 * 365.25:
            raise CardRefused("decade_spaced needs a daily span of at least 80 years")
        out = [start]
        y = (start.year // 10 + 1) * 10
        while y <= span_end.year - 10:
            out.append(_first_session(sessions, y, 1))
            y += 10
        return out
    raise CardRefused(f"unknown band shape {shape!r}")


def midpoint_halves(history_start: date, span_end: date) -> tuple[date, tuple[date, date], tuple[date, date]]:
    """Calendar midpoint of the fixed span (L2342): split = start + floor(days / 2); KR 1997-04-01..2026-10-02
    -> 2012-01-01. The split date is written in the header."""
    split = history_start + timedelta(days=(span_end - history_start).days // 2)
    return split, (history_start, split), (split, span_end)


def stability_floor(shape: str, verdicts: Sequence[str], halves: Sequence[str]) -> dict:
    """The integer floor (L2343): no REJECT at any start; 3 n_pass >= 2 n_starts (4/5 -> 5 n_pass >= 4 n_starts
    for decade_spaced); no REJECT in either midpoint half. A miss caps the card at INSUFFICIENT_DATA (`stability`)."""
    for v in list(verdicts) + list(halves):
        if v not in VERDICTS:
            raise CardRefused(f"stability floor: {v!r} is not a verdict")
    n, n_pass, n_reject = len(verdicts), sum(v == "PASS" for v in verdicts), sum(v == "REJECT" for v in verdicts)
    num, den = (4, 5) if shape == "decade_spaced" else (2, 3)
    share_ok = den * n_pass >= num * n
    halves_ok = not any(v == "REJECT" for v in halves)
    ok = n_reject == 0 and share_ok and halves_ok
    reason = None if ok else ("reject_at_start" if n_reject else "pass_count_below_floor" if not share_ok else "reject_in_half")
    return {"n_starts": n, "n_pass": n_pass, "n_reject": n_reject, "floor_pass": bool(ok), "min_pass": -(-num * n // den),
            "halves": list(halves), "reason": reason}


def regime_lines(market: str, history_start: date, span_end: date, *, primary_oos_line: str,
                 gating_lines: Optional[dict] = None) -> list[dict]:
    """One line per R-20 regime (L2346-2347): Korea pre-ETF (history start -> 2002-10-14), the ETF era, the +/-30%
    limits from 2015-06-15; the declared primary out-of-sample line gates, the pre-design 2002-10 -> 2015-12 line
    is printed. Other markets: a single full-span line until their tag file names regimes. When the header's
    `gating_lines` declares {from, to} for the gated line, that span gates (Resolution 1 (ii), L1574) and the
    regime line to the present is printed as `<line>_to_present`; an undeclared `from` / `to` is refused."""
    if market != "KR":
        lines = [{"line": "full_span", "span": (history_start, span_end)}]
    else:
        lines = [{"line": "pre_etf", "span": (history_start, min(KR_ETF_LISTING, span_end))},
                 {"line": "etf_era", "span": (KR_ETF_LISTING, span_end)},
                 {"line": "limits_30pct", "span": (KR_LIMITS_30, span_end)},
                 {"line": "pre_design", "span": (KR_ETF_LISTING, KR_PRE_DESIGN_END)}]
    names = {x["line"] for x in lines} | {"full_span"}
    if primary_oos_line not in names:
        raise CardRefused(f"primary_oos_line {primary_oos_line!r} is not a regime line of {market}")
    for x in lines:
        x["gated"] = x["line"] == primary_oos_line
    declared = (gating_lines or {}).get(primary_oos_line)
    gated = next((x for x in lines if x["gated"]), None)
    if isinstance(declared, dict) and gated is not None:
        if not (declared.get("from") and declared.get("to")):
            raise CardRefused(f"gating_lines.{primary_oos_line}: from / to not declared (OWNER): the gated line has no span")
        lines.append({"line": f"{primary_oos_line}_to_present", "span": gated["span"], "gated": False})
        gated["span"] = (date.fromisoformat(str(declared["from"])[:10]), date.fromisoformat(str(declared["to"])[:10]))
    return lines


def check_card_book_convention(header: dict) -> None:
    """R-22 rule 6 (L2348): card books exclude the R-07 hard stop and caps unless the card's claim concerns them;
    a run with the convention flipped is refused (T-RLAYER-01). Header keys: `card_books: {hard_stop, caps}`,
    `claim_concerns: [...]`."""
    books = header.get("card_books") or {"hard_stop": False, "caps": False}
    concerns = set(header.get("claim_concerns") or ())
    for k in ("hard_stop", "caps"):
        if books.get(k, False) and k not in concerns:
            raise CardRefused(f"card books include the {k} but the claim does not concern it (R-22 rule 6)")


# --------------------------------------------------------------------------- #
# R-21: verdict order, caps, cardp_evaluate
# --------------------------------------------------------------------------- #
def _worse(a: str, b: str) -> str:
    return a if ORDER[a] <= ORDER[b] else b


def line_verdict(c: dict, f: float) -> dict:
    """The verdict order, coded once (L2173, L5228-5250), for ONE gating line's checks at 1x and 2x:
    1 INSUFFICIENT_DATA (sufficiency) -> 2 REJECT at 1x -> 3 INSUFFICIENT_DATA (inconclusive | underpowered) ->
    4 REVISE (2x legs: lengthen_holding; PC-6: widen_grid; PC-5: extend_history) -> 5 caps, lowering only
    (do_no_harm, timing_fragile, claim_not_shown, stability, estimator_calibration -> REVISE) -> 6 PASS.
    `c` keys: pc7{pass}, pc1p{legs[], two_x[]}, pc2{ratio_used}, pc3{dSR, p_ni, point_2x}, pc4{positive, max_share},
    step4{ran, pbo, winner_loses} (optional), power{mde80}, pc6{pass|None}, pc5{pass}, caps{do_no_harm,
    timing_fragile, claim_not_shown, stability, estimator_calibration} (bools)."""
    if f < 1.0:
        raise CardRefused("selection factor f is at least 1")
    caps_applied: list[str] = []
    if not c["pc7"]["pass"]:
        return {"verdict": "INSUFFICIENT_DATA", "reason": "sufficiency", "permitted_fix": None, "caps_applied": caps_applied,
                "first_failed_check": "PC7"}
    legs = c["pc1p"]["legs"]
    # written as not (x passes) so a NaN statistic fails closed instead of skipping the check
    if any(not leg["dES"] > 0.0 for leg in legs):
        return _v("REJECT", "PC1p", caps_applied)
    if not c["pc2"]["ratio_used"] <= PC2_RATIO_MAX:
        return _v("REJECT", "PC2", caps_applied)
    if not c["pc3"]["dSR"] >= -PC3_DELTA:
        return _v("REJECT", "PC3", caps_applied)
    if c["pc4"]["positive"] < PC4_MIN_POSITIVE:
        return _v("REJECT", "PC4", caps_applied)
    s4 = c.get("step4") or {}
    if s4.get("ran") and s4.get("pbo", 0.0) > 0.2 and s4.get("winner_loses"):
        return _v("REJECT", "step4", caps_applied)
    if any(min(1.0, leg["p"] * f) > P_MAX for leg in legs):
        return _v("INSUFFICIENT_DATA", "inconclusive", caps_applied, "PC1p")
    if not c["pc4"]["max_share"] <= PC4_MAX_SHARE:
        return _v("INSUFFICIENT_DATA", "inconclusive", caps_applied, "PC4")
    if min(1.0, c["pc3"]["p_ni"] * f) > P_MAX:
        verdict, reason = GS.apply_underpowered("pc3_p_value", True, c.get("power") or {"mde80": 0.0})   # rule 4, one home
        return _v(verdict, reason, caps_applied, "PC3")
    two_x = c["pc1p"].get("two_x") or []
    if any(not (leg["dES"] > 0.0 and min(1.0, leg["p"] * f) <= P_MAX) for leg in two_x) or not c["pc3"]["point_2x"] >= -PC3_DELTA:
        first = "PC1p_2x" if any(not (leg["dES"] > 0.0 and min(1.0, leg["p"] * f) <= P_MAX) for leg in two_x) else "PC3_2x"
        v = {"verdict": "REVISE", "reason": first, "permitted_fix": "lengthen_holding", "first_failed_check": first}
    elif c["pc6"].get("pass") is False:
        v = {"verdict": "REVISE", "reason": "PC6", "permitted_fix": "widen_grid", "first_failed_check": "PC6"}
    elif not c["pc5"]["pass"]:
        v = {"verdict": "REVISE", "reason": "PC5", "permitted_fix": "extend_history", "first_failed_check": "PC5"}
    else:
        v = {"verdict": "PASS", "reason": None, "permitted_fix": None, "first_failed_check": None}
    caps = c.get("caps") or {}
    for name, level in (("do_no_harm", "INSUFFICIENT_DATA"), ("timing_fragile", "INSUFFICIENT_DATA"),
                        ("claim_not_shown", "INSUFFICIENT_DATA"), ("stability", "INSUFFICIENT_DATA"),
                        ("estimator_calibration", "REVISE")):
        if caps.get(name) and ORDER[level] < ORDER[v["verdict"]]:
            v["verdict"], v["reason"] = level, name
            caps_applied.append(name)
    v["caps_applied"] = caps_applied
    return v


def _v(verdict, reason, caps, first=None):
    return {"verdict": verdict, "reason": reason, "permitted_fix": None, "caps_applied": caps,
            "first_failed_check": first or reason}


def combine_card_verdict(parts) -> tuple[str, Optional[str]]:
    """Pure: the card verdict is the worst of its gating lines (L5226); PASS iff every part is PASS. I-16's
    reading for R-06 KR: PASS iff (i) full-span PASS, (ii) ETF-era PASS, (iii) the band floor holds and (iv) no
    REJECT in either midpoint half; a False part (a failed floor or half) counts as INSUFFICIENT_DATA
    (`stability`). `parts` = {name: verdict | bool}. Returns (verdict, reason)."""
    if not parts:
        raise CardRefused("combine_card_verdict: no gating line")
    worst, reason = "PASS", None
    for name, v in dict(parts).items():
        if isinstance(v, bool):
            v, why = ("PASS", None) if v else ("INSUFFICIENT_DATA", "stability")
        else:
            if v not in VERDICTS:
                raise CardRefused(f"{name}: {v!r} is not a verdict")
            why = name
        if ORDER[v] < ORDER[worst]:
            worst, reason = v, why
    return worst, reason


@dataclass(frozen=True)
class CardResult:
    verdict: str
    reason_code: Optional[str]
    verdict_at_f1: str
    verdict_at_f_neff: str
    f: float
    pc1_prime: dict
    pc2: dict
    pc3: dict
    pc4: dict
    pc5: dict
    pc6: dict
    pc7: dict
    do_no_harm: bool
    printed: dict
    caps_applied: tuple
    permitted_fix: Optional[str]
    first_failed_check: Optional[str]
    episodes: tuple
    lines: dict
    timing: dict
    power: dict


def _check_header(header: dict) -> None:
    for k in ("episode_rule_version", "cash_convention", "history_first_close"):
        if k not in header:
            raise CardRefused(f"header lacks {k} (R-22 fail-closed, L2391)")
    if "selection_factor" in header:
        raise CardRefused("a header declaring selection_factor is refused; f is computed by step3 (C-2)")
    if (header["cash_convention"] or {}).get("returns") != "excess":
        raise CardRefused("cash_convention.returns must be excess (L2337)")
    check_card_book_convention(header)


def cardp_evaluate(on, off, S, header: dict, ledger_f, seed: int, B: int, *, m=None, dates=None, on_2x=None,
                   eps: Optional[Sequence[Episode]] = None, timing: Optional[dict] = None, control: Optional[dict] = None,
                   power: Optional[dict] = None, kind: str = "continuous", onsets: Optional[int] = None,
                   neighbours: Optional[Sequence[dict]] = None, estimator_ok: bool = True, claim_lines_ok: bool = True,
                   band: Optional[dict] = None, step4: Optional[dict] = None, f_neff: Optional[float] = None,
                   horizon_used: str = "daily", market: str = "KR", books: Optional[Books] = None) -> CardResult:
    """PC-1' .. PC-7, the caps and the verdict order on one gating line (section 8.7). `ledger_f` is step3's
    binding selection factor (float, >= 1) and `f_neff` its N_eff alternative (both verdicts printed, L4091).
    `timing` is a `timing_profile` result and `control` a `lookahead_positive_control` result: a card without a
    timing profile, or without a tripped positive control, is refused (L3453-3454); `power` is R-24's power line
    (`gate_stats.power_line` or its `as_dict()`; `gate_stats.check_power_block` refuses a card without every L2612
    field, T-POWER-02). `band` = {shape, verdicts, halves} feeds the stability cap.
    Refused: probe books (`synthetic_lookahead`), a header declaring f, a flipped card-book convention."""
    _check_header(header)
    if books is not None and books.synthetic_lookahead:
        raise CardRefused("a card whose statistics read a synthetic_lookahead row is refused (C-4)")
    if timing is None:
        raise CardRefused("a card without a timing profile is refused (R-34)")
    if control is None or not control.get("tripped"):
        raise CardRefused("the look-ahead positive control is missing or did not trip: every card run is blocked (L3454)")
    try:
        GS.check_power_block(power)
    except GS.PowerBlockMissing as exc:
        raise CardRefused(f"a card without its power block is refused (R-24 power_line, L2619): {exc}") from exc
    power = power.as_dict() if isinstance(power, GS.PowerLine) else {k: v for k, v in power.items()}
    if ledger_f is None or float(ledger_f) < 1.0:
        raise CardRefused("ledger_f: the selection factor comes from step3 and is >= 1 (P13)")
    f = float(ledger_f)
    fn = float(f_neff) if f_neff is not None else f
    on, off, S = (np.asarray(x, dtype=float) for x in (on, off, S))
    if not (on.shape == off.shape == S.shape) or on.ndim != 1:
        raise CardRefused("on, off and S must be aligned 1-D series")
    if m is None or dates is None:
        raise CardRefused("the multiplier path and the return dates are required")
    m = np.asarray(m, dtype=float)
    if eps is None:
        raise CardRefused("the episode list failed or was not built: no card is written (L2245)")
    span = C._dates(dates)
    closed = closed_in_span(eps, span[0].astype(date), span[-1].astype(date))      # this line's own episodes (F-12)
    idx = _stationary(on.size, B, seed)
    legs = pc1_prime(on, S, f=f, B=B, seed=seed, idx=idx)
    two_x = pc1_prime(on_2x, S, f=f, B=B, seed=seed, idx=idx) if on_2x is not None else []
    r2 = pc2(m, off, B=B, seed=seed, horizon_used=horizon_used, idx=idx)
    r3 = pc3_noninferiority(on, S, f=f, B=B, seed=seed, x_rule_2x=on_2x)
    benefits = episode_benefits(on, S, dates, closed)
    r4 = pc4(benefits)
    r5 = pc5(on, S, dates)
    centre = {"dES_21": legs[0]["dES"], "dES_126": legs[1]["dES"] if len(legs) > 1 else legs[0]["dES"], "dSR": r3["dSR"]}
    r6 = pc6(centre, neighbours)
    r7 = pc7(kind, n_sessions=on.size, n_episodes=len(closed), onsets=onsets)
    lines = printed_lines(on, S, B=B, seed=seed, idx=idx)
    lines["post_trough"] = [post_trough_window(on, S, dates, e) for e in eps]
    lines["cost_episodes"] = cost_episodes(on, S, dates, market)
    lines["shock_type_table"] = shock_type_table(on, S, dates, market)
    lines["open_episodes"] = [e for e in eps if e.open]
    lines["gjr_null_pct"] = None     # not built: the TASK-M7-11 printed line (core.quant.gjr fit + 1,000 paths); never gated
    stability_ok = True
    if band is not None:
        stability_ok = stability_floor(band["shape"], band["verdicts"], band.get("halves", ()))["floor_pass"]
    caps = {"do_no_harm": lines["do_no_harm"], "timing_fragile": bool(timing.get("fragile")),
            "claim_not_shown": not claim_lines_ok, "stability": not stability_ok, "estimator_calibration": not estimator_ok}
    checks = {"pc7": r7, "pc1p": {"legs": legs, "two_x": two_x}, "pc2": r2, "pc3": r3, "pc4": r4, "pc5": r5, "pc6": r6,
              "power": power, "caps": caps, "step4": step4}
    v = line_verdict(checks, f)
    v1, vn = line_verdict(checks, 1.0), line_verdict(checks, fn)
    return CardResult(v["verdict"], v["reason"], v1["verdict"], vn["verdict"], f, {"legs": legs, "two_x": two_x}, r2, r3,
                      r4, r5, r6, r7, lines["do_no_harm"], lines, tuple(v["caps_applied"]), v["permitted_fix"],
                      v["first_failed_check"], tuple(eps), {"line": header.get("line", "full_span"), **v},
                      dict(timing), dict(power))


# --------------------------------------------------------------------------- #
# R-34: timing profile, probe sandbox, positive control
# --------------------------------------------------------------------------- #
_PROBE = contextvars.ContextVar("quantgen_timing_probe", default=False)


def _under(path: Path, base: Path) -> bool:
    try:
        path.relative_to(base)
        return True
    except ValueError:
        return False


def _caller_file(depth: int = 2) -> Optional[Path]:
    frame = inspect.currentframe()
    for _ in range(depth):
        frame = frame.f_back if frame is not None else None
    if frame is None:
        return None
    p = Path(frame.f_code.co_filename)
    return p.resolve() if p.is_absolute() else None


def _stack_touches_runtime() -> Optional[str]:
    frame = inspect.currentframe()
    while frame is not None:
        p = Path(frame.f_code.co_filename)
        rel = p.as_posix()
        for pre in RUNTIME_PREFIXES:
            if f"/{pre}/" in rel or rel.startswith(f"{pre}/"):
                return rel
        frame = frame.f_back
    return None


def _run_lagged(data_fn: Callable[[int], Books], L) -> Books:
    """The only producer of lagged books. L <= 0 (look-ahead) is served only while `timing_probe` holds the
    context flag; anywhere else it raises `TimingProbeForbidden` (C-4). Probe books are tagged."""
    if isinstance(L, int) and L <= 0:
        if not _PROBE.get():
            raise TimingProbeForbidden(f"lag {L} is a look-ahead row: only timing_probe(sandbox=True) from tests/ may run it")
        b = data_fn(L)
        return Books(b.on, b.off, b.S, b.m, b.dates, b.on_2x, True)
    return data_fn(L)


def _row(L, b: Books, *, B: int, seed: int) -> dict:
    dsr = float(sharpe(b.on) - sharpe(b.S))
    look = isinstance(L, int) and L <= 0
    # L <= 0 re-times the acting inputs outside pit_value: the lag audit records that as a violation instead of
    # raising (L3432, T-LAG-01/02 probe clauses); honest and strict rows carry zero violations.
    audit = {"violations": 1 if look else 0, "recorded_not_raised": look, "check": "synthetic_lookahead" if look else None}
    return {"L": L, "dSR": dsr, "dMDD": float(mdd(b.on) - mdd(b.S)), "dES21": float(es(b.S, ES_LEVEL, 21) - es(b.on, ES_LEVEL, 21)),
            "lag_audit": audit, "timing_class": "NON-COMPLIANT" if look else "COMPLIANT", "synthetic_lookahead": look}


def fragility(dsr_1: float, dsr_2: float, *, fr_max: float = FR_MAX) -> tuple[float, Optional[float], bool]:
    """(LF, FR, fragile) from the L = 1 and L = 2 rows (L3424-3427): LF = dSR[1] - dSR[2]; FR = LF / dSR[1] when
    dSR[1] > 0 else None (printed "n/m"); fragile = FR > 0.5 or a sign flip by lag 2."""
    lf = dsr_1 - dsr_2
    fr = lf / dsr_1 if dsr_1 > 0 else None
    flip = dsr_1 != 0 and dsr_2 != 0 and np.sign(dsr_2) == -np.sign(dsr_1)
    return lf, fr, bool((fr is not None and fr > fr_max) or flip)


def timing_profile(card: dict, data_fn: Callable[[int], Books], *, B: int, seed: int, ledger_append: Optional[Callable] = None,
                   strict_fn: Optional[Callable[[], Books]] = None, reported_dsr: Optional[float] = None) -> dict:
    """R-34 (L3416-3432): rows L = 1, 2, 3 and publication-strict; LF = dSR[1] - dSR[2]; FR = LF / dSR[1] ("n/m"
    when dSR[1] <= 0); fragile = FR > 0.5 or a sign flip by lag 2. The L = 1 row must equal the card's reported
    dSR (harness integrity). Every lag is a family-ledger row through `ledger_append(family_id, row)` (package A's
    `gate_ledger.append`); rows are also returned in `ledger_rows`. L <= 0 rows join only when `timing_probe`
    holds the sandbox flag (then LP = dSR[0] - dSR[1]). FR's paired-bootstrap 90% interval is printed (L5457)."""
    lags = list(HONEST_LAGS) + (list(LOOKAHEAD_LAGS) if _PROBE.get() else [])
    books = {L: _run_lagged(data_fn, L) for L in lags}
    rows = {L: _row(L, b, B=B, seed=seed) for L, b in books.items()}
    if strict_fn is not None:
        rows["strict"] = _row("strict", strict_fn(), B=B, seed=seed)
    if reported_dsr is not None and abs(rows[1]["dSR"] - reported_dsr) >= 1e-9:
        raise CardRefused(f"timing profile: the L = 1 row {rows[1]['dSR']:.6f} is not the card's reported dSR {reported_dsr:.6f}")
    d1, d2 = rows[1]["dSR"], rows[2]["dSR"]
    lf, fr, fragile = fragility(d1, d2)
    idx = _stationary(books[1].on.size, B, seed)
    s1 = GS.row_sharpes(books[1].on[idx]) - GS.row_sharpes(books[1].S[idx])
    s2 = GS.row_sharpes(books[2].on[idx]) - GS.row_sharpes(books[2].S[idx])
    with np.errstate(divide="ignore", invalid="ignore"):
        fr_star = np.where(s1 > 0, (s1 - s2) / s1, np.nan)
    fr_ci = tuple(float(x) for x in np.nanpercentile(fr_star, [5, 95])) if np.isfinite(fr_star).any() else None
    ledger_rows = []
    for L, r in rows.items():
        row = {**(card.get("config") or {}), "lag": L, "timing_class": r["timing_class"]}
        ledger_rows.append(row)
        if ledger_append is not None:
            ledger_append(card.get("family_id"), row)
    lp = rows[0]["dSR"] - d1 if 0 in rows else None
    return {"lags": [rows[L] for L in lags], "strict": rows.get("strict"), "LP": lp, "LF": lf,
            "FR": fr if fr is not None else "n/m", "FR_ci90": fr_ci, "fragile": fragile,
            "label": "timing_fragile" if fragile else "robust", "live_feeds": list(card.get("live_feeds") or ()),
            "lag_audit_violations": sum(r["lag_audit"]["violations"] for L, r in rows.items() if not (isinstance(L, int) and L <= 0)),
            "ledger_rows": ledger_rows, "probe": _PROBE.get()}


def timing_probe(card: dict, data_fn: Callable[[int], Books], *, sandbox: bool, B: int, seed: int, out_dir: Optional[Path] = None,
                 ledger_append: Optional[Callable] = None, strict_fn=None, reported_dsr=None) -> dict:
    """The hermetic look-ahead sandbox (C-4, L3432): runs `timing_profile` with the L <= 0 rows. Callable only with
    `sandbox=True`, directly from a module under tests/ or docs/ (the R-34 sandbox), never with a runtime, book
    builder or verdict module on the stack; its output is tagged `synthetic_lookahead` and, when `out_dir` is
    given, written there (refused under `config.macro_dir()`, the production artifact directory)."""
    if not sandbox:
        raise TimingProbeForbidden("timing_probe needs sandbox=True")
    hit = _stack_touches_runtime()
    if hit:
        raise TimingProbeForbidden(f"timing_probe reached from a runtime / book-builder frame: {hit}")
    caller = _caller_file(2)
    if caller is None or not any(_under(caller, d) for d in SANDBOX_DIRS):
        raise TimingProbeForbidden(f"timing_probe may be called from tests/ or docs/ only, not {caller}")
    if out_dir is not None:
        import config
        prod = config.macro_dir().resolve()
        if _under(Path(out_dir).resolve(), prod):
            raise TimingProbeForbidden("probe output may not land in the production artifact directory")
    token = _PROBE.set(True)
    try:
        prof = timing_profile(card, data_fn, B=B, seed=seed, ledger_append=ledger_append, strict_fn=strict_fn, reported_dsr=reported_dsr)
    finally:
        _PROBE.reset(token)
    prof["synthetic_lookahead"] = True
    if out_dir is not None:
        p = Path(out_dir) / f"timing_probe_{card.get('card_id', 'card')}.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({k: v for k, v in prof.items() if k != "ledger_rows"}, default=str), encoding="utf-8")
        prof["path"] = str(p)
    return prof


def lookahead_positive_control(profile: dict, *, min_lp: float = LP_MIN) -> dict:
    """The positive control (L3430): the probe profile of the KR SOX x KRW gate fixture `KR_SOX_KRW_gate_B3`
    (REFDATA) must show LP >= 0.20. `tripped` False blocks every card run; a profile without an L = 0 row is a
    missing control."""
    lp = profile.get("LP")
    if lp is None or not profile.get("synthetic_lookahead"):
        return {"tripped": False, "LP": None, "reason": "no look-ahead row: the control was not run in the probe"}
    return {"tripped": bool(lp >= min_lp), "LP": float(lp), "min": min_lp,
            "L0": next((r["dSR"] for r in profile["lags"] if r["L"] == 0), None),
            "L1": next((r["dSR"] for r in profile["lags"] if r["L"] == 1), None)}


# --------------------------------------------------------------------------- #
# R-21 rule 9: placebos, negative controls, D6 guard, attempts log, bounded redesign
# --------------------------------------------------------------------------- #
def placebo_passes(m, x_off, cost_bp: float, tau: int, f: float, *, B: int, seed: int) -> bool:
    """One definition for both counts (L2178): the multiplier circularly shifted by tau against its returns,
    rebuilt at 1x cost; passes iff both PC-1' legs pass (points > 0 and p x f <= 0.10)."""
    m_star = np.roll(np.asarray(m, dtype=float), int(tau))
    on = C.costed_path(m_star, x_off, cost_bp).net
    legs = pc1_prime(on, comparator_S(m_star, x_off), f=f, B=B, seed=seed)
    return all(leg["pass"] for leg in legs)


def placebo_taus(T: int, *, n_family: int, seed: int) -> tuple[np.ndarray, list[int]]:
    """Family taus uniform on [252, T - 252] (seed); per-card tau_k = round(252 + k (T - 504) / 19), k = 0..19
    (Python round, frozen with the source; brief F-29)."""
    if T < 2 * TAU_MIN:
        raise AcceptanceRefused(f"T = {T} < {2 * TAU_MIN}: no placebo shift window")
    fam = np.random.default_rng(seed).integers(TAU_MIN, T - TAU_MIN, size=n_family, endpoint=True)
    card = [round(TAU_MIN + k * (T - 2 * TAU_MIN) / (PLACEBO_PER_CARD - 1)) for k in range(PLACEBO_PER_CARD)]
    return fam, card


def placebo_panel(m, x_off, cost_bp: float, f: float, *, B: int, seed: int) -> dict:
    """The 20-shift panel printed on every card (L2192); appends no ledger row."""
    _, taus = placebo_taus(np.asarray(m).size, n_family=1, seed=seed)
    passes = sum(placebo_passes(m, x_off, cost_bp, t, f, B=B, seed=seed) for t in taus)
    return {"n": len(taus), "passes": int(passes), "taus": taus}


def cdar_guard_default_rule(candidates_results: dict) -> str:
    """D6 default (L2187): of the three candidates, the one with the lowest per-family placebo false-pass rate
    among those that bring every negative control to REJECT or INSUFFICIENT_DATA; ties go to the Professors'
    test. `candidates_results` = {name: {placebo_false_pass_rate, controls: {id: verdict}}}. Fails closed (raises
    AcceptanceRefused) when no candidate brings every control to an allowed verdict (R-21 9(a))."""
    eligible = {}
    for name in CDAR_CANDIDATES:
        r = candidates_results.get(name)
        if r is None:
            continue
        ctl = r.get("controls") or {}
        if set(ctl) >= set(NEGATIVE_CONTROLS) and all(ctl[c] in CONTROL_VERDICTS for c in NEGATIVE_CONTROLS):
            eligible[name] = float(r["placebo_false_pass_rate"])
    if not eligible:
        raise AcceptanceRefused("CDaR guard: no candidate brings every negative control to REJECT or INSUFFICIENT_DATA; the attempt fails")
    best = min(eligible.values())
    tied = [n for n, v in eligible.items() if v == best]
    return CDAR_CANDIDATES[0] if CDAR_CANDIDATES[0] in tied else tied[0]


def _read_attempts(path: Path) -> list[dict]:
    """The log through `cards.read_chain` (canonical bytes, ATTEMPT_ROW fields), the reader gate_package uses."""
    from core.quant import cards                              # lazy: cards / gate_package never import this module
    from core.quant.gate_package import ATTEMPT_ROW
    try:
        return cards.read_chain(path, ATTEMPT_ROW)
    except cards.CardRefused as exc:
        raise AcceptanceRefused(f"attempts log {path}: hash chain broken: {exc}") from None


def _append_attempt(path: Path, row: dict) -> str:
    from core.quant import cards
    _read_attempts(path)                                      # never append onto a broken chain
    return cards.chain_append(path, row)                     # flush + fsync (one writer, one chain)


def attempts(log_path) -> list[dict]:
    """Every attempt row of the hash-chained log, printed beside every verdict produced later (L2188)."""
    return _read_attempts(Path(log_path))


def _check_redesign(redesign: Optional[dict], rows: list[dict], card_ids: set, run_utc: str) -> dict:
    """Bounded redesign (R2-C3, L2181): one per package version; the diff touches frozen-items-table items only;
    the rationale cites the family panels and the negative controls, never a named card; fresh seeds fixed and
    logged before the run."""
    if not redesign:
        raise AcceptanceRefused("one failure is on record: a re-attempt needs a redesign record (frozen-items diff, rationale, fresh seeds)")
    diff = list(redesign.get("diff") or ())
    bad = [d for d in diff if d.split(".")[0] not in FROZEN_ITEMS]
    if not diff or bad:
        raise AcceptanceRefused(f"redesign diff touches items outside the frozen-items table: {bad or 'empty diff'}")
    rationale = str(redesign.get("rationale") or "")
    if "family" not in rationale.lower() or "control" not in rationale.lower():
        raise AcceptanceRefused("redesign rationale must cite the per-family panels and the negative controls")
    if any(cid in rationale for cid in card_ids):
        raise AcceptanceRefused("redesign rationale names a card: refused (never a named card's panel or numbers)")
    seeds = redesign.get("seeds")
    logged = redesign.get("seeds_logged_utc")
    if not seeds or not logged or str(logged) >= run_utc:
        raise AcceptanceRefused("redesign: fresh seeds must be fixed and logged before the run")
    if rows and seeds == rows[-1].get("seeds"):
        raise AcceptanceRefused("redesign: seeds must be fresh (they equal the failed attempt's)")
    version = rows[-1].get("package_version") if rows else None
    if any(r.get("redesign") and r.get("package_version") == version for r in rows):
        raise AcceptanceRefused("one bounded redesign per package version is allowed")
    return {"diff": diff, "rationale": rationale, "seeds": seeds, "seeds_logged_utc": str(logged)}


@dataclass(frozen=True)
class AcceptanceResult:
    per_family_placebo_pass_rate: dict
    per_card_pass_counts: dict
    controls: dict
    passed: bool
    attempt_no: int
    redesign_allowed: bool
    reason: Optional[str]
    pc2_horizon_adopted: bool
    cdar_guard: Optional[str]
    d6_rule: str
    row_md5: str
    f: dict


def gate_acceptance_test(package_version: str, families: dict, controls: dict, seed: int, B: int, log_path,
                         *, run_utc: str, d6_rule: str = D6_OPTIONS[0], redesign: Optional[dict] = None,
                         governance_log=None, page_owner: Optional[Callable[[str], None]] = None,
                         n_family: int = PLACEBO_PER_FAMILY, cdar_candidates: Optional[dict] = None,
                         pc2_horizon_false_pass: Optional[dict] = None, clock: Optional[Callable] = None) -> AcceptanceResult:
    """R-21 rule 9 (L2174-2188). `families` = {family_id: [card]} with card = {card_id, m (earning multiplier),
    x_off (excess), cost_bp, f (per row-set reading, max binds), draft_md5}; `controls` = {id: verdict | callable
    -> verdict} for every one of the five named negative controls (their rule definitions are reference data;
    a missing control fails closed). Placebos: 300 per family pooled across its cards (own series, 300 per card)
    and 20 per card; pass by `placebo_passes`. Every attempt, passing or not, is appended to the hash-chained
    `log_path` as a package trial; failures count across all 2.x versions and never reset: the third attempt is
    refused, a second failure writes a `package_redesign` governance event and pages the owner, every card stays
    NOT_RUN. No real card's verdict is computed here. Tests pass a temporary `log_path`; the production
    `gate/acceptance_runs.jsonl` stays empty until the real attempt on the frozen reference data."""
    log_path = Path(log_path)
    rows = _read_attempts(log_path)
    fails = sum(r.get("outcome") == "fail" for r in rows)
    if fails >= 2:
        raise AcceptanceRefused("no_card_evaluated_under_v2: two failed attempts are on record across 2.x versions; "
                                "a third attempt is refused, also after a version bump")
    if d6_rule not in D6_OPTIONS:
        raise AcceptanceRefused(f"D6 rule {d6_rule!r} is not an option; it is recorded before the first attempt")
    card_ids = {c["card_id"] for cards in families.values() for c in cards}
    redesign_rec = _check_redesign(redesign, rows, card_ids, run_utc) if fails == 1 else None
    seeds = redesign_rec["seeds"] if redesign_rec else {"placebo": seed, "controls": seed}
    missing = [c for c in NEGATIVE_CONTROLS if c not in controls]
    if missing:
        raise AcceptanceRefused(f"negative controls not supplied (their rules are reference data): {missing}")
    per_family, per_card, f_out = {}, {}, {}
    pseed = int(seeds["placebo"])
    for fid, cards in families.items():
        passes, n = 0, 0
        for c in cards:
            m, off = np.asarray(c["m"], dtype=float), np.asarray(c["x_off"], dtype=float)
            f = float(c.get("f", 1.0))
            f_out[c["card_id"]] = {"binding": f, "readings": c.get("f_readings") or {"binding": f}}
            fam_taus, card_taus = placebo_taus(m.size, n_family=n_family, seed=pseed)
            passes += sum(placebo_passes(m, off, c["cost_bp"], int(t), f, B=B, seed=pseed) for t in fam_taus)
            n += len(fam_taus)
            per_card[c["card_id"]] = int(sum(placebo_passes(m, off, c["cost_bp"], int(t), f, B=B, seed=pseed) for t in card_taus))
        per_family[fid] = {"n": n, "passes": int(passes), "rate": passes / n if n else 0.0}
    family_ok = all(10 * v["passes"] <= v["n"] for v in per_family.values())
    cards_ok = all(v <= PLACEBO_CARD_MAX for v in per_card.values())
    verdicts = {k: (controls[k]() if callable(controls[k]) else controls[k]) for k in NEGATIVE_CONTROLS}
    controls_ok = all(v in CONTROL_VERDICTS for v in verdicts.values())
    guard = None
    if not controls_ok and cdar_candidates is not None:
        try:
            guard = cdar_guard_default_rule(cdar_candidates) if d6_rule == D6_OPTIONS[0] else d6_rule
            r = cdar_candidates.get(guard) or {}
            if all((r.get("controls") or {}).get(c) in CONTROL_VERDICTS for c in NEGATIVE_CONTROLS):
                verdicts, controls_ok = {c: r["controls"][c] for c in NEGATIVE_CONTROLS}, True
        except AcceptanceRefused:
            guard = None
    adopted = False
    if pc2_horizon_false_pass:
        adopted = all(v <= 0.10 for v in pc2_horizon_false_pass.values())
    passed = family_ok and cards_ok and controls_ok
    reason = None if passed else ("placebo_family_excess" if not family_ok else "placebo_card_excess" if not cards_ok else "negative_control_passed")
    attempt_no = len(rows) + 1
    row = {"attempt_no": attempt_no, "utc": run_utc, "package_version": package_version, "counts_as": "package_trial",
           "seeds": seeds, "d6_rule": d6_rule, "cdar_guard": guard, "draft_md5s": {c["card_id"]: c.get("draft_md5") for cs in families.values() for c in cs},
           "per_family": per_family, "per_card": per_card, "controls": verdicts, "pc2_horizon_adopted": adopted,
           "outcome": "pass" if passed else "fail", "reason": reason, "redesign": redesign_rec, "f": f_out}
    row_md5 = _append_attempt(log_path, row)
    second_failure = (not passed) and fails == 1
    if second_failure:
        if governance_log is not None:
            from core.rules import governance
            governance.append_event(Path(governance_log), {"kind": "package_redesign", "actor": "harness", "key": "gate.package",
                                                           "old": package_version, "new": None, "utc": run_utc,
                                                           "reason": "second acceptance failure across 2.x: no card evaluated under v2; owner paged",
                                                           "refs": [str(log_path)]})
        if page_owner is not None:
            page_owner("second gate-acceptance failure: no card can be evaluated under v2 (R2-C3)")
    return AcceptanceResult(per_family, per_card, verdicts, passed, attempt_no, not passed and fails == 0, reason, adopted,
                            guard, d6_rule, row_md5, f_out)
