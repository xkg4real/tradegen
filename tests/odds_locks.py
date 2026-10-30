"""The path engine, part 2 (odds plan Task 10; spec 7.2 "Bands", "Band edges", "Limit-down locks", "Delisting
stress", 7.3; contract 8.3-8.4; Q5, Q26, Q29): the KRX band of each session, band-edge sessions, the limit-down lock
with d_lock and its flat 2x exit charge, LOCKED_AT_HORIZON, the daily loss stop on Asia/Seoul dates, the rule dates,
the delisting columns, the OKX per-entry cap and the worst stop gap. Hand-made prices run simulate._paths directly
(each session's band built as the engine builds it); engine runs draw their own paths. Everything runs under
OF.chunk() (CHUNK 2,000). The fixtures of tests/odds_simulate.py (Task 9) are reused by name."""
from __future__ import annotations

import dataclasses
import hashlib
import math
from datetime import date, timedelta

import numpy as np

from core.odds import costs, plan, simulate
from tests import odds_fixtures as OF
from tests.odds_simulate import _FIT, _L, _W0, _days, _gap, _garch, _raises, _spec, _terms

_SEED = hashlib.sha256(b"tests/odds_locks").digest()
_MILLION = 1_000_000.0
_WIDE = plan.Bracket(take_profit=1.0, stop=0.9)          # a bracket that never fires on these prices


def _weekdays(k: int) -> tuple[date, ...]:
    """k KRX-like sessions: the weekdays from Friday 2026-10-23 (a fixture: no holidays)."""
    days, day = [], date(2026, 10, 23)
    while len(days) < k:
        if day.weekday() < 5:
            days.append(day)
        day += timedelta(days=1)
    return tuple(days)


def _etf(**changes) -> costs.Terms:
    """KIS terms of the KRX ETF 069500: KRX_ETF_line (3 bp, or the tick floor of the copied ETF table), lot 1, no
    minimum and no fixed charge; any field can be changed."""
    fields = dict(venue="kis", symbol="069500", book="KRX_ETF_line", quote="KRW", lot=1.0, min_quote=0.0,
                  min_krw=0.0, phi_buy=0.0, phi_sell=0.0, ladder=None, ladder_from=None, quote_krw=1.0)
    fields.update(changes)
    return costs.Terms(**fields)


def _krx(**changes) -> simulate.PathSpec:
    """Task 9's _spec on the KRX ETF: the open and the close of 20 weekday sessions (KR checks: both on the session
    date), a 30% band in each session, p0 KRW 10,000."""
    days = changes.pop("days", _weekdays(20))
    fields = dict(terms=_etf(), p0=10_000.0, checks=simulate.checks("KR", days, False),
                  limits=np.full(len(days), 0.30))
    fields.update(changes)
    return _spec(days=days, **fields)


def _hand(spec: simulate.PathSpec, prices, n: int = 1) -> dict:
    """simulate._paths over hand-made prices, one per check of `spec` and the same on each of n paths. Each session's
    band is costs.band around the previous close at the session's limit (nan: none), as the engine builds it, and
    every price must lie inside its band."""
    assert len(prices) == len(spec.checks.on)
    rows, ref, d, u = [], float(spec.p0), 0.0, math.inf
    for j, price in enumerate(prices):
        if not spec.checks.close[j]:
            limit = float(spec.limits[spec.checks.session[j]])
            if not math.isnan(limit):
                d, u = costs.band(np.full(n, ref), limit, spec.terms, spec.checks.on[j])
        p = np.full(n, float(price))
        assert np.all(d <= p) and np.all(p <= u), (j, price)
        rows.append((p, d, u))
        ref = float(price)
    with OF.chunk():
        return simulate._paths(spec, iter(rows), n, False)


def _rate(terms: costs.Terms, price: float, on: date, side: str) -> float:
    """The base-scenario rate of one fill (costs.kappa at mult 1)."""
    return float(costs.kappa(terms, np.array([price]), on, 1.0, side=side)[0])


def _rule(what: str, day: date) -> dict:
    """The rule dates simulate() passes for one Screening flag (contract 8.5): entries stop from any flag's date, and
    an auto_off or effective_until date also forces the exit."""
    return {"stop_entries_from": day, "force_exit_from": day if what in ("auto_off", "effective_until") else None}


# The lock fixture: 50 units of the ETF bought at the first open for KRW 10,000 with a 5% stop (KRW 9,500), and
# fixed charges of KRW 300 a buy and KRW 500 a sell. Session 0's band is [7,000, 13,000]; the close at 7,000 is its
# D, so the stop triggers there and is locked (d_lock 7,000). Sessions 1 and 2 have the band [4,900, 9,100].
_LOCK = dict(w0=_MILLION, floor=0.0, target=1e12, fraction=plan.fixed(0.5), bracket=plan.Bracket(take_profit=1.0,
             stop=0.05), terms=_etf(phi_buy=300.0, phi_sell=500.0))
