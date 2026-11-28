"""Verified ctypes dispatcher for C++17 kernels with automatic pure-NumPy fallback."""
from __future__ import annotations

import ctypes
import hashlib
import json
import os
from pathlib import Path

import numpy as np

from core.compliance.native_accel import sealed_image
from core.isolation import checked_target
from qlib_lab._accel import numpy_fallback as _np_fb
from qlib_lab.exceptions import SecurityRefusalError

ACCEL_DIR = Path(__file__).resolve().parent
SOURCE_PATH = ACCEL_DIR / "kernels.cpp"
BUILD_DIR = ACCEL_DIR / "build"
LIB_PATH = BUILD_DIR / "libqlib_accel.so"
MANIFEST_PATH = BUILD_DIR / "build_manifest.json"
# Reproduced from kernels.cpp using build_accel.CXX_FLAGS on Linux x86-64
# with g++ (Debian 14.2.0-19) 14.2.0. Both pins are independent of the build directory.
EXPECTED_SOURCE_SHA256 = "b9a5bbe17394f9040082e1733a582939a2c1900dc072ee9043906dbd4dfb2111"
EXPECTED_BINARY_SHA256 = "5422b5743c8943e44edaf683e66220b8db3cd81c8f929f09d8bb21539b13a510"
MAX_BINARY_BYTES = 32 * 1024 * 1024

_C_DOUBLE_P = ctypes.POINTER(ctypes.c_double)
_C_INT64_P = ctypes.POINTER(ctypes.c_int64)
_C_INT32_P = ctypes.POINTER(ctypes.c_int32)
_C_UINT8_P = ctypes.POINTER(ctypes.c_uint8)

_LIB_HANDLE: ctypes.CDLL | None = None
_BACKEND: str = "uninitialized"


