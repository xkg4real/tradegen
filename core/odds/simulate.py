"""The odds path engine (spec 7.1 "Rounding and re-entry", 7.2 "Brackets", 7.3; odds plan Q22, Q26, Q27, Q28;
contract section 8).

`run_column` simulates one column (a member's model under one cost scenario) in chunks of CHUNK paths and folds the
per-path results into a `report.ColumnStats`. `_run_paths` runs the state machine of contract 8.4 over any number of
paths: at each check it moves the price, values every path at its liquidation value, records first passage, fills
at most one exit (target, take-profit, stop, in that order) and, from the next check on and never at the last one,
one entry sized by `costs.rule_units`. Every fill books its charges, so the gross value cash + units x price + costs
moves only with the price: with no edge it is a martingale, and X = G_tau - W0 is the HIDDEN_EDGE sample.

Not simulated yet, and refused with ValueError by `_check_spec` rather than priced without the rule: KRX price
bands and limit-down locks, the daily loss stop, rule dates, the delisting columns and the replay engine.
Pure: no clock, no file, no network.
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
    if np.isfinite(np.asarray(spec.limits, dtype=float)).any():
        raise ValueError("KRX price bands and limit-down locks are not simulated yet")
    if not math.isinf(spec.daily_loss):
        raise ValueError("the daily loss stop is not simulated yet")
    if spec.stop_entries_from is not None or spec.force_exit_from is not None:
        raise ValueError("rule dates are not simulated yet")
    if spec.delist_h is not None:
        raise ValueError("delisting columns are not simulated yet")


def _bootstrap_prices(spec: PathSpec, n: int, chunk: int, seed: bytes) -> Iterator[np.ndarray]:
    """Contract 8.3: the row index takes one step of models.indices at each session's open (step 0 at the first);
    the open moves by m_o, the close by m_i of that row, through the fair two-point kernel with one uniform of the
    "sign" stream per check. No band (D = 0, U = inf)."""
    rows = models.indices(models.stream(seed, chunk, "index"), len(spec.m_o), n, spec.block)
    sign = models.stream(seed, chunk, "sign")
    p = np.full(n, float(spec.p0))
    for close in spec.checks.close:
        if not close:
            idx = next(rows)
        p = models.kernel(p, (spec.m_i if close else spec.m_o)[idx], 0.0, math.inf, sign.random(n), spec.theta)
        yield p


def _garch_prices(p0: float, ret: np.ndarray) -> Iterator[np.ndarray]:
    """GARCH-t: one close check per session, p = p x exp(ret[:, s]) (contract 8.3)."""
    p = np.full(ret.shape[0], float(p0))
    for s in range(ret.shape[1]):
        p = p * np.exp(ret[:, s])
        yield p


def _paths(spec: PathSpec, prices: Iterator[np.ndarray], n: int, record: bool) -> dict[str, np.ndarray]:
    """The state machine of contract 8.4 over n paths, one check per price array of `prices` (Q26, Q27)."""
    terms, mult, w0, target, floor = spec.terms, spec.mult, float(spec.w0), float(spec.target), float(spec.floor)
    bracket, moonshot, last = spec.bracket, spec.track == "moonshot", len(spec.checks.on) - 1
    take_profit, stop = (None, None) if bracket is None else (bracket.take_profit, bracket.stop)
    phib, phis = mult * terms.phi_buy, mult * terms.phi_sell
    cash, units, booked, x = np.full(n, w0), np.zeros(n), np.zeros(n), np.zeros(n)
    entry, kb_e, gap = np.zeros(n), np.zeros(n), np.zeros(n)
    tp, sl = np.full(n, math.inf), np.zeros(n)             # no exit price until a bracket entry sets them
    j_e, entries, wins, losses = (np.zeros(n, dtype=np.int64) for _ in range(4))
    done, entered, fp, x_set = (np.zeros(n, dtype=bool) for _ in range(4))
    outcome = np.zeros(n, dtype=np.int8)                  # 0 running, 1 reached, 2 at_floor
    cash_min = cash.copy()
    br_r: list[np.ndarray] = []
    br_d: list[np.ndarray] = []

    def settle(rows: np.ndarray, p: np.ndarray) -> None:
        """X = cash + units x p + costs - W0 at tau, for the paths in `rows` whose X is not set yet."""
        rows = rows[~x_set[rows]]
        x[rows] = cash[rows] + units[rows] * p[rows] + booked[rows] - w0
        x_set[rows] = True

    for j, p in enumerate(prices):
        on = spec.checks.on[j]
        ks = costs.kappa(terms, p, on, mult, side="sell")
        v = cash + units * p * np.maximum(0.0, 1.0 - ks) - phis * (units > 0)
        new = ~done & ~fp & (v >= target)                 # first passage, on the liquidation value
        fp |= new
        settle(np.flatnonzero(new), p)
        live = ~done & (units > 0)
        reach = live & (v >= target) if moonshot else np.zeros(n, dtype=bool)
        win = live & ~reach & (p >= tp)
        loss = live & ~reach & ~win & (p <= sl)
        filled = reach | win | loss
        if filled.any():
            k = np.flatnonzero(win | loss)
            if record and k.size:
                br_r.append(p[k] / entry[k] * (1.0 - np.minimum(1.0, ks[k])) - (1.0 + kb_e[k]))
                br_d.append(j - j_e[k])
            k = np.flatnonzero(loss & (p < sl))
            gap[k] = np.maximum(gap[k], (sl[k] - p[k]) / entry[k])
            charge = np.where(filled, units * p * np.minimum(1.0, ks) + phis, 0.0)
            cash = np.where(filled, cash + units * p - charge, cash)
            booked += charge
            units = np.where(filled, 0.0, units)
            wins += win
            losses += loss
            reached = filled & (cash >= target) if moonshot else np.zeros(n, dtype=bool)
            floored = filled & ~reached & (cash <= floor)
            outcome[reached], outcome[floored] = 1, 2
            done |= reached | floored
            settle(np.flatnonzero(reached | floored), p)
            cash_min = np.minimum(cash_min, cash)
        can = ~done & (units == 0) & ~filled
        if bracket is None:
            can &= ~entered                                # buy-and-hold enters once
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
                entered[b] = True
                entries[b] += 1
                if bracket is not None:
                    tp[b], sl[b] = pb * (1.0 + take_profit), pb * (1.0 - stop)
                cash_min[b] = np.minimum(cash_min[b], cash[b])
    # the horizon: p and ks are the last check's; a live path is RUNNING at its liquidation value
    held = units > 0
    v = cash + units * p * np.maximum(0.0, 1.0 - ks) - phis * held
    settle(np.flatnonzero(~x_set), p)
    unresolved = entries - wins - losses if bracket is not None else np.zeros(n, dtype=np.int64)
    return {"p": p, "v": v, "cost": booked + units * p * np.minimum(1.0, ks) + phis * held, "x": x,
            "outcome": outcome, "fp": fp, "entered": entered, "entries": entries, "wins": wins, "losses": losses,
            "unresolved": unresolved, "gap": gap, "cash_min": cash_min,
            "br_r": np.concatenate(br_r) if br_r else np.zeros(0),
            "br_d": np.concatenate(br_d) if br_d else np.zeros(0, dtype=np.int64)}


def _run_paths(spec: PathSpec, *, n: int, chunk: int, seed: bytes) -> dict[str, np.ndarray]:
    """The state machine of contract 8.4 over n >= 1 paths of chunk `chunk`: the per-path arrays run_column merges,
    plus "p" (terminal price), "entries" and "cash_min", and the bracket sample "br_r", "br_d" (chunk 0, when
    record_brackets). Draws (contract 8.2): the bootstrap's "index" and "sign" streams; GARCH-t's "garch" stream for
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


_MERGED = ("v", "cost", "x", "outcome", "fp", "entered", "wins", "losses", "unresolved", "gap")


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
        locked_at_horizon=0,                                  # no lock without a band (_check_spec)
        rungs=tuple(int((v >= rung * spec.w0).sum()) for rung in report.LADDER) + (int((v >= spec.target).sum()),),
        median=float(np.median(v)), p5=float(np.quantile(v, 0.05)), mean=float(v.mean()),
        mean_se=float(v.std(ddof=1)) / math.sqrt(n), mean_cost=float(cost.mean()),
        g_se=float((v + cost).std(ddof=1)) / math.sqrt(n),
        kept_lo=float(kept.min()) if kept.size else None, kept_hi=float(kept.max()) if kept.size else None,
        x_mean=float(a["x"].mean()), x_var=float(a["x"].var(ddof=1)),
        x_range=math.nan,                                     # no range computed here: HIDDEN_EDGE unavailable
        wins=int(a["wins"].sum()), losses=int(a["losses"].sum()), unresolved=int(a["unresolved"].sum()),
        brackets=brackets,
        band_edge_share=0.0, band_edge_sessions=0,            # no band (_check_spec)
        worst_gap=float(a["gap"].max()), trades=int(a["entered"].sum()))
