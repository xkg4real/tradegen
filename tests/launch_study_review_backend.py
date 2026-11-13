"""Shared authentication backend: actual arithmetic, invented review fixtures.

Legacy fixture authority remains an explicit test dependency; the separate
sealed integration suite supplies actual current owner/store trust. No result
is invented, no production registry is reset, and no order/activation is used.
"""
from dataclasses import replace
from datetime import timedelta
import hashlib
import json
from unittest.mock import patch

from execution_launch import strategy as E, study_review as R, study_evidence as F
from tests import launch_study_review as T
from tests import launch_study_receipts as RF, launch_study as SF


def family(f):
    return F.evaluate_study_family(tuple(c.protocol for c in f.env.plan.candidates), f.captures,
        f.profile.instrument_rules, registry=f.env.plan.registry, now=f.env.now)


def select(f, evaluated, **changes):
    args = dict(profile=f.profile, evaluated=evaluated, reviews=f.documents,
        evaluated_at=f.env.now, clock=lambda:f.now, authority_provider=T.authority)
    return R._authenticate_evaluated_selection(f.env.plan, **(args | changes))


def refused_before_owner(f, evaluated, code=None, **changes):
    before = dict(E._EVALUATED)
    with (patch.object(E,'evaluate_capture_json',side_effect=AssertionError('second evaluation')),
          patch.object(R,'verify_source_review',side_effect=AssertionError('signature before family validation'))):
        T.refused(lambda:select(f,evaluated,authority_provider=T.no_history,**changes),code)
    assert E._EVALUATED == before


@T.isolated_evaluations
def test_shared_backend_reuses_genuine_family_without_arithmetic_or_capacity_and_preserves_winner():
    f = T.fixture(); evaluated = family(f)
    before = dict(E._EVALUATED)
    with (patch.object(E,'evaluate_capture_json',side_effect=AssertionError('second evaluation')),
          patch.object(E,'run_paper_validation',side_effect=AssertionError('second arithmetic')),
          patch.object(E,'require_evaluation_capacity',side_effect=AssertionError('new issuance capacity')),
          patch.object(R,'evaluate_study_family',side_effect=AssertionError('second family evaluation'))):
        result = select(f,evaluated)
    assert result.selection.status == 'SELECTED'
    assert result.selection.selected_strategy_id == 'fixture-ma-1-2-a'
    assert result.authenticated_study_ids == tuple(sorted(f.documents))
    assert result.source_reviews_authenticated and not result.execution_ready
    assert not result.implementation_authenticated and not result.selection.execution_ready
    assert E._EVALUATED == before
    # A container clone with the SAME genuine complete inputs/results adds no
    # authority and need not be rejected: each underlying result is rechecked.
    assert select(f,replace(evaluated)).selection == result.selection
    refreshed = replace(f.profile,instrument_rules=replace(f.profile.instrument_rules,asof=f.now))
    assert refreshed.instrument_rules.asof != f.profile.instrument_rules.asof
    fresh_result = select(f,evaluated,profile=refreshed)
    assert fresh_result.selection == result.selection
    assert fresh_result.evaluated_at == f.env.now
    assert all(row.evaluated_at == f.env.now for row in fresh_result.selection.rows)
    assert E._EVALUATED == before


@T.isolated_evaluations
def test_legacy_public_api_still_evaluates_actual_original_family_exactly_once():
    f = T.fixture()
    actual = R.evaluate_study_family
    with patch.object(R,'evaluate_study_family',wraps=actual) as call:
        result = T.select()
    assert call.call_count == 1 and result.selection.status == 'SELECTED'
    assert set(call.call_args.args[1]) == set(f.captures)


