### Task 10: The path engine, part 2: locks, daily loss, rule dates, delisting and the OKX cap (`core/odds/simulate.py`)

**Files:**
- Modify: `core/odds/simulate.py` (anchors, in file order: the module docstring; `_check_spec` (its last five `if`
  clauses); `_bootstrap_prices` and `_garch_prices` (both whole); `_paths` (whole); the `_run_paths` docstring (its
  first three lines); `_MERGED`; the `locked_at_horizon=` and `band_edge_share=` keyword lines of `run_column`; LF,
  kept)
- Modify: `tests/odds_simulate.py` (anchors: one line of `test_moves_follow_the_rows_and_the_streams`, and the
  docstring and the `cases` tuple of `test_rules_this_engine_does_not_simulate_fail_closed`; LF, kept)
- Create: `tests/odds_locks.py` (LF, UTF-8, no BOM; `odds_locks` is already in `tests.odds_acceptance.MODULES` since
  Task 1)
- Test: `tests/odds_locks.py` (new), `tests/odds_simulate.py` (Task 9's, two tests edited)

Both modified files are created by Task 9 of this plan, and the compliance follow-up touches neither, so the DRIFT
RULE of the Global Constraints applies only if Task 9 was executed with a recorded change to these texts: re-read each
file before each Edit, and if an old text below differs only because of such a ruling, make the same change to the
current text, keep that ruling's behaviour and add a one-line ruling under "Drift rulings" in the execution ledger.

**Interfaces:**
- Consumes:
  - Task 1: `tests.odds_fixtures.chunk(n=2_000)` (swaps `simulate.CHUNK`, `DEFAULT_PATHS` and `GARCH_SUB`, looked up
    when entered, restored in `finally`); the runner `.venv/Scripts/python.exe -m tests.odds_acceptance <module>/`,
    which collects only the `test_*` functions defined in each module (an imported helper is never a test).
  - Task 5 (`core.odds.plan`): `Bracket(take_profit, stop)`, `fixed(f)`.
  - Task 6 (`core.odds.costs`): `Terms` (keywords `venue, symbol, book, quote, lot, min_quote, min_krw, phi_buy,
    phi_sell, ladder, ladder_from, quote_krw`); `band(ref, limit, terms, on) -> (D, U)` (KRX_ETF_line and
    KRX_stock_book: the tick-rounded, clamped edges, ValueError unless 0 < limit < 1; every other book
    `(zeros, +inf)`); `kappa(terms, prices, on, mult, *, side)`; `rule_units(..., cap_krw)`;
    `LIMIT_DOWN_CARRY_COST_MULTIPLIER` (2.0); `DELIST_STRESS` ((0.30, 1.00)); `COST_STRESS` (2.0).
  - Task 9 (`core.odds.simulate`): `CHUNK`, `Checks(session, close, seoul, on)`, `checks(market, sessions,
    close_only)`, `PathSpec` (every field of contract 8.2), `run_column(spec, *, n, seed, key, member, scenario)`,
    `_run_paths(spec, *, n, chunk, seed)`, and the private `_check_spec`, `_bootstrap_prices`, `_garch_prices`,
    `_paths(spec, prices, n, record)` and `_MERGED` this task edits by name; `report.ColumnStats`.
  - Task 9 (`tests/odds_simulate.py`, imported by name): `_FIT` (one GARCH-t fit), `_W0` (42,000.0), `_L`
    (21,000.0), `_days(k=30)` (k crypto session dates from 2026-10-23), `_gap(m, rows=50)` (rows moving exactly m at
    every check, block 1), `_garch(**changes)`, `_raises(call, text)`, `_spec(**changes)` (a compounding
    floor-protected buy-and-hold of KRW 42,000 on 30 crypto sessions, Upbit-like terms; `days=` sets the sessions)
    and `_terms(**changes)` (Upbit BTC terms: 10 bp a side, lot 1e-8, minimum KRW 5,000).
- Produces (Tasks 11, 13, 14 and 17 rely on these):
  - The price protocol: `_bootstrap_prices(spec, n, chunk, seed)` and `_garch_prices(p0, ret)` yield one
    `(p, D, U)` per check, D and U the session's band arrays from `costs.band` on a banded (KRX) session, else the
    floats `0.0` and `math.inf`; `_paths(spec, prices, n, record)` consumes such triples. Task 17's replay engine
    (`_run_replay`) follows steps 1-6 of contract 8.4 on its own sleeve and does not call `_paths`.
  - `_paths` and `_run_paths` return, besides Task 9's keys, `"locked"` (bool: still locked at the horizon),
    `"edge"` (int64: sessions of the path that opened at a band edge), `"carried"` (int64: queued locked exits
    filled) and `"stake"` (float: the path's largest entry notional, KRW).
  - `_MERGED` gains `"locked"` and `"edge"`; `run_column` now fills `locked_at_horizon` (paths still locked at the
    horizon), `band_edge_sessions` (path-sessions that opened at a band edge) and `band_edge_share`
    (`band_edge_sessions / (n x sessions)`), which `report.flags_for` (Task 12) prints as `flag.locked` and
    `flag.bandedge`.
  - `_check_spec` keeps Task 9's engine and check-shape clauses (Task 17 routes engine `"replay"` around it through
    a dispatcher and leaves it unchanged) and now refuses, with ValueError: `limits` not of one entry per session; a
    KRX book with a non-finite limit, or any other book with a finite one; GARCH-t on a KRX book; `delist_h` outside
    (0, 1]; a `daily_loss` that is not > 0 (nan included: no loss is >= nan; `math.inf` means no limit). Task 9's
    band, daily-loss, rule-date and delisting refusals are gone: the engine simulates them.
  - `tests/odds_locks.py` private helpers (no later task imports them): `_SEED`, `_MILLION`, `_WIDE`, `_weekdays`,
    `_etf`, `_krx`, `_hand`, `_rate`, `_rule`, `_LOCK`, `_LOCK_PRICES`, `_lock_spec`, `_entered_cash`.

**Plan decisions used:** Q5 (rule dates in the horizon), Q10 (the CHUNK swap; every engine run under `OF.chunk()`),
Q11 (the OKX per-entry cap), Q22 (Asia/Seoul dates of the checks), Q26 (the state machine: exit priority, the
limit-down lock with `d_lock`, the daily-loss reference, one fill per path per check), Q27 (the flat 2x locked exit
charge, the proportional charge clipped at the position value), Q29 (delisting stress), Q41 (band edges, through
`costs.band`); RULINGS O5 ("Test both"), O10 (band rounding per edge), O11 (the cap per entry); RULINGS_ROUND2 R2-2
(the per-edge band, 1,404 at ETF ref 2,005), R2-13 (DRIFT RULE).

Design notes (read before Step 3):
- **One check, in contract 8.4's order.** (1) The price moves inside the session's band: at each open the band is
  `costs.band(previous close, limits[s], terms, on_s)` (p0 for session 0) and it holds until the close. On a new
  Asia/Seoul date, `day_ref` becomes each path's liquidation value at the end of the previous check (W0 before the
  first check) and `day_stop` clears. At an open, every path whose price equals D or U adds one to `edge`. (2) `V =
  cash + units x p x max(0, 1 - ks x chi) - phi_sell' x chi x [units > 0]`, chi = 2 on locked paths. (3) First
  passage on V. A breach `day_ref - V >= daily_loss` sets `day_stop`. (4) Exits, one per path: a queued exit of a
  locked path fills when `p > d_lock`, at chi = 2; then, on the delisting columns, the sale at the first check after
  the first entry; then the new triggers of unlocked longs in priority order target (moonshot, V >= T), take-profit,
  stop, daily loss, rule date (`d_j >= force_exit_from`). A new trigger at a price that is not above the session's D
  is not executable: the path is locked with `d_lock = D` and nothing fills. After the fills, cash >= T is REACHED on
  a moonshot path and cash <= L is AT_FLOOR. (5) Entries also need `~day_stop`, `~delisted`, and a date before both
  `stop_entries_from` and `force_exit_from`. (6) The state at the end of the check feeds the next date's `day_ref`.
