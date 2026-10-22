"""M2 package D tests: costed golden engine, research bootstrap, v1.2-check mode, reference mode
(TASK-M2-06, TASK-M2-07; core/quant/costed.py, core/quant/gate_stats.py, tests/reference/).

Spec tests: T-COST-01 (engine clauses; the R4b goldens are REFDATA), G-KR-06 / G-MOM-07 / G-LAD-01..03 (reference
mode; REFDATA until their fixtures are listed, then PENDING / reference values through tests/reference). The
pw_block, bootstrap and v1.2-check tests carry no spec id: they are the harness checks M7's G-KR-L* ride on.
Hermetic: synthetic paths only (seeded), no file writes, no clock.
"""
from __future__ import annotations

import ast
import csv
import importlib
import math
import tempfile
from datetime import date, timedelta
from pathlib import Path

import numpy as np

from core.quant import costed as C
from core.quant import gate_stats as GS
from core.quant import validate as V
from tests import golden_tools as G
from tests.acceptance import _code_only
from tests.notrun import NotRun, require_fixture

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "core"
# Fixture ids -> generator file names (docs/macro_fixtures.REFERENCE_FILES); U1 = French Mkt-RF spliced with ^GSPC.
FIXTURE_FILES = {
    "F13": ("yahoo_KS11_1996-12_2026-10-02.csv",),
    "U1": ("french_daily_5f_2x3.csv", "yahoo_GSPC_1990_2026-10-01.csv"),
    "F10": ("french_daily_mom_1990-01-02_2026-08-31.csv",),
    "F11": ("french_monthly_ff_1926-07_2026-08.csv",),
    "F24": ("results/QX_DLA_ladder.csv",),
}


def _refdata(*fids) -> dict[str, Path]:
    """Paths of every fixture of `fids`, or NotRun("REFDATA: ...") naming each absent file."""
    paths, missing = {}, []
    for fid in fids:
        for name in FIXTURE_FILES[fid]:
            try:
                paths[name] = require_fixture(name)
            except NotRun as exc:
                missing.append(f"{fid} {exc.reason.split(': ', 1)[1]}")
    if missing:
        raise NotRun("REFDATA: " + "; ".join(missing))
    return paths


def _raises(fn, exc, needle: str = "") -> None:
    try:
        fn()
    except exc as e:
        assert needle in str(e), f"{exc.__name__} without {needle!r}: {e}"
        return
    raise AssertionError(f"{exc.__name__} not raised")


def _closes(path: Path) -> tuple[list[str], np.ndarray]:
    """(obs_date, close) columns of a generated price fixture (source columns kept, provenance appended)."""
    with path.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        fields = list(reader.fieldnames or ())
        col = next((c for c in ("close", "Close", "adj_close", "value") if c in fields), fields[1])
        rows = list(reader)
    return [r["obs_date"] for r in rows], np.array([float(r[col]) for r in rows])


KR_WINDOW = "2016-01-04"            # G-KR-01..06 are defined on ^KS11 2016-01-04 -> 2026-10-02 (L5766)


def _window_returns(path: Path, start: str = KR_WINDOW, warm: int = 20) -> np.ndarray:
    """Simple returns dated `start` onward plus the `warm` returns before it (the vol-target warm-up, as R4): with a
    20-return window the first earning weight falls on `start`, so the scored sample is exactly the golden's span."""
    dates, closes = _closes(path)
    r = closes[1:] / closes[:-1] - 1.0
    first = next(i for i, d in enumerate(dates[1:]) if d >= start)
    if first < warm:
        raise ValueError(f"{path.name}: {first} returns before {start}, {warm} needed for the warm-up")
    return r[first - warm:]


