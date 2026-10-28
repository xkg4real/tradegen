### Task 7: The two-point bootstrap, block lengths, the index generator and the seeds (`core/odds/models.py` part 1)

**Files:**
- Create: `core/odds/models.py` (LF, UTF-8, no BOM; Tasks 8 and 17 append to it)
- Create: `tests/odds_models.py` (LF, UTF-8, no BOM)
- Test: `tests/odds_models.py` (already listed in `tests/odds_acceptance.MODULES` since Task 1)

No existing file is modified, so the DRIFT RULE has nothing to apply to. The originals the tests compare against
(`core/quant/gate_stats.py`, `validate.py`, `garch.py`, `instruments.py`, `montecarlo.py`, `history.py`) are not in
the follow-up's change list (followup CONTRACT section 12) and are not edited here.

**Interfaces:**
- Consumes:
  - Task 1: `core/odds/__init__.py` (0 bytes); `tests/odds_acceptance.py` (`MODULES` holds `"odds_models"`; `_wrap`
    runs each test inside `hermetic()` and `temp_home()` and fails it if `docs/asset_expansion/cache/upbit_KRW-BTC.csv`
    changed, which this task's test only reads); `tests/odds_guards.py` (scans every `core/odds/*.py`, so the new
    module is checked with no change there).
  - Task 5 (`core.odds.plan`, CONTRACT 5.2-5.3): `Series` (kw_only: `symbol`, `source`, `dates`, `open`, `close`,
    `adjustment`, `status`, `md5`, `components=()`, `proxy_dates=None`); `ReplayInput` (kw_only: `card_id`,
    `input_symbol`, `input_source`, `input_dates`, `input_close`, `oos_dates`, `oos_pnl`, `oos_turnover`, `lookbacks`,
    `mas`, `grid`, `cost_bps_per_side`, `embargo`, `n_trials`, `seed`, `domain`, `protocol`, `gate_protocol`, `stats`,
    `results_md5`, `card_md5`); `series_md5(symbol, source, dates, open_, close, adjustment, status) -> str`.
  - `core.compliance.model.canonical_json(obj) -> str` (unchanged by the follow-up).
  - Tests only (the originals): `core.quant.gate_stats.optimal_block_length(x)`, `gate_stats.pw_block(x, kind)`,
    `gate_stats.LIVE_SHARPE_MULTIPLIER`; `core.quant.validate.sharpe(daily)`, `validate.TRADING_DAYS`,
    `validate.GATE["haircut"]`; `core.quant.garch.Z_BOUND`, `garch.TRADING_DAYS`, `garch.NU_NORMAL`;
    `core.quant.instruments.TICK_TABLES["KRX_ETF"]` (`((date(2023, 12, 11), ((2000.0, 1.0), (inf, 5.0))),)`);
    `core.quant.montecarlo.run_monte_carlo(history, *, model, n_paths, horizon_days, drift, rf_rate, seed,
    n_sample_paths)` (`.terminal`, `.spot`); `core.quant.history.History(symbol, source, dates, closes)`.
- Produces (`core/odds/models.py`, CONTRACT 7.1 and 7.2, exact names):
  - `LIVE_SHARPE_MULTIPLIER = 0.60`, `Z_BOUND = 22`, `TRADING_DAYS = 252`, `NU_NORMAL = 100.0`.
  - `_optimal_block_length(x) -> tuple[float, float]` (bit-exact copy), `pw_block(x) -> float` (the stationary
    length), `sharpe(daily) -> float` (copy of `validate.sharpe`).
  - `rows(series: plan.Series) -> tuple[np.ndarray, np.ndarray, np.ndarray]` (`m_o`, `m_i`, `r`, each of length n - 1);
    `block_length(r) -> float`; `variant_block(b: float, mult: float, n_rows: int) -> float`.
  - `indices(rng: np.random.Generator, n_rows: int, n_paths: int, block: float) -> Iterator[np.ndarray]` (endless;
    ValueError at the call for a block that is not a finite number >= 1); its body is the private generator
    `_steps(rng, n_rows, n_paths, restart_p) -> Iterator[np.ndarray]`.
  - `tilt(q, theta: float) -> np.ndarray`; `kernel(p, m, d_edge, u_edge, u, theta: float = 0.0) -> np.ndarray`
    (broadcasts: per-path arrays, or scalars `0.0` and `np.inf` for a leg with no band); the private
    `_points(p, m, d_edge, u_edge) -> tuple[np.ndarray, np.ndarray, np.ndarray]` returns `(x_u, x_d, q)`.
  - `STREAMS` (the ten names of CONTRACT 7.2, `replay_sign` included), `SEED_TAG = b"tradegen-odds/seed/1\x00"`.
  - `data_hashes(series, replay) -> tuple[str, ...]` (sorted); `market_seed(data_hashes, calendar_digest: str,
    comparison_id: str, run_counter: int) -> bytes` (32 bytes, Q34; ValueError for `data_hashes` given as one
    `str`, an empty `data_hashes`, a hash that is not a non-empty NUL-free `str`, a calendar digest or comparison id
    that is not a NUL-free `str`, or a run counter that is not an `int` in [0, 2**64)); `seed_sequence(seed: bytes,
    chunk: int, name: str, *extra: int) -> np.random.SeedSequence`; `stream(seed: bytes, chunk: int, name: str,
    *extra: int) -> np.random.Generator` (PCG64; KeyError for a name outside `STREAMS`).
  - Private helpers later tasks reuse: `_input_md5(rep) -> str` (md5 of the canonical JSON `{symbol, source, dates,
    close}` of the replay input, the definition of `REPLAY_PINS["input_md5"]`) and `_array_md5(values) -> str` (md5
    of the `"<f8"` bytes, the definition of `pnl_md5` and `turnover_md5`). Task 17's `verify_replay` recomputes its
    three digests with these two, so the seed and the verification hash the same bytes.
  - Layout for Tasks 8 and 17: the import block is `hashlib`, `math`, `collections.abc.Iterator`,
    `typing.TYPE_CHECKING`, `numpy as np`, `core.compliance.model`, and `core.odds.plan` under `if TYPE_CHECKING:`
    only; the file ends with `stream`. Task 8 adds its imports to that block and appends the GARCH-t part after
    `stream`; a later task that needs `plan` at run time moves its import out of the `TYPE_CHECKING` block.

**Plan decisions used:** Q1 (O1: every copy pinned by an equality test), Q10 (the stationary pw_block, b = max(1,
pw(r), pw(r^2)), half-up variants capped at the history, the vectorised Politis-Romano generator), Q12 (streams are
`SeedSequence(int.from_bytes(seed, "big"), spawn_key=(chunk, STREAMS[name], *extra))`), Q30 (the tilt formula), Q34 (the
seed bytes; plan fields never enter), Q42 (no I/O, no clock). Covers spec 8 odds items 1 (E[next | p] = p to 1e-12,
prices inside the band, an edge holds, drift="zero" and per-row demeaning fail) and 8 (one comparison shares every
stream; renaming cannot reach the seed). RULINGS O1, O10, O12.

