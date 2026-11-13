"""Actual BundleStore/read graph over invented records, not actual HTTP issuance.

The pure COLLECTED label below is intentionally a caller claim. Only the separate
integration suite exercises the genuine E1/collector wrapper. No keys or API here.
"""
from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import threading
from unittest.mock import patch

from execution_launch import upbit_read_archive as A, upbit_read_format as F
from execution_launch import research_bundle_store as S
from tests import launch_research_bundle_store as B

NOW = datetime(2031, 1, 1, tzinfo=timezone.utc)
LIMITS = F.ReadBatchLimits(max_calls=4,max_attempts=8,max_records=26,max_body_bytes=4096,
    max_total_body_bytes=8192,max_record_bytes=8192,max_total_record_bytes=131072)


def refused(call, *codes):
    try: call()
    except (A.ReadBatchArchiveError,F.ReadBatchFormatError,S.BundleStoreError) as exc:
        if codes: assert str(exc) in codes,(str(exc),codes)
        return str(exc)
    raise AssertionError('invalid archive accepted')


def opener(*,batch='archive-unit',started=NOW,limits=LIMITS):
    return F.ReadBatchRecord(schema_version=1,batch_id=batch,ordinal=0,previous_archive_digest=None,
        kind='OPEN',body=dict(account_scope='synthetic',started_at=started,limits_sha256=F.limits_digest(limits),
            anchor_sha256='1'*64,coverage_sha256='2'*64,baseline_sha256='3'*64,trade_fees_sha256='4'*64))


def publish(store, record, body=None, *, require_new=False):
    raw,payloads,digest=A._manifest(store,record,body,LIMITS)
    store.archive_raw(raw,payloads,require_new=require_new)
    retained=store.read_raw(digest,require_backup=True)
    assert retained.manifest_bytes==raw and dict(retained.files)==payloads
    return digest


def trace(store, *,raw=b' []\n',batch='archive-unit',close=True,retry=False,mutate=None):
    records,digests=[],[]
    def add(kind,body,payload=None):
        record=F.ReadBatchRecord(schema_version=1,batch_id=batch,ordinal=len(records),
            previous_archive_digest=digests[-1] if digests else None,kind=kind,body=body)
        if mutate is not None: record,payload=mutate(record,payload)
        digest=publish(store,record,payload,require_new=kind=='OPEN')
        records.append(record);digests.append(digest)
    add('OPEN',dict(opener(batch=batch).body))
    add('FETCH_BEGIN',dict(call_ordinal=1,path='/v1/accounts',params=(),requested_at=NOW))
    for number in range(1,3 if retry else 2):
        base=dict(call_ordinal=1,attempt=number,path='/v1/accounts',params=(),observed_at=NOW,clock_status='OK')
        add('ATTEMPT',base|dict(phase='BEFORE_SEND',status_code=None,body_status='NOT_RECEIVED',
            body_bytes=None,body_sha256=None,error_code=None))
        add('ATTEMPT',base|dict(phase='RESPONSE',status_code=503 if retry and number==1 else 200,
            body_status='PRESENT',body_bytes=len(raw),body_sha256=hashlib.sha256(raw).hexdigest(),error_code=None),raw)
    add('FETCH_END',dict(call_ordinal=1,status='RETURNED',error_code=None,receipt=dict(path='/v1/accounts',
        params=(),account_scope='synthetic',received_at=NOW,server_time=NOW,sha256=hashlib.sha256(raw).hexdigest())))
    if close:
        add('CLOSE',dict(status='COLLECTED',error_code=None,collection_manifest_sha256='c'*64,
            records=tuple(enumerate(digests)),calls=1,attempts=2 if retry else 1,finished_at=NOW,clock_status='OK'))
    return tuple(records),tuple(digests)


def test_actual_reader_preserves_backed_original_bytes_and_inert_collected_claim():
    with B.fixture() as e:
        raw=b' {"number": 1.00, "repeated": [0, 0]}\n'
        records,digests=trace(e.store,raw=raw)
        result=A.read_upbit_read_batch(e.reopen(),digests[-1],limits=LIMITS)
        assert result.records==records and result.payloads[3]==raw
        assert result.status=='COLLECTED' and result.final_archive_digest==digests[-1]
        assert not result.source_authenticated and not result.coverage_verified and not result.execution_ready
        assert not hasattr(result,'collection')


def test_empty_response_and_duplicate_retry_response_positions_remain_distinct():
    with B.fixture() as e:
        records,digests=trace(e.store,raw=b'',retry=True)
        result=A.read_upbit_read_batch(e.store,digests[-1],limits=LIMITS)
        assert tuple(result.payloads)==(3,5) and result.payloads[3]==result.payloads[5]==b''
        assert digests[3]!=digests[5] and len(records)==8


def test_partial_trace_reader_reports_incomplete_without_inventing_final_inventory():
    with B.fixture() as e:
        records,digests=trace(e.store,close=False)
        for index in (0,1,2,3,4):
            result=A.read_upbit_read_batch(e.store,digests[index],limits=LIMITS)
            assert result.status=='INCOMPLETE' and result.final_archive_digest is None
            assert result.records==records[:index+1]


