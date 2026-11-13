"""Invented outcome metadata only: no actual study, source, signature or order.

The codec proves syntax and caller-declared set consistency. These tests must not
be reported as universe evaluation, original-evidence authentication or approval.
"""
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone
import hashlib
import json
from unittest.mock import patch

from execution_launch import research_outcomes as R


AT = datetime(2031, 1, 2, 3, 4, 5, 6, tzinfo=timezone.utc)


def evaluated(**changes):
    body = dict(schema_version=1, status="EVALUATED", study_id="candidate-A",
                protocol_digest="b" * 64, registry_digest="c" * 64, capture_sha256="a" * 64,
                inputs_digest="d" * 64, evaluator_revision="forward-paper-v1", source_kind_claim="synthetic",
                evaluated_at=AT, result_digest="e" * 64, failure=None)
    body.update(changes)
    return R.CandidateOutcomeDocument(**body)


def failed(**changes):
    return evaluated(**(dict(status="EVALUATION_FAILED", evaluator_revision="forward-universe-v1",
                             result_digest=None, failure=R.EvaluationFailureDetail(
                                 code="STRATEGY_UNIVERSE_MARK_UNAVAILABLE", slot_index=7, phase="primary")) | changes))


def refused(call, code=None):
    try:
        call()
    except R.ResearchOutcomeError as exc:
        assert str(exc).startswith("RESEARCH_OUTCOME_")
        if code is not None:
            assert str(exc) == code, (str(exc), code)
        return str(exc)
    raise AssertionError("invalid metadata accepted")


def encoded(body):
    return json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")


def body(document):
    return json.loads(R.outcome_document_bytes(document))


def test_evaluated_document_has_a_fixed_canonical_wire_contract_and_separate_digest_domain():
    document = evaluated()
    expected = (b'{"capture_sha256":"' + b"a" * 64
                + b'","evaluated_at":"2031-01-02T03:04:05.000006+00:00",'
                  b'"evaluator_revision":"forward-paper-v1","failure":null,"inputs_digest":"' + b"d" * 64
                + b'","protocol_digest":"' + b"b" * 64 + b'","registry_digest":"' + b"c" * 64
                + b'","result_digest":"' + b"e" * 64
                + b'","schema_version":1,"source_kind_claim":"synthetic","status":"EVALUATED",'
                  b'"study_id":"candidate-A"}')
    assert R.outcome_document_bytes(document) == expected
    assert R.parse_outcome_document(expected) == document
    assert R.outcome_document_digest(document) == hashlib.sha256(
        b"tradegen-candidate-evaluated-document/1\x00" + expected).hexdigest()
    assert R.outcome_document_digest(document) != hashlib.sha256(expected).hexdigest()
    assert R.outcome_document_digest(document) != document.result_digest


def test_failed_document_preserves_location_and_has_no_metrics_or_approval_fields():
    document = failed()
    raw = R.outcome_document_bytes(document)
    parsed = R.parse_outcome_document(raw)
    assert parsed == document and parsed.result_digest is None
    assert body(parsed)["failure"] == {"code": "STRATEGY_UNIVERSE_MARK_UNAVAILABLE",
                                       "slot_index": 7, "phase": "primary"}
    assert R.outcome_document_digest(document) == hashlib.sha256(
        b"tradegen-candidate-evaluation-failure/1\x00" + raw).hexdigest()
    assert R.outcome_document_digest(document) != hashlib.sha256(
        b"tradegen-candidate-evaluated-document/1\x00" + raw).hexdigest()
    assert not any(name in body(parsed) for name in ("metrics", "total_return", "benchmark_p", "approved",
                                                    "execution_ready", "signature"))


