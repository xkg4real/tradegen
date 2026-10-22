"""M1 package D — fixture tooling, golden registry, acquisition register, owner scripts (TASK-M1-01, TASK-M1-21,
TASK-M1-22; G-POST-01 data rows; G-DSR-01 / T-DSR-01; the T-PBO-01 noise control; T-RO-02 record clause).

Hermetic: no network (the macro guard is armed around every test), tempfile only, module globals restored in
`finally`. A clause that needs absent reference data raises NotRun("REFDATA: <file>") naming each missing file; one
that needs the owner raises NotRun("OWNER: ...").
"""
from __future__ import annotations

import ast
import contextlib
import csv
import fnmatch
import io
import json
import math
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import scipy.stats as sps

from core.quant import validate as V
from docs import kis_quote_check as KQ
from docs import macro_fixtures as MF
from tests import golden_tools as G
from tests.acceptance import _code_only
from tests.notrun import FIXTURES, MANIFEST, NotRun, load_manifest, require_fixture

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "tests" / "macro_registry.csv"
ACQUISITION = FIXTURES / "ACQUISITION.csv"
ACQ_COLUMNS = ("series", "source", "depth", "needed_by", "licence", "owner", "md5", "fixture")
SPEC_ACQ_ROWS = ("KRX official KOSPI daily closes, Saturday sessions included", "KODEX 200 PDF history",
                 "French daily Mkt-RF and RF", "The ECOS code of BOK_CALL_RATE", "USD_LIVE_PROXY (named, default DX-Y.NYB)",
                 "The 16:00 ET VIX / VIX3M snapshot source", "The hyperscaler list",
                 "JPX, SSE, HKEX, TWSE, CME and Cboe calendars")                                    # L6026-6033 verbatim
FILE_OF = {fid: Path(rel).name for fid, rel, *_ in MF.REFERENCE_FILES}                           # F13 -> yahoo_KS11_...


def _registry_ids(prefix: str) -> list[str]:
    with REGISTRY.open(encoding="utf-8", newline="") as fh:
        return [r["test_id"] for r in csv.DictReader(fh) if r["test_id"].startswith(prefix)]


def _refdata(fids) -> None:
    """NotRun("REFDATA: ...") naming every absent fixture among `fids`; returns when all are present."""
    missing = []
    for fid in fids:
        name = FILE_OF.get(fid, fid)
        try:
            require_fixture(name)
        except NotRun as exc:
            missing.append(f"{fid} {name} ({exc.reason.split(': ', 1)[1]})")
    if missing:
        raise NotRun("REFDATA: " + "; ".join(missing))


# --------------------------------------------------------------------------- #
# Tolerance table and helpers (L5734-5738)
# --------------------------------------------------------------------------- #
def test_tolerance_table_self_test():
    """LEVEL1 / LEVEL2 verbatim; p-kind by value; Level 2 refuses kinds it has no tolerance for."""
    assert G.LEVEL1 == {"sharpe": 0.01, "mdd": 0.01, "window_return": 0.01, "weight": 0.02, "share": 0.03,
                        "exceedance": 0.003, "p_hi": 0.01,
                        "p_lo": 0.005, "z": 0.05, "es_pp": 0.002, "count_exact": 0, "count_boot": 1, "percentile": 5,
                        "qlike_ratio": 0.005, "se": 0.005, "vol_level": 0.001, "ratio": 0.01, "price": 0}
    assert G.LEVEL2 == {"sharpe": 0.03, "window_return": 0.02, "mdd": 0.02, "p": 0.02}
    assert G.tol("sharpe") == 0.01 and G.tol("sharpe", 2) == 0.03 and G.tol("p_lo", 2) == 0.02 and G.tol("price") == 0
    assert G.p_kind(0.05) == "p_hi" and G.p_kind(0.049) == "p_lo"
    assert G.within("sharpe", 0.641, 0.6505) and not G.within("sharpe", 0.641, 0.652)
    assert G.within("count_exact", 132, 132) and not G.within("count_exact", 133, 132) and G.within("count_boot", 72, 71)
    assert G.within("price", 7003.74, 7003.74) and not G.within("price", 7003.75, 7003.74)
    assert not G.within("sharpe", float("nan"), 0.6)
    for kind in ("weight", "share", "count_exact", "z", "es_pp"):
        try:
            G.tol(kind, 2)
            raise AssertionError(f"Level 2 must not assert {kind}")
        except ValueError:
            pass
    for bad in (("nope", 1), ("sharpe", 3)):
        try:
            G.tol(*bad)
            raise AssertionError(bad)
        except (KeyError, ValueError):
            pass
    G.assert_close(0.6723, 0.6723 + 0.0099, "sharpe", label="G-DSR-02/sr")
    try:
        G.assert_close(0.60, 0.6723, "sharpe", label="G-DSR-02/sr")
        raise AssertionError("assert_close must raise")
    except AssertionError as exc:
        assert "G-DSR-02/sr" in str(exc) and "0.6723" in str(exc)


