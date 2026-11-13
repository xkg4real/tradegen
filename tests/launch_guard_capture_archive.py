"""I3b archive integration using invented GET replies, never production sources.

The actual collector, recorder, typed codec, BundleStore primary/backup/head and
historical material replay run unchanged. Coverage/owner claims in the shared
fixtures are explicitly synthetic. Fresh reader construction is tested here;
it is not an OS-process restart, actual API capture or native Windows run.
"""
from contextlib import contextmanager, ExitStack
from copy import deepcopy
from dataclasses import fields, is_dataclass, replace
from datetime import datetime, timedelta
from decimal import Decimal
import gc
import hashlib
import json
import re
import shutil
from unittest.mock import patch

from execution_accounts.baseline import state_json
from execution_accounts.baseline_store import CheckpointStore
from execution_accounts.continuous import (COVERAGE_CONTRACT, ContinuousPriceRecorder,
    PriceMark, VerifiedCoverage)
from execution_accounts.model import content_digest
from execution_accounts.provider import build_observation
from execution_control.controller import Controller
from execution_launch import account_interval as AI
from execution_launch import evidence_objects as EO
from execution_launch import guard_capture_archive as A
from execution_launch import guard_capture_format as F
from execution_launch import guard_capture_material as M
from execution_launch import research_bundle_format as BF
from tests import launch_guard_capture_material as I
from tests import launch_research_bundle_store as B
from tests.accounts_continuous import held_series, mark_event, fill_event
from tests.launch_account_interval import ANCHOR, COVERAGE, SCOPE, FakeUpbit, at, order, series

D = Decimal


def limits(**changes):
    """Room for typed packet metadata; still a finite private temporary store."""
    return B.limits(format_limits=BF.BundleLimits(max_manifest_bytes=65536, max_files=2048,
        max_file_bytes=1024*1024, max_total_bytes=8*1024*1024, max_candidates=8, max_name_bytes=256),
        object_limits=EO.ObjectLimits(chunk_bytes=65536, max_payload_bytes=1024*1024,
            max_chunks=16, max_manifest_bytes=65536),
        primary_budget=EO.StoreBudget(max_bytes=32*1024*1024, max_objects=8192),
        backup_budget=EO.StoreBudget(max_bytes=32*1024*1024, max_objects=8192), **changes)


@contextmanager
def fixture(*, held=False, start=I.START, env_options=None, capture_options=None,
            storage_limits=None, provision=True, initialize=True):
    # Keep the account temporary home active throughout collect/archive/replay.
    # Bundle roots remain separate temporary directories, never inside that home.
    with B.fixture(storage_limits=storage_limits or limits(), provision=provision,
                   initialize=initialize) as store:
        with (held_series if held else series)(start, **(env_options or {})) as env:
            captured=I.capture(env, **(capture_options or {}))
            yield store,env,captured


def refused(call, expected=None):
    try:
        call()
    except ValueError as exc:
        code=str(exc)
        assert re.fullmatch(r'[A-Z][A-Z0-9_]+',code), 'private or non-code diagnostic'
        if expected is not None:
            assert code in ((expected,) if isinstance(expected,str) else expected),(code,expected)
        return code
    raise AssertionError('expected actual archive/evidence refusal')


def typed_equal(actual, expected):
    """Decimals retain representation; datetime timezone canonicalization is allowed."""
    assert type(actual) is type(expected),(type(actual),type(expected))
    if type(actual) is D:
        assert actual.as_tuple()==expected.as_tuple()
    elif type(actual) is datetime:
        assert actual==expected and actual.utcoffset() is not None
    elif is_dataclass(actual):
        assert {f.name for f in fields(actual)}=={f.name for f in fields(expected)}
        for field in fields(actual):
            typed_equal(getattr(actual,field.name),getattr(expected,field.name))
    elif type(actual) is tuple:
        assert len(actual)==len(expected)
        for left,right in zip(actual,expected): typed_equal(left,right)
    else:
        assert actual==expected


