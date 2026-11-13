"""Read-only committed-baseline projection over invented, temporary evidence.

One fixture uses actual guard/baseline commits and independent heads. The helper
itself checks consistency, never issuance, source authenticity or owner consent.
No live source, actual owner state, order or account credential is used.
"""
from contextlib import ExitStack
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal, localcontext
import re
from unittest.mock import patch

from execution_accounts import baseline_bridge as B
from execution_accounts.baseline import advance_baseline, initialize_baseline, state_json
from execution_accounts.baseline_store import CheckpointStore
from execution_accounts.model import ExternalFlow, content_digest
from execution_control.store import Journal
from execution_launch.baseline_head import BaselineHead
from tests import accounts_baseline_integration as I
from tests.accounts_provider import bundle, fill
from tests import control_continuous_guard as G, control_continuous_guard_commit as C

D = Decimal


def project(state, frame, **changes):
    args = dict(now=frame.interval.end,source_sha256=frame.interval.source_sha256,
                interval_start=frame.interval.start)
    return B.reconcile_committed_baseline(state,frame.accounts,**(args | changes))


def refused(call,code=None):
    try: call()
    except B.BaselineBridgeError as exc:
        assert re.fullmatch(r'BASELINE_BRIDGE_[A-Z0-9_]+',str(exc)), 'private diagnostic escaped'
        if code is not None: assert str(exc) == code,(str(exc),code)
        return
    raise AssertionError('invalid committed projection accepted')


def prepared_profit():
    before = I.initial()
    frame = I.profit_frame(before)
    return B.advance_account_baseline(before,frame.interval,frame.accounts,now=frame.interval.end).state,frame


def test_actual_committed_guard_endpoint_projects_repeatedly_without_advancing_or_accessing_stores():
    with C.stack() as e:
        package = G.build(e.state,e.policy,e.context)
        receipt = C.commit(e,package)
        state = e.bstore.load(expected_head=receipt.baseline_head)
        guard = e.gstore.load(expected_head=receipt.guard_head)
        accounts = package['account_capture'].endpoint_accounts
        original = state_json(state)
        paths = tuple(sorted(e.bstore._base.rglob('*')))
        files = {path:path.read_bytes() for path in paths if path.is_file()}
        with ExitStack() as checks:
            for target,name in ((B,'advance_baseline'),(B,'initialize_baseline'),
                (CheckpointStore,'load'),(CheckpointStore,'commit'),(CheckpointStore,'seed'),
                (BaselineHead,'read'),(BaselineHead,'compare_and_set'),(BaselineHead,'initialize_reviewed_head'),
                (Journal,'snapshot'),(Journal,'transaction')):
                checks.enter_context(patch.object(target,name,side_effect=AssertionError('projection performed I/O or reduction')))
            first = B.reconcile_committed_baseline(state,accounts,now=package['now'],
                source_sha256=package['interval'].source_sha256,interval_start=package['path'].start)
            second = B.reconcile_committed_baseline(state,accounts,now=package['now']+timedelta(seconds=1),
                source_sha256=package['interval'].source_sha256,interval_start=package['path'].start)
        assert first == second and first.state == state and first.state is not state
        assert first.state.sequence == 1 and state_json(state) == original
        assert first.observation.asof == state.asof == first.observation.risk.asof
        assert first.observation.risk.prior_high_watermark == state.high_watermark
        assert first.observation.risk.approved_effective_floor == state.approved_effective_floor
        # Baseline projection alone must not invent the separate guard latch or
        # claim it was consumed; the later bridge must preserve guard.floor/halt.
        assert guard.permanently_halted and guard.applied_floor_krw > state.approved_effective_floor
        assert not first.observation.risk.halted and not hasattr(first,'execution_ready')
        assert {path:path.read_bytes() for path in paths if path.is_file()} == files
        assert e.bhead.read() == receipt.baseline_head and e.ghead.read() == receipt.guard_head


def test_committed_profit_extrema_and_fees_remain_exact_under_low_caller_precision():
    state,frame = prepared_profit()
    original = state_json(state)
    with localcontext() as numeric:
        numeric.prec = 3
        result = project(state,frame)
    assert result.observation.risk.equity == D('1018')
    assert result.observation.risk.current_day_realized_net_profit == D('18')
    assert result.state.realized_net_total_krw == D('18')
    assert result.observation.risk.observed_daily_loss == D('1')
    assert result.observation.risk.prior_high_watermark == D('1018')
    assert result.bundle.risk_baseline.source_sha256 == state.state_digest
    assert state_json(state) == original


