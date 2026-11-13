"""Pure bounded recovery attempts and result outbox; never recovery authority.

Actual adapters must establish route, incident, owner, source and destination
facts. This model only checks their structure and restrictive chronology. No
hold release, source mutation, approval, message send or order is possible here.
"""
from dataclasses import dataclass, fields
from datetime import datetime, timedelta
from functools import wraps
import base64
import hashlib
import re

from execution_launch import research_incidents as I


DOMAIN = b'tradegen-research-recovery-attempts/1\n'
_CAPS = dict(max_event_bytes=2*1024*1024, max_state_bytes=32*1024*1024,
             max_routes=128, max_attempts=1024, max_delivery_attempts=8192)
_STATUS = ('EXACT_ARCHIVE_RESTORED', 'AUTHORITY_REFUSED', 'DESTINATION_UNCONFIRMED',
           'EVIDENCE_REFUSED', 'READ_UNAVAILABLE', 'RESOURCE_LIMIT', 'PARTIAL_UNVERIFIED')
_TERMINAL = frozenset(_STATUS[:4])
_REVOCATION = ('UNOBSERVED', 'REVOKED', 'NOT_REVOKED_AT_HEAD')
_KINDS = ('ROUTE_REGISTERED', 'ATTEMPT_STARTED', 'RESUME_STARTED',
          'PREFLIGHT_REFUSED', 'ATTEMPT_OBSERVED', 'DELIVERY_REPORTED')
_REASON = re.compile(r'[A-Z][A-Z0-9_]{0,95}\Z')
_ID = re.compile(r'[a-z][a-z0-9_-]{0,63}\Z')


class RecoveryAttemptError(ValueError):
    pass


def _fail(code='RECOVERY_FORMAT_INVALID'):
    raise RecoveryAttemptError(code)