def inert(value):
    names=(('source_authenticated','execution_ready') if type(value) is M.GuardCaptureMaterial else
           ('source_authenticated','current_freshness_verified','guard_committed','execution_ready'))
    for name in names:
        assert getattr(value,name) is False,name
    for name in ('current_use_eligible','research_selection_ready','order_authorized'):
        if hasattr(value,name): assert getattr(value,name) is False,name


def archive(e,env,staged):
    result=A.archive_guard_capture_packet(e.store,staged,env.state)
    inert(result)
    assert result.backup_verified is True
    return result


def replay(e,env,receipt):
    result=A.replay_guard_capture_archive(e.reopen(),receipt.archive_digest,
        expected_previous_state_sha256=env.state.state_digest)
    inert(result); inert(result.receipt); inert(result.material)
    assert result.historical_replay is True
    return result


def test_actual_flat_capture_publishes_full_raw_graph_then_fresh_reader_replays_real_material():
    with fixture(env_options={'high':D('100090'),'day_start':D('100090'),'loss':D(0)}) as (e,env,c):
        expected=M.prepare_guard_capture_material(c.staged,env.state,now=c.staged.observed_at)
        before=I.snapshot(env.home);head=env.head.value
        receipt=archive(e,env,c.staged)
        raw=e.reopen().read_raw(receipt.archive_digest,require_backup=True)
        assert raw.manifest.kind=='RAW_ARCHIVED' and raw.manifest.inventory_complete
        assert raw.manifest.expected_candidates is None
        assert all(row.role=='other_input' and row.source_name is None and row.study_id is None
                   and row.required for row in raw.manifest.files)
        assert raw.manifest.run_id==raw.manifest.attempt_id=='capture-'+receipt.packet_sha256
        assert raw.manifest.revision_id=='capture-packet-v1'
        assert dict(raw.files)['baseline']==state_json(env.state).encode('utf-8')
        assert set(raw.files)=={'baseline','packet'}|{f'receipt-{i:06d}' for i in range(len(c.originals))}
        assert receipt.catalog_head==(e.store._catalog().sequence,e.store.head.read())
        original=deepcopy(c.staged);del c;gc.collect()
        restored=A.read_guard_capture_packet(e.reopen(),receipt.archive_digest,
            expected_previous_state_sha256=env.state.state_digest)
        inert(restored);typed_equal(restored.staged,original);typed_equal(restored.previous,env.state)
        assert restored.staged is not original and restored.previous is not env.state
        audited=replay(e,env,receipt)
        assert audited.capture_material_sha256==expected.capture_material_sha256
        typed_equal(audited.material,expected)
        assert I.snapshot(env.home)==before and env.head.value==head and not env.head.commits


def test_actual_held_path_extrema_survive_archive_and_drive_existing_guard_arithmetic():
    events=(mark_event(10,'10200',I.START+timedelta(seconds=1)),
            mark_event(11,'9900',I.START+timedelta(seconds=2)),
            mark_event(12,'10050',I.START+timedelta(seconds=3)))
    with fixture(held=True,env_options={'high':D('100045'),'day_start':D('100045')},
                 capture_options={'events':events}) as (e,env,c):
        audited=replay(e,env,archive(e,env,c.staged))
        assert audited.material.path.events==events
        assert audited.material.interval.equity_krw==D('100045')
        assert audited.material.interval.minimum_equity_krw==D('99895')
        result=I.plan(env,audited.material,now=c.staged.observed_at)
        assert result.proposed_checkpoint.permanently_halted and not result.execution_ready
        halt=next(row for row in result.required_records if row.kind=='permanent_floor_halt')
        assert halt.source_at==I.START+timedelta(seconds=2) and halt.floor_krw==D('100195')


