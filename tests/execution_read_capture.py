"""Actual inquiry capture flow with synthetic keys/replies and no real network.

The ordinary header/query/JSON path runs. Only existing key/send/sleep/clock seams
are replaced; an event or raw hash is never treated as source authentication.
"""
from contextlib import contextmanager
from contextvars import copy_context
from dataclasses import FrozenInstanceError, fields
from datetime import datetime, timedelta, timezone
import hashlib
from threading import Thread
from types import SimpleNamespace
from unittest.mock import patch

import requests

from execution import keys, transport as T, upbit_inquiry as U

NOW = datetime(2026, 11, 13, 1, 0, tzinfo=timezone.utc)
PATH = '/v1/accounts'
DATE = 'Fri, 13 Nov 2026 01:00:00 GMT'


def refused(call, code=None, kind=Exception):
    try:
        call()
    except kind as exc:
        if code is not None:
            assert str(exc) == code, (str(exc), code)
        return exc
    raise AssertionError('expected refusal')


@contextmanager
def wire(*replies, clock=None, explicit=True):
    calls, sleeps, times, key_reads = [], [], [], []
    sequence = iter(replies or ((200, {'Date': DATE}, b'[]'),))
    def read_clock():
        times.append(None)
        return NOW if clock is None else clock()
    def read_keys(names):
        key_reads.append(tuple(names))
        return tuple('synthetic-read-key-' + str(index) for index, _ in enumerate(names))
    def send(method, url, **kwargs):
        calls.append((method, url, kwargs))
        value = next(sequence)
        if isinstance(value, BaseException):
            raise value
        return value() if callable(value) else value
    with patch.object(T, '_send', send), patch.object(T, '_sleep', sleeps.append), \
         patch.object(T, '_clock', read_clock), patch.object(keys, 'read', read_keys):
        env = SimpleNamespace(calls=calls, sleeps=sleeps, times=times, key_reads=key_reads)
        if explicit:
            with T.inquiry_clock(read_clock):
                yield env
        else:
            yield env


def capture(events, **kwargs):
    return T.capture_upbit_reads(events.append, call_ordinal=kwargs.pop('call_ordinal', 1),
                                not_before=kwargs.pop('not_before', NOW), **kwargs)


def request(params=None):
    return T.request('upbit', 'GET', PATH, params)


def test_exact_capture_subset_is_nine_existing_get_pairs():
    expected = frozenset(('GET', path) for path in (PATH, '/v1/orders/open', '/v1/orders/closed',
        '/v1/order', '/v1/deposits', '/v1/withdraws', '/v1/ticker', '/v1/market/all', '/v1/orderbook'))
    assert U.READ_CAPTURE_ENDPOINTS == expected and expected < U.ENDPOINTS
    assert type(U.READ_CAPTURE_ENDPOINTS) is frozenset


def test_event_shape_is_frozen_keyword_only_and_hides_private_values():
    events = []
    raw = b'[{"private":"synthetic-raw-secret"}]'
    with wire((200, {'Date': DATE, 'Authorization': 'synthetic-header-secret'}, raw)) as e, capture(events):
        answer = request((('uuid', 'synthetic-query-secret'),))
    assert [x.phase for x in events] == ['BEFORE_SEND', 'RESPONSE']
    event = events[-1]
    assert {f.name for f in fields(event)} == {'call_ordinal', 'attempt', 'phase', 'path', 'params',
        'observed_at', 'clock_status', 'status_code', 'body_status', 'body_bytes', 'body_sha256', 'raw_body', 'error_code'}
    assert event.raw_body is raw and event.body_bytes == len(raw) and event.body_sha256 == hashlib.sha256(raw).hexdigest()
    assert answer.raw_body is raw and answer.received_utc == event.observed_at == NOW
    assert event.clock_status == 'OK' and event.status_code == 200 and event.body_status == 'PRESENT'
    assert event.error_code is None and e.key_reads and len(e.times) == 2
    assert all(value not in repr(event) for value in ('synthetic-raw-secret', 'synthetic-query-secret',
                                                    'synthetic-header-secret', 'Bearer', 'synthetic-read-key'))
    refused(lambda: setattr(event, 'attempt', 2), kind=FrozenInstanceError)
    refused(lambda: T.UpbitReadEvent(*[getattr(event, f.name) for f in fields(event)]), kind=TypeError)