def test_wrong_final_inventory_missing_parent_and_reordered_chain_are_refused():
    for choice in ('inventory','missing','ordinal'):
        with B.fixture() as e:
            def mutate(record,payload):
                if record.kind=='CLOSE' and choice=='inventory':
                    body=dict(record.body);items=list(body['records']);items[1]=(1,'f'*64);body['records']=tuple(items)
                    record=replace(record,body=body)
                elif record.kind=='FETCH_END' and choice=='missing':
                    record=replace(record,previous_archive_digest='f'*64)
                elif record.kind=='FETCH_BEGIN' and choice=='ordinal':
                    record=replace(record,ordinal=20)
                return record,payload
            _,digests=trace(e.store,mutate=mutate)
            refused(lambda:A.read_upbit_read_batch(e.store,digests[-1],limits=LIMITS),'READ_BATCH_CHAIN_INVALID')


def test_changed_payload_or_backup_bytes_are_not_replaced_by_manifest_hash_claim():
    for backup in (False,True):
        with B.fixture() as e:
            _,digests=trace(e.store,raw=b'original-private-response')
            target=B.chunk_path(e.store,b'original-private-response',backup)
            target.write_bytes(b'changed-private-response')
            refused(lambda:A.read_upbit_read_batch(e.store,digests[-1],limits=LIMITS),'READ_BATCH_ARCHIVE_REFUSED')


def test_arbitrary_large_foreign_bundle_is_refused_before_any_full_graph_materialization():
    with B.fixture() as e:
        m,raw,payloads=B.raw_archive(e.store,{'foreign':b'x'*20000})
        receipt=e.store.archive_raw(raw,payloads)
        with patch.object(e.store,'_validate_graph',side_effect=AssertionError('full graph called')):
            refused(lambda:A.read_upbit_read_batch(e.store,receipt.bundle_digest,limits=LIMITS),
                    'READ_BATCH_CHAIN_INVALID')


def test_body_limit_metadata_preflight_refuses_before_reading_that_graph():
    with B.fixture() as e:
        _,digests=trace(e.store,raw=b'x'*1024)
        limited=replace(LIMITS,max_body_bytes=1023)
        original=e.store._validate_graph;visited=[]
        def graph(catalog,digest,**kwargs):
            visited.append(digest);return original(catalog,digest,**kwargs)
        with patch.object(e.store,'_validate_graph',graph):
            refused(lambda:A.read_upbit_read_batch(e.store,digests[-1],limits=limited),'READ_BATCH_RESOURCE_LIMIT')
        assert digests[3] not in visited


def test_reader_replays_catalog_only_at_start_and_finish_not_once_per_parent():
    with B.fixture() as e:
        _,digests=trace(e.store,retry=True)
        with (patch.object(e.store,'_load',wraps=e.store._load) as loaded,
              patch.object(e.store,'_validate_graph',wraps=e.store._validate_graph) as graph):
            result=A.read_upbit_read_batch(e.store,digests[-1],limits=LIMITS)
        assert loaded.call_count==2 and graph.call_count==len(result.records)


def test_non200_returned_receipt_and_invalid_clock_followups_are_impossible_chains():
    for choice in ('non200','clock'):
        with B.fixture() as e:
            def mutate(record,payload):
                if record.kind=='ATTEMPT' and record.body['phase']==('RESPONSE' if choice=='non200' else 'BEFORE_SEND'):
                    body=dict(record.body)
                    body.update(status_code=503) if choice=='non200' else body.update(clock_status='RAISED',observed_at=None)
                    record=replace(record,body=body)
                return record,payload
            _,digests=trace(e.store,mutate=mutate)
            refused(lambda:A.read_upbit_read_batch(e.store,digests[-1],limits=LIMITS),'READ_BATCH_CHAIN_INVALID')


def test_record_codec_acceptance_does_not_allow_excluded_endpoint_archival():
    with B.fixture() as e:
        opened=opener();first=publish(e.store,opened,require_new=True)
        record=F.ReadBatchRecord(schema_version=1,batch_id=opened.batch_id,ordinal=1,previous_archive_digest=first,
            kind='FETCH_BEGIN',body=dict(call_ordinal=1,path='/v1/api_keys',params=(),requested_at=NOW))
        assert F.record_bytes(record)
        before=B.files(e.base)
        refused(lambda:publish(e.store,record),'READ_BATCH_CHAIN_INVALID')
        assert B.files(e.base)==before


def test_require_new_rejects_backed_identity_while_default_exact_retry_is_unchanged():
    with B.fixture() as e:
        raw,payloads,digest=A._manifest(e.store,opener(),None,LIMITS)
        first=e.store.archive_raw(raw,payloads,require_new=True);before=B.files(e.base)
        refused(lambda:e.store.archive_raw(raw,payloads,require_new=True),'BUNDLE_STORE_ALREADY_PUBLISHED')
        assert e.store.archive_raw(raw,payloads)==first and B.files(e.base)==before
        for value in (0,1,None,'yes'):
            refused(lambda value=value:e.store.archive_raw(raw,payloads,require_new=value),'BUNDLE_STORE_INPUT_INVALID')
        assert e.store.read_raw(digest,require_backup=True).backup_verified