Design notes (read before Step 3):
- **Kernel.** With D <= p <= U and m >= 0, x_d <= p <= x_u, so q = (p - x_d)/(x_u - x_d) lies in [0, 1] and
  q x_u + (1 - q) x_d = p up to rounding (measured over 20,000 random cases: at most 3.8e-16 relative, 2.2e-16 with
  bands; the test bound is 1e-12). At p = U, x_u = U exactly and q = 1; at p = D, q = 0; so a price at an edge
  stays there for every draw and every theta (`u` is in [0, 1)). `_points` returns the very q the kernel uses, so
  the test checks the identity on it and then checks `kernel == where(u < tilt(q, theta), x_u, x_d)` element by element.
- **Tilt.** There is no `theta == 0` branch: `math.exp(0.0)` is 1.0 and `q + (1.0 - q)` rounds to 1.0 for every q
  in [0, 1], so `tilt(q, 0.0)` returns q bit for bit (the test checks 240,004 values, `5e-324` and
  `nextafter(1, 0)` included). The parentheses around `(1.0 - q)` are what makes it exact; the test fails without
  them.
- **Index generator.** `indices` checks the block when it is called (a NaN or infinite block never restarts, and a
  block below 1 would give mean 1, not `block`), then returns `_steps`, which makes its first draw at the first
  `next()`. The draw order (step 0 `integers`; then `random` before `integers` at every step, both always drawn) is
  pinned against a hand loop, so later tasks can reproduce a stream exactly. The mean-block test counts breaks
  (`idx != prev + 1 mod n`): a restart is invisible when the fresh row happens to be the next one, so breaks occur at
  rate (1 - 1/n)/block and the mean block estimate is (1 - 1/n)/rate.
- **Seed.** `market_seed` refuses a bare `str` for `data_hashes` (`tuple(series.md5)` would be its sorted
  characters, so two anagram md5s would share a seed), then turns `data_hashes` into a tuple (an iterator would
  otherwise be consumed by the check). It refuses an empty tuple and an empty hash (`()` and `("",)` would both join
  to the same bytes), a NUL inside any part (the NUL separators would let two different inputs share bytes) and a run
  counter that is not an `int` in [0, 2**64) (`True` is an int, so the check is `type(...) is int`). With those
  refused, the bytes decode back to their inputs: the counter is the last 8 bytes, and splitting the rest at NUL gives
  the hashes, then the calendar digest (which may be `""`), then the comparison id.
- **Replay hashes.** `REPLAY_PINS` arrives only in Task 17, so `data_hashes` recomputes the replay's input md5 and
  pnl md5 from the `ReplayInput`. Every run that reaches the seed has passed `verify_replay` (Task 17), which
  requires both to equal their pins, so the seed holds exactly the "pinned input md5 and pnl md5" of CONTRACT 7.2.
  `test_replay_input_md5_is_the_pinned_digest_of_the_committed_cache` pins `_input_md5`'s definition against the
  committed cache: `18ec83bdfe158efe4d648caf45ff849f` (CONTRACT 7.5 and 16).
- **No run-time `plan` import.** `models` reads `Series` and `ReplayInput` by attribute only. The D14 closure skips
  `TYPE_CHECKING` bodies (`owner.code_files`), and `plan.py` is a closure seed anyway.
- **`series.open`.** `rows` reads the contract field `Series.open` as an attribute, never as a call. CONTRACT
  section 0 bans `open(...)` and attribute calls `.open(...)`. If `odds_guards/test_core_odds_does_no_file_io` flags
  `rows`, the guard reads more than the contract says: stop and rule; never rename the field and never route around
  the guard with `getattr`.
- **The two traps** (spec 7.2) run on fixed seeds, so their margins are deterministic under numpy 2.3.5. Measured in
  the drafting sandbox: montecarlo `drift="zero"` z = 16.3 (terminal mean 1.0107 of spot), the same model with
  `drift="rf"`, `rf_rate=0.0` z = 0.45; the rev-1 per-row demeaned bootstrap with a 3% stop z = +21.8 (mean payoff
  +1.03% over 30 sessions) and with plain buy-and-hold z = +8.06 (rows inside a block are serially dependent, so the
  mean of their product is not 1), the two-point kernel on the same AR(1) rows, blocks, stop rule and index stream
  z = -0.68. Other margins: mean-block z between -1.29 and 1.25 (bound 3); chi-square p-values 0.068 and above
  (bound 0.001); 4,199 of 20,000 kernel cases clamp at U. `core.quant.montecarlo` and `core.quant.history` are
  imported inside the trap test only (`history` imports `config`); no test calls a data function.
- **The tests discriminate.** In the drafting sandbox each of 32 deliberate breaks of `models.py` failed at least one
  test: `round()` in `variant_block`, `fresh` drawn before `restart`, q = 1/2, the circular pw length, no floor,
  `pw(r)` only, unsorted hashes, a wrong tilt, an unparenthesised tilt, unclamped x_u or x_d, no wrap, no tag, the
  spawn key order swapped, `*extra` dropped, no replay hashes, no component hashes, `ddof=0`, a fair-coin kernel,
  `u <= q`, a restart rate 1/(b + 1), `m_o` from closes, a 4-byte counter, the calendar digest dropped, no block
  check, big-endian pnl bytes, the source missing from the input md5, an MT19937 stream, and in `market_seed` a bare
  `str` accepted, `()` accepted, `("",)` accepted, a NUL in the calendar digest accepted.

- [ ] **Step 1: Write the failing tests**

  Create `tests/odds_models.py` (whole file, LF). It builds its own `plan.Series` with `_series` instead of
  `tests.odds_fixtures.series`, because the rows test needs exact opens and closes.

