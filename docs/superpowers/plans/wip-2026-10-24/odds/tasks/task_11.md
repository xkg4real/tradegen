### Task 11: References: ceiling, structural maximum, bracket reference, brackets needed, bold_even (`core/odds/bold.py`)

**Files:**
- Create: `core/odds/bold.py` (LF, UTF-8, no BOM; a D14 closure file through the `core/odds/*.py` glob seed)
- Create: `tests/odds_bold.py` (LF, UTF-8, no BOM; `odds_bold` is already in `tests/odds_acceptance.MODULES`, Task 1)
- Test: `tests/odds_bold.py`

This task edits no tracked file, so it has no old-text/new-text pair. The DRIFT RULE applies only to the names it
consumes: every one comes from Tasks 1 and 5 to 10 of this plan, or from `tests/macro_m1_calendars.py` and
`core/calendars/{clocks,regime}.py`, which no earlier plan changes (followup CONTRACT section 12). Before Step 1,
re-read the names listed under "Consumes" in the files that define them; if one differs (an earlier task of this plan
renamed or reshaped it), use the current name or shape in the test, keep that task's behaviour, and record a one-line
ruling under "Drift rulings" in the execution ledger.

**Interfaces:**
- Consumes:
  - Task 1 (`tests/odds_fixtures.py`): `chunk(n: int = 2_000)`, the context manager that swaps
    `simulate.CHUNK = n`, `simulate.DEFAULT_PATHS` and `simulate.GARCH_SUB` with save/restore.
  - Task 5 (`core.odds.plan`): `Bracket(take_profit: float, stop: float)`; `bold() -> Fraction`; `Series` (its `close`
    is a tuple of floats in KRW).
  - Task 6 (`core.odds.costs`): `Terms(venue, symbol, book, quote, lot, min_quote, min_krw, phi_buy, phi_sell, ladder,
    ladder_from, quote_krw)` (frozen, kw_only); the dict `TABLE_BP`, read at call time by `side_bp` for a book with
    no ladder (`crypto_venue` is 10.0); `kappa(terms, prices, on, mult, *, side) -> np.ndarray`;
    `rule_units(fraction, cash, p, *, terms, on, mult, target, w0, take_profit, stop, sizing, floor, fstar, cap_krw)
    -> (units, at_floor)` with the bold rule of contract 6.5 (`c_w = take_profit - kw * (2 + take_profit)`,
    `s = min(ceil_units(max(s_reach, m)) * p, floor_units(a) * p)`, no bet once `cash >= target`).
  - Task 7 (`core.odds.models`): `rows(series) -> (m_o, m_i, r)`.
  - Task 9 (`core.odds.simulate`, `core.odds.report`, `tests/odds_fixtures.py`): `PathSpec` with every field of
    contract 8.2; `checks(market, sessions, close_only) -> Checks`;
    `run_column(spec, *, n, seed, key, member, scenario) -> report.ColumnStats`; `BRACKET_SAMPLE = 50_000`;
    `ColumnStats.n`, `.reached`, `.reached_outcome`, `.ended_at_or_above`, `.at_floor`, `.running`, `.rungs`
    (counts of terminal value >= `LADDER[i] * W0` for `LADDER = (1.10, 1.25, 2.0, 10.0)`, then >= T), `.median`,
    `.p5`, `.mean`, `.mean_cost`; `OF.even_rows(m: float, n: int = 400) -> plan.Series` (each open equals the
    previous close and every |ln(close/open)| is m or a few ulps above it: the upper price is nudged until
    `exp(m_i) >= exp(m)` and `exp(-m_i) <= exp(-m)` on every row, so a bracket with take_profit `e^m - 1` and stop
    `1 - e^-m` fills at every close).
  - Task 10: the `PathSpec` fields `daily_loss`, `cap_krw`, `stop_entries_from`, `force_exit_from`, `delist_h`
    behave as contract 8.4 says; here they are inert (KRW 1e9, None, None, None, None).
  - Repo, unchanged: `tests.macro_m1_calendars.fixture_set()` (the signed fixture calendar set, KRX coverage
    1995-01-01..2027-12-31, price limit 0.30 from 2015-06-15); `core.calendars.clocks.sessions_between(market, lo, hi,
    *, cal)` (both ends included); `core.calendars.regime.regime_tags(market, d, *, cal)["price_limit"]`.
