"""Risk layer v2 (M2): R-06 market vol target and its two display labels, R-02 composition by min(), R-09 hedge
state, the per-book {composed, gross, binding_factor} line and the acting-exception guard (spec section 3.3, 3.5,
3.8; P2, P16, P18, P19; rulings 2 "risk functions", 3.3, 3.5, section 4).

Implements: `sma_vol` (SMA20 on simple returns, ddof 1, x sqrt(252)), `ewma_vol` (delegates to the M3 race's `vol_estimators.ewma`; never an
acting estimator here, section 10 item 25), `market_vol_target` -> `VTResult | MissingInput` with the warm-up /
degenerate-sigma mapping and `vt_for_book`, `display_label_rel` / `display_label_abs` (causal quartile labels, display
only, never gating: P19, section 10 items 24 and 28), `compose` / `compose_detail` / `verify_composition` (min() with the
0.5 x vt floor; a product path raises), `risk_layer` (gross = min(composed, concentration bound); HALTED = 0x outside
min()), `hedge_state` -> `HedgeState` (date-aligned corr63, core PCE YoY read as of its vintage, the conservative
default on any stale input or exception; never raises, never HALTs), `apply_hedge_state` (max(corr, 0) on the hedge
legs of a covariance input), `covariance_carry` (carry-5-then-drop status), `guard_acting` (an exception in an acting
risk-layer function HALTs (OPS) the books it feeds).

Every acting read goes through `pit_value` / `pit_window` with the binding's consumer ("R-06", "corr63",
"corr63_backtests", "hedge_state"); every function takes `decision_utc` and `knowledge_utc`; the store, registry,
clocks and book registry are injected. Decimals in the core (0.030 is 3.0%). Bounds are asserted in code:
overlays [0.5, 1.0], vt / vs [0, 1.0], ladder and post_rearm_cap in {1.0, 0.5}; nothing above 1.0 (cap permanent).
Tests: T-CAP-02, T-VT-01, T-LABEL-01, T-HEDGE-01, T-CORR-01, T-ROLE-01/02 and T-MISS-02 (M2 clauses), T-LAG-02 (vt clause).
M5 (R-07, R-31; T-BOOK-03, T-CAPS-01, I-04, T-STEP-05): `lookthrough_exposure` (daily ETF baskets, L/I products at x L,
tick <= 10 bp eligibility), `concentration_bound` (the D1 template from the store; absolute / active / aggregate / semis
bounds, `bound` = their min, `binding_factor`), `risk_limit_breach` (hard levels 25 / 50 on post-action weights),
`ladder_step` (the R-31 pseudocode, pure), `ladder_path` / `drawdown_ladder` (the fold with the R-07 re-arm cycle),
`steps_act_in` / `ladder_for_book` / `ladder_disposition` (INVARIANT_STEP at a frozen share <= 0.10, else the
specification book only), `ladder_flags`. The per-decision runtime step is `core/engine/books.risk_step`.
# integration: the M8 pipeline reads KODEX200_PDF through pit_value(consumer R-07) into `Basket` objects and
# KRX_MARKET_CAPS_005930_000660_KOSPI for pair_share_kospi; M6 builds macro_state.concentration / flags from
# ConcentrationBound, `risk_layer(...)` per book and `ladder_flags`; M7 freezes `binding_share` at the R-31 header commit.
# VSResult is core/quant/sleeves.VSResult (M4, `sleeve_vol_scale`), re-exported here lazily; `vol_state` assembles
# macro_state.vol from VTResult + vt_for_book + the M3 gate's vol_fields(); the M8 pipeline passes the ingest's
# stale-carry flags to market_vol_target(stale_carry=...) and wires guard_acting to the book registry.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, replace
from datetime import date, datetime, timedelta, timezone
from functools import lru_cache
from typing import Collection, Mapping, Sequence

import numpy as np

from core.ficc import contracts as _contracts
from core.ficc import pit as _pit
from core.ficc.macro_schema import md5_hex
from core.ficc.pit import MissingInput, PITValue


def assert_overlay(x: float) -> float:
    """core.rules.macro_rules.assert_overlay (P2), imported on first use: that module pulls core.quant.validate."""
    from core.rules.macro_rules import assert_overlay as f
    return f(x)


def assert_vt(x: float) -> float:
    from core.rules.macro_rules import assert_vt as f
    return f(x)


def assert_vs(x: float) -> float:
    from core.rules.macro_rules import assert_vs as f
    return f(x)


LABELS = ("calm", "normal", "elevated", "stressed")                  # vol_target.display_labels.values
LABEL_METHOD_REL = "trailing756_quartiles_causal_filtered"           # macro_state.vol.label_method_rel (const)
LABEL_METHOD_ABS = "expanding_full_history_quartiles_causal_filtered"
REL_WINDOW = 756
ABS_MIN_YEARS = 10
VT_CONSUMER = "R-06"
VT_SERIES = {"KR": "KOSPI_OFFICIAL_CLOSE", "US": "US_SLEEVE_OFFICIAL_CLOSE"}   # F-8: US books [] while D5 = none
HEDGE_CONSUMER = "hedge_state"
US10Y = {"live": ("US10Y_KIS_QUOTE", "corr63"), "backtest": ("DGS10", "corr63_backtests"),
         "replay": ("US10Y_KIS_QUOTE", "corr63")}                   # data.us10y: production vs history channel
HEDGE_REASONS = ("ok", "risk_model_input_stale", "risk_model_exception", "corr_positive", "core_pce_ge_3")
BOUND_FACTORS = ("none", "absolute_single_name", "active_single_name", "aggregate", "semis")
ACTING_EXCEPTION = "acting_risk_layer_exception"                     # risk_layer.halted_triggers.OPS (L4357)
STEP_VALUES = (1.0, 0.5)                                             # ladder and post_rearm_cap (L872)
ALERT_STALE, ALERT_HEDGE_EXC, ALERT_ACTING_EXC = "RISK_MODEL_INPUT_STALE", "HEDGE_STATE_EXCEPTION", "ACTING_RISK_LAYER_EXCEPTION"


class CompositionError(ValueError):
    """A product-composed path, a recorded composed value that min() does not reproduce, or a factor out of bounds."""


# --------------------------------------------------------------------------- #
# Types (section 3.5; brief B.1; rulings section 4)
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class VTResult:
    market: str
    estimator: str                       # "sma20" in M2
    status: str                          # "ok" | "insufficient_history"
    sigma_ann: float | None              # decimals; None when insufficient_history
    target_ann: float
    weight: float | None                 # min(1.0, target / sigma) in [0, 1]; None when insufficient_history
    n_valid_returns: int
    display_label_rel: str | None
    display_label_abs: str | None
    exposure_basis: str = "total"
    inputs: tuple[dict, ...] = ()        # macro_state $defs/input records of the closes read
    series_id: str = ""
    books: tuple[str, ...] = ()          # the HALT scope of the close's binding
    label_status: str = "ok"             # why a label is None (display only; never a failure)


def __getattr__(name: str):
    """`VSResult` has one home, `core.quant.sleeves.VSResult` (R-03; S3 integration ruling): the overlay record
    `sleeve_vol_scale` returns and `apply_overlays` consumes. Resolved lazily so this module stays a 0.3 s import."""
    if name == "VSResult":
        from core.quant.sleeves import VSResult
        return VSResult
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


@dataclass(frozen=True)
class BookVT:
    book_id: str
    weight: float | None                 # the value entering compose() for this book (None: no state to carry)
    vt_status: str                       # "ok" | "warmup" | "fail_closed" (macro_state.vol.vt_status)
    fail_closed: bool
    missing: MissingInput | None


@dataclass(frozen=True)
class ComposeResult:
    composed: float
    overlay_min: float                   # min(1.0, overlays..., ladder, post_rearm_cap) in [0.5, 1.0]
    binding: tuple[str, ...]             # factor ids equal to overlay_min when it is below 1.0 (F-9, F-10)
    reasons: tuple[str, ...] = ()        # readable lines for overlay_decision.reasons


@dataclass(frozen=True)
class HedgeState:
    hedge_credit_off: bool
    hedge_failure: bool
    classic_risk_off: bool
    fx_hedge_credit: bool | None         # display only
    hedge_reasons: tuple[str, ...]
    hedge_stale_inputs: tuple[str, ...]
    core_pce_yoy: float | None
    corr63: float | None
    alerts: tuple[dict, ...]
    inputs: tuple[dict, ...]
    notes: tuple[str, ...] = ()          # what was stale or raised (the alert text)


@dataclass(frozen=True)
class ConcentrationBound:                # filled by concentration_bound (M5; R-07)
    absolute_bound: float | None
    active_bound: float | None
    aggregate_bound: float | None
    semis_bound: float | None
    bound: float
    binding_factor: str                  # one of BOUND_FACTORS
    template: str = ""                   # M5 trailing fields (positional construction preserved, rulings 5)
    pair_lookthrough_share: float | None = None
    shares: tuple = ()                   # (name, look-through share) descending
    reasons: tuple = ()


@dataclass(frozen=True)
class LadderState:                       # filled by drawdown_ladder (M5; R-07, R-31 names binding)
    hwm_hard: float | None
    ref_step: float | None
    step_mult: float
    dwell_left: int
    block_new_entries: bool
    halted: bool
    rearm_not_before: date | None
    post_rearm_left: int
    binding_share: float | None


@dataclass(frozen=True)
class ActingFailure:
    component: str
    error: str
    books: tuple[str, ...]
    alert: dict
    fail_closed: bool = True


# --------------------------------------------------------------------------- #
# Rules-store parameters (read verbatim; the shipped store is loaded once)
# --------------------------------------------------------------------------- #
@lru_cache(maxsize=1)
def _shipped_store():
    from core.rules.macro_rules import load_store
    return load_store()


def _rule(rules, dotted: str):
    """`rules` is a MacroStore (`.get(dotted)`), a plain dict, or None for the shipped store."""
    rules = _shipped_store() if rules is None else rules
    if isinstance(rules, dict):
        cur = rules
        for k in dotted.split("."):
            cur = cur[k]
        return cur
    return rules.get(dotted)


def alert(code: str, component: str, decision_utc: datetime, *, series_id: str | None = None, books=(),
          severity: str = "warn", escalated: bool = False) -> dict:
    """A macro_state alerts[] record (L3625-3629)."""
    stamp = _pit.iso_utc(decision_utc)
    return {"alert_id": md5_hex(f"{code}|{component}|{series_id or ''}|{stamp}")[:12], "code": code,
            "severity": severity, "component": component, "series_id": series_id, "books": list(books),
            "first_seen_utc": stamp, "count": 1, "escalated": bool(escalated), "ack_utc": None}


def input_record(v: PITValue, registry, clocks, *, name: str, status: str = "ok") -> dict:
    """A macro_state $defs/input record of one PIT value read (L3632-3651)."""
    try:
        exp = _contracts.expected_available_utc(registry, v.series_id, v.obs_date, clocks)
        deadline = _contracts.stale_deadline_utc(registry, v.series_id, v.obs_date, clocks)
    except Exception:                                       # an unreadable calendar is reported, never raised here
        exp = deadline = None
    iso = lambda x: None if x is None else _pit.iso_utc(x)   # noqa: E731
    books = registry.book_ids(_contracts.Binding(v.series_id, v.role, tuple(v.books)))
    return {"name": name, "series_id": v.series_id, "source": v.source, "channel": v.channel,
            "obs_date": v.obs_date.isoformat(), "session_date": v.session_date.isoformat() if v.session_date else None,
            "obs_kind": v.obs_kind, "value": v.value, "value_status": v.value_status, "dispute": v.dispute,
            "available_at_utc": iso(v.available_at_utc), "available_at_source": v.available_at_source,
            "retrieved_at_utc": iso(v.retrieved_at_utc), "expected_available_utc": iso(exp),
            "stale_deadline_utc": iso(deadline), "vintage": v.vintage.isoformat() if v.vintage else None,
            "timing": registry.series[v.series_id]["timing_class"], "role": v.role, "books": list(books),
            "status": "disputed" if v.dispute else status, "content_hash": v.content_hash}


# --------------------------------------------------------------------------- #
# Estimators (R-06 L1561; vol_target.sigma)
# --------------------------------------------------------------------------- #
def sma_vol(valid_returns: Sequence[float], window: int = 20, annualisation_days: int = 252) -> float | None:
    """stdev (ddof 1, mean-adjusted) of the last `window` simple returns x sqrt(252); None with fewer returns."""
    r = np.asarray(list(valid_returns)[-window:] if window > 0 else [], dtype=float)
    if window < 2 or r.size < window:
        return None
    # sqrt(var x days), the form of vol_estimators.sma (h x var, h = 1): the acting sigma and the M3 harness baseline
    # are bit-identical (sigma_for_decision delegates here; T-EST-04 asserts ==).
    return math.sqrt(float(np.var(r, ddof=1)) * annualisation_days)


def ewma_vol(valid_returns: Sequence[float], lam: float = 0.94, annualisation_days: int = 252,
             min_obs: int = 20) -> float | None:
    """sqrt(252 x the one-step variance of `vol_estimators.ewma`), the RiskMetrics recursion the M3 race grades as
    ewma094 / ewma097 (one implementation, so the two cannot diverge). Feed it the full return history (the recursion
    is seeded on the first 20 returns); it never sizes a book outside an R-30 counted revision (section 10 item 25)."""
    r = np.asarray(list(valid_returns), dtype=float)
    if r.size < min_obs or not 0.0 < lam < 1.0:
        return None
    from core.quant.vol_estimators import ewma                   # lazy: vol_estimators imports sma_vol from here
    s = math.sqrt(float(ewma(r, 1, lam).var[-1]) * annualisation_days)
    return s if math.isfinite(s) else None


ESTIMATORS = {"sma20": lambda returns, window, days: sma_vol(returns, window, days)}
# The R-30 challengers live in core/quant/vol_estimators.ESTIMATORS (M3) and are refused by forecast_eval.estimator_gate
# before any read; none is registered here until an R-30 counted revision exists (M7; section 10 item 25), so
# market_vol_target(estimator=<challenger>) raises (T-VT-01 clause).


# --------------------------------------------------------------------------- #
# Display labels (R-06 L1565; vol_target.display_labels; T-LABEL-01)
# --------------------------------------------------------------------------- #
def label_of(sigma: float, history: Sequence[float]) -> str:
    """sigma against the quartiles of `history` (numpy linear quantiles); a value on a boundary takes the higher
    label (L5643): < Q1 calm, [Q1, Q2) normal, [Q2, Q3) elevated, >= Q3 stressed."""
    q1, q2, q3 = np.quantile(np.asarray(history, dtype=float), (0.25, 0.5, 0.75))
    return LABELS[int(sigma >= q1) + int(sigma >= q2) + int(sigma >= q3)]


def display_label_rel(sigma_history: Sequence[float], window: int = REL_WINDOW) -> str | None:
    """sigma(t) against its own trailing `window` values (t included); None when the history is shorter (F-11)."""
    xs = [float(s) for s in sigma_history][-window:]
    if len(xs) < window:
        return None
    return label_of(xs[-1], xs)


def _add_years(d: date, n: int) -> date:
    try:
        return d.replace(year=d.year + n)
    except ValueError:                                       # 29 Feb
        return d.replace(year=d.year + n, month=3, day=1)


def display_label_abs(sigma_history: Sequence[float], first_date: date | None, t: date,
                      min_years: int = ABS_MIN_YEARS) -> str | None:
    """sigma(t) against the quartiles of its expanding full history, once that history spans `min_years` calendar
    years from the first sigma date; None before (F-11)."""
    xs = [float(s) for s in sigma_history]
    if not xs or first_date is None or _add_years(first_date, min_years) > t:
        return None
    return label_of(xs[-1], xs)


def sigma_history(closes: Sequence[tuple[date, float]], window: int = 20, annualisation_days: int = 252,
                  estimator=sma_vol) -> list[tuple[date, float]]:
    """Causal sigma series: sigma dated s uses the `window` simple returns between consecutive valid closes through
    s only, so appending later closes never changes an earlier value (filtered, never smoothed)."""
    dates = [d for d, _ in closes[1:]]
    r = [b / a - 1.0 for (_, a), (_, b) in zip(closes, closes[1:])]
    out = []
    for i in range(window, len(r) + 1):
        s = estimator(r[i - window:i], window, annualisation_days)
        if s is not None and math.isfinite(s):
            out.append((dates[i - 1], s))
    return out


# --------------------------------------------------------------------------- #
# market_vol_target (R-06 L1562-1566; vol_target.*; T-VT-01)
# --------------------------------------------------------------------------- #
def _prev_session(clocks, market: str, d: date, max_days: int = 400) -> date:
    for _ in range(max_days):
        d -= timedelta(days=1)
        if clocks.is_session(market, d):
            return d
    raise ValueError(f"{market}: no session in the {max_days} days before {d}")


def _close_ok(v: PITValue, run_mode: str, vendor: str | None) -> bool:
    """A close that may size a book: official, or the declared vendor's vendor_close in a backtest (section 4.1)."""
    return v.value_status == "official_close" or bool(
        run_mode == "backtest" and vendor and v.value_status == "vendor_close" and v.source == vendor)


