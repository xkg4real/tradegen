"""Unsigned handoff tests with invented source/program bytes; no owner approval."""
from contextlib import ExitStack
from copy import deepcopy
from dataclasses import asdict, replace
from datetime import timedelta
from decimal import Decimal
from functools import lru_cache
import hashlib
import json
from unittest.mock import patch

from execution_launch.profile import profile_contract_digest
from execution_launch.program import ProgramSpec, parameters_json, program_digest
from execution_launch.review_request import (
    MAX_REQUEST_BYTES, ReviewRequestError, build_review_request, parse_review_request, review_request_json,
)
from execution_launch.strategy import StrategyEvidenceError, assess_strategy
from tests.launch_profile import fixture_profile
from tests.launch_strategy import START, fixture_capture


@lru_cache(maxsize=3)
def fixture(kind="prospective_paper_capture"):
    now = START + timedelta(days=250, seconds=1)
    artifact = b"invented review fixture source; no deployed implementation"
    spec = ProgramSpec(schema_version=1, strategy_id="test-strategy", kind="moving_average_trend",
                       fast_window=2, slow_window=3, exposure_fraction=Decimal("1"))
    profile = fixture_profile(now)
    profile = replace(profile, strategy_code_sha256=program_digest(spec, artifact),
                      policy=replace(profile.policy, initial_equity=Decimal("1000")))
    p, _, _, _, _, result, at = fixture_capture(source_kind=kind,
        profile_digest=profile_contract_digest(profile), code_digest=profile.strategy_code_sha256,
        rules=profile.instrument_rules)
    assert now == at
    return profile, p, result, now, artifact, parameters_json(spec)


def request(kind="prospective_paper_capture", **changes):
    profile, protocol, result, now, artifact, parameters = fixture(kind)
    args = dict(profile=profile, protocol=protocol, result=result, now=now,
                program_artifact=artifact, parameters_json=parameters)
    return build_review_request(**(args | changes))


def refused(call, code=None):
    try:
        call()
    except ReviewRequestError as exc:
        if code:
            assert str(exc) == code, (str(exc), code)
        return
    raise AssertionError("invalid review request accepted")