def test_no_observer_preserves_response_clock_pacing_and_answer():
    raw = b' [ {"currency":"KRW"} ] '
    with wire((200, {'Date': DATE}, raw)) as e:
        answer = request()
    assert len(e.calls) == 1 and len(e.times) == 1 and e.sleeps == [T.PACE_S]
    assert answer.raw_body == raw and answer.sha256 == hashlib.sha256(raw).hexdigest()
    assert answer.body == [{'currency': 'KRW'}] and answer.server_utc == NOW


def test_retry_responses_are_preserved_before_either_is_parsed():
    for status in (429, 503):
        events, parsed = [], []
        first, second = b'not-json-first', b'[]'
        original = T._check_answer
        def check(*args):
            parsed.append(args[-1]); return original(*args)
        with wire((status, {}, first), (200, {'Date': DATE}, second)) as e, capture(events), \
             patch.object(T, '_check_answer', check):
            answer = request()
        assert [(x.attempt, x.phase) for x in events] == [(1,'BEFORE_SEND'), (1,'RESPONSE'),
                                                        (2,'BEFORE_SEND'), (2,'RESPONSE')]
        assert [x.raw_body for x in events if x.phase == 'RESPONSE'] == [first, second]
        assert parsed == [second] and answer.raw_body == second
        assert e.sleeps == [0.2, 2.0, 0.2] and len(e.times) == 4 and len(e.calls) == 2
        assert e.calls[0][2]['headers']['Authorization'] != e.calls[1][2]['headers']['Authorization']


def test_second_failed_response_is_also_retained():
    events = []
    with wire((503, {}, b'first'), (503, {}, b'second')) as e, capture(events):
        refused(request, kind=T.InquiryError)
    assert [x.raw_body for x in events if x.phase == 'RESPONSE'] == [b'first', b'second']
    assert len(e.calls) == 2


def test_empty_malformed_and_authentication_error_bodies_are_retained_exactly():
    for status, raw, kind in ((200,b'',T.InquiryError), (200,b'\xffbad',T.InquiryError),
        (401,b'{"error":{"name":"jwt_verification","message":"private"}}',T.AuthError)):
        events = []
        with wire((status, {}, raw)) as e, capture(events):
            refused(request, kind=kind)
        event = events[-1]
        assert event.raw_body == raw and event.body_bytes == len(raw) and event.body_status == 'PRESENT'
        assert event.body_sha256 == hashlib.sha256(raw).hexdigest() and len(e.calls) == 1


def test_network_retry_records_error_without_inventing_response():
    events = []
    with wire(requests.exceptions.ConnectionError('synthetic-private-url'), (200, {}, b'[]')) as e, capture(events):
        request()
    error = events[1]
    assert error.phase == 'TRANSPORT_ERROR' and error.error_code == 'CONNECTION_ERROR'
    assert (error.raw_body,error.body_sha256,error.body_bytes,error.status_code) == (None,None,None,None)
    assert error.body_status == 'NOT_RECEIVED' and error.clock_status == 'OK'
    assert [x.attempt for x in events] == [1,1,2,2] and e.sleeps == [0.2,2.0,0.2]


def test_all_transport_exception_categories_are_fixed_and_never_expose_text():
    errors = ((requests.exceptions.ReadTimeout('PRIVATE'), 'READ_TIMEOUT'),
              (requests.exceptions.Timeout('PRIVATE'), 'TIMEOUT'),
              (OSError('PRIVATE'), 'OS_ERROR'), (ValueError('PRIVATE'), 'VALUE_ERROR'),
              (RuntimeError('PRIVATE'), 'OTHER_EXCEPTION'))
    for exc, code in errors:
        events=[]
        with wire(exc) as e, capture(events):
            refused(request, 'READ_CAPTURE_TRANSPORT_ERROR', T.InquiryError)
        assert events[-1].error_code == code and 'PRIVATE' not in repr(events[-1])
        assert len(e.calls) == 1


