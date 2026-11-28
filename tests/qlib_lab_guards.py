"""Static security, isolation, D14 closure, forbidden-pattern, and C++17 native kernel parity tests."""
from __future__ import annotations

import ast
import hashlib
import json
import os
from pathlib import Path
import tempfile
from unittest.mock import patch

import numpy as np

from core.compliance.owner import code_files
from core.isolation import QUANTGEN_STATE
from core.quant.gate_ledger import scan_forbidden
from qlib_lab import (
    RESEARCH_FLAGS,
    SecurityRefusalError,
    _accel,
    init_instance_by_config,
    list_registered_components,
)
from qlib_lab._accel.build_accel import build_shared_library
from qlib_lab.online.exporter import DISCLAIMER_KO
from qlib_lab.workflow import R

REPO_ROOT = Path(__file__).resolve().parents[1]
QLIB_DIR = REPO_ROOT / "qlib_lab"
DOC_PATH = REPO_ROOT / "docs" / "qlib-model-factory.md"

_FORBIDDEN_MODULES = frozenset(
    {
        "pickle",
        "_pickle",
        "cPickle",
        "dill",
        "marshal",
        "shelve",
        "cloudpickle",
        "urllib",
        "requests",
        "httpx",
        "aiohttp",
        "socket",
        "websocket",
        "ftplib",
        "smtplib",
    }
)


def test_d14_code_closure_has_zero_qlib_lab_paths() -> None:
    closure = [rel for rel, _sha in code_files(REPO_ROOT)]
    assert closure, "Expected non-empty D14 code closure"
    leaked = [p for p in closure if p.startswith("qlib_lab/") or p.startswith("tools/research/")]
    assert leaked == [], f"D14 code closure leaked research paths: {leaked}"


def test_gate_ledger_scan_forbidden_is_clean() -> None:
    sources: dict[str, str] = {}
    for path in sorted(QLIB_DIR.rglob("*.py")):
        sources[path.relative_to(REPO_ROOT).as_posix()] = path.read_text(encoding="utf-8")
    assert len(sources) >= 18
    hits = scan_forbidden(sources)
    assert hits == [], f"gate_ledger.scan_forbidden flagged qlib_lab sources: {hits}"


def test_static_ast_zero_pickle_eval_network_wallclock_and_lf() -> None:
    all_checked_files = (
        sorted(QLIB_DIR.rglob("*.py"))
        + [QLIB_DIR / "_accel" / "kernels.cpp", DOC_PATH]
        + sorted((REPO_ROOT / "tests").glob("qlib_lab_*.py"))
    )
    for fpath in all_checked_files:
        raw = fpath.read_bytes()
        assert b"\r" not in raw, f"Non-LF line ending (CR) detected in {fpath}"

    doc_text = DOC_PATH.read_text(encoding="utf-8").strip()
    assert doc_text.endswith(DISCLAIMER_KO), "docs/qlib-model-factory.md missing required Korean disclaimer footer"

    for py_path in sorted(QLIB_DIR.rglob("*.py")):
        rel = py_path.relative_to(REPO_ROOT).as_posix()
        tree = ast.parse(py_path.read_text(encoding="utf-8"), filename=rel)

        # Check imports and dynamic calls
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    top = alias.name.split(".")[0]
                    assert top not in _FORBIDDEN_MODULES, f"{rel}: forbidden import {alias.name}"
                    assert alias.name != "http.client", f"{rel}: forbidden http.client import"
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                top = mod.split(".")[0]
                assert top not in _FORBIDDEN_MODULES, f"{rel}: forbidden from-import {mod}"
                assert not mod.startswith("http"), f"{rel}: forbidden http import {mod}"
                for alias in node.names:
                    assert alias.name != "import_module", f"{rel}: importlib.import_module is forbidden"
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    assert node.func.id not in ("eval", "exec", "compile", "__import__"), (
                        f"{rel}: forbidden builtin call {node.func.id}()"
                    )
                elif isinstance(node.func, ast.Attribute):
                    assert node.func.attr != "import_module", f"{rel}: import_module() call forbidden"

        # Check wall-clock calls outside qlib_lab/cli.py:main
        if rel != "qlib_lab/cli.py":
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                    if node.func.attr in ("now", "utcnow", "today"):
                        raise AssertionError(f"{rel}: wall-clock call .{node.func.attr}() forbidden outside cli.py:main")
                    if (
                        node.func.attr == "time"
                        and isinstance(node.func.value, ast.Name)
                        and node.func.value.id == "time"
                    ):
                        raise AssertionError(f"{rel}: time.time() forbidden outside cli.py:main")
        else:
            for stmt in tree.body:
                if isinstance(stmt, ast.FunctionDef) and stmt.name != "main":
                    for sub in ast.walk(stmt):
                        if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute):
                            assert sub.func.attr not in ("now", "utcnow", "today"), (
                                f"qlib_lab/cli.py:{stmt.name} called .{sub.func.attr}() outside main()"
                            )