def test_raw_capture_byte_changes_require_a_different_claim_without_rehashing_as_json():
    first, second = b'{"data":1}', b'{ "data":1 }'
    assert json.loads(first) == json.loads(second)
    one = evaluated(capture_sha256=hashlib.sha256(first).hexdigest())
    two = replace(one, capture_sha256=hashlib.sha256(second).hexdigest())
    assert one.capture_sha256 != two.capture_sha256
    assert R.outcome_document_digest(one) != R.outcome_document_digest(two)
    # No bytes are supplied to the parser: a syntactically valid false claim is
    # still only metadata and deliberately cannot be authenticated by this API.
    assert R.parse_outcome_document(R.outcome_document_bytes(one)) == one


def test_every_metadata_binding_and_failure_location_participates_in_document_digest():
    original = evaluated()
    digest = R.outcome_document_digest(original)
    for change in (dict(study_id="candidate-B"), dict(protocol_digest="f" * 64), dict(registry_digest="f" * 64),
                   dict(capture_sha256="f" * 64), dict(inputs_digest="f" * 64), dict(result_digest="f" * 64),
                   dict(evaluator_revision="forward-universe-v1"), dict(source_kind_claim="prospective_paper_capture"),
                   dict(evaluated_at=AT + timedelta(microseconds=1))):
        assert R.outcome_document_digest(replace(original, **change)) != digest
    failure = failed()
    for detail in (replace(failure.failure, slot_index=8), replace(failure.failure, phase="double_cost"),
                   replace(failure.failure, code="STRATEGY_UNIVERSE_HELD_COIN_VANISHED")):
        assert R.outcome_document_digest(replace(failure, failure=detail)) != R.outcome_document_digest(failure)


def test_result_and_failure_are_disjoint_and_cannot_be_coerced_into_each_other():
    for change in (dict(result_digest=None), dict(result_digest=True), dict(failure=failed().failure),
                   dict(status="EVALUATION_FAILED"), dict(status="PASS"), dict(status=True), dict(status=["EVALUATED"])):
        refused(lambda change=change: evaluated(**change))
    for change in (dict(result_digest="a" * 64), dict(failure=None), dict(failure={"code": "timeout"}),
                   dict(status="EVALUATED")):
        refused(lambda change=change: failed(**change))


def test_schema_and_bindings_use_exact_types_and_bounded_ascii_identifiers():
    for change in (dict(schema_version=True), dict(schema_version=1.0), dict(schema_version=2),
                   dict(study_id=""), dict(study_id="1candidate"), dict(study_id="a" * 97),
                   dict(study_id="candidate/secret"), dict(study_id="후보"), dict(study_id=["candidate"]),
                   dict(protocol_digest="B" * 64), dict(registry_digest="a" * 63),
                   dict(capture_sha256="g" * 64), dict(inputs_digest=123), dict(result_digest=b"e" * 64)):
        refused(lambda change=change: evaluated(**change))
    assert evaluated(study_id="A" + "b" * 95).study_id.endswith("b" * 95)


def test_known_revision_and_source_labels_remain_claims_not_verification():
    for revision in ("forward-paper-v1", "forward-universe-v1"):
        for kind in ("synthetic", "retrospective_replay", "prospective_paper_capture"):
            document = evaluated(evaluator_revision=revision, source_kind_claim=kind)
            assert R.parse_outcome_document(R.outcome_document_bytes(document)) == document
    for change in (dict(evaluator_revision="forward-universe-v2"), dict(evaluator_revision=[]),
                   dict(source_kind_claim="genuine_approved"), dict(source_kind_claim=True)):
        refused(lambda change=change: evaluated(**change))
    refused(lambda: failed(evaluator_revision="forward-paper-v1"), "RESEARCH_OUTCOME_REVISION_UNSUPPORTED")


