"""Sprint 7 carry-over package D: TASK-M9-03, the seeded scenario library (core/quant/scenarios.py) and the SEP-band
rate paths (core/ficc/ratesim.sep_band_params / sep_band_paths). T-REPRO-01c on scenarios, the I-11 scenario clause
(seeded and reproducible; no sizing module imports scenarios or lab), the LETF path identity, the SEP band dispersion,
Brent naming; the reference-data and owner clauses NOT_RUN. Hermetic: inline synthetic series with fixed dates,
nothing written anywhere; the shipped store is read, never written (T-HERM-02)."""
from __future__ import annotations

import ast
import math
import tempfile
from dataclasses import fields, replace
from datetime import date, timedelta
from pathlib import Path
from statistics import NormalDist

import numpy as np

from core.engine.books import BookRuntime
from core.ficc import ratesim as R
from core.quant import lab
from core.quant import scenarios as S
from core.rules.macro_rules import load_store
from tests.macro_m9_lab import FORBIDDEN, ROOT, _sizing_modules
from tests.notrun import NotRun, require_fixture

KOSPI_FIXTURE = "krx_kospi_official_close_1997-01-03_2026-10-02.csv"       # F01
BRENT_FIXTURE = "DCOILBRENTEU.csv"           # F18 fred_snapshot_2026-10-02/; generate() writes the basename
SEP_TARGET_SD = 0.014 / NormalDist().inv_cdf(0.85)                          # 1.4 pp RMSE band, 70% coverage
SCENARIO_FORBIDDEN = FORBIDDEN + ("core.quant.scenarios",)
TEST_ANCHOR = {"oil_2022_p20": "2022-03-02"}                                # synthetic only: the real t0 is OWNER


def _weekdays(start: str, end: str, drop=()) -> list[str]:
    d, e, out = date.fromisoformat(start), date.fromisoformat(end), []
    while d <= e:
        if d.weekday() < 5 and d.isoformat() not in drop:
            out.append(d.isoformat())
        d += timedelta(days=1)
    return out


def _panel(seed: int = 5, drop=("2026-07-17",)) -> dict:
    """Seeded random-walk closes on weekdays 2021-12 -> 2026-08 (2026-07-17 dropped so the Jul-2026 window holds the
    printed 27 sessions), DFII10 in percent, FEDFUNDS monthly in percent (a Vasicek path)."""
    ds, rng = _weekdays("2021-12-01", "2026-08-31", drop), np.random.default_rng(seed)
    src = {sid: (ds, 100.0 * np.exp(np.cumsum(0.012 * rng.standard_normal(len(ds)))))
           for sid in ("KOSPI_OFFICIAL_CLOSE", "SPX_OFFICIAL_CLOSE", "ECOS_1530_CLOSE", "DCOILBRENTEU", "069500",
                       "US_LINE", "KOSPI200_OFFICIAL_CLOSE")}
    src["DFII10"] = (ds, 1.5 + np.cumsum(0.03 * rng.standard_normal(len(ds))))
    r, ff = 0.045, []
    for _ in range(420):
        r += 0.5 * (0.04 - r) / 12 + 0.01 * math.sqrt(1 / 12) * rng.standard_normal()
        ff.append(100.0 * r)
    src["FEDFUNDS"] = ([f"{1990 + i // 12}-{i % 12 + 1:02d}-01" for i in range(420)], np.array(ff))
    return src


def _runnable(s: S.Scenario) -> S.Scenario:
    a = TEST_ANCHOR.get(s.id)
    return replace(s, anchor_start=a, status="SPECIFIED", owner_input="") if a else s


def _book(s: S.Scenario) -> dict:
    return {"069500": 0.6} if s.market == "KR" else {"US_LINE": 0.4}


def _rel(a, b) -> float:
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    return float(np.max(np.abs(a - b) / np.maximum(np.abs(a), 1e-300))) if a.size else 0.0


def _raises(fn, exc=Exception, needle=""):
    try:
        fn()
    except exc as e:
        assert needle.lower() in str(e).lower(), f"{needle!r} not in {e}"
        return e
    raise AssertionError(f"expected {exc.__name__}")


