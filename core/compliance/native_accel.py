"""Verified C++20 native kernel loader and pure-value marshalling seam.

This module performs no network, clock, credential, signing or ledger operation.
Before loading ``libtradegen_fast.so``, it checks the source and binary digests
against pins in this module and loads a sealed copy of the verified bytes.
Unsupported builds and hosts use the Python reference path. Setting
``TRADEGEN_DISABLE_NATIVE=1`` or running without a built shared object cleanly
returns ``None`` so callers execute their exact pure-Python reference path. A
present manifest or binary whose digest mismatches raises ``NativeIntegrityError``.
"""
from __future__ import annotations

from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import threading

EXPECTED_ABI_VERSION = 1
EXPECTED_SOURCE_SHA256 = "d7a6fd44a93eae1f08d645fe88a94f516617cb017102a1ab7cd8309cbc74ab44"
# Linux x86-64, g++ (Debian 14.2.0-19) 14.2.0, build_native.CXX_FLAGS.
# An additional toolchain output requires review of this D14-covered file.
EXPECTED_BINARY_SHA256 = "66967ba825a69761668e82e09117ebeb73aa7f416e1bb18767d69eb5c346a7ce"

TG_OK = 0
TG_FALLBACK_PRECISION = 1
TG_ERR_INVALID = -1
TG_ERR_NEGATIVE_STATE = -2
TG_ERR_CAPACITY = -3

TG_EVENT_MARK = 0
TG_EVENT_BUY = 1
TG_EVENT_SELL = 2

TG_ORDER_VALID = 0
TG_ORDER_FRACTIONAL_SHARES = 1
TG_ORDER_OFF_LOT = 2
TG_ORDER_OFF_TICK = 3
TG_ORDER_BELOW_MIN_QTY = 4
TG_ORDER_BELOW_MIN_NOTIONAL = 5

TG_FLAG_UNFLAGGED = 0
TG_FLAG_WARNING = 1
TG_FLAG_CAUTION = 2
TG_FLAG_UNKNOWN = 3
TG_FLAG_ABSENT = 4

TG_DECISION_LONG = 0
TG_DECISION_CASH = 1
TG_DECISION_WARMUP = 2
TG_DECISION_UNAVAILABLE = 3

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BUILD_DIR = REPO_ROOT / "native" / "tradegen_fast" / "build"

_HEX64 = re.compile(r"[0-9a-f]{64}")
_SCALE_EXP = 18
_SCALE_INT = 10 ** 18
_MAX_MAG_FP18 = 10 ** 38
_MASK64 = 0xFFFFFFFFFFFFFFFF
_MASK128 = (1 << 128) - 1
_SIGN64 = 1 << 63
_MOD64 = 1 << 64
_MOD128 = 1 << 128
_MAX_MANIFEST_BYTES = 65536
_MAX_SO_BYTES = 32 * 1024 * 1024

_LOCK = threading.Lock()
_CACHE: dict[tuple[str, str], object] = {}


class NativeIntegrityError(RuntimeError):
    """Fixed diagnostic code when a native build manifest or binary is tampered."""


def is_native_disabled() -> bool:
    raw = (os.environ.get("TRADEGEN_DISABLE_NATIVE") or "").strip()
    return raw in ("1", "true", "TRUE", "yes", "YES", "on", "ON")


_ZERO_DEC = Decimal(0)


def decimal_to_fp18(value: Decimal) -> tuple[int, int] | None:
    """Convert exact Decimal to signed 128-bit fp18 (hi, lo), or None if out of fp18 precision/range."""
    if type(value) is not Decimal or not value.is_finite():
        return None
    if not value:
        return (0, 0)
    if not -_SCALE_EXP <= value.adjusted() <= 20:
        return None
    sign = value.is_signed()
    text = format(value.copy_abs(), "f")
    if "." in text:
        whole, frac = text.split(".", 1)
        frac = frac.rstrip("0")
        if len(frac) > _SCALE_EXP or len(whole) > 21:
            return None
        scaled = int(whole) * _SCALE_INT + (int(frac.ljust(_SCALE_EXP, "0")) if frac else 0)
    else:
        if len(text) > 21:
            return None
        scaled = int(text) * _SCALE_INT
    if scaled > _MAX_MAG_FP18:
        return None
    if scaled == 0:
        return (0, 0)
    signed_val = -scaled if sign else scaled
    u = signed_val & _MASK128
    lo = u & _MASK64
    hi_u = (u >> 64) & _MASK64
    hi = hi_u - _MOD64 if hi_u >= _SIGN64 else hi_u
    return (hi, lo)


def fp18_to_int(hi: int, lo: int) -> int:
    u = ((hi & _MASK64) << 64) | (lo & _MASK64)
    return u - _MOD128 if hi < 0 else u


def fp18_to_decimal(hi: int, lo: int) -> Decimal:
    """Convert signed 128-bit fp18 (hi, lo) to canonical exact Decimal without using ambient context."""
    if hi == 0 and lo == 0:
        return _ZERO_DEC
    signed_val = fp18_to_int(hi, lo)
    sign = signed_val < 0
    mag = -signed_val if sign else signed_val
    q, r = divmod(mag, _SCALE_INT)
    if r == 0:
        return Decimal(-q if sign else q)
    frac_str = f"{r:018d}".rstrip("0")
    return Decimal(f"{'-' if sign else ''}{q}.{frac_str}")


def _read_regular_fd(path: Path, max_bytes: int) -> tuple[int, bytes]:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
    fd = os.open(path, flags)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise NativeIntegrityError("NATIVE_FILE_NOT_REGULAR")
        if info.st_size <= 0 or info.st_size > max_bytes:
            raise NativeIntegrityError("NATIVE_FILE_SIZE_INVALID")
        chunks: list[bytes] = []
        remaining = info.st_size
        while remaining > 0:
            block = os.read(fd, min(remaining, 1048576))
            if not block:
                break
            chunks.append(block)
            remaining -= len(block)
        raw = b"".join(chunks)
        if len(raw) != info.st_size:
            raise NativeIntegrityError("NATIVE_FILE_READ_INCOMPLETE")
        return fd, raw
    except BaseException:
        os.close(fd)
        raise


