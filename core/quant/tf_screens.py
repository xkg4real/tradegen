"""Tech-fund screens and KRX panel hygiene (Sprint 7 package B; R3 G-01..G-03, G-05, G-06, G-14, G-28, G-34).

Library code on a wide (T sessions x N codes) panel, ported from the KRX data labs and the QA corrections:

- INV-3 / DATA-1..2 panel hygiene: six-character codes (`pad_code`; files 1995-05-02..2000-05-26 store '5930'),
  common shares (code ending '0'), the five-class name classifier with the 인터리츠 exception (kr_common.py 61-84;
  QA C.5), float32 storage of prices, amounts, market caps and features, eligibility on rows <= t-1 (INV-3) with
  the lab's decide-at-close-t convention exposed as `as_of="close_t"` (tf_core_link D-05: lab goldens were made
  with rows <= t, so they stay reference constants), the RX-05 extras, the |dln shares| > 1% corporate-action flag.
- SCR-1/2/3 inputs: `quantile_groups`, `top_frac`, the P6/F4 lottery composite (ordinal cut of exactly
  floor(0.10 n) names), F1..F8, DIL_LIT / DIL_NI with the QA split-like and float32 tie rules, and
  `screen_mask(book_type)` with the CR-06 weights 3 (EW / small-mid) / 1 (capped CW hygiene) / 0 (top 200).
- INV-2 lab detection: `limit_lock_mask` with the KRX limit eras (KOSPI from the regime price-limit tags).
  Simulated fills use the R-27 exact-limit-price test in core/engine/orders.py (tf_core_link D-07); this mask is
  the research-panel audit that explains GV-171..174.
- ML-1 L0 equal-weight z-score composite (signs fixed in advance); FS-5 monthly reversal guard.
- RISK-1 display: `pair_share_kospi` (CR-07) and its three alternatives; `rebuilt_kospi` (QA C4-7).

Nothing here feeds a book: screens, weights and pair shares are research and display code (rulings 3.7-3.9).
The KRX all-stock panel is not on this machine, so every card run is NOT_RUN (REFDATA). Sources:
tf_algorithms.md A.3-A.9, B.1-B.3, B.15; tf_chairs_qa.md C.4-C.5; tf_core_link.md A1-A4.
"""
from __future__ import annotations

import re
from bisect import bisect_right
from dataclasses import dataclass
from datetime import date
from functools import cached_property
from typing import Callable, Iterable, Mapping

import numpy as np
from scipy.stats import rankdata

LAB_SEED = 20261002                                   # kr_common.py SEED: quantile tie-break draws
KOSPI, KOSDAQ = 1, 2
MARKET_CODE = {"KOSPI": 1, "KOSDAQ": 2, "KOSDAQ GLOBAL": 2}   # KOSDAQ GLOBAL is KOSDAQ; KONEX and others dropped
NAME_CLASSES = ("", "SPAC", "REIT", "INFRA_FUND", "FUND", "DR_ETN")   # stored int8 = index; 0 = operating company
LIMIT_CHANGE = date(2015, 6, 15)                      # +-15% -> +-30% daily price limit (kr_common.py 25)
DIL_THRESHOLD = 0.10                                   # F6: float32-stored DIL_LIT > 0.10 (QA C4-3: 10.0% is flagged)
CA_FLAG_DLN = 0.01                                     # RX-06 / DATA-2: |dln shares| > 1%
SCREEN_WEIGHT = {"EW": 3, "small_mid": 3, "capped_CW": 1, "top200": 0}   # CR-06 priors (R3:46), not gate results
PAIR_CODES = ("005930", "005935", "000660")           # CR-07 numerator: Samsung common + preferred, SK hynix
REBUILT_KOSPI_BASE = (date(2007, 10, 31), 2064.85)    # kr_05_index_timing.py 54-55
# QA check values of the rebuilt KOSPI (qa/QA_recomputation.md 28-30); reproducible only on the KRX marcap panel.
REBUILT_KOSPI_CHECK = {date(2020, 3, 19): 1457.46, date(2026, 6, 22): 9120.19, date(2026, 7, 30): 5599.30}

# --------------------------------------------------------------------------- #
# Codes and names (QA C4-5, C.5)
# --------------------------------------------------------------------------- #
_RX_SPAC = re.compile(r"스팩|SPAC|기업인수목적")
_RX_REIT = re.compile(r"리츠|코크렙|REIT|리얼티\d*$|^교보메리츠|^유레스메리츠|맥쿼리센트럴")
_RX_INFRA = re.compile(r"맥쿼리인프라|발해인프라|인프라펀드|인프라투융자")
_RX_FUND = re.compile(r"선박투자|\d+호|[가-힣]{2,}(?:일|이|삼|사|오|육|칠|팔|구|십|십오)호(?:-?MF)?$|-?MF$|펀드|뮤추얼"
                      r"|경매|베트남(?:개발)?\d$|유전\d|유전$")
