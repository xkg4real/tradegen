"""The path engine, part 1 (odds plan Task 9; spec 7.1 "Rounding and re-entry", 7.2 "Brackets", 7.3; contract
8.1-8.4): the moves, entries, take-profit, stop and target exits, the cost ledger, the outcomes and first passage.
Every simulation runs under OF.chunk() (CHUNK 2,000) on a 30-day crypto horizon from 2026-10-23, with Upbit-like
terms built here (10 bp a side, KRW 5,000 minimum, lot 1e-8) and the gross value X = G_tau - W0 of contract 8.4."""
from __future__ import annotations

import dataclasses
import hashlib
import math
from datetime import date, timedelta

import numpy as np

from core.odds import costs, models, plan, report, simulate
from tests import odds_fixtures as OF

_SEED = hashlib.sha256(b"tests/odds_simulate").digest()
_W0, _T, _L = 42_000.0, 42_000_000.0, 21_000.0
_FIT = models.GarchParams(dist="t", omega=2e-6, alpha=0.08, beta=0.90, nu=6.0, mean_daily=0.0, n_obs=1500,
                          cond_vol_last=0.015 * math.sqrt(252), converged=True, at_bound=())
_SERIES = OF.series(n=600, seed=3, vol=0.02, open_gap=0.01)
_M_O, _M_I, _R = models.rows(_SERIES)


def _days(k: int = 30) -> tuple[date, ...]:
    return tuple(date(2026, 10, 23) + timedelta(days=i) for i in range(k))


def _terms(**changes) -> costs.Terms:
    """Upbit BTC terms: crypto_venue (10 bp a side, no tick floor), KRW quote, lot 1e-8, minimum KRW 5,000, no fixed
    charge; any field can be changed."""
    fields = dict(venue="upbit", symbol="BTC", book="crypto_venue", quote="KRW", lot=1e-8, min_quote=5000.0,
                  min_krw=5000.0, phi_buy=0.0, phi_sell=0.0, ladder=None, ladder_from=None, quote_krw=1.0)
    fields.update(changes)
    return costs.Terms(**fields)


def _spec(**changes) -> simulate.PathSpec:
    """A compounding floor-protected buy-and-hold of KRW 42,000 (floor 21,000, target 42,000,000) on the bootstrap
    rows of a 600-bar fixture series, base costs, 30 crypto sessions checked at the open and the close."""
    days = changes.pop("days", _days())
    fields = dict(track="compounding", w0=_W0, target=_T, floor=_L, daily_loss=math.inf, p0=_SERIES.close[-1],
                  engine="bootstrap", m_o=_M_O, m_i=_M_I, block=models.block_length(_R),
                  checks=simulate.checks("CRYPTO", days, False), limits=np.full(len(days), np.nan), terms=_terms(),
                  mult=1.0, bracket=None, sizing="floor_safe", fraction=plan.fixed(1.0), fstar=None, cap_krw=None,
                  stop_entries_from=None, force_exit_from=None, delist_h=None)
    fields.update(changes)
    return simulate.PathSpec(**fields)


def _garch(**changes) -> simulate.PathSpec:
    """_spec on the GARCH-t engine: one fixture fit, the close of each session only."""
    days = changes.pop("days", _days())
    fields = dict(engine="garch", m_o=None, m_i=None, block=1.0, fits=(_FIT,),
                  checks=simulate.checks("CRYPTO", days, True))
    fields.update(changes)
    return _spec(days=days, **fields)


def _gap(m: float, rows: int = 50) -> dict:
    """Bootstrap rows whose open and close both move by exactly m: every check moves the price by e^m or e^-m."""
    return dict(m_o=np.full(rows, m), m_i=np.full(rows, m), block=1.0)


def _even(m: float) -> plan.Bracket:
    """A bracket a hair inside e^m - 1 and 1 - e^-m, so a move of e^m or e^-m always fills it."""
    return plan.Bracket(take_profit=math.exp(m) - 1.0 - 1e-9, stop=1.0 - math.exp(-m) - 1e-9)


def _col(spec: simulate.PathSpec, n: int | None = None, seed: bytes = _SEED, scenario: str = "base"):
    return simulate.run_column(spec, n=simulate.CHUNK if n is None else n, seed=seed, key=f"no_edge/x/{scenario}",
                               member="bootstrap", scenario=scenario)


def _raises(call, text: str) -> str:
    try:
        call()
    except ValueError as exc:
        assert text in str(exc), f"{text!r} not in {str(exc)!r}"
        return str(exc)
    raise AssertionError(f"no ValueError (wanted {text!r})")