def test_failure_vocabulary_is_revision_specific_and_benchmark_phase_is_consistent():
    for code in ("STRATEGY_UNIVERSE_HELD_COIN_VANISHED", "STRATEGY_UNIVERSE_MARK_UNAVAILABLE",
                 "STRATEGY_UNIVERSE_TERMINAL_BOOK_UNAVAILABLE"):
        for phase in ("primary", "double_cost", "extra_bar_delay"):
            detail = R.EvaluationFailureDetail(code=code, slot_index=7, phase=phase)
            assert R.parse_outcome_document(R.outcome_document_bytes(failed(failure=detail))).failure == detail
        refused(lambda code=code: R.EvaluationFailureDetail(code=code, slot_index=7, phase="benchmark"))
    benchmark = R.EvaluationFailureDetail(code="STRATEGY_UNIVERSE_BENCHMARK_UNAVAILABLE",
                                          slot_index=7, phase="benchmark")
    assert R.parse_outcome_document(R.outcome_document_bytes(failed(failure=benchmark))).failure == benchmark
    for code, phase in (("STRATEGY_CAPTURE_JSON_SCHEMA_INVALID", "primary"), ("TIMEOUT", "primary"),
                        ("STRATEGY_UNIVERSE_MARK_UNAVAILABLE", "lag2"),
                        ("STRATEGY_UNIVERSE_BENCHMARK_UNAVAILABLE", "primary")):
        refused(lambda: R.EvaluationFailureDetail(code=code, slot_index=7, phase=phase))


def test_failure_slot_boundaries_refuse_booleans_floats_strings_and_out_of_range():
    for index in (0, 19999):
        assert replace(failed().failure, slot_index=index).slot_index == index
    for index in (-1, 20000, True, 7.0, "7", None, 10**100):
        refused(lambda: replace(failed().failure, slot_index=index), "RESEARCH_OUTCOME_FAILURE_INVALID")


def test_utc_wire_time_is_canonical_and_in_memory_offsets_normalize_to_same_instant():
    original = evaluated()
    offset = original.evaluated_at.astimezone(timezone(timedelta(hours=9)))
    assert R.outcome_document_bytes(replace(original, evaluated_at=offset)) == R.outcome_document_bytes(original)
    for timestamp in ("2031-01-02T03:04:05.000006Z", "2031-01-02T03:04:05+00:00",
                      "2031-01-02T12:04:05.000006+09:00", "2031-01-02 03:04:05.000006+00:00",
                      "2031-02-30T03:04:05.000006+00:00", 123, None):
        changed = body(original) | {"evaluated_at": timestamp}
        refused(lambda: R.parse_outcome_document(encoded(changed)), "RESEARCH_OUTCOME_TIME_INVALID")
    for timestamp in (AT.replace(tzinfo=None), "2031-01-02T03:04:05.000006+00:00", None):
        refused(lambda: replace(original, evaluated_at=timestamp), "RESEARCH_OUTCOME_TIME_INVALID")


def test_unknown_missing_and_approval_or_metrics_fields_are_rejected_at_every_object_level():
    for document in (evaluated(), failed()):
        original = body(document)
        for name in original:
            missing = {key: value for key, value in original.items() if key != name}
            refused(lambda: R.parse_outcome_document(encoded(missing)), "RESEARCH_OUTCOME_SCHEMA_INVALID")
        for name in ("metrics", "total_return", "family_adjusted_p", "approved", "signature", "execution_ready"):
            refused(lambda: R.parse_outcome_document(encoded(original | {name: True})),
                    "RESEARCH_OUTCOME_SCHEMA_INVALID")
    original = body(failed())
    for altered in (original["failure"] | {"result": "PASS"}, {"code": "STRATEGY_UNIVERSE_MARK_UNAVAILABLE"},
                    [], "unavailable", True):
        refused(lambda: R.parse_outcome_document(encoded(original | {"failure": altered})),
                "RESEARCH_OUTCOME_FAILURE_INVALID")