def test_no_observer_preserves_original_unexpected_exception_identity():
    exc = RuntimeError('synthetic-original')
    with wire(exc) as e:
        assert refused(request, kind=RuntimeError) is exc
    assert len(e.calls) == 1 and len(e.times) == 0 and e.sleeps == []


def test_base_exception_is_not_claimed_as_a_completed_transport_error():
    events=[]; exc=KeyboardInterrupt()
    with wire(exc) as e, capture(events):
        assert refused(request, kind=KeyboardInterrupt) is exc
    assert len(e.calls) == 1 and [x.phase for x in events] == ['BEFORE_SEND']


def test_after_response_guard_refusal_occurs_after_exact_raw_record():
    events=[]
    def guard(stage):
        if stage == 'after_response':
            raise ValueError('synthetic-private-guard')
    with wire((429, {}, b'first-response')) as e, capture(events), T.inquiry_guard(guard):
        refused(request, 'E1_GUARD_REFUSED', T.InquiryRefused)
    assert events[-1].raw_body == b'first-response' and len(e.calls) == 1 and e.sleeps == []


def test_slow_before_send_sink_cannot_bypass_existing_guard():
    events=[]; cell=[NOW]
    def sink(event):
        events.append(event)
        cell[0] += timedelta(seconds=31)
    def guard(stage):
        if cell[0] > NOW + timedelta(seconds=30):
            raise ValueError('synthetic expired guard')
    with wire(clock=lambda:cell[0]) as e, \
         T.capture_upbit_reads(sink,call_ordinal=1,not_before=NOW), T.inquiry_guard(guard):
        refused(request, 'E1_GUARD_REFUSED', T.InquiryRefused)
    assert [x.phase for x in events] == ['BEFORE_SEND'] and not e.calls


def test_ordinary_guard_stage_sequence_without_observer_is_unchanged():
    stages=[]
    with wire(), T.inquiry_guard(stages.append):
        request()
    assert stages == ['before_headers','before_send','after_response','after_wait']


def test_sink_failure_or_non_none_return_stops_before_send_or_retry():
    for phase in ('BEFORE_SEND','RESPONSE'):
        for raises in (False,True):
            events=[]
            def sink(event):
                events.append(event)
                if event.phase == phase:
                    if raises:
                        raise OSError('SYNTHETIC_PRIVATE_PATH')
                    return False
            with wire((429, {}, b'first')) as e, \
                 T.capture_upbit_reads(sink,call_ordinal=1,not_before=NOW):
                refused(request, 'READ_CAPTURE_SINK_REFUSED', T.InquiryRefused)
                refused(request, 'READ_CAPTURE_CONTEXT_REFUSED', T.InquiryRefused)
            assert len(e.calls) == (0 if phase=='BEFORE_SEND' else 1)
            assert len(events) == (1 if phase=='BEFORE_SEND' else 2)


def test_invalid_clock_after_response_preserves_raw_then_stops_retry():
    for bad, status in ((None,'INVALID'), (datetime(2026,11,13),'INVALID'),
                        (NOW-timedelta(microseconds=1),'ROLLBACK'), (ValueError('PRIVATE_CLOCK'),'RAISED')):
        readings=iter((NOW,bad)); events=[]
        def clock():
            value=next(readings)
            if isinstance(value,Exception): raise value
            return value
        with wire((429, {}, b'raw-clock-failure'),clock=clock) as e, capture(events):
            refused(request, 'READ_CAPTURE_CLOCK_REFUSED', T.InquiryRefused)
        event=events[-1]
        assert event.raw_body == b'raw-clock-failure' and event.observed_at is None and event.clock_status == status
        assert len(e.calls) == 1 and len(e.times) == 2