def test_constants_and_the_chunk_swap() -> None:
    assert simulate.CHUNK == 200_000 and simulate.DEFAULT_PATHS == {"moonshot": 1_000_000, "compounding": 200_000}
    assert (simulate.GARCH_SUB, simulate.REFIT_B, simulate.BRACKET_SAMPLE) == (20_000, 20, 50_000)
    assert (simulate.TILT_PILOT, simulate.TILT_BOUND, simulate.TILT_ITER, simulate.TILT_TOL, simulate.TILT_FAIL) == \
        (20_000, 8.0, 30, 0.002, 0.01)
    assert simulate.MEMBERS == ("bootstrap", "bootstrap_half", "bootstrap_double", "garch_t", "garch_refit")
    assert report.LADDER == (1.10, 1.25, 2.0, 10.0) and report.COST_DOMINATED_SHARE == 0.10
    with OF.chunk():
        assert (simulate.CHUNK, simulate.GARCH_SUB) == (2_000, 2_000)
        assert simulate.DEFAULT_PATHS == {"moonshot": 2_000, "compounding": 2_000}
    assert (simulate.CHUNK, simulate.GARCH_SUB, simulate.DEFAULT_PATHS["moonshot"]) == (200_000, 20_000, 1_000_000)


def test_checks_follow_the_sessions_and_their_seoul_dates() -> None:
    days = (date(2026, 10, 23), date(2026, 10, 26))
    nxt = timedelta(days=1)
    for market, shift in (("KR", timedelta(0)), ("US", nxt), ("CRYPTO", nxt)):
        both = simulate.checks(market, days, False)
        assert both.session.tolist() == [0, 0, 1, 1] and both.close.tolist() == [False, True, False, True]
        assert both.on == (days[0], days[0], days[1], days[1])
        assert both.seoul == (days[0], days[0] + shift, days[1], days[1] + shift)
        close = simulate.checks(market, days, True)
        assert close.session.tolist() == [0, 1] and close.close.tolist() == [True, True]
        assert close.on == days and close.seoul == (days[0] + shift, days[1] + shift)
    assert len(simulate.checks("CRYPTO", _days(), False).on) == 60
    assert len(simulate.checks("US", _days(), True).on) == 30


def test_moves_follow_the_rows_and_the_streams() -> None:
    """Contract 8.3: the row index steps once per session, at its open; the open moves by m_o and the close by m_i
    of that row (no band: e^m up or e^-m down, fair); one sign uniform per check; GARCH-t multiplies by exp(ret)."""
    m_o = np.linspace(0.001, 0.05, 40)
    with OF.chunk():
        for theta in (0.0, 0.7):                            # theta: the assumed-edge tilt of the kernel (Q30)
            spec = _spec(m_o=m_o, m_i=2.0 * m_o + 0.001, block=3.0, days=_days(10), theta=theta)
            got = [p for p, _, _ in simulate._bootstrap_prices(spec, 500, 0, _SEED)]   # (p, D, U) since Task 10
            rows = models.indices(models.stream(_SEED, 0, "index"), 40, 500, 3.0)
            sign = models.stream(_SEED, 0, "sign")
            p = np.full(500, spec.p0)
            for j, close in enumerate(spec.checks.close):
                if not close:
                    idx = next(rows)
                m = spec.m_i[idx] if close else spec.m_o[idx]
                want = models.kernel(p, m, 0.0, math.inf, sign.random(500), theta)
                assert np.array_equal(got[j], want), (theta, j)
                assert np.allclose(np.abs(np.log(got[j] / p)), m, rtol=0.0, atol=1e-12), (theta, j)
                p = want
            assert len(got) == 20
            assert np.array_equal(simulate._run_paths(spec, n=500, chunk=0, seed=_SEED)["p"], p)
        assert p.mean() > 1.05 * spec.p0                    # the tilt at 0.7 drifts the price up
        g = _garch(days=_days(10))
        ret = models.simulate_garch(_FIT, n_paths=500, horizon=10, seed=models.stream(_SEED, 0, "garch", 0))[0]
        p = np.full(500, g.p0)
        for s in range(10):
            p = p * np.exp(ret[:, s])
        assert np.array_equal(simulate._run_paths(g, n=500, chunk=0, seed=_SEED)["p"], p)


def test_no_edge_mean_payoff_is_zero_before_costs() -> None:
    """Spec 8.o1: a stop, a bracket and buy-and-hold have mean gross payoff 0 (X within 4 SE) under the two-point
    bootstrap and under GARCH-t, while the bracket's net value is below the stake by more than 4 SE (the costs)."""
    plans = {"buy_and_hold": None, "stop": plan.Bracket(take_profit=1000.0, stop=0.03),
             "bracket": plan.Bracket(take_profit=0.02, stop=0.02)}
    with OF.chunk():
        for engine in (_spec, _garch):
            for name, bracket in plans.items():
                col = _col(engine(bracket=bracket), n=2 * simulate.CHUNK)
                se = math.sqrt(col.x_var / col.n)
                assert abs(col.x_mean) <= 4.0 * se, (engine.__name__, name, col.x_mean, se)
                assert col.trades == col.n and col.mean_cost > 0.0, (engine.__name__, name)
                if name == "bracket":
                    assert col.mean - _W0 < -4.0 * col.mean_se, (engine.__name__, col.mean, col.mean_se)
                    assert col.wins > 0 and col.losses > 0


