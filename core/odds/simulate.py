"""The odds path engine (spec 7.1 "Rounding and re-entry", 7.2 "Brackets", "Bands", "Band edges", "Limit-down locks",
"Delisting stress", 7.3; odds plan Q5, Q22, Q26, Q27, Q28, Q29; contract section 8).

`run_column` simulates one column (a member's model under one cost scenario) in chunks of CHUNK paths and folds the
per-path results into a `report.ColumnStats`. `_run_paths` runs the state machine of contract 8.4 over any number of
paths: at each check it moves the price inside the session's band, values every path at its liquidation value,
records first passage, fills at most one exit (a queued locked exit, a delisting sale, then target, take-profit,
stop, daily loss and rule date, in that order) and, from the next check on and never at the last one, one entry
sized by `costs.rule_units`. Every fill and every delisting sale books its charges and losses, so the gross value
cash + units x price + costs moves only with the price: with no edge it is a martingale, and X = G_tau - W0 is the
HIDDEN_EDGE sample.

KRX legs move inside each session's daily band [D, U] (costs.band around the previous close). An exit that triggers
at the session's D cannot fill: it is locked and queued until the first check strictly above that D, and then fills
at a flat 2x exit charge (LIMIT_DOWN_CARRY_COST_MULTIPLIER); a position still locked at the horizon is valued the
same way. The daily loss stop works on Asia/Seoul dates, the rule dates of the screening stop entries (Q5) and force
an exit, and a delisting column sells at p (1 - h) at the first check after the first entry (Q29). Not simulated
yet, and refused with ValueError by `_check_spec` rather than priced without it: the replay engine.
Pure except `simulate`'s calendar step, which reads the signed calendar through owner.calendar_in_force for KRX and
US legs (Q42); no clock, no network.
"""
from __future__ import annotations

import math
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date, timedelta

import numpy as np

from core.odds import costs, models, plan, report

CHUNK = 200_000
DEFAULT_PATHS = {"moonshot": 1_000_000, "compounding": 200_000}
GARCH_SUB = 20_000
REFIT_B = 20
TILT_PILOT = 20_000
TILT_BOUND = 8.0
TILT_ITER = 30
TILT_TOL = 0.002
TILT_FAIL = 0.01
BRACKET_SAMPLE = 50_000
MEMBERS = ("bootstrap", "bootstrap_half", "bootstrap_double", "garch_t", "garch_refit")
# LADDER and COST_DOMINATED_SHARE live in report.py (section 10.1); simulate reads report.LADDER and
# report.COST_DOMINATED_SHARE, because simulate imports report and never the reverse.
_CLOSE_DAYS = {"KR": 0, "US": 1, "CRYPTO": 1}    # a close check's Asia/Seoul date is the session date + this (Q22)


@dataclass(frozen=True, kw_only=True)
class Checks:
    session: np.ndarray           # int, session index of each check
    close: np.ndarray             # bool, True at a close check
    seoul: tuple[date, ...]       # Asia/Seoul date of each check (Q22)
    on: tuple[date, ...]          # the session's own date (cost quotes)


def checks(market: str, sessions: tuple[date, ...], close_only: bool) -> Checks:
    """The check points of a horizon (Q22): each session's open, then its close, or its close only. An open's
    Asia/Seoul date is the session date d; a close's is d on KRX and d + 1 for US and crypto sessions."""
    shift = timedelta(days=_CLOSE_DAYS[market])
    points = [(s, True) for s in range(len(sessions))] if close_only else \
        [(s, close) for s in range(len(sessions)) for close in (False, True)]
    return Checks(session=np.array([s for s, _ in points], dtype=np.int64),
                  close=np.array([close for _, close in points], dtype=bool),
                  seoul=tuple(sessions[s] + shift if close else sessions[s] for s, close in points),
                  on=tuple(sessions[s] for s, _ in points))


@dataclass(frozen=True, kw_only=True)
class PathSpec:
    track: str                    # "moonshot" | "compounding"
    w0: float                     # the stake, KRW
    target: float
    floor: float                  # L
    daily_loss: float
    p0: float                     # the series' last close
    engine: str                   # "bootstrap" | "garch" | "replay"
    m_o: np.ndarray | None        # bootstrap rows: overnight and intraday move sizes
    m_i: np.ndarray | None
    block: float                  # bootstrap mean block
    fits: tuple[models.GarchParams, ...] = ()        # 1 fit, or REFIT_B refits
    replay_move: np.ndarray | None = None            # replay: a = |g| (no-edge, signed by replay_sign) or R1 (tested)
    replay_cost: np.ndarray | None = None            # replay no-edge: c per OOS day (x 2 on stress2x); tested: None
    checks: Checks
    limits: np.ndarray            # per session; nan = no band
    terms: costs.Terms
    mult: float                   # 1.0 base, 2.0 stress
    bracket: plan.Bracket | None
    sizing: str                   # "floor_safe" | "stop_based"
    fraction: plan.Fraction
    fstar: float | None
    cap_krw: float | None         # OKX per-entry cap, else None
    stop_entries_from: date | None                   # Q5
    force_exit_from: date | None
    delist_h: float | None
    theta: float = 0.0
    record_brackets: bool = False


def _check_spec(spec: PathSpec) -> None:
    """ValueError for a spec this engine cannot price faithfully, so no column is ever simulated without a rule it
    needs."""
    if spec.engine not in ("bootstrap", "garch"):
        raise ValueError(f"engine {spec.engine!r} is not simulated")
    close = spec.checks.close
    if not len(close):
        raise ValueError("a column needs at least one check")
    if spec.engine == "bootstrap" and not np.array_equal(close, np.arange(len(close)) % 2 == 1):
        raise ValueError("the bootstrap checks each session's open, then its close")
    if spec.engine == "garch" and not close.all():
        raise ValueError("GARCH-t checks each session's close only")
    limits = np.asarray(spec.limits, dtype=float)
    if limits.shape != (int(spec.checks.session[-1]) + 1,):
        raise ValueError(f"limits must hold one price limit per session (nan for no band), got shape {limits.shape}")
    # costs.band gives a finite upper edge only on a KRX book: such a leg needs its dated limit for every session,
    # and any other leg none, so no session is ever simulated without the band it has (or with one it lacks)
    krx = bool(np.isfinite(costs.band(np.ones(1), 0.5, spec.terms, spec.checks.on[0])[1]).all())
    if spec.engine == "garch" and krx:
        raise ValueError("GARCH-t simulates no daily band: a KRX leg runs on the bootstrap")
    if not (np.isfinite(limits) == krx).all():
        raise ValueError("a KRX leg needs a finite price limit for every session, and any other leg nan")
    if spec.delist_h is not None and not 0.0 < spec.delist_h <= 1.0:
        raise ValueError(f"delist_h must be in (0, 1], got {spec.delist_h}")
    if not spec.daily_loss > 0.0:                         # a nan would switch the stop off: no loss is >= nan
        raise ValueError(f"daily_loss must be > 0 (inf for none), got {spec.daily_loss}")