# --------------------------------------------------------------------------- #
# T-COST-01: engine conventions (L5721-5725, L5019-5020)
# --------------------------------------------------------------------------- #
def test_cost01_engine_conventions():
    r = np.array([0.01, -0.02, 0.015, 0.0, 0.01, -0.01, 0.02])
    decided = np.array([0.5, 0.5, 0.8, 0.8, 0.8, 0.2, 0.2])
    earning = C.earning_weights(decided)
    assert np.isnan(earning[0]) and np.array_equal(earning[1:], decided[:-1])          # decide at t, earn t+1
    book = C.costed_path(earning, r, 35.0)
    assert np.allclose(book.turnover, [0.0, 0.0, 0.0, 0.3, 0.0, 0.0, 0.6])                # change at t charged on t+1
    assert np.isclose(book.cost[3], 0.3 * 35e-4) and book.cost[1] == 0.0                 # initial entry uncosted
    assert np.allclose(book.gross, np.where(np.isfinite(earning), earning, 0.0) * r)
    assert np.allclose(book.net, book.gross - book.cost)
    assert C.costed_path(earning, r, 35.0, 2.0).cost.sum() == 2 * book.cost.sum()       # 2x stress doubles
    assert C.costed_path(earning, r, 35.0, legs=2).cost.sum() == 2 * book.cost.sum()    # L/S pays both legs
    assert C.costed_path(np.ones(7), r, 35.0).cost.sum() == 0.0                          # buy-and-hold uncosted
    S = C.same_exposure_static(earning, r)
    assert np.allclose(S, np.mean(decided[:-1]) * r)                                     # constant mean weight, no cost
    assert abs(book.average_exposure - np.mean(np.where(np.isfinite(earning), earning, 0.0))) < 1e-12
    _raises(lambda: C.costed_path(earning, r, 35.0, 0.5), ValueError, "lowers")          # never lower a cost
    _raises(lambda: C.costed_path(earning, r, -1.0), ValueError)
    _raises(lambda: C.costed_path(earning, r, 35.0, legs=3), ValueError)
    gap = earning.copy()
    gap[4] = np.nan
    _raises(lambda: C.costed_path(gap, r, 35.0), ValueError, "gap")
    over = earning.copy()
    over[3] = 1.2
    _raises(lambda: C.costed_path(over, r, 35.0), C.RefusedConfiguration, "> 1.0")       # nothing above 1.0


test_cost01_engine_conventions.test_ids = ["T-COST-01"]


def test_cost01_r4b_goldens_refdata():
    """KOSPI VT20 at 35 bp SR 0.609, US VT15 at 50 bp SR 0.505 (L5638): needs the ^KS11 and U1 fixtures."""
    paths = _refdata("F13", "U1")
    r = _window_returns(paths["yahoo_KS11_1996-12_2026-10-02.csv"])
    w = C.earning_weights(C.vt_weights(r, 0.20, 20, 1.0))
    valid = np.isfinite(w)
    got = {"stock35_sharpe": V.sharpe(C.costed_path(w, r, 35.0).net[valid]),
           "x2_70bp_sharpe": V.sharpe(C.costed_path(w, r, 35.0, 2.0).net[valid])}
    G.assert_golden("G-KR-02", got)                           # the spliced US line joins when U1 is listed
    raise NotRun("REFDATA: U1 splice (French Mkt-RF + ^GSPC Sep-2026) needs the generator's U1 fixture row")


test_cost01_r4b_goldens_refdata.test_ids = ["T-COST-01"]


def test_kr_golden_window_scores_from_2016_01_04_after_a_20_return_warm_up():
    """The G-KR replays read the whole F13 file (1996-12 -> 2026-10); only 2016-01-04 onward is scored (L5766)."""
    days = [date(2015, 11, 2) + timedelta(d) for d in range(120)]
    days = [d for d in days if d.weekday() < 5]
    path = Path(tempfile.mkdtemp(prefix="m2costed_window_")) / "ks.csv"
    path.write_text("obs_date,close\n" + "".join(f"{d.isoformat()},{100 + i * 0.5 + (i % 3)}\n" for i, d in enumerate(days)),
                    encoding="utf-8")
    dates, closes = _closes(path)
    r = _window_returns(path)
    scored = [d for d in dates[1:] if d >= KR_WINDOW]
    assert len(r) == 20 + len(scored) and np.allclose(r, (closes[1:] / closes[:-1] - 1.0)[-len(r):])
    w = C.earning_weights(C.vt_weights(r, 0.20, 20, 1.0))
    assert np.isnan(w[:20]).all() and np.isfinite(w[20:]).all()            # first earning weight on 2016-01-04
    assert scored[0] == "2016-01-04"
    _raises(lambda: _window_returns(path, start="2015-11-20"), ValueError, "warm-up")


