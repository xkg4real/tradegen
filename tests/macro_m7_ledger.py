"""M7 package B tests: family trial ledger, N_eff and step 3 (R-23; core/quant/gate_ledger.py; TASK-M7-01..05).

Spec tests: T-LEDGER-01, T-NEFF-01, T-STEP3-01, T-STEP3-02, T-SEL-01 (clauses (a)-(d), (f)-(h); (e) joins after
the freeze), T-DSR-02, and the ledger seeds of section 9.5 (REFDATA). Every numeric assertion runs on synthetic
panels or the inline numbers the brief checked; QF3's 26-trial matrix and every seed value are absent and report
NOT_RUN. Hermetic: ledgers are written to tempfile directories only (T-HERM-02); no clock; seeds explicit.
"""
from __future__ import annotations

import json
import math
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import scipy.stats as sps

from core.quant import gate_ledger as GL
from tests.acceptance import _code_only
from tests.notrun import NotRun, require_fixture

ROOT = Path(__file__).resolve().parents[1]
SEED = 11
DRAWS = 200_000
ANCHOR = "external:spec-fixture-anchor-1"


def _raises(fn, exc, needle: str = ""):
    try:
        fn()
    except exc as e:
        assert needle in str(e), f"{exc.__name__} without {needle!r}: {e}"
        return e
    raise AssertionError(f"{exc.__name__} not raised")


def _tmp_ledger(family: str = "R-06") -> GL.FamilyLedger:
    return GL.family_ledger(family, Path(tempfile.mkdtemp(prefix="m7_ledger_")))


def _row(**over) -> dict:
    base = dict(rule="R-06", params={"estimator": "sma", "window": 20, "target": 0.20}, estimator="sma", window=20,
                cap=1.0, instrument_book="KRX_ETF_line", rebalance="daily", start_convention="first_close_plus_warmup",
                timing_class="COMPLIANT", span=["2016-01-04", "2026-10-02"], market="KR",
                run_utc="2026-09-01T00:00:00Z", phase="research", script="docs/r4_vt.py", run_utc_anchor=ANCHOR,
                cost=3.0)
    base.update(over)
    return base


def _block_series(blocks: int = 5, size: int = 5, rho: float = 0.9, T: int = 4000, seed: int = SEED) -> dict:
    """K = blocks x size synthetic difference series: within-block correlation rho, zero across blocks."""
    rng = np.random.default_rng(np.random.SeedSequence(seed))
    out = {}
    for b in range(blocks):
        common = rng.standard_normal(T)
        for j in range(size):
            x = math.sqrt(rho) * common + math.sqrt(1.0 - rho) * rng.standard_normal(T)
            out[f"b{b}s{j}"] = x
    return out


def _header(**over) -> dict:
    h = {"card_id": "MACRO-R06-KR-ETF", "class": "CARD-P", "family_id": "R-06", "market": "KR",
         "data_span": {"start": "1997-04-01", "end": "2026-10-02"}, "created_utc": "2026-10-20T00:00:00Z",
         "ledger_hash_at_registration": ""}
    h.update(over)
    return h


# --------------------------------------------------------------------------- #
# T-LEDGER-01: append-only, hash chain, tamper, quick checks, hash at run
# --------------------------------------------------------------------------- #
def test_ledger01_chain_tamper_quick_checks_and_hash_at_run():
    lg = _tmp_ledger()
    assert lg.hash() == GL.ledger_hash([]) and lg.verify_chain().ok and lg.n_raw == 0
    r1 = GL.register_trial(lg, _row())
    r2 = GL.register_trial(lg, _row(params={"estimator": "sma", "window": 60, "target": 0.20}, window=60))
    r3 = GL.register_trial(lg, _row(params={"estimator": "sma", "window": 20, "target": 0.20, "lag": 0},
                                    timing_class="NON-COMPLIANT", run_kind="timing_lag", phase="card",
                                    card_id="MACRO-R06-KR-ETF"), script="core/quant/cardp.py::timing_profile")
    assert all(r.appended for r in (r1, r2, r3)) and lg.n_raw == 3
    rows = lg.rows()
    assert rows[0]["prev_row_md5"] is None and rows[1]["prev_row_md5"] == r1.row_md5 and rows[2]["prev_row_md5"] == r2.row_md5
    assert rows[2]["script"] == "core/quant/cardp.py::timing_profile" and rows[2]["timing_class"] == "NON-COMPLIANT"
    h3 = lg.hash()
    assert len({GL.ledger_hash(rows[:k]) for k in range(4)}) == 4            # the hash changes on every row
    assert lg.snapshot(GL.ledger_hash(rows[:2])) == rows[:2]
    _raises(lambda: lg.snapshot("0" * 32), GL.LedgerRefused, "names no snapshot")
    # a quick check from a research script is a row; a re-run of the same configuration is the same trial
    q = GL.register_trial(lg, _row(params={"estimator": "sma", "window": 20, "target": 0.25}, run_kind="quick_check",
                                   script="docs/scratch_quick_check.py"))
    assert q.appended and lg.n_raw == 4 and lg.hash() != h3
    again = GL.register_trial(lg, _row())
    assert not again.appended and again.row["config_id"] == r1.row["config_id"] and lg.n_raw == 4
    # the card's ledger_hash_at_run must equal the stored hash (the run's own rows included) or it is not written
    assert GL.assert_hash_at_run(lg, lg.hash()) == lg.hash()
    _raises(lambda: GL.assert_hash_at_run(lg, h3), GL.LedgerRefused, "card not written")
    # a hand-edited row (the last one, no later line anchors it) breaks the chain and the ledger is refused
    lines = lg.path.read_bytes().split(b"\n")
    row = json.loads(lines[3])
    row["params"]["target"] = 0.30
    lines[3] = GL.canonical_json(row).encode("utf-8")
    lg.path.write_bytes(b"\n".join(lines))
    check = lg.verify_chain()
    assert not check.ok and check.first_bad_line == 4 and "row_md5" in check.reason
    _raises(lambda: lg.rows(), GL.LedgerRefused, "chain broken")
    _raises(lambda: GL.register_trial(lg, _row(window=10)), GL.LedgerRefused, "chain broken")   # nothing appended
    # an edited middle row breaks prev_row_md5 of the next line; a dropped line too
    lg2 = _tmp_ledger()
    for r in (_row(), _row(window=60, params={"window": 60}), _row(window=10, params={"window": 10})):
        GL.register_trial(lg2, r)
    lines = lg2.path.read_bytes().split(b"\n")
    lg2.path.write_bytes(b"\n".join([lines[0], lines[2], b""]))
    assert not lg2.verify_chain().ok and lg2.verify_chain().first_bad_line == 2
    lines[1] = lines[1].replace(b'"cost":3.0', b'"cost":2.0')
    lg2.path.write_bytes(b"\n".join(lines))
    assert not lg2.verify_chain().ok


