"""Real fresh-odds preparation in test-signed temporary homes only."""
from contextlib import contextmanager
from dataclasses import replace
from datetime import datetime, time, timedelta, timezone
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


def universe_snapshot(now, *, eligible=(('KRW-BTC', D('900000000000')),), sha='5'*64, valid_until=None):
    """A Universe as PR 3's load_context returns it: built for the UTC day before `now`, in force from that day's
    00:40 UTC (09:40 KST) until the next day's 00:40 UTC, or until `valid_until`."""
    day = now.astimezone(timezone.utc).date() - timedelta(days=1)
    start = datetime.combine(day, time(0, 40), tzinfo=timezone.utc)
    return M.Universe(day=day, rule_sha256='7'*64, snapshot_sha256=sha, built_at=start - timedelta(minutes=10),
                      valid_from=start, valid_until=valid_until or start + timedelta(days=1),
                      listed=tuple(sorted(market for market, _ in eligible)), eligible=tuple(sorted(eligible)))


@contextmanager
def universe_context(**changes):
    """Patch owner.load_context to return the real sealed context re-sealed with `changes`; each value is either
    the new field value or a function of the real context (for example universe=lambda ctx: env.universe)."""
    from dataclasses import fields
    from unittest.mock import patch
    real = owner.load_context

    def load(now, positions, **kwargs):
        ctx = real(now, positions, **kwargs)
        body = {f.name: getattr(ctx, f.name) for f in fields(M.Context) if f.name != 'ctx_hash'}
        body.update({name: value(ctx) if callable(value) else value for name, value in changes.items()})
        return M.seal_context(**body)
    with patch.object(owner, 'load_context', load):
        yield


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
            quote_currency_by_account={('upbit','fixture-account'):'KRW'},
            inventory_exposure_krw={('upbit','fixture-account'):D('0')},
            quote_rates_krw={('upbit','fixture-account','KRW'):D('1')},
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
                account_scope='fixture-account',market='spot',quote_currency='KRW',
                clock=lambda: env.now, positions_asof=observation.asof)
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
            account_scope='fixture-account',market='spot',quote_currency='KRW',
            clock=lambda: env.now, positions_asof=env.observation.asof)
        refused(lambda:prepare_session(**args))
        refused(lambda:prepare_session(**(args|{'selection_seed_hex':'0'*64})))


def test_same_label_different_preparations_cannot_share_owner_arm():
    with signed_control(arm=False) as env:
        plan,inputs,seed=selected(env.now)
        second=prepare_session(journal=env.journal,session_id='fixture',selected_plan=plan,inputs=inputs,
            positions=env.observation.positions,policy=env.policy,instrument_rules=env.rules,now=env.now,selection_seed_hex=seed,
            account_scope='other-account',market='spot',quote_currency='KRW',
            clock=lambda: env.now, positions_asof=env.observation.asof)
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


def _preparation_args(env, **overrides):
    plan, inputs, seed = selected(env.now)
    args = dict(journal=env.journal, session_id='freshness', selected_plan=plan, inputs=inputs,
        positions=env.observation.positions, policy=env.policy, instrument_rules=env.rules, now=env.now,
        selection_seed_hex=seed, account_scope='fixture-account', market='spot', quote_currency='KRW',
        clock=lambda: env.now, positions_asof=env.observation.asof)
    return args | overrides


def _no_preparation(env, before):
    from execution_control import session as S
    assert S._PREPARED == before
    with env.journal.transaction() as tx:
        assert not any(row['kind'] == 'session_prepared' for row in tx.events)
    assert not env.adapter.requests


def _fixed_refusal(call, code):
    try:
        call()
    except ValueError as exc:
        assert str(exc) == code, (str(exc), code)
    else:
        raise AssertionError('expected ' + code)


