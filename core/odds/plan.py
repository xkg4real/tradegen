"""Odds plan types, the injected-input types, the refusal codes and the product, state and data checks (spec 7.1,
7.2 "Data rules"; odds plan Q4, Q7, Q8, Q23, Q24, Q25, Q39). Pure: no clock, no file, no network. Every check
returns the first Refusal it finds, or None; check_plan, check_state and check_now never raise."""
from __future__ import annotations

import dataclasses
import hashlib
import math
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import TYPE_CHECKING

from core.compliance import model

if TYPE_CHECKING:
    from core.compliance import rules

# --------------------------------------------------------------------------- #
# Constants (contract 5.1)
# --------------------------------------------------------------------------- #
REFUSALS = ("PARTIAL_CHUNK", "UNSUPPORTED_PRODUCT", "MULTI_LEG_UNSUPPORTED", "STATE_UNUSABLE", "LIMITS_UNSET",
            "CALENDAR_UNSIGNED", "CALENDAR_COVERAGE", "DATA_INVALID", "SYNTHETIC_REFUSED", "NOT_TRADABLE",
            "SPECIAL_REGIME", "SHORT_HISTORY", "CARD_NOT_REPRODUCED", "MODEL_NOT_FOR_LIMITED_VENUE", "COST_DOMINATED",
            "STUCK_AT_START", "SCREEN_BLOCKED", "ASSUMED_EDGE_UNREACHABLE", "MODEL_CHECK_FAILED")
            # the codes; their reporting order is Q24's numbered list (DATA_INVALID sub "now" comes before CALENDAR_*)
VENUES_OK = ("kis", "upbit", "okx")
CLASSES_OK = ("share", "etp_1x", "coin")
TRACKS = ("moonshot", "compounding")
MODELS = ("bootstrap", "garch_t")
SIZINGS = ("floor_safe", "stop_based")
REPLAY_SOURCE = "replay:S_C3_crypto_trend_krwbtc"
EDGE_SOURCES = ("none", "assumed", REPLAY_SOURCE)
FRACTION_KINDS = ("fixed", "kelly", "bold")
TAX_BASES_OK = ("krx_small_holder_exempt", "overseas_22pct_over_2.5m", "crypto_22pct_from_2027")
MAX_HORIZON_DAYS = 366
MIN_BARS = 250
SPECIAL_REGIME_BARS = 60
STALE_DAYS = {"CRYPTO": 3, "KR": 14, "US": 14}     # Q39: the last bar at most this many calendar days before start
LIMIT_KEYS = ("total_loss_floor_krw", "daily_loss_krw")
OKX_CAP_KEY = "okx_equity_share"
FEEDS = {("kis", "krx"): "kis_daily", ("kis", "us"): "yfinance", ("upbit", "crypto"): "upbit_daily",
         ("okx", "crypto"): "binance_x_upbit_usdt"}    # okx: symbol BTC only
MARKET = {("kis", "krx"): "KR", ("kis", "us"): "US", ("upbit", "crypto"): "CRYPTO", ("okx", "crypto"): "CRYPTO"}

_ISO = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
_SHA = re.compile(r"[0-9a-f]{64}")


# --------------------------------------------------------------------------- #
# Types (contract 5.2)
# --------------------------------------------------------------------------- #
@dataclass(frozen=True, kw_only=True)
class Bracket:
    take_profit: float                               # +u as a fraction: 0 < u <= 1000
    stop: float                                      # -d as a fraction: 0 < d < 1


@dataclass(frozen=True, kw_only=True)
class Fraction:
    kind: str                                        # "fixed" | "kelly" | "bold"
    value: float | None = None


def fixed(f: float) -> Fraction:
    return Fraction(kind="fixed", value=float(f))


def kelly(c: float) -> Fraction:
    return Fraction(kind="kelly", value=float(c))


def bold() -> Fraction:
    return Fraction(kind="bold")


@dataclass(frozen=True, kw_only=True)
class Leg:
    venue: str
    symbol: str
    model: str                                       # "bootstrap" | "garch_t"
    bracket: Bracket | None = None                   # None: buy at the first check and hold
    sizing: str = "floor_safe"                       # "floor_safe" | "stop_based" (bracket legs only)
    edge_source: str = "none"                        # one of EDGE_SOURCES
    assumed_p: float | None = None


