"""Inert candidate outcome documents, never evaluated evidence or authority.

Every field is caller-claimed metadata, including capture/registry/input digests,
the evaluation time, status and failure location. Parsing checks representation
and internal consistency only: it neither reads original bytes nor proves their
completeness, provenance, registration, arithmetic, failure cause or chronology.
An EVALUATED document may describe a mathematically rejected candidate. A valid
EVALUATION_FAILED document is not an issued evaluator failure. The universe-v1
failure vocabulary does not implement that evaluator or alter its terminal rule.

validate_outcome_set checks exactly the current IDs supplied by its caller, not
their membership in a frozen plan or the registered prior-attempt family. It
does not compute K, rank candidates, issue results, approve research, renew a
session or authorize orders. Future shared whole-input validation must precede
any actual outcome issuance; corruption must never be relabelled as failure.

This stdlib-only module has no I/O, implicit clock or repository imports. Legacy
ValidationResult digests, schema-1/2 reviews and driver semantics are unchanged.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import re

MAX_OUTCOME_BYTES = 65536
MAX_OUTCOME_MEMBERS = 128
MAX_SLOT_INDEX = 19999
_MAX_JSON_DEPTH = 4
_HASH = re.compile(r"[0-9a-f]{64}")
_ID = re.compile(r"[A-Za-z][A-Za-z0-9_.:-]{0,95}")
_REVISIONS = frozenset({"forward-paper-v1", "forward-universe-v1"})
_SOURCE_KINDS = frozenset({"prospective_paper_capture", "synthetic", "retrospective_replay"})
_PHASES = frozenset({"benchmark", "primary", "double_cost", "extra_bar_delay"})
_BENCHMARK_FAILURE = "STRATEGY_UNIVERSE_BENCHMARK_UNAVAILABLE"
_FAILURES = frozenset({"STRATEGY_UNIVERSE_HELD_COIN_VANISHED", "STRATEGY_UNIVERSE_MARK_UNAVAILABLE",
                       "STRATEGY_UNIVERSE_TERMINAL_BOOK_UNAVAILABLE", _BENCHMARK_FAILURE})
_FAILURE_DOMAIN = b"tradegen-candidate-evaluation-failure/1\x00"
_EVALUATED_DOMAIN = b"tradegen-candidate-evaluated-document/1\x00"
_FIELDS = frozenset({"schema_version", "status", "study_id", "protocol_digest", "registry_digest",
                     "capture_sha256", "inputs_digest", "evaluator_revision", "source_kind_claim",
                     "evaluated_at", "result_digest", "failure"})
_FAILURE_FIELDS = frozenset({"code", "slot_index", "phase"})


class ResearchOutcomeError(ValueError):
    """Fixed diagnostics, without supplied text, paths or financial values."""


def _require(condition, code):
    if not condition:
        raise ResearchOutcomeError(code)


def _hash(value):
    return type(value) is str and _HASH.fullmatch(value) is not None


def _identifier(value):
    return type(value) is str and _ID.fullmatch(value) is not None


def _stamp(value):
    try:
        _require(type(value) is datetime and value.utcoffset() is not None, "RESEARCH_OUTCOME_TIME_INVALID")
        return value.astimezone(timezone.utc).isoformat(timespec="microseconds")
    except (ValueError, TypeError, OverflowError):
        raise ResearchOutcomeError("RESEARCH_OUTCOME_TIME_INVALID") from None


def _parse_time(value):
    _require(type(value) is str and len(value) == 32, "RESEARCH_OUTCOME_TIME_INVALID")
    try:
        stamp = datetime.fromisoformat(value)
        _require(_stamp(stamp) == value, "RESEARCH_OUTCOME_TIME_INVALID")
        return stamp
    except (ValueError, TypeError, OverflowError):
        raise ResearchOutcomeError("RESEARCH_OUTCOME_TIME_INVALID") from None


@dataclass(frozen=True, kw_only=True, slots=True)
class EvaluationFailureDetail:
    """A claimed failure location; no original input or semantic evaluation here."""
    code: str
    slot_index: int
    phase: str

    def __post_init__(self):
        _require(type(self.code) is str and self.code in _FAILURES,
                 "RESEARCH_OUTCOME_FAILURE_INVALID")
        _require(type(self.slot_index) is int and 0 <= self.slot_index <= MAX_SLOT_INDEX,
                 "RESEARCH_OUTCOME_FAILURE_INVALID")
        _require(type(self.phase) is str and self.phase in _PHASES
                 and (self.code == _BENCHMARK_FAILURE) == (self.phase == "benchmark"),
                 "RESEARCH_OUTCOME_FAILURE_INVALID")


@dataclass(frozen=True, kw_only=True, slots=True)
class CandidateOutcomeDocument:
    """Representation only. Hashes and status do not authenticate an evaluator."""
    schema_version: int
    status: str
    study_id: str
    protocol_digest: str
    registry_digest: str
    capture_sha256: str
    inputs_digest: str
    evaluator_revision: str
    source_kind_claim: str
    evaluated_at: datetime
    result_digest: str | None
    failure: EvaluationFailureDetail | None

    def __post_init__(self):
        _require(type(self.schema_version) is int and self.schema_version == 1,
                 "RESEARCH_OUTCOME_SCHEMA_INVALID")
        _require(type(self.status) is str and self.status in ("EVALUATED", "EVALUATION_FAILED"),
                 "RESEARCH_OUTCOME_SCHEMA_INVALID")
        _require(_identifier(self.study_id)
                 and all(_hash(value) for value in (self.protocol_digest, self.registry_digest,
                                                    self.capture_sha256, self.inputs_digest)),
                 "RESEARCH_OUTCOME_BINDING_INVALID")
        _require(type(self.evaluator_revision) is str and self.evaluator_revision in _REVISIONS,
                 "RESEARCH_OUTCOME_REVISION_UNSUPPORTED")
        _require(type(self.source_kind_claim) is str and self.source_kind_claim in _SOURCE_KINDS,
                 "RESEARCH_OUTCOME_SOURCE_KIND_INVALID")
        _stamp(self.evaluated_at)
        if self.status == "EVALUATED":
            _require(_hash(self.result_digest) and self.failure is None, "RESEARCH_OUTCOME_RESULT_INVALID")
        else:
            _require(self.result_digest is None and type(self.failure) is EvaluationFailureDetail,
                     "RESEARCH_OUTCOME_FAILURE_INVALID")
            _require(self.evaluator_revision == "forward-universe-v1",
                     "RESEARCH_OUTCOME_REVISION_UNSUPPORTED")
            self.failure.__post_init__()


def _body(document):
    _require(type(document) is CandidateOutcomeDocument, "RESEARCH_OUTCOME_DOCUMENT_REQUIRED")
    try:
        document.__post_init__()  # Frozen dataclasses are discipline, not a Python security boundary.
        failure = document.failure
        return {"schema_version": document.schema_version, "status": document.status, "study_id": document.study_id,
                "protocol_digest": document.protocol_digest, "registry_digest": document.registry_digest,
                "capture_sha256": document.capture_sha256, "inputs_digest": document.inputs_digest,
                "evaluator_revision": document.evaluator_revision, "source_kind_claim": document.source_kind_claim,
                "evaluated_at": _stamp(document.evaluated_at), "result_digest": document.result_digest,
                "failure": None if failure is None else
                    {"code": failure.code, "slot_index": failure.slot_index, "phase": failure.phase}}
    except ResearchOutcomeError:
        raise
    except (AttributeError, TypeError, ValueError, OverflowError):
        raise ResearchOutcomeError("RESEARCH_OUTCOME_DOCUMENT_INVALID") from None


def outcome_document_bytes(document: CandidateOutcomeDocument) -> bytes:
    """Canonical ASCII JSON bytes, without a newline or any signature/status grant."""
    raw = json.dumps(_body(document), sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                     allow_nan=False).encode("ascii")
    _require(len(raw) <= MAX_OUTCOME_BYTES, "RESEARCH_OUTCOME_SIZE_INVALID")
    return raw


def outcome_document_digest(document: CandidateOutcomeDocument) -> str:
    """Hash the claimed document, not a legacy ValidationResult or issued receipt."""
    raw = outcome_document_bytes(document)
    domain = _EVALUATED_DOMAIN if document.status == "EVALUATED" else _FAILURE_DOMAIN
    return hashlib.sha256(domain + raw).hexdigest()


def _check_depth(raw):
    # Bound nesting before the JSON decoder allocates a nested object graph. Scan
    # only ASCII structural bytes and honor escapes inside UTF-8 JSON strings.
    depth, quoted, escaped = 0, False, False
    for value in raw:
        if quoted:
            if escaped:
                escaped = False
            elif value == 92:
                escaped = True
            elif value == 34:
                quoted = False
        elif value == 34:
            quoted = True
        elif value in (91, 123):
            depth += 1
            _require(depth <= _MAX_JSON_DEPTH, "RESEARCH_OUTCOME_JSON_INVALID")
        elif value in (93, 125):
            depth -= 1
            _require(depth >= 0, "RESEARCH_OUTCOME_JSON_INVALID")
    _require(depth == 0 and not quoted, "RESEARCH_OUTCOME_JSON_INVALID")


def _pairs(pairs):
    body = {}
    for key, value in pairs:
        _require(key not in body, "RESEARCH_OUTCOME_JSON_INVALID")
        body[key] = value
    return body


def _integer(text):
    _require(len(text) <= 6, "RESEARCH_OUTCOME_JSON_INVALID")
    return int(text)


def _no_number(text):
    # Every numeric document field is an exact integer. No exponent, float,
    # non-finite constant or coerced numeric string is accepted.
    raise ResearchOutcomeError("RESEARCH_OUTCOME_JSON_INVALID")


def parse_outcome_document(raw: bytes) -> CandidateOutcomeDocument:
    """Parse metadata only; a prospective label or valid digest proves nothing."""
    _require(type(raw) is bytes and 0 < len(raw) <= MAX_OUTCOME_BYTES, "RESEARCH_OUTCOME_SIZE_INVALID")
    _check_depth(raw)
    try:
        body = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs, parse_int=_integer,
                          parse_float=_no_number, parse_constant=_no_number)
    except ResearchOutcomeError:
        raise
    except (ValueError, TypeError, UnicodeError, OverflowError, RecursionError):
        raise ResearchOutcomeError("RESEARCH_OUTCOME_JSON_INVALID") from None
    _require(type(body) is dict and set(body) == _FIELDS, "RESEARCH_OUTCOME_SCHEMA_INVALID")
    failure = body["failure"]
    if failure is not None:
        _require(type(failure) is dict and set(failure) == _FAILURE_FIELDS,
                 "RESEARCH_OUTCOME_FAILURE_INVALID")
        failure = EvaluationFailureDetail(**failure)
    return CandidateOutcomeDocument(**(body | {"evaluated_at": _parse_time(body["evaluated_at"]),
                                               "failure": failure}))


def validate_outcome_set(outcomes: tuple[CandidateOutcomeDocument, ...], *,
                         expected_study_ids: tuple[str, ...]) -> tuple[CandidateOutcomeDocument, ...]:
    """Check a caller-declared CURRENT candidate set and return it sorted by ID.

    This does not verify a plan, prior attempts or K. Every supplied document is
    checked; a failed or unprofitable candidate cannot be silently dropped here.
    Returning a tuple does not issue evaluation evidence or authenticate a family.
    """
    _require(type(expected_study_ids) is tuple and 1 <= len(expected_study_ids) <= MAX_OUTCOME_MEMBERS
             and all(_identifier(value) for value in expected_study_ids)
             and expected_study_ids == tuple(sorted(set(expected_study_ids))),
             "RESEARCH_OUTCOME_EXPECTED_SET_INVALID")
    _require(type(outcomes) is tuple and len(outcomes) == len(expected_study_ids),
             "RESEARCH_OUTCOME_SET_MISMATCH")
    for document in outcomes:
        _body(document)
    ordered = tuple(sorted(outcomes, key=lambda document: document.study_id))
    _require(tuple(document.study_id for document in ordered) == expected_study_ids,
             "RESEARCH_OUTCOME_SET_MISMATCH")
    return ordered
