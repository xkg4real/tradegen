"""Factor sleeves (v2.0 milestone M4): R-03 sleeve_vol_scale, R-04 dm_gate, R-05 fixed 1.0x, R-15 admissibility and
base weights, family tags (section 3.7), apply_overlays and the two book builders (section 3.3).

Rule ids implemented: R-03 (revisions 1-3), R-04 (specification book only), R-05, R-15, R-02 family level, P1/P2/P8.
Composition is `min()` only; vs in [0, 1]; overlays in [0.5, 1]; nothing above 1.0; no renormalisation of freed budget
(the one logged exception is the R-15 K/(K-1) re-weight). Every acting read goes through `pit_value` / `pit_window`
with a consumer binding and an explicit `decision_utc` / `knowledge_utc`; nothing here reads a clock.

Conservative readings (brief spec_M4_sleeves F-01..F-23): every composite component stays untagged until the owner
confirms BL-G07; the R-15 prior table is shipped as module data (the rules store carries `weights_prior: see_R-15`);
no sleeve registry exists in production, so callers pass their `Sleeve` objects; in the recommended book every macro
card is NOT_RUN, so vs and dm enter as 1.0 and ts_trend keeps its K slot at zero budget (F-04).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
from datetime import date, datetime, timedelta, timezone
from typing import Mapping, Sequence

import numpy as np

from core.ficc import pit as P
from core.quant import risk_layer as RL
from core.rules.macro_rules import BASES, MacroRefusal, assert_overlay, assert_vs, assert_vt
from core.rules.validation import Issue, Report, Severity

FAMILIES = ("momentum", "reversal", "flow", "quality", "ts_trend")
FIXED_ONE = ("reversal", "quality", "flow")                # R-05 + config families.{reversal,quality,flow}.overlay
FACTORS = ("overlay", "vs", "vt", "ladder", "post_rearm_cap")
SLEEVE_KINDS = ("long_only", "long_short")
BOOK_KINDS = ("recommended", "specification")
VERDICTS = ("PASS", "REVISE", "REJECT", "INSUFFICIENT_DATA", "NOT_RUN")
RECOMMENDED_DISPOSITIONS = ("RECOMMENDATION", "BUILD_AS_INSURANCE", "INVARIANT_STEP")
REFUSED_IN_RECOMMENDED = ("SPECIFICATION_ONLY", "FORWARD_SIM", "REFUSAL_BOOK")

# R-03 / R-04 parameters (rules store families.momentum.*; L1518-1520, L1536-1537)
VS_WINDOW, VS_TARGET, VS_CAP, VS_MIN_OBS, VS_MEDIAN_MIN_OBS, ANN_DAYS = 126, 0.12, 1.0, 126, 252, 252
DM_MONTHS, DM_VOL_WINDOW, DM_QUANTILE, DM_QUANTILE_MIN_OBS, DM_MULTIPLIER = 24, 126, 2.0 / 3.0, 252, 0.5
R03_CARD = {"card_id": "MACRO-R03-US-MOM", "class": "CARD-O", "verdict": "NOT_RUN", "disposition": "DESCRIPTIVE",
            "displayed_as": "descriptive", "label": "indicative PASS; step 3 borderline", "results_md5": None}
R04_CARD = {"card_id": "MACRO-R04-US-DM", "class": "CARD-O", "verdict": "NOT_RUN", "disposition": "SPECIFICATION_ONLY",
            "displayed_as": "descriptive", "label": "step 3 FAIL (indicative)", "results_md5": None}
# Derived PIT series per (market, family) / market (registry: data/macro/series_registry.yaml; F-13: one id today)
PAPER_SERIES = {("US", "momentum"): "MOM_PAPER_LS_SERIES"}
DM_SERIES = {"US": ("DM_MKT_RET_24M", "DM_MKT_VOL_126")}

# --------------------------------------------------------------------------- #
# Family tags (section 3.7, BL-G07): effective tags are all "" until the owner or council confirm the proposal.
# --------------------------------------------------------------------------- #
TAG_STATUS = "proposed"
FAMILY_TAGS = {"trend50": "", "trend200": "", "momentum": "", "rsi": "", "macd": "", "vol": ""}
PROPOSED_TAGS = {"trend50": "ts_trend", "trend200": "ts_trend", "momentum": "ts_trend", "rsi": "reversal",
                 "macd": "ts_trend", "vol": ""}


def family_of(component) -> str:
    """The component's family tag ("" = untagged: no family overlay, still under vt and the risk layer)."""
    tag = getattr(component, "family", "") or ""
    if tag not in FAMILIES and tag != "":
        raise MacroRefusal(f"family tag {tag!r} not in {FAMILIES}")
    return tag


def tag_components(components, tags: Mapping[str, str] = FAMILY_TAGS):
    """Re-tag `SignalComponent`s from a tag map (the rules-store revision); unknown keys stay untagged."""
    out = []
    for c in components:
        tag = tags.get(c.key, "") or ""
        if tag not in FAMILIES and tag != "":
            raise MacroRefusal(f"family tag {tag!r} for {c.key} not in {FAMILIES}")
        out.append(replace(c, family=tag))
    return tuple(out)


# --------------------------------------------------------------------------- #
# Result objects
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class VSResult:
    """R-03 own-vol scale of one sleeve; `value` in [0, 1] (factor "vs", exposure_basis active)."""
    rule_id: str
    market: str
    family: str
    revision: int
    sigma126_ann: float | None
    target_ann: float | None
    value: float
    status: str                     # ok | warmup | fixed_1.0 | not_run
    exposure_basis: str = "active"
    applies_to: str = ""
    inputs: tuple = ()
    reasons: tuple[str, ...] = ()
    card: dict = field(default_factory=lambda: dict(R03_CARD))
    factor: str = "vs"
    book: str = "specification"
    n_valid: int = 0

    def __post_init__(self) -> None:
        assert_vs(self.value)
        if self.exposure_basis not in BASES:
            raise MacroRefusal(f"{self.rule_id}: exposure_basis {self.exposure_basis!r} not in {BASES} (P8)")