def test_at_floor_keeps_between_l_and_l_plus_x() -> None:
    """Spec 7.3: under floor-protected sizing an AT_FLOOR path keeps between L and L + X, X at most the minimum
    stake with its entry charge plus phi_buy plus R_exit (lot rounding included); none ends below L. Spec 7.1 draws
    the line to "no bet": a rule stake below the minimum while the minimum is affordable buys nothing and the path
    stays flat and RUNNING. A path floored at an entry is done: it never enters later, even once the price has
    risen enough for the minimum to become affordable."""
    terms = _terms(phi_buy=100.0, phi_sell=50.0)
    spec = _spec(terms=terms, bracket=_even(0.25), p0=1_000.0, **_gap(0.25))
    p_hi = 1_000.0 * math.exp(0.25 * len(spec.checks.on))
    kb = costs.TABLE_BP["crypto_venue"] * 1e-4
    x_cap = (terms.min_krw + terms.lot * p_hi) * (1.0 + kb) + terms.phi_buy + costs.r_exit(terms)
    # a KRW 1,000 tick at about KRW 100 makes the buy rate about 500%: KRW 21,000 above the floor affords at most
    # 21,000 / 5.5 < 5,000 at the first check (price 90 or 111), and from KRW 157 up the minimum would be affordable
    low = _spec(p0=100.0, terms=_terms(ladder=((0.0, 1_000.0),), ladder_from=date(2026, 1, 1)), **_gap(0.1))
    with OF.chunk():
        col = _col(spec)
        out = simulate._run_paths(spec, n=simulate.CHUNK, chunk=0, seed=_SEED)
        flat = _col(_spec(fraction=plan.fixed(0.1)))           # KRW 4,200, below the KRW 5,000 minimum
        floored = simulate._run_paths(low, n=simulate.CHUNK, chunk=0, seed=_SEED)
    assert col.at_floor > col.n // 2, col.at_floor
    assert _L <= col.kept_lo and col.kept_hi <= _L + x_cap, (col.kept_lo, col.kept_hi, _L + x_cap)
    assert out["v"].min() >= _L and out["cash_min"].min() >= _L
    assert flat.trades == 0 and flat.at_floor == 0 and flat.running == flat.n and flat.mean == _W0
    assert (floored["outcome"] == 2).all() and not floored["entered"].any() and (floored["v"] == _W0).all()
    assert (floored["p"] > 200.0).any()     # above 157 one check before the last: a path not done would have entered


def test_reentry_waits_for_the_next_check_and_never_the_last() -> None:
    """Spec 7.1: after an exit fills, the next entry happens at the next check, and no entry at the last check.
    Contract 8.4: a take-profit fills at p >= tp and a stop at p <= sl, so a move exactly onto either fills it."""
    with OF.chunk():
        # every move fills the bracket: entries at checks 0, 2, ..., 58 and exits at 1, 3, ..., 59 (a re-entry at
        # the exit's own check would make 59 entries)
        spec = _spec(terms=_terms(min_quote=1.0, min_krw=1.0), floor=0.0, bracket=_even(0.2), **_gap(0.2))
        out = simulate._run_paths(spec, n=300, chunk=0, seed=_SEED)
        assert (out["entries"] == 30).all() and (out["wins"] + out["losses"] == 30).all()
        assert (out["unresolved"] == 0).all()
        # the same on prices that exactly double or halve (e^ln2 is 2.0 in floating point) with no costs: a
        # take-profit of 100% and a stop of 50% equal the next price, and fill
        exact = _spec(terms=_terms(min_quote=1.0, min_krw=1.0), floor=0.0, mult=0.0, p0=1_000.0, days=_days(5),
                      bracket=plan.Bracket(take_profit=1.0, stop=0.5), **_gap(math.log(2.0)))
        out = simulate._run_paths(exact, n=300, chunk=0, seed=_SEED)
        assert (out["entries"] == 5).all() and (out["wins"] + out["losses"] == 5).all()
        assert out["wins"].sum() > 0 and out["losses"].sum() > 0
        tiny = plan.Bracket(take_profit=1e-9, stop=1e-9)        # the first close after an entry exits
        for k, entries in ((1, 0), (2, 1), (3, 1), (4, 2)):
            out = simulate._run_paths(_garch(days=_days(k), bracket=tiny), n=300, chunk=0, seed=_SEED)
            assert (out["entries"] == entries).all(), (k, entries)
        out = simulate._run_paths(_garch(days=_days(1)), n=300, chunk=0, seed=_SEED)
        assert not out["entered"].any() and (out["v"] == _W0).all() and (out["outcome"] == 0).all()


