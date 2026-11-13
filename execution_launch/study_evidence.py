"""Whole current-family input validation before any actual paper evaluation.

Pure explicit inputs: no files, clocks, source authentication, approvals or orders.
Every raw capture is retained, including numerically rejected candidates. Resource
admission is neither evidence corruption nor a market/evaluation failure outcome.
Prior-attempt completeness and sealed research bundles remain separate contracts.
"""
from collections.abc import Mapping
from dataclasses import dataclass, fields, replace
from datetime import timedelta
import hashlib

from execution_control.model import InstrumentRules
from execution_launch import strategy as S


class StudyEvidenceError(ValueError):
    """Fixed family/admission diagnostics; never provider text or private data."""


def _need(condition, code):
    if not condition:
        raise StudyEvidenceError(code)


@dataclass(frozen=True, kw_only=True)
class FamilyEvidenceLimits:
    max_candidates: int = 128
    max_capture_bytes: int = 16 * 1024 * 1024
    max_total_bytes: int = 128 * 1024 * 1024
    max_inference_work: int = 40_000_000

    def __post_init__(self):
        ceilings = (128, 16 * 1024 * 1024, 128 * 1024 * 1024, 40_000_000)
        for field, ceiling in zip(fields(type(self)), ceilings):
            value = getattr(self, field.name)
            _need(type(value) is int and 0 < value <= ceiling, 'STUDY_EVIDENCE_LIMITS_INVALID')


DEFAULT_LIMITS = FamilyEvidenceLimits()


@dataclass(frozen=True, kw_only=True)
class EvaluatedCandidate:
    study_id: str
    raw_capture: bytes
    capture_sha256: str
    result: S.ValidationResult | S.CarryValidationResult


@dataclass(frozen=True, kw_only=True)
class FamilyEvaluation:
    """Actual results when returned by the evaluator; construction gives no trust."""
    rows: tuple[EvaluatedCandidate, ...]

    @property
    def results(self):
        return {row.study_id: row.result for row in self.rows}

    @property
    def capture_digests(self):
        return {row.study_id: row.capture_sha256 for row in self.rows}


def evaluate_study_family(protocols, captures, rules, *, registry, now, limits=DEFAULT_LIMITS):
    """Check the complete current family, then rerun the existing real evaluators.

    The caller validates its StudyPlan first. Snapshots preserve the raw bytes and
    economic inputs across both passes. Validation returns no privileged token;
    each actual evaluator repeats all its checks. No partial family is returned
    on an unexpected evaluation failure. This synchronous admission does not
    reserve capacity against unrelated concurrent evaluations.
    """
    _need(type(limits) is FamilyEvidenceLimits, 'STUDY_EVIDENCE_LIMITS_INVALID')
    try:
        limits = replace(limits)
    except (AttributeError, TypeError):
        raise StudyEvidenceError('STUDY_EVIDENCE_LIMITS_INVALID') from None
    _need(type(protocols) is tuple and len(protocols) > 0, 'STUDY_EVIDENCE_FAMILY_INVALID')
    _need(len(protocols) <= limits.max_candidates, 'STUDY_EVIDENCE_RESOURCE_LIMIT')
    # Reparse explicit values, not summaries, to avoid retaining caller-owned
    # frozen objects that can nevertheless be changed with object.__setattr__.
    protocols = tuple(S.parse_protocol(S.protocol_json(p)) for p in protocols)
    identifiers = tuple(p.study_id for p in protocols)
    strategies = tuple(sorted(p.strategy_id for p in protocols))
    _need(len(set(identifiers)) == len(identifiers) and len(set(strategies)) == len(strategies)
          and all(p.family_members == strategies for p in protocols), 'STUDY_EVIDENCE_FAMILY_INVALID')
    S._instant(now)
    registry_digest = S.validate_registry(registry)
    registry = tuple(replace(row) for row in registry)
    _need(type(rules) is InstrumentRules, 'STUDY_EVIDENCE_RULES_REQUIRED')
    rules = replace(rules)
    work = sum(p.bootstrap_replications * (
        ((p.capture_end - p.capture_start) // timedelta(seconds=p.bar_seconds)) // p.block_length + 1)
        for p in protocols)
    _need(work <= limits.max_inference_work, 'STUDY_EVIDENCE_RESOURCE_LIMIT')
    _need(isinstance(captures, Mapping), 'STUDY_EVIDENCE_CAPTURE_FAMILY_INCOMPLETE')
    _need(len(captures) <= limits.max_candidates, 'STUDY_EVIDENCE_RESOURCE_LIMIT')
    snapshot, total = {}, 0
    for key, value in captures.items():
        _need(type(key) is str and key in identifiers and key not in snapshot,
              'STUDY_EVIDENCE_CAPTURE_FAMILY_INCOMPLETE')
        _need(type(value) in (str, bytes), 'STUDY_EVIDENCE_CAPTURE_TYPE_INVALID')
        _need(len(value) <= limits.max_capture_bytes, 'STUDY_EVIDENCE_RESOURCE_LIMIT')
        try:
            raw = value.encode('utf-8') if type(value) is str else value
        except UnicodeEncodeError:
            raise StudyEvidenceError('STUDY_EVIDENCE_CAPTURE_ENCODING_INVALID') from None
        _need(len(raw) <= limits.max_capture_bytes, 'STUDY_EVIDENCE_RESOURCE_LIMIT')
        total += len(raw)
        _need(total <= limits.max_total_bytes, 'STUDY_EVIDENCE_RESOURCE_LIMIT')
        snapshot[key] = raw
    _need(set(snapshot) == set(identifiers), 'STUDY_EVIDENCE_CAPTURE_FAMILY_INCOMPLETE')
    # All candidates, including the final frame of the last candidate, must
    # finish input validation before the first simulator or issuance is called.
    for protocol in protocols:
        S.validate_capture_json(protocol, snapshot[protocol.study_id], rules, now=now,
                                expected_registry_digest=registry_digest)
    try:
        S.require_evaluation_capacity(len(protocols))
    except S.StrategyEvidenceError:
        raise StudyEvidenceError('STUDY_EVIDENCE_RESOURCE_LIMIT') from None
    rows = []
    for protocol in protocols:
        raw = snapshot[protocol.study_id]
        result = S.evaluate_capture_json(protocol, raw, rules, now=now)
        rows.append(EvaluatedCandidate(study_id=protocol.study_id, raw_capture=raw,
            capture_sha256=hashlib.sha256(raw).hexdigest(), result=result))
    return FamilyEvaluation(rows=tuple(rows))