@T.isolated_evaluations
def test_missing_duplicate_extra_or_non_exact_rows_refuse_before_any_owner_review():
    f = T.fixture(); evaluated = family(f)
    first = evaluated.rows[0]
    variants = (replace(evaluated,rows=evaluated.rows[:-1]),
        replace(evaluated,rows=evaluated.rows+(first,)),
        replace(evaluated,rows=(replace(first,study_id='another-study'),)+evaluated.rows[1:]),
        replace(evaluated,rows=list(evaluated.rows)),
        replace(evaluated,rows=(object(),)+evaluated.rows[1:]),
        {'rows':evaluated.rows})
    for bad in variants: refused_before_owner(f,bad)


@T.isolated_evaluations
def test_cloned_or_mutated_result_including_failed_candidate_is_never_silently_excluded():
    f = T.fixture(); evaluated = family(f)
    failed = next(index for index,row in enumerate(evaluated.rows) if row.study_id not in f.documents)
    for index in (0,failed):
        rows = list(evaluated.rows)
        rows[index] = replace(rows[index],result=replace(rows[index].result))
        refused_before_owner(f,replace(evaluated,rows=tuple(rows)),
                             'STUDY_REVIEW_RESULT_NOT_ISSUED_OR_MUTATED')
    row = evaluated.rows[failed]
    prior = row.result.benchmark_p
    object.__setattr__(row.result,'benchmark_p',0.875)
    try:
        refused_before_owner(f,evaluated,'STUDY_REVIEW_RESULT_NOT_ISSUED_OR_MUTATED')
    finally:
        object.__setattr__(row.result,'benchmark_p',prior)


@T.isolated_evaluations
def test_wrong_original_hash_and_valid_other_issued_candidate_cannot_be_substituted():
    f = T.fixture(); evaluated = family(f)
    first,second = evaluated.rows[:2]
    refused_before_owner(f,replace(evaluated,rows=(replace(first,capture_sha256='f'*64),)+evaluated.rows[1:]),
                         'STUDY_REVIEW_CAPTURE_HASH_MISMATCH')
    swapped = replace(first,result=second.result)
    refused_before_owner(f,replace(evaluated,rows=(swapped,)+evaluated.rows[1:]),
                         'STUDY_REVIEW_EVALUATED_INPUT_MISMATCH')


@T.isolated_evaluations
def test_rehashed_semantically_changed_raw_input_cannot_reuse_genuine_result():
    f = T.fixture(); evaluated = family(f)
    row = evaluated.rows[-1]
    body = json.loads(row.raw_capture)
    body['source_kind'] = 'synthetic'
    raw = json.dumps(body,sort_keys=True).encode('ascii')
    changed = replace(row,raw_capture=raw,capture_sha256=hashlib.sha256(raw).hexdigest())
    refused_before_owner(f,replace(evaluated,rows=evaluated.rows[:-1]+(changed,)),
                         'STUDY_REVIEW_EVALUATED_INPUT_MISMATCH')
    # Changed original bytes with equal parsed inputs still change the signed
    # family commitment. Canonicalizing away that raw-byte difference is forbidden.
    raw = b'\n'+row.raw_capture
    changed = replace(row,raw_capture=raw,capture_sha256=hashlib.sha256(raw).hexdigest())
    refused_before_owner(f,replace(evaluated,rows=evaluated.rows[:-1]+(changed,)),
                         'STUDY_REVIEW_SIGNED_FAMILY_MISMATCH')


@T.isolated_evaluations
def test_historical_evaluation_time_and_plan_registry_must_match_actual_issued_inputs():
    f = T.fixture(); evaluated = family(f)
    refused_before_owner(f,evaluated,'STUDY_REVIEW_EVALUATED_INPUT_MISMATCH',
                         evaluated_at=f.env.now-timedelta(seconds=1))
    first = evaluated.rows[0]
    raw = json.loads(first.raw_capture)
    raw['registry'][-1]['protocol_digest'] = 'f'*64
    data = json.dumps(raw).encode('ascii')
    changed = replace(first,raw_capture=data,capture_sha256=hashlib.sha256(data).hexdigest())
    refused_before_owner(f,replace(evaluated,rows=(changed,)+evaluated.rows[1:]))