_LOCK_PRICES = (10_000.0, 7_000.0, 6_000.0, 7_000.0, 7_005.0, 7_010.0)


def _lock_spec(checks: int) -> simulate.PathSpec:
    """The lock fixture over its first `checks` checks (3 sessions, so at most 6), with one 30% limit for each
    session those checks touch, so the engine's own _check_spec accepts it."""
    full = simulate.checks("KR", _weekdays(3), False)
    cut = simulate.Checks(session=full.session[:checks], close=full.close[:checks], seoul=full.seoul[:checks],
                          on=full.on[:checks])
    return _krx(days=_weekdays(3), checks=cut, limits=np.full(int(cut.session[-1]) + 1, 0.30), **_LOCK)


def _entered_cash() -> tuple[float, float]:
    """(cash after the first entry, its charge) in the lock fixture: 50 units at KRW 10,000, the buy rate there,
    and the KRW 300 fixed charge."""
    kb = _rate(_LOCK["terms"], 10_000.0, date(2026, 10, 23), "buy")
    charge = 50 * 10_000.0 * kb + 300.0
    return _MILLION - 50 * 10_000.0 - charge, charge


def test_a_limit_down_lock_persists_and_fills_at_a_flat_2x_exit_charge() -> None:
    """Spec 7.2: the stop that triggers at the close on session 0's D (7,000) cannot fill; the exit stays queued
    across checks and sessions (6,000 and then exactly 7,000 keep it) and fills at the first check strictly above
    d_lock, the open at 7,005, at a flat 2x exit charge: twice the sell rate and twice the fixed charge, never 4x.
    A locked exit is neither a win nor a loss (unresolved), and its fill below the stop is the worst gap. Every exit
    that triggers at D is locked (Q26), the rule-date and daily-loss exits included."""
    out = _hand(_lock_spec(6), _LOCK_PRICES)
    cash, buy = _entered_cash()
    ks = _rate(_LOCK["terms"], 7_005.0, date(2026, 10, 27), "sell")
    fill = 50 * 7_005.0 * 2.0 * ks + 2.0 * 500.0
    assert math.isclose(out["v"][0], cash + 50 * 7_005.0 - fill, rel_tol=1e-12), out["v"]
    assert math.isclose(out["cost"][0], buy + fill, rel_tol=1e-12), out["cost"]
    assert out["carried"][0] == 1 and not out["locked"][0] and out["entries"][0] == 1
    assert (out["wins"][0], out["losses"][0], out["unresolved"][0]) == (0, 0, 1)
    assert math.isclose(out["gap"][0], (9_500.0 - 7_005.0) / 10_000.0, rel_tol=1e-12)
    assert math.isclose(out["x"][0], out["v"][0] + out["cost"][0] - _MILLION, abs_tol=1e-6)   # G unchanged
    # still locked after every earlier check: the fill comes at the open of session 2, not before
    for k in (2, 3, 4):
        part = _hand(_lock_spec(k), _LOCK_PRICES[:k])
        assert part["locked"][0] and part["carried"][0] == 0, k
        simulate._check_spec(_lock_spec(k))                              # a spec the engine itself accepts
    # session 1 opens at its D (7,000) with no bracket exit in reach; an auto_off date (Monday 2026-10-26) or a
    # breach of a KRW 100,000 daily loss names the exit there: it locks, fills at session 2's open (7,005) at the
    # flat 2x charge, and nothing is entered after it
    wide = dict(_LOCK, bracket=plan.Bracket(take_profit=1.0, stop=0.5))
    rows = (10_000.0, 10_000.0, 7_000.0, 7_000.0, 7_005.0, 7_010.0)
    for extra in (_rule("auto_off", date(2026, 10, 26)), {"daily_loss": 100_000.0}):
        at_d = _hand(_krx(days=_weekdays(3), **wide, **extra), rows)
        assert at_d["carried"][0] == 1 and not at_d["locked"][0] and at_d["entries"][0] == 1, extra
        assert math.isclose(at_d["v"][0], cash + 50 * 7_005.0 - fill, rel_tol=1e-12), (extra, at_d["v"])


