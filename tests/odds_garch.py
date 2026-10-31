"""The GARCH-t copy and its pilot checks (odds plan Task 8; spec 7.2 "GarchT"; 8.o item 1; O1, O10, R2-9; Q10,
Q31). Every copied piece of core/odds/models.py is pinned against core/quant/garch.py; both pilot checks pass on two
fixture fits at 30 and 90 steps with the real 20,000 paths and 512 nodes, and fail on a corrupted correction table
and on zero log drift."""
from __future__ import annotations

import contextlib
import dataclasses
import functools
import math

import numpy as np

from core.odds import models
from core.quant import garch

SEED = models.market_seed(("0" * 32,), "", "c000001", 1)   # every pilot here: the real "pilot" stream (R2-9)
FIXTURES = {
    "nu56": garch.simulate_garch_series(2e-6, 0.08, 0.90, 6.0, n=1500, seed=1),     # fits nu about 5.6
    "nu46": garch.simulate_garch_series(5e-5, 0.08, 0.90, 5.0, n=1500, seed=1),     # fits nu about 4.6
    "normal": np.random.default_rng(2).normal(0.0004, 0.012, 500),                    # fits eta 0, so nu inf
}
OFFSET = 2e-6          # c + OFFSET at every node: check 1 must see it (contract 7.4)
RATIO_FACTOR = 3.0     # the ratio column x RATIO_FACTOR: check 2 must see it at 90 steps (R2-9: raise, never lower)
LOG_DRIFT = 0.0        # zero log drift: check 2 must see it at 90 steps (R2-9: a d > 0 here if it ever falls under 4)
# c_quad is pure and the table never moves sigma, so a corrupted pilot has the clean pilot's nodes: the pilot tests
# share this memo of the real c_quad and run quad once per (fit, horizon) instead of once per pilot
_QUAD = functools.lru_cache(maxsize=None)(models.c_quad)


@functools.lru_cache(maxsize=None)
def _fits(name: str) -> tuple[models.GarchParams, garch.GarchFit]:
    """(the odds fit, the original fit) of one fixture series, computed once per process."""
    r = FIXTURES[name]
    return models.fit_garch_t(r), garch.fit_garch(r, profile=False)


@contextlib.contextmanager
def _swap(**values):
    """Set attributes of core.odds.models for the block; restored in finally."""
    saved = {name: getattr(models, name) for name in values}
    for name, value in values.items():
        setattr(models, name, value)
    try:
        yield
    finally:
        for name, value in saved.items():
            setattr(models, name, value)


def _table(change):
    """models._correction_table replaced by change(*real(nu, bound)) for the block (restored in finally), the real
    lru cache cleared as contract 7.4 asks; martingale_correction reaches the wrapper by its call-time lookup."""
    real = models._correction_table
    real.cache_clear()
    return _swap(_correction_table=lambda nu, bound: change(*real(nu, bound)))


def _memo():
    """pilot_checks with the shared memo of the real c_quad."""
    return _swap(c_quad=_QUAD)


def _pilot_draws(make):
    """models.simulate_garch replaced by make(real, fit, **kw), so pilot_checks judges other draws."""
    real = models.simulate_garch
    return _swap(simulate_garch=lambda fit, **kw: make(real, fit, **kw))


def _offset(z, wt, grid, ratio):
    """The ratio column holds c / sigma^2, so adding OFFSET / grid^2 moves c by OFFSET at every node."""
    return z, wt, grid, ratio + OFFSET / grid ** 2


def _scaled(z, wt, grid, ratio):
    return z, wt, grid, RATIO_FACTOR * ratio


def _scaled_pilot(real, fit, **kw):
    """The pilot drawn with the scaled table while check 1 judges the real one (sigma never depends on the table),
    so only check 2 can see the scaled correction."""
    with _table(_scaled):
        return real(fit, **kw)