def test_buy_and_hold_holds_its_position_to_the_horizon() -> None:
    """Q26: a buy-and-hold leg below its target enters once and holds to the horizon: no bracket entry, so nothing
    is unresolved, and its terminal value pays the in-rate exit charge and phi_sell, which the terminal cost holds,
    so V + C - W0 = X. Its lowest cash is the cash after the entry: the floor plus R_exit (KRW 200), to within one
    lot (1e-8 BTC, about KRW 1.1 at the fixture's price). A moonshot buy-and-hold ends REACHED at the target or
    RUNNING. Its re-entry clause (a buy-and-hold leg never enters twice) cannot be reached in part 1: without a
    bracket the only exit is the moonshot target, and that fill always ends REACHED. Its test is handed to Task 10,
    after a daily-loss exit."""
    terms = _terms(phi_buy=100.0, phi_sell=50.0)
    with OF.chunk():
        out = simulate._run_paths(_spec(terms=terms), n=simulate.CHUNK, chunk=0, seed=_SEED)
        assert (out["entries"] == 1).all() and out["entered"].all() and (out["unresolved"] == 0).all()
        assert np.allclose(out["x"], out["v"] + out["cost"] - _W0, rtol=0.0, atol=1e-6)
        low = _L + costs.r_exit(terms)
        assert costs.r_exit(terms) == 200.0 and (out["cash_min"] >= low).all() and (out["cash_min"] < low + 2.0).all()
        moon = _spec(track="moonshot", target=46_000.0, terms=_terms(min_quote=1.0, min_krw=1.0),
                     **_gap(0.1))
        out = simulate._run_paths(moon, n=simulate.CHUNK, chunk=0, seed=_SEED)
        assert (out["entries"] == 1).all() and (out["outcome"] == 1).any() and (out["outcome"] == 0).any()


def test_reached_counts_the_liquidation_value_after_exit_costs() -> None:
    """Spec 7.3: REACHED and first passage use the liquidation value after the in-rate exit charge: a path whose
    gross mark is at the target while its liquidation value is just below it is not reached."""
    m = 0.1
    rows = models.rows(OF.even_rows(m))
    terms = _terms()
    p0 = 50_000_000.0
    units = float(costs.floor_units((_W0 - _L) / (1.0 + 1e-3), p0, terms.lot))     # the floor-protected stake
    cash = _W0 - units * p0 * (1.0 + 1e-3)
    p1 = p0 * math.exp(m)
    mark, value = cash + units * p1, cash + units * p1 * (1.0 - 1e-3)
    assert mark - value > 20.0
    with OF.chunk():
        def run(target, sessions):
            spec = _spec(track="moonshot", target=target, p0=p0, m_o=rows[0], m_i=rows[1], block=1.0,
                         days=_days(sessions))
            return _col(spec), simulate._run_paths(spec, n=simulate.CHUNK, chunk=0, seed=_SEED)["p"]
        miss, _ = run((mark + value) / 2.0, 1)
        hit, p = run(value - 1.0, 1)
        again, p2 = run((mark + value) / 2.0, 2)
    assert miss.reached == miss.reached_outcome == miss.ended_at_or_above == 0
    up = int((p > p0).sum())                                 # one session: the close moved up
    assert 0 < hit.reached == hit.reached_outcome == hit.ended_at_or_above == up < hit.n
    assert hit.running == hit.n - hit.reached
    # two sessions: a path one move up still holds (its gross mark above T is no exit) and is reached only by a
    # second move up
    twice = int((p2 > p0 * math.exp(1.5 * m)).sum())
    assert 0 < again.reached == again.reached_outcome == twice

    # P38: 21 whole units at 1,000, cash 21,000; a close at 2,000 is exactly T.
    exact = _spec(track="moonshot", target=63_000.0, p0=1_000.0, mult=0.0, days=_days(1),
                  terms=_terms(lot=1.0, min_quote=1.0, min_krw=1.0),
                  m_o=np.zeros(1), m_i=np.full(1, math.log(2.0)), block=1.0)
    with OF.chunk():
        col = _col(exact)
        out = simulate._run_paths(exact, n=simulate.CHUNK, chunk=0, seed=_SEED)
    at_target = out["p"] == 2_000.0
    assert 0 < at_target.sum() < col.n and (out["v"][at_target] == 63_000.0).all()
    assert np.array_equal(out["fp"], at_target) and np.array_equal(out["outcome"] == 1, at_target)
    assert col.reached == col.reached_outcome == col.ended_at_or_above == col.rungs[-1] == int(at_target.sum())