def test_same_aggregate_equity_with_changed_holdings_is_not_the_committed_endpoint():
    with C.stack() as e:
        package = G.build(e.state,e.policy,e.context)
        receipt = C.commit(e,package)
        state = e.bstore.load(expected_head=receipt.baseline_head)
        account = package['account_capture'].endpoint_accounts[0]
        position = account.positions[0]
        changed = (replace(account,positions=(replace(position,units=position.units/2,price=position.price*2),)),)
        assert changed[0].positions[0].units*changed[0].positions[0].price == position.units*position.price
        refused(lambda:B.reconcile_committed_baseline(state,changed,now=package['now'],
            source_sha256=package['interval'].source_sha256,interval_start=package['path'].start),
            'BASELINE_BRIDGE_ENDPOINT_CHANGED')
        # A freshly computed self-hash still cannot bypass independent FIFO
        # inventory reconciliation, and would never prove source authenticity.
        refused(lambda:B.reconcile_committed_baseline(state,changed,now=package['now'],
            source_sha256=content_digest(changed),interval_start=package['path'].start))


def test_changed_endpoint_timestamp_is_not_restamped_to_match_a_committed_state():
    state,frame = prepared_profit()
    changed = (replace(frame.accounts[0],observed_at=state.asof+timedelta(microseconds=1)),)
    refused(lambda:B.reconcile_committed_baseline(state,changed,now=state.asof+timedelta(seconds=1),
        source_sha256=content_digest(changed),interval_start=frame.interval.start),
        'BASELINE_BRIDGE_ACCOUNT_BINDING_MISMATCH')
    assert frame.accounts[0].observed_at == state.asof


def test_checkpoint_mutation_refuses_but_an_identical_valid_clone_is_not_an_issuer_token():
    state,frame = prepared_profit()
    cloned = replace(state)
    assert project(cloned,frame).state == state
    assert not hasattr(project(cloned,frame),'authenticated')
    changed = replace(state,equity_krw=state.equity_krw+D('1'))
    refused(lambda:project(changed,frame),'BASELINE_BRIDGE_EVIDENCE_REFUSED')
    erased = replace(state)
    object.__delattr__(erased,'state_digest')
    refused(lambda:project(erased,frame),'BASELINE_BRIDGE_EVIDENCE_REFUSED')


def test_schema_valid_but_unreconciled_profit_counters_do_not_gain_trust_from_their_hash():
    before = I.initial(); frame = I.profit_frame(before)
    wrong = advance_baseline(before,replace(frame.interval,realized_net_total_krw=D('17')))
    refused(lambda:project(wrong,frame),'BASELINE_BRIDGE_CUMULATIVE_PROFIT_MISMATCH')
    conventions,anchor,_ = I.anchor_fixture(day_open=D('1'))
    before = initialize_baseline(conventions,anchor); frame = I.profit_frame(before)
    wrong = advance_baseline(before,frame.interval)
    refused(lambda:project(wrong,frame),'BASELINE_BRIDGE_DAILY_PROFIT_MISMATCH')
    conventions,anchor,_ = I.anchor_fixture(previous=D('1'))
    before = initialize_baseline(conventions,anchor); frame = I.frame_for(before)
    wrong = advance_baseline(before,frame.interval)
    refused(lambda:project(wrong,frame),'BASELINE_BRIDGE_PRIOR_PROFIT_MISMATCH')


def test_half_open_endpoint_fill_and_interval_external_flow_remain_refused():
    before = I.initial(); end = before.asof+timedelta(seconds=10)
    buy = fill(quantity=D('1'),fee=D('1'),at=end)
    accounts = bundle(now=end,opening=D('1000'),cash=D('899'),units=D('1'),price=D('100'),fills=(buy,)).accounts
    frame = I.frame_for(before,accounts=accounts,equity_krw=D('999'),minimum_equity_krw=D('999'))
    state = advance_baseline(before,frame.interval)
    refused(lambda:project(state,frame),'BASELINE_BRIDGE_CUTOFF_MISMATCH')
    deposit = ExternalFlow(flow_id='invented-deposit',currency='KRW',kind='deposit',amount=D('1'),
        effective_at=before.asof+timedelta(seconds=1))
    accounts = bundle(now=end,opening=D('1000'),cash=D('1001'),flows=(deposit,)).accounts
    frame = I.frame_for(before,accounts=accounts,equity_krw=D('1001'),maximum_equity_krw=D('1001'))
    state = advance_baseline(before,frame.interval)
    refused(lambda:project(state,frame),'BASELINE_BRIDGE_INTERVAL_FLOW_REFUSED')


