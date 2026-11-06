"""Authenticated study selection using fake captures and disposable synthetic keys.

No real owner state, credentials, API, signature, account, arm or order is used.
The cryptographic signatures below attest only invented test fixtures.
"""
from __future__ import annotations

import ast
import base64
from contextlib import redirect_stdout
from copy import deepcopy
from dataclasses import asdict, replace
from datetime import timedelta
from functools import lru_cache
import hashlib
from io import StringIO
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

from core.compliance import model as M
from execution_control.owner_authority import ReviewAuthority
from execution_launch import study as S, study_review as R
from execution_launch.driver import DeploymentWindow, describe_fixed_driver, make_fixed_driver
from execution_launch.paper_capture import capture_json
from execution_launch.profile import profile_body
from execution_launch.program import parameters_json, program_digest
from execution_launch.review_auth import review_body, review_signing_bytes
from execution_launch.review_request import build_review_request, build_family_commitment, bind_review_family
from execution_launch.strategy import evidence_digest
from tests.launch_profile import context
from tests.launch_study import A, B, Driver, PRINCIPAL, SCOPE, plan, profile, program


def no_history(*_):
    raise AssertionError("review selection cannot load live history")


@lru_cache(maxsize=1)
def fixture():
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    frozen = plan(500, programs=(A, B, program("fixture-ma-200-250", 200, 250)))
    outcome = Driver(frozen).run()
    at = frozen.candidates[0].protocol.capture_end + timedelta(seconds=60)
    results = {candidate.protocol.study_id: R.evaluate_capture_json(candidate.protocol, capture_json(archive),
        profile().instrument_rules, now=at) for candidate, archive in zip(frozen.candidates, outcome.archives)}
    env = SimpleNamespace(plan=frozen, outcome=outcome, results=results, now=at)
    now = env.now + timedelta(seconds=2)
    current = profile(instrument_rules=replace(profile().instrument_rules, asof=env.now))
    artifact = S._fixed_file(S.PROGRAM_SOURCE)
    initial = S.rank_market_evidence(env.plan, env.results, profile=current, now=now)
    eligible = {row.study_id for row in initial.rows if row.reasons == ("STRATEGY_TRUSTED_REVIEW_REQUIRED",)}
    key = Ed25519PrivateKey.from_private_bytes(bytes(range(32)))
    public = key.public_key().public_bytes_raw()
    fingerprint = "SHA256:" + hashlib.sha256(public).hexdigest()
    captures = {c.protocol.study_id: capture_json(a) for c, a in zip(env.plan.candidates, env.outcome.archives)}
    family = build_family_commitment(plan_digest=S.validate_study_plan(env.plan),
        capture_digests={key:hashlib.sha256(raw.encode("utf-8")).hexdigest() for key,raw in captures.items()},
        result_digests={key:evidence_digest(value) for key,value in env.results.items()})
    docs, bodies = {}, {}
    for candidate in env.plan.candidates:
        identifier = candidate.protocol.study_id
        if identifier not in eligible:
            continue
        variant = replace(current, strategy_id=candidate.program.strategy_id,
                          strategy_code_sha256=program_digest(candidate.program, artifact))
        request = build_review_request(variant, candidate.protocol, env.results[identifier], now=env.now,
            program_artifact=artifact, parameters_json=parameters_json(candidate.program))
        request = bind_review_family(request, family)
        window = DeploymentWindow(deployment_id="synthetic-review-deployment", start=now,
                                  end=now + timedelta(hours=1))
        driver = make_fixed_driver(candidate.program, candidate.protocol, variant, window=window,
            history_provider=no_history, history_verifier=no_history, program_artifact=artifact)
        body = review_body(request, asdict(describe_fixed_driver(driver)), deployment_code_hash="c" * 64,
            audit_sha256=hashlib.sha256(b"synthetic test audit; not an actual owner's review").hexdigest(),
            owner_fingerprint=fingerprint, issued_at=env.now + timedelta(seconds=1),
            expires_at=env.now + timedelta(hours=1))
        bodies[identifier] = body
        docs[identifier] = signed(body, key)
    assert len(docs) >= 2
    assert len(docs) < len(captures), "fixture includes a computed failure before signing"
    return SimpleNamespace(env=env, now=now, profile=current, key=key, public=public, fingerprint=fingerprint,
        documents=docs, bodies=bodies,
        captures=captures)


