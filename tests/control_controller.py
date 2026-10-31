"""Durable control, accounting and restart behavior using synthetic signed homes."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal, localcontext

from core.compliance import model as M, owner
from execution_control.controller import Controller, _fold
from execution_control.risk import Fill
from execution_orders.model import AdapterResult
from tests import compliance_fixtures as F
from tests.control_session import signed_control, refused

D=Decimal


def result(env,status='accepted',quantity=None,identity='broker-fixture'):
    return AdapterResult(status=status,code='fixture',venue_order_id=identity,
                         client_id=env.order.client_id,filled_quantity=quantity)


def reserve(env,order=None,rules=None):
    return env.controller.reserve(order or env.order,rules or env.rules,session_id=env.session_id,now=env.now)


def send(env):
    return env.controller.dispatch(env.order.client_id,now=env.now)


def snapshot(env,**changes):
    env.observation=replace(env.observation,**changes)


def risk_change(env,**changes):
    snapshot(env,risk=replace(env.observation.risk,**changes))


def fill(env,**changes):
    values=dict(venue='upbit',account_scope='fixture-account',order_id='broker-fixture',fill_id='fill-fixture',
                market='spot',symbol='KRW-BTC',side='buy',quantity=env.order.quantity,
                price=env.order.limit_price,quote_currency='KRW',quote_krw=D('1'),fee_amount=D('10'),
                fee_currency='KRW',executed_at=env.now,base_currency='BTC')
    return Fill(**(values|changes))


def restart(env):
    return Controller(journal=env.journal,account_provider=lambda now:env.observation,policy=env.policy,
                      adapters={'upbit':env.adapter},session_provider=lambda sid:env.prepared)


def test_reservation_identity_and_pre_send_durability_with_no_post_retry():
    with signed_control() as env:
        first=reserve(env)
        assert first.status=='RESERVED' and reserve(env)==first and not env.adapter.requests
        refused(lambda:reserve(env,replace(env.order,limit_price=D('100000001'))))
        original=env.adapter.dispatch
        def dispatch(request,capability,*,now):
            # The actual durable file already contains the pre-send transition.
            assert b'"kind":"dispatching"' in (env.home/'execution-control'/'journal.jsonl').read_bytes()
            return original(request,capability,now=now)
        env.adapter.dispatch=dispatch
        state=send(env)
        assert state.status=='ACKNOWLEDGED' and send(env)==state and len(env.adapter.requests)==1
        assert restart(env).dispatch(env.order.client_id,now=env.now)==state
        assert len(env.adapter.requests)==1


def test_reserved_restart_rechecks_signed_session_and_exact_permit():
    with signed_control() as env:
        reserve(env)
        env.controller=restart(env)
        env.controller.session_provider=lambda sid:replace(env.prepared)
        refused(lambda:send(env))
        assert not env.adapter.requests


def test_unknown_keeps_reservation_and_never_retries_create():
    with signed_control(results=(TimeoutError('fixture'),)) as env:
        reserve(env)
        state=send(env)
        assert state.status=='UNKNOWN'
        env.controller=restart(env)
        assert send(env).status=='UNKNOWN' and len(env.adapter.requests)==1
        refused(lambda:reserve(env,replace(env.order,client_id='second')))
        with env.journal.transaction() as tx:
            orders,_,_,_=_fold(tx.events)
            assert orders[env.order.client_id]['status']=='UNKNOWN'


def test_send_in_progress_after_process_crash_is_unknown_without_a_retry():
    with signed_control() as env:
        reserve(env)
        with env.journal.transaction() as tx:
            rec=_fold(tx.events)[0][env.order.client_id]
            tx.append('dispatching',{'client_id':env.order.client_id,'order_digest':rec['digest'],
                'request_digest':rec['request_digest'],'permit_digest':rec['permit_digest']},now=env.now)
        assert restart(env).dispatch(env.order.client_id,now=env.now).status=='UNKNOWN'
        assert not env.adapter.requests


def test_exact_cash_reservations_include_fees_and_exclude_only_own_at_send():
    with signed_control() as env:
        snapshot(env,settled_cash_krw={('upbit','fixture-account'):D('20020')})
        reserve(env)
        reserve(env,replace(env.order,client_id='second'))
        refused(lambda:reserve(env,replace(env.order,client_id='third')))
        assert send(env).status=='ACKNOWLEDGED'


def test_session_capital_is_aggregate_and_rules_cannot_change_after_owner_arm():
    with signed_control() as env:
        order=replace(env.order,quantity=D('0.0003'))
        reserve(env,order)
        refused(lambda:reserve(env,replace(env.order,client_id='second',quantity=D('0.0002'))))
        refused(lambda:reserve(env,replace(env.order,client_id='new-rules'),
                                replace(env.rules,fee_fraction=D('0'),source_digest='b'*64)))
        assert not env.adapter.requests


def test_stale_account_wrong_scope_unknown_credit_and_clock_rollback_refuse():
    with signed_control() as env:
        original=env.observation
        for bad in (replace(original,asof=env.now-timedelta(seconds=31)),
                    replace(original,server_time=env.now+timedelta(seconds=61)),
                    replace(original,account_scopes={'upbit':'other'}),replace(original,no_credit=False)):
            env.observation=bad
            refused(lambda:reserve(env))
        env.observation=original
        reserve(env)
        refused(lambda:env.controller.dispatch(env.order.client_id,now=env.now-timedelta(seconds=1)))
        assert not env.adapter.requests


def test_terminal_status_does_not_release_unreconciled_fee_or_quantity():
    with signed_control() as env:
        env.adapter.results.append(result(env))
        reserve(env);send(env)
        env.adapter.results.append(result(env,'filled',env.order.quantity))
        snapshot(env,fills=(fill(env,fee_amount=None),),reconciled_client_ids={env.order.client_id})
        state=env.controller.reconcile(env.order.client_id,now=env.now)
        assert state.status=='ACKNOWLEDGED' and state.filled_quantity==0
        env.adapter.results.append(result(env,'filled',env.order.quantity))
        snapshot(env,fills=(fill(env),))
        state=env.controller.reconcile(env.order.client_id,now=env.now)
        assert state.status=='FILLED' and state.filled_quantity==env.order.quantity
        sent=len(env.adapter.requests)
        assert env.controller.reconcile(env.order.client_id,now=env.now)==state
        assert len(env.adapter.requests)==sent


def test_reconciliation_rejects_wrong_side_or_scope_and_cumulative_replacement():
    with signed_control() as env:
        env.adapter.results.append(result(env));reserve(env);send(env)
        for bad in (fill(env,account_scope='other'),fill(env,side='sell')):
            snapshot(env,fills=(bad,),reconciled_client_ids={env.order.client_id})
            env.adapter.results.append(result(env,'partial',D('0.00005')))
            assert env.controller.reconcile(env.order.client_id,now=env.now).filled_quantity==0
        first=fill(env,quantity=D('0.00005'),fee_amount=D('5'))
        snapshot(env,fills=(first,))
        env.adapter.results.append(result(env,'partial',D('0.00005')))
        assert env.controller.reconcile(env.order.client_id,now=env.now).status=='PARTIAL'
        snapshot(env,fills=(replace(first,fill_id='replacement'),))
        env.adapter.results.append(result(env,'partial',D('0.00005')))
        refused(lambda:env.controller.reconcile(env.order.client_id,now=env.now))


def test_cancel_ack_retains_pending_marker_and_capacity_until_status_proof():
    with signed_control() as env:
        env.adapter.results.append(result(env));reserve(env);send(env)
        env.adapter.results.append(result(env))
        env.controller.cancel(env.order.client_id,now=env.now)
        count=len(env.adapter.requests)
        env.controller.cancel(env.order.client_id,now=env.now)
        assert len(env.adapter.requests)==count
        refused(lambda:reserve(env,replace(env.order,client_id='second')))
        snapshot(env,reconciled_client_ids={env.order.client_id})
        env.adapter.results.append(result(env,'canceled',D('0')))
        assert env.controller.reconcile(env.order.client_id,now=env.now).status=='CANCELED'
        assert reserve(env,replace(env.order,client_id='second')).status=='RESERVED'


def test_broker_id_collision_becomes_unknown_without_poisoning_journal():
    with signed_control() as env:
        env.adapter.results.append(result(env));reserve(env);send(env)
        second=replace(env.order,client_id='second')
        reserve(env,second)
        env.adapter.results.append(AdapterResult(status='accepted',code='fixture',client_id='second',
                                                venue_order_id='broker-fixture'))
        state=env.controller.dispatch('second',now=env.now)
        assert state.status=='UNKNOWN' and not state.venue_order_id
        with env.journal.transaction() as tx:
            assert _fold(tx.events)[0]['second']['status']=='UNKNOWN'


def test_signed_daily_ceiling_latches_until_next_seoul_day():
    with signed_control(prepare=False) as env:
        risk_change(env,prior_day_realized_net_profit=D('100000'),observed_daily_loss=D('5000'))
        assert env.controller.observe(now=env.now).new_entry_blocked
        risk_change(env,observed_daily_loss=D('0'))
        assert 'PERSISTENT_DAILY_STOP' in restart(env).observe(now=env.now).reasons
        later=env.now+timedelta(days=1)
        snapshot(env,asof=later,server_time=later,risk=replace(env.observation.risk,asof=later))
        assert not restart(env).observe(now=later).new_entry_blocked


def test_floor_equality_allows_monitoring_but_breach_persists_across_recovery():
    with signed_control(prepare=False) as env:
        snapshot(env,positions=replace(env.observation.positions,equity_krw=6000.0))
        risk_change(env,equity=D('6000'),prior_high_watermark=D('6000'),day_start_equity=D('6000'),
                    approved_effective_floor=D('6000'))
        assert not env.controller.observe(now=env.now).new_entry_blocked
        snapshot(env,positions=replace(env.observation.positions,equity_krw=5999.0))
        risk_change(env,equity=D('5999'))
        assert 'PERSISTENT_HALT' in env.controller.observe(now=env.now).reasons
        snapshot(env,positions=replace(env.observation.positions,equity_krw=6000.0))
        risk_change(env,equity=D('6000'))
        assert 'PERSISTENT_HALT' in restart(env).observe(now=env.now).reasons
        assert owner.load_context(env.now,env.observation.positions).owner.halted_floors


def test_deferred_floor_relaxation_requires_next_day_signed_unarmed_approval():
    with signed_control(prepare=False) as env:
        F.sign(env.key,'limit_set',{'total_loss_floor_krw':7999.0,'daily_loss_krw':5000.0},M.iso_utc(env.now))
        snapshot(env,positions=replace(env.observation.positions,equity_krw=7999.0))
        risk_change(env,equity=D('7999'),prior_high_watermark=D('7999'),day_start_equity=D('7999'),
                    approved_effective_floor=D('7999'))
        env.controller.observe(now=env.now)
        snapshot(env,positions=replace(env.observation.positions,equity_krw=8000.0))
        risk_change(env,equity=D('8000'))
        assert env.controller.observe(now=env.now).relaxation_pending
        F.sign(env.key,'limit_set',{'total_loss_floor_krw':6000.0,'daily_loss_krw':5000.0},M.iso_utc(env.now))
        refused(lambda:env.controller.approve_floor_relaxation(floor=D('6000'),now=env.now,session_id='fixture'))
        later=env.now+timedelta(days=1)
        snapshot(env,asof=later,server_time=later,risk=replace(env.observation.risk,asof=later,day_start_equity=D('8000')))
        lowered=env.controller.approve_floor_relaxation(floor=D('6000'),now=later,session_id='fixture')
        assert lowered.effective_floor==D('6000')
        risk_change(env,approved_effective_floor=D('6000'))
        assert restart(env).observe(now=later).effective_floor==D('6000')


def test_kill_clock_failure_latches_locally_and_does_not_write_owner_log():
    with signed_control() as env:
        reserve(env)
        before=owner.log_path().read_bytes()
        snapshot(env,server_time=env.now+timedelta(seconds=61))
        assert env.controller.kill(env.session_id,reason='fixture',now=env.now) is False
        assert owner.log_path().read_bytes()==before
        snapshot(env,server_time=env.now)
        refused(lambda:send(env))
        # Reserved unsubmitted orders can still be locally canceled under a kill.
        assert env.controller.cancel(env.order.client_id,now=env.now).status=='CANCELLED_LOCAL'
        assert not env.adapter.requests


def test_kill_and_daily_stop_leave_verified_reducing_sell_available():
    with signed_control() as env:
        assert env.controller.kill(env.session_id,reason='fixture',now=env.now)
        snapshot(env,positions=replace(env.observation.positions,holdings={('upbit','BTC'):0.001}),
                 holdings={('upbit','fixture-account','spot','KRW-BTC'):D('0.001')})
        risk_change(env,observed_daily_loss=D('5000'))
        sell=replace(env.order,side='sell',client_id='reducing-exit')
        assert reserve(env,sell).status=='RESERVED'
        assert env.controller.dispatch(sell.client_id,now=env.now).status=='ACKNOWLEDGED'


def test_lifecycle_semantic_corruption_refuses_before_adapter_effects():
    with signed_control() as env:
        reserve(env)
        with env.journal.transaction() as tx:
            rec=_fold(tx.events)[0][env.order.client_id]
            tx.append('reconciled',{'client_id':env.order.client_id,'order_digest':rec['digest'],
                'status':'FILLED','filled_quantity':str(env.order.quantity),'venue_order_id':'invented',
                'metadata':[]},now=env.now)
        refused(lambda:send(env))
        assert not env.adapter.requests


def test_accounting_controls_ignore_ambient_decimal_precision():
    with signed_control() as env:
        env.adapter.results.append(result(env));reserve(env);send(env)
        snapshot(env,fills=(fill(env),),reconciled_client_ids={env.order.client_id})
        env.adapter.results.append(result(env,'filled',env.order.quantity))
        with localcontext() as context:
            context.prec=2
            assert env.controller.reconcile(env.order.client_id,now=env.now).status=='FILLED'


def test_exact_venue_cap_rejects_amount_that_float_conversion_rounds_down():
    with signed_control(prepare=False) as env:
        order=replace(env.order,venue='okx',symbol='BTC-USDT',quantity=D('1'),
                      limit_price=D('10.00000000000000000000000000001'))
        positions=M.Positions(equity_krw=100.0,exposure={'okx':M.Exposure(held_krw=0.0)})
        observation=replace(env.observation,positions=positions,account_scopes={'okx':'fixture-account'},
            held_exposure_krw={('okx','fixture-account'):D('0')},
            inventory_exposure_krw={('okx','fixture-account'):D('0')},
            risk=replace(env.observation.risk,equity=D('100')))
        ctx=F.ctx(equity_krw=100.0,exposure=positions.exposure)
        intent=env.controller._intent(order,ctx)
        assert intent.notional_krw==10.0
        with localcontext() as context:
            context.prec=100
            refused(lambda:env.controller._exact_caps(order,observation,{},ctx,intent))
            exact=replace(order,limit_price=D('10'))
            env.controller._exact_caps(exact,observation,{},ctx,env.controller._intent(exact,ctx))


def test_h2_seoul_day_disagreement_keeps_local_latch_without_owner_write():
    with signed_control(prepare=False) as env:
        boundary=env.now.replace(hour=0,minute=0,second=1)
        snapshot(env,asof=boundary,server_time=boundary-timedelta(seconds=2),
                 risk=replace(env.observation.risk,asof=boundary))
        before=owner.log_path().read_bytes()
        assert env.controller.kill('boundary-session',reason='fixture',now=boundary) is False
        assert env.controller.halt(floor=D('2000'),now=boundary) is False
        assert owner.log_path().read_bytes()==before
        with env.journal.transaction() as tx:
            _,killed,halted,_=_fold(tx.events)
            assert 'boundary-session' in killed and halted
    with signed_control(prepare=False) as env:
        boundary=env.now.replace(hour=0,minute=0,second=5)
        previous=boundary-timedelta(seconds=10)
        snapshot(env,asof=previous,server_time=boundary,risk=replace(env.observation.risk,asof=previous))
        refused(lambda:env.controller._account(boundary,()))


def test_contradictory_terminal_status_adds_no_fill_or_terminal_journal_rows():
    with signed_control() as env:
        env.adapter.results.append(result(env));reserve(env);send(env)
        snapshot(env,fills=(fill(env,quantity=D('0.00005'),fee_amount=D('5')),),
                 reconciled_client_ids={env.order.client_id})
        for status in ('rejected','filled'):
            with env.journal.transaction() as tx:
                before=tx.events
            env.adapter.results.append(result(env,status,D('0.00005')))
            assert env.controller.reconcile(env.order.client_id,now=env.now).status=='ACKNOWLEDGED'
            with env.journal.transaction() as tx:
                assert tx.events==before
                _fold(tx.events)


def test_external_sell_promises_and_inconsistent_legacy_holdings_fail_closed():
    with signed_control(prepare=False) as env:
        sell=replace(env.order,side='sell',quantity=D('0.000500000001'))
        rules=replace(env.rules,lot_size=D('0.000000000001'))
        positions=replace(env.observation.positions,holdings={('upbit','BTC'):0.001},
            exposure={'upbit':M.Exposure(held_krw=0.0,promised_sell_units={'BTC':0.0005})})
        snapshot(env,positions=positions,holdings={('upbit','fixture-account','spot','KRW-BTC'):D('0.001')})
        refused(lambda:reserve(env,sell,rules))
        snapshot(env,positions=replace(positions,holdings={('upbit','BTC'):0.002},
                                      exposure={'upbit':M.Exposure(held_krw=0.0)}))
        refused(lambda:reserve(env,sell,rules))
        assert not env.adapter.requests


def test_okx_sell_promises_share_base_inventory_across_quote_pairs_exactly():
    from execution_control.dry_run import DryRunAdapter
    from execution_orders import okx
    with signed_control(prepare=False) as env:
        env.controller.adapters['okx']=DryRunAdapter(okx)
        snapshot(env,positions=M.Positions(equity_krw=1000000.0,holdings={('okx','BTC'):1.0},
                exposure={'okx':M.Exposure(held_krw=1000.0)}),account_scopes={'okx':'fixture-account'},
            held_exposure_krw={('okx','fixture-account'):D('1000')},
            inventory_exposure_krw={('okx','fixture-account'):D('1000')},
            quote_currency_by_account={('okx','fixture-account'):'USDT'},settled_cash_krw={},
            quote_rates_krw={('okx','fixture-account','USDT'):D('1'),('okx','fixture-account','USDC'):D('1')},
            holdings={('okx','fixture-account','spot','BTC-USDT'):D('1'),
                      ('okx','fixture-account','spot','BTC-USDC'):D('1')})
        first=replace(env.order,client_id='okxfirst',venue='okx',symbol='BTC-USDT',side='sell',quantity=D('0.5'),limit_price=D('100'))
        rules=replace(env.rules,venue='okx',symbol='BTC-USDT',lot_size=D('0.0000000000001'),min_notional_krw=D('1'))
        assert reserve(env,first,rules).status=='RESERVED'
        second=replace(first,client_id='second',symbol='BTC-USDC',quantity=D('0.5000000000001'))
        refused(lambda:reserve(env,second,replace(rules,symbol='BTC-USDC')))
        assert reserve(env,replace(second,quantity=D('0.5')),replace(rules,symbol='BTC-USDC')).status=='RESERVED'


def test_kis_broker_identity_includes_market_date_and_organization():
    from execution_control.capability import plain
    from execution_control.model import order_body, order_digest
    with signed_control(prepare=False) as env:
        def attach(client,market,symbol,org):
            order=replace(env.order,client_id=client,venue='kis',market=market,symbol=symbol,
                          quantity=D('1'),limit_price=D('10000'),time_in_force='day')
            rules=replace(env.rules,venue='kis',market=market,symbol=symbol,lot_size=D('1'),min_quantity=D('1'))
            with env.journal.transaction() as tx:
                tx.append('reserved',{'client_id':client,'order_digest':order_digest(order),'order':order_body(order),
                    'rules':plain(rules),'session_id':'fixture','request_digest':'b'*64,'permit_digest':'c'*64,
                    'trade_date':'20261024'},now=env.now)
                tx.append('dispatching',{'client_id':client,'order_digest':order_digest(order),
                    'request_digest':'b'*64,'permit_digest':'c'*64},now=env.now)
                rec=_fold(tx.events)[0][client]
                response=AdapterResult(status='accepted',code='fixture',venue_order_id='123',client_id=client,
                    metadata=(('broker_org_id',org),) if org else ())
                env.controller._result(tx,rec,'acknowledged',response,env.now)
                return _fold(tx.events)[0][client]['status']
        assert attach('krx-one','krx','005930','001')=='ACKNOWLEDGED'
        assert attach('krx-two','krx','005930','002')=='ACKNOWLEDGED'
        assert attach('us-one','nasd','AAPL','')=='ACKNOWLEDGED'
        assert attach('duplicate','krx','005930','001')=='UNKNOWN'


def test_conflicting_broker_average_preserves_reservation_without_journal_rows():
    with signed_control() as env:
        env.adapter.results.append(result(env));reserve(env);send(env)
        snapshot(env,fills=(fill(env),),reconciled_client_ids={env.order.client_id})
        with env.journal.transaction() as tx:
            before=tx.events
        env.adapter.results.append(replace(result(env,'filled',env.order.quantity),average_price=D('99999999')))
        assert env.controller.reconcile(env.order.client_id,now=env.now).status=='ACKNOWLEDGED'
        with env.journal.transaction() as tx:
            assert tx.events==before
        env.adapter.results.append(replace(result(env,'filled',env.order.quantity),average_price=env.order.limit_price))
        assert env.controller.reconcile(env.order.client_id,now=env.now).status=='FILLED'


def test_buy_requires_explicit_quote_cash_binding_before_reserve_and_dispatch():
    with signed_control() as env:
        original=env.observation
        for mapping in ({}, {('upbit','fixture-account'):'USD'}, {('upbit','other-account'):'KRW'}):
            snapshot(env,quote_currency_by_account=mapping)
            refused(lambda:reserve(env))
            assert not env.adapter.requests
        env.observation=original
        assert reserve(env).status=='RESERVED'
        snapshot(env,quote_currency_by_account={('upbit','fixture-account'):'USD'})
        refused(lambda:send(env))
        assert not env.adapter.requests
        env.observation=original
        assert send(env).status=='ACKNOWLEDGED'


def test_equal_krw_values_do_not_substitute_usdt_usdc_or_krw_usd_cash():
    with signed_control(prepare=False) as env:
        for venue,market,symbol,quote,wrong in (
                ('okx','spot','BTC-USDC','USDC','USDT'),
                ('kis','nasd','AAPL','USD','KRW'),
                ('kis','krx','005930','KRW','USD')):
            order=replace(env.order,venue=venue,market=market,symbol=symbol,quantity=D('1'),
                          limit_price=D('10'),quote_krw=D('1') if quote=='KRW' else D('1400'),
                          time_in_force='day' if venue=='kis' else 'gtc')
            rules=replace(env.rules,venue=venue,market=market,symbol=symbol)
            account=(venue,'fixture-account')
            observation=replace(env.observation,settled_cash_krw={account:D('1000000')},
                quote_currency_by_account={account:wrong},
                quote_rates_krw={(*account,quote):order.quote_krw})
            refused(lambda:env.controller._capacity(order,rules,observation,{}))
            env.controller._capacity(order,rules,replace(observation,quote_currency_by_account={account:quote}),{})


def test_verified_reducing_sell_does_not_require_spendable_quote_cash():
    with signed_control(prepare=False) as env:
        snapshot(env,positions=replace(env.observation.positions,holdings={('upbit','BTC'):0.001}),
                 holdings={('upbit','fixture-account','spot','KRW-BTC'):D('0.001')},
                 quote_currency_by_account={},settled_cash_krw={})
        sell=replace(env.order,side='sell')
        assert reserve(env,sell).status=='RESERVED'


def test_session_inventory_is_required_bounded_and_distinct_from_total_cash_exposure():
    with signed_control() as env:
        original=env.observation
        for inventory in ({}, {('upbit','fixture-account'):D('1')}):
            snapshot(env,inventory_exposure_krw=inventory)
            refused(lambda:reserve(env))
        snapshot(env,inventory_exposure_krw={('upbit','fixture-account'):D('0')},
                 held_exposure_krw={('upbit','fixture-account'):D('1000000')},
                 positions=replace(original.positions,exposure={'upbit':M.Exposure(held_krw=1000000.0)}))
        assert reserve(env).status=='RESERVED'
        assert send(env).status=='ACKNOWLEDGED'


def test_broker_cash_reservations_block_entries_before_any_dispatch():
    with signed_control() as env:
        snapshot(env,positions=replace(env.observation.positions,
                 exposure={'upbit':M.Exposure(held_krw=0.0,reservations={'outside-order':1.0})}))
        refused(lambda:reserve(env))
        assert not env.adapter.requests


def test_venue_cap_counts_settlement_assets_even_when_session_inventory_is_zero():
    with signed_control(prepare=False) as env:
        order=replace(env.order,venue='okx',symbol='BTC-USDT',quantity=D('1'),limit_price=D('1'))
        positions=M.Positions(equity_krw=100.0,exposure={'okx':M.Exposure(held_krw=10.0)})
        observation=replace(env.observation,positions=positions,account_scopes={'okx':'fixture-account'},
            held_exposure_krw={('okx','fixture-account'):D('10')},
            inventory_exposure_krw={('okx','fixture-account'):D('0')},
            risk=replace(env.observation.risk,equity=D('100')))
        ctx=F.ctx(equity_krw=100.0,exposure=positions.exposure)
        refused(lambda:env.controller._exact_caps(order,observation,{},ctx,env.controller._intent(order,ctx)))


def test_missing_authoritative_fx_blocks_reservation_and_dispatch_for_both_sides():
    with signed_control() as env:
        original=env.observation
        snapshot(env,quote_rates_krw={})
        refused(lambda:reserve(env))
        env.observation=original
        reserve(env)
        snapshot(env,quote_rates_krw={})
        refused(lambda:send(env))
        assert not env.adapter.requests
    with signed_control(prepare=False) as env:
        snapshot(env,positions=replace(env.observation.positions,holdings={('upbit','BTC'):0.001}),
                 holdings={('upbit','fixture-account','spot','KRW-BTC'):D('0.001')})
        sell=replace(env.order,side='sell')
        original=env.observation
        snapshot(env,quote_rates_krw={})
        refused(lambda:reserve(env,sell))
        env.observation=original
        reserve(env,sell)
        snapshot(env,quote_rates_krw={})
        refused(lambda:send(env))
        assert not env.adapter.requests


def test_pending_foreign_cash_is_revalued_and_unrelated_scopes_cannot_fund_entries():
    with signed_control(prepare=False) as env:
        order=replace(env.order,venue='okx',symbol='BTC-USDT',quantity=D('1'),
                      limit_price=D('100'),quote_krw=D('1500'))
        old=replace(order,client_id='old-quote',quote_krw=D('1000'))
        rules=replace(env.rules,venue='okx',symbol=order.symbol)
        account=('okx','fixture-account')
        observation=replace(env.observation,account_scopes={'okx':'fixture-account'},
            positions=M.Positions(equity_krw=1000000.0,exposure={'okx':M.Exposure(held_krw=0.0)}),
            quote_currency_by_account={account:'USDT'},quote_rates_krw={(*account,'USDT'):D('1500')},
            settled_cash_krw={account:D('250000')})
        pending={old.client_id:{'order':old,'rules':rules,'status':'RESERVED','filled':D('0')}}
        assert env.controller._pending_buy_krw(order,observation,pending)==D('150150')
        assert env.controller._positions(observation,pending).exposure['okx'].reservations[old.client_id]==150150.0
        refused(lambda:env.controller._capacity(order,rules,observation,pending))
        observation=replace(observation,settled_cash_krw={account:D('300300')})
        env.controller._capacity(order,rules,observation,pending)
        for changed in (replace(old,account_scope='another-account'),replace(old,symbol='BTC-USDC')):
            pending[old.client_id]['order']=changed
            refused(lambda:env.controller._capacity(order,rules,observation,pending))