def market_vol_target(store, registry, clocks, market: str, decision_utc: datetime, knowledge_utc: datetime,
                      estimator: str = "sma20", book_ever_armed: bool = False, *, rules=None, run_mode: str = "live",
                      vendor: str | None = None, stale_carry: Collection[date] = ()) -> VTResult | MissingInput:
    """vt = min(cap, target / sigma) decided at the close of t (`decision_utc == close_print_bound_utc(market, t)`).

    Reads the decided session's close through `pit_value(consumer="R-06", require_session=t)` (a MissingInput is
    returned unchanged), then the window through `pit_window`, walking sessions backwards: a session in
    `stale_carry` (the ingest's flat-OHLC zero-volume flags) is skipped and the window extends (L1561); any other
    session without a usable close inside the window fails closed (F-3). Fewer than `window` valid returns is
    `insufficient_history` (warm-up) unless `book_ever_armed`, when it is MissingInput("missing") (L1111); a
    sigma of 0 or not finite is MissingInput("missing") (F-5). Raises on a market without a pre-registered target
    (F-7), on a cap above 1.0 and on an estimator other than sma20 (section 10 items 2, 25); the guard turns a raise
    into an OPS HALT of the books the close feeds.
    """
    if estimator not in ESTIMATORS:
        raise ValueError(f"estimator {estimator!r}: sma20 is the acting estimator; a challenger enters only through "
                         "R-30 as a counted card revision (section 10 item 25)")
    block = _rule(rules, "vol_target")
    p = block.get(market) or block["other_markets"]
    target, cap, window = p.get("target_ann"), float(p.get("cap", 1.0)), int(p.get("window", 20))
    if target is None or not (isinstance(target, (int, float)) and target > 0):
        raise ValueError(f"vol_target.{market}.target_ann is {target!r}: pre-register the target on the market's card "
                         "before it runs (R-06 L1563); no default is invented")
    if cap > 1.0:
        raise ValueError(f"vol_target.{market}.cap {cap} > 1.0: the cap of 1.0 is permanent (R-06 L1563)")
    days = int(block["annualisation_days"])
    sid = VT_SERIES.get(market)
    if sid is None:
        raise ValueError(f"{market}: no close series registered for R-06 (VT_SERIES)")
    t = decision_utc.astimezone(timezone.utc).date()
    if not clocks.is_session(market, t) or clocks.close_print_bound_utc(market, t) != decision_utc:
        raise ValueError(f"{market}: decision_utc {_pit.iso_utc(decision_utc)} is not close_print_bound_utc of a "
                         f"{market} session (time.decision_instant)")
    ctx = _pit.RunContext(decision_utc, knowledge_utc, run_mode)
    binding = registry.resolve_binding(sid, VT_CONSUMER)
    books = registry.book_ids(binding)
    v = _contracts.read_input(store, registry, sid, ctx, VT_CONSUMER, clocks, require_session=t, vendor=vendor)
    if isinstance(v, MissingInput):
        return v
    rows = _pit.pit_window(store, sid, decision_utc, knowledge_utc, registry=registry, statuses=_pit.CLOSE_STATUSES)
    flagged = {d for d in stale_carry}
    closes = {r.obs_date: r for r in rows if r.obs_date <= t and r.obs_date not in flagged and _close_ok(r, run_mode, vendor)}
    closes[t] = v
    first = min(closes)
    seq, d = [v], t
    while len(seq) < window + 1:
        d = _prev_session(clocks, market, d)
        if d < first:
            break
        if d in flagged:
            continue
        r = closes.get(d)
        if r is None:
            return MissingInput(sid, "missing", binding.role, tuple(binding.books),
                                detail=f"no usable close for {market} session {d} inside the {window}-return window "
                                       "(an unflagged gap fails closed; F-3)")
        seq.append(r)
    seq.reverse()
    returns = [b.value / a.value - 1.0 for a, b in zip(seq, seq[1:])]
    n = len(returns)
    inputs = (input_record(v, registry, clocks, name="close_t"),
              input_record(seq[0], registry, clocks, name="close_window_start"))
    if n < window:
        if book_ever_armed:
            return MissingInput(sid, "missing", binding.role, tuple(binding.books),
                                detail=f"{n} valid returns < {window} on a book that has been ARMED: a truncated history "
                                       "never resets vt to 1.0 (L1111)")
        return VTResult(market, estimator, "insufficient_history", None, float(target), None, n, None, None, "total",
                        inputs, sid, books, f"insufficient_history: {n} of {window} valid returns")
    sigma = ESTIMATORS[estimator](returns, window, days)
    if sigma is None or not math.isfinite(sigma) or sigma <= 0.0:
        return MissingInput(sid, "missing", binding.role, tuple(binding.books),
                            detail=f"degenerate sigma {sigma!r} with {n} valid returns: a contract violation (R-06 L1562)")
    vt = assert_vt(min(cap, float(target) / sigma))
    # labels: the causal sigma series over every usable close in the store (display only; gaps do not fail it)
    hist = sigma_history([(d, closes[d].value) for d in sorted(closes)], window, days, ESTIMATORS[estimator])
    values = [s for _, s in hist]
    rel = display_label_rel(values)
    abs_ = display_label_abs(values, hist[0][0] if hist else None, t)
    why = []
    if rel is None:
        why.append(f"rel: {len(values)} < {REL_WINDOW} sigma values")
    if abs_ is None:
        why.append(f"abs: history from {hist[0][0].isoformat() if hist else 'n/a'} < {ABS_MIN_YEARS} years")
    return VTResult(market, estimator, "ok", float(sigma), float(target), vt, n, rel, abs_, "total", inputs, sid, books,
                    "; ".join(why) or "ok")