def _verify_manifest(raw: bytes) -> dict:
    try:
        body = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise NativeIntegrityError("NATIVE_MANIFEST_CORRUPT") from exc
    if not isinstance(body, dict):
        raise NativeIntegrityError("NATIVE_MANIFEST_CORRUPT")
    if body.get("abi_version") != EXPECTED_ABI_VERSION:
        raise NativeIntegrityError("NATIVE_ABI_VERSION_MISMATCH")
    if body.get("binary_name") != "libtradegen_fast.so":
        raise NativeIntegrityError("NATIVE_BINARY_NAME_MISMATCH")
    source_sha = body.get("source_sha256")
    binary_sha = body.get("binary_sha256")
    if not (isinstance(source_sha, str) and _HEX64.fullmatch(source_sha)):
        raise NativeIntegrityError("NATIVE_SOURCE_DIGEST_INVALID")
    if not (isinstance(binary_sha, str) and _HEX64.fullmatch(binary_sha)):
        raise NativeIntegrityError("NATIVE_BINARY_DIGEST_INVALID")
    if source_sha != EXPECTED_SOURCE_SHA256:
        raise NativeIntegrityError("NATIVE_SOURCE_DIGEST_MISMATCH")
    return body


def sealed_image(raw: bytes):
    """Return a sealed Linux file containing exactly raw, or None if unavailable."""
    if not hasattr(os, "memfd_create") or not Path("/proc/self/fd").is_dir():
        return None
    import fcntl

    try:
        fd = os.memfd_create("tradegen-kernel", os.MFD_CLOEXEC | os.MFD_ALLOW_SEALING)
    except OSError:
        return None
    image = os.fdopen(fd, "wb", buffering=0)
    try:
        if image.write(raw) != len(raw):
            raise OSError("incomplete native image")
        # Stable Linux UAPI (linux/fcntl.h); some CPython builds omit the aliases.
        add_seals = getattr(fcntl, "F_ADD_SEALS", 1033)
        seal_all_writes = 0x0008 | 0x0004 | 0x0002 | 0x0001  # WRITE, GROW, SHRINK, SEAL
        fcntl.fcntl(fd, add_seals, seal_all_writes)
        return image
    except OSError:
        image.close()
        return None