_RX_OTHER = re.compile(r"ETN|KDR")
_NOT_REIT = ("인터리츠",)                              # 1996-2007 KOSDAQ operating company


def pad_code(code) -> str:
    """Six-character KRX code: '5930' and 5930 are read as '005930' before any filter."""
    return str(code).strip().zfill(6)


def is_common(code) -> bool:
    return pad_code(code)[-1] == "0"


def classify_name(name) -> str:
    """'' for an operating company, else SPAC / REIT / INFRA_FUND / FUND / DR_ETN (first match in that order)."""
    n = re.sub(r"\s+", "", str(name))
    if _RX_SPAC.search(n):
        return "SPAC"
    masked = n.replace("메리츠", "#").replace("블리츠", "#")
    if n not in _NOT_REIT and (_RX_REIT.search(masked)
                               or (_RX_REIT.search(n) and n.startswith(("교보메리츠", "유레스메리츠")))):
        return "REIT"
    if _RX_INFRA.search(n):
        return "INFRA_FUND"
    if _RX_FUND.search(n):
        return "FUND"
    if _RX_OTHER.search(n):
        return "DR_ETN"
    return ""


# --------------------------------------------------------------------------- #
# Panel
# --------------------------------------------------------------------------- #
@dataclass(frozen=True, eq=False)
class Panel:
    """Wide KRX panel. Float32: close, high, low, ret, amount, marcap (lab storage); float64: shares.
    `ret` is the cleaned return r = ChangesRatio/100 (the lab's step-2 cleaning rules are not recoverable here,
    tf_chairs_qa F-19, so the panel takes r and `beyond_nonca` as delivered); `cr` the raw ChangesRatio/100."""
    dates: tuple
    codes: tuple
    close: np.ndarray
    high: np.ndarray
    low: np.ndarray
    ret: np.ndarray
    volume: np.ndarray
    amount: np.ndarray
    marcap: np.ndarray
    shares: np.ndarray
    market: np.ndarray            # int8: 1 KOSPI, 2 KOSDAQ (incl. GLOBAL), 0 other
    name_cls: np.ndarray          # int8 index into NAME_CLASSES, from the row's own Name on day t
    exists: np.ndarray            # bool: listed on day t
    cr: np.ndarray | None = None
    change_code: np.ndarray | None = None      # 4 / 5 = old KRX limit-up / limit-down codes (absent in 2026 data)
    beyond_nonca: np.ndarray | None = None     # beyond-limit move without a corporate action (cleaning step)
    admin: np.ndarray | None = None            # RX-05: administrative / caution / warning designation

    def __post_init__(self) -> None:
        shape = (len(self.dates), len(self.codes))
        for name in ("close", "high", "low", "ret", "volume", "amount", "marcap", "shares", "market", "name_cls",
                     "exists", "cr", "change_code", "beyond_nonca", "admin"):
            a = getattr(self, name)
            if a is not None and np.shape(a) != shape:
                raise ValueError(f"Panel.{name} shape {np.shape(a)} != {shape}")
        if any(c != pad_code(c) for c in self.codes):
            raise ValueError("Panel.codes must be six-character codes (pad_code)")

    @property
    def T(self) -> int:
        return len(self.dates)

    @cached_property
    def common(self) -> np.ndarray:
        return np.array([c[-1] == "0" for c in self.codes], dtype=bool)

    @cached_property
    def valid(self) -> np.ndarray:
        """VALID set: finite cleaned return and Volume > 0."""
        return np.isfinite(self.ret) & (self.volume > 0)

    @cached_property
    def cumlog(self) -> np.ndarray:
        """CL: cumulative log price from the cleaned returns (float64)."""
        return np.cumsum(np.log1p(np.nan_to_num(self.ret.astype(np.float64), nan=0.0)), axis=0)