def vt_for_book(result: VTResult | MissingInput, book_id: str, *, ever_armed: bool,
                prev_weight: float | None = None) -> BookVT:
    """Per-book mapping (L1046-1047, L1111; brief B.4): insufficient_history -> 1.0 `warmup` only while the book
    has never been ARMED, else MissingInput("missing"); any MissingInput -> `fail_closed`, weight = the previous
    state (never 1.0, never interpolated)."""
    if isinstance(result, MissingInput):
        return BookVT(book_id, prev_weight, "fail_closed", True, result)
    if result.status == "insufficient_history":
        if not ever_armed:
            return BookVT(book_id, 1.0, "warmup", False, None)
        miss = MissingInput(result.series_id, "missing", "acting_exposure", result.books,
                            detail=f"{result.n_valid_returns} valid returns on an ARMED book (L1111)")
        return BookVT(book_id, prev_weight, "fail_closed", True, miss)
    return BookVT(book_id, assert_vt(result.weight), "ok", False, None)


def vol_state(vt: VTResult, book: BookVT, gate: Mapping | None = None, *, instrument_book: str,
              rebalance: str | None = None, no_trade_band: float | None = None, recommended_pass: bool = False) -> dict:
    """The `macro_state.vol` sub-object (L3370) from this layer: vt fields from `vt` / `book` (`vt_for_book`), the
    estimator fields from `forecast_eval.EstimatorSelection.vol_fields()` (`gate`; None = gate not run, sma20).
    The recommended book carries vt only once the R-06 card is PASS (`recommended_pass`), else 1.0 (rulings 1).
    A fail_closed book with no previous weight has nothing to publish (M6 carries the previous artifact)."""
    if book.weight is None:
        raise ValueError(f"{book.book_id}: no vt weight to publish (fail_closed with no previous state)")
    gate = dict(gate or {"estimator": vt.estimator, "estimator_b5": "NOT_RUN",
                         "estimator_gate": {"status": "NOT_RUN", "stage1": None, "stage2_mcs_p": None,
                                            "stage3_rank": None, "fallback_used": False, "reason": "gate not run"}})
    out = {**gate, "vt_status": book.vt_status, "sigma_ann": vt.sigma_ann, "target_ann": vt.target_ann,
           "vt_weight_next": float(book.weight), "vt_weight_recommended_book": float(book.weight) if recommended_pass else 1.0,
           "instrument_book": instrument_book, "display_label_rel": vt.display_label_rel,
           "label_method_rel": LABEL_METHOD_REL, "display_label_abs": vt.display_label_abs,
           "label_method_abs": LABEL_METHOD_ABS, "alt_sigma_logged": None, "label_status": vt.label_status}
    if rebalance is not None:
        out["rebalance"] = rebalance
    if no_trade_band is not None:
        out["no_trade_band"] = float(no_trade_band)
    return out


# --------------------------------------------------------------------------- #
# Composition (section 3.3 L870-881; R-02; overlay.*; T-CAP-02)
# --------------------------------------------------------------------------- #
def _number(x, what: str) -> float:
    if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(float(x)):
        raise CompositionError(f"{what} {x!r} is not a finite number")
    return float(x)