- **Why every rule keeps the martingale.** Each fill moves `units x p` into cash and its charges into costs, and the
  delisting sale books `h x units x p` as a loss beside its exit charge, so G = cash + units x p + costs never moves
  at a fill or a sale: X = G_tau - W0 keeps mean 0 inside the band, with locks, the carry and the daily loss (the
  fair kernel stays fair at every band, contract 7.2). Tested in
  `test_gross_value_stays_fair_under_bands_locks_and_the_daily_loss`.
- **Band edges need no code to stay.** At D the kernel's up chance is q = 0, at U it is 1, so a session that opens at
  an edge stays there until the close by construction; the engine only counts such sessions. Because the price can
  never go below D, "a check at D that would exit" is `not p > D`. Unbanded sessions (every non-KRX leg) carry
  D = 0.0 and U = inf as floats, so `p > D` always holds and no lock, no edge and no band arithmetic happen there.
- **Readings of contract 8.4 adopted here (each only stops trading sooner or reports more; Step 4 records them in
  the execution ledger, to be folded into Q26 and contract 8.4):**
  1. A breach stops trading for the rest of the date whether or not the daily loss names the exit (spec 7.3: "A
     breach exits and stops trading for the rest of that day"): a stop fill that is also a breach blocks the
     same-date re-entry.
  2. `worst_gap` also counts a locked stop whose queued fill lands below the stop (the lock records only whether the
     stop named it, `lock_stop`): LIMIT_GAP is "the worst overshoot".
  3. `force_exit_from` blocks entries by itself (`simulate()` always passes `stop_entries_from` on or before it,
     contract 8.5, but the engine does not rely on it).
  4. The delisting sale's exit charge is the normal one at the sale price p (1 - h); at h = 1 there is no sale and no
     charge (Q29). The delisting has priority over the bracket's triggers at that check.
  5. `band_edge_sessions` counts path-sessions (every simulated session of every path, done paths included), and
     `band_edge_share` divides by n x sessions, as `flag.bandedge` reads ("{count} simulated sessions ({share} of
     all)").
  6. A KRX leg is recognised by `costs.band` itself (a finite upper edge at a probe limit), not by a copied list of
     book names: costs keeps its `_KRX_BOOKS` private.
- **Speed.** The value with chi is a scalar multiply while nothing is locked, unbanded sessions skip the lock and
  edge arithmetic, and `day_ref` is computed only when the date changes. In the drafting sandbox Task 11's heaviest
  engine run (20,000 paths, 366 crypto days, bold) took 9.3 s against 8.3 s under Task 9's engine.
- **Hand-made prices.** `_paths` takes the price triples, so the lock, daily-loss, rule-date and delisting tests feed
  exact prices through the private `_hand` helper, which builds each session's band with `costs.band` exactly as
  `_bootstrap_prices` does and asserts every price is inside it. Engine-level tests draw their own paths.

- [ ] **Step 1: Write the failing tests**

  First edit Task 9's `tests/odds_simulate.py` (LF, kept) with the Edit tool, re-reading the file first (DRIFT
  RULE). The price generators now yield `(p, D, U)`, and the band, daily-loss, rule-date and delisting rules are no
  longer refused.

  Edit 1 (anchor: `test_moves_follow_the_rows_and_the_streams`, the line that lists the generated prices).
  Old text:

