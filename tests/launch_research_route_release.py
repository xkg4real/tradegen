"""Pure invented route/registration metadata, never actual research permission.

No source, signature, recovery attempt or owner verification occurs here. These
checks establish exact records and unchanged general holds; actual consumers
must independently establish provenance and current authority on every use.
"""
from copy import deepcopy
from dataclasses import replace
from datetime import timedelta
import hashlib
import json
from types import MappingProxyType
from unittest.mock import patch

from execution_launch import research_incidents as F
from tests import launch_research_incidents as H

AT = H.AT
KIND = 'RESEARCH_ROUTE_RELEASE'
SOURCE_PURPOSE = 'strategy_source_and_fixed_implementation_review'
CARRY_PURPOSE = 'strategy_source_and_fixed_carry_implementation_review'


def stamp(at):
    return at.isoformat(timespec='microseconds').replace('+00:00', 'Z')


def fixture(*, scope='TARGET'):
    source = H.registration('sealed-study', store='source-store')
    destination = replace(source, store_binding_sha256=H.digest('destination-store'),
        catalog_head_sha256=H.digest('destination-catalog'), catalog_sequence=2)
    state = H.registered(source, destination)
    event = H.failure(source, scope=scope, objects=(source.objects[0].sha256,) if scope == 'OBJECTS' else (),
                      at=AT+timedelta(seconds=1))
    state = F.reduce(state, event)
    return state, source, destination


def binding(state, source, destination, *, label='a'):
    selection = {name:H.digest(label+'-'+name) for name in (
        'attestation_sha256', 'revocation_target_sha256', 'family_sha256', 'program_sha256',
        'protocol_sha256', 'evidence_sha256', 'profile_contract_sha256', 'rule_terms_sha256',
        'window_sha256', 'driver_identity_sha256')}
    selection.update(bundle_digest=source.bundle_digest, input_archive_digest=source.input_archive_digest,
        selected_study_id='Study.A', evaluated_at=stamp(AT-timedelta(seconds=1)),
        approval_expires_at=stamp(AT+timedelta(minutes=5)), source_reviews=[dict(study_id='Study.A',
            document_sha256=H.digest('source-review'), purpose=SOURCE_PURPOSE,
            revocation_target_sha256=H.digest('source-target'), audit_logical_id='study-a-audit',
            audit_sha256=H.digest('audit'))])
    result = {name:H.digest(label+'-'+name) for name in (
        'route_id', 'attempt_id', 'outcome_event_id', 'incident_namespace_sha256',
        'attempt_namespace_sha256', 'recovery_artifact_digest')}
    result.update(incident_id=state.incidents[0].incident_id,
        source_store_binding_sha256=source.store_binding_sha256,
        source_registration_sha256=F.registration_digest(source),
        destination_store_binding_sha256=destination.store_binding_sha256,
        destination_registration_sha256=F.registration_digest(destination),
        bundle_digest=source.bundle_digest, input_archive_digest=source.input_archive_digest,
        graph_sha256=source.graph_sha256, selection=selection)
    return result


def payload(state, source, destination, *, label='a'):
    value = binding(state, source, destination, label=label)
    return dict(release_schema=1, scope='recovered_research_selection', binding=value,
        binding_sha256=F.research_release_binding_digest(value),
        incident_head=[len(state.events), H.digest('incident-head')],
        attempt_head=[3, H.digest('attempt-head')], destination_head=[2, H.digest('destination-head')],
        owner_checkpoint=dict(key_fingerprint='SHA256:'+H.digest('owner-key'), code_hash=H.digest('owner-code'),
            owner_head=[4, H.digest('owner-head')], observed_at=stamp(AT+timedelta(seconds=2))))


def release(state, source, destination, *, label='a', at=None):
    return F.make_event(KIND, payload(state, source, destination, label=label),
                        observed_at=at or AT+timedelta(seconds=3))


