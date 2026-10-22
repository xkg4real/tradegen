"""Tech-fund governance amendments GOV-1..GOV-11 (R3 section 5.6; register G-15..G-25) and the INV-1 bound line.

Rulings 3.7 / 3.8: the tech-fund cards are CARD-O cards under the existing nine-step gate and these amendments are
*tightenings or report lines only*; nothing here changes an acting parameter of the macro package or feeds a book.
Values the R3 programme proposes (the factor-tilt threshold, the planning haircuts, the beta_hat window) are labelled
proposals pending owner confirmation; where tech-fund and Council differ, Council v2.0 governs (D-01, D-16).
Lab numbers are reference constants with file + line (`REFERENCE`), never recomputed from absent raw data.

- GOV-1  `primary_statistic`: long-only net excess vs the same-universe EW benchmark; capped VW reported (sign split
         -> REVISE); L/S a diagnostic; the short leg's share of L/S profit.
- GOV-2  `spa_test` (Hansen 2005 SPA, studentised, stationary bootstrap, lower / consistent / upper p plus White's RC;
         ported, no `arch`), `bh_fdr` (q 0.10 per release, reported), `holm` (displayed cards), `family_gate`
         (consistent p <= 0.05 at 1x, BH survivors, persistence >= 60% of windows), `trial_registry` (append-only
         family ledgers of R-23 with the global N; a k-of-n composite counts n^k).
- GOV-3  `attribution_block` (beta, Jensen alpha with Newey-West t, factor alpha, 'factor tilt' label);
         `ledoit_wolf_sharpe_test` (R-24 studentised bootstrap at the GOV-4 block).
- GOV-4  `pw_block_dd2(d, holding)` = max(10, PW(d), PW(d^2), 2 x holding) on `gate_stats.pw_block`.
- GOV-5  min-track-record line: `validate.min_track_record` (the existing INSUFFICIENT_DATA route is unchanged, D-17).
- GOV-6  `expected_live` = 0.6 x OOS (one multiplier, `gate_stats.LIVE_SHARPE_MULTIPLIER`); `step8_subperiods`.
- GOV-7  `break_even_screen` (pre-gate REJECT if break-even < 2 x the pre-registered cost) on `tf_books.break_even_bps`.
- GOV-8  `PLANNING_HAIRCUTS` + `planning_haircuts(council)`: a labelled proposal printed beside the Council's
         `prior_haircuts`, which govern.
- GOV-9  `stress_table` (fixed windows incl. the 2026-06-22..07-30 replay; worst rolling 21 / 63 / 25-session relative).
- GOV-10 `contamination_log` (append-only, chained) + `incubation` (>= 252 sessions from the first recorded session,
         never back-filled).
- GOV-11 `s_beta_book` = beta_hat x market + (1 - beta_hat) x cash with `beta_hat` = OLS daily beta over the prior
         252 sessions (OQ-03 reading), frozen in the header.
- INV-1  `inv1_bound_line`: decide at close t, earn from t+1 (the costed engine) and the close t+1 bound line (D-09).

Pure numpy / scipy; seeds, B and blocks are parameters; no clock, no data read, no `validate.GATE` read.
"""
from __future__ import annotations

import math
from datetime import date
from pathlib import Path
from typing import Mapping, Optional, Sequence

import numpy as np

from core.quant import costed as C
from core.quant import gate_ledger as GL
from core.quant import gate_stats as GS
from core.quant import validate as V
from core.quant.tf_books import break_even_bps   # one home (package B); re-exported here for GOV-7
from core.quant.validate import TRADING_DAYS

# --------------------------------------------------------------------------- #
# Constants (proposals labelled; Council governs on conflict)
# --------------------------------------------------------------------------- #
BLOCK_FLOOR = 10                       # GOV-4 (R3:296): never a block below 10 sessions
NW_LAG = 10                            # daily Newey-West lags (labs K05 247; tf_algorithms A.7)
FACTOR_TILT_T = 2.0                    # GOV-3 label threshold: PROPOSAL (OQ-15 / D-19), owner to fix; display only
FACTOR_TILT_STATUS = "proposal pending owner confirmation (OQ-15); display only, never changes a verdict (D-19)"
FACTOR_SETS = {"US": ("MKT", "SMB", "HML", "RMW", "CMA", "UMD"),               # FF5 + UMD (P:L609)
               "KR": ("MKT", "SMB", "HML", "RMWq", "CMA", "UMD", "SEMI")}      # local set + Samsung/SK hynix SEMI
