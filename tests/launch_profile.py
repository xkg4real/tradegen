"""Private profile boundaries tested with invented values and supplied contexts."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal, localcontext
import json
from pathlib import Path

from core.compliance import model as M
from execution_control.model import InstrumentRules
from execution_control.risk import RiskObservation, evaluate
from execution_launch.profile import (
    AccountingConventions, LaunchProfile, PolicyInputs, ProfileError,
    limit_change_earliest_date, parse_profile_json, preflight_profile, profile_body,
    profile_digest, profile_contract_digest, rule_terms_digest, risk_policy,
)
from tests import compliance_fixtures as F

D = Decimal
NOW = datetime(2026, 10, 23, 1, tzinfo=timezone.utc)


def fixture_profile(now=NOW):
    return LaunchProfile(schema_version=1, profile_id="test-profile", venue="upbit", account_scope="test-scope",
        market="spot", symbol="KRW-BTC", quote_currency="KRW", time_in_force="gtc", strategy_id="test-strategy",
        strategy_code_sha256="b"*64, policy=PolicyInputs(version="fixture-v1", source_sha256="a"*64,
            initial_equity=D("2000"), drawdown_activation_equity=D("8000"), positive_profit_loss_fraction=D("0.2"),
            peak_drawdown_fraction=D("0.25"), zero_profit_day_target_fraction=D("0.1"),
            first_day_loss_budget=D("10"), zero_profit_day_loss_budget=D("8")),
        conventions=AccountingConventions(valuation="marked_equity", daily_loss="externally_reconciled",
            external_flows="externally_cashflow_adjusted", realized_profit="fifo_all_fees_krw",
            fx="current_marks_execution_time_fills", rounding="fifo_floor_18dp_remainder_to_final",
            day_boundary="Asia/Seoul", first_day_scope="first_trading_day_only"),
        instrument_rules=InstrumentRules(venue="upbit", market="spot", symbol="KRW-BTC", lot_size=D("0.01"),
            tick_size=D("1"), min_quantity=D("0.01"), min_notional_krw=D("20"), fee_fraction=D("0.001"),
            asof=now, source_digest="c"*64))


def context(now=NOW, **changes):
    args=dict(date=now.astimezone(M.KST).date(), session=M.SessionState(),
              owner=M.OwnerState(status="OK", limits={"total_loss_floor_krw":2000.0,"daily_loss_krw":100.0}))
    args.update(changes)
    return F.ctx(**args)


def rejected(call, code=None):
    try:
        call()
    except ProfileError as exc:
        if code is not None:
            assert exc.code==code, (exc.code, code)
        return
    raise AssertionError("expected explicit profile refusal")


def test_unknown_owner_choices_remain_missing_and_cannot_construct_risk_policy():
    profile=parse_profile_json('{"schema_version":1,"profile_id":"incomplete"}')
    report=preflight_profile(profile,now=NOW)
    assert not report.profile_complete and not report.prerequisites_ready and not report.execution_ready
    assert any(i.field=="policy.first_day_loss_budget" for i in report.issues)
    assert any(i.field=="policy.zero_profit_day_loss_budget" for i in report.issues)
    assert "SIGNED_CONTEXT_REQUIRED" in report.reasons
    rejected(lambda:risk_policy(profile),"POLICY_INPUTS_INCOMPLETE")


def test_strict_json_refuses_duplicates_unknown_keys_numerical_ambiguity_and_oversize():
    for raw in ('{"schema_version":1,"schema_version":1,"profile_id":"x"}',
                '{"schema_version":1,"profile_id":"x","secret":"do-not-echo"}',
                '{"schema_version":1.0,"profile_id":"x"}',
                '{"schema_version":1,"profile_id":"x","policy":{"initial_equity":NaN}}',
                '{"schema_version":1,"profile_id":"x","policy":{"initial_equity":100}}',
                '{"schema_version":1,"profile_id":"x","policy":{"initial_equity":"1e5"}}',
                '{"schema_version":1,"profile_id":"x","policy":{"initial_equity":"-1"}}',
                '{"schema_version":true,"profile_id":"x"}',b'\xff',' '*65537):
        rejected(lambda raw=raw:parse_profile_json(raw))
    try:
        parse_profile_json('{"schema_version":1,"profile_id":"x","secret":"do-not-echo"}')
    except ProfileError as exc:
        assert 'do-not-echo' not in str(exc) and 'secret' not in str(exc)


def test_exact_decimal_roundtrip_and_digest_ignore_numeric_context_and_object_key_order():
    profile=fixture_profile()
    raw=json.dumps(profile_body(profile))
    parsed=parse_profile_json(raw)
    assert parsed==profile
    with localcontext() as numeric:
        numeric.prec=2
        assert profile_digest(profile)==profile_digest(parsed)
        assert risk_policy(profile).first_day_loss_budget==D('10')
    body=profile_body(profile)
    body['policy']['initial_equity']='2000.00'
    assert profile_digest(parse_profile_json(json.dumps(body)))==profile_digest(profile)


def test_profile_digest_binds_scope_policy_strategy_rules_and_accounting_choices():
    profile=fixture_profile(); first=profile_digest(profile)
    for changed in (replace(profile,account_scope='other-scope'),replace(profile,strategy_code_sha256='d'*64),
                    replace(profile,policy=replace(profile.policy,first_day_loss_budget=D('11'))),
                    replace(profile,instrument_rules=replace(profile.instrument_rules,fee_fraction=D('0.002'))),
                    replace(profile,conventions=replace(profile.conventions,daily_loss='unimplemented'))):
        assert profile_digest(changed)!=first
    report=preflight_profile(replace(profile,conventions=replace(profile.conventions,daily_loss='unimplemented')),now=NOW)
    assert 'ACCOUNTING_CONVENTION_UNSUPPORTED' in report.reasons
    rejected(lambda:risk_policy(replace(profile,conventions=replace(profile.conventions,daily_loss='unimplemented'))))


def test_complete_profile_never_claims_execution_and_requires_current_signed_context():
    profile=fixture_profile()
    report=preflight_profile(profile,now=NOW)
    assert report.profile_complete and not report.prerequisites_ready and not report.execution_ready
    report=preflight_profile(profile,now=NOW,context=context())
    assert report.profile_complete and report.prerequisites_ready and not report.execution_ready and not report.issues
    for ctx,code in ((replace(context()),'SIGNED_CONTEXT_INVALID'),
                     (context(owner=None),'SIGNED_CONTEXT_INVALID'),
                     (context(active=None),'SIGNED_CONTEXT_INVALID'),
                     (context(owner=M.OwnerState(status='OK',limits=[])),'SIGNED_CONTEXT_INVALID'),
                     (context(date=NOW.date()-timedelta(days=1)),'SIGNED_CONTEXT_WRONG_SEOUL_DAY'),
                     (context(code_signed=False),'OWNER_APPROVALS_INCOMPLETE'),
                     (context(owner=M.OwnerState.broken('fixture')),'OWNER_APPROVALS_INCOMPLETE')):
        report=preflight_profile(profile,now=NOW,context=ctx)
        assert code in report.reasons and not report.prerequisites_ready


def test_context_mutation_and_nonfinite_or_inactive_limits_cannot_pass_preflight():
    profile=fixture_profile()
    mutated=context();mutated.owner.limits['daily_loss_krw']=999.0
    assert 'SIGNED_CONTEXT_INVALID' in preflight_profile(profile,now=NOW,context=mutated).reasons
    for limits in ({},{'total_loss_floor_krw':2000.0,'daily_loss_krw':0.0},
                   {'total_loss_floor_krw':1.0,'daily_loss_krw':100.0}):
        report=preflight_profile(profile,now=NOW,context=context(owner=M.OwnerState(status='OK',limits=limits)))
        assert not report.prerequisites_ready
        assert any(c in report.reasons for c in ('SIGNED_LIMIT_NOT_EFFECTIVE','SIGNED_PRINCIPAL_FLOOR_TOO_LOW'))
    ctx=context(owner=M.OwnerState(status='OK',limits={'total_loss_floor_krw':2000.0,'daily_loss_krw':100.0},halted_floors=frozenset({2000.0})))
    assert 'OWNER_HALT_PRESENT' in preflight_profile(profile,now=NOW,context=ctx).reasons


def test_scope_currency_time_in_force_and_rule_freshness_are_explicit():
    profile=fixture_profile()
    for changes,reason in (({'quote_currency':'USDT'},'QUOTE_CURRENCY_MISMATCH'),
                           ({'market':'krx'},'MARKET_VENUE_MISMATCH'),
                           ({'time_in_force':'day'},'TIME_IN_FORCE_MISMATCH'),
                           ({'symbol':'BTC-USDT'},'SYMBOL_VENUE_MISMATCH'),
                           ({'instrument_rules':None},'INSTRUMENT_RULES_REQUIRED')):
        assert reason in preflight_profile(replace(profile,**changes),now=NOW).reasons
    for seconds in (-1,301):
        changed=replace(profile,instrument_rules=replace(profile.instrument_rules,asof=NOW-timedelta(seconds=seconds)))
        assert 'INSTRUMENT_RULES_STALE_OR_FUTURE' in preflight_profile(changed,now=NOW).reasons
    krx=replace(profile,venue='kis',market='krx',symbol='123456',time_in_force='day',
                instrument_rules=InstrumentRules(venue='kis',market='krx',symbol='123456',lot_size=D('1'),
                    tick_size=D('1'),min_quantity=D('1'),min_notional_krw=D('0'),fee_fraction=D('0.001'),asof=NOW,source_digest='c'*64))
    assert preflight_profile(krx,now=NOW).profile_complete


def test_floor_equality_and_profit_target_keep_existing_risk_semantics():
    profile=fixture_profile();policy=risk_policy(profile)
    obs=RiskObservation(equity=D('2000'),prior_high_watermark=D('2000'),day_start_equity=D('2000'),
        current_day_realized_net_profit=D('0'),prior_day_realized_net_profit=None,observed_daily_loss=D('0'),
        approved_effective_floor=D('2000'),is_first_trading_day=True,asof=NOW)
    first=evaluate(policy,obs)
    assert not first.new_entry_blocked and first.daily_loss_budget==D('10')
    zero=replace(obs,is_first_trading_day=False,prior_day_realized_net_profit=D('0'))
    result=evaluate(policy,zero)
    larger=evaluate(replace(policy,zero_profit_day_target_fraction=D('10')),zero)
    assert result.daily_loss_budget==larger.daily_loss_budget==D('8')
    assert not result.new_entry_blocked and not larger.new_entry_blocked
    negative=evaluate(policy,replace(zero,prior_day_realized_net_profit=D('-1')))
    assert negative.new_entry_blocked and negative.daily_loss_budget==0


def test_zero_budget_is_explicit_and_distinct_from_unconfigured():
    profile=fixture_profile()
    zero=replace(profile,policy=replace(profile.policy,first_day_loss_budget=D('0')))
    missing=replace(profile,policy=replace(profile.policy,first_day_loss_budget=None))
    assert preflight_profile(zero,now=NOW).profile_complete
    assert not preflight_profile(missing,now=NOW).profile_complete
    assert profile_digest(zero)!=profile_digest(missing)
    rejected(lambda:risk_policy(missing),'POLICY_INPUTS_INCOMPLETE')


def test_inconsistent_policy_values_and_deliberately_mutated_exact_types_refuse():
    profile=fixture_profile()
    for changes,reason in (({'initial_equity':D('0')},'PRINCIPAL_MUST_BE_POSITIVE'),
                           ({'drawdown_activation_equity':D('1')},'ACTIVATION_BELOW_PRINCIPAL'),
                           ({'positive_profit_loss_fraction':D('1.01')},'POLICY_FRACTION_OUT_OF_RANGE'),
                           ({'peak_drawdown_fraction':D('1')},'POLICY_FRACTION_OUT_OF_RANGE')):
        changed=replace(profile,policy=replace(profile.policy,**changes))
        assert reason in preflight_profile(changed,now=NOW).reasons
        rejected(lambda changed=changed:risk_policy(changed))
    changed=replace(profile);object.__setattr__(changed,'schema_version',True)
    rejected(lambda:profile_digest(changed),'PROFILE_VERSION_UNSUPPORTED')
    changed=replace(profile,policy=replace(profile.policy));object.__setattr__(changed.policy,'initial_equity',2000.0)
    rejected(lambda:profile_digest(changed),'PROFILE_DECIMAL_INVALID')


def test_limit_timing_respects_first_setting_tightening_and_seoul_midnight():
    before=datetime(2026,10,23,14,59,59,tzinfo=timezone.utc)
    after=before+timedelta(seconds=1)
    assert limit_change_earliest_date(key='daily_loss_krw',previous=None,proposed=D('10'),signed_at=before).isoformat()=='2026-10-24'
    assert limit_change_earliest_date(key='daily_loss_krw',previous=None,proposed=D('10'),signed_at=after).isoformat()=='2026-10-25'
    assert limit_change_earliest_date(key='daily_loss_krw',previous=D('20'),proposed=D('10'),signed_at=before)==before.astimezone(M.KST).date()
    assert limit_change_earliest_date(key='total_loss_floor_krw',previous=D('20'),proposed=D('10'),signed_at=before).isoformat()=='2026-10-24'
    assert limit_change_earliest_date(key='total_loss_floor_krw',previous=D('10'),proposed=D('20'),signed_at=before)==before.astimezone(M.KST).date()
    rejected(lambda:limit_change_earliest_date(key='daily_loss_krw',previous=D('0'),proposed=D('10'),signed_at=before),'SIGNED_LIMIT_VALUE_INVALID')
    rejected(lambda:preflight_profile(fixture_profile(),now=datetime.max.replace(tzinfo=timezone.utc)),'PROFILE_AWARE_TIME_REQUIRED')


def test_public_example_is_explicitly_incomplete_and_never_execution_ready():
    root=Path(__file__).resolve().parents[1]
    profile=parse_profile_json((root/'docs/launch-profile.example.json').read_bytes())
    report=preflight_profile(profile,now=NOW)
    assert not report.profile_complete and not report.prerequisites_ready and not report.execution_ready
    assert profile.policy.initial_equity is None and profile.policy.first_day_loss_budget is None


def test_prospective_contract_refreshes_only_timestamp_and_keeps_economic_terms_bound():
    profile=fixture_profile()
    fresh=replace(profile,instrument_rules=replace(profile.instrument_rules,asof=NOW+timedelta(days=3)))
    assert profile_digest(fresh)!=profile_digest(profile)
    assert profile_contract_digest(fresh)==profile_contract_digest(profile)
    assert rule_terms_digest(fresh.instrument_rules)==rule_terms_digest(profile.instrument_rules)
    for field,value in (("fee_fraction",D('0.002')),("tick_size",D('2')),("source_digest",'d'*64)):
        changed=replace(profile,instrument_rules=replace(profile.instrument_rules,**{field:value}))
        assert profile_contract_digest(changed)!=profile_contract_digest(profile)
        assert rule_terms_digest(changed.instrument_rules)!=rule_terms_digest(profile.instrument_rules)
    changed=replace(profile,policy=replace(profile.policy,first_day_loss_budget=D('12')))
    assert profile_contract_digest(changed)!=profile_contract_digest(profile)
    # A stable research identity never excuses an old runtime observation.
    assert 'INSTRUMENT_RULES_STALE_OR_FUTURE' in preflight_profile(profile,now=NOW+timedelta(days=3)).reasons