def test_vt_weights_research_builder():
    rng = np.random.default_rng(11)
    r = rng.standard_normal(300) * 0.012
    w = C.vt_weights(r, 0.20, 20, 1.0)
    assert np.isnan(w[:19]).all() and np.isfinite(w[19:]).all()
    for t in (19, 100, 299):
        sig = np.std(r[t - 19:t + 1], ddof=1) * math.sqrt(252)
        assert abs(w[t] - min(1.0, 0.20 / sig)) < 1e-12
    assert np.nanmax(w) <= 1.0                                                            # cap 1.0 permanent
    assert abs(min(1.0, 0.20 / 0.2882) - 0.694) < 0.001                                   # rv20 28.82% -> vt 0.694
    _raises(lambda: C.vt_weights(r, 0.20, 20, 1.5), C.RefusedConfiguration, "cap 1.5")
    _raises(lambda: C.vt_weights(r, 0.20, 20, 1.5, reference_only=False), C.RefusedConfiguration)
    _raises(lambda: C.vt_weights(r, 0.20, 20, 1.5, reference_only=True), C.RefusedConfiguration, "tests/reference/")
    _raises(lambda: C.vt_weights(r, 0.0), ValueError)


# --------------------------------------------------------------------------- #
# Politis-White block and the resamplers
# --------------------------------------------------------------------------- #
def _ar1(phi: float, n: int, seed: int) -> np.ndarray:
    e = np.random.default_rng(seed).standard_normal(n)
    x = np.empty(n)
    x[0] = e[0]
    for t in range(1, n):
        x[t] = phi * x[t - 1] + e[t]
    return x


def test_pw_block_ar1_textbook_and_floors():
    """AR(1) phi 0.5: gamma_k = sigma^2 phi^k, G = 2 sigma^2 phi/(1-phi)^2, D_CB = 4/3 (sigma^2 (1+phi)/(1-phi))^2,
    so b*_CB = (2G^2/D_CB)^(1/3) n^(1/3) = (32/12)^(1/3) n^(1/3) (Politis & White 2004 eq. 9)."""
    n, phi = 20000, 0.5
    want = (32.0 / 12.0) ** (1.0 / 3.0) * n ** (1.0 / 3.0)
    got = GS.pw_block(_ar1(phi, n, 2))
    assert abs(got / want - 1.0) < 0.15, (got, want)
    sb, cb = GS.optimal_block_length(_ar1(phi, n, 2))
    assert abs(cb / sb - (2.0 / (4.0 / 3.0)) ** (1.0 / 3.0)) < 1e-9                     # stationary/circular constants
    white = np.random.default_rng(0).standard_normal(3000)
    assert GS.pw_block(white) < 10 and GS.pw_block_floor(white) == 10                   # the 10-session floor
    short = _ar1(0.999, 200, 1)
    assert GS.pw_block(short) <= math.ceil(min(3 * math.sqrt(200), 200 / 3))            # the b_max cap
    assert GS.pw_block_floor(_ar1(0.9, 5000, 3)) >= 10
    _raises(lambda: GS.pw_block(np.ones(10)), ValueError)
    _raises(lambda: GS.pw_block(np.r_[white, np.nan]), ValueError)
    _raises(lambda: GS.pw_block(white, "moving"), ValueError)