BENCHMARK_SET_KRX = ("EW", "CW", "CW_ex_pair", "capped_CW")                    # GOV-1 (R3:812): added, never removed
SPA_B = 2000                           # family gate: >= 2,000 stationary-bootstrap resamples (P:L606)
SPA_BLOCK = 15                         # the labs' mean block (tf_algorithms B.12)
FAMILY_SPA_P_MAX = 0.05                # consistent p at 1x costs (chair override of P2's 0.10)
FDR_Q = 0.10                           # BH per release (P:L608)
PERSISTENCE_MIN = 0.60                 # positive OOS net excess in >= 60% of walk-forward windows (P:L606)
BREAK_EVEN_MULTIPLE = 2.0              # GOV-7: reject before the gate if break-even < 2 x cost (R3:818)
BETA_WINDOW = 252                      # GOV-11 beta_hat window: OQ-03 proposal (prior 252 sessions, frozen)
INCUBATION_START = date(2026, 10, 1)   # GOV-10 clock (R3:821; D-23: the macro holdout 2027-01-01 is a separate clock)
INCUBATION_MIN_SESSIONS = 252
MAX_RECORD_LAG_DAYS = 3                # reading: a row written > 3 calendar days after its session is a back-fill
LIVE_MULTIPLIER = GS.LIVE_SHARPE_MULTIPLIER    # GOV-6 step 9: expected live = 0.6 x OOS (CA-21; GV-523)
PLANNING_HAIRCUTS = {"in_sample": 0.5, "post_publication": 0.3, "drift_like": 0.75}   # GOV-8 (R3:819)
PLANNING_HAIRCUTS_LABEL = ("tech-fund planning haircuts (GOV-8, PX-T-10): a labelled PROPOSAL, display only; the Council "
                           "store's prior_haircuts govern (rulings 3.7, D-16); replaced by measured local decay where "
                           "20+ years of data exist")
STEP8_STANDALONE_NOTE = ("step 8 alone passes 23.8% (KOSPI bootstrap, GV-451) / 31.2% (sign-flip, GV-453) / 29.5% (iid, "
                         "GV-455) of zero-Sharpe strategies at 10 years; reported beside 2-of-3 subperiods (PX-T-05)")
YEARS_POS_MIN = 0.60                   # step 8 unchanged (GOV-6): >= 60% of calendar years positive
SUBPERIODS_KRX =(("1996-2005", "1996-01-01", "2005-12-31"), ("2006-2015", "2006-01-01", "2015-12-31"),
                  ("2016-2026", "2016-01-01", "2026-12-31"))                      # P:L644; lab SUB3
# GOV-9 windows (D-27): the lab sets scr:r2_kr_common.py:54-67, convention start_close < d <= end_close.
STRESS_WINDOWS = (("2008-06..2009-03 GFC", "2008-05-31", "2009-03-31"),
                  ("2009-03..2009-05 post-GFC rebound", "2009-02-27", "2009-05-29"),
                  ("2020-02-17..03-19 COVID crash", "2020-02-17", "2020-03-19"),
                  ("2020-03-20..06-30 COVID rebound", "2020-03-19", "2020-06-30"),
                  ("2022 full year", "2021-12-31", "2022-12-31"),
                  ("2026-01-02..06-22 melt-up", "2025-12-31", "2026-06-22"),
                  ("2026-06-22..07-30 crash", "2026-06-22", "2026-07-30"),
                  ("2026-07-31..09-29 after crash", "2026-07-30", "2026-09-29"))
ROLLING_RELATIVE = (21, 63, 25)        # GOV-9: worst rolling 21 / 63-session and 5-week (25-session) relative loss
# GOV-10 seed (R3:319): families and the span the R1/R2 labs examined.
CONTAMINATED_1996_2026 = ("MOM_12_1", "MOM_6_1", "MOM_12_7", "REV_1M", "REV_1W", "VOL_3M", "MAX_1M", "TURN_1M",
                          "HIGH52", "PRICE_SMA200", "RSI", "PCT_B", "INDEX_RULES_600")
CONTAMINATION_ROW = ("family", "start", "end", "source", "recorded_utc")

# Reference constants (lab, in sample, 1996-03..2026-09, price returns, rf 0): file + line, never recomputed.
_KR = "QUANTGEN_techfund_research_bundle/QUANTGEN_techfund_research/datalab/results/"
REFERENCE = {
    "REV_1W_EW_LS": {"gross_ann": 0.199254, "turnover_yr": 159.462, "break_even_bp": 12.495390751401589,
                     "source": _KR + "kr/kr_key_numbers.csv", "line": 30, "gv": "GV-189"},
    "MOM_12_1_EW_LS": {"gross_ann": 0.0933695, "turnover_yr": 14.6556, "break_even_bp": 63.70909413466524,
                       "source": _KR + "kr/kr_key_numbers.csv", "line": 2, "gv": "GV-192"},
    "SCR1_F4_B1": {"gross_ann": 0.0338837, "turnover_filtered": 2.78453, "turnover_unfiltered": 1.89331,
                   "break_even_bp": 380.2, "source": _KR + "r2_kr/r2_kr_excl_summary.csv", "line": 13, "gv": "GV-001"},
}


class GovRefused(ValueError):
    """A governance helper refused its input (fail closed)."""


def _a(x) -> np.ndarray:
    return np.asarray(x, dtype=float).ravel()