def signed(body, key):
    return json.dumps({"body": body,
        "signature_b64": base64.b64encode(key.sign(review_signing_bytes(body))).decode("ascii")})


def authority(at, **changes):
    f = fixture()
    ctx = context(at, owner=M.OwnerState(status="OK", fingerprint=f.fingerprint), code_hash="c" * 64)
    return ReviewAuthority(**(dict(context=ctx, public_key_raw=f.public, observed_at=at) | changes))


def select(**changes):
    f = fixture()
    args = dict(profile=f.profile, captures=f.captures, reviews=f.documents,
                evaluated_at=f.env.now, clock=lambda: f.now, authority_provider=authority)
    args.update(changes)
    return R.authenticate_study_selection(f.env.plan, **args)


def refused(call, code=None):
    try:
        call()
    except ValueError as exc:
        if code:
            assert str(exc) == code, (str(exc), code)
        assert PRINCIPAL not in str(exc) and SCOPE not in str(exc)
        return
    raise AssertionError("expected authenticated selection refusal")


def test_signed_complete_family_selects_the_frozen_winner_without_execution_authority():
    result = select()
    assert result.selection.status == "SELECTED"
    assert result.selection.selected_strategy_id == "fixture-ma-1-2-a"
    assert result.authenticated_study_ids == tuple(sorted(fixture().documents))
    assert result.source_reviews_authenticated is True
    assert result.implementation_authenticated is False and result.execution_ready is False
    assert result.selection.execution_ready is False
    assert all(row.evaluated_at == fixture().env.now for row in result.selection.rows)


def test_missing_capture_extra_capture_and_imported_metrics_refuse():
    f = fixture()
    first = next(iter(f.captures))
    for captures in ({key: value for key, value in f.captures.items() if key != first},
                     f.captures | {"extra-study": "{}"},
                     f.captures | {first: f.env.results[first]}):
        refused(lambda captures=captures: select(captures=captures), "STUDY_REVIEW_CAPTURE_FAMILY_INCOMPLETE")


def test_missing_review_cannot_cherry_pick_a_lower_ranked_candidate():
    f = fixture()
    first = next(iter(f.documents))
    for documents in ({}, {key: value for key, value in f.documents.items() if key != first}):
        refused(lambda documents=documents: select(reviews=documents), "STUDY_REVIEW_ELIGIBLE_FAMILY_INCOMPLETE")
    refused(lambda: select(reviews=f.documents | {"extra-study": "{}"}),
            "STUDY_REVIEW_DOCUMENT_FAMILY_INVALID")


def test_bad_signature_refuses_entire_selection_instead_of_dropping_a_row():
    f = fixture()
    first = next(iter(f.documents))
    bad = json.loads(f.documents[first])
    bad["signature_b64"] = base64.b64encode(bytes(64)).decode("ascii")
    refused(lambda: select(reviews=f.documents | {first: json.dumps(bad)}), "REVIEW_SIGNATURE_UNVERIFIED")


def test_signed_other_candidate_and_changed_evaluation_time_cannot_replay():
    f = fixture()
    a, b = list(f.documents)[:2]
    refused(lambda: select(reviews=f.documents | {a: f.documents[b]}),
            "STUDY_REVIEW_COMPUTED_BINDING_MISMATCH")
    refused(lambda: select(evaluated_at=f.env.now + timedelta(seconds=1)),
            "STUDY_REVIEW_SIGNED_FAMILY_MISMATCH")
    refused(lambda: select(evaluated_at=f.now + timedelta(seconds=1)),
            "STUDY_REVIEW_EVALUATION_IN_FUTURE")


