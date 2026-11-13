"""Synthetic carry studies through actual capture re-derivation and issuance.

No claim of real source provenance, owner approval or trading profitability.
The repeatable triangle is deliberately planted data, not a financial forecast.
"""
from dataclasses import asdict, replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from functools import lru_cache
from fractions import Fraction
import hashlib
import base64
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from execution_launch import managed_behavior as M
from execution_launch import strategy as S
from execution_launch import review_request as Q
from execution_launch import study as U
from execution_launch.capture_v2 import capture_json_v2, make_archive_v2, parse_capture_v2
from execution_launch.program import ProgramSpec, parameters_json, program_digest
from execution_launch.profile import profile_contract_digest, rule_terms_digest
from tests.launch_profile import fixture_profile


D = Decimal
START = datetime(2031, 1, 1, tzinfo=timezone.utc)


@lru_cache(maxsize=8)
def fixture_capture(source_kind='prospective_paper_capture', *, count=901, account_scope='test-scope'):
    """Actually evaluate an invented study; a prospective label is a fixture claim.

    Account scope is frozen before the protocol and capture. Consumers must not
    replace profile scope after evaluating and reuse the old issued result.
    """
    now = START + timedelta(minutes=count - 1, seconds=1)
    artifact = (Path(__file__).resolve().parents[1] / 'execution_launch/program.py').read_bytes()
    program = ProgramSpec(schema_version=1, strategy_id='test-strategy', kind='moving_average_trend',
                          fast_window=2, slow_window=3, exposure_fraction=D('1'))
    profile = fixture_profile(now)
    profile = replace(profile, account_scope=account_scope, strategy_code_sha256=program_digest(program, artifact),
                      policy=replace(profile.policy, initial_equity=D('1000')))
    protocol = S.ForwardProtocol(schema_version=2, study_id='carry-fixture-v2', strategy_id=program.strategy_id,
        strategy_code_sha256=profile.strategy_code_sha256, capture_source_id='invented-carry-source',
        capture_source_code_sha256='a' * 64, evaluator_revision=M.CARRY_EVALUATOR_REVISION,
        profile_contract_digest=profile_contract_digest(profile), rule_terms_digest=rule_terms_digest(profile.instrument_rules),
        venue='upbit', market='spot', symbol='KRW-BTC', quote_currency='KRW',
        preregistered_at=START - timedelta(days=1), capture_start=START, capture_end=now - timedelta(seconds=1),
        initial_cash_quote=D('1000'), fee_fraction=profile.instrument_rules.fee_fraction, slippage_bps=D('0'),
        bar_seconds=60, minimum_fill_delay_seconds=1, minimum_observations=200, minimum_roundtrips=20,
        block_length=20, bootstrap_replications=999, family_members=(program.strategy_id,),
        alpha=D('0.05'), max_drawdown=D('0.2'), review_max_age_seconds=86400, seed=991,
        behavior_revision=M.BEHAVIOR_REVISION, terminal_accounting=M.TERMINAL_ACCOUNTING,
        management_behavior_sha256=M.behavior_digest())
    protocol = replace(protocol, capture_source_code_sha256=hashlib.sha256(U.capture_source_artifact(protocol)).hexdigest())
    registry = S.register_protocol(protocol)
    bars, decisions, marks, chain = [], [], [], ''
    for index in range(count):
        phase = index % 40
        price = D(100 + 5 * (phase if phase <= 20 else 40 - phase))
        row = S.PaperBar(observed_at=START + timedelta(minutes=index),
            received_at=START + timedelta(minutes=index, seconds=1), bid=price, ask=price, mark=price,
            quote_krw=D(1), source_sha256=hashlib.sha256(('invented-carry-bar-' + str(index)).encode()).hexdigest())
        bars.append(row); marks.append(price)
        chain = S.evidence_digest((chain, row))
        decisions.append(M.derive_fixed_decision_v2(program, tuple(marks), bar_index=index,
            decided_at=row.received_at, history_sha256=chain))
    archive = make_archive_v2(registry, source_kind, program, program_artifact=artifact,
                             bars=tuple(bars), decisions=tuple(decisions))
    raw = capture_json_v2(archive).encode('ascii')
    result = S.evaluate_capture_json(protocol, raw, profile.instrument_rules, now=now)
    return SimpleNamespace(program=program, profile=profile, protocol=protocol, result=result, now=now,
                           artifact=artifact, parameters=parameters_json(program), bars=tuple(bars),
                           decisions=tuple(decisions), registry=registry, archive=archive, raw=raw)