def test_bad_initial_clock_records_unsent_attempt_and_never_calls_send():
    events=[]
    with wire(clock=lambda:None) as e, capture(events):
        refused(request,'READ_CAPTURE_CLOCK_REFUSED',T.InquiryRefused)
    assert len(events)==1 and events[0].phase=='BEFORE_SEND' and events[0].clock_status=='INVALID'
    assert events[0].body_status=='NOT_RECEIVED' and not e.calls


def test_retry_clock_rollback_does_not_send_second_attempt():
    events=[]; readings=iter((NOW,NOW+timedelta(seconds=1),NOW))
    with wire((429,{},b'first'),clock=lambda:next(readings)) as e, capture(events):
        refused(request,'READ_CAPTURE_CLOCK_REFUSED',T.InquiryRefused)
    assert len(e.calls)==1 and events[-1].attempt==2 and events[-1].phase=='BEFORE_SEND'
    assert events[-1].clock_status=='ROLLBACK' and events[-1].observed_at is None


def test_body_limit_is_admitted_before_hash_and_never_truncates_as_success():
    events=[]
    with wire((200,{},b'1234')) as e, capture(events,max_body_bytes=3), \
         patch.object(T.hashlib,'sha256',side_effect=AssertionError('oversize body must not be hashed')):
        refused(lambda:T.request('upbit','GET','/v1/ticker'), 'READ_CAPTURE_RESOURCE_LIMIT',T.InquiryRefused)
    event=events[-1]
    assert event.body_status=='LIMIT_EXCEEDED' and event.body_bytes==4
    assert event.raw_body is None and event.body_sha256 is None and len(e.calls)==1


def test_invalid_status_or_nonbytes_response_is_observed_without_coercion():
    class Trap:
        def __str__(self): raise AssertionError('no stringify')
        def __bytes__(self): raise AssertionError('no bytes conversion')
    for status,body,expected in ((True,b'[]','PRESENT'), (99,b'[]','PRESENT'),
                                 (1000,b'[]','PRESENT'), (200,Trap(),'INVALID')):
        events=[]
        with wire((status,{},body)) as e, capture(events):
            refused(request,'READ_CAPTURE_RESPONSE_INVALID',T.InquiryRefused)
        event=events[-1]
        assert event.error_code=='INVALID_RESPONSE' and event.body_status==expected
        assert event.status_code==(200 if type(status) is int and 100<=status<=999 else None)
        assert event.raw_body==(body if type(body) is bytes else None) and len(e.calls)==1


def test_nonstandard_bounded_status_is_retained_then_ordinary_http_refusal():
    events=[]
    with wire((777,{},b'[]'),(777,{},b'[]')) as e,capture(events):
        refused(request,kind=T.InquiryError)
    assert [x.status_code for x in events if x.phase=='RESPONSE']==[777,777] and len(e.calls)==2


def test_capture_context_admission_is_exact_and_precedes_keys_or_network():
    cases=({'call_ordinal':True},{'call_ordinal':0},{'call_ordinal':2001},
           {'not_before':datetime(2026,11,13)},{'not_before':datetime(1,1,1,tzinfo=timezone.utc)},
           {'max_body_bytes':True},{'max_body_bytes':0},{'max_body_bytes':8*1024*1024+1})
    for changes in cases:
        args={'call_ordinal':1,'not_before':NOW}|changes
        with wire() as e:
            refused(lambda:T.capture_upbit_reads(lambda _:None,**args),'READ_CAPTURE_CONTEXT_REFUSED',T.InquiryRefused)
        assert not e.calls and not e.key_reads and not e.times
    refused(lambda:T.capture_upbit_reads(None,call_ordinal=1,not_before=NOW),
            'READ_CAPTURE_CONTEXT_REFUSED',T.InquiryRefused)