def test_moonshot_stops_at_reached_and_compounding_counts_first_passage() -> None:
    """Contract 8.4 steps 3-4 and Q32: a moonshot path ends REACHED at the target exit, while a compounding path on
    the same prices goes on (with a bracket too: a take-profit that lifts its cash above T ends nothing) and keeps
    X = G_tau - W0 of its first passage, the moonshot's own X, not the horizon's. The target names the exit (Q26),
    so a target fill is never also a take-profit win: each moonshot bracket entry ends as one win, loss or REACHED."""
    with OF.chunk():
        base = dict(target=46_000.0, terms=_terms(min_quote=1.0, min_krw=1.0), **_gap(0.1))
        moon = _col(_spec(track="moonshot", **base))
        comp = _col(_spec(track="compounding", **base))
        mo = simulate._run_paths(_spec(track="moonshot", **base), n=simulate.CHUNK, chunk=0, seed=_SEED)
        co = simulate._run_paths(_spec(track="compounding", **base), n=simulate.CHUNK, chunk=0, seed=_SEED)
        comp_br = _col(_spec(track="compounding", bracket=_even(0.1), **base))
        mb = simulate._run_paths(_spec(track="moonshot", bracket=_even(0.1), **base), n=simulate.CHUNK, chunk=0,
                                 seed=_SEED)
    assert 0 < moon.reached == moon.reached_outcome == moon.ended_at_or_above < moon.n
    assert moon.running == moon.n - moon.reached and moon.at_floor == 0
    assert comp.reached == moon.reached and comp.reached_outcome == 0       # the same paths, up to first passage
    assert comp.ended_at_or_above < comp.reached and comp.running == comp.n
    fp = co["fp"]
    assert fp.any() and np.array_equal(co["x"][fp], mo["x"][fp])            # X froze at first passage
    assert not np.allclose(co["x"][fp], (co["v"] + co["cost"] - _W0)[fp])   # and is not the horizon's G - W0
    assert comp_br.reached > 0 and comp_br.reached_outcome == 0
    assert (mb["outcome"] == 1).any()
    assert np.array_equal(mb["wins"] + mb["losses"] + (mb["outcome"] == 1), mb["entries"])


def test_the_stress_scenario_doubles_each_charge_and_cash_and_floor_hold() -> None:
    """Q27: the stress scenario doubles the proportional rate (mult enters costs.kappa once) and both fixed charges:
    one round trip of the same units in both scenarios costs exactly twice as much. Spec 7.1 and 8.o5: under 2x
    costs the always rule keeps cash >= 0 and floor-protected sizing keeps every path at or above L, on prices that
    jump by a factor of 20 at every check, far through any stop; a stop fill that leaves the value at or below L is
    AT_FLOOR at once (spec 7.3), with its overshoot (stop - fill) / entry recorded."""
    trip = _spec(terms=_terms(min_quote=1.0, min_krw=1.0, phi_buy=100.0, phi_sell=50.0), fraction=plan.fixed(0.1),
                 bracket=_even(0.1), days=_days(1), **_gap(0.1))       # KRW 4,200 in at the open, out at the close
    terms = _terms(phi_buy=300.0, phi_sell=500.0)
    adverse = dict(terms=terms, mult=costs.COST_STRESS, p0=1_000.0, **_gap(3.0))
    with OF.chunk():
        base = simulate._run_paths(trip, n=simulate.CHUNK, chunk=0, seed=_SEED)
        stress = simulate._run_paths(dataclasses.replace(trip, mult=costs.COST_STRESS), n=simulate.CHUNK, chunk=0,
                                     seed=_SEED)
        assert (base["entries"] == 1).all() and (base["wins"] + base["losses"] == 1).all()
        assert (stress["entries"] == 1).all() and (stress["wins"] + stress["losses"] == 1).all()
        assert np.allclose(stress["cost"], costs.COST_STRESS * base["cost"], rtol=1e-12, atol=0.0)
        for floor in (0.0, _L):
            stop = _spec(floor=floor, sizing="stop_based", bracket=plan.Bracket(take_profit=0.5, stop=0.05),
                         **adverse)
            out = simulate._run_paths(stop, n=simulate.CHUNK, chunk=0, seed=_SEED)
            assert out["cash_min"].min() >= 0.0 and out["v"].min() >= 0.0, floor
            assert out["gap"].max() > 0.9                       # fills far below the stop
        assert out["v"].min() < _L                              # stop-based: a gap overshoots the floor
        # one session: in at the open, out at the close; a close at e^-3 times the entry fills 0.95 - e^-3 of the
        # entry price below the stop and leaves the value below L, so that path is AT_FLOOR at its fill
        one = simulate._run_paths(_spec(floor=_L, sizing="stop_based", bracket=plan.Bracket(take_profit=0.5, stop=0.05),
                                        days=_days(1), **adverse), n=simulate.CHUNK, chunk=0, seed=_SEED)
        for bracket in (None, plan.Bracket(take_profit=0.5, stop=0.05)):
            safe = _spec(bracket=bracket, **adverse)
            out = simulate._run_paths(safe, n=simulate.CHUNK, chunk=0, seed=_SEED)
            assert out["cash_min"].min() >= _L and out["v"].min() >= _L, bracket
        # a tick of KRW 1,000 makes the sell rate exceed 100% at low prices: the proportional exit charge, and the
        # liquidation value of a position still open at the horizon, are clipped at the position's value (Q27), so
        # cash and value still never go below 0
        ticky = dict(adverse, p0=20_000.0, terms=_terms(phi_buy=300.0, phi_sell=500.0, ladder=((0.0, 1_000.0),),
                                                        ladder_from=date(2026, 1, 1)))
        spec = _spec(floor=0.0, bracket=plan.Bracket(take_profit=0.5, stop=0.05), **ticky)
        out = simulate._run_paths(spec, n=simulate.CHUNK, chunk=0, seed=_SEED)
        held = simulate._run_paths(_spec(floor=0.0, **ticky), n=simulate.CHUNK, chunk=0, seed=_SEED)
    under = one["v"] <= _L
    assert under.any() and np.array_equal(one["outcome"] == 2, under)
    assert np.allclose(one["gap"][under], 0.95 - math.exp(-3.0), rtol=1e-12, atol=0.0)
    assert out["losses"].sum() > 1_000                          # stops filled at sell rates far above 100%
    assert out["cash_min"].min() >= 0.0 and out["v"].min() >= 0.0
    assert held["entered"].all() and held["v"].min() >= 0.0