def build_panel(rows: Iterable[Mapping]) -> Panel:
    """Pivot raw marcap-style rows (Date, Code, Name, Market, Close, High, Low, Volume, Amount, Marcap, Stocks,
    ChangesRatio; optional ChangeCode, BeyondNonCA, Admin) into a Panel: codes zero-padded first, KONEX / unknown
    markets, non-'0' codes and Close <= 0 dropped (r2_kr_01_build_extra.py row filter), Low 0 -> Close, float32
    storage, name class from each row's own Name."""
    kept = []
    for r in rows:
        code = pad_code(r["Code"])
        mk = MARKET_CODE.get(str(r["Market"]).strip())
        if mk is None or code[-1] != "0" or not float(r["Close"]) > 0:
            continue
        kept.append((r["Date"], code, mk, r))
    dates = tuple(sorted({d for d, *_ in kept}))
    codes = tuple(sorted({c for _, c, *_ in kept}))
    di = {d: i for i, d in enumerate(dates)}
    ci = {c: j for j, c in enumerate(codes)}
    shape = (len(dates), len(codes))
    f32 = {k: np.full(shape, np.nan, np.float32) for k in ("close", "high", "low", "ret", "amount", "marcap", "cr")}
    vol, shares = np.full(shape, np.nan), np.full(shape, np.nan)
    market, ncls, cc = np.zeros(shape, np.int8), np.zeros(shape, np.int8), np.zeros(shape, np.int8)
    exists, bnc, adm = np.zeros(shape, bool), np.zeros(shape, bool), np.zeros(shape, bool)
    for d, code, mk, r in kept:
        i, j = di[d], ci[code]
        close = float(r["Close"])
        low = float(r.get("Low") or 0.0)
        f32["close"][i, j], f32["high"][i, j] = close, float(r["High"])
        f32["low"][i, j] = low if low > 0 else close
        f32["ret"][i, j] = f32["cr"][i, j] = float(r["ChangesRatio"]) / 100.0
        f32["amount"][i, j], f32["marcap"][i, j] = float(r["Amount"]), float(r["Marcap"])
        vol[i, j], shares[i, j] = float(r["Volume"]), float(r["Stocks"])
        market[i, j], exists[i, j] = mk, True
        ncls[i, j] = NAME_CLASSES.index(classify_name(r.get("Name", "")))
        code_chg = int(r.get("ChangeCode") or 0)
        cc[i, j] = code_chg if code_chg in (4, 5) else 0
        bnc[i, j], adm[i, j] = bool(r.get("BeyondNonCA", False)), bool(r.get("Admin", False))
    return Panel(dates, codes, f32["close"], f32["high"], f32["low"], f32["ret"], vol, f32["amount"], f32["marcap"],
                 shares, market, ncls, exists, cr=f32["cr"], change_code=cc, beyond_nonca=bnc, admin=adm)


# --------------------------------------------------------------------------- #
# Eligibility and universes (K02 94-106; RX-05; INV-3)
# --------------------------------------------------------------------------- #
def _asof(t: int, as_of: str) -> int:
    if as_of == "t-1":
        return t - 1
    if as_of == "close_t":
        return t
    raise ValueError(f"as_of {as_of!r} not in ('t-1', 'close_t')")


def _month_end_at_or_before(dates, s: int) -> int:
    for j in range(s, -1, -1):
        if j == len(dates) - 1 or (dates[j + 1].year, dates[j + 1].month) != (dates[j].year, dates[j].month):
            return j
    return -1


def eligible(P: Panel, t: int, *, as_of: str = "t-1", rx05: bool = False, cap_min: float = 100e9,
             top_n: int = 500, adv_min: float = 1e9, min_listed: int = 60) -> np.ndarray:
    """Eligible set for a decision at the close of t, from rows <= s (s = t-1 per INV-3 / DATA-1; s = t is the lab
    convention, kept for reproducing lab constants on their own basis):
    listed; KOSPI or KOSDAQ; common share; operating company; Close >= 1,000; Marcap > 0; >= 200 valid days in
    s-251..s; Amount > 0 on >= 4 of s-4..s; traded on s; no beyond-limit move without a corporate action in s-29..s.
    `rx05=True` adds RX-05: Marcap >= cap_min or top `top_n` by Marcap at the prior month-end; ADV20 >= adv_min;
    listed on each of the last `min_listed` sessions; no administrative / caution / warning designation.
    (DART rights / merger windows and IPO days need the PIT event layer and are not applied here.)"""
    s = _asof(t, as_of)
    out = np.zeros(len(P.codes), bool)
    if s < 251:
        return out
    nvalid = P.valid[s - 251:s + 1].sum(axis=0)
    npos = (P.amount[s - 4:s + 1] > 0).sum(axis=0)
    base = (P.exists[s] & np.isin(P.market[s], (KOSPI, KOSDAQ)) & P.common & (P.name_cls[s] == 0)
            & (P.close[s] >= 1000) & (P.marcap[s] > 0) & (nvalid >= 200) & (npos >= 4))
    out = base & (P.volume[s] > 0)
    if P.beyond_nonca is not None:
        out &= ~P.beyond_nonca[s - 29:s + 1].any(axis=0)
    if rx05:
        rows = P.exists[s - 19:s + 1]
        n20 = rows.sum(axis=0)
        amt = np.where(rows, np.nan_to_num(P.amount[s - 19:s + 1].astype(np.float64)), 0.0).sum(axis=0)
        adv20 = np.where(n20 >= 15, amt / np.maximum(n20, 1), np.nan)
        j = _month_end_at_or_before(P.dates, s)
        top = np.zeros_like(out)
        if j >= 0:
            mc = np.where(P.exists[j] & (P.marcap[j] > 0), P.marcap[j].astype(np.float64), -np.inf)
            order = np.argsort(-mc, kind="stable")[:top_n]
            top[order[np.isfinite(mc[order])]] = True
        listed = P.exists[max(0, s - min_listed + 1):s + 1].all(axis=0) & (s + 1 >= min_listed)
        out &= ((P.marcap[s].astype(np.float64) >= cap_min) | top) & (adv20 >= adv_min) & listed
        if P.admin is not None:
            out &= ~P.admin[s]
    return out