def test_component_registry_whitelist_refuses_untrusted_classes() -> None:
    comps = list_registered_components()
    for expected in (
        "RidgeLinearModel",
        "MultinomialDirectionModel",
        "HistGBDTModel",
        "DoubleEnsembleModel",
        "DataHandlerLP",
        "DatasetH",
        "SignalRecord",
        "DirectionGateRecord",
        "PortfolioGateRecord",
        "RollingGen",
    ):
        assert expected in comps, f"Missing registered component {expected}"

    for bad_cfg in (
        {"class": "Popen", "module_path": "subprocess", "kwargs": {}},
        {"class": "system", "module_path": "os", "kwargs": {}},
        {"class": "NonExistentModel", "kwargs": {}},
        {"class": "RidgeLinearModel", "module_path": "os.path", "kwargs": {}},
        {"class": "RidgeLinearModel", "unexpected_key": 123},
    ):
        try:
            init_instance_by_config(bad_cfg)
            raise AssertionError(f"Expected SecurityRefusalError for {bad_cfg}")
        except SecurityRefusalError:
            pass


def test_cpp17_accel_build_tamper_guard_and_numpy_parity() -> None:
    prev_env = os.environ.get("QLIB_LAB_DISABLE_ACCEL")
    try:
        # 1. Build canonical workspace library & verify RESEARCH_FLAGS in build_manifest.json
        manifest = build_shared_library()
        for k, v in RESEARCH_FLAGS.items():
            assert manifest[k] is v
        os.environ["QLIB_LAB_DISABLE_ACCEL"] = "0"
        lib = _accel.verify_and_load_accel(force_reload=True)
        assert lib is not None and _accel.active_backend() == "cpp17"
        assert lib._name == f"/proc/self/fd/{lib._tradegen_image.fileno()}"

        # 2. Verify SHA-256 tamper refusal in an isolated temporary directory
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            build_shared_library(output_dir=tmp_dir)
            so_copy = tmp_dir / "libqlib_accel.so"
            mf_copy = tmp_dir / "build_manifest.json"
            assert _accel.verify_and_load_accel(lib_path=so_copy, manifest_path=mf_copy) is not None

            # Tamper manifest binary_sha256 -> must refuse before CDLL!
            tampered_mf = json.loads(mf_copy.read_text(encoding="utf-8"))
            tampered_mf["binary_sha256"] = "0" * 64
            mf_copy.write_text(json.dumps(tampered_mf), encoding="utf-8")
            try:
                _accel.verify_and_load_accel(lib_path=so_copy, manifest_path=mf_copy)
                raise AssertionError("Expected SecurityRefusalError on tampered binary_sha256")
            except SecurityRefusalError:
                pass

        # 3. Full numerical parity across all C++17 kernels vs pure-NumPy fallback (including large offset 1e8 + eps)
        rng = np.random.default_rng(2026)
        x = 1.0e8 + rng.normal(0.0, 2.5, 400)
        x[[0, 1, 33, 120]] = np.nan
        y = rng.normal(0.0, 1.0, 400)
        y[[5, 120]] = np.nan
        high = x + np.abs(rng.normal(1.2, 0.3, 400))
        low = x - np.abs(rng.normal(1.2, 0.3, 400))

        xb = rng.integers(0, 64, size=(250, 8), dtype=np.uint8)
        xb[:20, 3] = 255
        grad = rng.normal(0.0, 1.0, 250)
        hess = rng.uniform(0.05, 1.5, 250)
        s_idx = np.arange(0, 180, dtype=np.int32)
        n_fin = np.full(8, 64, dtype=np.int32)

        def _collect_all():
            G_p, H_p, C_p = _accel.hist_build(xb, grad, hess, s_idx)
            G_s, H_s, C_s = _accel.hist_build(xb, grad, hess, s_idx[:70])
            G_l, H_l, C_l = _accel.hist_subtract(G_p, H_p, C_p, G_s, H_s, C_s)
            sp = _accel.hist_best_split(G_p, H_p, C_p, n_fin, None, 10, 0.1, 1.0, 0.0)
            return (
                [
                    _accel.rolling_mean(x, 24),
                    _accel.rolling_sum(x - 1.0e8, 24),
                    _accel.rolling_std(x, 24),
                    _accel.rolling_var(x, 24),
                    _accel.rolling_skew(x, 24),
                    _accel.rolling_kurt(x, 24),
                    _accel.rolling_max(x, 24),
                    _accel.rolling_min(x, 24),
                    _accel.ema(x - 1.0e8, 12),
                    _accel.wilder_rsi(x, 14),
                    _accel.wilder_atr(high, low, x, 14),
                    _accel.rolling_cov(x, y, 24),
                    _accel.rolling_corr(x, y, 24),
                    *_accel.rolling_ols(x - 1.0e8, 24),
                ],
                (G_p, H_p, C_p, G_l, H_l, C_l, sp),
            )

        os.environ["QLIB_LAB_DISABLE_ACCEL"] = "0"
        _accel.verify_and_load_accel(force_reload=True)
        assert _accel.active_backend() == "cpp17"
        cpp_vecs, cpp_hist = _collect_all()

        os.environ["QLIB_LAB_DISABLE_ACCEL"] = "1"
        assert _accel.active_backend() == "numpy"
        np_vecs, np_hist = _collect_all()

        for idx, (va, vb) in enumerate(zip(cpp_vecs, np_vecs)):
            np.testing.assert_allclose(va, vb, rtol=1e-11, atol=1e-11, equal_nan=True, err_msg=f"vec {idx}")

        for idx in (0, 1, 3, 4):
            np.testing.assert_allclose(cpp_hist[idx], np_hist[idx], rtol=1e-12, atol=1e-12)
        assert np.array_equal(cpp_hist[2], np_hist[2])
        assert np.array_equal(cpp_hist[5], np_hist[5])
        assert cpp_hist[6][:3] == np_hist[6][:3]
        assert abs(cpp_hist[6][3] - np_hist[6][3]) < 1e-11
    finally:
        if prev_env is None:
            os.environ.pop("QLIB_LAB_DISABLE_ACCEL", None)
        else:
            os.environ["QLIB_LAB_DISABLE_ACCEL"] = prev_env
        _accel.verify_and_load_accel(force_reload=True)