def _check_factors(vt, overlays, ladder, post_rearm_cap) -> tuple[float, list[float], float, float]:
    try:
        vt = assert_vt(_number(vt, "vt"))
        ovs = [assert_overlay(_number(o, "overlay")) for o in overlays]
    except ValueError as exc:
        raise CompositionError(str(exc)) from None
    if ladder not in STEP_VALUES or post_rearm_cap not in STEP_VALUES:
        raise CompositionError(f"ladder {ladder!r} / post_rearm_cap {post_rearm_cap!r} must be 1.0 or 0.5 (L872)")
    return vt, ovs, float(ladder), float(post_rearm_cap)


def compose(vt: float, overlays: Sequence[float], ladder: float, post_rearm_cap: float, *, combine: str = "min") -> float:
    """composed = vt x min(1.0, overlays..., ladder, post_rearm_cap). Raises CompositionError on any factor outside
    its bound and on a request to combine other than by min() (a product-composed path; section 10 item 31)."""
    if combine != "min":
        raise CompositionError(f"composition {combine!r} refused: overlay.combine is min; a product-composed de-risk "
                               "stack raises (R-02, section 10 item 31)")
    vt, ovs, ladder, cap = _check_factors(vt, overlays, ladder, post_rearm_cap)
    composed = vt * min([1.0] + ovs + [ladder, cap])
    if composed < 0.5 * vt:                                  # written as a product: vt = 0 needs no division (L881)
        raise CompositionError(f"composed {composed} < 0.5 x vt {vt}")
    return composed


def compose_detail(vt: float, overlays: Mapping[str, float] | Sequence[float], ladder: float,
                   post_rearm_cap: float) -> ComposeResult:
    """`compose` plus the binding log: the ids of every factor equal to overlay_min when it binds (F-9, F-10)."""
    ids = list(overlays) if isinstance(overlays, Mapping) else [f"overlay_{i + 1}" for i in range(len(overlays))]
    vals = [overlays[k] for k in ids] if isinstance(overlays, Mapping) else list(overlays)
    composed = compose(vt, vals, ladder, post_rearm_cap)
    vt, ovs, ladder, cap = _check_factors(vt, vals, ladder, post_rearm_cap)
    m = min([1.0] + ovs + [ladder, cap])
    factors = list(zip(ids, ovs)) + [("ladder", ladder), ("post_rearm_cap", cap)]
    binding = tuple(k for k, x in factors if m < 1.0 and x == m)
    reasons = (f"min() binds at {m:.4f}: {', '.join(binding)}",) if binding else ()
    return ComposeResult(composed, m, binding, reasons)


def verify_composition(vt: float, overlays: Sequence[float], ladder: float, post_rearm_cap: float,
                       recorded_composed, *, tol: float = 1e-12) -> None:
    """`bounds_ok` (M8): recompute composed from the recorded factors and raise when the record differs (a product
    such as 0.375 for overlays 0.75 and 0.5 is caught here; L881)."""
    if recorded_composed is None:
        raise CompositionError("no composed value recorded")
    want = compose(vt, overlays, ladder, post_rearm_cap)
    got = _number(recorded_composed, "composed")
    if abs(got - want) > tol:
        raise CompositionError(f"recorded composed {got} != vt x min(...) = {want} (product-composed path?)")


def risk_layer(vt: float, overlays: Mapping[str, float] | Sequence[float], ladder: float, post_rearm_cap: float,
               bound: ConcentrationBound | float | None = None, *, bound_factor: str | None = None,
               halted: bool = False) -> dict:
    """The per-book `macro_state.concentration.by_book` line: composed from `compose`, gross = min(composed, bound)
    (a risk limit, not an overlay: it may take gross below 0.5 x vt), binding_factor "none" when the bound does not
    bind. HALTED sets the book to 0x and is never an argument of min() (L874)."""
    if halted:
        return {"composed": 0.0, "gross": 0.0, "binding_factor": "none"}
    composed = compose_detail(vt, overlays, ladder, post_rearm_cap).composed
    if bound is None:
        return {"composed": composed, "gross": composed, "binding_factor": "none"}
    if isinstance(bound, ConcentrationBound):
        b, factor = bound.bound, bound.binding_factor
    else:                                                    # integration: concentration_bound (M5) supplies the object
        if bound_factor is None:
            raise ValueError("a scalar concentration bound names its binding_factor")
        b, factor = _number(bound, "concentration bound"), bound_factor
    if factor not in BOUND_FACTORS:
        raise ValueError(f"binding_factor {factor!r} not in {BOUND_FACTORS}")
    if b < 0.0:
        raise ValueError(f"concentration bound {b} < 0")
    gross = min(composed, b)
    return {"composed": composed, "gross": gross, "binding_factor": factor if composed > b else "none"}


# --------------------------------------------------------------------------- #
# Acting-exception guard (section 3.8 L1178; T-MISS-02; brief B.10)
# --------------------------------------------------------------------------- #
def guard_acting(component: str, books: Sequence[str], book_registry, decision_utc: datetime, fn, *args, **kw):
    """Run an acting risk-layer function; on any exception HALT (OPS, `acting_risk_layer_exception`) exactly the
    books it feeds and return an `ActingFailure` marker with the alert (never the exception). `hedge_state` is
    never wrapped here (its exception is the conservative default, red line E4)."""
    try:
        return fn(*args, **kw)
    except Exception as exc:
        from core.engine import books as _books              # lazy: keeps this module free of the engine at import
        for b in books:
            _books.runtime_halt(book_registry, b, "OPS", ACTING_EXCEPTION, decision_utc, component=component)
        return ActingFailure(component, f"{type(exc).__name__}: {exc}", tuple(books),
                             alert(ALERT_ACTING_EXC, component, decision_utc, books=books, severity="page"))


# --------------------------------------------------------------------------- #
# corr63 (R-09 L1612; T-CORR-01)
# --------------------------------------------------------------------------- #
def corr63(eq_closes: Mapping[date, float], y10: Mapping[date, float], last_usable_10y_date: date | None,
           window: int = 63) -> float | None:
    """Pearson correlation of the last `window` date-aligned pairs (r_eq(D), -dy(D)) over the common dates
    D <= last_usable_10y_date; both changes are taken over the same consecutive common dates (F-13). The statistic
    is lagged by the usability of the 10y leg, never one leg. None with fewer than `window` pairs."""
    if last_usable_10y_date is None:
        return None
    dates = sorted(d for d in eq_closes if d in y10 and d <= last_usable_10y_date)
    pairs = [(eq_closes[b] / eq_closes[a] - 1.0, -(y10[b] - y10[a])) for a, b in zip(dates, dates[1:])][-window:]
    if len(pairs) < window:
        return None
    x, y = np.asarray(pairs, dtype=float).T
    if np.std(x) == 0.0 or np.std(y) == 0.0:
        return None
    return float(np.corrcoef(x, y)[0, 1])


# --------------------------------------------------------------------------- #
# hedge_state (R-09 L1612-1614; R-19 rule 4; risk_layer.hedge_state; T-HEDGE-01)
# --------------------------------------------------------------------------- #
def missed_releases(registry, sid: str, last_obs: date, decision_utc: datetime, clocks, *, limit: int = 24) -> int:
    """How many expected observations after `last_obs` are past their deadline (due + grace) at `decision_utc`."""
    grace = _contracts.contract(registry, sid).grace_pub_bdays
    n, d = 0, last_obs
    for _ in range(limit):
        d = clocks.next_expected_obs(sid, d)
        due = None if d is None else clocks.publication_instant(sid, d)
        deadline = None if due is None else clocks.add_publication_bdays(sid, due, grace)
        if deadline is None or decision_utc <= deadline:
            return n
        n += 1
    return n


def _change(series: Mapping[date, float], d: date, prev: date) -> float:
    return series[d] / series[prev] - 1.0


def _week_anchors(dates: Sequence[date]) -> list[date]:
    """The last session of each ISO week (F-28: the Friday KRX close, or the week's last session)."""
    last: dict[tuple[int, int], date] = {}
    for d in dates:
        key = d.isocalendar()[:2]
        last[key] = max(d, last.get(key, d))
    return sorted(last.values())