def test_block_indices_schemes():
    T, block, B, seed = 500, 63, 1000, 20261002
    rng = np.random.default_rng(seed)                                                    # validate.sharpe_diff_bootstrap's draw
    starts = rng.integers(0, T, size=(B, int(math.ceil(T / block))))
    want = ((starts[:, :, None] + np.arange(block)[None, None, :]) % T).reshape(B, -1)[:, :T]
    got = GS.block_indices(T, block, B, seed)
    assert got.shape == (B, T) and np.array_equal(got, want)
    assert np.array_equal(got, GS.block_indices(T, block, B, seed))                     # deterministic
    st = GS.block_indices(4000, 20, 100, 5, "stationary")
    assert st.shape == (100, 4000) and st.min() >= 0 and st.max() < 4000
    runs = np.sum(np.diff(st, axis=1) != 1, axis=1) + 1                                 # blocks per row
    assert abs(4000 / runs.mean() - 20) < 3                                              # mean block length ~ 20
    _raises(lambda: GS.block_indices(T, block, B, seed, "moving"), ValueError)
    _raises(lambda: GS.block_indices(1, 1, 1, 0), ValueError)


def test_research_bootstrap_deterministic_and_share():
    rng = np.random.default_rng(20261002)
    b = rng.standard_normal(2000) * 0.01 + 0.0003
    a = b + rng.standard_normal(2000) * 0.002
    one, two = C.research_bootstrap(a, b), C.research_bootstrap(a, b)
    assert one == two and one.block == 63 and one.B == 1000 and one.seed == 20261002
    assert abs(one.share - (1.0 - one.p)) < 1e-12 and 0.0 <= one.share <= 1.0
    idx = GS.block_indices(a.size, 63, 1000, 20261002)
    d = GS.row_sharpes(a[idx]) - GS.row_sharpes(b[idx])
    assert abs(one.share - np.mean(d > 0)) < 1e-12                                      # share = fraction with dSR* > 0
    assert abs(one.dsr - (V.sharpe(a) - V.sharpe(b))) < 1e-12
    assert C.research_bootstrap(b + 0.001, b).share == 1.0                               # dominated comparator
    _raises(lambda: C.research_bootstrap(a[:100], b[:100]), ValueError)


def test_gate_boot_margin():
    rng = np.random.default_rng(11)
    b = rng.standard_normal(1500) * 0.01 + 0.0002
    a = b + rng.standard_normal(1500) * 0.003
    p0 = C.gate_boot(a, b, block=10, delta=0.0)
    assert abs(p0 - V.sharpe_diff_bootstrap(a, b, block=10, B=2000, seed=11)["p"]) < 1e-12
    ps = [C.gate_boot(a, b, block=10, delta=d) for d in (0.0, 0.05, 0.10, 0.5, 5.0)]
    assert ps == sorted(ps, reverse=True) and ps[-1] == 0.0 and all(0.0 <= p <= 1.0 for p in ps)
    assert C.gate_boot(a, b, block=10) == C.gate_boot(a, b, block=10, seed=11, B=2000)


# --------------------------------------------------------------------------- #
# v1.2-check mode (L5985-5990)
# --------------------------------------------------------------------------- #
def _synthetic(n_years=20, seed=7, crash_windows=6, drift=0.001, noise=0.010, crash_drift=-0.02, win_len=30,
               rally_drift=0.0, rally_windows=0):
    """Market with injected crash (and rally) windows; the rule halves exposure inside them (known in advance:
    this is a verdict-ordering test, not a causality test)."""
    rng = np.random.default_rng(seed)
    n = n_years * 252
    r = rng.standard_normal(n) * noise + drift
    dates, d = [], date(2004, 1, 2)
    while len(dates) < n:
        if d.weekday() < 5:
            dates.append(d)
        d += timedelta(days=1)
    dates = np.array(dates, dtype="datetime64[D]")
    h, windows = np.ones(n), []
    for s in np.linspace(300, n - 100, crash_windows).astype(int):
        r[s:s + win_len] += crash_drift
        h[s:s + win_len] = 0.5
        windows.append((dates[s - 1].astype(object), dates[s + win_len - 1].astype(object), False))
    if rally_windows:
        for s in np.linspace(300, n - 100, rally_windows).astype(int) + 120:
            r[s:s + win_len] += rally_drift
            h[s:s + win_len] = 0.5
    return r, h, dates, windows