def _bind_library(image):
    import ctypes

    class C_I128(ctypes.Structure):
        _fields_ = [("hi", ctypes.c_int64), ("lo", ctypes.c_uint64)]

    class C_FifoLot(ctypes.Structure):
        _fields_ = [
            ("market_idx", ctypes.c_int32),
            ("reserved", ctypes.c_int32),
            ("quantity", C_I128),
            ("cost_krw", C_I128),
        ]

    class C_IntervalEvent(ctypes.Structure):
        _fields_ = [
            ("at_ms", ctypes.c_int64),
            ("kind", ctypes.c_int32),
            ("market_idx", ctypes.c_int32),
            ("quantity", C_I128),
            ("price", C_I128),
            ("fee_krw", C_I128),
        ]

    class C_EquityPoint(ctypes.Structure):
        _fields_ = [("equity_krw", C_I128), ("realized_net_krw", C_I128)]

    class C_FoldOutput(ctypes.Structure):
        _fields_ = [
            ("closing_equity_krw", C_I128),
            ("min_equity_krw", C_I128),
            ("max_equity_krw", C_I128),
            ("realized_net_krw", C_I128),
            ("closing_cash_krw", C_I128),
            ("closing_units", C_I128 * 4),
            ("closing_marks", C_I128 * 4),
        ]

    class C_OrderCheckIn(ctypes.Structure):
        _fields_ = [
            ("quantity", C_I128),
            ("limit_price", C_I128),
            ("quote_krw", C_I128),
            ("lot_size", C_I128),
            ("tick_size", C_I128),
            ("min_quantity", C_I128),
            ("min_notional_krw", C_I128),
            ("require_integer_qty", ctypes.c_int32),
            ("require_exact_notional_fp18", ctypes.c_int32),
        ]

    class C_OrderCheckOut(ctypes.Structure):
        _fields_ = [
            ("code", ctypes.c_int32),
            ("exact_notional_fp18", ctypes.c_int32),
            ("notional_krw", C_I128),
        ]

    class C_BookLevelIn(ctypes.Structure):
        _fields_ = [
            ("has_bid", ctypes.c_int32),
            ("has_bid_size", ctypes.c_int32),
            ("has_ask", ctypes.c_int32),
            ("has_ask_size", ctypes.c_int32),
            ("bid", C_I128),
            ("bid_size", C_I128),
            ("ask", C_I128),
            ("ask_size", C_I128),
        ]

    class C_BookMetricsOut(ctypes.Structure):
        _fields_ = [
            ("valid", ctypes.c_int32),
            ("non_empty_levels", ctypes.c_int32),
            ("has_spread", ctypes.c_int32),
            ("has_imbalance", ctypes.c_int32),
            ("spread", C_I128),
            ("imbalance_num", C_I128),
            ("imbalance_den", C_I128),
        ]

    class C_MomentumCandidate(ctypes.Structure):
        _fields_ = [
            ("coin_id", ctypes.c_int32),
            ("flag_code", ctypes.c_int32),
            ("has_now_price", ctypes.c_int32),
            ("has_lag_price", ctypes.c_int32),
            ("now_price", C_I128),
            ("lag_price", C_I128),
        ]

    class C_CarryBarIn(ctypes.Structure):
        _fields_ = [
            ("bid", C_I128),
            ("ask", C_I128),
            ("mark", C_I128),
            ("observed_us", ctypes.c_int64),
        ]

    class C_CarryDecisionIn(ctypes.Structure):
        _fields_ = [
            ("state", ctypes.c_int32),
            ("reserved", ctypes.c_int32),
            ("target_fraction", C_I128),
            ("decided_us", ctypes.c_int64),
        ]

    class C_CarryFillOut(ctypes.Structure):
        _fields_ = [
            ("bar_index", ctypes.c_int32),
            ("action", ctypes.c_int32),
            ("quantity", C_I128),
            ("price_quote", C_I128),
            ("fee_quote", C_I128),
        ]

    class C_CarrySimOut(ctypes.Structure):
        _fields_ = [
            ("completed_roundtrips", ctypes.c_int32),
            ("rejected_small_orders", ctypes.c_int32),
            ("num_fills", ctypes.c_int32),
            ("num_lots", ctypes.c_int32),
            ("terminal_cash", C_I128),
            ("terminal_units", C_I128),
            ("terminal_basis", C_I128),
            ("realized_net_profit", C_I128),
            ("total_fees", C_I128),
            ("turnover", C_I128),
        ]

    class C_KisTickIn(ctypes.Structure):
        _fields_ = [
            ("observed_us", ctypes.c_int64),
            ("received_us", ctypes.c_int64),
            ("delay_seconds", ctypes.c_int32),
            ("state_code", ctypes.c_int32),
            ("has_size", ctypes.c_int32),
            ("reserved", ctypes.c_int32),
            ("price", C_I128),
            ("size", C_I128),
        ]

    class C_KisMetricsOut(ctypes.Structure):
        _fields_ = [
            ("sample_count", ctypes.c_int32),
            ("has_window_return", ctypes.c_int32),
            ("has_vwap", ctypes.c_int32),
            ("vwap_hi_overflow", ctypes.c_int32),
            ("ret_num", C_I128),
            ("ret_den", C_I128),
            ("vwap_num_words", ctypes.c_uint64 * 4),
            ("vwap_den_fp18", C_I128),
        ]

    class C_OddsSpecIn(ctypes.Structure):
        _fields_ = [
            ("n_paths", ctypes.c_int32),
            ("n_checks", ctypes.c_int32),
            ("moonshot", ctypes.c_int32),
            ("has_bracket", ctypes.c_int32),
            ("sizing_kind", ctypes.c_int32),
            ("fraction_kind", ctypes.c_int32),
            ("has_fstar", ctypes.c_int32),
            ("has_cap_krw", ctypes.c_int32),
            ("has_delist_h", ctypes.c_int32),
            ("book_kind", ctypes.c_int32),
            ("n_ladder_rows", ctypes.c_int32),
            ("record_brackets", ctypes.c_int32),
            ("w0", ctypes.c_double),
            ("target", ctypes.c_double),
            ("floor_val", ctypes.c_double),
            ("daily_loss", ctypes.c_double),
            ("mult", ctypes.c_double),
            ("take_profit", ctypes.c_double),
            ("stop", ctypes.c_double),
            ("fraction_val", ctypes.c_double),
            ("fstar", ctypes.c_double),
            ("cap_krw", ctypes.c_double),
            ("delist_h", ctypes.c_double),
            ("table_bp", ctypes.c_double),
            ("commission_bp", ctypes.c_double),
            ("quote_krw", ctypes.c_double),
            ("lot", ctypes.c_double),
            ("min_krw", ctypes.c_double),
            ("phi_buy", ctypes.c_double),
            ("phi_sell", ctypes.c_double),
            ("carry_mult", ctypes.c_double),
            ("cost_stress", ctypes.c_double),
        ]

    class C_BidGapMcOut(ctypes.Structure):
        _fields_ = [
            ("favorable_prob", ctypes.c_double),
            ("adverse_prob", ctypes.c_double),
            ("mean_net_return", ctypes.c_double),
            ("p05_net_return", ctypes.c_double),
            ("p95_net_return", ctypes.c_double),
        ]

    lib = ctypes.CDLL(f"/proc/self/fd/{image.fileno()}")
    # dlopen caches pathname strings; retain the fd until the handle is released.
    lib._tradegen_image = image

    lib.tg_abi_version.argtypes = []
    lib.tg_abi_version.restype = ctypes.c_uint32
    if int(lib.tg_abi_version()) != EXPECTED_ABI_VERSION:
        raise NativeIntegrityError("NATIVE_ABI_VERSION_MISMATCH")

    lib.tg_fold_continuous_interval.argtypes = [
        ctypes.c_int32,
        ctypes.POINTER(C_I128),
        ctypes.POINTER(C_I128),
        ctypes.POINTER(C_I128),
        ctypes.POINTER(C_I128),
        ctypes.POINTER(C_FifoLot),
        ctypes.c_int32,
        ctypes.POINTER(C_IntervalEvent),
        ctypes.c_int32,
        ctypes.c_int32,
        ctypes.POINTER(C_FoldOutput),
        ctypes.POINTER(C_EquityPoint),
        ctypes.c_int32,
        ctypes.POINTER(C_FifoLot),
        ctypes.c_int32,
        ctypes.POINTER(ctypes.c_int32),
    ]
    lib.tg_fold_continuous_interval.restype = ctypes.c_int32

    lib.tg_check_bid_gap.argtypes = [
        ctypes.POINTER(C_I128),
        ctypes.POINTER(C_I128),
        ctypes.POINTER(C_I128),
        ctypes.c_int32,
        ctypes.c_int32,
        ctypes.POINTER(ctypes.c_int32),
    ]
    lib.tg_check_bid_gap.restype = ctypes.c_int32

    lib.tg_validate_and_size_order.argtypes = [
        ctypes.POINTER(C_OrderCheckIn),
        ctypes.POINTER(C_OrderCheckOut),
    ]
    lib.tg_validate_and_size_order.restype = ctypes.c_int32

    lib.tg_validate_book_levels.argtypes = [
        ctypes.POINTER(C_BookLevelIn),
        ctypes.c_int32,
        ctypes.c_int32,
        ctypes.POINTER(C_BookMetricsOut),
    ]
    lib.tg_validate_book_levels.restype = ctypes.c_int32

    lib.tg_ma_crossover.argtypes = [
        ctypes.POINTER(C_I128),
        ctypes.c_int32,
        ctypes.c_int32,
        ctypes.c_int32,
        ctypes.POINTER(ctypes.c_int32),
    ]
    lib.tg_ma_crossover.restype = ctypes.c_int32

    lib.tg_universe_momentum_top1.argtypes = [
        ctypes.POINTER(C_MomentumCandidate),
        ctypes.c_int32,
        ctypes.c_int32,
        ctypes.c_int32,
        ctypes.c_int32,
        ctypes.c_int32,
        ctypes.POINTER(C_I128),
        ctypes.POINTER(C_I128),
        ctypes.c_int32,
        ctypes.c_int32,
        ctypes.POINTER(C_I128),
        ctypes.POINTER(ctypes.c_int32),
        ctypes.POINTER(ctypes.c_int32),
    ]
    lib.tg_universe_momentum_top1.restype = ctypes.c_int32

    lib.tg_simulate_carry.argtypes = [
        ctypes.POINTER(C_CarryBarIn),
        ctypes.POINTER(C_CarryDecisionIn),
        ctypes.c_int32,
        ctypes.POINTER(C_I128),
        ctypes.POINTER(C_I128),
        ctypes.POINTER(C_I128),
        ctypes.POINTER(C_I128),
        ctypes.POINTER(C_I128),
        ctypes.POINTER(C_I128),
        ctypes.POINTER(C_I128),
        ctypes.c_int64,
        ctypes.c_int32,
        ctypes.c_int32,
        ctypes.POINTER(C_CarrySimOut),
        ctypes.POINTER(ctypes.c_double),
        ctypes.POINTER(C_CarryFillOut),
        ctypes.c_int32,
        ctypes.POINTER(C_FifoLot),
        ctypes.c_int32,
    ]
    lib.tg_simulate_carry.restype = ctypes.c_int32

    lib.tg_kis_parse_caret_fields.argtypes = [
        ctypes.c_char_p,
        ctypes.c_size_t,
        ctypes.c_int32,
        ctypes.c_int32,
        ctypes.POINTER(ctypes.c_int32),
        ctypes.POINTER(ctypes.c_int32),
    ]
    lib.tg_kis_parse_caret_fields.restype = ctypes.c_int32

    lib.tg_kis_window_metrics.argtypes = [
        ctypes.POINTER(C_KisTickIn),
        ctypes.c_int32,
        ctypes.c_int64,
        ctypes.c_int64,
        ctypes.c_int32,
        ctypes.POINTER(C_KisMetricsOut),
    ]
    lib.tg_kis_window_metrics.restype = ctypes.c_int32

    lib.tg_odds_run_paths_f64.argtypes = [
        ctypes.POINTER(C_OddsSpecIn),
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_int64,
        ctypes.POINTER(ctypes.c_int64),
    ]
    lib.tg_odds_run_paths_f64.restype = ctypes.c_int32

    lib.tg_adaptive_bid_gap_mc.argtypes = [
        ctypes.POINTER(ctypes.c_double),
        ctypes.c_int32,
        ctypes.c_int32,
        ctypes.c_int32,
        ctypes.c_int32,
        ctypes.c_double,
        ctypes.c_uint64,
        ctypes.POINTER(C_BidGapMcOut),
    ]
    lib.tg_adaptive_bid_gap_mc.restype = ctypes.c_int32

    return {
        "ctypes": ctypes,
        "lib": lib,
        "I128": C_I128,
        "FifoLot": C_FifoLot,
        "IntervalEvent": C_IntervalEvent,
        "EquityPoint": C_EquityPoint,
        "FoldOutput": C_FoldOutput,
        "OrderCheckIn": C_OrderCheckIn,
        "OrderCheckOut": C_OrderCheckOut,
        "BookLevelIn": C_BookLevelIn,
        "BookMetricsOut": C_BookMetricsOut,
        "MomentumCandidate": C_MomentumCandidate,
        "CarryBarIn": C_CarryBarIn,
        "CarryDecisionIn": C_CarryDecisionIn,
        "CarryFillOut": C_CarryFillOut,
        "CarrySimOut": C_CarrySimOut,
        "KisTickIn": C_KisTickIn,
        "KisMetricsOut": C_KisMetricsOut,
        "OddsSpecIn": C_OddsSpecIn,
        "BidGapMcOut": C_BidGapMcOut,
    }