def _fx_hedge_credit(store, registry, decision_utc, knowledge_utc, p: dict) -> bool | None:
    """Display only (L1613, F-28, F-30): no credit while the trailing 26-week correlation of weekly KOSPI returns
    with the weekly change of the ECOS 15:30 USD/KRW close is >= 0. None when not computable."""
    weeks, lt = int(p["window_weeks"]), float(p["credit_if_corr_lt"])
    kospi = {r.obs_date: r.value for r in _pit.pit_window(store, "KOSPI_OFFICIAL_CLOSE", decision_utc, knowledge_utc,
                                                           registry=registry, statuses=("official_close",))}
    fx = _pit.pit_value(store, "ECOS_1530_CLOSE", decision_utc, knowledge_utc, "display", registry=registry)
    if isinstance(fx, MissingInput) or not kospi:
        return None
    ecos = {r.obs_date: r.value for r in _pit.pit_window(store, "ECOS_1530_CLOSE", decision_utc, knowledge_utc, registry=registry)}
    pairs, prev = [], None
    for a in _week_anchors(sorted(kospi)):
        at = max((d for d in ecos if d <= a), default=None)
        if prev is not None and at is not None and at > prev[1]:
            pairs.append((kospi[a] / kospi[prev[0]] - 1.0, ecos[at] / ecos[prev[1]] - 1.0))
        if at is not None:
            prev = (a, at)
    pairs = pairs[-weeks:]
    if len(pairs) < weeks:
        return None
    x, y = np.asarray(pairs, dtype=float).T
    if np.std(x) == 0.0 or np.std(y) == 0.0:
        return None
    return bool(float(np.corrcoef(x, y)[0, 1]) < lt)


def hedge_state(store, registry, decision_utc: datetime, knowledge_utc: datetime, *, clocks=None,
                run_mode: str = "live", rules=None) -> HedgeState:
    """R-09 hedge-validity state from its risk_model inputs. Never raises and never HALTs: a stale or failing input
    sets hedge_credit_off (reason risk_model_input_stale, series listed, alert; escalated after two missed releases)
    and any exception inside sets hedge_credit_off with reason risk_model_exception (red line E4). No exposure
    changes anywhere; fx_hedge_credit is display only."""
    try:
        return _hedge_state(store, registry, decision_utc, knowledge_utc, clocks, run_mode, rules)
    except Exception as exc:                                  # the conservative default (L1109, L1614, L5625)
        return HedgeState(True, False, False, None, ("risk_model_exception",), (), None, None,
                          (alert(ALERT_HEDGE_EXC, "hedge_state", decision_utc, severity="warn"),), (),
                          (f"exception inside hedge_state: {type(exc).__name__}: {exc}",))


def _hedge_state(store, registry, decision_utc, knowledge_utc, clocks, run_mode, rules) -> HedgeState:
    p = _rule(rules, "risk_layer.hedge_state")
    escalate_after = int(_rule(rules, "data_contracts.on_failure.risk_model.operator_alert_after_missed_releases"))
    ctx = _pit.RunContext(decision_utc, knowledge_utc, run_mode)
    y10_sid, y10_consumer = US10Y[run_mode]
    usd_sid = p["usd_input"]
    stale, inputs, notes, alerts, values = [], [], [], [], []

    def read(sid: str, consumer: str, name: str) -> PITValue | None:
        if clocks is None:
            v = MissingInput(sid, "missing", "risk_model", (), detail="no publication calendar: conservative default (L1956)")
        else:
            v = _contracts.read_input(store, registry, sid, ctx, consumer, clocks)
        if isinstance(v, MissingInput):
            mark(sid, _contracts.STATUS_OF[v.reason] + (f" ({v.detail})" if v.detail else ""))
            return None
        inputs.append(input_record(v, registry, clocks, name=name))
        values.append(v)
        return v

    def mark(sid: str, why: str) -> None:
        if sid in stale:
            return
        stale.append(sid)
        notes.append(f"{sid}: {why}")
        try:
            last = _pit.pit_last(store, sid, decision_utc, knowledge_utc, registry=registry)
            n = missed_releases(registry, sid, last.obs_date, decision_utc, clocks) if (last and clocks) else 0
        except Exception:                                    # an unreadable calendar: the count is unknown, not an error
            n = 0
        alerts.append(alert(ALERT_STALE, "hedge_state", decision_utc, series_id=sid,
                            severity="page" if n >= escalate_after else "warn", escalated=n >= escalate_after))

    # core PCE YoY, calendar-based, as of the vintage visible at knowledge_utc (L1612, L5637; data.monthly_lag_method)
    core_pce = None
    pce = read("PCEPILFE", HEDGE_CONSUMER, "core_pce")
    if pce is not None:
        levels = {r.obs_date: r.value for r in _pit.pit_window(store, "PCEPILFE", decision_utc, knowledge_utc, registry=registry)}
        yy = _pit.yoy(levels, pce.obs_date)
        if yy.flagged:
            mark("PCEPILFE", f"YoY not computable ({yy.reason})")
        else:
            core_pce = float(yy.value)
    # equity leg, 10y leg (production quote or strict-H.15 history), live USD proxy (never DTWEXBGS)
    eq_v = read("SPX_OFFICIAL_CLOSE", "corr63", "equity_close")
    y10_v = read(y10_sid, y10_consumer, "us10y")
    usd_v = read(usd_sid, HEDGE_CONSUMER, "usd_live_proxy")
    # the independent lag audit on every risk-model value read: a violation is the conservative default, never a
    # HALT (L1215); listed under the live context so a backtest gets the same list instead of LookAheadError
    if values and clocks is not None:
        from core.ficc.lag_audit import lag_audit
        try:
            found = lag_audit(values, _pit.RunContext(decision_utc, knowledge_utc, "live"), "US", registry, clocks)["violations"]
        except Exception as exc:
            found = [{"series_id": v.series_id, "check": f"lag audit unavailable ({type(exc).__name__}: {exc})",
                      "obs_date": v.obs_date.isoformat()} for v in values]
        for x in found:
            mark(x["series_id"], f"lag audit: {x['check']} ({x['obs_date']})")
    eq = {r.obs_date: r.value for r in _pit.pit_window(store, "SPX_OFFICIAL_CLOSE", decision_utc, knowledge_utc,
                                                        registry=registry, statuses=_pit.CLOSE_STATUSES)}
    y10 = {r.obs_date: r.value for r in _pit.pit_window(store, y10_sid, decision_utc, knowledge_utc, registry=registry)}
    usd = {r.obs_date: r.value for r in _pit.pit_window(store, usd_sid, decision_utc, knowledge_utc, registry=registry)}
    if usd_v is not None and eq_v is not None and usd_v.obs_date < eq_v.obs_date:
        mark(usd_sid, f"snapshot dated {usd_v.obs_date} precedes the last usable US close {eq_v.obs_date}")
    corr = None
    if eq_v is not None and y10_v is not None:
        corr = corr63(eq, y10, max(y10) if y10 else None, int(p["corr_window"]))
        if corr is None:
            mark(y10_sid, f"corr63 needs {int(p['corr_window'])} date-aligned pairs with SPX_OFFICIAL_CLOSE")
    # daily legs on the same US session D (F-16); weekly = the last 5 common sessions; classic_risk_off on the last
    # session with all three legs usable (the 10y leg lags under strict H.15 in backtests; F-27: a yield change)
    hedge_failure = classic = False
    if eq_v is not None and usd_sid not in stale:
        daily = p["hedge_failure_daily"]
        eq_lt = float(daily["equity_ret_lt"])
        common = sorted(d for d in eq if d in usd)
        if len(common) >= 2:
            D, Dp = common[-1], common[-2]
            hedge_failure = _change(eq, D, Dp) < eq_lt and _change(usd, D, Dp) < float(daily["usd_ret_lt"])
        triple = [d for d in common if d in y10]
        if len(triple) >= 2 and y10_sid not in stale:
            D, Dp = triple[-1], triple[-2]
            classic = _change(eq, D, Dp) < eq_lt and _change(usd, D, Dp) > 0.0 and (y10[D] - y10[Dp]) < 0.0
        if len(common) >= 6:
            weekly = p["hedge_failure_weekly"]
            D, D5 = common[-1], common[-6]
            hedge_failure = hedge_failure or (_change(eq, D, D5) < float(weekly["equity_ret_lt"])
                                              and _change(usd, D, D5) < float(weekly["usd_ret_lt"]))
    try:
        fx = _fx_hedge_credit(store, registry, decision_utc, knowledge_utc, p["fx_hedge_credit"])
    except Exception as exc:                                  # display only: never the conservative default (F-30)
        fx = None
        notes.append(f"fx_hedge_credit not computable: {type(exc).__name__}: {exc}")
    reasons = []
    if corr is not None and corr > float(p["corr_threshold"]):
        reasons.append("corr_positive")
    if core_pce is not None and core_pce >= float(p["core_pce_yoy_threshold"]):
        reasons.append("core_pce_ge_3")
    if stale:
        reasons.append("risk_model_input_stale")
    return HedgeState(bool(reasons), bool(hedge_failure), bool(classic), fx, tuple(reasons) or ("ok",), tuple(stale),
                      core_pce, corr, tuple(alerts), tuple(inputs), tuple(notes))