# --------------------------------------------------------------------------- #
# GOV-4 block length
# --------------------------------------------------------------------------- #
def pw_block_dd2(d, holding: int = 1) -> int:
    """`max(10, ceil(PW(d)), ceil(PW(d^2)), 2 x holding)` sessions (R3:296; P:L615 the 2 x holding-period floor).
    A tightening for the tech-fund CARD-O steps 2 and 5; the macro package keeps `max(21, PW(psi))` (rulings 3.7)."""
    if int(holding) < 1:
        raise GovRefused("holding period must be >= 1 session")
    return max(GS.pw_block_floor(_a(d), BLOCK_FLOOR), 2 * int(holding))


# --------------------------------------------------------------------------- #
# GOV-3 attribution block
# --------------------------------------------------------------------------- #
def _ols_nw(y: np.ndarray, X: np.ndarray, lags: int) -> tuple[np.ndarray, np.ndarray]:
    """OLS with an intercept and Bartlett Newey-West covariance (labs `ols_nw`, tf_algorithms B.8): (coef, t)."""
    X = np.column_stack([np.ones(y.size), X])
    inv = np.linalg.inv(X.T @ X)
    coef = inv @ X.T @ y
    g = X * (y - X @ coef)[:, None]
    S = g.T @ g
    for lag in range(1, int(lags) + 1):
        G = g[lag:].T @ g[:-lag]
        S += (1.0 - lag / (lags + 1.0)) * (G + G.T)
    se = np.sqrt(np.diag(inv @ S @ inv))
    return coef, np.where(se > 0, coef / np.where(se > 0, se, 1.0), np.nan)


def attribution_block(returns, factors, benchmark, *, factor_names: Optional[Sequence[str]] = None,
                      nw_lag: int = NW_LAG, threshold: float = FACTOR_TILT_T, periods: int = TRADING_DAYS) -> dict:
    """GOV-3 (R3:282; P:L609): beta and Jensen's alpha on the declared benchmark (Newey-West t), the alpha left after
    the factor set (FF5+UMD for US, MKT SMB HML RMWq CMA UMD + SEMI for KRX), and the label. `factor tilt` = CAPM
    alpha significant but factor alpha not (PC-T-01). `factors` is None (not supplied: typed null), a (T, F) array or
    {name: series}. Alphas are annualised by `periods`. Display only: never changes a verdict (D-19)."""
    y, m = _a(returns), _a(benchmark)
    if y.size != m.size or y.size < 30 or not (np.isfinite(y).all() and np.isfinite(m).all()):
        raise GovRefused("attribution needs >= 30 finite returns aligned with the benchmark")
    coef, t = _ols_nw(y, m[:, None], nw_lag)
    out = {"beta": float(coef[1]), "jensen_alpha": float(coef[0] * periods), "nw_t": float(t[0]),
           "factor_alpha": None, "factor_alpha_t": None, "factor_loadings": None, "factor_tilt": None,
           "threshold_t": float(threshold), "threshold_status": FACTOR_TILT_STATUS, "nw_lag": int(nw_lag),
           "T": int(y.size), "nulls": {}}
    capm_sig = out["nw_t"] >= threshold
    if factors is None:
        out["nulls"]["factor_alpha"] = "REFDATA: factor returns not supplied (French / local KRX factor files absent)"
        out["label"] = "alpha (CAPM only; factor attribution not run)" if capm_sig else "no alpha (CAPM only)"
        return out
    if isinstance(factors, Mapping):
        factor_names = list(factors)
        F = np.column_stack([_a(factors[k]) for k in factor_names])
    else:
        F = np.asarray(factors, dtype=float)
        F = F[:, None] if F.ndim == 1 else F
        factor_names = list(factor_names or [f"f{i + 1}" for i in range(F.shape[1])])
    if F.shape[0] != y.size or not np.isfinite(F).all():
        raise GovRefused("factor returns must be finite and aligned with the card returns")
    fc, ft = _ols_nw(y, F, nw_lag)
    out.update(factor_alpha=float(fc[0] * periods), factor_alpha_t=float(ft[0]),
               factor_loadings={n: float(b) for n, b in zip(factor_names, fc[1:])})
    factor_sig = out["factor_alpha_t"] >= threshold
    out["factor_tilt"] = bool(capm_sig and not factor_sig)
    out["label"] = "alpha" if factor_sig else ("factor tilt" if capm_sig else "no alpha")
    return out


def ledoit_wolf_sharpe_test(a, b, B: int = GS.B_DEFAULT, seed: int = GS.SEED_STUDY, *, holding: int = 1,
                            block: Optional[int] = None) -> dict:
    """GOV-3 Sharpe difference (P:L609): the R-24 Ledoit-Wolf studentised circular-block bootstrap of SR(a) - SR(b),
    one-sided H0 dSR <= 0, at the GOV-4 block of the difference series unless `block` is given. Adds `p` (numeric)."""
    blk = int(block) if block is not None else pw_block_dd2(_a(a) - _a(b), holding)
    out = GS.lw_studentized_boot(a, b, blk, B, seed, null=0.0)
    out["p"] = GS.p_numeric(out["p_lw"], B)
    return out