def test_golden_helpers_class_and_floor():
    """Near a threshold a verdict is a class (G-KR-L10: p_ni 0.103 vs 0.10), away from it the point holds; p = 0 is '<1/B'."""
    assert G.near_threshold(0.103, 0.10, "p_hi") and not G.near_threshold(0.146, 0.10, "p_hi")
    G.assert_class(0.103, 0.10, "p_hi", "PASS", {"PASS", "INSUFFICIENT_DATA"}, point="PASS")
    G.assert_class(0.103, 0.10, "p_hi", "INSUFFICIENT_DATA", {"PASS", "INSUFFICIENT_DATA"}, point="PASS")
    G.assert_class(0.146, 0.10, "p_hi", "REJECT", {"REJECT", "INSUFFICIENT_DATA"}, point="REJECT")
    # the fallback raise sits in `else:`, outside the try, so a helper that accepts everything fails here
    for stat, verdict, needle in ((0.103, "REJECT", "not in"), (0.146, "INSUFFICIENT_DATA", "although")):
        try:
            G.assert_class(stat, 0.10, "p_hi", verdict, {"PASS", "INSUFFICIENT_DATA"}, point="PASS")
        except AssertionError as exc:
            assert verdict in str(exc) and needle in str(exc), str(exc)
        else:
            raise AssertionError(f"assert_class accepted {verdict} at stat {stat}")
    G.assert_p_floor(0.0, 2000)
    G.assert_p_floor(0.0004, 2000)
    try:
        G.assert_p_floor(0.0005, 2000)
    except AssertionError as exc:
        assert "1/B" in str(exc), str(exc)
    else:
        raise AssertionError("assert_p_floor accepted p = 1/B")


