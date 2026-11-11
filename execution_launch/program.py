"""Explicit deterministic paper candidates; no fitted edge or deployment approval.

The decision function consumes only supplied historical marks. Source artifacts
and parameters are bound with the same digest shape as the existing runner;
matching that digest does not authenticate a callback or its source.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from fractions import Fraction
import hashlib
import json
import re

from execution_control.capability import digest

_ID = re.compile(r"[A-Za-z][A-Za-z0-9_.:-]{0,95}")
_DECIMAL = re.compile(r"(?:0|[1-9][0-9]*)(?:\.[0-9]+)?")
_SHA = re.compile(r"[0-9a-f]{64}")
MAX_PROGRAM_BYTES = 16384
MAX_MARKS = 20000
_UNIVERSE = "universe_top1_momentum"  # program schema v2 (spec section 14)
_UNIVERSE_FIELDS = ("lookback_slots", "min_hold_slots", "switch_margin", "max_candidates", "universe_rule_sha256")
_V1_KEYS = frozenset({"schema_version", "strategy_id", "kind", "fast_window", "slow_window", "exposure_fraction"})
_OMIT = {"omit_none": True}  # strategy._plain drops it while None; parse_program takes v1 keys or v1 plus all five


class ProgramError(ValueError):
    """Fixed reason codes only."""


def _require(condition, code):
    if not condition:
        raise ProgramError(code)


@dataclass(frozen=True, kw_only=True)
class ProgramSpec:
    schema_version: int
    strategy_id: str
    kind: str
    fast_window: int
    slow_window: int
    exposure_fraction: Decimal
    # universe_top1_momentum only (schema 2): L, m, margin, N and the signed rule. None for every other kind.
    lookback_slots: int | None = field(default=None, metadata=_OMIT)
    min_hold_slots: int | None = field(default=None, metadata=_OMIT)
    switch_margin: Decimal | None = field(default=None, metadata=_OMIT)
    max_candidates: int | None = field(default=None, metadata=_OMIT)
    universe_rule_sha256: str | None = field(default=None, metadata=_OMIT)


def _decimal(value, *, positive=False):
    _require(type(value) is Decimal and value.is_finite(), "PROGRAM_DECIMAL_REQUIRED")
    _require(len(value.as_tuple().digits) <= 40 and abs(value.as_tuple().exponent) <= 30,
             "PROGRAM_DECIMAL_RANGE")
    _require(value > 0 if positive else value >= 0, "PROGRAM_AMOUNT_INVALID")


def _validate(spec):
    universe = type(spec) is ProgramSpec and spec.kind == _UNIVERSE
    _require(type(spec) is ProgramSpec and type(spec.schema_version) is int
             and spec.schema_version == (2 if universe else 1), "PROGRAM_SCHEMA_INVALID")
    _require(type(spec.strategy_id) is str and _ID.fullmatch(spec.strategy_id) is not None,
             "PROGRAM_ID_INVALID")
    _require(type(spec.kind) is str, "PROGRAM_KIND_UNSUPPORTED")
    _require(type(spec.fast_window) is int and type(spec.slow_window) is int,
             "PROGRAM_WINDOW_INVALID")
    _decimal(spec.exposure_fraction)
    if universe:
        # L, m and N count slots, decisions and coins; 4096 is the moving-average window bound below.
        _require(spec.fast_window == spec.slow_window == 0
                 and all(type(value) is int and 1 <= value <= 4096
                         for value in (spec.lookback_slots, spec.min_hold_slots, spec.max_candidates))
                 and type(spec.universe_rule_sha256) is str
                 and _SHA.fullmatch(spec.universe_rule_sha256) is not None,
                 "PROGRAM_UNIVERSE_PARAMETERS_INVALID")
        _decimal(spec.switch_margin)
        _require(0 < spec.exposure_fraction <= 1, "PROGRAM_EXPOSURE_INVALID")
        return
    _require(all(getattr(spec, name) is None for name in _UNIVERSE_FIELDS),
             "PROGRAM_UNIVERSE_PARAMETERS_INVALID")
    if spec.kind == "cash":
        _require(spec.fast_window == spec.slow_window == 0 and spec.exposure_fraction == 0,
                 "PROGRAM_CASH_PARAMETERS_INVALID")
    elif spec.kind == "moving_average_trend":
        _require(1 <= spec.fast_window < spec.slow_window <= 4096,
                 "PROGRAM_WINDOW_INVALID")
        _require(0 < spec.exposure_fraction <= 1, "PROGRAM_EXPOSURE_INVALID")
    else:
        raise ProgramError("PROGRAM_KIND_UNSUPPORTED")


def _text(value):
    text = format(value, "f")
    text = (text.rstrip("0").rstrip(".") if "." in text else text)
    return text if value else "0"


def _body(spec):
    _validate(spec)
    body = {"schema_version": spec.schema_version, "strategy_id": spec.strategy_id,
            "kind": spec.kind, "fast_window": spec.fast_window, "slow_window": spec.slow_window,
            "exposure_fraction": _text(spec.exposure_fraction)}
    if spec.kind == _UNIVERSE:
        body |= {"lookback_slots": spec.lookback_slots, "min_hold_slots": spec.min_hold_slots,
                 "switch_margin": _text(spec.switch_margin), "max_candidates": spec.max_candidates,
                 "universe_rule_sha256": spec.universe_rule_sha256}
    return body


def parameters_json(spec: ProgramSpec) -> str:
    """Canonical parameter string suitable for a reviewed StrategyDriver."""
    return json.dumps(_body(spec), sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def program_json(spec: ProgramSpec) -> str:
    return json.dumps(_body(spec), sort_keys=True, indent=2)+"\n"


def program_digest(spec: ProgramSpec, artifact: bytes) -> str:
    """Bind explicit reviewed source/package bytes and exact program parameters.

    The caller supplies the real artifact. This function does not inspect source
    files or establish that another callback implements those bytes.
    """
    _require(type(artifact) is bytes and 0 < len(artifact) <= 1048576,
             "PROGRAM_ARTIFACT_INVALID")
    return digest({"artifact_sha256": hashlib.sha256(artifact).hexdigest(), "parameters": _body(spec)})


def parse_program(raw: str | bytes) -> ProgramSpec:
    _require(type(raw) in (str, bytes) and len(raw) <= MAX_PROGRAM_BYTES, "PROGRAM_JSON_SIZE_OR_TYPE")
    def unique(pairs):
        result = {}
        for key, value in pairs:
            _require(key not in result, "PROGRAM_JSON_DUPLICATE_KEY")
            result[key] = value
        return result
    def invalid(value):
        raise ProgramError("PROGRAM_JSON_NUMBER_INVALID")
    try:
        body = json.loads(raw, object_pairs_hook=unique, parse_float=invalid, parse_constant=invalid)
        # Schema 1 keys, or schema 1 keys plus every universe key (spec section 10: old set, or old plus new).
        _require(type(body) is dict and set(body) in (_V1_KEYS, _V1_KEYS | set(_UNIVERSE_FIELDS)),
                 "PROGRAM_JSON_SCHEMA_INVALID")
        decimals = {}
        for key in ("exposure_fraction", "switch_margin"):
            if key in body:
                value = body[key]
                _require(type(value) is str and len(value) <= 72 and _DECIMAL.fullmatch(value) is not None,
                         "PROGRAM_DECIMAL_STRING_REQUIRED")
                decimals[key] = Decimal(value)
        spec = ProgramSpec(**(body | decimals))
        _validate(spec)
        return spec
    except ProgramError:
        raise
    except (ValueError, TypeError, UnicodeError, RecursionError, ArithmeticError):
        raise ProgramError("PROGRAM_JSON_INVALID") from None


def target_fraction(spec: ProgramSpec, marks: tuple[Decimal, ...]) -> Decimal:
    """Long/cash decision using only this prefix (or its last slow-window marks).

    Warm-up and equality hold cash. The trend rule holds the configured fraction
    exactly when the fast arithmetic mean is strictly above the slow mean. No
    parameters are optimized, no future marks are requested and no probability
    or profitability claim is produced. Execution sizing belongs to a separately
    reviewed runner adapter and the account controller.
    """
    _validate(spec)
    _require(spec.kind != _UNIVERSE, "PROGRAM_KIND_UNSUPPORTED")  # the rotation decides through choose()
    _require(type(marks) is tuple and len(marks) <= MAX_MARKS, "PROGRAM_HISTORY_INVALID")
    for value in marks:
        _decimal(value, positive=True)
    if spec.kind == "cash" or len(marks) < spec.slow_window:
        return Decimal(0)
    fast = sum((Fraction(v) for v in marks[-spec.fast_window:]), Fraction(0))/spec.fast_window
    slow = sum((Fraction(v) for v in marks[-spec.slow_window:]), Fraction(0))/spec.slow_window
    return spec.exposure_fraction if fast > slow else Decimal(0)