def _sha256_bytes(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _bind_signatures(lib: ctypes.CDLL) -> None:
    lib.rolling_moments_f64.argtypes = [
        _C_DOUBLE_P, ctypes.c_int64, ctypes.c_int64, ctypes.c_int64, ctypes.c_int32, _C_DOUBLE_P,
    ]
    lib.rolling_moments_f64.restype = None

    lib.rolling_extrema_f64.argtypes = [
        _C_DOUBLE_P, ctypes.c_int64, ctypes.c_int64, ctypes.c_int64, ctypes.c_int32, _C_DOUBLE_P,
    ]
    lib.rolling_extrema_f64.restype = None

    lib.ema_f64.argtypes = [
        _C_DOUBLE_P, ctypes.c_int64, ctypes.c_double, ctypes.c_int64, _C_DOUBLE_P,
    ]
    lib.ema_f64.restype = None

    lib.wilder_rsi_f64.argtypes = [
        _C_DOUBLE_P, ctypes.c_int64, ctypes.c_int64, _C_DOUBLE_P,
    ]
    lib.wilder_rsi_f64.restype = None

    lib.wilder_atr_f64.argtypes = [
        _C_DOUBLE_P, _C_DOUBLE_P, _C_DOUBLE_P, ctypes.c_int64, ctypes.c_int64, _C_DOUBLE_P,
    ]
    lib.wilder_atr_f64.restype = None

    lib.rolling_biv_f64.argtypes = [
        _C_DOUBLE_P, _C_DOUBLE_P, ctypes.c_int64, ctypes.c_int64, ctypes.c_int64, ctypes.c_int32, _C_DOUBLE_P,
    ]
    lib.rolling_biv_f64.restype = None

    lib.rolling_ols_f64.argtypes = [
        _C_DOUBLE_P, ctypes.c_int64, ctypes.c_int64, ctypes.c_int64, _C_DOUBLE_P, _C_DOUBLE_P, _C_DOUBLE_P,
    ]
    lib.rolling_ols_f64.restype = None

    lib.hist_build_f64.argtypes = [
        _C_UINT8_P, _C_DOUBLE_P, _C_DOUBLE_P, _C_INT32_P,
        ctypes.c_int64, ctypes.c_int64, ctypes.c_int64,
        _C_DOUBLE_P, _C_DOUBLE_P, _C_INT64_P,
    ]
    lib.hist_build_f64.restype = None

    lib.hist_subtract_f64.argtypes = [
        _C_DOUBLE_P, _C_DOUBLE_P, _C_INT64_P,
        _C_DOUBLE_P, _C_DOUBLE_P, _C_INT64_P,
        ctypes.c_int64,
        _C_DOUBLE_P, _C_DOUBLE_P, _C_INT64_P,
    ]
    lib.hist_subtract_f64.restype = None

    lib.hist_best_split_f64.argtypes = [
        _C_DOUBLE_P, _C_DOUBLE_P, _C_INT64_P,
        _C_INT32_P, _C_UINT8_P,
        ctypes.c_int64, ctypes.c_int64, ctypes.c_double, ctypes.c_double, ctypes.c_double,
        _C_INT32_P, _C_INT32_P, _C_INT32_P, _C_DOUBLE_P,
    ]
    lib.hist_best_split_f64.restype = None


def verify_and_load_accel(
    *,
    force_reload: bool = False,
    lib_path: Path | None = None,
    manifest_path: Path | None = None,
    source_path: Path | None = None,
) -> ctypes.CDLL | None:
    """Verify SHA-256 of kernels.cpp and libqlib_accel.so before loading via ctypes.CDLL.

    Returns None (using pure-NumPy fallback) if QLIB_LAB_DISABLE_ACCEL=1 or the .so has not been built yet.
    Raises SecurityRefusalError if .so exists without a valid matching SHA-256 manifest (tamper refusal).
    """
    global _LIB_HANDLE, _BACKEND

    custom_paths = any(p is not None for p in (lib_path, manifest_path, source_path))
    if not force_reload and not custom_paths and _BACKEND != "uninitialized":
        if os.environ.get("QLIB_LAB_DISABLE_ACCEL", "0").strip() == "1":
            return None
        return _LIB_HANDLE

    if os.environ.get("QLIB_LAB_DISABLE_ACCEL", "0").strip() == "1":
        if not custom_paths:
            _LIB_HANDLE = None
            _BACKEND = "numpy"
        return None

    so_file = lib_path or LIB_PATH
    mf_file = manifest_path or MANIFEST_PATH
    src_file = source_path or SOURCE_PATH

    if not so_file.exists():
        if not custom_paths:
            _LIB_HANDLE = None
            _BACKEND = "numpy"
        return None

    checked_so = checked_target(so_file, "accel_so", within=so_file.parent if custom_paths else BUILD_DIR)
    if not mf_file.exists():
        raise SecurityRefusalError(
            f"Shared library {checked_so} exists without {mf_file.name}; refusing unverified binary"
        )
    checked_mf = checked_target(mf_file, "accel_manifest", within=mf_file.parent if custom_paths else BUILD_DIR)
    checked_src = checked_target(src_file, "accel_source", within=src_file.parent if custom_paths else ACCEL_DIR)

    try:
        manifest = json.loads(checked_mf.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise SecurityRefusalError(f"Unreadable accel build manifest: {exc}") from exc

    if not isinstance(manifest, dict):
        raise SecurityRefusalError("Accel build manifest is not a JSON object")

    actual_src_sha = _sha256_bytes(checked_src)
    with checked_so.open("rb") as stream:
        binary = stream.read(MAX_BINARY_BYTES + 1)
    if not 0 < len(binary) <= MAX_BINARY_BYTES:
        raise SecurityRefusalError("Invalid native kernel image size")
    actual_bin_sha = hashlib.sha256(binary).hexdigest()
    if manifest.get("source_sha256") != actual_src_sha:
        raise SecurityRefusalError(
            f"Accel source SHA-256 mismatch: manifest={manifest.get('source_sha256')} vs actual={actual_src_sha}"
        )
    if manifest.get("binary_sha256") != actual_bin_sha:
        raise SecurityRefusalError(
            f"Accel binary SHA-256 mismatch: manifest={manifest.get('binary_sha256')} vs actual={actual_bin_sha}"
        )

    image = None
    if actual_src_sha == EXPECTED_SOURCE_SHA256 and actual_bin_sha == EXPECTED_BINARY_SHA256:
        image = sealed_image(binary)
    if image is None:
        if not custom_paths:
            _LIB_HANDLE = None
            _BACKEND = "numpy"
        return None
    try:
        lib = ctypes.CDLL(f"/proc/self/fd/{image.fileno()}")
    except OSError:
        image.close()
        if not custom_paths:
            _LIB_HANDLE = None
            _BACKEND = "numpy"
        return None
    lib._tradegen_image = image
    _bind_signatures(lib)
    if not custom_paths:
        _LIB_HANDLE = lib
        _BACKEND = "cpp17"
    return lib


def active_backend() -> str:
    """Return 'cpp17' when verified shared library is active, else 'numpy'."""
    lib = verify_and_load_accel()
    return "cpp17" if lib is not None else "numpy"


def _f64_1d(x) -> np.ndarray:
    return np.ascontiguousarray(x, dtype=np.float64).ravel()


def rolling_mean(x, window: int, min_periods: int | None = None) -> np.ndarray:
    mp = window if min_periods is None else int(min_periods)
    lib = verify_and_load_accel()
    if lib is None:
        return _np_fb.rolling_moments_np(x, int(window), mp, 0)
    arr = _f64_1d(x)
    out = np.full(arr.size, np.nan, dtype=np.float64)
    if arr.size > 0 and window > 0:
        lib.rolling_moments_f64(
            arr.ctypes.data_as(_C_DOUBLE_P), arr.size, int(window), mp, 0, out.ctypes.data_as(_C_DOUBLE_P)
        )
    return out


def rolling_sum(x, window: int, min_periods: int | None = None) -> np.ndarray:
    mp = window if min_periods is None else int(min_periods)
    lib = verify_and_load_accel()
    if lib is None:
        return _np_fb.rolling_moments_np(x, int(window), mp, 5)
    arr = _f64_1d(x)
    out = np.full(arr.size, np.nan, dtype=np.float64)
    if arr.size > 0 and window > 0:
        lib.rolling_moments_f64(
            arr.ctypes.data_as(_C_DOUBLE_P), arr.size, int(window), mp, 5, out.ctypes.data_as(_C_DOUBLE_P)
        )
    return out


def rolling_std(x, window: int, min_periods: int | None = None) -> np.ndarray:
    mp = window if min_periods is None else int(min_periods)
    lib = verify_and_load_accel()
    if lib is None:
        return _np_fb.rolling_moments_np(x, int(window), mp, 1)
    arr = _f64_1d(x)
    out = np.full(arr.size, np.nan, dtype=np.float64)
    if arr.size > 0 and window > 0:
        lib.rolling_moments_f64(
            arr.ctypes.data_as(_C_DOUBLE_P), arr.size, int(window), mp, 1, out.ctypes.data_as(_C_DOUBLE_P)
        )
    return out


def rolling_var(x, window: int, min_periods: int | None = None) -> np.ndarray:
    mp = window if min_periods is None else int(min_periods)
    lib = verify_and_load_accel()
    if lib is None:
        return _np_fb.rolling_moments_np(x, int(window), mp, 2)
    arr = _f64_1d(x)
    out = np.full(arr.size, np.nan, dtype=np.float64)
    if arr.size > 0 and window > 0:
        lib.rolling_moments_f64(
            arr.ctypes.data_as(_C_DOUBLE_P), arr.size, int(window), mp, 2, out.ctypes.data_as(_C_DOUBLE_P)
        )
    return out


def rolling_skew(x, window: int, min_periods: int | None = None) -> np.ndarray:
    mp = window if min_periods is None else int(min_periods)
    lib = verify_and_load_accel()
    if lib is None:
        return _np_fb.rolling_moments_np(x, int(window), mp, 3)
    arr = _f64_1d(x)
    out = np.full(arr.size, np.nan, dtype=np.float64)
    if arr.size > 0 and window > 0:
        lib.rolling_moments_f64(
            arr.ctypes.data_as(_C_DOUBLE_P), arr.size, int(window), mp, 3, out.ctypes.data_as(_C_DOUBLE_P)
        )
    return out


def rolling_kurt(x, window: int, min_periods: int | None = None) -> np.ndarray:
    mp = window if min_periods is None else int(min_periods)
    lib = verify_and_load_accel()
    if lib is None:
        return _np_fb.rolling_moments_np(x, int(window), mp, 4)
    arr = _f64_1d(x)
    out = np.full(arr.size, np.nan, dtype=np.float64)
    if arr.size > 0 and window > 0:
        lib.rolling_moments_f64(
            arr.ctypes.data_as(_C_DOUBLE_P), arr.size, int(window), mp, 4, out.ctypes.data_as(_C_DOUBLE_P)
        )
    return out


def rolling_max(x, window: int, min_periods: int | None = None) -> np.ndarray:
    mp = window if min_periods is None else int(min_periods)
    lib = verify_and_load_accel()
    if lib is None:
        return _np_fb.rolling_extrema_np(x, int(window), mp, True)
    arr = _f64_1d(x)
    out = np.full(arr.size, np.nan, dtype=np.float64)
    if arr.size > 0 and window > 0:
        lib.rolling_extrema_f64(
            arr.ctypes.data_as(_C_DOUBLE_P), arr.size, int(window), mp, 1, out.ctypes.data_as(_C_DOUBLE_P)
        )
    return out


def rolling_min(x, window: int, min_periods: int | None = None) -> np.ndarray:
    mp = window if min_periods is None else int(min_periods)
    lib = verify_and_load_accel()
    if lib is None:
        return _np_fb.rolling_extrema_np(x, int(window), mp, False)
    arr = _f64_1d(x)
    out = np.full(arr.size, np.nan, dtype=np.float64)
    if arr.size > 0 and window > 0:
        lib.rolling_extrema_f64(
            arr.ctypes.data_as(_C_DOUBLE_P), arr.size, int(window), mp, 0, out.ctypes.data_as(_C_DOUBLE_P)
        )
    return out


def ema(x, span: int | float, min_periods: int = 1) -> np.ndarray:
    alpha = 2.0 / (float(span) + 1.0)
    lib = verify_and_load_accel()
    if lib is None:
        return _np_fb.ema_np(x, alpha, int(min_periods))
    arr = _f64_1d(x)
    out = np.full(arr.size, np.nan, dtype=np.float64)
    if arr.size > 0:
        lib.ema_f64(arr.ctypes.data_as(_C_DOUBLE_P), arr.size, alpha, int(min_periods), out.ctypes.data_as(_C_DOUBLE_P))
    return out


def wilder_rsi(close, period: int = 14) -> np.ndarray:
    lib = verify_and_load_accel()
    if lib is None:
        return _np_fb.wilder_rsi_np(close, int(period))
    arr = _f64_1d(close)
    out = np.full(arr.size, np.nan, dtype=np.float64)
    if arr.size > 0:
        lib.wilder_rsi_f64(arr.ctypes.data_as(_C_DOUBLE_P), arr.size, int(period), out.ctypes.data_as(_C_DOUBLE_P))
    return out


def wilder_atr(high, low, close, period: int = 14) -> np.ndarray:
    lib = verify_and_load_accel()
    if lib is None:
        return _np_fb.wilder_atr_np(high, low, close, int(period))
    ha, la, ca = _f64_1d(high), _f64_1d(low), _f64_1d(close)
    out = np.full(ca.size, np.nan, dtype=np.float64)
    if ca.size > 0:
        lib.wilder_atr_f64(
            ha.ctypes.data_as(_C_DOUBLE_P),
            la.ctypes.data_as(_C_DOUBLE_P),
            ca.ctypes.data_as(_C_DOUBLE_P),
            ca.size,
            int(period),
            out.ctypes.data_as(_C_DOUBLE_P),
        )
    return out


def rolling_corr(x, y, window: int, min_periods: int | None = None) -> np.ndarray:
    mp = max(2, int(window)) if min_periods is None else int(min_periods)
    lib = verify_and_load_accel()
    if lib is None:
        return _np_fb.rolling_biv_np(x, y, int(window), mp, True)
    xa, ya = _f64_1d(x), _f64_1d(y)
    out = np.full(xa.size, np.nan, dtype=np.float64)
    if xa.size > 0 and window > 0:
        lib.rolling_biv_f64(
            xa.ctypes.data_as(_C_DOUBLE_P),
            ya.ctypes.data_as(_C_DOUBLE_P),
            xa.size,
            int(window),
            mp,
            1,
            out.ctypes.data_as(_C_DOUBLE_P),
        )
    return out


def rolling_cov(x, y, window: int, min_periods: int | None = None) -> np.ndarray:
    mp = max(2, int(window)) if min_periods is None else int(min_periods)
    lib = verify_and_load_accel()
    if lib is None:
        return _np_fb.rolling_biv_np(x, y, int(window), mp, False)
    xa, ya = _f64_1d(x), _f64_1d(y)
    out = np.full(xa.size, np.nan, dtype=np.float64)
    if xa.size > 0 and window > 0:
        lib.rolling_biv_f64(
            xa.ctypes.data_as(_C_DOUBLE_P),
            ya.ctypes.data_as(_C_DOUBLE_P),
            xa.size,
            int(window),
            mp,
            0,
            out.ctypes.data_as(_C_DOUBLE_P),
        )
    return out


def rolling_ols(y, window: int, min_periods: int | None = None) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    mp = max(2, int(window)) if min_periods is None else int(min_periods)
    lib = verify_and_load_accel()
    if lib is None:
        return _np_fb.rolling_ols_np(y, int(window), mp)
    ya = _f64_1d(y)
    slp = np.full(ya.size, np.nan, dtype=np.float64)
    r2 = np.full(ya.size, np.nan, dtype=np.float64)
    resi = np.full(ya.size, np.nan, dtype=np.float64)
    if ya.size > 0 and window > 0:
        lib.rolling_ols_f64(
            ya.ctypes.data_as(_C_DOUBLE_P),
            ya.size,
            int(window),
            mp,
            slp.ctypes.data_as(_C_DOUBLE_P),
            r2.ctypes.data_as(_C_DOUBLE_P),
            resi.ctypes.data_as(_C_DOUBLE_P),
        )
    return slp, r2, resi


def hist_build(
    X_binned: np.ndarray,
    grad: np.ndarray,
    hess: np.ndarray,
    sample_idx: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    lib = verify_and_load_accel()
    if lib is None:
        return _np_fb.hist_build_np(X_binned, grad, hess, sample_idx)
    xb = np.ascontiguousarray(X_binned, dtype=np.uint8)
    g = np.ascontiguousarray(grad, dtype=np.float64).ravel()
    h = np.ascontiguousarray(hess, dtype=np.float64).ravel()
    idx = np.ascontiguousarray(sample_idx, dtype=np.int32).ravel()
    n_total, n_features = xb.shape
    out_g = np.zeros((n_features, 256), dtype=np.float64)
    out_h = np.zeros((n_features, 256), dtype=np.float64)
    out_c = np.zeros((n_features, 256), dtype=np.int64)
    lib.hist_build_f64(
        xb.ctypes.data_as(_C_UINT8_P),
        g.ctypes.data_as(_C_DOUBLE_P),
        h.ctypes.data_as(_C_DOUBLE_P),
        idx.ctypes.data_as(_C_INT32_P),
        int(n_total),
        int(idx.size),
        int(n_features),
        out_g.ctypes.data_as(_C_DOUBLE_P),
        out_h.ctypes.data_as(_C_DOUBLE_P),
        out_c.ctypes.data_as(_C_INT64_P),
    )
    return out_g, out_h, out_c


def hist_subtract(
    parent_G: np.ndarray,
    parent_H: np.ndarray,
    parent_count: np.ndarray,
    small_G: np.ndarray,
    small_H: np.ndarray,
    small_count: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    lib = verify_and_load_accel()
    if lib is None:
        return _np_fb.hist_subtract_np(parent_G, parent_H, parent_count, small_G, small_H, small_count)
    pg = np.ascontiguousarray(parent_G, dtype=np.float64)
    ph = np.ascontiguousarray(parent_H, dtype=np.float64)
    pc = np.ascontiguousarray(parent_count, dtype=np.int64)
    sg = np.ascontiguousarray(small_G, dtype=np.float64)
    sh = np.ascontiguousarray(small_H, dtype=np.float64)
    sc = np.ascontiguousarray(small_count, dtype=np.int64)
    n_features = int(pg.shape[0])
    lg = np.empty_like(pg)
    lh = np.empty_like(ph)
    lc = np.empty_like(pc)
    lib.hist_subtract_f64(
        pg.ctypes.data_as(_C_DOUBLE_P),
        ph.ctypes.data_as(_C_DOUBLE_P),
        pc.ctypes.data_as(_C_INT64_P),
        sg.ctypes.data_as(_C_DOUBLE_P),
        sh.ctypes.data_as(_C_DOUBLE_P),
        sc.ctypes.data_as(_C_INT64_P),
        n_features,
        lg.ctypes.data_as(_C_DOUBLE_P),
        lh.ctypes.data_as(_C_DOUBLE_P),
        lc.ctypes.data_as(_C_INT64_P),
    )
    return lg, lh, lc


def hist_best_split(
    G: np.ndarray,
    H: np.ndarray,
    count: np.ndarray,
    n_finite_bins: np.ndarray,
    feature_mask: np.ndarray | None,
    min_samples_leaf: int,
    min_child_weight: float,
    reg_lambda: float,
    min_split_gain: float,
) -> tuple[int, int, bool, float]:
    lib = verify_and_load_accel()
    if lib is None:
        return _np_fb.hist_best_split_np(
            G, H, count, n_finite_bins, feature_mask, min_samples_leaf, min_child_weight, reg_lambda, min_split_gain
        )
    gc = np.ascontiguousarray(G, dtype=np.float64)
    hc = np.ascontiguousarray(H, dtype=np.float64)
    cc = np.ascontiguousarray(count, dtype=np.int64)
    nb = np.ascontiguousarray(n_finite_bins, dtype=np.int32).ravel()
    n_features = int(gc.shape[0])
    if feature_mask is None:
        fm_ptr = ctypes.cast(0, _C_UINT8_P)
    else:
        fm = np.ascontiguousarray(feature_mask, dtype=np.uint8).ravel()
        fm_ptr = fm.ctypes.data_as(_C_UINT8_P)

    best_f = ctypes.c_int32(-1)
    best_b = ctypes.c_int32(-1)
    best_nan_left = ctypes.c_int32(1)
    best_gain = ctypes.c_double(0.0)
    lib.hist_best_split_f64(
        gc.ctypes.data_as(_C_DOUBLE_P),
        hc.ctypes.data_as(_C_DOUBLE_P),
        cc.ctypes.data_as(_C_INT64_P),
        nb.ctypes.data_as(_C_INT32_P),
        fm_ptr,
        n_features,
        int(min_samples_leaf),
        float(min_child_weight),
        float(reg_lambda),
        float(min_split_gain),
        ctypes.byref(best_f),
        ctypes.byref(best_b),
        ctypes.byref(best_nan_left),
        ctypes.byref(best_gain),
    )
    return int(best_f.value), int(best_b.value), bool(best_nan_left.value), float(best_gain.value)
