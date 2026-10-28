### Task 8: The GARCH-t copy and its pilot checks (`core/odds/models.py` part 2)

**Files:**
- Modify: `core/odds/models.py` (LF; two anchors: the module docstring with the import block at the top of the file,
  and the function `stream`, the last function of the file; Task 7 created the file, so both old texts are Task 7's
  exact text)
- Create: `tests/odds_garch.py` (LF, UTF-8, no BOM)
- Test: `tests/odds_garch.py` (already listed in `tests/odds_acceptance.MODULES` since Task 1)

The DRIFT RULE has nothing to apply to here: `core/odds/models.py` is this plan's own file, and the original the
tests compare against, `core/quant/garch.py`, is not in the follow-up's change list (followup CONTRACT section 12)
and is not edited. If a reviewer changed Task 7's text before this task runs, re-read `core/odds/models.py`, apply
the same two changes to the current text and record a one-line ruling in the execution ledger under "Drift rulings".

**Interfaces:**
- Consumes:
  - Task 7 (`core.odds.models`): `Z_BOUND = 22`, `TRADING_DAYS = 252`, `NU_NORMAL = 100.0`, `STREAMS` (`"garch": 3`,
    `"pilot": 4`, `"refit_series": 9`), `market_seed(data_hashes, calendar_digest, comparison_id, run_counter) ->
    bytes`, `seed_sequence(seed, chunk, name, *extra) -> np.random.SeedSequence`, `stream(seed, chunk, name, *extra)
    -> np.random.Generator`; the module docstring, the import block and the function `stream`, quoted in Step 3.
  - Task 1: `tests/odds_acceptance.py` (`MODULES` holds `"odds_garch"`; `_wrap` runs each test inside `hermetic()`
    and `temp_home()`); `tests/odds_guards.py` (scans every `core/odds/*.py`, so the new code is checked with no
    change there).
  - Tests only, the original (`core/quant/garch.py`, read, never edited): `fit_garch(returns, *, dist="t",
    profile=True) -> GarchFit`; `GarchFit` (its fields `dist`, `omega`, `alpha`, `beta`, `nu`, `mean_daily`,
    `n_obs`, `cond_vol_last`, `converged` and `at_bound`, among others); `simulate_returns(fit, *, n_paths, horizon, seed=7,
    drift_daily=None, rate_daily=None, bound=Z_BOUND) -> tuple[np.ndarray, float]`; `simulate_garch_series(omega,
    alpha, beta, nu, *, n, seed, dist="t")`; `martingale_correction`, `_correction_table`, `_draw_z`, `t_density`,
    `_t_scale`, `_t_const`, `_log_mgf`, `_variance_path`, `_loglik`, `_fit`; `BOUNDS`, `STATIONARITY_MAX`, `_SIG_LO`,
    `_SIG_HI`, `_ETA_EPS`, `_PENALTY`, `_MIN_OBS`, `_OMEGA_SCALE`, `Z_BOUND`, `NU_NORMAL`.