def universe_all(P: Panel, t: int, **kw) -> np.ndarray:
    """ALL = eligible with float32 Marcap >= the 20th percentile (np.quantile, linear) of eligible Marcap in float64."""
    elig = eligible(P, t, **kw)
    if not elig.any():
        return elig
    mc = P.marcap[_asof(t, kw.get("as_of", "t-1"))].astype(np.float64)   # float32 values, compared exactly
    cut = np.quantile(mc[elig], 0.20)
    return elig & (mc >= cut)


def universe_large(P: Panel, t: int, n: int = 200, **kw) -> np.ndarray:
    """LARGE = top `n` eligible names by Marcap (stable argsort, K02 102-106)."""
    elig = eligible(P, t, **kw)
    mc = np.where(elig, P.marcap[_asof(t, kw.get("as_of", "t-1"))].astype(np.float64), -np.inf)
    order = np.argsort(-mc, kind="stable")[:n]
    out = np.zeros_like(elig)
    out[order[np.isfinite(mc[order])]] = True
    return out


def corporate_action_flag(P: Panel) -> np.ndarray:
    """RX-06 / DATA-2: |dln shares| > 1% between consecutive listed sessions (False on the first session)."""
    out = np.zeros(P.shares.shape, bool)
    s = P.shares.astype(np.float64)
    both = P.exists[1:] & P.exists[:-1] & (s[1:] > 0) & (s[:-1] > 0)
    with np.errstate(invalid="ignore", divide="ignore"):
        out[1:] = both & (np.abs(np.log(np.where(both, s[1:] / np.where(both, s[:-1], 1.0), 1.0))) > CA_FLAG_DLN)
    return out


# --------------------------------------------------------------------------- #
# Features at a formation (K02 110-173; R01 223-248), rows <= t, float32
# --------------------------------------------------------------------------- #
def _window_count(mask: np.ndarray) -> np.ndarray:
    return mask.sum(axis=0)


def features_at(P: Panel, t: int) -> dict[str, np.ndarray]:
    """MOM_12_1, MOM_12_7, REV_1M, VOL_3M, MAX_1M, TURN_1M, ADV20 at the close of t (NaN unless listed at t)."""
    CL, E, N = P.cumlog, P.exists, len(P.codes)
    nan = np.full(N, np.nan)
    out: dict[str, np.ndarray] = {}
    with np.errstate(invalid="ignore", divide="ignore"):
        if t >= 252:
            ok = E[t] & E[t - 252]
            out["MOM_12_1"] = np.where(ok, np.expm1(CL[t - 21] - CL[t - 252]), np.nan)
            out["MOM_12_7"] = np.where(ok, np.expm1(CL[t - 126] - CL[t - 252]), np.nan)
        else:
            out["MOM_12_1"] = out["MOM_12_7"] = nan
        out["REV_1M"] = np.where(E[t], np.expm1(CL[t] - CL[t - 21]), np.nan) if t >= 21 else nan
        r = np.where(P.valid, P.ret.astype(np.float64), np.nan)
        w = r[max(0, t - 62):t + 1]
        out["VOL_3M"] = np.where(_window_count(np.isfinite(w)) >= 40, _nanstd1(w), np.nan)
        w = r[max(0, t - 20):t + 1]
        out["MAX_1M"] = np.where(_window_count(np.isfinite(w)) >= 15, _nanmax(w), np.nan)
        rows = slice(max(0, t - 20), t + 1)
        okm = E[rows] & (P.marcap[rows] > 0)
        turn = np.where(okm, P.amount[rows].astype(np.float64) / np.where(okm, P.marcap[rows], 1.0), np.nan)
        out["TURN_1M"] = np.where(okm.sum(axis=0) >= 15, _nanmean(turn), np.nan)
        rows = slice(max(0, t - 19), t + 1)
        amt = np.where(E[rows], P.amount[rows].astype(np.float64), np.nan)
        out["ADV20"] = np.where(E[rows].sum(axis=0) >= 15, _nanmean(amt), np.nan)
    return {k: np.where(E[t], v, np.nan).astype(np.float32) for k, v in out.items()}


def _nanstd1(w):
    n = np.isfinite(w).sum(axis=0)
    mu = np.where(n > 0, np.nansum(w, axis=0) / np.maximum(n, 1), np.nan)
    ss = np.nansum((w - mu) ** 2, axis=0)
    return np.where(n > 1, np.sqrt(ss / np.maximum(n - 1, 1)), np.nan)


def _nanmax(w):
    return np.where(np.isfinite(w).any(axis=0), np.max(np.where(np.isfinite(w), w, -np.inf), axis=0), np.nan)


def _nanmean(w):
    n = np.isfinite(w).sum(axis=0)
    return np.where(n > 0, np.nansum(w, axis=0) / np.maximum(n, 1), np.nan)