def rejected(call, code=None):
    try:
        call()
    except S.StrategyEvidenceError as exc:
        if code is not None:
            assert str(exc) == code, (str(exc), code)
        return
    raise AssertionError('invalid carry evidence accepted')


def assessment(sample, result=None, **changes):
    args = dict(profile_contract_digest=sample.protocol.profile_contract_digest,
                rule_terms_digest=sample.protocol.rule_terms_digest,
                strategy_code_sha256=sample.protocol.strategy_code_sha256, now=sample.now)
    args.update(changes)
    return S.assess_strategy(sample.protocol, sample.result if result is None else result, **args)


def test_actual_carry_evaluator_issues_a_qualified_synthetic_fixture_without_research_authority():
    sample = fixture_capture()
    result = sample.result
    assert type(result) is S.CarryValidationResult and result.schema_version == 2
    report = assessment(sample)
    assert report.math_qualified and not report.research_review_ready and not report.execution_ready
    assert report.reasons == ('STRATEGY_TRUSTED_REVIEW_REQUIRED',)
    assert result.primary.completed_roundtrips >= 20 and result.family_adjusted_p <= float(sample.protocol.alpha)
    assert result.primary.total_return > 0 and result.double_cost.total_return > 0
    assert result.extra_bar_delay.total_return > 0 and result.benchmark_excess_mean > 0
    assert D(result.primary.terminal_units) > 0
    assert result.terminal_accounting == 'mark_open_positions'
    assert 'MANAGED_DEADLINE_REACHED' in result.primary.terminal_execution_block_reasons


def test_carry_protocol_strict_revision_behavior_and_explicit_schema_roundtrip():
    sample = fixture_capture()
    body = json.loads(S.protocol_json(sample.protocol))
    assert body['schema_version'] == 2 and body['behavior_revision'] == M.BEHAVIOR_REVISION
    assert S.parse_protocol(json.dumps(body)) == sample.protocol
    for mutate in (lambda b: b.update(schema_version=1), lambda b: b.update(evaluator_revision='forward-paper-v1'),
                   lambda b: b.update(management_behavior_sha256='f' * 64),
                   lambda b: b.update(universe_rule_sha256='f' * 64),
                   lambda b: b.update(history_storage_sha256='f' * 64),
                   lambda b: b.update(terminal_accounting='terminal_sell')):
        altered = dict(body); mutate(altered)
        rejected(lambda: S.parse_protocol(json.dumps(altered)))
    for name in ('behavior_revision', 'terminal_accounting', 'management_behavior_sha256'):
        altered = {key: value for key, value in body.items() if key != name}
        rejected(lambda: S.parse_protocol(json.dumps(altered)))
        rejected(lambda: S.parse_protocol(json.dumps(body | {name: None})))


