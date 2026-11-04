"""Explicit deterministic paper candidates; no fitted edge or deployment approval.

The decision function consumes only supplied historical marks. Source artifacts
and parameters are bound with the same digest shape as the existing runner;
matching that digest does not authenticate a callback or its source.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction
import hashlib
import json
import re

from execution_control.capability import digest

_ID = re.compile(r"[A-Za-z][A-Za-z0-9_.:-]{0,95}")
_DECIMAL = re.compile(r"(?:0|[1-9][0-9]*)(?:\.[0-9]+)?")
MAX_PROGRAM_BYTES = 16384
MAX_MARKS = 20000


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


def _decimal(value, *, positive=False):
    _require(type(value) is Decimal and value.is_finite(), "PROGRAM_DECIMAL_REQUIRED")
    _require(len(value.as_tuple().digits) <= 40 and abs(value.as_tuple().exponent) <= 30,
             "PROGRAM_DECIMAL_RANGE")
    _require(value > 0 if positive else value >= 0, "PROGRAM_AMOUNT_INVALID")


def _validate(spec):
    _require(type(spec) is ProgramSpec and type(spec.schema_version) is int
             and spec.schema_version == 1, "PROGRAM_SCHEMA_INVALID")
    _require(type(spec.strategy_id) is str and _ID.fullmatch(spec.strategy_id) is not None,
             "PROGRAM_ID_INVALID")
    _require(type(spec.kind) is str, "PROGRAM_KIND_UNSUPPORTED")
    _require(type(spec.fast_window) is int and type(spec.slow_window) is int,
             "PROGRAM_WINDOW_INVALID")
    _decimal(spec.exposure_fraction)
    if spec.kind == "cash":
        _require(spec.fast_window == spec.slow_window == 0 and spec.exposure_fraction == 0,
                 "PROGRAM_CASH_PARAMETERS_INVALID")
    elif spec.kind == "moving_average_trend":
        _require(1 <= spec.fast_window < spec.slow_window <= 4096,
                 "PROGRAM_WINDOW_INVALID")
        _require(0 < spec.exposure_fraction <= 1, "PROGRAM_EXPOSURE_INVALID")
    else:
        raise ProgramError("PROGRAM_KIND_UNSUPPORTED")


def _body(spec):
    _validate(spec)
    fraction = format(spec.exposure_fraction, "f")
    fraction = (fraction.rstrip("0").rstrip(".") if "." in fraction else fraction)
    return {"schema_version": spec.schema_version, "strategy_id": spec.strategy_id,
            "kind": spec.kind, "fast_window": spec.fast_window, "slow_window": spec.slow_window,
            "exposure_fraction": fraction if spec.exposure_fraction else "0"}


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
        _require(type(body) is dict and set(body) == {
            "schema_version", "strategy_id", "kind", "fast_window", "slow_window", "exposure_fraction"},
            "PROGRAM_JSON_SCHEMA_INVALID")
        value = body["exposure_fraction"]
        _require(type(value) is str and len(value) <= 72 and _DECIMAL.fullmatch(value) is not None,
                 "PROGRAM_DECIMAL_STRING_REQUIRED")
        spec = ProgramSpec(**(body | {"exposure_fraction": Decimal(value)}))
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
    _require(type(marks) is tuple and len(marks) <= MAX_MARKS, "PROGRAM_HISTORY_INVALID")
    for value in marks:
        _decimal(value, positive=True)
    if spec.kind == "cash" or len(marks) < spec.slow_window:
        return Decimal(0)
    fast = sum((Fraction(v) for v in marks[-spec.fast_window:]), Fraction(0))/spec.fast_window
    slow = sum((Fraction(v) for v in marks[-spec.slow_window:]), Fraction(0))/spec.slow_window
    return spec.exposure_fraction if fast > slow else Decimal(0)