def test_source_program_or_statistic_mutation_never_qualifies():
    f = fixture()
    first = next(iter(f.documents))
    body = deepcopy(f.bodies[first])
    request = body["request"]
    request["bindings"]["inputs_digest"] = "f" * 64
    values = {key: value for key, value in request.items() if key != "request_sha256"}
    request["request_sha256"] = hashlib.sha256(json.dumps(values, sort_keys=True,
        separators=(",", ":"), ensure_ascii=True).encode("ascii")).hexdigest()
    refused(lambda: select(reviews=f.documents | {first: signed(body, f.key)}),
            "STUDY_REVIEW_COMPUTED_BINDING_MISMATCH")
    with patch.object(S, "capture_source_artifact", return_value=b"changed frozen capture code"):
        refused(select, "STUDY_CAPTURE_SOURCE_CHANGED")


def test_signed_but_inconsistent_metric_summary_is_not_accepted():
    f = fixture()
    first = next(iter(f.documents))
    body = deepcopy(f.bodies[first])
    request = body["request"]
    request["computed_summary"]["metrics"]["total_return"] += 0.1
    values = {key: value for key, value in request.items() if key != "request_sha256"}
    request["request_sha256"] = hashlib.sha256(json.dumps(values, sort_keys=True,
        separators=(",", ":"), ensure_ascii=True).encode("ascii")).hexdigest()
    refused(lambda: select(reviews=f.documents | {first: signed(body, f.key)}),
            "STUDY_REVIEW_COMPUTED_SUMMARY_MISMATCH")


def test_mutating_winner_to_cash_and_omitting_its_review_cannot_select_another_candidate():
    f = fixture()
    winner = select().selection.selected_study_id
    capture = json.loads(f.captures[winner])
    for decision in capture["decisions"]:
        decision["target_fraction"] = "0"
    changed = f.captures | {winner: json.dumps(capture)}
    remaining = {key: value for key, value in f.documents.items() if key != winner}
    refused(lambda: select(captures=changed, reviews=remaining), "STUDY_REVIEW_SIGNED_FAMILY_MISMATCH")


def test_failed_candidate_raw_bytes_are_also_in_every_signed_family_commitment():
    f = fixture()
    failed = [key for key in f.captures if key not in f.documents]
    assert failed, "fixture must include a genuine computed failure"
    # Same mathematical archive, different byte-level source record still needs
    # a fresh family review. Failed evidence cannot be silently replaced.
    changed = f.captures | {failed[0]: f.captures[failed[0]] + "\n"}
    refused(lambda: select(captures=changed), "STUDY_REVIEW_SIGNED_FAMILY_MISMATCH")


def test_legacy_candidate_only_signature_never_upgrades_into_a_family_review():
    f = fixture()
    first = next(iter(f.documents))
    body = deepcopy(f.bodies[first])
    request = body["request"]
    request.pop("family_commitment")
    request["schema_version"] = 1
    values = {key:value for key,value in request.items() if key != "request_sha256"}
    request["request_sha256"] = hashlib.sha256(json.dumps(values,sort_keys=True,
        separators=(",",":"),ensure_ascii=True).encode("ascii")).hexdigest()
    refused(lambda: select(reviews=f.documents | {first:signed(body,f.key)}),
            "STUDY_REVIEW_SIGNED_FAMILY_REQUIRED")


def test_schema2_standalone_signer_matches_runtime_signing_bytes():
    from tests.compliance_signer import signer
    for body in fixture().bodies.values():
        assert signer._rv_review_signing_bytes(body) == review_signing_bytes(body)
        assert signer._rr_parse_review_request(json.dumps(body["request"])) == body["request"]


def test_study_request_generation_commits_every_evaluated_candidate_including_failure():
    f = fixture()
    with tempfile.TemporaryDirectory(prefix="full_review_family_") as directory:
        root = Path(os.path.realpath(directory))
        for identifier, raw in f.captures.items():
            (root/(identifier+".capture.json")).write_text(raw, encoding="utf-8")
        _, evaluation, requests = S._select(f.env.plan, f.profile, root, f.env.now)
        assert set(evaluation) == set(f.captures) and len(requests) == len(f.documents)
        for request in requests:
            assert request["schema_version"] == 2
            assert request["family_commitment"] == f.bodies[request["study_id"]]["request"]["family_commitment"]
            assert {row["study_id"] for row in request["family_commitment"]["members"]} == set(f.captures)


