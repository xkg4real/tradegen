"""I3a integration over invented GET replies and an actual precreated recorder.

Collector replay, FIFO, boundary reconstruction and guard planning run for real.
Coverage and owner claims are explicitly synthetic, never production authority.
All baseline files and the existing path-only archive live in disposable homes;
no key, live API, order, publication or full-packet restart store is involved.
"""
from contextlib import ExitStack
from copy import deepcopy
from dataclasses import fields, replace
from datetime import timedelta
from decimal import Decimal, localcontext
import hashlib
import json
import re
from types import SimpleNamespace
from unittest.mock import patch

from execution_accounts.baseline_store import CheckpointStore
from execution_accounts.baseline_bridge import ContinuousAccountProvider
from execution_accounts.collector import SourceReceipt
from execution_accounts.continuous import (COVERAGE_CONTRACT, ContinuousPriceRecorder, CoverageRequest,
    EquityEvent, PriceMark, VerifiedCoverage)
from execution_accounts.model import content_digest
from execution_accounts.provider import build_observation
from execution_control.controller import Controller
from execution_control.risk import RecoveryCondition, RiskPolicy
from execution_launch import account_interval as AI
from execution_launch import guard_capture_material as M
from execution_launch.continuous_guard import (GuardAnchor, OwnerContextClaim,
    plan_continuous_guard, reviewed_guard_anchor)
from tests.launch_account_interval import (ANCHOR, COVERAGE, BUY, FEES, FakeClock, FakeUpbit,
    SCOPE, at, order, series)
from tests.accounts_continuous import held_series, mark_event, fill_event

D = Decimal
START = at(26, 20)


class TraceClock(FakeClock):
    def __init__(self, start, step_ms=0):
        super().__init__(start, step_ms)
        self.values = []

    def __call__(self):
        value = super().__call__()
        self.values.append(value)
        return value


def snapshot(root):
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob('*') if p.is_file()}


def capture(env, *, events=(), opening='10050', capture_at=None, step_ms=100,
            exchange=None, fees=None, recorder=None, stream_epoch='synthetic-i3a-epoch', first_sequence=10):
    """Recorder exists, with any synthetic events, before the actual GET capture."""
    previous = env.state
    recorder = recorder or ContinuousPriceRecorder(account_scope=SCOPE, stream_epoch=stream_epoch,
        previous_state_digest=previous.state_digest, start=previous.asof,
        opening_marks=(PriceMark(symbol='KRW-BTC', price=D(opening), asof=previous.asof),), first_sequence=first_sequence)
    for event in events:
        recorder.append(event)
    exchange = env.exchange if exchange is None else exchange
    clock = TraceClock(capture_at or previous.asof+timedelta(seconds=5), step_ms)
    exchange.clock = clock
    originals, path_inputs, verification_calls = [], [], []

    class RecordingSource:
        account_scope = SCOPE
        def fetch(self, path, params):
            receipt = exchange.fetch(path, params)
            originals.append(receipt)
            return receipt

    def path_source(baseline, original, end):
        assert baseline == previous and type(original) is AI.ContinuousCapture
        assert not hasattr(original, 'bundle')
        path_inputs.append(original)
        return recorder.seal(end=end, watermark_sequence=first_sequence+len(events),
            watermark_received_at=original.observed_at, watermark_source_sha256='a'*64)

    def synthetic_coverage(request, path):
        verification_calls.append((request, path))
        return VerifiedCoverage(request_sha256=content_digest(request), contract=COVERAGE_CONTRACT,
            authority_sha256='b'*64, source_proof_sha256='c'*64, verified_at=path.watermark_received_at)

    anchor, coverage = replace(ANCHOR), replace(COVERAGE)
    fee_inputs = tuple(replace(fee) for fee in (env.fees if fees is None else fees))
    source = AI.ContinuousUpbitCandidateSource(path_source=path_source,
        coverage_verifier=synthetic_coverage, archive_root=env.home)
    staged = source.collect(RecordingSource(), previous=previous, anchor=anchor, coverage=coverage,
                            clock=clock, trade_fees=fee_inputs)
    return SimpleNamespace(staged=staged, source=source, recorder=recorder, clock=clock,
        originals=originals, path_inputs=path_inputs, verification_calls=verification_calls,
        anchor=anchor, coverage=coverage, fees=fee_inputs)