def clear_native_cache() -> None:
    """Clear cached native library handles so subsequent calls re-verify disk artifacts."""
    with _LOCK:
        _CACHE.clear()


def get_native_handle(*, build_dir: Path | None = None) -> dict | None:
    """Return verified native handle dict, None if disabled/absent, or raise NativeIntegrityError on tamper."""
    if is_native_disabled():
        return None
    if build_dir is None:
        cached_default = _CACHE.get(("<default>", ""))
        if cached_default is not None:
            return cached_default  # type: ignore[return-value]
    directory = DEFAULT_BUILD_DIR if build_dir is None else Path(build_dir)
    manifest_path = directory / "build_manifest.json"
    so_path = directory / "libtradegen_fast.so"
    if build_dir is None and (not manifest_path.exists() or not so_path.exists()):
        return None
    if not manifest_path.exists() or not so_path.exists():
        raise NativeIntegrityError("NATIVE_ARTIFACTS_MISSING")

    m_fd, m_raw = _read_regular_fd(manifest_path, _MAX_MANIFEST_BYTES)
    os.close(m_fd)
    manifest = _verify_manifest(m_raw)

    so_fd, so_raw = _read_regular_fd(so_path, _MAX_SO_BYTES)
    try:
        actual_sha = hashlib.sha256(so_raw).hexdigest()
        if actual_sha != manifest["binary_sha256"]:
            raise NativeIntegrityError("NATIVE_BINARY_DIGEST_MISMATCH")
        if actual_sha != EXPECTED_BINARY_SHA256:
            return None
        key = (str(directory.resolve()), actual_sha)
        with _LOCK:
            cached = _CACHE.get(key)
            if cached is not None:
                if build_dir is None:
                    _CACHE[("<default>", "")] = cached
                return cached  # type: ignore[return-value]
            image = sealed_image(so_raw)
            if image is None:
                return None
            try:
                bound = _bind_library(image)
            except OSError:
                image.close()
                return None
            except BaseException:
                image.close()
                raise
            _CACHE[key] = bound
            if build_dir is None:
                _CACHE[("<default>", "")] = bound
            return bound
    finally:
        os.close(so_fd)


def check_bid_gap(
    best_bid: Decimal | None,
    mark_price: Decimal,
    bid_gap_y: Decimal | None,
    *,
    build_dir: Path | None = None,
) -> bool | None:
    """HP-2: Exact u256 BR-10 bid-gap check; returns bool, or None if fallback required."""
    handle = get_native_handle(build_dir=build_dir)
    if handle is None:
        return None
    m_fp = decimal_to_fp18(mark_price)
    if m_fp is None:
        return None
    I128 = handle["I128"]
    ctypes_mod = handle["ctypes"]
    c_mark = I128(*m_fp)
    has_bid = 1 if best_bid is not None else 0
    has_y = 1 if bid_gap_y is not None else 0
    c_bid = I128(0, 0)
    c_y = I128(0, 0)
    if has_bid:
        b_fp = decimal_to_fp18(best_bid)
        if b_fp is None:
            return None
        c_bid = I128(*b_fp)
    if has_y:
        y_fp = decimal_to_fp18(bid_gap_y)
        if y_fp is None:
            return None
        c_y = I128(*y_fp)
    triggered = ctypes_mod.c_int32(0)
    rc = handle["lib"].tg_check_bid_gap(
        ctypes_mod.byref(c_bid),
        ctypes_mod.byref(c_mark),
        ctypes_mod.byref(c_y),
        has_bid,
        has_y,
        ctypes_mod.byref(triggered),
    )
    if rc != TG_OK:
        return None
    return bool(triggered.value)