@dataclass(frozen=True)
class Multiplier:
    """One multiplier record (overlay_decision.multipliers[] item). Bounds by factor: overlay [0.5, 1]; vt/vs [0, 1];
    ladder and post_rearm_cap in {0.5, 1.0}. `exposure_basis` is mandatory (P8)."""
    rule_id: str
    value: float
    exposure_basis: str
    applies_to: str                 # family or market_gross
    status: str = "ok"
    book: str = "specification"
    reasons: tuple[str, ...] = ()
    inputs: tuple = ()
    card: dict = field(default_factory=dict)
    factor: str = "overlay"
    flags: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.exposure_basis not in BASES:
            raise MacroRefusal(f"{self.rule_id}: exposure_basis {self.exposure_basis!r} not in {BASES} (P8)")
        if self.factor not in FACTORS:
            raise MacroRefusal(f"{self.rule_id}: factor {self.factor!r} not in {FACTORS}")
        if self.factor == "overlay":
            assert_overlay(self.value)
        elif self.factor == "vt":
            assert_vt(self.value)
        elif self.factor == "vs":
            assert_vs(self.value)
        elif self.value not in (0.5, 1.0):
            raise MacroRefusal(f"{self.rule_id}: {self.factor} must be 0.5 or 1.0, got {self.value!r}")
        if self.factor == "vt" and self.applies_to != "market_gross":
            raise MacroRefusal(f"{self.rule_id}: vt applies to market_gross only, not {self.applies_to!r} (T-BASIS-01)")
        if self.applies_to == "ts_trend":
            raise MacroRefusal(f"{self.rule_id}: no multiplier on ts_trend (R-14 exempt; T-BASIS-01)")


@dataclass(frozen=True)
class Sleeve:
    """A (market, family) sleeve: instrument weights with the sleeve's own ranking; long-only sleeves carry their
    benchmark (freed active budget moves toward it), long/short sleeves move toward zero (L893)."""
    market: str
    family: str
    kind: str                       # long_only | long_short
    weights: dict                   # instrument -> weight (long-only: >= 0, sum 1; L/S: long +1, short -1)
    benchmark: dict | None = None   # long-only only
    base_weight: float = 0.0
    variant: str | None = None      # prior sub-index (F-20), e.g. "12-7_residual", "KOSPI", "DAX"

    def __post_init__(self) -> None:
        if self.family not in FAMILIES:
            raise MacroRefusal(f"sleeve family {self.family!r} not in {FAMILIES}")
        if self.kind not in SLEEVE_KINDS:
            raise MacroRefusal(f"sleeve kind {self.kind!r} not in {SLEEVE_KINDS}")
        if self.kind == "long_short" and self.benchmark:
            raise MacroRefusal("a long/short sleeve has no benchmark (its freed budget moves to zero)")
        if self.kind == "long_only" and any(w < 0 for w in self.weights.values()):
            raise MacroRefusal("a long-only sleeve has no negative weight")
        if not 0.0 <= self.base_weight <= 1.0:
            raise MacroRefusal(f"base_weight {self.base_weight!r} outside [0, 1]")

    @property
    def key(self) -> tuple[str, str]:
        return (self.market, self.family)


@dataclass(frozen=True)
class Weights:
    """Instrument weights of one sleeve after `apply_overlays`, with the binding log (L897)."""
    market: str
    family: str
    basis: str
    weights: dict
    factor: float                   # active: vs x min(1, overlays); total: gross
    vs: float
    overlay_min: float
    multipliers: tuple
    binding: tuple[str, ...]
    reasons: tuple[str, ...]
    label: str = ""
    kind: str = "long_only"


@dataclass(frozen=True)
class BaseWeights:
    """R-15 base weights for one decision: IV_m x 1/K_m over admissible families (L860-861)."""
    book: str
    weights: dict                   # (market, family) -> base weight
    iv: dict                        # market -> IV_m
    admissible: dict                # market -> tuple of admissible families (K slots)
    events: tuple = ()              # admissibility_reweight events written this decision
    printed: tuple[str, ...] = ()
    fail_closed: bool = False
    status: str = "ok"
    detail: str = ""


@dataclass(frozen=True)
class Book:
    """One book's factor-sleeve weights for a decision."""
    kind: str                       # recommended | specification
    decision_utc: datetime
    sleeves: tuple                  # Weights per sleeve
    weights: dict                   # (market, instrument) -> weight, summed over sleeves
    labels: dict                    # (market, family) -> factor labels
    fail_closed: bool = False
    reasons: tuple[str, ...] = ()

    @property
    def book_ids(self) -> tuple[str, ...]:
        return tuple(sorted({f"{self.kind}:{s.market}" for s in self.sleeves}))


# --------------------------------------------------------------------------- #
# R-03 kernel: own-vol scale on the paper unit-gross long/short returns
# --------------------------------------------------------------------------- #
def sigma126_series(returns, *, window: int = VS_WINDOW, ann_days: int = ANN_DAYS) -> np.ndarray:
    """Annualised rolling sigma over the last `window` VALID returns (excluded days dropped, L1518); NaN before."""
    r = np.asarray(returns, dtype=float)
    r = r[np.isfinite(r)]
    out = np.full(r.size, np.nan)
    for t in range(window - 1, r.size):
        out[t] = float(np.std(r[t - window + 1:t + 1], ddof=1)) * math.sqrt(ann_days)
    return out


def vol_scale_from_returns(returns, *, revision: int = 1, window: int = VS_WINDOW, target_ann: float = VS_TARGET,
                           cap: float = VS_CAP, min_obs: int = VS_MIN_OBS, median_min_obs: int = VS_MEDIAN_MIN_OBS,
                           ann_days: int = ANN_DAYS) -> tuple[float | None, float | None, str]:
    """(vs, sigma126_ann, status); status in {ok, insufficient_history, degenerate_sigma}. Revision 1 fixed target,
    2 expanding median of sigma126 (>= `median_min_obs` sigma observations, F-08), 3 variance-scaled (L1518-1519).
    `cap > 1.0` raises here: cap-2 variants live in tests/reference only (L5992)."""
    if cap > 1.0:
        raise MacroRefusal(f"vol scale cap {cap!r} above 1.0 (P2; L1520, L5992)")
    if revision not in (1, 2, 3):
        raise ValueError(f"R-03 revision {revision!r} not in (1, 2, 3)")
    r = np.asarray(returns, dtype=float)
    r = r[np.isfinite(r)]
    if r.size < min_obs:
        return None, None, "insufficient_history"
    sigma = float(np.std(r[-window:], ddof=1)) * math.sqrt(ann_days)
    if not (math.isfinite(sigma) and sigma > 0):
        return None, sigma, "degenerate_sigma"
    if revision == 2:
        sig = sigma126_series(r, window=window, ann_days=ann_days)
        sig = sig[np.isfinite(sig)]
        if sig.size < median_min_obs:
            return None, sigma, "insufficient_history"
        target_ann = float(np.median(sig))
        vs = min(cap, target_ann / sigma)
    elif revision == 3:
        vs = min(cap, (target_ann / sigma) ** 2)
    else:
        vs = min(cap, target_ann / sigma)
    return assert_vs(float(vs)), sigma, "ok"