```python
"""The two-point bootstrap, block lengths, index generator and seeds (odds plan Task 7; spec 7.2, 7.3; 8.o items 1
and 8; Q10, Q12, Q34). The copies in core/odds/models.py are pinned against their originals; two test-only
references show the traps of spec 7.2 fail the same martingale check the odds kernel passes."""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import inspect
import math
from pathlib import Path

import numpy as np
from scipy import stats

from core.compliance import model
from core.odds import plan, models          # plan first: at Step 2 a missing Task 5 is named, not models
from core.quant import garch, gate_stats, instruments, validate

ROOT = Path(__file__).resolve().parents[1]
SEED = models.market_seed(("0" * 32,), "", "c000001", 1)
ETF_TICKS = instruments.TICK_TABLES["KRX_ETF"][0][1]      # ((2000.0, 1.0), (inf, 5.0)), from 2023-12-11


def _series(open_, close, *, symbol="FIXTURE", components=()) -> plan.Series:
    """A plan.Series of the given KRW opens and closes (daily dates from 2024-01-01), md5 filled."""
    o, c = tuple(float(x) for x in open_), tuple(float(x) for x in close)
    dates = tuple((dt.date(2024, 1, 1) + dt.timedelta(days=i)).isoformat() for i in range(len(c)))
    return plan.Series(symbol=symbol, source="SYNTHETIC", dates=dates, open=o, close=c, adjustment="", status="final",
                       md5=plan.series_md5(symbol, "SYNTHETIC", dates, o, c, "", "final"), components=components)


def _replay(**changes) -> plan.ReplayInput:
    """A small ReplayInput (every field of contract 5.2; values are fixtures, not the card's)."""
    fields = dict(card_id="S_C3_crypto_trend_krwbtc", input_symbol="KRW-BTC", input_source="UPBIT",
                  input_dates=("2024-01-01", "2024-01-02", "2024-01-03"), input_close=(1.0e7, 1.01e7, 0.99e7),
                  oos_dates=("2024-01-02", "2024-01-03"), oos_pnl=(0.01, -0.0198), oos_turnover=(1.0, 0.0),
                  lookbacks=(7, 14, 21, 28), mas=(10, 20, 50, 100, 200), grid=(0.0, 0.222, 0.444, 0.667, 0.889),
                  cost_bps_per_side=10.0, embargo=1, n_trials=11, seed=11, domain=(0.0, 0.889),
                  protocol={"block": 10}, gate_protocol={"block": 10}, stats={"decision": "PASS"},
                  results_md5="a" * 32, card_md5="b" * 32)
    fields.update(changes)
    return plan.ReplayInput(**fields)


def _ar1(n: int, phi: float, sigma: float, seed: int) -> np.ndarray:
    e = sigma * np.random.default_rng(seed).standard_normal(n)
    r = np.empty(n)
    r[0] = e[0]
    for t in range(1, n):
        r[t] = phi * r[t - 1] + e[t]
    return r


def _etf_band(ref: np.ndarray, limit: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """A test band in the shape of Q41's, per path, on the copied KRX ETF ticks: D up to the tick at D's level, U down
    to the tick at U's level, then D <= ref <= U. Not the shipped costs.band (Task 6 tests that one at 2005); this
    one only feeds the kernel random per-path edges."""
    def tick(x):
        return np.where(x < ETF_TICKS[0][0], ETF_TICKS[0][1], ETF_TICKS[1][1])
    raw_d, raw_u = ref * (1.0 - limit), ref * (1.0 + limit)
    d_edge = np.ceil(raw_d / tick(raw_d)) * tick(raw_d)
    u_edge = np.floor(raw_u / tick(raw_u)) * tick(raw_u)
    return np.minimum(d_edge, ref), np.maximum(u_edge, ref)


def _z(x: np.ndarray) -> float:
    return float(x.mean() / (x.std(ddof=1) / math.sqrt(x.size)))


def test_copied_constants_equal_the_originals():
    assert models.LIVE_SHARPE_MULTIPLIER == gate_stats.LIVE_SHARPE_MULTIPLIER == validate.GATE["haircut"]
    assert type(models.Z_BOUND) is type(garch.Z_BOUND) and models.Z_BOUND == garch.Z_BOUND == 22
    assert models.TRADING_DAYS == garch.TRADING_DAYS == validate.TRADING_DAYS == 252
    assert models.NU_NORMAL == garch.NU_NORMAL == 100.0


def test_pw_block_equals_the_original_on_a_grid():
    rng = np.random.default_rng(20261024)
    for n in (20, 21, 37, 100, 250, 999, 3000):
        z = rng.standard_normal(n)
        heavy = rng.standard_t(3, n)
        vol = np.exp(_ar1(n, 0.95, 0.3, int(rng.integers(1 << 30))))
        for x in (z, _ar1(n, 0.5, 1.0, n), _ar1(n, 0.9, 1.0, n + 1), _ar1(n, -0.5, 1.0, n + 2), heavy, heavy * vol,
                  np.full(n, 0.01)):
            for y in (x, x * x):
                assert models._optimal_block_length(y) == gate_stats.optimal_block_length(y), (n, y[:3])
                assert models.pw_block(y) == gate_stats.pw_block(y, kind="stationary"), (n, y[:3])
    for bad in (np.ones(19), np.r_[np.ones(30), np.nan], np.r_[np.ones(30), np.inf]):
        for fn in (models.pw_block, lambda v: gate_stats.pw_block(v, kind="stationary")):
            try:
                fn(bad)
            except ValueError as exc:
                assert str(exc) == "pw_block needs at least 20 finite observations"
            else:
                raise AssertionError(f"no ValueError for {bad[-3:]}")


def test_sharpe_equals_the_original():
    rng = np.random.default_rng(7)
    x = 0.01 + 0.02 * rng.standard_normal(500)
    for d in (x, np.r_[x, np.nan, np.inf, -np.inf], list(x[:30]), np.full(40, 0.003), np.zeros(5)):
        assert models.sharpe(d) == validate.sharpe(np.asarray(d, dtype=float)), d
    for d in (np.array([0.01]), np.array([]), np.array([np.nan, 0.02])):
        assert math.isnan(models.sharpe(d)) and math.isnan(validate.sharpe(d))


def test_rows_are_the_two_magnitudes_and_the_close_return():
    s = _series((100.0, 104.0, 99.0, 101.0), (102.0, 98.0, 100.0, 103.0))
    m_o, m_i, r = models.rows(s)
    assert np.allclose(m_o, [abs(math.log(104 / 102)), abs(math.log(99 / 98)), abs(math.log(101 / 100))],
                       rtol=0, atol=1e-15)
    assert np.allclose(m_i, [abs(math.log(98 / 104)), abs(math.log(100 / 99)), abs(math.log(103 / 101))],
                       rtol=0, atol=1e-15)
    assert np.allclose(r, [math.log(98 / 102), math.log(100 / 98), math.log(103 / 100)], rtol=0, atol=1e-15)
    assert (m_o >= 0).all() and (m_i >= 0).all() and abs(r.sum() - math.log(103 / 102)) < 1e-15


def test_block_length_floors_at_one_and_takes_the_larger():
    white = np.random.default_rng(1).standard_normal(2000)
    assert models.pw_block(white) < 1.0 and models.pw_block(white * white) < 1.0       # the floor is what acts
    assert models.block_length(white) == 1.0
    for r in (_ar1(2000, 0.5, 0.02, 4), 0.02 * np.random.default_rng(5).standard_t(3, 2000)
              * np.exp(_ar1(2000, 0.98, 0.2, 6))):
        b = models.block_length(r)
        assert b == max(1.0, gate_stats.pw_block(r, kind="stationary"),
                        gate_stats.pw_block(r * r, kind="stationary")) and b > 1.0, b
        assert type(b) is float


def test_variant_blocks_round_half_up_and_cap_at_the_history():
    assert round(0.5 * 5) == 2                       # the trap: Python's round() is half to even
    assert models.variant_block(5, 0.5, 100) == 3.0 and type(models.variant_block(5, 0.5, 100)) is float
    assert models.variant_block(3, 0.5, 100) == 2.0
    assert models.variant_block(1, 0.5, 100) == 1.0
    assert models.variant_block(1.0, 0.5, 100) == 1.0
    assert models.variant_block(88.57, 2.0, 3287) == 177.0
    assert models.variant_block(88.57, 0.5, 3287) == 44.0
    assert models.variant_block(100.0, 2.0, 150) == 150.0          # capped at the history length
    assert models.variant_block(7.28, 2.0, 10) == 10.0


def test_index_generator_mean_block_is_the_block():
    """A restart shows as a break (idx != prev + 1 mod n) unless the fresh row happens to be prev + 1, so breaks
    occur at the rate (1 - 1/n) / block; the mean block estimate (1 - 1/n) / rate must be within 3 SE of block."""
    n_rows, n_paths, steps = 50, 20_000, 200
    for block in (1.0, 2.5, 7.5, 88.57):
        gen = models.indices(models.stream(SEED, 0, "index"), n_rows, n_paths, block)
        prev = next(gen)
        breaks = 0
        for _ in range(steps - 1):
            idx = next(gen)
            breaks += int(np.count_nonzero(idx != (prev + 1) % n_rows))
            prev = idx
        trials = n_paths * (steps - 1)
        rate, expected = breaks / trials, (1.0 - 1.0 / n_rows) / block
        se_rate = math.sqrt(expected * (1.0 - expected) / trials)
        b_hat, se_b = (1.0 - 1.0 / n_rows) / rate, block * se_rate / expected
        assert abs(b_hat - block) <= 3.0 * se_b, (block, b_hat, se_b)


def test_index_generator_rows_stay_uniform():
    """Every step's row is uniform (chi-square at steps 0, 1, 2, 10 and 120) and in range at every step."""
    n_rows, n_paths = 40, 40_000
    for block in (3.0, 100.0):                       # 100 > n_rows: every block wraps
        gen = models.indices(models.stream(SEED, 1, "index"), n_rows, n_paths, block)
        for step in range(121):
            idx = next(gen)
            assert idx.shape == (n_paths,) and idx.min() >= 0 and idx.max() < n_rows
            if step in (0, 1, 2, 10, 120):
                counts = np.bincount(idx, minlength=n_rows)
                assert stats.chisquare(counts).pvalue > 1e-3, (block, step, counts)


def test_index_generator_draws_in_the_contract_order():
    n_rows, n_paths, block = 30, 500, 4.0
    gen = models.indices(np.random.default_rng(5), n_rows, n_paths, block)
    ref = np.random.default_rng(5)
    expect = ref.integers(0, n_rows, n_paths)
    for _ in range(50):
        assert np.array_equal(next(gen), expect)
        restart = ref.random(n_paths) < 1 / block
        fresh = ref.integers(0, n_rows, n_paths)
        expect = np.where(restart, fresh, (expect + 1) % n_rows)
    for bad in (0.5, 0.0, math.nan, math.inf):
        try:
            models.indices(np.random.default_rng(5), n_rows, n_paths, bad)
        except ValueError:
            pass
        else:
            raise AssertionError(f"block {bad} accepted")


def test_kernel_is_a_martingale_to_1e_12():
    """E[next | p] = q x_u + (1 - q) x_d = p on random prices, moves and bands, tick-clamped edges included; the
    kernel draws x_u exactly where u < tilt(q, theta)."""
    rng = np.random.default_rng(11)
    k = 20_000
    ref = np.exp(rng.uniform(math.log(100.0), math.log(1e6), k))
    ref[:200] = 2005.0
    d_edge, u_edge = _etf_band(ref, rng.uniform(0.05, 0.30, k))
    p = d_edge + rng.uniform(0.0, 1.0, k) * (u_edge - d_edge)
    p[:1000], p[1000:2000], p[2000:3000] = d_edge[:1000], u_edge[1000:2000], ref[2000:3000]
    m = np.abs(rng.normal(0.0, 0.03, k))
    m[::7], m[::11], m[::13] = 0.0, 0.5, 2.0
    for d, u in ((d_edge, u_edge), (np.zeros(k), np.full(k, np.inf))):
        x_u, x_d, q = models._points(p, m, d, u)
        assert ((0.0 <= q) & (q <= 1.0)).all() and (x_d <= p).all() and (p <= x_u).all()
        assert ((d <= x_d) & (x_u <= u)).all()
        assert (np.abs(q * x_u + (1.0 - q) * x_d - p) <= 1e-12 * p).all()
        draw = rng.random(k)
        for theta in (0.0, -3.0, 2.5):
            assert np.array_equal(models.kernel(p, m, d, u, draw, theta),
                                  np.where(draw < models.tilt(q, theta), x_u, x_d))
    clamped = (models._points(p, m, d_edge, u_edge)[0] == u_edge) & (p < u_edge)
    assert clamped.sum() > 1000                      # the upper edge clamps many moves


def test_prices_stay_inside_the_band_and_an_edge_holds():
    rng = np.random.default_rng(12)
    n_paths, steps = 2_000, 300
    d_edge, u_edge = _etf_band(np.full(n_paths, 2005.0), np.full(n_paths, 0.30))
    p = np.full(n_paths, 2005.0)
    path = np.empty((steps, n_paths))
    for j in range(steps):
        m = np.where(rng.random(n_paths) < 0.05, 0.6, np.abs(rng.normal(0.0, 0.04, n_paths)))
        p = models.kernel(p, m, d_edge, u_edge, rng.random(n_paths), float(rng.choice([0.0, -8.0, 8.0])))
        path[j] = p
    assert ((d_edge <= path) & (path <= u_edge)).all()
    at_edge = (path == d_edge) | (path == u_edge)
    assert at_edge[-1].sum() > 100                   # many paths reached an edge
    first = np.where(at_edge.any(axis=0), at_edge.argmax(axis=0), steps)
    for i in np.flatnonzero(first < steps):
        assert (path[first[i]:, i] == path[first[i], i]).all(), i
    for edge in (d_edge, u_edge):
        for theta in (0.0, -8.0, 8.0):
            out = models.kernel(edge, np.full(n_paths, 0.3), d_edge, u_edge, np.linspace(0.0, 1.0, n_paths,
                                endpoint=False), theta)
            assert np.array_equal(out, edge)


def test_tilt_is_identity_at_zero_and_increasing():
    rng = np.random.default_rng(13)
    every = np.r_[rng.random(200_000), 1e-12 * rng.random(20_000), 1.0 - 1e-12 * rng.random(20_000), 0.0, 1.0,
                  5e-324, np.nextafter(1.0, 0.0)]
    assert np.array_equal(models.tilt(every, 0.0), every)            # bit for bit: the no-edge kernel is untouched
    q = np.r_[0.0, np.linspace(1e-6, 1.0 - 1e-6, 999), 1.0]
    thetas = np.linspace(-8.0, 8.0, 161)
    table = np.array([models.tilt(q, t) for t in thetas])
    assert (np.diff(table[:, 1:-1], axis=0) > 0).all()
    assert (table[:, 0] == 0.0).all() and (table[:, -1] == 1.0).all()
    assert ((0.0 <= table) & (table <= 1.0)).all()
    assert abs(models.tilt(np.array([0.5]), math.log(3.0))[0] - 0.75) < 1e-15


def test_market_seed_follows_the_q34_bytes():
    a, b = "c4ca4238a0b923820dcc509a6f75849b", "0cc175b9c0f1b6a831c399e269772661"
    cal = "e" * 64
    hand = hashlib.sha256(b"tradegen-odds/seed/1\x00" + (b + "\x00" + a).encode("ascii") + b"\x00"
                          + cal.encode("ascii") + b"\x00" + "c000001".encode("utf-8") + b"\x00"
                          + (1).to_bytes(8, "big")).digest()
    assert models.SEED_TAG == b"tradegen-odds/seed/1\x00"
    seed = models.market_seed((a, b), cal, "c000001", 1)
    assert seed == hand and len(seed) == 32
    assert models.market_seed((b, a), cal, "c000001", 1) == seed               # sorted inside
    assert models.market_seed(iter((a, b)), cal, "c000001", 1) == seed         # any iterable
    variants = [models.market_seed((a, "1" * 32), cal, "c000001", 1), models.market_seed((a, b, "2" * 32), cal,
                "c000001", 1), models.market_seed((a, b), "", "c000001", 1), models.market_seed((a, b), cal,
                "c000002", 1), models.market_seed((a, b), cal, "c000001", 2), models.market_seed((a, b), cal,
                "비교", 1)]
    assert len({seed, *variants}) == 1 + len(variants)
    for args in (((a, b), cal, "c\x00001", 1), ((a + "\x00",), cal, "c000001", 1), ((a, b), cal, "c000001", -1),
                 ((a, b), cal, "c000001", 2 ** 64), ((a, b), cal, "c000001", True), ((a, b), cal, "c000001", 1.0),
                 ((a, 3), cal, "c000001", 1), (a, cal, "c000001", 1), ((), cal, "c000001", 1),
                 (("",), cal, "c000001", 1), ((a, b), "e\x00", "c000001", 1)):
        try:
            models.market_seed(*args)
        except ValueError:
            pass
        else:
            raise AssertionError(f"market_seed accepted {args!r}")


def test_no_plan_field_can_enter_the_seed():
    assert list(inspect.signature(models.market_seed).parameters) == ["data_hashes", "calendar_digest",
                                                                       "comparison_id", "run_counter"]
    assert list(inspect.signature(models.data_hashes).parameters) == ["series", "replay"]
    s = _series(np.full(300, 100.0), np.full(300, 100.0))
    twin = _series(np.full(300, 100.0), np.full(300, 100.0))                       # equal data, another object
    first = models.market_seed(models.data_hashes(s, None), "", "c000001", 1)
    second = models.market_seed(models.data_hashes(twin, None), "", "c000001", 1)  # no clock, no randomness
    assert first == second
    for name in models.STREAMS:
        for chunk in (0, 1):
            assert np.array_equal(models.stream(first, chunk, name).random(16),
                                  models.stream(second, chunk, name).random(16))
    other = models.market_seed(models.data_hashes(s, None), "", "c000002", 1)
    assert not np.array_equal(models.stream(first, 0, "index").random(16), models.stream(other, 0, "index").random(16))


def test_data_hashes_cover_the_series_components_and_the_replay():
    s = _series(np.full(30, 100.0), np.linspace(100.0, 101.0, 30), components=(("binance BTCUSDT", "9" * 32),
                                                                                ("upbit KRW-USDT", "1" * 32)))
    assert models.data_hashes(s, None) == tuple(sorted((s.md5, "9" * 32, "1" * 32)))
    rep = _replay()
    text = model.canonical_json({"symbol": "KRW-BTC", "source": "UPBIT", "dates": list(rep.input_dates),
                                 "close": list(rep.input_close)})
    in_md5 = hashlib.md5(text.encode("utf-8")).hexdigest()
    pnl_md5 = hashlib.md5(np.array(rep.oos_pnl, dtype="<f8").tobytes()).hexdigest()
    assert models.data_hashes(s, rep) == tuple(sorted((s.md5, "9" * 32, "1" * 32, in_md5, pnl_md5)))
    moved = _replay(input_close=(1.0e7, 1.01e7, 0.98e7))
    assert models.data_hashes(s, moved) != models.data_hashes(s, rep)
    assert models.market_seed(models.data_hashes(s, moved), "", "c000001", 1) != models.market_seed(
        models.data_hashes(s, rep), "", "c000001", 1)
    assert models.data_hashes(s, _replay(oos_pnl=(0.01, -0.0197))) != models.data_hashes(s, rep)


def test_replay_input_md5_is_the_pinned_digest_of_the_committed_cache():
    """The input md5 data_hashes uses is the definition of the pin 18ec83bd... (contract 7.5, section 16)."""
    dates, close = [], []
    with (ROOT / "docs/asset_expansion/cache/upbit_KRW-BTC.csv").open(encoding="utf-8", newline="") as fh:
        reader = csv.reader(fh)
        next(reader)
        for day, value in reader:
            dates.append(day)
            close.append(float(value))
    rep = _replay(input_dates=tuple(dates), input_close=tuple(close))
    assert len(dates) == 3288 and models._input_md5(rep) == "18ec83bdfe158efe4d648caf45ff849f"


def test_streams_are_seed_sequences_through_default_rng():
    assert models.STREAMS == {"index": 1, "sign": 2, "garch": 3, "pilot": 4, "tilt": 5, "kelly": 6, "refit": 7,
                              "replay": 8, "refit_series": 9, "replay_sign": 10}
    assert len(set(models.STREAMS.values())) == len(models.STREAMS)
    ss = models.seed_sequence(SEED, 5, "garch", 2)
    assert type(ss) is np.random.SeedSequence and ss.entropy == int.from_bytes(SEED, "big")
    assert ss.spawn_key == (5, 3, 2)                                 # (chunk, STREAMS["garch"], extra)
    g = models.stream(SEED, 5, "garch", 2)
    assert type(g.bit_generator) is np.random.PCG64
    draws = g.random(8)
    assert np.array_equal(draws, np.random.default_rng(models.seed_sequence(SEED, 5, "garch", 2)).random(8))
    assert np.array_equal(draws, np.random.Generator(np.random.PCG64(models.seed_sequence(SEED, 5, "garch",
                                                                                          2))).random(8))
    passed = models.stream(SEED, 0, "index")
    assert np.random.default_rng(passed) is passed                  # a Generator passes through unchanged
    base = models.stream(SEED, 0, "index").random(8)
    for other in (models.stream(SEED, 1, "index"), models.stream(SEED, 0, "sign"), models.stream(SEED, 0, "index", 1),
                  models.stream(models.market_seed(("1" * 32,), "", "c000001", 1), 0, "index")):
        assert not np.array_equal(base, other.random(8))
    try:
        models.stream(SEED, 0, "sign_flip")
    except KeyError:
        pass
    else:
        raise AssertionError("an unknown stream name was accepted")


def test_zero_log_drift_is_not_zero_edge():
    """Spec 7.2 trap 1: core.quant.montecarlo with drift="zero" adds a log drift of 0, so the terminal mean is above
    the spot by far more than 4 SE; the same model with the convexity correction (drift "rf", rate 0) passes."""
    from core.quant import montecarlo
    from core.quant.history import History
    n = 600
    r = 0.03 * np.random.default_rng(20261024).standard_normal(n - 1)
    closes = 100.0 * np.exp(np.r_[0.0, np.cumsum(r)])
    dates = tuple((dt.date(2024, 1, 1) + dt.timedelta(days=i)).isoformat() for i in range(n))
    hist = History(symbol="FIXTURE", source="SYNTHETIC", dates=dates, closes=tuple(float(c) for c in closes))
    zero = montecarlo.run_monte_carlo(hist, model="bootstrap", n_paths=50_000, horizon_days=21, drift="zero", seed=7,
                                      n_sample_paths=1)
    assert _z(zero.terminal / zero.spot - 1.0) > 4.0
    fair = montecarlo.run_monte_carlo(hist, model="bootstrap", n_paths=50_000, horizon_days=21, drift="rf",
                                      rf_rate=0.0, seed=7, n_sample_paths=1)
    assert abs(_z(fair.terminal / fair.spot - 1.0)) < 4.0


def test_per_row_demeaning_lets_a_stop_rule_harvest_the_pattern():
    """Spec 7.2 trap 2: the rev-1 model (each row's gross move divided by the mean gross move, rows drawn in
    stationary blocks) keeps E[move] = 1 per row but not given the row before, so on an AR(1) history both a 3% stop
    and plain buy-and-hold over 30 sessions have a mean payoff far from 0 (rows inside a block are serially
    dependent, so the mean of their product is not 1). The two-point kernel on the same rows, blocks, stop rule and
    index stream has a mean payoff within 4 SE of 0."""
    r = _ar1(1000, 0.3, 0.02, 7)
    block, n_paths, sessions = models.block_length(r), 50_000, 30

    def run(moves, stop):
        idx_gen = models.indices(models.stream(SEED, 0, "index"), r.size, n_paths, block)
        p, done, payoff = np.ones(n_paths), np.zeros(n_paths, dtype=bool), np.zeros(n_paths)
        for _ in range(sessions):
            for step in moves(next(idx_gen)):
                p = np.where(done, p, step(p))
                hit = ~done & (p <= 1.0 - stop)
                payoff[hit] = p[hit] - 1.0
                done |= hit
        payoff[~done] = p[~done] - 1.0
        return payoff

    gross = np.exp(r) / np.exp(r).mean()

    def demeaned(idx):
        return (lambda p: p * gross[idx],)

    rev1 = run(demeaned, 0.03)
    hold = run(demeaned, math.inf)                       # no stop: p <= 1 - inf never holds
    sign = models.stream(SEED, 0, "sign")
    m_o, m_i = np.abs(0.3 * r), np.abs(0.7 * r)          # the AR(1) move split into an overnight and a day part
    ours = run(lambda idx: (lambda p: models.kernel(p, m_o[idx], 0.0, np.inf, sign.random(n_paths)),
                            lambda p: models.kernel(p, m_i[idx], 0.0, np.inf, sign.random(n_paths))), 0.03)
    assert _z(rev1) > 4.0, _z(rev1)
    assert _z(hold) > 4.0, _z(hold)
    assert abs(_z(ours)) < 4.0, _z(ours)
```