@dataclass(frozen=True, kw_only=True)
class Plan:
    name: str                                        # cosmetic; never hashed, never rendered
    track: str                                       # "moonshot" | "compounding"
    stake_krw: float
    target_krw: float                                # before income tax, fixed in KRW
    fx_krw_per_usd: float
    start: date                                      # the Asia/Seoul date of the run
    horizon_days: int                                # half-open [start, start + horizon_days)
    leg: Leg
    fraction: Fraction


@dataclass(frozen=True, kw_only=True)
class Refusal:
    code: str                                        # one of REFUSALS
    sub: str = ""                                    # a catalogue sub-reason key suffix, or ""
    slots: Mapping[str, str] = field(default_factory=dict)    # render slots: numbers, dates, symbols, row ids only
    detail: str = ""                                 # internal text for logs and tests; never rendered


@dataclass(frozen=True, kw_only=True)
class Series:
    symbol: str
    source: str
    dates: tuple[str, ...]                           # ISO dates, strictly increasing, all before the start
    open: tuple[float, ...]                          # KRW
    close: tuple[float, ...]                         # KRW
    adjustment: str
    status: str
    md5: str                                         # series_md5 of the seven fields above
    components: tuple[tuple[str, str], ...] = ()     # (label, md5) of each downloaded part
    proxy_dates: tuple[str, str] | None = None       # first and last date priced through the FX fallback


@dataclass(frozen=True, kw_only=True)
class Provenance:
    repo_anchor: str
    tree_hash: str
    cryptography: str                                # its version, read by the unsigned side ("absent" when missing)


@dataclass(frozen=True, kw_only=True)
class ReplayInput:
    card_id: str
    input_symbol: str
    input_source: str
    input_dates: tuple[str, ...]
    input_close: tuple[float, ...]
    oos_dates: tuple[str, ...]
    oos_pnl: tuple[float, ...]
    oos_turnover: tuple[float, ...]
    lookbacks: tuple[int, ...]
    mas: tuple[int, ...]
    grid: tuple[float, ...]
    cost_bps_per_side: float
    embargo: int
    n_trials: int
    seed: int
    domain: tuple[float, float]
    protocol: Mapping[str, float]
    gate_protocol: Mapping[str, float]
    stats: Mapping[str, object]      # sr_oos, bench_sr, haircut_sr, bench_diff, bench_ci (2-tuple), decision,
                                     # chosen_last (hysteresis float), n_sessions, n_trades
    results_md5: str
    card_md5: str


@dataclass(frozen=True, kw_only=True)
class Inputs:
    now: datetime                    # aware; the moment load_context saw
    series: Series
    sessions: tuple[str, ...]        # the horizon's session dates (each market's own date), ISO
    price_limits: tuple[float, ...]  # KRX: one per session; other legs: ()
    calendar_sha256: str             # KRX/US: rules.calendar_sha256 of the set used; crypto: ""
    calendar_version: str
    calendar_md5s: tuple[tuple[str, str], ...]       # (file id, md5)
    calendar_error: str              # "" | "unsigned: <text>" | "coverage: <text>"
    replay: ReplayInput | None
    comparison_id: str
    run_counter: int                 # the comparison's own counter, fixed when begin_run created it (Q12, Q34)
    comparison_plans: int            # K, this plan included
    comparison_typed: int            # J, this plan included
    plan_runs: int                   # R: comparisons whose plans include this plan hash, this one included (Q12)
    provenance: Provenance


# --------------------------------------------------------------------------- #
# Hashes and lookups (contract 5.3)
# --------------------------------------------------------------------------- #
def series_md5(symbol, source, dates, open_, close, adjustment, status) -> str:
    """md5 of the canonical JSON {symbol, source, dates, open, close, adjustment, status} (spec 7.2)."""
    return hashlib.md5(model.canonical_json({"symbol": symbol, "source": source, "dates": list(dates),
                                             "open": list(open_), "close": list(close), "adjustment": adjustment,
                                             "status": status}).encode("utf-8")).hexdigest()


def plan_hash(plan: Plan) -> str:
    """sha256 of the canonical JSON of the plan with its name blanked: renaming a plan changes nothing."""
    return model.sha256_hex(model.canonical_json(dataclasses.replace(plan, name="")))


def _leg(plan) -> Leg | None:
    """The plan's one Leg: plan.leg, or the only item of a one-item list or tuple; else None."""
    leg = getattr(plan, "leg", None)
    if isinstance(leg, (list, tuple)) and len(leg) == 1:
        leg = leg[0]
    return leg if type(leg) is Leg else None


