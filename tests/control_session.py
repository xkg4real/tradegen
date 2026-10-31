"""Real fresh-odds preparation in test-signed temporary homes only."""
from contextlib import contextmanager
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from types import SimpleNamespace

from core.compliance import model as M, owner
from core.odds import models
from execution_control.capability import digest
from execution_control.controller import AccountObservation, Controller
from execution_control.dry_run import DryRunAdapter
from execution_control.model import Order, InstrumentRules
from execution_control.risk import RiskPolicy, RiskObservation
from execution_control.session import prepare_session, verify_session
from execution_control.store import Journal
from execution_orders import upbit
from tests import compliance_fixtures as F, odds_fixtures as OF

D = Decimal


def refused(call):
    try:
        call()
    except ValueError:
        return
    raise AssertionError('expected refusal')


def selected(now):
    plan = OF.plan(start=now.astimezone(M.KST).date(), horizon_days=1)
    series = OF.fresh_series(end=(plan.start-timedelta(days=1)).isoformat())
    inputs = OF.inputs(plan, series, now=now)
    seed = models.market_seed(models.data_hashes(series, inputs.replay), inputs.calendar_sha256,
                              inputs.comparison_id, inputs.run_counter).hex()
    return plan, inputs, seed


@contextmanager
def signed_control(*, prepare=True, arm=True, results=(), policy=None, observation=None):
    """Reusable real signed home/session fixture; provider reads mutable env.observation."""
    with F.temp_home() as home, F.pubkey_at(home/'test-anchor.pem'), OF.chunk(), OF.pilots():
        key = F.full_home(home, venues_raw=OF.ODDS_VENUES,
                          limits={'total_loss_floor_krw':2000.0,'daily_loss_krw':5000.0}, cap=0.1)
        now=F.NOW
        policy=policy or RiskPolicy(version='fixture-v1',initial_equity=D('2000'),
            drawdown_activation_equity=D('8000'),positive_profit_loss_fraction=D('0.2'),
            peak_drawdown_fraction=D('0.25'),zero_profit_day_target_fraction=D('0.1'),
            first_day_loss_budget=D('10'),zero_profit_day_loss_budget=D('10'))
        observation=observation or AccountObservation(positions=M.Positions(equity_krw=1000000.0,holdings={},
                exposure={'upbit':M.Exposure(held_krw=0.0)}),account_scopes={'upbit':'fixture-account'},
            settled_cash_krw={('upbit','fixture-account'):D('1000000')},
            holdings={},held_exposure_krw={('upbit','fixture-account'):D('0')},
            risk=RiskObservation(equity=D('1000000'),prior_high_watermark=D('1000000'),
                day_start_equity=D('1000000'),current_day_realized_net_profit=D('0'),
                prior_day_realized_net_profit=D('100'),observed_daily_loss=D('0'),
                approved_effective_floor=D('750000'),is_first_trading_day=False,asof=now),
            asof=now,server_time=now,no_credit=True)
        env=SimpleNamespace(home=home,key=key,journal=Journal(),policy=policy,now=now,
                            observation=observation,prepared=None,session_id='fixture')
        env.order=Order(client_id='fixture-order-a',account_scope='fixture-account',venue='upbit',
                        market='spot',symbol='KRW-BTC',side='buy',quantity=D('0.0001'),
                        limit_price=D('100000000'),quote_krw=D('1'))
        env.rules=InstrumentRules(venue='upbit',market='spot',symbol='KRW-BTC',lot_size=D('0.00000001'),
            tick_size=D('1'),min_quantity=D('0.00000001'),min_notional_krw=D('5000'),
            fee_fraction=D('0.001'),asof=now,source_digest='a'*64)
        if prepare:
            plan,inputs,seed=selected(now)
            env.prepared=prepare_session(journal=env.journal,session_id='fixture',selected_plan=plan,
                inputs=inputs,positions=observation.positions,policy=policy,instrument_rules=env.rules,now=now,selection_seed_hex=seed,
                account_scope='fixture-account',market='spot',quote_currency='KRW')
            env.session_id=env.prepared.session_id
            if arm:
                F.sign(key,'session_armed',{'session_id':env.session_id},M.iso_utc(now))
        env.adapter=DryRunAdapter(upbit,results=results)
        env.controller=Controller(journal=env.journal,account_provider=lambda stamp:env.observation,
            policy=policy,adapters={'upbit':env.adapter},session_provider=lambda sid:env.prepared)
        yield env


