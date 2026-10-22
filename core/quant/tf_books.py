"""Tech-fund book engine and book-level rules (Sprint 7 package B; R3 G-01..G-03, G-07, G-14, G-31; GOV-7 break-even).

- Book engine of the KRX labs (kr_03_portfolios.py 81-109, reused unchanged by round 2): buy at the formation close,
  buy-and-hold to the next formation (weights drift), names halted at a rebalance carried ("stuck"), a delisted
  name frozen as cash and sold at the next rebalance (buy side only), turnover = sum |w_new - w_drifted| over listed
  names; plus the PC-T-15 delisting stress (-30% / -100% on the first missing session).
- Base books B1-B4 and their filtered books (r2_kr_04_exclusion.py 132-147: an empty filtered book suspends the
  filter for that month); `cap_weights` (r2_kr_common.py 129-146) and the RX-10 group caps.
- INV-4: `band_select` (enter top 20%, exit below top 40%), `turnover_limit` (one-way <= 30%/month, hard 50%),
  `capacity_check` (<= 1% of ADV20, the tighter end of 1-2%, tf_chairs_qa F-12).
- Statistic bases (QA C4-1, C4-2, C4-9). Daily (the gate's): each book pays c x its own turnover on the first
  session its new weights earn; d_t = r_screened,t - r_base,t; ann = mean x 252; IR = mean / sd(ddof 1) x sqrt(252).
  Monthly (R2 lab, only to reproduce lab constants on their own basis): C_d = V_L,d - c TO_L [- (V_B,d - 1 - cb TO_B)],
  period return C_last - 1; x12, sqrt(12), Newey-West 6 lags.
- `break_even_bps` (KR 12, 303); FS-2 constrained momentum builder (FORWARD-SIM book only) with its R-03 scale from
  `sleeves.sleeve_vol_scale` (`fs2_vol_scale`); `CARD_RULES`: the `extras["tf"]` descriptor of each tech-fund card
  that the DNB-TF-01..17 predicates of core/rules/macro_rules evaluate.
- RISK-1 caps by book type: 5% single name and 5% of a VW leg are construction rules; the 0.35 pair cap on
  look-through above a 0.45 pair share and semis <= 0.50 are a display proposal pending owner confirmation
  (rulings 3.7: Council v2.0 R-07 / D1 `msci_25_50` governs exposure; tf_core_link D-02).

Nothing here changes an acting macro parameter or feeds a displayed book; lab numbers are reference constants.
"""
from __future__ import annotations

import math
from typing import Callable, Iterable, Mapping, NamedTuple, Sequence

import numpy as np
from scipy.stats import rankdata

from core.quant.tf_screens import quantile_groups
from core.quant.validate import newey_west_t

COST_PER_SIDE = {"gross": 0.0, "net35": 0.0035, "net70": 0.0070}   # KRX stock, per side (kr_common.py 26)
DELIST_STRESS = (0.30, 1.00)                                       # PC-T-15 / DATA-4 stress cases
BAND_ENTER, BAND_EXIT = 0.20, 0.40                                 # INV-4 / PC-T-04
TURNOVER_TARGET, TURNOVER_HARD = 0.30, 0.50                        # one-way per month (RX-09)
CAPACITY_SHARE = 0.01                                              # <= 1% of ADV20 (F-12 tighter bound)
BASES = {"B1": "EW ALL universe", "B2": "VW ALL capped 5%", "B3": "top-200 VW capped 5%",
         "B4": "MOM 12-1 top quintile EW"}                         # r2_kr_04_exclusion.py 36
BASE_RULE = {"B1": "EW", "B2": "VWcap5", "B3": "VWcap5", "B4": "EW"}
BASE_BOOK_TYPE = {"B1": "EW", "B2": "capped_CW", "B3": "top200", "B4": "EW"}   # tf_screens.SCREEN_WEIGHT keys
RISK1_PROPOSAL = {"single_name": 0.05, "vw_leg": 0.05, "sector_band": 0.10, "pair_cap": 0.35, "pair_trigger": 0.45,
                  "semis_max": 0.50, "pair_cap_books": ("market", "ETF"),
                  "status": "proposal pending owner confirmation (tech-fund RISK-1, G-14; display only); "
                            "Council v2.0 R-07 / D1 msci_25_50 governs exposure"}