- Produces (`core/odds/bold.py`; Tasks 12 to 14 rely on these exact names and behaviours):
  - `ceiling(w0: float, l_min: float, target: float) -> float`: `(w0 - l_min) / (target - l_min)`, computed with
    `fractions.Fraction` from the float inputs and rounded once (so `ceiling(42_000.0, 0.0, 42_000_000.0) == 0.001`
    and `ceiling(42_000.0, 21_000.0, 42_000_000.0) == 1 / 1999`). ValueError (text holds `l_min < w0 < target`)
    unless every argument is a finite real (bool excluded) and `l_min < w0 < target`. The pipeline calls it only after
    STUCK_AT_START, where `w0 > l_min` holds; a refusal report must not call it (it has no ceiling to print).
  - `ceiling_one_in(w0: float, l_min: float, target: float) -> int`: `floor((target - l_min) / (w0 - l_min))`
    computed exactly (1,000 and 1,999 for the spec's two cases); the same ValueError. Its consumer is the card's
    "1 in N" of a ceiling below 1% (contract 9). Task 12's `_ceiling_text` prints this exact N on every card (Task 12
    D2); `fmt_ceiling` keeps contract 10.2's floor(1/c). Nothing in this task depends on it.
  - `structural_max(limits: tuple[float, ...]) -> float`: `(1 + l1)/(1 - l1) * prod(1 + li, i >= 2)` (Q44); ValueError
    (text holds `one price limit in (0, 1)`) for an empty sequence or a limit that is not a finite real in (0, 1).
  - `brackets_needed(p: float, p0: float) -> float`: `float(ceil(((1.645 sqrt(p0 (1 - p0)) + 0.842 sqrt(p (1 - p))) /
    |p - p0|) ** 2))`, `math.inf` when `p == p0`; ValueError (text holds `win rates in [0, 1]`) outside [0, 1].
  - `bold_even(x: fractions.Fraction, p: fractions.Fraction) -> fractions.Fraction`: exact; TypeError (text holds
    `fractions.Fraction`) unless both are `int` or `fractions.Fraction` (bool and float refused); ValueError (text
    holds `0 <= x <= 1`) outside [0, 1].
  - `bracket_reference(r, d, *, w0, l_min, target, n_checks, kappa, phi_buy, phi_sell, r_exit) -> float`: contract
    9.1 exactly; ValueError with `equal-length` (bad arrays, `d < 1`), `whole number of checks` (`n_checks` not an
    integral number >= 0, bool refused) or `l_min < target` (a non-finite scalar, `l_min >= target`, `kappa < 0` or a
    negative charge) in its text. Measured 2026-10-27 in the drafting sandbox, machine- and load-dependent: 0.2 s
    (idle) to 0.6 s (under load from parallel jobs) for 60 checks on 50,000 brackets with four durations, and 3.8 to
    12 ms a check in general (a 366-day crypto horizon, 732 checks, 2.8 to 8.9 s). The only timing assert is the
    test's 3 s for 60 checks.
  - Private names (contract section 0: names not in the contract are private): `_Z_ALPHA = 1.645`,
    `_Z_POWER = 0.842`, `_R_BINS = 32`, `_D_BINS = 4`, `_NODES = 129`, `_STAKES = 16`, `_HALF = fractions.Fraction(1,
    2)`, `_real(*values) -> bool`, `_span(w0, l_min, target) -> tuple[fractions.Fraction, fractions.Fraction]`,
    `_bins(v, k) -> tuple[np.ndarray, list[np.ndarray]]`.
  - `bold.py` imports only `fractions`, `math`, `numbers` and `numpy` (the O1 allowlist); it reads no clock, opens no
    file and never imports `core.odds.plan` (Q4: the module `fractions` is imported whole and written
    `fractions.Fraction`, so it never meets the plan type `plan.Fraction`).