def paper_ls_returns(prices, *, lookback: int = 252, skip: int = 21, top: float = 1 / 3, step: int = 21) -> np.ndarray:
    """Daily returns of the paper unit-gross long/short series (+1 / -1, the sleeve's own ranking, cost 0; L1517)."""
    from core.quant import strategies as S          # lazy: strategies pulls pandas-free numpy only, but keep the leaf light
    W = S.xs_momentum(np.asarray(prices, dtype=float), lookback=lookback, skip=skip, top=top, step=step, long_only=False)
    pnl, _ = S.simulate(prices, W, cost_bps=0.0)
    return np.concatenate([[np.nan], pnl])          # aligned with prices: the return earned on session t


def overlay_net_returns(r: np.ndarray, w: np.ndarray, cost_per_side: float, *, legs: int = 2) -> np.ndarray:
    """Net return path of an overlay weight `w` (decided at the close of t, earning r[t+1]): the overlay's own
    turnover |w[t] - w[t-1]| is charged on both legs of an L/S sleeve (`legs = 2`), one leg for long-only, on the day
    the new weight earns; the initial entry is not charged (L1523, section 9.3.1; T-COST-01 clause)."""
    r = np.asarray(r, dtype=float)
    w = np.asarray(w, dtype=float)
    if r.shape != w.shape:
        raise ValueError(f"returns {r.shape} and weights {w.shape} differ")
    out = np.full(r.size, np.nan)
    for t in range(1, r.size):
        cost = cost_per_side * legs * abs(w[t - 1] - w[t - 2]) if t >= 2 else 0.0
        out[t] = w[t - 1] * r[t] - cost
    return out


def years_line(dates: Sequence[date], r_static: np.ndarray, r_scaled: np.ndarray, w: np.ndarray) -> dict:
    """R-03 years line (L1526, G-YRS-01): a year is identical when vs = 1.0 all year; among the differing years count
    the scaled sleeve's higher per-year Sharpe; own-return > 0 share over every year."""
    from core.quant.validate import sharpe
    years = sorted({d.year for d in dates})
    identical, higher, differing, positive = 0, 0, 0, 0
    for y in years:
        idx = np.array([d.year == y for d in dates])
        if np.all(np.asarray(w)[idx] == 1.0):
            identical += 1
        else:
            differing += 1
            higher += sharpe(np.asarray(r_scaled)[idx]) > sharpe(np.asarray(r_static)[idx])
        positive += float(np.nansum(np.asarray(r_scaled)[idx])) > 0
    return {"n_years": len(years), "identical": identical, "differing": differing, "higher": higher,
            "higher_share": higher / differing if differing else float("nan"),
            "positive_share": positive / len(years) if years else float("nan")}


# --------------------------------------------------------------------------- #
# R-03 acting function
# --------------------------------------------------------------------------- #
def _books(value, market: str) -> tuple[str, ...]:
    return tuple(b if ":" in b else f"{b}:{market}" for b in (value.books or ()))


def _stale(value, due: date, books) -> P.MissingInput | None:
    """A derived acting input dated before `due` fails closed as "stale" (P18; spec L3797). The DERIVED schedule has
    no stale deadline (calendars adapter), so the acting function checks the obs_date itself."""
    if value.obs_date >= due:
        return None
    return P.MissingInput(value.series_id, "stale", value.role, books,
                          detail=f"obs_date {value.obs_date} < {due}: the derived writer has not produced the decided value")


def _last_month_end(t: date) -> date:
    return t if (t + timedelta(days=1)).day == 1 else t.replace(day=1) - timedelta(days=1)


def sleeve_vol_scale(store, registry, market: str, family: str, decision_utc: datetime, knowledge_utc: datetime,
                     revision: int = 1, *, armed: bool = False, series_id: str | None = None,
                     target_ann: float = VS_TARGET) -> VSResult | P.MissingInput:
    """vs(m, f) on the paper unit-gross long/short series through the close of t (R-03). `armed` is the bound book's
    "ever ARMED" state (books.ever_armed): fewer than 126 valid returns is warm-up (1.0) only before the first ARMED
    decision and MissingInput("missing") afterwards (L1518, L1111); a degenerate sigma fails closed (F-06). Every
    family but momentum is fixed at 1.0 (R-05; L867); ts_trend is exempt (R-14)."""
    if family not in FAMILIES:
        raise MacroRefusal(f"family {family!r} not in {FAMILIES}")
    if family != "momentum":
        return VSResult("R-03", market, family, revision, None, None, 1.0, "fixed_1.0", applies_to=family,
                        reasons=(f"VS: {family} has no own-vol scale (R-05 fixed 1.0)",))
    sid = series_id or PAPER_SERIES.get((market, family))
    if sid is None:
        return P.MissingInput(f"MOM_PAPER_LS_SERIES:{market}", "missing", "acting_exposure", (f"specification:{market}",),
                              detail=f"no registered paper long/short series for ({market}, {family})")
    latest = P.pit_value(store, sid, decision_utc, knowledge_utc, "R-03", registry=registry)
    if isinstance(latest, P.MissingInput):
        return latest
    books = _books(latest, market)
    stale = _stale(latest, decision_utc.astimezone(timezone.utc).date(), books)      # sigma126 through the close of t
    if stale is not None:
        return stale
    rows = [v for v in P.pit_window(store, sid, decision_utc, knowledge_utc, registry=registry, statuses=P.CLOSE_STATUSES)
            if not v.synthetic]
    vs, sigma, status = vol_scale_from_returns([v.value for v in rows], revision=revision, target_ann=target_ann)
    n = sum(1 for v in rows if math.isfinite(v.value))
    if status == "insufficient_history":
        if not armed:
            return VSResult("R-03", market, family, revision, None, target_ann, 1.0, "warmup", applies_to=family,
                            inputs=(latest,), reasons=(f"VS: {n} valid returns < {VS_MIN_OBS}: warm-up, vs 1.0",), n_valid=n)
        return P.MissingInput(sid, "missing", latest.role, books, detail=f"insufficient_history: {n} valid returns < {VS_MIN_OBS}")
    if status != "ok":
        return P.MissingInput(sid, "missing", latest.role, books, detail=f"sigma126 degenerate ({sigma!r})")
    tgt = target_ann if revision != 2 else vs * sigma
    form = {1: f"min(1, {target_ann:.2f}/{sigma:.3f})", 2: f"min(1, median {tgt:.3f}/{sigma:.3f})",
            3: f"min(1, ({target_ann:.2f}/{sigma:.3f})^2)"}[revision]
    reason = f"VS: sigma126 {sigma * 100:.1f}% -> {form}={vs:.2f}"
    return VSResult("R-03", market, family, revision, sigma, tgt, vs, "ok", applies_to=family, inputs=(latest,),
                    reasons=(reason,), n_valid=n)


