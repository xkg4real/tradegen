"""Actual Controller/guard/owner integration; disposable signatures and synthetic source.

The owner context is loaded from an actually signed temporary log. Continuous
prices, account pages and coverage remain invented fixture evidence. Only
DryRunAdapter consumes capabilities; no real account, credential, API or order.
"""
from contextlib import contextmanager, ExitStack
from dataclasses import replace
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from core.compliance import model as M, owner
from execution_accounts.baseline_store import CheckpointStore
from execution_accounts.model import content_digest
from execution_control.capability import digest as control_digest
from execution_control.controller import AccountObservation, Controller, _fold
from execution_control.dry_run import DryRunAdapter
from execution_control.model import InstrumentRules, Order
from execution_control.store import GENESIS, Journal
from execution_launch.baseline_head import BaselineHead, CheckpointChain
from execution_launch.continuous_guard import OwnerContextClaim
from execution_launch.continuous_guard_commit import GuardChain, GuardCheckpointStore
from execution_launch import committed_account as P
from execution_orders import upbit
from tests import compliance_fixtures as CF, control_continuous_guard as GF
from tests import control_continuous_guard_commit as GC, launch_committed_account as PF
from tests.launch_baseline_head import head_root
from tests.launch_carry_coordinator import memoized_pure_inputs

D=Decimal


@contextmanager
def fixture(*, prices=('101',), start=GF.START, end=None, floor='100', daily='10',
            configure=None, pol=None, daily_stopped=False, halted=False, spare_cash=False, clock=None,
            control_prefix=False):
    with memoized_pure_inputs(), CF.temp_home() as home, head_root() as hroot, CF.pubkey_at(home/'fixture-owner.pem'):
        key=CF.full_home(home,limits={'total_loss_floor_krw':float(floor),'daily_loss_krw':float(daily)})
        if configure is not None:
            configure(home,key,start)
        contexts=[]
        def current_claim(at,**_):
            ctx=owner.load_context(at,M.Positions(equity_krw=100.0,holdings={('upbit','BTC'):1.0}))
            assert M.is_sealed(ctx) and ctx.owner.ok and ctx.code_signed
            contexts.append(ctx)
            return OwnerContextClaim(owner_head_sha256=ctx.owner.head[1],code_sha256=ctx.code_hash,
                code_approval_sha256=ctx.code_hash,
                signed_floor_krw=D(str(ctx.owner.limits['total_loss_floor_krw'])),
                signed_daily_loss_krw=D(str(ctx.owner.limits['daily_loss_krw'])),
                observed_at=at,source_sha256=ctx.ctx_hash)
        with patch.object(GF,'owner',side_effect=current_claim):
            state,policy,claim=GF.seed(start=start,pol=pol,floor=floor,daily=daily,
                                      daily_stopped=daily_stopped,halted=halted)
        bstore,gstore=CheckpointStore(root=home),GuardCheckpointStore(root=home)
        bhead=BaselineHead(root=hroot,name='baseline-head',chain=CheckpointChain(bstore))
        ghead=BaselineHead(root=hroot,name='continuous-guard',chain=GuardChain(gstore))
        bstore.seed(state.baseline,expected_head=state.baseline.state_digest)
        bhead.initialize_reviewed_head(state.baseline.state_digest)
        gstore.seed(state,expected_head=state.state_sha256)
        ghead.initialize_reviewed_head(state.state_sha256)
        s=SimpleNamespace(state=state,policy=policy,context=claim,journal=Journal(),
                          bstore=bstore,gstore=gstore,bhead=bhead,ghead=ghead)
        with patch.object(GF,'START',start):
            package=GF.build(state,policy,claim,prices,end=end)
        if spare_cash:
            package=with_spare_cash(package)
        control=GENESIS
        if control_prefix:
            prior=s.journal.snapshot()  # verified actual prefix, outside the guard transaction
            control=prior[-1]['row_sha256'] if prior else GENESIS
        receipt=GC.commit(s,package,control=control)
        provider=PF.provider(s,package,receipt,expected_control_head=control)
        adapter=DryRunAdapter(upbit)
        clock_cell=[package['now']]
        fixture_clock=(lambda:clock_cell[0]) if clock is None else clock
        controller=Controller(journal=s.journal,account_provider=provider,policy=policy,
                              adapters={'upbit':adapter},session_provider=lambda _:None,clock=fixture_clock)
        rules=InstrumentRules(venue='upbit',market='spot',symbol='KRW-BTC',lot_size=D('0.1'),tick_size=D(1),
            min_quantity=D('0.1'),min_notional_krw=D(1),fee_fraction=D(0),asof=package['now'],source_digest='a'*64)
        order=Order(client_id='fixture-reducing-order',account_scope=GF.SCOPE,venue='upbit',market='spot',
            symbol='KRW-BTC',side='sell',quantity=D('0.1'),limit_price=D(100),quote_krw=D(1))
        yield SimpleNamespace(s=s,package=package,receipt=receipt,provider=provider,controller=controller,
            home=home,key=key,adapter=adapter,rules=rules,order=order,now=package['now'],contexts=contexts,
            clock=fixture_clock,clock_cell=clock_cell)