def test_preparation_requires_explicit_clock_and_current_input_and_account_times():
    from execution_control import session as S
    from unittest.mock import patch
    for bad in ('clock', 'inputs', 'account', 'future'):
        with signed_control(prepare=False, arm=False) as env:
            args = _preparation_args(env)
            code = 'SESSION_PREPARATION_INPUTS_STALE_OR_FUTURE'
            if bad == 'clock':
                args['clock'] = None
                code = 'SESSION_PREPARATION_CLOCK_REQUIRED'
            elif bad == 'inputs': env.now += timedelta(seconds=31)
            elif bad == 'account':
                args['positions_asof'] -= timedelta(seconds=31)
                code = 'SESSION_PREPARATION_ACCOUNT_STALE_OR_FUTURE'
            else: args['clock'] = lambda: env.now-timedelta(seconds=1)
            before = dict(S._PREPARED)
            with patch.object(S.simulate, 'simulate', side_effect=AssertionError('stale inputs reached simulation')):
                _fixed_refusal(lambda: prepare_session(**args), code)
            _no_preparation(env, before)


def test_preparation_rechecks_simulation_duration_expiry_rules_and_clock_rollback():
    from execution_control import session as S
    from unittest.mock import patch
    cases = (('slow', 31, 'SESSION_PREPARATION_INPUTS_STALE_OR_FUTURE'),
             ('expiry', 2, 'SESSION_PREPARATION_EXPIRED'),
             ('rules', 2, 'SESSION_PREPARATION_RULES_STALE_OR_FUTURE'),
             ('rollback', -1, 'SESSION_PREPARATION_CLOCK_ROLLBACK'))
    for kind, elapsed, code in cases:
        with signed_control(prepare=False, arm=False) as env:
            args = _preparation_args(env)
            if kind == 'expiry': args['expires_at'] = env.now+timedelta(seconds=1)
            if kind == 'rules': args['instrument_rules'] = replace(env.rules, asof=env.now-timedelta(seconds=299))
            before, real = dict(S._PREPARED), S.simulate.simulate
            def simulate(*a, **kw):
                report = real(*a, **kw)
                env.now += timedelta(seconds=elapsed)
                return report
            with patch.object(S.simulate, 'simulate', side_effect=simulate):
                _fixed_refusal(lambda: prepare_session(**args), code)
            _no_preparation(env, before)


def test_preparation_cannot_cross_seoul_midnight_during_simulation():
    from execution_control import session as S
    from unittest.mock import patch
    with patch.object(F, 'NOW', F.NOW.replace(hour=23, minute=59, second=59)), \
            signed_control(prepare=False, arm=False) as env:
        args, before, real = _preparation_args(env), dict(S._PREPARED), S.simulate.simulate
        def simulate(*a, **kw):
            report = real(*a, **kw)
            env.now += timedelta(seconds=2)
            return report
        with patch.object(S.simulate, 'simulate', side_effect=simulate):
            _fixed_refusal(lambda: prepare_session(**args), 'SESSION_PREPARATION_DAY_CHANGED')
        _no_preparation(env, before)


def test_preparation_checks_time_after_acquiring_the_journal_lock():
    from execution_control import session as S
    from unittest.mock import patch
    with signed_control(prepare=False, arm=False) as env:
        args, before, transaction = _preparation_args(env), dict(S._PREPARED), env.journal.transaction
        @contextmanager
        def delayed_lock():
            with transaction() as tx:
                env.now += timedelta(seconds=31)
                yield tx
        with patch.object(env.journal, 'transaction', delayed_lock):
            _fixed_refusal(lambda: prepare_session(**args), 'SESSION_PREPARATION_INPUTS_STALE_OR_FUTURE')
        _no_preparation(env, before)