test_ledger01_chain_tamper_quick_checks_and_hash_at_run.test_ids = ["T-LEDGER-01"]


def test_ledger01_refusals_and_null_distribution_runs():
    """A row without a timing class, an unknown timing class, a bad span or phase is refused; placebo, shift-panel,
    GJR-null and D4-panel runs append no row (T-SEL-01 (f))."""
    lg = _tmp_ledger()
    GL.register_trial(lg, _row())
    before = (lg.n_raw, lg.hash())
    _raises(lambda: GL.register_trial(lg, _row(timing_class=None)), GL.LedgerRefused, "timing_class")
    _raises(lambda: GL.register_trial(lg, _row(timing_class="compliant")), GL.LedgerRefused, "timing_class")
    _raises(lambda: GL.register_trial(lg, _row(span=["2026-10-02", "2016-01-04"])), GL.LedgerRefused, "span")
    _raises(lambda: GL.register_trial(lg, _row(phase="placebo")), GL.LedgerRefused, "phase")
    _raises(lambda: GL.register_trial(lg, _row(run_utc="2026-09-01 00:00")), ValueError)
    _raises(lambda: GL.register_trial(lg, _row(extra_field=1)), GL.LedgerRefused, "unknown")
    for kind in GL.NULL_DISTRIBUTION_KINDS:
        _raises(lambda k=kind: GL.register_trial(lg, _row(run_kind=k, params={"tau": 300})),
                GL.NullDistributionRun, "no ledger row")
    assert (lg.n_raw, lg.hash()) == before
    # an unanchored run is still a row (every configuration ever run); only step 3 refuses it
    r = GL.register_trial(lg, _row(window=40, params={"window": 40}, run_utc_anchor=None))
    assert r.appended and r.row["run_utc_anchor"] == GL.UNVERSIONED and not GL.anchored(r.row["run_utc_anchor"])
    # a folder without .git is UNVERSIONED (rulings 3.1); a git folder anchors HEAD from a loose ref or, after
    # `git gc` / `git pack-refs`, from packed-refs (hermetic: fixture repos, never the live one, git since 2026-10-23)
    root, sha = Path(tempfile.mkdtemp(prefix="m7_git_")), "c" * 40
    assert GL.repo_anchor(root) == GL.UNVERSIONED
    (root / ".git" / "refs" / "heads").mkdir(parents=True)
    (root / ".git" / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    (root / ".git" / "packed-refs").write_text(f"# pack-refs with: peeled\n{sha} refs/heads/main\n", encoding="utf-8")
    assert GL.repo_anchor(root) == f"git:{sha}"
    (root / ".git" / "refs" / "heads" / "main").write_text("d" * 40 + "\n", encoding="utf-8")
    assert GL.repo_anchor(root) == "git:" + "d" * 40                       # a loose ref wins over packed-refs
    assert GL.anchored("git:" + "a" * 40) and GL.anchored("external:council-release-2.0.0") and not GL.anchored("git:")


test_ledger01_refusals_and_null_distribution_runs.test_ids = ["T-LEDGER-01", "T-SEL-01"]


def test_ledger_family_filing_by_rule_or_correlation():
    assert GL.file_family("R-29") == "R-06" and GL.file_family("R-04") == "R-03"
    s = _block_series(2, 3, 0.8, 1000)
    fam = {"R-06": {k: v for k, v in s.items() if k.startswith("b0")}, "R-28": {k: v for k, v in s.items() if k.startswith("b1")}}
    d_new = 0.9 * s["b1s0"] + 0.1 * np.random.default_rng(1).standard_normal(1000)
    assert GL.file_family("R-99", d_new, fam) == "R-28"
    _raises(lambda: GL.file_family("R-99", np.random.default_rng(2).standard_normal(1000), fam), GL.FamilyRefused, "refused")
    _raises(lambda: GL.file_family("R-99"), GL.FamilyRefused)


test_ledger_family_filing_by_rule_or_correlation.test_ids = ["T-LEDGER-01"]


# --------------------------------------------------------------------------- #
# T-NEFF-01: e(N), n_equiv, clusters, E_sim, padding, N_eff = max
# --------------------------------------------------------------------------- #
def test_neff01_e_of_n_and_n_equiv_round_trip():
    """e(N): 0 at N <= 1, exact integral below 2, closed form from 2 (drop 0.564 -> 0.520); e_inverse round trips;
    n_equiv(1.329) = 6.31 (brief D1)."""
    assert GL.emax_iid(1.0) == 0.0 and GL.emax_iid(0.5) == 0.0
    assert abs(GL.E_EXACT_2 - 1 / math.sqrt(math.pi)) < 1e-9 and abs(GL.E_CLOSED_2 - 0.51976) < 5e-5
    assert abs(GL.emax_iid(1.9999) - GL.E_EXACT_2) < 1e-3 and GL.emax_iid(2.0) == GL.E_CLOSED_2
    assert abs(GL.emax_iid(12.6) - 1.68837) < 1e-5 and abs(GL.emax_iid(6.3) - 1.32796) < 1e-5
    for n in (1.2, 1.5, 1.8, 2.0, 3.0, 6.3, 12.6, 46.0, 100.0, 1000.0, 1e5):   # (1.9, 2) maps to 2 by the spec rule
        assert abs(GL.n_equiv(GL.emax_iid(n)) - n) < 1e-6 * max(1.0, n), n
    for e in np.linspace(GL.E_CLOSED_2, GL.E_EXACT_2, 5):
        assert GL.n_equiv(float(e)) == 2.0
    assert GL.n_equiv(0.0) == 1.0 and GL.n_equiv(-1.0) == 1.0 and GL.n_equiv(10.0) == GL.N_MAX
    assert abs(GL.n_equiv(1.329) - 6.31) < 0.01
    assert abs(GL.linear_n_hat(0.46, 26) - 14.5) < 1e-9 and GL.linear_n_hat(1.0, 26) == 1.0 and GL.linear_n_hat(0.0, 26) == 26.0


test_neff01_e_of_n_and_n_equiv_round_trip.test_ids = ["T-NEFF-01"]


def test_neff01_synthetic_block_panel_clusters_emax_padding_and_max():
    """Five blocks of five series at rho 0.9: N_clusters 5; E_sim of an identity C equals the analytic iid value
    (E[max of 5] = 1.1630 +/- 0.01); N_equiv of the panel within 0.4 of the value at its exact correlation matrix;
    padding with 80 near-duplicates (rho 0.99) moves N_equiv by < 0.5; N_eff = max(N_clusters, N_equiv)."""
    series = _block_series(5, 5, 0.9, 4000)
    C = GL.diff_corr(series)
    assert C.shape == (25, 25) and np.allclose(np.diag(C), 1.0)
    assert GL.n_clusters(C) == 5
    for k in (2, 3, 5, 10):
        exact = GL.emax_iid_exact(k)                                       # analytic E[max of k iid N(0,1)]
        assert abs(GL.emax_sim(np.eye(k), DRAWS, SEED) - exact) < 0.01, k
    assert GL.emax_sim(np.eye(1)) == 0.0 and GL.n_clusters(np.eye(1)) == 1
    design = np.kron(np.eye(5), np.full((5, 5), 0.9))
    np.fill_diagonal(design, 1.0)
    res = GL.n_eff(series, draws=DRAWS, seed=SEED)
    want = GL.n_equiv(GL.emax_sim(design, DRAWS, SEED))
    assert abs(res.N_equiv - want) < 0.4 and res.N_raw == 25 and res.N_clusters == 5
    assert abs(res.rho_bar - GL.mean_offdiag(C)) < 1e-12 and abs(res.N_hat_linear - GL.linear_n_hat(res.rho_bar, 25)) < 1e-12
    assert res.N_eff == max(res.N_clusters, res.N_equiv)
    assert GL.emax_sim(C, DRAWS, SEED) == GL.emax_sim(C, DRAWS, SEED)       # same seed, same draw
    assert GL.emax_sim(C, DRAWS, SEED) != GL.emax_sim(C, DRAWS, SEED + 1)
    # padding: 80 near-duplicates of one series move N_equiv by < 0.5 and N_clusters not at all
    rng = np.random.default_rng(np.random.SeedSequence(SEED + 7))
    padded = dict(series)
    base = series["b0s0"]
    for j in range(80):
        padded[f"dup{j}"] = math.sqrt(0.99) * base + math.sqrt(0.01) * rng.standard_normal(base.size)
    pres = GL.n_eff(padded, draws=DRAWS, seed=SEED)
    assert pres.N_raw == 105 and pres.N_clusters == 5 and abs(pres.N_equiv - res.N_equiv) < 0.5, (res, pres)
    # the linear N-hat is a bound that padding games: it jumps; it is printed, never the gate's N
    assert pres.N_hat_linear != res.N_hat_linear
    # the max rule: a panel whose clusters exceed its N_equiv takes N_clusters
    far = _block_series(8, 1, 0.9, 4000)
    r8 = GL.n_eff(far, draws=DRAWS, seed=SEED)
    assert r8.N_clusters == 8 and r8.N_eff == max(8.0, r8.N_equiv) and r8.N_eff >= 8.0
    # a correlation that cannot be built fails closed
    _raises(lambda: GL.diff_corr({"a": np.ones(100), "b": base[:100]}), GL.CorrUnavailable, "variance")
    _raises(lambda: GL.diff_corr({"a": base[:10], "b": base[:10]}), GL.CorrUnavailable, "common window")
    _raises(lambda: GL.diff_corr({"a": base, "b": None}), GL.CorrUnavailable, "missing")
    # undated arrays of different spans are never tail-paired (day t of one against day t + k of the other)
    _raises(lambda: GL.diff_corr({"a": base, "b": series["b1s0"][500:]}), GL.CorrUnavailable, "unequal length")
    # pandas Series align on the intersection of their indices (the common window)
    idx = pd.date_range("2016-01-04", periods=4000, freq="B")
    a = pd.Series(base, index=idx)
    b = pd.Series(series["b1s0"], index=idx)[500:]
    C2 = GL.diff_corr({"a": a, "b": b})
    assert abs(C2[0, 1] - np.corrcoef(base[500:], series["b1s0"][500:])[0, 1]) < 1e-12


test_neff01_synthetic_block_panel_clusters_emax_padding_and_max.test_ids = ["T-NEFF-01"]


def test_neff01_qf3_26_trial_matrix_refdata():
    """E_sim 1.33 +/- 0.01, N_equiv 6.3 +/- 0.4, N_clusters 5, N_hat_linear 12.6 +/- 0.1 and the 6.33 -> 6.59 padding
    on QF3's matrix need QX_EX1_qf3_trial_corr_diff.csv (absent, no local substitute)."""
    rows = GL.load_seed(ROOT / "tests" / "fixtures" / "macro" / "ledger_seed_R-03.csv")
    assert len(rows) == 26 and [r["row_id"] for r in rows] == [f"R-03-T{k:02d}" for k in range(1, 27)]   # 26 rows stay 26
    require_fixture("QX_EX1_qf3_trial_corr_diff.csv")
    raise AssertionError("fixture listed: golden assertion not implemented")


test_neff01_qf3_26_trial_matrix_refdata.test_ids = ["T-NEFF-01"]


# --------------------------------------------------------------------------- #
# T-STEP3-01: the inline numbers; T-DSR-02 units
# --------------------------------------------------------------------------- #
def test_step3_01_inline_numbers_r03_pass_borderline_r04_fail():
    """R-03 dSR 0.2729, SE_obs 0.0716, SE_null 0.0935: 0.98 +/- 0.01 PASS at N 6.3, 0.947 +/- 0.01 at N_hat_linear 12.6
    flagged "step 3 borderline", break-even N 11.86; R-04 0.0724 / 0.0349 / 0.0349: 0.77 +/- 0.02 FAIL."""
    n = GL.NResult(26, 0.46, 12.6, 5, 1.33, 6.3, 6.3)
    lines = GL.step3_lines(0.2729, 0.0716, 0.0935, n)
    assert abs(lines["deflated_dSR"] - 0.98) <= 0.01 and abs(lines["deflated_dSR"] - 0.9811) < 1e-3
    assert lines["deflated_dSR"] >= GL.CARD_O_BAR
    assert abs(lines["at_N_hat_linear"] - 0.947) <= 0.01 and abs(lines["at_N_hat_linear"] - 0.9459) < 1e-3
    assert lines["borderline"] and lines["flag"] == "step 3 borderline"
    assert abs(lines["break_even_N"] - 11.86) < 0.01
    assert abs(GL.deflated_dsr(0.2729, 0.0716, 0.0935, GL.emax_iid(lines["break_even_N"])) - 0.95) < 1e-6
    assert lines["z_check"]["pass"] and abs(lines["z_check"]["z"] - 3.81) < 0.01 and lines["z_check"]["bar"] == 3.34
    assert GL.step3_lines(0.2729, 0.0716, 0.0935, n, cells=8)["z_check"]["bar"] == 2.50
    assert lines["by_q"] is None and lines["holm"] is None      # integration: gate_stats (printed only)
    r04 = GL.deflated_dsr(0.0724, 0.0349, 0.0349, GL.emax_iid(6.3))
    assert abs(r04 - 0.77) <= 0.02 and abs(r04 - 0.7723) < 1e-3 and r04 < GL.CARD_O_BAR
    be = GL.break_even_n(0.0724, 0.0349, 0.0349)                 # R-04 passes at N = 1 (0.981) and fails at 6.3
    assert 1.0 < be < 2.0 and abs(GL.deflated_dsr(0.0724, 0.0349, 0.0349, GL.emax_iid(be)) - 0.95) < 1e-6
    assert GL.break_even_n(0.05, 0.0349, 0.0349) is None       # below 0.95 already at N = 1: no break-even
    assert GL.break_even_n(0.2, 0.07, 0.0) is None              # SE_null 0: no N moves it
    assert GL.deflated_dsr(0.2729, 0.0716, 0.0935, 0.0) == sps.norm.cdf(0.2729 / 0.0716)   # N = 1: no hurdle
    _raises(lambda: GL.deflated_dsr(0.1, 0.0, 0.1, 1.0), ValueError)


test_step3_01_inline_numbers_r03_pass_borderline_r04_fail.test_ids = ["T-STEP3-01"]


def test_step3_01_end_to_end_from_the_matrix_refdata():
    """R-03 / R-04 step 3 with N from QF3's matrix (not inline) needs QX_EX1_qf3_trial_corr_diff.csv."""
    require_fixture("QX_EX1_qf3_trial_corr_diff.csv")
    raise AssertionError("fixture listed: golden assertion not implemented")


test_step3_01_end_to_end_from_the_matrix_refdata.test_ids = ["T-STEP3-01"]


def test_dsr02_units_daily_monthly_agree_and_annualised_sr_raises():
    """PSR / DSR take the per-period SR and T in one declared unit; daily and monthly values of one series agree
    within 0.1; an annualised SR passed with a daily T raises."""
    rng = np.random.default_rng(np.random.SeedSequence(SEED))
    daily = 0.0004 + 0.01 * rng.standard_normal(252 * 12)
    idx = pd.date_range("2014-01-01", periods=daily.size, freq="B")
    monthly = (1.0 + pd.Series(daily, index=idx)).resample("ME").prod() - 1.0
    d = GL.dsr_vs_zero(daily, units="daily")
    m = GL.dsr_vs_zero(monthly.to_numpy(), units="monthly")
    assert 0.0 < d < 1.0 and abs(d - m) < 0.1, (d, m)
    sr_annual = float(np.mean(daily) / np.std(daily, ddof=1) * math.sqrt(252))
    _raises(lambda: GL.psr(sr_annual, daily.size, units="daily"), ValueError, "annualised")
    _raises(lambda: GL.psr(0.01, daily.size, units="weekly"), ValueError, "units")
    assert abs(GL.psr_vs_s(daily, daily, units="daily") - 0.5) < 1e-12        # identical to S: 0.5


test_dsr02_units_daily_monthly_agree_and_annualised_sr_raises.test_ids = ["T-DSR-02"]


# --------------------------------------------------------------------------- #
# T-STEP3-02: refusals and the static Kish guard
# --------------------------------------------------------------------------- #
def test_step3_02_no_ledger_hash_refused_and_no_kish_anywhere():
    lg = _tmp_ledger()
    GL.register_trial(lg, _row())
    kw = dict(delta_sr=0.2729, se_obs=0.0716, se_null=0.0935, commit=GL.Anchor("2026-10-20T00:00:00Z", ANCHOR))
    _raises(lambda: GL.step3(_header(ledger_hash_at_registration=""), lg, SEED, **kw), GL.HeaderRefused, "ledger_hash_at_registration")
    h = _header(ledger_hash_at_registration=lg.hash())
    del h["ledger_hash_at_registration"]
    _raises(lambda: GL.step3(h, lg, SEED, **kw), GL.HeaderRefused, "ledger_hash_at_registration")
    _raises(lambda: GL.step3(_header(ledger_hash_at_registration=lg.hash(), selection_factor={"value": 1.0}), lg, SEED, **kw),
            GL.HeaderRefused, "selection_factor")
    _raises(lambda: GL.step3(_header(ledger_hash_at_registration=lg.hash(), **{"class": "CARD-X"}), lg, SEED, **kw),
            GL.HeaderRefused, "class")
    # static scan: no implementation of M / (1 + (M - 1) rho), no Kish definition or call, no revision count as N
    files = [p for base in ("core", "docs") for p in (ROOT / base).rglob("*.py") if "__pycache__" not in p.parts]
    files += [ROOT / "config.py", ROOT / "main.py"]
    sources = {p.relative_to(ROOT).as_posix(): _code_only(p) for p in files if p.is_file()}
    assert len(sources) > 50
    hits = GL.scan_forbidden(sources)
    assert hits == [], hits
    # positive controls: the guard trips on each forbidden shape
    controls = {"a": "n_hat = M / (1 + (M - 1) * rho_bar)", "b": "x = m / (1.0 + rho * (m - 1))",
                "c": "N_raw = len(header['revisions'])", "d": "from kish import design_effect",
                "e": "def kish_n(m, r):\n    return m", "f": "n = kish_effect(m, rho)"}
    found = GL.scan_forbidden(controls)
    assert {h.split(":")[0] for h in found} == set(controls), found
    assert "a: kish_design_effect" in found and "c: revision_count_as_N" in found and "d: kish_name" in found
    # labels and refusal predicates are not implementations
    assert GL.scan_forbidden({"l": "forbidden = ['kish_design_effect']\nkish = [k for k in keys]"}) == []
    assert GL.scan_forbidden({"ok": "n_hat = rho + (1 - rho) * m\nx = 1 / n\ny = a / (1 + b)"}) == []


test_step3_02_no_ledger_hash_refused_and_no_kish_anywhere.test_ids = ["T-STEP3-02", "T-NEFF-01"]


# --------------------------------------------------------------------------- #
# T-SEL-01: the selection factor is computed, never declared
# --------------------------------------------------------------------------- #
def _family_with_series(n_rows: int = 4, seed: int = SEED):
    lg = _tmp_ledger()
    series = _block_series(n_rows, 1, 0.9, 3000, seed)
    keys = list(series)
    rows = []
    for k, name in enumerate(keys):
        r = GL.register_trial(lg, _row(params={"estimator": "sma", "window": 20 + 10 * k, "target": 0.20},
                                       window=20 + 10 * k, run_utc=f"2026-09-0{k + 1}T00:00:00Z",
                                       diff_series_ref=name, delta_sr=0.1 + 0.01 * k))
        rows.append(r.row)
    series = {r["config_id"]: series[r["diff_series_ref"]] for r in rows}
    return lg, rows, series


def test_sel01_a_rows_touching_the_span_before_the_commit_give_f_neff():
    """(a) A and B run on 2016-26 (anchored), A's header is committed, A runs on 1997-2026: f = N_eff under any_overlap."""
    lg, rows, series = _family_with_series(2)
    card = _header(ledger_hash_at_registration=lg.hash())
    commit = GL.Anchor("2026-10-20T00:00:00Z", ANCHOR)
    res = GL.step3(card, lg, SEED, delta_sr=0.2729, se_obs=0.0716, se_null=0.0935, series=series, commit=commit)
    want = GL.n_eff(series, draws=DRAWS, seed=SEED).N_eff
    assert res["f"] == want > 1.0 and res["f_by_reading"] == {"market_scoped": want, "family_wide": want}
    assert res["f_at_1"] == 1.0 and res["f_at_neff"] == want and res["n_raw"] == 2 and res["n_eff"] == want
    assert res["selection_factor"] == {"value": want, "rule": "computed_by_step3", "alt_value": 1.0}
    assert res["verdict_contrib"] == {"gated": False, "pass": None, "bar": None}          # CARD-P: not gated
    assert res["printed"]["N_raw"] == 2 and res["printed"]["N_clusters"] == 2
    # a different market's rows touch only the family-wide reading
    lg2, rows2, series2 = _family_with_series(3)
    us = GL.register_trial(lg2, _row(market="US", params={"estimator": "sma", "window": 15, "target": 0.15}, window=15,
                                     diff_series_ref="us", run_utc="2026-09-05T00:00:00Z"))
    series2[us.row["config_id"]] = _block_series(1, 1, 0.9, 3000, 99)["b0s0"]
    card2 = _header(market="US", ledger_hash_at_registration=lg2.hash())
    res2 = GL.step3(card2, lg2, SEED, delta_sr=0.1, se_obs=0.05, series=series2, commit=commit)
    assert res2["f_by_reading"]["market_scoped"] == 1.0           # only its own run touched the US span
    assert res2["f_by_reading"]["family_wide"] > 1.0 and res2["f"] == res2["f_by_reading"]["family_wide"]


test_sel01_a_rows_touching_the_span_before_the_commit_give_f_neff.test_ids = ["T-SEL-01"]


def test_sel01_b_configuration_fixed_before_any_row_touched_its_span_gives_f_1_only_anchored():
    """(b) f = 1 for a configuration committed before any family row touched its span, through anchored timestamps
    only; rows run after the commit are sensitivity rows; rows outside the span never touch it; an unanchored commit
    or row refuses step 3 with the owner action in the reason (TASK-M7-05, rulings 3.1)."""
    lg, rows, series = _family_with_series(3)
    card = _header(ledger_hash_at_registration=lg.hash())
    kw = dict(delta_sr=0.2729, se_obs=0.0716, se_null=0.0935, series=series)
    early = GL.Anchor("2026-08-01T00:00:00Z", "git:" + "b" * 40)                  # before every row's run_utc
    res = GL.step3(card, lg, SEED, commit=early, **kw)
    assert res["f"] == 1.0 and res["f_by_reading"] == {"market_scoped": 1.0, "family_wide": 1.0}
    assert res["f_at_neff"] > 1.0 and res["selection_factor"]["alt_value"] == res["f_at_neff"]
    assert res["printed"]["N_eff"] == res["f_at_neff"] and res["fixed_at"] == "2026-08-01T00:00:00Z"
    # a published SPEC version naming the configuration is the earlier anchored instant
    cid = rows[0]["config_id"]
    spec = GL.Anchor("2026-07-01T00:00:00Z", "external:SPEC-v1.1", "spec_version", (cid,))
    late = GL.Anchor("2026-10-20T00:00:00Z", ANCHOR)
    res_spec = GL.step3({**card, "config_id": cid}, lg, SEED, commit=late, spec_versions=[spec], **kw)
    assert res_spec["f"] == 1.0 and res_spec["fixed_at"] == "2026-07-01T00:00:00Z"
    assert GL.step3(card, lg, SEED, commit=late, spec_versions=[spec], **kw)["f"] > 1.0   # not this config
    # rows outside the evaluation span never touch it
    narrow = _header(ledger_hash_at_registration=lg.hash(), data_span={"start": "1997-04-01", "end": "2015-12-31"})
    assert GL.step3(narrow, lg, SEED, commit=late, **kw)["f"] == 1.0
    # unanchored: the commit (an UNVERSIONED header commit, explicit now that this folder is under git) or a row
    unv = GL.Anchor(card["created_utc"], GL.UNVERSIONED, "header_commit")
    e = _raises(lambda: GL.step3(card, lg, SEED, commit=unv, **kw), GL.UnanchoredTimestamp,
                "owner must place the repository under git")
    assert GL.UNVERSIONED in str(e)
    _raises(lambda: GL.step3(card, lg, SEED, commit=GL.Anchor("2026-08-01T00:00:00Z", "git:"), **kw), GL.UnanchoredTimestamp)
    lg_u = _tmp_ledger()
    GL.register_trial(lg_u, _row(run_utc_anchor=None))
    _raises(lambda: GL.step3(_header(ledger_hash_at_registration=lg_u.hash()), lg_u, SEED, commit=late, **kw),
            GL.UnanchoredTimestamp, "ledger row")


test_sel01_b_configuration_fixed_before_any_row_touched_its_span_gives_f_1_only_anchored.test_ids = ["T-SEL-01"]


def test_sel01_c_d_declared_factor_refused_both_verdict_inputs_printed_card_o_gated():
    """(c) a header declaring selection_factor is refused; (d) the deflated value and f are printed at f = 1 and at
    f = N_eff; a CARD-O passes iff deflated >= 0.95 at N_eff; C unavailable: CARD-O no verdict, CARD-P f = N_raw."""
    lg, rows, series = _family_with_series(3)
    commit = GL.Anchor("2026-10-20T00:00:00Z", ANCHOR)
    card = _header(ledger_hash_at_registration=lg.hash())
    _raises(lambda: GL.step3({**card, "selection_factor": {"value": 1.0, "rule": "computed_by_step3", "alt_value": 1.0}},
                             lg, SEED, delta_sr=0.2, se_obs=0.07, series=series, commit=commit), GL.HeaderRefused, "selection_factor")
    res = GL.step3(card, lg, SEED, delta_sr=0.2729, se_obs=0.0716, se_null=0.0935, series=series, commit=commit,
                   x_rule=0.0004 + 0.01 * np.random.default_rng(1).standard_normal(2000),
                   x_s=0.0003 + 0.01 * np.random.default_rng(2).standard_normal(2000))
    assert res["dsr_at_1"] == GL.deflated_dsr(0.2729, 0.0716, 0.0935, 0.0)
    assert res["dsr_at_neff"] == GL.deflated_dsr(0.2729, 0.0716, 0.0935, GL.emax_iid(res["n_eff"]))
    assert res["dsr_at_neff"] < res["dsr_at_1"] and 0 < res["printed"]["dsr_vs0"] < 1 and 0 < res["printed"]["psr_vs_S"] < 1
    for key in ("N_raw", "N_hat_linear", "N_clusters", "N_equiv", "N_eff", "E_sim", "SE_obs", "SE_null", "V_trials",
                "at_N_raw", "at_N_hat_linear", "borderline", "break_even_N", "z_check", "by_q"):
        assert key in res["printed"], key
    assert res["printed"]["V_trials"] is None                      # < 30 independent trials: V_null only
    # CARD-O: gated at 0.95; SE_null absent -> SE_obs
    o = GL.step3({**card, "class": "CARD-O"}, lg, SEED, delta_sr=0.2729, se_obs=0.0716, se_null=0.0935, series=series, commit=commit)
    assert o["verdict_contrib"] == {"gated": True, "pass": True, "bar": 0.95}
    o2 = GL.step3({**card, "class": "CARD-O"}, lg, SEED, delta_sr=0.0724, se_obs=0.0349, series=series, commit=commit)
    assert o2["verdict_contrib"]["pass"] is False and o2["printed"]["SE_null"] == 0.0349
    # C unavailable: CARD-O writes no verdict (raises); CARD-P defaults f to N_raw and says so
    partial = {k: v for k, v in list(series.items())[:2]}
    _raises(lambda: GL.step3({**card, "class": "CARD-O"}, lg, SEED, delta_sr=0.2, se_obs=0.07, series=partial, commit=commit),
            GL.CorrUnavailable, "no verdict written")
    p = GL.step3(card, lg, SEED, delta_sr=0.2, se_obs=0.07, series=partial, commit=commit)
    assert p["f"] == 3.0 == p["n_raw"] and p["fail_closed"] and "missing" in p["fail_closed"]
    # a loader resolves the stored references; a failing loader is the same fail-closed path
    store = {r["diff_series_ref"]: series[r["config_id"]] for r in rows}
    via_loader = GL.step3(card, lg, SEED, delta_sr=0.2729, se_obs=0.0716, se_null=0.0935, loader=store.__getitem__, commit=commit)
    assert via_loader["f"] == res["f"]
    _raises(lambda: GL.step3({**card, "class": "CARD-O"}, lg, SEED, delta_sr=0.2, se_obs=0.07, loader=lambda ref: {}[ref], commit=commit),
            GL.CorrUnavailable, "unavailable")


test_sel01_c_d_declared_factor_refused_both_verdict_inputs_printed_card_o_gated.test_ids = ["T-SEL-01", "T-STEP3-02"]


def test_sel01_f_g_h_own_rows_excluded_readings_max_and_two_rows():
    """(f) the card's own lag rows do not enter its f and null runs append no row; (g) readings 1.3 and 2.9 -> 2.9
    (and the larger of the run's and the report's f, both printed); (h) target, threshold, multiplier or lag differences
    are distinct configurations."""
    lg, rows, series = _family_with_series(2)
    commit = GL.Anchor("2026-10-20T00:00:00Z", ANCHOR)
    card = _header(ledger_hash_at_registration=lg.hash())
    base = GL.step3(card, lg, SEED, delta_sr=0.2, se_obs=0.07, series=series, commit=commit)
    for lag, cls in ((-1, "NON-COMPLIANT"), (0, "NON-COMPLIANT"), (1, "COMPLIANT"), (2, "COMPLIANT")):
        r = GL.register_trial(lg, _row(params={"estimator": "sma", "window": 20, "target": 0.20, "lag": lag}, timing_class=cls,
                                       run_kind="timing_lag", phase="card", card_id=card["card_id"], span=["1997-04-01", "2026-10-02"],
                                       run_utc="2026-10-21T00:00:00Z", diff_series_ref=f"lag{lag}"))
        series[r.row["config_id"]] = _block_series(1, 1, 0.9, 3000, 100 + lag)["b0s0"]
    assert lg.n_raw == 6
    after = GL.step3(card, lg, SEED, delta_sr=0.2, se_obs=0.07, series=series, commit=commit)
    assert after["n_raw"] == base["n_raw"] == 2 and after["f"] == base["f"]
    # those lag rows count for a later card of the family (registered at the new hash)
    later = _header(card_id="MACRO-R06-KR-ETF-r2", ledger_hash_at_registration=lg.hash())
    assert GL.step3(later, lg, SEED, delta_sr=0.2, se_obs=0.07, series=series,
                    commit=GL.Anchor("2026-11-01T00:00:00Z", ANCHOR))["n_raw"] == 6
    # (g)
    assert GL.combine_readings({"market_scoped": 1.3, "family_wide": 2.9}) == 2.9
    assert GL.combine_readings({"market_scoped": 2.9, "family_wide": 1.3}, acceptance_f=1.5) == 2.9
    assert GL.combine_readings({"market_scoped": 1.0, "family_wide": 1.0}, acceptance_f=1.49) == 1.49
    rep = GL.step3(card, lg, SEED, delta_sr=0.2, se_obs=0.07, series=series, commit=commit, acceptance_f=99.0)
    assert rep["f"] == 99.0 and rep["acceptance_f"] == 99.0 and rep["f_by_reading"] == base["f_by_reading"]
    # (h)
    lg2 = _tmp_ledger()
    p = {"signal": "sma", "threshold": 0.0, "target": 0.20, "lookback": 20, "multiplier": 0.5, "lag": 1}
    ids = set()
    for change in ({}, {"target": 0.15}, {"threshold": 0.01}, {"multiplier": 0.75}, {"lag": 2}):
        ids.add(GL.register_trial(lg2, _row(params={**p, **change})).row["config_id"])
    assert len(ids) == 5 and lg2.n_raw == 5
    assert GL.config_id(_row()) == GL.config_id(_row(run_utc="2000-01-01T00:00:00Z", script="other.py", cost=5.0))   # key fields only
    assert GL.config_id(_row(timing_class="VALUE")) != GL.config_id(_row())


test_sel01_f_g_h_own_rows_excluded_readings_max_and_two_rows.test_ids = ["T-SEL-01"]


def test_sel01_e_card_run_f_vs_acceptance_report_f_after_freeze():
    """(e) joins after the freeze (section 9.0b): the acceptance report does not exist (package NOT_FROZEN); the
    arithmetic (larger binds, both printed, never a refusal) is asserted in the (g) test."""
    raise NotRun("PENDING: T-SEL-01 (e) runs after the gate freeze (section 9.0b); gate.package.status is NOT_FROZEN "
                 "and no acceptance report exists on this machine")


test_sel01_e_card_run_f_vs_acceptance_report_f_after_freeze.test_ids = ["T-SEL-01"]


# --------------------------------------------------------------------------- #
# Revisions: adoption counts as one revision, never a row
# --------------------------------------------------------------------------- #
def test_adoption_is_a_revision_and_a_package_freeze_event_never_a_row():
    from datetime import datetime, timezone
    from core.rules.governance import read_events, verify_chain
    lg_a, lg_b = _tmp_ledger("R-06"), _tmp_ledger("R-03")
    GL.register_trial(lg_a, _row())
    GL.register_trial(lg_b, _row(rule="R-03", market="US"))
    hashes = (lg_a.hash(), lg_b.hash())
    headers = [{"card_id": "A", "revision": 2}, {"card_id": "B", "revision": 1}]
    log = Path(tempfile.mkdtemp(prefix="m7_gov_")) / "governance_events.jsonl"
    clock = lambda: datetime(2026, 10, 22, tzinfo=timezone.utc)
    out = GL.record_adoption([lg_a, lg_b], headers, governance_log=log, clock=clock, version="2.0.0", definitions_md5="0" * 32)
    assert [h["revision"] for h in out["headers"]] == [3, 2] and headers[0]["revision"] == 2
    assert out["headers"][0]["revision_reasons"] == ["package_adoption:2.0.0"]
    assert (lg_a.hash(), lg_b.hash()) == hashes and out["n_rows"] == {"R-06": 1, "R-03": 1}
    events = read_events(log)
    assert verify_chain(log).ok and len(events) == 1 and events[0]["kind"] == "package_freeze" and events[0]["actor"] == "harness"
    assert GL.bump_revision({"revision": 1}, "class_change")["revision"] == 2


test_adoption_is_a_revision_and_a_package_freeze_event_never_a_row.test_ids = ["T-LEDGER-01"]


# --------------------------------------------------------------------------- #
# Ledger seeds (section 9.5; TASK-M7-02): structure shipped, values REFDATA
# --------------------------------------------------------------------------- #
SEED_COUNTS = {"R-03": 26, "R-06": 35, "R-28": 94, "R-31": 6}


def test_ledger_seeds_load_with_null_values_and_report_refdata():
    """Each seed file is manifest-listed, has the section 9.5 columns and the row ids the brief gives (R-03 26 trials,
    R-28 94 DLB-T3f variants, R-31 EX1 L1-L6); every value column is null and says so; a null row is not registrable."""
    missing_total = 0
    for family, n in SEED_COUNTS.items():
        path = require_fixture(f"ledger_seed_{family}.csv")
        rows = GL.load_seed(path)
        assert len(rows) == n, (family, len(rows))
        assert all(r["comment"] and "absent reference file" in r["comment"] for r in rows)
        missing = GL.seed_missing(rows)
        assert missing == [r["row_id"] for r in rows]
        missing_total += len(missing)
        for r in rows[:3]:
            _raises(lambda r=r: GL.register_trial(_tmp_ledger(family), {**{k: r[k] for k in ("span", "run_utc", "timing_class")},
                                                                        "rule": family, "params": r["params"] or {}, "market": r["market"],
                                                                        "phase": "research", "script": r["source_file"]}),
                    GL.LedgerRefused)
    r28 = GL.load_seed(require_fixture("ledger_seed_R-28.csv"))
    sig = {(r["params"]["signal"], r["params"]["lookback_months"], r["params"]["multiplier_below"]) for r in r28}
    assert len(sig) == 94 and {s for s, _, _ in sig} == {"sma", "ts"} and {m for _, _, m in sig} == {0.5, 0.0}
    assert {m for s, m, _ in sig if s == "sma"} == set(range(2, 25)) and {m for s, m, _ in sig if s == "ts"} == set(range(1, 25))
    r31 = GL.load_seed(require_fixture("ledger_seed_R-31.csv"))
    assert [r["row_id"] for r in r31] == [f"R-31-EX1-L{k}" for k in range(1, 7)]
    r06 = GL.load_seed(require_fixture("ledger_seed_R-06.csv"))
    assert {r["market"] for r in r06} == {"KR", "US"} and sum(r["market"] == "US" for r in r06) == 6   # DLA-U1..U5, DLB-T1h
    assert sum(r["row_id"].startswith("R-06-DLA-K") for r in r06) == 9
    raise NotRun(f"REFDATA: ledger seed rows from QX_* files ({missing_total} rows across 4 families: "
                 "QX_EX1_qf3_trial_corr_diff.csv, R4/R4b golden files, QX_DLA_*, QX_DLB_*, QX_EX1 ladders; run_utc anchors "
                 "need a git commit, section 9.4 item 15)")


test_ledger_seeds_load_with_null_values_and_report_refdata.test_ids = ["T-NEFF-01", "T-SEL-01"]


def test_module_has_no_wall_clock_and_no_config_import():
    import ast
    src = (ROOT / "core" / "quant" / "gate_ledger.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    calls = {ast.unparse(n.func) for n in ast.walk(tree) if isinstance(n, ast.Call)}
    assert not {c for c in calls if c.endswith(("now", "today", "time.time", "utcnow"))}, calls
    imports = {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    froms = {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
    assert "config" not in imports and "config" not in froms
    assert "core.ficc.context_log" not in froms and "core.ficc.macro" not in froms


test_module_has_no_wall_clock_and_no_config_import.test_ids = ["T-LEDGER-01"]


if __name__ == "__main__":
    from tests.macro_acceptance import run_module
    raise SystemExit(run_module(globals()))