# --------------------------------------------------------------------------- #
# Ranking primitives (K03 46-71; R04 39-67)
# --------------------------------------------------------------------------- #
def quantile_groups(s, U, nq: int, k: int = 0) -> np.ndarray:
    """Group 1..nq (1 = lowest) of s inside U on finite values; 0 = not assigned (fewer than nq*5 names).
    Average ranks, group = floor((rank - 0.5)/n * nq) + 1; a tie block that leaves a group under half its normal
    size is broken by a seeded draw (seed 20261002 + k), exactly as the lab."""
    s = np.asarray(s)
    g = np.zeros(s.shape, np.int8)
    m = np.asarray(U, bool) & np.isfinite(s)
    n = int(m.sum())
    if n < nq * 5:
        return g
    x = s[m].astype(np.float64)
    r = rankdata(x, method="average")
    gm = np.floor((r - 0.5) / n * nq).astype(np.int64) + 1
    if np.bincount(gm, minlength=nq + 1)[1:].min() < 0.5 * n / nq:
        u = np.random.default_rng(LAB_SEED + int(k)).random(s.shape[0])[m]
        r2 = np.empty(n)
        r2[np.lexsort((u, x))] = np.arange(1, n + 1)
        gm = np.floor((r2 - 0.5) / n * nq).astype(np.int64) + 1
    g[m] = gm
    return g


def top_frac(x, U, frac: float) -> np.ndarray:
    """Top `frac` of x inside U: average ranks, (rank - 0.5)/n >= 1 - frac; none below 25 names."""
    x = np.asarray(x)
    out = np.zeros(x.shape, bool)
    m = np.asarray(U, bool) & np.isfinite(x)
    n = int(m.sum())
    if n < 25:
        return out
    out[m] = (rankdata(x[m].astype(np.float64), method="average") - 0.5) / n >= 1.0 - frac
    return out


def p6_composite(vol_3m, max_1m, turn_1m, U, frac: float = 0.10) -> np.ndarray:
    """F4 lottery composite: pct-rank(-VOL_3M) + pct-rank(-MAX_1M) + pct-rank(-TURN_1M) (average ranks over U,
    all three finite), ascending stable sort (most lottery-like first), ordinal cut of exactly floor(frac * n)."""
    U = np.asarray(U, bool)
    parts = []
    for x in (vol_3m, max_1m, turn_1m):
        x = np.asarray(x).astype(np.float64)
        m = U & np.isfinite(x)
        r = np.full(x.shape, np.nan)
        r[m] = rankdata(-x[m], method="average") / m.sum()
        parts.append(r)
    comp = parts[0] + parts[1] + parts[2]
    idx = np.flatnonzero(U & np.isfinite(comp))
    out = np.zeros(U.shape, bool)
    if idx.size:
        order = idx[np.argsort(comp[idx], kind="stable")]
        out[order[np.arange(1, idx.size + 1) / idx.size <= frac]] = True
    return out


# --------------------------------------------------------------------------- #
# Dilution (R01 178-191; QA C4-3, C4-4) and attention-fade events (R01 155-170)
# --------------------------------------------------------------------------- #
def _prev(a: np.ndarray, fill) -> np.ndarray:
    out = np.empty_like(a)
    out[0] = fill
    out[1:] = a[:-1]
    return out


def share_change_terms(P: Panel) -> dict[str, np.ndarray]:
    """Daily float64 terms: s_d (share ratio), p_d (raw close ratio), `split_like`, `lit` = ln s on non-split-like
    change days, `ni` = net-issuance term. s_d = Stocks_d/Stocks_{d-1} when the code exists on d and on the previous
    session with both counts > 0, else 1; p_d = Close_d/Close_{d-1} (previous close > 0), else 1; change day iff
    |s - 1| > 0.001; split-like iff change and |s - 1| > 0.05 (strict) and |s p - 1| <= 0.05 (inclusive)."""
    E, Ep = P.exists, _prev(P.exists, False)
    stk = P.shares.astype(np.float64)
    stkp = _prev(stk, np.nan)
    close = P.close.astype(np.float64)
    closep = _prev(close, np.nan)
    cr = (P.cr if P.cr is not None else P.ret).astype(np.float64)
    with np.errstate(invalid="ignore", divide="ignore"):
        s = np.where(E & Ep & (stkp > 0) & (stk > 0), stk / stkp, 1.0)
        p = np.where(E & Ep & (closep > 0), close / closep, 1.0)
        chg = np.abs(s - 1.0) > 0.001
        split = chg & (np.abs(s - 1.0) > 0.05) & (np.abs(s * p - 1.0) <= 0.05)
        lit = np.where(chg & ~split, np.log(s), 0.0)
        a = np.where(E & Ep & (closep > 0) & np.isfinite(cr), (1.0 + cr) / p, 1.0)
        a = np.where(np.abs(a - 1.0) > 0.005, a, 1.0)
        ni = np.where(chg, np.log(s), 0.0) - np.log(np.where(a > 0, a, 1.0))
    return {"s": s, "p": p, "change": chg, "split_like": split, "lit": np.nan_to_num(lit), "ni": np.nan_to_num(ni)}