def rehash(body):
    value = {k: v for k, v in body.items() if k != "request_sha256"}
    body["request_sha256"] = hashlib.sha256(json.dumps(value, sort_keys=True,
        separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")).hexdigest()
    return json.dumps(body)


def test_computed_request_binds_actual_inputs_and_leaves_all_review_authority_pending():
    profile, p, result, _, artifact, _ = fixture()
    body = request()
    assert body["computed_summary"]["mathematical_criteria_met"] is True
    assert body["source_kind_claim"] == "prospective_paper_capture"
    assert body["bindings"]["program_digest"] == profile.strategy_code_sha256 == p.strategy_code_sha256
    assert body["bindings"]["program_artifact_sha256"] == hashlib.sha256(artifact).hexdigest()
    assert body["bindings"]["inputs_digest"] == result.inputs_digest
    assert body["bindings"]["registry_digest"] == result.registry_digest
    assert all(value is False for value in body["authority"].values())
    assert all(row["reviewed"] is None and row["evidence_sha256"] is None for row in body["required_checks"])
    assert body["reviewer_id"] is body["review_public_key"] is body["review_signature"] is None
    assert "SIGNED_CONTEXT_REQUIRED" in body["profile_blockers"]
    assert body["assessment_reasons"] == ["STRATEGY_TRUSTED_REVIEW_REQUIRED"]
    text = review_request_json(body)
    assert profile.account_scope not in text and profile.profile_id not in text


def test_actual_program_parameters_profile_and_capital_must_match_computed_study():
    profile, p, _, _, _, parameters = fixture()
    refused(lambda: request(program_artifact=b"unrelated private artifact"), "REVIEW_PROGRAM_OR_PROFILE_MISMATCH")
    refused(lambda: request(parameters_json=" " + parameters), "REVIEW_PARAMETERS_FORMAT_INVALID")
    refused(lambda: request(profile=replace(profile, account_scope="other-account")),
            "REVIEW_PROGRAM_OR_PROFILE_MISMATCH")
    changed = replace(profile, policy=replace(profile.policy, initial_equity=Decimal("2000")))
    refused(lambda: request(profile=changed, protocol=replace(p,
        profile_contract_digest=profile_contract_digest(changed))), "REVIEW_CAPITAL_MISMATCH")


def test_imported_summary_or_rebuilt_result_is_not_computed_evidence_for_a_request():
    _, _, result, _, _, _ = fixture()
    refused(lambda: request(result=asdict(result)), "REVIEW_COMPUTED_EVIDENCE_OR_INPUT_INVALID")
    refused(lambda: request(result=replace(result)), "REVIEW_COMPUTED_EVIDENCE_OR_INPUT_INVALID")


def test_changed_protocol_cannot_relabel_a_previously_computed_result():
    _, p, _, _, _, _ = fixture()
    refused(lambda: request(protocol=replace(p, seed=p.seed + 1)), "REVIEW_PROTOCOL_RESULT_MISMATCH")


def test_request_roundtrip_never_accepts_approval_fields_even_with_a_recomputed_hash():
    body = request()
    assert parse_review_request(review_request_json(body)) == body
    for name in body["authority"]:
        changed = deepcopy(body)
        changed["authority"][name] = True
        refused(lambda: parse_review_request(rehash(changed)), "REVIEW_REQUEST_CANNOT_GRANT_AUTHORITY")
    for name in ("reviewer_id", "review_public_key", "review_signature", "deployment_code_hash"):
        changed = deepcopy(body); changed[name] = "supplied-but-unverified"
        refused(lambda: parse_review_request(rehash(changed)), "REVIEW_REQUEST_CANNOT_CONTAIN_APPROVAL")
    changed = deepcopy(body); changed["required_checks"][0]["reviewed"] = True
    refused(lambda: parse_review_request(rehash(changed)), "REVIEW_REQUEST_REVIEW_MUST_REMAIN_PENDING")
    changed = deepcopy(body); changed["PASS"] = True
    refused(lambda: parse_review_request(rehash(changed)), "REVIEW_REQUEST_SCHEMA_INVALID")


def test_import_is_only_unsigned_integrity_and_cannot_be_used_as_strategy_evidence():
    profile, p, _, now, _, _ = fixture()
    body = request(); body["computed_summary"]["metrics"]["total_return"] += 1
    refused(lambda: parse_review_request(json.dumps(body)), "REVIEW_REQUEST_DIGEST_MISMATCH")
    imported = parse_review_request(rehash(body))
    assert not any(imported["authority"].values())
    try:
        assess_strategy(p, imported, profile_contract_digest=profile_contract_digest(profile),
            rule_terms_digest=p.rule_terms_digest, strategy_code_sha256=p.strategy_code_sha256, now=now)
    except StrategyEvidenceError as exc:
        assert str(exc) == "STRATEGY_COMPUTED_RESULT_REQUIRED"
    else:
        raise AssertionError("unsigned imported summary became strategy evidence")


def test_replay_claim_and_expired_evidence_remain_visible_without_any_authority():
    body = request("retrospective_replay")
    assert body["source_kind_claim"] == "retrospective_replay"
    assert "STRATEGY_NONPROSPECTIVE_SOURCE" in body["assessment_reasons"]
    _, p, _, now, _, _ = fixture()
    stale = request(now=now + timedelta(seconds=p.review_max_age_seconds + 1))
    assert "STRATEGY_EVIDENCE_STALE_OR_FUTURE" in stale["assessment_reasons"]
    assert not any(stale["authority"].values())


def test_duplicate_nonfinite_unknown_and_oversized_json_is_refused_without_echo():
    for raw in (b"\xff", '{"private":"secret","private":"value"}', '{"x":NaN}',
                " " * (MAX_REQUEST_BYTES + 1), "null", "[]"):
        refused(lambda: parse_review_request(raw))
    changed = request(); changed["source_kind_claim"] = "claimed-live-PASS-secret"
    refused(lambda: parse_review_request(rehash(changed)), "REVIEW_SOURCE_KIND_INVALID")


def test_request_preparation_reads_no_owner_state_key_environment_or_network():
    fixture()
    with ExitStack() as stack:
        for target in ("core.compliance.owner.load_context", "core.compliance.owner.read_pubkey",
                       "pathlib.Path.read_bytes", "pathlib.Path.home", "os.getenv",
                       "socket.create_connection", "socket.socket"):
            stack.enter_context(patch(target, side_effect=AssertionError("unexpected side effect")))
        assert not request()["authority"]["execution_ready"]
