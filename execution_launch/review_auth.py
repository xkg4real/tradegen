"""Owner-attested source and fixed-driver reviews; never an order capability.

Callers supply freshly verified owner context and public bytes. This module has
no signer, key loader, implicit clock, network or owner-state write. Fixed-driver
identity does not authenticate its injected live-history adapters.
"""
from __future__ import annotations

import base64
import binascii
from dataclasses import fields
from datetime import datetime, timedelta, timezone
import hashlib
import json
import re

from core.compliance import model as compliance
from execution_control.capability import digest
from execution_control.owner_authority import MAX_AUTHORITY_AGE_SECONDS, ReviewAuthority
from execution_launch.driver import FACTORY_ID, FixedDriverError, describe_fixed_driver, fixed_history_dependencies
from execution_launch.review_request import parse_review_request, review_request_json, ReviewRequestError
from execution_launch.runner import ImplementationBinding, ImplementationReceipt
from execution_launch.strategy import ReviewBinding, ReviewReceipt, evidence_digest

REVIEW_DOMAIN = b"tradegen-strategy-review/1\n"
MAX_DOCUMENT_BYTES = 98304
MAX_REVIEW_SECONDS = 86400
REVIEW_CHECKS = (
    "original_source_identity_and_records", "publication_before_capture",
    "independent_capture_window", "complete_candidate_and_retry_family",
    "causal_decisions_match_frozen_program", "fixed_runtime_driver_matches_reviewed_program",
    "deployment_source_and_dependency_closure", "capital_fees_rules_and_account_risk_applicability",
)
_BODY = frozenset({"schema_version", "purpose", "request", "driver_identity", "deployment_code_hash",
    "audit_sha256", "owner_fingerprint", "reviewer_id", "issued_at", "expires_at", "approved_checks"})
_IDENTITY = frozenset({"factory_id", "program_digest", "deployment_code_sha256", "protocol_digest",
    "profile_contract_digest", "rule_terms_digest", "deployment_window_digest"})
_HASH = re.compile(r"[0-9a-f]{64}")


class ReviewAuthenticationError(ValueError):
    """Fixed diagnostics only, no external body, exception or private state."""


def _need(value, code):
    if not value:
        raise ReviewAuthenticationError(code)


def _canonical(value):
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
    except (TypeError, ValueError, RecursionError, OverflowError):
        raise ReviewAuthenticationError("REVIEW_DOCUMENT_INVALID") from None


def _time(value):
    try:
        _need(type(value) is str and len(value) <= 40, "REVIEW_TIME_INVALID")
        stamp = datetime.fromisoformat(value)
        _need(stamp.utcoffset() is not None and stamp.astimezone(timezone.utc).isoformat(timespec="microseconds")
              == value, "REVIEW_TIME_INVALID")
        return stamp
    except (TypeError, ValueError, OverflowError):
        raise ReviewAuthenticationError("REVIEW_TIME_INVALID") from None


def _stamp(value):
    _need(type(value) is datetime and value.utcoffset() is not None, "REVIEW_TIME_INVALID")
    return value.astimezone(timezone.utc).isoformat(timespec="microseconds")


def _hash(value):
    return type(value) is str and _HASH.fullmatch(value) is not None


def _validate_body(body):
    _need(type(body) is dict and set(body) == _BODY and type(body["schema_version"]) is int
          and body["schema_version"] == 1 and body["purpose"] == "strategy_source_and_fixed_implementation_review",
          "REVIEW_DOCUMENT_SCHEMA_INVALID")
    try:
        request = parse_review_request(_canonical(body["request"]))
    except ReviewRequestError:
        raise ReviewAuthenticationError("REVIEW_UNSIGNED_REQUEST_INVALID") from None
    _need(request["source_kind_claim"] == "prospective_paper_capture"
          and request["computed_summary"]["mathematical_criteria_met"] is True
          and request["assessment_reasons"] == ["STRATEGY_TRUSTED_REVIEW_REQUIRED"]
          and set(request["profile_blockers"]) <= {"SIGNED_CONTEXT_REQUIRED"}, "REVIEW_REQUEST_NOT_ELIGIBLE")
    identity = body["driver_identity"]
    _need(type(identity) is dict and set(identity) == _IDENTITY and identity["factory_id"] == FACTORY_ID
          and all(_hash(v) for k, v in identity.items() if k != "factory_id"), "REVIEW_DRIVER_IDENTITY_INVALID")
    _need(all(identity[key] == request["bindings"][key] for key in
          ("program_digest", "protocol_digest", "profile_contract_digest", "rule_terms_digest")),
          "REVIEW_DRIVER_REQUEST_MISMATCH")
    _need(_hash(body["deployment_code_hash"]) and _hash(body["audit_sha256"]), "REVIEW_DIGEST_INVALID")
    fp = body["owner_fingerprint"]
    _need(type(fp) is str and fp.startswith("SHA256:") and _hash(fp[7:])
          and body["reviewer_id"] == "owner:" + fp[7:], "REVIEW_SIGNER_IDENTITY_INVALID")
    issued, expires = _time(body["issued_at"]), _time(body["expires_at"])
    _need(_time(request["requested_at"]) <= issued < expires <= _time(request["review_deadline"])
          and expires - issued <= timedelta(seconds=MAX_REVIEW_SECONDS), "REVIEW_VALIDITY_INVALID")
    _need(body["approved_checks"] == list(REVIEW_CHECKS), "REVIEW_CHECKLIST_INCOMPLETE")
    return body