def raw_payload(document, *, at=None):
    body = dict(schema=1, kind=KIND, observed_at=stamp(at or AT+timedelta(seconds=3)), payload=document)
    return H.encoded(H.resign(body))


def projected(state):
    return state.registrations, state.incidents, state.outbox, state.receipts


def test_exact_domains_roundtrip_query_and_general_holds_remain_non_authoritative():
    state, source, destination = fixture()
    document = payload(state, source, destination)
    expected = hashlib.sha256(b'tradegen-research-route-release-binding/1\n'+H.encoded(document['binding'])).hexdigest()
    assert document['binding_sha256'] == expected
    assert F.registration_digest(source) == hashlib.sha256(
        b'tradegen-research-release-registration/1\n'+H.encoded(F.registration_document(source))).hexdigest()
    event = release(state, source, destination)
    assert F.event_bytes(event) == raw_payload(document)
    parsed = F.parse_event(F.event_bytes(event))
    assert parsed == event
    after = F.reduce(state, parsed)
    assert projected(after) == projected(state) and after.pending_notifications == state.pending_notifications
    assert F.research_route_releases(after)[0] is after.events[-1]
    assert F.research_route_releases(after)[0] == parsed
    assert F.blocked_incidents(after, source) == F.blocked_incidents(state, source)
    assert F.blocked_incidents(after, destination) == F.blocked_incidents(state, destination)
    assert not any(name in json.loads(F.state_bytes(after)) for name in
                   ('releases', 'approved', 'execution_ready', 'source_authenticated', 'quarantine_released'))


def test_legacy_event_state_and_domain_bytes_are_exact_independent_wire_reference():
    # A closed v1 history, assembled independently of the new reducer/projections.
    reg = dict(store_binding_sha256='a'*64, bundle_digest='b'*64, input_archive_digest='c'*64,
        bundle_kind='VERIFIED_UNAPPROVED', raw_manifest_sha256='d'*64, verified_manifest_sha256='e'*64,
        graph_sha256='f'*64, catalog_head_sha256='1'*64, catalog_sequence=1,
        objects=[dict(kind='chunk', sha256='2'*64, byte_count=7, from_raw=True)])
    first = H.resign(dict(schema=1, kind='REGISTER', observed_at=stamp(AT), payload=reg))
    failure = dict(store_binding_sha256='a'*64, bundle_digest='b'*64, scope='TARGET', failed_objects=[],
                   category='INTEGRITY_FAILURE', reason_code='TEST_INTEGRITY')
    second = H.resign(dict(schema=1, kind='FAILURE', observed_at=stamp(AT), payload=failure))
    intent = dict(incident_id=second['event_id'], kind='RESEARCH_EVIDENCE_HELD', bundle_digest='b'*64,
                  category='INTEGRITY_FAILURE', reason_code='TEST_INTEGRITY')
    message = hashlib.sha256(b'tradegen-research-incidents/1\nnotification\n'+H.encoded(intent)).hexdigest()
    receipt = dict(message_id=message, attempt_id='attempt-a', outcome='unknown')
    third = H.resign(dict(schema=1, kind='DELIVERY', observed_at=stamp(AT), payload=receipt))
    raw_events = tuple(H.encoded(item) for item in (first, second, third))
    state = F._replay_events(raw_events)
    expected = dict(schema=1, last_trusted_at=stamp(AT), registrations=[reg],
        incidents=[dict(incident_id=second['event_id'], **failure, observed_at=stamp(AT),
                        affected_bundle_digests=['b'*64], affected_raw_digests=[])],
        outbox=[dict(message_id=message, **intent)], receipts=[dict(**receipt, observed_at=stamp(AT))],
        events=[first, second, third])
    raw = H.encoded(expected)
    assert F.state_bytes(state) == raw
    assert tuple(F.event_bytes(item) for item in state.events) == raw_events
    assert F.state_digest(state) == hashlib.sha256(b'tradegen-research-incidents/1\nstate\n'+raw).hexdigest()
    assert F.research_route_releases(state) == ()
    for kind in ('RELEASE', 'APPROVE', 'SELL', 'REPAIR', 'EXPIRE', 'RESUME'):
        H.refused(lambda:F.make_event(kind, {}, observed_at=AT))


