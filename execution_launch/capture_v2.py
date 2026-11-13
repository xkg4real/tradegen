"""Strict fixed carry capture evidence; importing it never authenticates a source.

The archive commits canonical program parameters and the actual artifact hash
recorded by capture. Import re-derives every typed decision, including the final
bar. Artifact provenance still needs independent review against installed code.
Legacy capture/PaperDecision bytes are a separate, unchanged wire format.
"""
from __future__ import annotations

from dataclasses import dataclass, fields
from datetime import datetime, timedelta
from decimal import Decimal
from fractions import Fraction
import hashlib
import json
import re

from execution_control.capability import digest
from execution_launch import managed_behavior as M
from execution_launch.program import ProgramSpec, parameters_json, parse_program, program_digest
from execution_launch.strategy import (
    ForwardProtocol, PaperBar, Registration, evidence_digest, parse_protocol,
    protocol_json, validate_registry,
)

MAX_CAPTURE_BYTES = 16 * 1024 * 1024
_MAX_ROWS = 20000
_KINDS = ("prospective_paper_capture", "retrospective_replay", "synthetic")
_DECIMAL = re.compile(r"(?:0|[1-9][0-9]*)(?:\.[0-9]+)?")
_SHA = re.compile(r"[0-9a-f]{64}")


class CaptureV2Error(ValueError):
    """Fixed diagnostics only; malformed evidence is never an unavailable input."""


def _require(condition, code):
    if not condition:
        raise CaptureV2Error(code)


@dataclass(frozen=True, kw_only=True)
class CaptureArchiveV2:
    schema_version: int
    registry: tuple[Registration, ...]
    source_kind: str
    program_parameters_json: str
    program_artifact_sha256: str
    behavior_sha256: str
    bars: tuple[PaperBar, ...]
    decisions: tuple[M.FixedDecisionV2, ...]

    @property
    def program(self) -> ProgramSpec:
        return parse_program(self.program_parameters_json)


def _structure(archive):
    _require(type(archive) is CaptureArchiveV2 and type(archive.schema_version) is int
             and archive.schema_version == 2, "CAPTURE_V2_SCHEMA_INVALID")
    _require(type(archive.source_kind) is str and archive.source_kind in _KINDS,
             "CAPTURE_V2_SOURCE_INVALID")
    validate_registry(archive.registry)
    _require(type(archive.program_parameters_json) is str, "CAPTURE_V2_PROGRAM_REQUIRED")
    program = archive.program
    _require(program.schema_version == 1 and program.kind in ("cash", "moving_average_trend")
             and parameters_json(program) == archive.program_parameters_json,
             "CAPTURE_V2_PROGRAM_FORMAT_OR_KIND_INVALID")
    _require(type(archive.program_artifact_sha256) is str
             and _SHA.fullmatch(archive.program_artifact_sha256) is not None,
             "CAPTURE_V2_ARTIFACT_DIGEST_INVALID")
    _require(type(archive.behavior_sha256) is str and archive.behavior_sha256 == M.behavior_digest(),
             "CAPTURE_V2_BEHAVIOR_MISMATCH")
    _require(type(archive.bars) is tuple and type(archive.decisions) is tuple
             and len(archive.bars) == len(archive.decisions) <= _MAX_ROWS
             and all(type(row) is PaperBar for row in archive.bars)
             and all(type(row) is M.FixedDecisionV2 for row in archive.decisions),
             "CAPTURE_V2_ROWS_INVALID")
    for decision in archive.decisions:
        # Recheck frozen dataclasses too; construction alone is not a trust boundary.
        M.parse_decision_document(M.decision_document(decision))
    return program


def _binding(protocol, archive):
    _require(type(protocol) is ForwardProtocol, "CAPTURE_V2_PROTOCOL_REQUIRED")
    parse_protocol(protocol_json(protocol))
    _require(M.resolve_behavior(protocol) == M.BEHAVIOR_REVISION,
             "CAPTURE_V2_PROTOCOL_REVISION_MISMATCH")
    program = _structure(archive)
    _require(program.strategy_id == protocol.strategy_id and digest({
        "artifact_sha256": archive.program_artifact_sha256,
        "parameters": json.loads(archive.program_parameters_json),
    }) == protocol.strategy_code_sha256, "CAPTURE_V2_PROGRAM_BINDING_MISMATCH")
    _require(any(row.study_id == protocol.study_id and row.protocol_digest == evidence_digest(protocol)
                 and row.registered_at == protocol.preregistered_at for row in archive.registry),
             "CAPTURE_V2_PROTOCOL_NOT_REGISTERED")
    spacing = timedelta(seconds=protocol.bar_seconds)
    span = protocol.capture_end - protocol.capture_start
    _require(span % spacing == timedelta(0) and 2 <= span // spacing + 1 <= _MAX_ROWS,
             "CAPTURE_V2_WINDOW_GRID_INVALID")
    return program


def validate_bar_v2(protocol, bar, index, decided_at) -> None:
    """Use the fixed driver's exact midpoint definition without changing legacy bars."""
    from execution_launch.paper_capture import _bar

    _bar(protocol, bar, index, decided_at)
    _require(Fraction(bar.mark) == (Fraction(bar.bid) + Fraction(bar.ask)) / 2,
             "CAPTURE_V2_MARK_NOT_MIDPOINT")
    _require(decided_at < bar.observed_at + timedelta(seconds=protocol.bar_seconds),
             "CAPTURE_V2_DECISION_TOO_LATE")