def review_body(request, driver_identity, *, deployment_code_hash, audit_sha256,
                owner_fingerprint, issued_at, expires_at):
    """Build strictly typed unsigned signing input; this grants no review status."""
    body = {"schema_version": 1, "purpose": "strategy_source_and_fixed_implementation_review",
        "request": parse_review_request(review_request_json(request)), "driver_identity": dict(driver_identity),
        "deployment_code_hash": deployment_code_hash, "audit_sha256": audit_sha256,
        "owner_fingerprint": owner_fingerprint, "reviewer_id": "owner:" + owner_fingerprint[7:],
        "issued_at": _stamp(issued_at), "expires_at": _stamp(expires_at), "approved_checks": list(REVIEW_CHECKS)}
    return _validate_body(body)


def review_signing_bytes(body):
    return REVIEW_DOMAIN + _canonical(_validate_body(body)).encode("ascii")


def parse_review_document(raw):
    """Parse only; even a correctly shaped signature is not authenticated here."""
    _need(type(raw) in (str, bytes) and len(raw) <= MAX_DOCUMENT_BYTES, "REVIEW_DOCUMENT_TOO_LARGE")
    def pairs(items):
        result = {}
        for key, value in items:
            _need(key not in result, "REVIEW_DOCUMENT_DUPLICATE_KEY")
            result[key] = value
        return result
    def invalid(_):
        raise ReviewAuthenticationError("REVIEW_DOCUMENT_INVALID")
    try:
        envelope = json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid)
        _need(type(envelope) is dict and set(envelope) == {"body", "signature_b64"}, "REVIEW_ENVELOPE_INVALID")
        _validate_body(envelope["body"])
        signature = envelope["signature_b64"]
        _need(type(signature) is str and len(signature) == 88, "REVIEW_SIGNATURE_INVALID")
        decoded = base64.b64decode(signature, validate=True)
        _need(len(decoded) == 64 and base64.b64encode(decoded).decode("ascii") == signature,
              "REVIEW_SIGNATURE_INVALID")
        return envelope
    except ReviewAuthenticationError:
        raise
    except (TypeError, ValueError, UnicodeError, OverflowError, RecursionError, binascii.Error):
        raise ReviewAuthenticationError("REVIEW_DOCUMENT_INVALID") from None


def _authenticate(document, authority, now):
    body = parse_review_document(document)["body"]
    _stamp(now)
    _need(type(authority) is ReviewAuthority, "REVIEW_OWNER_AUTHORITY_REQUIRED")
    _stamp(authority.observed_at)
    _need(timedelta(0) <= now - authority.observed_at <= timedelta(seconds=MAX_AUTHORITY_AGE_SECONDS),
          "REVIEW_OWNER_AUTHORITY_STALE")
    context = authority.context
    try:
        intact = (type(context) is compliance.Context and compliance.is_sealed(context)
            and type(context.owner) is compliance.OwnerState and type(context.active) is compliance.ApprovedState
            and context.ctx_hash == compliance.sha256_hex(compliance.canonical_json({f.name: getattr(context, f.name)
                for f in fields(compliance.Context) if f.name != "ctx_hash"})))
    except (ValueError, TypeError, AttributeError, OverflowError, RecursionError):
        intact = False
    _need(intact, "REVIEW_OWNER_CONTEXT_INVALID")
    _need(context.date == now.astimezone(compliance.KST).date() and context.owner.ok
          and context.active.valid is True and context.code_signed is True and not context.owner.halted_floors,
          "REVIEW_OWNER_APPROVAL_REQUIRED")
    public = authority.public_key_raw
    _need(type(public) is bytes and len(public) == 32, "REVIEW_PUBLIC_KEY_INVALID")
    fp = "SHA256:" + hashlib.sha256(public).hexdigest()
    _need(fp == context.owner.fingerprint == body["owner_fingerprint"], "REVIEW_CURRENT_KEY_MISMATCH")
    _need(context.code_hash == body["deployment_code_hash"], "REVIEW_DEPLOYMENT_CODE_MISMATCH")
    _need(_time(body["issued_at"]) <= now < _time(body["expires_at"]), "REVIEW_EXPIRED_OR_FUTURE")
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    try:
        Ed25519PublicKey.from_public_bytes(public).verify(
            base64.b64decode(parse_review_document(document)["signature_b64"]), review_signing_bytes(body))
    except (InvalidSignature, ValueError, TypeError):
        raise ReviewAuthenticationError("REVIEW_SIGNATURE_UNVERIFIED") from None
    return body