def with_spare_cash(package):
    """Reconcile real arithmetic for a synthetic half-unit holding plus cash.

    No capacity/evaluator/verifier outcome is patched. Coverage, like GF.build's
    original fixture, is explicitly synthetic and grants no live source authority.
    """
    from execution_accounts.continuous import COVERAGE_CONTRACT, VerifiedCoverage, verify_coverage, value_path
    from execution_accounts.model import CashBalance
    capture=package['account_capture']
    original=capture.endpoint_accounts[0]
    fills=tuple(replace(row,quantity=D('0.5')) for row in package['valuation_inputs'].historical_fills)
    pages=[]
    for page in original.pages:
        records=(fills if page.kind=='fills' else
                 tuple(replace(row,quantity=D('0.5'),filled_quantity=D('0.5')) for row in page.rows)
                 if page.kind=='orders' else page.rows)
        pages.append(replace(page,rows=records,page_sha256=""))
    account=replace(original,balances=(CashBalance(currency='KRW',total=D(50),settled=D(50)),),
        positions=tuple(replace(row,units=D('0.5')) for row in original.positions),pages=tuple(pages))
    capture=replace(capture,captured_accounts=(account,),endpoint_accounts=(account,))
    inputs=replace(package['valuation_inputs'],opening_cash_krw=D(50),
                   opening_units=(('KRW-BTC',D('0.5')),),historical_fills=fills)
    path=package['path']
    def synthetic(request, supplied_path):
        return VerifiedCoverage(request_sha256=content_digest(request),contract=COVERAGE_CONTRACT,
            authority_sha256='b'*64,source_proof_sha256='c'*64,verified_at=supplied_path.watermark_received_at)
    coverage=verify_coverage(path,account_capture_sha256=content_digest((capture.manifest_sha256,
        capture.captured_accounts,capture.endpoint_accounts)),verifier=synthetic,now=package['now'])
    valuation=value_path(path,opening_cash_krw=inputs.opening_cash_krw,opening_units=inputs.opening_units,
        historical_fills=inputs.historical_fills,interval_fills=inputs.interval_fills,
        previous_equity_krw=package['baseline_before'].equity_krw,
        previous_realized_net_krw=package['baseline_before'].realized_net_total_krw)
    interval=replace(package['interval'],equity_krw=valuation.equity_krw,
        minimum_equity_krw=valuation.minimum_equity_krw,maximum_equity_krw=valuation.maximum_equity_krw,
        realized_net_total_krw=valuation.realized_net_total_krw,source_sha256=content_digest((account,)),
        coverage_sha256=content_digest((path,coverage)))
    return package|{'account_capture':capture,'valuation_inputs':inputs,'coverage':coverage,'interval':interval}


def refused(call,code=None):
    try:
        call()
    except (ValueError,RuntimeError) as exc:
        if code is not None:assert str(exc)==code,(str(exc),code)
        return str(exc)
    raise AssertionError('unverified committed account accepted')


def rows(e):
    return e.s.journal.snapshot()


def test_actual_owner_committed_read_and_repeat_observation_keep_heads_and_original_times():
    with fixture() as e:
        before=(e.s.bhead.read(),e.s.ghead.read(),e.s.bstore.load(expected_head=e.receipt.baseline_head))
        with ExitStack() as stack:
            for cls,method in ((CheckpointStore,'commit'),(GuardCheckpointStore,'commit'),
                               (BaselineHead,'compare_and_set'),(BaselineHead,'initialize_reviewed_head'),
                               (Journal,'snapshot')):
                stack.enter_context(patch.object(cls,method,side_effect=AssertionError('unexpected second commit/snapshot')))
            first=e.controller.observe(now=e.now)
            second=e.controller.observe(now=e.now)
        after=(e.s.bhead.read(),e.s.ghead.read(),e.s.bstore.load(expected_head=e.receipt.baseline_head))
        assert before==after and first==second and not first.new_entry_blocked
        snapshots=[r['data'] for r in rows(e) if r['kind']=='risk_snapshot']
        assert len(snapshots)==2 and snapshots[-1]['policy_digest']==control_digest(e.s.policy)
        assert after[2].asof==e.package['interval'].end
        assert not e.adapter.requests