def test_release_documents_detach_every_nested_collection_without_changing_general_state():
    state, source, destination = fixture()
    document = payload(state, source, destination)
    event = F.make_event(KIND, document, observed_at=AT+timedelta(seconds=3))
    before = F.event_bytes(event)
    document['binding']['selection']['source_reviews'][0]['purpose'] = 'APPROVE'
    document['owner_checkpoint']['owner_head'][0] = 999
    document['incident_head'].clear()
    assert F.event_bytes(event) == before
    assert type(event.payload) is MappingProxyType
    assert type(event.payload['binding']['selection']['source_reviews']) is tuple
    try:
        event.payload['binding']['selection']['source_reviews'][0]['purpose'] = 'APPROVE'
    except TypeError:
        pass
    else:
        raise AssertionError('nested review record is mutable')
    after = F.reduce(state, event)
    assert projected(after) == projected(state)


def test_every_release_object_is_closed_against_extra_and_missing_fields():
    state, source, destination = fixture()
    original = payload(state, source, destination)
    paths = ((), ('binding',), ('binding','selection'), ('binding','selection','source_reviews',0),
             ('owner_checkpoint',))
    for path in paths:
        for extra in (True, False):
            document = deepcopy(original)
            item = document
            for name in path:
                item = item[name]
            if extra:
                item['authority_granted'] = True
            else:
                del item[next(iter(item))]
            H.refused(lambda:F.parse_event(raw_payload(document)))


def test_release_exact_primitive_hash_head_and_fingerprint_constraints():
    state, source, destination = fixture()
    original = payload(state, source, destination)
    for updates in ({'release_schema':True}, {'release_schema':2}, {'scope':'trade_activation'},
                    {'binding_sha256':'A'*64}, {'incident_head':[True,'a'*64]},
                    {'incident_head':[0,'a'*64]}, {'attempt_head':[2**63,'a'*64]},
                    {'destination_head':[1,'a'*63]}, {'destination_head':[1,'a'*64,'extra']}):
        H.refused(lambda:F.parse_event(raw_payload(original|updates)))
    for updates in ({'key_fingerprint':'SHA256:'+'A'*64}, {'key_fingerprint':'a'*64},
                    {'code_hash':False}, {'owner_head':[0,'a'*64]}, {'owner_head':[True,'a'*64]}):
        H.refused(lambda:F.parse_event(raw_payload(original|{'owner_checkpoint':original['owner_checkpoint']|updates})))
    for name in ('route_id','attempt_id','outcome_event_id','incident_id','incident_namespace_sha256',
                 'attempt_namespace_sha256','source_store_binding_sha256','destination_registration_sha256'):
        document = deepcopy(original); document['binding'][name] = False
        H.refused(lambda:F.parse_event(raw_payload(document)))


def test_review_ids_purposes_sort_uniqueness_membership_and_inventory_cap():
    state, source, destination = fixture()
    original = binding(state, source, destination)
    review = original['selection']['source_reviews'][0]
    bad_reviews = ([], [review, review], [review|{'study_id':'Study.Z'}, review],
        [review|{'study_id':'1wrong'}], [review|{'audit_logical_id':'../audit'}],
        [review|{'purpose':'research_archive_manifest_attestation'}],
        [review|{'purpose':'owner.code'}], [review|{'document_sha256':'a'*63}])
    for reviews in bad_reviews:
        value = deepcopy(original); value['selection']['source_reviews'] = reviews
        H.refused(lambda:F.research_release_binding_digest(value))
    value = deepcopy(original); value['selection']['selected_study_id'] = 'Missing'
    H.refused(lambda:F.research_release_binding_digest(value))
    value = deepcopy(original)
    value['selection']['source_reviews'] = [review|{'study_id':f'Study.{index:03d}'} for index in range(128)]
    value['selection']['selected_study_id'] = 'Study.000'
    assert F.research_release_binding_digest(value)
    value['selection']['source_reviews'].append(review|{'study_id':'Study.128'})
    H.refused(lambda:F.research_release_binding_digest(value), 'INCIDENT_RESOURCE_LIMIT')
    value = deepcopy(original); value['selection']['source_reviews'][0]['purpose'] = CARRY_PURPOSE
    assert F.research_release_binding_digest(value) != F.research_release_binding_digest(original)