def material(env, staged, *, now=None):
    return M.prepare_guard_capture_material(staged, env.state,
        now=staged.observed_at+timedelta(milliseconds=100) if now is None else now)


def plan(env, value, *, now, checkpoint=None, daily_stopped=False):
    """Synthetic owner/anchor only; existing guard validates and computes every amount."""
    baseline = env.state
    policy = RiskPolicy(version='synthetic-i3a-only', initial_equity=D('70000'),
        drawdown_activation_equity=D('6000000'), positive_profit_loss_fraction=D('.35'),
        peak_drawdown_fraction=D('.35'), zero_profit_day_target_fraction=D('.3'),
        first_day_loss_budget=D('10000'), zero_profit_day_loss_budget=D('10000'),
        valuation_convention='marked_equity', daily_loss_convention='externally_reconciled',
        recovery_condition=RecoveryCondition(cutoff_seconds=79200, timezone='Asia/Seoul',
                                            reference='day_start_marked_equity'))
    owner = OwnerContextClaim(owner_head_sha256='1'*64, code_sha256='2'*64,
        code_approval_sha256='3'*64, signed_floor_krw=baseline.approved_effective_floor,
        signed_daily_loss_krw=D('10000'), observed_at=baseline.asof, source_sha256='4'*64)
    anchor = GuardAnchor(baseline_state_sha256=baseline.state_digest, control_journal_head_sha256='6'*64,
        high_watermark=baseline.high_watermark, day_start_equity=baseline.day_start_equity,
        observed_daily_loss=baseline.observed_daily_loss, applied_floor_krw=baseline.high_watermark,
        daily_stopped=daily_stopped, permanently_halted=baseline.equity_krw < baseline.high_watermark,
        recorded_at=baseline.asof, source_sha256='7'*64)
    if checkpoint is None:
        checkpoint = reviewed_guard_anchor(anchor, baseline=baseline, policy=policy, owner=owner)
    return plan_continuous_guard(checkpoint, baseline_before=baseline, policy=policy,
        owner_before=owner, owner_after=replace(owner, observed_at=now), path=value.path,
        valuation_inputs=value.valuation_inputs, account_capture=value.account_capture,
        coverage=value.coverage, interval=value.interval, now=now)


def refused(call, expected=None):
    try:
        call()
    except ValueError as exc:
        code = str(exc)
        assert re.fullmatch(r'(?:GUARD_CAPTURE|COLLECTOR|ACCOUNT_INTERVAL|CONTINUOUS|BASELINE|GUARD|CASH|POSITION|FILL|ORDER|EVIDENCE)_[A-Z0-9_]+', code), code
        if expected is not None:
            assert code in ((expected,) if isinstance(expected, str) else expected), (code, expected)
        return code
    raise AssertionError('expected fixed evidence refusal')


def receipt_body(receipt, body):
    raw = json.dumps(body, separators=(',', ':')).encode('utf-8')
    return replace(receipt, raw_body=raw, sha256=hashlib.sha256(raw).hexdigest())


