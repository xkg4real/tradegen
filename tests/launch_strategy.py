"""Invented paper captures only; no old research data or genuine authorization.

A deliberately predictable sawtooth fixture tests that a planted edge survives
cost/lag checks. Its labels/review receipts are synthetic test doubles, never
statistical evidence or approval for a real account.
"""
from dataclasses import asdict, replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal, localcontext
import json

from execution_control.model import InstrumentRules, rules_digest
from execution_launch.profile import rule_terms_digest
from execution_launch.strategy import (
    EVALUATOR_REVISION, ForwardProtocol, PaperBar, PaperDecision, Registration, ReviewReceipt,
    StrategyEvidenceError, assess_strategy, capture_history_digests, evaluate_capture_json,
    evidence_digest, history_digest, parse_protocol, protocol_json,
    register_protocol, run_paper_validation, validate_registry,
)

D = Decimal
START = datetime(2030, 1, 1, tzinfo=timezone.utc)


def fixture_capture(*, source_kind='prospective_paper_capture', profile_digest='a'*64,
                    code_digest='b'*64, rules=None):
    rules = rules or InstrumentRules(venue='upbit', market='spot', symbol='KRW-BTC',
        lot_size=D('0.01'), tick_size=D('1'), min_quantity=D('0.01'), min_notional_krw=D('1'),
        fee_fraction=D('0.001'), asof=START-timedelta(days=1), source_digest='c'*64)
    count = 251
    protocol = ForwardProtocol(schema_version=1, study_id='future-fixture-v1', strategy_id='test-strategy',
        strategy_code_sha256=code_digest, capture_source_id='fixture-source',
        capture_source_code_sha256='e'*64, evaluator_revision=EVALUATOR_REVISION,
        profile_contract_digest=profile_digest,
        rule_terms_digest=rule_terms_digest(rules), venue=rules.venue, market=rules.market,
        symbol=rules.symbol, quote_currency='KRW', preregistered_at=START-timedelta(days=1),
        capture_start=START, capture_end=START+timedelta(days=count-1), initial_cash_quote=D('1000'),
        fee_fraction=D('0.001'), slippage_bps=D('0'), bar_seconds=86400, minimum_fill_delay_seconds=1,
        minimum_observations=200, minimum_roundtrips=20, block_length=20, bootstrap_replications=999,
        family_members=('test-strategy',), alpha=D('0.05'), max_drawdown=D('0.2'),
        review_max_age_seconds=86400, seed=991)
    bars = tuple(PaperBar(observed_at=START+timedelta(days=i),
        received_at=START+timedelta(days=i, seconds=1), bid=D(100+10*(i%10)), ask=D(100+10*(i%10)),
        mark=D(100+10*(i%10)), quote_krw=D('1'), source_sha256=evidence_digest(('fake-source', i)))
        for i in range(count))
    prefixes = capture_history_digests(bars)
    decisions = tuple(PaperDecision(bar_index=i, decided_at=bars[i].received_at,
        history_sha256=prefixes[i], target_fraction=D(1 if i%10 < 5 else 0)) for i in range(count-1))
    now = bars[-1].received_at
    registry = register_protocol(protocol)
    result = run_paper_validation(protocol, bars, decisions, rules, registry=registry,
                                 source_kind=source_kind, now=now)
    return protocol, bars, decisions, rules, registry, result, now


def fixture_review(now):
    def verify(binding):
        return ReviewReceipt(binding_digest=evidence_digest(binding), reviewer_id='fixture-only',
            source_review_sha256='d'*64, reviewed_at=now, expires_at=now+timedelta(hours=1))
    return verify


def assessment(protocol, result, now, **changes):
    args=dict(profile_contract_digest=protocol.profile_contract_digest,
              rule_terms_digest=protocol.rule_terms_digest,
              strategy_code_sha256=protocol.strategy_code_sha256, now=now)
    args.update(changes)
    return assess_strategy(protocol, result, **args)


def rejected(call, code=None):
    try:
        call()
    except StrategyEvidenceError as exc:
        if code:
            assert str(exc) == code, (str(exc), code)
        return
    raise AssertionError('invalid strategy evidence accepted')