- [ ] **Step 2: Run to verify it fails**

  QUANTGEN overlap check with the PowerShell tool (it must print nothing; otherwise wait and re-run it):

```powershell
Get-CimInstance Win32_Process -Filter "Name LIKE 'python%'" | Where-Object { $_.CommandLine -match 'run_all' } | Select-Object ProcessId,Name,CommandLine
```

  Then, from the repo root in Git Bash:

```bash
.venv/Scripts/python.exe -m tests.odds_acceptance odds_models/
```

  Expected: a traceback, then

```
FAIL odds_models/import ImportError: cannot import name 'models' from 'core.odds' (C:\Users\whydi\OneDrive\Desktop\TRADEGEN\core\odds\__init__.py)

0/1 passed, 1 failed, 0 not run
```

  and exit code 1 (the path in parentheses is the repo's `core\odds\__init__.py`; its separators follow the
  `sys.path` entry). The test imports `plan` before `models`, so `cannot import name 'plan'` here means Task 5 is not
  in place, and any other error means the tree is not the one this task expects: stop in both cases.

- [ ] **Step 3: Implement**

  Create `core/odds/models.py` (whole file, LF):

```python
"""The no-edge models of the odds core, part 1 (spec 7.2, 7.3; odds plan Q10, Q12, Q34): the copied constants, block
length and Sharpe (O1: each pinned against its original by tests/odds_models.py), the two-point bootstrap's row
magnitudes, block lengths, index generator, kernel and tilt, and the market seed with its streams. Pure: no clock,
no file, no network."""
from __future__ import annotations

import hashlib
import math
from collections.abc import Iterator
from typing import TYPE_CHECKING

import numpy as np

from core.compliance import model

if TYPE_CHECKING:
    from core.odds import plan

# --------------------------------------------------------------------------- #
# Copied constants and pieces (contract 7.1)
# --------------------------------------------------------------------------- #
LIVE_SHARPE_MULTIPLIER = 0.60          # == core.quant.gate_stats.LIVE_SHARPE_MULTIPLIER
Z_BOUND = 22                           # == core.quant.garch.Z_BOUND
TRADING_DAYS = 252                     # == core.quant.garch.TRADING_DAYS == core.quant.validate.TRADING_DAYS
NU_NORMAL = 100.0                      # == core.quant.garch.NU_NORMAL


def _optimal_block_length(x) -> tuple[float, float]:
    """Copy of core.quant.gate_stats.optimal_block_length (bit-exact): the (stationary, circular) Politis-White
    block lengths of one series; NaN-free finite input, n >= 20."""
    x = np.asarray(x, dtype=float).ravel()
    if x.size < 20 or not np.all(np.isfinite(x)):
        raise ValueError("pw_block needs at least 20 finite observations")
    nobs = x.size
    eps = x - x.mean()
    b_max = math.ceil(min(3 * math.sqrt(nobs), nobs / 3))
    kn = max(5, int(math.log10(nobs)))
    m_max = int(math.ceil(math.sqrt(nobs))) + kn
    cv = 2 * math.sqrt(math.log10(nobs) / nobs)          # the conservative +/- 2 sqrt(log10 n / n) band
    acv = np.zeros(m_max + 1)
    abs_acorr = np.zeros(m_max + 1)
    opt_m = None
    for i in range(m_max + 1):
        v1 = eps[i + 1:] @ eps[i + 1:]
        v2 = eps[:-(i + 1)] @ eps[:-(i + 1)]
        cross = eps[i:] @ eps[:nobs - i]
        acv[i] = cross / nobs
        abs_acorr[i] = abs(cross) / math.sqrt(v1 * v2) if v1 > 0 and v2 > 0 else 0.0
        if i >= kn and opt_m is None and np.all(abs_acorr[i - kn:i] < cv):
            opt_m = i - kn                                  # first run of kn insignificant autocorrelations
    m = min(2 * max(opt_m, 1) if opt_m is not None else m_max, m_max)
    g, lr_acv = 0.0, acv[0]
    for k in range(1, m + 1):
        lam = 1.0 if k / m <= 0.5 else 2.0 * (1.0 - k / m)  # flat-top (trapezoid) kernel
        g += 2 * lam * k * acv[k]
        lr_acv += 2 * lam * acv[k]
    if lr_acv <= 0:
        return 1.0, 1.0
    b_sb = ((2 * g ** 2) / (2 * lr_acv ** 2)) ** (1 / 3) * nobs ** (1 / 3)
    b_cb = ((2 * g ** 2) / (4 / 3 * lr_acv ** 2)) ** (1 / 3) * nobs ** (1 / 3)
    return float(min(b_sb, b_max)), float(min(b_cb, b_max))


def pw_block(x) -> float:
    """The stationary Politis-White block length: gate_stats.pw_block(x, kind="stationary")."""
    return _optimal_block_length(x)[0]


def sharpe(daily) -> float:
    """Copy of core.quant.validate.sharpe: the annualised Sharpe ratio of the finite entries (nan under two)."""
    d = np.asarray(daily, dtype=float)
    d = d[np.isfinite(d)]
    if d.size < 2:
        return float("nan")
    sd = float(np.std(d, ddof=1))
    return float(np.mean(d) / sd * math.sqrt(TRADING_DAYS)) if sd > 0 else 0.0


# --------------------------------------------------------------------------- #
# The two-point bootstrap (contract 7.2)
# --------------------------------------------------------------------------- #
def rows(series: plan.Series) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(m_o, m_i, r) for t = 1..n-1: the overnight move m_o = |ln(open_t / close_{t-1})|, the intraday move
    m_i = |ln(close_t / open_t)| and the close-to-close log return r = ln(close_t / close_{t-1}) (spec 7.2)."""
    o = np.asarray(series.open, dtype=float)
    c = np.asarray(series.close, dtype=float)
    return np.abs(np.log(o[1:] / c[:-1])), np.abs(np.log(c[1:] / o[1:])), np.log(c[1:] / c[:-1])


def block_length(r: np.ndarray) -> float:
    """The mean block b = max(1, pw(r), pw(r^2)) (spec 7.2 "Blocks"; floored at 1 because pw_block falls below 1 on
    white noise, Q10)."""
    r = np.asarray(r, dtype=float)
    return float(max(1.0, pw_block(r), pw_block(r * r)))


def variant_block(b: float, mult: float, n_rows: int) -> float:
    """A sensitivity block: max(1, floor(mult * b + 0.5)), capped at the history length (Q10: round half up;
    Python's round() rounds half to even, so it is never used here)."""
    return float(min(max(1, math.floor(mult * b + 0.5)), n_rows))


def indices(rng: np.random.Generator, n_rows: int, n_paths: int, block: float) -> Iterator[np.ndarray]:
    """An endless generator of (n_paths,) row indices, one array per step: the Politis-Romano stationary bootstrap,
    vectorised over paths. Step 0 is uniform; each later step restarts a path at a fresh uniform row with
    probability 1 / block, else moves it to the next row mod n_rows. Both draws are made at every step, the restart
    first, so the stream never depends on the outcome. The mean block is exactly `block`."""
    if not (math.isfinite(block) and block >= 1.0):
        raise ValueError(f"the mean block must be a finite number >= 1, got {block!r}")
    return _steps(rng, n_rows, n_paths, 1.0 / block)


def _steps(rng: np.random.Generator, n_rows: int, n_paths: int, restart_p: float) -> Iterator[np.ndarray]:
    idx = rng.integers(0, n_rows, n_paths)
    while True:
        yield idx
        restart = rng.random(n_paths) < restart_p
        fresh = rng.integers(0, n_rows, n_paths)
        idx = np.where(restart, fresh, (idx + 1) % n_rows)


def tilt(q: np.ndarray, theta: float) -> np.ndarray:
    """The assumed-edge tilt q' = q e^theta / (q e^theta + 1 - q) (spec 7.2). Theta 0 gives q back bit for bit
    (exp(0.0) is 1.0 and q + (1 - q) rounds to 1.0 for every q in [0, 1]), so the no-edge kernel is untouched; every
    theta keeps q = 0 and q = 1."""
    q = np.asarray(q, dtype=float)
    w = q * math.exp(theta)
    return w / (w + (1.0 - q))


def _points(p, m, d_edge, u_edge) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(x_u, x_d, q) of the kernel: x_u = min(p e^m, U), x_d = max(p e^-m, D), q = (p - x_d) / (x_u - x_d) where
    x_u > x_d, else 0 (there x_u = x_d = p)."""
    p, m = np.asarray(p, dtype=float), np.asarray(m, dtype=float)
    x_u = np.minimum(p * np.exp(m), u_edge)
    x_d = np.maximum(p * np.exp(-m), d_edge)
    gap = x_u - x_d
    q = np.divide(p - x_d, gap, out=np.zeros(gap.shape), where=gap > 0)
    return x_u, x_d, q


def kernel(p, m, d_edge, u_edge, u, theta: float = 0.0) -> np.ndarray:
    """One check of the no-edge law (spec 7.2 "The kernel"): x_u where u < tilt(q, theta), else x_d. With theta 0,
    q x_u + (1 - q) x_d == p to rounding, so the price is a conditional martingale; it never leaves [D, U], and a
    price at an edge stays there (q is 1 at U and 0 at D)."""
    x_u, x_d, q = _points(p, m, d_edge, u_edge)
    return np.where(u < tilt(q, theta), x_u, x_d)


# --------------------------------------------------------------------------- #
# Seeds and streams (contract 7.2; spec 7.3; Q12, Q34)
# --------------------------------------------------------------------------- #
STREAMS = {"index": 1, "sign": 2, "garch": 3, "pilot": 4, "tilt": 5, "kelly": 6, "refit": 7, "replay": 8,
           "refit_series": 9, "replay_sign": 10}
SEED_TAG = b"tradegen-odds/seed/1\x00"


def _input_md5(rep: plan.ReplayInput) -> str:
    """md5 of the canonical JSON {symbol, source, dates, close} of the replay's input closes (contract 7.5
    `input_md5`)."""
    text = model.canonical_json({"symbol": rep.input_symbol, "source": rep.input_source,
                                 "dates": list(rep.input_dates), "close": list(rep.input_close)})
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def _array_md5(values) -> str:
    """md5 of the little-endian float64 bytes of `values` (contract 7.5 `pnl_md5`, `turnover_md5`)."""
    return hashlib.md5(np.ascontiguousarray(values, dtype="<f8").tobytes()).hexdigest()


def data_hashes(series: plan.Series, replay: plan.ReplayInput | None) -> tuple[str, ...]:
    """The data hashes that enter the market seed, sorted: the series md5 and every component md5, plus for a
    replay leg the input md5 and the pnl md5 (recomputed here; verify_replay requires both to equal their pins)."""
    hashes = [series.md5, *(md5 for _, md5 in series.components)]
    if replay is not None:
        hashes += [_input_md5(replay), _array_md5(replay.oos_pnl)]
    return tuple(sorted(hashes))


def market_seed(data_hashes, calendar_digest: str, comparison_id: str, run_counter: int) -> bytes:
    """The 32-byte market seed of spec 7.3 in the byte layout of Q34. No plan field enters it, so every plan on the
    same data in one comparison shares every stream, and the owner never chooses it. ValueError unless every part is
    a string with no NUL (a NUL would let two different inputs share bytes) and the run counter an int in
    [0, 2**64). One str for data_hashes, no hash, or an empty hash is refused too: each would share bytes with
    another input (the sorted characters of an md5; () and ("",))."""
    if isinstance(data_hashes, str):
        raise ValueError("market_seed needs an iterable of hashes, not one string")
    hashes = tuple(data_hashes)
    if not hashes or not all(type(x) is str and x for x in hashes):
        raise ValueError("market_seed needs one or more hashes, each a non-empty string")
    if not all(type(x) is str and "\x00" not in x for x in (*hashes, calendar_digest, comparison_id)):
        raise ValueError("market_seed needs strings with no NUL character")
    if type(run_counter) is not int or not 0 <= run_counter < 2 ** 64:
        raise ValueError(f"market_seed needs a run counter in [0, 2**64), got {run_counter!r}")
    return hashlib.sha256(SEED_TAG + "\x00".join(sorted(hashes)).encode("ascii") + b"\x00"
                          + calendar_digest.encode("ascii") + b"\x00" + comparison_id.encode("utf-8") + b"\x00"
                          + run_counter.to_bytes(8, "big")).digest()


def seed_sequence(seed: bytes, chunk: int, name: str, *extra: int) -> np.random.SeedSequence:
    """The SeedSequence of stream `name` in chunk `chunk` (spec 7.3): entropy int.from_bytes(seed, "big"), spawn_key
    (chunk, STREAMS[name], *extra). The copied GARCH code calls default_rng(seed) and takes it directly."""
    return np.random.SeedSequence(int.from_bytes(seed, "big"), spawn_key=(chunk, STREAMS[name], *extra))


def stream(seed: bytes, chunk: int, name: str, *extra: int) -> np.random.Generator:
    """The Generator of stream `name`: np.random.default_rng(seed_sequence(seed, chunk, name, *extra)), a PCG64
    (default_rng passes a SeedSequence through)."""
    return np.random.default_rng(seed_sequence(seed, chunk, name, *extra))
```