# --------------------------------------------------------------------------- #
# Applying the hedge state to covariance inputs (R-09 Effect L1614; R-19 rule 4; brief B.9)
# --------------------------------------------------------------------------- #
def _nearest_psd(corr: np.ndarray) -> np.ndarray:
    """Clip negative eigenvalues and rescale to unit diagonal (F-24); an already-PSD matrix is returned as is."""
    w, v = np.linalg.eigh((corr + corr.T) / 2.0)
    if w.min() >= -1e-12:
        return corr
    fixed = (v * np.clip(w, 0.0, None)) @ v.T
    d = np.sqrt(np.clip(np.diag(fixed), 1e-12, None))
    out = fixed / np.outer(d, d)
    np.fill_diagonal(out, 1.0)
    return out


def apply_hedge_state(stats, asset_class: Mapping[str, str], hedge: HedgeState):
    """`stats` is a `core.quant.risk.BasketStats` (symbols, cov, corr). When hedge_credit_off, corr[equity,
    duration] = max(corr, 0); when hedge_failure (or while the live USD proxy is stale, F-17) also corr[equity,
    usd_hedge | jpy_hedge]. cov is rebuilt from the clamped, PSD-repaired corr and the unchanged vols; equity gross
    and weights are never touched. asset_class values: equity | duration | usd_hedge | jpy_hedge | other."""
    hedged = {"duration"} if hedge.hedge_credit_off else set()
    if hedge.hedge_failure or "USD_LIVE_PROXY" in hedge.hedge_stale_inputs:
        hedged |= {"usd_hedge", "jpy_hedge"}
    if not hedged:
        return stats
    cls = [asset_class.get(s, "other") for s in stats.symbols]
    corr = np.array(stats.corr, dtype=float, copy=True)
    for i in range(len(cls)):
        for j in range(len(cls)):
            if {cls[i], cls[j]} & {"equity"} and (cls[i] in hedged or cls[j] in hedged):
                corr[i, j] = max(corr[i, j], 0.0)
    corr = _nearest_psd(corr)
    sd = np.sqrt(np.clip(np.diag(np.asarray(stats.cov, dtype=float)), 0.0, None))
    return replace(stats, corr=corr, cov=corr * np.outer(sd, sd))


def covariance_carry(previous: Mapping[str, int], failed: Collection[str], series: Collection[str],
                     carry_max: int = 5) -> tuple[dict[str, str], dict[str, int]]:
    """risk_model_covariance failure action: carry a failing series' last valid terms labelled stale for up to
    `carry_max` decisions, then drop it with a label; never sets hedge_credit_off (L1877, L4239). Returns the
    displayed status per series ("ok" | "stale_carried:<n>" | "dropped") and the next carry state."""
    status, nxt = {}, {}
    for sid in series:
        n = int(previous.get(sid, 0)) + 1 if sid in failed else 0
        nxt[sid] = n
        status[sid] = "ok" if n == 0 else (f"stale_carried:{n}" if n <= carry_max else "dropped")
    return status, nxt


# --------------------------------------------------------------------------- #
# M5: look-through exposure (R-07 (1); R-26 rule 2; T-BOOK-03)
# --------------------------------------------------------------------------- #
LI_MAX_TICK_BP = 10.0                       # instruments.li_etf.max_tick_bp_of_price (L4397; R-26 rule 2, L2802)
SEMIS_DEFAULT = ("005930", "000660")        # F-6: the semiconductor set is owner-signed; at least the pair
PAIR = ("005930", "000660")
TEMPLATES = ("domestic_max10_or_weight", "msci_25_50", "pair_35")
KOREA_CAPS = "risk_layer.korea_caps"
HARD_STOP_LEVEL_REF = "risk_layer.drawdown.hard_stop.level"   # D2's canonical key, read by {ref} only (T-OWNER-01)
R31_KEY = "cards.R-31_step_down"
_EPS = 1e-12


@dataclass(frozen=True)
class Basket:
    """One ETF line's daily look-through basket (the KODEX 200 PDF as published): each name's share of the line's
    NAV, cash in the denominator. `leverage` is L for a leveraged / inverse product (signed; the caps use |L|).
    `price` / `tick` (when given) decide the R-26 rule-2 eligibility; `available_at_utc` is the PIT stamp."""
    code: str
    basket_date: date
    shares: Mapping[str, float]
    leverage: float = 1.0
    price: float | None = None
    tick: float | None = None
    available_at_utc: datetime | None = None


@dataclass(frozen=True)
class Exposure:
    per_name: dict                           # name -> look-through share of the holdings' NAV (|L|-weighted)
    signed: dict                             # name -> signed share (an inverse product is negative; printed only)
    basket_date: date | None
    basket_age_sessions: int
    carried: bool                            # older than the previous session (L1411: carried, age printed)
    fail_closed: bool                        # a held line without a usable basket
    inputs: tuple = ()
    reasons: tuple = ()


def li_etf_eligible(price: float, tick: float, max_bp: float = LI_MAX_TICK_BP) -> bool:
    """R-26 rule 2: a product is eligible only if its tick is <= `max_bp` of its price (exactly 10 bp is eligible)."""
    if not (math.isfinite(price) and price > 0 and math.isfinite(tick) and tick >= 0):
        raise ValueError(f"price {price!r} and tick {tick!r} must be finite and positive")
    return tick / price * 1e4 <= max_bp + _EPS


def _age_sessions(basket_date: date, t: date, sessions) -> int:
    if sessions is None:
        return (t - basket_date).days
    return sum(1 for d in sessions if basket_date < d <= t)


def lookthrough_exposure(holdings: Mapping[str, float], baskets: Mapping[str, Basket], decision_utc: datetime, *,
                         sessions: Sequence[date] | None = None, relatives: Mapping[str, float] | None = None) -> Exposure:
    """Per-name look-through of `holdings` (line code -> weight of NAV) through each line's basket, leveraged and
    inverse products at x L (L1585 (1)). `relatives` (name -> P_i(t) / P_i(basket_date)) recomputes the carried
    basket on current prices (F-4); a name without one keeps its basket share. A basket stamped available after
    `decision_utc`, dated t or later, or absent, fails the line closed (reported, never interpolated); an ineligible L/I product
    (tick > 10 bp of price) raises: it is not tradable in the simulated book (L2863)."""
    t = decision_utc.astimezone(timezone.utc).date()
    per: dict[str, float] = {}
    signed: dict[str, float] = {}
    reasons, inputs, dates, fail = [], [], [], False
    for code, w in holdings.items():
        if w == 0.0:
            continue
        b = baskets.get(code)
        # the basket dated t is published on t+1 (08:00 KST): the decision at the close of t reads t-1 (L1411)
        if b is None or b.basket_date >= t or (b.available_at_utc is not None and b.available_at_utc > decision_utc):
            fail = True
            reasons.append(f"{code}: no basket usable at {_pit.iso_utc(decision_utc)}: fail_closed")
            continue
        if b.price is not None and b.tick is not None and not li_etf_eligible(b.price, b.tick):
            raise ValueError(f"{code}: tick {b.tick} is {b.tick / b.price * 1e4:.1f} bp of price {b.price} > "
                             f"{LI_MAX_TICK_BP:g} bp: ineligible (R-26 rule 2, T-BOOK-03)")
        L = float(b.leverage)
        shares = {n: float(s) for n, s in b.shares.items()}
        if relatives:
            rel = {n: float(relatives.get(n, 1.0)) for n in shares}
            line = sum(s * rel[n] for n, s in shares.items()) + (1.0 - sum(shares.values()))   # cash relative 1
            shares = {n: s * rel[n] / line for n, s in shares.items()}
            reasons.append(f"{code}: basket of {b.basket_date} recomputed on current prices (F-4)")
        for n, s in shares.items():
            per[n] = per.get(n, 0.0) + w * abs(L) * s
            signed[n] = signed.get(n, 0.0) + w * L * s
        dates.append(b.basket_date)
        inputs.append({"code": code, "basket_date": b.basket_date.isoformat(), "leverage": L, "n_names": len(shares)})
    basket_date = min(dates) if dates else None
    age = _age_sessions(basket_date, t, sessions) if basket_date else 0
    return Exposure(per, signed, basket_date, age, age > 1, fail, tuple(inputs), tuple(reasons))