def rebound(staged, *, receipts=None, accounts=None, fees=None):
    """Adversary recomputes all public hashes; this does NOT issue source trust."""
    receipts = staged.capture.receipts if receipts is None else tuple(receipts)
    fees = staged.trade_fees if fees is None else tuple(fees)
    manifest = content_digest((staged.anchor, staged.collection_coverage, fees,
        tuple((r.path, r.params, r.account_scope, r.received_at, r.server_time, r.sha256) for r in receipts)))
    def bind(account):
        return replace(account, pages=tuple(replace(p, source_sha256=manifest, page_sha256='') for p in account.pages),
            fx=tuple(replace(rate, source_sha256=manifest) for rate in account.fx))
    captured = tuple(bind(a) for a in (staged.capture.accounts if accounts is None else accounts))
    # These mutation fixtures use a non-boundary capture, where endpoints must
    # equal the original normalized accounts. No timestamp reconstruction here.
    assert staged.capture.observed_at == staged.preview.interval.end
    endpoint = captured
    original = replace(staged.capture, accounts=captured, receipts=receipts, manifest_sha256=manifest)
    path = staged.preview.path
    request = CoverageRequest(path_sha256=content_digest(path),
        account_capture_sha256=content_digest((manifest, captured, endpoint)), account_scope=path.account_scope,
        stream_epoch=path.stream_epoch, start=path.start, end=path.end,
        first_sequence=path.first_sequence, watermark_sequence=path.watermark_sequence)
    proof = replace(staged.preview.coverage, request_sha256=content_digest(request))
    interval = replace(staged.preview.interval, source_sha256=content_digest(endpoint),
                       coverage_sha256=content_digest((path, proof)))
    preview = replace(staged.preview, accounts=endpoint, coverage=proof, interval=interval)
    return replace(staged, capture=original, manifest_sha256=manifest, trade_fees=fees, preview=preview)


def test_actual_flat_collector_recorder_material_and_guard_plan_keep_realized_fee_history():
    with series(START, high=D('100090'), day_start=D('100090'), loss=D(0)) as env:
        e = capture(env)
        value = material(env, e.staged)
        assert value.valuation_inputs.opening_cash_krw == D('100090')
        assert value.valuation_inputs.opening_units == ()
        assert len(value.valuation_inputs.historical_fills) == 3 and not value.valuation_inputs.interval_fills
        assert value.interval.realized_net_total_krw == D('90')
        result = plan(env, value, now=e.staged.observed_at+timedelta(milliseconds=100))
        assert result.proposed_checkpoint.baseline.equity_krw == D('100090')
        assert not result.execution_ready and not value.execution_ready and not value.source_authenticated
        assert len(e.verification_calls) == 1


def test_actual_held_hidden_trough_reaches_guard_halt_without_endpoint_summary_erasure():
    with held_series(high=D('100045'), day_start=D('100045')) as env:
        events = (mark_event(10, '10200', START+timedelta(seconds=1)),
                  mark_event(11, '9900', START+timedelta(seconds=2)),
                  mark_event(12, '10050', START+timedelta(seconds=3)))
        e = capture(env, events=events)
        value = material(env, e.staged)
        assert value.valuation_inputs.opening_cash_krw == D('89995')
        assert value.valuation_inputs.opening_units == (('KRW-BTC', D(1)),)
        assert value.interval.equity_krw == D('100045')
        assert value.interval.minimum_equity_krw == D('99895')
        result = plan(env, value, now=e.staged.observed_at+timedelta(milliseconds=100))
        assert result.proposed_checkpoint.permanently_halted
        halt = next(r for r in result.required_records if r.kind == 'permanent_floor_halt')
        assert halt.source_at == START+timedelta(seconds=2) and halt.floor_krw == D('100195')