def test_legacy_protocol_and_review_binding_keep_omitted_fields_and_digest_bytes():
    from tests.launch_strategy import fixture_capture as legacy_fixture
    protocol, _, _, _, _, result, _ = legacy_fixture(source_kind='synthetic')
    encoded = S._plain(protocol)
    assert not {'behavior_revision', 'terminal_accounting', 'management_behavior_sha256'} & set(encoded)
    expected = hashlib.sha256(json.dumps(encoded, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()).hexdigest()
    assert S.evidence_digest(protocol) == expected
    assert S.parse_protocol(S.protocol_json(protocol)) == protocol
    binding = S.ReviewBinding(protocol_digest=S.evidence_digest(protocol), evidence_digest=S.evidence_digest(result),
        registry_digest=result.registry_digest, inputs_digest=result.inputs_digest, strategy_id=protocol.strategy_id,
        strategy_code_sha256=protocol.strategy_code_sha256, profile_contract_digest=protocol.profile_contract_digest,
        rule_terms_digest=protocol.rule_terms_digest, capture_end=result.ended_at)
    assert len(S._plain(binding)) == 9 and 'evaluator_revision' not in S._plain(binding)


def test_manual_clone_or_mutated_carry_result_never_passes_issued_registry_check():
    sample = fixture_capture()
    cloned = replace(sample.result)
    rejected(lambda: assessment(sample, cloned), 'STRATEGY_RESULT_NOT_ISSUED_OR_MUTATED')
    result = S.evaluate_capture_json(sample.protocol, sample.raw, sample.profile.instrument_rules, now=sample.now)
    object.__setattr__(result, 'terminal_accounting', 'terminal_sell')
    rejected(lambda: assessment(sample, result), 'STRATEGY_RESULT_NOT_ISSUED_OR_MUTATED')


def test_carry_result_has_a_separate_domain_and_no_legacy_result_coercion():
    sample = fixture_capture()
    raw = json.dumps(S._plain(sample.result), sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode('ascii')
    assert S.evidence_digest(sample.result) == hashlib.sha256(b'tradegen-fixed-carry-validation/2\x00' + raw).hexdigest()
    assert S.evidence_digest(sample.result) != hashlib.sha256(raw).hexdigest()
    legacy_shape = {name: getattr(sample.result, name) for name in S.ValidationResult.__dataclass_fields__}
    rejected(lambda: assessment(sample, S.ValidationResult(**legacy_shape)), 'STRATEGY_COMPUTED_RESULT_REQUIRED')


def test_all_carry_prefixes_and_decisions_are_rederived_before_simulation():
    sample = fixture_capture()
    source = json.loads(sample.raw)
    source['decisions'][-1]['cause'] = 'always_cash'
    with patch('execution_launch.carry_evaluator.simulate_carry', side_effect=AssertionError('simulation before validation')):
        rejected(lambda: S.evaluate_capture_json(sample.protocol, json.dumps(source), sample.profile.instrument_rules,
                                                now=sample.now), 'STRATEGY_CARRY_CAPTURE_INVALID')
    changed = json.loads(sample.raw)
    changed['program_artifact_sha256'] = 'f' * 64
    rejected(lambda: S.evaluate_capture_json(sample.protocol, json.dumps(changed), sample.profile.instrument_rules,
                                            now=sample.now), 'STRATEGY_CARRY_CAPTURE_INVALID')


def test_legacy_capture_format_and_direct_legacy_evaluator_cannot_relabel_carry_protocol():
    sample = fixture_capture()
    rejected(lambda: S.evaluate_capture_json(sample.protocol, '{"registry":[],"source_kind":"synthetic","bars":[],"decisions":[]}',
        sample.profile.instrument_rules, now=sample.now), 'STRATEGY_CARRY_CAPTURE_INVALID')
    rejected(lambda: S.run_paper_validation(sample.protocol, sample.bars, (), sample.profile.instrument_rules,
        registry=sample.registry, source_kind='synthetic', now=sample.now), 'STRATEGY_EVALUATOR_UNSUPPORTED')


def test_carry_validation_preserves_rules_grid_and_finish_time_requirements():
    sample = fixture_capture()
    rejected(lambda: S.run_carry_validation(sample.protocol, sample.archive,
        replace(sample.profile.instrument_rules, fee_fraction=D('0.002')), now=sample.now), 'STRATEGY_RULES_MISMATCH')
    rejected(lambda: S.run_carry_validation(sample.protocol, sample.archive, sample.profile.instrument_rules,
        now=sample.now - timedelta(microseconds=1)), 'STRATEGY_CAPTURE_NOT_FINISHED')
    rejected(lambda: S.run_carry_validation(sample.protocol, replace(sample.archive, bars=sample.bars[:-1],
        decisions=sample.decisions[:-1]), sample.profile.instrument_rules, now=sample.now), 'STRATEGY_CARRY_CAPTURE_INVALID')


def test_signed_accounting_identity_and_realized_vs_valuation_are_separate_in_request():
    sample = fixture_capture()
    metrics = sample.result.primary
    assert (Fraction(metrics.terminal_cash_quote) + Fraction(metrics.terminal_units) * Fraction(metrics.terminal_mark_quote)
            - Fraction(sample.protocol.initial_cash_quote) == Fraction(metrics.realized_net_profit_quote)
            + Fraction(metrics.unrealized_net_profit_quote))
    request = Q.build_review_request(sample.profile, sample.protocol, sample.result, now=sample.now,
                                    program_artifact=sample.artifact, parameters_json=sample.parameters)
    assert request['schema_version'] == 3
    summary = request['computed_summary']['metrics']
    assert summary['valuation_total_return'] == metrics.total_return and 'total_return' not in summary
    assert summary['realized_net_profit_quote'] == metrics.realized_net_profit_quote
    assert summary['unrealized_net_profit_quote'] == metrics.unrealized_net_profit_quote
    assert summary['terminal_units'] == metrics.terminal_units
    assert all(value is False for value in request['authority'].values())


def test_carry_requests_family_binding_and_legacy_schema_are_not_interchangeable():
    sample = fixture_capture()
    request = Q.build_review_request(sample.profile, sample.protocol, sample.result, now=sample.now,
                                    program_artifact=sample.artifact, parameters_json=sample.parameters)
    family = Q.build_family_commitment(plan_digest='a' * 64,
        capture_digests={sample.protocol.study_id: hashlib.sha256(sample.raw).hexdigest()},
        result_digests={sample.protocol.study_id: S.evidence_digest(sample.result)})
    bound = Q.bind_review_family(request, family)
    assert bound['schema_version'] == 4 and Q.parse_review_request(Q.review_request_json(bound)) == bound
    for version in (1, 2):
        altered = dict(bound); altered['schema_version'] = version
        altered['request_sha256'] = hashlib.sha256(Q._canonical({k:v for k,v in altered.items() if k != 'request_sha256'}).encode()).hexdigest()
        try:
            Q.parse_review_request(json.dumps(altered))
        except Q.ReviewRequestError:
            pass
        else:
            raise AssertionError('carry summary accepted as legacy review')


def test_actual_carry_study_family_requires_every_capture_and_authenticates_real_temporary_signatures():
    from execution_control.owner_authority import CurrentOwnerAuthority
    from execution_launch import study_review as V
    from execution_launch.driver import DeploymentWindow, describe_fixed_driver, make_fixed_carry_driver
    from execution_launch.review_auth import review_body, review_signing_bytes
    from tests.launch_windows_owner_authority import keys, real_code_hash, signed_home

    sample = fixture_capture()
    frozen_profile = replace(sample.profile, instrument_rules=replace(sample.profile.instrument_rules,
                             asof=sample.protocol.preregistered_at))
    programs = tuple(replace(sample.program, strategy_id=name) for name in ('carry-A', 'carry-B'))
    plan = U.build_study_plan(frozen_profile, programs, template=sample.protocol,
                             plan_id='invented-carry-plan', asset='BTC', risk_group='crypto')
    assert plan.selection_rule == U.CARRY_SELECTION_RULE
    assert U.parse_study_plan(U.study_plan_json(plan)) == plan
    captures, results, reviews = {}, {}, {}
    for candidate in plan.candidates:
        decisions, marks, chain = [], [], ''
        for index, row in enumerate(sample.bars):
            marks.append(row.mark); chain = S.evidence_digest((chain, row))
            decisions.append(M.derive_fixed_decision_v2(candidate.program, tuple(marks), bar_index=index,
                decided_at=row.received_at, history_sha256=chain))
        archive = make_archive_v2(plan.registry, 'prospective_paper_capture', candidate.program,
            program_artifact=sample.artifact, bars=sample.bars, decisions=tuple(decisions))
        raw = capture_json_v2(archive).encode('ascii')
        captures[candidate.protocol.study_id] = raw
        results[candidate.protocol.study_id] = S.evaluate_capture_json(candidate.protocol, raw,
            sample.profile.instrument_rules, now=sample.now)
    family = Q.build_family_commitment(plan_digest=U.validate_study_plan(plan),
        capture_digests={name: hashlib.sha256(raw).hexdigest() for name, raw in captures.items()},
        result_digests={name: S.evidence_digest(result) for name, result in results.items()})
    key = keys()[0]
    fingerprint = 'SHA256:' + hashlib.sha256(key.public_key().public_bytes_raw()).hexdigest()

    def no_history(*args):
        raise AssertionError('research review must not consume live history')

    for candidate in plan.candidates:
        identifier = candidate.protocol.study_id
        profile = replace(sample.profile, strategy_id=candidate.program.strategy_id,
                          strategy_code_sha256=program_digest(candidate.program, sample.artifact))
        request = Q.build_review_request(profile, candidate.protocol, results[identifier], now=sample.now,
                                        program_artifact=sample.artifact, parameters_json=parameters_json(candidate.program))
        request = Q.bind_review_family(request, family)
        assert request['schema_version'] == 4 and request['computed_summary']['mathematical_criteria_met'] is True
        driver = make_fixed_carry_driver(candidate.program, candidate.protocol, profile,
            window=DeploymentWindow(deployment_id='synthetic-family-window', start=sample.now,
                                    end=sample.now + timedelta(hours=1)),
            history_provider=no_history, history_verifier=no_history, program_artifact=sample.artifact)
        signed = review_body(request, asdict(describe_fixed_driver(driver)), deployment_code_hash=real_code_hash(),
            audit_sha256=hashlib.sha256(b'invented whole-family source audit').hexdigest(), owner_fingerprint=fingerprint,
            issued_at=sample.now, expires_at=sample.now + timedelta(minutes=30))
        reviews[identifier] = json.dumps({'body': signed,
            'signature_b64': base64.b64encode(key.sign(review_signing_bytes(signed))).decode('ascii')})
    with signed_home():
        authority = CurrentOwnerAuthority(clock=lambda: sample.now)
        def select(captured):
            return V.authenticate_study_selection(plan, profile=sample.profile, captures=captured, reviews=reviews,
                evaluated_at=sample.now, clock=lambda: sample.now, authority_provider=authority)
        selected = select(captures)
        assert selected.source_reviews_authenticated and selected.selection.selected_strategy_id == 'carry-A'
        assert not selected.selection.execution_ready and len(selected.selection.rows) == 2
        incomplete = {key: value for key, value in captures.items() if key == plan.candidates[0].protocol.study_id}
        try:
            select(incomplete)
        except V.StudyReviewError as exc:
            assert str(exc) == 'STUDY_REVIEW_CAPTURE_FAMILY_INCOMPLETE'
        else:
            raise AssertionError('partial carry family selected')
        altered = dict(captures)
        second = plan.candidates[1].protocol.study_id
        altered[second] += b' '
        try:
            select(altered)
        except V.StudyReviewError as exc:
            assert str(exc) == 'STUDY_REVIEW_SIGNED_FAMILY_MISMATCH'
        else:
            raise AssertionError('changed non-winning capture ignored')


def test_runner_preserves_strategy_sell_metadata_and_refuses_order_construction_when_blocked():
    from execution_launch import runner as R
    signal = R.Signal(signal_id='blocked-sell', action='hold', decision_state='cash_target',
                      decision_cause='trend_not_above', execution_block_reasons=('MANAGED_AUTHORITY_UNAVAILABLE',))
    metadata = R._signal_metadata(signal)
    assert metadata['decision_state'] == 'cash_target' and metadata['decision_cause'] == 'trend_not_above'
    try:
        R.Runner._order(object(), signal, None)
    except R.RunnerError as exc:
        assert str(exc) == 'RUNNER_SIGNAL_EXECUTION_BLOCKED'
    else:
        raise AssertionError('execution-blocked signal reached order construction')
    result = R.TickResult(mode='rehearsal', status='blocked', reasons=signal.execution_block_reasons, **metadata)
    assert result.status == 'blocked' and result.decision_state == 'cash_target'
    assert R._signal_metadata(R.Signal(signal_id='legacy', action='hold')) == dict(
        decision_state=None, decision_cause=None, execution_block_reasons=())


def test_runner_metadata_cannot_turn_warmup_unavailable_or_long_target_into_sell():
    from execution_launch import runner as R
    cases = (R.Signal(signal_id='a', action='exit', decision_state='long_target', decision_cause='trend_above'),
             R.Signal(signal_id='a', action='entry', decision_state='cash_target', decision_cause='always_cash'),
             R.Signal(signal_id='a', action='hold', decision_state='unavailable', decision_cause='input_unavailable'),
             R.Signal(signal_id='a', action='hold', decision_state='long_target', decision_cause='benchmark_buy_hold'),
             R.Signal(signal_id='a', action='hold', execution_block_reasons=('MANAGED_DEADLINE_REACHED',)),
             R.Signal(signal_id='a', action='hold', decision_state='warmup', decision_cause='insufficient_history',
                      execution_block_reasons=('INVENTED_PERMISSION',)))
    for signal in cases:
        try:
            R._signal_metadata(signal)
        except R.RunnerError as exc:
            assert str(exc) == 'RUNNER_SIGNAL_METADATA_INVALID'
        else:
            raise AssertionError('inconsistent verdict accepted')
