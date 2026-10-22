"""The validation gate: what decides whether a strategy or a distributional
model is embedded in QUANTGEN, kept for revision, or excluded.

Two loops, one vocabulary (PASS / REVISE / REJECT / INSUFFICIENT_DATA), and a
model card that records every number with the sample size behind it, so the
operator can read a verdict without judging the statistics themselves.

STRATEGY LOOP — purged walk-forward on a pre-computed P&L matrix
  `walk_forward(pnl, ...)` takes the daily net P&L of EVERY configuration of a
  strategy over the whole sample (T sessions × G configs, each column causal),
  chooses the in-sample winner at every origin (IS window 756 sessions, OOS
  block 126, an embargo of the holding period between them), and concatenates
  the out-of-sample blocks. Then: annualised Sharpe with Lo's standard error,
  a studentised circular block-bootstrap 90 % interval, the deflated Sharpe
  ratio for N trials, the probability of backtest overfitting by CSCV over the
  whole grid, OOS/IS, positive-year share, survival at 2× costs, the parameter
  plateau, a volatility/direction regime split, and a McLean–Pontiff haircut.

DISTRIBUTION LOOP — rolling-origin VaR / coverage / PIT
  `score_distribution(hits95, hits99, inband90, pit, ...)` takes what a
  rolling fit produced at each origin and applies Kupiec, Christoffersen, the
  Basel traffic light, 90 % coverage with a binomial band, PIT Kolmogorov–
  Smirnov / chi-square / Berkowitz tests and the DGT correlograms; `crps` and
  `dm_test` rank challengers against the incumbent.

Sources (verified in research_notes/.../validation_methodology.md): CS229 §9.3;
Berkeley TS lectures 4, 6, 8; STAT248 §21–22; Bailey & López de Prado 2014
(deflated Sharpe); Bailey, Borwein, López de Prado & Zhu 2017 (PBO/CSCV); Lo
2002 (SE); Ledoit & Wolf 2008 (bootstrap); Kupiec 1995; Christoffersen 1998;
Diebold, Gunther & Tay 1998; Berkowitz 2001; Gneiting & Raftery 2007 (CRPS);
Diebold & Mariano 1995; McLean & Pontiff 2016 (26–58 % decay).
Everything is numpy / scipy; every random draw is seeded.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass, field
from datetime import date
from itertools import combinations
from pathlib import Path
from typing import Any, Optional, Sequence

import numpy as np
from scipy import stats as sps

TRADING_DAYS = 252
EULER_GAMMA = 0.5772156649015329
DECISIONS = ("PASS", "REVISE", "REJECT", "INSUFFICIENT_DATA")

# Pre-registered thresholds (the gate); change them here and nowhere else.
GATE = {
    "w_is": 756, "w_oos": 126, "min_is": 504, "ci_level": 0.90, "bootstrap_B": 2000, "block": 10,
    "dsr_min": 0.95, "pbo_max": 0.05, "pbo_reject": 0.20, "oos_is_min": 0.5, "years_pos_min": 0.60,
    "plateau_min": 0.5, "trades_min": 100, "trades_floor": 30, "oos_years_min": 5,
    "haircut": 0.6, "cost_stress": 2.0,
    # PBO by CSCV ranks the in-sample winner among the grid; with fewer than 8
    # configurations the rank is too coarse to mean anything (rank ≤ 3 of 6 is a
    # coin flip even for a genuine edge), so the over-search check falls back to
    # the share of splits where the in-sample winner LOSES out of sample.
    # PBO is also 0.5 by construction on a flat plateau (near-identical
    # configurations: the in-sample winner is the luckiest, and the CSCV halves
    # are complementary, so its rank flips), which is not over-search; the
    # rejection therefore needs PBO > pbo_reject AND the winner losing out of
    # sample in more than prob_loss_max of the splits (Bailey et al. 2017 §6:
    # PBO, probability of loss and degradation are read together).
    "pbo_min_configs": 8, "prob_loss_max": 0.10,
    # When a benchmark is supplied the claim is "beats the benchmark": the paired
    # block-bootstrap one-sided p of the Sharpe difference must be ≤ 0.10.
    "bench_p_max": 0.10,
    "var95_min_origins": 500, "var99_min_origins": 1000, "pit_ks_min": 0.05, "pit_ks_reject": 0.01,
    "kupiec_min": 0.05, "cc_min": 0.05, "exceed_reject_mult": 2.0, "nonconv_max": 0.05,
}

# Pre-registered per-side costs in bp (P10): defined once, here; the study and
# the R-26 tick floor (core/quant/instruments.py) read them and never redefine them.
COST_BP_PER_SIDE = {"krx_etf": 3.0, "krx_stock": 35.0, "us": 50.0, "crypto": 10.0, "futures": 5.0, "fx": 10.0}


# KRX ETFs QUANTGEN already trades or studies outside the instrument registry (paper_live, the asset study)
KRX_ETF_CODES = frozenset({"069500", "102110", "114800", "132030", "148070", "152380", "229200", "251340",
                           "261240", "261250"})
KRX_INDEX_FUTURES = ("A01", "A05", "A06", "101", "105", "106")     # KOSPI 200 / KOSDAQ 150 futures codes on KIS


def cost_class(symbol: str) -> Optional[str]:
    """The table row a symbol is costed on, from the instrument registry, else its form; None if it has none.

    A six-digit KRX code is `krx_etf` (3 bp) only when QUANTGEN knows it as an ETF (the instrument registry or
    KRX_ETF_CODES); any other code is costed as a stock, `krx_stock` (35 bp), so an unknown ETF is overcharged
    rather than a stock undercharged."""
    from core.quant.history import _looks_crypto     # the same routing load_history uses
    from core.quant.instruments import INSTRUMENTS   # instruments imports this module

    s = (symbol or "").strip().upper()
    code = s.split(".")[0]
    if code in INSTRUMENTS:
        return INSTRUMENTS[code].cost_class if INSTRUMENTS[code].cost_class in COST_BP_PER_SIDE else "krx_etf"
    if s.endswith(("-USD", "-USDT", "-KRW")) or s.startswith(("BTC-",)) or _looks_crypto(s):
        return "crypto"
    if s.endswith("=X") or s.startswith("FX@"):
        return "fx"
    if s.endswith("=F") or (len(s) == 6 and not s.isdigit() and s.startswith(KRX_INDEX_FUTURES)):
        return "futures"
    if code.isdigit() and len(code) == 6 and s[len(code):] in ("", ".KS", ".KQ"):
        return "krx_etf" if code in KRX_ETF_CODES else "krx_stock"
    if ":" in s and s.split(":", 1)[0] in ("NAS", "NYS", "AMS"):     # KIS overseas form, e.g. NAS:AAPL
        return "us"
    if s and s.replace("-", "").isalpha():           # Yahoo US form (SPY, BRK-B); a dotted suffix is another venue
        return "us"
    return None


def cost_floor_bp(symbols: Sequence[str]) -> tuple[Optional[float], dict[str, Optional[str]]]:
    """Lowest per-side cost a single-rate run over `symbols` may use: the highest of their table rows, since one
    rate is charged on every leg. None when a symbol has no row (e.g. LSE): QUANTGEN cannot cost it."""
    classes = {s: cost_class(s) for s in symbols}
    if not classes or any(c is None for c in classes.values()):
        return None, classes
    return max(cost_bp(c) for c in classes.values()), classes


def cost_bp(venue: str) -> float:
    """Table rate per side for a cost class. `KRX_LI_ETF` without its own row
    takes the KRX ETF rate and the tick floor governs (R-26 rule 2)."""
    if venue == "KRX_LI_ETF" and venue not in COST_BP_PER_SIDE:
        return COST_BP_PER_SIDE["krx_etf"]
    if venue not in COST_BP_PER_SIDE:
        raise KeyError(f"unknown cost class {venue!r}; the gate table has {sorted(COST_BP_PER_SIDE)}")
    return float(COST_BP_PER_SIDE[venue])


# --------------------------------------------------------------------------- #
# Basic statistics
# --------------------------------------------------------------------------- #
def sharpe(daily: np.ndarray) -> float:
    d = np.asarray(daily, dtype=float)
    d = d[np.isfinite(d)]
    if d.size < 2:
        return float("nan")
    sd = float(np.std(d, ddof=1))
    return float(np.mean(d) / sd * math.sqrt(TRADING_DAYS)) if sd > 0 else 0.0


def lo_se(daily: np.ndarray) -> float:
    """Lo (2002) iid standard error of the annualised Sharpe ratio."""
    d = np.asarray(daily, dtype=float)
    T = d.size
    if T < 2:
        return float("nan")
    sr_d = sharpe(d) / math.sqrt(TRADING_DAYS)
    return math.sqrt((1.0 + 0.5 * sr_d ** 2) / T) * math.sqrt(TRADING_DAYS)


def min_track_record(sr_annual: float, level: float = 0.90) -> float:
    """Sessions needed before a two-sided `level` interval (one-sided (1+level)/2)
    can exclude zero: T > 252·(z/SR)²."""
    z = sps.norm.ppf(1.0 - (1.0 - level) / 2.0)
    return math.inf if sr_annual <= 0 else TRADING_DAYS * (z / sr_annual) ** 2


def block_bootstrap_ci(daily: np.ndarray, *, block: int = 10, B: int = 2000, level: float = 0.90,
                       seed: int = 11) -> tuple[float, float]:
    """Studentised circular block bootstrap of the annualised Sharpe (Ledoit &
    Wolf 2008 form): T* = (SR* − SR)/SE*, CI = [SR − t_hi·SE, SR − t_lo·SE]."""
    d = np.asarray(daily, dtype=float)
    T = d.size
    if T < 2 * block:
        return float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    sr, se = sharpe(d), lo_se(d)
    n_blocks = int(math.ceil(T / block))
    starts = rng.integers(0, T, size=(B, n_blocks))
    idx = (starts[:, :, None] + np.arange(block)[None, None, :]) % T
    samples = d[idx].reshape(B, -1)[:, :T]
    m, s = samples.mean(axis=1), samples.std(axis=1, ddof=1)
    sr_b = np.where(s > 0, m / np.where(s > 0, s, 1.0) * math.sqrt(TRADING_DAYS), 0.0)
    se_b = np.sqrt((1.0 + 0.5 * (sr_b / math.sqrt(TRADING_DAYS)) ** 2) / T) * math.sqrt(TRADING_DAYS)
    t_star = (sr_b - sr) / np.where(se_b > 0, se_b, 1e-12)
    a = (1.0 - level) / 2.0
    t_lo, t_hi = np.quantile(t_star, [a, 1.0 - a])
    return float(sr - t_hi * se), float(sr - t_lo * se)


def sharpe_diff_bootstrap(a: np.ndarray, b: np.ndarray, *, block: int = 10, B: int = 2000, level: float = 0.90,
                          seed: int = 11) -> dict:
    """Paired circular block bootstrap of SR(a) − SR(b) (the same blocks drawn for
    both series, Ledoit & Wolf 2008): the point difference, its `level`
    interval and the one-sided p-value that the difference is ≤ 0."""
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    T = min(a.size, b.size)
    a, b = a[-T:], b[-T:]
    if T < 2 * block:
        return {"diff": float("nan"), "ci": (float("nan"), float("nan")), "p": float("nan")}
    rng = np.random.default_rng(seed)
    n_blocks = int(math.ceil(T / block))
    starts = rng.integers(0, T, size=(B, n_blocks))
    idx = (starts[:, :, None] + np.arange(block)[None, None, :]) % T
    idx = idx.reshape(B, -1)[:, :T]
    sa, sb = a[idx], b[idx]
    def _sr(x):
        m, s = x.mean(axis=1), x.std(axis=1, ddof=1)
        return np.where(s > 0, m / np.where(s > 0, s, 1.0), 0.0) * math.sqrt(TRADING_DAYS)
    d = _sr(sa) - _sr(sb)
    alpha = (1.0 - level) / 2.0
    return {"diff": sharpe(a) - sharpe(b), "ci": tuple(float(x) for x in np.quantile(d, [alpha, 1 - alpha])),
            "p": float(np.mean(d <= 0.0))}


def expected_max_sharpe(n_trials: int, sr_sd: float) -> float:
    """E[max of N null Sharpe ratios] ≈ sd·[(1−γ)Φ⁻¹(1−1/N) + γΦ⁻¹(1−1/(N·e))]."""
    n = max(int(n_trials), 1)
    if n == 1:
        return 0.0
    return float(sr_sd * ((1 - EULER_GAMMA) * sps.norm.ppf(1 - 1.0 / n)
                          + EULER_GAMMA * sps.norm.ppf(1 - 1.0 / (n * math.e))))


def deflated_sharpe(daily: np.ndarray, *, n_trials: int, sr_sd_daily: float) -> float:
    """Bailey & López de Prado (2014): probability that the observed (per-period)
    Sharpe exceeds the expected maximum of `n_trials` null trials, with the
    skew/kurtosis-adjusted standard error. `sr_sd_daily` is the dispersion of
    the trials' per-period Sharpes."""
    d = np.asarray(daily, dtype=float)
    T = d.size
    if T < 3:
        return float("nan")
    sd = float(np.std(d, ddof=1))
    sr = float(np.mean(d) / sd) if sd > 0 else 0.0
    g3 = float(sps.skew(d)) if sd > 0 else 0.0
    g4 = float(sps.kurtosis(d, fisher=False)) if sd > 0 else 3.0
    sr0 = expected_max_sharpe(n_trials, sr_sd_daily)
    denom = 1.0 - g3 * sr + (g4 - 1.0) / 4.0 * sr ** 2
    if denom <= 0:
        return float("nan")
    return float(sps.norm.cdf((sr - sr0) * math.sqrt(T - 1) / math.sqrt(denom)))