def test_require_new_refuses_partial_primary_without_retrying_backup_but_default_can_finish():
    with B.fixture() as e:
        raw,payloads,digest=A._manifest(e.store,opener(),None,LIMITS)
        actual=e.store._stage
        def broken(values,backup,anchor):
            if backup: raise S.BundleStoreError('BUNDLE_STORE_IO_REFUSED')
            return actual(values,backup,anchor)
        with patch.object(e.store,'_stage',broken):
            refused(lambda:e.store.archive_raw(raw,payloads,require_new=True),'BUNDLE_STORE_IO_REFUSED')
        assert not e.store.inspect(digest).backup_verified
        before=B.files(e.base)
        with patch.object(e.store,'_stage',side_effect=AssertionError('new attempt repaired old OPEN')):
            refused(lambda:e.store.archive_raw(raw,payloads,require_new=True),'BUNDLE_STORE_ALREADY_PUBLISHED')
        assert B.files(e.base)==before
        assert e.store.archive_raw(raw,payloads).backup_verified


def test_changed_open_time_same_batch_id_cannot_restart_but_distinct_batch_can():
    from datetime import timedelta
    with B.fixture() as e:
        first=publish(e.store,opener(),require_new=True)
        refused(lambda:publish(e.store,opener(started=NOW+timedelta(seconds=1)),require_new=True),'BUNDLE_STORE_ID_REUSED')
        second=publish(e.store,opener(batch='distinct-batch'),require_new=True)
        assert first!=second and e.store.read_raw(first).manifest.run_id!=e.store.read_raw(second).manifest.run_id


def test_two_actual_concurrent_store_instances_have_one_new_open_winner():
    # Thread/actual OS lock contention, not a claimed OS-process restart test.
    with B.fixture() as e:
        raw,payloads,_=A._manifest(e.store,opener(),None,LIMITS)
        barrier=threading.Barrier(2);outcomes=[]
        def worker(store):
            barrier.wait(timeout=5)
            try: outcomes.append(store.archive_raw(raw,payloads,require_new=True))
            except S.BundleStoreError as exc: outcomes.append(str(exc))
        threads=[threading.Thread(target=worker,args=(store,)) for store in (e.store,e.reopen())]
        for thread in threads: thread.start()
        for thread in threads: thread.join(timeout=10);assert not thread.is_alive()
        winners=[value for value in outcomes if type(value) is S.BundleReceipt]
        assert len(outcomes)==2 and len(winners)==1 and winners[0].backup_verified
        assert next(value for value in outcomes if type(value) is str) in ('BUNDLE_STORE_LOCKED','BUNDLE_STORE_ALREADY_PUBLISHED')


def test_missing_head_does_not_auto_provision_adopt_or_publish_raw_records():
    with B.fixture(initialize=False) as e:
        before=B.files(e.base)
        refused(lambda:publish(e.store,opener(),require_new=True),'BUNDLE_STORE_HEAD_REFUSED')
        assert B.files(e.base)==before


def test_input_hash_preflight_refuses_hidden_state_or_lying_fee_iterable_before_digest():
    from tests.accounts_collector import proofs
    from decimal import Decimal
    anchor,coverage,baseline=proofs()
    def check(a,c,b,fees=()): return A._inputs(a,c,b,fees,LIMITS)
    class Trap:
        def __iter__(self): raise AssertionError('unbounded iterable consumed')
    class TrapDict(dict):
        def __len__(self): raise AssertionError('foreign dict length inspected')
        def __iter__(self): raise AssertionError('foreign dict inventory iterated')
    with patch.object(A,'content_digest',side_effect=AssertionError('digest before admission')):
        refused(lambda:check(anchor,coverage,baseline,Trap()),'READ_BATCH_INPUT_INVALID')
        altered=replace(anchor,cash_krw=Decimal('1E+1000000000'))
        refused(lambda:check(altered,coverage,baseline),'READ_BATCH_INPUT_INVALID')
        altered=replace(anchor,cash_krw=Decimal('1'*10000))
        refused(lambda:check(altered,coverage,baseline),'READ_BATCH_INPUT_INVALID')
        altered=replace(anchor);object.__setattr__(altered,'hidden',Trap())
        refused(lambda:check(altered,coverage,baseline),'READ_BATCH_INPUT_INVALID')
        altered=replace(anchor);object.__setattr__(altered,'__dict__',TrapDict(vars(altered)))
        refused(lambda:check(altered,coverage,baseline),'READ_BATCH_INPUT_INVALID')
    snapshots=check(anchor,coverage,baseline)
    assert snapshots==(anchor,coverage,baseline,()) and snapshots[0] is not anchor