def _drift_pilot(name: str):
    """The pilot's returns replaced by those of garch.simulate_returns with drift_daily=LOG_DRIFT on the same
    SeedSequence: the same innovations and sigma, with a constant log drift in place of the correction."""
    def make(real, fit, *, n_paths, horizon, seed):
        _, sigma = real(fit, n_paths=n_paths, horizon=horizon, seed=seed)
        ret = garch.simulate_returns(_fits(name)[1], n_paths=n_paths, horizon=horizon, seed=seed,
                                     drift_daily=LOG_DRIFT)[0]
        return ret, sigma
    return make


def _table_plus(err):
    """A c_quad that returns the table's own value plus err(sigma): a known check-1 error at every node."""
    def fake(sigma, nu, bound=models.Z_BOUND):
        return float(models.martingale_correction(sigma, nu, "t")[0]) + err(sigma)
    return fake


def test_copied_constants_equal_the_originals():
    assert (models._SIG_LO, models._SIG_HI) == (garch._SIG_LO, garch._SIG_HI) == (1e-6, 0.25)
    assert models._BOUNDS == {k: garch.BOUNDS[k] for k in ("omega", "alpha", "beta", "eta")}
    assert models._STATIONARITY_MAX == garch.STATIONARITY_MAX
    assert (models._ETA_EPS, models._PENALTY, models._MIN_OBS, models._OMEGA_SCALE) == (
        garch._ETA_EPS, garch._PENALTY, garch._MIN_OBS, garch._OMEGA_SCALE)
    assert models.Z_BOUND == garch.Z_BOUND and models.NU_NORMAL == garch.NU_NORMAL
    assert (models.PILOT_PATHS, models.PILOT_NODES, models.PILOT_STEP_TOL, models.PILOT_SUM_TOL,
            models.PILOT_SE) == (20_000, 512, 1e-7, 1e-6, 4.0)
    assert models._correction_table.cache_info().maxsize == garch._correction_table.cache_info().maxsize == 32


def test_fit_garch_t_equals_the_original_field_by_field():
    names = [f.name for f in dataclasses.fields(models.GarchParams)]
    assert names == ["dist", "omega", "alpha", "beta", "nu", "mean_daily", "n_obs", "cond_vol_last", "converged",
                     "at_bound"]
    for key in FIXTURES:
        mine, theirs = _fits(key)
        for name in names:
            assert getattr(mine, name) == getattr(theirs, name), (key, name, getattr(mine, name))
            assert type(getattr(mine, name)) is type(getattr(theirs, name)), (key, name)
        assert mine.dist == "t" and mine.converged and mine.n_obs == FIXTURES[key].size
    assert 5.4 < _fits("nu56")[0].nu < 5.8 and 4.4 < _fits("nu46")[0].nu < 4.8
    near = _fits("normal")[0]
    assert math.isinf(near.nu) and near.at_bound                 # eta 0 and a guardrail hit, both copied
    try:
        near.nu = 5.0
    except dataclasses.FrozenInstanceError:
        pass
    else:
        raise AssertionError("GarchParams is not frozen")


def test_fit_garch_t_refuses_fewer_than_100_returns():
    r = FIXTURES["nu56"]
    for n in (0, 1, 99):
        for fn in (models.fit_garch_t, lambda x: garch.fit_garch(x, profile=False)):
            try:
                fn(r[:n])
            except ValueError as exc:
                assert str(exc) == f"Need at least 100 observations to fit GARCH; got {n}.", exc
            else:
                raise AssertionError(f"a fit on {n} returns was accepted")
    assert models.fit_garch_t(list(r[:100])) == models.fit_garch_t(r[:100])        # any array-like; 100 is enough