def validate_and_size_order(
    *,
    quantity: Decimal,
    limit_price: Decimal,
    quote_krw: Decimal,
    lot_size: Decimal,
    tick_size: Decimal,
    min_quantity: Decimal,
    min_notional_krw: Decimal,
    require_integer_qty: bool = False,
    build_dir: Path | None = None,
) -> int | None:
    """HP-4: Exact u256/u384 lot/tick/notional check; returns TG_ORDER_* code or None for fallback."""
    handle = get_native_handle(build_dir=build_dir)
    if handle is None:
        return None
    converted = [
        decimal_to_fp18(v)
        for v in (quantity, limit_price, quote_krw, lot_size, tick_size, min_quantity, min_notional_krw)
    ]
    if any(item is None for item in converted):
        return None
    I128 = handle["I128"]
    ctypes_mod = handle["ctypes"]
    inp = handle["OrderCheckIn"](
        quantity=I128(*converted[0]),
        limit_price=I128(*converted[1]),
        quote_krw=I128(*converted[2]),
        lot_size=I128(*converted[3]),
        tick_size=I128(*converted[4]),
        min_quantity=I128(*converted[5]),
        min_notional_krw=I128(*converted[6]),
        require_integer_qty=1 if require_integer_qty else 0,
        require_exact_notional_fp18=0,
    )
    out = handle["OrderCheckOut"]()
    rc = handle["lib"].tg_validate_and_size_order(ctypes_mod.byref(inp), ctypes_mod.byref(out))
    if rc != TG_OK:
        return None
    return int(out.code)


def validate_book_levels(
    raw_levels: tuple[tuple[Decimal | None, Decimal | None, Decimal | None, Decimal | None], ...],
    *,
    allow_crossed: bool = False,
    build_dir: Path | None = None,
) -> dict | None:
    """HP-4: Validate up to 64 book levels and return spread/imbalance rationals, or None for fallback."""
    handle = get_native_handle(build_dir=build_dir)
    if handle is None or len(raw_levels) > 64:
        return None
    I128 = handle["I128"]
    BookLevelIn = handle["BookLevelIn"]
    ctypes_mod = handle["ctypes"]
    n = len(raw_levels)
    arr = (BookLevelIn * n)()
    for idx, (bid, bsz, ask, asz) in enumerate(raw_levels):
        hb = int(bid is not None)
        hbs = int(bsz is not None)
        ha = int(ask is not None)
        has = int(asz is not None)
        bfp = decimal_to_fp18(bid) if hb else (0, 0)
        bsfp = decimal_to_fp18(bsz) if hbs else (0, 0)
        afp = decimal_to_fp18(ask) if ha else (0, 0)
        asfp = decimal_to_fp18(asz) if has else (0, 0)
        if None in (bfp, bsfp, afp, asfp):
            return None
        arr[idx] = BookLevelIn(
            has_bid=hb,
            has_bid_size=hbs,
            has_ask=ha,
            has_ask_size=has,
            bid=I128(*bfp),
            bid_size=I128(*bsfp),
            ask=I128(*afp),
            ask_size=I128(*asfp),
        )
    out = handle["BookMetricsOut"]()
    rc = handle["lib"].tg_validate_book_levels(arr, n, 1 if allow_crossed else 0, ctypes_mod.byref(out))
    if rc != TG_OK:
        return None
    return {
        "valid": bool(out.valid),
        "non_empty_levels": int(out.non_empty_levels),
        "spread": fp18_to_decimal(out.spread.hi, out.spread.lo) if out.has_spread else None,
        "imbalance_num": fp18_to_int(out.imbalance_num.hi, out.imbalance_num.lo) if out.has_imbalance else None,
        "imbalance_den": fp18_to_int(out.imbalance_den.hi, out.imbalance_den.lo) if out.has_imbalance else None,
    }