def _usable(state) -> bool:
    """gate._usable: a valid ApprovedState with its three tables."""
    return (isinstance(state, model.ApprovedState) and state.valid is True and state.rules is not None
            and state.instruments is not None and state.venues is not None)


def instrument(plan: Plan, ctx) -> tuple[rules.Venue | None, rules.Instrument | None]:
    """The leg's venue facts and instrument from the APPROVED state in ctx.active (never a draft file); (None, None)
    when that state is not usable."""
    state, leg = getattr(ctx, "active", None), _leg(plan)
    if not _usable(state) or leg is None or type(leg.venue) is not str:
        return None, None
    venue = state.venues.venues.get(leg.venue)
    return venue, (state.instruments.lookup(venue.sections, leg.symbol) if venue is not None else None)


def section(plan: Plan, ctx) -> str | None:
    """The instrument's section ("krx" | "us" | "crypto"), or None."""
    inst = instrument(plan, ctx)[1]
    return inst.section if inst is not None else None


# --------------------------------------------------------------------------- #
# Checks (Q24 steps 2-5, 7 and 9; Q25, Q39)
# --------------------------------------------------------------------------- #
def _is(value, members) -> bool:
    return type(value) is str and value in members


def _float(value) -> bool:
    """A finite float (an int is refused, so a plan's hash never depends on how a number was typed)."""
    return type(value) is float and math.isfinite(value)


def _real(value) -> bool:
    """A finite float or an int below 2**63, never a bool (gate._number)."""
    if type(value) is float:
        return math.isfinite(value)
    return type(value) is int and abs(value) < 2 ** 63


def _iso(value) -> bool:
    if type(value) is not str or not _ISO.fullmatch(value):
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _fraction_ok(frac, bracket, replay: bool) -> bool:
    """fixed(0 < f <= 1); kelly(0 < c <= 0.5) on the replay only; bold() on bracket legs only (Q25)."""
    if type(frac) is not Fraction:
        return False
    if frac.kind == "fixed":
        return _real(frac.value) and 0 < frac.value <= 1
    if frac.kind == "kelly":
        return replay and _real(frac.value) and 0 < frac.value <= 0.5
    if frac.kind == "bold":
        return frac.value is None and bracket is not None and not replay
    return False


def _edge_ok(leg: Leg) -> bool:
    """assumed: a bracket, the bootstrap model and 0 < assumed_p < 1; otherwise no assumed_p (Q25)."""
    if leg.edge_source == "assumed":
        return (leg.bracket is not None and leg.model == "bootstrap" and _real(leg.assumed_p)
                and 0 < leg.assumed_p < 1)
    return _is(leg.edge_source, EDGE_SOURCES) and leg.assumed_p is None


def _product(plan, ctx) -> tuple[str, str] | None:
    """(sub, detail) of the first UNSUPPORTED_PRODUCT rule the plan breaks, in contract 5.3's order."""
    if type(plan) is not Plan or type(plan.name) is not str:
        return "file", "not a Plan with a text name"
    if not _is(plan.track, TRACKS):
        return "track", f"track {plan.track!r}"
    stake, target, fx = plan.stake_krw, plan.target_krw, plan.fx_krw_per_usd
    if not (_float(stake) and _float(target) and _float(fx) and stake > 0 and target > stake and fx > 0):
        return "numbers", f"stake {stake!r}, target {target!r}, fx {fx!r}"
    today = getattr(ctx, "date", None)
    if type(plan.start) is not date or plan.start != today:
        return "start", f"start {plan.start!r}, context date {today!r}"
    if type(plan.horizon_days) is not int or not 1 <= plan.horizon_days <= MAX_HORIZON_DAYS:
        return "horizon", f"horizon_days {plan.horizon_days!r}"
    leg = _leg(plan)
    if leg is None:
        return "file", f"leg {plan.leg!r} is not one Leg"
    if not _is(leg.model, MODELS):
        return "model", f"model {leg.model!r}"
    if not _is(leg.sizing, SIZINGS) or (leg.sizing == "stop_based" and leg.bracket is None):
        return "sizing", f"sizing {leg.sizing!r} with bracket {leg.bracket!r}"
    replay = leg.edge_source == REPLAY_SOURCE
    if not _fraction_ok(plan.fraction, leg.bracket, replay):
        return "fraction", f"fraction {plan.fraction!r} with bracket {leg.bracket!r}"
    b = leg.bracket
    if b is not None and not (type(b) is Bracket and _real(b.take_profit) and _real(b.stop)
                              and 0 < b.take_profit <= 1000 and 0 < b.stop < 1):
        return "bracket", f"bracket {b!r}"
    if not _edge_ok(leg):
        return "edge", f"edge_source {leg.edge_source!r}, assumed_p {leg.assumed_p!r}"
    if replay and not (leg.venue == "upbit" and leg.symbol == "BTC" and b is None and leg.model == "bootstrap"
                       and leg.sizing == "floor_safe"):
        return "replay", f"replay leg {leg.venue!r} {leg.symbol!r}"
    if not _is(leg.venue, VENUES_OK):
        return "venue", f"venue {leg.venue!r}"
    if leg.venue == "okx" and leg.symbol != "BTC":
        return "feed", f"okx {leg.symbol!r} has no price feed"
    if _usable(getattr(ctx, "active", None)):
        inst = instrument(plan, ctx)[1]
        if inst is None:
            return "symbol", f"{leg.venue} {leg.symbol!r} is not in the approved instrument map"
        if (leg.venue, inst.section) not in FEEDS:         # a signed venue file may list a section with no feed
            return "feed", f"{leg.venue} has no price feed for section {inst.section}"
        if inst.cls not in CLASSES_OK:
            return "class", f"class {inst.cls}"
        if inst.multiple != 1.0:
            return "multiple", f"multiple {inst.multiple}"
        if inst.tax_basis not in TAX_BASES_OK:
            return "tax", f"tax basis {inst.tax_basis}"
    return None