def test_guard_only_daily_stop_is_persisted_without_fake_loss_or_permanent_halt():
    with fixture(daily_stopped=True) as e:
        projected=PF.read(e.s,e.provider,e.now)
        assert projected.daily_stopped and projected.observation.risk.observed_daily_loss==0
        assert not projected.observation.risk.halted
        result=e.controller.observe(now=e.now)
        assert result.new_entry_blocked and 'PERSISTENT_DAILY_STOP' in result.reasons
        assert 'PERSISTENT_HALT' not in result.reasons and result.protective_action_needed
        snapshots=[r['data'] for r in rows(e) if r['kind']=='risk_snapshot']
        assert len(snapshots)==1 and snapshots[0]['daily_stopped'] is True
        assert not any(r['kind']=='halt' for r in rows(e))
        assert e.controller.observe(now=e.now).new_entry_blocked
        assert not e.adapter.requests


def test_guard_daily_stop_does_not_veto_explicit_reducing_dry_order_or_known_cancel():
    with fixture(daily_stopped=True) as e:
        assert e.controller.observe(now=e.now).new_entry_blocked
        reserved=e.controller.reserve(e.order,e.rules,session_id='fixture-monitor',now=e.now)
        assert reserved.status=='RESERVED'
        sent=e.controller.dispatch(e.order.client_id,now=e.now)
        assert sent.status=='ACKNOWLEDGED' and len(e.adapter.requests)==1
        current=e.controller.reconcile(e.order.client_id,now=e.now)
        assert current.status=='ACKNOWLEDGED' and e.adapter.requests[-1].operation=='status'
        e.controller.cancel(e.order.client_id,now=e.now)
        assert e.adapter.requests[-1].operation=='cancel'
        assert [r.operation for r in e.adapter.requests].count('create')==1
        assert not any(r['kind']=='risk_snapshot' and not r['data']['daily_stopped'] for r in rows(e))


def test_guard_peak_and_permanent_halt_survive_recovered_endpoint():
    with fixture(prices=('110','105','115')) as e:
        result=e.controller.observe(now=e.now)
        assert result.new_entry_blocked and 'PERSISTENT_HALT' in result.reasons
        assert result.high_watermark==D(115) and result.effective_floor==D(115)
        assert any(r['kind']=='halt' for r in rows(e)) and not e.adapter.requests


def test_guard_and_control_policy_hashes_keep_distinct_decimal_codecs():
    with fixture(pol=GF.policy(initial='5E1',activation='5E1'),floor='65') as e:
        assert content_digest(e.s.policy)!=control_digest(e.s.policy)
        result=e.controller.observe(now=e.now)
        assert result==e.controller.observe(now=e.now)
        assert PF.read(e.s,e.provider,e.now).policy_sha256==content_digest(e.s.policy)
        assert [r['data']['policy_digest'] for r in rows(e) if r['kind']=='risk_snapshot']==[control_digest(e.s.policy)]*2


def test_same_head_midnight_scheduled_limits_are_compared_with_actual_current_fold():
    start=datetime(2026,11,6,23,59,50,tzinfo=M.KST)
    end=datetime(2026,11,7,tzinfo=M.KST)
    def schedule(home,key,at):
        CF.sign(key,'limit_set',{'total_loss_floor_krw':90.0,'daily_loss_krw':20.0},
                M.iso_utc(at-timedelta(hours=1)))
    with fixture(start=start,end=end,configure=schedule,prices=('101',)) as e:
        projection=PF.read(e.s,e.provider,e.now)
        current=owner.load_context(e.now,projection.observation.positions)
        assert current.owner.head==e.contexts[0].owner.head
        assert projection.policy_day==end.date()
        assert current.owner.limits['total_loss_floor_krw']==90.0
        assert projection.owner_claim.signed_floor_krw==100
        before=rows(e)
        refused(lambda:e.controller.observe(now=e.now),'COMMITTED_ACCOUNT_EFFECTIVE_LIMITS_CHANGED')
        assert rows(e)==before and not e.adapter.requests


