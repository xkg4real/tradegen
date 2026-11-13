"""Pure restrictive research-incident records; no observation or order authority.

An adapter must establish dependency provenance. These constructors and hashes
prove only internal consistency, never that a read failed or a message was sent.
A scoped research-route record is historical metadata only. General holds never
change; no record issues source, owner, recovery, approval or trading authority.
"""
from dataclasses import dataclass, fields
from datetime import datetime, timedelta, timezone
from functools import wraps
import hashlib
import json
import re
from types import MappingProxyType


DOMAIN = b'tradegen-research-incidents/1\n'
_CAPS = dict(max_event_bytes=2*1024*1024, max_state_bytes=32*1024*1024,
             max_targets=256, max_dependencies_per_target=8192,
             max_incidents=4096, max_attempts=8192)
_HASH = re.compile(r'[0-9a-f]{64}\Z')
_REASON = re.compile(r'[A-Z][A-Z0-9_]{0,95}\Z')
_ATTEMPT = re.compile(r'[a-z][a-z0-9_-]{0,63}\Z')
_CATEGORIES = ('INTEGRITY_FAILURE', 'READ_UNAVAILABLE', 'RESOURCE_LIMIT', 'VALIDATION_REFUSED')
_RESEARCH_RELEASE = 'RESEARCH_ROUTE_RELEASE'
_RELEASE_REGISTRATION_DOMAIN = b'tradegen-research-release-registration/1\n'
_RELEASE_BINDING_DOMAIN = b'tradegen-research-route-release-binding/1\n'
_STUDY_ID = re.compile(r'[A-Za-z][A-Za-z0-9_.:-]{0,95}\Z')
_RELEASE_BINDING_HASHES = (
    'route_id', 'attempt_id', 'outcome_event_id', 'incident_id',
    'incident_namespace_sha256', 'attempt_namespace_sha256',
    'source_store_binding_sha256', 'source_registration_sha256',
    'destination_store_binding_sha256', 'destination_registration_sha256',
    'bundle_digest', 'input_archive_digest', 'graph_sha256', 'recovery_artifact_digest')
_RELEASE_SELECTION_HASHES = (
    'bundle_digest', 'input_archive_digest', 'attestation_sha256', 'revocation_target_sha256',
    'family_sha256', 'program_sha256', 'protocol_sha256', 'evidence_sha256',
    'profile_contract_sha256', 'rule_terms_sha256', 'window_sha256', 'driver_identity_sha256')
_SOURCE_REVIEW_PURPOSES = (
    'strategy_source_and_fixed_implementation_review',
    'strategy_source_and_fixed_carry_implementation_review')
_MAX_DEPTH = 16
_MAX_NODES = 2_000_000


class IncidentFormatError(ValueError):
    pass


def _fail(code='INCIDENT_FORMAT_INVALID'):
    raise IncidentFormatError(code)