def validate_capture_v2(protocol, archive) -> None:
    """Recompute complete prefix evidence; unavailable/malformed records cannot replace bars."""
    program = _binding(protocol, archive)
    _require(len(archive.bars) >= 2 and archive.bars[-1].observed_at == protocol.capture_end,
             "CAPTURE_V2_WINDOW_INCOMPLETE")
    chain, marks, previous_time = "", (), None
    for index, (bar, decision) in enumerate(zip(archive.bars, archive.decisions)):
        validate_bar_v2(protocol, bar, index, decision.decided_at)
        _require(previous_time is None or decision.decided_at >= previous_time,
                 "CAPTURE_V2_DECISION_CLOCK_ROLLBACK")
        chain = evidence_digest((chain, bar))
        marks += (bar.mark,)
        expected = M.derive_fixed_decision_v2(program, marks, bar_index=index,
            decided_at=decision.decided_at, history_sha256=chain, input_status="available")
        _require(M.decision_document(decision) == M.decision_document(expected),
                 "CAPTURE_V2_DECISION_REDERIVATION_MISMATCH")
        previous_time = decision.decided_at


def make_archive_v2(registry, source_kind, program, *, program_artifact, bars, decisions):
    """Capture-side commitment from actual supplied bytes, including incomplete evidence."""
    program_digest(program, program_artifact)  # Validates the real artifact bound below.
    result = CaptureArchiveV2(schema_version=2, registry=registry, source_kind=source_kind,
        program_parameters_json=parameters_json(program),
        program_artifact_sha256=hashlib.sha256(program_artifact).hexdigest(),
        behavior_sha256=M.behavior_digest(), bars=bars, decisions=decisions)
    _structure(result)
    return result


def capture_json_v2(archive) -> str:
    """Preserve incomplete trials too; only strict import can accept a complete study."""
    from execution_launch.paper_capture import _plain

    _structure(archive)
    body = {"schema_version": 2, "registry": _plain(archive.registry),
        "source_kind": archive.source_kind, "program_parameters_json": archive.program_parameters_json,
        "program_artifact_sha256": archive.program_artifact_sha256,
        "behavior_sha256": archive.behavior_sha256, "bars": _plain(archive.bars),
        "decisions": [M.decision_document(decision) for decision in archive.decisions]}
    raw = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False) + "\n"
    _require(len(raw.encode("utf-8")) <= MAX_CAPTURE_BYTES, "CAPTURE_V2_JSON_TOO_LARGE")
    return raw


def parse_capture_v2(protocol, raw) -> CaptureArchiveV2:
    """Closed schema import with duplicate-key, finite-value and complete re-derivation checks."""
    from execution_launch.paper_capture import _amount, _date, _sha

    _require(type(raw) in (str, bytes) and len(raw) <= MAX_CAPTURE_BYTES, "CAPTURE_V2_JSON_SIZE_OR_TYPE")

    def unique(pairs):
        result = {}
        for key, value in pairs:
            _require(key not in result, "CAPTURE_V2_JSON_DUPLICATE_KEY")
            result[key] = value
        return result

    def invalid(value):
        raise CaptureV2Error("CAPTURE_V2_JSON_NUMBER_INVALID")

    def closed(body, cls):
        _require(type(body) is dict and set(body) == {field.name for field in fields(cls)},
                 "CAPTURE_V2_JSON_SCHEMA_INVALID")
        return dict(body)

    try:
        body = closed(json.loads(raw, object_pairs_hook=unique, parse_float=invalid,
                                 parse_constant=invalid), CaptureArchiveV2)
        _require(type(body["registry"]) is list and len(body["registry"]) <= 1000
                 and type(body["bars"]) is list and type(body["decisions"]) is list
                 and 2 <= len(body["bars"]) <= _MAX_ROWS
                 and len(body["bars"]) == len(body["decisions"]), "CAPTURE_V2_ROWS_INVALID")
        registry, bars = [], []
        for item in body["registry"]:
            row = closed(item, Registration)
            row["registered_at"] = _date(row["registered_at"])
            registry.append(Registration(**row))
        for item in body["bars"]:
            row = closed(item, PaperBar)
            for key in ("observed_at", "received_at"):
                row[key] = _date(row[key])
            for key in ("bid", "ask", "mark", "quote_krw"):
                value = row[key]
                _require(type(value) is str and len(value) <= 72 and _DECIMAL.fullmatch(value) is not None,
                         "CAPTURE_V2_DECIMAL_STRING_REQUIRED")
                row[key] = Decimal(value)
                _amount(row[key])
            _sha(row["source_sha256"])
            bars.append(PaperBar(**row))
        archive = CaptureArchiveV2(**(body | {"registry": tuple(registry), "bars": tuple(bars),
            "decisions": tuple(M.parse_decision_document(item) for item in body["decisions"])}))
        validate_capture_v2(protocol, archive)
        return archive
    except CaptureV2Error:
        raise
    except (ValueError, TypeError, UnicodeError, RecursionError, ArithmeticError):
        raise CaptureV2Error("CAPTURE_V2_JSON_INVALID") from None