def test_partial_fill_fee_locked_cash_and_remaining_order_survive_full_archive():
    with B.fixture(storage_limits=limits()) as e, series(I.START,
            exchange=FakeUpbit(cash='100000',orders=()),fees=(),realized=D(0),
            high=D('100000'),loss=D(0)) as env:
        buy=order('partial-buy','bid',I.START+timedelta(seconds=1),'10000',
                  [('partial-fill','1','10000')],paid_fee='5')
        buy.update(state='wait',volume='2',remaining_volume='1',locked='10005')
        exchange=FakeUpbit(cash='79990',btc='1',orders=(buy,),ticker='10000')
        exchange.balances[0]['locked']='10005'
        collection=env.capture(I.START+timedelta(seconds=5),exchange=exchange)
        fill,=build_observation(collection.bundle,now=collection.bundle.accounts[0].observed_at).fills
        c=I.capture(env,events=(fill_event(10,fill),),exchange=exchange,opening='10000',fees=())
        audited=replay(e,env,archive(e,env,c.staged))
        assert audited.material.valuation_inputs.interval_fills==(fill,) and fill.fee_amount==D(5)
        account=audited.material.account_capture.captured_accounts[0]
        orders=next(page.rows for page in account.pages if page.kind=='orders')
        assert len(orders)==1 and orders[0].status=='partial'
        assert orders[0].remaining_quantity==D(1) and orders[0].reserved_cash==D('10005')
        assert audited.material.interval.equity_krw==D('99995')


def test_2200_archive_preserves_later_capture_and_reconstructed_boundary_as_distinct_accounts():
    start=at(26,21,59,40)
    with B.fixture(storage_limits=limits()) as e, held_series(start,
            high=D('100045'),day_start=D('100045')) as env:
        env.exchange.ticker='10300'
        c=I.capture(env,events=(mark_event(10,'10080',start+timedelta(seconds=15)),),
                    capture_at=at(26,21,59,59),step_ms=200)
        result=replay(e,env,archive(e,env,c.staged))
        captured=result.material.account_capture.captured_accounts[0]
        endpoint=result.material.account_capture.endpoint_accounts[0]
        assert captured.observed_at>at(26,22)==endpoint.observed_at
        assert captured.positions[0].price==D('10300') and captured.positions[0].asof>at(26,22)
        assert endpoint.positions[0].price==D('10080') and endpoint.positions[0].asof==at(26,22)
        assert result.material.interval.equity_krw==D('100075')


def test_midnight_archive_recreates_original_collector_baseline_without_exporting_it():
    start=at(27,23,59,40)
    with B.fixture(storage_limits=limits()) as e, held_series(start,
            high=D('100045'),day_start=D('100045'),previous=D(0)) as env:
        env.exchange.ticker='10300'
        c=I.capture(env,events=(mark_event(10,'10080',start+timedelta(seconds=15)),),
                    capture_at=at(27,23,59,59),step_ms=200)
        receipt=archive(e,env,c.staged)
        packet=A.read_guard_capture_packet(e.reopen(),receipt.archive_digest,
            expected_previous_state_sha256=env.state.state_digest)
        assert packet.staged.collection_baseline_sha256==c.staged.collection_baseline_sha256
        assert not hasattr(packet.staged,'collection_baseline')
        audited=replay(e,env,receipt)
        assert audited.material.account_capture.captured_accounts[0].observed_at>at(28,0)
        assert audited.material.account_capture.endpoint_accounts[0].observed_at==at(28,0)
        result=I.plan(env,audited.material,now=c.staged.observed_at,daily_stopped=True)
        assert result.proposed_checkpoint.baseline.day_start_equity==D('100075')
        assert result.proposed_checkpoint.baseline.high_watermark==D('100075')