def fold_continuous_interval(
    *,
    num_markets: int,
    opening_cash_krw: Decimal,
    opening_units: tuple[Decimal, ...],
    opening_marks: tuple[Decimal, ...],
    opening_realized_krw: Decimal,
    opening_lots: tuple[tuple[int, Decimal, Decimal], ...],
    events: tuple[tuple[int, int, int, Decimal, Decimal, Decimal], ...],
    conservative_ms: bool = False,
    need_points: bool = True,
    build_dir: Path | None = None,
) -> dict | None:
    """HP-1: Multi-coin continuous equity fold + exact 1e-18 FIFO lot cost reducer."""
    handle = get_native_handle(build_dir=build_dir)
    if handle is None or not (1 <= num_markets <= 4):
        return None
    cash_fp = decimal_to_fp18(opening_cash_krw)
    real_fp = decimal_to_fp18(opening_realized_krw)
    if cash_fp is None or real_fp is None:
        return None
    I128 = handle["I128"]
    FifoLot = handle["FifoLot"]
    IntervalEvent = handle["IntervalEvent"]
    EquityPoint = handle["EquityPoint"]
    ctypes_mod = handle["ctypes"]

    c_units = (I128 * num_markets)()
    c_marks = (I128 * num_markets)()
    for m in range(num_markets):
        ufp = decimal_to_fp18(opening_units[m])
        mfp = decimal_to_fp18(opening_marks[m])
        if ufp is None or mfp is None:
            return None
        c_units[m] = I128(*ufp)
        c_marks[m] = I128(*mfp)

    n_lots = len(opening_lots)
    c_lots = (FifoLot * max(1, n_lots))()
    for i, (m_idx, lq, lc) in enumerate(opening_lots):
        qfp = decimal_to_fp18(lq)
        cfp = decimal_to_fp18(lc)
        if qfp is None or cfp is None:
            return None
        c_lots[i] = FifoLot(market_idx=m_idx, reserved=0, quantity=I128(*qfp), cost_krw=I128(*cfp))

    n_ev = len(events)
    c_events = (IntervalEvent * max(1, n_ev))()
    price_cache: dict[Decimal, tuple[int, int] | None] = {}
    for i, (at_ms, kind, m_idx, eqty, eprice, efee) in enumerate(events):
        pfp = price_cache.get(eprice)
        if pfp is None and eprice not in price_cache:
            pfp = decimal_to_fp18(eprice)
            price_cache[eprice] = pfp
        if pfp is None:
            return None
        slot = c_events[i]
        slot.at_ms = int(at_ms)
        slot.kind = int(kind)
        slot.market_idx = int(m_idx)
        slot.price.hi, slot.price.lo = pfp
        if kind != TG_EVENT_MARK:
            qfp = decimal_to_fp18(eqty)
            ffp = decimal_to_fp18(efee)
            if qfp is None or ffp is None:
                return None
            slot.quantity.hi, slot.quantity.lo = qfp
            slot.fee_krw.hi, slot.fee_krw.lo = ffp

    max_pts = (n_ev + 2) if need_points else 0
    c_points = (EquityPoint * max(1, max_pts))() if need_points else None
    max_out_lots = n_lots + sum(1 for ev in events if ev[1] == TG_EVENT_BUY) + 1
    c_out_lots = (FifoLot * max_out_lots)()
    out_num_lots = ctypes_mod.c_int32(0)
    summary = handle["FoldOutput"]()

    c_cash = I128(*cash_fp)
    c_real = I128(*real_fp)
    rc = handle["lib"].tg_fold_continuous_interval(
        num_markets,
        ctypes_mod.byref(c_cash),
        c_units,
        c_marks,
        ctypes_mod.byref(c_real),
        c_lots if n_lots > 0 else None,
        n_lots,
        c_events if n_ev > 0 else None,
        n_ev,
        1 if conservative_ms else 0,
        ctypes_mod.byref(summary),
        c_points if need_points else None,
        max_pts,
        c_out_lots,
        max_out_lots,
        ctypes_mod.byref(out_num_lots),
    )
    if rc == TG_FALLBACK_PRECISION:
        return None
    if rc != TG_OK:
        return {"status": rc}

    pts = ()
    if need_points:
        dec_cache: dict[tuple[int, int], Decimal] = {}
        pts_list = []
        for i in range(n_ev + 2):
            cp = c_points[i]
            ek = (cp.equity_krw.hi, cp.equity_krw.lo)
            rk = (cp.realized_net_krw.hi, cp.realized_net_krw.lo)
            ev_dec = dec_cache.get(ek)
            if ev_dec is None:
                ev_dec = fp18_to_decimal(*ek)
                dec_cache[ek] = ev_dec
            rv_dec = dec_cache.get(rk)
            if rv_dec is None:
                rv_dec = fp18_to_decimal(*rk)
                dec_cache[rk] = rv_dec
            pts_list.append((ev_dec, rv_dec))
        pts = tuple(pts_list)
    rem_lots = tuple(
        (
            int(c_out_lots[i].market_idx),
            fp18_to_decimal(c_out_lots[i].quantity.hi, c_out_lots[i].quantity.lo),
            fp18_to_decimal(c_out_lots[i].cost_krw.hi, c_out_lots[i].cost_krw.lo),
        )
        for i in range(out_num_lots.value)
    )
    return {
        "status": TG_OK,
        "closing_equity_krw": fp18_to_decimal(summary.closing_equity_krw.hi, summary.closing_equity_krw.lo),
        "min_equity_krw": fp18_to_decimal(summary.min_equity_krw.hi, summary.min_equity_krw.lo),
        "max_equity_krw": fp18_to_decimal(summary.max_equity_krw.hi, summary.max_equity_krw.lo),
        "realized_net_krw": fp18_to_decimal(summary.realized_net_krw.hi, summary.realized_net_krw.lo),
        "closing_cash_krw": fp18_to_decimal(summary.closing_cash_krw.hi, summary.closing_cash_krw.lo),
        "closing_units": tuple(
            fp18_to_decimal(summary.closing_units[m].hi, summary.closing_units[m].lo) for m in range(num_markets)
        ),
        "closing_marks": tuple(
            fp18_to_decimal(summary.closing_marks[m].hi, summary.closing_marks[m].lo) for m in range(num_markets)
        ),
        "points": pts,
        "lots": rem_lots,
    }


def ma_crossover(
    marks: tuple[Decimal, ...],
    fast_window: int,
    slow_window: int,
    *,
    build_dir: Path | None = None,
) -> bool | None:
    """HP-3: Exact u256/u384 moving-average crossover check."""
    handle = get_native_handle(build_dir=build_dir)
    if handle is None:
        return None
    n = len(marks)
    if n < slow_window:
        return False
    I128 = handle["I128"]
    ctypes_mod = handle["ctypes"]
    # Only the last slow_window marks participate in fast and slow sums
    tail = marks[-slow_window:]
    arr = (I128 * slow_window)()
    cache: dict[Decimal, tuple[int, int] | None] = {}
    for i, val in enumerate(tail):
        fp = cache.get(val)
        if fp is None and val not in cache:
            fp = decimal_to_fp18(val)
            cache[val] = fp
        if fp is None:
            return None
        slot = arr[i]
        slot.hi, slot.lo = fp
    out_above = ctypes_mod.c_int32(0)
    rc = handle["lib"].tg_ma_crossover(arr, slow_window, fast_window, slow_window, ctypes_mod.byref(out_above))
    if rc != TG_OK:
        return None
    return bool(out_above.value)


def universe_momentum_top1(
    *,
    candidates: list[tuple[int, int, Decimal | None, Decimal | None]],
    held_coin_id: int,
    held_flag_code: int,
    held_now_price: Decimal | None,
    held_lag_price: Decimal | None,
    hold_count: int,
    min_hold_slots: int,
    switch_margin: Decimal,
    build_dir: Path | None = None,
) -> tuple[int, int] | None:
    """HP-3: Exact u256/u384 top-1 momentum chooser."""
    handle = get_native_handle(build_dir=build_dir)
    if handle is None:
        return None
    sm_fp = decimal_to_fp18(switch_margin)
    if sm_fp is None:
        return None
    I128 = handle["I128"]
    Cand = handle["MomentumCandidate"]
    ctypes_mod = handle["ctypes"]
    n = len(candidates)
    arr = (Cand * max(1, n))()
    for i, (cid, fcode, p_now, p_lag) in enumerate(candidates):
        hn = int(p_now is not None)
        hl = int(p_lag is not None)
        nfp = decimal_to_fp18(p_now) if hn else (0, 0)
        lfp = decimal_to_fp18(p_lag) if hl else (0, 0)
        if nfp is None or lfp is None:
            return None
        arr[i] = Cand(
            coin_id=cid,
            flag_code=fcode,
            has_now_price=hn,
            has_lag_price=hl,
            now_price=I128(*nfp),
            lag_price=I128(*lfp),
        )
    h_hn = int(held_now_price is not None)
    h_hl = int(held_lag_price is not None)
    hn_fp = decimal_to_fp18(held_now_price) if h_hn else (0, 0)
    hl_fp = decimal_to_fp18(held_lag_price) if h_hl else (0, 0)
    if hn_fp is None or hl_fp is None:
        return None
    c_hn = I128(*hn_fp)
    c_hl = I128(*hl_fp)
    c_sm = I128(*sm_fp)
    out_id = ctypes_mod.c_int32(-1)
    out_cnt = ctypes_mod.c_int32(0)
    rc = handle["lib"].tg_universe_momentum_top1(
        arr if n > 0 else None,
        n,
        held_coin_id,
        held_flag_code,
        h_hn,
        h_hl,
        ctypes_mod.byref(c_hn),
        ctypes_mod.byref(c_hl),
        hold_count,
        min_hold_slots,
        ctypes_mod.byref(c_sm),
        ctypes_mod.byref(out_id),
        ctypes_mod.byref(out_cnt),
    )
    if rc != TG_OK:
        return None
    return int(out_id.value), int(out_cnt.value)