# --------------------------------------------------------------------------- #
# Library: the five named scenarios, anchors from the spec text, typed nulls, Brent named
# --------------------------------------------------------------------------- #
def test_library_names_brent_anchors_from_the_spec_and_owner_nulls():
    """(a)-(e) are in the library with the spec's windows; every scenario names DCOILBRENTEU or BZ=F (the store's
    data.brent_series); an unnamed Brent or a SPECIFIED scenario without an anchor is refused; the 2022 oil t0 and the
    latest SEP are OWNER_INPUT; an OWNER anchor runs to missing_input naming the owner input."""
    ids = {s.id for s in S.SCENARIOS}
    assert ids == {"oil_2026_p20", "oil_2022_p20", "kospi_leverage_unwind_2026_07", "carry_unwind_2024_08",
                   "carry_unwind_2024_08_us", "tariffs_2025_04", "tariffs_2025_04_us", "sep_rate_band"}
    assert load_store().get("data.brent_series") == S.BRENT_SERIES
    rows = {r["id"]: r for r in S.scenario_library()}
    assert set(rows) == ids and all(r["status"] in S.STATUSES for r in rows.values())
    for s in S.SCENARIOS:
        assert s.brent_series_id in S.BRENT_SERIES.values() and s.series["brent"] == s.brent_series_id, s.id
        assert s.source.startswith("L1747 (4)"), s.id
    w = {s.id: (s.anchor_start, s.anchor_end, s.horizon_sessions) for s in S.SCENARIOS}
    assert w["oil_2026_p20"] == ("2026-02-27", None, 20)
    assert w["kospi_leverage_unwind_2026_07"] == ("2026-06-23", "2026-07-30", 27)
    rp = lab.REPLAY_BY_ID["KR-2026-06-23_07-30"]
    assert (rp.start, rp.end) == w["kospi_leverage_unwind_2026_07"][:2]
    assert w["carry_unwind_2024_08"][:2] == ("2024-07-31", "2024-08-09") and w["tariffs_2025_04"][:2] == ("2025-03-28", "2025-04-09")
    assert w["carry_unwind_2024_08_us"][:2] == ("2024-07-17", "2024-08-05") and w["tariffs_2025_04_us"][:2] == ("2025-02-20", "2025-04-08")
    oil22, sep = S.SCENARIO_BY_ID["oil_2022_p20"], S.SCENARIO_BY_ID["sep_rate_band"]
    assert oil22.anchor_start is None and oil22.status == "OWNER_INPUT" and "2022" in oil22.owner_input
    assert sep.kind == "rate_band" and sep.status == "OWNER_INPUT" and sep.anchor_start == S.SEP_VINTAGE == "2023-12-13"
    assert sep.shocks == {"rmse_pp": 1.4, "horizon_years": 1.0, "coverage": 0.70} and "latest SEP Table 2" in sep.owner_input
    assert S.SCENARIO_BY_ID["oil_2026_p20"].shocks == {"kospi": -0.155, "usdkrw": 0.052, "us10y_real": 0.0032}
    res = S.run_scenario(oil22, {"069500": 1.0}, _panel())
    assert res.status == "missing_input" and res.missing == ("OWNER: " + oil22.owner_input,) and res.acts is False
    base = S.SCENARIO_BY_ID["carry_unwind_2024_08"]
    _raises(lambda: replace(base, brent_series_id="Brent"), ValueError, "DNB item 19")
    _raises(lambda: replace(base, factors={**base.factors, "brent": "DCOILWTICO"}), ValueError, "unnamed")
    _raises(lambda: replace(base, anchor_start=None), ValueError, "owner input")
    _raises(lambda: replace(base, letf_leverage={"X": ("KOSPI200_OFFICIAL_CLOSE", 2.0, -0.01)}), ValueError, "carry >= 0")


test_library_names_brent_anchors_from_the_spec_and_owner_nulls.test_ids = ["I-11"]