def _bootstrap_prices(spec: PathSpec, n: int, chunk: int, seed: bytes) -> Iterator[tuple]:
    """Contract 8.3: the row index takes one step of models.indices at each session's open (step 0 at the first);
    the open moves by m_o, the close by m_i of that row, through the fair two-point kernel with one uniform of the
    "sign" stream per check. At each open the session's band [D, U] is costs.band around the previous close (p0 for
    the first session) at that session's limit, and it holds until the close (a nan limit: D = 0, U = inf); a
    session that opens at an edge stays there, because the kernel's chance of leaving it is 0. Yields (p, D, U) for
    each check; the band draws nothing, so the streams are the same with and without it."""
    rows = models.indices(models.stream(seed, chunk, "index"), len(spec.m_o), n, spec.block)
    sign = models.stream(seed, chunk, "sign")
    p, d, u = np.full(n, float(spec.p0)), 0.0, math.inf
    for j, close in enumerate(spec.checks.close):
        if not close:
            idx = next(rows)
            limit = float(spec.limits[spec.checks.session[j]])
            d, u = (0.0, math.inf) if math.isnan(limit) else costs.band(p, limit, spec.terms, spec.checks.on[j])
        p = models.kernel(p, (spec.m_i if close else spec.m_o)[idx], d, u, sign.random(n), spec.theta)
        yield p, d, u


def _garch_prices(p0: float, ret: np.ndarray) -> Iterator[tuple]:
    """GARCH-t: one close check per session, p = p x exp(ret[:, s]), no band (contract 8.3). Yields (p, 0, inf)."""
    p = np.full(ret.shape[0], float(p0))
    for s in range(ret.shape[1]):
        p = p * np.exp(ret[:, s])
        yield p, 0.0, math.inf


