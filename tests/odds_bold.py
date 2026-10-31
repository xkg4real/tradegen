"""References (odds plan Task 11; spec 3, 7.4, 8.o items 3 and 4; Q32, Q33, Q44): the ceiling and its "1 in N", the
KRX structural maximum on the fixture calendar, the brackets needed, exact bold play, simulated bold play (an
even-money game and the engine) against it, and the estimated bracket reference."""
from __future__ import annotations

import bisect
import contextlib
import fractions
import hashlib
import math
import random
import time
from datetime import date, timedelta

import numpy as np
from scipy import stats

from core.odds import bold, costs, models, plan, simulate
from tests import odds_fixtures as OF

Fr = fractions.Fraction
ON = date(2026, 10, 23)                    # F.ctx's date: the first session of every engine fixture here
LEVEL = 0.999                              # every simulated match uses the 99.9% Clopper-Pearson interval
SEED = hashlib.sha256(b"tradegen-odds/tests/odds_bold").digest()
W0, L, T = 42_000.0, 21_000.0, 336_000.0   # the engine fixture: stake, floor at half the stake, target 8x
ZERO = {"kappa": 0.0, "phi_buy": 0.0, "phi_sell": 0.0, "r_exit": 0.0}


def _raises(call, exc) -> str:
    try:
        call()
    except exc as e:
        return str(e)
    raise AssertionError(f"expected {exc.__name__}")


def _cp(k: int, n: int) -> tuple[float, float]:
    """The two-sided exact (Clopper-Pearson) interval of k in n at LEVEL."""
    ci = stats.binomtest(k, n).proportion_ci(confidence_level=LEVEL, method="exact")
    return ci.low, ci.high


def _terms(lot: float) -> costs.Terms:
    """Upbit BTC in KRW with no minimum and no fixed charge; _no_rate zeroes its 10 bp table rate."""
    return costs.Terms(venue="upbit", symbol="BTC", book="crypto_venue", quote="KRW", lot=lot, min_quote=0.0,
                       min_krw=0.0, phi_buy=0.0, phi_sell=0.0, ladder=None, ladder_from=None, quote_krw=1.0)


@contextlib.contextmanager
def _no_rate(terms: costs.Terms):
    """costs.TABLE_BP["crypto_venue"] = 0.0 with save/restore, checked on both sides (a copied table fails here)."""
    saved = costs.TABLE_BP["crypto_venue"]
    costs.TABLE_BP["crypto_venue"] = 0.0
    try:
        for side in ("buy", "sell"):
            assert costs.kappa(terms, np.array([1.0, 5e7]), ON, 1.0, side=side).tolist() == [0.0, 0.0], side
        yield
    finally:
        costs.TABLE_BP["crypto_venue"] = saved


# --------------------------------------------------------------------------- #
# The ceiling, the structural maximum and the brackets needed
# --------------------------------------------------------------------------- #
def test_ceiling_and_its_one_in_n():
    """Spec 3: KRW 42,000 -> 42,000,000 is 1 in 1,000 with no protected floor and 1 in 1,999 with the floor at half the
    stake. Both are exact, and the N of "1 in N" is never rounded up."""
    assert bold.ceiling(42_000.0, 0.0, 42_000_000.0) == 0.001
    assert bold.ceiling(42_000.0, 21_000.0, 42_000_000.0) == 1 / 1999
    assert bold.ceiling(W0, L, T) == 1 / 15
    assert bold.ceiling(42_000.0, 21_000.0, 52_500.0) == 2 / 3
    one_in = (bold.ceiling_one_in(42_000.0, 0.0, 42_000_000.0), bold.ceiling_one_in(42_000.0, 21_000.0, 42_000_000.0))
    assert one_in == (1000, 1999) and all(type(v) is int for v in one_in)
    assert bold.ceiling_one_in(W0, L, T) == 15
    # math.floor of the float quotient gives 2,126 here, which would print a smaller chance than the bound
    assert math.floor((89_276_487.5 - 7.3) / (42_000.0 - 7.3)) == 2126
    assert bold.ceiling_one_in(42_000.0, 7.3, 89_276_487.5) == 2125
    for bad in ((42_000.0, 42_000.0, 84_000.0), (42_000.0, 50_000.0, 84_000.0), (84_000.0, 0.0, 84_000.0),
                (math.nan, 0.0, 1.0), (1.0, 0.0, math.inf), (1.0, False, 2.0)):
        for fn in (bold.ceiling, bold.ceiling_one_in):
            assert "l_min < w0 < target" in _raises(lambda: fn(*bad), ValueError), (fn, bad)