def test_actual_partial_buy_preserves_fill_fee_open_order_and_locked_cash():
    with series(START, exchange=FakeUpbit(cash='100000', orders=()), fees=(), realized=D(0),
                high=D('100000'), loss=D(0)) as env:
        buy = order('partial-buy', 'bid', START+timedelta(seconds=1), '10000',
                    [('partial-fill', '1', '10000')], paid_fee='5')
        buy.update(state='wait', volume='2', remaining_volume='1', locked='10005')
        exchange = FakeUpbit(cash='79990', btc='1', orders=(buy,), ticker='10000')
        exchange.balances[0]['locked'] = '10005'
        collection = env.capture(START+timedelta(seconds=5), exchange=exchange)
        fill, = build_observation(collection.bundle, now=collection.bundle.accounts[0].observed_at).fills
        e = capture(env, events=(fill_event(10, fill),), exchange=exchange, opening='10000', fees=())
        value = material(env, e.staged)
        assert value.valuation_inputs.interval_fills == (fill,) and fill.fee_amount == D(5)
        orders = next(p.rows for p in value.account_capture.captured_accounts[0].pages if p.kind == 'orders')
        assert len(orders) == 1 and orders[0].status == 'partial'
        assert orders[0].remaining_quantity == D(1) and orders[0].reserved_cash == D('10005')
        assert value.interval.equity_krw == D('99995')
        assert plan(env, value, now=e.staged.observed_at+timedelta(milliseconds=100)).proposed_checkpoint.permanently_halted


def test_capture_preserves_exact_raw_receipts_and_outer_inner_fenced_preview_clock_distinctions():
    with held_series() as env:
        e = capture(env)
        staged = e.staged
        assert staged.capture.receipts == tuple(e.originals)
        assert all(a is not b and a.raw_body == b.raw_body for a,b in zip(staged.capture.receipts,e.originals))
        assert staged.collection_requested_at == e.clock.values[0]
        assert staged.collection_clock == (e.clock.values[1], e.clock.values[-2])
        assert staged.collection_started_at == e.clock.values[1] < staged.first_received_at
        assert staged.first_received_at == e.originals[0].received_at
        assert staged.collection_completed_at == staged.capture.observed_at == e.clock.values[-2]
        assert staged.observed_at == e.clock.values[-1] > staged.capture.observed_at
        assert staged.capture == e.path_inputs[0] and staged.capture is not e.path_inputs[0]
        assert 'bundle' not in {f.name for f in fields(staged.capture)}
        assert re.fullmatch('[0-9a-f]{64}', staged.collection_baseline_sha256)


def test_capture_detaches_original_claim_receipt_and_path_callback_objects():
    with series(START) as env:
        e = capture(env)
        before = deepcopy(e.staged)
        object.__setattr__(e.anchor, 'cash_krw', D(1))
        object.__setattr__(e.coverage, 'source_sha256', '9'*64)
        object.__setattr__(e.fees[0], 'fee_krw', D(999))
        object.__setattr__(e.originals[0], 'raw_body', b'[]')
        object.__setattr__(e.path_inputs[0].accounts[0], 'balances', ())
        assert e.staged == before
        assert material(env, e.staged).interval == before.preview.interval


def test_2200_boundary_keeps_original_later_ticker_separate_from_path_endpoint():
    start = at(26, 21, 59, 40)
    with held_series(start, high=D('100045'), day_start=D('100045')) as env:
        env.exchange.ticker = '10300'
        e = capture(env, events=(mark_event(10,'10080',start+timedelta(seconds=15)),),
                    capture_at=at(26,21,59,59), step_ms=200)
        value = material(env, e.staged)
        captured, endpoint = value.account_capture.captured_accounts[0], value.account_capture.endpoint_accounts[0]
        assert captured.observed_at == e.staged.capture.observed_at > at(26,22) == endpoint.observed_at
        assert captured.positions[0].price == D('10300') and captured.positions[0].asof > at(26,22)
        assert endpoint.positions[0].price == D('10080') and endpoint.positions[0].asof == at(26,22)
        assert value.interval.equity_krw == D('100075')
        assert plan(env,value,now=e.staged.observed_at+timedelta(milliseconds=100)).proposed_checkpoint.baseline.asof == at(26,22)