def test_a_next_open_above_the_new_d_but_not_above_d_lock_keeps_the_lock() -> None:
    """Contract 8.4 (REVISIONS M12): after a close locked at D_s = 7,000, the next open at 6,000 lies in
    (0.7 D_s, D_s], above the new session's D (4,900): the queued exit still waits, because it needs a price
    strictly above the D of the session where it locked. A new trigger uses the current D: a stop that fills at
    7,005 (above session 0's D), re-entered at session 1's open at 6,400 and hit at its close at 6,000 (above that
    session's D, 4,905), fills at once at the normal charge, with no lock."""
    held = _hand(_lock_spec(3), _LOCK_PRICES[:3])
    assert held["locked"][0] and held["carried"][0] == 0 and held["losses"][0] == 0
    released = _hand(_lock_spec(3), (10_000.0, 7_000.0, 7_005.0))
    assert not released["locked"][0] and released["carried"][0] == 1
    fresh = _hand(_krx(days=_weekdays(3), **_LOCK), (10_000.0, 7_005.0, 6_400.0, 6_000.0, 6_000.0, 6_000.0))
    assert fresh["losses"][0] == 2 and fresh["carried"][0] == 0 and not fresh["locked"][0]


def test_locked_at_horizon_is_valued_at_the_locked_price_less_the_carried_charge() -> None:
    """Spec 7.2: a position still locked at the horizon is valued at its price less the carried (2x) exit charge;
    the terminal cost holds that charge, so V + C - W0 is still X. run_column counts these paths."""
    out = _hand(_lock_spec(3), _LOCK_PRICES[:3])
    cash, buy = _entered_cash()
    ks = _rate(_LOCK["terms"], 6_000.0, date(2026, 10, 26), "sell")
    carried = 50 * 6_000.0 * 2.0 * ks + 2.0 * 500.0
    assert math.isclose(out["v"][0], cash + 50 * 6_000.0 - carried, rel_tol=1e-12)
    assert math.isclose(out["cost"][0], buy + carried, rel_tol=1e-12)
    assert out["outcome"][0] == 0 and out["locked"][0]                 # RUNNING, flagged LOCKED_AT_HORIZON
    # engine: every session moves to a band edge, so stops lock often and some stay locked at the end
    spec = _krx(bracket=plan.Bracket(take_profit=0.2, stop=0.1), terms=_etf(phi_sell=200.0), **_gap(0.5))
    with OF.chunk():
        col = simulate.run_column(spec, n=simulate.CHUNK, seed=_SEED, key="no_edge/bootstrap/base",
                                  member="bootstrap", scenario="base")
        out = simulate._run_paths(spec, n=simulate.CHUNK, chunk=0, seed=_SEED)
    assert col.locked_at_horizon == int(out["locked"].sum()) > 0, col.locked_at_horizon
    assert (out["outcome"][out["locked"]] == 0).all() and col.running >= col.locked_at_horizon
    assert out["carried"].sum() > 0 and col.unresolved > 0
    assert np.allclose(out["x"], out["v"] + out["cost"] - _W0, rtol=0.0, atol=1e-6)


def test_krx_prices_stay_in_each_sessions_band_and_edge_sessions_are_counted() -> None:
    """Spec 7.2 and 8.o1 at engine level: at each open the band is costs.band around the previous close at that
    session's own limit (here 30% and 15% in turn), it holds until the close, and every price lies inside it; a
    session that opens at its D or U stays there until the close, and run_column counts those path-sessions in
    band_edge_sessions and their share of all."""
    m = np.linspace(0.0, 0.6, 61)
    limits = np.where(np.arange(20) % 2 == 1, 0.15, 0.30)
    spec = _krx(m_o=m, m_i=m[::-1].copy(), block=3.0, limits=limits)
    n = 2_000
    ref, edges, lows, highs = np.full(n, spec.p0), np.zeros(n, dtype=np.int64), 0, 0
    with OF.chunk():
        for j, (p, d, u) in enumerate(simulate._bootstrap_prices(spec, n, 0, _SEED)):
            if not spec.checks.close[j]:
                want = costs.band(ref, limits[spec.checks.session[j]], spec.terms, spec.checks.on[j])
                assert np.array_equal(d, want[0]) and np.array_equal(u, want[1]), j
                band, opened = (d, u), p
                at_edge = (p == d) | (p == u)
                edges += at_edge
                lows, highs = lows + int((p == d).sum()), highs + int((p == u).sum())
            else:
                assert np.array_equal(d, band[0]) and np.array_equal(u, band[1]), j   # held until the close
                assert np.array_equal(p[at_edge], opened[at_edge]), j        # an edge open stays at the edge
            assert (d <= p).all() and (p <= u).all(), j
            ref = p
        col = simulate.run_column(spec, n=n, seed=_SEED, key="no_edge/bootstrap/base", member="bootstrap",
                                  scenario="base")
    assert lows > 0 and highs > 0 and 0 < edges.sum() < n * 20
    assert col.band_edge_sessions == int(edges.sum())
    assert math.isclose(col.band_edge_share, edges.sum() / (n * 20), rel_tol=1e-12)