def _paths(spec: PathSpec, prices: Iterator[tuple], n: int, record: bool) -> dict[str, np.ndarray]:
    """The state machine of contract 8.4 over n paths, one check per (p, D, U) of `prices` (Q5, Q26, Q27, Q29)."""
    terms, mult, w0, target, floor = spec.terms, spec.mult, float(spec.w0), float(spec.target), float(spec.floor)
    bracket, moonshot, last = spec.bracket, spec.track == "moonshot", len(spec.checks.on) - 1
    take_profit, stop = (None, None) if bracket is None else (bracket.take_profit, bracket.stop)
    phib, phis = mult * terms.phi_buy, mult * terms.phi_sell
    carry, daily, h = costs.LIMIT_DOWN_CARRY_COST_MULTIPLIER, float(spec.daily_loss), spec.delist_h
    exit_from = spec.force_exit_from
    entries_until = min((day for day in (spec.stop_entries_from, exit_from) if day is not None), default=None)
    cash, units, booked, x = np.full(n, w0), np.zeros(n), np.zeros(n), np.zeros(n)
    entry, kb_e, gap, stake = np.zeros(n), np.zeros(n), np.zeros(n), np.zeros(n)
    tp, sl = np.full(n, math.inf), np.zeros(n)             # no exit price until a bracket entry sets them
    d_lock = np.zeros(n)                                  # the D of the session where the lock started
    j_e, entries, wins, losses, carried, edge = (np.zeros(n, dtype=np.int64) for _ in range(6))
    first = np.full(n, -2, dtype=np.int64)               # the check of the first entry fill (after_entry)
    done, entered, fp, x_set = (np.zeros(n, dtype=bool) for _ in range(4))
    locked, lock_stop, day_stop, delisted = (np.zeros(n, dtype=bool) for _ in range(4))
    outcome = np.zeros(n, dtype=np.int8)                  # 0 running, 1 reached, 2 at_floor
    cash_min = cash.copy()
    day_ref = cash.copy()                                 # the value carried into the Asia/Seoul date (W0 at start)
    none = np.zeros(n, dtype=bool)
    br_r: list[np.ndarray] = []
    br_d: list[np.ndarray] = []

    def settle(rows: np.ndarray, p: np.ndarray) -> None:
        """X = cash + units x p + costs - W0 at tau, for the paths in `rows` whose X is not set yet."""
        rows = rows[~x_set[rows]]
        x[rows] = cash[rows] + units[rows] * p[rows] + booked[rows] - w0
        x_set[rows] = True

    def value(p: np.ndarray, ks: np.ndarray) -> np.ndarray:
        """The liquidation value V of every path at price p (Q27): a locked position pays the carried 2x charge."""
        chi = np.where(locked, carry, 1.0) if locked.any() else 1.0
        return cash + units * p * np.maximum(0.0, 1.0 - ks * chi) - phis * chi * (units > 0)

    for j, (p, d_edge, u_edge) in enumerate(prices):
        on, today = spec.checks.on[j], spec.checks.seoul[j]
        if j and today != spec.checks.seoul[j - 1]:       # a new Asia/Seoul date: V at the end of the last check
            day_ref, day_stop = value(p_end, ks_end), np.zeros(n, dtype=bool)
        banded = isinstance(d_edge, np.ndarray)           # a KRX session; elsewhere D = 0 and U = inf
        if banded and not spec.checks.close[j]:
            edge += (p == d_edge) | (p == u_edge)         # the session opened at its band edge (and stays there)
        ks = costs.kappa(terms, p, on, mult, side="sell")
        v = value(p, ks)
        new = ~done & ~fp & (v >= target)                 # first passage, on the liquidation value
        fp |= new
        settle(np.flatnonzero(new), p)
        breach = ~done & (day_ref - v >= daily)           # a breach stops trading for the rest of the date
        day_stop |= breach
        live = ~done & (units > 0)
        queued = live & locked & (p > d_lock) if locked.any() else none     # strictly above the D where it locked
        free = live & ~locked
        gone = free & (j == first + 1) if h is not None else none
        free &= ~gone
        reach = free & (v >= target) if moonshot else none
        win = free & ~reach & (p >= tp)
        loss = free & ~reach & ~win & (p <= sl)
        rest = free & ~reach & ~win & ~loss
        cut = rest & breach
        rule = rest & ~cut if exit_from is not None and today >= exit_from else none
        trigger = reach | win | loss | cut | rule
        stuck = trigger & ~(p > d_edge) if banded else none     # at the session's D: locked and queued, no fill
        if stuck.any():
            locked = locked | stuck
            d_lock = np.where(stuck, d_edge, d_lock)
            lock_stop = np.where(stuck, loss, lock_stop)
            win, loss = win & ~stuck, loss & ~stuck
        out = (trigger & ~stuck) | queued
        filled = out | gone
        if filled.any():
            k = np.flatnonzero(win | loss)
            if record and k.size:
                br_r.append(p[k] / entry[k] * (1.0 - np.minimum(1.0, ks[k])) - (1.0 + kb_e[k]))
                br_d.append(j - j_e[k])
            k = np.flatnonzero((loss | (queued & lock_stop)) & (p < sl))    # stop fills below the stop
            gap[k] = np.maximum(gap[k], (sl[k] - p[k]) / entry[k])
            chi = np.where(queued, carry, 1.0)            # a queued exit pays the flat 2x exit charge
            charge = np.where(out, units * p * np.minimum(1.0, ks * chi) + phis * chi, 0.0)
            if gone.any():                                # the delisting sale at p (1 - h); h x the value is a loss
                g = np.flatnonzero(gone)
                fee = 0.0                                 # h = 1: written off, no sale and no exit charge
                if h < 1.0:
                    q = p[g] * (1.0 - h)
                    fee = units[g] * q * np.minimum(1.0, costs.kappa(terms, q, on, mult, side="sell")) + phis
                charge[g] = units[g] * p[g] * h + fee
            cash = np.where(filled, cash + units * p - charge, cash)
            booked += charge
            units = np.where(filled, 0.0, units)
            locked, lock_stop = locked & ~queued, lock_stop & ~queued
            d_lock = np.where(queued, 0.0, d_lock)
            wins += win
            losses += loss
            carried += queued
            delisted |= gone
            reached = filled & (cash >= target) if moonshot else none
            floored = filled & ~reached & (cash <= floor)
            outcome[reached], outcome[floored] = 1, 2
            done |= reached | floored
            settle(np.flatnonzero(reached | floored), p)
            cash_min = np.minimum(cash_min, cash)
        can = ~done & (units == 0) & ~filled & ~day_stop & ~delisted
        if bracket is None:
            can &= ~entered                                # buy-and-hold enters once
        if entries_until is not None and today >= entries_until:
            can = none                                     # Q5: no entry from a rule date on
        if j < last and can.any():
            k = np.flatnonzero(can)
            buy, at_floor = costs.rule_units(spec.fraction, cash[k], p[k], terms=terms, on=on, mult=mult,
                                             target=target, w0=w0, take_profit=take_profit, stop=stop,
                                             sizing=spec.sizing, floor=floor, fstar=spec.fstar, cap_krw=spec.cap_krw)
            outcome[k[at_floor]] = 2
            done[k[at_floor]] = True
            settle(k[at_floor], p)
            b, u = k[buy > 0], buy[buy > 0]
            if b.size:
                pb = p[b]
                kb = costs.kappa(terms, pb, on, mult, side="buy")
                charge = u * pb * kb + phib
                cash[b] -= u * pb + charge
                booked[b] += charge
                units[b], entry[b], kb_e[b], j_e[b] = u, pb, kb, j
                first[b] = np.where(entered[b], first[b], j)
                stake[b] = np.maximum(stake[b], u * pb)
                entered[b] = True
                entries[b] += 1
                if bracket is not None:
                    tp[b], sl[b] = pb * (1.0 + take_profit), pb * (1.0 - stop)
                cash_min[b] = np.minimum(cash_min[b], cash[b])
        p_end, ks_end = p, ks
    # the horizon: p and ks are the last check's; a live path is RUNNING at its liquidation value, a locked one at
    # the locked price less the carried 2x exit charge (LOCKED_AT_HORIZON)
    held = units > 0
    chi = np.where(locked, carry, 1.0)
    v = value(p, ks)
    settle(np.flatnonzero(~x_set), p)
    unresolved = entries - wins - losses if bracket is not None else np.zeros(n, dtype=np.int64)
    return {"p": p, "v": v, "cost": booked + units * p * np.minimum(1.0, ks * chi) + phis * chi * held, "x": x,
            "outcome": outcome, "fp": fp, "entered": entered, "entries": entries, "wins": wins, "losses": losses,
            "unresolved": unresolved, "gap": gap, "cash_min": cash_min, "locked": locked, "edge": edge,
            "carried": carried, "stake": stake,
            "br_r": np.concatenate(br_r) if br_r else np.zeros(0),
            "br_d": np.concatenate(br_d) if br_d else np.zeros(0, dtype=np.int64)}