FS2_BOOK = "forward_sim:FS-2"

# Reference constants (lab, in sample, KRX 366 formations 1996-03..2026-09, price returns, rf 0, net 35 bp/side):
# never recomputed here (no KRX panel); compared only on their own basis (tolerance +-0.10 pp/yr, IR +-0.02).
SCREEN_REFERENCE = {
    ("SCR-1", "B1", "monthly"): {"ann_diff": 0.0307644, "ir": 1.52953, "basis": "monthly (R2 lab)",
                                 "source": "datalab/results/r2_kr/r2_kr_excl_summary.csv:11 (GV-002, GV-004)"},
    ("SCR-1", "B1", "daily"): {"ann_diff": 0.0312, "ir": 1.64, "basis": "daily (QA recomputation; the gate's)",
                               "source": "qa/QA_recomputation.md:63 (G-TF-SCR-15)"},
    ("SCR-2", "B1", "monthly"): {"ann_diff": 0.0233631, "ir": 0.645267, "basis": "monthly (R2 lab)",
                                 "source": "datalab/results/r2_kr/r2_kr_excl_summary.csv:17 (GV-015, GV-017)"},
    ("SCR-2", "B1", "daily"): {"ann_diff": 0.0248, "ir": 1.03, "basis": "daily (QA recomputation; the gate's)",
                               "source": "qa/QA_recomputation.md:64 (G-TF-SCR-16)"},
}


# --------------------------------------------------------------------------- #
# Weights and caps
# --------------------------------------------------------------------------- #
def cap_weights(base, cap: float = 0.05) -> np.ndarray:
    """Normalise base (> 0) to 1, cap every weight at `cap` and give the excess pro rata (by base weight) to the
    uncapped names until none exceeds the cap; fewer than 1/cap names -> equal weights (lab convention)."""
    base = np.asarray(base, dtype=np.float64)
    w = base / base.sum()
    n = len(w)
    if n * cap < 1.0 - 1e-12:
        return np.full(n, 1.0 / n)
    capped = np.zeros(n, bool)
    for _ in range(n + 1):
        room = 1.0 - cap * capped.sum()
        w = np.where(capped, cap, base * room / base[~capped].sum())
        new = ~capped & (w > cap + 1e-15)
        if not new.any():
            break
        capped |= new
    return w


def weights(members, rule: str, mcap_row) -> np.ndarray:
    """EW = 1/n; VW = Marcap / sum; VWcap5 = cap_weights(Marcap, 0.05) (each VW leg capped at 5% of the leg)."""
    n = len(members)
    if n == 0:
        return np.zeros(0)
    if rule == "EW":
        return np.full(n, 1.0 / n)
    m = np.asarray(mcap_row)[np.asarray(members)].astype(np.float64)
    if rule == "VW":
        return m / m.sum()
    if rule == "VWcap5":
        return cap_weights(m, 0.05)
    raise ValueError(f"weight rule {rule!r} not in ('EW', 'VW', 'VWcap5')")


def apply_caps(base, *, single: float = 0.05, groups: Iterable[tuple[np.ndarray, float]] = ()) -> np.ndarray:
    """Single-name cap (cap_weights), then group caps (sector bands, semis share): a breaching group is scaled to
    its cap and locked, the freed weight goes pro rata to the unlocked names under the single cap; repeat until no
    group breaches. Raises ValueError when the caps cannot all hold (never returns a breaching book)."""
    w = cap_weights(base, single)
    if w.max() > single + 1e-12:
        raise ValueError(f"caps infeasible: {len(w)} names cannot hold a {single:.0%} single-name cap")
    groups = [(np.asarray(m, bool), float(c)) for m, c in groups]
    locked = np.zeros(len(w), bool)
    for _ in range(len(groups) + 2):
        breach = [(m, c) for m, c in groups if w[m].sum() > c + 1e-12]
        if not breach:
            return w
        for m, c in breach:
            w[m] *= c / w[m].sum()
            locked |= m
        free = ~locked
        total = 1.0 - w[locked].sum()
        if w[free].sum() <= 0 or free.sum() * single < total - 1e-12:
            raise ValueError("caps infeasible: the unlocked names cannot absorb the group excess under the single cap")
        w[free] = cap_weights(w[free], single / total) * total
    raise ValueError("caps did not converge")