def test_gross_value_stays_fair_under_bands_locks_and_the_daily_loss() -> None:
    """Spec 8.o1: inside the band, with locks, the 2x carry and daily-loss exits, X = G_tau - W0 still has mean 0
    while the net value pays the costs. The 4 SE bound sees only gross drift (4 SE is above the column's mean cost);
    pathwise, X = V + C - W0 holds exactly (no first passage at this target, and a done path holds no units), so
    neither a locked horizon value nor a path after tau may disagree with its costs."""
    m = np.linspace(0.0, 0.6, 61)
    spec = _krx(m_o=m, m_i=m[::-1].copy(), block=3.0, bracket=plan.Bracket(take_profit=0.1, stop=0.1),
                daily_loss=1_500.0, terms=_etf(phi_buy=50.0, phi_sell=50.0))
    with OF.chunk():
        col = simulate.run_column(spec, n=2 * simulate.CHUNK, seed=_SEED, key="no_edge/bootstrap/base",
                                  member="bootstrap", scenario="base")
        out = simulate._run_paths(spec, n=simulate.CHUNK, chunk=0, seed=_SEED)
        free = simulate._run_paths(dataclasses.replace(spec, daily_loss=math.inf), n=simulate.CHUNK, chunk=0,
                                   seed=_SEED)
    se = math.sqrt(col.x_var / col.n)
    assert abs(col.x_mean) <= 4.0 * se, (col.x_mean, se)
    assert np.allclose(out["x"], out["v"] + out["cost"] - _W0, rtol=0.0, atol=1e-6)
    assert out["carried"].sum() > 0 and not np.array_equal(out["v"], free["v"])    # locks and daily-loss exits
    assert col.mean < _W0 and col.mean_cost > 0.0


def test_cash_never_below_zero_under_2x_stress_plus_the_carry() -> None:
    """Spec 7.1 and 8.o5: under 2x costs plus the 2x carry of locked exits, on sessions that all close at a band
    edge, the always rule keeps cash and value >= 0 and floor-protected sizing keeps both >= L; on a stock ladder
    whose KRW 1,000 tick makes the sell rate exceed 100% at low prices, exact hand-made fill, locked-horizon and
    delisting cases below exercise the clips and retain nonnegative cash and value."""
    ladder = _etf(symbol="005930", book="KRX_stock_book", phi_buy=300.0, phi_sell=500.0, ladder=((0.0, 1_000.0),),
                  ladder_from=date(2026, 1, 1))
    for terms, p0 in ((_etf(phi_buy=300.0, phi_sell=500.0), 2_005.0), (ladder, 20_005.0)):
        adverse = dict(terms=terms, p0=p0, mult=costs.COST_STRESS, daily_loss=2_000.0, **_gap(1.0))
        with OF.chunk():
            for floor in (0.0, _L):
                spec = _krx(floor=floor, sizing="stop_based", bracket=plan.Bracket(take_profit=0.5, stop=0.05),
                            **adverse)
                out = simulate._run_paths(spec, n=simulate.CHUNK, chunk=0, seed=_SEED)
                assert out["cash_min"].min() >= 0.0 and out["v"].min() >= 0.0, (terms.book, floor)
                assert out["carried"].sum() > 0 and out["locked"].any(), (terms.book, floor)
            for bracket in (None, plan.Bracket(take_profit=0.5, stop=0.05)):
                out = simulate._run_paths(_krx(bracket=bracket, **adverse), n=simulate.CHUNK, chunk=0, seed=_SEED)
                assert out["cash_min"].min() >= _L and out["v"].min() >= _L, (terms.book, bracket)

    # P3: component-level prices inside dated bands, with a wider second session to
    # expose the queued-fill clip. The stochastic band-edge law is tested separately.
    low = _krx(days=_weekdays(2), p0=2_000.0, limits=np.array([0.30, 0.75]),
               **dict(_LOCK, terms=ladder), mult=costs.COST_STRESS)
    prices = (2_000.0, 2_000.0, 1_000.0, 1_500.0)
    units = 250.0
    buy = units * 2_000.0 * 2.0 * _rate(ladder, 2_000.0, low.checks.on[0], "buy") + 600.0
    cash = _MILLION - units * 2_000.0 - buy
    released = _hand(low, prices)
    cut = simulate.Checks(session=low.checks.session[:3], close=low.checks.close[:3],
                          seoul=low.checks.seoul[:3], on=low.checks.on[:3])
    locked = _hand(dataclasses.replace(low, checks=cut), prices[:3])
    for out, price, is_locked in ((released, 1_500.0, False), (locked, 1_000.0, True)):
        assert 4.0 * _rate(ladder, price, low.checks.on[2], "sell") > 1.0
        assert out["entries"][0] == 1 and bool(out["locked"][0]) is is_locked
        assert out["carried"][0] == (0 if is_locked else 1)
        assert math.isclose(out["v"][0], cash - 2_000.0, rel_tol=1e-12)
        assert math.isclose(out["cost"][0], buy + units * price + 2_000.0, rel_tol=1e-12)
        assert out["cash_min"].min() >= 0.0 and out["v"].min() >= 0.0
    gone = dataclasses.replace(low, checks=simulate.checks("KR", _weekdays(1), False),
                               limits=np.array([0.75]), delist_h=0.30)
    out = _hand(gone, (2_000.0, 1_000.0))
    assert 2.0 * _rate(ladder, 700.0, gone.checks.on[1], "sell") > 1.0
    assert out["entries"][0] == 1 and not out["locked"][0]
    assert math.isclose(out["v"][0], cash - 1_000.0, rel_tol=1e-12)
    assert math.isclose(out["cost"][0], buy + units * 1_000.0 + 1_000.0, rel_tol=1e-12)
    assert out["cash_min"].min() >= 0.0 and out["v"].min() >= 0.0