def check_plan(plan, ctx) -> Refusal | None:
    """The product refusals of Q24 step 2: MULTI_LEG_UNSUPPORTED for a list or tuple of two or more legs, then
    UNSUPPORTED_PRODUCT with its sub (an empty list, or one item that is not a Leg, is sub "file"). The instrument
    checks run only on a usable ctx.active."""
    legs = getattr(plan, "leg", None)
    if isinstance(legs, (list, tuple)) and len(legs) > 1:
        return Refusal(code="MULTI_LEG_UNSUPPORTED", detail=f"{len(legs)} legs")
    found = _product(plan, ctx)
    return None if found is None else Refusal(code="UNSUPPORTED_PRODUCT", sub=found[0], detail=found[1])


def _cap_ok(cap) -> bool:
    """gate._cap's rule: a number in (0, 1] (_real: a finite float or an int below 2**63, never a bool)."""
    return _real(cap) and 0 < cap <= 1


def check_state(plan, ctx) -> Refusal | None:
    """Q24 steps 3-4: STATE_UNUSABLE (sub "code" for unsigned code), then LIMITS_UNSET (sub "cap" for an OKX leg
    without its cap). A floor of 0 is a set limit."""
    if not model.is_sealed(ctx):
        return Refusal(code="STATE_UNUSABLE", detail="state: context not from load_context")
    owner = ctx.owner
    if not (isinstance(owner, model.OwnerState) and owner.ok):
        return Refusal(code="STATE_UNUSABLE", detail=f"owner log: {getattr(owner, 'reason', '') or 'not OK'}")
    if not _usable(ctx.active):
        return Refusal(code="STATE_UNUSABLE", detail=f"state: {getattr(ctx.active, 'reason', '') or 'unusable'}")
    if ctx.code_signed is not True:
        return Refusal(code="STATE_UNUSABLE", sub="code", detail="unsigned code")
    missing = [key for key in LIMIT_KEYS if key not in owner.limits]
    if missing:
        return Refusal(code="LIMITS_UNSET", detail=f"unset: {', '.join(missing)}")
    leg = _leg(plan)
    if leg is not None and leg.venue == "okx" and not _cap_ok(owner.caps.get(OKX_CAP_KEY)):
        return Refusal(code="LIMITS_UNSET", sub="cap", detail=f"{OKX_CAP_KEY} {owner.caps.get(OKX_CAP_KEY)!r}")
    return None


def check_now(ctx, now) -> Refusal | None:
    """DATA_INVALID sub "now" unless `now` is an aware datetime whose Asia/Seoul date is ctx.date."""
    today = getattr(ctx, "date", None)
    try:
        ok = isinstance(now, datetime) and now.utcoffset() is not None and now.astimezone(model.KST).date() == today
    except (OverflowError, TypeError, ValueError):
        ok = False
    return None if ok else Refusal(code="DATA_INVALID", sub="now", detail=f"now {now!r}, context date {today!r}")