def test_raw_whitespace_number_spelling_decimal_scale_and_duplicate_response_positions_are_lossless():
    class SpacedExchange(FakeUpbit):
        def fetch(self,path,params):
            receipt=super().fetch(path,params)
            raw=(b' \n'+json.dumps(json.loads(receipt.raw_body),indent=2).encode('utf-8')+b'\n ')
            return replace(receipt,raw_body=raw,sha256=hashlib.sha256(raw).hexdigest())
    with B.fixture(storage_limits=limits()) as e, held_series() as env:
        exchange=SpacedExchange(cash='89995.00',btc='1.000',orders=tuple(env.exchange.orders),ticker='10050.000')
        c=I.capture(env,exchange=exchange,opening='10050.000')
        receipt=archive(e,env,c.staged)
        raw=e.reopen().read_raw(receipt.archive_digest,require_backup=True)
        packet=A.read_guard_capture_packet(e.reopen(),receipt.archive_digest,
            expected_previous_state_sha256=env.state.state_digest)
        for index,original in enumerate(c.originals):
            assert raw.files[f'receipt-{index:06d}']==original.raw_body
            assert original.raw_body.startswith(b' \n') and original.raw_body.endswith(b'\n ')
        typed_equal(packet.staged,c.staged)
        position=packet.staged.capture.accounts[0].positions[0]
        assert position.price.as_tuple()==D('10050.000').as_tuple()
        assert any(left.raw_body==right.raw_body for i,left in enumerate(c.originals)
                   for right in c.originals[i+1:])
        assert len(packet.staged.capture.receipts)==len(c.originals)
        assert len([name for name in raw.files if name.startswith('receipt-')])==len(c.originals)
        assert replay(e,env,receipt).capture_material_sha256==I.material(env,c.staged).capture_material_sha256


def test_outer_request_two_inner_clocks_and_preview_time_remain_original_after_restart_read():
    with fixture(held=True) as (e,env,c):
        receipt=archive(e,env,c.staged)
        p=A.read_guard_capture_packet(e.reopen(),receipt.archive_digest,
            expected_previous_state_sha256=env.state.state_digest)
        assert p.staged.collection_requested_at==c.clock.values[0]
        assert p.staged.collection_clock==(c.clock.values[1],c.clock.values[-2])
        assert p.staged.collection_started_at<p.staged.first_received_at
        assert p.staged.collection_completed_at==p.staged.capture.observed_at<p.staged.observed_at
        assert p.staged.observed_at==receipt.observed_at==c.clock.values[-1]
        result=replay(e,env,receipt)
        assert result.historical_evaluation_at==c.staged.observed_at
        assert len(c.verification_calls)==1
        assert result.material.coverage.verified_at==c.staged.preview.coverage.verified_at


def test_old_archive_is_a_historical_audit_and_actual_later_freshness_still_refuses():
    with fixture(held=True) as (e,env,c):
        receipt=archive(e,env,c.staged)
        expected=I.material(env,c.staged)
        p=A.read_guard_capture_packet(e.reopen(),receipt.archive_digest,
            expected_previous_state_sha256=env.state.state_digest)
        late=c.staged.observed_at+timedelta(hours=7)
        refused(lambda:M.prepare_guard_capture_material(p.staged,p.previous,now=late),
                'GUARD_CAPTURE_CLOCK_BINDING_INVALID')
        audited=replay(e,env,receipt)
        assert audited.historical_evaluation_at==c.staged.observed_at and audited.historical_evaluation_at<late
        assert audited.capture_material_sha256==expected.capture_material_sha256
        assert len(c.verification_calls)==1 and audited.material.coverage.verified_at<late


def test_rehashed_normalized_account_and_rehashed_source_substitution_remain_archived_but_fail_audit():
    with fixture(held=True) as (e,env,c):
        account=c.staged.capture.accounts[0]
        changed=replace(account,balances=(replace(account.balances[0],total=D('95020'),settled=D('95020')),),
                        positions=(replace(account.positions[0],units=D('.5')),))
        normalized=I.rebound(c.staged,accounts=(changed,))
        receipts=[]
        for row in c.staged.capture.receipts:
            if row.path=='/v1/accounts':
                body=row.decode();body[0]['balance']='89996';row=I.receipt_body(row,body)
            receipts.append(row)
        source=I.rebound(c.staged,receipts=receipts)
        for forged,code in ((normalized,'GUARD_CAPTURE_COLLECTION_REPLAY_MISMATCH'),
                            (source,'CASH_RECONCILIATION_MISMATCH')):
            receipt=archive(e,env,forged);before=B.files(e.base)
            refused(lambda:replay(e,env,receipt),code)
            assert B.files(e.base)==before
            retained=A.read_guard_capture_packet(e.reopen(),receipt.archive_digest,
                expected_previous_state_sha256=env.state.state_digest)
            typed_equal(retained.staged,forged)
            assert e.reopen().read_raw(receipt.archive_digest,require_backup=True).manifest.kind=='RAW_ARCHIVED'


