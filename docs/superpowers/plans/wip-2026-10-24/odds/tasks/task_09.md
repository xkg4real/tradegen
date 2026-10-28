### Task 9: The path engine, part 1: moves, entries, exits, ledger and outcomes (`core/odds/simulate.py`)

**Files:**
- Create: `core/odds/report.py` (LF, UTF-8, no BOM; a D14 closure file; holds only `LADDER`, `COST_DOMINATED_SHARE`
  and `ColumnStats` here; Task 12 appends the rest of contract section 10 and no later task edits it)
- Create: `core/odds/simulate.py` (LF, UTF-8, no BOM; a D14 closure file; Tasks 10, 13, 14 and 17 extend it)
- Modify: `tests/odds_fixtures.py` (anchor: the end of the file, after Task 5's last fixture `odds_ctx`; LF, kept)
- Test: `tests/odds_simulate.py` (create; LF; `odds_simulate` is already in `tests.odds_acceptance.MODULES` since
  Task 1; Tasks 10 and 17 edit it)

**Interfaces:**
- Consumes:
  - Task 1: `tests.odds_fixtures.chunk(n=2_000)` (swaps `simulate.CHUNK`, `simulate.DEFAULT_PATHS` (every track to n)
    and `simulate.GARCH_SUB` (to `min(GARCH_SUB, n)`), looked up when entered, restored in `finally`); the runner
    `.venv/Scripts/python.exe -m tests.odds_acceptance <module>/` and its `FAIL <module>/import ...` entry for a test
    module that does not import.
  - Task 5 (`core.odds.plan`): `Bracket(take_profit, stop)`, `Fraction`, `fixed(f)`, `Series` (fields of contract
    5.2), `Provenance(repo_anchor, tree_hash, cryptography)`, `Inputs` (fields of contract 5.2: `now`, `series`,
    `sessions`, `price_limits`, `calendar_sha256`, `calendar_version`, `calendar_md5s`, `calendar_error`, `replay`,
    `comparison_id`, `run_counter`, `comparison_plans`, `comparison_typed`, `plan_runs`, `provenance`),
    `series_md5(symbol, source, dates, open_, close, adjustment, status)`, `check_now(ctx, now)`,
    `check_data(plan, ctx, inputs, market)`, `check_history(plan, inputs, market)`; the fixtures
    `OF.series(*, n, seed, vol, open_gap, ...)` (a synthetic KRW-BTC walk at KRW 50,000,000, md5 filled),
    `OF.plan()` (start 2026-10-23, horizon 10 days) and `OF.odds_ctx()` (date 2026-10-23).
  - Task 6 (`core.odds.costs`): `Terms` (keywords `venue, symbol, book, quote, lot, min_quote, min_krw, phi_buy,
    phi_sell, ladder, ladder_from, quote_krw`), `kappa(terms, prices, on, mult, *, side)`,
    `rule_units(fraction, cash, p, *, terms, on, mult, target, w0, take_profit, stop, sizing, floor, fstar, cap_krw)
    -> (units, at_floor)`, `floor_units(stake, p, lot)`, `r_exit(terms)`, `TABLE_BP`, `COST_STRESS`.
  - Task 7 (`core.odds.models`): `rows(series) -> (m_o, m_i, r)`, `block_length(r)`,
    `indices(rng, n_rows, n_paths, block)`, `kernel(p, m, d_edge, u_edge, u, theta=0.0)`,
    `stream(seed, chunk, name, *extra)`.
  - Task 8 (`core.odds.models`): `GarchParams` (built by keyword in the tests: `dist, omega, alpha, beta, nu,
    mean_daily, n_obs, cond_vol_last, converged, at_bound`) and `simulate_garch(fit, *, n_paths, horizon, seed) ->
    (ret, sigma)`, whose copied first line `rng = np.random.default_rng(seed)` passes the Generator of `stream(...)`
    through unchanged.
- Produces (Tasks 10, 11, 13, 14 and 17 rely on these exact names):
  - `core.odds.report`: `LADDER = (1.10, 1.25, 2.0, 10.0)`, `COST_DOMINATED_SHARE = 0.10`, and `ColumnStats` with
    the fields and order of contract 10.1 (`brackets` is `field(default=None, compare=False, repr=False)`). Task 12
    appends everything else of contract section 10 below `ColumnStats` and may widen the import block.
    Contract 10.1 amendment (recorded in the ledger, Step 4): two columns compare equal only through
    `dataclasses.replace(col, brackets=None, x_range=0.0 if math.isnan(col.x_range) else col.x_range)`, never
    through `dataclasses.replace(col, brackets=None)` alone: `x_range` is nan in every column `run_column` builds
    (Task 14 sets it on bootstrap columns afterwards; GARCH-t and delisting columns keep nan), and nan != nan. Task
    13's `_strip` (`tests/odds_pipeline.py`) must use this idiom from its creation.
  - `core.odds.simulate`: the constants of contract 8.1 (`CHUNK`, `DEFAULT_PATHS`, `GARCH_SUB`, `REFIT_B`,
    `TILT_PILOT`, `TILT_BOUND`, `TILT_ITER`, `TILT_TOL`, `TILT_FAIL`, `BRACKET_SAMPLE`, `MEMBERS`); `Checks`;
    `checks(market, sessions, close_only) -> Checks`; `PathSpec` (contract 8.2, every field);
    `run_column(spec, *, n, seed, key, member, scenario) -> report.ColumnStats`;
    `_run_paths(spec, *, n, chunk, seed) -> dict[str, np.ndarray]` with the per-path keys `"p"` (terminal price),
    `"v"` (terminal liquidation value), `"cost"` (costs booked plus the liquidation charge of an open position),
    `"x"` (X = G_tau - W0), `"outcome"` (int8: 0 running, 1 reached, 2 at_floor), `"fp"` (first passage),
    `"entered"`, `"entries"` (entry fills), `"wins"` (take-profit fills), `"losses"` (stop fills), `"unresolved"`
    (bracket entries closed otherwise or open at the horizon; 0 for buy-and-hold), `"gap"` (largest stop overshoot
    over the entry price), `"cash_min"` (lowest cash after any fill), and the bracket sample `"br_r"`, `"br_d"`
    (chunk 0, only with `record_brackets`; variable length).
  - Private helpers later tasks edit by name: `_check_spec(spec)` (one `raise ValueError` clause per rule not
    simulated yet; Task 10 deletes the band, daily-loss, rule-date and delisting clauses as it builds each rule, Task
    17 routes engine `"replay"` around it (dispatchers in front of `run_column` and `_run_paths`) and leaves the
    clause unchanged), `_bootstrap_prices(spec, n, chunk, seed)` (the 8.3 move with D = 0,
    U = inf; Task 10 adds the band), `_garch_prices(p0, ret)`, `_paths(spec, prices, n, record)` (the 8.4 state
    machine; Task 10 adds locks, the daily loss, rule dates and delisting), `_MERGED` (the per-path keys run_column
    folds), `_CLOSE_DAYS` (Q22's close-date shift per market).
  - `tests/odds_fixtures.py`: `inputs(plan, series, **changes) -> plan.Inputs` and
    `even_rows(m: float, n: int = 400) -> plan.Series` (contract 3.2).

**Plan decisions used:** Q10 (the CHUNK swap: every simulation runs under `OF.chunk()`, and the "multiple of CHUNK"
refusal is also tested at the real 200,000), Q11 (the OKX per-entry cap reaches `costs.rule_units` as `cap_krw`),
Q22 (check points and their Asia/Seoul dates), Q26 (the state machine: exit priority, one fill per path per check,
re-entry only for bracket legs and only at a later check, no entry at the last check, AT_FLOOR, REACHED, first
passage), Q27 (the cost ledger: kappa per side and fill, phi, the stress multiplier, the exit charge clipped at the
position value), Q28 (stakes, lot rounding and the minimum through `costs.rule_units`), Q30 (the tilt `theta` reaches
the kernel), Q31 (GARCH-t sub-chunks of `GARCH_SUB` paths and the `REFIT_B` refit groups), Q32 (X = G_tau - W0 and
`g_se`), Q12 and Q34 (named streams; plan fields never enter a draw). RULINGS O10 (CHUNK swap), O11.

Design notes (read before Step 3):
- **What is simulated here and what is refused.** This task builds contract 8.2-8.4 for the bootstrap and GARCH-t
  engines without the session-structure rules: no KRX band (D = 0, U = inf, so no exit is ever locked), no daily loss
  stop, no rule dates, no delisting column, no replay engine. A `PathSpec` that needs one of them is refused by
  `_check_spec` with a ValueError (any finite entry in `limits`, a finite `daily_loss`, a set `stop_entries_from` or
  `force_exit_from`, a set `delist_h`, an engine other than bootstrap or garch), so no column is ever priced without
  a rule it needs. Task 10 deletes each clause when it builds that rule; Task 17 adds the replay engine. Because no
  band exists here, `locked_at_horizon`, `band_edge_share` and `band_edge_sessions` are exactly 0. A spec whose checks
  do not alternate open, close (bootstrap) or are not all closes (GARCH-t) is refused too.
- **One check, in contract 8.4's order.** (1) the price moves (8.3); (2) `ks = costs.kappa(..., side="sell")` and
  `V = cash + units x p x max(0, 1 - ks) - phi_sell' x [units > 0]` (chi = 1 here); (3) first passage on V: the first
  check with V >= T sets `fp` and X; (4) exits on held paths, in priority order target (moonshot and V >= T),
  take-profit (p >= tp), stop (p <= sl), each filling at p with `units x p x min(1, ks) + phi_sell'`; after the fills,
  cash >= T on a moonshot path is REACHED and cash <= L is AT_FLOOR, both done; (5) entries on flat paths that did not
  fill this check, not at the last check, bracket legs or a buy-and-hold leg that never entered: `costs.rule_units`
  at p with W = cash; its `at_floor` rows are AT_FLOOR and done; a rule stake below the minimum is no bet and the path
  stays flat (it tries again next check). The buy-and-hold half of that clause cannot be reached in part 1: without a
  bracket the only exit is the moonshot target, and that fill always ends the path REACHED (the cash after it equals
  V >= T). Task 10's daily-loss exit is the first after which it matters, so the test is handed to Task 10.
  Entries charge `units x p x kb + phi_buy'` with
  `kb = costs.kappa(..., side="buy")`. Primes are `x mult`; `mult` is passed into `kappa` once.
- **Every fill leaves the gross value G = cash + units x p + costs unchanged**, so G moves only with the price and,
  with no edge, is a martingale: X = G_tau - W0 (tau = first passage, AT_FLOOR, or the horizon) has mean 0 under every
  martingale model, costs or not. The terminal cost adds the liquidation charge of an open position, so
  V_term + cost_term = G_term, and `g_se = std(V_term + cost_term, ddof 1) / sqrt(n)`.
- **`x_range` is nan in this task, for every column.** Section 10.3's range is computed by `report.hidden_range`,
  which Task 12 adds. Task 14's `_column` wrapper sets it on bootstrap columns (through `_hidden_range`, from the spec
  alone); `run_column` itself keeps nan, which reads as "HIDDEN_EDGE unavailable" (never a claim the core did not
  check). Contract 10.3 says `run_column` stores the value, so this is a departure: recorded under "Deferred minors"
  in Step 4 for the "For spec rev 3.3" list.
- **ColumnStats equality.** `brackets` holds arrays, so it is `compare=False, repr=False` (and out of the hash).
  Python 3.13's generated `__eq__` returns True for the same object and otherwise compares field by field, so
  nan != nan: a column whose `x_range` is nan never equals another column object, even an identical one (`col == col`
  is still True through the identity shortcut). Every comparison of two columns therefore uses
  `dataclasses.replace(col, brackets=None, x_range=0.0 if math.isnan(col.x_range) else col.x_range)`, which keeps a
  finite range (the contract 10.1 amendment under Produces); the test pins both. `report.py`'s comment on `brackets`
  names the same idiom; Task 12's Step 3d sha256 is computed from this task's `report.py` text, comment included.
- **Rules no part-1 test can fail.** Three choices of contract 8.4 give the same paths as their mistakes on every leg
  this task can run: the buy-and-hold no-re-entry clause (above); the cost side (`side="buy"` at entries, `"sell"` at
  V and exits), because the two rates differ only on a KRX stock sell and a KRX leg needs Task 10's band; and the
  cost date (`checks.on[j]`, not `checks.seoul[j]`), because the two dates differ only on US and crypto closes,
  whose rates do not depend on the date once `costs.check_validity` has passed the horizon. The first two are
  handed to Task 10, whose legs reach them; the third has no observable effect. One more choice is left untested on
  purpose: the clip of a mid-path V at a sell rate above 100% changes first passage only when cash alone is within
  phi_sell of T beside a position worth nothing (the clip of the horizon's V is tested). Every other branch of
  `_paths` has a test that fails without it, the equality cases included (`p >= tp`, `p <= sl`, `cash <= L` and the
  rungs' `>=`, on prices that exactly double or halve: `np.exp(np.log(2.0))` is 2.0 in floating point).
- **Common random numbers.** The price of a path depends only on the seed, the chunk, the rows (or fits) and the
  block, never on the plan, the sizing or the cost scenario, because each stream is drawn at every check whatever
  the state: the bootstrap's `"index"` stream steps once per session (at its open) and its `"sign"` stream once per
  check; GARCH-t draws `"garch"` per slice of `GARCH_SUB` paths (spawn key `start // GARCH_SUB`, the last slice
  holding the rest) or `"refit"` g for group g of `n // REFIT_B` paths.
- **run_column** runs `_run_paths(spec, n=CHUNK, chunk=c, seed=seed)` for each chunk and keeps only the ten per-path
  arrays of `_MERGED` (about 12 MB per 200,000-path chunk), plus chunk 0's bracket sample cut to `BRACKET_SAMPLE`.
  `CHUNK` and `BRACKET_SAMPLE` are read at call time, so the test swaps take effect.
- **`even_rows(m)`** alternates two prices, so every open is the previous close (m_o = 0 exactly) and every close is
  the other price. `|ln(close/open)|` equals m only to rounding: a naive walk at m = 0.5 lands one ulp BELOW 0.5 on
  half its rows, and a take-profit of exactly e^0.5 - 1 would then miss every other up move. The fixture nudges the
  upper price up until `exp(m_i) >= exp(m)` and `exp(-m_i) <= exp(-m)` on every row, so a bracket at e^m - 1 and
  1 - e^-m fills at every close (Task 11's even-money engine test relies on this). This task's own tests use
  brackets a hair inside (`_even(m)`, 1e-9) on rows built directly.

- [ ] **Step 1: Write the failing tests**

  First append the engine fixtures to `tests/odds_fixtures.py` (anchor: `odds_ctx`, Task 5's last fixture, whose
  last line is the last line of the file; LF). Re-read the file, then one Edit-tool replacement:
  - `old_string`: the single line `    return F.ctx(**fields)` (four spaces, then `return F.ctx(**fields)`). It occurs
    once in the file Task 5 leaves, as its last line.
  - `new_string`: that same line, then two empty lines, then the block below exactly, from its first `# ----` line
    to the last line of `even_rows`. The file then ends with that last line and one newline.

  DRIFT RULE: if that line is no longer the file's last line, or not unique, use the actual last line of `odds_ctx`
  (with the lines above it until it is unique) as `old_string`, keep the same tail in `new_string`, and record a
  ruling. The block imports what it needs inside each function, like the Task 5 block above it, and defines no
  `test_*` name.

```python
# --------------------------------------------------------------------------- #
# Task 9: engine inputs (contract 3.2). Like the blocks above, each function imports what it needs inside.
# --------------------------------------------------------------------------- #
def inputs(plan, series, **changes):
    """plan.Inputs for `plan` on `series`: now 2026-10-23 09:00 KST, the crypto sessions of the horizon (every date
    of [plan.start, plan.start + plan.horizon_days)), no calendar, comparison "c000001" with run counter 1, K 1,
    J 0, R 1, and the provenance ("git:" + "0" * 40, "f" * 64, "49.0.0"). Any field can be changed by keyword."""
    import datetime

    from core.compliance import model
    from core.odds import plan as P
    fields = dict(now=datetime.datetime(2026, 10, 23, 9, 0, tzinfo=model.KST), series=series,
                  sessions=tuple((plan.start + datetime.timedelta(days=i)).isoformat()
                                 for i in range(plan.horizon_days)),
                  price_limits=(), calendar_sha256="", calendar_version="", calendar_md5s=(), calendar_error="",
                  replay=None, comparison_id="c000001", run_counter=1, comparison_plans=1, comparison_typed=0,
                  plan_runs=1, provenance=P.Provenance(repo_anchor="git:" + "0" * 40, tree_hash="f" * 64,
                                                      cryptography="49.0.0"))
    fields.update(changes)
    return P.Inputs(**fields)


def even_rows(m: float, n: int = 400):
    """n daily KRW-BTC bars ending 2026-10-22 that alternate between two prices: each open is the previous close
    and each close is the other price, so every overnight move m_o is 0 and every intraday move m_i is m, or a few
    ulps above it. The upper price is nudged up until exp(m_i) >= exp(m) and exp(-m_i) <= exp(-m) on every row, so
    a bracket with take_profit e^m - 1 and stop 1 - e^-m fills at every close: an even-money bet."""
    import datetime
    import math

    import numpy as np

    from core.odds import plan as P
    lo = 50_000_000.0
    hi = lo * math.exp(m)
    while True:
        o = np.array([lo if i % 2 == 0 else hi for i in range(n)])
        c = np.array([hi if i % 2 == 0 else lo for i in range(n)])
        m_i = np.abs(np.log(c[1:] / o[1:]))
        if (np.exp(m_i) >= math.exp(m)).all() and (np.exp(-m_i) <= math.exp(-m)).all():
            break
        hi = math.nextafter(hi, math.inf)
    first = datetime.date(2026, 10, 22) - datetime.timedelta(days=n - 1)
    dates = tuple((first + datetime.timedelta(days=i)).isoformat() for i in range(n))
    opens, closes = tuple(float(x) for x in o), tuple(float(x) for x in c)
    return P.Series(symbol="KRW-BTC", source="UPBIT", dates=dates, open=opens, close=closes, adjustment="",
                    status="final", md5=P.series_md5("KRW-BTC", "UPBIT", dates, opens, closes, "", "final"))
```

  Then create `tests/odds_simulate.py` (LF):

```python
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
            got = list(simulate._bootstrap_prices(spec, 500, 0, _SEED))
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
    """A spec that needs a rule not simulated here is refused, never priced without it."""
    days = _days()
    cases = ((_spec(limits=np.full(30, 0.30)), "price bands and limit-down locks"),
             (_spec(daily_loss=5_000.0), "daily loss stop"),
             (_spec(stop_entries_from=days[5]), "rule dates"), (_spec(force_exit_from=days[5]), "rule dates"),
             (_spec(delist_h=0.30), "delisting columns"), (_spec(engine="replay"), "engine 'replay'"),
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
```

- [ ] **Step 2: Run to verify it fails**

  Overlap check with the PowerShell tool (it must print nothing; otherwise wait and re-run):

```powershell
Get-CimInstance Win32_Process -Filter "Name LIKE 'python%'" | Where-Object { $_.CommandLine -match 'run_all' } | Select-Object ProcessId,Name,CommandLine
```

  Then from the repo root in Git Bash:

```bash
.venv/Scripts/python.exe -m tests.odds_acceptance odds_simulate/
```

  Expected: a traceback, then the one entry
  `FAIL odds_simulate/import ImportError: cannot import name 'report' from 'core.odds' (C:\Users\whydi\OneDrive\Desktop\TRADEGEN\core\odds\__init__.py)`
  and the tail `0/1 passed, 1 failed, 0 not run` (exit code 1): `core/odds/report.py` and `core/odds/simulate.py`
  do not exist yet.

- [ ] **Step 3: Implement**

  Create `core/odds/report.py` (LF, UTF-8, no BOM). Task 12 appends below `ColumnStats`:

```python
"""The odds report (spec 7.5; odds plan contract section 10). This first part holds what the path engine fills: the
outcome ladder, the cost share of the COST_DOMINATED flag and the statistics of one simulated column. simulate
imports report, never the reverse. Pure: no clock, no file, no network."""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

LADDER = (1.10, 1.25, 2.0, 10.0)                  # x W0; then the target (simulate reads report.LADDER)
COST_DOMINATED_SHARE = 0.10                       # Q43 (simulate reads report.COST_DOMINATED_SHARE)


@dataclass(frozen=True, kw_only=True)
class ColumnStats:
    """One column: a member's model under one cost scenario, n paths (contract 10.1). Counts are paths; values are
    KRW. `brackets` holds arrays, so it stays out of ==, repr and the hash."""
    key: str
    member: str
    scenario: str
    n: int
    reached: int                  # first passage: liquidation value >= T at some check (the ceiling's quantity)
    reached_outcome: int          # moonshot REACHED outcomes (<= reached: a locked exit can miss T); 0 for compounding
    ended_at_or_above: int        # terminal value >= T
    at_floor: int
    running: int
    locked_at_horizon: int
    rungs: tuple[int, ...]        # counts of terminal value >= LADDER[i] x W0, then >= T
    median: float
    p5: float
    mean: float
    mean_se: float                # std(V_term, ddof 1) / sqrt(n)
    mean_cost: float
    g_se: float                   # std(V_term + cost_term, ddof 1) / sqrt(n): the SE of the average-line statistic
    kept_lo: float | None         # min and max terminal value of AT_FLOOR paths (None without one)
    kept_hi: float | None
    x_mean: float                 # HIDDEN_EDGE sample X = G_tau - W0 (ddof 1 variance) and its range R (section
    x_var: float                  # 10.3, fixed before the run; nan when no finite range was computed, inf unbounded)
    x_range: float
    wins: int                     # take-profit fills
    losses: int                   # stop fills
    unresolved: int               # brackets closed otherwise or still open at the horizon
    brackets: tuple[np.ndarray, np.ndarray] | None = field(default=None, compare=False, repr=False)
    # (r, d) of up to BRACKET_SAMPLE brackets of chunk 0; compare two columns through dataclasses.replace(col,
    # brackets=None, x_range=0.0 if math.isnan(col.x_range) else col.x_range) (contract 10.1 as Task 9 amends it)
    band_edge_share: float
    band_edge_sessions: int       # simulated sessions that opened at a band edge
    worst_gap: float              # the largest (stop - fill) / entry of a stop fill below its stop
    trades: int                   # paths with an entry fill
```

  Create `core/odds/simulate.py` (LF, UTF-8, no BOM):

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
```

- [ ] **Step 4: Run to verify it passes**

  Run the overlap check of Step 2 (PowerShell tool; it must print nothing) before EACH Python command below. All
  run from the repo root in Git Bash.

  Overlap check, then:

```bash
.venv/Scripts/python.exe -m tests.odds_acceptance odds_simulate/
```

  Expected: 18 PASS lines, then `18/18 passed, 0 failed, 0 not run` (exit code 0). The tests take about 1 s after
  the runner's import of every suite (budget 18 s, contract 3.4), so a much slower run is worth a look. A FAIL of
  `test_no_edge_mean_payoff_is_zero_before_costs` on the 4 SE bound is a real bias in the ledger or the moves (the
  test has no tolerance to raise): find it, never widen the bound.

  Overlap check, then the plan module, whose fixture file just grew:

```bash
.venv/Scripts/python.exe -m tests.odds_acceptance odds_plan/
```

  Expected: the same tail Task 5 recorded under "Runs" in the execution ledger, `0 failed` (exit code 0).

  Overlap check, then the odds guards, which now scan `simulate.py` and `report.py` (the O1 import allowlist, no
  clock, no `__main__` block, no file I/O, no package re-export, a flat package, the closure holding no data layer):

```bash
.venv/Scripts/python.exe -m tests.odds_acceptance odds_guards/
```

  Expected: no FAIL line and the tail Task 1 recorded under "Runs" (exit code 0). A failure names the file and the
  text: fix the core file, never the guard.

  Overlap check, then the compliance guards (raw words and dynamic imports over `core/odds`):

```bash
.venv/Scripts/python.exe -m tests.compliance_acceptance compliance_guards/
```

  Overlap check again, then the store (the D14 code hash now includes the two new files):

```bash
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

  Expected: exactly `?? core/odds/report.py`, `?? core/odds/simulate.py`, ` M tests/odds_fixtures.py`,
  `?? tests/odds_simulate.py` and `?? docs/superpowers/plans/2026-10-24-odds-engine-execution-ledger.md`.

  In the execution ledger (LF; it stays untracked): append the tails of these runs, one line each, under "Runs",
  and under "Deferred minors" these three lines:
  - "Task 9: run_column stores x_range = nan for every column; Task 14's `_column` sets x_range from
    report.hidden_range (through `_hidden_range`) for bootstrap columns, and run_column itself keeps nan. Contract
    10.3 says run_column stores it: a departure for the 'For spec rev 3.3' list."
  - "Task 9: contract 10.1 amended: two ColumnStats compare through dataclasses.replace(col, brackets=None,
    x_range=0.0 if math.isnan(col.x_range) else col.x_range); a nan x_range makes two distinct columns unequal
    (Python 3.13 compares field by field). report.py's `brackets` comment names the amended idiom, and Task 13's
    `_strip` uses it."
  - "Task 9: no part-1 test can fail on the buy-and-hold no-re-entry clause (its only exit is the moonshot target,
    which ends it REACHED), on the cost side (buy and sell rates differ only on a KRX stock sell) or on the cost
    date (checks.on vs checks.seoul: no rate depends on it). Handed to Task 10: the re-entry clause after a
    daily-loss exit, and the cost side on a KRX stock leg. The mid-path V clip at a sell rate above 100% is left
    untested."

- [ ] **Step 5: Commit**

```bash
git add core/odds/report.py core/odds/simulate.py tests/odds_fixtures.py tests/odds_simulate.py
git grep -n -i -E "order_cash|order-cash|place_order|submit_order|tttc0802u|tttc0801u|vttc0802u|private_key|seed_phrase|/v1/orders|/v1/withdraws|/v1/deposits|/api/v3/order|/sapi/v1/capital|/uapi/|r18_research_log|r18_break_log|context_log/|tests\.reference|reference_mode|reference_only" -- core/odds/simulate.py core/odds/report.py
git grep -n -E "CANO|KIS_ACCOUNT|ACNT_PRDT_CD|0\.4 *[*x]|kish|__import__|import_module|\bexec\b|\beval\b|\bopen\(" -- core/odds/simulate.py core/odds/report.py
git diff --cached --stat
git diff --cached --stat --ignore-cr-at-eol
```

  Both `git grep` commands print nothing (exit code 1; they run after the `git add` because `git grep` does not
  search untracked files): no banned word, route, 40% literal or dynamic call in the new core files. The two stat
  outputs must be identical (all four files are LF). Then:

```bash
git commit -m "feat(odds): path engine part 1: moves, entries, exits, ledger and outcomes" -m "Odds plan Task 9 (Q22, Q26-Q28): checks, PathSpec, run_column and _run_paths for the bootstrap and GARCH-t engines, and report.ColumnStats; bands, locks, the daily loss, rule dates and delisting fail closed until Task 10." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

  Afterwards `git status --short` prints only `?? docs/superpowers/plans/2026-10-24-odds-engine-execution-ledger.md`.