# --------------------------------------------------------------------------- #
# R-04 kernel and acting function (specification book only)
# --------------------------------------------------------------------------- #
def dm_from_inputs(r24, sigma126_mkt, q23) -> tuple[float, bool, bool]:
    """(dm, bear24, hivol): dm = 0.5 iff r24 < 0 and sigma126_mkt > q23, both strict (L1536); any missing input -> 1.0."""
    vals = [r24, sigma126_mkt, q23]
    if any(v is None or not math.isfinite(float(v)) for v in vals):
        return 1.0, False, False
    bear = float(r24) < 0.0
    hivol = float(sigma126_mkt) > float(q23)
    return (DM_MULTIPLIER if (bear and hivol) else 1.0), bear, hivol


def dm_gate(store, registry, market: str, decision_utc: datetime, knowledge_utc: datetime, *, armed: bool = False,
            book: str = "specification", series: tuple[str, str] | None = None) -> Multiplier | P.MissingInput:
    """R-04 Daniel-Moskowitz bear-state gate, {0.5, 1.0}, the momentum family's overlay in the specification book only.
    Inputs `DM_MKT_RET_24M` (24-month return as of the last month-end on or before t) and `DM_MKT_VOL_126` (sigma126 of
    the market through the close of t), consumer "R-04"; the expanding 2/3 quantile needs >= 252 sigma observations
    (warm-up 1.0 before the first ARMED decision, MissingInput afterwards; F-12). Any other book is refused (item 22)."""
    if book != "specification":
        raise MacroRefusal(f"R-04 acts in the specification book only, never {book!r} (L1542, section 10 item 22)")
    ids = series or DM_SERIES.get(market)
    if ids is None:
        return P.MissingInput(f"DM_MKT_RET_24M:{market}", "missing", "acting_exposure", (f"specification:{market}",),
                              detail=f"no registered R-04 inputs for {market}")
    ret_id, vol_id = ids
    r24 = P.pit_value(store, ret_id, decision_utc, knowledge_utc, "R-04", registry=registry)
    if isinstance(r24, P.MissingInput):
        return r24
    vol = P.pit_value(store, vol_id, decision_utc, knowledge_utc, "R-04", registry=registry)
    if isinstance(vol, P.MissingInput):
        return vol
    books = _books(vol, market)
    t = decision_utc.astimezone(timezone.utc).date()
    stale = _stale(vol, t, books) or _stale(r24, _last_month_end(t).replace(day=1), _books(r24, market))
    if stale is not None:
        return stale
    hist = np.array([v.value for v in P.pit_window(store, vol_id, decision_utc, knowledge_utc, registry=registry,
                                                   statuses=P.CLOSE_STATUSES)
                     if not v.synthetic and math.isfinite(v.value)], dtype=float)
    if hist.size < DM_QUANTILE_MIN_OBS:
        if not armed:
            return Multiplier("R-04-DM", 1.0, "active", "momentum", status="warmup", inputs=(r24, vol), card=dict(R04_CARD),
                              reasons=(f"DM: {hist.size} sigma126 observations < {DM_QUANTILE_MIN_OBS}: warm-up, 1.0",),
                              flags={"dm_bear_state": False})
        return P.MissingInput(vol_id, "missing", vol.role, books,
                              detail=f"insufficient_history: {hist.size} sigma126 observations < {DM_QUANTILE_MIN_OBS}")
    q23 = float(np.quantile(hist, DM_QUANTILE))
    dm, bear, hivol = dm_from_inputs(r24.value, vol.value, q23)
    reason = (f"DM: 24m market return {r24.value * 100:+.1f}% {'<' if bear else '>='} 0"
              + (f", sigma126 {vol.value * 100:.1f}% {'>' if hivol else '<='} q2/3 {q23 * 100:.1f}%" if bear else "")
              + f" -> {dm} (specification book only)")
    return Multiplier("R-04-DM", dm, "active", "momentum", status="ok", inputs=(r24, vol), card=dict(R04_CARD),
                      reasons=(reason,), flags={"dm_bear_state": bear, "dm_hivol": hivol, "q23": q23})


# --------------------------------------------------------------------------- #
# R-15 priors, admissibility, base weights
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Prior:
    """An R-15 prior cell: `lo` is the value used for admissibility (a range resolves to its lower bound, a cell with
    variants to the lowest variant unless the sleeve declares one; F-20); None = no registered prior."""
    lo: int | None
    hi: int | None = None
    flag: str = ""
    text: str = ""
    variants: dict | None = None

    def value(self, variant: str | None = None) -> int | None:
        if self.variants:
            if variant is not None:
                if variant not in self.variants:
                    raise MacroRefusal(f"prior variant {variant!r} not in {sorted(self.variants)}")
                return self.variants[variant]
            return min(self.variants.values())
        return self.lo

    @property
    def printed(self) -> str:
        if self.hi is not None and self.hi != self.lo:
            return f"{self.lo}-{self.hi}"
        if self.variants:
            return "; ".join(f"{k} {v}" for k, v in self.variants.items())
        return "none" if self.lo is None else str(self.lo)