def test_the_daily_loss_stops_trading_until_the_next_seoul_date() -> None:
    """Spec 7.3 and Q26: the loss is measured from the value carried into the Asia/Seoul date (a crypto open d and
    the previous close share the date d). Prices 1,000 | 1,100, 1,060 | 1,010, 1,020 | 1,000, 990 | 960, 940 | 950
    ('|' starts a date) on 100 units, no costs: the 5,000 loss from the 106,000 carried in is hit at 1,010 and the
    exit fills; the same-date open at 1,020 opens nothing; the next date re-enters 101 units at 1,000; and 940 is
    5,050 below the 99,990 carried into its date (but only 2,020 below the check before), so it exits again. The
    breach and the value carried in are both V, the liquidation value, never the mark cash + units x p."""
    rows = (1_000.0, 1_100.0, 1_060.0, 1_010.0, 1_020.0, 1_000.0, 990.0, 960.0, 940.0, 950.0)
    base = dict(days=_days(5), terms=_terms(lot=1.0, min_quote=1.0, min_krw=1.0), mult=0.0, w0=100_000.0,
                floor=0.0, target=1e12, bracket=_WIDE, p0=1_000.0)
    out = _hand(_spec(daily_loss=5_000.0, **base), rows)
    assert out["entries"][0] == 2 and out["unresolved"][0] == 2 and out["wins"][0] == out["losses"][0] == 0
    assert math.isclose(out["v"][0], 101 * 940.0, rel_tol=1e-12), out["v"]
    held = _hand(_spec(daily_loss=math.inf, **base), rows)
    assert held["entries"][0] == 1 and math.isclose(held["v"][0], 100 * 950.0, rel_tol=1e-12)
    # P1: buy-and-hold exits at the daily loss, then never enters again.
    once = _hand(_spec(daily_loss=5_000.0, **dict(base, bracket=None)), rows)
    assert once["entries"][0] == 1 and once["v"][0] == 101_000.0
    assert once["unresolved"][0] == 0
    # a breach stops the date even when the stop names the exit (spec 7.3: "A breach exits and stops trading for
    # the rest of that day"): the stop fill at 940 is also 6,000 below the 100,000 carried in, so the same-date
    # open at 900 opens nothing, and the next date buys 94 units at 1,000
    stop = dict(base, days=_days(3), bracket=plan.Bracket(take_profit=10.0, stop=0.05))
    stopped = _hand(_spec(daily_loss=5_000.0, **stop), (1_000.0, 940.0, 900.0, 1_000.0, 1_000.0, 1_000.0))
    assert stopped["losses"][0] == 1 and stopped["entries"][0] == 2 and stopped["v"][0] == 94 * 1_000.0
    # V, not the mark: on the KRX ETF with KRW 300 and 500 fixed charges, a Friday close at 9,950 is KRW 3,689.65
    # below W0 in V (2,995 in the mark), so a 3,500 limit exits there and re-enters on Monday; a Monday open at 9,950
    # is 2,499.65 below the V carried in (3,194.65 below Friday's mark), so a 3,000 limit keeps the position
    krx = dict(w0=_MILLION, floor=0.0, target=1e12, fraction=plan.fixed(0.5), bracket=_WIDE,
               terms=_etf(phi_buy=300.0, phi_sell=500.0))
    cut = _hand(_krx(days=_weekdays(2), daily_loss=3_500.0, **krx), (10_000.0, 9_950.0, 9_950.0, 9_950.0))
    kept = _hand(_krx(days=_weekdays(3), daily_loss=3_000.0, **krx), (10_000.0, 10_000.0) + (9_950.0,) * 4)
    assert cut["entries"][0] == 2 and kept["entries"][0] == 1, (cut["entries"], kept["entries"])
    # an engine run on crypto checks (a close's Seoul date is the next day's): the stop changes the paths and the
    # floor still holds
    spec = _spec(daily_loss=300.0, bracket=plan.Bracket(take_profit=0.05, stop=0.05))
    with OF.chunk():
        out = simulate._run_paths(spec, n=simulate.CHUNK, chunk=0, seed=_SEED)
        free = simulate._run_paths(_spec(bracket=spec.bracket), n=simulate.CHUNK, chunk=0, seed=_SEED)
    assert not np.array_equal(out["entries"], free["entries"]) and out["cash_min"].min() >= _L