def test_midnight_replays_original_collector_baseline_without_export_or_relabel():
    start = at(27,23,59,40)
    with held_series(start, high=D('100045'), day_start=D('100045'), previous=D(0)) as env:
        env.exchange.ticker = '10300'
        e = capture(env, events=(mark_event(10,'10080',start+timedelta(seconds=15)),),
                    capture_at=at(27,23,59,59), step_ms=200)
        value = material(env,e.staged)
        assert value.account_capture.captured_accounts[0].observed_at > at(28,0)
        assert value.account_capture.endpoint_accounts[0].observed_at == at(28,0)
        assert not hasattr(e.staged,'collection_baseline') and not hasattr(value,'collection_baseline')
        # The prior zero-profit day had no authenticated 22:00 checkpoint. Its
        # synthetic prior guard anchor must preserve the required daily stop.
        result = plan(env,value,now=e.staged.observed_at+timedelta(milliseconds=100),daily_stopped=True)
        assert result.proposed_checkpoint.baseline.day_start_equity == D('100075')
        assert result.proposed_checkpoint.baseline.high_watermark == D('100075')
        refused(lambda:material(env,replace(e.staged,collection_baseline_sha256='0'*64)),
                'GUARD_CAPTURE_BASELINE_BINDING_MISMATCH')


def test_raw_changed_without_hash_and_rehashed_changed_cash_fence_are_both_rejected():
    with held_series() as env:
        e = capture(env); staged=e.staged
        bad=replace(staged.capture.receipts[0],raw_body=b'[]')
        changed=replace(staged,capture=replace(staged.capture,receipts=(bad,*staged.capture.receipts[1:])))
        refused(lambda:material(env,changed),'COLLECTOR_RECEIPT_DIGEST_MISMATCH')
        receipts=[]
        for receipt in staged.capture.receipts:
            if receipt.path=='/v1/accounts':
                body=receipt.decode();body[0]['balance']='89996'
                receipt=receipt_body(receipt,body)
            receipts.append(receipt)
        forged=rebound(staged,receipts=receipts)
        assert forged.manifest_sha256 != staged.manifest_sha256
        refused(lambda:material(env,forged),'CASH_RECONCILIATION_MISMATCH')


def test_equal_equity_account_substitution_is_rejected_after_all_public_hashes_are_recomputed():
    with held_series() as env:
        e=capture(env); account=e.staged.capture.accounts[0]
        changed=replace(account,balances=(replace(account.balances[0],total=D('95020'),settled=D('95020')),),
                        positions=(replace(account.positions[0],units=D('.5')),))
        assert changed.balances[0].total+changed.positions[0].units*changed.positions[0].price == env.state.equity_krw
        forged=rebound(e.staged,accounts=(changed,))
        refused(lambda:material(env,forged),'GUARD_CAPTURE_COLLECTION_REPLAY_MISMATCH')


def test_missing_normalized_fill_order_and_page_cannot_be_hidden_by_recomputed_claim_hashes():
    with held_series() as env:
        e=capture(env); account=e.staged.capture.accounts[0]
        for kind in ('fills','orders'):
            pages=tuple(replace(p,rows=(),page_sha256='') if p.kind==kind else p for p in account.pages)
            refused(lambda:material(env,rebound(e.staged,accounts=(replace(account,pages=pages),))),
                    'GUARD_CAPTURE_COLLECTION_REPLAY_MISMATCH')
        refused(lambda:material(env,rebound(e.staged,accounts=(replace(account,pages=account.pages[:-1]),))),
                'GUARD_CAPTURE_COLLECTION_REPLAY_MISMATCH')


def test_missing_original_fee_evidence_refuses_even_with_fresh_manifest_and_preview_claim_hashes():
    with series(START) as env:
        e=capture(env)
        refused(lambda:material(env,rebound(e.staged,fees=())), 'COLLECTOR_PER_TRADE_FEE_EVIDENCE_REQUIRED')