def test_current_profile_must_be_fresh_and_preserve_frozen_contract():
    f = fixture()
    stale = replace(f.profile, instrument_rules=replace(f.profile.instrument_rules,
                    asof=f.now - timedelta(minutes=6)))
    refused(lambda: select(profile=stale), "STUDY_REVIEW_PROFILE_NOT_CURRENT")
    changed = replace(f.profile, account_scope="another-synthetic-account")
    refused(lambda: select(profile=changed), "STUDY_REVIEW_ELIGIBLE_FAMILY_INCOMPLETE")
    renewed = replace(f.profile, instrument_rules=replace(f.profile.instrument_rules, asof=f.now))
    assert select(profile=renewed).selection.status == "SELECTED"


def test_authority_expiry_current_key_code_and_seal_are_authenticated():
    f = fixture()
    refused(lambda: select(authority_provider=lambda at: authority(at,
        observed_at=at-timedelta(seconds=31))), "REVIEW_OWNER_AUTHORITY_STALE")
    refused(lambda: select(authority_provider=lambda at: authority(at,
        context=replace(authority(at).context))), "REVIEW_OWNER_CONTEXT_INVALID")
    refused(lambda: select(authority_provider=lambda at: authority(at,
        context=context(at, owner=authority(at).context.owner, code_hash="d"*64))),
        "REVIEW_DEPLOYMENT_CODE_MISMATCH")
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    other = Ed25519PrivateKey.from_private_bytes(bytes(range(1, 33))).public_key().public_bytes_raw()
    refused(lambda: select(authority_provider=lambda at: authority(at, public_key_raw=other)),
            "REVIEW_CURRENT_KEY_MISMATCH")
    # Keep terms fresh so this case reaches detached-signature validity.
    late = f.env.now + timedelta(hours=1)
    fresh = replace(f.profile, instrument_rules=replace(f.profile.instrument_rules, asof=late))
    refused(lambda: select(profile=fresh, clock=lambda: late), "REVIEW_EXPIRED_OR_FUTURE")


def test_each_review_refreshes_authority_and_mid_selection_change_refuses():
    calls = []
    def changed(at):
        calls.append(at)
        return authority(at) if len(calls) == 1 else authority(at,
            context=context(at, owner=authority(at).context.owner, code_signed=False))
    refused(lambda: select(authority_provider=changed), "REVIEW_OWNER_APPROVAL_REQUIRED")
    assert len(calls) == 2
    calls.clear()
    def unchanged(at):
        calls.append(at)
        return authority(at)
    assert select(authority_provider=unchanged).selection.status == "SELECTED"
    assert len(calls) == 2 * len(fixture().documents)


def test_clock_rollback_or_unsigned_document_refuses():
    f = fixture()
    stamps = iter((f.now, f.now - timedelta(seconds=1)))
    refused(lambda: select(clock=lambda: next(stamps)), "STUDY_REVIEW_CLOCK_ROLLBACK")
    first = next(iter(f.documents))
    unsigned = json.dumps(f.bodies[first]["request"])
    refused(lambda: select(reviews=f.documents | {first: unsigned}), "REVIEW_ENVELOPE_INVALID")


def test_numerically_failed_complete_family_stays_unqualified_without_owner_access():
    p = plan()
    outcome = Driver(p).run()
    at = p.candidates[0].protocol.capture_end + timedelta(seconds=1)
    current = profile(instrument_rules=replace(profile().instrument_rules, asof=at))
    captures = {c.protocol.study_id: capture_json(a) for c, a in zip(p.candidates, outcome.archives)}
    result = R.authenticate_study_selection(p, profile=current, captures=captures, reviews={},
        evaluated_at=at, clock=lambda: at, authority_provider=no_history)
    assert result.selection.status == "NO_QUALIFIED_MARKET" and not result.source_reviews_authenticated
    assert not result.execution_ready and result.authenticated_study_ids == ()