# --------------------------------------------------------------------------- #
# GOV-1 primary statistic
# --------------------------------------------------------------------------- #
def _excess_line(x: np.ndarray, nw_lag: int) -> dict:
    sd = float(np.std(x, ddof=1))
    return {"ann": float(np.mean(x) * TRADING_DAYS), "ir": float(np.mean(x) / sd * math.sqrt(TRADING_DAYS)) if sd > 0 else float("nan"),
            "nw_t": float(V.newey_west_t(x, nw_lag)), "T": int(x.size)}


def primary_statistic(long_only, benchmarks: Mapping[str, Sequence[float]], *, long_short=None, short_leg=None,
                      nw_lag: int = NW_LAG) -> dict:
    """GOV-1 (P:L610; R3:812): the primary statistic is the long-only daily net excess over the same-universe EW
    benchmark; the capped value-weighted excess is reported beside it and a sign split caps the card at REVISE;
    every other declared benchmark (CW, CW ex-pair) is printed. Long-short is a diagnostic; `short_leg` (the return
    of the basket held short) gives the short leg's share of L/S profit = mean(-short) / mean(L/S)."""
    lo = _a(long_only)
    missing = [k for k in ("EW", "capped_CW") if k not in benchmarks]
    if missing:
        raise GovRefused(f"primary statistic needs the pre-registered benchmarks {missing} (GOV-1)")
    lines = {}
    for name, bench in benchmarks.items():
        b = _a(bench)
        if b.size != lo.size or not (np.isfinite(b).all() and np.isfinite(lo).all()):
            raise GovRefused(f"benchmark {name!r} is not aligned with the long-only book")
        lines[name] = _excess_line(lo - b, nw_lag)
    ew, cap = lines["EW"]["ann"], lines["capped_CW"]["ann"]
    split = bool(ew * cap < 0)
    out = {"primary": "long_only_net_excess_vs_EW", "vs": lines, "sign_split_ew_capped": split,
           "verdict_cap": "REVISE" if split else None, "long_short": None, "short_leg_share": None}
    if long_short is not None:
        ls = _a(long_short)
        sd = float(np.std(ls, ddof=1))
        out["long_short"] = {"role": "diagnostic only", "ann": float(np.mean(ls) * TRADING_DAYS),
                             "sharpe": float(np.mean(ls) / sd * math.sqrt(TRADING_DAYS)) if sd > 0 else float("nan")}
        if short_leg is not None:
            mls = float(np.mean(ls))
            out["short_leg_share"] = float(np.mean(-_a(short_leg)) / mls) if mls != 0 else None
    return out


# --------------------------------------------------------------------------- #
# GOV-2 multiplicity: SPA / RC, BH, Holm, family gate, trial registry
# --------------------------------------------------------------------------- #
def _sb_variance(d: np.ndarray, block: float) -> np.ndarray:
    """Variance of sqrt(T) x mean per column under the stationary bootstrap (Politis-Romano kernel; the form `arch`
    uses for a studentised SPA): gamma_0 + 2 sum_i kappa_i gamma_i, autocovariances by FFT."""
    T = d.shape[0]
    dm = d - d.mean(axis=0)
    n = 1 << (2 * T - 1).bit_length()
    f = np.fft.rfft(dm, n=n, axis=0)
    acov = np.fft.irfft(f * np.conj(f), n=n, axis=0)[:T] / T
    p = 1.0 / float(block)
    i = np.arange(1, T)
    kappa = (1.0 - i / T) * (1.0 - p) ** i + (i / T) * (1.0 - p) ** (T - i)
    return acov[0] + 2.0 * (kappa[:, None] * acov[1:]).sum(axis=0)


def _boot_means(d: np.ndarray, idx: np.ndarray, chunk: int = 256) -> np.ndarray:
    """(B, K) resample means without materialising (B, T, K): per-chunk index counts times d."""
    B, T = idx.shape
    out = np.empty((B, d.shape[1]))
    for s in range(0, B, chunk):
        rows = idx[s:s + chunk]
        flat = (rows + (np.arange(rows.shape[0]) * T)[:, None]).ravel()
        counts = np.bincount(flat, minlength=rows.shape[0] * T).reshape(rows.shape[0], T)
        out[s:s + chunk] = counts @ d / T
    return out