def test_missing_reordered_trailing_receipts_and_changed_route_params_scope_are_rejected():
    with held_series() as env:
        e=capture(env); receipts=e.staged.capture.receipts
        variants=(receipts[:-1], receipts+(receipts[-1],), (receipts[1],receipts[0],*receipts[2:]),
                  (replace(receipts[0],path='/v1/orders/open'),*receipts[1:]),
                  (replace(receipts[0],params=(('unexpected','1'),)),*receipts[1:]),
                  (replace(receipts[0],account_scope='other-synthetic'),*receipts[1:]))
        for changed in variants:
            refused(lambda:material(env,rebound(e.staged,receipts=changed)))


def test_exact_two_inner_clock_reads_original_request_and_completion_are_required():
    with held_series() as env:
        e=capture(env); s=e.staged
        for changed in (replace(s,collection_clock=()), replace(s,collection_clock=(*s.collection_clock,s.observed_at)),
                        replace(s,collection_clock=tuple(reversed(s.collection_clock))),
                        replace(s,collection_requested_at=s.collection_started_at+timedelta(seconds=1)),
                        replace(s,collection_clock=(s.collection_started_at,s.collection_completed_at-timedelta(milliseconds=1))),
                        replace(s,observed_at=s.capture.observed_at-timedelta(milliseconds=1))):
            refused(lambda:material(env,changed))
        refused(lambda:material(env,s,now=s.observed_at-timedelta(milliseconds=1)))
        refused(lambda:material(env,s,now=s.capture.observed_at+timedelta(seconds=31)))


def test_builder_rejects_changed_previous_preview_extrema_and_captured_endpoint_times():
    with held_series() as env:
        e=capture(env);s=e.staged
        refused(lambda:M.prepare_guard_capture_material(s,replace(env.state,sequence=99),now=s.observed_at))
        altered=replace(s.preview,interval=replace(s.preview.interval,minimum_equity_krw=D(1)))
        refused(lambda:material(env,replace(s,preview=altered)),'GUARD_CAPTURE_PREVIEW_REPLAY_MISMATCH')
        altered=replace(s.capture,observed_at=s.capture.observed_at-timedelta(milliseconds=1))
        refused(lambda:material(env,replace(s,capture=altered)))


def test_resource_limits_are_checked_before_receipt_decode_copy_or_replay():
    with held_series() as env:
        e=capture(env);s=e.staged;original=s.capture.receipts[0]
        oversized=replace(original,raw_body=b'0'*(M.MAX_CAPTURE_BODY_BYTES+1))
        largebody=b'0'*M.MAX_CAPTURE_BODY_BYTES
        count=M.MAX_CAPTURE_TOTAL_BYTES//M.MAX_CAPTURE_BODY_BYTES+1
        variants=((original,)*(M.MAX_CAPTURE_RECEIPTS+1), (oversized,),
                  tuple(replace(original,raw_body=largebody) for _ in range(count)))
        with patch.object(SourceReceipt,'decode',side_effect=AssertionError('admission must precede decode')), \
                patch.object(M,'deepcopy',side_effect=AssertionError('admission must precede copy')), \
                patch.object(M,'collect_upbit',side_effect=AssertionError('admission must precede replay')):
            for receipts in variants:
                changed=replace(s,capture=replace(s.capture,receipts=receipts))
                refused(lambda:material(env,changed),'GUARD_CAPTURE_RESOURCE_LIMIT')


def test_real_capture_gap_late_boundary_and_half_open_fill_fail_before_stage_or_material():
    with held_series() as env:
        refused(lambda:capture(env,capture_at=START+timedelta(seconds=31)), 'EVIDENCE_STALE_OR_FUTURE')
    start=at(26,21,59,40)
    with held_series(start) as env:
        refused(lambda:capture(env,capture_at=at(26,22,0,1)),'ACCOUNT_INTERVAL_BOUNDARY_MISSED')
    with series(START,exchange=FakeUpbit(cash='100000',orders=()),fees=(),realized=D(0),high=D('100000'),loss=D(0)) as env:
        buy=order('boundary-buy','bid',START+timedelta(seconds=5),'10000',[('boundary-fill','1','10000')],paid_fee='5')
        exchange=FakeUpbit(cash='89995',btc='1',orders=(buy,),ticker='10000')
        collection=env.capture(START+timedelta(seconds=5),exchange=exchange)
        fill,=build_observation(collection.bundle,now=collection.bundle.accounts[0].observed_at).fills
        refused(lambda:capture(env,events=(fill_event(10,fill),),opening='10000',exchange=exchange,step_ms=0),
                'CONTINUOUS_WATERMARK_REFUSED')