# L1722-1732 verbatim cells; flow: Korea 3 (L698, L1718); quality: none anywhere.
PRIORS: dict[tuple[str, str], Prior] = {
    ("US", "momentum"): Prior(1, text="2 if vol-scaled with the D&M gate, else 1", flag="ONE-SIDED (N-35)"),
    ("US", "reversal"): Prior(1, text="1 (prior)"), ("US", "ts_trend"): Prior(3),
    ("EU", "momentum"): Prior(3), ("EU", "reversal"): Prior(1, text="1 (prior)"),
    ("EU", "ts_trend"): Prior(0, 1, text="0-1 (STOXX50 0, DAX 1, FTSE 0-1)", variants={"STOXX50": 0, "DAX": 1, "FTSE": 0}),
    ("JP", "momentum"): Prior(0, text="0 (vol-scaled R4 SR 0.196: may rise to 1 if verified)"),
    ("JP", "reversal"): Prior(2, text="2 (prior)"), ("JP", "ts_trend"): Prior(1, 2),
    ("KR", "momentum"): Prior(0, text="12-1: 0; 12-7 / residual: 1", variants={"12-1": 0, "12-7_residual": 1}),
    ("KR", "reversal"): Prior(1, flag="UNVERIFIED", text="1 (v2.0; was 3): UNVERIFIED until BL-U02 runs net of 35 bp plus the 0.20% sell tax"),
    ("KR", "ts_trend"): Prior(0, text="KOSPI 1, KOSDAQ 0", variants={"KOSPI": 1, "KOSDAQ": 0}),
    ("KR", "flow"): Prior(3, text="section 2.2 prior"),
    ("TW", "momentum"): Prior(1, text="1 (prior)"), ("TW", "reversal"): Prior(3, text="3 (prior)"), ("TW", "ts_trend"): Prior(1, 2),
    ("CN", "momentum"): Prior(0, text="0 (prior)"), ("CN", "reversal"): Prior(3, text="3 (prior)"), ("CN", "ts_trend"): Prior(0),
    ("IN", "momentum"): Prior(3, text="3 (prior)"), ("IN", "reversal"): Prior(1, text="1 (prior)"), ("IN", "ts_trend"): Prior(1),
    ("EM", "momentum"): Prior(3), ("EM", "reversal"): Prior(1, text="1 (prior)"), ("EM", "ts_trend"): Prior(None, text="no registered prior"),
    ("CRYPTO", "momentum"): Prior(1, text="1 (prior)"), ("CRYPTO", "reversal"): Prior(2, text="2 (prior)"),
    ("CRYPTO", "ts_trend"): Prior(2, text="own trend plus vol cap; card C3 is the trend part"),
}
PRIOR_MIN = 1


def prior_value(market: str, family: str, variant: str | None = None, priors: Mapping = PRIORS) -> int | None:
    p = priors.get((market, family))
    return None if p is None else p.value(variant)


def is_admissible(market: str, family: str, verdict: str = "NOT_RUN", *, variant: str | None = None,
                  priors: Mapping = PRIORS) -> bool:
    """prior >= 1 and card not REJECT (L860, L1713); no registered prior -> not admissible; NOT_RUN stays admissible."""
    if verdict not in VERDICTS:
        raise MacroRefusal(f"verdict {verdict!r} not in {VERDICTS}")
    v = prior_value(market, family, variant, priors)
    return v is not None and v >= PRIOR_MIN and verdict != "REJECT"


def check_tilts(tilts: Sequence[Mapping], cards: Mapping) -> Report:
    """A bounded tilt is allowed only after the family's own card passes (L1719; base_weights.tilt_requires_family_card_pass)."""
    issues = []
    for i, t in enumerate(tilts):
        key = (t.get("market"), t.get("family"))
        verdict = _verdict(cards, key, t.get("family_card_id"))
        if verdict != "PASS":
            issues.append(Issue(f"tilts[{i}]", f"tilt on {key} refused: family card {t.get('family_card_id')!r} is "
                                                f"{verdict}, not PASS (R-15; base_weights.tilt_requires_family_card_pass)",
                                Severity.ERROR))
        if t.get("value") is not None and not 0.0 <= float(t["value"]) <= 1.0:
            issues.append(Issue(f"tilts[{i}]", "a tilt never lifts a weight above 1.0 (P2)", Severity.ERROR))
    return Report(tuple(issues))


def check_fixed_family(rule, store=None) -> Report:
    """R-05: a multiplier on reversal, quality or flow is refused in every state; a calm-state reversal down-weight is
    refused while owner decision D3 (`families.reversal.calm_state_downweight`) is `not_adopted` (L1550, L1740, P3)."""
    applies = getattr(rule, "applies_to", None) if not isinstance(rule, Mapping) else rule.get("applies_to")
    factor = getattr(rule, "factor", "overlay") if not isinstance(rule, Mapping) else rule.get("factor", "overlay")
    rid = getattr(rule, "rule_id", None) if not isinstance(rule, Mapping) else rule.get("rule_id")
    if applies not in FIXED_ONE or factor == "none":
        return Report()
    d3 = store.get("families.reversal.calm_state_downweight") if store is not None else "not_adopted"
    msg = f"{rid}: {applies} carries no overlay multiplier, fixed 1.0 in every state (R-05, families.{applies}.overlay)"
    if applies == "reversal":
        msg += f"; calm-state down-weight {d3} (owner decision D3, P3)"
    return Report((Issue("applies_to", msg, Severity.ERROR),))


def _verdict(cards: Mapping | None, key, card_id: str | None = None) -> str:
    if not cards:
        return "NOT_RUN"
    c = cards.get(key)
    if c is None and card_id is not None:
        c = cards.get(card_id)
    if c is None:
        return "NOT_RUN"
    v = c.get("verdict", "NOT_RUN") if isinstance(c, Mapping) else str(c)
    if v not in VERDICTS:
        raise MacroRefusal(f"verdict {v!r} not in {VERDICTS}")
    return v