def test_archive_binding_rejects_wrong_expected_previous_and_unrelated_valid_raw_wrapper():
    with fixture() as (e,env,c):
        receipt=archive(e,env,c.staged);before=B.files(e.base)
        refused(lambda:A.read_guard_capture_packet(e.reopen(),receipt.archive_digest,
            expected_previous_state_sha256='0'*64),'CAPTURE_BASELINE_MISMATCH')
        assert B.files(e.base)==before
        original=e.store.read_raw(receipt.archive_digest,require_backup=True)
        variants=(replace(original.manifest,run_id='unrelated-run'),
                  replace(original.manifest,attempt_id='unrelated-attempt',revision_id='different-revision'),
                  replace(original.manifest,run_id='incomplete-run',inventory_complete=False))
        for manifest in variants:
            raw=BF.raw_archive_bytes(manifest,limits=e.store.limits.format_limits)
            stored=e.store.archive_raw(raw,dict(original.files))
            before=B.files(e.base)
            refused(lambda:A.read_guard_capture_packet(e.reopen(),stored.bundle_digest,
                expected_previous_state_sha256=env.state.state_digest))
            assert B.files(e.base)==before and e.store.read_raw(stored.bundle_digest).backup_verified


def test_exact_retry_is_read_only_and_new_raw_spelling_produces_distinct_immutable_archive():
    with fixture(held=True) as (e,env,c):
        first=archive(e,env,c.staged);before=B.files(e.base)
        repeated=A.archive_guard_capture_packet(e.reopen(),deepcopy(c.staged),deepcopy(env.state))
        assert repeated==first and B.files(e.base)==before
        altered=[]
        for row in c.staged.capture.receipts:
            raw=b'\n'+row.raw_body+b' '
            altered.append(replace(row,raw_body=raw,sha256=hashlib.sha256(raw).hexdigest()))
        second=archive(e,env,I.rebound(c.staged,receipts=altered))
        assert second.packet_sha256!=first.packet_sha256 and second.archive_digest!=first.archive_digest
        assert replay(e,env,second).capture_material_sha256!=replay(e,env,first).capture_material_sha256
        assert e.store.read_raw(first.archive_digest).files['receipt-000000']==c.originals[0].raw_body


def test_backup_damage_after_success_blocks_read_and_historical_replay_without_repair():
    with fixture() as (e,env,c):
        receipt=archive(e,env,c.staged)
        original=e.store.read_raw(receipt.archive_digest).files['packet']
        target=B.chunk_path(e.store,original,backup=True)
        target.write_bytes(b'X'*target.stat().st_size);before=B.files(e.base)
        assert e.store.inspect(receipt.archive_digest).backup_verified  # historical catalog fact only
        refused(lambda:A.read_guard_capture_packet(e.reopen(),receipt.archive_digest,
            expected_previous_state_sha256=env.state.state_digest),'BUNDLE_STORE_OBJECT_REFUSED')
        refused(lambda:replay(e,env,receipt),'BUNDLE_STORE_OBJECT_REFUSED')
        assert B.files(e.base)==before