- [ ] **Step 4: Run to verify it passes**

  Run the overlap check of Step 2 (PowerShell tool; it must print nothing) before EACH Python command below. All
  run from the repo root in Git Bash.

  Overlap check, then:

```bash
.venv/Scripts/python.exe -m tests.odds_acceptance odds_models/
```

  Expected: these 19 lines (in this order, each with nothing after the name), then
  `19/19 passed, 0 failed, 0 not run` (exit code 0; the module's test time is about 3 to 4 s, inside its 6 s
  budget):

```
PASS odds_models/test_block_length_floors_at_one_and_takes_the_larger
PASS odds_models/test_copied_constants_equal_the_originals
PASS odds_models/test_data_hashes_cover_the_series_components_and_the_replay
PASS odds_models/test_index_generator_draws_in_the_contract_order
PASS odds_models/test_index_generator_mean_block_is_the_block
PASS odds_models/test_index_generator_rows_stay_uniform
PASS odds_models/test_kernel_is_a_martingale_to_1e_12
PASS odds_models/test_market_seed_follows_the_q34_bytes
PASS odds_models/test_no_plan_field_can_enter_the_seed
PASS odds_models/test_per_row_demeaning_lets_a_stop_rule_harvest_the_pattern
PASS odds_models/test_prices_stay_inside_the_band_and_an_edge_holds
PASS odds_models/test_pw_block_equals_the_original_on_a_grid
PASS odds_models/test_replay_input_md5_is_the_pinned_digest_of_the_committed_cache
PASS odds_models/test_rows_are_the_two_magnitudes_and_the_close_return
PASS odds_models/test_sharpe_equals_the_original
PASS odds_models/test_streams_are_seed_sequences_through_default_rng
PASS odds_models/test_tilt_is_identity_at_zero_and_increasing
PASS odds_models/test_variant_blocks_round_half_up_and_cap_at_the_history
PASS odds_models/test_zero_log_drift_is_not_zero_edge
```

  A failing assertion that prints a z value or a p-value means the numbers above did not reproduce: record the
  printed value in the execution ledger under "Deferred minors" and stop; never loosen a bound.

  Overlap check, then the odds guards, which now scan `core/odds/models.py` too:

```bash
.venv/Scripts/python.exe -m tests.odds_acceptance odds_guards/
```

  Expected: every line PASS, ending `N/N passed, 0 failed, 0 not run` with the N Task 6 ended with (exit code 0). A
  failure names the file and the text: fix `models.py`, never the guard (see the `series.open` design note).

  Overlap check before each, then the compliance guards and store:

```bash
.venv/Scripts/python.exe -m tests.compliance_acceptance compliance_guards/
.venv/Scripts/python.exe -m tests.compliance_acceptance compliance_store/
```

  Expected: each ends `N/N passed, 0 failed, 0 not run` with the counts Task 6 ended with (exit code 0).
  `compliance_store/test_code_files_is_the_import_closure` now finds `core/odds/models.py` in the closure; its
  expected set is the `core/odds/*.py` glob, so it passes unchanged, and `models.py` adds no new in-repo file
  (`core.compliance.model` is already in the closure; numpy is third party and never hashed).

  Overlap check before each, then the core-wide scans:

```bash
.venv/Scripts/python.exe -m tests.macro_m0_harness
.venv/Scripts/python.exe -m tests.macro_tf_gov
.venv/Scripts/python.exe -m tests.macro_m7_ledger
.venv/Scripts/python.exe -m tests.macro_m8_forward
.venv/Scripts/python.exe -m tests.macro_m6_context
KIS_APP_KEY='<unset>' KIS_APP_SECRET='<unset>' KIS_ACCOUNT_8='<unset>' KIS_ACCOUNT_PD='<unset>' UPBIT_ACCESS_KEY='<unset>' UPBIT_SECRET_KEY='<unset>' OKX_API_KEY='<unset>' OKX_API_SECRET='<unset>' OKX_API_PASSPHRASE='<unset>' OPENDART_API_KEY='<unset>' KRX_API_KEY='<unset>' FMP_API_KEY='<unset>' ANTHROPIC_API_KEY='<unset>' GS_CLIENT_ID='<unset>' GS_CLIENT_SECRET='<unset>' FINVIZ_API_KEY='<unset>' ALPACA_API_KEY='<unset>' ALPACA_SECRET_KEY='<unset>' FXMACRODATA_API_KEY='<unset>' .venv/Scripts/python.exe tests/run_all.py --suite cockpit; echo "exit $?"; git checkout -- qa/acceptance_results.json
```

  Expected: each `-m` run's last line reports `0 failed` (exit code 0); the cockpit suite exits 0 with test_08,
  test_09, test_16 and test_18 PASS; the `git checkout` restores the CRLF results file the suite rewrote.

  Then the raw-text checks (git only, no overlap check needed):