def test_likelihood_pieces_equal_the_original():
    eps = FIXTURES["nu46"] - FIXTURES["nu46"].mean()
    eps2, var = eps ** 2, float(np.var(eps))
    for nu in (2.51, 4.6, 30.0, 9_999.0, 1e5, 1e8):               # both branches of _t_const
        assert models._t_const(nu) == garch._t_const(nu), nu
    for params in ([5e-5, 0.08, 0.90, 0.2], [5e-5, 0.08, 0.90, 0.0], [5e-5, 0.0, 0.0, 1e-11], [5e-5, 0.5, 0.4999, 0.1],
                   [5e-5, 0.3, 0.6995, 0.4], [-1.0, 0.0, 0.0, 0.1]):
        p = np.array(params)
        assert np.array_equal(models._variance_path(eps2, *p[:3], var), garch._variance_path(eps2, *p[:3], var))
        for dist in ("t", "normal"):
            assert models._loglik(p, eps, eps2, var, dist) == garch._loglik(p, eps, eps2, var, dist), (params, dist)
    assert models._loglik(np.array([5e-5, 0.5, 0.4999, 0.1]), eps, eps2, var, "t") == -1e10   # past stationarity
    assert models._loglik(np.array([-1.0, 0.0, 0.0, 0.1]), eps, eps2, var, "t") == -1e10      # a negative variance
    for dist in ("t", "normal"):
        mine, theirs = models._fit(eps, dist), garch._fit(eps, dist)
        assert np.array_equal(mine[0], theirs[0]) and mine[1:4] == theirs[1:4] and np.array_equal(mine[4], theirs[4])


def test_t_density_scale_and_draws_equal_the_original():
    z = np.linspace(-25.0, 25.0, 2_001)
    for nu in (2.51, 2.6, 5.618, 100.0, 150.0, math.inf):
        assert np.array_equal(models.t_density(z, nu), garch.t_density(z, nu)), nu
        if math.isfinite(nu):
            assert models._t_scale(nu) == garch._t_scale(nu)
    unbounded = models._draw_z(np.random.default_rng(3), 2.6, "t", (400, 500), bound=None)
    replaced = np.abs(unbounded) > models.Z_BOUND
    assert replaced.sum() >= 5                                  # the inverse-CDF branch runs
    bounded = models._draw_z(np.random.default_rng(3), 2.6, "t", (400, 500))
    assert np.array_equal(bounded[~replaced], unbounded[~replaced]) and (bounded[replaced] != unbounded[replaced]).all()
    cases = ((2.6, "t", (400, 500), models.Z_BOUND), (2.6, "t", (400, 500), None), (5.618, "t", 10_000, 22),
             (150.0, "t", 1_000, 22), (math.inf, "t", 1_000, 22), (5.0, "normal", 1_000, 22))
    for nu, dist, size, bound in cases:
        mine = models._draw_z(np.random.default_rng(3), nu, dist, size, bound)
        assert np.array_equal(mine, garch._draw_z(np.random.default_rng(3), nu, dist, size, bound)), (nu, dist)
        if bound is not None:
            assert np.abs(mine).max() <= bound
    sig, nodes, wt = np.geomspace(1e-4, 0.4, 50), np.linspace(-22.0, 22.0, 301), np.full(301, 1.0 / 301)
    assert np.array_equal(models._log_mgf(sig, nodes, wt), garch._log_mgf(sig, nodes, wt))


def test_correction_table_and_martingale_correction_equal_the_original():
    sig = np.r_[np.geomspace(1e-7, 0.4, 400), 0.25, 0.2500001, 0.5]        # below, on and above the sigma grid
    for nu in (2.6, _fits("nu46")[0].nu, _fits("nu56")[0].nu):
        for mine, theirs in zip(models._correction_table(nu, 22.0), garch._correction_table(nu, 22.0), strict=True):
            assert np.array_equal(mine, theirs), nu
        assert np.array_equal(models.martingale_correction(sig, nu, "t"), garch.martingale_correction(sig, nu, "t"))
        assert np.array_equal(models.martingale_correction(0.013, nu, "t"),
                              garch.martingale_correction(0.013, nu, "t"))
        try:
            models.martingale_correction(sig, nu, "t", bound=None)
        except ValueError as exc:
            assert "no finite expectation" in str(exc)
        else:
            raise AssertionError("an unbounded t got a correction")
    for nu, dist in ((150.0, "t"), (math.inf, "t"), (5.0, "normal")):
        out = models.martingale_correction(sig, nu, dist, bound=None)
        assert np.array_equal(out, garch.martingale_correction(sig, nu, dist, bound=None))
        assert np.array_equal(out, 0.5 * sig ** 2)