def test_shock_window_on_the_current_book_synthetic_companion():
    """(b) on a 28-close path built to fall exactly 38.6% in 27 sessions: the window holds the printed 27 sessions,
    the KOSPI move is -38.6%, a `BookRuntime` and the same weights as a dict give the same static-weight book path;
    a feed with an extra session, a missing Brent series or a missing book instrument is missing_input (named)."""
    src = _panel()
    ds = src["KOSPI_OFFICIAL_CLOSE"][0]
    i0, i1 = ds.index("2026-06-22"), ds.index("2026-07-30")
    k = np.full(len(ds), 9114.55)
    k[i0:i1 + 1] = 9114.55 * (1 - 0.386) ** (np.arange(i1 - i0 + 1) / (i1 - i0))
    k[i1 + 1:] = k[i1]
    src["KOSPI_OFFICIAL_CLOSE"] = (ds, k)
    s = S.SCENARIO_BY_ID["kospi_leverage_unwind_2026_07"]
    rt = BookRuntime("recommended:KR", held={"069500": 0.6})
    a = S.run_scenario(s, rt, src)
    b = S.run_scenario(s, {"069500": 0.6}, src)
    assert a.status == "ok" and len(a.dates) == 27 and a.dates[0] == "2026-06-23" and a.dates[-1] == "2026-07-30"
    assert abs(a.factor_moves["kospi"] + 0.386) < 1e-12 and set(a.factor_moves) == {"kospi", "usdkrw", "us10y_real", "brent"}
    d, c = src["069500"]
    r = np.array([c[d.index(x)] / c[d.index(x) - 1] - 1 for x in a.dates])
    assert abs(a.book_return - (np.prod(1 + 0.6 * r) - 1)) < 1e-12 and a.book_return == b.book_return
    assert _rel(a.paths["book"], b.paths["book"]) == 0.0 and a.max_dd <= 0 and a.acts is False
    assert rt.held == {"069500": 0.6} and a.series["brent"] == "DCOILBRENTEU"
    full = dict(src, KOSPI_OFFICIAL_CLOSE=(_weekdays("2021-12-01", "2026-08-31"), np.linspace(100, 90, len(_weekdays("2021-12-01", "2026-08-31")))))
    bad = S.run_scenario(s, rt, full)
    assert bad.status == "missing_input" and "28 sessions" in bad.missing[0] and "prints 27" in bad.missing[0]
    nob = S.run_scenario(s, rt, {k_: v for k_, v in src.items() if k_ != "DCOILBRENTEU"})
    assert nob.status == "missing_input" and nob.missing == ("REFDATA: DCOILBRENTEU",)
    noi = S.run_scenario(s, {"069500": 0.5, "252670": 0.1}, src)
    assert noi.status == "missing_input" and noi.missing == ("REFDATA: 252670",)


test_shock_window_on_the_current_book_synthetic_companion.test_ids = ["I-11"]


def test_letf_identity_on_a_synthetic_path():
    """A leveraged / inverse ETF in `letf_leverage` is modelled from its underlying through lab.letf_path_return:
    ln(1 + R_L) = L ln(1 + R) - 1/2 (L^2 - L) sum r^2 - carry holds on the window to 1e-12 for L = 2 and -2 with a
    carry; a mixed book compounds the static weights of the daily path; the LETF's own closes are never read."""
    src = _panel()
    base = S.SCENARIO_BY_ID["tariffs_2025_04"]
    for L, carry in ((2.0, 0.003), (-2.0, 0.0)):
        s = replace(base, letf_leverage={"LETF": ("KOSPI200_OFFICIAL_CLOSE", L, carry)})
        res = S.run_scenario(s, {"LETF": 1.0}, src)
        assert res.status == "ok" and "LETF" not in src and "R-26 rule 2" in res.note
        d, c = src["KOSPI200_OFFICIAL_CLOSE"]
        r = np.array([c[d.index(x)] / c[d.index(x) - 1] - 1 for x in res.dates])
        R_, sr2 = float(np.prod(1 + r) - 1), float(np.sum(r * r))
        want = lab.letf_path_return(R_, sr2, L, carry)
        assert abs(res.book_return - want) < 1e-12 and abs(res.paths["LETF"][-1] - 1 - want) < 1e-12, (L, res.book_return, want)
        assert abs(math.log1p(res.book_return) - (L * math.log1p(R_) - 0.5 * (L * L - L) * sr2 - carry)) < 1e-12
    s = replace(base, letf_leverage={"LETF": ("KOSPI200_OFFICIAL_CLOSE", 2.0, 0.003)})
    mix = S.run_scenario(s, {"069500": 0.5, "LETF": 0.5}, src)
    rl = mix.paths["LETF"] / np.r_[1.0, mix.paths["LETF"][:-1]] - 1
    re = mix.paths["069500"] / np.r_[1.0, mix.paths["069500"][:-1]] - 1
    assert abs(mix.book_return - (np.prod(1 + 0.5 * re + 0.5 * rl) - 1)) < 1e-12
    gone = S.run_scenario(s, {"LETF": 1.0}, {k: v for k, v in src.items() if k != "KOSPI200_OFFICIAL_CLOSE"})
    assert gone.status == "missing_input" and gone.missing == ("REFDATA: KOSPI200_OFFICIAL_CLOSE",)
    assert abs(lab.letf_path_return(-0.4081, 0.08121, 2) + 0.677) < 0.001          # local cache check (brief B.4)