def test_run_column_folds_the_chunks_into_column_stats() -> None:
    """Every ColumnStats field from the per-path arrays of the two chunks; g_se is the SE of V_term + cost_term,
    not of V_term, and differs from it where the cost varies with the value (paths that stop at the floor stop
    paying KRW 800 a round trip). A bracket still open at the horizon is unresolved. At equality: on prices that
    exactly double or halve with no costs, a stop fill leaving cash exactly at L is AT_FLOOR (cash <= L) and a value
    of exactly 2 x W0 counts in that rung (>=)."""
    spec = _spec(terms=_terms(phi_buy=400.0, phi_sell=400.0), bracket=_even(0.25), p0=1_000.0, **_gap(0.25))
    # one session, lot 1: 21 units at 2,000 or 84 at 500 (stop-based at a 50% stop risks exactly W0 - L), sold at the
    # close for twice (KRW 84,000 = 2 x W0) or half the entry price (KRW 21,000 = L)
    exact = _spec(terms=_terms(lot=1.0, min_quote=1.0, min_krw=1.0), mult=0.0, p0=1_000.0, sizing="stop_based",
                  bracket=plan.Bracket(take_profit=1.0, stop=0.5), days=_days(1), **_gap(math.log(2.0)))
    with OF.chunk():
        col = _col(spec, n=2 * simulate.CHUNK)
        parts = [simulate._run_paths(spec, n=simulate.CHUNK, chunk=c, seed=_SEED) for c in (0, 1)]
        wide = _col(_spec(bracket=plan.Bracket(take_profit=0.5, stop=0.5), days=_days(5), **_gap(0.01)))
        eq = _col(exact)
    a = {k: np.concatenate([part[k] for part in parts]) for k in parts[0]}
    v, cost, n = a["v"], a["cost"], col.n
    assert n == 4_000 and (col.key, col.member, col.scenario) == ("no_edge/x/base", "bootstrap", "base")
    assert col.reached == int(a["fp"].sum()) and col.reached_outcome == 0
    assert col.at_floor == int((a["outcome"] == 2).sum()) and col.running == n - col.at_floor
    assert col.locked_at_horizon == 0 and col.band_edge_sessions == 0 and col.band_edge_share == 0.0
    assert col.ended_at_or_above == int((v >= _T).sum())
    assert col.rungs == tuple(int((v >= k * _W0).sum()) for k in report.LADDER) + (col.ended_at_or_above,)
    assert col.median == float(np.median(v)) and col.p5 == float(np.quantile(v, 0.05))
    assert math.isclose(col.mean, float(v.mean()), rel_tol=1e-12)
    assert math.isclose(col.mean_cost, float(cost.mean()), rel_tol=1e-12)
    assert math.isclose(col.mean_se, float(v.std(ddof=1)) / math.sqrt(n), rel_tol=1e-12)
    assert math.isclose(col.g_se, float((v + cost).std(ddof=1)) / math.sqrt(n), rel_tol=1e-12)
    assert col.g_se > 1.1 * col.mean_se, (col.g_se, col.mean_se)
    kept = v[a["outcome"] == 2]
    assert (col.kept_lo, col.kept_hi) == (float(kept.min()), float(kept.max()))
    assert math.isclose(col.x_mean, float(a["x"].mean()), rel_tol=1e-12, abs_tol=1e-9)
    assert math.isclose(col.x_var, float(a["x"].var(ddof=1)), rel_tol=1e-12)
    assert math.isnan(col.x_range)
    assert (col.wins, col.losses) == (int(a["wins"].sum()), int(a["losses"].sum()))
    assert col.unresolved == int((a["entries"] - a["wins"] - a["losses"]).sum())
    assert col.trades == int(a["entered"].sum()) == n and col.worst_gap == float(a["gap"].max())
    assert np.allclose(a["x"], v + cost - _W0, rtol=0.0, atol=1e-6)    # X = G_tau - W0, fills leave G unchanged
    assert wide.unresolved == wide.trades == wide.n and wide.wins == wide.losses == 0
    assert 0 < eq.at_floor < eq.n and eq.kept_lo == eq.kept_hi == _L and eq.wins == eq.n - eq.at_floor
    assert eq.rungs[:3] == (eq.wins,) * 3 and eq.rungs[3] == eq.ended_at_or_above == 0 and eq.mean_cost == 0.0