def test_c_quad_agrees_with_the_table_and_the_normal():
    for nu in (2.6, _fits("nu46")[0].nu, _fits("nu56")[0].nu):
        for s in (1e-4, 0.01, 0.05, 0.2, 0.3):
            gap = models.c_quad(s, nu) - float(models.martingale_correction(s, nu, "t")[0])
            assert abs(math.expm1(gap)) <= 1e-7, (nu, s, gap)
    for nu in (100.0 + 1e-9, 150.0, math.inf):
        assert models.c_quad(0.03, nu) == 0.5 * 0.03 ** 2
    for bound in (4.0, 10.0):                                   # the bound reaches both integrals
        gap = models.c_quad(0.05, 6.0, bound=bound) - float(models.martingale_correction(0.05, 6.0, "t", bound)[0])
        assert abs(math.expm1(gap)) <= 1e-7, (bound, gap)


def test_simulate_garch_equals_simulate_returns_at_rate_zero():
    for key in ("nu56", "nu46", "normal"):
        mine, theirs = _fits(key)
        ret, sigma = models.simulate_garch(mine, n_paths=3_000, horizon=40,
                                           seed=models.seed_sequence(SEED, 3, "garch", 1))
        want = garch.simulate_returns(theirs, n_paths=3_000, horizon=40,
                                      seed=models.seed_sequence(SEED, 3, "garch", 1), rate_daily=0.0,
                                      bound=garch.Z_BOUND)[0]
        assert ret.shape == sigma.shape == (3_000, 40) and np.array_equal(ret, want), key
        assert np.array_equal(sigma[:, 0], np.full(3_000, math.sqrt(mine.cond_vol_last ** 2 / models.TRADING_DAYS)))
        eps = ret + models.martingale_correction(sigma.ravel(), mine.nu, mine.dist).reshape(sigma.shape)
        s2 = mine.omega + mine.alpha * eps[:, :-1] ** 2 + mine.beta * sigma[:, :-1] ** 2
        assert np.allclose(sigma[:, 1:] ** 2, s2, rtol=1e-12, atol=0.0), key          # the kept sigma is the path's
        again = models.simulate_garch(mine, n_paths=3_000, horizon=40, seed=models.stream(SEED, 3, "garch", 1))
        assert np.array_equal(again[0], ret) and np.array_equal(again[1], sigma)       # a Generator passes through
    # nu 2.6 (eta near its 0.4 bound): the bound replaces draws on this stream, so the equality pins bound=Z_BOUND
    heavy, heavy_g = (dataclasses.replace(f, nu=2.6) for f in _fits("nu46"))
    ss = models.seed_sequence(SEED, 3, "garch", 2)
    raw = models._draw_z(np.random.default_rng(ss), 2.6, "t", (3_000, 40), bound=None)
    assert (np.abs(raw) > models.Z_BOUND).any()
    ret = models.simulate_garch(heavy, n_paths=3_000, horizon=40, seed=ss)[0]
    assert np.array_equal(ret, garch.simulate_returns(heavy_g, n_paths=3_000, horizon=40, seed=ss, rate_daily=0.0,
                                                      bound=garch.Z_BOUND)[0])