def _source_binding(body):
    request, binding = body["request"], body["request"]["bindings"]
    return ReviewBinding(protocol_digest=binding["protocol_digest"], evidence_digest=binding["evidence_digest"],
        registry_digest=binding["registry_digest"], inputs_digest=binding["inputs_digest"],
        strategy_id=request["strategy_id"], strategy_code_sha256=binding["program_digest"],
        profile_contract_digest=binding["profile_contract_digest"], rule_terms_digest=binding["rule_terms_digest"],
        capture_end=_time(request["capture_end"]))


def verify_source_review(binding, document, *, authority, now):
    body = _authenticate(document, authority, now)
    _need(type(binding) is ReviewBinding and evidence_digest(binding) == evidence_digest(_source_binding(body)),
          "REVIEW_SOURCE_BINDING_MISMATCH")
    return ReviewReceipt(binding_digest=evidence_digest(binding), reviewer_id=body["reviewer_id"],
        source_review_sha256=body["audit_sha256"], reviewed_at=_time(body["issued_at"]),
        expires_at=_time(body["expires_at"]))


def verify_implementation_review(binding, driver, document, *, authority, now,
                                 approved_history_provider, approved_history_verifier):
    body = _authenticate(document, authority, now)
    values = body["request"]["bindings"]
    expected = ImplementationBinding(**{name: values[name] for name in
        ("program_digest", "protocol_digest", "evidence_digest", "profile_contract_digest", "rule_terms_digest")})
    _need(type(binding) is ImplementationBinding and digest(binding) == digest(expected),
          "REVIEW_IMPLEMENTATION_BINDING_MISMATCH")
    try:
        actual = describe_fixed_driver(driver)
        history_provider, history_verifier = fixed_history_dependencies(driver)
    except (FixedDriverError, ValueError, TypeError, AttributeError):
        raise ReviewAuthenticationError("REVIEW_FIXED_DRIVER_REQUIRED") from None
    _need(callable(approved_history_provider) and callable(approved_history_verifier)
          and history_provider is approved_history_provider and history_verifier is approved_history_verifier,
          "REVIEW_HISTORY_DEPLOYMENT_MISMATCH")
    _need({f.name: getattr(actual, f.name) for f in fields(actual)} == body["driver_identity"],
          "REVIEW_FIXED_DRIVER_MISMATCH")
    return ImplementationReceipt(binding_digest=digest(binding), callback=driver.callback,
        audit_sha256=body["audit_sha256"], reviewed_at=_time(body["issued_at"]), expires_at=_time(body["expires_at"]))


class ReviewVerifiers:
    """Callbacks with explicit trusted clock and a freshly loaded authority each call.

    Neither provider is authenticated by this wrapper. The signed deployment must
    wire reviewed providers; live-history origin remains a separate prerequisite.
    """
    def __init__(self, document, *, clock, authority_provider,
                 approved_history_provider, approved_history_verifier):
        parse_review_document(document)
        _need(callable(clock) and callable(authority_provider), "REVIEW_PROVIDERS_REQUIRED")
        self._document = document
        self._clock = clock
        self._authority_provider = authority_provider
        _need(callable(approved_history_provider) and callable(approved_history_verifier),
              "REVIEW_HISTORY_DEPLOYMENT_REQUIRED")
        self._history_provider = approved_history_provider
        self._history_verifier = approved_history_verifier

    def source(self, binding):
        now = self._clock()
        return verify_source_review(binding, self._document, authority=self._authority_provider(now), now=now)

    def implementation(self, binding, driver):
        now = self._clock()
        return verify_implementation_review(binding, driver, self._document,
            authority=self._authority_provider(now), now=now,
            approved_history_provider=self._history_provider, approved_history_verifier=self._history_verifier)