# --------------------------------------------------------------------------- #
# goldens.csv and ACQUISITION.csv integrity
# --------------------------------------------------------------------------- #
def test_goldens_csv_integrity():
    """Every registry G-* id has rows; enums valid; pending rows carry no value and a section 9.4 note; loader semantics."""
    table = G.load_goldens()
    missing = [g for g in _registry_ids("G-") if g not in table]
    assert not missing, f"registry golden ids without goldens.csv rows: {missing}"
    rows = [r for g in table.values() for r in g.rows]
    assert len(rows) > 1000 and len(table) >= 78
    pending = [r for r in rows if r.status == "pending"]
    assert {r.golden_id for r in pending} >= {f"P94-{n:02d}" for n in range(1, 18)}, "the 17 section 9.4 items (L5996-6014)"
    for r in pending:
        assert r.value is None and r.note.startswith("§9.4 item "), r
    pre = [r for r in rows if r.status == "pre_patch_pending"]
    assert {r.golden_id for r in pre} == {"G-KR-06", "G-KR-02b"} and all("§9.4 item 2" in r.note for r in pre), pre
    assert all(r.status == "reference" for r in table["G-MOM-07"].rows + table["G-LAD-01"].rows)
    for r in rows:
        if r.kind in ("verdict", "text"):
            assert r.value is None or isinstance(r.value, str), r
        elif isinstance(r.value, str):
            assert r.kind == "p_lo" and r.value.startswith("<"), r          # a p floor ("<1/B", "<0.001"), T-PZERO-01
        elif r.value is not None and not isinstance(r.value, float):
            raise AssertionError(r)
        if r.kind == "p_lo" and isinstance(r.value, float):
            assert r.value < 0.05, r
        if r.kind == "p_hi" and isinstance(r.value, float):
            assert 0.05 <= r.value <= 1.0, r
        if r.kind == "verdict" and r.value not in ("PASS", "FAIL", "outside"):
            assert set(r.value.split("|")) <= {"PASS", "REVISE", "REJECT", "INSUFFICIENT_DATA"}, r   # schema enum, L4007
        # +/- 0.03 is for bootstrap shares only (L5734): an exceedance rate or band is `exceedance` (+/- 0.3 pp, L5642),
        # a deterministic fraction (staleness, days on, years positive, plateau, max share) is a `ratio` (+/- 0.01)
        q = r.quantity.lower()
        if any(s in q for s in ("exceedance", "band lower", "band upper")):
            assert r.kind == "exceedance", r
        elif r.kind == "share":
            assert r.golden_id not in ("G-STALE-01", "G-YRS-01", "G-R08-01") and not any(
                s in q for s in ("days", "years positive", "plateau", "max share", "implied share", "vol-of-vol")), r
    g = G.golden("G-POST-01")
    assert g.want("kospi_close_2oct") == 7003.74 and g.row("rv20_2oct").runs_from == "M2" and "F13" in g.fixtures
    for gid, sub in (("G-KR-06", "sharpe"), ("G-KR-02b", "x2_70bp_dsr_2016_26"), ("G-LAD-04", "halts_with_stop"), ("P94-11", "value")):
        try:
            G.golden(gid).want(sub)
            raise AssertionError(f"{gid}/{sub} must raise NotRun")
        except NotRun as exc:
            assert exc.reason.startswith("PENDING: §9.4 item "), exc.reason
    assert G.golden("G-MOM-08").want("p_pw251") == G.P_FLOOR
    report = G.assert_golden("G-DSR-02", {"sr": 0.6723, "dsr_vs_unscaled": 0.2729, "T": 9233})
    assert len(report) == 3 and report[0][4] == 0.0
    try:
        G.assert_golden("G-DSR-02", {"sr": 0.70, "T": 9233})
        raise AssertionError("deviation must raise")
    except AssertionError as exc:
        assert "sr: got 0.7" in str(exc) and "T:" not in str(exc)
    assert G.assert_golden("G-MOM-08", {"p_pw251": (0.0, 2000), "years_positive": 0.71})
    try:
        G.golden("G-NOPE-99")
        raise AssertionError
    except KeyError:
        pass


def test_acquisition_csv_integrity():
    """The 8 section 9.5 rows verbatim plus every absent D.1 fixture; licence / owner / md5 blank; none is in the manifest."""
    with ACQUISITION.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        assert tuple(reader.fieldnames or ()) == ACQ_COLUMNS, reader.fieldnames
        rows = list(reader)
    series = [r["series"] for r in rows]
    assert series[:8] == list(SPEC_ACQ_ROWS), series[:8]
    fids = {tok for r in rows for tok in r["fixture"].split() if tok.startswith(("F", "U")) and tok[1:3].isdigit()}
    expected = {"F01", "F02", "F03", "F04-F06", "F07", "F08", "F09", "F10", "F11", "F12", "F13", "F14", "F15", "F16", "F17",
                "F18", "F19", "F20", "F21", "F22", "F23", "F24", "F25", "F27", "F28", "F29", "U1"}
    assert expected <= fids, sorted(expected - fids)
    listed = load_manifest()
    for r in rows:
        assert r["series"] and r["source"] and r["needed_by"], r
        assert not (r["licence"] or r["owner"] or r["md5"]), f"an open row with licence/owner/md5: {r}"
        for name in r["fixture"].split(" ", 1)[-1].split(";"):
            assert Path(name).name not in listed, f"{name} is both open in ACQUISITION.csv and listed in MANIFEST.csv"
    # every absent reference file the generator expects is an open row (by F-id)
    for fid in {f for f, *_ in MF.REFERENCE_FILES}:
        assert any(fid in tok or (fid in ("F04", "F05", "F06") and "F04-F06" in tok) for tok in fids), f"{fid} not registered"