def sector_groups(sectors: Sequence, bench_weight: Mapping[str, float], band: float = RISK1_PROPOSAL["sector_band"]):
    """RX-10 sector caps: sector weight <= benchmark weight + band (the band has no number in R3, tf_core_link D-04;
    RX-10's +10 pp is the executives' proposal)."""
    sectors = np.asarray(sectors)
    return [(sectors == s, float(bench_weight.get(s, 0.0)) + band) for s in np.unique(sectors)]


def pair_cap_proposal(pair_lookthrough_weight: float, pair_share: float, book_type: str) -> dict:
    """RISK-1 display line: the 0.35 pair cap on look-through for market / ETF books when the pair share > 0.45.
    `acting` is always False: it never changes a weight (Council D1 governs)."""
    p = RISK1_PROPOSAL
    applies = book_type in p["pair_cap_books"]
    triggered = applies and pair_share > p["pair_trigger"]
    excess = max(0.0, pair_lookthrough_weight - p["pair_cap"]) if triggered else 0.0
    return {"applies": applies, "triggered": triggered, "cap": p["pair_cap"], "pair_share": pair_share,
            "pair_weight": pair_lookthrough_weight, "would_bind": excess > 0, "excess": excess, "acting": False,
            "status": p["status"]}


# --------------------------------------------------------------------------- #
# Book engine (K03 81-109; RC 155-182)
# --------------------------------------------------------------------------- #
class Book:
    """Value vector `v` (fractions of book value) of one simulated book."""
    __slots__ = ("v", "started")

    def __init__(self, n: int):
        self.v = np.zeros(n)
        self.started = False

    def rebalance(self, members, base_w, E_t, TR_t) -> tuple[float, int]:
        """Target `base_w` on `members`, carrying names that are held, listed and not traded at t (stuck);
        returns (turnover, n_stuck). A delisted position is already cash: only its redeployment is counted."""
        v = self.v
        stuck = (v > 0) & E_t & ~TR_t
        stuck_val = v[stuck].sum() if self.started else 0.0
        w = np.zeros_like(v)
        if len(members):
            w[np.asarray(members)] = (1.0 - stuck_val) * np.asarray(base_w)
        ns = ~stuck & E_t
        to = float(np.abs(w[ns] - v[ns]).sum())
        w[stuck] = v[stuck]
        self.v = w
        self.started = True
        return to, int(stuck.sum())

    def hold(self, G) -> np.ndarray:
        """Daily book returns over the period from the growth matrix G (sessions x N); weights drift."""
        idx = np.flatnonzero(self.v)
        if idx.size == 0:
            return np.zeros(G.shape[0])
        vals = self.v[idx][None, :] * G[:, idx]
        pv = vals.sum(axis=1)
        prev = np.concatenate(([self.v[idx].sum()], pv[:-1]))
        with np.errstate(invalid="ignore", divide="ignore"):
            r = np.where(prev > 0, pv / prev - 1.0, 0.0)
        nv = np.zeros_like(self.v)
        if pv[-1] > 0:
            nv[idx] = vals[-1] / pv[-1]
        self.v = nv
        return r