def test_auto_off_forces_an_exit_at_its_first_check_and_no_entry_after() -> None:
    """Spec 6.3 and O5 (auto_off): from 2026-10-28, a Wednesday session, the first check on or after it (that
    session's open at 10,900) forces the exit, and nothing is entered after it. Before it the bracket wins at
    10,600 and re-enters 48 units at the next check. No costs, so every value is exact."""
    rows = (10_000.0, 10_100.0, 10_600.0, 10_600.0, 10_700.0, 10_800.0, 10_900.0, 11_200.0, 11_000.0, 11_100.0,
            11_000.0, 11_000.0)
    spec = _krx(days=_weekdays(6), w0=_MILLION, floor=0.0, target=1e12, mult=0.0, fraction=plan.fixed(0.5),
                bracket=plan.Bracket(take_profit=0.05, stop=0.5), **_rule("auto_off", date(2026, 10, 28)))
    out = _hand(spec, rows)
    cash = _MILLION - 50 * 10_000.0 + 50 * 10_600.0 - 48 * 10_600.0
    assert out["entries"][0] == 2 and out["wins"][0] == 1 and out["unresolved"][0] == 1
    assert math.isclose(out["v"][0], cash + 48 * 10_900.0, rel_tol=1e-12) and out["cost"][0] == 0.0
    free = _hand(_krx(days=_weekdays(6), w0=_MILLION, floor=0.0, target=1e12, mult=0.0, fraction=plan.fixed(0.5),
                      bracket=plan.Bracket(take_profit=0.05, stop=0.5)), rows)
    assert free["wins"][0] == 2 and free["entries"][0] == 3              # without the date: a win at 11,200


def test_effective_until_on_a_non_session_date_exits_at_the_next_check() -> None:
    """Spec 6.3 and O5 (effective_until): a Saturday date (2026-10-31) has no check, so the forced exit comes at the
    next one, Monday 2026-11-02's open at 11,200; the flat path then opens nothing in the checks left."""
    rows = tuple(10_000.0 + 100.0 * j for j in range(16))
    base = dict(days=_weekdays(8), w0=_MILLION, floor=0.0, target=1e12, mult=0.0, fraction=plan.fixed(0.5),
                bracket=_WIDE)
    out = _hand(_krx(**base, **_rule("effective_until", date(2026, 10, 31))), rows)
    assert _weekdays(8)[6] == date(2026, 11, 2) and rows[12] == 11_200.0
    assert out["entries"][0] == 1 and out["unresolved"][0] == 1
    assert math.isclose(out["v"][0], _MILLION - 50 * 10_000.0 + 50 * 11_200.0, rel_tol=1e-12)
    held = _hand(_krx(**base), rows)
    assert math.isclose(held["v"][0], _MILLION - 50 * 10_000.0 + 50 * 11_500.0, rel_tol=1e-12)
    # the engine itself opens nothing after a forced-exit date, even with no stop_entries_from beside it
    alone = _hand(_krx(**base, force_exit_from=date(2026, 10, 31)), rows)
    assert alone["entries"][0] == 1 and alone["v"][0] == out["v"][0]


def test_from_review_by_no_entry_happens_while_the_position_is_kept_and_may_close() -> None:
    """Q5 and O5 (review_by, OWNER): from 2026-10-27 no entry and no re-entry, but nothing is forced: the position
    held then stays open and still closes at its take-profit (11,200 on 48 units entered at 10,600); a review_by on
    the start date opens nothing at all."""
    rows = (10_000.0, 10_100.0, 10_600.0, 10_600.0, 10_700.0, 11_200.0, 11_000.0, 10_900.0, 10_800.0, 10_900.0)
    base = dict(days=_weekdays(5), w0=_MILLION, floor=0.0, target=1e12, mult=0.0, fraction=plan.fixed(0.5),
                bracket=plan.Bracket(take_profit=0.05, stop=0.5))
    out = _hand(_krx(**base, **_rule("review_by", date(2026, 10, 27))), rows)
    cash = _MILLION - 50 * 10_000.0 + 50 * 10_600.0 - 48 * 10_600.0
    assert out["entries"][0] == 2 and out["wins"][0] == 2 and out["unresolved"][0] == 0
    assert math.isclose(out["v"][0], cash + 48 * 11_200.0, rel_tol=1e-12)
    free = _hand(_krx(**base), rows)
    assert free["entries"][0] == 3                                        # without the date: a re-entry at 11,000
    none = _hand(_krx(**base, **_rule("review_by", date(2026, 10, 23))), rows)
    assert not none["entered"][0] and none["v"][0] == _MILLION