**Plan decisions used:** Q32 (L_min = L under floor-protected sizing, else 0; the ceiling is an upper bound, so its
"1 in N" rounds N down), Q33 (the bracket reference is a duration-aware dynamic programme, an estimate that only feeds
the amber ABOVE_ESTIMATED_REFERENCE), Q44 (the structural cap formula with each session's dated limit), Q42 (purity),
Q4 (`fractions` imported as a module), Q28 (bold's reaching stake, used by the simulated checks), Q26 and Q27 (the
engine's re-entry, REACHED and ledger, used by the engine checks), Q40 (the `OF.chunk` swap). RULINGS_ROUND3 O3-9
(the engine-run assertions, as amended below; T11-1 to T11-3).

**Departures from TASKS Task 11 and contract 3.4 (ruled: RULINGS_ROUND3 O3-9).** O3-9 rules that the engine-run
assertions are the drafter's, because a lot of 1e-12 BTC with a KRW 0 minimum never reaches the floor, and that
CONTRACT 16.1 and TASKS Task 11 follow. As first written, O3-9 lists an older draft's assertions
(`rungs[0] - reached <= 2`, and ISSUES_round1 adds a second short run: T = 50,000, 30 days, 2,000 paths). The
controller amends O3-9's list to the one below: the rungs equality and the excess bound replace
`rungs[0] - reached <= 2`, there is no second run, and T11-2 and T11-3 are added. Before Step 1, read O3-9 in the
rulings file. If it still lists `rungs[0] - reached <= 2` or a second run, stop for a ruling, because a rulings file
wins over a task text. Where TASKS Task 11 or CONTRACT 16.1 still reads "leaves no path running", "some path ends
within KRW 1 of T" or `venues_with(...)`, O3-9 and this list win. None of these departures changes a produced name.
`test_engine_bold_play_meets_the_ceiling_and_lands_on_the_target` makes one run and asserts exactly these:
- the fixture rows: `max(m_o) == 0.0` and every `m_i` within 1e-12 of 0.5;
- `col.n == 20_000` and `k = col.reached == col.reached_outcome == col.ended_at_or_above`;
- `col.rungs == (k, k, k, 0, k)`: every path at or above 1.1 W0 is at T = 8 W0, and none reaches 10 W0. This gives
  `rungs[0] - reached == 0`, stronger than O3-9's first `<= 2`;
- the 99.9% Clopper-Pearson interval of k in 20,000 contains `bold.ceiling(W0, L, T)` = 1/15;
- `L <= col.p5 <= col.median <= L + 1.0`;
- `col.mean_cost == 0.0` and `-1e-6 <= excess <= 0.01`, with `excess = col.mean - (k T + (n - k) L) / n`;
- `col.at_floor + col.running + col.reached_outcome == col.n`.

The figures below come from the drafting sandbox, which assembles Tasks 5 to 9 as planned and removes only the
daily-loss clause of `_check_spec` to stand in for Task 10.
- **T11-1: the test does not assert "leaves no path running"** (TASKS Task 11; REVISIONS M7). That bullet cannot hold
  with TASKS' own fixture. With lot 1e-12 BTC and a KRW 0 minimum, the minimum stake is one lot. A path that lost
  never has less than that left to stake, so it never becomes AT_FLOOR (`a < m` in `rule_units`); it stays RUNNING a
  fraction of a won above L. Measured over 366 days and 20,000 paths: 0 AT_FLOOR, 18,692 RUNNING and 1,308 REACHED,
  with the highest RUNNING value at KRW 21,000.95. The test keeps contract 16.1's "the engine test runs with no
  minimum". In place of the bullet it asserts the mean-excess bound explained in its docstring, which is stronger
  than the bullet's intent: every path that missed T ends within KRW 200 of L, and the winners land on average under
  KRW 0.16 past T. That bound also proves
  TASKS' "some path ends within KRW 1 of T" inside the TASKS run itself, so the test needs no second run.
  The alternative is a KRW 1 minimum (`min_quote = min_krw = 1.0`). It makes the bullet hold literally (measured:
  k = 1,308, 18,692 AT_FLOOR, 0 RUNNING, kept values 21,000.727 to 21,000.997, a 99.9% interval of 5.979% to 7.134%).
  It contradicts 16.1, though, so it is not used.
- **T11-2: the terms are built directly.** The test builds a `costs.Terms` with every field given (contract 6.2 fixes
  them). TASKS' `venues_with(upbit lot {default: 1e-12}, min_order {KRW: 0}, fee_extras 0/0)` and `costs.terms` are
  not used. The values are TASKS' own, and the engine reads only these fields. The venue parser belongs to Tasks 2 and
  5 to test, and `costs.terms` to Task 6.
- **T11-3: the engine runs in one chunk.** The engine run uses `OF.chunk(20_000)` instead of contract 3.4's 2,000-path
  chunk, so it makes one pass over the 732 checks instead of ten. Measured 2026-10-27: one chunk takes 3.1 s on an
  idle machine and 7.4 to 8.5 s under load from parallel jobs (k = 1,308). Ten 2,000-path chunks took 13.1 s idle,
  about four times as long and over the module's 12 s target on their own (k = 1,307).

Design notes (read before Step 1):
- **The bracket is TASKS' own:** `take_profit = math.exp(0.5) - 1.0` and `stop = 1.0 - math.exp(-0.5)`. Each
  subtraction is exact in binary floating point, so `1 + take_profit == e^0.5` and `1 - stop == e^-0.5` as floats.
  Task 9's `even_rows` nudges the upper price until every row moves at least that far up and down, so both triggers
  fire at every close. The fill is at the check price, so the game stays fair. Measured: winners land 1.97e-07 to
  0.00039 KRW past T (KRW 0.29 in all), and losers end 3.6e-12 to 0.95 KRW above L (KRW 1.68 in all). That puts the
  excess at KRW 9.8e-05 a path, against the bound of 0.01.
- **`_no_rate`** zeroes `costs.TABLE_BP["crypto_venue"]` with save/restore. It first checks that `costs.kappa`
  returns 0 on both sides, so a cost table copied at import fails loudly instead of charging 10 bp.
- **The charges of contract 9.1 are each tested on their own** (phi_buy, phi_sell, kappa, r_exit), and phi_buy is
  also tested against phi_sell. The combined `costly` case alone let a dropped `- phi_buy - phi_sell`, a dropped
  `/ (1.0 + kappa)` or a room without phi_buy pass. Each of these mutants now fails the bracket test (sandbox
  mutation run).
- **Timings** were measured 2026-10-27 in the drafting sandbox and depend on the machine and its load. The whole
  module took 23.1 to 23.6 s at 50% to 90% CPU load from parallel jobs: about 8.3 s for the engine test, 5 s for the
  fixture calendar and 5 s for the first test's hermetic first entry. On review, an idle machine ran the previous
  draft, which had one more short engine run, in 9.3 s, 2.5 s of that the first hermetic import. The 12 s module
  budget of contract 3.4 is a target, not an assert. The only timing assert is the bracket reference's 3 s for 60
  checks.
- **Simulated matches use the 99.9% Clopper-Pearson interval** (`LEVEL`; `report.cp_two_sided` arrives only in Task
  12, so `_cp` calls `scipy.stats.binomtest(k, n).proportion_ci(confidence_level=LEVEL, method="exact")`). The game
  test is exact and reproducible: integer KRW stakes and `numpy.random.default_rng(1)` and `(2)` gave k = 1,793
  (x = 1/8; 1,822.5 expected) and k = 5,391 (x = 1/3; 5,382.1 expected) in the sandbox, both inside the interval.
  The engine test's interval fails a correct engine 1 run in 1,000. If it ever fails on that line alone, do not change
  `SEED`, `LEVEL` or the path count (O3-9: a failure is a ruling, never a reseed): record k under "Drift rulings" and
  stop for a ruling.

- [ ] **Step 1: Write the failing tests**

  Create `tests/odds_bold.py` (LF) with exactly this content:

```python
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
    +(e^0.5 - 1) / -(1 - e^-0.5) entered at an open fills at that day's close: an even-money bet); bold stakes,
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
    assert col.at_floor + col.running + col.reached_outcome == col.n


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
    good = {"w0": W0, "l_min": L, "target": T, "n_checks": 6, **ZERO}
    assert 0.0 <= bold.bracket_reference(r, d, **good) <= 1.0
    for rr, dd in ((r, d[:-1]), (r[:0], d[:0]), (np.where(r > 0, np.nan, r), d), (r, d - 1.0),
                   (r.reshape(10, 10), d.reshape(10, 10))):
        assert "equal-length" in _raises(lambda: bold.bracket_reference(rr, dd, **good), ValueError)
    for change in ({"n_checks": -1}, {"n_checks": 6.0}, {"n_checks": True}):
        assert "whole number of checks" in _raises(lambda: bold.bracket_reference(r, d, **{**good, **change}),
                                                   ValueError), change
    for change in ({"target": L}, {"kappa": -0.1}, {"phi_sell": math.inf}, {"w0": math.nan}, {"r_exit": -1.0}):
        assert "l_min < target" in _raises(lambda: bold.bracket_reference(r, d, **{**good, **change}),
                                           ValueError), change
```

- [ ] **Step 2: Run to verify it fails**

  Overlap check with the PowerShell tool (it must print nothing; otherwise wait and re-run it):

```powershell
Get-CimInstance Win32_Process -Filter "Name LIKE 'python%'" | Where-Object { $_.CommandLine -match 'run_all' } | Select-Object ProcessId,Name,CommandLine
```

  Then, from the repo root in Git Bash (or with the Git Bash prefix of Global Constraints in front of it):

```bash
.venv/Scripts/python.exe -m tests.odds_acceptance odds_bold/
```

  Expected: a traceback, then exactly one result line and the tally (exit code 1):

```
FAIL odds_bold/import ImportError: cannot import name 'bold' from 'core.odds' (C:\Users\whydi\OneDrive\Desktop\TRADEGEN\core\odds\__init__.py)

0/1 passed, 1 failed, 0 not run
```

- [ ] **Step 3: Implement**

  Create `core/odds/bold.py` (LF) with exactly this content:

```python
"""References on the odds card (spec 3, 7.4): the fair-game ceiling and its "1 in N", the KRX structural maximum of a
buy-and-hold leg (Q44), the brackets needed to tell a typed win rate from the no-edge one (spec 7.2), exact bold play
at even money (Dubins-Savage; regression tests only) and the estimated bracket reference (Q33; amber only).

Pure: no clock, no file, no network (Q42). Imports the standard library and numpy only."""
from __future__ import annotations

import fractions
import math
import numbers

import numpy as np

_Z_ALPHA = 1.645        # one-sided test at 5% (spec 7.2)
_Z_POWER = 0.842        # 80% power (spec 7.2)
_R_BINS = 32            # bracket_reference: equal-count bins of the net return per unit stake (contract 9.1)
_D_BINS = 4             # equal-count bins of the duration in checks
_NODES = 129            # wealth nodes from l_min to the target
_STAKES = 16            # stake choices: k/16 of the floor-protected room, k = 1..16
_HALF = fractions.Fraction(1, 2)


def _real(*values) -> bool:
    """True when every value is a finite real number (bool excluded)."""
    return all(isinstance(v, numbers.Real) and not isinstance(v, bool) and math.isfinite(v) for v in values)


def _span(w0, l_min, target) -> tuple[fractions.Fraction, fractions.Fraction]:
    """(W0 - L_min, T - L_min), exact from the float inputs; ValueError unless finite l_min < w0 < target."""
    if not (_real(w0, l_min, target) and l_min < w0 < target):
        raise ValueError(f"need finite l_min < w0 < target, got w0={w0!r}, l_min={l_min!r}, target={target!r}")
    low = fractions.Fraction(l_min)
    return fractions.Fraction(w0) - low, fractions.Fraction(target) - low


def ceiling(w0: float, l_min: float, target: float) -> float:
    """(W0 - L_min) / (T - L_min): no plan without a real edge that keeps the floor L_min beats it (Ville; spec 3,
    Q32). Computed exactly, then rounded once."""
    gain, span = _span(w0, l_min, target)
    return float(gain / span)


def ceiling_one_in(w0: float, l_min: float, target: float) -> int:
    """floor((T - L_min) / (W0 - L_min)), exactly: the N of "1 in N" for a ceiling below 1%. The ceiling is an upper
    bound, so N rounds down and never prints a smaller chance than the bound."""
    gain, span = _span(w0, l_min, target)
    return math.floor(span / gain)


def structural_max(limits: tuple[float, ...]) -> float:
    """(1 + l1)/(1 - l1) x prod(1 + li, i >= 2) over the dated daily price limits l1..ln of a leg's n KRX sessions
    (spec 3, 7.4; Q44): the most a position bought at the first open and held can multiply. Buy-and-hold KRX legs
    only; repeated intraday round trips, IPO days and special reference-price regimes are not bounded this way."""
    limits = tuple(limits)
    if not limits or not all(_real(v) and 0.0 < v < 1.0 for v in limits):
        raise ValueError(f"need one price limit in (0, 1) per session, got {limits!r}")
    first = limits[0]
    return (1.0 + first) / (1.0 - first) * math.prod(1.0 + v for v in limits[1:])


def brackets_needed(p: float, p0: float) -> float:
    """Resolved brackets needed to tell the typed win rate p from the no-edge p0, one-sided at 5% with 80% power,
    assuming independent brackets (spec 7.2): ceil(((1.645 sqrt(p0 (1 - p0)) + 0.842 sqrt(p (1 - p))) / |p - p0|)
    ** 2); math.inf when p == p0."""
    if not (_real(p, p0) and 0.0 <= p <= 1.0 and 0.0 <= p0 <= 1.0):
        raise ValueError(f"need win rates in [0, 1], got p={p!r}, p0={p0!r}")
    if p == p0:
        return math.inf
    root = (_Z_ALPHA * math.sqrt(p0 * (1.0 - p0)) + _Z_POWER * math.sqrt(p * (1.0 - p))) / abs(p - p0)
    return float(math.ceil(root * root))


def bold_even(x: fractions.Fraction, p: fractions.Fraction) -> fractions.Fraction:
    """Exact P(reach 1 from x) under bold play at even money with win chance p (Dubins-Savage): f(0) = 0, f(1) = 1,
    f(1/2) = p, f(x) = p f(2x) below 1/2 and p + (1 - p) f(2x - 1) above it. The doubling orbit of a rational x ends
    at 0, 1/2 or 1, or comes back to a point it has visited; the repeat closes a linear equation, solved exactly.
    Regression tests only (spec 7.4)."""
    for v in (x, p):
        if isinstance(v, bool) or not isinstance(v, (int, fractions.Fraction)):
            raise TypeError(f"bold_even takes exact fractions.Fraction values, got {v!r}")
    x, p = fractions.Fraction(x), fractions.Fraction(p)
    if not (0 <= x <= 1 and 0 <= p <= 1):
        raise ValueError(f"need 0 <= x <= 1 and 0 <= p <= 1, got x={x}, p={p}")
    a, b, seen = fractions.Fraction(0), fractions.Fraction(1), {}
    while True:                                  # invariant: f(start) = a + b f(x)
        if b == 0 or x == 0:
            return a
        if x == 1:
            return a + b
        if x == _HALF:
            return a + b * p
        if x in seen:                            # a0 + b0 f(x) = a + b f(x), so f(x) = (a - a0) / (b0 - b)
            a0, b0 = seen[x]
            return a0 + b0 * (a - a0) / (b0 - b)
        seen[x] = (a, b)
        if x < _HALF:
            b, x = b * p, 2 * x
        else:
            a, b, x = a + b * p, b * (1 - p), 2 * x - 1


def _bins(v: np.ndarray, k: int) -> tuple[np.ndarray, list[np.ndarray]]:
    """Equal-count bins of v by rank: (the bin of each value, the indices in each non-empty bin)."""
    parts = [part for part in np.array_split(np.argsort(v, kind="stable"), k) if part.size]
    label = np.empty(v.size, dtype=np.int64)
    for i, part in enumerate(parts):
        label[part] = i
    return label, parts


def bracket_reference(r, d, *, w0, l_min, target, n_checks, kappa, phi_buy, phi_sell, r_exit) -> float:
    """An ESTIMATED reference (Q33, contract 9.1), never a certified bound and never a red flag: the best chance of
    reaching the target within n_checks checks when each bracket stakes k/16 of the floor-protected room
    max(0, w - l_min - phi_buy - r_exit) / (1 + kappa) on the binned joint law of (r, d). r is the net return per unit
    stake (exit proceeds net of the proportional exit charge, minus the stake and its proportional entry charge, over
    the stake), d the checks from entry to exit fill. Dynamic programme over (wealth on 129 nodes from l_min to the
    target, checks left); interpolation is clamped at both grid ends. kappa is the buy side's base rate at p0."""
    r = np.asarray(r, dtype=float)
    d = np.asarray(d, dtype=float)
    if (r.ndim != 1 or r.shape != d.shape or r.size == 0 or not (np.isfinite(r).all() and np.isfinite(d).all())
            or d.min() < 1.0):
        raise ValueError("need equal-length non-empty 1-d arrays: finite r, and durations d >= 1")
    if isinstance(n_checks, bool) or not isinstance(n_checks, numbers.Integral) or n_checks < 0:
        raise ValueError(f"need a whole number of checks >= 0, got {n_checks!r}")
    if not (_real(w0, l_min, target, kappa, phi_buy, phi_sell, r_exit) and l_min < target and kappa >= 0.0
            and min(phi_buy, phi_sell, r_exit) >= 0.0):
        raise ValueError("need finite w0, l_min < target, kappa >= 0 and charges >= 0")
    r_label, r_parts = _bins(r, _R_BINS)
    d_label, d_parts = _bins(d, _D_BINS)
    r_value = np.array([r[part].mean() for part in r_parts])
    d_value = np.array([math.ceil(d[part].mean()) for part in d_parts])
    width = len(d_parts)
    counts = np.bincount(r_label * width + d_label, minlength=len(r_parts) * width)
    cells = np.flatnonzero(counts)                                    # cells with weight 0 dropped
    weight, cell_r, cell_d = counts[cells] / r.size, r_value[cells // width], d_value[cells % width]
    grid = np.linspace(l_min, target, _NODES)
    top = (grid >= target).astype(float)
    room = np.maximum(0.0, grid - l_min - phi_buy - r_exit) / (1.0 + kappa)
    stakes = np.arange(1, _STAKES + 1)[:, None] / _STAKES * room[None, :]          # (stake choice, node)
    groups = []                                   # per duration: (checks, wealth after the bracket, cell weights)
    for checks in np.unique(cell_d):
        pick = cell_d == checks
        after = grid + stakes[:, None, :] * cell_r[pick][None, :, None] - phi_buy - phi_sell   # (stake, cell, node)
        groups.append((int(checks), after, weight[pick][None, :, None]))
    value = [top]                                 # value[t]: the chance of reaching the target with t checks left
    for t in range(1, int(n_checks) + 1):
        bet = sum((np.interp(after, grid, value[max(t - checks, 0)]) * w).sum(axis=1) for checks, after, w in groups)
        value.append(np.maximum(np.maximum(top, value[t - 1]), bet.max(axis=0)))
    return float(np.interp(w0, grid, value[int(n_checks)]))
```

- [ ] **Step 4: Run to verify it passes**

  Run the overlap check of Step 2 (PowerShell tool; it must print nothing) before EACH Python command below. All run
  from the repo root in Git Bash.

  Every runner below ends with a tally line of the form `<passed>/<total> passed, <failed> failed, <not run> not run`
  (`tests/run_all.py` adds `; ` and the path of `qa\acceptance_results.json`). "The counts the previous task recorded"
  means that task's line for the same command under "Runs" in the execution ledger.

  Overlap check, then:

```bash
.venv/Scripts/python.exe -m tests.odds_acceptance odds_bold/; echo "exit $?"
```

  Expected: 12 `PASS odds_bold/test_...` lines, then `12/12 passed, 0 failed, 0 not run` and `exit 0`. The module's
  12 s budget (contract 3.4) is a target, not an assert: under load from parallel jobs the module took about 23 s in
  the drafting sandbox (see the timing note above).

  Overlap check, then the odds guards, which now scan `bold.py` (allowlist imports, no clock, no file I/O, no
  `__main__`, no package re-export, a flat package, the D14 closure):

```bash
.venv/Scripts/python.exe -m tests.odds_acceptance odds_guards/; echo "exit $?"
```

  Expected: no FAIL line, the tally with the counts the previous task recorded (`0 failed, 0 not run`), and `exit 0`.
  A failure names `core/odds/bold.py` and the text: fix `bold.py`, never the guard.

  Overlap check, then the static guards and the store (Global Constraints: every task that touches `core/odds`;
  `test_code_files_is_the_import_closure` now sees `core/odds/bold.py` in the code hash), with the overlap check
  before each:

```bash
.venv/Scripts/python.exe -m tests.compliance_acceptance compliance_guards/; echo "exit $?"
.venv/Scripts/python.exe -m tests.compliance_acceptance compliance_store/; echo "exit $?"
```

  Expected: each prints no FAIL line, the tally with the counts the previous task recorded (`0 failed, 0 not run`),
  and `exit 0`.

  Overlap check, then the core-wide scans (Global Constraints: every task that changes `core/`), one at a time with
  the overlap check before each:

```bash
.venv/Scripts/python.exe -m tests.macro_m0_harness; echo "exit $?"
.venv/Scripts/python.exe -m tests.macro_tf_gov; echo "exit $?"
.venv/Scripts/python.exe -m tests.macro_m7_ledger; echo "exit $?"
.venv/Scripts/python.exe -m tests.macro_m8_forward; echo "exit $?"
.venv/Scripts/python.exe -m tests.macro_m6_context; echo "exit $?"
```

  Expected: each prints no FAIL line, the tally with `0 failed` and the passed, total and not-run counts the previous
  task recorded (Task 1 recorded `11/11 passed, 0 failed, 0 not run`, `20/22 passed, 0 failed, 2 not run`,
  `14/18 passed, 0 failed, 4 not run`, `17/23 passed, 0 failed, 6 not run` and `14/16 passed, 0 failed, 2 not run`),
  and `exit 0`.

  Overlap check, then the cockpit suite (test_08, test_09, test_16, test_18 scan every `core/**/*.py`;
  `timeout: 300000`). It rewrites the tracked `qa/acceptance_results.json`, so the same line restores it whatever the
  result:

```bash
KIS_APP_KEY='<unset>' KIS_APP_SECRET='<unset>' KIS_ACCOUNT_8='<unset>' KIS_ACCOUNT_PD='<unset>' UPBIT_ACCESS_KEY='<unset>' UPBIT_SECRET_KEY='<unset>' OKX_API_KEY='<unset>' OKX_API_SECRET='<unset>' OKX_API_PASSPHRASE='<unset>' OPENDART_API_KEY='<unset>' KRX_API_KEY='<unset>' FMP_API_KEY='<unset>' ANTHROPIC_API_KEY='<unset>' GS_CLIENT_ID='<unset>' GS_CLIENT_SECRET='<unset>' FINVIZ_API_KEY='<unset>' ALPACA_API_KEY='<unset>' ALPACA_SECRET_KEY='<unset>' FXMACRODATA_API_KEY='<unset>' .venv/Scripts/python.exe tests/run_all.py --suite cockpit; echo "exit $?"; git checkout -- qa/acceptance_results.json
```

  Expected: the tally with the counts the previous task recorded (Task 1 recorded `47/47 passed, 0 failed, 0 not
  run`), then `; ` and the path, then `exit 0`.

  Then the text checks (git only; no overlap check needed):

```bash
git status --short
git grep --untracked -n -E "^(import|from) " -- core/odds/bold.py
git grep --untracked -n -i -E "order_cash|order-cash|place_order|submit_order|tttc0802u|tttc0801u|vttc0802u|private_key|seed_phrase|/v1/orders|/v1/withdraws|/v1/deposits|/api/v3/order|/sapi/v1/capital|/trading/|r18_research_log|r18_break_log|context_log/|tests\.reference|reference_mode|reference_only" -- core/odds/bold.py
git grep --untracked -n -E "CANO|KIS_ACCOUNT|ACNT_PRDT_CD|0\.4 *[*x×]|[*x×] *0\.4|open\(|datetime|time\.|__main__|exec|eval|__import__" -- core/odds/bold.py
```

  Expected: `git status --short` lists exactly `?? core/odds/bold.py`,
  `?? docs/superpowers/plans/2026-10-24-odds-engine-execution-ledger.md` and `?? tests/odds_bold.py`; the import grep
  prints exactly five lines, `core/odds/bold.py:6:from __future__ import annotations`, then `:8:import fractions`,
  `:9:import math`, `:10:import numbers` and `:12:import numpy as np` (each with the same path prefix); the last two
  greps print nothing (exit code 1).

  Append one line per run above under "Runs" in the execution ledger (LF; it stays untracked), in the order run, each
  `- Task 11: <the command after .venv/Scripts/python.exe, without the echo>: <its tally line>` (the path after `;`
  left out), for example `- Task 11: -m tests.odds_acceptance odds_bold/: 12/12 passed, 0 failed, 0 not run`.

- [ ] **Step 5: Commit**

```bash
git add core/odds/bold.py tests/odds_bold.py
git diff --cached --stat
git diff --cached --stat --ignore-cr-at-eol
```

  The two stat outputs must be identical (both files are LF). Then:

```bash
git commit -m "feat(odds): references: ceiling, structural maximum, brackets needed, bold play" -m "Odds plan Task 11 (Q32, Q33, Q44): core/odds/bold.py with exact bold play matched by a simulated game and by the engine, the KRX cap checked on the fixture calendar, and the estimated bracket reference." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

  Afterwards `git status --short` prints only `?? docs/superpowers/plans/2026-10-24-odds-engine-execution-ledger.md`.