def test_structural_max_values():
    """Spec 3 and Q44: (1.3/0.7) x 1.3^(n-1) is 95.06 at 16 sessions and 458.83 at 22; 1,000x needs 25 sessions. Each
    session uses its own dated limit, the first in the open-to-close ratio."""
    assert f"{bold.structural_max((0.30,) * 16):.2f}" == "95.06"
    assert f"{bold.structural_max((0.30,) * 22):.2f}" == "458.83"
    assert bold.structural_max((0.30,) * 24) < 1_000.0 < bold.structural_max((0.30,) * 25)
    assert f"{bold.structural_max((0.30,) * 25):.2f}" == "1008.06"
    assert bold.structural_max((0.30,)) == 1.3 / 0.7
    assert math.isclose(bold.structural_max((0.15, 0.30, 0.30)), 1.15 / 0.85 * 1.3 * 1.3, rel_tol=1e-12)
    for bad in ((), (0.0,), (1.0,), (0.30, math.nan), (0.30, -0.1), (True,)):
        assert "one price limit in (0, 1)" in _raises(lambda: bold.structural_max(bad), ValueError), bad


def test_structural_max_stays_below_1000x_on_the_fixture_calendar():
    """Spec 8.o item 4: on the fixture calendar every half-open 30-day window starting 2026-01-01 to 2027-12-02 holds
    16 to 22 KRX sessions, each at its dated 30% limit, so a buy-and-hold KRX leg cannot reach 1,000x in 30 days
    (IMPOSSIBLE at that target; the card itself is Task 14's). A 40-day window holds at least 25 sessions and can.
    fixture_set() writes its signed set once per process into a cached temp dir under the system temp (prefix
    quantgen_cal_), never under ~/.tradegen or the repo, as the macro calendar tests do."""
    from core.calendars import clocks, regime
    from tests.macro_m1_calendars import fixture_set
    cal = fixture_set()
    days = clocks.sessions_between("KR", date(2026, 1, 1), date(2027, 12, 31), cal=cal)
    limit = {d: regime.regime_tags("KR", d, cal=cal)["price_limit"] for d in days}
    assert set(limit.values()) == {0.30}

    def window(start: date, horizon_days: int) -> list[date]:
        return days[bisect.bisect_left(days, start):bisect.bisect_left(days, start + timedelta(days=horizon_days))]

    counts, start = [], date(2026, 1, 1)
    while start <= date(2027, 12, 2):
        held = window(start, 30)
        assert bold.structural_max(tuple(limit[d] for d in held)) < 1_000.0, (start, len(held))
        counts.append(len(held))
        start += timedelta(days=1)
    assert (len(counts), min(counts), max(counts)) == (701, 16, 22), (len(counts), min(counts), max(counts))
    assert window(date(2026, 2, 7), 30) == clocks.sessions_between("KR", date(2026, 2, 7), date(2026, 3, 8), cal=cal)
    longer = window(date(2026, 10, 26), 40)
    assert len(longer) >= 25 and bold.structural_max(tuple(limit[d] for d in longer)) > 1_000.0, len(longer)


def test_brackets_needed():
    """Spec 7.2: 617 resolved brackets tell 55% from 50% and 153 tell 60%; both directions agree; equal rates never
    can be told apart."""
    assert bold.brackets_needed(0.55, 0.50) == 617
    assert bold.brackets_needed(0.60, 0.50) == 153
    assert bold.brackets_needed(0.45, 0.50) == 617
    assert bold.brackets_needed(0.501, 0.50) == 1_546_291
    assert bold.brackets_needed(0.50, 0.50) == math.inf
    for bad in ((1.2, 0.5), (0.5, -0.1), (math.nan, 0.5), (0.5, True)):
        assert "win rates in [0, 1]" in _raises(lambda: bold.brackets_needed(*bad), ValueError), bad


