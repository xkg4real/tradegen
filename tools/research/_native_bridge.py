"""Optional ctypes fast-path loader for native/tradegen_fast/build/libtradegen_fast.so.

Research only. Falls back seamlessly to pure Python when libtradegen_fast.so is absent,
unbuilt, ABI-mismatched, or when TRADEGEN_DISABLE_NATIVE=1 is set.
Zero imports from core.compliance, core.odds, execution*, tools.owner, config, or main.
"""
from __future__ import annotations

import ctypes
import math
import os
from pathlib import Path
import stat
from typing import Any, Mapping, Sequence


EXPECTED_ABI_VERSION = 1
TG_OK = 0
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SO_PATH = REPO_ROOT / "native" / "tradegen_fast" / "build" / "libtradegen_fast.so"


class TgBidGapMcOut(ctypes.Structure):
    _fields_ = [
        ("favorable_prob", ctypes.c_double),
        ("adverse_prob", ctypes.c_double),
        ("mean_net_return", ctypes.c_double),
        ("p05_net_return", ctypes.c_double),
        ("p95_net_return", ctypes.c_double),
    ]


_CACHED_SO_PATH: Path | None = None
_CACHED_LIB: ctypes.CDLL | None = None
_LOAD_ATTEMPTED = False


def is_native_disabled() -> bool:
    return os.environ.get("TRADEGEN_DISABLE_NATIVE", "").strip() == "1"


def _load_library(so_path: Path | None = None) -> ctypes.CDLL | None:
    global _CACHED_SO_PATH, _CACHED_LIB, _LOAD_ATTEMPTED
    if is_native_disabled():
        return None
    target = DEFAULT_SO_PATH if so_path is None else Path(so_path)
    if so_path is None and _LOAD_ATTEMPTED and _CACHED_SO_PATH == target:
        return _CACHED_LIB

    try:
        st = target.lstat()
        if stat.S_ISLNK(st.st_mode) or not stat.S_ISREG(st.st_mode):
            return None
        lib = ctypes.CDLL(str(target))
        abi_fn = getattr(lib, "tg_abi_version", None)
        mc_fn = getattr(lib, "tg_adaptive_bid_gap_mc", None)
        if abi_fn is None or mc_fn is None:
            return None
        abi_fn.argtypes = []
        abi_fn.restype = ctypes.c_uint32
        if int(abi_fn()) != EXPECTED_ABI_VERSION:
            return None

        mc_fn.argtypes = [
            ctypes.POINTER(ctypes.c_double),
            ctypes.c_int32,
            ctypes.c_int32,
            ctypes.c_int32,
            ctypes.c_int32,
            ctypes.c_double,
            ctypes.c_uint64,
            ctypes.POINTER(TgBidGapMcOut),
        ]
        mc_fn.restype = ctypes.c_int32
    except OSError:
        lib = None

    if so_path is None:
        _CACHED_SO_PATH = target
        _CACHED_LIB = lib
        _LOAD_ATTEMPTED = True
    return lib


def reset_cache() -> None:
    global _CACHED_SO_PATH, _CACHED_LIB, _LOAD_ATTEMPTED
    _CACHED_SO_PATH = None
    _CACHED_LIB = None
    _LOAD_ATTEMPTED = False


def native_available(so_path: Path | None = None) -> bool:
    return _load_library(so_path) is not None


def run_adaptive_bid_gap_mc(
    simple_returns: Sequence[float],
    *,
    n_paths: int,
    horizon: int,
    block_len: int,
    cost_hurdle: float,
    seed: int,
    so_path: Path | None = None,
) -> dict[str, float] | None:
    """Invoke tg_adaptive_bid_gap_mc if native library is available; else return None."""
    lib = _load_library(so_path)
    if lib is None:
        return None
    n_obs = len(simple_returns)
    if n_obs < 2 or n_paths < 1 or horizon < 1 or block_len < 1 or cost_hurdle < 0.0:
        return None
    arr_type = ctypes.c_double * n_obs
    c_returns = arr_type(*(float(r) for r in simple_returns))
    out = TgBidGapMcOut()
    rc = int(lib.tg_adaptive_bid_gap_mc(
        c_returns,
        ctypes.c_int32(n_obs),
        ctypes.c_int32(n_paths),
        ctypes.c_int32(horizon),
        ctypes.c_int32(block_len),
        ctypes.c_double(cost_hurdle),
        ctypes.c_uint64(seed & 0xFFFFFFFFFFFFFFFF),
        ctypes.byref(out),
    ))
    if rc != TG_OK:
        return None
    return {
        "favorable_prob": float(out.favorable_prob),
        "adverse_prob": float(out.adverse_prob),
        "mean_net_return": float(out.mean_net_return),
        "p05_net_return": float(out.p05_net_return),
        "p95_net_return": float(out.p95_net_return),
    }


def sample_direction_native(
    log_returns: Sequence[float],
    config: Mapping[str, Any],
    origin: int,
    *,
    so_path: Path | None = None,
) -> tuple[int, int] | None:
    """Fast-path hook for adaptive_bid_gap_preview.sample_direction."""
    if is_native_disabled() or len(log_returns) < 2:
        return None
    draws = int(config["paths"])
    horizon = int(config["horizon"])
    block_len = int(config["block"])
    if "cost_bps" in config:
        cost_hurdle = int(config["cost_bps"]) / 10000.0
    else:
        cost_hurdle = max(0.0, math.expm1(float(config.get("up_barrier", 0.0))))
    seed64 = ((int(config["seed"]) << 40) + int(origin)) & 0xFFFFFFFFFFFFFFFF
    simple_rets = [math.expm1(float(r)) for r in log_returns]
    res = run_adaptive_bid_gap_mc(
        simple_rets,
        n_paths=draws,
        horizon=horizon,
        block_len=block_len,
        cost_hurdle=cost_hurdle,
        seed=seed64,
        so_path=so_path,
    )
    if res is None:
        return None
    pos = int(round(res["favorable_prob"] * draws))
    neg = int(round(res["adverse_prob"] * draws))
    return pos, neg