def _books(r, h, cost=3.0):
    return C.costed_path(h, r, cost).net, C.costed_path(h, r, cost, 2.0).net, C.same_exposure_static(h, r)


def test_v12_check_verdict_ordering():
    r, h, dates, windows = _synthetic()
    on, on2, S = _books(r, h)
    res = C.v12_check(on, r, S, on_2x=on2, exposure=h, dates=dates, windows=windows)
    assert res.label == C.V12_LABEL == "v1.2-check, never a verdict"
    assert res.verdict_class == "PASS" and all((res.pc1, res.pc2, res.pc3, res.pc4, res.pc5, res.pc7)) and res.pc6 is None
    assert res.dmdd_1x_pp >= 3.0 and res.dmdd_2x_pp >= 3.0 and res.mdd_on > res.mdd_off
    assert res.tail_ratio <= 0.90 and res.p_ni == max(res.p10, res.p_pw) <= 0.10 and res.dsr_1x >= -0.10
    assert res.block == max(10, math.ceil(res.pw_block_d), math.ceil(res.pw_block_d2)) and res.block > 10
    assert res.n_windows == 6 and res.n_positive == 6 and res.largest_share <= 0.5 and res.years_positive_share >= 0.6
    assert res.n_sessions == 5040 and res.onsets is None
    # 1. sufficiency: a discrete rule with < 30 de-clustered onsets, or fewer than 882 sessions
    assert C.v12_check(on, r, S, on_2x=on2, exposure=h, dates=dates, windows=windows, discrete=True
                       ).verdict_class == "INSUFFICIENT DATA (sufficiency)"
    k = 600
    assert C.v12_check(on[:k], r[:k], S[:k], on_2x=on2[:k], exposure=h[:k], dates=dates[:k], windows=windows
                       ).verdict_class == "INSUFFICIENT DATA (sufficiency)"
    # 2. REJECT: the wrong-way rule (de-risks outside the crashes) fails PC-1 and PC-2 and dSR < -0.10
    hw = np.where(h < 1.0, 1.0, 0.5)
    onw, on2w, Sw = _books(r, hw)
    rej = C.v12_check(onw, r, Sw, on_2x=on2w, exposure=hw, dates=dates, windows=windows)
    assert rej.verdict_class == "REJECT" and not rej.pc1 and not rej.pc2 and rej.dsr_1x < -0.10 and rej.n_positive == 0
    # 3. inconclusive: protection holds (PC-1, PC-2, PC-4) but p_ni > 0.10 (the rule also halves rallies)
    ri, hi, di, wi = _synthetic(rally_drift=0.03, rally_windows=6)
    oni, on2i, Si = _books(ri, hi)
    inc = C.v12_check(oni, ri, Si, on_2x=on2i, exposure=hi, dates=di, windows=wi)
    assert inc.verdict_class == "INSUFFICIENT DATA (inconclusive)" and inc.pc1 and inc.pc2 and inc.pc4
    assert inc.p_ni > 0.10 and inc.dsr_1x >= -0.10 and not inc.pc3
    bon = C.v12_check(oni, ri, Si, on_2x=on2i, exposure=hi, dates=di, windows=wi, bonferroni=3)
    assert bon.p_ni == min(1.0, 3 * max(inc.p10, inc.p_pw)) and bon.bonferroni == 3
    # 4. REVISE: the 2x book loses the PC-1 margin (here: no better than S at 2x)
    rev = C.v12_check(on, r, S, on_2x=S, exposure=h, dates=dates, windows=windows)
    assert rev.verdict_class == "REVISE" and rev.dmdd_2x_pp == 0.0 and not rev.pc1
    # 4b. REVISE: declared neighbours that keep neither the PC-1 improvement nor the PC-3 point
    nb = C.v12_check(on, r, S, on_2x=on2, exposure=h, dates=dates, windows=windows, neighbours=[(S, S), (S, S), (on, S)])
    assert nb.verdict_class == "REVISE" and nb.pc6 is False and abs(nb.neighbours_kept - 1 / 3) < 1e-12
    _raises(lambda: C.v12_check(on, r, S, on_2x=on2, exposure=h, dates=dates, windows=windows, bonferroni=0), ValueError)
    _raises(lambda: C.v12_check(on, r, S[:-1], on_2x=on2, exposure=h, dates=dates), ValueError)