def test_primary_only_publication_is_not_a_packet_and_exact_retry_completes_only_backup():
    with fixture() as (e,env,c):
        real=EO.EvidenceObjectStore.stage
        def fail_backup(self,*args,**kwargs):
            if self.root.is_relative_to(e.roots.backup_root):
                raise EO.EvidenceObjectError('EVIDENCE_OBJECT_IO_REFUSED')
            return real(self,*args,**kwargs)
        with patch.object(EO.EvidenceObjectStore,'stage',fail_backup):
            refused(lambda:archive(e,env,c.staged),'BUNDLE_STORE_IO_REFUSED')
        digest,=e.store._catalog().entries
        assert not e.store.inspect(digest).backup_verified
        raw=e.store.read_raw(digest,require_backup=False)
        assert raw.files['receipt-000000']==c.originals[0].raw_body
        refused(lambda:A.read_guard_capture_packet(e.reopen(),digest,
            expected_previous_state_sha256=env.state.state_digest),'CAPTURE_ARCHIVE_BACKED_RAW_REQUIRED')
        touched=[]
        def watch(self,*args,**kwargs):
            touched.append(self.root);return real(self,*args,**kwargs)
        with patch.object(EO.EvidenceObjectStore,'stage',watch):
            result=A.archive_guard_capture_packet(e.reopen(),c.staged,env.state)
        assert result.archive_digest==digest and result.backup_verified
        assert touched and all(path.is_relative_to(e.roots.backup_root) for path in touched)
        assert e.store._catalog().sequence==2
        assert replay(e,env,result).material.interval==c.staged.preview.interval


def test_partial_object_and_head_cas_failure_preserve_unpublished_bytes_without_auto_adoption():
    for failure in ('partial-object','head-cas'):
        with fixture() as (e,env,c):
            real=EO.EvidenceObjectStore._publish;interrupted=[False]
            def partial(self,kind,value):
                if not interrupted[0]:
                    interrupted[0]=True
                    (self.root/'objects'/'pending.blob').write_bytes(value)
                    (self.root/'objects'/(EO._object_digest(kind,value)+'.blob')).write_bytes(value[:1])
                    raise EO.EvidenceObjectError('EVIDENCE_OBJECT_IO_REFUSED')
                return real(self,kind,value)
            with (patch.object(EO.EvidenceObjectStore,'_publish',partial) if failure=='partial-object'
                  else patch.object(e.store.head,'compare_and_set',return_value=False)):
                refused(lambda:archive(e,env,c.staged),
                    'BUNDLE_STORE_IO_REFUSED' if failure=='partial-object' else 'BUNDLE_STORE_HEAD_UPDATE_REFUSED')
            before=B.files(e.base)
            assert e.store.head.read()==e.store.genesis_digest
            refused(lambda:A.archive_guard_capture_packet(e.reopen(),c.staged,env.state),
                'BUNDLE_STORE_OBJECT_REFUSED' if failure=='partial-object' else 'BUNDLE_STORE_HEAD_MISMATCH')
            assert B.files(e.base)==before


def test_one_sided_head_or_catalog_rollback_never_adopts_archived_packet_as_current_baseline():
    for side in ('head','catalog'):
        with fixture() as (e,env,c):
            target=e.store.head._dir/'head.json' if side=='head' else e.roots.sealed_root/'catalog.jsonl'
            initial=target.read_bytes()
            receipt=archive(e,env,c.staged)
            target.write_bytes(initial);before=B.files(e.base);baseline_before=I.snapshot(env.home)
            refused(lambda:A.read_guard_capture_packet(e.reopen(),receipt.archive_digest,
                expected_previous_state_sha256=env.state.state_digest),'BUNDLE_STORE_HEAD_MISMATCH')
            assert B.files(e.base)==before and I.snapshot(env.home)==baseline_before and not env.head.commits


def test_original_store_root_replacement_is_refused_despite_identical_copied_files():
    with fixture() as (e,env,c):
        receipt=archive(e,env,c.staged)
        old=e.base/'original-primary';e.roots.sealed_root.rename(old)
        shutil.copytree(old,e.roots.sealed_root);before=B.files(e.base)
        refused(lambda:A.read_guard_capture_packet(e.store,receipt.archive_digest,
            expected_previous_state_sha256=env.state.state_digest),'BUNDLE_STORE_ROOT_CHANGED')
        assert B.files(e.base)==before