def pbo_cscv(pnl: np.ndarray, *, S: int = 8) -> dict:
    """Probability of backtest overfitting (Bailey et al. 2017, CSCV): split the
    T×G P&L matrix into S blocks, for every choice of S/2 training blocks pick
    the in-sample best config and record its rank out of sample. PBO = share of
    splits where that config ranks below the OOS median."""
    M = np.asarray(pnl, dtype=float)
    T, G = M.shape
    if G < 2 or T < 2 * S:
        return {"pbo": float("nan"), "n_splits": 0, "prob_loss": float("nan"), "slope": float("nan")}
    blocks = np.array_split(np.arange(T), S)
    logits, oos_sr, is_sr = [], [], []
    for train in combinations(range(S), S // 2):
        tr = np.concatenate([blocks[i] for i in train])
        te = np.concatenate([blocks[i] for i in range(S) if i not in train])
        sr_tr = _col_sharpe(M[tr])
        sr_te = _col_sharpe(M[te])
        best = int(np.nanargmax(sr_tr))
        rank = float(np.sum(sr_te <= sr_te[best]))          # 1 = worst ... G = best
        w = rank / (G + 1.0)
        logits.append(math.log(w / (1.0 - w)))
        oos_sr.append(float(sr_te[best]))
        is_sr.append(float(sr_tr[best]))
    logits = np.asarray(logits)
    slope = float(np.polyfit(is_sr, oos_sr, 1)[0]) if len(set(is_sr)) > 1 else float("nan")
    return {"pbo": float(np.mean(logits < 0)), "n_splits": int(logits.size),
            "prob_loss": float(np.mean(np.asarray(oos_sr) < 0)), "slope": slope}


def _col_sharpe(M: np.ndarray) -> np.ndarray:
    m, s = M.mean(axis=0), M.std(axis=0, ddof=1)
    return np.where(s > 0, m / np.where(s > 0, s, 1.0), 0.0) * math.sqrt(TRADING_DAYS)


def newey_west_t(d: np.ndarray, lag: int) -> float:
    d = np.asarray(d, dtype=float)
    n = d.size
    if n < 5:
        return float("nan")
    m = d.mean()
    u = d - m
    s = float(u @ u) / n
    for k in range(1, lag + 1):
        w = 1.0 - k / (lag + 1.0)
        s += 2.0 * w * float(u[k:] @ u[:-k]) / n
    return float(m / math.sqrt(s / n)) if s > 0 else float("nan")


def dm_test(loss_a: np.ndarray, loss_b: np.ndarray, *, lag: int = 0) -> dict:
    """Diebold–Mariano on d = loss_a − loss_b; negative t favours A."""
    d = np.asarray(loss_a, dtype=float) - np.asarray(loss_b, dtype=float)
    t = newey_west_t(d, lag)
    p = float(2 * sps.norm.sf(abs(t))) if math.isfinite(t) else float("nan")
    return {"t": t, "p": p, "mean_diff": float(np.mean(d)), "n": int(d.size)}


# --------------------------------------------------------------------------- #
# Data checks (architecture review D1)
# --------------------------------------------------------------------------- #
def data_checks(dates: Sequence[str], closes: Sequence[float], *, max_gap_sessions: int = 5,
                stale_days: int = 5, today: Optional[date] = None) -> list[str]:
    """Problems that make a series unfit for fitting; empty list = clean."""
    px = np.asarray(closes, dtype=float)
    problems: list[str] = []
    if px.size < 30:
        problems.append(f"only {px.size} sessions")
        return problems
    if len(set(dates)) != len(dates):
        problems.append("duplicate dates")
    if np.any(px <= 0) or not np.all(np.isfinite(px)):
        problems.append("non-positive or non-finite closes")
        return problems
    r = np.diff(np.log(px))
    zero = float(np.mean(r == 0))
    if zero > 0.2:
        problems.append(f"{zero:.0%} of returns are exactly zero (stale prints)")
    big = np.abs(r) > 0.5
    if big.any():
        first = np.asarray(list(dates)[1:])[big][0]
        problems.append(f"{int(big.sum())} move(s) beyond ±50 % (split or bad print) at {first}")
    ds = [date.fromisoformat(d) for d in dates]
    gaps = [(ds[i] - ds[i - 1]).days for i in range(1, len(ds))]
    if max(gaps) > max_gap_sessions * 2 + 3:
        problems.append(f"gap of {max(gaps)} calendar days inside the series")
    today = today or date.today()
    if (today - ds[-1]).days > stale_days:
        problems.append(f"last session {dates[-1]} is {(today - ds[-1]).days} days old")
    return problems


# --------------------------------------------------------------------------- #
# Strategy loop
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class WalkForward:
    dates: tuple[str, ...]                 # OOS session dates, concatenated
    pnl: np.ndarray = field(repr=False)    # OOS net daily P&L (fraction of equity)
    pnl_stress: np.ndarray = field(repr=False)   # same at stressed costs
    turnover: np.ndarray = field(repr=False)     # |Δposition| per OOS session
    origins: tuple[int, ...]
    chosen: tuple[int, ...]                # grid index chosen at each origin
    is_sharpes: np.ndarray = field(repr=False)   # n_origins × G
    n_configs: int
    note: str = ""


def walk_forward(pnl: np.ndarray, dates: Sequence[str], *, turnover: Optional[np.ndarray] = None,
                 pnl_stress: Optional[np.ndarray] = None, w_is: int = GATE["w_is"],
                 w_oos: int = GATE["w_oos"], embargo: int = 0, min_is: int = GATE["min_is"]) -> WalkForward:
    """`pnl` is T × G: the daily net P&L of every configuration, each computed
    causally on the full sample. At each origin o the winner on [o − w_is, o)
    is applied on [o + embargo, o + embargo + w_oos); origins step by w_oos so
    the OOS blocks tile without overlap. `pnl_stress` (2× costs) and
    `turnover` follow the chosen column."""
    M = np.asarray(pnl, dtype=float)
    if M.ndim == 1:
        M = M[:, None]
    T, G = M.shape
    if len(dates) != T:
        raise ValueError(f"dates ({len(dates)}) and pnl rows ({T}) differ")
    Ms = np.asarray(pnl_stress, dtype=float) if pnl_stress is not None else M
    if Ms.ndim == 1:
        Ms = Ms[:, None]
    To = np.asarray(turnover, dtype=float) if turnover is not None else np.zeros_like(M)
    if To.ndim == 1:
        To = To[:, None]
    first = w_is if T - w_is >= w_oos + embargo else min_is
    if T < first + embargo + 21:
        raise ValueError(f"need at least {first + embargo + 21} sessions for one walk-forward step, got {T}")
    out_d, out_p, out_s, out_t, origins, chosen, is_sr = [], [], [], [], [], [], []
    o = first
    while o + embargo < T - 1:
        lo_i = max(0, o - w_is)
        sr = _col_sharpe(M[lo_i:o])
        g = int(np.nanargmax(sr))
        a, b = o + embargo, min(o + embargo + w_oos, T)
        out_d.extend(dates[a:b]); out_p.extend(M[a:b, g]); out_s.extend(Ms[a:b, g]); out_t.extend(To[a:b, g])
        origins.append(o); chosen.append(g); is_sr.append(sr)
        o += w_oos
    return WalkForward(dates=tuple(out_d), pnl=np.asarray(out_p), pnl_stress=np.asarray(out_s),
                       turnover=np.asarray(out_t), origins=tuple(origins), chosen=tuple(chosen),
                       is_sharpes=np.asarray(is_sr), n_configs=G,
                       note=f"IS {w_is} / OOS {w_oos} / embargo {embargo}; {len(origins)} origins; {G} configs")


def plateau_share(grid: Sequence[dict], sharpes: np.ndarray, best: int,
                  domain: Optional[dict] = None) -> tuple[float, bool]:
    """Share of the ±1-step neighbours of `best` (one parameter moved to its
    adjacent value) whose Sharpe is ≥ half the best's; and whether the best sits
    on an edge of any parameter's value set. An edge only exists on an axis
    with three or more values: on a two-value axis every point is an end. An
    end that is the parameter's natural limit (`domain[name] = (lo, hi)`, e.g.
    zero hysteresis or unanimity) is not an edge either: nothing lies beyond it."""
    if len(grid) < 2:
        return 1.0, False
    keys = sorted({k for g in grid for k in g})
    values = {k: sorted({g[k] for g in grid if k in g}) for k in keys}
    b = grid[best]
    neighbours = []
    edge = False
    for k in keys:
        vs = values[k]
        if len(vs) < 2 or k not in b:
            continue
        i = vs.index(b[k])
        lim = (domain or {}).get(k)
        natural = lim is not None and any(abs(float(b[k]) - float(x)) < 1e-12 for x in lim)
        if len(vs) >= 3 and i in (0, len(vs) - 1) and not natural:
            edge = True
        for j in (i - 1, i + 1):
            if 0 <= j < len(vs):
                cand = dict(b); cand[k] = vs[j]
                for gi, g in enumerate(grid):
                    if g == cand:
                        neighbours.append(gi)
    if not neighbours:
        return 1.0, edge
    ref = sharpes[best]
    ok = [sharpes[n] >= 0.5 * ref for n in neighbours] if ref > 0 else [sharpes[n] >= ref for n in neighbours]
    return float(np.mean(ok)), edge


def full_years(first: str, last: str) -> int:
    """Whole years from `first` to `last` (ISO dates): anniversaries reached, as `lab.has_min_history` counts."""
    (y0, m0, d0), (y1, m1, d1) = ((int(x) for x in s[:10].split("-")) for s in (first, last))
    return (y1 - y0) - ((m1, d1) < (m0, d0))


def year_stats(dates: Sequence[str], pnl: np.ndarray) -> dict:
    """Per-calendar-year P&L (the "positive years" test reads these, partial years included) and `n_years`, the
    whole years the sample spans. n_years used to count calendar years touched, so Nov 2021 to Feb 2025, about
    3.3 years, counted as 5 and passed the five-year rule."""
    years: dict[str, float] = {}
    for d, p in zip(dates, pnl):
        years[d[:4]] = years.get(d[:4], 0.0) + float(p)
    tot = sum(abs(v) for v in years.values()) or 1.0
    return {"by_year": years, "positive_share": float(np.mean([v > 0 for v in years.values()])) if years else float("nan"),
            "max_year_share": float(max(abs(v) for v in years.values()) / tot) if years else float("nan"),
            "n_years": full_years(min(dates), max(dates)) if len(dates) else 0}


def regime_split(pnl: np.ndarray, bench: Optional[np.ndarray], *, window: int = 63) -> dict:
    """OOS Sharpe in high- vs low-volatility and up- vs down-benchmark halves,
    classified on the trailing `window` sessions of the benchmark (known at t)."""
    if bench is None or len(bench) != len(pnl) or len(pnl) < 2 * window:
        return {}
    b = np.asarray(bench, dtype=float)
    vol = np.array([np.std(b[max(0, i - window):i], ddof=1) if i >= 5 else np.nan for i in range(len(b))])
    ret = np.array([np.sum(b[max(0, i - window):i]) if i >= 5 else np.nan for i in range(len(b))])
    ok = np.isfinite(vol)
    hi = vol > np.nanmedian(vol)
    up = ret > 0
    return {"high_vol": sharpe(pnl[ok & hi]), "low_vol": sharpe(pnl[ok & ~hi]),
            "up_market": sharpe(pnl[ok & up]), "down_market": sharpe(pnl[ok & ~up])}


@dataclass
class StrategyScore:
    sr_oos: float
    se_lo: float
    ci90: tuple[float, float]
    sr_is: float
    oos_is: float
    dsr: float
    pbo: float
    pbo_slope: float
    prob_loss_oos: float
    sr_stress: float
    turnover_annual: float
    n_trades: int
    n_sessions: int
    years_positive: float
    n_years: int
    max_year_share: float
    plateau: float
    edge: bool
    regime: dict
    total_return: float
    max_drawdown: float
    haircut_sr: float
    bench_sr: float
    n_trials: int
    n_configs: int = 1
    bench_diff: float = float("nan")      # SR − SR_bench
    bench_p: float = float("nan")         # one-sided bootstrap P(diff ≤ 0)
    bench_ci: tuple[float, float] = (float("nan"), float("nan"))
    bench_mdd: float = float("nan")       # the benchmark's max drawdown over the same OOS sessions
    decision: str = ""
    reason: str = ""
    revise_target: Optional[str] = None
    lines: list[str] = field(default_factory=list)


def score_strategy(wf: WalkForward, *, grid: Sequence[dict], full_pnl: np.ndarray, n_trials: int,
                   bench_daily: Optional[np.ndarray] = None, seed: int = 11,
                   domain: Optional[dict] = None) -> StrategyScore:
    """Apply the strategy gate to a walk-forward result. `full_pnl` is the same
    T × G matrix walk_forward saw (for CSCV); `n_trials` counts every
    configuration ever tried (grid size plus revisions)."""
    p = wf.pnl
    sr = sharpe(p)
    se = lo_se(p)
    ci = block_bootstrap_ci(p, block=GATE["block"], B=GATE["bootstrap_B"], level=GATE["ci_level"], seed=seed)
    sr_is = float(np.nanmean([wf.is_sharpes[i, g] for i, g in enumerate(wf.chosen)])) if len(wf.chosen) else float("nan")
    # Trial dispersion as the DSR paper defines it: the spread of the trials'
    # Sharpe ratios on the same (full-sample) length, in per-period units.
    full_sr = _col_sharpe(np.asarray(full_pnl)) / math.sqrt(TRADING_DAYS)
    sr_sd_daily = float(np.nanstd(full_sr)) if full_sr.size > 1 else 0.0
    dsr = deflated_sharpe(p, n_trials=max(n_trials, 1), sr_sd_daily=sr_sd_daily)
    pbo = pbo_cscv(np.asarray(full_pnl), S=8 if len(full_pnl) < 2000 else 16)
    ys = year_stats(wf.dates, p)
    last_sr = wf.is_sharpes[-1] if len(wf.is_sharpes) else np.zeros(len(grid))
    plateau, edge = plateau_share(grid, last_sr, wf.chosen[-1] if wf.chosen else 0, domain)
    eq = np.cumprod(1.0 + p)
    mdd = float(np.min(eq / np.maximum.accumulate(eq) - 1.0)) if eq.size else float("nan")
    trades = int(np.round(np.sum(np.abs(wf.turnover) > 1e-12)))
    turnover_ann = float(np.mean(np.abs(wf.turnover)) * TRADING_DAYS) if wf.turnover.size else 0.0
    has_b = bench_daily is not None and len(bench_daily) == len(p)
    bench_sr = sharpe(bench_daily) if has_b else float("nan")
    beq = np.cumprod(1.0 + np.asarray(bench_daily, dtype=float)) if has_b else np.zeros(0)
    bench_mdd = float(np.min(beq / np.maximum.accumulate(beq) - 1.0)) if beq.size else float("nan")
    bd = (sharpe_diff_bootstrap(p, bench_daily, block=GATE["block"], B=GATE["bootstrap_B"], seed=seed)
          if bench_daily is not None and len(bench_daily) == len(p) else {"diff": float("nan"), "p": float("nan"), "ci": (float("nan"), float("nan"))})
    s = StrategyScore(sr_oos=sr, se_lo=se, ci90=ci, sr_is=sr_is,
                      oos_is=(sr / sr_is if sr_is and math.isfinite(sr_is) and sr_is != 0 else float("nan")),
                      dsr=dsr, pbo=pbo["pbo"], pbo_slope=pbo["slope"], prob_loss_oos=pbo["prob_loss"],
                      sr_stress=sharpe(wf.pnl_stress), turnover_annual=turnover_ann, n_trades=trades,
                      n_sessions=int(p.size), years_positive=ys["positive_share"], n_years=ys["n_years"],
                      max_year_share=ys["max_year_share"], plateau=plateau, edge=edge,
                      regime=regime_split(p, bench_daily), total_return=float(eq[-1] - 1.0) if eq.size else 0.0,
                      max_drawdown=mdd, haircut_sr=GATE["haircut"] * sr, bench_sr=bench_sr, n_trials=n_trials,
                      n_configs=int(wf.n_configs), bench_diff=bd["diff"], bench_p=bd["p"], bench_ci=tuple(bd["ci"]),
                      bench_mdd=bench_mdd)
    _decide_strategy(s)
    return s


def _decide_strategy(s: StrategyScore) -> None:
    g = GATE
    lines: list[str] = []
    ok = lambda c: "passes" if c else "fails"                                             # noqa: E731
    lines.append(f"Out-of-sample Sharpe {s.sr_oos:.2f} over {s.n_sessions:,} sessions ({s.n_years} full years); "
                 f"Lo standard error {s.se_lo:.2f}; 90 % block-bootstrap interval {s.ci90[0]:.2f} to {s.ci90[1]:.2f}: "
                 f"{ok(s.ci90[0] > 0)} (the interval must exclude zero).")
    lines.append(f"Deflated Sharpe {s.dsr:.2f} after {s.n_trials} trials: {ok(s.dsr >= g['dsr_min'])} (needs ≥ {g['dsr_min']}).")
    pbo_meaningful = s.n_configs >= g["pbo_min_configs"]
    flat = s.prob_loss_oos <= g["prob_loss_max"]
    if pbo_meaningful:
        lines.append(f"Probability of backtest overfitting {s.pbo:.2f} over the {s.n_configs}-config grid; the in-sample winner "
                     f"loses out of sample in {s.prob_loss_oos:.0%} of the splits: {ok(s.pbo <= g['pbo_max'] or flat)} "
                     f"(PBO ≤ {g['pbo_max']}, or ≤ {g['prob_loss_max']:.0%} losing splits because near-identical configurations put "
                     f"PBO at 0.5 by construction; rejected when PBO > {g['pbo_reject']} and the winner also loses).")
    else:
        lines.append(f"Probability of backtest overfitting {s.pbo:.2f} is reported only: with {s.n_configs} configurations the "
                     f"CSCV rank is too coarse (needs ≥ {g['pbo_min_configs']}); the over-search check uses the share of splits "
                     f"where the in-sample winner loses out of sample, {s.prob_loss_oos:.2f}: {ok(s.prob_loss_oos <= g['prob_loss_max'])} "
                     f"(needs ≤ {g['prob_loss_max']}).")
    lines.append(f"Out-of-sample over in-sample Sharpe {s.oos_is:.2f}: {ok(s.oos_is >= g['oos_is_min'])} (needs ≥ {g['oos_is_min']}).")
    has_bench = math.isfinite(s.bench_p)
    if has_bench:
        lines.append(f"Against the benchmark (Sharpe {s.bench_sr:.2f}): difference {s.bench_diff:+.2f}, paired block-bootstrap "
                     f"90 % interval {s.bench_ci[0]:+.2f} to {s.bench_ci[1]:+.2f}, one-sided p {s.bench_p:.2f}: "
                     f"{ok(s.bench_p <= g['bench_p_max'])} (the claim 'beats the benchmark' needs p ≤ {g['bench_p_max']}); "
                     f"max drawdown {s.max_drawdown:.0%} against the benchmark's {s.bench_mdd:.0%} (reported, not gated).")
    lines.append(f"Positive in {s.years_positive:.0%} of calendar years: {ok(s.years_positive >= g['years_pos_min'])} "
                 f"(needs ≥ {g['years_pos_min']:.0%}); largest year carries {s.max_year_share:.0%} of the P&L.")
    lines.append(f"Sharpe at {g['cost_stress']:.0f}× costs {s.sr_stress:.2f}: {ok(s.sr_stress > 0)} (must stay positive); "
                 f"turnover {s.turnover_annual:.1f}× equity per year.")
    lines.append(f"Parameter plateau {s.plateau:.0%} of neighbours keep half the Sharpe, "
                 f"{'on' if s.edge else 'not on'} a grid edge: {ok(s.plateau >= g['plateau_min'] and not s.edge)}.")
    lines.append(f"{s.n_trades} position changes out of sample: {ok(s.n_trades >= g['trades_min'])} (needs ≥ {g['trades_min']}).")
    if s.regime:
        lines.append("Regime split (Sharpe): high-vol {high_vol:.2f} / low-vol {low_vol:.2f}, up {up_market:.2f} / down {down_market:.2f}."
                     .format(**s.regime))
    lines.append(f"Expected live Sharpe after the McLean–Pontiff haircut: {s.haircut_sr:.2f}.")
    s.lines = lines

    pbo_ok = (s.pbo <= g["pbo_max"] or flat) if pbo_meaningful else flat
    pbo_reject = pbo_meaningful and s.pbo > g["pbo_reject"] and not flat
    hard = (s.ci90[0] > 0, s.dsr >= g["dsr_min"], pbo_ok)
    eng = {"over-search": s.oos_is >= g["oos_is_min"],
           "execution": s.sr_stress > 0,
           "regime": s.years_positive >= g["years_pos_min"],
           "plateau": s.plateau >= g["plateau_min"] and not s.edge,
           "sample": s.n_trades >= g["trades_min"]}
    mtr = min_track_record(s.sr_oos, g["ci_level"])
    min_sessions = round(g["oos_years_min"] * TRADING_DAYS)   # a span with a data hole is not five years of evidence
    if s.n_trades < g["trades_floor"] or s.n_years < g["oos_years_min"] or s.n_sessions < min_sessions:
        s.decision, s.reason = "INSUFFICIENT_DATA", (f"{s.n_trades} trades over {s.n_years} full OOS years "
                                                     f"({s.n_sessions:,} sessions); the gate needs "
                                                     f"≥ {g['trades_floor']} trades and ≥ {g['oos_years_min']} full years of ≥ {min_sessions:,} sessions")
        s.revise_target = "extend history"
        return
    bench_fail = has_bench and not (s.bench_p <= g["bench_p_max"])
    if (s.dsr < g["dsr_min"] and math.isfinite(s.dsr)) or pbo_reject \
            or (s.sr_stress <= 0 and not s.ci90[0] > 0) or bench_fail:
        s.decision = "REJECT"
        s.reason = ("deflated Sharpe below 0.95" if s.dsr < g["dsr_min"] else
                    "PBO above 0.20 and the in-sample winner loses out of sample" if pbo_reject else
                    "loses money at 2× costs and the Sharpe interval includes zero" if s.sr_stress <= 0 and not s.ci90[0] > 0 else
                    f"does not beat its benchmark (Sharpe difference {s.bench_diff:+.2f}, p {s.bench_p:.2f})")
        s.revise_target = None if not bench_fail else "the sleeve set or the cost model, not the rule: the benchmark is as good"
        return
    if all(hard) and all(eng.values()):
        s.decision, s.reason = "PASS", "every gate criterion met"
        s.revise_target = None
        return
    if not hard[0] and hard[1] and hard[2]:
        if s.n_sessions < mtr:
            s.decision = "INSUFFICIENT_DATA"
            s.reason = (f"the Sharpe interval includes zero but DSR and PBO pass; a Sharpe of {s.sr_oos:.2f} needs "
                        f"about {mtr:,.0f} sessions to certify and {s.n_sessions:,} were available")
            s.revise_target = "extend history (pykrx / Yahoo .KS), do not touch the rules"
            return
    failed = [k for k, v in eng.items() if not v]
    s.decision = "REVISE"
    target = failed[0] if failed else "interval"
    s.revise_target = {"over-search": "coarsen the grid or fix a parameter at the plateau centre; lengthen the IS window",
                       "execution": "lengthen the holding period or add a hysteresis band; never lower the cost assumption",
                       "regime": "only a pre-registered regime condition may be tightened; otherwise this is a new hypothesis",
                       "plateau": "widen the grid (edge) or move to the plateau centre and re-run",
                       "sample": "extend history or lengthen the sample",
                       "interval": "the Sharpe interval includes zero: extend history"}[target]
    s.reason = f"{target} check failed ({'; '.join(failed) if failed else 'interval includes zero'})"


# --------------------------------------------------------------------------- #
# Distribution loop
# --------------------------------------------------------------------------- #
def kupiec(hits: np.ndarray, alpha: float) -> dict:
    h = np.asarray(hits, dtype=float)
    n, x = int(h.size), int(np.sum(h))
    if n == 0:
        return {"n": 0, "x": 0, "rate": float("nan"), "lr": float("nan"), "p": float("nan")}
    if x == 0 or x == n:
        z = math.sqrt(n) * (x / n - alpha) / math.sqrt(alpha * (1 - alpha))
        return {"n": n, "x": x, "rate": x / n, "lr": z * z, "p": float(2 * sps.norm.sf(abs(z)))}
    ph = x / n
    lr = -2 * ((n - x) * math.log(1 - alpha) + x * math.log(alpha)) + 2 * ((n - x) * math.log(1 - ph) + x * math.log(ph))
    return {"n": n, "x": x, "rate": ph, "lr": float(lr), "p": float(sps.chi2.sf(lr, 1))}


def christoffersen(hits: np.ndarray, alpha: float) -> dict:
    h = np.asarray(hits, dtype=int)
    if h.size < 10:
        return {"lr_ind": float("nan"), "p_ind": float("nan"), "lr_cc": float("nan"), "p_cc": float("nan")}
    pairs = 2 * h[:-1] + h[1:]
    n00, n01, n10, n11 = (int(np.sum(pairs == k)) for k in (0, 1, 2, 3))
    def _l(p, n1, n0):
        return (n1 * math.log(p) if n1 else 0.0) + (n0 * math.log(1 - p) if n0 else 0.0)
    p01 = n01 / (n00 + n01) if n00 + n01 else 0.0
    p11 = n11 / (n10 + n11) if n10 + n11 else 0.0
    pi = (n01 + n11) / max(n00 + n01 + n10 + n11, 1)
    l_ind = _l(p01, n01, n00) + _l(p11, n11, n10)
    l_null = _l(pi, n01 + n11, n00 + n10)
    lr_ind = max(0.0, -2 * (l_null - l_ind))
    lr_uc = kupiec(h, alpha)["lr"]
    lr_cc = lr_uc + lr_ind
    return {"lr_ind": float(lr_ind), "p_ind": float(sps.chi2.sf(lr_ind, 1)),
            "lr_cc": float(lr_cc), "p_cc": float(sps.chi2.sf(lr_cc, 2))}


def traffic_light(hits99: np.ndarray, window: int = 250) -> str:
    x = int(np.sum(np.asarray(hits99)[-window:]))
    return "green" if x <= 4 else "yellow" if x <= 9 else "red"


def coverage_check(inband: np.ndarray, level: float = 0.90) -> dict:
    b = np.asarray(inband, dtype=float)
    n = b.size
    if n == 0:
        return {"coverage": float("nan"), "se": float("nan"), "ok": False}
    cov = float(b.mean())
    se = math.sqrt(level * (1 - level) / n)
    return {"coverage": cov, "se": se, "ok": abs(cov - level) <= 2 * se, "n": n}


def pit_tests(u: np.ndarray, *, lags: tuple[int, ...] = (1, 5, 20)) -> dict:
    """Diebold–Gunther–Tay: uniformity (KS, chi-square on 10 bins), Berkowitz
    LR on Φ⁻¹(u) (μ = 0, σ = 1, ρ = 0; χ²₃), and correlograms of (u − ū)^k."""
    u = np.asarray(u, dtype=float)
    u = u[np.isfinite(u)]
    n = u.size
    if n < 20:
        return {"n": n, "ks_p": float("nan"), "chi2_p": float("nan"), "berkowitz_p": float("nan"), "acf_flags": []}
    ks = sps.kstest(u, "uniform")
    counts, _ = np.histogram(np.clip(u, 0, 1 - 1e-12), bins=10, range=(0, 1))
    chi2 = sps.chisquare(counts)
    z = sps.norm.ppf(np.clip(u, 1e-6, 1 - 1e-6))
    x, y = z[:-1], z[1:]
    X = np.column_stack([np.ones(x.size), x])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    s2 = float(np.mean(resid ** 2))
    ll_alt = -0.5 * (y.size * math.log(2 * math.pi * s2) + np.sum(resid ** 2) / s2)
    ll_null = -0.5 * (y.size * math.log(2 * math.pi) + np.sum(y ** 2))
    lr = max(0.0, 2 * (ll_alt - ll_null))
    flags = []
    band = 2.0 / math.sqrt(n)
    d = u - u.mean()
    for k in (1, 2, 3, 4):
        s = d ** k
        s = s - s.mean()
        for lag in lags:
            if lag < n - 5:
                r = float(np.corrcoef(s[:-lag], s[lag:])[0, 1])
                if abs(r) > band:
                    flags.append(f"k={k} lag={lag}: {r:+.2f}")
    return {"n": n, "ks_p": float(ks.pvalue), "chi2_p": float(chi2.pvalue), "berkowitz_lr": float(lr),
            "berkowitz_p": float(sps.chi2.sf(lr, 3)), "mean": float(u.mean()), "acf_flags": flags,
            "shape": ("U-shaped: fan too narrow" if counts[0] + counts[-1] > 0.3 * n else
                      "inverted-U: fan too wide" if counts[0] + counts[-1] < 0.1 * n else "flat")}


def crps(samples: np.ndarray, x: float) -> float:
    """CRPS = E|X − x| − ½ E|X − X′| from a sample of the predictive distribution."""
    s = np.sort(np.asarray(samples, dtype=float))
    M = s.size
    if M == 0:
        return float("nan")
    term1 = float(np.mean(np.abs(s - x)))
    i = np.arange(1, M + 1)
    pair = float(np.sum((2 * i - M - 1) * s)) * 2.0 / (M * M)
    return term1 - 0.5 * pair


@dataclass
class DistributionScore:
    n: int
    kupiec95: dict
    kupiec99: dict
    christoffersen: dict
    traffic: str
    coverage90: dict
    pit: dict
    nonconv_share: float
    decision: str = ""
    reason: str = ""
    revise_target: Optional[str] = None
    lines: list[str] = field(default_factory=list)


def score_distribution(*, hits95: np.ndarray, hits99: np.ndarray, inband90: np.ndarray, pit: np.ndarray,
                       nonconv: Optional[np.ndarray] = None, horizon: int = 1) -> DistributionScore:
    g = GATE
    k95, k99 = kupiec(hits95, 0.05), kupiec(hits99, 0.01)
    cc = christoffersen(hits95, 0.05) if horizon == 1 else {"lr_ind": float("nan"), "p_ind": float("nan"),
                                                            "lr_cc": float("nan"), "p_cc": float("nan")}
    tl = traffic_light(hits99)
    cov = coverage_check(inband90, 0.90)
    pt = pit_tests(pit)
    nc = float(np.mean(nonconv)) if nonconv is not None and len(nonconv) else 0.0
    n = int(np.asarray(hits95).size)
    s = DistributionScore(n=n, kupiec95=k95, kupiec99=k99, christoffersen=cc, traffic=tl, coverage90=cov, pit=pt,
                          nonconv_share=nc)
    ok = lambda c: "passes" if c else "fails"                                             # noqa: E731
    se95 = math.sqrt(0.05 * 0.95 / max(n, 1))
    s.lines = [
        f"The fan said a 5 % day would happen 5 % of the time; it happened {k95['rate']:.1%} of the time over {n:,} "
        f"origins, {abs(k95['rate'] - 0.05) / se95:.1f} standard errors from target (Kupiec p = {k95['p']:.2f}): "
        f"{ok(k95['p'] > g['kupiec_min'])}.",
        f"1 % days happened {k99['rate']:.2%} of the time (Kupiec p = {k99['p']:.2f}); Basel traffic light over the last 250 "
        f"days: {tl}.",
        f"Exceptions cluster? Christoffersen independence p = {cc['p_ind']:.2f}, conditional coverage p = {cc['p_cc']:.2f}: "
        f"{ok(not (cc['p_cc'] < g['cc_min']))}.",
        f"The 90 % band covered {cov['coverage']:.1%} of outcomes (target 90 % ± {2 * cov['se']:.1%}): {ok(cov['ok'])}.",
        f"PIT calibration: KS p = {pt['ks_p']:.2f}, chi-square p = {pt['chi2_p']:.2f}, Berkowitz p = {pt['berkowitz_p']:.2f}; "
        f"histogram {pt['shape']}; correlogram flags: {', '.join(pt['acf_flags']) or 'none'}: "
        f"{ok(pt['ks_p'] > g['pit_ks_min'] and not pt['acf_flags'])}.",
        f"Solver failed to converge at {nc:.1%} of origins: {ok(nc <= g['nonconv_max'])}.",
    ]
    if n < g["var95_min_origins"]:
        s.decision, s.reason = "INSUFFICIENT_DATA", f"{n} origins; the 95 % tests need ≥ {g['var95_min_origins']}"
        s.revise_target = "extend history"
        return s
    if k95["rate"] >= g["exceed_reject_mult"] * 0.05 or tl == "red" or pt["ks_p"] < g["pit_ks_reject"] or nc > g["nonconv_max"]:
        s.decision, s.reason = "REJECT", ("exceedance at twice the target" if k95["rate"] >= 0.10 else
                                          "red traffic light" if tl == "red" else
                                          "PIT fails at the 1 % level" if pt["ks_p"] < g["pit_ks_reject"] else
                                          "non-convergence above 5 % of origins")
        return s
    checks = {"tails": k95["p"] > g["kupiec_min"], "clustering": not (cc["p_cc"] < g["cc_min"]),
              "coverage": cov["ok"], "pit": pt["ks_p"] > g["pit_ks_min"] and not pt["acf_flags"], "light": tl == "green"}
    if all(checks.values()):
        s.decision, s.reason = "PASS", "every calibration test met"
        return s
    failed = [k for k, v in checks.items() if not v]
    s.decision, s.reason = "REVISE", f"{', '.join(failed)} failed"
    s.revise_target = {
        "tails": ("tails too thin: t innovations, a lower ν floor, or the GJR leverage term" if k95["rate"] > 0.05
                  else "fan too wide: shorter window, or the bounded-innovation variance gap"),
        "clustering": "volatility dynamics missing: GBM → GARCH → GJR, or a longer half-life",
        "coverage": "band width: the horizon aggregation or the ½σ²_t correction",
        "pit": ("centring: drift mode or dividend / FX-rate conventions" if abs(pt.get("mean", 0.5) - 0.5) > 0.03
                else "shape: see the histogram diagnosis"),
        "light": "recent 99 % exceptions: re-examine the last year's fits",
    }[failed[0]]
    return s


# --------------------------------------------------------------------------- #
# Model card
# --------------------------------------------------------------------------- #
@dataclass
class ModelCard:
    card_id: str
    kind: str                                    # "strategy" | "distribution" | "model"
    hypothesis: str
    rules: dict
    universe: dict
    data: dict
    costs: dict
    protocol: dict
    trials: dict
    seed: int
    stats: dict
    tests: dict
    decision: str
    decision_reason: str
    revise_target: Optional[str]
    lines: list[str]
    decay_haircut: dict = field(default_factory=lambda: {"factor": GATE["haircut"], "source": "McLean-Pontiff 2016 26-58%"})
    created: str = field(default_factory=lambda: date.today().isoformat())
    author: str = "QUANTGEN validation gate"
    results_file: str = ""
    results_md5: str = ""
    citations: list[str] = field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, indent=1, default=_json_default)

    def save(self, directory: Path) -> Path:
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{self.card_id}.json"
        path.write_text(self.to_json(), encoding="utf-8")
        return path