def dilution_at(P: Panel, t: int, *, window: int = 252, terms: dict | None = None) -> dict[str, np.ndarray]:
    """DIL_LIT and DIL_NI at the close of t: expm1 of the difference of float64 cumulative sums over t-251..t,
    stored as float32; NaN when the code does not exist at t."""
    terms = terms or share_change_terms(P)
    out = {}
    for key, name in (("lit", "DIL_LIT"), ("ni", "DIL_NI")):
        cs = np.cumsum(terms[key], axis=0)
        tot = cs[t] - (cs[t - window] if t >= window else 0.0)
        out[name] = np.where(P.exists[t], np.expm1(tot), np.nan).astype(np.float32)
    return out


def dilution_flag(dil_lit, threshold: float = DIL_THRESHOLD) -> np.ndarray:
    """F6: the float32-stored DIL_LIT compared in float64, strictly, with 0.10; missing -> not flagged. A 10.0%
    increase stores as float32 0.1 = 0.100000001 and IS flagged (QA C4-3; 368 lab members sit on that tie).
    The float64 promotion is explicit: numpy >= 2 would otherwise compare in float32 and drop the tie."""
    stored = np.asarray(dil_lit, dtype=np.float64).astype(np.float32).astype(np.float64)
    return np.nan_to_num(stored, nan=0.0) > float(threshold)


def attention_fade_events(P: Panel) -> np.ndarray:
    """F5 daily events (E7; R01 155-170): volume spike (>= 5x the mean of the previous 20 listed rows, >= 15 rows,
    with r >= +5%) | locked limit-up close by E7's written thresholds (>= 29.5% from 2015-06-15, >= 14.5% before,
    close >= high) | 20-session run-up >= +50%. DROP as a monthly screen (DNB-TF-01); kept for F8 and audits."""
    E = P.exists
    vol = np.where(E, np.nan_to_num(P.volume.astype(np.float64)), 0.0)
    cs_v = np.vstack([np.zeros((1, vol.shape[1])), np.cumsum(vol, axis=0)])
    cs_n = np.vstack([np.zeros((1, vol.shape[1])), np.cumsum(E, axis=0)])
    T = vol.shape[0]
    lo = np.maximum(np.arange(T) - 20, 0)
    s20, n20 = cs_v[np.arange(T)] - cs_v[lo], cs_n[np.arange(T)] - cs_n[lo]     # rows d-20..d-1
    r = P.ret.astype(np.float64)
    cr = (P.cr if P.cr is not None else P.ret).astype(np.float64)
    with np.errstate(invalid="ignore", divide="ignore"):
        vavg = np.where(n20 >= 15, s20 / np.maximum(n20, 1), np.nan)
        vspike = E & (vol > 0) & (vol >= 5.0 * vavg) & (r >= 0.05)
        CL = P.cumlog
        r20 = np.zeros_like(E)
        r20[20:] = E[20:] & E[:-20] & (np.expm1(CL[20:] - CL[:-20]) >= 0.5)
        thr = np.array([0.295 if d >= LIMIT_CHANGE else 0.145 for d in P.dates])[:, None]
        lu_e7 = E & (P.volume > 0) & (P.close >= P.high) & (cr >= thr)
    return vspike | lu_e7 | r20


def f5_flag(events: np.ndarray, E_t: np.ndarray, t: int, window: int = 20) -> np.ndarray:
    """F5 at the close of t: listed at t and any event in t-19..t."""
    return E_t & events[max(0, t - window + 1):t + 1].any(axis=0)


# --------------------------------------------------------------------------- #
# Screens F1..F8 (R04 76-88) and the book-type weights (CR-06)
# --------------------------------------------------------------------------- #
def screen_flags(feat: Mapping[str, np.ndarray], U, k: int, *, dil_lit=None, f5=None) -> dict[str, np.ndarray]:
    """F1/F2/F3 = top quintile of TURN_1M / VOL_3M / MAX_1M inside U; F4 = P6 composite at 10%; F6 = DIL_LIT > 0.10;
    F5 = attention-fade (DROP as a monthly screen); F7 = F1|F2|F3; F8 = F4|F5|F6 (when F5 and F6 inputs are given).
    Every flag is ANDed with U: a filter is a property of the stock inside ALL, not of the base book."""
    U = np.asarray(U, bool)
    fl = {"F1": (quantile_groups(feat["TURN_1M"], U, 5, k) == 5) & U,
          "F2": (quantile_groups(feat["VOL_3M"], U, 5, k) == 5) & U,
          "F3": (quantile_groups(feat["MAX_1M"], U, 5, k) == 5) & U,
          "F4": p6_composite(feat["VOL_3M"], feat["MAX_1M"], feat["TURN_1M"], U, 0.10) & U}
    fl["F7"] = fl["F1"] | fl["F2"] | fl["F3"]
    if dil_lit is not None:
        fl["F6"] = dilution_flag(dil_lit) & U
    if f5 is not None:
        fl["F5"] = np.asarray(f5, bool) & U
    if dil_lit is not None and f5 is not None:
        fl["F8"] = fl["F4"] | fl["F5"] | fl["F6"]
    return fl