def test_actual_operation_session_controls_same_head_scheduled_limit_comparison():
    start=datetime(2026,11,7,20,tzinfo=M.KST)
    def schedule(home,key,at):
        CF.sign(key,'session_armed',{'session_id':'previously-armed'},M.iso_utc(at-timedelta(days=2)))
        CF.sign(key,'limit_set',{'total_loss_floor_krw':90.0,'daily_loss_krw':20.0},
                M.iso_utc(at-timedelta(days=1)))
    with fixture(start=start,configure=schedule,floor='100',daily='10',pol=GF.policy(initial='50',activation='50')) as e:
        # The guard anchor may retain a stricter floor; the original owner claim
        # is the actually effective unscoped context (90/20), not that floor.
        assert e.package['owner_after'].signed_floor_krw==90
        assert not e.controller.observe(now=e.now).new_entry_blocked
        obs=PF.read(e.s,e.provider,e.now).observation
        current=owner.load_context(e.now,obs.positions,session_id='previously-armed')
        assert current.owner.head==e.contexts[0].owner.head and current.owner.limits['total_loss_floor_krw']==100
        refused(lambda:e.controller.reserve(e.order,e.rules,session_id='previously-armed',now=e.now),
                'COMMITTED_ACCOUNT_EFFECTIVE_LIMITS_CHANGED')
        assert not any(r['kind']=='reserved' for r in rows(e)) and not e.adapter.requests


def test_new_owner_head_policy_or_future_code_approval_cannot_reuse_committed_epoch():
    with fixture() as e:
        CF.sign(e.key,'age_of_majority',{'birth_date':'2000-01-01','evidence':'fixture'})
        refused(lambda:e.controller.observe(now=e.now),'COMMITTED_ACCOUNT_OWNER_EPOCH_CHANGED')
    with fixture() as e:
        e.controller.policy=replace(e.s.policy,first_day_loss_budget=D(9))
        refused(lambda:e.controller.observe(now=e.now),'COMMITTED_ACCOUNT_OWNER_EPOCH_CHANGED')
    def future_code(home,key,at):
        files=[['fixture-future.py','f'*64]]
        CF.sign(key,'code_approved',{'sha256':owner.sha256_hex(owner.canonical_json(files)),'files':files},
                M.iso_utc(at+timedelta(seconds=1)))
    with fixture(configure=future_code) as e:
        assert e.contexts[0].code_signed
        refused(lambda:e.controller.observe(now=e.now),'COMMITTED_ACCOUNT_CURRENT_OWNER_REQUIRED')
        assert not e.adapter.requests


def test_actual_prior_owner_halt_cannot_disappear_from_matching_guard_epoch():
    def stop(home,key,at):
        CF.sign(None,'system_halt',{'floor_krw':100.0},M.iso_utc(at-timedelta(seconds=1)))
    for retained in (False,True):
        with fixture(configure=stop,halted=retained) as e:
            assert e.contexts[0].owner.halted_floors
            if retained:
                result=e.controller.observe(now=e.now)
                assert result.new_entry_blocked and 'PERSISTENT_HALT' in result.reasons
            else:
                refused(lambda:e.controller.observe(now=e.now),'COMMITTED_ACCOUNT_OWNER_HALT_NOT_RETAINED')
            assert not e.adapter.requests


def test_unsealed_or_modified_actual_loader_context_refuses_without_public_context_input():
    for mode in ('unsealed','mutated'):
        with fixture() as e:
            actual=owner.load_context
            def damaged(*args,**kwargs):
                ctx=actual(*args,**kwargs)
                if mode=='unsealed':return replace(ctx)
                object.__setattr__(ctx,'equity_krw',ctx.equity_krw+1)
                return ctx
            with patch.object(owner,'load_context',side_effect=damaged):
                refused(lambda:e.controller.observe(now=e.now),'COMMITTED_ACCOUNT_OWNER_CONTEXT_INVALID')
            assert not e.adapter.requests


def test_callable_projection_and_read_duck_type_never_replace_legacy_observation():
    with fixture() as e:
        projection=PF.read(e.s,e.provider,e.now)
        class Duck:
            def read(self,**_):raise AssertionError('duck read must not be invoked')
        for provider in (lambda _:projection,lambda _:True,Duck()):
            e.controller.account_provider=provider
            refused(lambda:e.controller.observe(now=e.now))
        assert not e.adapter.requests