def _run_paths(spec: PathSpec, *, n: int, chunk: int, seed: bytes) -> dict[str, np.ndarray]:
    """The state machine of contract 8.4 over n >= 1 paths of chunk `chunk`: the per-path arrays run_column merges,
    plus "p" (terminal price), "entries", "cash_min", "carried" (queued locked exits filled) and "stake" (the
    largest entry notional, KRW), and the bracket sample "br_r", "br_d" (chunk 0, when record_brackets). Draws
    (contract 8.2): the bootstrap's "index" and "sign" streams (the band draws nothing); GARCH-t's "garch" stream for
    each slice of GARCH_SUB paths (one fit; the last slice holds the rest), or the "refit" stream g for group g of
    n // REFIT_B paths (REFIT_B refits)."""
    _check_spec(spec)
    if n < 1:
        raise ValueError(f"n = {n} paths: need at least one")
    record = spec.record_brackets and chunk == 0
    if spec.engine == "bootstrap":
        return _paths(spec, _bootstrap_prices(spec, n, chunk, seed), n, record)
    if len(spec.fits) == 1:
        groups = [(spec.fits[0], min(GARCH_SUB, n - start), models.stream(seed, chunk, "garch", start // GARCH_SUB))
                  for start in range(0, n, GARCH_SUB)]
    elif len(spec.fits) == REFIT_B and n % REFIT_B == 0:
        groups = [(fit, n // REFIT_B, models.stream(seed, chunk, "refit", g)) for g, fit in enumerate(spec.fits)]
    else:
        raise ValueError(f"GARCH-t takes 1 fit, or {REFIT_B} refits over a multiple of {REFIT_B} paths; got "
                         f"{len(spec.fits)} fits and n = {n}")
    horizon = len(spec.checks.on)
    parts = [_paths(spec, _garch_prices(spec.p0, models.simulate_garch(fit, n_paths=size, horizon=horizon,
                                                                       seed=rng)[0]), size, record)
             for fit, size, rng in groups]
    return {key: np.concatenate([part[key] for part in parts]) for key in parts[0]}


_MERGED = ("v", "cost", "x", "outcome", "fp", "entered", "wins", "losses", "unresolved", "gap", "locked", "edge")


def run_column(spec: PathSpec, *, n: int, seed: bytes, key: str, member: str, scenario: str) -> report.ColumnStats:
    """One column of n paths: _run_paths(spec, n=CHUNK, chunk=c, seed=seed) for c in range(n // CHUNK), merged.
    ValueError unless n is a positive multiple of CHUNK (simulate() refuses PARTIAL_CHUNK first)."""
    if n <= 0 or n % CHUNK:
        raise ValueError(f"n = {n} paths is not a positive multiple of CHUNK = {CHUNK}")
    parts, brackets = [], None
    for c in range(n // CHUNK):
        part = _run_paths(spec, n=CHUNK, chunk=c, seed=seed)
        if c == 0 and spec.record_brackets:
            brackets = (part["br_r"][:BRACKET_SAMPLE], part["br_d"][:BRACKET_SAMPLE])
        parts.append({name: part[name] for name in _MERGED})
    a = {name: np.concatenate([part[name] for part in parts]) for name in _MERGED}
    v, cost, outcome = a["v"], a["cost"], a["outcome"]
    kept = v[outcome == 2]
    return report.ColumnStats(
        key=key, member=member, scenario=scenario, n=n,
        reached=int(a["fp"].sum()), reached_outcome=int((outcome == 1).sum()),
        ended_at_or_above=int((v >= spec.target).sum()), at_floor=int((outcome == 2).sum()),
        running=int((outcome == 0).sum()),
        locked_at_horizon=int(a["locked"].sum()),
        rungs=tuple(int((v >= rung * spec.w0).sum()) for rung in report.LADDER) + (int((v >= spec.target).sum()),),
        median=float(np.median(v)), p5=float(np.quantile(v, 0.05)), mean=float(v.mean()),
        mean_se=float(v.std(ddof=1)) / math.sqrt(n), mean_cost=float(cost.mean()),
        g_se=float((v + cost).std(ddof=1)) / math.sqrt(n),
        kept_lo=float(kept.min()) if kept.size else None, kept_hi=float(kept.max()) if kept.size else None,
        x_mean=float(a["x"].mean()), x_var=float(a["x"].var(ddof=1)),
        x_range=math.nan,                                     # no range computed here: HIDDEN_EDGE unavailable
        wins=int(a["wins"].sum()), losses=int(a["losses"].sum()), unresolved=int(a["unresolved"].sum()),
        brackets=brackets,
        band_edge_share=float(a["edge"].sum()) / (n * (int(spec.checks.session[-1]) + 1)),
        band_edge_sessions=int(a["edge"].sum()),                # path-sessions that opened at a band edge
        worst_gap=float(a["gap"].max()), trades=int(a["entered"].sum()))


# --------------------------------------------------------------------------- #
# Part 3 (Task 13): the pipeline of contract 8.5. precheck, every refusal of Q24 in its order, the headline no-edge
# column at base and 2x costs, the rule dates and the OKX cap from the gate, and the report. Task 14 adds the other
# columns and the GARCH-t headline, Task 17 the replay.
# --------------------------------------------------------------------------- #
import dataclasses  # noqa: E402

import numpy as np  # noqa: E402
import scipy  # noqa: E402

from core.compliance import gate, model, owner  # noqa: E402
from core.odds import bold, costs, models, plan, report  # noqa: E402

_VENUE_NAMES = {"kis": "KIS", "upbit": "Upbit", "okx": "OKX"}      # the {venue} slot of why.NOT_TRADABLE


def precheck(plan_obj, ctx, n_paths: int | None = None) -> plan.Refusal | None:
    """Q24 steps 1-4, before any data is loaded (Q45): PARTIAL_CHUNK when n_paths is given and is not a positive
    multiple of CHUNK; then plan.check_plan (the start date included) and plan.check_state (unsigned code, both limits
    and the OKX cap included). Never raises on a malformed plan."""
    if n_paths is not None and (type(n_paths) is not int or n_paths <= 0 or n_paths % CHUNK):
        return plan.Refusal(code="PARTIAL_CHUNK", slots={"chunk": f"{CHUNK:,}"}, detail=f"n_paths {n_paths!r}")
    return plan.check_plan(plan_obj, ctx) or plan.check_state(plan_obj, ctx)


def simulate(plan_obj, ctx, inputs: plan.Inputs, *, n_paths: int | None = None) -> report.OddsReport:
    """The odds of one plan (contract 8.5): the refusals of Q24 in their order, each a refused report with no
    probability, then the columns and the report; n = n_paths, or DEFAULT_PATHS[track] when it is None. The only
    I/O is owner.calendar_in_force for KRX and US legs (Q42). Raises only on a bug."""
    refusal = precheck(plan_obj, ctx, n_paths)
    if refusal is not None:
        return _refused_report(plan_obj, ctx, refusal)
    if isinstance(plan_obj.leg, (list, tuple)):            # check_plan let exactly one Leg through; screen needs it
        plan_obj = dataclasses.replace(plan_obj, leg=plan_obj.leg[0])
    leg = plan_obj.leg
    venue, inst = plan.instrument(plan_obj, ctx)
    market = plan.MARKET[(leg.venue, inst.section)]
    refusal = (plan.check_now(ctx, inputs.now) or _calendar_refusal(market, inputs)
               or plan.check_data(plan_obj, ctx, inputs, market))
    if refusal is not None:
        return _refused_report(plan_obj, ctx, refusal)
    replay = leg.edge_source == plan.REPLAY_SOURCE
    sessions = tuple(date.fromisoformat(d) for d in inputs.sessions)
    try:
        terms = costs.terms(venue, inst, plan_obj.fx_krw_per_usd, replay=replay)
        costs.check_validity(terms, sessions)
    except costs.NotTradable as exc:
        refusal = plan.Refusal(code="NOT_TRADABLE", slots={"venue": _VENUE_NAMES[leg.venue], "symbol": leg.symbol},
                               detail=str(exc))
        return _refused_report(plan_obj, ctx, refusal)
    refusal = plan.check_history(plan_obj, inputs, market)
    if refusal is None and replay:                         # Task 17 replaces this branch with models.verify_replay
        refusal = plan.Refusal(code="CARD_NOT_REPRODUCED", detail="replay not built yet")
    if refusal is None and leg.model == "garch_t" and market == "KR":
        refusal = plan.Refusal(code="MODEL_NOT_FOR_LIMITED_VENUE", detail="GARCH-t has no KRX daily band")
    if refusal is not None:
        return _refused_report(plan_obj, ctx, refusal)
    p0, first_day = float(inputs.series.close[-1]), sessions[0]
    why = costs.cost_refusal(plan_obj, terms, p0, first_day)
    if why is not None:
        return _refused_report(plan_obj, ctx, plan.Refusal(code="COST_DOMINATED", detail=why))
    first = costs.first_stake(plan_obj, terms, ctx, p0, first_day)
    if first <= 0.0:                                       # never screen a zero stake (O11)
        refusal = plan.Refusal(code="STUCK_AT_START", detail=f"first stake {first!r} at {p0!r}")
        return _refused_report(plan_obj, ctx, refusal)
    screening = gate.screen(plan_obj, ctx, float(first))
    if not screening.allowed:
        return _refused_report(plan_obj, ctx, _screen_refusal(screening, ctx))
    n = DEFAULT_PATHS[plan_obj.track] if n_paths is None else n_paths     # Q24 step 14 runs in _accepted_report
    return _accepted_report(plan_obj, ctx, inputs, inst=inst, terms=terms, market=market, sessions=sessions,
                            screening=screening, n=n)


def _calendar_refusal(market: str, inputs) -> plan.Refusal | None:
    """Q24 step 6 (Q6), KRX and US legs only: CALENDAR_COVERAGE on a "coverage: ..." error of the unsigned side;
    else CALENDAR_UNSIGNED unless it reported no error and the calendar signed at inputs.now is exactly the set the
    sessions came from. owner.calendar_in_force is the core's only I/O (Q42)."""
    if market not in ("KR", "US"):
        return None
    error = inputs.calendar_error
    if type(error) is str and error.startswith("coverage:"):
        return plan.Refusal(code="CALENDAR_COVERAGE", detail=error)
    if error != "":
        return plan.Refusal(code="CALENDAR_UNSIGNED", detail=str(error))
    sha = owner.calendar_in_force(inputs.now)
    if type(sha) is not str or sha != inputs.calendar_sha256:
        return plan.Refusal(code="CALENDAR_UNSIGNED",
                            detail=f"signed {sha!r}, sessions from {inputs.calendar_sha256!r}")
    return None


def _screen_refusal(screening, ctx) -> plan.Refusal:
    """SCREEN_BLOCKED with the sub of the gate's first reason: "unsigned" for unsigned code; "row" with the row id
    when the reason names a row of the table ("stale: review by <date> passed (<id>)", "<what>: <id>"); else
    "other"."""
    reasons = screening.decision.reasons
    first, detail = (reasons[0] if reasons else ""), "; ".join(reasons)
    if first == "unsigned code":
        return plan.Refusal(code="SCREEN_BLOCKED", sub="unsigned", detail=detail)
    row = first[first.rfind("(") + 1:-1] if first.endswith(")") else first.rpartition(": ")[2]
    if row in {r.id for r in ctx.active.rules.rows}:
        return plan.Refusal(code="SCREEN_BLOCKED", sub="row", slots={"row": row}, detail=detail)
    return plan.Refusal(code="SCREEN_BLOCKED", sub="other", detail=detail)


def _cap_text(x: float) -> str:
    """A cap as the card prints it: 0.1 -> "10%"."""
    return f"{100.0 * x:g}%"


def _grey_slots(plan_obj, ctx) -> tuple[tuple[str, str, str], ...]:
    """(row id, cap, auto-off date) of each in-force grey row of the leg (gate.grey_rows), for GREY_LEG. The gate
    has already refused a grey row whose cap is unset ("cap unset"), so every cap here is set."""
    rows = {row.id: row for row in ctx.active.rules.rows}
    return tuple((rid, _cap_text(ctx.owner.caps[rows[rid].cap_key]), rows[rid].auto_off.isoformat())
                 for rid in gate.grey_rows(plan_obj, ctx))


def _headline_spec(plan_obj, ctx, inputs, *, terms, market: str, sessions: tuple[date, ...], screening) -> PathSpec:
    """The headline member's PathSpec at base costs: the bootstrap rows and block of the history, open and close
    checks (Q22), the KRX limits per session, W0 = the stake (O11), the OKX per-entry cap, and the rule dates of
    Screening.flags (Q5): entries stop from the earliest flag date, and a forced exit comes at the first check on or
    after the earliest auto_off or effective_until. Every other column is dataclasses.replace of it."""
    leg, limits, flags = plan_obj.leg, ctx.owner.limits, screening.flags
    m_o, m_i, r = models.rows(inputs.series)
    return PathSpec(
        track=plan_obj.track, w0=float(plan_obj.stake_krw), target=float(plan_obj.target_krw),
        floor=float(limits["total_loss_floor_krw"]), daily_loss=float(limits["daily_loss_krw"]),
        p0=float(inputs.series.close[-1]), engine="bootstrap", m_o=m_o, m_i=m_i, block=models.block_length(r),
        checks=checks(market, sessions, False),
        limits=(np.asarray(inputs.price_limits, dtype=float) if market == "KR"
                else np.full(len(sessions), np.nan)),
        terms=terms, mult=costs.SCENARIOS["base"], bracket=leg.bracket, sizing=leg.sizing,
        fraction=plan_obj.fraction, fstar=None,
        cap_krw=(ctx.owner.caps[plan.OKX_CAP_KEY] * float(plan_obj.stake_krw) if leg.venue == "okx" else None),
        stop_entries_from=min((d for d, _, _ in flags), default=None),
        force_exit_from=min((d for d, what, _ in flags if what in ("auto_off", "effective_until")), default=None),
        delist_h=None)


def _no_edge_pair(spec: PathSpec, member: str, *, n: int, seed: bytes) -> tuple[report.ColumnStats, report.ColumnStats]:
    """One member's no-edge column at base and at 2x costs, on the same streams (common random numbers, Q31), each
    with its HIDDEN_EDGE range fixed from the spec (_column, Task 14)."""
    return tuple(_column(dataclasses.replace(spec, mult=mult), n=n, seed=seed, key=f"no_edge/{member}/{name}",
                         member=member, scenario=name) for name, mult in costs.SCENARIOS.items())


def context_provenance(ctx) -> dict:
    """The provenance keys a sealed context gives (its tables, owner head, key fingerprint and code hash), else {}.
    Every report of this module carries them, and so do the cards the CLI refuses itself (Task 18)."""
    if not model.is_sealed(ctx):
        return {}
    active, head = ctx.active, ctx.owner.head
    hashes = dict(getattr(active, "hashes", {}) or {})
    return {"rules_sha": hashes.get("rules", ""), "instruments_sha": hashes.get("instruments", ""),
            "venues_sha": hashes.get("venues", ""), "state_hash": active.state_hash, "owner_seq": head[0],
            "owner_row": head[1], "code_hash": ctx.code_hash, "code_signed": ctx.code_signed,
            "fingerprint": ctx.owner.fingerprint}


def _report_provenance(plan_obj, ctx, inputs, *, screening, seed: bytes, n: int, members: tuple[str, ...]) -> dict:
    """Every provenance key of contract 10.1, stored as data (render prints hashes as 16-hex prefixes)."""
    series, leg, prov = inputs.series, plan_obj.leg, inputs.provenance
    return {**context_provenance(ctx), "decision_id": screening.decision.decision_id,
            "screening_hash": screening.screening_hash, "series_md5": series.md5, "components": series.components,
            "proxy_dates": series.proxy_dates, "calendar_sha": inputs.calendar_sha256,
            "calendar_version": inputs.calendar_version, "calendar_md5s": inputs.calendar_md5s, "model": leg.model,
            "members": members, "seed_hex": seed.hex(), "n": n, "chunk": CHUNK, "numpy": np.__version__,
            "scipy": scipy.__version__, "cryptography": prov.cryptography, "edge_source": leg.edge_source,
            "repo_anchor": prov.repo_anchor, "tree_hash": prov.tree_hash, "comparison_id": inputs.comparison_id,
            "run_counter": inputs.run_counter, "plan_hash": plan.plan_hash(plan_obj)}


def _refused_report(plan_obj, ctx, refusal: plan.Refusal) -> report.OddsReport:
    """A refused report: the refusal and the context's provenance; no column, no flag, no probability."""
    return report.refusal_report(plan_obj, refusal, provenance=context_provenance(ctx))


# --------------------------------------------------------------------------- #
# Part 4 (Task 14): every other column of contract 8.5. The block-length members, the GARCH-t fit and the refit
# member with every pilot check (Q31, R2-8), the delisting pair (Q29), the assumed column and its tilt pilot (Q30),
# the spread (Q31), the structural cap (Q44), HIDDEN_EDGE's range fixed before the run (contract 10.3), the bracket
# reference (Q33) and every flag. Task 17 adds the replay card.
# --------------------------------------------------------------------------- #
_BLOCK_MULT = {"bootstrap": None, "bootstrap_half": 0.5, "bootstrap_double": 2.0}   # None: the block b itself


def _members(headline: str, market: str) -> tuple[str, ...]:
    """The members to run, the headline first (Q31): every MEMBERS entry, read at call time so a test can narrow
    the spread with OF.members(); KRX legs run the block-length members only (no GARCH-t: it has no daily band)."""
    others = tuple(m for m in MEMBERS if m != headline and (market != "KR" or m in _BLOCK_MULT))
    return (headline,) + others


def _garch_member(member: str, fit, horizon: int, seed: bytes) -> tuple[tuple, str]:
    """(fits, "") for a GARCH member that passed every check, else ((), the failed check). garch_t: the fit of the
    history ("fit" when it did not converge; at_bound alone is kept in the fit, not a failure) and both pilot checks on it
    ("deterministic" or "statistical"). garch_refit: REFIT_B synthetic series drawn from that fit (stream
    "refit_series" b), each refitted, and every refit must converge and pass both pilot checks (R2-8); the first
    that does not drops the whole member with check "refit"."""
    if not fit.converged:
        return (), "fit"
    if member == "garch_t":
        ok, check = models.pilot_checks(fit, horizon, seed)
        return ((fit,), "") if ok else ((), check)
    refits = []
    for b in range(REFIT_B):
        synthetic = models.simulate_garch_series(fit.omega, fit.alpha, fit.beta, fit.nu, n=fit.n_obs,
                                                 seed=models.seed_sequence(seed, 0, "refit_series", b))
        refit = models.fit_garch_t(synthetic)
        if not (refit.converged and models.pilot_checks(refit, horizon, seed)[0]):
            return (), "refit"
        refits.append(refit)
    return tuple(refits), ""


def _hidden_range(spec: PathSpec) -> float:
    """HIDDEN_EDGE's range R of a bootstrap no-edge column (contract 10.3), fixed before the run from the plan and
    the history only: m_max the largest open or close move of the history; the lowest price the model can reach,
    p0 x prod(1 - limit) over the horizon's sessions on a KRX leg (every check of a session stays at or above its D)
    and p0 x e^(-n_checks x m_max) otherwise; the cost bound costs.kappa_bound there on both sides; and the
    scenario's charges (mult). report.hidden_range returns inf when the bound makes k_x >= 1 (R2-7)."""
    m_max = float(max(np.max(spec.m_o), np.max(spec.m_i)))
    n_checks = len(spec.checks.on)
    bands = spec.limits[np.isfinite(spec.limits)]
    p_min = (spec.p0 * float(np.prod(1.0 - bands)) if bands.size
             else spec.p0 * math.exp(-n_checks * m_max))
    kappa_bound = costs.kappa_bound(spec.terms, p_min, tuple(sorted(set(spec.checks.on))), spec.mult)
    return report.hidden_range(target=spec.target, phi_buy=spec.mult * spec.terms.phi_buy,
                               phi_sell=spec.mult * spec.terms.phi_sell, kappa_bound=kappa_bound, m_max=m_max,
                               n_checks=n_checks)


def _column(spec: PathSpec, *, n: int, seed: bytes, key: str, member: str, scenario: str) -> report.ColumnStats:
    """run_column with HIDDEN_EDGE's range set: _hidden_range for a bootstrap column, nan for GARCH-t (no finite
    range exists: a bounded shock does not bound the volatility, spec 7.5). Both come from the spec alone, never
    from the paths."""
    x_range = _hidden_range(spec) if spec.engine == "bootstrap" else math.nan
    col = run_column(spec, n=n, seed=seed, key=key, member=member, scenario=scenario)
    return dataclasses.replace(col, x_range=x_range)


def _tilt_theta(spec: PathSpec, p: float, seed: bytes) -> float | None:
    """Q30: theta of the assumed column, by bisection over [-TILT_BOUND, TILT_BOUND] on a TILT_PILOT-path pilot
    through _run_paths (TILT_PILOT need not be a multiple of CHUNK), every theta on the same paths (the pilot's
    seed is drawn from stream "tilt"); at most TILT_ITER steps, stopping when the pilot's win rate is within
    TILT_TOL of p. None (ASSUMED_EDGE_UNREACHABLE) when p lies outside [win(-8), win(8)] or the last win rate
    misses p by more than TILT_FAIL. A win is a take-profit fill among the brackets resolved by take-profit or
    stop (a locked exit is unresolved)."""
    pilot = models.stream(seed, 0, "tilt").bytes(32)

    def win(theta: float) -> float:
        out = _run_paths(dataclasses.replace(spec, theta=theta, record_brackets=False), n=TILT_PILOT, chunk=0,
                         seed=pilot)
        wins, losses = int(np.sum(out["wins"])), int(np.sum(out["losses"]))
        return wins / (wins + losses) if wins + losses else math.nan

    lo, hi = -TILT_BOUND, TILT_BOUND
    if not win(lo) <= p <= win(hi):                        # nan (no resolved bracket) fails too
        return None
    theta, w = 0.0, math.nan
    for _ in range(TILT_ITER):
        theta = 0.5 * (lo + hi)
        w = win(theta)
        if abs(w - p) <= TILT_TOL:
            break
        if w < p:
            lo = theta
        else:
            hi = theta
    return theta if abs(w - p) <= TILT_FAIL else None


def _assumed(col: report.ColumnStats, p: float, theta: float) -> dict | None:
    """The assumed card's figures (Q30): the typed rate w; p0 and the unresolved share u of the headline's full
    no-edge base column; its resolved brackets; the brackets needed to tell w from p0 (bold.brackets_needed, inf
    when equal); theta. None when no bracket resolved or no win was observed (P4: no zero baseline probability)."""
    resolved = col.wins + col.losses
    if resolved == 0 or col.wins == 0:
        return None
    p0 = col.wins / resolved
    return {"w": p, "p0": p0, "u": col.unresolved / (resolved + col.unresolved),
            "nb": bold.brackets_needed(p, p0), "resolved": float(resolved), "theta": theta}


def _spread(columns, headline: report.ColumnStats, track: str, market: str):
    """Q31, Q32: (spread, kind). The spread runs from the lowest two-sided lower bound to the highest upper bound
    of the base no-edge cells of every member but the headline (REACHED outcomes on moonshot cards, first passages
    on compounding cards); kind "none" when no other member ran, "krx" on KRX legs, "other" when another model
    family ran, else "blocks" (the block-length members only)."""
    cells = [c for c in columns if c.key.startswith("no_edge/") and c.scenario == "base" and c.key != headline.key]
    if not cells:
        return None, "none"
    bounds = [report.cp_two_sided(c.reached_outcome if track == "moonshot" else c.reached, c.n) for c in cells]
    spread = (min(lo for lo, _ in bounds), max(hi for _, hi in bounds))
    family = headline.member.split("_")[0]                 # "bootstrap" | "garch"
    if market == "KR":
        return spread, "krx"
    if any(c.member.split("_")[0] != family for c in cells):
        return spread, "other"
    return spread, "blocks"


def _reference(col: report.ColumnStats, spec: PathSpec, *, l_min: float, on: date) -> float | None:
    """Q33: bold.bracket_reference on the bracket sample of the headline no-edge base column, at the buy side's base
    rate at p0; None for a buy-and-hold leg or when no bracket was recorded. An estimate: it only ever raises the
    amber ABOVE_ESTIMATED_REFERENCE."""
    if col.brackets is None or len(col.brackets[0]) == 0:
        return None
    r, d = col.brackets
    terms = spec.terms
    kappa = float(costs.kappa(terms, np.array([spec.p0]), on, 1.0, side="buy")[0])
    return bold.bracket_reference(r, d, w0=spec.w0, l_min=l_min, target=spec.target, n_checks=len(spec.checks.on),
                                  kappa=kappa, phi_buy=terms.phi_buy, phi_sell=terms.phi_sell,
                                  r_exit=costs.r_exit(terms))


def _accepted_report(plan_obj, ctx, inputs, *, inst, terms, market: str, sessions: tuple[date, ...], screening,
                     n: int) -> report.OddsReport:
    """Step 7 (contract 8.5): the market seed (Q34) and l_min per sizing (Q32); the GARCH fits and their pilot
    checks, the headline first (a failed headline is MODEL_CHECK_FAILED, a failed spread member is left out with
    its note); the tilt pilot of an assumed leg (ASSUMED_EDGE_UNREACHABLE); then the columns: each member's no-edge
    pair on one seed, the delisting pair of a share or coin leg and the assumed column, all on the headline member;
    then the spread, the structural cap of a buy-and-hold KRX leg, HIDDEN_EDGE on the headline, the bracket
    reference, the flags and report.build. plan_index and plan_count are 1 here; the CLI numbers the plans."""
    leg, series = plan_obj.leg, inputs.series
    seed = models.market_seed(models.data_hashes(series, inputs.replay), inputs.calendar_sha256,
                              inputs.comparison_id, inputs.run_counter)
    base = _headline_spec(plan_obj, ctx, inputs, terms=terms, market=market, sessions=sessions, screening=screening)
    stake, target = float(plan_obj.stake_krw), float(plan_obj.target_krw)
    l_min = base.floor if leg.sizing == "floor_safe" else 0.0
    ceiling = bold.ceiling(stake, l_min, target)
    headline = leg.model
    specs: dict[str, PathSpec] = {}
    notes: list[tuple[str, str]] = []
    fit = None
    for member in _members(headline, market):
        if member in _BLOCK_MULT:
            mult = _BLOCK_MULT[member]
            block = base.block if mult is None else models.variant_block(base.block, mult, len(base.m_o))
            specs[member] = dataclasses.replace(base, block=block)
            continue
        if fit is None:
            fit = models.fit_garch_t(models.rows(series)[2])
        fits, check = _garch_member(member, fit, len(sessions), seed)
        if check and member == headline:
            refusal = plan.Refusal(code="MODEL_CHECK_FAILED", sub=check, detail=f"{member}: {check} check failed")
            return _refused_report(plan_obj, ctx, refusal)
        if check:
            notes.append((member, check))
            continue
        specs[member] = dataclasses.replace(base, engine="garch", fits=fits, checks=checks(market, sessions, True))
    # only the headline keeps a bracket sample (Q33 reads its base column's); no other member pays for one
    head = specs[headline] = dataclasses.replace(specs[headline], record_brackets=leg.bracket is not None)
    theta = None
    if leg.edge_source == "assumed":
        theta = _tilt_theta(head, leg.assumed_p, seed)
        if theta is None:
            refusal = plan.Refusal(code="ASSUMED_EDGE_UNREACHABLE", slots={"w": _cap_text(leg.assumed_p)},
                                   detail=f"tilt pilot cannot reach {leg.assumed_p!r}")
            return _refused_report(plan_obj, ctx, refusal)
    columns: list[report.ColumnStats] = []
    for member, spec in specs.items():
        columns += _no_edge_pair(spec, member, n=n, seed=seed)
    head_col = columns[0]
    once = dataclasses.replace(head, record_brackets=False)
    if inst.cls in ("share", "coin"):
        for h in costs.DELIST_STRESS:
            columns.append(run_column(dataclasses.replace(once, delist_h=h), n=n, seed=seed,
                                      key=f"delist_{round(100 * h)}", member=headline, scenario="base"))
    assumed = None
    if theta is not None:
        assumed = _assumed(head_col, leg.assumed_p, theta)
        if assumed is None:
            refusal = plan.Refusal(code="ASSUMED_EDGE_UNREACHABLE", slots={"w": _cap_text(leg.assumed_p)},
                                   detail="the no-edge column resolved no bracket or observed no win")
            return _refused_report(plan_obj, ctx, refusal)
        columns.append(run_column(dataclasses.replace(once, theta=theta), n=n, seed=seed, key="assumed",
                                  member=headline, scenario="base"))
    spread, spread_kind = _spread(columns, head_col, plan_obj.track, market)
    structural = None
    if market == "KR" and leg.bracket is None:
        structural = (bold.structural_max(tuple(inputs.price_limits)), len(sessions))
    hidden = report.hidden_edge(head_col, w0=stake, target=target, l_min=l_min)
    reference = _reference(head_col, head, l_min=l_min, on=sessions[0])
    model_slots = {"symbol": leg.symbol, "first": series.dates[0], "last": series.dates[-1],
                   "rows": f"{len(series.dates):,}"}
    if head.cap_krw is not None:
        model_slots.update(cap=_cap_text(ctx.owner.caps[plan.OKX_CAP_KEY]), capkrw=report.fmt_krw(head.cap_krw))
    no_edge = tuple(c for c in columns if c.key.startswith("no_edge/"))
    flags = report.flags_for(headline=head_col, no_edge=no_edge, engine=head.engine, hidden=hidden, ceiling=ceiling,
                             structural=structural, target=target, stake=stake, reference=reference,
                             rule_flags=screening.flags, grey=_grey_slots(plan_obj, ctx), series=series,
                             okx=leg.venue == "okx")
    return report.build(
        plan_hash=plan.plan_hash(plan_obj), plan_index=1, plan_count=1, refused=None, track=plan_obj.track,
        stake=stake, target=target, floor=base.floor, l_min=l_min, horizon_days=plan_obj.horizon_days, n=n,
        sizing=leg.sizing, model_key="model.garch" if head.engine == "garch" else "model.bootstrap",
        model_slots=model_slots, columns=tuple(columns), headline=head_col.key, spread=spread,
        spread_kind=spread_kind, notes=tuple(notes), ceiling=ceiling,
        structural_cap=None if structural is None else structural[0],
        structural_sessions=None if structural is None else structural[1], tax_basis=inst.tax_basis,
        cost_words_key="cost.tax" if terms.book == "KRX_stock_book" else "cost.fees", hidden=hidden, flags=flags,
        assumed=assumed, replay=None, comparison=(inputs.comparison_plans, inputs.comparison_typed, inputs.plan_runs),
        provenance=_report_provenance(plan_obj, ctx, inputs, screening=screening, seed=seed, n=n,
                                      members=tuple(specs)))