def test_binding_identity_and_nested_bundle_agreement_are_not_normalized():
    state, source, destination = fixture()
    document = payload(state, source, destination)
    H.refused(lambda:F.parse_event(raw_payload(document|{'binding_sha256':H.digest('wrong')})),
              'INCIDENT_RELEASE_BINDING_MISMATCH')
    for changes in ({'bundle_digest':H.digest('other')},
                    {'input_archive_digest':H.digest('other')},
                    {'source_store_binding_sha256':destination.store_binding_sha256}):
        H.refused(lambda:F.research_release_binding_digest(document['binding']|changes))
    # Canonical shape/hashes do not establish an authentic recovery outcome.
    value = deepcopy(document); value['binding']['outcome_event_id'] = H.digest('invented-outcome')
    value['binding_sha256'] = F.research_release_binding_digest(value['binding'])
    event = F.parse_event(raw_payload(value))
    after = F.reduce(state, event)
    assert F.blocked_incidents(after, destination) == state.incidents


def test_release_chronology_expiry_and_exact_thirty_second_bound():
    state, source, destination = fixture()
    original = payload(state, source, destination)
    boundary = AT+timedelta(seconds=32)
    assert F.parse_event(raw_payload(original, at=boundary))
    H.refused(lambda:F.parse_event(raw_payload(original, at=boundary+timedelta(microseconds=1))))
    H.refused(lambda:F.parse_event(raw_payload(original, at=AT+timedelta(seconds=1))))
    H.refused(lambda:F.parse_event(raw_payload(original, at=AT+timedelta(minutes=5))))
    document = deepcopy(original)
    document['binding']['selection']['evaluated_at'] = stamp(AT+timedelta(seconds=3))
    document['binding_sha256'] = F.research_release_binding_digest(document['binding'])
    H.refused(lambda:F.parse_event(raw_payload(document)))
    document = deepcopy(original); document['owner_checkpoint']['observed_at'] = '2026-01-01T00:00:02+00:00'
    H.refused(lambda:F.parse_event(raw_payload(document)))
    H.refused(lambda:F.make_event(KIND, original, observed_at=None))


def test_release_requires_exact_current_registered_graph_and_manifest_pair():
    state, source, destination = fixture()
    event = release(state, source, destination)
    only_source = F.reduce(H.registered(source), H.failure(source, at=AT+timedelta(seconds=1)))
    H.refused(lambda:F.reduce(only_source, event), 'INCIDENT_TARGET_UNREGISTERED')
    for name in ('graph_sha256','raw_manifest_sha256','verified_manifest_sha256','catalog_head_sha256'):
        changed = replace(destination, **{name:H.digest('changed-'+name)})
        current = F.reduce(H.registered(source, changed), H.failure(source, at=AT+timedelta(seconds=1)))
        H.refused(lambda:F.reduce(current, event), 'INCIDENT_RELEASE_REGISTRATION_MISMATCH')
        updated = payload(current, source, changed)
        if name == 'catalog_head_sha256':
            assert F.research_route_releases(F.reduce(current, F.parse_event(raw_payload(updated))))
        else:
            H.refused(lambda:F.reduce(current, F.parse_event(raw_payload(updated))), 'INCIDENT_RELEASE_REGISTRATION_MISMATCH')
    raw = H.registration(original='raw', raw=True, store='raw-source')
    raw_copy = replace(raw, store_binding_sha256=H.digest('raw-copy'))
    current = F.reduce(H.registered(raw, raw_copy), H.failure(raw, at=AT+timedelta(seconds=1)))
    H.refused(lambda:F.reduce(current, release(current, raw, raw_copy)), 'INCIDENT_RELEASE_REGISTRATION_MISMATCH')


