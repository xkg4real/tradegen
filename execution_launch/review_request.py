"""Unsigned review handoff artifacts, never authenticated review receipts.

The builder uses an actually computed result and explicit program bytes. Import
checks structure and integrity only; no imported summary becomes evidence,
source authentication, a callback verifier, an owner approval or permission.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
import re

from execution_launch.profile import (
    LaunchProfile, preflight_profile, profile_contract_digest, profile_digest, rule_terms_digest,
)
from execution_launch.program import parse_program, parameters_json as canonical_parameters, program_digest
from execution_launch.strategy import assess_strategy

MAX_REQUEST_BYTES = 65536
_HASH = re.compile(r"[0-9a-f]{64}")
_ID = re.compile(r"[A-Za-z][A-Za-z0-9_.:-]{0,95}")
_KINDS = frozenset({"prospective_paper_capture", "synthetic", "retrospective_replay"})
_BINDINGS = frozenset({"protocol_digest", "evidence_digest", "registry_digest", "inputs_digest",
    "profile_contract_digest", "runtime_profile_digest", "rule_terms_digest", "program_digest",
    "program_artifact_sha256", "canonical_parameters_sha256", "capture_source_code_sha256"})
_AUTH_FLAGS = frozenset({"source_authenticated", "implementation_authenticated", "signature_verified",
                       "owner_context_verified", "research_review_ready", "execution_ready"})
_CHECKS = (
    "original_source_identity_and_records",
    "publication_before_capture",
    "independent_capture_window",
    "complete_candidate_and_retry_family",
    "causal_decisions_match_frozen_program",
    "fixed_runtime_driver_matches_reviewed_program",
    "deployment_source_and_dependency_closure",
    "capital_fees_rules_and_account_risk_applicability",
    "effective_owner_limits_and_actual_session",
)
_METRICS = frozenset({"observations", "completed_roundtrips", "total_return", "max_drawdown",
                     "double_cost_total_return", "extra_delay_total_return", "family_adjusted_p"})
_TOP = frozenset({"schema_version", "artifact_kind", "requested_at", "capture_start", "capture_end",
    "evaluated_at", "review_deadline", "study_id", "strategy_id", "capture_source_id",
    "evaluator_revision", "source_kind_claim", "bindings", "computed_summary", "profile_blockers",
    "assessment_reasons", "required_checks", "reviewer_id", "review_public_key", "review_signature",
    "deployment_code_hash", "authority", "request_sha256"})
_FAMILY = frozenset({"plan_digest", "members", "family_sha256"})
_MEMBER = frozenset({"study_id", "capture_sha256", "evidence_digest"})


class ReviewRequestError(ValueError):
    """Fixed diagnostics with no supplied value or provider text."""


def _require(condition, code):
    if not condition:
        raise ReviewRequestError(code)


def _stamp(value):
    _require(type(value) is datetime and value.utcoffset() is not None, "REVIEW_AWARE_TIME_REQUIRED")
    try:
        return value.astimezone(timezone.utc).isoformat(timespec="microseconds")
    except (ValueError, OverflowError):
        raise ReviewRequestError("REVIEW_TIME_INVALID") from None


def _time(value):
    _require(type(value) is str and len(value) <= 40, "REVIEW_TIME_INVALID")
    try:
        stamp = datetime.fromisoformat(value)
        _require(_stamp(stamp) == value, "REVIEW_TIME_FORMAT_INVALID")
        return stamp
    except (ValueError, TypeError, OverflowError):
        raise ReviewRequestError("REVIEW_TIME_INVALID") from None


def _hash(value):
    return type(value) is str and _HASH.fullmatch(value) is not None


def _identifier(value):
    return type(value) is str and _ID.fullmatch(value) is not None


def _canonical(value):
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
    except (ValueError, TypeError, RecursionError, OverflowError):
        raise ReviewRequestError("REVIEW_REQUEST_JSON_INVALID") from None


def _validate_family(value):
    _require(type(value) is dict and set(value) == _FAMILY and _hash(value["plan_digest"]),
             "REVIEW_FAMILY_SCHEMA_INVALID")
    members = value["members"]
    _require(type(members) is list and 1 <= len(members) <= 128
             and all(type(row) is dict and set(row) == _MEMBER and _identifier(row["study_id"])
                     and _hash(row["capture_sha256"]) and _hash(row["evidence_digest"]) for row in members),
             "REVIEW_FAMILY_SCHEMA_INVALID")
    ids = [row["study_id"] for row in members]
    _require(ids == sorted(set(ids)), "REVIEW_FAMILY_SCHEMA_INVALID")
    body = {"plan_digest": value["plan_digest"], "members": members}
    _require(_hash(value["family_sha256"]) and value["family_sha256"]
             == hashlib.sha256(_canonical(body).encode("ascii")).hexdigest(), "REVIEW_FAMILY_DIGEST_MISMATCH")


def build_family_commitment(*, plan_digest, capture_digests, result_digests):
    """Bind the entire evaluated family, including failures; this is not authentication.

    The study workflow computes these hashes from every raw capture and issued
    evaluation. A detached owner signature over a schema-2 request authenticates
    that reviewed family; the selector must recompute it before choosing a row.
    """
    _require(type(capture_digests) is dict and type(result_digests) is dict
             and set(capture_digests) == set(result_digests)
             and all(_identifier(name) for name in capture_digests), "REVIEW_FAMILY_SCHEMA_INVALID")
    body = {"plan_digest": plan_digest, "members": [{"study_id": name,
        "capture_sha256": capture_digests[name], "evidence_digest": result_digests[name]}
        for name in sorted(capture_digests)]}
    value = body | {"family_sha256": hashlib.sha256(_canonical(body).encode("ascii")).hexdigest()}
    _validate_family(value)
    return value


def bind_review_family(request, commitment):
    """Create a new unsigned schema-2 request; never upgrade an existing signature."""
    _validate(request)
    _require(request["schema_version"] == 1, "REVIEW_FAMILY_ALREADY_BOUND")
    _validate_family(commitment)
    body = {name: value for name, value in request.items() if name != "request_sha256"}
    body.update(schema_version=2, family_commitment=json.loads(_canonical(commitment)))
    result = body | {"request_sha256": hashlib.sha256(_canonical(body).encode("ascii")).hexdigest()}
    _validate(result)
    return result


def _validate(request):
    _require(type(request) is dict and type(request.get("schema_version")) is int
             and request["schema_version"] in (1, 2), "REVIEW_REQUEST_SCHEMA_INVALID")
    expected = _TOP if request["schema_version"] == 1 else _TOP | {"family_commitment"}
    _require(set(request) == expected, "REVIEW_REQUEST_SCHEMA_INVALID")
    _require(type(request["schema_version"]) is int and request["schema_version"] in (1, 2)
             and request["artifact_kind"] == "unsigned_strategy_review_request",
             "REVIEW_REQUEST_SCHEMA_INVALID")
    stamps = {name: _time(request[name]) for name in
              ("requested_at", "capture_start", "capture_end", "evaluated_at", "review_deadline")}
    _require(stamps["capture_start"] < stamps["capture_end"] <= stamps["evaluated_at"]
             <= stamps["requested_at"] and stamps["review_deadline"] > stamps["capture_end"],
             "REVIEW_REQUEST_CHRONOLOGY_INVALID")
    for name in ("study_id", "strategy_id", "capture_source_id", "evaluator_revision"):
        _require(_identifier(request[name]), "REVIEW_REQUEST_IDENTIFIER_INVALID")
    _require(type(request["source_kind_claim"]) is str and request["source_kind_claim"] in _KINDS,
             "REVIEW_SOURCE_KIND_INVALID")
    bindings = request["bindings"]
    _require(type(bindings) is dict and set(bindings) == _BINDINGS and all(_hash(v) for v in bindings.values()),
             "REVIEW_REQUEST_BINDING_INVALID")
    if request["schema_version"] == 2:
        family = request["family_commitment"]
        _validate_family(family)
        member = next((row for row in family["members"] if row["study_id"] == request["study_id"]), None)
        _require(member is not None and member["evidence_digest"] == bindings["evidence_digest"],
                 "REVIEW_FAMILY_CANDIDATE_MISMATCH")
    summary = request["computed_summary"]
    _require(type(summary) is dict and set(summary) == {"mathematical_criteria_met", "metrics"}
             and type(summary["mathematical_criteria_met"]) is bool,
             "REVIEW_REQUEST_SUMMARY_INVALID")
    metrics = summary["metrics"]
    _require(type(metrics) is dict and set(metrics) == _METRICS, "REVIEW_REQUEST_SUMMARY_INVALID")
    for name, value in metrics.items():
        _require(type(value) is int and 0 <= value <= 100000 if name in ("observations", "completed_roundtrips")
                 else type(value) in (float, int) and math.isfinite(value), "REVIEW_REQUEST_SUMMARY_INVALID")
    _require(0 < metrics["family_adjusted_p"] <= 1 and 0 <= metrics["max_drawdown"] <= 1,
             "REVIEW_REQUEST_SUMMARY_INVALID")
    for name in ("profile_blockers", "assessment_reasons"):
        values = request[name]
        _require(type(values) is list and len(values) <= 100
                 and all(type(v) is str and re.fullmatch(r"[A-Z][A-Z0-9_]{0,95}", v) for v in values),
                 "REVIEW_REQUEST_REASONS_INVALID")
    expected_checks = [{"id": name, "reviewed": None, "evidence_sha256": None} for name in _CHECKS]
    _require(request["required_checks"] == expected_checks, "REVIEW_REQUEST_REVIEW_MUST_REMAIN_PENDING")
    for name in ("reviewer_id", "review_public_key", "review_signature", "deployment_code_hash"):
        _require(request[name] is None, "REVIEW_REQUEST_CANNOT_CONTAIN_APPROVAL")
    authority = request["authority"]
    _require(type(authority) is dict and set(authority) == _AUTH_FLAGS
             and all(value is False for value in authority.values()),
             "REVIEW_REQUEST_CANNOT_GRANT_AUTHORITY")
    body = {name: value for name, value in request.items() if name != "request_sha256"}
    _require(_hash(request["request_sha256"])
             and request["request_sha256"] == hashlib.sha256(_canonical(body).encode("ascii")).hexdigest(),
             "REVIEW_REQUEST_DIGEST_MISMATCH")


def review_request_json(request) -> str:
    """Serialize an unsigned request, rejecting added approval or PASS fields."""
    _validate(request)
    raw = _canonical(request)
    _require(len(raw) <= MAX_REQUEST_BYTES, "REVIEW_REQUEST_TOO_LARGE")
    return raw


def parse_review_request(raw: str | bytes) -> dict:
    """Inspect only request integrity; imported summaries are never recomputed evidence."""
    _require(type(raw) in (str, bytes) and len(raw) <= MAX_REQUEST_BYTES, "REVIEW_REQUEST_TOO_LARGE")
    def pairs(values):
        result = {}
        for key, value in values:
            _require(key not in result, "REVIEW_REQUEST_DUPLICATE_KEY")
            result[key] = value
        return result
    def invalid(value):
        raise ReviewRequestError("REVIEW_REQUEST_JSON_INVALID")
    try:
        result = json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid)
        _validate(result)
        return result
    except ReviewRequestError:
        raise
    except (ValueError, TypeError, UnicodeError, ArithmeticError, RecursionError):
        raise ReviewRequestError("REVIEW_REQUEST_JSON_INVALID") from None


def build_review_request(profile, protocol, result, *, now, program_artifact: bytes,
                         parameters_json: str) -> dict:
    """Prepare a review queue item from computed evidence, never a successful verifier.

    The supplied program is bound by actual bytes and canonical parameters. Its
    relationship to a running Python callable is explicitly still a review duty.
    A prospective source label remains an unauthenticated claim, even if all
    mathematical criteria happen to pass. No key, context, file or clock is read.
    """
    try:
        requested_at = _stamp(now)
        _require(type(profile) is LaunchProfile and profile.instrument_rules is not None,
                 "REVIEW_PROFILE_RULES_REQUIRED")
        spec = parse_program(parameters_json)
        _require(type(parameters_json) is str and canonical_parameters(spec) == parameters_json,
                 "REVIEW_PARAMETERS_FORMAT_INVALID")
        code = program_digest(spec, program_artifact)
        contract = profile_contract_digest(profile)
        terms = rule_terms_digest(profile.instrument_rules)
        _require(code == profile.strategy_code_sha256 == protocol.strategy_code_sha256
                 and spec.strategy_id == profile.strategy_id == protocol.strategy_id
                 and contract == protocol.profile_contract_digest and terms == protocol.rule_terms_digest,
                 "REVIEW_PROGRAM_OR_PROFILE_MISMATCH")
        _require(protocol.quote_currency == "KRW" and profile.policy.initial_equity is not None
                 and protocol.initial_cash_quote == profile.policy.initial_equity,
                 "REVIEW_CAPITAL_MISMATCH")
        assessment = assess_strategy(protocol, result, profile_contract_digest=contract,
            rule_terms_digest=terms, strategy_code_sha256=code, now=now, review_verifier=None)
        _require(result.protocol_digest == assessment.protocol_digest
                 and result.started_at == protocol.capture_start and result.ended_at == protocol.capture_end,
                 "REVIEW_PROTOCOL_RESULT_MISMATCH")
        report = preflight_profile(profile, now=now)
        body = {
            "schema_version": 1, "artifact_kind": "unsigned_strategy_review_request",
            "requested_at": requested_at, "capture_start": _stamp(protocol.capture_start),
            "capture_end": _stamp(protocol.capture_end), "evaluated_at": _stamp(result.evaluated_at),
            "review_deadline": _stamp(protocol.capture_end + timedelta(seconds=protocol.review_max_age_seconds)),
            "study_id": protocol.study_id, "strategy_id": protocol.strategy_id,
            "capture_source_id": protocol.capture_source_id, "evaluator_revision": protocol.evaluator_revision,
            "source_kind_claim": result.source_kind,
            "bindings": {
                "protocol_digest": assessment.protocol_digest, "evidence_digest": assessment.evidence_digest,
                "registry_digest": result.registry_digest, "inputs_digest": result.inputs_digest,
                "profile_contract_digest": contract, "runtime_profile_digest": profile_digest(profile),
                "rule_terms_digest": terms, "program_digest": code,
                "program_artifact_sha256": hashlib.sha256(program_artifact).hexdigest(),
                "canonical_parameters_sha256": hashlib.sha256(parameters_json.encode("ascii")).hexdigest(),
                "capture_source_code_sha256": protocol.capture_source_code_sha256,
            },
            "computed_summary": {"mathematical_criteria_met": assessment.math_qualified, "metrics": {
                "observations": result.primary.observations,
                "completed_roundtrips": result.primary.completed_roundtrips,
                "total_return": result.primary.total_return, "max_drawdown": result.primary.max_drawdown,
                "double_cost_total_return": result.double_cost.total_return,
                "extra_delay_total_return": result.extra_bar_delay.total_return,
                "family_adjusted_p": result.family_adjusted_p,
            }},
            "profile_blockers": list(report.reasons), "assessment_reasons": list(assessment.reasons),
            "required_checks": [{"id": name, "reviewed": None, "evidence_sha256": None} for name in _CHECKS],
            "reviewer_id": None, "review_public_key": None, "review_signature": None,
            "deployment_code_hash": None, "authority": {name: False for name in sorted(_AUTH_FLAGS)},
        }
        request = body | {"request_sha256": hashlib.sha256(_canonical(body).encode("ascii")).hexdigest()}
        review_request_json(request)
        return request
    except ReviewRequestError:
        raise
    except Exception:
        raise ReviewRequestError("REVIEW_COMPUTED_EVIDENCE_OR_INPUT_INVALID") from None