test_letf_identity_on_a_synthetic_path.test_ids = ["I-11"]


def test_sep_band_dispersion_matches_the_band_at_the_horizon():
    """sep_band_params keeps kappa / theta / r0 and solves sigma so the terminal sd at 1 year is 1.4 pp / Phi^-1(0.85);
    the seeded paths reproduce it within Monte Carlo tolerance for Vasicek, Hull-White and CIR (70% inside +-1.4 pp,
    90% half-width about 2.2 pp); the rate band through run_scenario returns rate paths only, labelled stale with its
    Dec-2023 vintage, and never values the book."""
    assert abs(1.6449 * SEP_TARGET_SD - 0.0222) < 1e-4                     # the spec's "about +-2.2 pp"
    base = R.ShortRateParams("vasicek", 0.5, 0.04, 0.01, 0.045, note="base")
    for model, tol in (("vasicek", 0.03), ("hull_white", 0.03), ("cir", 0.05)):
        p = R.sep_band_params(1.4, 1.0, replace(base, model=model), vintage="2023-12-13")
        assert (p.kappa, p.theta, p.r0, p.model) == (0.5, 0.04, 0.045, model) and "vintage 2023-12-13" in p.note
        sim = R.sep_band_paths(model, p, 11, 10000, 1.0)
        t = sim.terminal
        sd = float(np.std(t))
        assert abs(sd / SEP_TARGET_SD - 1) < tol, (model, sd)
        assert abs(float(np.mean(np.abs(t - np.mean(t)) <= 0.014)) - 0.70) < 0.02, model
        assert abs((sim.p95 - sim.p05) / 2 / (1.6449 * SEP_TARGET_SD) - 1) < tol + 0.01, model
    _raises(lambda: R.sep_band_params(0.0, 1.0, base), ValueError, "band_pp > 0")
    _raises(lambda: R.sep_band_paths("cir", base, 11), ValueError, "not 'cir'")
    assert R.MODELS == ("vasicek", "cir", "hull_white")
    sep = S.SCENARIO_BY_ID["sep_rate_band"]
    res = S.run_scenario(sep, {"069500": 1.0}, _panel(), 11, n_paths=10000)
    assert res.status == "ok" and isinstance(res.rates, R.RateSimResult) and res.book_return is None and "book" not in res.paths
    assert res.band["label"] == "stale" and res.band["vintage"] == "2023-12-13" and res.band["rmse_pp"] == 1.4
    assert abs(res.band["terminal_sd"] / SEP_TARGET_SD - 1) < 0.03 and res.series["brent"] == "DCOILBRENTEU"
    latest = replace(sep, status="SPECIFIED", owner_input="", anchor_start="2026-09-17")
    assert S.run_scenario(latest, None, _panel(), n_paths=500).band["label"] == "latest"
    assert S.run_scenario(sep, None, {}).missing == ("REFDATA: FEDFUNDS",)


test_sep_band_dispersion_matches_the_band_at_the_horizon.test_ids = ["I-11"]