def invoke(argv):
    stream = StringIO()
    with redirect_stdout(stream):
        exitcode = R.main(argv)
    return exitcode, json.loads(stream.getvalue()), stream.getvalue()


def test_cli_uses_real_clock_boundary_and_explicit_review_files_only():
    f = fixture()
    with tempfile.TemporaryDirectory(prefix="study_review_") as temporary:
        root = Path(os.path.realpath(temporary))
        (root / "plan.json").write_text(S.study_plan_json(f.env.plan), encoding="utf-8")
        (root / "profile.json").write_text(json.dumps(profile_body(f.profile)), encoding="utf-8")
        for identifier, raw in f.captures.items():
            (root / (identifier + ".capture.json")).write_text(raw, encoding="utf-8")
        argv = ["select-reviewed", "--plan", str(root/"plan.json"), "--profile", str(root/"profile.json"),
                "--captures", str(root), "--evaluated-at", f.env.now.isoformat()]
        for index, raw in enumerate(f.documents.values()):
            path = root / f"review-{index}.json"
            path.write_text(raw, encoding="utf-8")
            argv += ["--review", str(path)]
        before = {path.name: path.read_bytes() for path in root.iterdir()}
        # Patch the wall-clock boundary, not datetime's type used by _aware.
        class FakeDatetime(type(f.now)):
            @classmethod
            def now(cls, tz):
                return f.now
        with patch.object(R, "datetime", FakeDatetime), patch.object(R, "_aware", side_effect=lambda x:x), \
             patch.object(R, "CurrentOwnerAuthority", side_effect=lambda **_: authority):
            code, result, raw = invoke(argv)
        assert code == 0 and result["selection"]["status"] == "SELECTED"
        assert result["research_review_ready"] is True
        assert result["source_reviews_authenticated"] and not result["execution_ready"]
        assert not result["implementation_authenticated"]
        assert PRINCIPAL not in raw and SCOPE not in raw and str(root) not in raw
        assert before == {path.name: path.read_bytes() for path in root.iterdir()}
        with patch.object(R, "CurrentOwnerAuthority", side_effect=AssertionError("must not load authority")):
            code, result, raw = invoke(argv + ["--now", f.now.isoformat()])
        assert code == 2 and result["reasons"] == ["STUDY_REVIEW_ARGUMENTS_INVALID"]
        code, result, _ = invoke(argv + argv[-2:])
        assert code == 2 and result["reasons"] == ["STUDY_REVIEW_DUPLICATE_DOCUMENT"]


def test_cli_invalid_time_and_private_path_fail_before_owner_loading():
    args = ["select-reviewed", "--plan", "/missing/plan.json", "--profile", "/missing/profile.json",
            "--captures", "/missing", "--evaluated-at", "2031-01-01"]
    with patch.object(R, "CurrentOwnerAuthority", side_effect=AssertionError("must not load owner")):
        code, body, raw = invoke(args)
        assert code == 2 and body["reasons"] == ["WORKFLOW_EXPLICIT_TIME_REQUIRED"]
        args[-1] = fixture().env.now.isoformat()
        args[2] = "/tmp/.tradegen/owner.json"
        code, body, raw = invoke(args)
        assert code == 2 and body["reasons"] == ["WORKFLOW_FILE_REFUSED"]
        assert ".tradegen" not in raw and "/missing" not in raw


def test_module_has_no_write_network_sign_or_arm_path():
    source = Path(R.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = {alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
    assert not imports & {"requests", "httpx", "socket", "subprocess"}
    attrs = {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
    assert not attrs & {"write_text", "write_bytes", "sign", "arm", "getenv", "environ", "home", "submit"}
    for node in tree.body:
        assert isinstance(node, (ast.Expr, ast.Import, ast.ImportFrom, ast.Assign, ast.FunctionDef,
                                 ast.ClassDef, ast.If))
    assert all(not isinstance(node, ast.Expr) for node in tree.body[1:])
