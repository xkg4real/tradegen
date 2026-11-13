"""Invented dependency metadata; no actual failures, send, source or authority."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import hashlib
import json
from types import MappingProxyType
from unittest.mock import patch

from execution_launch import research_incidents as F


AT = datetime(2026, 1, 1, tzinfo=timezone.utc)


def digest(label):
    return hashlib.sha256(label.encode('ascii')).hexdigest()


def encoded(document):
    return json.dumps(document, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('ascii')


def refused(call, code=None):
    try:
        call()
    except F.IncidentFormatError as exc:
        assert str(exc).startswith('INCIDENT_')
        if code is not None:
            assert str(exc) == code, (str(exc), code)
        return
    raise AssertionError('expected refusal')


def dependency(label='shared', *, raw=True, kind='chunk', size=7):
    return F.ObjectDependency(kind=kind, sha256=digest(label), byte_count=size, from_raw=raw)


def registration(label='a', *, store='store-a', original=None, raw=False, objects=None):
    original = original or label+'-raw'
    if raw:
        label = original
    return F.TargetRegistration(store_binding_sha256=digest(store), bundle_digest=digest(label),
        input_archive_digest=digest(original), bundle_kind='RAW_ARCHIVED' if raw else 'VERIFIED_UNAPPROVED',
        raw_manifest_sha256=digest(original+'-manifest'),
        verified_manifest_sha256=None if raw else digest(label+'-manifest'),
        graph_sha256=digest(label+'-graph'), catalog_head_sha256=digest('catalog'), catalog_sequence=1,
        objects=tuple(sorted(objects or (dependency(),), key=lambda obj:obj.sha256)))


def registered(*items):
    state = F.initial_state()
    for item in items:
        state = F.reduce(state, F.make_event('REGISTER', F.registration_document(item), observed_at=AT))
    return state


def failure(item, *, scope='TARGET', objects=(), at=AT, category='INTEGRITY_FAILURE', reason='TEST_INTEGRITY'):
    return F.make_event('FAILURE', dict(store_binding_sha256=item.store_binding_sha256,
        bundle_digest=item.bundle_digest, scope=scope, failed_objects=list(sorted(objects)),
        category=category, reason_code=reason), observed_at=at)


def delivery(message, attempt='attempt-a', *, outcome='unknown', at=AT):
    return F.make_event('DELIVERY', dict(message_id=message.message_id, attempt_id=attempt, outcome=outcome), observed_at=at)


def resign(document):
    body = {key:value for key, value in document.items() if key != 'event_id'}
    return {**body, 'event_id':hashlib.sha256(b'tradegen-research-incidents/1\nevent\n'+encoded(body)).hexdigest()}


def test_exact_event_and_state_domain_bytes_roundtrip_without_authority():
    item = registration()
    body = dict(schema=1, kind='REGISTER', observed_at='2026-01-01T00:00:00.000000Z',
                payload=F.registration_document(item))
    expected = {**body, 'event_id':hashlib.sha256(b'tradegen-research-incidents/1\nevent\n'+encoded(body)).hexdigest()}
    event = F.make_event('REGISTER', F.registration_document(item), observed_at=AT)
    assert F.event_bytes(event) == encoded(expected)
    assert F.parse_event(encoded(expected)) == event
    state = F.reduce(F.initial_state(), event)
    raw = F.state_bytes(state)
    assert F.state_digest(state) == hashlib.sha256(b'tradegen-research-incidents/1\nstate\n'+raw).hexdigest()
    assert not any(word in json.loads(raw) for word in ('approved', 'execution_ready', 'source_authenticated'))


def test_payload_is_detached_deeply_immutable_and_documents_are_fresh():
    item = registration()
    body = F.registration_document(item)
    event = F.make_event('REGISTER', body, observed_at=AT)
    original = F.event_bytes(event)
    body['objects'][0]['byte_count'] = 999
    body['objects'].append(dict(body['objects'][0]))
    assert F.event_bytes(event) == original
    assert type(event.payload) is MappingProxyType
    assert type(event.payload['objects']) is tuple
    try:
        event.payload['objects'][0]['byte_count'] = 999
    except TypeError:
        pass
    else:
        raise AssertionError('nested payload mutable')
    F.registration_document(item)['objects'].clear()
    assert len(item.objects) == 1


def test_registration_exact_replay_and_conflicting_graph_refused():
    item = registration()
    event = F.make_event('REGISTER', F.registration_document(item), observed_at=AT)
    state = F.reduce(F.initial_state(), event)
    assert F.reduce(state, event) is state
    identical = F.make_event('REGISTER', F.registration_document(item), observed_at=AT+timedelta(seconds=1))
    assert F.reduce(state, identical) is state
    changed = replace(item, graph_sha256=digest('changed'))
    refused(lambda:F.reduce(state, F.make_event('REGISTER', F.registration_document(changed), observed_at=AT)),
            'INCIDENT_REGISTRATION_CONFLICT')
    # Catalogue growth is not permission to overwrite the original registration.
    changed = replace(item, catalog_sequence=2, catalog_head_sha256=digest('later-head'))
    refused(lambda:F.reduce(state, F.make_event('REGISTER', F.registration_document(changed), observed_at=AT)),
            'INCIDENT_REGISTRATION_CONFLICT')


def test_incident_and_one_outbox_intent_are_derived_in_same_transition():
    item = registration()
    before = registered(item)
    event = failure(item)
    after = F.reduce(before, event)
    assert not before.incidents and not before.outbox
    assert len(after.incidents) == len(after.outbox) == 1
    incident, message = after.incidents[0], after.outbox[0]
    assert incident.incident_id == event.event_id == message.incident_id
    assert incident.affected_bundle_digests == (item.bundle_digest,)
    assert incident.affected_raw_digests == ()
    body = dict(incident_id=event.event_id, kind='RESEARCH_EVIDENCE_HELD',
        bundle_digest=item.bundle_digest, category='INTEGRITY_FAILURE', reason_code='TEST_INTEGRITY')
    assert message.message_id == hashlib.sha256(b'tradegen-research-incidents/1\nnotification\n'+encoded(body)).hexdigest()
    assert after.pending_notifications == after.outbox


def test_target_failure_holds_exact_bundle_copy_but_not_other_variant_or_store():
    target = registration('a', original='shared-raw')
    sibling = registration('b', original='shared-raw')
    unrelated = registration('c', store='store-b')
    state = F.reduce(registered(target, sibling, unrelated), failure(target))
    copied = replace(target, store_binding_sha256=digest('store-copy'))
    assert F.blocked_incidents(state, target) == state.incidents
    assert F.blocked_incidents(state, copied) == state.incidents
    assert not F.blocked_incidents(state, sibling)
    assert not F.blocked_incidents(state, unrelated)


def test_raw_target_failure_holds_every_variant_of_that_original_only():
    original = registration(original='raw-a', raw=True)
    derived = registration('derived-a', original='raw-a', store='other-store')
    other = registration('independent')
    state = F.reduce(registered(original, derived, other), failure(original))
    assert state.incidents[0].affected_raw_digests == (original.bundle_digest,)
    assert F.blocked_incidents(state, derived)
    assert not F.blocked_incidents(state, other)


def test_object_scope_tracks_raw_membership_and_does_not_globally_poison_content():
    shared = dependency('shared', raw=False)
    raw_obj = dependency('raw-only')
    target = registration('a', objects=(shared, raw_obj))
    sibling = registration('b', objects=(shared, dependency('b-raw')))
    raw_dependent = registration('c', objects=(replace(shared, from_raw=True),))
    foreign = registration('d', store='foreign', objects=(replace(shared, from_raw=True),))
    state = F.reduce(registered(target, sibling, raw_dependent, foreign),
                     failure(target, scope='OBJECTS', objects=(shared.sha256,)))
    incident = state.incidents[0]
    assert incident.affected_bundle_digests == tuple(sorted((target.bundle_digest, sibling.bundle_digest, raw_dependent.bundle_digest)))
    assert incident.affected_raw_digests == (raw_dependent.input_archive_digest,)
    assert not F.blocked_incidents(state, foreign)
    copy = registration('c-variant', original='c-raw', store='foreign')
    assert F.blocked_incidents(state, copy)
    unrelated_variant = registration('a-variant', original='a-raw', store='foreign')
    assert not F.blocked_incidents(state, unrelated_variant)


def test_late_object_dependent_then_cross_store_copy_inherits_existing_hold():
    obj = dependency('failed')
    original = registration('a', objects=(obj,))
    state = F.reduce(registered(original), failure(original, scope='OBJECTS', objects=(obj.sha256,)))
    historical = state.incidents[0]
    late = registration('late', objects=(obj,))
    state = F.reduce(state, F.make_event('REGISTER', F.registration_document(late), observed_at=AT))
    copy = replace(late, store_binding_sha256=digest('other-store'))
    state = F.reduce(state, F.make_event('REGISTER', F.registration_document(copy), observed_at=AT))
    assert state.incidents[0] == historical
    assert late.bundle_digest not in historical.affected_bundle_digests
    assert F.blocked_incidents(state, copy) == (historical,)
    variant = registration('late-new-version', original='late-raw', store='third-store')
    assert F.blocked_incidents(state, variant) == (historical,)


def test_store_scope_covers_later_registration_and_copy_without_broad_foreign_hold():
    first = registration('a')
    unrelated = registration('foreign', store='foreign')
    state = F.reduce(registered(first, unrelated), failure(first, scope='STORE', category='READ_UNAVAILABLE'))
    late = registration('late', objects=(dependency('entirely-new-object'),))
    assert F.blocked_incidents(state, late)
    state = F.reduce(state, F.make_event('REGISTER', F.registration_document(late), observed_at=AT))
    copied = replace(late, store_binding_sha256=digest('foreign'))
    assert F.blocked_incidents(state, copied)
    assert not F.blocked_incidents(state, unrelated)


def test_same_sha_incompatible_kind_or_length_refuses_instead_of_normalizing():
    obj = dependency()
    state = registered(registration('a', objects=(obj,)))
    for changed in (replace(obj, kind='manifest'), replace(obj, byte_count=8)):
        next_item = registration('b', store='foreign', objects=(changed,))
        event = F.make_event('REGISTER', F.registration_document(next_item), observed_at=AT)
        refused(lambda:F.reduce(state, event), 'INCIDENT_DEPENDENCY_CONFLICT')
    refused(lambda:registration(objects=(obj, replace(obj, kind='manifest'))))


def test_failure_requires_existing_target_and_known_nonempty_object_set():
    item = registration()
    refused(lambda:F.reduce(F.initial_state(), failure(item)), 'INCIDENT_TARGET_UNREGISTERED')
    state = registered(item)
    refused(lambda:F.reduce(state, failure(item, scope='OBJECTS', objects=(digest('unknown'),))),
            'INCIDENT_DEPENDENCY_UNKNOWN')
    refused(lambda:failure(item, scope='OBJECTS'))
    refused(lambda:failure(item, scope='TARGET', objects=(item.objects[0].sha256,)))


def test_unknown_failure_time_keeps_last_trusted_time_and_normal_rollback_refuses():
    item = registration()
    state = registered(item)
    later = failure(item, at=AT+timedelta(seconds=10))
    state = F.reduce(state, later)
    unknown = failure(item, at=None, reason='CLOCK_UNKNOWN')
    state = F.reduce(state, unknown)
    assert state.last_trusted_at == AT+timedelta(seconds=10)
    assert state.incidents[-1].observed_at is None
    assert F.reduce(state, unknown) is state
    refused(lambda:F.reduce(state, failure(item, at=AT+timedelta(seconds=9), reason='EARLIER')),
            'INCIDENT_CLOCK_ROLLBACK')
    state = F.reduce(state, failure(item, at=AT+timedelta(seconds=10), reason='SAME_TIME'))
    assert len(state.incidents) == 3


def test_global_event_retry_after_intervening_event_does_not_duplicate_outbox():
    item = registration()
    state = registered(item)
    first = failure(item, reason='FIRST')
    second = failure(item, reason='SECOND', at=AT+timedelta(seconds=1))
    state = F.reduce(F.reduce(state, first), second)
    assert F.reduce(state, first) is state
    assert len(state.outbox) == len(state.incidents) == 2


def test_unknown_failed_delivery_retry_then_delivered_keeps_all_restrictions():
    item = registration()
    state = F.reduce(registered(item), failure(item))
    message = state.outbox[0]
    original = state.incidents
    for attempt, outcome in (('attempt-a', 'unknown'), ('attempt-b', 'failed')):
        state = F.reduce(state, delivery(message, attempt, outcome=outcome))
        assert state.pending_notifications == (message,)
    done = delivery(message, 'attempt-c', outcome='delivered')
    state = F.reduce(state, done)
    assert not state.pending_notifications
    assert state.incidents == original and F.blocked_incidents(state, item) == original
    assert F.reduce(state, done) is state
    refused(lambda:F.reduce(state, delivery(message, 'attempt-d', outcome='unknown')),
            'INCIDENT_MESSAGE_DELIVERED')


def test_delivery_attempt_conflict_unknown_target_and_no_approval_outcome():
    item = registration()
    state = F.reduce(registered(item), failure(item))
    message = state.outbox[0]
    event = delivery(message)
    state = F.reduce(state, event)
    refused(lambda:F.reduce(state, delivery(message, outcome='delivered')), 'INCIDENT_DELIVERY_CONFLICT')
    refused(lambda:F.reduce(state, delivery(message, at=AT+timedelta(seconds=1))), 'INCIDENT_DELIVERY_CONFLICT')
    other = replace(message, message_id=digest('absent'))
    refused(lambda:F.reduce(state, delivery(other, 'new-attempt')), 'INCIDENT_MESSAGE_UNKNOWN')
    refused(lambda:delivery(message, outcome='approved'))
    refused(lambda:delivery(message, at=None))


def test_registration_shape_and_exact_primitive_types_are_enforced():
    item = registration()
    for kwargs in ({'catalog_sequence':True}, {'catalog_sequence':0}, {'objects':list(item.objects)},
                   {'verified_manifest_sha256':None}, {'bundle_digest':item.input_archive_digest},
                   {'bundle_kind':'APPROVED'}, {'store_binding_sha256':'A'*64}):
        refused(lambda:replace(item, **kwargs))
    for kwargs in ({'byte_count':True}, {'byte_count':0}, {'byte_count':2**63},
                   {'from_raw':1}, {'kind':'file'}, {'sha256':'../x'}):
        refused(lambda:replace(item.objects[0], **kwargs))
    raw = registration(raw=True)
    refused(lambda:replace(raw, verified_manifest_sha256=digest('not-none')))
    refused(lambda:replace(raw, objects=(replace(raw.objects[0], from_raw=False),)))


def test_parser_rejects_duplicate_keys_nonexact_wire_and_bad_identity():
    event = failure(registration())
    raw = F.event_bytes(event)
    refused(lambda:F.parse_event(b' '+raw))
    refused(lambda:F.parse_event(raw+b'\n'))
    refused(lambda:F.parse_event(raw.decode('ascii')))
    refused(lambda:F.parse_event(raw.replace(b'"schema":1', b'"schema":1,"schema":1')))
    document = json.loads(raw)
    refused(lambda:F.parse_event(encoded({**document, 'event_id':'0'*64})), 'INCIDENT_EVENT_ID_MISMATCH')
    for change in ({'schema':True}, {'schema':1.0}, {'extra':False}, {'kind':'RELEASE'}):
        refused(lambda:F.parse_event(encoded(resign({**document, **change}))))


def test_parser_rejects_rehashed_invalid_payload_not_just_stale_hash():
    document = json.loads(F.event_bytes(failure(registration())))
    for changes in ({'category':'NUMERICAL_FAILURE'}, {'category':'SUCCESS'}, {'scope':'GLOBAL'},
                    {'reason_code':'a path or amount'}, {'reason_code':'X'*97}, {'extra':'ignored'},
                    {'failed_objects':[digest('x')]}, {'bundle_digest':False}):
        changed = {**document, 'payload':{**document['payload'], **changes}}
        refused(lambda:F.parse_event(encoded(resign(changed))))
    for at in ('2026-01-01T00:00:00+00:00', '2026-01-01T00:00:00.000000+00:00',
               '2026-01-01T00:00:00.000000Zextra', False):
        refused(lambda:F.parse_event(encoded(resign({**document, 'observed_at':at}))))


def test_parser_depth_bytes_and_integer_bounds_refuse_before_interpretation():
    refused(lambda:F.parse_event(b'['*100+b'0'+b']'*100), 'INCIDENT_RESOURCE_LIMIT')
    refused(lambda:F.parse_event(b' '*17, limits=replace(F.DEFAULT_LIMITS, max_event_bytes=16)), 'INCIDENT_RESOURCE_LIMIT')
    raw = F.event_bytes(F.make_event('REGISTER', F.registration_document(registration()), observed_at=AT))
    refused(lambda:F.parse_event(raw.replace(b'"catalog_sequence":1', b'"catalog_sequence":999999999999999999999')))
    refused(lambda:F.parse_event(raw.replace(b'"catalog_sequence":1', b'"catalog_sequence":NaN')))


def test_limits_are_exact_downward_only_and_deleted_slots_have_fixed_diagnostics():
    for kwargs in ({'max_targets':True}, {'max_incidents':0}, {'max_attempts':8193}, {'max_state_bytes':-1}):
        refused(lambda:F.IncidentLimits(**kwargs), 'INCIDENT_LIMITS_INVALID')
    bad = F.IncidentLimits()
    object.__delattr__(bad, 'max_targets')
    event = failure(registration())
    state = F.initial_state()
    for call in (lambda:F.event_bytes(event, limits=bad), lambda:F.parse_event(F.event_bytes(event), limits=bad),
                 lambda:F.state_bytes(state, limits=bad), lambda:F.state_digest(state, limits=bad),
                 lambda:F.reduce(state, event, limits=bad),
                 lambda:F.parse_registration(F.registration_document(registration()), limits=bad)):
        refused(call, 'INCIDENT_LIMITS_INVALID')


def test_capacity_limits_refuse_without_truncating_prior_state():
    item = registration()
    state = registered(item)
    before = F.state_bytes(state)
    other = registration('b')
    limits = replace(F.DEFAULT_LIMITS, max_targets=1)
    refused(lambda:F.reduce(state, F.make_event('REGISTER', F.registration_document(other), observed_at=AT), limits=limits),
            'INCIDENT_RESOURCE_LIMIT')
    state = F.reduce(state, failure(item))
    limits = replace(F.DEFAULT_LIMITS, max_incidents=1)
    refused(lambda:F.reduce(state, failure(item, reason='SECOND'), limits=limits), 'INCIDENT_RESOURCE_LIMIT')
    limited = replace(F.DEFAULT_LIMITS, max_state_bytes=len(F.state_bytes(state))-1)
    refused(lambda:F.state_bytes(state, limits=limited), 'INCIDENT_RESOURCE_LIMIT')
    assert F.state_bytes(registered(item)) == before
    state = F.reduce(state, delivery(state.outbox[0]))
    refused(lambda:F.reduce(state, delivery(state.outbox[0], 'second'),
                            limits=replace(F.DEFAULT_LIMITS, max_attempts=1)), 'INCIDENT_RESOURCE_LIMIT')


def test_dependency_and_event_byte_limits_have_exact_boundary():
    item = registration(objects=(dependency('one'), dependency('two')))
    document = F.registration_document(item)
    refused(lambda:F.parse_registration(document, limits=replace(F.DEFAULT_LIMITS, max_dependencies_per_target=1)),
            'INCIDENT_RESOURCE_LIMIT')
    event = F.make_event('REGISTER', document, observed_at=AT)
    raw = F.event_bytes(event)
    exact = replace(F.DEFAULT_LIMITS, max_event_bytes=len(raw))
    assert F.event_bytes(event, limits=exact) == raw
    assert F.parse_event(raw, limits=exact) == event
    refused(lambda:F.event_bytes(event, limits=replace(exact, max_event_bytes=len(raw)-1)), 'INCIDENT_RESOURCE_LIMIT')


def test_state_projection_tampering_and_omitted_outbox_are_not_trusted():
    item = registration()
    state = F.reduce(registered(item), failure(item))
    for changed in (replace(state, outbox=()), replace(state, incidents=()),
                    replace(state, registrations=()), replace(state, events=state.events[:-1]),
                    replace(state, last_trusted_at=AT+timedelta(seconds=1)),
                    replace(state, events=state.events+(state.events[-1],))):
        refused(lambda:F.state_bytes(changed), 'INCIDENT_STATE_INVALID')
        refused(lambda:F.reduce(changed, failure(item, reason='SECOND')), 'INCIDENT_STATE_INVALID')
        refused(lambda:F.blocked_incidents(changed, item), 'INCIDENT_STATE_INVALID')
    invalid_incident = replace(state.incidents[0], affected_bundle_digests=list(state.incidents[0].affected_bundle_digests))
    refused(lambda:F.state_bytes(replace(state, incidents=(invalid_incident,))), 'INCIDENT_STATE_INVALID')
    invalid_message = replace(state.outbox[0], kind=True)
    refused(lambda:F.state_bytes(replace(state, outbox=(invalid_message,))), 'INCIDENT_STATE_INVALID')


def test_mutated_frozen_instances_and_wrong_types_normalize_without_getattr_hooks():
    item = registration()
    event = failure(item)
    object.__setattr__(event, 'schema', True)
    refused(lambda:F.event_bytes(event))
    object.__delattr__(item, 'graph_sha256')
    refused(lambda:F.registration_document(item))
    class Trap:
        @property
        def events(self):
            raise AssertionError('must not inspect foreign type')
    refused(lambda:F.state_bytes(Trap()), 'INCIDENT_STATE_INVALID')
    refused(lambda:F.reduce(Trap(), event), 'INCIDENT_STATE_INVALID')
    state = F.initial_state()
    object.__delattr__(state, 'events')
    refused(lambda:F.state_bytes(state))
    refused(lambda:state.pending_notifications)


def test_all_four_failure_categories_restrict_without_any_release_event():
    item = registration()
    state = registered(item)
    for category in ('INTEGRITY_FAILURE', 'READ_UNAVAILABLE', 'RESOURCE_LIMIT', 'VALIDATION_REFUSED'):
        state = F.reduce(state, failure(item, category=category, reason=category))
    assert len(F.blocked_incidents(state, item)) == len(state.outbox) == 4
    for kind in ('REPAIR', 'RELEASE', 'EXPIRE', 'RESUME', 'APPROVE', 'SELL'):
        refused(lambda:F.make_event(kind, {}, observed_at=AT))


def test_streaming_replay_applies_each_strict_event_once_and_refuses_duplicate_rows():
    item = registration()
    first = F.make_event('REGISTER', F.registration_document(item), observed_at=AT)
    events = (first,)+tuple(failure(item, reason=f'READ_FAILURE_{index}') for index in range(128))
    raw_events = tuple(F.event_bytes(event) for event in events)
    original_apply = F._apply
    calls = []
    def counted(state, event, limits):
        calls.append(event.event_id)
        return original_apply(state, event, limits)
    with patch.object(F, '_apply', counted):
        state = F._replay_events(raw_events)
    assert len(calls) == len(events) == len(set(calls))
    assert len(state.incidents) == len(state.outbox) == 128
    assert len(state.events) == len(events)
    assert F.state_bytes(state)
    refused(lambda:F._replay_events(raw_events+(raw_events[-1],)), 'INCIDENT_STATE_INVALID')
    refused(lambda:F._replay_events(raw_events+(F.event_bytes(F.make_event('REGISTER', F.registration_document(item), observed_at=AT)),)),
            'INCIDENT_STATE_INVALID')
    bad = json.loads(raw_events[0])
    bad['payload']['catalog_sequence'] = True
    refused(lambda:F._replay_events((encoded(resign(bad)),)))
    refused(lambda:F._replay_events(events))