def _fixed(fn):
    @wraps(fn)
    def checked(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except IncidentFormatError:
            raise
        except (AttributeError, TypeError, ValueError, KeyError, OverflowError, RecursionError):
            _fail()
    return checked


def _integer(value, *, minimum=1, maximum=2**63-1):
    if type(value) is not int or not minimum <= value <= maximum:
        _fail()
    return value


def _hash(value):
    if type(value) is not str or not _HASH.fullmatch(value):
        _fail()
    return value


def _enum(value, choices):
    if type(value) is not str or value not in choices:
        _fail()
    return value


def _keys(value, keys):
    if type(value) is not dict or set(value) != set(keys):
        _fail()


def _stamp(value):
    if type(value) is not datetime or value.tzinfo is None or value.utcoffset() is None:
        _fail()
    return value.astimezone(timezone.utc).isoformat(timespec='microseconds').replace('+00:00', 'Z')


def _time(value):
    if type(value) is not str or len(value) != 27:
        _fail()
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if _stamp(result) != value:
        _fail()
    return result


def _plain(value, *, depth=0, budget=None):
    """Detach only known containers; no arbitrary mapping callbacks or aliases."""
    if budget is None:
        budget = [_MAX_NODES]
    budget[0] -= 1
    if budget[0] < 0 or depth > _MAX_DEPTH:
        _fail('INCIDENT_RESOURCE_LIMIT')
    if value is None or type(value) is bool:
        return value
    if type(value) is int:
        if not -(2**63) <= value <= 2**63-1:
            _fail()
        return value
    if type(value) is str:
        if len(value) > _CAPS['max_event_bytes']:
            _fail('INCIDENT_RESOURCE_LIMIT')
        return value
    if type(value) in (dict, MappingProxyType):
        if len(value) > _MAX_NODES:
            _fail('INCIDENT_RESOURCE_LIMIT')
        result = {}
        for key, item in value.items():
            if type(key) is not str or len(key) > 96:
                _fail()
            result[key] = _plain(item, depth=depth+1, budget=budget)
        return result
    if type(value) in (list, tuple):
        if len(value) > _MAX_NODES:
            _fail('INCIDENT_RESOURCE_LIMIT')
        return [_plain(item, depth=depth+1, budget=budget) for item in value]
    _fail()


def _freeze(value):
    if type(value) is dict:
        return MappingProxyType({key:_freeze(item) for key, item in value.items()})
    if type(value) is list:
        return tuple(_freeze(item) for item in value)
    return value


def _encoded(document):
    return json.dumps(document, sort_keys=True, separators=(',', ':'), ensure_ascii=True,
                      allow_nan=False).encode('ascii')


def _digest(tag, document):
    return hashlib.sha256(DOMAIN+tag+b'\n'+_encoded(document)).hexdigest()


def _bounded(document, maximum):
    chunks = []
    size = 0
    encoder = json.JSONEncoder(sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False)
    for text in encoder.iterencode(document):
        chunk = text.encode('ascii')
        size += len(chunk)
        if size > maximum:
            _fail('INCIDENT_RESOURCE_LIMIT')
        chunks.append(chunk)
    return b''.join(chunks)


@dataclass(frozen=True, kw_only=True, slots=True)
class IncidentLimits:
    max_event_bytes: int = _CAPS['max_event_bytes']
    max_state_bytes: int = _CAPS['max_state_bytes']
    max_targets: int = _CAPS['max_targets']
    max_dependencies_per_target: int = _CAPS['max_dependencies_per_target']
    max_incidents: int = _CAPS['max_incidents']
    max_attempts: int = _CAPS['max_attempts']

    def __post_init__(self):
        try:
            for name, maximum in _CAPS.items():
                value = getattr(self, name)
                if type(value) is not int or not 1 <= value <= maximum:
                    _fail('INCIDENT_LIMITS_INVALID')
        except (AttributeError, TypeError):
            _fail('INCIDENT_LIMITS_INVALID')


DEFAULT_LIMITS = IncidentLimits()


def _limits(value):
    if type(value) is not IncidentLimits:
        _fail('INCIDENT_LIMITS_INVALID')
    value.__post_init__()
    return value


@dataclass(frozen=True, kw_only=True, slots=True)
class ObjectDependency:
    kind: str
    sha256: str
    byte_count: int
    from_raw: bool

    @_fixed
    def __post_init__(self):
        _enum(self.kind, ('chunk', 'manifest'))
        _hash(self.sha256)
        _integer(self.byte_count)
        if type(self.from_raw) is not bool:
            _fail()


@dataclass(frozen=True, kw_only=True, slots=True)
class TargetRegistration:
    store_binding_sha256: str
    bundle_digest: str
    input_archive_digest: str
    bundle_kind: str
    raw_manifest_sha256: str
    verified_manifest_sha256: str | None
    graph_sha256: str
    catalog_head_sha256: str
    catalog_sequence: int
    objects: tuple[ObjectDependency, ...]

    @_fixed
    def __post_init__(self):
        _registration_doc(self, DEFAULT_LIMITS)


def _registration_doc(value, limits):
    if type(value) is not TargetRegistration:
        _fail()
    for name in ('store_binding_sha256', 'bundle_digest', 'input_archive_digest',
                 'raw_manifest_sha256', 'graph_sha256', 'catalog_head_sha256'):
        _hash(getattr(value, name))
    _enum(value.bundle_kind, ('RAW_ARCHIVED', 'VERIFIED_UNAPPROVED'))
    _integer(value.catalog_sequence)
    if type(value.objects) is not tuple or not value.objects:
        _fail()
    if len(value.objects) > limits.max_dependencies_per_target:
        _fail('INCIDENT_RESOURCE_LIMIT')
    documents = []
    previous = None
    for item in value.objects:
        if type(item) is not ObjectDependency:
            _fail()
        item.__post_init__()
        if previous is not None and item.sha256 <= previous:
            _fail()
        previous = item.sha256
        documents.append({field.name:getattr(item, field.name) for field in fields(ObjectDependency)})
    if value.bundle_kind == 'RAW_ARCHIVED':
        if (value.bundle_digest != value.input_archive_digest or value.verified_manifest_sha256 is not None
                or not all(item.from_raw for item in value.objects)):
            _fail()
    else:
        _hash(value.verified_manifest_sha256)
        if value.bundle_digest == value.input_archive_digest or not any(item.from_raw for item in value.objects):
            _fail()
    return {field.name:(documents if field.name == 'objects' else getattr(value, field.name))
            for field in fields(TargetRegistration)}


@_fixed
def registration_document(registration):
    return _registration_doc(registration, DEFAULT_LIMITS)


@_fixed
def parse_registration(document, *, limits=DEFAULT_LIMITS):
    limits = _limits(limits)
    _keys(document, (field.name for field in fields(TargetRegistration)))
    objects = document['objects']
    if type(objects) is not list:
        _fail()
    if len(objects) > limits.max_dependencies_per_target:
        _fail('INCIDENT_RESOURCE_LIMIT')
    parsed = []
    for item in objects:
        _keys(item, (field.name for field in fields(ObjectDependency)))
        parsed.append(ObjectDependency(**item))
    result = TargetRegistration(**{**document, 'objects':tuple(parsed)})
    _registration_doc(result, limits)
    return result



def _release_identifier(value, pattern):
    if type(value) is not str or pattern.fullmatch(value) is None:
        _fail()
    return value


def _release_head(value):
    if type(value) is not list or len(value) != 2:
        _fail()
    return [_integer(value[0]), _hash(value[1])]


def _release_selection(document):
    _keys(document, _RELEASE_SELECTION_HASHES +
          ('selected_study_id', 'source_reviews', 'evaluated_at', 'approval_expires_at'))
    for name in _RELEASE_SELECTION_HASHES:
        _hash(document[name])
    selected = _release_identifier(document['selected_study_id'], _STUDY_ID)
    reviews = document['source_reviews']
    if type(reviews) is not list or not reviews:
        _fail()
    if len(reviews) > 128:
        _fail('INCIDENT_RESOURCE_LIMIT')
    previous = None
    identifiers = set()
    for item in reviews:
        _keys(item, ('study_id', 'document_sha256', 'purpose', 'revocation_target_sha256',
                     'audit_logical_id', 'audit_sha256'))
        identity = _release_identifier(item['study_id'], _STUDY_ID)
        if previous is not None and identity <= previous:
            _fail()
        previous = identity
        identifiers.add(identity)
        for name in ('document_sha256', 'revocation_target_sha256', 'audit_sha256'):
            _hash(item[name])
        _enum(item['purpose'], _SOURCE_REVIEW_PURPOSES)
        _release_identifier(item['audit_logical_id'], _ATTEMPT)
    if selected not in identifiers:
        _fail()
    if _time(document['evaluated_at']) >= _time(document['approval_expires_at']):
        _fail()
    return document


def _release_binding(document):
    _keys(document, _RELEASE_BINDING_HASHES + ('selection',))
    for name in _RELEASE_BINDING_HASHES:
        _hash(document[name])
    selection = _release_selection(document['selection'])
    if (document['source_store_binding_sha256'] == document['destination_store_binding_sha256']
            or any(document[name] != selection[name] for name in ('bundle_digest', 'input_archive_digest'))):
        _fail()
    return document


@_fixed
def registration_digest(registration, *, limits=DEFAULT_LIMITS):
    """Bind exact registration metadata; never authenticate its dependency graph."""
    limits = _limits(limits)
    raw = _bounded(_registration_doc(registration, limits), limits.max_event_bytes)
    return hashlib.sha256(_RELEASE_REGISTRATION_DOMAIN + raw).hexdigest()


@_fixed
def research_release_binding_digest(binding, *, limits=DEFAULT_LIMITS):
    """Strict inert binding, not a source verification or current-use decision."""
    limits = _limits(limits)
    raw = _bounded(_release_binding(_plain(binding)), limits.max_event_bytes)
    return hashlib.sha256(_RELEASE_BINDING_DOMAIN + raw).hexdigest()


def _release_payload(document, limits):
    _keys(document, ('release_schema', 'scope', 'binding', 'binding_sha256', 'incident_head',
                     'attempt_head', 'destination_head', 'owner_checkpoint'))
    if type(document['release_schema']) is not int or document['release_schema'] != 1:
        _fail()
    _enum(document['scope'], ('recovered_research_selection',))
    binding = _release_binding(document['binding'])
    _hash(document['binding_sha256'])
    if document['binding_sha256'] != research_release_binding_digest(binding, limits=limits):
        _fail('INCIDENT_RELEASE_BINDING_MISMATCH')
    for name in ('incident_head', 'attempt_head', 'destination_head'):
        _release_head(document[name])
    checkpoint = document['owner_checkpoint']
    _keys(checkpoint, ('key_fingerprint', 'code_hash', 'owner_head', 'observed_at'))
    fingerprint = checkpoint['key_fingerprint']
    if type(fingerprint) is not str or len(fingerprint) != 71 or not fingerprint.startswith('SHA256:'):
        _fail()
    _hash(fingerprint[7:]); _hash(checkpoint['code_hash'])
    _release_head(checkpoint['owner_head'])
    if not (_time(binding['selection']['evaluated_at']) <= _time(checkpoint['observed_at'])
            < _time(binding['selection']['approval_expires_at'])):
        _fail()
    return document


def _payload(kind, document, limits):
    if kind == _RESEARCH_RELEASE:
        return _release_payload(document, limits)
    if kind == 'REGISTER':
        return _registration_doc(parse_registration(document, limits=limits), limits)
    if kind == 'FAILURE':
        _keys(document, ('store_binding_sha256', 'bundle_digest', 'scope', 'failed_objects', 'category', 'reason_code'))
        _hash(document['store_binding_sha256'])
        _hash(document['bundle_digest'])
        scope = _enum(document['scope'], ('TARGET', 'OBJECTS', 'STORE'))
        _enum(document['category'], _CATEGORIES)
        if type(document['reason_code']) is not str or not _REASON.fullmatch(document['reason_code']):
            _fail()
        objects = document['failed_objects']
        if type(objects) is not list:
            _fail()
        if len(objects) > limits.max_dependencies_per_target:
            _fail('INCIDENT_RESOURCE_LIMIT')
        for item in objects:
            _hash(item)
        if objects != sorted(set(objects)) or (bool(objects) != (scope == 'OBJECTS')):
            _fail()
        return {**document, 'failed_objects':list(objects)}
    if kind == 'DELIVERY':
        _keys(document, ('message_id', 'attempt_id', 'outcome'))
        _hash(document['message_id'])
        if type(document['attempt_id']) is not str or not _ATTEMPT.fullmatch(document['attempt_id']):
            _fail()
        _enum(document['outcome'], ('delivered', 'failed', 'unknown'))
        return dict(document)
    _fail()


@dataclass(frozen=True, kw_only=True, slots=True)
class IncidentEvent:
    schema: int
    event_id: str
    kind: str
    observed_at: datetime | None
    payload: dict

    @_fixed
    def __post_init__(self):
        body = _event_doc(self, DEFAULT_LIMITS)
        # No retained reference to a caller-owned mutable dictionary or sequence.
        object.__setattr__(self, 'payload', _freeze(body['payload']))
        if self.observed_at is not None:
            object.__setattr__(self, 'observed_at', _time(body['observed_at']))


def _event_doc(value, limits):
    if type(value) is not IncidentEvent or type(value.schema) is not int or value.schema != 1:
        _fail()
    _hash(value.event_id)
    _enum(value.kind, ('REGISTER', 'FAILURE', 'DELIVERY', _RESEARCH_RELEASE))
    if value.observed_at is None:
        if value.kind != 'FAILURE':
            _fail()
        at = None
    else:
        at = _stamp(value.observed_at)
    payload = _payload(value.kind, _plain(value.payload), limits)
    if value.kind == _RESEARCH_RELEASE:
        checkpoint_at = _time(payload['owner_checkpoint']['observed_at'])
        if (not timedelta(0) <= _time(at)-checkpoint_at <= timedelta(seconds=30)
                or _time(at) >= _time(payload['binding']['selection']['approval_expires_at'])):
            _fail()
    body = dict(schema=1, kind=value.kind, observed_at=at, payload=payload)
    if value.event_id != _digest(b'event', body):
        _fail('INCIDENT_EVENT_ID_MISMATCH')
    document = dict(body, event_id=value.event_id)
    _bounded(document, limits.max_event_bytes)
    return document


@_fixed
def make_event(kind, payload, *, observed_at):
    _enum(kind, ('REGISTER', 'FAILURE', 'DELIVERY', _RESEARCH_RELEASE))
    at = None if observed_at is None else _stamp(observed_at)
    body = dict(schema=1, kind=kind, observed_at=at, payload=_payload(kind, _plain(payload), DEFAULT_LIMITS))
    return IncidentEvent(schema=1, event_id=_digest(b'event', body), kind=kind,
                         observed_at=observed_at, payload=body['payload'])


@_fixed
def event_bytes(event, *, limits=DEFAULT_LIMITS):
    limits = _limits(limits)
    return _bounded(_event_doc(event, limits), limits.max_event_bytes)


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            _fail()
        result[key] = value
    return result


def _number(text):
    if len(text) > 20:
        _fail()
    value = int(text)
    if not -(2**63) <= value <= 2**63-1:
        _fail()
    return value


def _no_number(text):
    _fail()


def _decode(raw, maximum):
    if type(raw) is not bytes or not raw:
        _fail()
    if len(raw) > maximum:
        _fail('INCIDENT_RESOURCE_LIMIT')
    # Check nesting before json.loads can recurse or allocate a deep graph.
    quoted = escaped = False
    depth = tokens = 0
    for byte in raw:
        if quoted:
            if escaped:
                escaped = False
            elif byte == 92:
                escaped = True
            elif byte == 34:
                quoted = False
        elif byte == 34:
            quoted = True
            tokens += 1
        elif byte in (91, 123):
            depth += 1
            tokens += 1
            if depth > _MAX_DEPTH:
                _fail('INCIDENT_RESOURCE_LIMIT')
        elif byte in (93, 125):
            depth -= 1
        elif byte == 44:
            tokens += 1
        if tokens > _MAX_NODES:
            _fail('INCIDENT_RESOURCE_LIMIT')
    document = json.loads(raw.decode('ascii'), object_pairs_hook=_pairs, parse_int=_number,
                          parse_float=_no_number, parse_constant=_no_number)
    _plain(document)
    if _encoded(document) != raw:
        _fail()
    return document


@_fixed
def parse_event(raw, *, limits=DEFAULT_LIMITS):
    limits = _limits(limits)
    document = _decode(raw, limits.max_event_bytes)
    _keys(document, ('schema', 'event_id', 'kind', 'observed_at', 'payload'))
    at = None if document['observed_at'] is None else _time(document['observed_at'])
    result = IncidentEvent(**{**document, 'observed_at':at})
    _event_doc(result, limits)
    return result


@dataclass(frozen=True, kw_only=True, slots=True)
class ResearchIncident:
    incident_id: str
    store_binding_sha256: str
    bundle_digest: str
    scope: str
    failed_objects: tuple[str, ...]
    category: str
    reason_code: str
    observed_at: datetime | None
    affected_bundle_digests: tuple[str, ...]
    affected_raw_digests: tuple[str, ...]


@dataclass(frozen=True, kw_only=True, slots=True)
class NotificationIntent:
    message_id: str
    incident_id: str
    kind: str
    bundle_digest: str
    category: str
    reason_code: str


@dataclass(frozen=True, kw_only=True, slots=True)
class NotificationReceipt:
    message_id: str
    attempt_id: str
    outcome: str
    observed_at: datetime


@dataclass(frozen=True, kw_only=True, slots=True)
class IncidentState:
    registrations: tuple[TargetRegistration, ...]
    incidents: tuple[ResearchIncident, ...]
    outbox: tuple[NotificationIntent, ...]
    receipts: tuple[NotificationReceipt, ...]
    events: tuple[IncidentEvent, ...]
    last_trusted_at: datetime | None

    @property
    @_fixed
    def pending_notifications(self):
        _validate_state(self, DEFAULT_LIMITS)
        delivered = {item.message_id for item in self.receipts if item.outcome == 'delivered'}
        return tuple(item for item in self.outbox if item.message_id not in delivered)


def initial_state():
    return IncidentState(registrations=(), incidents=(), outbox=(), receipts=(), events=(), last_trusted_at=None)


def _affected(registrations, *, store_binding_sha256, bundle_digest, scope, failed_objects):
    bundles, originals = set(), set()
    failed = set(failed_objects)
    for item in registrations:
        if item.store_binding_sha256 != store_binding_sha256:
            continue
        if scope == 'STORE':
            bundles.add(item.bundle_digest)
            originals.add(item.input_archive_digest)
        elif scope == 'TARGET' and item.bundle_digest == bundle_digest:
            bundles.add(item.bundle_digest)
            if item.bundle_kind == 'RAW_ARCHIVED':
                originals.add(item.input_archive_digest)
        elif scope == 'OBJECTS':
            matches = tuple(obj for obj in item.objects if obj.sha256 in failed)
            if matches:
                bundles.add(item.bundle_digest)
            if any(obj.from_raw for obj in matches):
                originals.add(item.input_archive_digest)
    return tuple(sorted(bundles)), tuple(sorted(originals))


def _blocked_incidents(registrations, incidents, registration):
    blocked = []
    for incident in incidents:
        # Preserve historical affected IDs, and extend physical-scope membership
        # from ALL current registrations. A late dependent's copy cannot escape.
        bundles, originals = _affected(registrations,
            store_binding_sha256=incident.store_binding_sha256, bundle_digest=incident.bundle_digest,
            scope=incident.scope, failed_objects=incident.failed_objects)
        bundles = set(bundles) | set(incident.affected_bundle_digests)
        originals = set(originals) | set(incident.affected_raw_digests)
        candidate_bundles, candidate_raw = _affected((registration,),
            store_binding_sha256=incident.store_binding_sha256, bundle_digest=incident.bundle_digest,
            scope=incident.scope, failed_objects=incident.failed_objects)
        if (registration.bundle_digest in bundles or registration.input_archive_digest in originals
                or candidate_bundles or candidate_raw):
            blocked.append(incident)
    return tuple(blocked)


def _apply_release(state, event, body, limits):
    """Check local references only; external provenance remains unverified here."""
    binding = body['binding']
    prior = tuple(item for item in state.events if item.kind == _RESEARCH_RELEASE)
    for item in prior:
        if item.payload['binding_sha256'] == body['binding_sha256']:
            if event_bytes(item, limits=limits) != event_bytes(event, limits=limits):
                _fail('INCIDENT_RELEASE_CONFLICT')
            return False
    if len(prior) >= limits.max_incidents:
        _fail('INCIDENT_RESOURCE_LIMIT')
    targets = []
    for prefix in ('source', 'destination'):
        target = next((item for item in state.registrations
            if item.store_binding_sha256 == binding[prefix+'_store_binding_sha256']
            and item.bundle_digest == binding['bundle_digest']), None)
        if target is None:
            _fail('INCIDENT_TARGET_UNREGISTERED')
        if (target.bundle_kind != 'VERIFIED_UNAPPROVED'
                or registration_digest(target, limits=limits) != binding[prefix+'_registration_sha256']
                or target.input_archive_digest != binding['input_archive_digest']
                or target.graph_sha256 != binding['graph_sha256']):
            _fail('INCIDENT_RELEASE_REGISTRATION_MISMATCH')
        targets.append(target)
    if any(getattr(targets[0], name) != getattr(targets[1], name)
           for name in ('raw_manifest_sha256', 'verified_manifest_sha256', 'objects')):
        _fail('INCIDENT_RELEASE_REGISTRATION_MISMATCH')
    if not any(item.incident_id == binding['incident_id'] for item in state.incidents):
        _fail('INCIDENT_RELEASE_INCIDENT_MISMATCH')
    for target in targets:
        blocked = _blocked_incidents(state.registrations, state.incidents, target)
        if tuple(item.incident_id for item in blocked) != (binding['incident_id'],):
            _fail('INCIDENT_RELEASE_INCIDENT_MISMATCH')
    return True


def _apply(state, event, limits):
    """Internal deterministic fold; caller has checked the event and prior fold."""
    if event.observed_at is not None and state.last_trusted_at is not None and event.observed_at < state.last_trusted_at:
        _fail('INCIDENT_CLOCK_ROLLBACK')
    registrations, incidents, outbox, receipts = state.registrations, state.incidents, state.outbox, state.receipts
    body = _plain(event.payload)
    if event.kind == 'REGISTER':
        registration = parse_registration(body, limits=limits)
        key = (registration.store_binding_sha256, registration.bundle_digest)
        previous = next((item for item in registrations if (item.store_binding_sha256, item.bundle_digest) == key), None)
        if previous is not None:
            if _registration_doc(previous, limits) != body:
                _fail('INCIDENT_REGISTRATION_CONFLICT')
            return state
        if len(registrations) >= limits.max_targets:
            _fail('INCIDENT_RESOURCE_LIMIT')
        # A kind-separated object digest cannot describe conflicting bytes.
        known = {obj.sha256:(obj.kind, obj.byte_count) for item in registrations for obj in item.objects}
        for obj in registration.objects:
            if obj.sha256 in known and known[obj.sha256] != (obj.kind, obj.byte_count):
                _fail('INCIDENT_DEPENDENCY_CONFLICT')
        registrations += (registration,)
    elif event.kind == 'FAILURE':
        key = (body['store_binding_sha256'], body['bundle_digest'])
        target = next((item for item in registrations if (item.store_binding_sha256, item.bundle_digest) == key), None)
        if target is None:
            _fail('INCIDENT_TARGET_UNREGISTERED')
        if not set(body['failed_objects']).issubset({obj.sha256 for obj in target.objects}):
            _fail('INCIDENT_DEPENDENCY_UNKNOWN')
        if len(incidents) >= limits.max_incidents:
            _fail('INCIDENT_RESOURCE_LIMIT')
        bundles, originals = _affected(registrations, store_binding_sha256=body['store_binding_sha256'],
            bundle_digest=body['bundle_digest'], scope=body['scope'], failed_objects=body['failed_objects'])
        incident = ResearchIncident(incident_id=event.event_id, **{**body, 'failed_objects':tuple(body['failed_objects'])},
            observed_at=event.observed_at, affected_bundle_digests=bundles, affected_raw_digests=originals)
        intent_body = dict(incident_id=event.event_id, kind='RESEARCH_EVIDENCE_HELD',
            bundle_digest=incident.bundle_digest, category=incident.category, reason_code=incident.reason_code)
        incidents += (incident,)
        outbox += (NotificationIntent(message_id=_digest(b'notification', intent_body), **intent_body),)
    elif event.kind == _RESEARCH_RELEASE:
        if not _apply_release(state, event, body, limits):
            return state
    else:
        message = next((item for item in outbox if item.message_id == body['message_id']), None)
        if message is None:
            _fail('INCIDENT_MESSAGE_UNKNOWN')
        receipt = NotificationReceipt(**body, observed_at=event.observed_at)
        previous = next((item for item in receipts if item.attempt_id == receipt.attempt_id), None)
        if previous is not None:
            if previous != receipt:
                _fail('INCIDENT_DELIVERY_CONFLICT')
            return state
        if any(item.message_id == receipt.message_id and item.outcome == 'delivered' for item in receipts):
            _fail('INCIDENT_MESSAGE_DELIVERED')
        if len(receipts) >= limits.max_attempts:
            _fail('INCIDENT_RESOURCE_LIMIT')
        receipts += (receipt,)
    if len(state.events) >= limits.max_targets+limits.max_incidents+limits.max_attempts:
        _fail('INCIDENT_RESOURCE_LIMIT')
    return IncidentState(registrations=registrations, incidents=incidents, outbox=outbox, receipts=receipts,
        events=state.events+(event,), last_trusted_at=event.observed_at or state.last_trusted_at)


def _projection_doc(value, cls):
    if type(value) is not cls:
        _fail('INCIDENT_STATE_INVALID')
    result = {}
    for field in fields(cls):
        item = getattr(value, field.name)
        if field.name == 'observed_at':
            result[field.name] = None if item is None else _stamp(item)
        else:
            if field.name in ('failed_objects', 'affected_bundle_digests', 'affected_raw_digests'):
                if type(item) is not tuple:
                    _fail('INCIDENT_STATE_INVALID')
                for digest in item:
                    _hash(digest)
            elif type(item) is not str:
                _fail('INCIDENT_STATE_INVALID')
            result[field.name] = _plain(item)
    return result


def _state_doc(state, limits):
    if type(state) is not IncidentState:
        _fail('INCIDENT_STATE_INVALID')
    for name, cap in (('registrations', limits.max_targets), ('incidents', limits.max_incidents),
                      ('outbox', limits.max_incidents), ('receipts', limits.max_attempts),
                      ('events', limits.max_targets+limits.max_incidents+limits.max_attempts)):
        value = getattr(state, name)
        if type(value) is not tuple:
            _fail('INCIDENT_STATE_INVALID')
        if len(value) > cap:
            _fail('INCIDENT_RESOURCE_LIMIT')
    document = dict(schema=1, last_trusted_at=None if state.last_trusted_at is None else _stamp(state.last_trusted_at))
    used = 0
    for name, converter in (
            ('registrations', lambda item:_registration_doc(item, limits)),
            ('incidents', lambda item:_projection_doc(item, ResearchIncident)),
            ('outbox', lambda item:_projection_doc(item, NotificationIntent)),
            ('receipts', lambda item:_projection_doc(item, NotificationReceipt)),
            ('events', lambda item:_event_doc(item, limits))):
        items = []
        for item in getattr(state, name):
            converted = converter(item)
            used += len(_bounded(converted, limits.max_state_bytes))
            if used > limits.max_state_bytes:
                _fail('INCIDENT_RESOURCE_LIMIT')
            items.append(converted)
        document[name] = items
    return document


@_fixed
def _replay_events(raw_events, *, limits=DEFAULT_LIMITS):
    """Store replay seam: derive from scratch, never accept a trusted-state flag.

    Each exact event byte record is strictly parsed before one transition.
    Persisted no-op duplicates are invalid rows. The final bound covers the
    derived projections as well as every original event; nothing is truncated.
    """
    limits = _limits(limits)
    if type(raw_events) is not tuple:
        _fail('INCIDENT_STATE_INVALID')
    if len(raw_events) > limits.max_targets+limits.max_incidents+limits.max_attempts:
        _fail('INCIDENT_RESOURCE_LIMIT')
    state = initial_state()
    seen = set()
    used = 0
    for raw in raw_events:
        if type(raw) is not bytes:
            _fail()
        used += len(raw)
        if used > limits.max_state_bytes:
            _fail('INCIDENT_RESOURCE_LIMIT')
        event = parse_event(raw, limits=limits)
        if event.event_id in seen:
            _fail('INCIDENT_STATE_INVALID')
        seen.add(event.event_id)
        next_state = _apply(state, event, limits)
        if next_state is state:
            _fail('INCIDENT_STATE_INVALID')
        state = next_state
    _bounded(_state_doc(state, limits), limits.max_state_bytes)
    return state


def _validate_state(state, limits):
    document = _state_doc(state, limits)
    raw = _bounded(document, limits.max_state_bytes)
    reconstructed = _replay_events(tuple(event_bytes(event, limits=limits) for event in state.events), limits=limits)
    # Byte equality is type-sensitive (unlike Python's True == 1).
    if _bounded(_state_doc(reconstructed, limits), limits.max_state_bytes) != raw:
        _fail('INCIDENT_STATE_INVALID')
    return raw


@_fixed
def reduce(state, event, *, limits=DEFAULT_LIMITS):
    limits = _limits(limits)
    _validate_state(state, limits)
    # Reparse a detached immutable event even if a frozen instance was altered.
    event = parse_event(event_bytes(event, limits=limits), limits=limits)
    for old in state.events:
        if old.event_id == event.event_id:
            if event_bytes(old, limits=limits) != event_bytes(event, limits=limits):
                _fail('INCIDENT_EVENT_CONFLICT')
            return state
    result = _apply(state, event, limits)
    _bounded(_state_doc(result, limits), limits.max_state_bytes)
    return result


@_fixed
def state_bytes(state, *, limits=DEFAULT_LIMITS):
    return _validate_state(state, _limits(limits))


@_fixed
def state_digest(state, *, limits=DEFAULT_LIMITS):
    return hashlib.sha256(DOMAIN+b'state\n'+state_bytes(state, limits=limits)).hexdigest()


@_fixed
def blocked_incidents(state, registration):
    _validate_state(state, DEFAULT_LIMITS)
    _registration_doc(registration, DEFAULT_LIMITS)
    return _blocked_incidents(state.registrations, state.incidents, registration)


@_fixed
def research_route_releases(state, *, route_id=None, incident_id=None,
                            destination_store_binding_sha256=None, limits=DEFAULT_LIMITS):
    """Return original validated records, never authority or a general unhold."""
    limits = _limits(limits)
    filters = (('route_id', route_id), ('incident_id', incident_id),
               ('destination_store_binding_sha256', destination_store_binding_sha256))
    for _, value in filters:
        if value is not None:
            _hash(value)
    _validate_state(state, limits)
    return tuple(event for event in state.events if event.kind == _RESEARCH_RELEASE
                 and all(value is None or event.payload['binding'][name] == value
                         for name, value in filters))