def test_planted_future_paper_edge_requires_explicit_review_and_never_grants_permission():
    p, bars, decisions, rules, registry, result, now = fixture_capture()
    missing = assessment(p, result, now)
    assert missing.math_qualified and not missing.research_review_ready
    assert missing.reasons == ('STRATEGY_TRUSTED_REVIEW_REQUIRED',)
    accepted = assessment(p, result, now, review_verifier=fixture_review(now))
    assert accepted.math_qualified and accepted.research_review_ready and not accepted.execution_ready
    assert result.primary.completed_roundtrips == 25
    assert result.primary.total_return > 0 and result.double_cost.total_return > 0
    assert result.extra_bar_delay.total_return > 0
    assert 0 < result.benchmark_p <= result.family_adjusted_p <= 0.05
    assert result.primary.terminal_units == '0' and result.primary.cash_nonnegative
    assert result.primary.total_fees_quote > 0


def test_unchanged_current_rule_refresh_preserves_research_terms_but_not_execution_digest():
    p, bars, decisions, rules, registry, result, now = fixture_capture()
    refreshed = replace(rules, asof=now)
    assert rules_digest(refreshed) != rules_digest(rules)
    assert rule_terms_digest(refreshed) == rule_terms_digest(rules)
    assert assessment(p, result, now, rule_terms_digest=rule_terms_digest(refreshed),
                      review_verifier=fixture_review(now)).research_review_ready
    changed = replace(refreshed, fee_fraction=D('0.002'))
    report = assessment(p, result, now, rule_terms_digest=rule_terms_digest(changed),
                        review_verifier=fixture_review(now))
    assert not report.research_review_ready and 'STRATEGY_DEPLOYMENT_BINDING_MISMATCH' in report.reasons


def test_retrospective_and_synthetic_sources_are_never_promoted_by_hash_or_review():
    for kind in ('synthetic', 'retrospective_replay'):
        p, _, _, _, _, result, now = fixture_capture(source_kind=kind)
        calls=[]
        report=assessment(p, result, now, review_verifier=lambda value:calls.append(value))
        assert report.math_qualified and not report.research_review_ready and not calls
        assert 'STRATEGY_NONPROSPECTIVE_SOURCE' in report.reasons
    p, _, _, _, _, _, now = fixture_capture()
    rejected(lambda:assessment(p, {'research_label':'promising_exploratory','production_status':'PASS'}, now),
             'STRATEGY_COMPUTED_RESULT_REQUIRED')


def test_review_receipt_cannot_be_boolean_wrong_digest_future_expired_or_raw_exception():
    p, _, _, _, _, result, now = fixture_capture()
    valid = fixture_review(now)
    def failure(binding):
        raise RuntimeError('private-provider-text')
    variants=(lambda b:True, lambda b:None,
        lambda b:replace(valid(b), binding_digest='e'*64),
        lambda b:replace(valid(b), reviewed_at=now+timedelta(seconds=1)),
        lambda b:replace(valid(b), expires_at=now),
        lambda b:replace(valid(b), expires_at=now+timedelta(days=2)), failure)
    for verifier in variants:
        report=assessment(p,result,now,review_verifier=verifier)
        assert not report.research_review_ready
        assert report.reasons==('STRATEGY_TRUSTED_REVIEW_UNVERIFIED',)
        assert 'private-provider-text' not in repr(report)


def test_profile_code_window_and_evidence_expiry_bindings_are_enforced():
    p, _, _, _, _, result, now = fixture_capture()
    for change in ({'profile_contract_digest':'e'*64},{'strategy_code_sha256':'e'*64},
                   {'now':now-timedelta(seconds=1)},{'now':now+timedelta(days=2)}):
        args=dict(review_verifier=fixture_review(now));args.update(change)
        stamp=args.pop('now',now)
        assert not assessment(p,result,stamp,**args).research_review_ready
    changed=replace(p,initial_cash_quote=D('2000'))
    assert 'STRATEGY_PROTOCOL_RESULT_MISMATCH' in assessment(changed,result,now).reasons


def test_summary_forgery_and_mutation_do_not_replace_replayed_arithmetic():
    p, _, _, _, _, result, now = fixture_capture()
    rejected(lambda:assessment(p,replace(result),now),'STRATEGY_RESULT_NOT_ISSUED_OR_MUTATED')
    original=result.family_adjusted_p
    try:
        object.__setattr__(result,'family_adjusted_p',0.000001)
        rejected(lambda:assessment(p,result,now),'STRATEGY_RESULT_NOT_ISSUED_OR_MUTATED')
    finally:
        object.__setattr__(result,'family_adjusted_p',original)