def base_weights(store, decision_utc: datetime, knowledge_utc: datetime | None = None, *, sleeves: Sequence[Sleeve],
                 cards: Mapping | None = None, priors: Mapping = PRIORS, book: str = "specification",
                 iv: Mapping[str, float] | None = None, previous: BaseWeights | None = None, governance_log=None,
                 clock=None, registry=None, weekly=None, sessions=None) -> BaseWeights:
    """base_weight(m, f) = IV_m x 1/K_m over the admissible families of market m (R-15, L860-861). `sleeves` are the
    sleeves that exist (F-03: no production registry); IV_m comes from `optimize.inverse_vol_weights` over their markets
    unless `iv` is given. Recommended book: ts_trend keeps its K slot but its budget is 0 until its own PASS (F-04).
    A family that dropped out since `previous` (card REJECT) writes exactly one `admissibility_reweight` event per market
    through the governance appender when `governance_log` is given (L1720). A MissingInput on IV carries `previous`
    with fail_closed = true; with no previous state the book has no factor budget."""
    if book not in BOOK_KINDS:
        raise MacroRefusal(f"book {book!r} not in {BOOK_KINDS}")
    markets = sorted({s.market for s in sleeves})
    if iv is None:
        from core.quant.optimize import inverse_vol_weights
        iv = inverse_vol_weights(markets, decision_utc, store=store, knowledge_utc=knowledge_utc, weekly=weekly,
                                 registry=registry, sessions=sessions)
    if isinstance(iv, P.MissingInput):
        carried = dict(previous.weights) if previous else {}
        return BaseWeights(book, carried, dict(previous.iv) if previous else {}, dict(previous.admissible) if previous else {},
                           fail_closed=True, status=iv.reason, detail=f"{iv.series_id}: {iv.detail or iv.reason}",
                           printed=(f"IV_m fail closed ({iv.series_id} {iv.reason}): previous base weights carried",))
    iv = {m: float(iv[m]) for m in markets} if markets else {}
    if markets:
        assert abs(sum(iv.values()) - 1.0) < 1e-9, "sum IV_m != 1"
    weights: dict[tuple[str, str], float] = {}
    admissible: dict[str, tuple[str, ...]] = {}
    events, printed = [], []
    for m in markets:
        fams = {s.family: s for s in sleeves if s.market == m}
        adm = tuple(f for f in FAMILIES if f in fams and is_admissible(m, f, _verdict(cards, (m, f)), variant=fams[f].variant, priors=priors))
        admissible[m] = adm
        k = len(adm)
        if k:
            assert abs(sum(1.0 / k for _ in adm) - 1.0) < 1e-12
        for f in fams:
            w = iv[m] / k if f in adm else 0.0
            if f == "ts_trend" and book == "recommended" and _verdict(cards, (m, f)) != "PASS":
                w = 0.0                                   # keeps its K slot, zero budget until its own PASS (R-14, F-04)
            weights[(m, f)] = w
            assert 0.0 <= w <= 1.0
        line = f"{m}: IV {iv[m]:.4f}, K {k} ({', '.join(adm) or 'none'})" + "".join(
            f", {f} prior {priors[(m, f)].printed}" for f in fams if (m, f) in priors)
        printed.append(line)
        if previous is not None and m in previous.admissible:
            dropped = [f for f in previous.admissible[m] if f not in adm]
            if dropped and k:
                k_old = len(previous.admissible[m])
                old = {f: previous.weights.get((m, f), 0.0) for f in fams}
                new = {f: weights[(m, f)] for f in fams}
                reason = (f"R-15 admissibility re-weight {m}: {', '.join(dropped)} dropped (card REJECT); K {k_old} -> {k}; "
                          f"other families x {k_old}/{k} = {k_old / k:.4f} (the one logged exception to T-MONO-01)")
                ev = {"kind": "admissibility_reweight", "rule_id": "R-15", "key": f"base_weights.{m}",
                      "book_id": f"{book}:{m}", "actor": "runtime", "reason": reason, "old": old, "new": new,
                      "refs": [f"cards.{m}.{f}" for f in dropped]}
                if governance_log is not None:
                    from core.rules.governance import append_event
                    ev["utc"] = decision_utc.isoformat().replace("+00:00", "Z")
                    append_event(governance_log, ev, clock)
                events.append(ev)
                printed.append(reason + "; old " + ", ".join(f"{f} {v:.5f}" for f, v in old.items())
                               + "; new " + ", ".join(f"{f} {v:.5f}" for f, v in new.items()))
    return BaseWeights(book, weights, iv, admissible, tuple(events), tuple(printed))


# --------------------------------------------------------------------------- #
# Family-level composition (exposure_basis active) and the market-level product with min()
# --------------------------------------------------------------------------- #
def _compose(vt: float, overlays: Sequence[float], ladder: float = 1.0, post_rearm_cap: float = 1.0) -> float:
    """The market-level product is `risk_layer.compose` (M2, TASK-M2-03): one min(), one set of bound checks."""
    return float(RL.compose(vt, tuple(overlays), ladder, post_rearm_cap))


def _sign(x: float) -> int:
    return (x > 0) - (x < 0)