def test_scope_excludes_token_other_venues_and_noncapture_upbit_paths_before_credentials():
    cases=(('kis','POST','/oauth2/tokenP'),('okx','GET','/api/v5/public/time'),
           ('upbit','POST','/v1/orders'),('upbit','GET','/v1/api_keys'),
           ('upbit','GET','/v1/withdraws/coin_addresses'))
    for venue,method,path in cases:
        events=[]
        with wire() as e,capture(events):
            refused(lambda:T.request(venue,method,path),'READ_CAPTURE_SCOPE_REFUSED',T.InquiryRefused)
        assert not e.calls and not e.key_reads and not e.times and not events


def test_snapshot_params_match_actual_query_even_if_caller_changes_original_list():
    events=[];params=[('states[]','wait'),('states[]','watch')]
    def sink(event):
        events.append(event)
        params[:] = [('states[]','changed')]
    with wire() as e,T.capture_upbit_reads(sink,call_ordinal=17,not_before=NOW):
        request(params)
    assert all(x.params == (('states[]','wait'),('states[]','watch')) and x.call_ordinal==17 for x in events)
    assert e.calls[0][1].endswith('?states[]=wait&states[]=watch')


def test_param_bounds_precede_iteration_or_query_allocation():
    class Trap:
        def __iter__(self): raise AssertionError('no caller iteration')
    for params in (Trap(), [('x','y')]*17, [('x'*129,'y')], [('x','y'*65537)], [(True,'y')], [['x','y']]):
        events=[]
        with wire() as e,capture(events):
            refused(lambda:request(params),'READ_CAPTURE_SCOPE_REFUSED',T.InquiryRefused)
        assert not e.calls and not e.key_reads and not e.times and not events


def test_one_context_allows_only_one_request_and_context_object_is_single_use():
    events=[];context=capture(events)
    with wire() as e:
        with context:
            request()
            refused(request,'READ_CAPTURE_CONTEXT_REFUSED',T.InquiryRefused)
        refused(context.__enter__,'READ_CAPTURE_CONTEXT_REFUSED',T.InquiryRefused)
    assert len(e.calls)==1 and len(events)==2
    with wire(),capture([]):
        request()  # prior failed context was restored, not leaked


def test_nested_context_refusal_remains_latched_if_caught():
    events=[]
    with wire() as e,capture(events):
        refused(lambda:capture([]),'READ_CAPTURE_CONTEXT_REFUSED',T.InquiryRefused)
        refused(request,'READ_CAPTURE_CONTEXT_REFUSED',T.InquiryRefused)
    assert not e.calls and not events


def test_recursive_request_from_sink_cannot_be_swallowed_into_permission():
    events=[]
    def sink(event):
        events.append(event)
        refused(request,'READ_CAPTURE_CONTEXT_REFUSED',T.InquiryRefused)
    with wire() as e,T.capture_upbit_reads(sink,call_ordinal=1,not_before=NOW):
        refused(request,'READ_CAPTURE_CONTEXT_REFUSED',T.InquiryRefused)
    assert len(events)==1 and not e.calls


def test_copied_active_context_cannot_be_used_in_another_thread():
    events=[];errors=[]
    with wire() as e,capture(events):
        copied=copy_context()
        def other():
            errors.append(refused(lambda:copied.run(request),'READ_CAPTURE_CONTEXT_REFUSED',T.InquiryRefused))
        thread=Thread(target=other);thread.start();thread.join()
        refused(request,'READ_CAPTURE_CONTEXT_REFUSED',T.InquiryRefused)
    assert len(errors)==1 and not events and not e.calls


def test_explicit_clock_precedence_and_utc_normalization_are_unchanged():
    events=[];offset=timezone(timedelta(hours=9));local=NOW.astimezone(offset)
    with wire(clock=lambda:local) as e,capture(events), \
         patch.object(T,'_clock',side_effect=AssertionError('explicit context must win')):
        answer=request()
    assert all(x.observed_at==NOW and x.observed_at.tzinfo is timezone.utc for x in events)
    assert answer.received_utc==NOW and len(e.times)==2


def test_legacy_clock_seam_is_supported_without_an_explicit_inquiry_context():
    events=[]
    with wire(explicit=False) as e,capture(events):
        request()
    assert len(e.times)==2 and all(x.clock_status=='OK' for x in events)