```bash
git grep --untracked -n -i -E "order_cash|order-cash|place_order|submit_order|tttc0802u|tttc0801u|vttc0802u|private_key|seed_phrase|/v1/orders|/v1/withdraws|/v1/deposits|/api/v3/order|/sapi/v1/capital|/trading/|r18_research_log|r18_break_log|context_log/|tests\.reference|reference_mode|reference_only" -- core/odds/models.py
git grep --untracked -n -E "CANO|KIS_ACCOUNT|ACNT_PRDT_CD|kish|datetime|date\.today|time\.|perf_counter|monotonic|__main__|open\(|\.read_|\.write_|\.load\(|\.save" -- core/odds/models.py
git status --short
```

  Expected: both greps print nothing (exit code 1), and `git status --short` prints exactly:

```
?? core/odds/models.py
?? docs/superpowers/plans/2026-10-24-odds-engine-execution-ledger.md
?? tests/odds_models.py
```

  Append one line under "Runs" in the execution ledger (LF, Edit tool):
  `- Task 7: odds_models 19/19 PASS; odds_guards, compliance_guards, compliance_store and the core-wide scans 0 failed.`

- [ ] **Step 5: Commit**

```bash
git add core/odds/models.py tests/odds_models.py
git diff --cached --stat
git diff --cached --stat --ignore-cr-at-eol
```

  The two stat outputs must be identical (both files are new and LF): `core/odds/models.py | 209`,
  `tests/odds_models.py | 410`, `2 files changed, 619 insertions(+)`. Then:

```bash
git commit -m "feat(odds): two-point bootstrap, block lengths, index generator, seeds" -m "Task 7: core/odds/models.py part 1 (pw_block, sharpe and the constants copied with equality tests; kernel, tilt, Politis-Romano indices, the Q34 seed and its streams) and tests/odds_models.py." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