def test_unsupported_guard_floor_relaxation_and_invalidated_heads_do_not_mutate_state():
    with fixture() as e:
        before=rows(e)
        refused(lambda:e.controller.approve_floor_relaxation(floor=D(100),now=e.now,session_id='fixture'),
                'COMMITTED_ACCOUNT_FLOOR_TRANSITION_UNSUPPORTED')
        assert rows(e)==before
        with patch.object(e.s.ghead,'read',return_value='f'*64):
            refused(lambda:e.controller.observe(now=e.now),'COMMITTED_ACCOUNT_HEAD_CHANGED')
        assert rows(e)==before and not e.adapter.requests


def test_kill_and_halt_remain_durable_when_new_provider_is_unavailable():
    for operation in ('kill','halt'):
        with fixture() as e:
            with patch.object(e.provider,'read',side_effect=ValueError('COMMITTED_ACCOUNT_HEAD_CHANGED')):
                result=(e.controller.kill('fixture',reason='owner_requested',now=e.now) if operation=='kill'
                        else e.controller.halt(floor=D(100),now=e.now))
            assert result is False and rows(e)[-1]['kind']==operation
            assert not e.adapter.requests


def test_legacy_cancel_and_reconcile_do_not_gain_new_committed_owner_requirements():
    with fixture() as e:
        obs=PF.read(e.s,e.provider,e.now).observation
        e.controller=Controller(journal=e.s.journal,account_provider=lambda _:obs,policy=e.s.policy,
                                adapters={'upbit':e.adapter},session_provider=lambda _:None)
        e.controller.reserve(e.order,e.rules,session_id='fixture',now=e.now)
        e.controller.dispatch(e.order.client_id,now=e.now)
        with patch.object(owner,'load_context',side_effect=AssertionError('legacy reconciliation has no owner read')):
            e.controller.reconcile(e.order.client_id,now=e.now)
        assert e.adapter.requests[-1].operation=='status'
        # Break only the temporary actual owner log after a real good snapshot.
        # The actual loader, not a fabricated Context, supplies its legacy fallback.
        path=owner.log_path()
        path.write_bytes(path.read_bytes()+b'{incomplete fixture row\n')
        context=owner.load_context(e.now,obs.positions,session_id='fixture')
        assert not context.owner.ok and context.snapshot is not None and context.snapshot.valid
        e.controller.cancel(e.order.client_id,now=e.now)
        assert e.adapter.requests[-1].operation=='cancel'


def test_first_buy_without_prior_observe_retains_guard_only_daily_stop():
    with fixture(daily_stopped=True,spare_cash=True) as e:
        projection=PF.read(e.s,e.provider,e.now)
        obs=projection.observation
        assert obs.settled_cash_krw[('upbit',GF.SCOPE)]==50
        assert projection.daily_stopped and obs.risk.observed_daily_loss==0 and not obs.risk.halted
        assert not any(r['kind']=='risk_snapshot' for r in rows(e))
        buy=replace(e.order,side='buy',client_id='fixture-blocked-buy')
        # Genuine capacity is sufficient; metadata alone must block this first
        # reserve before a session or adapter preparation can be reached.
        e.controller._capacity(buy,e.rules,obs,{})
        refused(lambda:e.controller.reserve(buy,e.rules,session_id='fixture',now=e.now),
                'risk policy blocks new entry')
        current=rows(e)
        assert current[-1]['kind']=='risk_snapshot' and current[-1]['data']['daily_stopped']
        assert not any(r['kind']=='reserved' for r in current) and not e.adapter.requests


def test_owner_change_after_real_reservation_blocks_dispatch_and_preserves_local_cancel():
    with fixture() as e:
        reserved=e.controller.reserve(e.order,e.rules,session_id='fixture',now=e.now)
        assert reserved.status=='RESERVED'
        CF.sign(e.key,'age_of_majority',{'birth_date':'2000-01-01','evidence':'updated fixture'})
        refused(lambda:e.controller.dispatch(e.order.client_id,now=e.now),
                'COMMITTED_ACCOUNT_OWNER_EPOCH_CHANGED')
        assert e.controller.states()[0].status=='RESERVED' and not e.adapter.requests
        assert e.controller.cancel(e.order.client_id,now=e.now).status=='CANCELLED_LOCAL'
        assert not e.adapter.requests