def growth(R, E, t: int, te: int, delist_haircut: float = 0.0) -> np.ndarray:
    """G for holding days t+1..te: cumprod(1 + r x alive), alive = listed without a gap since t; a name that stops
    existing freezes as cash, after a one-off loss of `delist_haircut` (0, or the -30% / -100% stress)."""
    if not 0.0 <= delist_haircut <= 1.0:
        raise ValueError(f"delist_haircut {delist_haircut!r} outside [0, 1]")
    Rb = np.nan_to_num(np.asarray(R[t + 1:te + 1], dtype=np.float64), nan=0.0)
    A = np.cumprod(np.asarray(E[t + 1:te + 1], dtype=bool), axis=0).astype(bool)
    drop = ~A & np.vstack([np.ones((1, A.shape[1]), bool), A[:-1]])
    return np.cumprod((1.0 + Rb * A) * np.where(drop, 1.0 - delist_haircut, 1.0), axis=0)


def periods(fidx: Sequence[int], T: int) -> tuple[np.ndarray, np.ndarray]:
    """(starts, ends) of each holding period: days fidx[k]+1 .. fidx[k+1] (last: .. T-1); ends exclusive."""
    f = np.asarray(fidx, dtype=int)
    ends = np.append(f[1:], T - 1) + 1
    return f + 1, ends


def run_books(R, E, TR, fidx: Sequence[int], specs: Sequence[tuple[str, Callable]], *,
              delist_haircut: float = 0.0) -> dict[str, dict]:
    """Run books side by side over the formations: spec fn(k) -> (member indices, weights summing to 1).
    Returns name -> {daily (T, gross, NaN outside the sample), to (K), nmem (K), nstuck (K)}."""
    T, N = np.shape(R)
    K = len(fidx)
    out = {nm: {"daily": np.full(T, np.nan), "to": np.full(K, np.nan), "nmem": np.zeros(K, int),
                "nstuck": np.zeros(K, int)} for nm, _ in specs}
    books = {nm: Book(N) for nm, _ in specs}
    for k, t in enumerate(fidx):
        te = fidx[k + 1] if k + 1 < K else T - 1
        if te <= t:
            continue
        G = growth(R, E, t, te, delist_haircut)
        for nm, fn in specs:
            m, w = fn(k)
            if len(m) == 0:
                continue
            o = out[nm]
            o["to"][k], o["nstuck"][k] = books[nm].rebalance(m, w, np.asarray(E[t], bool), np.asarray(TR[t], bool))
            o["daily"][t + 1:te + 1] = books[nm].hold(G)
            o["nmem"][k] = len(m)
    return out


def base_member_masks(k: int, univ_all, univ_large, mom_12_1) -> dict[str, np.ndarray]:
    """B1 / B2 on ALL, B3 on LARGE, B4 = MOM_12_1 top quintile of ALL (r2_kr_04_exclusion.py 132-135)."""
    ua = np.asarray(univ_all, bool)
    return {"B1": ua, "B2": ua, "B3": np.asarray(univ_large, bool),
            "B4": quantile_groups(mom_12_1, ua, 5, k) == 5}


def book_weights(mask, rule: str, mcap_row, exclude=None) -> tuple[np.ndarray, np.ndarray, bool]:
    """(member indices, weights, suspended) of a base book or its filtered book (members minus flagged names, same
    weighting rule); a filter that would empty the book is suspended for that formation (R04 140-147)."""
    mask = np.asarray(mask, bool)
    keep = mask if exclude is None else mask & ~np.asarray(exclude, bool)
    suspended = bool(exclude is not None and mask.any() and not keep.any())
    idx = np.flatnonzero(mask if suspended else keep)
    return idx, weights(idx, rule, mcap_row), suspended


