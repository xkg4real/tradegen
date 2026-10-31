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
