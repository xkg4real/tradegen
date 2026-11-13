"""Pure caller-claimed read records; no source, store, credential or transport."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import hashlib
import json
from types import MappingProxyType
from unittest.mock import patch

from execution_launch import upbit_read_format as F

NOW = datetime(2031, 1, 1, tzinfo=timezone.utc)


def opened(**changes):
    args = dict(schema_version=1, batch_id='unit-batch', ordinal=0, previous_archive_digest=None,
        kind='OPEN', body=dict(account_scope='synthetic-scope', started_at=NOW,
            limits_sha256=F.limits_digest(), anchor_sha256='1'*64, coverage_sha256='2'*64,
            baseline_sha256='3'*64, trade_fees_sha256='4'*64))
    return F.ReadBatchRecord(**(args | changes))


def attempt(**changes):
    body = dict(call_ordinal=1, attempt=1, phase='RESPONSE', path='/v1/accounts', params=(),
        observed_at=NOW, clock_status='OK', status_code=200, body_status='PRESENT', body_bytes=0,
        body_sha256=hashlib.sha256(b'').hexdigest(), error_code=None)
    return F.ReadBatchRecord(schema_version=1, batch_id='unit-batch', ordinal=2,
        previous_archive_digest='a'*64, kind='ATTEMPT', body=body | changes)


def refused(call, code=None):
    try: call()
    except F.ReadBatchFormatError as exc:
        assert str(exc) in F.BATCH_CODES
        if code is not None: assert str(exc) == code
        return
    raise AssertionError('invalid pure read record accepted')


def canonical(body):
    return json.dumps(body, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('ascii')


def test_canonical_record_and_domain_digest_have_independent_golden_bytes():
    body = dict(account_scope='synthetic-scope', started_at='2031-01-01T00:00:00.000000+00:00',
        limits_sha256=F.limits_digest(), anchor_sha256='1'*64, coverage_sha256='2'*64,
        baseline_sha256='3'*64, trade_fees_sha256='4'*64)
    expected = canonical(dict(schema_version=1, batch_id='unit-batch', ordinal=0,
        previous_archive_digest=None, kind='OPEN', body=body))
    value = opened()
    assert F.record_bytes(value) == expected
    assert F.record_digest(value) == hashlib.sha256(b'tradegen-upbit-read-batch-record/1\x00'+expected).hexdigest()
    assert F.parse_record(expected) == value


def test_limits_digest_has_its_own_domain_and_no_mutable_or_boolean_limits():
    value = F.ReadBatchLimits(max_calls=3)
    document = dict(max_calls=3, max_attempts=4000, max_records=12002, max_body_bytes=8388608,
                    max_total_body_bytes=67108864, max_record_bytes=2097152, max_total_record_bytes=67108864)
    assert F.limits_digest(value) == hashlib.sha256(b'tradegen-upbit-read-batch-limits/1\x00'+canonical(document)).hexdigest()
    for change in (dict(max_calls=True), dict(max_attempts=0), dict(max_records=12003), dict(max_body_bytes=8388609)):
        refused(lambda change=change:F.ReadBatchLimits(**change), 'READ_BATCH_LIMITS_INVALID')
    object.__delattr__(value, 'max_calls')
    refused(lambda:F.limits_digest(value), 'READ_BATCH_LIMITS_INVALID')


def test_record_detaches_nested_containers_and_preserves_ordered_duplicate_query_keys():
    body = dict(call_ordinal=1, path='/v1/orders/open', params=[['states[]','wait'],['states[]','watch']],
                requested_at=NOW)
    value = F.ReadBatchRecord(schema_version=1,batch_id='unit-batch',ordinal=1,
        previous_archive_digest='a'*64,kind='FETCH_BEGIN',body=body)
    before = F.record_bytes(value)
    body['params'][0][1] = 'changed'
    assert F.record_bytes(value) == before and type(value.body) is MappingProxyType
    assert value.body['params'] == (('states[]','wait'),('states[]','watch'))


def test_dataclass_field_deletion_or_postconstruction_mutation_is_revalidated():
    for operation in (F.record_bytes, F.record_digest):
        value = opened(); object.__delattr__(value, 'ordinal')
        refused(lambda:operation(value))
        value = opened(); object.__setattr__(value, 'schema_version', True)
        refused(lambda:operation(value))


def test_all_five_record_shapes_roundtrip_without_asserting_actual_collection():
    values = [opened(), F.ReadBatchRecord(schema_version=1,batch_id='unit-batch',ordinal=1,
        previous_archive_digest='a'*64,kind='FETCH_BEGIN',body=dict(call_ordinal=1,path='/v1/accounts',
            params=(),requested_at=NOW)), attempt(), F.ReadBatchRecord(schema_version=1,batch_id='unit-batch',
        ordinal=3,previous_archive_digest='a'*64,kind='FETCH_END',body=dict(call_ordinal=1,status='REFUSED',
            receipt=None,error_code='READ_BATCH_COLLECTOR_REFUSED')),
        F.ReadBatchRecord(schema_version=1,batch_id='unit-batch',ordinal=4,previous_archive_digest='a'*64,
            kind='CLOSE',body=dict(status='REFUSED',error_code='READ_BATCH_COLLECTOR_REFUSED',
                collection_manifest_sha256=None,records=tuple((i,'b'*64) for i in range(4)),calls=1,
                attempts=1,finished_at=NOW,clock_status='OK'))]
    for value in values: assert F.parse_record(F.record_bytes(value)) == value


def test_open_ordinal_parent_batch_identity_and_exact_fields_are_mandatory():
    for change in (dict(ordinal=True), dict(ordinal=1), dict(previous_archive_digest='a'*64),
                   dict(batch_id='1bad'),dict(batch_id='x'*65),dict(schema_version=2)):
        refused(lambda change=change:opened(**change))
    for mutation in ('extra','missing'):
        body = dict(opened().body)
        if mutation == 'extra': body['headers'] = {}
        else: del body['anchor_sha256']
        refused(lambda:opened(body=body))


def test_present_empty_body_has_exact_zero_length_sha_and_no_string_coercions():
    value = attempt()
    assert value.body['body_bytes'] == 0 and value.body['body_sha256'] == hashlib.sha256(b'').hexdigest()
    for change in (dict(body_bytes=True),dict(body_bytes=-1),dict(body_sha256=None),
                   dict(status_code=True),dict(status_code='200'),dict(attempt=3)):
        refused(lambda change=change:attempt(**change))


def test_oversized_and_nonbytes_response_facts_are_distinct_from_received_raw():
    over = attempt(body_status='LIMIT_EXCEEDED',body_bytes=F.DEFAULT_LIMITS.max_body_bytes+1,body_sha256=None)
    invalid = attempt(body_status='INVALID',body_bytes=None,body_sha256=None,error_code='INVALID_RESPONSE')
    assert F.parse_record(F.record_bytes(over)) == over
    assert F.parse_record(F.record_bytes(invalid)) == invalid
    refused(lambda:F.record_bytes(attempt(body_status='LIMIT_EXCEEDED',body_bytes=10,body_sha256=None)))
    refused(lambda:attempt(body_status='INVALID',body_bytes=None,body_sha256=None))


def test_invalid_status_preserves_valid_body_but_requires_fixed_error():
    value = attempt(status_code=None,error_code='INVALID_RESPONSE')
    assert value.body['body_status'] == 'PRESENT'
    refused(lambda:attempt(status_code=None))
    refused(lambda:attempt(error_code='private secret exception text'))


def test_before_send_and_transport_error_have_no_invented_response_payload():
    base = dict(phase='BEFORE_SEND',status_code=None,body_status='NOT_RECEIVED',body_bytes=None,body_sha256=None)
    assert F.record_bytes(attempt(**base))
    assert F.record_bytes(attempt(**(base | dict(phase='TRANSPORT_ERROR',error_code='READ_TIMEOUT'))))
    refused(lambda:attempt(**(base | dict(body_bytes=0))))
    refused(lambda:attempt(**(base | dict(phase='TRANSPORT_ERROR',error_code='TypeError: private'))))


def test_clock_failure_has_no_fabricated_observation_time_and_raw_fact_survives():
    for status in ('RAISED','INVALID','ROLLBACK'):
        value = attempt(clock_status=status,observed_at=None)
        assert F.parse_record(F.record_bytes(value)).body['body_status'] == 'PRESENT'
        refused(lambda status=status:attempt(clock_status=status))
    refused(lambda:attempt(clock_status='OK',observed_at=None))


def test_timestamp_timezone_is_canonicalized_and_noncanonical_wire_time_refused():
    other = NOW.astimezone(timezone(timedelta(hours=9)))
    assert attempt(observed_at=other) == attempt()
    refused(lambda:attempt(observed_at=datetime(2031,1,1)))
    body = json.loads(F.record_bytes(attempt()))
    body['body']['observed_at'] = '2031-01-01T00:00:00Z'
    refused(lambda:F.parse_record(canonical(body)))


def test_fetch_end_returned_receipt_and_refusal_are_disjoint_shapes():
    base = dict(schema_version=1,batch_id='unit-batch',ordinal=2,previous_archive_digest='a'*64,kind='FETCH_END')
    receipt = dict(path='/v1/accounts',params=(),account_scope='scope',received_at=NOW,server_time=NOW,sha256='a'*64)
    valid = F.ReadBatchRecord(**base,body=dict(call_ordinal=1,status='RETURNED',receipt=receipt,error_code=None))
    assert F.parse_record(F.record_bytes(valid)) == valid
    for body in (dict(call_ordinal=1,status='RETURNED',receipt=None,error_code=None),
                 dict(call_ordinal=1,status='REFUSED',receipt=receipt,error_code='READ_BATCH_COLLECTOR_REFUSED')):
        refused(lambda body=body:F.ReadBatchRecord(**base,body=body))


def test_close_inventory_indices_and_collected_clock_are_exact():
    base = dict(schema_version=1,batch_id='unit-batch',ordinal=1,previous_archive_digest='a'*64,kind='CLOSE')
    body = dict(status='COLLECTED',error_code=None,collection_manifest_sha256='b'*64,
                records=((0,'a'*64),),calls=1,attempts=1,finished_at=NOW,clock_status='OK')
    assert F.record_bytes(F.ReadBatchRecord(**base,body=body))
    for change in (dict(records=((True,'a'*64),)),dict(records=()),dict(records=((1,'a'*64),)),
                   dict(clock_status='RAISED',finished_at=None),dict(error_code='READ_BATCH_COLLECTOR_REFUSED')):
        refused(lambda change=change:F.ReadBatchRecord(**base,body=body | change))


def test_json_duplicate_nonfinite_float_extra_top_level_and_noncanonical_bytes_refuse():
    raw = F.record_bytes(opened())
    samples = (raw.replace(b'"ordinal":0',b'"ordinal":0,"ordinal":0'),
               raw.replace(b'"ordinal":0',b'"ordinal":NaN'),raw.replace(b'"ordinal":0',b'"ordinal":0.0'),
               b' '+raw,raw[:-1]+b',"extra":1}')
    for value in samples: refused(lambda value=value:F.parse_record(value))


def test_json_depth_and_raw_size_are_refused_before_decoder():
    with patch.object(F.json,'loads',side_effect=AssertionError('decoder called')):
        refused(lambda:F.parse_record(b'['*13+b'0'+b']'*13),'READ_BATCH_RESOURCE_LIMIT')
        refused(lambda:F.parse_record(b' '*1025,limits=F.ReadBatchLimits(max_record_bytes=1024)),
                'READ_BATCH_RESOURCE_LIMIT')


def test_lying_containers_large_hidden_values_and_huge_ints_refuse_before_canonical_allocation():
    class Trap(dict):
        def items(self): raise AssertionError('lying mapping iterated')
    template = opened()  # limits_digest encoding is fixture setup, outside the trap
    for body in (Trap(opened().body),dict(opened().body,extra=10**1000),
                 dict(opened().body,extra='x'*65537),dict(opened().body,extra=object())):
        with patch.object(F.json,'dumps',side_effect=AssertionError('encoder called')):
            refused(lambda body=body:replace(template,body=body))


def test_actual_record_byte_boundary_is_admitted_exactly_without_truncation():
    value = opened(); raw = F.record_bytes(value)
    assert F.record_bytes(value,limits=F.ReadBatchLimits(max_record_bytes=len(raw))) == raw
    refused(lambda:F.record_bytes(value,limits=F.ReadBatchLimits(max_record_bytes=len(raw)-1)),
            'READ_BATCH_RESOURCE_LIMIT')


def test_pure_path_structure_is_not_an_endpoint_permission():
    # Endpoint membership belongs to the actual archive/transport; no network here.
    value = attempt(path='/v1/api_keys')
    assert F.parse_record(F.record_bytes(value)) == value
    for path in ('https://private.invalid/path','/bad path','/é','/'+('a'*128)):
        refused(lambda path=path:attempt(path=path))


def test_mapping_proxy_is_snapshotted_once_with_bounds_on_every_yielded_value():
    from collections.abc import Mapping
    class Changing(Mapping):
        def __init__(self, malicious_first=False): self.calls=0;self.malicious_first=malicious_first
        def __len__(self): return 8
        def __iter__(self): return iter(opened().body)
        def __getitem__(self,key): return opened().body[key]
        def items(self):
            self.calls+=1
            if self.malicious_first or self.calls>1:
                return dict(opened().body,extra=[None]*250001).items()
            return opened().body.items()
    changing=Changing()
    value=opened(body=MappingProxyType(changing))
    assert changing.calls==1 and F.record_bytes(value)==F.record_bytes(opened())
    malicious=Changing(malicious_first=True)
    refused(lambda:opened(body=MappingProxyType(malicious)),'READ_BATCH_RESOURCE_LIMIT')


def test_mapping_callback_cannot_replace_validated_record_headers_before_encoding():
    from collections.abc import Mapping
    for operation in (F.record_bytes,F.record_digest):
        for name,bad in (('schema_version',True),('batch_id','/invalid'),('ordinal',True),
                         ('previous_archive_digest','f'*64),('kind','FETCH_END')):
            record=opened(); body=dict(record.body)
            class Changing(Mapping):
                def __len__(self): return len(body)
                def __iter__(self): return iter(body)
                def __getitem__(self,key): return body[key]
                def items(self):
                    object.__setattr__(record,name,bad)
                    return body.items()
            object.__setattr__(record,'body',MappingProxyType(Changing()))
            refused(lambda:operation(record),'READ_BATCH_FORMAT_INVALID')


def test_body_overflow_fact_uses_selected_batch_limit_in_encoding_and_reading():
    limits=F.ReadBatchLimits(max_body_bytes=8)
    value=attempt(body_status='LIMIT_EXCEEDED',body_bytes=9,body_sha256=None)
    raw=F.record_bytes(value,limits=limits)
    assert F.parse_record(raw,limits=limits)==value
    refused(lambda:F.record_bytes(value),'READ_BATCH_FORMAT_INVALID')
    refused(lambda:F.parse_record(raw),'READ_BATCH_FORMAT_INVALID')
    exact=attempt(body_status='LIMIT_EXCEEDED',body_bytes=8,body_sha256=None)
    refused(lambda:F.record_bytes(exact,limits=limits),'READ_BATCH_FORMAT_INVALID')
