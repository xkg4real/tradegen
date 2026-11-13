"""Authenticate the frozen study selection against owner-signed source reviews.

    python -m execution_launch.study_review select-reviewed --plan PLAN.json --profile PROFILE.json --captures DIR --evaluated-at ORIGINAL_EVALUATION_TIME --review A.signed-review.json --review B.signed-review.json

The ordinary study select command first emits unsigned requests. The owner reviews
the original sources, full trial family and implementation, then signs those
requests using the standalone signer. This command recomputes every candidate at
the original evaluation time and verifies those detached signatures against fresh
owner authority. No imported PASS, matching hash or claimed source label is a
review. All numerically eligible, rankable candidates need a signed review; one
missing, invalid or expired review refuses the whole authenticated selection.

Only main() reads explicit files and the current owner context. It reads no API
credential, signs nothing, writes nothing and grants no order capability. Import
has no I/O. The selected row remains execution_ready=False: runtime implementation,
account evidence, risk, fresh rules and owner session approval are separate gates.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
import hashlib
import json
import sys

from execution_control.owner_authority import CurrentOwnerAuthority, OwnerAuthorityError
from execution_launch.profile import (LaunchProfile, ProfileError, parse_profile_json,
                                      preflight_profile, profile_contract_digest, rule_terms_digest)
from execution_launch.program import parameters_json, program_digest
from execution_launch.review_auth import (MAX_DOCUMENT_BYTES, ReviewAuthenticationError,
                                           parse_review_document, verify_source_review)
from execution_launch.review_request import build_family_commitment, computed_summary
from execution_launch.managed_behavior import CARRY_EVALUATOR_REVISION
from execution_launch.strategy import (ReviewBinding, StrategyEvidenceError, _plain,
                                       evidence_digest)
from execution_launch import strategy as _evaluator
from execution_launch.study_evidence import (DEFAULT_LIMITS, EvaluatedCandidate, FamilyEvaluation,
                                             StudyEvidenceError, evaluate_study_family)
from execution_launch.study import (MarketSelection, PROGRAM_SOURCE, StudyError, StudyPlan,
                                    _MAX_PLAN_BYTES, _fixed_file, parse_study_plan,
                                    load_capture_family, rank_market_evidence, validate_study_plan)
from execution_launch.workflow import (MAX_CONFIG_BYTES, WorkflowError,
                                       _CODE, _base, _read_file, _time)


class StudyReviewError(ValueError):
    """Fixed diagnostics only, never paths, amounts, external text or owner state."""


def _need(value, code):
    if not value:
        raise StudyReviewError(code)


def _aware(value):
    _need(type(value) is datetime and value.utcoffset() is not None, "STUDY_REVIEW_TIME_INVALID")
    return value.astimezone(timezone.utc)


@dataclass(frozen=True, kw_only=True)
class AuthenticatedSelection:
    selection: MarketSelection
    evaluated_at: datetime
    verified_at: datetime
    authenticated_study_ids: tuple[str, ...]
    source_reviews_authenticated: bool
    implementation_authenticated: bool = False
    execution_ready: bool = False


def _binding(candidate, result):
    protocol = candidate.protocol
    return ReviewBinding(protocol_digest=evidence_digest(protocol), evidence_digest=evidence_digest(result),
        registry_digest=result.registry_digest, inputs_digest=result.inputs_digest,
        strategy_id=protocol.strategy_id, strategy_code_sha256=protocol.strategy_code_sha256,
        profile_contract_digest=protocol.profile_contract_digest, rule_terms_digest=protocol.rule_terms_digest,
        capture_end=result.ended_at,
        **({"evaluator_revision": protocol.evaluator_revision, "behavior_revision": protocol.behavior_revision,
            "terminal_accounting": protocol.terminal_accounting,
            "management_behavior_sha256": protocol.management_behavior_sha256,
            "computed_summary_sha256": evidence_digest(computed_summary(result, mathematical_criteria_met=True))}
           if protocol.evaluator_revision == CARRY_EVALUATOR_REVISION else {}))


def _request_matches(candidate, result, profile, artifact, body, evaluated_at):
    request, bindings = body["request"], body["request"]["bindings"]
    protocol, program = candidate.protocol, candidate.program
    variant = replace(profile, strategy_id=program.strategy_id,
                      strategy_code_sha256=program_digest(program, artifact))
    expected = {
        "protocol_digest": evidence_digest(protocol), "evidence_digest": evidence_digest(result),
        "registry_digest": result.registry_digest, "inputs_digest": result.inputs_digest,
        "profile_contract_digest": profile_contract_digest(variant),
        "rule_terms_digest": rule_terms_digest(profile.instrument_rules,
                                               universe_rule_sha256=profile.universe_rule_sha256),
        "program_digest": variant.strategy_code_sha256,
        "program_artifact_sha256": hashlib.sha256(artifact).hexdigest(),
        "canonical_parameters_sha256": hashlib.sha256(parameters_json(program).encode("ascii")).hexdigest(),
        "capture_source_code_sha256": protocol.capture_source_code_sha256,
    }
    _need(request["study_id"] == protocol.study_id and request["strategy_id"] == program.strategy_id
          and request["capture_source_id"] == protocol.capture_source_id
          and request["evaluator_revision"] == protocol.evaluator_revision
          and request["capture_start"] == protocol.capture_start.astimezone(timezone.utc).isoformat(timespec="microseconds")
          and request["capture_end"] == protocol.capture_end.astimezone(timezone.utc).isoformat(timespec="microseconds")
          and request["review_deadline"] == (protocol.capture_end + timedelta(
              seconds=protocol.review_max_age_seconds)).astimezone(timezone.utc).isoformat(timespec="microseconds")
          and request["evaluated_at"] == evaluated_at.isoformat(timespec="microseconds")
          and request["source_kind_claim"] == result.source_kind
          and all(bindings[name] == value for name, value in expected.items()),
          "STUDY_REVIEW_COMPUTED_BINDING_MISMATCH")
    if protocol.evaluator_revision == CARRY_EVALUATOR_REVISION:
        _need(request["schema_version"] == 4 and all(request[name] == getattr(protocol, name) for name in
              ("behavior_revision", "terminal_accounting", "management_behavior_sha256")),
              "STUDY_REVIEW_COMPUTED_BINDING_MISMATCH")
    summary = computed_summary(result, mathematical_criteria_met=True)
    _need(request["computed_summary"] == summary, "STUDY_REVIEW_COMPUTED_SUMMARY_MISMATCH")
    # runtime_profile_digest includes the observation asof. A fresh observation
    # may change asof, but the unchanged source and economics remain bound by
    # profile_contract_digest and rule_terms_digest and checked again by E2.


def authenticate_study_selection(plan: StudyPlan, *, profile: LaunchProfile,
                                 captures: Mapping[str, str | bytes], reviews: Mapping[str, str | bytes],
                                 evaluated_at: datetime, clock, authority_provider) -> AuthenticatedSelection:
    """Recompute the complete family and authenticate all rankable source reviews.

    clock and authority_provider are trusted deployment dependencies, never
    deserialized from JSON. The CLI supplies CurrentOwnerAuthority itself. Raw
    captures, rather than imported metrics or ValidationResults, are required.
    Every original is snapshotted and checked before any candidate arithmetic
    or owner-signature verification. Numerical failures remain in that family.
    A fresh current profile is required, with the same frozen policy/source/terms.
    The original evaluated_at is reproducibility metadata, not the approval clock.
    """
    validate_study_plan(plan)
    _need(type(profile) is LaunchProfile and profile.instrument_rules is not None,
          "STUDY_REVIEW_PROFILE_REQUIRED")
    _need(callable(clock) and callable(authority_provider), "STUDY_REVIEW_PROVIDERS_REQUIRED")
    initial_now, evaluated_at = _aware(clock()), _aware(evaluated_at)
    _need(evaluated_at <= initial_now, "STUDY_REVIEW_EVALUATION_IN_FUTURE")
    ids = {candidate.protocol.study_id for candidate in plan.candidates}
    _need(isinstance(captures, Mapping) and set(captures) == ids
          and all(type(value) in (str, bytes) for value in captures.values()),
          "STUDY_REVIEW_CAPTURE_FAMILY_INCOMPLETE")
    _need(isinstance(reviews, Mapping) and set(reviews) <= ids
          and all(type(value) in (str, bytes) and len(value) <= MAX_DOCUMENT_BYTES for value in reviews.values()),
          "STUDY_REVIEW_DOCUMENT_FAMILY_INVALID")
    # Public callers still supply originals and receive one actual full-family
    # evaluation. The private shared backend never simulates or issues results.
    evaluated = evaluate_study_family(tuple(candidate.protocol for candidate in plan.candidates),
        captures, profile.instrument_rules, registry=plan.registry, now=evaluated_at)
    return _authenticate_evaluated_selection(plan, profile=profile, evaluated=evaluated,
        reviews=reviews, evaluated_at=evaluated_at, clock=clock,
        authority_provider=authority_provider, initial_now=initial_now)


def _family_stamp(evaluated):
    """Recheck retained identities/bytes; a copied display object grants no trust."""
    _need(type(evaluated) is FamilyEvaluation, "STUDY_REVIEW_EVALUATED_FAMILY_INVALID")
    members = getattr(evaluated, "rows", None)
    _need(type(members) is tuple
          and 0 < len(members) <= DEFAULT_LIMITS.max_candidates,
          "STUDY_REVIEW_EVALUATED_FAMILY_INVALID")
    rows, total = [], 0
    for row in members:
        _need(type(row) is EvaluatedCandidate and type(getattr(row, "study_id", None)) is str
              and type(getattr(row, "raw_capture", None)) is bytes
              and type(getattr(row, "capture_sha256", None)) is str,
              "STUDY_REVIEW_EVALUATED_FAMILY_INVALID")
        total += len(row.raw_capture)
        _need(len(row.raw_capture) <= DEFAULT_LIMITS.max_capture_bytes and total <= DEFAULT_LIMITS.max_total_bytes,
              "STUDY_REVIEW_RESOURCE_LIMIT")
        _need(hashlib.sha256(row.raw_capture).hexdigest() == row.capture_sha256,
              "STUDY_REVIEW_CAPTURE_HASH_MISMATCH")
        _need(type(getattr(row, "result", None)) in (_evaluator.ValidationResult, _evaluator.CarryValidationResult),
              "STUDY_REVIEW_ACTUAL_RESULT_REQUIRED")
        try:
            digest = evidence_digest(row.result)
        except (AttributeError, TypeError, OverflowError, RecursionError):
            raise StudyReviewError("STUDY_REVIEW_RESULT_NOT_ISSUED_OR_MUTATED") from None
        issued = _evaluator._EVALUATED.get(id(row.result))
        _need(issued is not None and issued[0] is row.result and issued[1] == digest,
              "STUDY_REVIEW_RESULT_NOT_ISSUED_OR_MUTATED")
        rows.append((id(row), row.study_id, row.capture_sha256, id(row.result), digest))
    return id(members), tuple(rows)


def _validated_evaluated_family(plan, evaluated, *, profile, evaluated_at):
    """Parse all retained originals and bind actual issuance without re-evaluation.

    FamilyEvaluation has no privileged constructor. Every row, including a
    numerically rejected candidate, must match its actual registry-issued result,
    original raw bytes and this exact plan. This does not prove sealed storage or
    source provenance; the sealed orchestrator and signed review retain those
    separate responsibilities.
    """
    stamp = _family_stamp(evaluated)
    by_id = {row.study_id: row for row in evaluated.rows}
    _need(len(by_id) == len(evaluated.rows)
          and set(by_id) == {candidate.protocol.study_id for candidate in plan.candidates},
          "STUDY_REVIEW_EVALUATED_FAMILY_INCOMPLETE")
    registry_digest = _evaluator.validate_registry(plan.registry)
    for candidate in plan.candidates:
        protocol = candidate.protocol
        row = by_id[protocol.study_id]
        result = row.result
        if protocol.evaluator_revision == CARRY_EVALUATOR_REVISION:
            _need(type(result) is _evaluator.CarryValidationResult, "STUDY_REVIEW_ACTUAL_RESULT_REQUIRED")
            archive = _evaluator._decode_carry_capture(protocol, row.raw_capture)
            protocol_digest = _evaluator._carry_validation_inputs(protocol, archive, profile.instrument_rules,
                                                                   now=evaluated_at)
            captured_registry = _evaluator.validate_registry(archive.registry)
            inputs_digest, source_kind = evidence_digest(archive), archive.source_kind
        else:
            _need(type(result) is _evaluator.ValidationResult, "STUDY_REVIEW_ACTUAL_RESULT_REQUIRED")
            registry, source_kind, bars, decisions = _evaluator._decode_paper_capture(row.raw_capture)
            protocol_digest, captured_registry = _evaluator._paper_validation_inputs(protocol, bars, decisions,
                profile.instrument_rules, registry=registry, source_kind=source_kind, now=evaluated_at)
            inputs_digest = evidence_digest((bars, decisions))
        _need(captured_registry == registry_digest == result.registry_digest
              and result.protocol_digest == protocol_digest and result.inputs_digest == inputs_digest
              and result.source_kind == source_kind and result.started_at == protocol.capture_start
              and result.ended_at == protocol.capture_end and result.evaluated_at == evaluated_at,
              "STUDY_REVIEW_EVALUATED_INPUT_MISMATCH")
    _need(_family_stamp(evaluated) == stamp, "STUDY_REVIEW_EVALUATED_FAMILY_CHANGED")
    return {identifier: row.result for identifier, row in by_id.items()}, stamp


def _authenticate_evaluated_selection(plan: StudyPlan, *, profile: LaunchProfile,
                                      evaluated: FamilyEvaluation, reviews: Mapping[str, str | bytes],
                                      evaluated_at: datetime, clock, authority_provider,
                                      initial_now: datetime | None = None) -> AuthenticatedSelection:
    """Shared actual-result backend; never a public imported-result approval API.

    The existing public path evaluates raw captures once; the sealed path calls
    its own actual sealed evaluator once. This backend validates exact complete
    inputs and issuance, then uses the same review/ranking policy for both. It
    neither resets registry capacity nor promotes a manifest/summary to evidence.
    The sealed caller additionally supplies its actual provider and storage gates.
    """
    validate_study_plan(plan)
    _need(type(profile) is LaunchProfile and profile.instrument_rules is not None,
          "STUDY_REVIEW_PROFILE_REQUIRED")
    _need(callable(clock) and callable(authority_provider), "STUDY_REVIEW_PROVIDERS_REQUIRED")
    initial_now = _aware(clock()) if initial_now is None else _aware(initial_now)
    evaluated_at = _aware(evaluated_at)
    _need(evaluated_at <= initial_now, "STUDY_REVIEW_EVALUATION_IN_FUTURE")
    ids = {candidate.protocol.study_id for candidate in plan.candidates}
    _need(isinstance(reviews, Mapping) and set(reviews) <= ids
          and all(type(value) in (str, bytes) and len(value) <= MAX_DOCUMENT_BYTES for value in reviews.values()),
          "STUDY_REVIEW_DOCUMENT_FAMILY_INVALID")
    reviews = dict(reviews)
    results, family_stamp = _validated_evaluated_family(plan, evaluated, profile=profile, evaluated_at=evaluated_at)
    artifact = _fixed_file(PROGRAM_SOURCE)
    family = build_family_commitment(plan_digest=validate_study_plan(plan),
        capture_digests=evaluated.capture_digests,
        result_digests={key: evidence_digest(value) for key, value in results.items()})
    now = _aware(clock())
    _need(now >= initial_now, "STUDY_REVIEW_CLOCK_ROLLBACK")
    unreviewed = rank_market_evidence(plan, results, profile=profile, now=now, review_verifier=None)
    eligible = {row.study_id for row in unreviewed.rows
                if row.reasons == ("STRATEGY_TRUSTED_REVIEW_REQUIRED",)}
    _need(set(reviews) == eligible, "STUDY_REVIEW_ELIGIBLE_FAMILY_INCOMPLETE")
    if not eligible:
        _need(_family_stamp(evaluated) == family_stamp, "STUDY_REVIEW_EVALUATED_FAMILY_CHANGED")
        return AuthenticatedSelection(selection=unreviewed, evaluated_at=evaluated_at, verified_at=now,
                                      authenticated_study_ids=(), source_reviews_authenticated=False)
    documents, by_binding, expires = {}, {}, []
    for candidate in plan.candidates:
        identifier = candidate.protocol.study_id
        if identifier not in eligible:
            continue
        variant = replace(profile, strategy_id=candidate.program.strategy_id,
                          strategy_code_sha256=program_digest(candidate.program, artifact))
        report = preflight_profile(variant, now=now)
        _need(set(report.reasons) <= {"SIGNED_CONTEXT_REQUIRED"}, "STUDY_REVIEW_PROFILE_NOT_CURRENT")
        raw = reviews[identifier]
        body = parse_review_document(raw)["body"]
        _need(body["request"]["schema_version"] ==
              (4 if candidate.protocol.evaluator_revision == CARRY_EVALUATOR_REVISION else 2),
              "STUDY_REVIEW_SIGNED_FAMILY_REQUIRED")
        _need(body["request"]["family_commitment"] == family, "STUDY_REVIEW_SIGNED_FAMILY_MISMATCH")
        _request_matches(candidate, results[identifier], profile, artifact, body, evaluated_at)
        binding = _binding(candidate, results[identifier])
        documents[identifier] = raw
        by_binding[evidence_digest(binding)] = identifier
        expires.append(_time(body["expires_at"]))
    last_now, authority_identity = [now], [None]

    def authenticated(binding):
        at = _aware(clock())
        _need(at >= last_now[0], "STUDY_REVIEW_CLOCK_ROLLBACK")
        last_now[0] = at
        identifier = by_binding.get(evidence_digest(binding))
        _need(identifier is not None, "STUDY_REVIEW_BINDING_NOT_REGISTERED")
        authority = authority_provider(at)
        receipt = verify_source_review(binding, documents[identifier], authority=authority, now=at)
        identity = (authority.context.owner.fingerprint, authority.context.code_hash)
        _need(authority_identity[0] in (None, identity), "STUDY_REVIEW_AUTHORITY_CHANGED")
        authority_identity[0] = identity
        return receipt

    # Authenticate first outside assess_strategy's diagnostic wrapper. One bad
    # document must not silently remove a candidate and choose a different winner.
    for candidate in plan.candidates:
        if candidate.protocol.study_id in eligible:
            authenticated(_binding(candidate, results[candidate.protocol.study_id]))
    rank_now = _aware(clock())
    _need(rank_now >= last_now[0], "STUDY_REVIEW_CLOCK_ROLLBACK")
    last_now[0] = rank_now
    selection = rank_market_evidence(plan, results, profile=profile, now=rank_now,
                                    review_verifier=authenticated)
    _need({row.study_id for row in selection.rows if row.status == "QUALIFIED"} == eligible,
          "STUDY_REVIEW_AUTHENTICATION_CHANGED")
    _need(_family_stamp(evaluated) == family_stamp, "STUDY_REVIEW_EVALUATED_FAMILY_CHANGED")
    finished = _aware(clock())
    _need(finished >= last_now[0], "STUDY_REVIEW_CLOCK_ROLLBACK")
    _need(finished < min(expires), "STUDY_REVIEW_EXPIRED_DURING_SELECTION")
    return AuthenticatedSelection(selection=selection, evaluated_at=evaluated_at, verified_at=finished,
        authenticated_study_ids=tuple(sorted(eligible)), source_reviews_authenticated=True)


def _arguments(argv):
    values = sys.argv[1:] if argv is None else argv
    _need(type(values) in (list, tuple) and all(type(value) is str for value in values),
          "STUDY_REVIEW_ARGUMENTS_INVALID")
    if tuple(values) in (("--help",), ("-h",)):
        return "help", {}
    _need(bool(values) and values[0] == "select-reviewed" and len(values) % 2 == 1,
          "STUDY_REVIEW_ARGUMENTS_INVALID")
    required = {"plan", "profile", "captures", "evaluated-at"}
    output = {"review": []}
    for key, value in zip(values[1::2], values[2::2]):
        _need(key.startswith("--") and key[2:] in required | {"review"} and value
              and not value.startswith("--"), "STUDY_REVIEW_ARGUMENTS_INVALID")
        name = key[2:]
        if name == "review":
            _need(len(output[name]) < 128, "STUDY_REVIEW_ARGUMENTS_INVALID")
            output[name].append(value)
        else:
            _need(name not in output, "STUDY_REVIEW_ARGUMENTS_INVALID")
            output[name] = value
    _need(required <= set(output), "STUDY_REVIEW_ARGUMENTS_INVALID")
    return values[0], output


def main(argv=None):
    output = _base("select-reviewed")
    try:
        command, args = _arguments(argv)
        if command == "help":
            print(__doc__)
            return 0
        evaluated_at = _time(args["evaluated-at"])
        plan = parse_study_plan(_read_file(args["plan"], _MAX_PLAN_BYTES))
        profile = parse_profile_json(_read_file(args["profile"], MAX_CONFIG_BYTES))
        captures = load_capture_family(plan, args["captures"])
        reviews = {}
        for path in args["review"]:
            raw = _read_file(path, MAX_DOCUMENT_BYTES)
            identifier = parse_review_document(raw)["body"]["request"]["study_id"]
            _need(identifier not in reviews, "STUDY_REVIEW_DUPLICATE_DOCUMENT")
            reviews[identifier] = raw

        def clock():
            return datetime.now(timezone.utc)

        result = authenticate_study_selection(plan, profile=profile, captures=captures, reviews=reviews,
            evaluated_at=evaluated_at, clock=clock, authority_provider=CurrentOwnerAuthority(clock=clock))
        output.update(workflow_complete=True, selection=_plain(result.selection),
                      research_review_ready=result.selection.status == "SELECTED",
                      evaluated_at=_plain(result.evaluated_at), verified_at=_plain(result.verified_at),
                      authenticated_study_ids=list(result.authenticated_study_ids),
                      source_reviews_authenticated=result.source_reviews_authenticated,
                      implementation_authenticated=False, reasons=list(result.selection.reasons))
        print(json.dumps(output, sort_keys=True, allow_nan=False))
        return 0
    except (StudyReviewError, StudyError, StudyEvidenceError, ReviewAuthenticationError, OwnerAuthorityError,
            StrategyEvidenceError, WorkflowError, ProfileError) as exc:
        code = exc.code if type(exc) is ProfileError else str(exc)
        if _CODE.fullmatch(code) is None:
            code = "STUDY_REVIEW_INPUT_REFUSED"
    except KeyboardInterrupt:
        code = "STUDY_REVIEW_STOPPED"
    except (OSError, ValueError, TypeError, AttributeError, ArithmeticError, RecursionError, KeyError):
        code = "STUDY_REVIEW_INPUT_REFUSED"
    output["reasons"] = [code]
    print(json.dumps(output, sort_keys=True))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