def test_unprovisioned_or_uninitialized_storage_never_seeds_from_packet_predecessor():
    for provision in (False,True):
        with fixture(provision=provision,initialize=False) as (e,env,c):
            before=B.files(e.base);baseline_before=I.snapshot(env.home)
            refused(lambda:archive(e,env,c.staged))
            assert B.files(e.base)==before and I.snapshot(env.home)==baseline_before
            assert not e.store.head._dir.exists() and not env.head.commits


def test_storage_resource_admission_retains_stage_and_does_not_publish_partial_capture():
    with fixture(storage_limits=limits(max_catalog_records=1)) as (e,env,c):
        before=B.files(e.base);original=deepcopy(c.staged)
        refused(lambda:archive(e,env,c.staged),'BUNDLE_STORE_RESOURCE_LIMIT')
        assert B.files(e.base)==before
        typed_equal(c.staged,original)
        assert e.store._catalog().sequence==0 and e.store.head.read()==e.store.genesis_digest


def test_read_manifest_budget_refuses_before_full_graph_decode_or_historical_replay():
    with fixture() as (e,env,c):
        receipt=archive(e,env,c.staged);before=B.files(e.base)
        def forbidden(*args,**kwargs):raise AssertionError('full payload allocation preceded admission')
        with patch.object(B.S.BundleStore,'read_raw',side_effect=forbidden), \
             patch.object(F,'parse_capture_archive',side_effect=forbidden), \
             patch.object(M,'prepare_guard_capture_material',side_effect=forbidden):
            refused(lambda:A.replay_guard_capture_archive(e.reopen(),receipt.archive_digest,
                expected_previous_state_sha256=env.state.state_digest,
                limits=F.CaptureFormatLimits(max_packet_bytes=16)),'CAPTURE_ARCHIVE_RESOURCE_LIMIT')
        assert B.files(e.base)==before


def test_backup_change_after_actual_material_replay_blocks_final_archive_observation():
    with fixture(held=True) as (e,env,c):
        receipt=archive(e,env,c.staged)
        packet=e.store.read_raw(receipt.archive_digest).files['packet']
        target=B.chunk_path(e.store,packet,backup=True)
        real=M.prepare_guard_capture_material;calls=[]
        def actual_then_damage(*args,**kwargs):
            result=real(*args,**kwargs);calls.append(result.capture_material_sha256)
            target.write_bytes(b'X'*target.stat().st_size)
            return result
        with patch.object(M,'prepare_guard_capture_material',actual_then_damage):
            refused(lambda:replay(e,env,receipt),'BUNDLE_STORE_OBJECT_REFUSED')
        assert len(calls)==1
        assert target.read_bytes()==b'X'*target.stat().st_size


def test_archived_material_never_commits_guard_or_account_publishes_controller_or_refreshes_coverage():
    with fixture(held=True) as (e,env,c):
        before=I.snapshot(env.home);head=env.head.value
        def forbidden(*args,**kwargs):raise AssertionError('unexpected operational side effect')
        with ExitStack() as patches:
            patches.enter_context(patch.object(CheckpointStore,'commit',side_effect=forbidden))
            for method in ('observe','reserve','dispatch'):
                patches.enter_context(patch.object(Controller,method,side_effect=forbidden))
            patches.enter_context(patch('execution_launch.continuous_guard_commit.commit_continuous_guard',
                                       side_effect=forbidden))
            audited=replay(e,env,archive(e,env,c.staged))
        assert I.snapshot(env.home)==before and env.head.value==head and not env.head.commits
        assert len(c.verification_calls)==1
        for value in (audited,audited.receipt,audited.material):inert(value)
        refused(lambda:c.source(env.state,c.staged.observed_at),'CONTINUOUS_LIVE_RISK_INTEGRATION_REQUIRED')
        public=repr(audited)+repr(audited.receipt)
        assert SCOPE not in public and str(e.base) not in public and str(env.home) not in public
        assert c.originals[0].raw_body.decode('utf-8') not in public