def apply_overlays(composite: Sleeve, multipliers: Sequence, basis: str, *, concentration_bound: float | None = None,
                   ladder: float = 1.0, post_rearm_cap: float = 1.0) -> Weights:
    """Family level (basis "active"): a = vs x min(1.0, overlays) in [0, 1]; long-only sleeve ->
    base x [w_b + a (w_s - w_b)] (toward the benchmark), long/short -> base x a x w_ls (toward zero). Market level
    (basis "total"): gross = min(vt x min(1, overlays, ladder, cap), concentration_bound) scales the long book.
    Refused (P8, T-BASIS-01): a multiplier without exposure_basis, a total-basis multiplier on a family sleeve (vt is
    never applied to L/S sleeves), a vt on anything but market_gross, any multiplier on ts_trend. Overlays never create
    an instrument and never flip a sign (P1); nothing is renormalised (L883); the binding factor is logged (L897)."""
    if basis not in BASES:
        raise MacroRefusal(f"basis {basis!r} not in {BASES} (P8)")
    mults = tuple(multipliers)
    for m in mults:
        if not isinstance(m, (Multiplier, VSResult)):
            raise MacroRefusal(f"{m!r} is not a multiplier record")
        if getattr(m, "exposure_basis", None) not in BASES:
            raise MacroRefusal(f"{m.rule_id}: exposure_basis missing (P8)")
    if composite.family == "ts_trend" and mults:
        raise MacroRefusal(f"{composite.market}/ts_trend: no multiplier on ts_trend (R-14; T-BASIS-01)")
    if basis == "active" and composite.family in FIXED_ONE and any(m.factor == "overlay" or m.value != 1.0 for m in mults):
        raise MacroRefusal(f"{composite.market}/{composite.family}: no overlay multiplier, fixed 1.0 in every state (R-05)")
    reasons, binding = [], []
    if basis == "active":
        vs_list = [m for m in mults if m.factor == "vs"]
        if len(vs_list) > 1:
            raise MacroRefusal("one vs per sleeve (R-03)")
        for m in mults:
            if m.exposure_basis == "total" or m.factor in ("vt", "ladder", "post_rearm_cap"):
                raise MacroRefusal(f"{m.rule_id}: a total-basis multiplier ({m.factor}) is never applied to a family "
                                   f"sleeve ({composite.kind}); vt scales the market's long book only (L894, T-BASIS-01)")
        vs = assert_vs(float(vs_list[0].value)) if vs_list else 1.0
        applied = [m for m in mults if m.factor == "overlay" and m.applies_to in (composite.family, "")]
        skipped = [m for m in mults if m.factor == "overlay" and m not in applied]
        for m in skipped:
            reasons.append(f"{m.rule_id}: applies_to {m.applies_to!r} != {composite.family!r}: not applied")
        values = [assert_overlay(float(m.value)) for m in applied]
        omin = min([1.0, *values])
        a = vs * omin
        assert 0.0 <= a <= 1.0
        if vs < 1.0:
            binding.append(vs_list[0].rule_id)
        if omin < 1.0:
            binding.append(applied[values.index(omin)].rule_id)
        for m in mults:
            reasons.extend(m.reasons)
        reasons.append(f"active budget: {composite.base_weight:.5f} x vs {vs:.4f} x min(1.0{''.join(f', {v:.2f}' for v in values)})={omin:.2f}")
        base = composite.base_weight
        if composite.kind == "long_only":
            wb = composite.benchmark or {}
            keys = sorted(set(composite.weights) | set(wb))
            out = {i: base * (wb.get(i, 0.0) + a * (composite.weights.get(i, 0.0) - wb.get(i, 0.0))) for i in keys}
            for i, w in out.items():
                assert w >= -1e-15, "a long-only sleeve never goes short"
        else:
            out = {i: base * a * w for i, w in composite.weights.items()}
            for i, w in out.items():
                assert _sign(w) in (_sign(composite.weights[i]), 0), "an overlay never flips a sign (P1)"
        factor, vs_v, omin_v = a, vs, omin
    else:
        if composite.kind != "long_only":
            raise MacroRefusal("the total basis scales the market's long book only (L894)")
        vt_list = [m for m in mults if m.factor == "vt"]
        if len(vt_list) > 1:
            raise MacroRefusal("one vt per market (R-06)")
        for m in mults:
            if m.exposure_basis != "total":
                raise MacroRefusal(f"{m.rule_id}: an active-basis multiplier never scales the market gross (P8)")
            if m.factor == "vs":
                raise MacroRefusal(f"{m.rule_id}: vs is a family factor; it never scales the market gross (R-03)")
        # ladder / post_rearm_cap records enter min() with the scalar arguments (never dropped)
        ladder = min([ladder, *(float(m.value) for m in mults if m.factor == "ladder")])
        post_rearm_cap = min([post_rearm_cap, *(float(m.value) for m in mults if m.factor == "post_rearm_cap")])
        vt = assert_vt(float(vt_list[0].value)) if vt_list else 1.0
        overlays = [m for m in mults if m.factor == "overlay"]
        values = [float(m.value) for m in overlays]
        composed = _compose(vt, values, ladder, post_rearm_cap)
        gross = composed if concentration_bound is None else min(composed, float(concentration_bound))
        assert 0.0 <= gross <= 1.0
        omin = min([1.0, *values, ladder, post_rearm_cap])
        if vt < 1.0:
            binding.append(vt_list[0].rule_id)
        if values and min(values) == omin and omin < 1.0:
            binding.append(overlays[values.index(omin)].rule_id)
        if ladder == omin < 1.0:
            binding.append("ladder")
        if post_rearm_cap == omin < 1.0:
            binding.append("post_rearm_cap")
        if concentration_bound is not None and concentration_bound < composed:
            binding.append("concentration_bound")
        for m in mults:
            reasons.extend(m.reasons)
        reasons.append(f"gross: min(vt {vt:.4f} x min(1.0, overlays, ladder {ladder}, cap {post_rearm_cap})={composed:.4f}"
                       f"{'' if concentration_bound is None else f', bound {concentration_bound:.4f}'})={gross:.4f}")
        out = {i: gross * w for i, w in composite.weights.items()}
        factor, vs_v, omin_v = gross, vt, omin
    assert set(out) <= set(composite.weights) | set(composite.benchmark or {}), "an overlay never creates an instrument (P1)"
    return Weights(composite.market, composite.family, basis, out, factor, vs_v, omin_v, mults, tuple(binding), tuple(reasons),
                   kind=composite.kind)


# --------------------------------------------------------------------------- #
# Book builders (L885-887, L3770)
# --------------------------------------------------------------------------- #
def _label(card: Mapping, status: str) -> str:
    return f"{card.get('card_id')}: {card.get('verdict')} ({card.get('label')}); {status}"


def _collect(results: Sequence[Weights], fail_closed: bool, kind: str, decision_utc, reasons) -> Book:
    total: dict[tuple[str, str], float] = {}
    labels = {}
    for w in results:
        for i, x in w.weights.items():
            total[(w.market, i)] = total.get((w.market, i), 0.0) + x
        labels[(w.market, w.family)] = w.label
    return Book(kind, decision_utc, tuple(results), total, labels, fail_closed, tuple(reasons))


def build_specification_book(sleeves: Sequence[Sleeve], base: BaseWeights, vs: Mapping, dm: Mapping, *,
                             decision_utc: datetime, previous: Book | None = None) -> Book:
    """Every BUILD NOW / SPECIFICATION BOOK factor whatever its verdict, labelled: vs (R-03 revision 1) and dm (R-04 at
    floor 0.5) on momentum; reversal / quality / flow fixed 1.0; ts_trend exempt. `vs` maps (market, family) ->
    VSResult | MissingInput, `dm` maps market -> Multiplier | MissingInput. A MissingInput carries the sleeve's
    previous weights with fail_closed = true (never interpolated, L1108); with no previous state the sleeve has no budget."""
    if base.book != "specification":
        raise MacroRefusal(f"base weights of the {base.book} book passed to the specification builder")
    out, reasons, fail = [], [], base.fail_closed
    for s in sleeves:
        sl = replace(s, base_weight=base.weights.get(s.key, 0.0))
        mults, labels = [], []
        r = vs.get(s.key)
        if s.family == "momentum":
            d = dm.get(s.market)
            failed = [x for x in (r, d) if isinstance(x, P.MissingInput)]
            if failed:
                fail = True
                prev = next((p for p in (previous.sleeves if previous else ()) if (p.market, p.family) == s.key), None)
                reasons.append(f"{s.market}/{s.family}: fail_closed {failed[0].series_id} {failed[0].reason} "
                               f"{failed[0].detail}; previous weights {'carried' if prev else 'absent: no budget'}")
                w = replace(prev, label=prev.label + "; fail_closed") if prev else Weights(
                    s.market, s.family, "active", {i: 0.0 for i in s.weights}, 0.0, 1.0, 1.0, (), (),
                    ("fail_closed: no previous state",), "fail_closed", s.kind)
                out.append(w)
                continue
            if r is not None:
                mults.append(r)
                labels.append(_label(r.card, r.status))
            if d is not None:
                if d.book != "specification":
                    raise MacroRefusal("R-04 multiplier not bound to the specification book")
                mults.append(d)
                labels.append(_label(d.card, d.status))
        else:
            if isinstance(r, VSResult) and r.value != 1.0:
                raise MacroRefusal(f"{s.market}/{s.family}: vs is momentum only, else 1.0 (R-05, L867)")
            if s.family in FIXED_ONE:
                labels.append(f"R-05: {s.family} fixed 1.0 (no overlay)")
            if s.family == "ts_trend":
                labels.append("R-14: ts_trend exempt from overlays and vt")
        w = apply_overlays(sl, mults, "active")
        out.append(replace(w, label="; ".join(labels)))
    return _collect(out, fail, "specification", decision_utc, reasons)