@T.isolated_evaluations
def test_owner_callback_cannot_mutate_failed_candidate_after_initial_family_validation():
    f = T.fixture(); evaluated = family(f)
    index = next(i for i,row in enumerate(evaluated.rows) if row.study_id not in f.documents)
    original = evaluated.rows
    count = [0]
    def change(at):
        count[0] += 1
        if count[0] == 1:
            rows = list(original)
            rows[index] = replace(rows[index],raw_capture=b' '+rows[index].raw_capture,
                capture_sha256=hashlib.sha256(b' '+rows[index].raw_capture).hexdigest())
            object.__setattr__(evaluated,'rows',tuple(rows))
        return T.authority(at)
    try:
        T.refused(lambda:select(f,evaluated,authority_provider=change),'STUDY_REVIEW_EVALUATED_FAMILY_CHANGED')
    finally:
        object.__setattr__(evaluated,'rows',original)


@T.isolated_evaluations
def test_missing_result_fields_and_deleted_family_member_slot_return_fixed_refusals():
    f = T.fixture(); evaluated = family(f)
    bad = replace(evaluated)
    object.__delattr__(bad,'rows')
    refused_before_owner(f,bad,'STUDY_REVIEW_EVALUATED_FAMILY_INVALID')
    row = replace(evaluated.rows[0])
    object.__delattr__(row,'raw_capture')
    refused_before_owner(f,replace(evaluated,rows=(row,)+evaluated.rows[1:]),
                         'STUDY_REVIEW_EVALUATED_FAMILY_INVALID')


@T.isolated_evaluations
def test_impostor_family_property_is_not_executed_before_exact_type_refusal():
    f = T.fixture()
    class Impostor:
        @property
        def rows(self):
            raise AssertionError('untrusted family property was evaluated')
    refused_before_owner(f,Impostor(),'STUDY_REVIEW_EVALUATED_FAMILY_INVALID')


@T.isolated_evaluations
def test_private_backend_rejects_clock_rollback_without_resetting_legacy_clock_boundary():
    f = T.fixture(); evaluated = family(f)
    T.refused(lambda:select(f,evaluated,initial_now=f.now+timedelta(seconds=1)),
              'STUDY_REVIEW_CLOCK_ROLLBACK')
    stamps = iter((f.now,f.now-timedelta(seconds=1)))
    T.refused(lambda:T.select(clock=lambda:next(stamps)),'STUDY_REVIEW_CLOCK_ROLLBACK')


@T.isolated_evaluations
def test_unqualified_legacy_and_carry_families_keep_every_actual_result_without_owner_or_second_evaluation():
    for carry in (False,True):
        env = RF.fixture(carry)
        at = env.plan.candidates[0].protocol.capture_end+timedelta(seconds=1)
        profile = replace(SF.profile(),instrument_rules=replace(SF.profile().instrument_rules,asof=at))
        evaluated = F.evaluate_study_family(tuple(c.protocol for c in env.plan.candidates),env.captures,
            profile.instrument_rules,registry=env.plan.registry,now=at)
        before = dict(E._EVALUATED)
        with (patch.object(E,'evaluate_capture_json',side_effect=AssertionError('second evaluation')),
              patch.object(E,'_simulate',side_effect=AssertionError('legacy arithmetic')),
              patch('execution_launch.carry_evaluator.simulate_carry',side_effect=AssertionError('carry arithmetic'))):
            result = R._authenticate_evaluated_selection(env.plan,profile=profile,evaluated=evaluated,
                reviews={},evaluated_at=at,clock=lambda:at,authority_provider=T.no_history)
        assert result.selection.status == 'NO_QUALIFIED_MARKET'
        assert len(result.selection.rows) == len(env.plan.candidates) == 3
        assert not result.source_reviews_authenticated and not result.execution_ready
        assert E._EVALUATED == before