def wrapper_inputs(env):
    """Real source/recorder with a plainly synthetic coverage claim for the wrapper."""
    clock=I.TraceClock(env.state.asof+timedelta(seconds=5),100)
    env.exchange.clock=clock
    recorder=ContinuousPriceRecorder(account_scope=SCOPE,stream_epoch='synthetic-i3b-wrapper',
        previous_state_digest=env.state.state_digest,start=env.state.asof,
        opening_marks=(PriceMark(symbol='KRW-BTC',price=D('10050'),asof=env.state.asof),),first_sequence=10)
    calls=[]
    def path_source(previous,capture,end):
        assert previous==env.state
        return recorder.seal(end=end,watermark_sequence=10,watermark_received_at=capture.observed_at,
                             watermark_source_sha256='a'*64)
    def coverage(request,path):
        calls.append(request)
        return VerifiedCoverage(request_sha256=content_digest(request),contract=COVERAGE_CONTRACT,
            authority_sha256='b'*64,source_proof_sha256='c'*64,verified_at=path.watermark_received_at)
    source=AI.ContinuousUpbitCandidateSource(path_source=path_source,coverage_verifier=coverage,archive_root=env.home)
    return source,clock,calls


def test_actual_collect_archive_wrapper_uses_returned_archive_digest_and_freshly_decoded_material():
    with B.fixture(storage_limits=limits()) as e, held_series() as env:
        source,clock,calls=wrapper_inputs(env)
        observed=[];real=A.replay_guard_capture_archive
        def watch(store,digest,**kwargs):
            observed.append(digest)
            # Poison the retained mutable Python object after actual archive readback.
            # A wrapper reusing it instead of decoding the archive cannot pass.
            object.__setattr__(source.latest().capture,'accounts',())
            return real(store,digest,**kwargs)
        with patch.object(A,'replay_guard_capture_archive',watch):
            result=A.collect_archive_guard_capture(source,env.exchange,store=e.store,previous=env.state,
                anchor=ANCHOR,coverage=COVERAGE,clock=clock,trade_fees=env.fees)
        assert result.audit_error_code is None and result.replay is not None
        assert observed==[result.receipt.archive_digest] and result.replay.receipt.archive_digest==observed[0]
        assert result.replay.material.account_capture.captured_accounts and not source.latest().capture.accounts
        assert len(calls)==1
        inert(result);inert(result.receipt);inert(result.replay)


def test_wrapper_reports_actual_semantic_audit_refusal_with_preserved_raw_identifier():
    with B.fixture(storage_limits=limits()) as e, held_series() as env:
        source,clock,calls=wrapper_inputs(env)
        real=AI.ContinuousUpbitCandidateSource.collect
        def collect_then_corrupt(self,*args,**kwargs):
            staged=real(self,*args,**kwargs)
            account=staged.capture.accounts[0]
            changed=replace(account,balances=(replace(account.balances[0],total=D('95020'),settled=D('95020')),),
                positions=(replace(account.positions[0],units=D('.5')),))
            return I.rebound(staged,accounts=(changed,))
        # Explicit negative injection after a genuine collector; no fake positive
        # authentication/evaluation result is supplied to the production adapter.
        with patch.object(AI.ContinuousUpbitCandidateSource,'collect',collect_then_corrupt):
            result=A.collect_archive_guard_capture(source,env.exchange,store=e.store,previous=env.state,
                anchor=ANCHOR,coverage=COVERAGE,clock=clock,trade_fees=env.fees)
        assert result.replay is None and result.audit_error_code=='GUARD_CAPTURE_COLLECTION_REPLAY_MISMATCH'
        inert(result);inert(result.receipt)
        stored=e.reopen().read_raw(result.receipt.archive_digest,require_backup=True)
        assert stored.manifest.kind=='RAW_ARCHIVED' and len(calls)==1
        retained=A.read_guard_capture_packet(e.reopen(),result.receipt.archive_digest,
            expected_previous_state_sha256=env.state.state_digest)
        assert retained.staged.capture.accounts[0].positions[0].units==D('.5')