# --------------------------------------------------------------------------- #
# M5: concentration bound (R-07 (2)-(6); section 3.3 L873, L896; T-CAPS-01)
# --------------------------------------------------------------------------- #
def capped_benchmark(benchmark: Mapping[str, float], cap: float | Mapping[str, float]) -> dict:
    """b-tilde: the benchmark capped at the template's single-name level, the excess redistributed pro rata to the
    uncapped names, iterated to a fixed point (F-6). `cap` is one level or a per-name level."""
    b = {n: float(x) for n, x in benchmark.items() if x > 0}
    lvl = (lambda n: float(cap[n])) if isinstance(cap, Mapping) else (lambda n: float(cap))
    capped: set[str] = set()
    for _ in range(len(b) + 1):
        over = {n for n, x in b.items() if n not in capped and x > lvl(n) + _EPS}
        if not over:
            return b
        excess = sum(b[n] - lvl(n) for n in over)
        for n in over:
            b[n] = lvl(n)
        capped |= over
        free = {n: x for n, x in b.items() if n not in capped}
        tot = sum(free.values())
        if tot <= 0.0:
            return b                                             # every name capped: the excess is cash
        for n, x in free.items():
            b[n] = x + excess * x / tot
    return b


def _shares_of(exposure) -> dict:
    s = exposure.per_name if isinstance(exposure, Exposure) else exposure
    return {n: float(x) for n, x in s.items() if x > 0.0}


def _bound(limit: float, share: float) -> float | None:
    return None if share <= 0.0 else limit / share


def concentration_bound(market: str, decision_utc: datetime, template: str | None, exposure, benchmark=None, *,
                        rules=None, semis: Collection[str] = SEMIS_DEFAULT, market_cap_weights=None) -> ConcentrationBound:
    """The maximum gross g of the Korea long book under the D1 template, on the look-through shares `exposure` of the
    book at unit gross (name -> share of the line's NAV, cash in the denominator; an `Exposure` of unit holdings or a
    plain mapping). Every bound is the level over the share it limits (L896, L1585 (4)); `bound` is their min and
    `binding_factor` names it (ties in enum order, F-7). The template is read from the rules store (D1); a `template`
    argument that differs from it is refused (T-OWNER-01). `benchmark` defaults to the line's own basket (F-6)."""
    if market != "KR":
        raise ValueError(f"{market}: the look-through caps are Korea's (R-07); no template for another market")
    if decision_utc.tzinfo is None:
        raise ValueError("decision_utc must be tz-aware UTC")
    caps = _rule(rules, KOREA_CAPS)
    stored = caps["template"]
    if template is None:
        template = stored
    if template != stored:
        raise ValueError(f"template {template!r} is not the rules-store value {stored!r} (D1 is read by reference; T-OWNER-01)")
    if template not in TEMPLATES or template not in caps["templates"]:
        raise ValueError(f"template {template!r} not in {TEMPLATES}")
    p = caps["templates"][template]
    cap_nav = float(caps["active_single_name_cap_nav"])
    semis_max = float(caps["semis_max_share_of_sleeve_nav"])
    s = _shares_of(exposure)
    reasons = []
    absolute = active = aggregate = None
    if template == "pair_35":
        aggregate = _bound(float(p["pair_max_share_of_sleeve_nav"]), sum(s.get(n, 0.0) for n in PAIR))
        reasons.append("pair_35: the pair cap binds as the aggregate factor (F-7)")
    else:
        if template == "msci_25_50":
            level: float | dict = float(p["single_name_max"])
        else:                                                    # domestic_max10_or_weight: max(0.10, market-cap weight)
            if market_cap_weights is None:
                raise ValueError("domestic_max10_or_weight needs the names' market-cap weights "
                                 "(KRX_MARKET_CAPS_005930_000660_KOSPI); none given: fail closed")
            level = {n: max(0.10, float(market_cap_weights.get(n, 0.0))) for n in s}
        lvl = (lambda n: level[n]) if isinstance(level, dict) else (lambda n: level)
        if s:
            absolute = min(lvl(n) / x for n, x in s.items())
        b = capped_benchmark(s if benchmark is None else benchmark, level)
        over = [(n, x - b.get(n, 0.0)) for n, x in s.items() if x - b.get(n, 0.0) > _EPS]
        if over:
            active = min(cap_nav / gap for _, gap in over)
            reasons.append("active single-name cap w_i - g*b_i <= %.2f binds on %s" % (cap_nav, ", ".join(n for n, _ in over)))
        if template == "msci_25_50":
            above = [x for x in s.values() if x > float(p["names_above"]) + _EPS]
            aggregate = _bound(float(p["aggregate_max"]), sum(above))
    semis_share = sum(s.get(n, 0.0) for n in semis)
    semis_b = _bound(semis_max, semis_share)
    cands = [("absolute_single_name", absolute), ("active_single_name", active), ("aggregate", aggregate), ("semis", semis_b)]
    finite = [(f, x) for f, x in cands if x is not None]
    if not finite:
        raise ValueError("no look-through share: the concentration bound is undefined (fail closed)")
    bound = min(x for _, x in finite)
    if bound < 0.0:
        raise ValueError(f"concentration bound {bound} < 0")
    factor = next(f for f, x in finite if x == bound)
    pair_share = sum(s.get(n, 0.0) for n in PAIR)
    basket = exposure.basket_date.isoformat() if isinstance(exposure, Exposure) and exposure.basket_date else "unit shares"
    reasons.append("bound %.4f (%s) on the basket of %s; pair look-through %.4f" % (bound, factor, basket, pair_share))
    return ConcentrationBound(absolute, active, aggregate, semis_b, bound, factor, template, pair_share,
                              tuple(sorted(s.items(), key=lambda kv: -kv[1])), tuple(reasons))


def risk_limit_breach(post_action: Mapping[str, float], *, rules=None, template: str | None = None) -> str | None:
    """R-07 (3) breach test on the post-action look-through weights (name -> weight of book NAV after the prescribed
    action; carried orders at their held weight): a single name above the hard level (0.25) or the names above 4.5%
    above 0.50 in aggregate is the RISK `risk_limit_breach`; None when the limit is met. A HALTED book's zero
    exposure meets nothing by itself (L1179): the caller tests the target it would hold on re-arming."""
    caps = _rule(rules, KOREA_CAPS)
    template = template or caps["template"]
    p = caps["templates"][template]
    w = {n: float(x) for n, x in post_action.items()}
    if template == "pair_35":
        pair = sum(w.get(n, 0.0) for n in PAIR)
        return f"breach_pair:{pair:.4f}" if pair > float(p["pair_max_share_of_sleeve_nav"]) + _EPS else None
    if template != "msci_25_50":
        raise ValueError(f"template {template!r} declares no hard levels (breach_single_name / breach_aggregate): fail closed")
    worst = max(w.items(), key=lambda kv: kv[1], default=(None, 0.0))
    if worst[0] is not None and worst[1] > float(p["breach_single_name"]) + _EPS:
        return f"breach_single_name:{worst[0]}"
    agg = sum(x for x in w.values() if x > float(p["names_above"]) + _EPS)
    if agg > float(p["breach_aggregate"]) + _EPS:
        return f"breach_aggregate:{agg:.4f}"
    return None


# --------------------------------------------------------------------------- #
# M5: drawdown ladder (R-31 L3278-3303 verbatim; R-07 hard stop; I-04, T-STEP-05, T-HALT-01)
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class LadderConfig:
    hard_stop_level: float
    steps: tuple                             # ((dd, mult, block), ...) deepest first
    dwell: int                               # DWELL sessions, the trigger decision included
    rearm_refused_sessions: int = 10
    post_rearm_sessions: int = 10
    binding_share_threshold: float = 0.10
    notes: tuple = ()


def hard_stop_level(rules=None, *, level_ref: str = HARD_STOP_LEVEL_REF) -> tuple[float, tuple]:
    """D2 through the R-31 card's `{ref}` (L3327): the stored shape must be `{"ref": level_ref}`, never a literal copy
    (T-OWNER-01). Option (b) `-1.5*sigma_book` is not evaluated until an owner ruling defines sigma_book (F-8, S1
    deviation 13): the registry default stays in force, noted."""
    store = _shipped_store() if rules is None else rules
    raw = store.raw(f"{R31_KEY}.hard_stop_level") if hasattr(store, "raw") else _rule(store, f"{R31_KEY}.hard_stop_level")
    if not (isinstance(raw, Mapping) and set(raw) == {"ref"} and raw["ref"] == level_ref):
        raise ValueError(f"{R31_KEY}.hard_stop_level must be {{'ref': {level_ref!r}}}, never a literal copy (T-OWNER-01); got {raw!r}")
    level = _rule(rules, level_ref)
    notes: tuple = ()
    if isinstance(level, str):
        default = _rule(rules, "owner_decisions.D2.default")
        notes = (f"D2 option {level!r} is not evaluated until sigma_book is defined (F-8): default {default} in force",)
        level = default
    level = float(level)
    if not (-1.0 < level < 0.0):
        raise ValueError(f"hard-stop level {level} must be a negative fraction of NAV")
    return level, notes