def test_freshness_boundary_and_clock_rollback_never_refresh_the_original_asof():
    state,frame = prepared_profit()
    result = project(state,frame,now=state.asof+timedelta(seconds=30))
    assert result.observation.asof == state.asof
    for at in (state.asof-timedelta(microseconds=1),state.asof+timedelta(seconds=30,microseconds=1)):
        refused(lambda at=at:project(state,frame,now=at),'BASELINE_BRIDGE_EVIDENCE_REFUSED')


def test_seoul_midnight_requires_its_actual_new_day_checkpoint_and_preserves_profit_history():
    start = I.NOW.replace(hour=14,minute=59,second=49)
    conventions,anchor,accounts = I.anchor_fixture(now=start)
    before = B.initialize_account_baseline(conventions,anchor,accounts,now=start).state
    old_frame = I.profit_frame(before)
    old = B.advance_account_baseline(before,old_frame.interval,old_frame.accounts,now=old_frame.interval.end).state
    midnight = old.asof+timedelta(seconds=1)
    refused(lambda:project(old,old_frame,now=midnight),'BASELINE_BRIDGE_EVIDENCE_REFUSED')
    start = I.NOW.replace(hour=14,minute=59,second=50)
    conventions,anchor,accounts = I.anchor_fixture(now=start)
    before = B.initialize_account_baseline(conventions,anchor,accounts,now=start).state
    frame = I.profit_frame(before)
    state = B.advance_account_baseline(before,frame.interval,frame.accounts,now=frame.interval.end).state
    projected = project(state,frame)
    assert projected.state.realized_net_total_krw == D('18')
    assert projected.observation.risk.current_day_realized_net_profit == D(0)
    assert projected.observation.risk.prior_day_realized_net_profit == D('18')
    assert projected.observation.risk.prior_high_watermark == D('1018')
    assert projected.state.first_trading_day == before.first_trading_day


def test_recovery_cutoff_requires_boundary_evidence_and_exact_original_checkpoint_source():
    start = G.START.replace(hour=21,minute=59,second=50)
    with C.stack(start=start,pol=G.policy(initial='50',activation='50',recovery=True),floor='65') as e:
        package = G.build(e.state,e.policy,e.context,('100',))
        receipt = C.commit(e,package)
        state = e.bstore.load(expected_head=receipt.baseline_head)
        accounts = package['account_capture'].endpoint_accounts
        cutoff = start.replace(hour=22,minute=0,second=0)
        refused(lambda:B.reconcile_committed_baseline(state,accounts,now=cutoff,
            source_sha256=package['interval'].source_sha256,interval_start=start),
            'BASELINE_BRIDGE_EVIDENCE_REFUSED')
    with C.stack(start=start,pol=G.policy(initial='50',activation='50',recovery=True),floor='65') as e:
        package = G.build(e.state,e.policy,e.context,('100',),end=cutoff)
        receipt = C.commit(e,package)
        state = e.bstore.load(expected_head=receipt.baseline_head)
        accounts = package['account_capture'].endpoint_accounts
        result = B.reconcile_committed_baseline(state,accounts,now=cutoff,
            source_sha256=package['interval'].source_sha256,interval_start=start)
        assert result.observation.risk.recovery_checkpoint == state.recovery_checkpoint
        changed = (replace(accounts[0],server_time=cutoff+timedelta(seconds=1)),)
        refused(lambda:B.reconcile_committed_baseline(state,changed,now=cutoff,
            source_sha256=content_digest(changed),interval_start=start),
            'BASELINE_BRIDGE_RECOVERY_SOURCE_CHANGED')


def test_exact_state_digest_and_interval_start_types_fail_with_bounded_diagnostics():
    state,frame = prepared_profit()
    class Impostor:
        @property
        def state_digest(self): raise AssertionError('untrusted property executed')
    refused(lambda:project(Impostor(),frame),'BASELINE_BRIDGE_STATE_REQUIRED')
    for digest in (True,None,'','f'*63,'F'*64,b'f'*64):
        refused(lambda digest=digest:project(state,frame,source_sha256=digest),
                'BASELINE_BRIDGE_SOURCE_DIGEST_REQUIRED')
    for start in (True,'earlier',state.asof,state.asof+timedelta(seconds=1),state.asof.replace(tzinfo=None)):
        refused(lambda start=start:project(state,frame,interval_start=start),
                'BASELINE_BRIDGE_INTERVAL_START_INVALID')
    assert B.reconcile_committed_baseline(state,frame.accounts,now=state.asof,
        source_sha256=frame.interval.source_sha256).state == state