def _fixture_gates():
    """(module path, test function, require_fixture call, module-level literal constants) for every test module."""
    for path in sorted((ROOT / "tests").glob("macro_*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        consts = {}
        for node in tree.body:
            if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                with contextlib.suppress(ValueError, SyntaxError):
                    consts[node.targets[0].id] = ast.literal_eval(node.value)
        for fn in tree.body:
            if isinstance(fn, ast.FunctionDef):
                for call in ast.walk(fn):
                    if isinstance(call, ast.Call) and getattr(call.func, "id", "") == "require_fixture" and call.args:
                        yield path, fn, call, consts


def test_every_required_fixture_is_generated_or_registered():
    """A `require_fixture` name is a D.1 generator output, an ACQUISITION.csv fixture or a manifest row; any other
    spelling stays NOT_RUN forever after `generate` + `freeze`, whatever data arrives."""
    with ACQUISITION.open(encoding="utf-8", newline="") as fh:
        acq = {Path(n).name for r in csv.DictReader(fh) for n in r["fixture"].split(" ", 1)[-1].split(";") if n}
    known = {Path(rel).name for _, rel, *_ in MF.REFERENCE_FILES} | set(load_manifest())
    bad, checked = [], 0
    for path, fn, call, consts in _fixture_gates():
        if any(k.arg == "manifest" for k in call.keywords):
            continue                                                  # the loader's own tests on a temp manifest
        loops = {n.target.id: n.iter for n in ast.walk(fn) if isinstance(n, ast.For) and isinstance(n.target, ast.Name)}
        arg = call.args[0]
        expr = loops.get(arg.id, arg) if isinstance(arg, ast.Name) else arg
        try:
            val = eval(compile(ast.Expression(expr), path.name, "eval"), {"__builtins__": {}}, dict(consts))
        except Exception:
            continue                                                  # a runtime name (FILE_OF lookup, manifest loop)
        for name in [val] if isinstance(val, str) else val:
            checked += 1
            if Path(name).name not in known and not any(fnmatch.fnmatch(Path(name).name, a) for a in acq):
                bad.append(f"{path.name}:{call.lineno} {name}")
    assert checked >= 30 and not bad, f"names no generator, ACQUISITION or manifest row produces ({checked} checked): {bad}"


test_every_required_fixture_is_generated_or_registered.test_ids = ["T-HERM-01"]


def test_no_golden_test_passes_on_its_fixture_gate_alone():
    """A test whose last statement is its `require_fixture` gate PASSES with nothing asserted once the file is listed.
    After the gate a test asserts, raises NotRun naming the input still missing, or fails as not implemented."""
    def gate_only(stmt):
        if isinstance(stmt, ast.For):
            return all(gate_only(s) for s in stmt.body)
        call = stmt.value if isinstance(stmt, ast.Expr) else None
        return isinstance(call, ast.Call) and getattr(call.func, "id", "") == "require_fixture"
    bare = sorted({f"{path.name}::{fn.name}" for path, fn, _call, _c in _fixture_gates()
                   if path.stem != "macro_m0_harness" and gate_only(fn.body[-1])})   # m0_harness tests the gate itself
    assert not bare, f"tests that pass on the fixture gate alone: {bare}"


test_no_golden_test_passes_on_its_fixture_gate_alone.test_ids = ["T-HERM-01"]


# --------------------------------------------------------------------------- #
# The first two real golden checks (SYNTH; reproduce on core/quant/validate.py)
# --------------------------------------------------------------------------- #
def test_g_dsr_01_reproduces_bldp():
    """BLdP worked example with the L2522 mapping: 0.9505 at N 46, 0.9004 at N 100 (paper inputs frozen in F30)."""
    fx = json.loads(require_fixture("bldp_dsr_example.json").read_text(encoding="utf-8"))
    m = fx["mapping"]
    sr = m["sr_annual"] / math.sqrt(m["periods_per_year"])
    se_obs = math.sqrt((1 - m["skew"] * sr + (m["kurtosis"] - 1) / 4 * sr ** 2) / (m["T"] - 1))
    assert abs(se_obs - math.sqrt((1 + 3 * sr + 9 / 4 * sr ** 2) / (m["T"] - 1))) < 1e-15     # the L2522 form
    sd_null = math.sqrt(m["sr_trials_variance_annual"] / m["periods_per_year"])
    got = {}
    for n, want in fx["expected"].items():
        hurdle = V.expected_max_sharpe(int(n), sd_null)                   # sd * e(N), validate.py L168
        got[n] = float(sps.norm.cdf((sr - hurdle) / se_obs))
        assert abs(got[n] - want) <= 5e-5, (n, got[n], want)              # printed precision, tighter than kind p_hi
    g = G.golden("G-DSR-01")
    assert round(got["46"], 4) == g.want("dsr_n46") and round(got["100"], 4) == g.want("dsr_n100")
    G.assert_golden("G-DSR-01", {"dsr_n46": got["46"], "dsr_n100": got["100"]})


test_g_dsr_01_reproduces_bldp.test_ids = ["G-DSR-01", "T-DSR-01"]


def test_t_pbo_01_noise_control_reproduces():
    """QF3's recipe exactly (L2632): first draw of default_rng(11), normal(0, 0.01, (2600, 10)), 2,592 rows, 16 blocks,
    Sharpe ddof 1 -> PBO 0.536 +/- 0.001. The 200-panel calibration and the KOSPI grid PBO 0.28 are freeze tier (M7)."""
    panel = np.random.default_rng(11).normal(0.0, 0.01, size=(2600, 10))[:2592]
    pbo = V.pbo_cscv(panel, S=16)
    assert pbo["n_splits"] == 12870 and abs(pbo["pbo"] - 0.536) <= 0.001, pbo
    assert abs(pbo["pbo"] - 0.5359) <= 1e-4, pbo["pbo"]


test_t_pbo_01_noise_control_reproduces.test_ids = ["T-PBO-01"]


# --------------------------------------------------------------------------- #
# G-POST-01 data rows (REFDATA) and the arithmetic identities (SYNTH)
# --------------------------------------------------------------------------- #
def test_g_post_01_m1_data_rows_refdata():
    """The M1 rows (close, return, 200-day ratio, Samsung / SK hynix closes, KRW=X) need F01/F13/F16/F20/F27: NotRun
    naming each absent file; once present, the rows are asserted at Level 1 from goldens.csv."""
    g = G.golden("G-POST-01")
    m1 = [r for r in g.rows if r.runs_from == "M1"]
    assert {r.sub_id for r in m1} >= {"kospi_close_2oct", "kospi_return_2oct", "close_over_200d", "samsung_close_2oct",
                                      "hynix_close_2oct", "krwx_last_row", "krwx_dlog20"}
    fids = sorted({f for r in m1 for f in r.fixtures})
    assert fids == ["F01", "F13", "F16", "F20", "F27"], fids
    _refdata(fids)
    raise NotRun("REFDATA: fixtures present but the G-POST-01 row replay is wired by the M1 PIT package (pit_value on F13/F16/F27)")


test_g_post_01_m1_data_rows_refdata.test_ids = ["G-POST-01"]


def test_g_post_01_arithmetic_identities():
    """Identities between printed numbers (brief D.3 ARITH): drawdown -23.16% from 7,003.74 / 9,114.55; vt = min(1, 0.20/0.2882) = 0.694."""
    g = G.golden("G-POST-01")
    close = g.want("kospi_close_2oct")
    assert close == 7003.74
    G.assert_close(close / 9114.55 - 1.0, g.want("drawdown_from_peak"), "mdd", label="G-POST-01/drawdown_from_peak")
    assert abs(close / 9114.55 - 1.0 - (-0.2316)) < 5e-5
    rv20 = g.want("rv20_2oct")
    G.assert_close(min(1.0, 0.20 / rv20), g.want("vt_2oct"), "weight", label="G-POST-01/vt_2oct")
    assert abs(min(1.0, 0.20 / 0.2882) - 0.694) < 5e-4
    k4 = G.golden("G-KR-04")
    G.assert_close(min(1.0, 0.20 / k4.want("rv20_2oct2026")), k4.want("w_decided_2oct2026"), "weight")
    assert abs(g.want("samsung_share") + g.want("hynix_share") - g.want("pair_implied_share")) < 1e-9


test_g_post_01_arithmetic_identities.test_ids = ["G-POST-01"]


def test_synth_b5_bands_and_concentration_bounds():
    """B5 exceedance bands 0.05 +/- 2*sqrt(0.05*0.95/n) (L5642; brief B.4) and the section 11 concentration bounds."""
    def band(n):
        h = 2.0 * math.sqrt(0.05 * 0.95 / n)
        return 0.05 - h, 0.05 + h
    for gid, sub, n in (("G-B5-01", "sample", 2594), ("G-B5-01", "subsample", 371), ("G-B5-01", "garch_fhs", 2123),
                        ("G-B5-02", "sample", 2663), ("G-B5-03", "sample", 8961)):
        g = G.golden(gid)
        assert g.want(f"{sub}_origins") == n
        lo, hi = band(n)
        assert abs(lo - g.want(f"{sub}_band_lo")) < 5e-5 and abs(hi - g.want(f"{sub}_band_hi")) < 5e-5, (gid, sub, lo, hi)
    assert band(2594) == (band(2594)[0], band(2594)[1]) and abs(band(2594)[0] - 0.0414) < 5e-5 and abs(band(2594)[1] - 0.0586) < 5e-5
    s11 = G.golden("S11")
    G.assert_close(22.5 / 29.8, s11.want("conc_bound_abs"), "ratio")
    G.assert_close(0.05 / (0.298 - 0.225), s11.want("conc_bound_single"), "ratio")
    G.assert_close(min(0.694, 22.5 / 29.8, 0.05 / (0.298 - 0.225)), s11.want("gross_2oct"), "weight")


# --------------------------------------------------------------------------- #
# docs/macro_fixtures.py (TASK-M1-22)
# --------------------------------------------------------------------------- #
def test_macro_fixtures_refuses_when_reference_dir_absent():
    """An absent or empty reference directory: clear refusal listing every missing file; nothing written; exit 2."""
    with tempfile.TemporaryDirectory() as tmp:
        absent, empty, out = Path(tmp) / "nope", Path(tmp) / "ref", Path(tmp) / "out"
        empty.mkdir()
        for ref in (absent, empty):
            missing = MF.missing_files(ref)
            assert missing[0] == "CATALOG.md" and len(missing) == 1 + len(MF.REFERENCE_FILES)
            try:
                MF.generate(ref, out, retrieved_at_utc=datetime(2026, 10, 2, 9, tzinfo=timezone.utc), licence="x", owner="y")
                raise AssertionError("generate must refuse")
            except MF.ReferenceMissing as exc:
                msg = str(exc)
                assert exc.missing == missing and "refused" in msg and "yahoo_KS11_1996-12_2026-10-02.csv" in msg
                assert ("absent" in msg) == (ref is absent)
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = MF.main(["--reference", str(ref), "--out", str(out)])
            assert rc == 2 and "refused" in buf.getvalue() and "fred_snapshot_2026-10-02/DGS10.csv" in buf.getvalue()
            assert not out.exists()
        # a partial directory names only what is missing
        (empty / "CATALOG.md").write_text("catalog\n", encoding="utf-8")
        (empty / "sox_daily.csv").write_text("date,close\n2026-10-01,1\n", encoding="utf-8")
        missing = MF.missing_files(empty)
        assert "CATALOG.md" not in missing and "sox_daily.csv" not in missing and len(missing) == len(MF.REFERENCE_FILES) - 1


def _fake_reference(ref: Path) -> None:
    (ref / "CATALOG.md").write_text("fake catalog\n", encoding="utf-8")
    for i, (fid, rel, series, status, *_rest) in enumerate(MF.REFERENCE_FILES):
        p = ref / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        if status:
            p.write_text(f"date,close\n2026-09-30,{100 + i}\n2026-10-01,{101 + i}.5\n", encoding="utf-8")
        else:
            p.write_text(f"item,value\n{fid},{i}\n", encoding="utf-8")


def _available_at(series_id, obs, value_status):
    close = datetime(obs.year, obs.month, obs.day, 6, 30, tzinfo=timezone.utc)      # stub: KRX 15:30 KST
    return close, close + timedelta(seconds=30)


def test_macro_fixtures_generates_provenance_and_freezes_md5():
    """On a complete reference set: values unchanged, the section 4.1 provenance fields appended, md5 per file, manifest
    rows appended once; a regeneration reproduces the md5s; a changed reference file is refused by `freeze`."""
    with tempfile.TemporaryDirectory() as tmp:
        ref, out, manifest = Path(tmp) / "ref", Path(tmp) / "out", Path(tmp) / "MANIFEST.csv"
        ref.mkdir()
        _fake_reference(ref)
        retrieved = datetime(2026, 10, 2, 9, 0, tzinfo=timezone.utc)
        checked = []
        rows = MF.generate(ref, out, retrieved_at_utc=retrieved, licence="test licence", owner="package D",
                           available_at=_available_at, check_fixture=checked.append)
        assert len(rows) == len(MF.REFERENCE_FILES) and all(r["md5"] and r["licence"] and r["owner"] for r in rows)
        assert len(checked) == sum(1 for *_, st, _s, _m, _t in MF.REFERENCE_FILES if st in ("official_close", "vendor_close", "live_snapshot"))
        with (out / "yahoo_KS11_1996-12_2026-10-02.csv").open(encoding="utf-8", newline="") as fh:
            data = list(csv.DictReader(fh))
        assert tuple(data[0]) == ("date", "close") + MF.PROVENANCE_FIELDS
        assert [d["close"] for d in data] == ["114", "115.5"] and data[0]["obs_date"] == "2026-09-30"
        assert data[0]["available_at_utc"] == "2026-09-30T06:30:30Z" and data[0]["obs_utc"] == "2026-09-30T06:30:00Z"
        assert data[0]["value_status"] == "vendor_close" and data[0]["available_at_source"] == "calendar_bound"
        assert data[0]["retrieved_at_utc"] == "2026-10-02T09:00:00Z" and data[0]["vintage"] == "2026-10-02" and len(data[0]["content_hash"]) == 32
        ks11 = next(r for r in rows if r["file"] == "yahoo_KS11_1996-12_2026-10-02.csv")
        assert ks11["span"] == "2026-09-30..2026-10-01" and ks11["value_status_rule"] == "vendor_close; available_at_source = calendar_bound"
        assert (out / "QX_DLA_postpatch.csv").read_text(encoding="utf-8") == (ref / "results/QX_DLA_postpatch.csv").read_text(encoding="utf-8")
        assert MF.freeze(manifest, rows) == len(rows)
        listed = load_manifest(manifest)
        assert set(listed) == {r["file"] for r in rows} and listed[ks11["file"]]["md5"] == ks11["md5"]
        again = MF.generate(ref, out, retrieved_at_utc=retrieved, licence="test licence", owner="package D", available_at=_available_at)
        assert [r["md5"] for r in again] == [r["md5"] for r in rows] and MF.freeze(manifest, again) == 0
        assert load_manifest(manifest) == listed
        (ref / "sox_daily.csv").write_text("date,close\n2026-09-30,1\n2026-10-01,2\n", encoding="utf-8")
        changed = MF.generate(ref, out, retrieved_at_utc=retrieved, licence="test licence", owner="package D", available_at=_available_at)
        try:
            MF.freeze(manifest, changed)
            raise AssertionError("a changed md5 must be refused")
        except MF.FixtureChanged as exc:
            assert "sox_daily.csv" in str(exc) and "L5492" in str(exc)
        assert load_manifest(manifest) == listed
        try:
            MF.generate(ref, out, retrieved_at_utc=retrieved, licence="", owner="package D", available_at=_available_at)
            raise AssertionError("licence required")
        except ValueError as exc:
            assert "not a fixture" in str(exc)
        try:
            MF.generate(ref, out, retrieved_at_utc=retrieved, licence="l", owner="o")       # no calendar injected
            raise AssertionError("must not infer instants from retrieval")
        except RuntimeError as exc:
            assert "inferred" in str(exc)


# --------------------------------------------------------------------------- #
# docs/kis_quote_check.py (TASK-M1-01; T-RO-02 record clause)
# --------------------------------------------------------------------------- #
def test_kis_quote_check_refuses_without_credentials():
    """Import-safe, quotation-only; without credentials it prints the not-run line, records status 'not run' and exits 2."""
    code = _code_only(ROOT / "docs" / "kis_quote_check.py")
    tree = ast.parse(code)
    uapi = [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str) and n.value.startswith("/uapi/")]
    assert uapi and all("/quotations/" in p for p in uapi), uapi
    assert set(KQ.PATHS.values()) == set(uapi) and not any(w in code.lower() for w in ("/trading/", "order_cash", "cano", "tttc"))
    assert "data.krx.kis_client" not in {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.col_offset == 0}
    assert KQ.NOT_RUN_MESSAGE == "not run: owner must run this with KIS credentials over ~20 live sessions"
    import config
    original = config.kis_ready
    config.kis_ready = lambda: False
    try:
        with tempfile.TemporaryDirectory() as tmp:
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = KQ.main(["--out", tmp, "--session", "2026-10-06"], clock=lambda: datetime(2026, 10, 6, 6, 19, 59, tzinfo=timezone.utc))
            assert rc == 2 and buf.getvalue().startswith(KQ.NOT_RUN_MESSAGE)
            rec = json.loads((Path(tmp) / "2026-10-06.json").read_text(encoding="utf-8"))
            assert rec["status"] == "not run" and rec["reason"] == KQ.NOT_RUN_MESSAGE and rec["read_only"] is True
            assert rec["app_key_can_trade"] == "unknown" and rec["sessions"] == [] and rec["official_close"]["market_div_code"] is None
            assert set(rec["dependent_features"]) == {"R-27 snapshots", "R-08 spread snapshots", "R-26 stress-line calibration"}
            assert set(rec["dependent_features"].values()) == {"UNVERIFIED"} and rec["codes"] == ["069500", "005930"]
    finally:
        config.kis_ready = original


test_kis_quote_check_refuses_without_credentials.test_ids = ["T-RO-02"]


def test_kis_quote_check_owner_record():
    """T-RO-02 record clause: a 'run' record from the owner's live sessions; until then OWNER."""
    runs = [p for p in sorted(KQ.OUT_DIR.glob("*.json")) if json.loads(p.read_text(encoding="utf-8")).get("status") == "run"]
    if not runs:
        raise NotRun("OWNER: KIS quote-field check not run; run docs/kis_quote_check.py with KIS credentials at 15:19:59 KST "
                     "over ~20 live sessions and record app_key_can_trade (docs/kis_quote_check/<session>.json)")
    for p in runs:
        rec = json.loads(p.read_text(encoding="utf-8"))
        assert rec["read_only"] is True and all("/quotations/" in x for x in rec["paths"])
        assert rec["app_key_can_trade"] in ("yes", "no", "unknown") and rec["sessions"], p.name


test_kis_quote_check_owner_record.test_ids = ["T-RO-02"]


if __name__ == "__main__":
    from tests.macro_acceptance import run_module
    raise SystemExit(run_module(globals()))