def spa_test(losses_benchmark, losses_rules, B: int = SPA_B, block: float = SPA_BLOCK, seed: int = GS.SEED_STUDY) -> dict:
    """GOV-2 family test: Hansen (2005) Superior Predictive Ability, H0 "no rule has a lower expected loss than the
    benchmark", d_k = L_bench - L_rule_k (> 0: the rule is better). Studentised with the stationary-bootstrap kernel
    variance; stationary bootstrap of mean block `block` (gate_stats.block_indices). Returns the lower / consistent /
    upper p, the naive (unstudentised) consistent p (what `arch 8.0.0` prints, tf_algorithms ambiguity 9), White's
    Reality Check p (naive, upper), and per-rule one-sided bootstrap p-values from the same draws (for BH / Holm).
    The gate reads `p_consistent` (<= 0.05 at 1x costs, P:L606)."""
    Lb = _a(losses_benchmark)
    Lm = np.asarray(losses_rules, dtype=float)
    Lm = Lm[:, None] if Lm.ndim == 1 else Lm
    if Lm.shape[0] != Lb.size or Lb.size < 20 or not (np.isfinite(Lb).all() and np.isfinite(Lm).all()):
        raise GovRefused("spa_test needs >= 20 finite aligned losses: benchmark (T,), rules (T, K)")
    d = Lb[:, None] - Lm
    T, K = d.shape
    dbar = d.mean(axis=0)
    omega = np.sqrt(np.maximum(_sb_variance(d, block), 0.0))
    omega = np.where(omega > 0, omega, np.inf)                   # a degenerate rule (d constant) never drives the max
    means = _boot_means(d, GS.block_indices(T, max(1, int(round(block))), int(B), seed, "stationary"))
    rt = math.sqrt(T)
    thresh = -np.sqrt(omega ** 2 / T * 2.0 * math.log(math.log(T)))
    centre = {"lower": np.maximum(dbar, 0.0), "consistent": dbar * (dbar >= thresh), "upper": dbar}

    def p_of(stat_obs: float, z: np.ndarray, scale) -> float:
        boot = np.maximum(np.max(rt * z / scale, axis=1), 0.0)
        return float(np.mean(boot > stat_obs))

    t_stud = max(float(np.max(rt * dbar / omega)), 0.0)
    t_naive = max(float(np.max(rt * dbar)), 0.0)
    out = {k: p_of(t_stud, means - c, omega) for k, c in centre.items()}
    rule_p = np.mean((means - dbar) >= dbar, axis=0)
    return {"p_lower": out["lower"], "p_consistent": out["consistent"], "p_upper": out["upper"],
            "p_consistent_naive": p_of(t_naive, means - centre["consistent"], 1.0),
            "p_rc": p_of(t_naive, means - dbar, 1.0), "stat": t_stud, "best": int(np.argmax(rt * dbar / omega)),
            "rule_p": rule_p, "T": int(T), "K": int(K), "B": int(B), "block": float(block), "seed": int(seed),
            "bootstrap": "stationary", "studentized": True}


def bh_fdr(pvalues, q: float = FDR_Q) -> dict:
    """Benjamini-Hochberg step-up at FDR q (q 0.10 per release, reported; P:L608): adjusted p (input order) and the
    rejection mask."""
    p = _a(pvalues)
    if p.size == 0:
        return {"adjusted": p, "rejected": np.zeros(0, bool), "q": float(q), "m": 0}
    if np.any(~np.isfinite(p)) or np.any(p < 0) or np.any(p > 1):
        raise GovRefused("p-values must lie in [0, 1]")
    m = p.size
    order = np.argsort(p, kind="stable")
    adj_sorted = np.minimum(1.0, np.minimum.accumulate((p[order] * m / np.arange(1, m + 1))[::-1])[::-1])
    adj = np.empty(m)
    adj[order] = adj_sorted
    return {"adjusted": adj, "rejected": adj <= q, "q": float(q), "m": int(m)}


holm = GS.holm_adjusted        # Holm step-down for displayed cards (P:L608); one home in gate_stats


def family_gate(family_results: Mapping) -> dict:
    """GOV-2 family gate before the nine-step gate (P:L606; F1-F3). `family_results` = {"spa": spa_test dict or its
    consistent p, "rules": {name: {"p": per-rule p, "window_excess": [OOS net excess per walk-forward window]}}}.
    SPA consistent p > 0.05 rejects the whole family (no member carried forward); otherwise the survivors are the
    BH-FDR (q 0.10) rejections whose OOS net excess is positive in >= 60% of windows."""
    spa = family_results["spa"]
    p_spa = float(spa["p_consistent"] if isinstance(spa, Mapping) else spa)
    rules = dict(family_results.get("rules") or {})
    if not p_spa <= FAMILY_SPA_P_MAX:
        return {"family_pass": False, "spa_p": p_spa, "survivors": [], "persistence": {}, "bh": None,
                "reason": f"family SPA consistent p {p_spa:.3f} > {FAMILY_SPA_P_MAX}: whole family REJECTED, no member carried forward"}
    names = list(rules)
    bh = bh_fdr([rules[n]["p"] for n in names])
    persistence = {}
    for n in names:
        w = _a(rules[n]["window_excess"])
        persistence[n] = float(np.mean(w > 0)) if w.size else 0.0
    survivors = [n for i, n in enumerate(names) if bh["rejected"][i] and persistence[n] >= PERSISTENCE_MIN]
    return {"family_pass": True, "spa_p": p_spa, "survivors": survivors, "persistence": persistence,
            "bh": {n: float(bh["adjusted"][i]) for i, n in enumerate(names)},
            "reason": f"{len(survivors)} of {len(names)} members survive BH q {FDR_Q} and persistence >= {PERSISTENCE_MIN:.0%}"}