def test_run_column_needs_whole_chunks_and_run_paths_takes_any_n() -> None:
    with OF.chunk():
        for n in (2_100, 1_000, 0, -2_000):
            _raises(lambda: _col(_spec(), n=n), "is not a positive multiple of CHUNK = 2000")
        for spec in (_spec(), _garch()):
            out = simulate._run_paths(spec, n=2_100, chunk=0, seed=_SEED)
            assert all(len(out[k]) == 2_100 for k in ("p", "v", "cost", "x", "outcome", "fp", "entries"))
        # GARCH draws in slices of GARCH_SUB paths: the first slice of 2,100 paths is the 2,000-path run
        g = _garch()
        p = simulate._run_paths(g, n=2_100, chunk=0, seed=_SEED)["p"]
        assert np.array_equal(p[:2_000], simulate._run_paths(g, n=2_000, chunk=0, seed=_SEED)["p"])
        ret = models.simulate_garch(_FIT, n_paths=100, horizon=30, seed=models.stream(_SEED, 0, "garch", 1))[0]
        tail = np.full(100, g.p0)
        for s in range(30):
            tail = tail * np.exp(ret[:, s])
        assert np.array_equal(p[2_000:], tail)                 # slice 1: the last 100 paths, stream key 1
        _raises(lambda: simulate._run_paths(_spec(), n=0, chunk=0, seed=_SEED), "need at least one")
    _raises(lambda: _col(_spec(), n=2_000), "is not a positive multiple of CHUNK = 200000")


def test_common_random_numbers_across_columns_and_scenarios() -> None:
    """Spec 7.3: one seed gives the same price paths to every column and cost scenario; another seed or another
    chunk gives other paths."""
    def prices(spec, seed=_SEED, chunk=0):
        return simulate._run_paths(spec, n=1_000, chunk=chunk, seed=seed)["p"]
    with OF.chunk():
        for make in (_spec, _garch):
            ref = prices(make())
            for changes in ({"mult": costs.COST_STRESS}, {"bracket": _even(0.02)}, {"track": "moonshot"},
                            {"bracket": plan.Bracket(take_profit=0.05, stop=0.05), "sizing": "stop_based"},
                            {"fraction": plan.fixed(0.5), "terms": _terms(phi_buy=50.0, phi_sell=50.0)}):
                assert np.array_equal(prices(make(**changes)), ref), (make.__name__, changes)
            assert not np.array_equal(prices(make(), seed=hashlib.sha256(b"other").digest()), ref)
            assert not np.array_equal(prices(make(), chunk=1), ref)


def test_column_stats_compare_without_their_brackets() -> None:
    """brackets stays out of ==, repr and the hash, so two columns compare without touching their arrays. The
    generated == (Python 3.13) is True for the same object and otherwise compares field by field, so a column whose
    x_range is nan never equals another column object, even an identical one. Two columns are therefore compared
    through dataclasses.replace(col, brackets=None, x_range=0.0 if math.isnan(col.x_range) else col.x_range), the
    idiom of contract 10.1 as Task 9 amends it."""
    def strip(col):
        return dataclasses.replace(col, brackets=None, x_range=0.0 if math.isnan(col.x_range) else col.x_range)
    spec = _spec(bracket=_even(0.02), record_brackets=True)
    with OF.chunk():
        one, two = _col(spec), _col(spec)
    assert one.brackets is not None and len(one.brackets[0]) > 0 and math.isnan(one.x_range)
    assert one == one and one != two                          # the identity shortcut; else nan != nan
    assert strip(one) == strip(two) and strip(dataclasses.replace(one, x_range=5.0)) != strip(two)
    one, two = dataclasses.replace(one, x_range=0.0), dataclasses.replace(two, x_range=0.0)
    assert one.brackets is not None and one == two and hash(one) == hash(two)   # never touching the arrays
    blank = dataclasses.replace(one, brackets=None)
    assert blank == one and dataclasses.replace(two, brackets=(np.zeros(3), np.zeros(3))) == one
    assert "brackets" not in repr(one) and "wins=" in repr(one)
    assert dataclasses.replace(one, wins=one.wins + 1) != one