def _series_problem(s, start: date) -> str:
    """Q39 sub "series": "" when the series passes, else why not."""
    if type(s) is not Series:
        return "not a Series"
    try:
        n = len(s.dates)
        if n < 2 or len(s.open) != n or len(s.close) != n:
            return f"lengths {n}, {len(s.open)}, {len(s.close)}: need one length >= 2"
        if not all(_real(x) and x > 0 for x in (*s.open, *s.close)):
            return "a price is not a finite number > 0"
        if not all(_iso(d) for d in s.dates):
            return "a date is not an ISO calendar date"
        if any(a >= b for a, b in zip(s.dates, s.dates[1:])):
            return "dates are not strictly increasing"
        if s.dates[-1] >= start.isoformat():
            return f"the last bar {s.dates[-1]} is not before the start {start}"
        if s.md5 != series_md5(s.symbol, s.source, s.dates, s.open, s.close, s.adjustment, s.status):
            return "md5 differs from the one recomputed here"
    except (TypeError, ValueError) as exc:
        return f"unreadable ({type(exc).__name__})"
    return ""


def _sessions_problem(inputs, start: date, horizon: int, market: str) -> str:
    """Q39 sub "sessions": "" when the session list, the price limits and the calendar sha pass."""
    try:
        days, limits, sha = inputs.sessions, inputs.price_limits, inputs.calendar_sha256
        if not all(_iso(d) for d in days) or any(a >= b for a, b in zip(days, days[1:])):
            return "sessions are not strictly increasing ISO dates"
        end = (start + timedelta(days=horizon)).isoformat()
        if days and (days[0] < start.isoformat() or days[-1] >= end):
            return f"sessions {days[0]} .. {days[-1]} leave [{start}, {end})"
        if market == "KR":
            if len(limits) != len(days) or not all(_real(x) and 0 < x < 1 for x in limits):
                return "a KRX leg needs one price limit in (0, 1) per session"
        elif len(limits):
            return "price limits on a market without a daily band"
        if market in ("KR", "US") and not (type(sha) is str and _SHA.fullmatch(sha)):
            return "a KRX or US leg needs the 64-hex calendar sha"
        if market not in ("KR", "US") and sha != "":
            return "a crypto leg carries no calendar sha"
    except (AttributeError, TypeError, ValueError, OverflowError) as exc:
        return f"unreadable ({type(exc).__name__})"
    return ""


def check_data(plan, ctx, inputs, market: str) -> Refusal | None:
    """Q24 step 7 (Q39): DATA_INVALID subs "series", "stale", "sessions", "empty", in that order, then
    SYNTHETIC_REFUSED. `market` is MARKET[(venue, section)]; `ctx` is not read (simulate checks `now` and the
    calendar before this step)."""
    s, start = getattr(inputs, "series", None), plan.start
    why = _series_problem(s, start)
    if why:
        return Refusal(code="DATA_INVALID", sub="series", detail=why)
    gap = (start - date.fromisoformat(s.dates[-1])).days
    if gap > STALE_DAYS[market]:
        return Refusal(code="DATA_INVALID", sub="stale", slots={"days": str(STALE_DAYS[market])},
                       detail=f"the last bar {s.dates[-1]} is {gap} days before the start {start}")
    why = _sessions_problem(inputs, start, plan.horizon_days, market)
    if why:
        return Refusal(code="DATA_INVALID", sub="sessions", detail=why)
    if not inputs.sessions:
        return Refusal(code="DATA_INVALID", sub="empty", detail=f"no {market} session in the horizon")
    if s.status == "SYNTHETIC" or s.source == "SYNTHETIC":
        return Refusal(code="SYNTHETIC_REFUSED", detail=f"status {s.status!r}, source {s.source!r}")
    return None


def check_history(plan, inputs, market: str) -> Refusal | None:
    """Q24 step 9 (Q8, Q23): a KRX leg with fewer than SPECIAL_REGIME_BARS bars before the start is SPECIAL_REGIME;
    then any leg with fewer than MIN_BARS is SHORT_HISTORY. simulate runs it after costs.terms and check_validity."""
    first = plan.start.isoformat()
    bars = sum(1 for d in inputs.series.dates if d < first)
    slots = {"symbol": _leg(plan).symbol}
    if market == "KR" and bars < SPECIAL_REGIME_BARS:
        return Refusal(code="SPECIAL_REGIME", slots=slots, detail=f"{bars} KRX bars before {first}")
    if bars < MIN_BARS:
        return Refusal(code="SHORT_HISTORY", slots=slots, detail=f"{bars} bars before {first}")
    return None