# --------------------------------------------------------------------------- #
# INV-4 bands, turnover, capacity
# --------------------------------------------------------------------------- #
def band_select(score, U, held, enter: float = BAND_ENTER, exit: float = BAND_EXIT) -> np.ndarray:
    """Buy/hold band on a higher-is-better score inside U: enter in the top `enter`, keep a held name while it is in
    the top `exit` (average ranks, pct = (rank - 0.5)/n)."""
    if not 0.0 < enter <= exit <= 1.0:
        raise ValueError(f"band needs 0 < enter <= exit <= 1, got {enter}, {exit}")
    score = np.asarray(score, dtype=np.float64)
    m = np.asarray(U, bool) & np.isfinite(score)
    out = np.zeros(score.shape, bool)
    n = int(m.sum())
    if n == 0:
        return out
    pct = (rankdata(score[m], method="average") - 0.5) / n
    out[m] = (pct >= 1.0 - enter) | (np.asarray(held, bool)[m] & (pct >= 1.0 - exit))
    return out


def turnover_one_way(w_prev, w_new) -> float:
    """One-way turnover = half the sum of absolute weight changes (2 x one-way = the lab's per-rebalance turnover)."""
    return 0.5 * float(np.abs(np.asarray(w_new, float) - np.asarray(w_prev, float)).sum())


class TurnoverCheck(NamedTuple):
    weights: np.ndarray
    one_way: float
    status: str            # ok | above_target | clipped_to_hard


def turnover_limit(w_prev, w_target, *, target: float = TURNOVER_TARGET, hard: float = TURNOVER_HARD) -> TurnoverCheck:
    """One-way monthly turnover: <= target ok; above target reported; above the hard limit the trade is scaled
    toward the target weights so the one-way turnover equals `hard`."""
    w_prev, w_target = np.asarray(w_prev, float), np.asarray(w_target, float)
    ow = turnover_one_way(w_prev, w_target)
    if ow <= hard + 1e-12:
        return TurnoverCheck(w_target, ow, "ok" if ow <= target + 1e-12 else "above_target")
    w = w_prev + (hard / ow) * (w_target - w_prev)
    return TurnoverCheck(w, turnover_one_way(w_prev, w), "clipped_to_hard")


def capacity_check(weights_, nav: float, adv20, share: float = CAPACITY_SHARE) -> np.ndarray:
    """True where the position notional is <= `share` x ADV20 (missing ADV20 fails)."""
    adv = np.asarray(adv20, dtype=np.float64)
    pos = np.abs(np.asarray(weights_, dtype=np.float64)) * float(nav)
    with np.errstate(invalid="ignore"):
        return np.isfinite(adv) & (pos <= share * adv + 1e-9)


# --------------------------------------------------------------------------- #
# Series and statistics
# --------------------------------------------------------------------------- #
def daily_net(gross_daily, to, starts, c: float) -> np.ndarray:
    """Daily basis (QA C4-9): c x the book's own turnover subtracted on the first session the new weights earn."""
    net = np.array(gross_daily, dtype=np.float64, copy=True)
    for k, s in enumerate(starts):
        if s < net.size and np.isfinite(to[k]):
            net[s] -= c * to[k]
    return net


def diff_series(r_screened, r_base) -> np.ndarray:
    """d_t = r_screened,t - r_base,t on the sessions where both are finite (same days, both net of own costs)."""
    d = np.asarray(r_screened, dtype=np.float64) - np.asarray(r_base, dtype=np.float64)
    return d[np.isfinite(d)]


def daily_stats(d) -> dict:
    """Daily basis: ann = mean x 252; te = sd(ddof 1) x sqrt(252); IR = mean / sd(ddof 1) x sqrt(252)."""
    d = np.asarray(d, dtype=np.float64)
    d = d[np.isfinite(d)]
    if d.size < 2:
        return {"n": int(d.size), "ann": float("nan"), "te": float("nan"), "ir": float("nan")}
    mu, sd = float(d.mean()), float(d.std(ddof=1))
    return {"n": int(d.size), "ann": mu * 252, "te": sd * math.sqrt(252),
            "ir": mu / sd * math.sqrt(252) if sd > 0 else float("nan")}