# --------------------------------------------------------------------------- #
# T-REPRO-01c
# --------------------------------------------------------------------------- #
def test_t_repro_01c_scenarios_identical_paths_under_the_seed():
    """The same seed, rules-store hash, data snapshot and package version give identical scenario paths (relative
    difference <= 1e-12) for every library scenario; a different seed changes the SEP-band paths; the repro record
    carries seed, config_hash, data_snapshot_id and package_version, and the snapshot id moves with the data; no clock
    and no unseeded generator in scenarios.py (the rate paths draw through ratesim's default_rng(seed))."""
    store = load_store()
    ctx = lab.LabContext(config_hash=store.config_hash, package_version="2.0.0", knowledge_utc="2026-10-02T07:00:00Z")
    src = _panel()
    for s in map(_runnable, S.SCENARIOS):
        a = S.run_scenario(s, _book(s), src, 11, ctx=ctx, n_paths=2000)
        b = S.run_scenario(s, _book(s), _panel(), 11, ctx=ctx, n_paths=2000)
        assert a.status == b.status == "ok", (s.id, a.missing)
        assert set(a.paths) == set(b.paths) and a.paths and all(_rel(a.paths[k], b.paths[k]) <= 1e-12 for k in a.paths), s.id
        assert a.factor_moves == b.factor_moves and a.repro == b.repro and a.book_return == b.book_return, s.id
        assert {"seed", "config_hash", "data_snapshot_id", "package_version"} <= set(a.repro), s.id
        assert a.repro["seed"] == a.seed == 11 and a.repro["config_hash"] == store.config_hash, s.id
        moved = dict(src, DCOILBRENTEU=(src["DCOILBRENTEU"][0], src["DCOILBRENTEU"][1] * 1.0001),
                     FEDFUNDS=(src["FEDFUNDS"][0], src["FEDFUNDS"][1] * 1.0001))
        assert S.run_scenario(s, _book(s), moved, 11, ctx=ctx, n_paths=2000).repro["data_snapshot_id"] != a.repro["data_snapshot_id"], s.id
    sep = S.SCENARIO_BY_ID["sep_rate_band"]
    a, b = (S.run_scenario(sep, None, src, 11, ctx=ctx, n_paths=2000) for _ in range(2))
    c = S.run_scenario(sep, None, src, 12, ctx=ctx, n_paths=2000)
    assert _rel(a.rates.terminal, b.rates.terminal) <= 1e-12 and all(_rel(a.rates.fan[p], b.rates.fan[p]) <= 1e-12 for p in a.rates.fan)
    assert _rel(a.rates.terminal, c.rates.terminal) > 1e-6 and c.repro["seed"] == 12
    for path in (ROOT / "core/quant/scenarios.py", ROOT / "core/ficc/ratesim.py"):
        src_text = path.read_text(encoding="utf-8")
        calls = {ast.unparse(n.func) for n in ast.walk(ast.parse(src_text)) if isinstance(n, ast.Call)}
        assert not {"datetime.now", "datetime.utcnow", "time.time", "date.today"} & calls, path.name
    scen = (ROOT / "core/quant/scenarios.py").read_text(encoding="utf-8")
    assert "default_rng" not in scen and "np.random" not in scen


test_t_repro_01c_scenarios_identical_paths_under_the_seed.test_ids = ["T-REPRO-01c", "I-11"]


# --------------------------------------------------------------------------- #
# I-11 rule (6) extended to the scenario library
# --------------------------------------------------------------------------- #
def _imports(path: Path, forbidden=SCENARIO_FORBIDDEN) -> list[str]:
    hits = []
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"), filename=str(path))):
        if isinstance(node, ast.Import):
            hits += [a.name for a in node.names if a.name.startswith(forbidden)]
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if mod.startswith(forbidden):
                hits.append(mod)
            elif mod in ("core.quant", "core.ficc"):
                hits += [f"{mod}.{a.name}" for a in node.names if f"{mod}.{a.name}" in forbidden]
    return hits