# --------------------------------------------------------------------------- #
# Bold play: exact, then simulated
# --------------------------------------------------------------------------- #
def test_bold_even_exact_values():
    """Spec 3: P(1,000x) under bold play at even money is 0.1000%, 0.0816%, 0.0346% and 0.0106% at p = 0.50, 0.49,
    0.45 and 0.40, and 0.0400% at 0.49 with the floor at half the stake (x = 21,000 / 41,979,000 = 1/1999)."""
    got = [f"{100 * float(bold.bold_even(Fr(1, 1000), Fr(p, 100))):.4f}" for p in (50, 49, 45, 40)]
    assert got == ["0.1000", "0.0816", "0.0346", "0.0106"], got
    assert f"{100 * float(bold.bold_even(Fr(1, 1999), Fr(49, 100))):.4f}" == "0.0400"
    p = Fr(45, 100)
    assert bold.bold_even(Fr(1, 8), p) == p ** 3                       # 1/8 -> 1/4 -> 1/2: three wins in a row
    assert bold.bold_even(Fr(1, 3), p) == p * p / (1 - p * (1 - p))     # 1/3 -> 2/3 -> 1/3: a cycle, solved exactly
    assert (bold.bold_even(Fr(0), p), bold.bold_even(Fr(1), p), bold.bold_even(Fr(1, 2), p)) == (0, 1, p)
    assert bold.bold_even(Fr(3, 4), Fr(0)) == 0 and bold.bold_even(Fr(1, 3), Fr(1)) == 1
    assert "fractions.Fraction" in _raises(lambda: bold.bold_even(0.125, p), TypeError)
    assert "fractions.Fraction" in _raises(lambda: bold.bold_even(Fr(1, 8), 0.45), TypeError)
    for bad in ((Fr(3, 2), p), (Fr(-1, 8), p), (Fr(1, 8), Fr(11, 10))):
        assert "0 <= x <= 1" in _raises(lambda: bold.bold_even(*bad), ValueError), bad


def test_bold_even_is_x_at_a_fair_coin():
    """At p = 1/2 bold play is a fair game, so f(x) = x exactly: dyadic x (finite orbits) and others (cycles)."""
    rng = random.Random(20261023)
    xs = [Fr(rng.randrange(0, 2 ** k + 1), 2 ** k) for k in (rng.randrange(1, 48) for _ in range(40))]
    xs += [Fr(rng.randrange(1, b), b) for b in (2 * rng.randrange(1, 500) + 1 for _ in range(40))]
    xs += [Fr(1, 1999), Fr(7, 12), Fr(1000, 1001)]
    for x in xs:
        assert bold.bold_even(x, Fr(1, 2)) == x, x


def _bernoulli_bold(w0: float, target: float, p_win: float, n: int, seed: int) -> int:
    """n even-money games (a win pays the stake, a loss takes it) staked by costs.rule_units' bold rule at a price of
    KRW 1, lot 1, no costs and the floor at 0; returns how many reached the target. Every number stays a whole KRW."""
    terms, price = _terms(1.0), np.ones(n)
    cash, live = np.full(n, w0), np.ones(n, dtype=bool)
    rng = np.random.default_rng(seed)
    with _no_rate(terms):
        for _ in range(200):
            units, at_floor = costs.rule_units(plan.bold(), cash, price, terms=terms, on=ON, mult=1.0, target=target,
                                               w0=w0, take_profit=1.0, stop=0.5, sizing="floor_safe", floor=0.0,
                                               fstar=None, cap_krw=None)     # the stop is unused under this sizing
            live &= ~at_floor & (units > 0) & (cash < target)
            if not live.any():
                break
            stake = np.where(live, units * price, 0.0)
            cash = cash + np.where(rng.random(n) < p_win, stake, -stake)
    assert not live.any(), "a game outlived 200 rounds"
    return int((cash >= target).sum())


def test_simulated_bold_play_matches_bold_even():
    """Spec 8.o item 3: 20,000 even-money games under the engine's own bold stake reach the target as often as
    bold_even says, inside the 99.9% Clopper-Pearson interval: x = 1/8 (KRW 1,000 -> 8,000: three wins in a row) and
    x = 1/3 (KRW 1,000 -> 3,000: a cycle), both at p = 0.45."""
    p = Fr(45, 100)
    for w0, target, x, seed in ((1_000.0, 8_000.0, Fr(1, 8), 1), (1_000.0, 3_000.0, Fr(1, 3), 2)):
        k = _bernoulli_bold(w0, target, float(p), 20_000, seed)
        lo, hi = _cp(k, 20_000)
        exact = float(bold.bold_even(x, p))
        assert lo <= exact <= hi, (x, k, lo, exact, hi)