def test_simulate_garch_series_equals_the_original():
    refit_seed = models.seed_sequence(SEED, 0, "refit_series", 3)
    for args, kw in (((2e-6, 0.08, 0.90, 6.0), {"n": 1500, "seed": 1}),
                     ((5e-5, 0.08, 0.90, 5.0), {"n": 300, "seed": 9}),
                     ((1e-5, 0.1, 0.9, 6.0), {"n": 200, "seed": 4}),
                     ((2e-6, 0.08, 0.90, 2.6), {"n": 2000, "seed": 3}),
                     ((2e-6, 0.08, 0.90, math.inf), {"n": 400, "seed": refit_seed}),
                     ((2e-6, 0.08, 0.90, 6.0), {"n": 400, "seed": 5, "dist": "normal"})):
        mine = models.simulate_garch_series(*args, **kw)
        assert mine.shape == (kw["n"],) and np.array_equal(mine, garch.simulate_garch_series(*args, **kw)), args
    # the nu 2.6 case draws past Z_BOUND (seed 3, 2,000 + 500 burn-in draws), so the equality pins bound=None
    assert (np.abs(models._draw_z(np.random.default_rng(3), 2.6, "t", 2_500, bound=None)) > models.Z_BOUND).any()


def test_both_pilot_checks_pass_on_the_fixture_fits():
    """20,000 paths and 512 nodes, no pilots() swap: check 1 within 1e-7 per step and 1e-6 summed, check 2 within
    4 SE at every step, on the fits with nu about 5.6 and about 4.6, at 30 and 90 steps."""
    with _memo():
        for key in ("nu56", "nu46"):
            for horizon in (30, 90):
                assert models.pilot_checks(_fits(key)[0], horizon, SEED) == (True, ""), (key, horizon)


def test_pilot_checks_reads_its_sizes_and_stream_at_call_time():
    seen, quads, drawn = [], [], []
    real_quad = models.c_quad

    def record(real, fit, **kw):
        seen.append(kw)
        drawn.append(real(fit, **kw))
        return drawn[-1]

    def counted(sigma, nu, bound=models.Z_BOUND):
        quads.append(sigma)
        return real_quad(sigma, nu, bound)

    with _swap(PILOT_PATHS=500, PILOT_NODES=16, c_quad=counted), _pilot_draws(record):
        assert models.pilot_checks(_fits("nu56")[0], 12, SEED) == (True, "")
    assert len(seen) == 1 and seen[0]["n_paths"] == 500 and seen[0]["horizon"] == 12
    ss = seen[0]["seed"]
    assert type(ss) is np.random.SeedSequence and ss.entropy == int.from_bytes(SEED, "big")
    assert ss.spawn_key == (0, models.STREAMS["pilot"])
    want = np.unique(np.quantile(drawn[0][1].ravel(), np.linspace(0.0, 1.0, 16))).tolist()
    assert 2 <= len(quads) <= 16 and quads == want                  # the distinct quantile nodes, in order


def test_deterministic_check_sums_each_paths_nearest_node_errors():
    """Each sigma takes its nearest node's error and check 1 sums their sizes over each path's horizon: with nodes
    0.010 and 0.050 (PILOT_NODES 2) and errors 1e-7 and -3e-7 (opposite signs, so a signed max or a signed sum would
    cancel), the rows below sum to 3e-7, 7e-7 and 7e-7. An error of 9e-8 per step passes the 1e-7 step bound but its
    sum fails 1e-6 from 12 steps on."""
    fit = _fits("nu56")[0]
    sigma = np.array([[0.012, 0.012, 0.012], [0.049, 0.049, 0.010], [0.010, 0.050, 0.050]])
    with _swap(PILOT_NODES=2, c_quad=_table_plus(lambda s: -3e-7 if s > 0.03 else 1e-7)):
        step, summed = models._deterministic_gap(fit, sigma)
    assert math.isclose(step, -math.expm1(-3e-7), rel_tol=1e-6) and math.isclose(summed, 7e-7, rel_tol=1e-6)
    with _swap(PILOT_PATHS=500, c_quad=_table_plus(lambda s: 9e-8)):
        assert models.pilot_checks(fit, 11, SEED) == (True, "")                  # 11 x 9e-8 = 9.9e-7
        assert models.pilot_checks(fit, 12, SEED) == (False, "deterministic")    # 12 x 9e-8 = 1.08e-6