def test_release_requires_one_current_incident_for_both_source_and_destination():
    state, source, destination = fixture()
    original = payload(state, source, destination)
    no_incident = H.registered(source, destination)
    H.refused(lambda:F.reduce(no_incident, F.parse_event(raw_payload(original))), 'INCIDENT_RELEASE_INCIDENT_MISMATCH')
    additional = F.reduce(state, H.failure(destination, at=AT+timedelta(seconds=2), reason='SECOND_FAULT'))
    H.refused(lambda:F.reduce(additional, F.parse_event(raw_payload(original))), 'INCIDENT_RELEASE_INCIDENT_MISMATCH')
    unknown = deepcopy(original); unknown['binding']['incident_id'] = H.digest('unknown')
    unknown['binding_sha256'] = F.research_release_binding_digest(unknown['binding'])
    H.refused(lambda:F.reduce(state, F.parse_event(raw_payload(unknown))), 'INCIDENT_RELEASE_INCIDENT_MISMATCH')


def test_every_scope_retains_general_copy_holds_and_unrelated_research_independence():
    for scope in ('TARGET','OBJECTS','STORE'):
        state, source, destination = fixture(scope=scope)
        unrelated = H.registration('independent', store='independent-store', objects=(H.dependency('independent'),))
        state = F.reduce(state, F.make_event('REGISTER', F.registration_document(unrelated),
                                           observed_at=AT+timedelta(seconds=2)))
        prior = projected(state), state.pending_notifications
        after = F.reduce(state, release(state, source, destination))
        assert (projected(after), after.pending_notifications) == prior
        copy = replace(destination, store_binding_sha256=H.digest('yet-another-copy'))
        for item in (source, destination, copy):
            assert F.blocked_incidents(after, item) == F.blocked_incidents(state, item) == state.incidents
        assert not F.blocked_incidents(after, unrelated)
        # A later destination failure is retained even though an old record exists.
        after = F.reduce(after, H.failure(destination, at=AT+timedelta(seconds=4), reason='LATER_FAULT'))
        assert len(F.blocked_incidents(after, destination)) == 2
        assert len(F.research_route_releases(after)) == 1


def test_exact_retry_is_inert_but_same_binding_different_observation_conflicts():
    state, source, destination = fixture()
    event = release(state, source, destination)
    state = F.reduce(state, event)
    assert F.reduce(state, event) is state
    delivered = H.delivery(state.outbox[0], outcome='failed', at=AT+timedelta(seconds=4))
    later = F.reduce(state, delivered)
    assert F.reduce(later, event) is later and len(F.research_route_releases(later)) == 1
    document = json.loads(F.event_bytes(event))['payload']
    document['incident_head'][1] = H.digest('another-head')
    changed = F.parse_event(raw_payload(document, at=AT+timedelta(seconds=4)))
    H.refused(lambda:F.reduce(later, changed), 'INCIDENT_RELEASE_CONFLICT')
    changed_time = F.parse_event(raw_payload(json.loads(F.event_bytes(event))['payload'],
                                           at=AT+timedelta(seconds=4)))
    H.refused(lambda:F.reduce(later, changed_time), 'INCIDENT_RELEASE_CONFLICT')