def test_engine_bold_play_meets_the_ceiling_and_lands_on_the_target():
    """Spec 8.o items 3 and 4 in the engine (contract 16.1): run_column over 366 days and 20,000 paths on rows that
    never move at the open and move 0.5 in log at every close (even_rows nudges the upper price so that a bracket of
    +(e^0.5 - 1) / -(1 - e^-0.5) entered at an open fills at that day's close: a fair bet); bold stakes,
    floor-protected sizing with the floor L = KRW 21,000, moonshot, W0 = KRW 42,000 on Upbit BTC, no costs and no
    minimum (lot 1e-12 BTC, KRW 0), daily loss limit KRW 1e9.

    P(T = 8 W0) is the fair-game chance (W0 - L)/(T - L) = 1/15, inside the 99.9% Clopper-Pearson interval. (With the
    KRW 5,000 Upbit minimum P(T) sits near 5.17%, below the ceiling, because a floor-protected loss never lands
    exactly on L.) No path ends below L and every winner ends at or above T, so the mean's excess over
    (k T + (n - k) L) / n is the summed distance of the losers above L and of the winners above T, over n. Its bound
    of KRW 0.01 (KRW 200 over all paths) shows that every path that missed T ends within KRW 200 of L (with no
    minimum it keeps a sliver above L and counts as RUNNING, not AT_FLOOR; the split is not pinned), and that a win
    lands on T, not past it: the k winners lie on average under KRW 200 / k (about 0.15) past T, so some path ends
    within KRW 1 of T. An engine that failed to re-enter after a win would leave thousands of paths at 1.1 W0 or
    more, short of T."""
    series = OF.even_rows(0.5)
    m_o, m_i, _ = models.rows(series)
    assert float(np.max(m_o)) == 0.0 and np.allclose(m_i, 0.5, rtol=0.0, atol=1e-12)
    terms, days = _terms(1e-12), 366
    sessions = tuple(ON + timedelta(days=i) for i in range(days))
    spec = simulate.PathSpec(
        track="moonshot", w0=W0, target=T, floor=L, daily_loss=1e9, p0=series.close[-1], engine="bootstrap",
        m_o=m_o, m_i=m_i, block=1.0,                 # every row is the same move, so the block length changes nothing
        checks=simulate.checks("CRYPTO", sessions, close_only=False), limits=np.full(days, np.nan), terms=terms,
        mult=1.0, bracket=plan.Bracket(take_profit=math.exp(0.5) - 1.0, stop=1.0 - math.exp(-0.5)),
        sizing="floor_safe", fraction=plan.bold(), fstar=None, cap_krw=None, stop_entries_from=None,
        force_exit_from=None, delist_h=None)
    with OF.chunk(20_000), _no_rate(terms):          # one chunk of all 20,000 paths: one pass over the checks
        col = simulate.run_column(spec, n=20_000, seed=SEED, key="no_edge/bootstrap/base", member="bootstrap",
                                  scenario="base")
    k = col.reached
    assert col.n == 20_000 and k == col.reached_outcome == col.ended_at_or_above, col
    assert col.rungs == (k, k, k, 0, k), col.rungs  # every path at or above 1.1 W0 is on T; 10 W0 lies past T
    lo, hi = _cp(k, col.n)
    assert lo <= bold.ceiling(W0, L, T) <= hi, (k, lo, hi)
    assert L <= col.p5 <= col.median <= L + 1.0, (col.p5, col.median)
    excess = col.mean - (k * T + (col.n - k) * L) / col.n
    assert col.mean_cost == 0.0 and -1e-6 <= excess <= 0.01, (col.mean_cost, excess)     # KRW 9.8e-05 measured
    assert col.at_floor + col.running + col.reached_outcome == col.n  # accounting invariant; split is not pinned


