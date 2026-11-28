"""Typed fail-closed exceptions for qlib_lab (research only)."""
from __future__ import annotations


class QlibLabError(Exception):
    """Base error for all fail-closed refusals in qlib_lab."""


class SecurityRefusalError(QlibLabError):
    """Unregistered component class, disallowed AST construct, tampered binary, or forbidden serialization."""


class LookAheadSyntaxError(QlibLabError):
    """Future-referencing shift or non-causal backfill detected outside LabelContext."""


class CausalLagViolationError(QlibLabError):
    """Bar or point-in-time input accessed before its known_at / receipt timestamp."""


class FitLeakageError(QlibLabError):
    """StatefulProcessor missing [fit_start_time, fit_end_time] or fitted beyond train_end."""


class TestLabelLeakageError(QlibLabError):
    """Attempt to prepare test segment with DK_L or label columns outside authorized evaluators."""


class MissingFeatureVoidError(QlibLabError):
    """Post-warmup missing feature fraction exceeded S1 threshold (fail-closed, zero silent imputation)."""


class SparseEventRefusalError(QlibLabError):
    """Event/binary feature has fewer than the minimum required events in the training window."""


class PromotionGateRefusedError(QlibLabError):
    """Attempt to mutate or promote a model without passing required statistical gates."""


class SnapshotContractError(QlibLabError):
    """Violation of tradegen-direction-forecast-v1 or non-revision contract."""