def simulate_carry_fast(
    *,
    bars_data: list[tuple[Decimal, Decimal, Decimal, int]],
    decisions_data: list[tuple[int, Decimal, int]],
    initial_cash: Decimal,
    fee_fraction: Decimal,
    slip_fraction: Decimal,
    lot_size: Decimal,
    tick_size: Decimal,
    min_qty: Decimal,
    min_notional: Decimal,
    deadline_us: int,
    lag: int,
    buy_hold: bool,
    build_dir: Path | None = None,
) -> dict | None:
    """HP-3: Fast 20,000-bar exact fp18 carry simulation; returns None on sub-1e-18 fallback."""
    handle = get_native_handle(build_dir=build_dir)
    if handle is None:
        return None
    scalars = [
        decimal_to_fp18(v)
        for v in (initial_cash, fee_fraction, slip_fraction, lot_size, tick_size, min_qty, min_notional)
    ]
    if any(s is None for s in scalars):
        return None
    I128 = handle["I128"]
    BarIn = handle["CarryBarIn"]
    DecIn = handle["CarryDecisionIn"]
    FillOut = handle["CarryFillOut"]
    FifoLot = handle["FifoLot"]
    ctypes_mod = handle["ctypes"]

    n = len(bars_data)
    c_bars = (BarIn * n)()
    px_cache: dict[Decimal, tuple[int, int] | None] = {}
    for i, (b, a, m, obs_us) in enumerate(bars_data):
        bfp = px_cache.get(b)
        if bfp is None and b not in px_cache:
            bfp = decimal_to_fp18(b)
            px_cache[b] = bfp
        afp = px_cache.get(a)
        if afp is None and a not in px_cache:
            afp = decimal_to_fp18(a)
            px_cache[a] = afp
        mfp = px_cache.get(m)
        if mfp is None and m not in px_cache:
            mfp = decimal_to_fp18(m)
            px_cache[m] = mfp
        if None in (bfp, afp, mfp):
            return None
        sb = c_bars[i]
        sb.bid.hi, sb.bid.lo = bfp
        sb.ask.hi, sb.ask.lo = afp
        sb.mark.hi, sb.mark.lo = mfp
        sb.observed_us = obs_us

    c_decs = (DecIn * n)()
    for i, (st_code, tf, dec_us) in enumerate(decisions_data):
        sd = c_decs[i]
        sd.state = st_code
        sd.decided_us = dec_us
        if tf:
            tfp = px_cache.get(tf)
            if tfp is None and tf not in px_cache:
                tfp = decimal_to_fp18(tf)
                px_cache[tf] = tfp
            if tfp is None:
                return None
            sd.target_fraction.hi, sd.target_fraction.lo = tfp

    c_scalars = [I128(*s) for s in scalars]
    summary = handle["CarrySimOut"]()
    c_rets = (ctypes_mod.c_double * (n - 1))()
    c_fills = (FillOut * n)()
    c_lots = (FifoLot * n)()

    rc = handle["lib"].tg_simulate_carry(
        c_bars,
        c_decs,
        n,
        ctypes_mod.byref(c_scalars[0]),
        ctypes_mod.byref(c_scalars[1]),
        ctypes_mod.byref(c_scalars[2]),
        ctypes_mod.byref(c_scalars[3]),
        ctypes_mod.byref(c_scalars[4]),
        ctypes_mod.byref(c_scalars[5]),
        ctypes_mod.byref(c_scalars[6]),
        int(deadline_us),
        int(lag),
        1 if buy_hold else 0,
        ctypes_mod.byref(summary),
        c_rets,
        c_fills,
        n,
        c_lots,
        n,
    )
    if rc != TG_OK:
        return None

    fills = tuple(
        (
            int(c_fills[i].bar_index),
            "entry" if c_fills[i].action == 1 else "exit",
            fp18_to_decimal(c_fills[i].quantity.hi, c_fills[i].quantity.lo),
            fp18_to_decimal(c_fills[i].price_quote.hi, c_fills[i].price_quote.lo),
            fp18_to_decimal(c_fills[i].fee_quote.hi, c_fills[i].fee_quote.lo),
        )
        for i in range(summary.num_fills)
    )
    lots = tuple(
        (
            fp18_to_decimal(c_lots[i].quantity.hi, c_lots[i].quantity.lo),
            fp18_to_decimal(c_lots[i].cost_krw.hi, c_lots[i].cost_krw.lo),
        )
        for i in range(summary.num_lots)
    )
    return {
        "completed_roundtrips": int(summary.completed_roundtrips),
        "rejected_small_orders": int(summary.rejected_small_orders),
        "terminal_cash": fp18_to_decimal(summary.terminal_cash.hi, summary.terminal_cash.lo),
        "terminal_units": fp18_to_decimal(summary.terminal_units.hi, summary.terminal_units.lo),
        "terminal_basis": fp18_to_decimal(summary.terminal_basis.hi, summary.terminal_basis.lo),
        "realized_net_profit": fp18_to_decimal(summary.realized_net_profit.hi, summary.realized_net_profit.lo),
        "total_fees": fp18_to_decimal(summary.total_fees.hi, summary.total_fees.lo),
        "turnover": fp18_to_decimal(summary.turnover.hi, summary.turnover.lo),
        "net_returns": tuple(float(c_rets[i]) for i in range(n - 1)),
        "fills": fills,
        "lots": lots,
    }