def test_actual_recorder_gap_disconnect_and_late_watermark_never_produce_material():
    with held_series() as env:
        def recorder():
            return ContinuousPriceRecorder(account_scope=SCOPE,stream_epoch='synthetic-i3a-broken',
                previous_state_digest=env.state.state_digest,start=START,
                opening_marks=(PriceMark(symbol='KRW-BTC',price=D('10050'),asof=START),),first_sequence=10)
        broken=recorder()
        refused(lambda:broken.append(mark_event(11,'10050',START+timedelta(seconds=1))), 'CONTINUOUS_EVENT_REFUSED')
        refused(lambda:capture(env,recorder=broken),'CONTINUOUS_EPOCH_BROKEN')
        broken=recorder();broken.disconnect()
        refused(lambda:capture(env,recorder=broken),'CONTINUOUS_EPOCH_BROKEN')
        broken=recorder()
        refused(lambda:broken.seal(end=START+timedelta(seconds=5),watermark_sequence=10,
            watermark_received_at=START+timedelta(seconds=31),watermark_source_sha256='a'*64),
            'CONTINUOUS_WATERMARK_REFUSED')


def test_material_and_guard_perform_no_durable_commit_controller_publication_or_extra_verification():
    with held_series(high=D('100045'),day_start=D('100045')) as env:
        initial=snapshot(env.home);head=env.head.value
        e=capture(env);before=snapshot(env.home)
        assert {name:raw for name,raw in before.items() if not name.startswith('execution-price-paths/')}==initial
        def forbidden(*args,**kwargs):raise AssertionError('no durable operation allowed')
        with ExitStack() as stack:
            stack.enter_context(patch.object(CheckpointStore,'commit',side_effect=forbidden))
            stack.enter_context(patch.object(Controller,'observe',side_effect=forbidden))
            stack.enter_context(patch.object(Controller,'reserve',side_effect=forbidden))
            stack.enter_context(patch.object(Controller,'dispatch',side_effect=forbidden))
            stack.enter_context(patch('execution_launch.continuous_guard_commit.commit_continuous_guard',side_effect=forbidden))
            value=material(env,e.staged)
            result=plan(env,value,now=e.staged.observed_at+timedelta(milliseconds=100))
        assert snapshot(env.home)==before and env.head.value==head and not env.head.commits
        assert len(e.verification_calls)==1 and not result.execution_ready
        files=[name for name in before if name.startswith('execution-price-paths/')]
        assert len(files)==1 and files[0].endswith(e.staged.path_sha256+'.json')
        refused(lambda:e.source(env.state,e.staged.observed_at),'CONTINUOUS_LIVE_RISK_INTEGRATION_REQUIRED')
        provider=ContinuousAccountProvider(source=lambda previous,now:value,store=env.store,trusted_head=env.head)
        refused(lambda:provider(e.staged.observed_at))


def test_self_consistent_different_raw_packet_is_distinct_audit_material_never_source_authority():
    with held_series() as env:
        e=capture(env); receipts=list(e.staged.capture.receipts)
        # Extra unconsumed JSON metadata is part of original bytes, yet does not
        # alter the collector's financial reconstruction. Rehash all public claims.
        for index,receipt in enumerate(receipts):
            if receipt.path=='/v1/accounts':
                body=receipt.decode();body[0]['synthetic_annotation']='different-source-claim'
                receipts[index]=receipt_body(receipt,body)
        altered=rebound(e.staged,receipts=receipts)
        original=material(env,e.staged);changed=material(env,altered)
        assert original.capture_material_sha256 != changed.capture_material_sha256
        assert original.valuation_inputs==changed.valuation_inputs
        assert not changed.source_authenticated and not changed.execution_ready
        clone=replace(changed)
        assert not clone.source_authenticated and not clone.execution_ready


