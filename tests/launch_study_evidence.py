"""Invented whole-family evidence; no real sources, credentials or approvals."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from functools import lru_cache, wraps
import hashlib
import json
from types import SimpleNamespace
from unittest.mock import patch

from execution_launch import strategy as S
from execution_launch import study_evidence as F
from execution_launch.capture_v2 import capture_json_v2, make_archive_v2
from execution_launch.program import program_digest
from tests.launch_strategy import fixture_capture as legacy_capture
from tests.launch_carry_strategy import fixture_capture as carry_capture


def isolated(function):
    @wraps(function)
    def inner():
        previous = dict(S._EVALUATED)
        S._EVALUATED.clear()
        try:
            return function()
        finally:
            S._EVALUATED.clear()
            S._EVALUATED.update(previous)
    return inner


@lru_cache(maxsize=2)
def family(carry=False):
    identifiers = ('family-a', 'family-b')
    if carry:
        sample = carry_capture(count=241)
        programs = tuple(replace(sample.program, strategy_id=name) for name in identifiers)
        protocols = tuple(replace(sample.protocol, study_id=name + '-study', strategy_id=name,
            strategy_code_sha256=program_digest(program, sample.artifact), family_members=identifiers)
            for name, program in zip(identifiers, programs))
        rules, now = sample.profile.instrument_rules, sample.now
    else:
        protocol, bars, decisions, rules, _, _, now = legacy_capture()
        protocols = tuple(replace(protocol, study_id=name + '-study', strategy_id=name,
                                  family_members=identifiers) for name in identifiers)
    registry = ()
    for protocol in protocols:
        registry = S.register_protocol(protocol, registry)
    captures = {}
    for index, protocol in enumerate(protocols):
        if carry:
            archive = make_archive_v2(registry, 'synthetic', programs[index],
                program_artifact=sample.artifact, bars=sample.bars, decisions=sample.decisions)
            raw = capture_json_v2(archive).encode('ascii')
        else:
            choices = decisions if index == 0 else tuple(replace(row, target_fraction=Decimal(0))
                                                         for row in decisions)
            raw = json.dumps(S._plain(dict(registry=registry, source_kind='synthetic',
                bars=bars, decisions=choices)), sort_keys=True).encode('ascii')
        captures[protocol.study_id] = raw
    work = sum(p.bootstrap_replications * (
        ((p.capture_end - p.capture_start) // timedelta(seconds=p.bar_seconds)) // p.block_length + 1)
        for p in protocols)
    return SimpleNamespace(protocols=protocols, captures=captures, registry=registry,
                           rules=rules, now=now, work=work)


def evaluate(env, **changes):
    args = dict(protocols=env.protocols, captures=env.captures, rules=env.rules,
                registry=env.registry, now=env.now)
    args.update(changes)
    return F.evaluate_study_family(**args)


def refused(call, code=None):
    try:
        call()
    except (F.StudyEvidenceError, S.StrategyEvidenceError) as exc:
        if code is not None:
            assert str(exc) == code, (str(exc), code)
        return
    raise AssertionError('invalid family admitted')


def no_issuance(env, **changes):
    before = dict(S._EVALUATED)
    with patch.object(S, 'evaluate_capture_json', side_effect=AssertionError('evaluation before admission')) as run:
        refused(lambda: evaluate(env, **changes))
        assert run.call_count == 0
    assert S._EVALUATED == before


@isolated
def test_validation_only_never_calls_arithmetic_or_issues_a_result_for_both_revisions():
    for carry in (False, True):
        env = family(carry)
        before = dict(S._EVALUATED)
        with patch.object(S, '_simulate', side_effect=AssertionError('legacy arithmetic called')), \
             patch('execution_launch.carry_evaluator.simulate_carry', side_effect=AssertionError('carry arithmetic called')), \
             patch.object(S, '_block_p', side_effect=AssertionError('inference called')):
            for protocol in env.protocols:
                assert S.validate_capture_json(protocol, env.captures[protocol.study_id], env.rules,
                    now=env.now, expected_registry_digest=S.validate_registry(env.registry)) is None
        assert S._EVALUATED == before


@isolated
def test_actual_results_match_single_capture_evaluations_byte_for_byte_for_legacy_and_carry():
    for carry in (False, True):
        env = family(carry)
        expected = {p.study_id: S.evaluate_capture_json(p, env.captures[p.study_id], env.rules, now=env.now)
                    for p in env.protocols}
        actual = evaluate(env)
        assert tuple(row.study_id for row in actual.rows) == tuple(p.study_id for p in env.protocols)
        for row in actual.rows:
            assert S.evidence_digest(row.result) == S.evidence_digest(expected[row.study_id])
            assert S._EVALUATED[id(row.result)][0] is row.result
            assert row.raw_capture == env.captures[row.study_id]
            assert row.capture_sha256 == hashlib.sha256(row.raw_capture).hexdigest()
        detached = actual.results
        detached.clear()
        assert len(actual.results) == 2


@isolated
def test_last_candidate_last_frame_damage_stops_every_evaluation_for_both_revisions():
    for carry in (False, True):
        env = family(carry)
        key = env.protocols[-1].study_id
        for field in ('source_sha256', 'observed_at'):
            body = json.loads(env.captures[key])
            body['bars'][-1][field] = 'not-a-valid-value'
            no_issuance(env, captures=env.captures | {key: json.dumps(body)})
        body = json.loads(env.captures[key])
        body['decisions'][-1]['history_sha256'] = '0' * 64
        no_issuance(env, captures=env.captures | {key: json.dumps(body)})


@isolated
def test_missing_extra_duplicate_and_foreign_family_inputs_never_evaluate():
    env = family()
    key = env.protocols[-1].study_id
    for captures in ({k:v for k,v in env.captures.items() if k != key},
                     env.captures | {'extra-study': b'{}'},
                     env.captures | {key: object()}):
        no_issuance(env, captures=captures)
    no_issuance(env, protocols=(env.protocols[0], env.protocols[0]))
    no_issuance(env, protocols=(replace(env.protocols[0], family_members=('family-a',)), env.protocols[1]))


@isolated
def test_duplicate_json_keys_in_last_candidate_are_not_a_normal_failure():
    for carry in (False, True):
        env = family(carry)
        key = env.protocols[-1].study_id
        raw = b'{"source_kind":"synthetic",' + env.captures[key][1:]
        no_issuance(env, captures=env.captures | {key: raw})


@isolated
def test_valid_but_different_registry_chain_is_refused_before_any_evaluation():
    env = family()
    extra = replace(env.protocols[-1], study_id='unplanned-registration')
    extended = S.register_protocol(extra, env.registry)
    captures = {}
    for key, raw in env.captures.items():
        body = json.loads(raw)
        body['registry'] = S._plain(extended)
        captures[key] = json.dumps(body)
    no_issuance(env, captures=captures)


@isolated
def test_truncated_registration_and_wrong_rules_and_not_finished_are_all_preflight_refusals():
    env = family()
    key = env.protocols[-1].study_id
    body = json.loads(env.captures[key])
    body['registry'] = body['registry'][:-1]
    no_issuance(env, captures=env.captures | {key: json.dumps(body)})
    no_issuance(env, rules=replace(env.rules, lot_size=env.rules.lot_size * 2))
    no_issuance(env, now=env.now - timedelta(days=1))


@isolated
def test_resource_limits_are_fixed_operational_refusals_before_evaluation():
    env = family()
    total = sum(map(len, env.captures.values()))
    largest = max(map(len, env.captures.values()))
    for changes in (dict(max_candidates=1), dict(max_capture_bytes=largest - 1),
                    dict(max_total_bytes=total - 1), dict(max_inference_work=env.work - 1)):
        limits = replace(F.DEFAULT_LIMITS, **changes)
        before = dict(S._EVALUATED)
        with patch.object(S, 'evaluate_capture_json', side_effect=AssertionError('not admitted')) as run:
            refused(lambda: evaluate(env, limits=limits), 'STUDY_EVIDENCE_RESOURCE_LIMIT')
            assert run.call_count == 0
        assert S._EVALUATED == before


@isolated
def test_exact_resource_boundaries_and_one_unit_headroom_admit_actual_evaluation():
    env = family()
    total = sum(map(len, env.captures.values()))
    largest = max(map(len, env.captures.values()))
    for extra in (0, 1):
        limits = F.FamilyEvidenceLimits(max_candidates=2 + extra, max_capture_bytes=largest + extra,
            max_total_bytes=total + extra, max_inference_work=env.work + extra)
        assert len(evaluate(env, limits=limits).rows) == 2


@isolated
def test_exhausted_actual_result_registry_stops_before_first_family_evaluation():
    env = family()
    # Actual-issued records are retained by their real identities; only fill the
    # capacity accounting with opaque sentinels, never use them as results.
    before = dict(S._EVALUATED)
    markers = []
    for index in range(128 - len(S._EVALUATED) - 1):
        marker = object()
        S._EVALUATED[id(marker)] = (marker, '0' * 64)
        markers.append(id(marker))
    saturated = dict(S._EVALUATED)
    assert len(saturated) == 127
    with patch.object(S, 'evaluate_capture_json', side_effect=AssertionError('capacity not admitted')) as run:
        refused(lambda: evaluate(env), 'STUDY_EVIDENCE_RESOURCE_LIMIT')
        assert run.call_count == 0
    assert S._EVALUATED == saturated
    # Exactly two slots remain after removing one capacity-only sentinel. Both
    # new values must then be genuine evaluator-issued results, filling 128.
    del S._EVALUATED[markers[-1]]
    result = evaluate(env)
    assert len(S._EVALUATED) == 128
    assert all(S._EVALUATED[id(row.result)][0] is row.result for row in result.rows)
    S._EVALUATED.clear()
    S._EVALUATED.update(before)


@isolated
def test_input_mapping_changes_cannot_swap_bytes_between_preflight_and_evaluation():
    env = family()
    mutable = dict(env.captures)
    original = S.validate_capture_json
    calls = []
    def validate(*args, **kwargs):
        original(*args, **kwargs)
        calls.append(args[0].study_id)
        mutable.clear()
        mutable['unplanned'] = b'{}'
    with patch.object(S, 'validate_capture_json', side_effect=validate):
        evaluated = evaluate(env, captures=mutable)
    assert calls == [p.study_id for p in env.protocols]
    assert {row.study_id:row.raw_capture for row in evaluated.rows} == env.captures


@isolated
def test_whitespace_changes_raw_commitment_without_changing_actual_arithmetic_digest():
    env = family()
    original = evaluate(env)
    whitespace = {key: raw.decode('ascii') + ' \n' for key, raw in env.captures.items()}
    changed = evaluate(env, captures=whitespace)
    assert all(a.capture_sha256 != b.capture_sha256 and S.evidence_digest(a.result) == S.evidence_digest(b.result)
               for a, b in zip(original.rows, changed.rows))
    assert all(row.raw_capture.endswith(b' \n') for row in changed.rows)


@isolated
def test_numerically_rejected_candidate_and_its_original_are_not_omitted():
    env = family()
    actual = evaluate(env)
    failed = actual.rows[-1]
    assert len(actual.rows) == 2 and failed.raw_capture == env.captures[failed.study_id]
    assert failed.result.primary.completed_roundtrips == 0
    assert failed.result.primary.total_return == 0 and failed.result.family_adjusted_p == 1
    assert type(failed.result) is S.ValidationResult


@isolated
def test_unexpected_arithmetic_error_returns_no_partial_family_and_is_not_relabelled():
    env = family()
    original = S.evaluate_capture_json
    calls = []
    def evaluate_one(*args, **kwargs):
        calls.append(args[0].study_id)
        if len(calls) == 2:
            raise ArithmeticError('synthetic arithmetic failure')
        return original(*args, **kwargs)
    before = len(S._EVALUATED)
    try:
        with patch.object(S, 'evaluate_capture_json', side_effect=evaluate_one):
            evaluate(env)
    except ArithmeticError:
        pass
    else:
        raise AssertionError('partial family returned')
    assert len(calls) == 2 and len(S._EVALUATED) == before + 1


@isolated
def test_failure_outcome_json_and_unknown_evaluator_cannot_replace_real_capture():
    env = family()
    key = env.protocols[-1].study_id
    no_issuance(env, captures=env.captures | {key: b'{"status":"EVALUATION_FAILED"}'})
    no_issuance(env, protocols=(env.protocols[0], replace(env.protocols[-1], evaluator_revision='invented-pass')))


def test_limits_reject_bool_nonpositive_and_expansion_above_documented_ceiling():
    for changes in (dict(max_candidates=True), dict(max_capture_bytes=0), dict(max_total_bytes=-1),
                    dict(max_inference_work=40_000_001), dict(max_candidates=129)):
        refused(lambda: F.FamilyEvidenceLimits(**changes), 'STUDY_EVIDENCE_LIMITS_INVALID')


@isolated
def test_multibyte_strings_are_budgeted_as_utf8_bytes_and_invalid_unicode_refuses():
    env = family()
    key = env.protocols[-1].study_id
    captures = {name:b'{}' for name in env.captures}
    for raw, limits, code in (
        ('é' * 11, replace(F.DEFAULT_LIMITS, max_capture_bytes=20), 'STUDY_EVIDENCE_RESOURCE_LIMIT'),
        ('\ud800', F.DEFAULT_LIMITS, 'STUDY_EVIDENCE_CAPTURE_ENCODING_INVALID'),
    ):
        before = dict(S._EVALUATED)
        with patch.object(S, 'evaluate_capture_json', side_effect=AssertionError('not admitted')) as run:
            refused(lambda: evaluate(env, captures=captures | {key:raw}, limits=limits), code)
            assert run.call_count == 0
        assert S._EVALUATED == before