def test_an_offset_correction_table_fails_the_deterministic_check():
    """c + 2e-6 at every node (the ratio column plus 2e-6 / grid^2): max |expm1| 2.0e-6 > 1e-7, at 30 and 90 steps
    on the real pilot (contract 7.4). Adding a constant to the ratio itself would move c by only that constant x
    sigma^2, which no check can see."""
    fit = _fits("nu56")[0]
    with _memo(), _table(_offset):
        for horizon in (30, 90):
            assert models.pilot_checks(fit, horizon, SEED) == (False, "deterministic"), horizon
    assert np.array_equal(models.martingale_correction([0.01, 0.3], fit.nu, "t"),
                          garch.martingale_correction([0.01, 0.3], fit.nu, "t"))           # restored


def test_a_scaled_correction_table_fails_the_statistical_check():
    """The ratio x RATIO_FACTOR (x 3: a drift of -2c per step), drawn into the pilot while check 1 judges the real
    table: check 2 fails it at 90 steps. A table scaled everywhere is caught first by check 1."""
    fit = _fits("nu56")[0]
    with _memo(), _pilot_draws(_scaled_pilot):
        assert models.pilot_checks(fit, 90, SEED) == (False, "statistical")
    with _memo(), _table(_scaled):
        assert models.pilot_checks(fit, 90, SEED) == (False, "deterministic")


def test_zero_log_drift_fails_the_statistical_check():
    """Zero LOG drift is not zero edge: garch.simulate_returns with drift_daily=0.0, fed to check 2, fails at 90 steps
    on both fixture fits. Check 2 sees a per-step drift error only above about 4 sigma / sqrt(N h) (about 3e-5 at
    sigma 0.01, N 20,000, h 90); zero log drift is an error of c, about sigma^2 / 2 per step, which the nu 5.6 fit
    (daily sigma about 0.008) shows at 90 steps but not at 30, so 30 steps are not asserted."""
    for key in ("nu56", "nu46"):
        with _memo(), _pilot_draws(_drift_pilot(key)):
            assert models.pilot_checks(_fits(key)[0], 90, SEED) == (False, "statistical"), key


def test_statistical_z_counts_standard_errors_of_the_cumulative_mean():
    """Two paths, ln 2 and ln 0.5 at both steps: e is (2, 0.5) then (4, 0.25); the z of step 2 is
    |2.125 - 1| / (std(ddof=1) / sqrt(2)) = 1.125 / 1.875 = 0.6, the larger of the two (step 1: 1/3). Reversed in
    time (e is (4, 0.25) then (2, 0.5)) the 0.6 is at step 1, so a check of the last step alone gives 1/3."""
    ret = np.log([[2.0, 2.0], [0.5, 0.5]])
    assert math.isclose(models._statistical_z(ret), 0.6, rel_tol=1e-12)
    assert math.isclose(models._statistical_z(ret[:, :1]), 1.0 / 3.0, rel_tol=1e-12)
    assert math.isclose(models._statistical_z(np.log([[4.0, 0.5], [0.25, 2.0]])), 0.6, rel_tol=1e-12)


def test_both_checks_fail_closed_on_nan():
    fit = _fits("nu56")[0]

    def nan_return(real, params, **kw):
        ret, sigma = real(params, **kw)
        ret[7, 5] = math.nan
        return ret, sigma

    with _swap(PILOT_PATHS=500, PILOT_NODES=16):
        with _pilot_draws(nan_return):
            assert models.pilot_checks(fit, 12, SEED) == (False, "statistical")
        with _swap(c_quad=lambda sigma, nu, bound=models.Z_BOUND: math.nan):
            assert models.pilot_checks(fit, 12, SEED) == (False, "deterministic")
    flat = dataclasses.replace(fit, dist="normal")                  # sigma^2/2 against sigma^2/2
    assert models._deterministic_gap(flat, np.full((10, 3), 0.01)) == (0.0, 0.0)