def _fixed(fn):
    @wraps(fn)
    def checked(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except RecoveryAttemptError:
            raise
        except I.IncidentFormatError as exc:
            raise RecoveryAttemptError(str(exc).replace('INCIDENT_', 'RECOVERY_', 1)) from None
        except (AttributeError, TypeError, ValueError, KeyError, OverflowError, RecursionError):
            _fail()
    return checked


def _need(ok, code='RECOVERY_FORMAT_INVALID'):
    if not ok:
        _fail(code)


def _digest(tag, body):
    return hashlib.sha256(DOMAIN+tag.encode('ascii')+b'\n'+I._encoded(body)).hexdigest()


def _head(value, *, minimum=0):
    _need(type(value) is tuple and len(value) == 2)
    I._integer(value[0], minimum=minimum)
    I._hash(value[1])
    return list(value)


def _parse_head(value, *, minimum=0):
    _need(type(value) is list and len(value) == 2)
    result = tuple(value)
    _head(result, minimum=minimum)
    return result


def _extends(current, previous):
    _need(current[0] >= previous[0] and (current[0] != previous[0] or current[1] == previous[1]),
          'RECOVERY_CHECKPOINT_ROLLBACK')


def _root_ids(value):
    _need(type(value) is tuple and len(value) == 2)
    rows = []
    for item in value:
        _need(type(item) is tuple and len(item) == 2)
        I._integer(item[0], minimum=0)
        I._integer(item[1])
        rows.append(list(item))
    _need(value[0] != value[1])
    return rows


@dataclass(frozen=True, kw_only=True, slots=True)
class RecoveryAttemptLimits:
    max_event_bytes: int = _CAPS['max_event_bytes']
    max_state_bytes: int = _CAPS['max_state_bytes']
    max_routes: int = _CAPS['max_routes']
    max_attempts: int = _CAPS['max_attempts']
    max_delivery_attempts: int = _CAPS['max_delivery_attempts']
    max_new_attempts: int = 1
    max_resumes: int = 2
    min_retry_seconds: int = 60

    def __post_init__(self):
        try:
            for name, cap in _CAPS.items():
                value = getattr(self, name)
                _need(type(value) is int and 1 <= value <= cap, 'RECOVERY_LIMITS_INVALID')
            _need(type(self.max_new_attempts) is int and self.max_new_attempts == 1
                  and type(self.max_resumes) is int and 0 <= self.max_resumes <= 2
                  and type(self.min_retry_seconds) is int and 60 <= self.min_retry_seconds <= 86400,
                  'RECOVERY_LIMITS_INVALID')
        except (AttributeError, TypeError):
            _fail('RECOVERY_LIMITS_INVALID')


DEFAULT_LIMITS = RecoveryAttemptLimits()


def _limits(value):
    _need(type(value) is RecoveryAttemptLimits, 'RECOVERY_LIMITS_INVALID')
    value.__post_init__()
    return value


@dataclass(frozen=True, kw_only=True, slots=True)
class OwnerCheckpoint:
    key_fingerprint: str
    code_hash: str
    owner_head: tuple[int, str]
    observed_at: datetime

    @_fixed
    def __post_init__(self):
        _checkpoint_doc(self)


def _checkpoint_doc(value):
    _need(type(value) is OwnerCheckpoint)
    _need(type(value.key_fingerprint) is str and len(value.key_fingerprint) == 71
          and value.key_fingerprint.startswith('SHA256:'))
    I._hash(value.key_fingerprint[7:])
    I._hash(value.code_hash)
    return dict(key_fingerprint=value.key_fingerprint, code_hash=value.code_hash,
                owner_head=_head(value.owner_head, minimum=1), observed_at=I._stamp(value.observed_at))


@_fixed
def checkpoint_document(checkpoint):
    return _checkpoint_doc(checkpoint)


@_fixed
def parse_checkpoint(document):
    I._keys(document, (field.name for field in fields(OwnerCheckpoint)))
    return OwnerCheckpoint(**{**document, 'owner_head':_parse_head(document['owner_head'], minimum=1),
                              'observed_at':I._time(document['observed_at'])})


@dataclass(frozen=True, kw_only=True, slots=True)
class RecoveryRoute:
    incident_namespace_sha256: str
    attempt_namespace_sha256: str
    incident_head: tuple[int, str]
    registration: I.TargetRegistration
    source_configuration_sha256: str
    source_root_ids: tuple[tuple[int, int], tuple[int, int]]
    destination_configuration_sha256: str
    destination_root_ids: tuple[tuple[int, int], tuple[int, int]]
    destination_context_sha256: str
    storage_policy_sha256: str
    object_policy_sha256: str
    attestation_sha256: str
    request_sha256: str
    file_set_sha256: str
    revocation_target_sha256: str
    issued_at: datetime
    expires_at: datetime
    checkpoint: OwnerCheckpoint

    @_fixed
    def __post_init__(self):
        _route_doc(self)

    @property
    @_fixed
    def route_id(self):
        return _route_doc(self)['route_id']


def _route_doc(value):
    _need(type(value) is RecoveryRoute)
    document = {}
    for field in fields(RecoveryRoute):
        name, item = field.name, getattr(value, field.name)
        if name.endswith('_sha256'):
            document[name] = I._hash(item)
        elif name == 'incident_head':
            document[name] = _head(item)
        elif name == 'registration':
            document[name] = I.registration_document(item)
        elif name.endswith('_root_ids'):
            document[name] = _root_ids(item)
        elif name in ('issued_at', 'expires_at'):
            document[name] = I._stamp(item)
        else:
            document[name] = _checkpoint_doc(item)
    _need(value.issued_at <= value.checkpoint.observed_at < value.expires_at
          and value.expires_at-value.issued_at <= timedelta(seconds=86400))
    _need(not set(value.source_root_ids).intersection(value.destination_root_ids))
    core = {key:item for key, item in document.items() if key not in ('incident_head', 'checkpoint')}
    core['checkpoint'] = {key:document['checkpoint'][key] for key in ('key_fingerprint', 'code_hash')}
    return {**document, 'route_id':_digest('route', core)}


@_fixed
def route_document(route):
    return _route_doc(route)


@_fixed
def parse_route(document, *, limits=DEFAULT_LIMITS):
    limits = _limits(limits)
    I._keys(document, (*[field.name for field in fields(RecoveryRoute)], 'route_id'))
    values = dict(document)
    claimed = values.pop('route_id')
    I._hash(claimed)
    values['registration'] = I.parse_registration(values['registration'])
    values['checkpoint'] = parse_checkpoint(values['checkpoint'])
    values['incident_head'] = _parse_head(values['incident_head'])
    for name in ('source_root_ids', 'destination_root_ids'):
        roots = values[name]
        _need(type(roots) is list and len(roots) == 2 and all(type(item) is list for item in roots))
        values[name] = tuple(tuple(item) for item in roots)
    for name in ('issued_at', 'expires_at'):
        values[name] = I._time(values[name])
    result = RecoveryRoute(**values)
    _need(result.route_id == claimed, 'RECOVERY_ROUTE_ID_MISMATCH')
    I._bounded(_route_doc(result), limits.max_event_bytes)
    return result


@_fixed
def artifact_incident_id(incident_id):
    I._hash(incident_id)
    return 'i'+base64.b32encode(bytes.fromhex(incident_id)).decode('ascii').lower().rstrip('=')


@_fixed
def plan_id(route, incident_id):
    I._hash(incident_id)
    return _digest('plan', dict(route_id=_route_doc(route)['route_id'], incident_id=incident_id))


@_fixed
def attempt_id(route, incident_id):
    return _digest('attempt', dict(plan_id=plan_id(route, incident_id), ordinal=1))


def _optional_checkpoint(value):
    return None if value is None else _checkpoint_doc(parse_checkpoint(value))


def _outcome_payload(document, *, preflight):
    keys = ('route_id', 'incident_id', 'execution_number', 'incident_head', 'status', 'reason_code',
            'checkpoint', 'revocation_status') if preflight else (
            'attempt_id', 'execution_number', 'status', 'reason_code', 'checkpoint', 'revocation_status',
            'verified_at', 'recovery_artifact_digest', 'destination_head')
    I._keys(document, keys)
    for key in ('route_id', 'incident_id') if preflight else ('attempt_id',):
        I._hash(document[key])
    I._integer(document['execution_number'], maximum=3)
    I._enum(document['status'], _STATUS)
    _need(type(document['reason_code']) is str and _REASON.fullmatch(document['reason_code']) is not None)
    I._enum(document['revocation_status'], _REVOCATION)
    document = {**document, 'checkpoint':_optional_checkpoint(document['checkpoint'])}
    _need(document['revocation_status'] == 'UNOBSERVED' or document['checkpoint'] is not None)
    if preflight:
        document['incident_head'] = _head(_parse_head(document['incident_head']))
        _need(document['status'] != 'EXACT_ARCHIVE_RESTORED')
    else:
        if document['verified_at'] is not None:
            document['verified_at'] = I._stamp(I._time(document['verified_at']))
        if document['recovery_artifact_digest'] is not None:
            I._hash(document['recovery_artifact_digest'])
        if document['destination_head'] is not None:
            document['destination_head'] = _head(_parse_head(document['destination_head']))
        if document['status'] == 'EXACT_ARCHIVE_RESTORED':
            _need(document['checkpoint'] is not None and document['verified_at'] is not None
                  and document['recovery_artifact_digest'] is not None and document['destination_head'] is not None
                  and document['revocation_status'] == 'NOT_REVOKED_AT_HEAD')
    return document


def _payload(kind, body, limits):
    if kind == 'ROUTE_REGISTERED':
        return route_document(parse_route(body, limits=limits))
    if kind in ('ATTEMPT_STARTED', 'RESUME_STARTED'):
        I._keys(body, ('route_id', 'incident_id', 'incident_head', 'checkpoint') if kind == 'ATTEMPT_STARTED'
                else ('attempt_id', 'execution_number', 'incident_head', 'checkpoint'))
        for key in ('route_id', 'incident_id') if kind == 'ATTEMPT_STARTED' else ('attempt_id',):
            I._hash(body[key])
        if kind == 'RESUME_STARTED':
            I._integer(body['execution_number'], maximum=3)
        return {**body, 'incident_head':_head(_parse_head(body['incident_head'])),
                'checkpoint':checkpoint_document(parse_checkpoint(body['checkpoint']))}
    if kind in ('PREFLIGHT_REFUSED', 'ATTEMPT_OBSERVED'):
        return _outcome_payload(body, preflight=kind == 'PREFLIGHT_REFUSED')
    I._keys(body, ('message_id', 'delivery_attempt_id', 'outcome'))
    I._hash(body['message_id'])
    _need(type(body['delivery_attempt_id']) is str and _ID.fullmatch(body['delivery_attempt_id']) is not None)
    I._enum(body['outcome'], ('delivered', 'failed', 'unknown'))
    return dict(body)


@dataclass(frozen=True, kw_only=True, slots=True)
class RecoveryEvent:
    schema: int
    event_id: str
    kind: str
    observed_at: datetime | None
    payload: dict

    @_fixed
    def __post_init__(self):
        document = _event_doc(self, DEFAULT_LIMITS)
        object.__setattr__(self, 'payload', I._freeze(document['payload']))
        if self.observed_at is not None:
            object.__setattr__(self, 'observed_at', I._time(document['observed_at']))


def _event_doc(event, limits):
    _need(type(event) is RecoveryEvent and type(event.schema) is int and event.schema == 1)
    I._hash(event.event_id)
    I._enum(event.kind, _KINDS)
    payload = _payload(event.kind, I._plain(event.payload), limits)
    if event.observed_at is None:
        _need(event.kind in ('PREFLIGHT_REFUSED', 'ATTEMPT_OBSERVED')
              and payload['status'] == 'AUTHORITY_REFUSED' and payload['checkpoint'] is None
              and payload['revocation_status'] == 'UNOBSERVED'
              and (event.kind == 'PREFLIGHT_REFUSED' or payload['verified_at'] is None))
        at = None
    else:
        at = I._stamp(event.observed_at)
    body = dict(schema=1, kind=event.kind, observed_at=at, payload=payload)
    _need(event.event_id == _digest('event', body), 'RECOVERY_EVENT_ID_MISMATCH')
    document = {**body, 'event_id':event.event_id}
    I._bounded(document, limits.max_event_bytes)
    return document


@_fixed
def make_event(kind, payload, *, observed_at):
    I._enum(kind, _KINDS)
    body = dict(schema=1, kind=kind, payload=_payload(kind, I._plain(payload), DEFAULT_LIMITS),
                observed_at=None if observed_at is None else I._stamp(observed_at))
    return RecoveryEvent(schema=1, event_id=_digest('event', body), kind=kind,
                         observed_at=observed_at, payload=body['payload'])


@_fixed
def event_bytes(event, *, limits=DEFAULT_LIMITS):
    limits = _limits(limits)
    return I._bounded(_event_doc(event, limits), limits.max_event_bytes)


@_fixed
def parse_event(raw, *, limits=DEFAULT_LIMITS):
    limits = _limits(limits)
    body = I._decode(raw, limits.max_event_bytes)
    I._keys(body, ('schema', 'event_id', 'kind', 'observed_at', 'payload'))
    event = RecoveryEvent(**{**body, 'observed_at':None if body['observed_at'] is None else I._time(body['observed_at'])})
    _event_doc(event, limits)
    return event


@dataclass(frozen=True, kw_only=True, slots=True)
class ExecutionEntry:
    execution_number: int
    kind: str
    observed_at: datetime | None
    incident_head: tuple[int, str]
    checkpoint: OwnerCheckpoint | None


@dataclass(frozen=True, kw_only=True, slots=True)
class AttemptOutcome:
    event_id: str
    execution_number: int
    status: str
    reason_code: str
    observed_at: datetime | None
    checkpoint: OwnerCheckpoint | None
    revocation_status: str
    verified_at: datetime | None
    recovery_artifact_digest: str | None
    destination_head: tuple[int, str] | None


@dataclass(frozen=True, kw_only=True, slots=True)
class RecoveryAttempt:
    plan_id: str
    attempt_id: str
    route_id: str
    incident_id: str
    artifact_incident_id: str
    entries: tuple[ExecutionEntry, ...]
    outcomes: tuple[AttemptOutcome, ...]

    @property
    def phase(self):
        if self.outcomes and self.outcomes[-1].execution_number == len(self.entries):
            return self.outcomes[-1].status
        return 'IN_PROGRESS'

    @property
    def terminal(self):
        return self.phase in _TERMINAL

    @property
    def execution_count(self):
        return len(self.entries)


@dataclass(frozen=True, kw_only=True, slots=True)
class RecoveryNotification:
    message_id: str
    attempt_id: str
    outcome_event_id: str
    kind: str
    bundle_digest: str
    status: str
    reason_code: str
    quarantine: str
    current_use: str


@dataclass(frozen=True, kw_only=True, slots=True)
class RecoveryDelivery:
    message_id: str
    delivery_attempt_id: str
    outcome: str
    observed_at: datetime


@dataclass(frozen=True, kw_only=True, slots=True)
class RecoveryState:
    routes: tuple[RecoveryRoute, ...]
    attempts: tuple[RecoveryAttempt, ...]
    outbox: tuple[RecoveryNotification, ...]
    receipts: tuple[RecoveryDelivery, ...]
    events: tuple[RecoveryEvent, ...]
    last_trusted_at: datetime | None

    @property
    @_fixed
    def pending_notifications(self):
        _validate_state(self, DEFAULT_LIMITS)
        delivered = {item.message_id for item in self.receipts if item.outcome == 'delivered'}
        return tuple(item for item in self.outbox if item.message_id not in delivered)


def initial_state():
    return RecoveryState(routes=(), attempts=(), outbox=(), receipts=(), events=(), last_trusted_at=None)


def _route(state, identifier, index=None):
    result = (index['routes'].get(identifier) if index is not None
              else next((item for item in state.routes if item.route_id == identifier), None))
    _need(result is not None, 'RECOVERY_ROUTE_UNKNOWN')
    return result


def _attempt(state, identifier, index=None):
    result = (index['attempts'].get(identifier) if index is not None
              else next((item for item in state.attempts if item.attempt_id == identifier), None))
    _need(result is not None, 'RECOVERY_ATTEMPT_UNKNOWN')
    return result


def _checkpoint(checkpoint, route, at, *, previous=None, current=False):
    _checkpoint_doc(checkpoint)
    _need(checkpoint.key_fingerprint == route.checkpoint.key_fingerprint
          and checkpoint.code_hash == route.checkpoint.code_hash, 'RECOVERY_CHECKPOINT_CHANGED')
    _extends(checkpoint.owner_head, route.checkpoint.owner_head)
    if previous is not None:
        _extends(checkpoint.owner_head, previous.owner_head)
        _need(checkpoint.observed_at >= previous.observed_at, 'RECOVERY_CLOCK_ROLLBACK')
    _need(at is not None and checkpoint.observed_at <= at, 'RECOVERY_CHECKPOINT_TIME_INVALID')
    if current:
        _need(at-checkpoint.observed_at <= timedelta(seconds=30), 'RECOVERY_CHECKPOINT_STALE')
        _need(route.issued_at <= at < route.expires_at, 'RECOVERY_ORIGINAL_APPROVAL_EXPIRED')


def _latest_checkpoint(route, attempt):
    points = [route.checkpoint]
    if attempt is not None:
        points += [entry.checkpoint for entry in attempt.entries if entry.checkpoint is not None]
        points += [outcome.checkpoint for outcome in attempt.outcomes if outcome.checkpoint is not None]
    return max(points, key=lambda item:(item.observed_at, item.owner_head[0]))


def _entry_admission(attempt, number, at, limits):
    if attempt is None:
        _need(number == 1, 'RECOVERY_EXECUTION_SEQUENCE_INVALID')
        return
    _need(not attempt.terminal, 'RECOVERY_ATTEMPT_TERMINAL')
    _need(number == len(attempt.entries)+1, 'RECOVERY_EXECUTION_SEQUENCE_INVALID')
    _need(number <= 1+limits.max_resumes, 'RECOVERY_EXECUTION_LIMIT')
    if at is not None:
        stamps = [entry.observed_at for entry in attempt.entries if entry.observed_at is not None]
        stamps += [outcome.observed_at for outcome in attempt.outcomes if outcome.observed_at is not None]
        _need(stamps and at >= max(stamps)+timedelta(seconds=limits.min_retry_seconds), 'RECOVERY_RETRY_NOT_DUE')


def _replace_attempt(attempts, updated):
    if any(item.attempt_id == updated.attempt_id for item in attempts):
        return tuple(updated if item.attempt_id == updated.attempt_id else item for item in attempts)
    return attempts+(updated,)


def _new_attempt(route_identifier, incident):
    plan = _digest('plan', dict(route_id=route_identifier, incident_id=incident))
    identifier = _digest('attempt', dict(plan_id=plan, ordinal=1))
    return RecoveryAttempt(plan_id=plan, attempt_id=identifier, route_id=route_identifier,
        incident_id=incident, artifact_incident_id=artifact_incident_id(incident), entries=(), outcomes=())


def _observe(attempt, route, event, body, *, preflight=False):
    number = body['execution_number']
    _need(number == len(attempt.entries) and not any(item.execution_number == number for item in attempt.outcomes),
          'RECOVERY_OUTCOME_CONFLICT')
    checkpoint = None if body['checkpoint'] is None else parse_checkpoint(body['checkpoint'])
    if checkpoint is not None:
        _checkpoint(checkpoint, route, event.observed_at, previous=_latest_checkpoint(route, attempt),
                    current=body['status'] == 'EXACT_ARCHIVE_RESTORED')
    verified = None if preflight or body['verified_at'] is None else I._time(body['verified_at'])
    if verified is not None:
        _need(event.observed_at is not None and verified <= event.observed_at, 'RECOVERY_OBSERVATION_TIME_INVALID')
    if body['status'] == 'EXACT_ARCHIVE_RESTORED':
        _need(verified == event.observed_at, 'RECOVERY_OBSERVATION_TIME_INVALID')
    outcome = AttemptOutcome(event_id=event.event_id, execution_number=number, status=body['status'],
        reason_code=body['reason_code'], observed_at=event.observed_at, checkpoint=checkpoint,
        revocation_status=body['revocation_status'], verified_at=verified,
        recovery_artifact_digest=None if preflight else body['recovery_artifact_digest'],
        destination_head=None if preflight or body['destination_head'] is None else _parse_head(body['destination_head']))
    updated = RecoveryAttempt(plan_id=attempt.plan_id, attempt_id=attempt.attempt_id, route_id=attempt.route_id,
        incident_id=attempt.incident_id, artifact_incident_id=attempt.artifact_incident_id,
        entries=attempt.entries, outcomes=attempt.outcomes+(outcome,))
    message = dict(attempt_id=attempt.attempt_id, outcome_event_id=event.event_id, kind='RECOVERY_RESULT_RECORDED',
        bundle_digest=route.registration.bundle_digest, status=body['status'], reason_code=body['reason_code'],
        quarantine='REMAINS', current_use='NOT_GRANTED')
    return updated, RecoveryNotification(message_id=_digest('notification', message), **message)


def _apply(state, event, limits, *, _index=None):
    if event.observed_at is not None and state.last_trusted_at is not None:
        _need(event.observed_at >= state.last_trusted_at, 'RECOVERY_CLOCK_ROLLBACK')
    routes, attempts, outbox, receipts = state.routes, state.attempts, state.outbox, state.receipts
    body = I._plain(event.payload)
    if event.kind == 'ROUTE_REGISTERED':
        route = parse_route(body, limits=limits)
        route_identifier = body['route_id']
        previous = (_index['routes'].get(route_identifier) if _index is not None
                    else next((item for item in routes if item.route_id == route_identifier), None))
        if previous is not None:
            _need(route_document(previous) == body, 'RECOVERY_ROUTE_CONFLICT')
            return state
        _need(len(routes) < limits.max_routes, 'RECOVERY_RESOURCE_LIMIT')
        _checkpoint(route.checkpoint, route, event.observed_at, current=True)
        routes += (route,)
        if _index is not None:
            _index['routes'][route_identifier] = route
    elif event.kind in ('ATTEMPT_STARTED', 'RESUME_STARTED', 'PREFLIGHT_REFUSED'):
        if event.kind == 'RESUME_STARTED':
            attempt = _attempt(state, body['attempt_id'], _index)
            route_identifier = attempt.route_id
            route = _route(state, route_identifier, _index)
            number = body['execution_number']
        else:
            route_identifier = body['route_id']
            route = _route(state, route_identifier, _index)
            candidate = _new_attempt(route_identifier, body['incident_id'])
            identifier = candidate.attempt_id
            attempt = (_index['attempts'].get(identifier) if _index is not None
                       else next((item for item in attempts if item.attempt_id == identifier), None))
            number = 1 if event.kind == 'ATTEMPT_STARTED' else body['execution_number']
            if event.kind == 'ATTEMPT_STARTED':
                _need(attempt is None, 'RECOVERY_ATTEMPT_EXISTS')
        _entry_admission(attempt, number, event.observed_at, limits)
        checkpoint = None if body['checkpoint'] is None else parse_checkpoint(body['checkpoint'])
        if checkpoint is not None:
            _checkpoint(checkpoint, route, event.observed_at, previous=_latest_checkpoint(route, attempt),
                        current=event.kind != 'PREFLIGHT_REFUSED')
        incident_head = _parse_head(body['incident_head'])
        _extends(incident_head, route.incident_head)
        if attempt is None:
            _need(len(attempts) < limits.max_attempts, 'RECOVERY_RESOURCE_LIMIT')
            attempt = _new_attempt(route_identifier, body['incident_id'])
        elif attempt.entries:
            _extends(incident_head, attempt.entries[-1].incident_head)
        entry = ExecutionEntry(execution_number=number, kind=event.kind, observed_at=event.observed_at,
                               incident_head=incident_head, checkpoint=checkpoint)
        attempt = RecoveryAttempt(plan_id=attempt.plan_id, attempt_id=attempt.attempt_id, route_id=attempt.route_id,
            incident_id=attempt.incident_id, artifact_incident_id=attempt.artifact_incident_id,
            entries=attempt.entries+(entry,), outcomes=attempt.outcomes)
        if event.kind == 'PREFLIGHT_REFUSED':
            attempt, message = _observe(attempt, route, event, body, preflight=True)
            outbox += (message,)
        attempts = _replace_attempt(attempts, attempt)
        if _index is not None:
            _index['attempts'][attempt.attempt_id] = attempt
    elif event.kind == 'ATTEMPT_OBSERVED':
        attempt = _attempt(state, body['attempt_id'], _index)
        _need(attempt.entries[-1].kind != 'PREFLIGHT_REFUSED', 'RECOVERY_OUTCOME_CONFLICT')
        attempt, message = _observe(attempt, _route(state, attempt.route_id, _index), event, body)
        attempts = _replace_attempt(attempts, attempt)
        if _index is not None:
            _index['attempts'][attempt.attempt_id] = attempt
        outbox += (message,)
    else:
        _need(any(item.message_id == body['message_id'] for item in outbox), 'RECOVERY_MESSAGE_UNKNOWN')
        receipt = RecoveryDelivery(**body, observed_at=event.observed_at)
        previous = next((item for item in receipts if item.delivery_attempt_id == receipt.delivery_attempt_id), None)
        if previous is not None:
            _need(previous == receipt, 'RECOVERY_DELIVERY_CONFLICT')
            return state
        _need(not any(item.message_id == receipt.message_id and item.outcome == 'delivered' for item in receipts),
              'RECOVERY_MESSAGE_DELIVERED')
        _need(len(receipts) < limits.max_delivery_attempts, 'RECOVERY_RESOURCE_LIMIT')
        receipts += (receipt,)
    return RecoveryState(routes=routes, attempts=attempts, outbox=outbox, receipts=receipts,
        events=state.events+(event,), last_trusted_at=event.observed_at or state.last_trusted_at)


def _projection(value, cls):
    _need(type(value) is cls, 'RECOVERY_STATE_INVALID')
    result = {}
    for field in fields(cls):
        name, item = field.name, getattr(value, field.name)
        if name in ('observed_at', 'verified_at'):
            result[name] = None if item is None else I._stamp(item)
        elif name == 'checkpoint':
            result[name] = None if item is None else checkpoint_document(item)
        elif name in ('incident_head', 'destination_head'):
            result[name] = None if item is None else _head(item)
        elif name in ('entries', 'outcomes'):
            _need(type(item) is tuple, 'RECOVERY_STATE_INVALID')
            _need(len(item) <= 3, 'RECOVERY_RESOURCE_LIMIT')
            result[name] = [_projection(row, ExecutionEntry if name == 'entries' else AttemptOutcome) for row in item]
        elif name == 'execution_number':
            result[name] = I._integer(item, maximum=3)
        else:
            _need(item is None or type(item) is str, 'RECOVERY_STATE_INVALID')
            _need(item is None or len(item) <= 96, 'RECOVERY_RESOURCE_LIMIT')
            result[name] = item
    return result


def _state_doc(state, limits):
    _need(type(state) is RecoveryState, 'RECOVERY_STATE_INVALID')
    caps = dict(routes=limits.max_routes, attempts=limits.max_attempts,
        outbox=limits.max_attempts*(1+limits.max_resumes), receipts=limits.max_delivery_attempts,
        events=limits.max_routes+limits.max_attempts*(1+limits.max_resumes)*2+limits.max_delivery_attempts)
    document = dict(schema=1, last_trusted_at=None if state.last_trusted_at is None else I._stamp(state.last_trusted_at))
    used = 0
    for name, cls in (('routes', RecoveryRoute), ('attempts', RecoveryAttempt), ('outbox', RecoveryNotification),
                      ('receipts', RecoveryDelivery), ('events', RecoveryEvent)):
        items = getattr(state, name)
        _need(type(items) is tuple, 'RECOVERY_STATE_INVALID')
        _need(len(items) <= caps[name], 'RECOVERY_RESOURCE_LIMIT')
        converted = []
        for item in items:
            value = route_document(item) if name == 'routes' else _event_doc(item, limits) if name == 'events' else _projection(item, cls)
            used += len(I._bounded(value, limits.max_state_bytes))
            _need(used <= limits.max_state_bytes, 'RECOVERY_RESOURCE_LIMIT')
            converted.append(value)
        document[name] = converted
    return document


@_fixed
def _replay_events(raw_events, *, limits=DEFAULT_LIMITS):
    limits = _limits(limits)
    _need(type(raw_events) is tuple, 'RECOVERY_STATE_INVALID')
    _need(len(raw_events) <= limits.max_routes+limits.max_attempts*(1+limits.max_resumes)*2+limits.max_delivery_attempts,
          'RECOVERY_RESOURCE_LIMIT')
    state, seen, used = initial_state(), set(), 0
    # Built only from this fold's strictly decoded rows, never caller state.
    index = {'routes':{}, 'attempts':{}}
    for raw in raw_events:
        _need(type(raw) is bytes)
        used += len(raw)
        _need(used <= limits.max_state_bytes, 'RECOVERY_RESOURCE_LIMIT')
        event = parse_event(raw, limits=limits)
        _need(event.event_id not in seen, 'RECOVERY_STATE_INVALID')
        seen.add(event.event_id)
        updated = _apply(state, event, limits, _index=index)
        _need(updated is not state, 'RECOVERY_STATE_INVALID')
        state = updated
    I._bounded(_state_doc(state, limits), limits.max_state_bytes)
    return state


def _validate_state(state, limits):
    raw = I._bounded(_state_doc(state, limits), limits.max_state_bytes)
    rebuilt = _replay_events(tuple(event_bytes(event, limits=limits) for event in state.events), limits=limits)
    _need(I._bounded(_state_doc(rebuilt, limits), limits.max_state_bytes) == raw, 'RECOVERY_STATE_INVALID')
    return raw


@_fixed
def reduce(state, event, *, limits=DEFAULT_LIMITS):
    limits = _limits(limits)
    _validate_state(state, limits)
    raw = event_bytes(event, limits=limits)
    event = parse_event(raw, limits=limits)
    for old in state.events:
        if old.event_id == event.event_id:
            _need(event_bytes(old, limits=limits) == raw, 'RECOVERY_EVENT_CONFLICT')
            return state
    updated = _apply(state, event, limits)
    I._bounded(_state_doc(updated, limits), limits.max_state_bytes)
    return updated


@_fixed
def state_bytes(state, *, limits=DEFAULT_LIMITS):
    return _validate_state(state, _limits(limits))


@_fixed
def state_digest(state, *, limits=DEFAULT_LIMITS):
    return hashlib.sha256(DOMAIN+b'state\n'+state_bytes(state, limits=limits)).hexdigest()