def series(L: Mapping, starts, ends, *, c: float = 0.0, S: Mapping | None = None, B: Mapping | None = None,
           cb: float = 0.0) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Monthly-basis (R2 lab) combination built period by period, C_0 = 1:
    C_d = V_L,d - c TO_L [- (V_S,d - 1) - c TO_S] [- (V_B,d - 1 - cb TO_B)]; daily = C_d / C_{d-1} - 1; period = C_last - 1.
    Books are {daily, to}; returns (per-period, daily, turnover)."""
    T = len(L["daily"])
    rl, tl = np.nan_to_num(L["daily"], nan=0.0), np.nan_to_num(L["to"], nan=0.0)
    to = tl.copy()
    if S is not None:
        rs, ts = np.nan_to_num(S["daily"], nan=0.0), np.nan_to_num(S["to"], nan=0.0)
        to = to + ts
    if B is not None:
        rb, tb = np.nan_to_num(B["daily"], nan=0.0), np.nan_to_num(B["to"], nan=0.0)
    daily, per = np.full(T, np.nan), np.full(len(starts), np.nan)
    for k, (s, e) in enumerate(zip(starts, ends)):
        if e <= s:
            continue
        C = np.cumprod(1.0 + rl[s:e]) - c * tl[k]
        if S is not None:
            C = C - (np.cumprod(1.0 + rs[s:e]) - 1.0) - c * ts[k]
        if B is not None:
            C = C - (np.cumprod(1.0 + rb[s:e]) - 1.0 - cb * tb[k])
        daily[s:e] = C / np.concatenate(([1.0], C[:-1])) - 1.0
        per[k] = C[-1] - 1.0
    return per, daily, to


def lab_diff_series(X: Mapping, Y: Mapping, starts, ends, c: float):
    """Filtered minus unfiltered on the monthly basis, both net of their own costs at c (RC 239-241)."""
    return series(X, starts, ends, B=Y, c=c, cb=c)


def monthly_stats(per, *, ann: int = 12, nw_lags: int = 6) -> dict:
    """Monthly basis: ann = mean x 12; te = sd(ddof 1) x sqrt(12); IR = mean / sd x sqrt(12); Newey-West t, 6 lags."""
    x = np.asarray(per, dtype=np.float64)
    x = x[np.isfinite(x)]
    if x.size < 3:
        return {"n": int(x.size), "ann": float("nan"), "te": float("nan"), "ir": float("nan"), "nw_t": float("nan")}
    mu, sd = float(x.mean()), float(x.std(ddof=1))
    return {"n": int(x.size), "ann": mu * ann, "te": sd * math.sqrt(ann),
            "ir": mu / sd * math.sqrt(ann) if sd > 0 else float("nan"), "nw_t": newey_west_t(x, nw_lags)}


# The one home of the formula: core/quant/tf_gov re-exports it; tf_gov.break_even_screen is the GOV-7 pre-gate test.
def break_even_bps(gross_ann: float, turnover: float) -> float:
    """Break-even cost per side (bp) = gross annual return / annual turnover (linear: net = gross - c x turnover).
    Signals: L/S gross / both legs' turnover (= 2 x one-way); screens: gross difference / the screened book's extra
    turnover. Approximate (tf_algorithms Ambiguity 16)."""
    if not turnover > 0:
        raise ValueError(f"break-even needs a positive turnover, got {turnover!r}")
    return float(gross_ann) / float(turnover) * 1e4


# --------------------------------------------------------------------------- #
# FS-2 constrained momentum (FORWARD-SIM only; CR-05; G-31)
# --------------------------------------------------------------------------- #
def fs2_momentum_book(mom, U, exclude, k: int, *, vs, cap: float = 0.05) -> dict:
    """Q5 of 12-1 (or 12-7) momentum inside U minus the excluded names (F4 or the highest-turnover quintile, SCR-3:
    mandatory), equal weights capped at `cap` per name, scaled by the R-03 own-vol scale `vs` (a
    sleeves.sleeve_vol_scale VSResult or a number in [0, 1]); long-only, the remainder in cash. The book id is
    `forward_sim:FS-2`: it never feeds the displayed or recommended book."""
    if exclude is None:
        raise ValueError("SCR-3: a KRX momentum sleeve must exclude the F4 names or the highest-turnover quintile")
    try:
        scale = float(getattr(vs, "value", vs))
    except (TypeError, ValueError):
        raise ValueError(f"FS-2: R-03 scale unavailable ({vs!r}); fail closed") from None
    if not 0.0 <= scale <= 1.0:
        raise ValueError(f"FS-2: R-03 scale {scale!r} outside [0, 1]")
    U = np.asarray(U, bool)
    idx = np.flatnonzero((quantile_groups(mom, U, 5, k) == 5) & ~np.asarray(exclude, bool))
    w = np.full(idx.size, min(1.0 / idx.size, cap) * scale) if idx.size else np.zeros(0)
    return {"book": FS2_BOOK, "status": "FORWARD_SIM", "acting": False, "members": idx, "weights": w,
            "cash": 1.0 - float(w.sum()), "vs": scale, "cap": cap}


def fs2_vol_scale(store, registry, decision_utc, knowledge_utc, *, series_id: str | None = None,
                  armed: bool = False, revision: int = 1):
    """FS-2's R-03 input: `sleeves.sleeve_vol_scale(store, registry, "KR", "momentum", ...)` -> VSResult or
    MissingInput (no KR paper long/short series is registered, so today it is MissingInput and
    `fs2_momentum_book` refuses: fail closed). Pass the result as `vs`."""
    from core.quant.sleeves import sleeve_vol_scale     # lazy: the screen library stays free of the PIT stack
    return sleeve_vol_scale(store, registry, "KR", "momentum", decision_utc, knowledge_utc, revision,
                            armed=armed, series_id=series_id)


# --------------------------------------------------------------------------- #
# Tech-fund card descriptors (`extras["tf"]`, read by macro_rules' DNB-TF-01..17; rulings 3.8)
# --------------------------------------------------------------------------- #
_CLOSE = {"decision_time": "close", "fill": "official_close"}            # INV-1 (DNB-TF-13)
_MONTHLY = {"rebalance": "monthly", "horizon_sessions": 21, **_CLOSE}
# card id -> the rule-object fields the book itself fixes (applies_to, multiplier fields) and its tf descriptor;
# docs/techfund_study.rule_object adds the draft's card fields (kind, market, instrument_book, books).
CARD_RULES = {
    "SCR-1": {"extras": {"tf": {"signal_family": "lottery", "role": "screen", "screen_id": "F4", "long_only": True,
                                "screen_features": ["VOL_3M", "MAX_1M", "TURN_1M"], **_MONTHLY}}},
    "SCR-2": {"extras": {"tf": {"signal_family": "dilution", "role": "screen", "screen_id": "F6", "long_only": True,
                                "screen_features": ["DIL_LIT"], **_MONTHLY}}},
    "FS-1": {"applies_to": "market_gross", "factor": "overlay", "output_range": [0.5, 1.0], "exposure_basis": "total",
             "composition": "min", "extras": {"tf": {"signal_family": "ts_trend", "role": "protective",
                                                     "horizon_sessions": 1, "comparator": "S", **_CLOSE}}},
    "FS-2": {"applies_to": "momentum", "extras": {"tf": {"signal_family": "momentum_12_1", "role": "alpha", "exclusions": ["F4"],
                                                         "vol_scale": "R-03", "name_cap": 0.05, "long_only": True, **_MONTHLY}}},
    "FS-3": {"extras": {"tf": {"signal_family": "low_vol", "role": "protective", "comparator": "S_beta",
                               "long_only": True, **_MONTHLY}}},
    "FS-4": {"extras": {"tf": {"signal_family": "l0_ridge_challenger", "role": "challenger", "long_only": True,
                               "rebalance": "monthly", "horizon_sessions": 63, **_CLOSE}}},
    "FS-5": {"applies_to": "reversal", "extras": {"tf": {"signal_family": "st_reversal", "role": "screen_guard",
                                                         "screen_id": "REV_1M_top_decile", "long_only": True, **_MONTHLY}}},
}