def screen_mask(flag, book_type: str) -> tuple[np.ndarray, int]:
    """(names to exclude, CR-06 weight) for a book type: 3 EW / small-mid, 1 capped CW (hygiene), 0 top 200 (the
    screen is not applied). The weight is a prior pending a gate PASS; nothing here feeds a displayed book."""
    if book_type not in SCREEN_WEIGHT:
        raise ValueError(f"book_type {book_type!r} not in {tuple(SCREEN_WEIGHT)}")
    w = SCREEN_WEIGHT[book_type]
    flag = np.asarray(flag, bool)
    return (flag.copy() if w else np.zeros_like(flag)), w


def reversal_guard(rev_1m, U, frac: float = 0.10) -> np.ndarray:
    """FS-5: exclude last month's top-decile winners (top 10% of REV_1M inside U). Screen variant, weight 1,
    FORWARD-SIM; gated like SCR-1 once the R2-style race exists (no lab test yet)."""
    return top_frac(rev_1m, U, frac)


# --------------------------------------------------------------------------- #
# INV-2 limit-lock detection (R01 12-15, 155-158)
# --------------------------------------------------------------------------- #
# Lab limit eras (fractions), verified from the data: KOSPI 6% < 1996-11-25 <= 8% < 1998-03-02 <= 12% < 1998-12-07
# <= 15% < 2015-06-15 <= 30%; KOSDAQ 8% < 1998-05-25 <= 12% < 2005-03-28 <= 15% < 2015-06-15 <= 30%.
LAB_LIMIT_ERAS = {
    KOSPI: (0.06, ((date(1996, 11, 25), 0.08), (date(1998, 3, 2), 0.12), (date(1998, 12, 7), 0.15),
                   (LIMIT_CHANGE, 0.30))),
    KOSDAQ: (0.08, ((date(1998, 5, 25), 0.12), (date(2005, 3, 28), 0.15), (LIMIT_CHANGE, 0.30))),
}


def lab_price_limit(market: int, d: date) -> float:
    first, eras = LAB_LIMIT_ERAS[market]
    i = bisect_right([e[0] for e in eras], d)
    return first if i == 0 else eras[i - 1][1]


def regime_price_limit(tags_fn: Callable | None = None) -> Callable[[int, date], float]:
    """Limit source from the R-20 regime tags: KOSPI reads `regime_tags('KR', d)['price_limit']` (owner-signed
    file; an unsigned file raises); the KR tag file carries the KOSPI schedule only, so KOSDAQ keeps the lab eras."""
    def limit(market: int, d: date) -> float:
        if market != KOSPI:
            return lab_price_limit(market, d)
        fn = tags_fn
        if fn is None:
            from core.calendars.regime import regime_tags as fn
        v = fn("KR", d)["price_limit"]
        if v is None:
            raise ValueError(f"regime price_limit is null on {d} (owner input)")
        return float(v)
    return limit


def limit_lock_mask(P: Panel, *, limit_of: Callable[[int, date], float] = lab_price_limit
                    ) -> tuple[np.ndarray, np.ndarray]:
    """(lu_lock, ld_lock) daily: listed and traded, close >= high (<= low), r > 0 (< 0) and ChangeCode 4 (5) or
    |r| >= L - 0.5 pp, L = the stock's market limit on day d (raw ChangesRatio; ChangeCode 4/5 absent in 2026)."""
    L = np.zeros(P.close.shape)
    for i, d in enumerate(P.dates):
        for m in (KOSPI, KOSDAQ):
            sel = P.market[i] == m
            if sel.any():
                L[i, sel] = 100.0 * limit_of(m, d)
    cr = (P.cr if P.cr is not None else P.ret).astype(np.float64)
    cc = P.change_code if P.change_code is not None else np.zeros(P.close.shape, np.int8)
    live = P.exists & (P.volume > 0) & (L > 0)
    with np.errstate(invalid="ignore"):
        lu = live & (P.close >= P.high) & (cr > 0) & ((cc == 4) | (cr * 100.0 >= L - 0.5))
        ld = live & (P.close <= P.low) & (cr < 0) & ((cc == 5) | (cr * 100.0 <= -(L - 0.5)))
    return lu, ld


def limit_lock_audit(mem_prev, mem, lu_t, ld_t) -> tuple[float, float]:
    """(share of entries bought at a locked limit-up close, share of exits sold at a locked limit-down close)."""
    mem_prev, mem = np.asarray(mem_prev, bool), np.asarray(mem, bool)
    new, out = mem & ~mem_prev, mem_prev & ~mem
    e = float((new & lu_t).sum() / new.sum()) if new.any() else float("nan")
    x = float((out & ld_t).sum() / out.sum()) if out.any() else float("nan")
    return e, x