def test_isolation_refuses_quantgen_and_symlinks() -> None:
    # 1. QUANTGEN (~/.nextgen) path refusal before any I/O
    q_target = QUANTGEN_STATE / "forbidden_qlib_exp"
    try:
        with R.start(experiment_name="bad", uri=q_target):
            pass
        raise AssertionError("Expected RuntimeError when targeting QUANTGEN_STATE")
    except RuntimeError:
        pass

    # 2. Symlink refusal via checked_target
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        real_dir = root / "real"
        real_dir.mkdir()
        link_dir = root / "sym_uri"
        link_dir.symlink_to(real_dir)
        try:
            with R.start(experiment_name="bad_sym", uri=link_dir):
                pass
            raise AssertionError("Expected RuntimeError when URI is a symlink")
        except RuntimeError:
            pass


def test_consistent_unreviewed_build_selects_numpy_before_binding() -> None:
    with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {"QLIB_LAB_DISABLE_ACCEL": "0"}):
        directory = Path(tmp)
        image = directory / "libqlib_accel.so"
        manifest = directory / "build_manifest.json"
        sample = b"offline fixture"
        image.write_bytes(sample)
        manifest.write_text(json.dumps({
            "source_sha256": _accel.EXPECTED_SOURCE_SHA256,
            "binary_sha256": hashlib.sha256(sample).hexdigest(),
        }), encoding="ascii")
        with patch.object(_accel.ctypes, "CDLL") as bind:
            assert _accel.verify_and_load_accel(lib_path=image, manifest_path=manifest) is None
            bind.assert_not_called()