def test_the_okx_cap_bounds_every_entry() -> None:
    """O11: every simulated OKX entry is at most the cap (here 10% of KRW 42,000), re-entries included; without
    the cap the same rule stakes about KRW 21,000."""
    terms = _terms(venue="okx", quote="USDT", min_quote=1.0, min_krw=1_400.0, quote_krw=1_400.0)
    spec = _spec(terms=terms, bracket=plan.Bracket(take_profit=0.02, stop=0.02), cap_krw=4_200.0)
    with OF.chunk():
        n = simulate.CHUNK
        out = simulate._run_paths(spec, n=n, chunk=0, seed=_SEED)
        free = simulate._run_paths(_spec(terms=terms, bracket=spec.bracket), n=n, chunk=0, seed=_SEED)
    entered = out["entered"]
    assert entered.all() and out["entries"].sum() > 2 * n                 # re-entries, each one capped
    # the largest stake of each path is the cap, less under one lot (1e-8 BTC, about KRW 1 here)
    assert out["stake"].max() <= 4_200.0 and out["stake"][entered].min() > 4_190.0
    assert free["stake"].min() > 20_000.0


def test_delisting_sells_at_p_times_1_minus_h_after_the_first_entry_and_never_reenters() -> None:
    """Spec 7.2 and Q29: on each delisting column (h = 0.30 and 1.00) every path entered at the first open sells at
    the next check for p (1 - h), with the normal exit charge (none when written off at h = 1), books h x p x units
    as the delisting stress loss, and never enters again, bracket or not; G is unchanged by the sale."""
    terms = _terms(phi_buy=100.0, phi_sell=200.0)
    n = 500
    for h in costs.DELIST_STRESS:
        for bracket in (None, plan.Bracket(take_profit=0.02, stop=0.02)):
            spec = _spec(terms=terms, bracket=bracket, delist_h=h)
            with OF.chunk():
                out = simulate._run_paths(spec, n=n, chunk=0, seed=_SEED)
                p0, p1 = [p for p, _, _ in simulate._bootstrap_prices(spec, n, 0, _SEED)][:2]
            on = spec.checks.on
            units, _ = costs.rule_units(spec.fraction, np.full(n, _W0), p0, terms=terms, on=on[0], mult=1.0,
                                        target=spec.target, w0=_W0, take_profit=None if bracket is None else 0.02,
                                        stop=None if bracket is None else 0.02, sizing="floor_safe", floor=_L,
                                        fstar=None, cap_krw=None)
            buy = units * p0 * costs.kappa(terms, p0, on[0], 1.0, side="buy") + 100.0
            q = p1 * (1.0 - h)
            fee = units * q * costs.kappa(terms, q, on[1], 1.0, side="sell") + 200.0 if h < 1.0 else 0.0
            assert np.allclose(out["v"], _W0 - units * p0 - buy + units * q - fee, rtol=0.0, atol=1e-6), h
            assert np.allclose(out["cost"], buy + units * p1 * h + fee, rtol=0.0, atol=1e-6), h
            assert (out["entries"] == 1).all() and (out["wins"] + out["losses"] == 0).all(), (h, bracket)
            assert np.allclose(out["x"], out["v"] + out["cost"] - _W0, rtol=0.0, atol=1e-6)
    # the first check after the FIRST entry: no bet at 10,000 (10% of the stake buys no unit), one unit at 4,000,
    # and the sale at the next check, 4,100 x 0.7
    spec = _spec(days=_days(3), delist_h=0.30, terms=_terms(lot=1.0, min_quote=1.0, min_krw=1.0),
                 fraction=plan.fixed(0.1), p0=10_000.0)
    out = _hand(spec, (10_000.0, 4_000.0, 4_100.0, 4_200.0, 4_300.0, 4_400.0))
    on = spec.checks.on
    buy, fee = 4_000.0 * _rate(spec.terms, 4_000.0, on[1], "buy"), 2_870.0 * _rate(spec.terms, 2_870.0, on[2], "sell")
    assert out["entries"][0] == 1 and math.isclose(out["v"][0], _W0 - 4_000.0 - buy + 2_870.0 - fee, rel_tol=1e-12)
    assert math.isclose(out["cost"][0], buy + 0.30 * 4_100.0 + fee, rel_tol=1e-12)
    # GARCH-t columns delist the same way
    with OF.chunk():
        out = simulate._run_paths(_garch(delist_h=1.0, bracket=plan.Bracket(take_profit=0.02, stop=0.02)), n=n,
                                  chunk=0, seed=_SEED)
    assert (out["entries"] == 1).all() and (out["wins"] + out["losses"] == 0).all()