def test_v12_statistics_helpers():
    x = np.array([0.10, -0.50, 0.20, 0.0])
    assert abs(C.max_drawdown(x) - (-0.5)) < 1e-12 and abs(C.nav(x)[-1] - 1.1 * 0.5 * 1.2) < 1e-12
    dates = [date(2026, 6, 19), date(2026, 6, 22), date(2026, 6, 23), date(2026, 6, 24)]
    r = np.array([0.01, -0.02, 0.03, 0.04])
    after = C.window_return(r, dates, date(2026, 6, 22), date(2026, 6, 24))               # returns after the start close
    incl = C.window_return(r, dates, date(2026, 6, 22), date(2026, 6, 24), include_start=True)
    assert abs(after - (1.03 * 1.04 - 1)) < 1e-12 and abs(incl - (0.98 * 1.03 * 1.04 - 1)) < 1e-12
    n = 400
    d = np.array([date(2024, 1, 1) + timedelta(days=i) for i in range(n)], dtype="datetime64[D]")
    years = C.calendar_years(np.full(n, 0.001), d)
    assert set(years) == {2024} and abs(years[2024] - (1.001 ** 366 - 1)) < 1e-9          # 2025 has < 126 sessions
    off = np.linspace(-0.05, 0.05, 100)
    h = np.where(off < -0.04, 0.5, 1.0)
    assert abs(C.tail_exposure_ratio(h, off) - 0.5 / np.mean(h)) < 1e-12                 # worst 5 days all at 0.5
    path = np.array([1, 1, 0.4, 1, 0.4, 1, 1, 1, 1, 1, 0.4, 0.4, 1])
    assert C.declustered_onsets(path, gap=5) == 2 and C.declustered_onsets(path, gap=1) == 3   # onsets at 2, 4, 10
    assert C.declustered_onsets(np.ones(5), gap=5) == 0 and C.declustered_onsets(path, gap=8) == 1


# --------------------------------------------------------------------------- #
# Reference mode (L5992)
# --------------------------------------------------------------------------- #
def test_reference_mode_refused_from_core_and_tests():
    r = np.random.default_rng(3).standard_normal(300) * 0.012
    # from this module (tests/, not tests/reference/): refused even with reference_only=True
    _raises(lambda: C.vt_weights(r, 0.20, 20, 1.5, reference_only=True), C.RefusedConfiguration, "tests/reference/")
    _raises(lambda: C.costed_path(np.full(300, 1.2), r, 3.0, reference_only=True), C.RefusedConfiguration)
    # from a frame whose file lives under core/: refused
    probe = compile("from core.quant import costed as C\nC.vt_weights(r, 0.20, 20, 1.5, reference_only=True)\n",
                    str(CORE / "quant" / "_reference_probe.py"), "exec")
    _raises(lambda: exec(probe, {"r": r}), C.RefusedConfiguration)
    # the only honoured entry: tests/reference/reference_mode
    from tests.reference import reference_mode as RM
    w = RM.vt_weights(r, 0.20, 20, 1.5)
    assert np.nanmax(w) > 1.0 and np.nanmax(w) <= 1.5
    line = RM.vol_target_line(r, 0.20, 1.5, 0.0)
    assert line["reference_only"] is True and line["cap"] == 1.5 and math.isfinite(line["sharpe"])
    assert len(RM.result_md5(line)) == 32 and RM.result_md5(line) == RM.result_md5(dict(line))
    assert np.allclose(RM.product_stack([0.75, 1.0], [0.5, 0.5]), [0.375, 0.5])         # the product min() never emits
    _raises(lambda: RM.literal_ladder(), NotImplementedError, "M5")
    # the import guard: core/ cannot import tests.reference
    import tests.reference as TR
    reload = compile("importlib.reload(TR)\n", str(CORE / "_reference_import_probe.py"), "exec")
    _raises(lambda: exec(reload, {"importlib": importlib, "TR": TR}), ImportError, "core/ cannot import")
    importlib.reload(TR)                                                                 # back to a clean module
    assert C.reference_caller() == Path(__file__).resolve()