```python
            got = list(simulate._bootstrap_prices(spec, 500, 0, _SEED))
```

  New text:

```python
            got = [p for p, _, _ in simulate._bootstrap_prices(spec, 500, 0, _SEED)]   # (p, D, U) since Task 10
```

  Edit 2 (anchor: `test_rules_this_engine_does_not_simulate_fail_closed`, from its `def` line to the end of its
  `cases` tuple; the `days = _days()` line and the loop below stay). Old text:

```python
def test_rules_this_engine_does_not_simulate_fail_closed() -> None:
    """A spec that needs a rule not simulated here is refused, never priced without it."""
    days = _days()
    cases = ((_spec(limits=np.full(30, 0.30)), "price bands and limit-down locks"),
             (_spec(daily_loss=5_000.0), "daily loss stop"),
             (_spec(stop_entries_from=days[5]), "rule dates"), (_spec(force_exit_from=days[5]), "rule dates"),
             (_spec(delist_h=0.30), "delisting columns"), (_spec(engine="replay"), "engine 'replay'"),
             (_spec(checks=simulate.checks("CRYPTO", days, True)), "open, then its close"),
             (_garch(checks=simulate.checks("CRYPTO", days, False)), "close only"),
             (_spec(checks=simulate.checks("CRYPTO", (), False), limits=np.zeros(0)), "at least one check"))
```

  New text:

```python
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
```

  Then create `tests/odds_locks.py` (LF, UTF-8, no BOM):

```python
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
    whose KRW 1,000 tick makes the sell rate exceed 100% at low prices, the clipped exit charge keeps it so."""
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
```

- [ ] **Step 2: Run to verify it fails**

  Overlap check with the PowerShell tool (it must print nothing; otherwise wait and re-run):

```powershell
Get-CimInstance Win32_Process -Filter "Name LIKE 'python%'" | Where-Object { $_.CommandLine -match 'run_all' } | Select-Object ProcessId,Name,CommandLine
```

  Then from the repo root in Git Bash:

```bash
.venv/Scripts/python.exe -m tests.odds_acceptance odds_locks/
```

  Expected (numpy 2.3.5): a traceback per test and these 14 lines, then the tail
  `0/14 passed, 14 failed, 0 not run` (exit code 1). Task 9's `_paths` takes price arrays, not `(p, D, U)` triples,
  so every hand-made run fails inside numpy; the engine runs meet Task 9's refusals; `"stake"` does not exist yet:

```text
FAIL odds_locks/test_a_limit_down_lock_persists_and_fills_at_a_flat_2x_exit_charge ValueError: non-broadcastable output operand with shape (1,) doesn't match the broadcast shape (3,1)
FAIL odds_locks/test_a_next_open_above_the_new_d_but_not_above_d_lock_keeps_the_lock ValueError: non-broadcastable output operand with shape (1,) doesn't match the broadcast shape (3,1)
FAIL odds_locks/test_a_stop_fill_below_the_stop_records_worst_gap ValueError: non-broadcastable output operand with shape (1,) doesn't match the broadcast shape (3,1)
FAIL odds_locks/test_auto_off_forces_an_exit_at_its_first_check_and_no_entry_after ValueError: non-broadcastable output operand with shape (1,) doesn't match the broadcast shape (3,1)
FAIL odds_locks/test_band_and_rule_inputs_fail_closed AssertionError: 'one price limit per session' not in 'KRX price bands and limit-down locks are not simulated yet'
FAIL odds_locks/test_cash_never_below_zero_under_2x_stress_plus_the_carry ValueError: KRX price bands and limit-down locks are not simulated yet
FAIL odds_locks/test_delisting_sells_at_p_times_1_minus_h_after_the_first_entry_and_never_reenters ValueError: delisting columns are not simulated yet
FAIL odds_locks/test_effective_until_on_a_non_session_date_exits_at_the_next_check ValueError: non-broadcastable output operand with shape (1,) doesn't match the broadcast shape (3,1)
FAIL odds_locks/test_from_review_by_no_entry_happens_while_the_position_is_kept_and_may_close ValueError: non-broadcastable output operand with shape (1,) doesn't match the broadcast shape (3,1)
FAIL odds_locks/test_gross_value_stays_fair_under_bands_locks_and_the_daily_loss ValueError: KRX price bands and limit-down locks are not simulated yet
FAIL odds_locks/test_krx_prices_stay_in_each_sessions_band_and_edge_sessions_are_counted ValueError: too many values to unpack (expected 3)
FAIL odds_locks/test_locked_at_horizon_is_valued_at_the_locked_price_less_the_carried_charge ValueError: non-broadcastable output operand with shape (1,) doesn't match the broadcast shape (3,1)
FAIL odds_locks/test_the_daily_loss_stops_trading_until_the_next_seoul_date ValueError: setting an array element with a sequence. The requested array has an inhomogeneous shape after 1 dimensions. The detected shape was (3,) + inhomogeneous part.
FAIL odds_locks/test_the_okx_cap_bounds_every_entry KeyError: 'stake'
```

  Overlap check, then:

```bash
.venv/Scripts/python.exe -m tests.odds_acceptance odds_simulate/
```

  Expected: these 2 FAIL lines among 16 PASS lines, then `16/18 passed, 2 failed, 0 not run` (exit code 1):

```text
FAIL odds_simulate/test_moves_follow_the_rows_and_the_streams ValueError: too many values to unpack (expected 3)
FAIL odds_simulate/test_rules_this_engine_does_not_simulate_fail_closed AssertionError: 'any other leg nan' not in 'KRX price bands and limit-down locks are not simulated yet'
```

- [ ] **Step 3: Implement**

  Eight Edits of `core/odds/simulate.py` (LF, kept), in file order, each with the Edit tool after re-reading the
  file (DRIFT RULE). Every old text below is Task 9's text.

  Edit 1 (anchor: the module docstring, the whole of it). Old text:

```python
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
```

  New text:

```python
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
Pure: no clock, no file, no network.
"""
```

  Edit 2 (anchor: `_check_spec`, from its GARCH-t close-only clause to its end; the engine clause, the check count
  and the bootstrap clause above stay). Old text:

```python
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
```

  New text:

```python
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
```

  Edit 3 (anchor: `_bootstrap_prices` and `_garch_prices`, both whole). Old text:

```python
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
```

  New text:

```python
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
```

  Edit 4 (anchor: `_paths`, the whole function, from its `def` line to its `return` dictionary). Old text:

```python
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
```

  New text:

```python
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
```

  Edit 5 (anchor: the `_run_paths` docstring, its first three lines; the rest of it and the body stay). Old text:

```python
    """The state machine of contract 8.4 over n >= 1 paths of chunk `chunk`: the per-path arrays run_column merges,
    plus "p" (terminal price), "entries" and "cash_min", and the bracket sample "br_r", "br_d" (chunk 0, when
    record_brackets). Draws (contract 8.2): the bootstrap's "index" and "sign" streams; GARCH-t's "garch" stream for
```

  New text:

```python
    """The state machine of contract 8.4 over n >= 1 paths of chunk `chunk`: the per-path arrays run_column merges,
    plus "p" (terminal price), "entries", "cash_min", "carried" (queued locked exits filled) and "stake" (the
    largest entry notional, KRW), and the bracket sample "br_r", "br_d" (chunk 0, when record_brackets). Draws
    (contract 8.2): the bootstrap's "index" and "sign" streams (the band draws nothing); GARCH-t's "garch" stream for
```

  Edit 6 (anchor: `_MERGED`). Old text:

```python
_MERGED = ("v", "cost", "x", "outcome", "fp", "entered", "wins", "losses", "unresolved", "gap")
```

  New text:

```python
_MERGED = ("v", "cost", "x", "outcome", "fp", "entered", "wins", "losses", "unresolved", "gap", "locked", "edge")
```

  Edit 7 (anchor: `run_column`, its `locked_at_horizon=` keyword line). Old text:

```python
        locked_at_horizon=0,                                  # no lock without a band (_check_spec)
```

  New text:

```python
        locked_at_horizon=int(a["locked"].sum()),
```

  Edit 8 (anchor: `run_column`, its `band_edge_share=` keyword line). Old text:

```python
        band_edge_share=0.0, band_edge_sessions=0,            # no band (_check_spec)
```

  New text:

```python
        band_edge_share=float(a["edge"].sum()) / (n * (int(spec.checks.session[-1]) + 1)),
        band_edge_sessions=int(a["edge"].sum()),                # path-sessions that opened at a band edge
```

  After the eight Edits, `core/odds/simulate.py` reads exactly as Task 9 left it except at these anchors; its
  imports are unchanged (`math`, `Iterator`, `dataclass`, `date`, `timedelta`, `numpy`, and `costs`, `models`,
  `plan`, `report` from `core.odds`).

- [ ] **Step 4: Run to verify it passes**

  Run the overlap check of Step 2 (PowerShell tool; it must print nothing) before EACH Python command below. All
  run from the repo root in Git Bash.

  Overlap check, then:

```bash
.venv/Scripts/python.exe -m tests.odds_acceptance odds_locks/
```

  Expected: 14 PASS lines, then `14/14 passed, 0 failed, 0 not run` (exit code 0). The tests took about 4 s in the
  drafting sandbox after the runner's import of every suite (budget 12 s, contract 3.4). In
  `test_gross_value_stays_fair_under_bands_locks_and_the_daily_loss` the exact identity X = V + C - W0 catches a
  horizon value or cost that disagrees with the ledger (a locked path's carried charge, a path that moves after
  tau); the 4 SE bound only catches gross drift (4 SE, about KRW 1,500 there, is above the column's mean cost of
  about KRW 1,000). The charges of each fill are pinned exactly by the hand-made tests of this module and of
  `tests/odds_simulate.py`. A FAIL of any of them is a real bug: find it, never widen a bound.

  Overlap check, then Task 9's module, two of whose tests changed and whose engine changed under it:

```bash
.venv/Scripts/python.exe -m tests.odds_acceptance odds_simulate/
```

  Expected: 18 PASS lines, then `18/18 passed, 0 failed, 0 not run` (exit code 0), the count Task 9 recorded.

  Overlap check, then the odds guards (the O1 import allowlist, no clock, no `__main__` block, no file I/O, no
  package re-export, a flat package, the closure holding no data layer), which scan the edited `simulate.py`:

```bash
.venv/Scripts/python.exe -m tests.odds_acceptance odds_guards/
```

  Expected: no FAIL line and the tail Task 1 recorded under "Runs" (exit code 0). A failure names the file and the
  text: fix the core file, never the guard.

  Overlap check, then the compliance guards (raw words and dynamic imports over `core/odds`) and the store (the D14
  code hash covers the edited file):

```bash
.venv/Scripts/python.exe -m tests.compliance_acceptance compliance_guards/
.venv/Scripts/python.exe -m tests.compliance_acceptance compliance_store/
```

  Expected: each ends with `0 failed, 0 not run` and the count recorded under "Runs" (exit code 0).

  Overlap check, then the core-wide scans (Global Constraints: every task that changes `core/`), one at a time with
  the overlap check before each:

```bash
.venv/Scripts/python.exe -m tests.macro_m0_harness
.venv/Scripts/python.exe -m tests.macro_tf_gov
.venv/Scripts/python.exe -m tests.macro_m7_ledger
.venv/Scripts/python.exe -m tests.macro_m8_forward
.venv/Scripts/python.exe -m tests.macro_m6_context
```

  Expected: each prints no FAIL line and ends with `0 failed` and exit code 0, with the passed and not-run counts
  Task 1 recorded under "Runs".

  Overlap check, then the cockpit suite (test_08, test_09, test_16, test_18), followed by restoring the tracked
  results file:

```bash
KIS_APP_KEY='<unset>' KIS_APP_SECRET='<unset>' KIS_ACCOUNT_8='<unset>' KIS_ACCOUNT_PD='<unset>' UPBIT_ACCESS_KEY='<unset>' UPBIT_SECRET_KEY='<unset>' OKX_API_KEY='<unset>' OKX_API_SECRET='<unset>' OKX_API_PASSPHRASE='<unset>' OPENDART_API_KEY='<unset>' KRX_API_KEY='<unset>' FMP_API_KEY='<unset>' ANTHROPIC_API_KEY='<unset>' GS_CLIENT_ID='<unset>' GS_CLIENT_SECRET='<unset>' FINVIZ_API_KEY='<unset>' ALPACA_API_KEY='<unset>' ALPACA_SECRET_KEY='<unset>' FXMACRODATA_API_KEY='<unset>' .venv/Scripts/python.exe tests/run_all.py --suite cockpit; echo "exit $?"; git checkout -- qa/acceptance_results.json
```

  Expected: `0 failed` and the counts Task 1 recorded (exit code 0).

  Then (git only; no overlap check needed):

```bash
git status --short
```

  Expected: exactly ` M core/odds/simulate.py`, ` M tests/odds_simulate.py`, `?? tests/odds_locks.py` and
  `?? docs/superpowers/plans/2026-10-24-odds-engine-execution-ledger.md`.

  In the execution ledger (LF; it stays untracked): append the tails of these runs, one line each, under "Runs", and
  under "Deferred minors" the line "Task 10: an entry at a session's upper band edge U fills in the odds engine
  (spec 7.2 and contract 8.4 lock only exits at D), while the order layer refuses a limit-up entry
  (core/engine/orders.py `limit_up_locked`)." and under "Drift rulings" the line "Task 10 readings of contract 8.4
  (no drift; to be folded into Q26 and 8.4 for spec rev 3.3): a daily-loss breach sets day_stop for every path not
  done, whatever names the exit; worst_gap also counts a queued stop fill below the stop; force_exit_from blocks
  entries by itself; band_edge_sessions counts path-sessions and band_edge_share divides them by n x sessions."

- [ ] **Step 5: Commit**

```bash
git add core/odds/simulate.py tests/odds_simulate.py tests/odds_locks.py
git grep -n -i -E "order_cash|order-cash|place_order|submit_order|tttc0802u|tttc0801u|vttc0802u|private_key|seed_phrase|/v1/orders|/v1/withdraws|/v1/deposits|/api/v3/order|/sapi/v1/capital|/uapi/|r18_research_log|r18_break_log|context_log/|tests\.reference|reference_mode|reference_only" -- core/odds/simulate.py
git grep -n -E "CANO|KIS_ACCOUNT|ACNT_PRDT_CD|0\.4 *(\*|x|×)|(\*|×) *0\.4\b|kish|__import__|import_module|exec_module|load_module|\bexec\b|\beval\b|(^|[^.])\bcompile\(|\bopen\(" -- core/odds/simulate.py
git diff --cached --stat
git diff --cached --stat --ignore-cr-at-eol
```

  Both `git grep` commands print nothing (exit code 1): no banned word, route, 40% literal (a 0.4 on either side of
  `*`, `x` or `×`) or dynamic call (`exec_module`, `load_module` and a bare `compile(` included) in the edited core
  file. The two stat outputs must be identical (all three files are LF). Then:

```bash
git commit -m "feat(odds): path engine part 2: bands, locks, daily loss, rule dates, delisting" -m "Odds plan Task 10 (Q5, Q26, Q27, Q29; O5, O11): KRX bands per session and band-edge sessions, limit-down locks released strictly above d_lock at a flat 2x exit charge, LOCKED_AT_HORIZON, the daily loss on Asia/Seoul dates, the rule dates, the delisting columns and the per-entry stake; the replay engine still fails closed." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

  Afterwards `git status --short` prints only `?? docs/superpowers/plans/2026-10-24-odds-engine-execution-ledger.md`.