# --------------------------------------------------------------------------- #
# The bracket reference (an estimate; amber only)
# --------------------------------------------------------------------------- #
def _fair_law(n: int = 50_000, seed: int = 7) -> tuple[np.ndarray, np.ndarray]:
    """A martingale bracket law: +0.6 on 40% of brackets and -0.4 on 60% (mean 0 to float rounding), each lasting 1 to
    6 checks."""
    r = np.where(np.arange(n) < 2 * n // 5, 0.6, -0.4)
    rng = np.random.default_rng(seed)
    rng.shuffle(r)
    return r, rng.integers(1, 7, n).astype(float)


def test_bracket_reference_is_0_out_of_reach_and_1_at_the_target():
    """Q33: a law that only loses, or a horizon too short for the target, gives exactly 0; a start at the target
    gives exactly 1, with or without checks left."""
    r, d = _fair_law()
    ones = np.ones_like(d)
    assert bold.bracket_reference(-np.abs(r), ones, w0=W0, l_min=L, target=T, n_checks=60, **ZERO) == 0.0
    small = np.where(np.arange(1_000) % 2 == 0, 0.05, -0.05)        # at most 100 x 1.05^2 in two checks
    assert bold.bracket_reference(small, np.ones(1_000), w0=100.0, l_min=0.0, target=10_000.0, n_checks=2,
                                  **ZERO) == 0.0
    assert bold.bracket_reference(r, d, w0=W0, l_min=L, target=T, n_checks=0, **ZERO) == 0.0
    assert bold.bracket_reference(r, ones, w0=T, l_min=L, target=T, n_checks=60, **ZERO) == 1.0
    assert bold.bracket_reference(r, d, w0=T, l_min=L, target=T, n_checks=0, **ZERO) == 1.0


def test_bracket_reference_never_beats_the_ceiling_without_an_edge():
    """Q33: on a martingale bracket law with no costs the reference stays at or below (W0 - L)/(T - L) (linear
    interpolation cannot lift values above a linear bound, and a stake never takes wealth below l_min) and approaches
    it with time for many brackets; longer brackets fit fewer in the horizon, costs lower it (together, and each
    charge of contract 9.1 on its own), and only an edge lifts it above the ceiling."""
    r, d = _fair_law()
    ones = np.ones_like(d)
    c = bold.ceiling(W0, L, T)
    long_brackets = bold.bracket_reference(r, d, w0=W0, l_min=L, target=T, n_checks=60, **ZERO)
    short_brackets = bold.bracket_reference(r, ones, w0=W0, l_min=L, target=T, n_checks=60, **ZERO)
    many = bold.bracket_reference(r, ones, w0=W0, l_min=L, target=T, n_checks=120, **ZERO)
    assert 0.0 < long_brackets < 0.5 * short_brackets, (long_brackets, short_brackets)    # 0.027 against 0.064
    assert short_brackets < many <= c and many >= 0.99 * c, (short_brackets, many, c)    # 0.0637, 0.0665, 1/15
    costly = bold.bracket_reference(r - 0.002, ones, w0=W0, l_min=L, target=T, n_checks=60, kappa=0.001,
                                    phi_buy=5.0, phi_sell=5.0, r_exit=20.0)
    assert 0.0 < costly < 0.97 * short_brackets, (costly, short_brackets)                # 0.0603
    alone = {name: bold.bracket_reference(r, ones, w0=W0, l_min=L, target=T, n_checks=60, **{**ZERO, name: value})
             for name, value in (("phi_buy", 300.0), ("phi_sell", 300.0), ("kappa", 1.0), ("r_exit", 10_000.0))}
    assert max(alone.values()) < 0.9 * short_brackets, (alone, short_brackets)   # 0.0481, 0.0488, 0.0289, 0.0342
    assert alone["phi_buy"] < alone["phi_sell"], alone      # phi_buy also comes off the room the stake is cut from
    assert bold.bracket_reference(r + 0.1, ones, w0=W0, l_min=L, target=T, n_checks=60, **ZERO) > 2 * c   # 0.48


def test_bracket_reference_takes_under_3_seconds_for_60_checks():
    """Q33: one 30-day open-and-close horizon (60 checks) on a full bracket sample with four durations."""
    r, d = _fair_law(n=simulate.BRACKET_SAMPLE)
    started = time.perf_counter()
    value = bold.bracket_reference(r, d, w0=W0, l_min=L, target=T, n_checks=60, kappa=0.0005, phi_buy=0.0,
                                   phi_sell=0.0, r_exit=0.0)
    assert time.perf_counter() - started < 3.0 and 0.0 < value < bold.ceiling(W0, L, T)


def test_bracket_reference_refuses_bad_input():
    """Fail closed on arrays of different shapes, empty or non-finite, durations below 1 check, a non-whole or
    negative check count, and a target at the floor, a negative rate or charge, or a non-finite number."""
    r, d = _fair_law(n=100)
    good = {"w0": W0, "l_min": L, "target": 63_000.0, "n_checks": 6, **ZERO}
    assert 0.0 < bold.bracket_reference(r, d, **good) <= 1.0  # P47: reachable positive control
    for rr, dd in ((r, d[:-1]), (r[:0], d[:0]), (np.where(r > 0, np.nan, r), d), (r, d - 1.0),
                   (r.reshape(10, 10), d.reshape(10, 10))):
        assert "equal-length" in _raises(lambda: bold.bracket_reference(rr, dd, **good), ValueError)
    for change in ({"n_checks": -1}, {"n_checks": 6.0}, {"n_checks": True}):
        assert "whole number of checks" in _raises(lambda: bold.bracket_reference(r, d, **{**good, **change}),
                                                   ValueError), change
    for change in ({"target": L}, {"kappa": -0.1}, {"phi_sell": math.inf}, {"w0": math.nan}, {"r_exit": -1.0}):
        assert "l_min < target" in _raises(lambda: bold.bracket_reference(r, d, **{**good, **change}),
                                           ValueError), change