def ladder_config(rules=None, *, level_ref: str = HARD_STOP_LEVEL_REF) -> LadderConfig:
    """`cards.R-31_step_down` plus the D2 level; refuses a composition other than min and a step outside {0.5, 1.0}."""
    card = _rule(rules, R31_KEY)
    if card.get("composition") != "min":
        raise CompositionError(f"{R31_KEY}.composition {card.get('composition')!r}: a ladder path composed by product raises (R-02, L3338)")
    steps = []
    for st in card["steps"]:
        if float(st["mult"]) not in STEP_VALUES:
            raise CompositionError(f"ladder step multiplier {st['mult']!r} not in {STEP_VALUES} (section 10 item 2)")
        steps.append((float(st["dd"]), float(st["mult"]), bool(st.get("evaluator_block_new_entries", False))))
    level, notes = hard_stop_level(rules, level_ref=level_ref)
    hs = _rule(rules, "risk_layer.drawdown.hard_stop")
    return LadderConfig(level, tuple(sorted(steps)), int(card["dwell_sessions"]), int(hs["rearm_refused_sessions"]),
                        int(hs["post_rearm_sessions"]), float(card["binding_share_threshold"]), notes)


LADDER_INITIAL = LadderState(None, None, 1.0, 0, False, False, None, 0, None)


def clear_steps(state: LadderState) -> LadderState:
    return replace(state, step_mult=1.0, block_new_entries=False, dwell_left=0)


def ladder_step(state: LadderState, nav_t: float, cfg: LadderConfig) -> LadderState:
    """One decision of the R-31 pseudocode (L3278-3301) at the close of t, setting the multiplier for t+1. Pure.
    Not evaluated while HALTED (references frozen, F-1); a hard stop returns `halted=True` with the steps cleared
    and the caller HALTs the book (RISK, hard_stop); `<=` on every level (exactly -15.00% triggers, T-HALT-01)."""
    if state.halted:
        return state
    if not (isinstance(nav_t, (int, float)) and math.isfinite(nav_t) and nav_t > 0):
        raise ValueError(f"nav {nav_t!r} is not a positive finite number (a missing NAV holds the state, it is not 0)")
    nav_t = float(nav_t)
    hwm = nav_t if state.hwm_hard is None else max(state.hwm_hard, nav_t)
    ref = state.ref_step if state.ref_step is not None else nav_t
    if state.dwell_left == 0:
        ref = max(ref, nav_t)                                   # running peak since the last reset
    dd_hard, dd_step = nav_t / hwm - 1.0, nav_t / ref - 1.0
    mult, block, dwell = state.step_mult, state.block_new_entries, state.dwell_left
    if dd_hard <= cfg.hard_stop_level + _EPS:
        return replace(clear_steps(state), hwm_hard=hwm, ref_step=ref, halted=True)
    if dwell > 0:                                               # inside the time box
        mult, dwell = 0.5, dwell - 1
        if dd_step <= cfg.steps[0][0] + _EPS:
            block = True                                        # escalation adds the block; sizing and clock unchanged
        if dwell == 0:
            ref = nav_t                                         # step spent: its reference resets; hwm_hard does not
    else:
        hit = next(((m, b) for dd, m, b in cfg.steps if dd_step <= dd + _EPS), None)
        if hit:
            mult, block, dwell = hit[0], hit[1], cfg.dwell - 1   # DWELL sessions incl. the first
        else:
            mult, block = 1.0, False
    return replace(state, hwm_hard=hwm, ref_step=ref, step_mult=mult, block_new_entries=block, dwell_left=dwell)


def _nav_points(nav_path) -> list[tuple[date | None, float]]:
    out = []
    for p in nav_path:
        if isinstance(p, (tuple, list)) and len(p) == 2:
            d, v = p
            d = d.astimezone(timezone.utc).date() if isinstance(d, datetime) else d
            out.append((d, float(v)))
        else:
            out.append((None, float(p)))
    return out


def ladder_path(nav_path, config: LadderConfig | None = None, *, rules=None) -> list[LadderState]:
    """Fold `ladder_step` over a whole-book NAV path ((date, nav) pairs or bare values, one per decision) with the
    R-07 cycle: a hard stop HALTs, the re-arm is refused for `rearm_refused_sessions` decisions and automatic at the
    next, both references reset to the NAV at re-arm, `post_rearm_left` counts the decisions still carrying the 0.5
    cap (this one included). Reference mode and the M7 binding share read this; the runtime steps one decision."""
    cfg = config or ladder_config(rules)
    pts = _nav_points(nav_path)
    out, state, halt_i, left = [], LADDER_INITIAL, None, 0
    for i, (d, nav) in enumerate(pts):
        if state.halted and i >= halt_i + cfg.rearm_refused_sessions:          # automatic re-arm at t+10
            state = replace(clear_steps(state), halted=False, hwm_hard=nav, ref_step=nav, rearm_not_before=None)
            left, halt_i = cfg.post_rearm_sessions, None
        if not state.halted:
            state = ladder_step(state, nav, cfg)
            if state.halted:
                halt_i, left = i, 0
                j = i + cfg.rearm_refused_sessions
                state = replace(state, rearm_not_before=pts[j][0] if j < len(pts) else None)
        out.append(replace(state, post_rearm_left=left))
        left = max(left - 1, 0)
    return out


def drawdown_ladder(nav_path, decision_utc: datetime, config=None, *, binding_share: float | None = None) -> LadderState:
    """`LadderState` at the close of `decision_utc` from the dated whole-book NAV path (R-31 names binding, L3271).
    `config` is a `LadderConfig`, a rules store / dict, or None (the shipped store). A NAV dated after the decision
    is refused (never read ahead); no NAV at or before it is a fail-closed error. `binding_share` is the share frozen
    with the R-31 header (M7), carried for the disposition; None until a header exists."""
    cfg = config if isinstance(config, LadderConfig) else ladder_config(config)
    t = decision_utc.astimezone(timezone.utc).date()
    pts = _nav_points(nav_path)
    if any(d is not None and d > t for d, _ in pts):
        raise ValueError(f"nav_path holds a NAV dated after the decision {t}: a look-ahead read is refused")
    if not pts:
        raise ValueError("nav_path is empty: the ladder state is undefined (fail closed)")
    states = ladder_path(pts, cfg)
    return replace(states[-1], binding_share=binding_share)


def binding_share_of(states: Sequence[LadderState]) -> float | None:
    """n_bind / n_sessions over the states of one book path (L3305); None on an empty path."""
    n = len(states)
    return None if n == 0 else sum(1 for s in states if s.step_mult < 1.0) / n


def steps_act_in(book_id: str, binding_share: float | None, *, r31_pass: bool = False,
                 threshold: float = 0.10) -> bool:
    """Where the R-31 steps act (L3305-3307; F-2): every specification book; a recommended book only as
    INVARIANT_STEP (a frozen binding share <= 0.10) or after an R-31 PASS; card, FORWARD-SIM and refusal books never."""
    kind = book_id.split(":", 1)[0]
    if kind == "specification":
        return True
    if kind == "recommended":
        return bool(r31_pass) or (binding_share is not None and binding_share <= threshold + _EPS)
    return False


def ladder_disposition(binding_share: float | None, threshold: float = 0.10) -> str:
    """INVARIANT_STEP at a frozen share <= 0.10, else SPECIFICATION_ONLY (None = no header yet: specification only)."""
    return "INVARIANT_STEP" if binding_share is not None and binding_share <= threshold + _EPS else "SPECIFICATION_ONLY"


def ladder_for_book(state: LadderState, book_id: str, *, binding_share: float | None = None,
                    r31_pass: bool = False) -> tuple[float, bool]:
    """(ladder term of min(), block_new_entries) for one book: the state's values where the steps act, else (1.0, False)."""
    if steps_act_in(book_id, binding_share, r31_pass=r31_pass):
        return state.step_mult, state.block_new_entries
    return 1.0, False


def ladder_flags(state: LadderState, *, level: float, acts_in: str = "specification", rearm_refused: bool = False) -> dict:
    """The ladder / hard-stop part of `macro_state.flags` (L3575-3584; F-3 mapping). Display fields only."""
    step = "hard_stop_-15" if state.halted else ("step_-12" if state.block_new_entries else ("step_-8" if state.step_mult < 1.0 else "none"))
    hs = ("rearm_refused" if state.halted and rearm_refused else "halted" if state.halted
          else "post_rearm_cap" if state.post_rearm_left > 0 else "armed")
    return {"ladder_step": step, "ladder_dwell_left": int(state.dwell_left), "block_new_entries": bool(state.block_new_entries),
            "ladder_steps_act_in": acts_in, "hard_stop": hs, "hard_stop_level": float(level)}


__all__ = [n for n in dir() if not n.startswith("_")]