# --------------------------------------------------------------------------- #
# ML-1 L0 composite (CR-11; R3:333-338)
# --------------------------------------------------------------------------- #
def l0_composite(features: Mapping[str, np.ndarray], signs: Mapping[str, int], U) -> np.ndarray:
    """Equal-weight mean of cross-sectional z-scores (inside U, population sd) times signs fixed in advance;
    NaN unless every feature is finite. Every feature needs a declared sign in {-1, +1} and no sign may be unused."""
    if set(features) != set(signs):
        raise ValueError(f"ML-1: signs must be fixed in advance for exactly the features "
                         f"(features {sorted(features)}, signs {sorted(signs)})")
    if any(v not in (-1, 1) for v in signs.values()):
        raise ValueError(f"ML-1: signs must be -1 or +1, got {dict(signs)}")
    U = np.asarray(U, bool)
    zs = []
    for name in sorted(features):
        x = np.asarray(features[name], dtype=np.float64)
        m = U & np.isfinite(x)
        z = np.full(x.shape, np.nan)
        sd = x[m].std() if m.sum() >= 2 else 0.0
        if sd > 0:
            z[m] = (x[m] - x[m].mean()) / sd
        zs.append(signs[name] * z)
    return np.mean(zs, axis=0)


# --------------------------------------------------------------------------- #
# RISK-1 pair share (CR-07; r3_01_pair_share.py) and the rebuilt KOSPI (QA C4-7)
# --------------------------------------------------------------------------- #
def pair_share_from_totals(samsung_common: float, samsung_pref: float, skhynix: float, all_lines: float,
                           common_only: float) -> dict[str, float]:
    """CR-07 and the three alternatives (display only; one pre-registered denominator is an owner decision)."""
    pair = samsung_common + skhynix
    return {"CR07_pair_incl_pref_over_all_lines": (pair + samsung_pref) / all_lines,
            "alt_pair_common_over_all_lines": pair / all_lines,
            "alt_pair_common_over_common_only": pair / common_only,
            "alt_pair_incl_pref_over_common_plus_pref": (pair + samsung_pref) / (common_only + samsung_pref)}


def pair_share_kospi(marcaps: Mapping) -> dict[str, float]:
    """Pair shares from one session's KOSPI market caps by code (every listed KOSPI line, preferred included):
    CR-07 = (005930 + 005935 + 000660) / all KOSPI lines; common lines = codes ending in '0'."""
    m = {pad_code(c): float(v) for c, v in marcaps.items()}
    missing = [c for c in PAIR_CODES if c not in m]
    if missing:
        raise ValueError(f"pair_share_kospi: {missing} not among the KOSPI lines")
    return pair_share_from_totals(m["005930"], m["005935"], m["000660"], sum(m.values()),
                                  sum(v for c, v in m.items() if c[-1] == "0"))


def pair_share_summary(dates, shares, threshold: float = 0.45) -> dict:
    """First session above `threshold`, its share, the peak session and share, and the count above (display)."""
    sh = np.asarray(shares, dtype=float)
    above = np.flatnonzero(sh > threshold)
    peak = int(np.nanargmax(sh))
    return {"first_above": dates[above[0]] if above.size else None,
            "first_share": float(sh[above[0]]) if above.size else None,
            "peak_date": dates[peak], "peak_share": float(sh[peak]), "n_above": int(above.size), "n": int(sh.size)}


def rebuilt_kospi(P: Panel, *, base: tuple[date, float] | None = REBUILT_KOSPI_BASE) -> tuple[np.ndarray, np.ndarray]:
    """(daily return, level) of the rebuilt KOSPI: ret_d = sum Marcap_{i,d-1} r_{i,d} / sum Marcap_{i,d-1} over lines
    listed on KOSPI at d-1 that exist at d with a finite cleaned return (zero-volume days included; not the VALID
    set), Marcap_{d-1} > 0 and a code ending in '0', of any name class; level scaled to `base` (official close
    2,064.85 on 2007-10-31). ret[0] is NaN."""
    Ep, mkp = _prev(P.exists, False), _prev(P.market, 0)
    mcp = _prev(P.marcap.astype(np.float64), np.nan)
    r = P.ret.astype(np.float64)
    ok = Ep & (mkp == KOSPI) & P.exists & np.isfinite(r) & (mcp > 0) & P.common[None, :]
    w = np.where(ok, mcp, 0.0)
    den = w.sum(axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        ret = np.where(den > 0, (w * np.nan_to_num(r)).sum(axis=1) / den, np.nan)
    ret[0] = np.nan
    level = np.cumprod(1.0 + np.nan_to_num(ret))
    if base is not None:
        if base[0] not in P.dates:
            raise ValueError(f"rebuilt_kospi: base date {base[0]} not in the panel")
        level = level / level[P.dates.index(base[0])] * base[1]
    return ret, level