def composite_count(n: int, k: int) -> int:
    """A composite choosing k of n signals counts n^k trials (P:L607)."""
    if int(n) < 1 or not 1 <= int(k) <= int(n):
        raise GovRefused("composite count needs 1 <= k <= n")
    return int(n) ** int(k)


def _trial_weight(row: Mapping) -> int:
    p = row.get("params") or {}
    if "composite_k" in p or "composite_n" in p:
        return composite_count(p["composite_n"], p["composite_k"])
    return 1


class TrialRegistry:
    """GOV-2 trial registry: one R-23 family ledger per family (`<dir>/<family>.jsonl`, append-only, hash-chained,
    duplicate configurations are the same trial) and the global N over every family in the directory."""

    def __init__(self, path) -> None:
        self.dir = Path(path)

    def ledger(self, family_id: str) -> GL.FamilyLedger:
        return GL.family_ledger(family_id, self.dir)

    def register(self, family_id: str, row: Mapping) -> GL.RegisterResult:
        return GL.register_trial(self.ledger(family_id), row)

    def rows(self) -> list[dict]:
        out = []
        for p in sorted(self.dir.glob("*.jsonl")) if self.dir.is_dir() else ():
            out.extend(GL.FamilyLedger(p).rows())          # a broken chain raises (fail closed)
        return out

    @property
    def n_rows(self) -> int:
        return len(self.rows())

    def global_n(self) -> int:
        """Every family member, revision and quick check counts; a k-of-n composite row counts n^k."""
        return sum(_trial_weight(r) for r in self.rows())


def trial_registry(path) -> TrialRegistry:
    return TrialRegistry(path)


# --------------------------------------------------------------------------- #
# GOV-5 / GOV-6 report lines
# --------------------------------------------------------------------------- #
def expected_live(oos: float) -> dict:
    """GOV-6 step 9 (report only): expected live = 0.6 x OOS ("take 40% off", CA-21; GV-523 is this arithmetic)."""
    v = LIVE_MULTIPLIER * float(oos)
    return {"expected_live": v, "multiplier": LIVE_MULTIPLIER,
            "line": f"step 9 (reported, not gated): expected live = {LIVE_MULTIPLIER} x OOS = {v:.4g}"}


def min_track_record_line(sr_oos: float, sessions: int, level: float = 0.90) -> dict:
    """GOV-5: the minimum track record at the existing 90% interval vs the history (the INSUFFICIENT_DATA route of
    `_decide_strategy` is unchanged; benchmark, DSR and 2x-cost failures stay REJECT, D-17)."""
    need = V.min_track_record(float(sr_oos), level)
    return {"min_trl_sessions": need if math.isfinite(need) else None, "sessions": int(sessions),
            "exceeds_history": (not math.isfinite(need)) or need > sessions}


def _dates(dates) -> np.ndarray:
    return np.array([np.datetime64(str(d)[:10], "D") for d in dates])