- Produces (`core/odds/models.py`, CONTRACT 7.3 and 7.4, exact names):
  - `GarchParams`: `@dataclass(frozen=True, kw_only=True)` with the fields, in this order, `dist: str`, `omega:
    float`, `alpha: float`, `beta: float`, `nu: float` (inf when the fitted eta is 0), `mean_daily: float`, `n_obs:
    int`, `cond_vol_last: float` (annualised with 252), `converged: bool`, `at_bound: tuple[str, ...]`. Every field
    equals the same field of `garch.fit_garch(r, profile=False)`. `kw_only=True` is added to CONTRACT 7.3's
    `@dataclass(frozen=True)` to match every other plan type (Q4, CONTRACT 5.2); every caller builds it by keyword
    (this task's `fit_garch_t`, Task 9's `_FIT`) and it stays frozen and hashable for Task 14.
  - `fit_garch_t(returns: np.ndarray) -> GarchParams` (ValueError `"Need at least 100 observations to fit GARCH; got N."` under
    100 returns, the original's text).
  - `t_density(z, nu) -> np.ndarray`; `martingale_correction(sigma_daily, nu, dist, bound=Z_BOUND) -> np.ndarray`;
    `simulate_garch(fit, *, n_paths: int, horizon: int, seed) -> tuple[np.ndarray, np.ndarray]` (`(ret, sigma)`, both
    `(n_paths, horizon)`; `seed` is anything `np.random.default_rng` takes: a SeedSequence from `seed_sequence` or a
    Generator from `stream`); `simulate_garch_series(omega, alpha, beta, nu, *, n: int, seed, dist: str = "t") -> np.ndarray`.
  - `PILOT_PATHS = 20_000`, `PILOT_NODES = 512`, `PILOT_STEP_TOL = 1e-7`, `PILOT_SUM_TOL = 1e-6`, `PILOT_SE = 4.0`,
    all read at call time (so `tests/odds_fixtures.pilots()` can swap `PILOT_PATHS` and `PILOT_NODES`);
    `c_quad(sigma: float, nu: float, bound: float = Z_BOUND) -> float`; `pilot_checks(fit: GarchParams, horizon: int,
    seed: bytes) -> tuple[bool, str]`, which returns `(True, "")` or `(False, "deterministic")` or `(False,
    "statistical")`, the first check that fails.
  - Private copies (same bodies as garch's): `_SIG_LO`, `_SIG_HI`, `_BOUNDS` (garch's `BOUNDS` on the four fitted
    coordinates omega, alpha, beta, eta), `_STATIONARITY_MAX`, `_ETA_EPS`, `_PENALTY`, `_MIN_OBS`, `_OMEGA_SCALE`,
    `_variance_path`, `_t_const`, `_loglik`, `_fit`, `_fit_t(eps)` (garch's `_fit_t` with no extra starts),
    `_t_scale`, `_draw_z(rng, nu, dist, size, bound=Z_BOUND)`, `_log_mgf`, `_correction_table(nu, bound)`
    (`lru_cache(maxsize=32)`).
  - Private, new: `_t_mass(nu, bound) -> float` (`lru_cache(maxsize=32)`, c_quad's denominator),
    `_deterministic_gap(fit, sigma) -> tuple[float, float]` (check 1's two statistics), `_statistical_z(ret) ->
    float` (check 2's statistic).
  - Call-time lookups later tasks rely on: `martingale_correction` reaches `_correction_table`, and `pilot_checks`
    reaches `simulate_garch`, `c_quad`, `PILOT_PATHS` and `PILOT_NODES`, through the module globals at call time.
    Task 14 drops both GARCH members when a test corrupts `core.odds.models._correction_table`; that works only
    because of this.

**Plan decisions used:** Q1 (O1: the GARCH-t fit, simulation and correction table copied from `core/quant/garch.py`,
each pinned by an equality test; numpy and scipy stay outside the signed hash), Q10 (pilot: 20,000 paths from the
stream "pilot"; check 1 deterministic, at most 512 quantile nodes, 1e-7 per step and 1e-6 summed over the horizon
per path, c_quad by `scipy.integrate.quad`; check 2 statistical, 4 SE at every step; the corruption magnitudes of
contract 7.4), Q12 (the pilot stream is `seed_sequence(seed, 0, "pilot")`), Q31 (Task 14 drops a member on
`converged` false or a failed pilot; `at_bound` alone is recorded, not a failure), Q42 (no I/O, no clock). Covers spec
8 odds item 1: both GARCH pilot checks pass on fixture fits and fail on a corrupted correction table and on zero log
drift (the mean payoff 0 of a stop, a bracket and buy-and-hold under GARCH-t is Task 9's). RULINGS O1, O10; R2-9 (the
margins confirmed on the real pilot stream, Step 4).

Design notes (read before Step 3):
- **What is copied.** Only the path of `garch.fit_garch(returns, dist="t", profile=False)` that ends in a
  `GarchParams` field: `_variance_path`, `_t_const`, `_loglik`, `_fit`, `_fit_t`, the `_MIN_OBS` check, `mu` fixed at
  the sample mean, `nu = inf` below `_ETA_EPS`, and `cond_vol_last = sqrt(s2_path[-1] * 252)`. Left out, because no
  field reads them: `_covariance`, `_hessian`, `_profile_eta`, `_fit_fixed_eta`, `loglik_iid_normal`, the note, the
  likelihood ratios, `forecast_variance`, `horizon_vol`, `bounded_t_stats` and `_half_life` (CONTRACT 7.3 lists
  `_half_life` in the copied path, but `GarchParams` has no half-life field, so the copy would be dead code in the
  signed closure). `_fit_t(eps)` drops garch's `extra_starts` parameter: the `profile=False` path always passes `()`,
  so the starts, and therefore the fit, are the same. Every copied constant is private (CONTRACT section 0: a name
  the contract does not list is a private helper) and pinned by `test_copied_constants_equal_the_originals`.
- **Bit-exact simulation.** `simulate_garch` is garch's `simulate_returns` body with `rate_daily=0.0` and
  `bound=Z_BOUND`: `ret[:, h] = 0.0 - c + eps` mirrors `float(rate_daily) - c + eps` exactly, and the draws come from
  `np.random.default_rng(seed)` with the same `_draw_z` call, so the same SeedSequence gives the same array
  (`test_simulate_garch_equals_simulate_returns_at_rate_zero`, `np.array_equal`). It also keeps each step's sigma for
  check 1. The fixture fits (nu 4.6 and up) never draw past 22, so that test adds a nu 2.6 case whose stream the
  bound reaches (10 of 120,000 draws), which pins `bound=Z_BOUND`; the martingale correction holds only for the
  bounded t. `simulate_garch_series` keeps the full tail (`bound=None`), pinned the same way by a nu 2.6 case with
  one draw past 22. Sigma never depends on the correction table (the recursion uses `eps = sigma z` only), so a
  corrupted table changes the pilot's returns but not its sigma or its quantile nodes.
- **Check 1** quads each distinct node once (`np.unique` of the quantiles of every pilot sigma at `PILOT_NODES`
  levels) and gives every pilot sigma its nearest node's error; the per-path sum over the horizon is the compounded
  error. The nearest-node index is safe for a single node (`lo = max(hi - 1, 0)`). `c_quad` integrates over the
  three panels garch's own `__main__` self-check uses (`(-bound, -1)`, `(-1, 1)`, `(1, bound)`, `limit=400`), so it
  shares no node with the table's Gauss-Legendre rule; its denominator does not depend on sigma and is cached per
  `(nu, bound)` in `_t_mass`. A normal fit (or nu above `NU_NORMAL`) gets sigma^2/2 on both sides, so its gap is 0.
- **Check order.** Check 1 runs first and `pilot_checks` returns the first failure. A table tripled everywhere is
  therefore caught by check 1 ("deterministic"). To show that check 2 alone sees the tripled correction, the test
  swaps `models.simulate_garch` for one that draws the pilot under the tripled table and then puts the real table
  back, so check 1 judges the real table on the very same sigma and passes, and check 2 fails ("statistical"). The
  zero-drift test swaps in the returns of `garch.simulate_returns` with `drift_daily=0.0` on the same SeedSequence in
  the same way ("fed to check 2").
- **Fail closed.** Both checks are written `not (x <= tol)`, so a NaN statistic fails its check
  (`test_both_checks_fail_closed_on_nan`); `x > tol` would pass it.
- **What check 2 can see.** A per-step drift error dc moves the mean of exp(cumulative return) after h steps by
  about h dc, while its SE is about sigma sqrt(h / N); so 4 SE detect dc only above about 4 sigma / sqrt(N h), about
  3e-5 at sigma 0.01, N 20,000 and h 90 (CONTRACT 7.4). Zero log drift is an error of c, about sigma^2/2 per step: on
  the nu 5.6 fixture (daily sigma about 0.0083, c about 3.4e-5) that limit is 2.5e-5 at 90 steps (visible) and 4.3e-5
  at 30 (not visible), which is why 30 steps are not asserted for zero drift.
- **R2-9 margins, measured on the real pilot stream** (`seed_sequence(SEED, 0, "pilot")` with the test's `SEED =
  market_seed(("0" * 32,), "", "c000001", 1)`; numpy 2.3.5, scipy 1.18.0, drafting sandbox 2026-10-27). They differ
  from the sandbox numbers in CONTRACT 7.4, which drew from `default_rng(4)`:

  | fixture (fitted nu) | steps | clean check 1 (step / sum) | clean z | offset check 1 (step / sum) | ratio x 3 z | zero log drift z |
  |---|---|---|---|---|---|---|
  | nu56 (5.618) | 30 | 2.2e-12 / 2.5e-11 | 1.64 | 2.0e-06 / 6.0e-05 | 8.22 | 2.48 (not asserted) |
  | nu56 (5.618) | 90 | 7.6e-11 / 3.9e-10 | 2.14 | 2.0e-06 / 1.8e-04 | 12.34 | 7.51 |
  | nu46 (4.604) | 30 | 8.2e-11 / 2.2e-09 | 1.21 | 2.0e-06 / 6.0e-05 | 35.67 | 15.41 |
  | nu46 (4.604) | 90 | 4.8e-10 / 2.9e-08 | 1.22 | 2.0e-06 / 1.8e-04 | 68.22 | 23.25 |

  Every asserted corruption fails with room (the smallest asserted check-2 z is 7.51 against 4); every clean pilot
  passes with room (the largest clean z is 2.14). The fixture "nu46" is `garch.simulate_garch_series(5e-5, 0.08, 0.90,
  5.0, n=1500, seed=1)`, the series behind the DIGEST's "fixture GARCH-t (nu 4.6)" probe (omega `2e-6 * 25`).
- **Test time.** Quad dominates (512 nodes x 3 panels, about 1 to 3 s per pilot). `c_quad` is pure and a corrupted
  pilot has the clean pilot's nodes, so the pilot tests share one test-side memo of the real `c_quad` (`_QUAD`) and
  run quad once per (fit, horizon): four times in all. The signed core caches nothing for the tests' sake. The module
  took 17.8 s with eleven uncached pilots on a quiet drafting machine, so about 12 to 18 s is expected (budget 25 s);
  under heavy parallel load it took up to 60 s, so a slow run on a busy machine is not a failure.
- **The tests discriminate.** In the drafting sandbox each of 27 deliberate breaks of the new code failed at least
  one test: the correction dropped from the returns, `simulate_garch` drawing unbounded, `simulate_garch_series`
  drawing bounded, the two checks swapped, either check written `x > tol` (NaN
  passes), the summed criterion dropped, the nearest node replaced by the node above or below, `martingale_correction`
  reading a module alias of the table (the corruption cannot reach it), the "garch" stream in place of "pilot",
  `PILOT_PATHS` bound at import, `PILOT_NODES` hard-coded, the fit's `dist` ignored in check 1, per-step in place of
  cumulative exp, `ddof=0` in check 2, `s2_path[-2]` for `cond_vol_last`, the second normal pass of `_fit_t` skipped,
  no inverse-CDF replacement in `_draw_z`, `c_quad` with a fixed bound, no direct sums above the sigma grid, a
  non-frozen `GarchParams`, no burn-in in `simulate_garch_series`, the eta bound 0.5, `<=` in the 100-return check,
  `s2` kept in place of sigma, and `_correction_table` without its `lru_cache`.

- [ ] **Step 1: Write the failing tests**

  Create `tests/odds_garch.py` (whole file, LF). `FIXTURES` and `SEED` are built at import from Task 7's
  `market_seed` and garch's own `simulate_garch_series` (cheap); every fit and pilot runs inside a test.
  `OFFSET`, `RATIO_FACTOR` and `LOG_DRIFT` are the three corruption magnitudes R2-9 lets the implementer raise.

```python
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
```

- [ ] **Step 2: Run to verify it fails**

  QUANTGEN overlap check with the PowerShell tool (it must print nothing; otherwise wait and re-run it):

```powershell
Get-CimInstance Win32_Process -Filter "Name LIKE 'python%'" | Where-Object { $_.CommandLine -match 'run_all' } | Select-Object ProcessId,Name,CommandLine
```

  Then, from the repo root in Git Bash:

```bash
.venv/Scripts/python.exe -m tests.odds_acceptance odds_garch/; echo "exit $?"
```

  Expected: a traceback, then

```
FAIL odds_garch/import AttributeError: module 'core.odds.models' has no attribute 'c_quad'

0/1 passed, 1 failed, 0 not run
exit 1
```

  (the module stops at `_QUAD = functools.lru_cache(maxsize=None)(models.c_quad)`, its first use of a
  Task 8 name). Any other error (for example `has no attribute 'market_seed'`) means Task 7 is not in place: stop.

- [ ] **Step 3: Implement**

  Two Edit-tool replacements in `core/odds/models.py` (LF; keep LF). Re-read the file first (DRIFT RULE).

  **Edit 1** (anchor: the module docstring and the import block, the first 14 lines of the file). It says the module
  now holds the GARCH-t part and adds the imports Task 7's layout note reserves for Task 8. Old text:

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
```

  New text:

```python
"""The no-edge models of the odds core (spec 7.2, 7.3; odds plan Q10, Q12, Q34): the copied constants, block length
and Sharpe (O1: each pinned against its original by tests/odds_models.py), the two-point bootstrap's row magnitudes,
block lengths, index generator, kernel and tilt, the market seed with its streams, and the GARCH-t copy with its
pilot checks (O1: pinned against core/quant/garch.py by tests/odds_garch.py). Pure: no clock, no file, no network."""
from __future__ import annotations

import hashlib
import math
from collections.abc import Iterator
from dataclasses import dataclass
from functools import lru_cache
from typing import TYPE_CHECKING

import numpy as np
from scipy import stats
from scipy.integrate import quad
from scipy.optimize import minimize
from scipy.signal import lfilter
from scipy.special import gammaln

from core.compliance import model
```

  **Edit 2** (anchor: the function `stream`, the last function of the file; Task 8 appends after it). Old text:

```python
def stream(seed: bytes, chunk: int, name: str, *extra: int) -> np.random.Generator:
    """The Generator of stream `name`: np.random.default_rng(seed_sequence(seed, chunk, name, *extra)), a PCG64
    (default_rng passes a SeedSequence through)."""
    return np.random.default_rng(seed_sequence(seed, chunk, name, *extra))
```

  New text (the same four lines, then the GARCH-t part; the file ends with `pilot_checks` and one newline):

```python
def stream(seed: bytes, chunk: int, name: str, *extra: int) -> np.random.Generator:
    """The Generator of stream `name`: np.random.default_rng(seed_sequence(seed, chunk, name, *extra)), a PCG64
    (default_rng passes a SeedSequence through)."""
    return np.random.default_rng(seed_sequence(seed, chunk, name, *extra))


# --------------------------------------------------------------------------- #
# GARCH-t copy (contract 7.3; O1: copied from core/quant/garch.py and pinned against it by tests/odds_garch.py)
# --------------------------------------------------------------------------- #
_SIG_LO, _SIG_HI = 1e-6, 0.25          # == garch._SIG_LO, garch._SIG_HI: the correction table's daily-sigma grid
_BOUNDS: dict[str, tuple[float, float]] = {   # == garch.BOUNDS on the four fitted coordinates
    "omega": (1e-12, math.inf),        # daily variance units
    "alpha": (0.0, 0.5),
    "beta": (0.0, 0.999),
    "eta": (0.0, 0.4),                 # the tail is fitted as eta = 1/nu; eta = 0 IS the normal
}
_STATIONARITY_MAX = 0.9995             # == garch.STATIONARITY_MAX
_ETA_EPS = 1e-10                       # == garch._ETA_EPS: below this eta the density IS the normal
_PENALTY = 1e10                        # == garch._PENALTY
_MIN_OBS = 100                         # == garch._MIN_OBS
_OMEGA_SCALE = 1e6                     # == garch._OMEGA_SCALE


@dataclass(frozen=True, kw_only=True)
class GarchParams:
    """The fields of garch.GarchFit that the odds engine runs on: GARCH(1,1) with Student-t innovations, mu fixed at
    the sample mean of the daily log returns. nu is inf when the fitted eta is 0 (the t is the normal);
    cond_vol_last is the annualised (TRADING_DAYS) next-session forecast sqrt(sigma^2_{T+1} * 252)."""
    dist: str
    omega: float
    alpha: float
    beta: float
    nu: float
    mean_daily: float
    n_obs: int
    cond_vol_last: float
    converged: bool
    at_bound: tuple[str, ...]


def _variance_path(eps2: np.ndarray, omega: float, alpha: float, beta: float, s2_init: float) -> np.ndarray:
    """Copy of garch._variance_path: sigma^2_1..sigma^2_{T+1} (length T+1), the IIR filter y_t = x_t + beta y_{t-1}
    with x_1 = s2_init and x_t = omega + alpha eps^2_{t-1}."""
    x = np.empty(eps2.size + 1)
    x[0] = s2_init
    x[1:] = omega + alpha * eps2
    return lfilter([1.0], [1.0, -beta], x)


def _t_const(nu: float) -> float:
    """Copy of garch._t_const: ln of the unit-variance t density's normalising constant (the Stirling expansion
    beyond nu = 1e4, where the two gammaln terms cancel catastrophically)."""
    if nu > 1e4:
        return 0.5 * math.log(nu / (2.0 * math.pi * (nu - 2.0))) - 1.0 / (4.0 * nu)
    return gammaln((nu + 1) / 2) - gammaln(nu / 2) - 0.5 * math.log(math.pi * (nu - 2))


def _loglik(params: np.ndarray, eps: np.ndarray, eps2: np.ndarray, s2_init: float, dist: str) -> float:
    """Copy of garch._loglik: the GARCH(1,1) log-likelihood, -_PENALTY past the stationarity cap or for a
    non-positive variance path."""
    omega, alpha, beta = params[:3]
    if alpha + beta > _STATIONARITY_MAX:
        return -_PENALTY
    s2 = _variance_path(eps2, omega, alpha, beta, s2_init)[:-1]
    if not np.all(np.isfinite(s2)) or np.any(s2 <= 0):
        return -_PENALTY
    if dist == "t" and params[3] >= _ETA_EPS:
        nu = 1.0 / params[3]
        ll = _t_const(nu) - 0.5 * np.log(s2) - ((nu + 1) / 2) * np.log1p(eps2 / ((nu - 2) * s2))
    else:                                                # normal, or a t with eta = 0
        ll = -0.5 * math.log(2 * math.pi) - 0.5 * np.log(s2) - eps2 / (2 * s2)
    return float(np.sum(ll))


def _fit(eps: np.ndarray, dist: str, extra_starts=(), default_starts: bool = True):
    """Copy of garch._fit: L-BFGS-B over (omega, alpha, beta[, eta]) from the three deterministic starts (unless
    `default_starts` is False) plus `extra_starts`, omega optimised in units of 1e-6. Returns (p, loglik,
    converged, at_bound, s2_path)."""
    eps2 = eps ** 2
    var = float(np.var(eps))
    names = ("omega", "alpha", "beta") + (("eta",) if dist == "t" else ())
    scale = np.ones(len(names))
    scale[0] = _OMEGA_SCALE
    bounds = [(_BOUNDS["omega"][0] * _OMEGA_SCALE, None)] + [_BOUNDS[n] for n in names[1:]]
    starts = ([[var * (1 - 0.05 - beta0), 0.05, beta0] + ([1.0 / 8.0] if dist == "t" else [])
               for beta0 in (0.80, 0.90, 0.94)] if default_starts else []) + [list(s) for s in extra_starts]
    best = None
    for x0 in starts:
        res = minimize(lambda p: -_loglik(p / scale, eps, eps2, var, dist), np.array(x0) * scale,
                       method="L-BFGS-B", bounds=bounds)
        if best is None or res.fun < best.fun:
            best = res
    p = best.x / scale
    at = []
    for name, val in zip(names, p):
        lo, hi = _BOUNDS[name]
        tol = 1e-4
        if name == "eta":                                # eta = 0 is the normal, not a failure
            if abs(val - hi) <= tol * abs(hi):
                at.append("nu")                          # nu at its lower bound 2.5
            continue
        if abs(val - lo) <= (tol if lo == 0 else tol * abs(lo)):
            at.append(name)
        elif math.isfinite(hi) and abs(val - hi) <= tol * abs(hi):
            at.append(name)
    if p[1] + p[2] > 0.995:
        at.append("stationarity")
    s2_path = _variance_path(eps2, p[0], p[1], p[2], var)
    return p, float(-best.fun), bool(best.success), tuple(at), s2_path


def _fit_t(eps: np.ndarray):
    """Copy of garch._fit_t with no extra starts: the normal first, the t from the normal's optimum (eta = 0), the
    normal re-fitted from the t's (omega, alpha, beta), and one more t pass if that normal climbs past the t.
    Returns (p, loglik, converged, at_bound, s2_path)."""
    p_n, _, _, _, _ = _fit(eps, "normal")
    p, ll, converged, at_bound, s2_path = _fit(eps, "t", extra_starts=[[*p_n[:3], 0.0]])
    p_n2, ll_n2, _, _, _ = _fit(eps, "normal", extra_starts=[list(p[:3])], default_starts=False)
    if ll_n2 > ll:
        t2 = _fit(eps, "t", extra_starts=[[*p_n2[:3], 0.0]], default_starts=False)
        if t2[1] >= ll:
            p, ll, converged, at_bound, s2_path = t2
    return p, ll, converged, at_bound, s2_path


def fit_garch_t(returns: np.ndarray) -> GarchParams:
    """GARCH(1,1)-t on daily log returns: the path of garch.fit_garch(returns, dist="t", profile=False) without the
    standard errors, the likelihood ratios and the note. ValueError under 100 observations."""
    r = np.asarray(returns, dtype=float)
    if r.size < _MIN_OBS:
        raise ValueError(f"Need at least {_MIN_OBS} observations to fit GARCH; got {r.size}.")
    mu = float(np.mean(r))
    p, _, converged, at_bound, s2_path = _fit_t(r - mu)
    eta = float(p[3])
    return GarchParams(dist="t", omega=float(p[0]), alpha=float(p[1]), beta=float(p[2]),
                       nu=math.inf if eta < _ETA_EPS else 1.0 / eta, mean_daily=mu, n_obs=r.size,
                       cond_vol_last=math.sqrt(s2_path[-1] * TRADING_DAYS), converged=converged, at_bound=at_bound)


def _t_scale(nu: float) -> float:
    """Copy of garch._t_scale: the unit-variance scaling of a standard t draw."""
    return math.sqrt((nu - 2.0) / nu)


def t_density(z, nu: float) -> np.ndarray:
    """Copy of garch.t_density: the density of the unit-variance Student-t (the normal density above NU_NORMAL)."""
    z = np.asarray(z, dtype=float)
    if nu > NU_NORMAL:
        return np.exp(-0.5 * z ** 2) / math.sqrt(2 * math.pi)
    return math.exp(_t_const(nu)) * (1.0 + z ** 2 / (nu - 2.0)) ** (-(nu + 1) / 2)


def _draw_z(rng, nu: float, dist: str, size, bound: float | None = Z_BOUND) -> np.ndarray:
    """Copy of garch._draw_z: unit-variance innovations; with a `bound` (t only) every draw beyond it is replaced by
    one from the t restricted to [-bound, bound] via the inverse CDF. A t with nu above NU_NORMAL is drawn as a
    normal."""
    if dist != "t" or nu > NU_NORMAL:
        return rng.standard_normal(size=size)
    s = _t_scale(nu)
    z = rng.standard_t(nu, size=size) * s
    if bound is None:
        return z
    out = np.abs(z) > bound
    n_out = int(np.count_nonzero(out))
    if n_out:
        d = stats.t(nu)
        lo, hi = d.cdf(-bound / s), d.cdf(bound / s)
        z[out] = s * d.ppf(lo + rng.random(n_out) * (hi - lo))
    return z


def _log_mgf(sig: np.ndarray, z: np.ndarray, wt: np.ndarray) -> np.ndarray:
    """Copy of garch._log_mgf: ln sum_i wt_i exp(sig z_i) for each sig, computed stably."""
    e = np.outer(sig, z)
    m = e.max(axis=1, keepdims=True)
    return m[:, 0] + np.log((wt[None, :] * np.exp(e - m)).sum(axis=1))


@lru_cache(maxsize=32)
def _correction_table(nu: float, bound: float):
    """Copy of garch._correction_table: Gauss-Legendre nodes and normalised weights of the t restricted to
    [-bound, bound] (three panels), and c(sigma)/sigma^2 on a 4,000-point geometric daily-sigma grid up to _SIG_HI.
    martingale_correction looks this name up at call time, so the corruption test of tests/odds_garch.py reaches
    every caller."""
    x, w = np.polynomial.legendre.leggauss(600)
    edges = (-bound, -1.0, 1.0, bound) if bound > 1.0 else (-bound, bound)
    z = np.concatenate([0.5 * (b - a) * x + 0.5 * (b + a) for a, b in zip(edges[:-1], edges[1:])])
    wt = np.concatenate([0.5 * (b - a) * w for a, b in zip(edges[:-1], edges[1:])]) * t_density(z, nu)
    wt = wt / wt.sum()
    sig = np.geomspace(_SIG_LO, _SIG_HI, 4000)
    c = np.concatenate([_log_mgf(s, z, wt) for s in np.array_split(sig, 16)])
    return z, wt, sig, c / sig ** 2


def martingale_correction(sigma_daily, nu: float, dist: str, bound: float | None = Z_BOUND) -> np.ndarray:
    """Copy of garch.martingale_correction: c(sigma) = ln E[exp(sigma z)] per step for the innovation law that is
    simulated (sigma^2/2 for a normal z; the interpolated table of the bounded t, direct sums above the grid). An
    unbounded t has no such correction and raises."""
    sig = np.atleast_1d(np.asarray(sigma_daily, dtype=float))
    if dist != "t" or nu > NU_NORMAL:                    # normal, or a t drawn as one
        return 0.5 * sig ** 2
    if bound is None:
        raise ValueError("exp(sigma z) has no finite expectation under an unbounded t; no correction exists")
    z, wt, grid, ratio = _correction_table(float(nu), float(bound))
    out = np.interp(sig, grid, ratio) * sig ** 2
    big = sig > grid[-1]
    if np.any(big):
        out[big] = _log_mgf(sig[big], z, wt)
    return out


def simulate_garch(fit: GarchParams, *, n_paths: int, horizon: int, seed) -> tuple[np.ndarray, np.ndarray]:
    """(ret, sigma), each (n_paths, horizon): the body of garch.simulate_returns(fit, rate_daily=0.0, bound=Z_BOUND)
    with the conditional daily sigma of every step kept. Each step's log return is -c(sigma_t) + sigma_t z_t, so
    exp(cumulative return) has mean 1 at every step: the no-edge law. `seed` goes to np.random.default_rng (a
    SeedSequence from seed_sequence, or a Generator)."""
    rng = np.random.default_rng(seed)
    z = _draw_z(rng, fit.nu, fit.dist, (n_paths, horizon), Z_BOUND)
    ret = np.empty((n_paths, horizon))
    sigma = np.empty((n_paths, horizon))
    s2 = np.full(n_paths, fit.cond_vol_last ** 2 / TRADING_DAYS)
    for h in range(horizon):
        sig = np.sqrt(s2)
        eps = sig * z[:, h]
        c = martingale_correction(sig, fit.nu, fit.dist, Z_BOUND)
        ret[:, h] = 0.0 - c + eps
        sigma[:, h] = sig
        s2 = fit.omega + fit.alpha * eps ** 2 + fit.beta * s2
    return ret, sigma


def simulate_garch_series(omega: float, alpha: float, beta: float, nu: float, *, n: int, seed,
                          dist: str = "t") -> np.ndarray:
    """Copy of garch.simulate_garch_series: zero-mean synthetic GARCH(1,1) returns with the full (unbounded) tail and
    a 500-session burn-in (the refit member's synthetic series)."""
    rng = np.random.default_rng(seed)
    burn = 500
    z = _draw_z(rng, nu, dist, n + burn, bound=None)
    eps = np.empty(n + burn)
    s2 = omega / (1 - alpha - beta) if alpha + beta < 1 else omega * 100
    for t in range(n + burn):
        eps[t] = math.sqrt(s2) * z[t]
        s2 = omega + alpha * eps[t] ** 2 + beta * s2
    return eps[burn:]


# --------------------------------------------------------------------------- #
# GARCH pilot checks (contract 7.4; Q10)
# --------------------------------------------------------------------------- #
PILOT_PATHS = 20_000
PILOT_NODES = 512
PILOT_STEP_TOL = 1e-7
PILOT_SUM_TOL = 1e-6
PILOT_SE = 4.0


@lru_cache(maxsize=32)
def _t_mass(nu: float, bound: float) -> float:
    """The quad mass of the unit-variance t density on [-bound, bound] over c_quad's three panels."""
    return sum(quad(lambda x: t_density(x, nu), a, b, limit=400)[0] for a, b in ((-bound, -1.0), (-1.0, 1.0),
                                                                                (1.0, bound)))


def c_quad(sigma: float, nu: float, bound: float = Z_BOUND) -> float:
    """The exact per-step correction ln E[exp(sigma z)] of the t restricted to [-bound, bound], by scipy quad over
    the panels (-bound, -1), (-1, 1), (1, bound) as garch's own self-check does, so it shares no node with the
    table; sigma^2/2 for a t drawn as a normal (nu > NU_NORMAL)."""
    if nu > NU_NORMAL:
        return 0.5 * sigma ** 2
    num = sum(quad(lambda x: math.exp(sigma * x) * t_density(x, nu), a, b, limit=400)[0]
              for a, b in ((-bound, -1.0), (-1.0, 1.0), (1.0, bound)))
    return math.log(num / _t_mass(float(nu), float(bound)))


def _deterministic_gap(fit: GarchParams, sigma: np.ndarray) -> tuple[float, float]:
    """Check 1's two statistics on the pilot's sigma: (max over the nodes of |expm1(c_quad - c_table)|, max over
    paths of the summed |c_quad - c_table| over the horizon). The nodes are the distinct quantiles of every pilot
    sigma at PILOT_NODES levels; each sigma takes its nearest node's error."""
    nodes = np.unique(np.quantile(sigma.ravel(), np.linspace(0.0, 1.0, PILOT_NODES)))
    nu = fit.nu if fit.dist == "t" else math.inf         # a normal fit: c = sigma^2/2 exactly
    gap = np.array([c_quad(float(s), nu) for s in nodes]) - martingale_correction(nodes, fit.nu, fit.dist)
    hi = np.clip(np.searchsorted(nodes, sigma), 0, nodes.size - 1)
    lo = np.maximum(hi - 1, 0)
    near = np.where(np.abs(nodes[lo] - sigma) <= np.abs(nodes[hi] - sigma), lo, hi)
    return float(np.max(np.abs(np.expm1(gap)))), float(np.max(np.abs(gap)[near].sum(axis=1)))


def _statistical_z(ret: np.ndarray) -> float:
    """Check 2's statistic: max over steps h of |mean(e_h) - 1| / (std(e_h, ddof=1) / sqrt(rows)), e = exp of the
    cumulative log return. NaN when a return is not finite, which fails the check."""
    e = np.exp(np.cumsum(ret, axis=1))
    return float(np.max(np.abs(e.mean(axis=0) - 1.0) / (e.std(axis=0, ddof=1) / math.sqrt(e.shape[0]))))


def pilot_checks(fit: GarchParams, horizon: int, seed: bytes) -> tuple[bool, str]:
    """The two GARCH pilot checks (spec 7.2 "GarchT"; Q10) on PILOT_PATHS paths of the "pilot" stream:
    1 (deterministic) the table's correction against quad, PILOT_STEP_TOL per step and PILOT_SUM_TOL summed over
    the horizon on every path; 2 (statistical) exp(cumulative return) within PILOT_SE standard errors of 1 at every
    step. (True, "") or (False, the first failing check). Each test fails closed on NaN."""
    ret, sigma = simulate_garch(fit, n_paths=PILOT_PATHS, horizon=horizon, seed=seed_sequence(seed, 0, "pilot"))
    step, summed = _deterministic_gap(fit, sigma)
    if not (step <= PILOT_STEP_TOL and summed <= PILOT_SUM_TOL):
        return False, "deterministic"
    if not _statistical_z(ret) <= PILOT_SE:
        return False, "statistical"
    return True, ""
```

- [ ] **Step 4: Run to verify it passes**

  Run the overlap check of Step 2 (PowerShell tool; it must print nothing) before EACH Python command below. All
  run from the repo root in Git Bash.

  Overlap check, then the module, timed:

```bash
time .venv/Scripts/python.exe -m tests.odds_acceptance odds_garch/; echo "exit $?"
```

  Expected: these 17 lines (in this order, each with nothing after the name), then
  `17/17 passed, 0 failed, 0 not run`, the three `real`/`user`/`sys` lines of `time`, and `exit 0`. The `real`
  value includes the imports of every suite (`tests.run_all.run` pulls them in), so it runs several seconds above
  the module's own test time:

```
PASS odds_garch/test_a_scaled_correction_table_fails_the_statistical_check
PASS odds_garch/test_an_offset_correction_table_fails_the_deterministic_check
PASS odds_garch/test_both_checks_fail_closed_on_nan
PASS odds_garch/test_both_pilot_checks_pass_on_the_fixture_fits
PASS odds_garch/test_c_quad_agrees_with_the_table_and_the_normal
PASS odds_garch/test_copied_constants_equal_the_originals
PASS odds_garch/test_correction_table_and_martingale_correction_equal_the_original
PASS odds_garch/test_deterministic_check_sums_each_paths_nearest_node_errors
PASS odds_garch/test_fit_garch_t_equals_the_original_field_by_field
PASS odds_garch/test_fit_garch_t_refuses_fewer_than_100_returns
PASS odds_garch/test_likelihood_pieces_equal_the_original
PASS odds_garch/test_pilot_checks_reads_its_sizes_and_stream_at_call_time
PASS odds_garch/test_simulate_garch_equals_simulate_returns_at_rate_zero
PASS odds_garch/test_simulate_garch_series_equals_the_original
PASS odds_garch/test_statistical_z_counts_standard_errors_of_the_cumulative_mean
PASS odds_garch/test_t_density_scale_and_draws_equal_the_original
PASS odds_garch/test_zero_log_drift_fails_the_statistical_check
```

  If `test_a_scaled_correction_table_fails_the_statistical_check` or
  `test_zero_log_drift_fails_the_statistical_check` fails, or `test_an_offset_correction_table_fails_the_deterministic_check`
  does, the margins did not reproduce: run the measurement below and apply R2-9 (raise `RATIO_FACTOR` in steps of 1.0,
  set `LOG_DRIFT` to the smallest d > 0, in steps of 1e-5, that lifts the 90-step z above 4.0, or raise `OFFSET` in
  steps of 1e-6; record the new value and its measured line in the ledger). Never lower `PILOT_SE`, `PILOT_STEP_TOL` or
  `PILOT_SUM_TOL` and never drop a corruption assertion. A failing clean pilot
  (`test_both_pilot_checks_pass_on_the_fixture_fits`) is a bug: stop and report it.

  R2-9: measure the margins on the real pilot stream and record them. Overlap check, then (it only prints; it writes
  nothing and calls no network function):

```bash
.venv/Scripts/python.exe -B - <<'EOF'
"""R2-9: the corruption margins of tests/odds_garch.py on the real "pilot" stream (prints only; writes nothing)."""
from core.odds import models
from core.quant import garch
from tests import odds_garch as G

with G._memo():
    for key in ("nu56", "nu46"):
        fit, gfit = G._fits(key)
        for h in (30, 90):
            def pilot():
                return models.seed_sequence(G.SEED, 0, "pilot")
            ret, sigma = models.simulate_garch(fit, n_paths=models.PILOT_PATHS, horizon=h, seed=pilot())
            step, summed = models._deterministic_gap(fit, sigma)
            with G._table(G._offset):
                o_step, o_sum = models._deterministic_gap(fit, sigma)
            with G._table(G._scaled):
                scaled = models.simulate_garch(fit, n_paths=models.PILOT_PATHS, horizon=h, seed=pilot())[0]
            drift = garch.simulate_returns(gfit, n_paths=models.PILOT_PATHS, horizon=h, seed=pilot(),
                                           drift_daily=G.LOG_DRIFT)[0]
            print(f"{key} h{h} nu {fit.nu:.3f}: clean {step:.1e} / {summed:.1e} z {models._statistical_z(ret):.2f};"
                  f" offset {o_step:.1e} / {o_sum:.1e}; ratio x{G.RATIO_FACTOR:g} z"
                  f" {models._statistical_z(scaled):.2f}; log drift {G.LOG_DRIFT:g} z {models._statistical_z(drift):.2f}")
EOF
```

  Expected (deterministic under numpy 2.3.5 and scipy 1.18.0; quad dominates, about 10 to 40 s depending on load):

```
nu56 h30 nu 5.618: clean 2.2e-12 / 2.5e-11 z 1.64; offset 2.0e-06 / 6.0e-05; ratio x3 z 8.22; log drift 0 z 2.48
nu56 h90 nu 5.618: clean 7.6e-11 / 3.9e-10 z 2.14; offset 2.0e-06 / 1.8e-04; ratio x3 z 12.34; log drift 0 z 7.51
nu46 h30 nu 4.604: clean 8.2e-11 / 2.2e-09 z 1.21; offset 2.0e-06 / 6.0e-05; ratio x3 z 35.67; log drift 0 z 15.41
nu46 h90 nu 4.604: clean 4.8e-10 / 2.9e-08 z 1.22; offset 2.0e-06 / 1.8e-04; ratio x3 z 68.22; log drift 0 z 23.25
```

  Append under "Runs" in the execution ledger (LF, Edit tool) the line
  `- Task 8 R2-9 margins (pilot stream of market_seed(("0" * 32,), "", "c000001", 1); OFFSET 2e-6, RATIO_FACTOR 3.0, LOG_DRIFT 0.0):`
  followed by the four printed lines, each indented by four spaces. If a printed line differs from the expected one,
  record the printed line as is, plus a one-line note under "Deferred minors"; the tests decide pass or fail.

  Overlap check, then the odds guards, which now scan the GARCH-t part of `core/odds/models.py` too:

```bash
.venv/Scripts/python.exe -m tests.odds_acceptance odds_guards/
```

  Expected: every line PASS, ending `N/N passed, 0 failed, 0 not run` with the N Task 7 ended with (exit code 0). The
  new imports are `dataclasses`, `functools` and five `scipy` modules, all inside the O1 allowlist. A failure names the
  file and the text: fix `models.py`, never the guard.

  Overlap check before each, then the compliance guards and store:

```bash
.venv/Scripts/python.exe -m tests.compliance_acceptance compliance_guards/
.venv/Scripts/python.exe -m tests.compliance_acceptance compliance_store/
```

  Expected: each ends `N/N passed, 0 failed, 0 not run` with the counts Task 7 ended with (exit code 0). The D14
  closure gains no file: scipy is third party and never hashed (`owner.py` `_module_file`), which the card states.

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
 M core/odds/models.py
?? docs/superpowers/plans/2026-10-24-odds-engine-execution-ledger.md
?? tests/odds_garch.py
```

  Append one line under "Runs" in the execution ledger (LF, Edit tool), with `<real>` replaced by the `real` value
  the timed odds_garch run printed (for example `0m21.4s`):
  `- Task 8: odds_garch 17/17 PASS (real <real> with the suite imports); odds_guards, compliance_guards, compliance_store and the core-wide scans 0 failed.`

  Then add these three lines under "Drift rulings" there (readings of the CONTRACT, not drift from the merged main,
  so a later reviewer does not move the code back toward the literal text):
  - `Task 8: CONTRACT 7.4 "the ratio x 3 fails check 2 with statistical": check 1 runs first and catches a table scaled everywhere ("deterministic"), so the test draws the pilot under the scaled table while check 1 judges the real one, and check 2 then fails it ("statistical").`
  - `Task 8: CONTRACT 7.3 GarchParams is @dataclass(frozen=True, kw_only=True), not @dataclass(frozen=True): every plan type is kw_only (Q4, CONTRACT 5.2) and every caller builds it by keyword (fit_garch_t, Task 9's _FIT).`
  - `Task 8: CONTRACT 7.3 _half_life is not copied: no GarchParams field reads it, so the copy would be dead code in the signed closure.`

- [ ] **Step 5: Commit**

```bash
git add core/odds/models.py tests/odds_garch.py
git diff --cached --stat
git diff --cached --stat --ignore-cr-at-eol
```

  The two stat outputs must be identical (both files LF): `core/odds/models.py | 317`, `tests/odds_garch.py | 364`,
  `2 files changed, 677 insertions(+), 4 deletions(-)` (a factor raised under R2-9 changes no line count). Then:

```bash
git commit -m "feat(odds): GARCH-t copy and its pilot checks" -m "Task 8: core/odds/models.py part 2 (the GARCH-t fit, simulation and correction table copied from core/quant/garch.py with equality tests; c_quad and the two pilot checks) and tests/odds_garch.py with the corruption tests; R2-9 margins in the ledger." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