def test_duplicate_json_keys_are_rejected_in_root_and_nested_failure_even_if_equal():
    raw = R.outcome_document_bytes(failed())
    duplicate_root = b'{"schema_version":1,' + raw[1:]
    duplicate_inner = raw.replace(b'"slot_index":7', b'"slot_index":7,"slot_index":7')
    duplicate_escaped = raw.replace(b'"status":"EVALUATION_FAILED"',
                                    b'"status":"EVALUATION_FAILED","statu\\u0073":"EVALUATION_FAILED"')
    for changed in (duplicate_root, duplicate_inner, duplicate_escaped):
        refused(lambda: R.parse_outcome_document(changed), "RESEARCH_OUTCOME_JSON_INVALID")


def test_invalid_json_numeric_forms_and_nonfinite_constants_never_become_integer_fields():
    raw = R.outcome_document_bytes(failed())
    for token in (b"NaN", b"Infinity", b"-Infinity", b"7.0", b"7e0", b"9" * 1000):
        changed = raw.replace(b'"slot_index":7', b'"slot_index":' + token)
        refused(lambda: R.parse_outcome_document(changed), "RESEARCH_OUTCOME_JSON_INVALID")
    for changed in (b"{", raw[:-1], raw + raw, b"\xff", b"\xef\xbb\xbf" + raw, b"[1,2,3]", b"null"):
        refused(lambda: R.parse_outcome_document(changed))


def test_byte_limit_is_checked_before_decoder_at_exact_boundary_and_one_over():
    raw = R.outcome_document_bytes(evaluated())
    padded = raw + b" " * (R.MAX_OUTCOME_BYTES - len(raw))
    assert len(padded) == 65536 and R.parse_outcome_document(padded) == evaluated()
    with patch.object(R.json, "loads", side_effect=AssertionError("decoder called for over-limit input")):
        refused(lambda: R.parse_outcome_document(padded + b" "), "RESEARCH_OUTCOME_SIZE_INVALID")
    for bad in (b"", raw.decode("ascii"), bytearray(raw), memoryview(raw), None):
        refused(lambda: R.parse_outcome_document(bad), "RESEARCH_OUTCOME_SIZE_INVALID")


def test_nested_input_is_refused_before_decoder_and_braces_inside_strings_do_not_count():
    with patch.object(R.json, "loads", side_effect=AssertionError("decoder called before nesting bound")):
        for depth in (5, 100):
            refused(lambda: R.parse_outcome_document(b"[" * depth + b"0" + b"]" * depth),
                    "RESEARCH_OUTCOME_JSON_INVALID")
    with patch.object(R.json, "loads", wraps=json.loads) as decode:
        refused(lambda: R.parse_outcome_document(b"[[[[0]]]]"), "RESEARCH_OUTCOME_SCHEMA_INVALID")
        assert decode.call_count == 1
    # Escaped quotation marks and braces are string content, not nesting. The
    # eventual refusal is the identifier validator, not the structural scanner.
    original = body(evaluated())
    for text in ('a{{{{{{{{{{', 'a\\"{{{{{{{{', 'a]]]]]]]]'):
        refused(lambda: R.parse_outcome_document(encoded(original | {"study_id": text})),
                "RESEARCH_OUTCOME_BINDING_INVALID")


def test_invalid_provider_text_is_not_in_diagnostics():
    secretish = "private-path-provider-message"
    for changed in (body(evaluated()) | {"status": secretish},
                    body(failed()) | {"failure": {"code": secretish, "slot_index": 7, "phase": "primary"}},
                    body(evaluated()) | {secretish: "ignored"}):
        message = refused(lambda: R.parse_outcome_document(encoded(changed)))
        assert secretish not in message


def test_documents_are_frozen_and_encoding_revalidates_deliberately_mutated_fields():
    original = evaluated()
    try:
        original.status = "APPROVED"
    except FrozenInstanceError:
        pass
    else:
        raise AssertionError("document is mutable")
    for mutate in (lambda doc: object.__setattr__(doc, "schema_version", True),
                   lambda doc: object.__setattr__(doc, "result_digest", None),
                   lambda doc: object.__setattr__(doc, "study_id", "../private")):
        document = evaluated()
        mutate(document)
        refused(lambda: R.outcome_document_bytes(document))
        refused(lambda: R.outcome_document_digest(document))
        refused(lambda: R.validate_outcome_set((document,), expected_study_ids=("candidate-A",)))
    document = failed()
    object.__setattr__(document.failure, "slot_index", True)
    refused(lambda: R.outcome_document_bytes(document))
    refused(lambda: R.outcome_document_digest(document))