def test_reference_mode_static_core_never_imports():
    """No core/** module names tests.reference / reference_mode or passes reference_only=True (L5992)."""
    offenders = []
    for path in sorted(CORE.rglob("*.py")):
        code = _code_only(path)
        if "tests.reference" in code or "reference_mode" in code:
            offenders.append(f"{path.relative_to(ROOT).as_posix()}: names the reference package")
        for node in ast.walk(ast.parse(code)):
            if isinstance(node, ast.keyword) and node.arg == "reference_only" and \
                    isinstance(node.value, ast.Constant) and node.value.value is True:
                offenders.append(f"{path.relative_to(ROOT).as_posix()}:{node.lineno}: reference_only=True")
    assert not offenders, offenders
    sig = C.costed_path.__kwdefaults__, C.vt_weights.__kwdefaults__
    assert sig[0]["reference_only"] is False and sig[1]["reference_only"] is False


# --------------------------------------------------------------------------- #
# Reference goldens: REFDATA here; reference mode once the fixtures are listed
# --------------------------------------------------------------------------- #
def test_g_kr_06_cap15_reference_refdata():
    """Cap-1.5 vol target Sharpe 0.534, max DD -46.2% (pre-patch R4; L5778), reference mode, PENDING until the
    section 9.4 item 2 rerun is md5-frozen."""
    paths = _refdata("F13")
    from tests.reference import reference_mode as RM
    line = RM.vol_target_line(_window_returns(paths["yahoo_KS11_1996-12_2026-10-02.csv"]), 0.20, RM.CAP_G_KR_06, 0.0)
    G.assert_golden("G-KR-06", {"sharpe": line["sharpe"], "mdd": line["mdd"]})


test_g_kr_06_cap15_reference_refdata.test_ids = ["G-KR-06"]


def test_g_mom_07_reference_refdata():
    """Vol scale cap 2 Sharpe 0.907, DM gate 0x Sharpe 0.657 (L5754), reference mode on the French files."""
    _refdata("F10", "F11")
    raise NotRun("REFDATA: G-MOM-07 sleeve builders  # integration: provided by M4 (core/quant/sleeves.py) "
                 "through tests/reference/reference_mode")


test_g_mom_07_reference_refdata.test_ids = ["G-MOM-07"]


def _lad(golden_id: str):
    _refdata("F13", "U1", "F24")
    raise NotRun(f"REFDATA: {golden_id} literal ladder  # integration: provided by M5 (drawdown_ladder, literal v1.2 "
                 "reading) through tests/reference/reference_mode.literal_ladder")


def test_g_lad_01_reference_refdata():
    _lad("G-LAD-01")


def test_g_lad_02_reference_refdata():
    _lad("G-LAD-02")


def test_g_lad_03_reference_refdata():
    _lad("G-LAD-03")


test_g_lad_01_reference_refdata.test_ids = ["G-LAD-01"]
test_g_lad_02_reference_refdata.test_ids = ["G-LAD-02"]
test_g_lad_03_reference_refdata.test_ids = ["G-LAD-03"]


if __name__ == "__main__":
    from tests.macro_acceptance import run_module
    raise SystemExit(run_module(globals()))