def test_query_filters_and_tampered_projections_cannot_hide_validation():
    state, source, destination = fixture()
    event = release(state, source, destination)
    after = F.reduce(state, event); bound = event.payload['binding']
    for name in ('route_id','incident_id','destination_store_binding_sha256'):
        assert F.research_route_releases(after, **{name:bound[name]}) == (event,)
        assert not F.research_route_releases(after, **{name:H.digest('absent')})
        for value in (False, 1, b'a'*64, 'A'*64):
            H.refused(lambda:F.research_route_releases(after, **{name:value}))
    H.refused(lambda:F.research_route_releases(replace(after, incidents=())), 'INCIDENT_STATE_INVALID')
    H.refused(lambda:F.research_route_releases(replace(after, outbox=())), 'INCIDENT_STATE_INVALID')


def test_release_count_reuses_existing_incident_limit_without_truncation():
    state, source, destination = fixture()
    limits = replace(F.DEFAULT_LIMITS, max_incidents=1)
    event = release(state, source, destination)
    after = F.reduce(state, event, limits=limits)
    before = F.state_bytes(after, limits=limits)
    H.refused(lambda:F.reduce(after, release(state, source, destination, label='b'), limits=limits),
              'INCIDENT_RESOURCE_LIMIT')
    assert F.state_bytes(after, limits=limits) == before and len(F.research_route_releases(after, limits=limits)) == 1


def test_release_consumes_original_total_event_budget_and_exact_byte_caps():
    state, source, destination = fixture()
    limits = replace(F.DEFAULT_LIMITS, max_targets=2, max_incidents=2, max_attempts=1)
    state = F.reduce(state, H.delivery(state.outbox[0], at=AT+timedelta(seconds=2)), limits=limits)
    event = release(state, source, destination)
    after = F.reduce(state, event, limits=limits)
    assert len(after.events) == 5
    H.refused(lambda:F.reduce(after, release(state, source, destination, label='b'), limits=limits),
              'INCIDENT_RESOURCE_LIMIT')
    raw = F.event_bytes(event)
    exact = replace(F.DEFAULT_LIMITS, max_event_bytes=len(raw))
    assert F.event_bytes(event, limits=exact) == raw
    H.refused(lambda:F.event_bytes(event, limits=replace(exact, max_event_bytes=len(raw)-1)), 'INCIDENT_RESOURCE_LIMIT')
    saved = F.state_bytes(after)
    assert F.state_bytes(after, limits=replace(F.DEFAULT_LIMITS, max_state_bytes=len(saved))) == saved
    H.refused(lambda:F.state_bytes(after, limits=replace(F.DEFAULT_LIMITS, max_state_bytes=len(saved)-1)), 'INCIDENT_RESOURCE_LIMIT')


def test_one_pass_streaming_replay_checks_each_release_without_recursive_public_query():
    state, source, destination = fixture()
    state = F.reduce(state, release(state, source, destination))
    raw = tuple(F.event_bytes(event) for event in state.events)
    original, calls = F._apply, []
    def counted(*args):
        calls.append(args[1].event_id)
        return original(*args)
    with patch.object(F, '_apply', counted), patch.object(F, 'blocked_incidents',
            side_effect=AssertionError('recursive public validation')):
        replayed = F._replay_events(raw)
    assert len(calls) == len(raw) and replayed == state
    H.refused(lambda:F._replay_events(raw+(raw[-1],)), 'INCIDENT_STATE_INVALID')
    H.refused(lambda:F._replay_events(tuple(reversed(raw))))


def test_release_frozen_mutation_and_limits_failure_have_fixed_diagnostics():
    state, source, destination = fixture()
    event = release(state, source, destination)
    object.__setattr__(event, 'payload', {'release_schema':True})
    H.refused(lambda:F.event_bytes(event))
    bad = replace(F.DEFAULT_LIMITS); object.__delattr__(bad, 'max_event_bytes')
    for call in (lambda:F.registration_digest(source, limits=bad),
                 lambda:F.research_release_binding_digest(binding(state, source, destination), limits=bad),
                 lambda:F.research_route_releases(state, limits=bad)):
        H.refused(call, 'INCIDENT_LIMITS_INVALID')