def verification(env, prepared=None, order=None, now=None):
    now=now or env.now
    with env.journal.transaction() as tx:
        ctx=owner.load_context(now,env.observation.positions,session_id=env.session_id)
        verify_session(prepared or env.prepared,session_id=env.session_id,policy=env.policy,instrument_rules=env.rules,ctx=ctx,now=now,
                       order=order or env.order,events=tx.events)


def test_real_fresh_odds_preparation_and_signed_arm_bind_content():
    with signed_control() as env:
        assert env.prepared.seed_hex!=env.prepared.selection_seed_hex
        assert env.prepared.session_id.endswith(digest({k:v for k,v in vars(env.prepared).items()
                                                     if k not in ('session_id','record_digest')}))
        verification(env)
        with env.journal.transaction() as tx:
            assert [e['kind'] for e in tx.events]==['session_prepared']


def test_owner_arm_is_required_after_preparation():
    with signed_control(arm=False) as env:
        refused(lambda:verification(env))
        F.sign(env.key,'session_armed',{'session_id':env.session_id},M.iso_utc(env.now))
        verification(env)


def test_fabricated_mutated_expired_and_wrong_account_preparations_refuse():
    with signed_control() as env:
        refused(lambda:verification(env,replace(env.prepared)))
        refused(lambda:verification(env,order=replace(env.order,account_scope='other-account')))
        refused(lambda:verification(env,now=env.prepared.expires_at))
        object.__setattr__(env.prepared,'stake_krw','999999999')
        fields={k:v for k,v in vars(env.prepared).items() if k!='record_digest'}
        object.__setattr__(env.prepared,'record_digest',digest(fields))
        refused(lambda:verification(env))


def test_prepare_rejects_armed_reuse_and_mismatched_selected_seed():
    with signed_control() as env:
        plan,inputs,seed=selected(env.now)
        args=dict(journal=env.journal,session_id='fixture',selected_plan=plan,inputs=inputs,
            positions=env.observation.positions,policy=env.policy,instrument_rules=env.rules,now=env.now,selection_seed_hex=seed,
            account_scope='fixture-account',market='spot',quote_currency='KRW')
        refused(lambda:prepare_session(**args))
        refused(lambda:prepare_session(**(args|{'selection_seed_hex':'0'*64})))


def test_same_label_different_preparations_cannot_share_owner_arm():
    with signed_control(arm=False) as env:
        plan,inputs,seed=selected(env.now)
        second=prepare_session(journal=env.journal,session_id='fixture',selected_plan=plan,inputs=inputs,
            positions=env.observation.positions,policy=env.policy,instrument_rules=env.rules,now=env.now,selection_seed_hex=seed,
            account_scope='other-account',market='spot',quote_currency='KRW')
        assert second.session_id!=env.session_id
        F.sign(env.key,'session_armed',{'session_id':env.session_id},M.iso_utc(env.now))
        verification(env)
        ctx=owner.load_context(env.now,env.observation.positions,session_id=second.session_id)
        with env.journal.transaction() as tx:
            refused(lambda:verify_session(second,session_id=second.session_id,policy=env.policy,instrument_rules=env.rules,ctx=ctx,
                now=env.now,order=replace(env.order,account_scope='other-account'),events=tx.events))


def test_restart_reconstructed_preparation_does_not_issue_entry():
    with signed_control() as env:
        env.controller.session_provider=lambda sid:replace(env.prepared)
        refused(lambda:env.controller.reserve(env.order,env.rules,session_id=env.session_id,now=env.now))
        assert not env.adapter.requests