def test_preparation_reloads_owner_authority_after_simulation_before_issuing():
    from execution_control import session as S
    from unittest.mock import patch
    for change in ('arm', 'limits', 'code'):
        with signed_control(prepare=False, arm=False) as env:
            args, before, real = _preparation_args(env), dict(S._PREPARED), S.simulate.simulate
            def simulate(*a, **kw):
                report = real(*a, **kw)
                env.now += timedelta(seconds=1)
                if change == 'arm':
                    F.sign(env.key, 'session_armed', {'session_id': 'other-session'}, M.iso_utc(env.now))
                elif change == 'limits':
                    F.sign(env.key, 'limit_set', {'total_loss_floor_krw': 3000.0, 'daily_loss_krw': 4000.0},
                           M.iso_utc(env.now))
                else:
                    files = [['core/unapproved-test-fixture.py', '0'*64]]
                    F.sign(env.key, 'code_approved', {'sha256': M.sha256_hex(M.canonical_json(files)), 'files': files},
                           M.iso_utc(env.now))
                return report
            with patch.object(S.simulate, 'simulate', side_effect=simulate):
                _fixed_refusal(lambda: prepare_session(**args), 'SESSION_PREPARATION_OWNER_CHANGED')
            _no_preparation(env, before)


def test_slow_final_authority_load_cannot_restamp_account_freshness():
    from execution_control import session as S
    from unittest.mock import patch
    with signed_control(prepare=False, arm=False) as env:
        args, before, real = _preparation_args(env), dict(S._PREPARED), owner.load_context
        calls = []
        def context(stamp, positions, **kw):
            result = real(stamp, positions, **kw)
            calls.append(stamp)
            if len(calls) == 2: env.now += timedelta(seconds=31)
            return result
        with patch.object(owner, 'load_context', side_effect=context):
            _fixed_refusal(lambda: prepare_session(**args), 'SESSION_PREPARATION_INPUTS_STALE_OR_FUTURE')
        assert len(calls) == 2
        _no_preparation(env, before)


def test_success_records_actual_completion_time_without_extending_expiry():
    from execution_control import session as S
    from unittest.mock import patch
    with signed_control(prepare=False, arm=False) as env:
        args, start, real = _preparation_args(env), env.now, S.simulate.simulate
        def simulate(*a, **kw):
            report = real(*a, **kw)
            env.now += timedelta(seconds=2)
            return report
        with patch.object(S.simulate, 'simulate', side_effect=simulate):
            prepared = prepare_session(**args)
        assert prepared.prepared_at == start+timedelta(seconds=2)
        assert prepared.expires_at == start+timedelta(minutes=30)
        assert S._PREPARED[id(prepared)][0] is prepared and prepared.seed_hex != prepared.selection_seed_hex
        with env.journal.transaction() as tx:
            rows = [r for r in tx.events if r['kind'] == 'session_prepared']
            from datetime import datetime
            assert len(rows) == 1 and datetime.fromisoformat(rows[0]['utc']) == prepared.prepared_at
        assert not env.adapter.requests


def test_preparation_rechecks_time_after_final_content_and_journal_snapshot_work():
    from execution_control import session as S
    from execution_control.store import Transaction
    from core.odds.plan import Inputs
    from unittest.mock import patch
    for phase in ('content', 'events', 'record'):
        with signed_control(prepare=False, arm=False) as env:
            args, before = _preparation_args(env), dict(S._PREPARED)
            real_digest, real_events, reads = S.digest, Transaction.events.fget, []
            def digest(value):
                result = real_digest(value)
                if phase == 'content' and type(value) is Inputs:
                    reads.append(True)
                    if len(reads) == 2: env.now += timedelta(seconds=31)
                elif phase == 'record' and type(value) is dict and 'session_id' in value:
                    env.now += timedelta(seconds=31)
                return result
            def events(tx):
                result = real_events(tx)
                env.now += timedelta(seconds=31)
                return result
            seam = (patch.object(S, 'digest', side_effect=digest) if phase in ('content', 'record')
                    else patch.object(Transaction, 'events', property(events)))
            with seam:
                _fixed_refusal(lambda: prepare_session(**args), 'SESSION_PREPARATION_INPUTS_STALE_OR_FUTURE')
            _no_preparation(env, before)