def test_brackets_record_return_and_duration_of_chunk_0() -> None:
    """Contract 9.1's input: per take-profit or stop fill, the net return per unit stake and the checks from entry
    to exit, from chunk 0 only, at most BRACKET_SAMPLE of them."""
    m = 0.2
    spec = _spec(mult=0.0, floor=0.0, terms=_terms(min_quote=1.0, min_krw=1.0), bracket=_even(m),
                 record_brackets=True, days=_days(10), **_gap(m))        # 10 brackets a path, 20,000 a chunk
    with OF.chunk():
        col = _col(spec, n=2 * simulate.CHUNK)
        first = simulate._run_paths(spec, n=simulate.CHUNK, chunk=0, seed=_SEED)
        later = simulate._run_paths(spec, n=simulate.CHUNK, chunk=1, seed=_SEED)
        saved = simulate.BRACKET_SAMPLE
        simulate.BRACKET_SAMPLE = 50
        try:
            short = _col(spec, n=2 * simulate.CHUNK)
        finally:
            simulate.BRACKET_SAMPLE = saved
        assert not _col(dataclasses.replace(spec, record_brackets=False)).brackets
    r, d = col.brackets
    assert len(r) == len(d) == int(first["wins"].sum() + first["losses"].sum()) < col.wins + col.losses
    assert later["wins"].sum() > 0 and later["br_r"].size == later["br_d"].size == 0     # chunk 1 records none
    assert (d == 1).all()
    assert np.allclose(np.sort(np.unique(np.round(r, 9))), [math.exp(-m) - 1.0, math.exp(m) - 1.0], atol=1e-9)
    assert np.array_equal(short.brackets[0], r[:50]) and np.array_equal(short.brackets[1], d[:50])
    with OF.chunk():
        costly = _col(dataclasses.replace(spec, mult=1.0))
    r1 = costly.brackets[0]
    assert np.allclose(r1[r1 > 0], math.exp(m) * (1 - 1e-3) - (1 + 1e-3), atol=1e-9)
    assert np.allclose(r1[r1 < 0], math.exp(-m) * (1 - 1e-3) - (1 + 1e-3), atol=1e-9)


def test_refit_groups_draw_their_own_fit_and_stream() -> None:
    fits = tuple(dataclasses.replace(_FIT, cond_vol_last=_FIT.cond_vol_last * (1.0 + g / 10.0))
                 for g in range(simulate.REFIT_B))
    spec = _garch(fits=fits, days=_days(5))
    with OF.chunk():
        p = simulate._run_paths(spec, n=2_000, chunk=0, seed=_SEED)["p"]
        for g in (0, 7, 19):
            ret = models.simulate_garch(fits[g], n_paths=100, horizon=5,
                                        seed=models.stream(_SEED, 0, "refit", g))[0]
            want = np.full(100, spec.p0)
            for s in range(5):
                want = want * np.exp(ret[:, s])
            assert np.array_equal(p[100 * g:100 * (g + 1)], want), g
        _raises(lambda: simulate._run_paths(spec, n=2_010, chunk=0, seed=_SEED), "refits over a multiple of 20")
        _raises(lambda: simulate._run_paths(_garch(fits=fits[:3]), n=2_000, chunk=0, seed=_SEED), "got 3 fits")


def test_rules_this_engine_does_not_simulate_fail_closed() -> None:
    """A spec this engine cannot price faithfully (a band where none belongs, the replay engine, wrong check shapes)
    is refused, never priced without the rule it needs."""
    days = _days()
    # Task 10 builds the band, the locks, the daily loss, the rule dates and the delisting columns (tests/odds_locks.py
    # tests each, and its refusals of a limit where none belongs); a crypto leg with a price limit is still refused
    cases = ((_spec(limits=np.full(30, 0.30)), "any other leg nan"), (_spec(engine="replay"), "engine 'replay'"),
             (_spec(checks=simulate.checks("CRYPTO", days, True)), "open, then its close"),
             (_garch(checks=simulate.checks("CRYPTO", days, False)), "close only"),
             (_spec(checks=simulate.checks("CRYPTO", (), False), limits=np.zeros(0)), "at least one check"))
    with OF.chunk():
        for spec, text in cases:
            _raises(lambda: simulate._run_paths(spec, n=10, chunk=0, seed=_SEED), text)
            _raises(lambda: _col(spec), text)


def test_fixtures_inputs_and_even_rows() -> None:
    rows = OF.even_rows(0.5)
    m_o, m_i, r = models.rows(rows)
    assert len(rows.dates) == 400 and rows.dates[-1] == "2026-10-22" and (m_o == 0.0).all()
    assert (np.exp(m_i) >= math.exp(0.5)).all() and (np.exp(-m_i) <= math.exp(-0.5)).all()
    assert np.allclose(m_i, 0.5, rtol=0.0, atol=1e-15) and np.allclose(np.abs(r), 0.5, rtol=0.0, atol=1e-15)
    assert rows.md5 == plan.series_md5(rows.symbol, rows.source, rows.dates, rows.open, rows.close, "", "final")
    p = OF.plan()
    inp = OF.inputs(p, rows)
    assert inp.sessions == tuple((date(2026, 10, 23) + timedelta(days=i)).isoformat() for i in range(10))
    assert (inp.comparison_id, inp.run_counter, inp.comparison_plans, inp.comparison_typed, inp.plan_runs) == \
        ("c000001", 1, 1, 0, 1)
    assert inp.provenance == plan.Provenance(repo_anchor="git:" + "0" * 40, tree_hash="f" * 64, cryptography="49.0.0")
    assert inp.replay is None and inp.price_limits == () and inp.calendar_sha256 == "" and inp.calendar_error == ""
    ctx = OF.odds_ctx()
    assert plan.check_now(ctx, inp.now) is None
    assert plan.check_data(p, ctx, inp, "CRYPTO") is None and plan.check_history(p, inp, "CRYPTO") is None
    assert OF.inputs(p, rows, run_counter=7).run_counter == 7