def test_registration_is_append_only_and_capture_cannot_precede_the_protocol():
    p, _, _, _, registry, _, _ = fixture_capture()
    assert validate_registry(registry)==registry[-1].entry_digest
    rejected(lambda:register_protocol(p,registry),'STRATEGY_STUDY_ALREADY_REGISTERED')
    rejected(lambda:validate_registry((replace(registry[0],protocol_digest='e'*64),)),
             'STRATEGY_REGISTRY_CHAIN_INVALID')
    rejected(lambda:register_protocol(replace(p,preregistered_at=p.capture_start)),
             'STRATEGY_PREREGISTRATION_NOT_BEFORE_CAPTURE')
    second=register_protocol(replace(p,study_id='future-fixture-v2'),registry)
    rejected(lambda:validate_registry(second[1:]),'STRATEGY_REGISTRY_CHAIN_INVALID')


def test_capture_rejects_gaps_duplicate_times_incomplete_window_and_future_availability():
    p,bars,decisions,rules,registry,_,now=fixture_capture()
    def run(changed_bars=bars, changed_decisions=decisions, stamp=now):
        return run_paper_validation(p,changed_bars,changed_decisions,rules,registry=registry,
                                   source_kind='synthetic',now=stamp)
    rejected(lambda:run(bars[:-1],decisions[:-1]),'STRATEGY_CAPTURE_WINDOW_INCOMPLETE')
    altered=list(bars);altered[5]=replace(altered[5],observed_at=altered[4].observed_at)
    rejected(lambda:run(tuple(altered)))
    altered=list(bars);altered[5]=replace(altered[5],received_at=altered[5].observed_at-timedelta(seconds=1))
    rejected(lambda:run(tuple(altered)))
    rejected(lambda:run(stamp=now-timedelta(seconds=1)),'STRATEGY_CAPTURE_NOT_FINISHED')
    rejected(lambda:run(changed_decisions=decisions[:-1]),'STRATEGY_DECISION_COVERAGE_INCOMPLETE')


def test_decision_history_and_timing_are_causal_and_no_leverage_is_accepted():
    p,bars,decisions,rules,registry,_,now=fixture_capture()
    assert history_digest(bars[:7])==capture_history_digests(bars)[6]
    for modified in (replace(decisions[0],history_sha256=history_digest(bars)),
                     replace(decisions[0],decided_at=bars[0].observed_at),
                     replace(decisions[0],decided_at=bars[1].observed_at),
                     replace(decisions[0],target_fraction=D('1.01')),
                     replace(decisions[0],bar_index=1)):
        rejected(lambda modified=modified:run_paper_validation(p,bars,(modified,)+decisions[1:],rules,
            registry=registry,source_kind='synthetic',now=now))


def test_fee_floor_rule_changes_off_tick_and_too_small_cash_are_not_hidden():
    p,bars,decisions,rules,registry,_,now=fixture_capture()
    rejected(lambda:run_paper_validation(p,bars,decisions,replace(rules,fee_fraction=D('0.01')),
        registry=registry,source_kind='synthetic',now=now),'STRATEGY_RULES_MISMATCH')
    p=replace(p,initial_cash_quote=D('0.001'))
    result=run_paper_validation(p,bars,decisions,rules,registry=register_protocol(p),source_kind='synthetic',now=now)
    assert result.primary.rejected_small_orders > 0 or result.primary.completed_roundtrips == 0
    assert not assessment(p,result,now).math_qualified
    altered=list(bars);altered[0]=replace(altered[0],ask=D('100.5'))
    rejected(lambda:run_paper_validation(p,tuple(altered),decisions,rules,registry=register_protocol(p),
        source_kind='synthetic',now=now),'STRATEGY_QUOTE_OFF_TICK')


def test_costs_are_nonnegative_cash_is_exact_and_ambient_decimal_precision_has_no_effect():
    p,bars,decisions,rules,registry,baseline,now=fixture_capture()
    with localcontext() as numeric:
        numeric.prec=2
        result=run_paper_validation(p,bars,decisions,rules,registry=registry,source_kind='prospective_paper_capture',now=now)
    assert result.primary==baseline.primary and result.net_returns==baseline.net_returns
    assert result.double_cost.total_return <= result.primary.total_return