def test_i11_no_sizing_module_reads_scenarios_or_lab():
    """Static AST scan: risk_layer, sleeves, books, pipeline, macro_daily (and the rest of the sizing list of the lab
    guard: risk, signals, optimiser, estimators, engine, rules, artifact builders) never import core.quant.scenarios,
    core.quant.lab, montecarlo or ratesim; a planted import trips the scan; ScenarioResult carries acts = False;
    scenarios.py imports no engine, skills, rules-store writer or provider module."""
    mods = _sizing_modules()
    names = {p.relative_to(ROOT).as_posix() for p in mods}
    assert {"core/quant/risk_layer.py", "core/quant/sleeves.py", "core/engine/books.py", "core/skills/pipeline.py",
            "core/skills/macro_daily.py"} <= names
    bad = {p.relative_to(ROOT).as_posix(): _imports(p) for p in mods if _imports(p)}
    assert not bad, f"sizing modules importing scenario / lab outputs: {bad}"
    with tempfile.TemporaryDirectory() as tmp:
        planted = Path(tmp) / "sleeves_copy.py"
        planted.write_text((ROOT / "core/quant/sleeves.py").read_text(encoding="utf-8")
                           + "\nfrom core.quant.scenarios import run_scenario\n", encoding="utf-8")
        assert _imports(planted) == ["core.quant.scenarios"]
        planted.write_text("from core.quant import scenarios, lab\n", encoding="utf-8")
        assert _imports(planted) == ["core.quant.scenarios", "core.quant.lab"]
    f = {x.name: x for x in fields(S.ScenarioResult)}["acts"]
    assert f.default is False
    tree = ast.parse((ROOT / "core/quant/scenarios.py").read_text(encoding="utf-8"))
    mods_in = {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)} | {
        a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    banned = ("core.engine", "core.skills", "core.rules", "data", "config")
    assert not {m for m in mods_in if m and any(m == b or m.startswith(b + ".") for b in banned)}, mods_in


test_i11_no_sizing_module_reads_scenarios_or_lab.test_ids = ["I-11"]


# --------------------------------------------------------------------------- #
# Reference data and owner inputs (NOT_RUN, named)
# --------------------------------------------------------------------------- #
def test_scenario_kospi_jul_2026_path_refdata():
    """(b) on the official KOSPI closes 2026-06-22 -> 2026-07-30 (-38.6% in 27 sessions, Level-1 +-1 pp)."""
    require_fixture(KOSPI_FIXTURE)
    raise NotRun("REFDATA: " + KOSPI_FIXTURE + " listed but the scenario run also needs the KOSPI200 / ECOS / DFII10 "
                 "/ DCOILBRENTEU histories and a persisted book state")


test_scenario_kospi_jul_2026_path_refdata.test_ids = ["I-11"]


def test_scenario_brent_history_refdata():
    """Every shock window's Brent factor move on DCOILBRENTEU (EIA Dated spot; F18 FRED snapshot)."""
    require_fixture(BRENT_FIXTURE)
    raise NotRun("REFDATA: " + BRENT_FIXTURE + " listed but the printed (a) moves need the KOSPI, ECOS and DFII10 files too")


test_scenario_brent_history_refdata.test_ids = ["I-11"]


def test_scenario_latest_sep_table_owner():
    """(e) reads the latest SEP Table-2 band; only the Dec-2023 +-1.4 pp band is printed (run labelled stale)."""
    raise NotRun("OWNER: latest SEP Table 2 (short-rate RMSE band and release date) and a FEDFUNDS history; "
                 "the stored band is the Dec-2023 +-1.4 pp at 1 year, labelled stale")


test_scenario_latest_sep_table_owner.test_ids = ["I-11"]


def test_scenario_oil_2022_anchor_owner():
    """(a) 2022 replay: KOSPI +0.4%, USD/KRW +2.1%, 10y real -4 bp at +20 days from a t0 the spec never prints."""
    raise NotRun("OWNER: t0 of the 2022 oil-shock replay (oil_2022_p20; brief F-16), then the KOSPI / ECOS / DFII10 / "
                 "DCOILBRENTEU histories (REFDATA)")


test_scenario_oil_2022_anchor_owner.test_ids = ["I-11"]


def tests():
    return [(name, fn) for name, fn in sorted(globals().items()) if name.startswith("test_") and callable(fn)]


if __name__ == "__main__":
    from tests.macro_acceptance import run_module
    raise SystemExit(run_module(globals()))