def kis_parse_caret_fields(
    payload_bytes: bytes,
    expected_fields: int,
    max_field_len: int = 128,
    *,
    build_dir: Path | None = None,
) -> tuple[str, ...] | bool | None:
    """HP-5: Fast C++20 '^'-delimited payload scanner; returns tuple of UTF-8 fields, False if invalid, or None."""
    handle = get_native_handle(build_dir=build_dir)
    if handle is None:
        return None
    if expected_fields < 1 or len(payload_bytes) > (1 << 20):
        return False
    ctypes_mod = handle["ctypes"]
    offsets = (ctypes_mod.c_int32 * expected_fields)()
    lengths = (ctypes_mod.c_int32 * expected_fields)()
    rc = handle["lib"].tg_kis_parse_caret_fields(
        payload_bytes,
        len(payload_bytes),
        expected_fields,
        max_field_len,
        offsets,
        lengths,
    )
    if rc != TG_OK:
        return False
    return tuple(
        payload_bytes[offsets[i] : offsets[i] + lengths[i]].decode("utf-8")
        for i in range(expected_fields)
    )


def kis_window_metrics(
    ticks_data: list[tuple[int, int, int, int, Decimal, Decimal | None]],
    *,
    now_us: int,
    window_us: int,
    trade_fresh: bool,
    build_dir: Path | None = None,
) -> dict | None:
    """HP-5: Sliding-window return and VWAP rational numerator/denominator reducer."""
    handle = get_native_handle(build_dir=build_dir)
    if handle is None or len(ticks_data) > 10000:
        return None
    I128 = handle["I128"]
    TickIn = handle["KisTickIn"]
    ctypes_mod = handle["ctypes"]
    n = len(ticks_data)
    arr = (TickIn * max(1, n))()
    for i, (obs_us, rec_us, delay_s, scode, price, size) in enumerate(ticks_data):
        pfp = decimal_to_fp18(price)
        if pfp is None:
            return None
        hs = int(size is not None)
        sfp = decimal_to_fp18(size) if hs else (0, 0)
        if sfp is None:
            return None
        arr[i] = TickIn(
            observed_us=obs_us,
            received_us=rec_us,
            delay_seconds=delay_s,
            state_code=scode,
            has_size=hs,
            reserved=0,
            price=I128(*pfp),
            size=I128(*sfp),
        )
    out = handle["KisMetricsOut"]()
    rc = handle["lib"].tg_kis_window_metrics(
        arr if n > 0 else None,
        n,
        int(now_us),
        int(window_us),
        1 if trade_fresh else 0,
        ctypes_mod.byref(out),
    )
    if rc != TG_OK:
        return None
    vwap_num = None
    vwap_den = None
    if out.has_vwap:
        w = out.vwap_num_words
        vwap_num = int(w[0]) | (int(w[1]) << 64) | (int(w[2]) << 128) | (int(w[3]) << 192)
        vwap_den = fp18_to_int(out.vwap_den_fp18.hi, out.vwap_den_fp18.lo) * _SCALE_INT
    return {
        "sample_count": int(out.sample_count),
        "ret_num": fp18_to_int(out.ret_num.hi, out.ret_num.lo) if out.has_window_return else None,
        "ret_den": fp18_to_int(out.ret_den.hi, out.ret_den.lo) if out.has_window_return else None,
        "vwap_num": vwap_num,
        "vwap_den": vwap_den,
    }


def odds_run_paths_f64(
    spec_fields: dict,
    pointers: dict[str, int],
    max_brackets: int,
    *,
    build_dir: Path | None = None,
) -> tuple[int, int] | None:
    """HP-6a: 0-ULP IEEE-754 f64 path state machine; returns (status_code, num_brackets) or None."""
    handle = get_native_handle(build_dir=build_dir)
    if handle is None:
        return None
    ctypes_mod = handle["ctypes"]
    c_spec = handle["OddsSpecIn"](**spec_fields)
    out_num_br = ctypes_mod.c_int64(0)
    rc = handle["lib"].tg_odds_run_paths_f64(
        ctypes_mod.byref(c_spec),
        pointers["ladder_starts"],
        pointers["ladder_steps"],
        pointers["check_close"],
        pointers["check_new_seoul_day"],
        pointers["check_banded"],
        pointers["check_can_enter_date"],
        pointers["check_force_exit_date"],
        pointers["check_sell_tax_bp"],
        pointers["prices"],
        pointers["d_edges"],
        pointers["u_edges"],
        pointers["out_p"],
        pointers["out_v"],
        pointers["out_cost"],
        pointers["out_x"],
        pointers["out_outcome"],
        pointers["out_fp"],
        pointers["out_entered"],
        pointers["out_entries"],
        pointers["out_wins"],
        pointers["out_losses"],
        pointers["out_unresolved"],
        pointers["out_gap"],
        pointers["out_cash_min"],
        pointers["out_locked"],
        pointers["out_edge"],
        pointers["out_carried"],
        pointers["out_stake"],
        pointers["out_br_r"],
        pointers["out_br_d"],
        int(max_brackets),
        ctypes_mod.byref(out_num_br),
    )
    if rc == TG_FALLBACK_PRECISION:
        return None
    return int(rc), int(out_num_br.value)


def adaptive_bid_gap_mc(
    returns: tuple[float, ...] | list[float],
    *,
    n_paths: int,
    horizon: int,
    block_len: int,
    cost_hurdle: float,
    seed: int,
    build_dir: Path | None = None,
) -> dict | None:
    """HP-6b: Moving-block bootstrap Monte Carlo kernel for BR-26 directional calibration."""
    handle = get_native_handle(build_dir=build_dir)
    if handle is None:
        return None
    n_obs = len(returns)
    if n_obs < 2:
        return None
    ctypes_mod = handle["ctypes"]
    c_rets = (ctypes_mod.c_double * n_obs)(*returns)
    out = handle["BidGapMcOut"]()
    rc = handle["lib"].tg_adaptive_bid_gap_mc(
        c_rets,
        int(n_obs),
        int(n_paths),
        int(horizon),
        int(block_len),
        float(cost_hurdle),
        int(seed) & _MASK64,
        ctypes_mod.byref(out),
    )
    if rc != TG_OK:
        return None
    return {
        "favorable_prob": float(out.favorable_prob),
        "adverse_prob": float(out.adverse_prob),
        "mean_net_return": float(out.mean_net_return),
        "p05_net_return": float(out.p05_net_return),
        "p95_net_return": float(out.p95_net_return),
    }
