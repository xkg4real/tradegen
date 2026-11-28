"""TRADEGEN Qlib-Inspired Continuous Model Factory (qlib_lab) — Research Only.

Strictly isolated from the D14 live execution closure (core/compliance/owner.py:code_files).
Zero pickle, zero network calls, zero dynamic module imports, bitemporal point-in-time safe.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

from qlib_lab.exceptions import (
    CausalLagViolationError,
    FitLeakageError,
    LookAheadSyntaxError,
    MissingFeatureVoidError,
    PromotionGateRefusedError,
    QlibLabError,
    SecurityRefusalError,
    SnapshotContractError,
    SparseEventRefusalError,
    TestLabelLeakageError,
)
from qlib_lab.registry import (
    COMPONENT_REGISTRY,
    get_registered_class,
    init_instance_by_config,
    list_registered_components,
    register_component,
)

RESEARCH_FLAGS: dict[str, bool] = {
    "research_only": True,
    "live_eligible": False,
    "execution_ready": False,
    "source_authenticated": False,
    "owner_approval_verified": False,
}


def canonical_json_ascii(obj: Any) -> str:
    """Deterministic compact ASCII JSON matching tools/research/adaptive_bid_gap_preview.py:model_id."""
    return json.dumps(obj, sort_keys=True, ensure_ascii=True, separators=(",", ":"), allow_nan=False)


def sha256_hex(data: bytes | str) -> str:
    raw = data.encode("ascii") if isinstance(data, str) else data
    return hashlib.sha256(raw).hexdigest()


def canonical_sha256(obj: Any) -> str:
    return sha256_hex(canonical_json_ascii(obj))


__all__ = [
    "COMPONENT_REGISTRY",
    "RESEARCH_FLAGS",
    "CausalLagViolationError",
    "FitLeakageError",
    "LookAheadSyntaxError",
    "MissingFeatureVoidError",
    "PromotionGateRefusedError",
    "QlibLabError",
    "SecurityRefusalError",
    "SnapshotContractError",
    "SparseEventRefusalError",
    "TestLabelLeakageError",
    "canonical_json_ascii",
    "canonical_sha256",
    "get_registered_class",
    "init_instance_by_config",
    "list_registered_components",
    "register_component",
    "sha256_hex",
]
