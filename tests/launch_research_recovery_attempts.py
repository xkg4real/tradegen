"""Synthetic model facts only; these tests issue no recovery/owner authority."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import base64
import hashlib
import json
from types import MappingProxyType
from unittest.mock import patch

from execution_launch import research_recovery_attempts as F
from tests import launch_research_incidents as IF

AT = datetime(2026, 1, 1, tzinfo=timezone.utc)
H = IF.digest


def stamp(at):
    return at.isoformat(timespec='microseconds').replace('+00:00','Z')


def encoded(document):
    return json.dumps(document, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('ascii')


def refused(call, code=None):
    try:
        call()
    except F.RecoveryAttemptError as exc:
        assert str(exc).startswith('RECOVERY_')
        if code is not None:
            assert str(exc) == code, (str(exc), code)
        return
    raise AssertionError('expected refusal')


def checkpoint(at=AT, *, sequence=1, label=None):
    return F.OwnerCheckpoint(key_fingerprint='SHA256:'+H('owner'), code_hash=H('code'),
        owner_head=(sequence,H(label or f'owner-{sequence}')), observed_at=at)


def route(label='a', *, at=AT):
    return F.RecoveryRoute(incident_namespace_sha256=H('incidents'), attempt_namespace_sha256=H('attempts'),
        incident_head=(1,H('incident-1')), registration=IF.registration(label),
        source_configuration_sha256=H('source-config'), source_root_ids=((1,10),(1,11)),
        destination_configuration_sha256=H('destination-config'), destination_root_ids=((1,20),(1,21)),
        destination_context_sha256=H('destination-context'), storage_policy_sha256=H('storage'),
        object_policy_sha256=H('objects'), attestation_sha256=H(label+'-attestation'),
        request_sha256=H(label+'-request'), file_set_sha256=H(label+'-files'),
        revocation_target_sha256=H(label+'-revocation'), issued_at=at,
        expires_at=at+timedelta(hours=1), checkpoint=checkpoint(at))


def registered(value=None):
    value = value or route()
    return F.reduce(F.initial_state(), F.make_event('ROUTE_REGISTERED', F.route_document(value),
                                                  observed_at=value.checkpoint.observed_at))


def start(value, *, incident=None, at=AT, current=None):
    return F.make_event('ATTEMPT_STARTED', dict(route_id=value.route_id, incident_id=incident or H('incident'),
        incident_head=[2,H('incident-2')], checkpoint=F.checkpoint_document(current or checkpoint(at, sequence=2))), observed_at=at)


def resume(attempt, *, at, number=None, current=None):
    return F.make_event('RESUME_STARTED', dict(attempt_id=attempt.attempt_id,
        execution_number=number or attempt.execution_count+1, incident_head=[3,H('incident-3')],
        checkpoint=F.checkpoint_document(current or checkpoint(at, sequence=4))), observed_at=at)


def observed(attempt, *, at=AT, status='EXACT_ARCHIVE_RESTORED', reason='TEST_RESULT', current=None,
             revocation=None):
    positive = status == 'EXACT_ARCHIVE_RESTORED'
    current = current or (checkpoint(at, sequence=3) if positive else None)
    return F.make_event('ATTEMPT_OBSERVED', dict(attempt_id=attempt.attempt_id,
        execution_number=attempt.execution_count, status=status, reason_code=reason,
        checkpoint=None if current is None else F.checkpoint_document(current),
        revocation_status=revocation or ('NOT_REVOKED_AT_HEAD' if positive else 'UNOBSERVED'),
        verified_at=stamp(at) if positive else None,
        recovery_artifact_digest=H('artifact') if positive else None,
        destination_head=[6,H('destination-head')] if positive else None), observed_at=at)


def preflight(value, *, incident=None, at=AT, number=1, status='READ_UNAVAILABLE', current=None, incident_head=None):
    return F.make_event('PREFLIGHT_REFUSED', dict(route_id=value.route_id, incident_id=incident or H('incident'),
        execution_number=number, incident_head=list(incident_head or (2,H('incident-2'))), status=status, reason_code='TEST_PREFLIGHT',
        checkpoint=None if current is None else F.checkpoint_document(current), revocation_status='UNOBSERVED'), observed_at=at)


def delivery(message, label='send-a', *, at=AT, outcome='unknown'):
    return F.make_event('DELIVERY_REPORTED', dict(message_id=message.message_id,
        delivery_attempt_id=label, outcome=outcome), observed_at=at)


def test_route_and_event_roundtrip_domain_and_stable_owner_prefix_identity():
    value = route()
    changed = replace(value, incident_head=(4,H('incident-4')),
                      checkpoint=checkpoint(AT+timedelta(seconds=1), sequence=2))
    assert value.route_id == changed.route_id
    assert F.route_document(value) != F.route_document(changed)
    assert F.parse_route(F.route_document(value)) == value
    assert F.plan_id(value,H('incident')) == F.plan_id(changed,H('incident'))
    assert F.attempt_id(value,H('incident')) == F.attempt_id(changed,H('incident'))
    event = start(value)
    raw = F.event_bytes(event)
    body = json.loads(raw); claimed = body.pop('event_id')
    assert claimed == hashlib.sha256(b'tradegen-research-recovery-attempts/1\nevent\n'+encoded(body)).hexdigest()
    assert F.parse_event(raw) == event
    state = registered(value)
    assert F.state_digest(state) == hashlib.sha256(b'tradegen-research-recovery-attempts/1\nstate\n'+F.state_bytes(state)).hexdigest()


def test_artifact_identifier_retains_all_256_bits_for_every_initial_nibble():
    labels = []
    for first in '0123456789abcdef':
        original = first+'f'*63
        label = F.artifact_incident_id(original)
        assert len(label) == 53 and label.startswith('i')
        decoded = base64.b32decode(label[1:].upper()+'====').hex()
        assert decoded == original
        labels.append(label)
    assert len(set(labels)) == 16
    for invalid in ('F'*64, '0'*63, '../path', False):
        refused(lambda:F.artifact_incident_id(invalid))


def test_event_payload_is_detached_and_deeply_immutable():
    value = route()
    body = F.route_document(value)
    event = F.make_event('ROUTE_REGISTERED', body, observed_at=AT)
    raw = F.event_bytes(event)
    body['registration']['objects'][0]['byte_count'] = 999
    body['checkpoint']['owner_head'][0] = 999
    assert F.event_bytes(event) == raw
    assert type(event.payload) is MappingProxyType
    assert type(event.payload['source_root_ids']) is tuple
    try:
        event.payload['checkpoint']['code_hash'] = H('forged')
    except TypeError:
        pass
    else:
        raise AssertionError('mutable payload')


def test_exact_route_retry_and_same_identity_rewrite_cannot_reset_attempt_budget():
    value = route()
    state = registered(value)
    original = state.events[0]
    assert F.reduce(state, original) is state
    changed = replace(value, checkpoint=checkpoint(AT+timedelta(seconds=1), sequence=2))
    refused(lambda:F.reduce(state, F.make_event('ROUTE_REGISTERED', F.route_document(changed),
                                               observed_at=AT+timedelta(seconds=1))), 'RECOVERY_ROUTE_CONFLICT')
    state = F.reduce(state,start(value))
    again = start(value, at=AT+timedelta(seconds=60), current=checkpoint(AT+timedelta(seconds=60), sequence=3))
    refused(lambda:F.reduce(state,again), 'RECOVERY_ATTEMPT_EXISTS')


def test_start_then_exact_outcome_creates_one_result_outbox_without_hold_release():
    value = route()
    state = F.reduce(registered(value),start(value))
    pending = state.attempts[0]
    assert pending.phase == 'IN_PROGRESS' and pending.execution_count == 1
    assert not state.outbox
    event = observed(pending)
    state = F.reduce(state,event)
    assert state.attempts[0].phase == 'EXACT_ARCHIVE_RESTORED'
    assert state.attempts[0].terminal and len(state.outbox) == 1
    message = state.outbox[0]
    assert message.outcome_event_id == event.event_id and message.attempt_id == pending.attempt_id
    assert message.kind == 'RECOVERY_RESULT_RECORDED' and message.quarantine == 'REMAINS'
    assert message.current_use == 'NOT_GRANTED' and state.pending_notifications == state.outbox
    assert F.reduce(state,event) is state
    refused(lambda:F.reduce(state,resume(state.attempts[0],at=AT+timedelta(minutes=1))), 'RECOVERY_ATTEMPT_TERMINAL')


def test_preflight_authority_refusal_is_terminal_with_no_fabricated_checkpoint():
    value = route()
    event = preflight(value,status='AUTHORITY_REFUSED')
    state = F.reduce(registered(value),event)
    attempt = state.attempts[0]
    assert attempt.execution_count == 1 and attempt.phase == 'AUTHORITY_REFUSED' and attempt.terminal
    assert attempt.entries[0].checkpoint is None and attempt.outcomes[0].checkpoint is None
    assert len(state.outbox) == 1 and attempt.entries[0].kind == 'PREFLIGHT_REFUSED'
    restarted = F._replay_events(tuple(F.event_bytes(item) for item in state.events))
    refused(lambda:F.reduce(restarted,resume(attempt,at=AT+timedelta(minutes=1))), 'RECOVERY_ATTEMPT_TERMINAL')
    refused(lambda:F.reduce(restarted,preflight(value,number=2,at=AT+timedelta(minutes=1))), 'RECOVERY_ATTEMPT_TERMINAL')


def test_preflight_reads_share_same_three_opportunities_and_exact_due_boundary():
    value = route()
    state = F.reduce(registered(value),preflight(value))
    refused(lambda:F.reduce(state,resume(state.attempts[0],at=AT+timedelta(seconds=60,microseconds=-1))),
            'RECOVERY_RETRY_NOT_DUE')
    state = F.reduce(state,resume(state.attempts[0],at=AT+timedelta(seconds=60)))
    assert state.attempts[0].execution_count == 2 and state.attempts[0].phase == 'IN_PROGRESS'
    state = F.reduce(state,observed(state.attempts[0],at=AT+timedelta(seconds=61),status='PARTIAL_UNVERIFIED'))
    refused(lambda:F.reduce(state,resume(state.attempts[0],at=AT+timedelta(seconds=120))), 'RECOVERY_RETRY_NOT_DUE')
    state = F.reduce(state,preflight(value,number=3,at=AT+timedelta(seconds=121),status='RESOURCE_LIMIT',
        incident_head=(3,H('incident-3'))))
    assert state.attempts[0].execution_count == 3
    assert len(state.outbox) == 3
    # A fourth execution is structurally outside the finite event schema.
    refused(lambda:resume(state.attempts[0],at=AT+timedelta(seconds=181),number=4))


def test_in_progress_crash_resume_uses_same_plan_and_never_resets_count():
    value = route()
    state = F.reduce(registered(value),start(value))
    original = state.attempts[0]
    state = F._replay_events(tuple(F.event_bytes(item) for item in state.events))
    state = F.reduce(state,resume(original,at=AT+timedelta(seconds=60)))
    assert state.attempts[0].attempt_id == original.attempt_id
    assert state.attempts[0].artifact_incident_id == F.artifact_incident_id(H('incident'))
    assert state.attempts[0].execution_count == 2
    refused(lambda:F.reduce(state,resume(state.attempts[0],at=AT+timedelta(seconds=120),number=2)),
            'RECOVERY_EXECUTION_SEQUENCE_INVALID')


def test_unknown_clock_only_records_terminal_refusal_and_does_not_advance_time():
    value = route()
    state = F.reduce(registered(value),preflight(value,at=None,status='AUTHORITY_REFUSED'))
    assert state.last_trusted_at == AT
    assert state.attempts[0].entries[0].observed_at is None
    assert state.attempts[0].terminal
    refused(lambda:preflight(value,at=None,status='READ_UNAVAILABLE'))
    body = dict(route_id=value.route_id,incident_id=H('incident'),incident_head=[2,H('incident-2')],
                checkpoint=F.checkpoint_document(checkpoint()))
    refused(lambda:F.make_event('ATTEMPT_STARTED',body,observed_at=None))


def test_unknown_clock_after_start_still_records_terminal_outcome_and_keeps_evidence():
    value = route()
    state = F.reduce(registered(value),start(value))
    state = F.reduce(state,observed(state.attempts[0],at=None,status='AUTHORITY_REFUSED'))
    assert state.last_trusted_at == AT and state.attempts[0].terminal
    assert len(state.attempts[0].entries) == len(state.attempts[0].outcomes) == len(state.outbox) == 1


def test_checkpoint_currentness_exact_types_prefix_metadata_and_expiry_are_required():
    value = route()
    state = registered(value)
    for cp in (replace(checkpoint(), code_hash=H('other-code')),
               replace(checkpoint(), key_fingerprint='SHA256:'+H('other-owner')),
               checkpoint(label='rewritten-owner')):
        refused(lambda:F.reduce(state,start(value,current=cp)))
    stale_at = AT+timedelta(seconds=30,microseconds=1)
    refused(lambda:F.reduce(state,start(value,at=stale_at,current=checkpoint())), 'RECOVERY_CHECKPOINT_STALE')
    valid = F.reduce(state,start(value,at=AT+timedelta(seconds=30),current=checkpoint()))
    assert valid.attempts[0].execution_count == 1
    refused(lambda:F.reduce(state,start(value,at=value.expires_at,current=checkpoint(value.expires_at,sequence=2))),
            'RECOVERY_ORIGINAL_APPROVAL_EXPIRED')
    refused(lambda:replace(checkpoint(),owner_head=(0,H('empty'))))
    refused(lambda:replace(checkpoint(),owner_head=(True,H('empty'))))


def test_resume_checkpoint_cannot_rewind_prior_actual_observation_metadata():
    value = route()
    state = F.reduce(registered(value),start(value,current=checkpoint(sequence=5)))
    state = F.reduce(state,observed(state.attempts[0],status='READ_UNAVAILABLE'))
    refused(lambda:F.reduce(state,resume(state.attempts[0],at=AT+timedelta(minutes=1),
                                        current=checkpoint(AT+timedelta(minutes=1),sequence=4))),
            'RECOVERY_CHECKPOINT_ROLLBACK')
    bad = start(value)
    body = json.loads(F.event_bytes(bad))['payload']
    body['incident_head'] = [1,H('rewritten-incident')]
    refused(lambda:F.reduce(registered(value),F.make_event('ATTEMPT_STARTED',body,observed_at=AT)),
            'RECOVERY_CHECKPOINT_ROLLBACK')


def test_outcome_cannot_rewrite_prior_execution_or_claim_revoked_success():
    value = route()
    state = F.reduce(registered(value),start(value))
    attempt = state.attempts[0]
    refused(lambda:observed(attempt,revocation='REVOKED'))
    state = F.reduce(state,observed(attempt,status='READ_UNAVAILABLE'))
    refused(lambda:F.reduce(state,observed(attempt,reason='SECOND_FACT')), 'RECOVERY_OUTCOME_CONFLICT')
    state = F.reduce(state,resume(state.attempts[0],at=AT+timedelta(seconds=60)))
    old = observed(attempt,status='READ_UNAVAILABLE',at=AT+timedelta(seconds=60),reason='LATE_OLD')
    refused(lambda:F.reduce(state,old), 'RECOVERY_OUTCOME_CONFLICT')


def test_positive_observation_requires_full_artifact_destination_and_exact_time():
    value = route(); state = F.reduce(registered(value),start(value))
    body = json.loads(F.event_bytes(observed(state.attempts[0])))['payload']
    for key in ('checkpoint','verified_at','recovery_artifact_digest','destination_head'):
        refused(lambda:F.make_event('ATTEMPT_OBSERVED',{**body,key:None},observed_at=AT))
    changed = {**body,'verified_at':stamp(AT-timedelta(microseconds=1))}
    refused(lambda:F.reduce(state,F.make_event('ATTEMPT_OBSERVED',changed,observed_at=AT)),
            'RECOVERY_OBSERVATION_TIME_INVALID')


def test_reported_delivery_is_separate_and_never_changes_terminal_or_quarantine():
    value = route()
    state = F.reduce(registered(value),preflight(value,status='AUTHORITY_REFUSED'))
    original = state.attempts
    message = state.outbox[0]
    for label,result in (('send-a','unknown'),('send-b','failed')):
        state = F.reduce(state,delivery(message,label,outcome=result))
        assert state.pending_notifications == (message,)
    done = delivery(message,'send-c',outcome='delivered')
    state = F.reduce(state,done)
    assert not state.pending_notifications and state.attempts == original
    assert state.outbox[0].quarantine == 'REMAINS'
    assert F.reduce(state,done) is state
    refused(lambda:F.reduce(state,delivery(message,'send-d')), 'RECOVERY_MESSAGE_DELIVERED')
    refused(lambda:F.reduce(state,delivery(message,'send-a',outcome='delivered')), 'RECOVERY_DELIVERY_CONFLICT')
    refused(lambda:delivery(message,outcome='approved'))


def test_global_event_replay_is_idempotent_after_intervening_outcome():
    value = route()
    state = registered(value)
    event = start(value)
    state = F.reduce(state,event)
    state = F.reduce(state,observed(state.attempts[0],at=AT+timedelta(seconds=1)))
    assert F.reduce(state,event) is state
    assert state.attempts[0].execution_count == 1 and len(state.outbox) == 1


def test_limits_downward_counts_restrictive_retry_and_deleted_slot_diagnostics():
    for kwargs in ({'max_routes':True},{'max_attempts':0},{'max_new_attempts':2},{'max_resumes':3},
                   {'min_retry_seconds':59},{'max_event_bytes':2*1024*1024+1}):
        refused(lambda:F.RecoveryAttemptLimits(**kwargs),'RECOVERY_LIMITS_INVALID')
    one = replace(F.DEFAULT_LIMITS,max_resumes=0)
    value = route(); state = F.reduce(registered(value),start(value))
    refused(lambda:F.reduce(state,resume(state.attempts[0],at=AT+timedelta(seconds=60)),limits=one),
            'RECOVERY_EXECUTION_LIMIT')
    bad = F.RecoveryAttemptLimits(); object.__delattr__(bad,'max_routes')
    for call in (lambda:F.state_bytes(state,limits=bad),lambda:F.parse_event(F.event_bytes(start(value)),limits=bad),
                 lambda:F.parse_route(F.route_document(value),limits=bad),lambda:F.reduce(state,start(value),limits=bad)):
        refused(call,'RECOVERY_LIMITS_INVALID')


def test_exact_event_and_state_quota_boundaries_leave_prior_records_intact():
    value = route(); state = registered(value); event = start(value)
    raw = F.event_bytes(event)
    assert F.event_bytes(event,limits=replace(F.DEFAULT_LIMITS,max_event_bytes=len(raw))) == raw
    refused(lambda:F.event_bytes(event,limits=replace(F.DEFAULT_LIMITS,max_event_bytes=len(raw)-1)),'RECOVERY_RESOURCE_LIMIT')
    state_raw = F.state_bytes(state)
    assert F.state_bytes(state,limits=replace(F.DEFAULT_LIMITS,max_state_bytes=len(state_raw))) == state_raw
    refused(lambda:F.state_bytes(state,limits=replace(F.DEFAULT_LIMITS,max_state_bytes=len(state_raw)-1)),'RECOVERY_RESOURCE_LIMIT')
    other = route('b')
    refused(lambda:F.reduce(state,F.make_event('ROUTE_REGISTERED',F.route_document(other),observed_at=AT),
                            limits=replace(F.DEFAULT_LIMITS,max_routes=1)),'RECOVERY_RESOURCE_LIMIT')
    assert F.state_bytes(state) == state_raw


def test_strict_parser_rejects_duplicates_rehashed_wrong_types_and_extra_keys():
    raw = F.event_bytes(start(route()))
    refused(lambda:F.parse_event(b' '+raw))
    refused(lambda:F.parse_event(raw+b'\n'))
    refused(lambda:F.parse_event(raw.decode('ascii')))
    refused(lambda:F.parse_event(raw.replace(b'"schema":1',b'"schema":1,"schema":1')))
    def rewritten(change):
        doc=json.loads(raw); doc.update(change); body={k:v for k,v in doc.items() if k!='event_id'}
        doc['event_id']=hashlib.sha256(F.DOMAIN+b'event\n'+encoded(body)).hexdigest()
        return encoded(doc)
    for change in ({'schema':True},{'schema':1.0},{'extra':1},{'kind':'RELEASE'}):
        refused(lambda:F.parse_event(rewritten(change)))
    payload=json.loads(raw)['payload']; payload['checkpoint']['owner_head'][0]=True
    refused(lambda:F.parse_event(rewritten({'payload':payload})))
    refused(lambda:F.parse_event(b'['*100+b'0'+b']'*100),'RECOVERY_RESOURCE_LIMIT')


def test_route_exact_types_complete_dependency_snapshot_and_unknown_kind_refusal():
    value=route()
    for changes in ({'source_root_ids':((1,0),(1,11))},{'source_root_ids':((1,10),(1,10))},
                    {'destination_root_ids':value.source_root_ids},{'issued_at':AT.replace(tzinfo=None)},
                    {'expires_at':AT},{'expires_at':AT+timedelta(days=2)},
                    {'attestation_sha256':False},{'registration':object()}):
        refused(lambda:replace(value,**changes))
    document=F.route_document(value); document['route_id']=H('invented')
    refused(lambda:F.parse_route(document),'RECOVERY_ROUTE_ID_MISMATCH')
    for kind in ('RELEASE','RESTORE','APPROVE','RESET','SELL'):
        refused(lambda:F.make_event(kind,{},observed_at=AT))


def test_state_cannot_omit_outbox_outcome_or_restore_a_smaller_execution_count():
    value=route(); state=F.reduce(registered(value),preflight(value,status='AUTHORITY_REFUSED'))
    for changed in (replace(state,outbox=()),replace(state,attempts=()),replace(state,events=state.events[:-1]),
                    replace(state,last_trusted_at=AT+timedelta(seconds=1)),
                    replace(state,attempts=(replace(state.attempts[0],outcomes=()),)),
                    replace(state,events=state.events+(state.events[-1],))):
        refused(lambda:F.state_bytes(changed),'RECOVERY_STATE_INVALID')
    invalid=replace(state.outbox[0],current_use='GRANTED')
    refused(lambda:F.state_bytes(replace(state,outbox=(invalid,))),'RECOVERY_STATE_INVALID')


def test_nested_attempt_bound_refuses_before_projecting_any_excess_child():
    value=route(); state=F.reduce(registered(value),start(value))
    attempt=state.attempts[0]
    huge=replace(attempt,entries=attempt.entries*10000)
    original=F._projection
    def guard(item,cls):
        assert cls is not F.ExecutionEntry, 'nested projection ran before hard bound'
        return original(item,cls)
    with patch.object(F,'_projection',guard):
        refused(lambda:F.state_bytes(replace(state,attempts=(huge,))),'RECOVERY_RESOURCE_LIMIT')


def test_streaming_replay_parses_applies_each_row_once_and_refuses_persisted_noops():
    value=route(); route_event=F.make_event('ROUTE_REGISTERED',F.route_document(value),observed_at=AT)
    events=(route_event,)+tuple(preflight(value,incident=H(f'incident-{n}'),status='AUTHORITY_REFUSED') for n in range(64))
    raw=tuple(F.event_bytes(event) for event in events)
    parse,apply=F.parse_event,F._apply
    parsed=[]; applied=[]
    def parse_count(value,**kwargs):
        parsed.append(value); return parse(value,**kwargs)
    def apply_count(state,event,limits,**kwargs):
        applied.append(event.event_id); return apply(state,event,limits,**kwargs)
    with patch.object(F,'parse_event',parse_count), patch.object(F,'_apply',apply_count):
        state=F._replay_events(raw)
    assert len(parsed)==len(applied)==len(raw)==65
    assert len(state.attempts)==len(state.outbox)==64
    refused(lambda:F._replay_events(raw+(raw[-1],)),'RECOVERY_STATE_INVALID')
    refused(lambda:F._replay_events(events))


def test_arbitrary_foreign_or_mutated_frozen_state_has_fixed_refusal():
    class Trap:
        @property
        def events(self):
            raise AssertionError('foreign state property read')
    refused(lambda:F.state_bytes(Trap()),'RECOVERY_STATE_INVALID')
    value=route(); object.__delattr__(value,'source_root_ids')
    refused(lambda:F.route_document(value))
    event=start(route()); object.__setattr__(event,'schema',True)
    refused(lambda:F.event_bytes(event))
    state=F.initial_state(); object.__delattr__(state,'events')
    refused(lambda:F.state_bytes(state))
    refused(lambda:state.pending_notifications)


def test_forged_projection_string_bound_is_checked_before_json_encoding():
    value=route(); state=F.reduce(registered(value),preflight(value,status='AUTHORITY_REFUSED'))
    message=replace(state.outbox[0],reason_code='X'*1000000)
    with patch.object(F.I,'_encoded',side_effect=AssertionError('encoder called')):
        refused(lambda:F._projection(message,F.RecoveryNotification),'RECOVERY_RESOURCE_LIMIT')


def test_streaming_fold_indexes_large_routes_instead_of_hashing_inventory_per_event():
    values=[]
    for index in range(4):
        value=route(f'route-{index}')
        objects=tuple(sorted((IF.dependency(f'object-{index}-{part}') for part in range(64)),key=lambda item:item.sha256))
        value=replace(value,registration=replace(value.registration,objects=objects))
        values.append(value)
    routes=tuple(F.make_event('ROUTE_REGISTERED',F.route_document(value),observed_at=AT) for value in values)
    small=routes+tuple(preflight(values[index%4],incident=H(f'a-{index}'),status='AUTHORITY_REFUSED') for index in range(8))
    large=small+tuple(preflight(values[index%4],incident=H(f'b-{index}'),status='AUTHORITY_REFUSED') for index in range(128))
    small_raw=tuple(F.event_bytes(event) for event in small)
    large_raw=tuple(F.event_bytes(event) for event in large)
    original=F._route_doc
    def counted(raw):
        calls=[]
        def count(value):
            calls.append(value); return original(value)
        with patch.object(F,'_route_doc',count):
            state=F._replay_events(raw)
        return len(calls),state
    small_count,_=counted(small_raw)
    large_count,state=counted(large_raw)
    assert small_count == large_count, (small_count,large_count)
    assert len(state.attempts)==136 and len(state.routes)==4