def test_returned_material_is_detached_and_exact_arithmetic_ignores_ambient_precision():
    with held_series() as env:
        e=capture(env);ordinary=material(env,e.staged)
        with localcontext() as numeric:
            numeric.prec=6
            low=material(env,e.staged)
        assert ordinary==low
        original=deepcopy(e.staged)
        object.__setattr__(ordinary.account_capture.captured_accounts[0],'balances',())
        assert e.staged==original
        assert material(env,e.staged)==low


def test_new_epoch_and_sequence_gap_remain_guard_refusals_after_material_reconstruction():
    with held_series(high=D('100045'),day_start=D('100045')) as env:
        first=capture(env)
        initial=material(env,first.staged)
        checkpoint=plan(env,initial,now=first.staged.observed_at+timedelta(milliseconds=100)).proposed_checkpoint
        env.state=checkpoint.baseline
        for epoch,sequence,expected in (('synthetic-other-epoch',checkpoint.next_sequence,'GUARD_STREAM_EPOCH_CHANGED'),
                (checkpoint.stream_epoch,checkpoint.next_sequence+1,'GUARD_STREAM_SEQUENCE_GAP')):
            following=capture(env,stream_epoch=epoch,first_sequence=sequence)
            value=material(env,following.staged)
            assert not value.source_authenticated and not value.execution_ready
            refused(lambda:plan(env,value,now=following.staged.observed_at+timedelta(milliseconds=100),
                                checkpoint=checkpoint),expected)


def test_bool_for_decimal_normalized_account_is_not_equal_to_actual_typed_replay():
    with held_series() as env:
        e=capture(env);account=e.staged.capture.accounts[0]
        changed=replace(account,positions=(replace(account.positions[0],units=True),))
        # Python/dataclass equality alone would accept True == Decimal(1).
        assert changed == account and type(changed.positions[0].units) is bool
        forged=rebound(e.staged,accounts=(changed,))
        assert content_digest(forged.capture.accounts) != content_digest(e.staged.capture.accounts)
        refused(lambda:material(env,forged))


def test_normalized_path_decimal_and_hidden_attributes_refuse_before_copy_replay_or_decode():
    with held_series() as env:
        e=capture(env);s=e.staged;account=s.capture.accounts[0]
        fills=next(p for p in account.pages if p.kind=='fills')
        largepage=replace(fills,rows=(fills.rows[0],)*(M.MAX_CAPTURE_ROWS+1))
        pages=tuple(largepage if p.kind=='fills' else p for p in account.pages)
        normalized=replace(s,capture=replace(s.capture,accounts=(replace(account,pages=pages),)))
        event=mark_event(10,'10050',START+timedelta(seconds=1))
        largepath=replace(s.preview.path,events=(event,)*(M.MAX_CAPTURE_ROWS+1))
        path=replace(s,preview=replace(s.preview,path=largepath))
        huge=replace(s,anchor=replace(s.anchor,cash_krw=D('1E+1000000000')))
        calls=[]
        class CopyTrap:
            def __deepcopy__(self,memo):
                calls.append('copied')
                raise AssertionError('unreviewed attribute must never be copied')
        hidden=replace(s)
        object.__setattr__(hidden,'unreviewed_payload',CopyTrap())
        with patch.object(SourceReceipt,'decode',side_effect=AssertionError('preflight before decode')), \
                patch.object(M,'deepcopy',side_effect=AssertionError('preflight before copy')), \
                patch.object(M,'collect_upbit',side_effect=AssertionError('preflight before replay')):
            for changed in (normalized,path,huge,hidden):
                refused(lambda:material(env,changed))
        assert not calls