def test_multiplicity_counts_the_frozen_family_and_p_values_are_nonzero():
    p,bars,decisions,rules,_,baseline,now=fixture_capture()
    p=replace(p,family_members=tuple(sorted(['test-strategy']+['unused-'+str(i) for i in range(99)])))
    result=run_paper_validation(p,bars,decisions,rules,registry=register_protocol(p),source_kind='synthetic',now=now)
    assert result.benchmark_p==baseline.benchmark_p
    assert result.family_adjusted_p==min(1.0,100*result.benchmark_p)
    assert result.family_adjusted_p > float(p.alpha)
    assert not assessment(p,result,now).math_qualified


def test_protocol_json_is_strict_canonical_and_does_not_import_claimed_pass():
    p,*_=fixture_capture()
    encoded=protocol_json(p)
    assert parse_protocol(encoded)==p
    assert evidence_digest(parse_protocol(encoded))==evidence_digest(p)
    bad=(encoded.replace('"schema_version": 1','"schema_version": 1, "schema_version": 1'),
         encoded.replace('"alpha": "0.05"','"alpha": 0.05'),
         encoded.replace('"alpha": "0.05"','"alpha": NaN'),
         encoded.replace('"alpha": "0.05"','"alpha": "5e-2"'),
         encoded[:-2]+', "eligible": true}', ' '*65537)
    for raw in bad:
        rejected(lambda raw=raw:parse_protocol(raw))


def test_capture_json_recomputes_results_and_refuses_a_supplied_summary():
    from execution_launch.strategy import _plain
    p,bars,decisions,rules,registry,result,now=fixture_capture()
    payload={'registry':_plain(registry),'source_kind':'prospective_paper_capture',
             'bars':_plain(bars),'decisions':_plain(decisions)}
    replay=evaluate_capture_json(p,json.dumps(payload),rules,now=now)
    assert evidence_digest(replay)==evidence_digest(result)
    assert replay is not result
    payload['eligible']=True
    rejected(lambda:evaluate_capture_json(p,json.dumps(payload),rules,now=now),
             'STRATEGY_CAPTURE_JSON_SCHEMA_INVALID')


def test_unsupported_fx_market_and_source_or_evaluator_versions_are_refused():
    p, _, _, _, _, _, _ = fixture_capture()
    for changes in ({'venue':'okx', 'symbol':'BTC-USDT', 'quote_currency':'USDT'},
                    {'venue':'kis', 'market':'nasd', 'symbol':'AAPL', 'quote_currency':'USD'},
                    {'venue':'kis', 'market':'krx', 'symbol':'005930'},
                    {'quote_currency':'USD'}, {'symbol':123}):
        rejected(lambda: register_protocol(replace(p, **changes)),
                 'STRATEGY_EVALUATOR_SCOPE_UNSUPPORTED')
    rejected(lambda: register_protocol(replace(p, evaluator_revision='forward-paper-v2')),
             'STRATEGY_EVALUATOR_UNSUPPORTED')
    rejected(lambda: register_protocol(replace(p, capture_source_code_sha256='unknown')),
             'STRATEGY_DIGEST_INVALID')
    assert evidence_digest(replace(p, capture_source_code_sha256='f'*64)) != evidence_digest(p)


def test_one_roundtrip_matches_independent_cash_fee_tick_and_lot_arithmetic():
    from execution_launch.strategy import _simulate
    p,bars,decisions,rules,_,_,_=fixture_capture()
    # 1,000 cash buys 9.08 at 110, paying .9988; 9.08 sells at 160,
    # paying 1.4528: terminal cash 1,451.5484 and one completed roundtrip.
    base,_=_simulate(p,bars[:8],decisions[:7],rules)
    assert base.completed_roundtrips==1
    assert base.total_return==float(D('0.4515484'))
    assert base.total_fees_quote==float(D('2.4516'))
    assert base.turnover_quote==float(D('2451.6'))
    assert base.max_drawdown==float(D('0.0009988'))
    # One adverse basis point rounds buy 110.011 up to 111 and sale
    # 159.984 down to 159; 9 units leave final cash 1,429.570.
    shifted,_=_simulate(replace(p,slippage_bps=D('1')),bars[:8],decisions[:7],rules)
    assert shifted.total_return==float(D('0.42957'))
    assert shifted.total_fees_quote==float(D('2.430'))
    assert shifted.turnover_quote==float(D('2430'))