def _refuse_outside_recommended(multipliers) -> None:
    for m in multipliers:
        card = getattr(m, "card", {}) or {}
        if card.get("disposition") in REFUSED_IN_RECOMMENDED or getattr(m, "book", "recommended") != "recommended":
            raise MacroRefusal(f"{m.rule_id}: disposition {card.get('disposition')!r} / book {getattr(m, 'book', None)!r} "
                               "never reaches the recommended book (P7, L3770, section 10 item 22)")


def _recommended_or_one(m: Multiplier, cards: Mapping | None) -> Multiplier:
    """An overlay acts in the recommended book only on a PASS card with a recommended disposition, or as an
    INVARIANT_STEP (L885, L3768; `macro_artifacts.acts_in_recommended`); any other card enters as 1.0, not_run."""
    from core.ficc.macro_artifacts import acts_in_recommended
    card = dict(m.card or {})
    card["verdict"] = _verdict(cards, card.get("card_id")) if cards else card.get("verdict", "NOT_RUN")
    if acts_in_recommended(card):
        return m
    return replace(m, value=1.0, status="not_run", card=card, reasons=(f"{m.rule_id}: card {card['verdict']}: enters as 1.0",))


def build_recommended_book(sleeves: Sequence[Sleeve], base: BaseWeights, vs: Mapping, *, cards: Mapping | None = None,
                           decision_utc: datetime, multipliers: Sequence = ()) -> Book:
    """Invariants plus PASS factors only (disposition RECOMMENDATION or BUILD_AS_INSURANCE); every other factor enters
    as 1.0 with status not_run. Refuses any multiplier with disposition SPECIFICATION_ONLY, FORWARD_SIM or
    REFUSAL_BOOK (R-04 included), any multiplier bound to another book, and a BUILD_AS_INSURANCE card still NOT_RUN /
    INSUFFICIENT_DATA (L3770, I-03). In v2.0 every macro card is NOT_RUN."""
    if base.book != "recommended":
        raise MacroRefusal(f"base weights of the {base.book} book passed to the recommended builder")
    _refuse_outside_recommended(multipliers)
    out, reasons, fail = [], [], base.fail_closed
    for s in sleeves:
        sl = replace(s, base_weight=base.weights.get(s.key, 0.0))
        mults, labels = [], []
        r = vs.get(s.key)
        if isinstance(r, VSResult):
            card = dict(r.card)
            card["verdict"] = _verdict(cards, s.key, card.get("card_id")) if cards else card.get("verdict", "NOT_RUN")
            if card.get("build_status_on_pass") == "BUILD_AS_INSURANCE" and card["verdict"] in ("NOT_RUN", "INSUFFICIENT_DATA"):
                raise MacroRefusal(f"{card['card_id']}: BUILD_AS_INSURANCE while {card['verdict']} (L3770)")
            if card["verdict"] == "PASS" and card.get("disposition") in RECOMMENDED_DISPOSITIONS:
                mults.append(r)
                labels.append(_label(card, r.status))
            else:
                mults.append(replace(r, value=1.0, status="not_run", card=card, reasons=(f"VS: card {card['verdict']}: enters as 1.0",)))
                labels.append(_label(card, "not_run: enters as 1.0"))
        elif isinstance(r, P.MissingInput):
            reasons.append(f"{s.market}/{s.family}: vs input {r.series_id} {r.reason} (bound to {r.books}); enters as 1.0 "
                           "(the recommended book reads no NOT_RUN factor)")
        for m in multipliers:
            if m.applies_to == s.family and m.factor == "overlay":
                m = _recommended_or_one(m, cards)
                mults.append(m)
                labels.append(_label(m.card, m.status))
        if s.family in FIXED_ONE:
            labels.append(f"R-05: {s.family} fixed 1.0 (no overlay)")
        if s.family == "ts_trend":
            labels.append("R-14: ts_trend zero budget until its own PASS; exempt from overlays and vt")
        w = apply_overlays(sl, mults, "active")
        out.append(replace(w, label="; ".join(labels)))
    return _collect(out, fail, "recommended", decision_utc, reasons)


def apply_market_gross(book: Book, vt, overlays: Sequence = (), *, ladder: float = 1.0, post_rearm_cap: float = 1.0,
                       concentration_bound: float | None = None) -> Book:
    """`composite_weights(i | active_budget, gross)`: the market's gross (exposure_basis total) scales the long-only
    sleeves' weights only; long/short sleeves (own vs) and ts_trend are never scaled by vt (L894; T-BASIS-01 clause).
    `vt` is a Multiplier (factor vt) or a bare float in [0, 1]. On a recommended book the overlays pass the builder's
    gate (I-03): another book's or a refused disposition raises, a non-PASS card enters as 1.0; the caller gates vt
    by admission (1.0 while R-06 is NOT_RUN, L885)."""
    vt_m = vt if isinstance(vt, (Multiplier, VSResult)) else Multiplier("R-06-VT", float(vt), "total", "market_gross", factor="vt")
    if book.kind == "recommended":
        _refuse_outside_recommended(overlays)
        overlays = [_recommended_or_one(m, None) for m in overlays]
    out = []
    for w in book.sleeves:
        if w.family == "ts_trend" or w.basis != "active" or w.kind == "long_short":
            out.append(w)                               # L/S sleeves and ts_trend: never scaled by vt
            continue
        long_book = Sleeve(w.market, w.family, "long_only", dict(w.weights), base_weight=1.0)
        g = apply_overlays(long_book, [vt_m, *overlays], "total", concentration_bound=concentration_bound,
                           ladder=ladder, post_rearm_cap=post_rearm_cap)
        out.append(replace(w, weights=g.weights, binding=w.binding + g.binding, reasons=w.reasons + g.reasons))
    return _collect(out, book.fail_closed, book.kind, book.decision_utc, book.reasons)