def test_deleted_frozen_fields_are_refused_with_fixed_diagnostics_not_attribute_errors():
    for nested, field in ((False, "result_digest"), (False, "status"), (True, "slot_index")):
        document = failed() if nested else evaluated()
        object.__delattr__(document.failure if nested else document, field)
        for call in (lambda: R.outcome_document_bytes(document), lambda: R.outcome_document_digest(document),
                     lambda: R.validate_outcome_set((document,), expected_study_ids=("candidate-A",))):
            refused(call, "RESEARCH_OUTCOME_DOCUMENT_INVALID")


def test_current_candidate_set_preserves_failure_members_and_uses_declared_order():
    one, two = evaluated(study_id="candidate-A"), failed(study_id="candidate-B")
    expected = ("candidate-A", "candidate-B")
    assert R.validate_outcome_set((two, one), expected_study_ids=expected) == (one, two)
    for items in ((one,), (two,), (one, one), (one, two, evaluated(study_id="candidate-C")),
                  (one, evaluated(study_id="candidate-C"))):
        refused(lambda: R.validate_outcome_set(items, expected_study_ids=expected),
                "RESEARCH_OUTCOME_SET_MISMATCH")
    # Supplying a smaller expected set proves only that declared set, not that a
    # full preregistered family, previous attempts or K was preserved.
    assert R.validate_outcome_set((one,), expected_study_ids=("candidate-A",)) == (one,)


def test_expected_set_requires_exact_sorted_unique_bounded_ids_and_tuple_documents():
    for expected in ((), ["candidate-A"], ("candidate-B", "candidate-A"), ("candidate-A", "candidate-A"),
                     (True,), ("",), tuple("candidate-" + str(n).zfill(3) for n in range(129))):
        refused(lambda: R.validate_outcome_set((evaluated(),), expected_study_ids=expected),
                "RESEARCH_OUTCOME_EXPECTED_SET_INVALID")
    refused(lambda: R.validate_outcome_set([evaluated()], expected_study_ids=("candidate-A",)),
            "RESEARCH_OUTCOME_SET_MISMATCH")
    expected = tuple("candidate-" + str(n).zfill(3) for n in range(128))
    documents = tuple(evaluated(study_id=name) for name in expected)
    assert R.validate_outcome_set(documents[::-1], expected_study_ids=expected) == documents


def test_no_constructor_or_parser_result_is_an_issued_strategy_evaluation():
    from execution_launch import strategy as S
    from tests import launch_strategy as T
    protocol, _, _, _, _, original_result, now = T.fixture_capture(source_kind="synthetic")
    original_digest = S.evidence_digest(original_result)
    for document in (evaluated(), failed()):
        parsed = R.parse_outcome_document(R.outcome_document_bytes(document))
        for representation in (document, parsed, body(parsed)):
            T.rejected(lambda: T.assessment(protocol, representation, now), "STRATEGY_COMPUTED_RESULT_REQUIRED")
    assert S.evidence_digest(original_result) == original_digest
    assert not T.assessment(protocol, original_result, now).research_review_ready


def test_outcome_documents_cannot_be_imported_as_legacy_review_requests_or_signed_reviews():
    from execution_launch import review_auth as A
    from execution_launch import review_request as Q
    for document in (evaluated(), failed()):
        raw = R.outcome_document_bytes(document)
        for parser, error in ((Q.parse_review_request, Q.ReviewRequestError),
                              (A.parse_review_document, A.ReviewAuthenticationError)):
            try:
                parser(raw)
            except error:
                pass
            else:
                raise AssertionError("outcome metadata became an approval format")