def test_a_stop_fill_below_the_stop_records_worst_gap() -> None:
    """LIMIT_GAP: a stop that fills inside the band below its level (9,000 for a 9,500 stop) records the overshoot
    over the entry price, 5%; a locked stop that fills later below it records its own (24.95%, the lock fixture),
    and the column keeps the largest; a fill exactly at the stop records none."""
    spec = _krx(days=_weekdays(2), **_LOCK)
    assert math.isclose(_hand(spec, (10_000.0, 9_000.0, 9_000.0, 9_000.0))["gap"][0], 0.05, rel_tol=1e-12)
    assert _hand(spec, (10_000.0, 9_500.0, 9_500.0, 9_500.0))["gap"][0] == 0.0
    assert math.isclose(_hand(_lock_spec(6), _LOCK_PRICES)["gap"][0], 0.2495, rel_tol=1e-12)
    # P2: the stock's sell tax belongs only to the exit, including a gap fill.
    stock = _etf(symbol="005930", book="KRX_stock_book", ladder=((0.0, 1_000.0),),
                 ladder_from=date(2026, 1, 1), phi_buy=300.0, phi_sell=500.0)
    trip = _krx(days=_weekdays(1), **dict(_LOCK, terms=stock))
    out = _hand(trip, (10_000.0, 9_000.0))
    on = trip.checks.on[0]
    assert math.isclose(_rate(stock, 9_000.0, on, "sell") - _rate(stock, 9_000.0, on, "buy"),
                        0.002, rel_tol=1e-12)
    buy = 50 * 10_000.0 * _rate(stock, 10_000.0, on, "buy") + 300.0
    sell = 50 * 9_000.0 * _rate(stock, 9_000.0, on, "sell") + 500.0
    assert out["entries"][0] == out["losses"][0] == 1 and not out["locked"][0]
    assert math.isclose(out["v"][0], _MILLION - 50 * 1_000.0 - buy - sell, rel_tol=1e-12)
    assert math.isclose(out["cash_min"][0], _MILLION - 50 * 10_000.0 - buy, rel_tol=1e-12)
    assert math.isclose(out["cost"][0], buy + sell, rel_tol=1e-12)
    adverse = _krx(bracket=plan.Bracket(take_profit=0.2, stop=0.1), **_gap(0.5))
    with OF.chunk():
        col = simulate.run_column(adverse, n=simulate.CHUNK, seed=_SEED, key="no_edge/bootstrap/base",
                                  member="bootstrap", scenario="base")
        out = simulate._run_paths(adverse, n=simulate.CHUNK, chunk=0, seed=_SEED)
    assert col.worst_gap == float(out["gap"].max()) > 0.1, col.worst_gap


def test_band_and_rule_inputs_fail_closed() -> None:
    """A spec whose limits do not match its book, or a GARCH-t spec on a banded leg, is refused, never simulated
    without the band it has (or with one it lacks); so is a delisting share outside (0, 1], and a daily loss limit
    that is nan (no loss is >= nan, so the stop would be off) or not above 0 (it would stop all trading)."""
    holed = np.full(20, 0.30)
    holed[3] = np.nan
    garch_krx = _krx(engine="garch", m_o=None, m_i=None, block=1.0, fits=(_FIT,),
                     checks=simulate.checks("KR", _weekdays(20), True))
    cases = ((_krx(limits=np.full(19, 0.30)), "one price limit per session"),
             (_krx(limits=holed), "a KRX leg needs a finite price limit for every session"),
             (_krx(limits=np.full(20, np.nan)), "a KRX leg needs a finite price limit for every session"),
             (_spec(limits=np.full(30, 0.30)), "any other leg nan"),
             (garch_krx, "GARCH-t simulates no daily band"),
             (_spec(delist_h=0.0), "delist_h must be in (0, 1]"), (_spec(delist_h=1.5), "delist_h must be in (0, 1]"),
             (_spec(daily_loss=math.nan), "daily_loss must be > 0"), (_spec(daily_loss=0.0), "daily_loss must be > 0"))
    with OF.chunk():
        for spec, text in cases:
            _raises(lambda: simulate._run_paths(spec, n=10, chunk=0, seed=_SEED), text)
            _raises(lambda: simulate.run_column(spec, n=simulate.CHUNK, seed=_SEED, key="k", member="bootstrap",
                                                scenario="base"), text)