def step8_subperiods(daily, dates, subperiods: Optional[Sequence[tuple[str, str, str]]] = None,
                     min_sessions: int = C.MIN_YEAR_SESSIONS) -> dict:
    """GOV-6 / PX-T-05 reporter: step 8 (>= 60% of calendar years with >= 126 sessions positive, compounded) and the
    "positive in at least 2 of 3 subperiods" line (KRX: 1996-2005 / 2006-2015 / 2016-2026; None = equal calendar
    thirds of the span). Reported, never gated here; a subperiod without sessions makes the 2-of-3 line None."""
    x, d = _a(daily), _dates(dates)
    years = C.calendar_years(x, d, min_sessions)
    share = float(np.mean([v > 0 for v in years.values()])) if years else float("nan")
    if subperiods is None:
        lo, hi = d.min(), d.max()
        c = [lo, lo + (hi - lo) // 3, lo + 2 * (hi - lo) // 3, hi]
        subperiods = tuple((f"third {i + 1}", str(c[i] + (i > 0)), str(c[i + 1])) for i in range(3))
    rows = []
    for name, s, e in subperiods:
        m = (d >= np.datetime64(s, "D")) & (d <= np.datetime64(e, "D"))
        rows.append({"name": name, "start": s, "end": e, "sessions": int(m.sum()),
                     "compounded": float(np.expm1(np.log1p(x[m]).sum())) if m.any() else None})
    defined = [r["compounded"] for r in rows if r["compounded"] is not None]
    two_of_three = (sum(v > 0 for v in defined) >= 2) if len(defined) == len(rows) else None
    return {"years_positive": share, "n_years": len(years), "step8_pass": bool(share >= YEARS_POS_MIN),
            "subperiods": rows, "two_of_three": two_of_three, "standalone_note": STEP8_STANDALONE_NOTE,
            "status": "reported, not gated (GOV-6; owner may add 2-of-3 as a tightening, OQ-04)"}


# --------------------------------------------------------------------------- #
# GOV-7 break-even pre-gate screen
# --------------------------------------------------------------------------- #
def break_even_screen(gross_ann: float, turnover: float, cost_bp: float) -> dict:
    """GOV-7 (R3:818): reject BEFORE the gate (no gate trial spent) when break-even < 2 x the pre-registered cost per
    side. Break-even = gross / turnover charged per side (signals: L/S gross / both legs; screens: gross difference
    / extra turnover; `tf_books.break_even_bps`, which refuses a non-positive turnover). The charged cost stays the
    flat table rate; an itemised total may only raise it (D-28)."""
    be = break_even_bps(gross_ann, turnover)
    thr = BREAK_EVEN_MULTIPLE * float(cost_bp)
    reject = be < thr
    return {"break_even_bp": be, "cost_bp": float(cost_bp), "threshold_bp": thr, "stage": "pre-gate",
            "verdict": "REJECT" if reject else "PROCEED",
            "reason": (f"break-even {be:.1f} bp/side < 2 x {cost_bp:g} bp: rejected before the gate" if reject
                       else f"break-even {be:.1f} bp/side >= 2 x {cost_bp:g} bp: proceeds to the gate")}


def planning_haircuts(council: Optional[Mapping] = None) -> dict:
    """GOV-8 display block: the tech-fund planning haircuts beside the Council `prior_haircuts` (pass
    `store.get("prior_haircuts")`); the Council values govern and neither touches exposure (D-16)."""
    return {"proposal": dict(PLANNING_HAIRCUTS), "label": PLANNING_HAIRCUTS_LABEL,
            "council_prior_haircuts": dict(council) if council is not None else None, "governs": "council"}


# --------------------------------------------------------------------------- #
# GOV-9 stress table
# --------------------------------------------------------------------------- #
def stress_table(series, dates, *, benchmark=None, windows: Sequence[tuple[str, str, str]] = STRESS_WINDOWS) -> dict:
    """GOV-9 (R3:820; reporting only, no pass/fail): compounded return of the card (and benchmark, relative = ratio
    of growth - 1) over each fixed window (start_close < d <= end_close), and the worst rolling 21 / 63-session and
    5-week (25-session) relative loss. A window with no sessions in the data prints None."""
    x, d = _a(series), _dates(dates)
    b = _a(benchmark) if benchmark is not None else np.zeros_like(x)
    if b.size != x.size or d.size != x.size:
        raise GovRefused("stress table: series, benchmark and dates must align")
    rows = []
    for name, s, e in windows:
        m = C.window_mask(d, date.fromisoformat(s), date.fromisoformat(e))
        if not m.any():
            rows.append({"name": name, "start": s, "end": e, "sessions": 0, "book": None, "benchmark": None, "relative": None})
            continue
        gb, gm = float(np.prod(1 + x[m])), float(np.prod(1 + b[m]))
        rows.append({"name": name, "start": s, "end": e, "sessions": int(m.sum()), "book": gb - 1,
                     "benchmark": gm - 1 if benchmark is not None else None, "relative": gb / gm - 1})
    rel = np.log1p(x) - np.log1p(b)
    worst = {}
    for k in ROLLING_RELATIVE:
        if rel.size < k:
            worst[str(k)] = None
            continue
        c = np.concatenate([[0.0], np.cumsum(rel)])
        worst[str(k)] = float(np.expm1(np.min(c[k:] - c[:-k])))
    return {"windows": rows, "worst_rolling_relative": worst, "reporting_only": True,
            "relative_to": "benchmark" if benchmark is not None else "cash (zero)"}


# --------------------------------------------------------------------------- #
# GOV-10 contamination log and incubation
# --------------------------------------------------------------------------- #
class ContaminationLog:
    """Append-only, chained log (`cards.chain_append`) of every family and date range the labs examined; for those
    the historical holdout is used up and only prospective incubation is a clean test (R3:821)."""

    def __init__(self, path) -> None:
        self.path = Path(path)

    def rows(self) -> list[dict]:
        from core.quant import cards                      # lazy: the card module pulls the schema / rules stack
        return cards.read_chain(self.path, CONTAMINATION_ROW) if self.path.exists() else []

    def append(self, family: str, start: str, end: str, source: str, recorded_utc: str) -> str:
        from core.quant import cards
        s, e = date.fromisoformat(start), date.fromisoformat(end)
        if s > e or not family or not source:
            raise GovRefused("contamination row needs a family, a source and start <= end")
        GL.parse_utc(recorded_utc)
        self.rows()                                       # refuses to append to a broken chain
        return cards.chain_append(self.path, {"family": family, "start": str(s), "end": str(e), "source": source,
                                              "recorded_utc": recorded_utc})

    def seed(self, recorded_utc: str) -> int:
        """Append the R3:319 list (1996-01-01..2026-09-30, R1/R2 labs) once; returns the rows added."""
        have = {(r["family"], r["source"]) for r in self.rows()}
        src = "R1/R2 data labs (R3:319)"
        new = [f for f in CONTAMINATED_1996_2026 if (f, src) not in have]
        for f in new:
            self.append(f, "1996-01-01", "2026-09-30", src, recorded_utc)
        return len(new)

    def contaminated(self, family: str, start: str, end: str) -> list[dict]:
        s, e = date.fromisoformat(start), date.fromisoformat(end)
        return [r for r in self.rows() if r["family"] == family
                and date.fromisoformat(r["start"]) <= e and s <= date.fromisoformat(r["end"])]


def contamination_log(path) -> ContaminationLog:
    return ContaminationLog(path)


def incubation(record, *, start: date = INCUBATION_START, min_sessions: int = INCUBATION_MIN_SESSIONS,
               max_record_lag_days: int = MAX_RECORD_LAG_DAYS) -> dict:
    """GOV-10 incubation (R3:821): >= 252 sessions counted from the first recorded session, never back-filled.
    `record` = rows (or {"rows": rows}) in append order, each {"session": ISO date, "recorded_utc": ISO instant}.
    A row is not counted when its session precedes the clock start (2026-10-01) or the last counted session, when it
    was recorded before its own session, or when it was recorded more than `max_record_lag_days` after it (a
    back-fill). The first counted row fixes the first recorded session; nothing before it ever counts."""
    rows = record["rows"] if isinstance(record, Mapping) else record
    counted: list[date] = []
    excluded = []
    for r in rows:
        s = date.fromisoformat(str(r["session"])[:10])
        lag = (GL.parse_utc(r["recorded_utc"]).date() - s).days
        why = ("before the incubation start" if s < start else
               "recorded before its session" if lag < 0 else
               "back-filled (recorded after the session)" if lag > max_record_lag_days else
               "at or before the last counted session" if counted and s <= counted[-1] else None)
        if why:
            excluded.append({"session": str(s), "reason": why})
        else:
            counted.append(s)
    return {"start_rule": str(start), "first_recorded_session": str(counted[0]) if counted else None,
            "sessions": len(counted), "min_sessions": int(min_sessions), "complete": len(counted) >= min_sessions,
            "excluded": excluded}


# --------------------------------------------------------------------------- #
# GOV-11 S_beta comparator
# --------------------------------------------------------------------------- #
def beta_hat(book, market, formation: int, window: int = BETA_WINDOW) -> float:
    """OLS daily beta of the book on the declared market over the `window` sessions BEFORE `formation`
    (rows formation-window .. formation-1); frozen in the header at formation (OQ-03 reading, a proposal)."""
    y, m = _a(book), _a(market)
    f, w = int(formation), int(window)
    if f - w < 0 or f > y.size or y.size != m.size:
        raise GovRefused(f"beta_hat needs {w} sessions before formation {f}")
    yy, mm = y[f - w:f], m[f - w:f]
    var = float(np.var(mm, ddof=1))
    if not (np.isfinite(yy).all() and np.isfinite(mm).all()) or var <= 0:
        raise GovRefused("beta_hat window has non-finite returns or no market variance")
    return float(np.cov(yy, mm, ddof=1)[0, 1] / var)


def s_beta_book(market, cash, beta_hat: float) -> np.ndarray:
    """GOV-11 / CR-01: S_beta = beta_hat x market + (1 - beta_hat) x cash, a static comparator for stock-level
    sleeves (FS-3, descriptive). Never replaces S for exposure rules (D-20); beta_hat outside [0, 1] is refused
    (no comparator above 1.0x)."""
    b = float(beta_hat)
    if not (math.isfinite(b) and 0.0 <= b <= 1.0):
        raise GovRefused(f"beta_hat {beta_hat!r} outside [0, 1]: S_beta would hold leverage or a short")
    m = _a(market)
    c = np.broadcast_to(_a(cash) if np.ndim(cash) else np.asarray(float(cash)), m.shape)
    return b * m + (1.0 - b) * c


# --------------------------------------------------------------------------- #
# INV-1 bound line
# --------------------------------------------------------------------------- #
def inv1_bound_line(weights_decided, returns, cost_bp_per_side: float) -> dict:
    """INV-1 (R3:801; D-09): decide at the close of t and fill at the official close of t, so the weight earns
    from t+1 (`costed.earning_weights`); the conservative bound fills at the close of t+1 (one further lag). A
    report line on every stock card, never a gate step and never a replacement for the close-t convention."""
    r = _a(returns)
    w1 = C.earning_weights(weights_decided)
    w2 = C.earning_weights(w1)
    p1 = C.costed_path(w1, r, cost_bp_per_side).net
    p2 = C.costed_path(w2, r, cost_bp_per_side).net
    s1, s2 = V.sharpe(p1), V.sharpe(p2)
    return {"primary_close_t": p1, "bound_close_t1": p2, "sharpe_close_t": s1, "sharpe_close_t1": s2,
            "line": f"INV-1: fill at the official close of t, Sharpe {s1:.2f}; bound (close t+1) {s2:.2f} (reported, not gated)"}