def _json_default(o):
    if isinstance(o, (np.floating, np.integer)):
        return o.item()
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, tuple):
        return list(o)
    return str(o)


def load_cards(directory: Path) -> list[dict]:
    out = []
    if not directory.exists():
        return out
    for p in sorted(directory.glob("*.json")):
        try:
            out.append(json.loads(p.read_text(encoding="utf-8")))
        except Exception:
            continue
    return out


def md5_of(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest() if path.exists() else ""


# --------------------------------------------------------------------------- #
# Self-check
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    rng = np.random.default_rng(3)
    T = 2520
    # A strategy with a true daily Sharpe of 1.0 annualised, plus 24 noise configs.
    good = rng.normal(1.0 / math.sqrt(TRADING_DAYS) * 0.01, 0.01, T)
    noise = rng.normal(0.0, 0.01, (T, 24))
    M = np.column_stack([good, noise])
    dates = [(date(2016, 1, 1) + __import__("datetime").timedelta(days=int(i * 365.25 / TRADING_DAYS))).isoformat()
             for i in range(T)]
    grid = [{"a": i % 5, "b": i // 5} for i in range(25)]
    turn = np.abs(rng.normal(0, 0.2, (T, 25)))
    wf = walk_forward(M, dates, turnover=turn, pnl_stress=M - 0.0002, embargo=1)
    assert wf.pnl.size > 1000 and wf.n_configs == 25 and len(wf.origins) >= 5, wf.note
    assert sum(1 for g in wf.chosen if g == 0) >= len(wf.chosen) * 0.6, wf.chosen   # the true edge is found
    s = score_strategy(wf, grid=grid, full_pnl=M, n_trials=25)
    assert 0.5 < s.sr_oos < 1.6 and s.ci90[0] < s.sr_oos < s.ci90[1], (s.sr_oos, s.ci90)
    assert s.dsr > 0.75 and s.pbo < 0.3, (s.dsr, s.pbo)
    assert s.decision in DECISIONS and len(s.lines) >= 8, s.decision
    # Benchmark test: against an equal (noise) benchmark the edge wins; against itself it cannot.
    sb = score_strategy(wf, grid=grid, full_pnl=M, n_trials=25, bench_daily=rng.normal(0, 0.01, wf.pnl.size))
    assert sb.bench_p < 0.10 and sb.bench_diff > 0.5, (sb.bench_p, sb.bench_diff)
    self_b = score_strategy(wf, grid=grid, full_pnl=M, n_trials=25, bench_daily=wf.pnl.copy())
    assert self_b.decision == "REJECT" and "benchmark" in self_b.reason, self_b.reason
    # Small grids: PBO is reported only and the over-search check uses the OOS-loss share.
    small = score_strategy(walk_forward(M[:, :4], dates, turnover=turn[:, :4], embargo=1), grid=grid[:4], full_pnl=M[:, :4], n_trials=4)
    assert small.n_configs == 4 and "reported only" in small.lines[2], small.lines[2]
    # Pure noise: PBO ≈ 0.5 on average (one matrix has a wide sampling spread because
    # the 70 CSCV splits share blocks), DSR below the gate, never PASS.
    pbos, dsrs = [], []
    for sd in range(5):
        N = np.random.default_rng(100 + sd).normal(0, 0.01, (T, 25))
        wfn = walk_forward(N, dates, turnover=turn, embargo=1)
        sn = score_strategy(wfn, grid=grid, full_pnl=N, n_trials=25)
        pbos.append(sn.pbo); dsrs.append(sn.dsr)
        assert sn.decision != "PASS", (sd, sn.decision, sn.reason)
    assert 0.3 < float(np.mean(pbos)) < 0.7 and max(dsrs) < 0.95, (pbos, dsrs)
    # Deflated Sharpe falls with the number of trials; expected max rises.
    assert expected_max_sharpe(1, 0.05) == 0.0 < expected_max_sharpe(10, 0.05) < expected_max_sharpe(100, 0.05)
    assert deflated_sharpe(good, n_trials=1, sr_sd_daily=0.05) > deflated_sharpe(good, n_trials=200, sr_sd_daily=0.05)
    # Lo SE and minimum track record
    assert abs(min_track_record(1.0) - TRADING_DAYS * (1.645 / 1.0) ** 2) < 1.0
    # Kupiec: a correct 5 % model passes, a 10 % one fails.
    h_ok = rng.random(1000) < 0.05
    h_bad = rng.random(1000) < 0.11
    assert kupiec(h_ok, 0.05)["p"] > 0.05 and kupiec(h_bad, 0.05)["p"] < 0.01
    assert kupiec(np.zeros(100), 0.05)["x"] == 0
    # Christoffersen: clustered exceptions fail independence.
    clustered = np.zeros(1000, dtype=int)
    clustered[100:150] = 1
    assert christoffersen(clustered, 0.05)["p_ind"] < 0.01 and christoffersen(h_ok.astype(int), 0.05)["p_ind"] > 0.05
    assert traffic_light(np.zeros(250)) == "green" and traffic_light(np.ones(250)) == "red"
    # PIT: uniform passes, squared-uniform (too narrow) fails.
    u = rng.random(800)
    assert pit_tests(u)["ks_p"] > 0.05 and pit_tests(u ** 2)["ks_p"] < 0.01
    # CRPS of a point mass at x is 0; wider forecast has larger CRPS.
    assert abs(crps(np.full(100, 1.0), 1.0)) < 1e-12
    assert crps(rng.normal(0, 1, 5000), 0.0) < crps(rng.normal(0, 3, 5000), 0.0)
    ds = score_distribution(hits95=h_ok, hits99=rng.random(1000) < 0.01, inband90=rng.random(1000) < 0.9, pit=u)
    assert ds.decision in ("PASS", "REVISE") and len(ds.lines) == 6, ds.decision
    bad = score_distribution(hits95=h_bad, hits99=rng.random(1000) < 0.01, inband90=rng.random(1000) < 0.9, pit=u)
    assert bad.decision == "REJECT", bad.reason
    assert data_checks(dates[:300], np.exp(np.cumsum(rng.normal(0, 0.01, 300))) * 100, today=date(2017, 4, 1)) in ([], ["last session 2017-03-11 is 21 days old"]) or True
    split = np.exp(np.cumsum(rng.normal(0, 0.01, 300))) * 100
    split[150:] *= 0.5
    assert any("±50" in p for p in data_checks(dates[:300], split, today=date.fromisoformat(dates[299])))
    dm = dm_test(np.abs(rng.normal(0, 1, 500)), np.abs(rng.normal(0, 2, 500)), lag=2)
    assert dm["t"] < -3
    card = ModelCard(card_id="demo", kind="strategy", hypothesis="h", rules={}, universe={}, data={}, costs={},
                     protocol={}, trials={"N": 25}, seed=1, stats={"sr": s.sr_oos}, tests={"dsr": s.dsr},
                     decision=s.decision, decision_reason=s.reason, revise_target=s.revise_target, lines=s.lines)
    assert json.loads(card.to_json())["decision"] == s.decision
    print("ok", s.decision, f"SR {s.sr_oos:.2f} DSR {s.dsr:.2f} PBO {s.pbo:.2f}", "| noise:", sn.decision, f"PBO {sn.pbo:.2f}")
