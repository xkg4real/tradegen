"""Incident-bound exact archive recovery with durable attempts and no release.

All graph, signature and owner checks use the actual existing implementations.
Registered routes describe configuration, never permission. START is durable
before destination writes; final completion requires new destination reads.
Historical results and outbox intents grant no selection, trading or release.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
import hashlib
import json
from threading import Lock

from core.compliance import model as compliance
from execution_control.owner_authority import CurrentOwnerAuthority, OwnerAuthorityError, MAX_AUTHORITY_AGE_SECONDS
from execution_launch import bundle_attestation as A
from execution_launch import bundle_auth as U
from execution_launch import bundle_recovery as B
from execution_launch import research_bundle_format as BF
from execution_launch import research_bundle_store as BS
from execution_launch import research_incident_monitor as M
from execution_launch import research_incidents as I
from execution_launch import research_recovery_attempts as F
from execution_launch.research_incident_store import IncidentStore
from execution_launch.research_recovery_store import RecoveryAttemptStore, RecoveryStoreError
from execution_launch.recovery_artifact import build_recovery_artifact
from execution_launch.evidence_objects import EvidenceObjectError
from execution_launch.baseline_head import BaselineHeadError
from execution_launch.research_revocation import revocation_target, target_is_revoked

_DOMAIN = b'tradegen-research-recovery-controller/1\n'
_FRESH = timedelta(seconds=MAX_AUTHORITY_AGE_SECONDS)
_LATCH_LOCK = Lock()
_LATCHED = set()
_LATCH_EXHAUSTED = False


class ResearchRecoveryError(ValueError):
    """Fixed diagnostics only; no supplied roots, bytes, keys or OS messages."""


class _Revoked(ResearchRecoveryError):
    """Private actual observation facts, never supplied by the public caller."""
    def __init__(self, authority):
        super().__init__('RECOVERY_ATTESTATION_REVOKED')
        self.checkpoint = _checkpoint(authority)


def _need(value, code):
    if not value:
        raise ResearchRecoveryError(code)


def _hash(value):
    return type(value) is str and len(value) == 64 and all(c in '0123456789abcdef' for c in value)


def _digest(kind, body):
    raw = json.dumps(body, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode('ascii')
    return hashlib.sha256(_DOMAIN+kind.encode('ascii')+b'\n'+raw).hexdigest()


def _latch(namespace):
    global _LATCH_EXHAUSTED
    with _LATCH_LOCK:
        if len(_LATCHED) >= 256:
            _LATCH_EXHAUSTED = True
        else:
            _LATCHED.add(namespace)


def _not_latched(namespace):
    with _LATCH_LOCK:
        _need(not _LATCH_EXHAUSTED and namespace not in _LATCHED, 'RECOVERY_RECORD_UNCONFIRMED')


def _attempt_namespace(store):
    _need(type(store) is RecoveryAttemptStore, 'RECOVERY_ACTUAL_ATTEMPT_STORE_REQUIRED')
    store._configuration()
    return _digest('attempt-namespace', dict(context=store.context_sha256,
        roots=[str(path) for path in store._roots], root_ids=store._root_ids, head_name=store._head_name))


def _source_configuration(source):
    roots, limits = B._source_configuration(source)
    return _digest('source-configuration', dict(roots=[str(path) for path in roots], limits=limits))


def _destination_configuration(store):
    _need(type(store) is BS.BundleStore, 'RECOVERY_ACTUAL_DESTINATION_REQUIRED')
    store._configuration()
    return _digest('destination-configuration', dict(
        roots=[str(store.roots.sealed_root), str(store.roots.backup_root)],
        limits=asdict(store.limits), head_name=store._head_name, context=store.context_sha256))


def _head(store):
    with store._locked():
        catalog = store._load()
        return catalog.sequence, catalog.head


def _separation(incidents, attempts, source, destination, *, allow_missing_source=False):
    incidents._configuration(); attempts._configuration(); destination._configuration()
    roots = (source.roots.sealed_root, source.roots.backup_root,
             destination.roots.sealed_root, destination.roots.backup_root,
             *incidents._roots, *attempts._roots)
    identities = tuple(B._directory(path, missing=allow_missing_source and index < 2)
                       for index, path in enumerate(roots))
    for index, path in enumerate(roots):
        for other_index, other in enumerate(roots[:index]):
            _need(not path.is_relative_to(other) and not other.is_relative_to(path)
                  and not path.resolve(strict=False).is_relative_to(other.resolve(strict=False))
                  and not other.resolve(strict=False).is_relative_to(path.resolve(strict=False))
                  and (identities[index] is None or identities[other_index] is None
                       or identities[index] != identities[other_index]), 'RECOVERY_ROOT_OVERLAP')
    return identities[:2], identities[2:4]


def _clock(clock, minimum=None):
    try:
        now = U._time(clock())
    except Exception:
        raise ResearchRecoveryError('RECOVERY_CLOCK_INVALID') from None
    _need(minimum is None or now >= minimum, 'RECOVERY_CLOCK_ROLLBACK')
    return now


def _provider(provider, clock):
    _need(type(provider) is CurrentOwnerAuthority and callable(clock)
          and provider._clock is clock, 'RECOVERY_ACTUAL_PROVIDER_REQUIRED')


def _checkpoint(authority):
    return F.OwnerCheckpoint(key_fingerprint=authority.context.owner.fingerprint,
        code_hash=authority.context.code_hash, owner_head=authority.context.owner.head,
        observed_at=authority.observed_at)


def _observe(document, provider, clock, required, *, minimum=None):
    now = _clock(clock, minimum)
    authority = (provider(now) if required is None else provider.observe_checkpoint(now,
        key_fingerprint=required.key_fingerprint, code_hash=required.code_hash, owner_head=required.owner_head))
    U._authority(document, authority, now)
    target = revocation_target(document, purpose=A.PURPOSE)
    if target_is_revoked(U._revocations(authority.context), purpose=A.PURPOSE, target_sha256=target):
        raise _Revoked(authority)
    return authority, _checkpoint(authority)


def _finish(document, authorities, clock, *, minimum, provider, guard=None):
    # Read only the actual provider completion; never assign caller checkpoint pins.
    minimum = max(minimum, U._time(provider._last))
    # All parsing, signature verification and context hashing precede the final clock.
    body = None
    for authority in authorities:
        body = U._authority(document, authority, minimum)
    issued, expires = datetime.fromisoformat(body['issued_at']), datetime.fromisoformat(body['expires_at'])
    stamps = tuple((authority.observed_at, authority.context.date) for authority in authorities)
    if guard is not None:
        guard()
    now = _clock(clock, minimum)
    _need(issued <= now < expires, 'RECOVERY_ATTESTATION_EXPIRED_OR_FUTURE')
    for observed, day in stamps:
        _need(timedelta(0) <= now-observed <= _FRESH, 'RECOVERY_OWNER_OBSERVATION_STALE')
        _need(day == now.astimezone(compliance.KST).date(), 'RECOVERY_OWNER_DAY_CHANGED')
    return now


def _commit(store, namespace, event, head):
    try:
        return store.commit(event, expected_head=head)
    except Exception:
        _latch(namespace)
        raise ResearchRecoveryError('RECOVERY_RECORD_UNCONFIRMED') from None


def _route_in(state, route_id):
    return next((route for route in state.routes if route.route_id == route_id), None)


def _attempt_in(state, route_id, incident_id):
    return next((attempt for attempt in state.attempts
                 if attempt.route_id == route_id and attempt.incident_id == incident_id), None)


def _incident(incidents, route, incident_id):
    _need(M.namespace_identity(incidents) == route.incident_namespace_sha256,
          'RECOVERY_INCIDENT_NAMESPACE_CHANGED')
    snapshot = incidents.inspect()
    registration = M._existing(snapshot.state, route.registration.store_binding_sha256,
                               route.registration.bundle_digest)
    _need(registration is not None and registration == route.registration,
          'RECOVERY_REGISTRATION_CHANGED')
    _need(any(item.incident_id == incident_id for item in I.blocked_incidents(snapshot.state, registration)),
          'RECOVERY_DEPENDENT_INCIDENT_REQUIRED')
    return snapshot


@dataclass(frozen=True, kw_only=True)
class RecoveryRouteConfig:
    source: B.SignedBackupSource
    destination: BS.BundleStore


@dataclass(frozen=True, kw_only=True)
class RecoveryRouteObservation:
    route_id: str
    bundle_digest: str
    incident_namespace_sha256: str
    attempt_namespace_sha256: str
    attempt_head: str
    attempt_sequence: int
    registered_at: datetime


@dataclass(frozen=True, kw_only=True)
class RecoveryControllerObservation:
    route_id: str
    plan_id: str
    attempt_id: str
    incident_id: str
    artifact_incident_id: str
    bundle_digest: str
    phase: str
    execution_count: int
    outcome_event_id: str | None
    recovery_artifact_digest: str | None
    attempt_head: str
    attempt_sequence: int
    observed_at: datetime | None
    quarantine_released: bool = False
    current_use_eligible: bool = False
    research_selection_ready: bool = False
    execution_ready: bool = False
    automatic_operational_recovery_supported: bool = False


def _projection(snapshot, route, incident_id):
    attempt = _attempt_in(snapshot.state, route.route_id, incident_id)
    _need(attempt is not None, 'RECOVERY_ATTEMPT_MISSING')
    outcome = attempt.outcomes[-1] if attempt.outcomes else None
    return RecoveryControllerObservation(route_id=route.route_id, plan_id=attempt.plan_id,
        attempt_id=attempt.attempt_id, incident_id=incident_id, artifact_incident_id=attempt.artifact_incident_id,
        bundle_digest=route.registration.bundle_digest, phase=attempt.phase,
        execution_count=attempt.execution_count, outcome_event_id=None if outcome is None else outcome.event_id,
        recovery_artifact_digest=None if outcome is None else outcome.recovery_artifact_digest,
        attempt_head=snapshot.head, attempt_sequence=snapshot.sequence,
        observed_at=attempt.entries[-1].observed_at if outcome is None else outcome.observed_at)


def register_recovery_route(incident_store, attempts, source_store, destination, bundle_digest,
                            attestation_bytes, *, clock, authority_provider):
    """Observe an existing healthy registered graph and explicit prepared destination."""
    _provider(authority_provider, clock)
    _need(type(incident_store) is IncidentStore and type(source_store) is BS.BundleStore,
          'RECOVERY_ACTUAL_STORE_REQUIRED')
    namespace = _attempt_namespace(attempts); _not_latched(namespace)
    source_store._configuration()
    source = B.SignedBackupSource(roots=source_store.roots, limits=source_store.limits)
    envelope = A.parse_attestation_document(attestation_bytes)
    body, request = envelope['body'], envelope['body']['request']
    _need(_hash(bundle_digest) and request['bundle_digest'] == bundle_digest, 'RECOVERY_TARGET_MISMATCH')
    with attempts.operation():
        state = attempts.inspect()
        source_ids, destination_ids = _separation(incident_store, attempts, source, destination)
        _need(source_ids == source_store._root_ids and destination_ids == destination._root_ids,
              'RECOVERY_ROOT_CHANGED')
        incident_namespace, binding = M._inputs(incident_store, source_store, bundle_digest)
        incidents = incident_store.inspect()
        registration = M._existing(incidents.state, binding, bundle_digest)
        _need(registration is not None, 'RECOVERY_REGISTERED_TARGET_REQUIRED')
        _need(not I.blocked_incidents(incidents.state, registration), 'RECOVERY_ROUTE_SOURCE_HELD')
        first, checkpoint = _observe(attestation_bytes, authority_provider, clock, None,
                                     minimum=state.state.last_trusted_at)
        try:
            graph = M._complete_graph(source_store, bundle_digest, binding,
                                      incident_store.limits.format_limits)
        except M._GraphFailure as exc:
            raise exc.cause from None
        _need(M._same_graph(registration, graph), 'RECOVERY_REGISTRATION_CHANGED')
        U.authenticate_bundle_attestation(source_store, bundle_digest, attestation_bytes,
                                         authority_provider=authority_provider, clock=clock)
        _head(destination)  # actual already-provisioned catalog/head; never seed
        latest, checkpoint = _observe(attestation_bytes, authority_provider, clock, checkpoint,
                                      minimum=first.observed_at)
        _need(incident_store.inspect() == incidents, 'RECOVERY_INCIDENT_CHANGED')
        _need(_separation(incident_store, attempts, source, destination) == (source_ids, destination_ids),
              'RECOVERY_ROOT_CHANGED')
        route = F.RecoveryRoute(incident_namespace_sha256=incident_namespace,
            attempt_namespace_sha256=namespace, incident_head=(incidents.sequence, incidents.head),
            registration=registration, source_configuration_sha256=_source_configuration(source),
            source_root_ids=source_ids, destination_configuration_sha256=_destination_configuration(destination),
            destination_root_ids=destination_ids, destination_context_sha256=destination.context_sha256,
            storage_policy_sha256=destination.limits.policy_sha256,
            object_policy_sha256=destination.limits.object_limits.policy_sha256,
            attestation_sha256=A.attestation_document_digest(attestation_bytes),
            request_sha256=request['request_sha256'], file_set_sha256=request['file_set_sha256'],
            revocation_target_sha256=revocation_target(attestation_bytes, purpose=A.PURPOSE),
            issued_at=datetime.fromisoformat(body['issued_at']), expires_at=datetime.fromisoformat(body['expires_at']),
            checkpoint=checkpoint)
        _need(asdict(source.limits) == asdict(destination.limits), 'RECOVERY_POLICY_MISMATCH')
        retained = _route_in(state.state, route.route_id)
        observations = (first, latest)
        if retained is not None:
            # Validate the original actual prefix before the final completion clock.
            prefix, _ = _observe(attestation_bytes, authority_provider, clock, retained.checkpoint,
                                 minimum=latest.observed_at)
            observations += (prefix,)
        def final_guard():
            attempts.check_operation()
            _need(incident_store.head.read() == incidents.head and attempts.head.read() == state.head,
                  'RECOVERY_FINAL_HEAD_CHANGED')
        finished = _finish(attestation_bytes, observations, clock,
                           minimum=observations[-1].observed_at, provider=authority_provider, guard=final_guard)
        if retained is not None:
            # Stable identity excludes observed heads/times; preserve the original route.
            return RecoveryRouteObservation(route_id=retained.route_id, bundle_digest=bundle_digest,
                incident_namespace_sha256=incident_namespace, attempt_namespace_sha256=namespace,
                attempt_head=state.head, attempt_sequence=state.sequence, registered_at=retained.checkpoint.observed_at)
        event = F.make_event('ROUTE_REGISTERED', F.route_document(route), observed_at=finished)
        attempts.admit(event, expected_head=state.head)
        committed = _commit(attempts, namespace, event, state.head)
        return RecoveryRouteObservation(route_id=route.route_id, bundle_digest=bundle_digest,
            incident_namespace_sha256=incident_namespace, attempt_namespace_sha256=namespace,
            attempt_head=committed.head, attempt_sequence=committed.sequence, registered_at=finished)


def _bound_config(incidents, attempts, config, route, namespace, *, paths):
    _need(type(config) is RecoveryRouteConfig and type(config.source) is B.SignedBackupSource
          and type(config.destination) is BS.BundleStore, 'RECOVERY_ROUTE_CONFIG_REQUIRED')
    _need(namespace == route.attempt_namespace_sha256
          and M.namespace_identity(incidents) == route.incident_namespace_sha256,
          'RECOVERY_NAMESPACE_CHANGED')
    _need(_source_configuration(config.source) == route.source_configuration_sha256
          and _destination_configuration(config.destination) == route.destination_configuration_sha256
          and config.destination.context_sha256 == route.destination_context_sha256
          and config.destination._root_ids == route.destination_root_ids,
          'RECOVERY_CONFIGURATION_CHANGED')
    _need(config.destination.limits.policy_sha256 == route.storage_policy_sha256
          and config.destination.limits.object_limits.policy_sha256 == route.object_policy_sha256
          and asdict(config.source.limits) == asdict(config.destination.limits), 'RECOVERY_POLICY_MISMATCH')
    if paths:
        source_ids, destination_ids = _separation(incidents, attempts, config.source, config.destination,
                                                 allow_missing_source=True)
        _need(all(actual is None or actual == original for actual, original in zip(source_ids, route.source_root_ids))
              and destination_ids == route.destination_root_ids, 'RECOVERY_ROOT_CHANGED')
        return source_ids


def _document_binding(document, route):
    body = A.parse_attestation_document(document)['body']; request = body['request']
    _need(A.attestation_document_digest(document) == route.attestation_sha256
          and request['bundle_digest'] == route.registration.bundle_digest
          and request['input_archive_digest'] == route.registration.input_archive_digest
          and request['request_sha256'] == route.request_sha256
          and request['file_set_sha256'] == route.file_set_sha256
          and revocation_target(document, purpose=A.PURPOSE) == route.revocation_target_sha256,
          'RECOVERY_DOCUMENT_CHANGED')
    return body, request


def _required_checkpoint(route, attempt):
    points = [route.checkpoint]
    if attempt is not None:
        points.extend(item.checkpoint for item in (*attempt.entries, *attempt.outcomes)
                      if item.checkpoint is not None)
    return max(points, key=lambda value:(value.observed_at, value.owner_head[0]))


def _admit_retry(state, attempt, limits, now):
    if attempt is None:
        return 1
    _need(not attempt.terminal, 'RECOVERY_ATTEMPT_TERMINAL')
    _need(attempt.execution_count < 1+limits.max_resumes, 'RECOVERY_EXECUTION_BUDGET_EXHAUSTED')
    prior_times = tuple(item.observed_at for item in (*attempt.entries, *attempt.outcomes)
                        if item.observed_at is not None)
    _need(now is not None and prior_times
          and now >= max(prior_times)+timedelta(seconds=limits.min_retry_seconds), 'RECOVERY_RETRY_NOT_DUE')
    return attempt.execution_count+1


def _reason(exc):
    # Plain ValueError/OS text, including uppercase-looking private data, is never echoed.
    allowed = (ResearchRecoveryError, OwnerAuthorityError, U.BundleAuthenticationError,
               B.BundleRecoveryError, BS.BundleStoreError, BF.BundleFormatError,
               F.RecoveryAttemptError, RecoveryStoreError, M.IncidentMonitorError,
               EvidenceObjectError, BaselineHeadError)
    code = str(exc) if isinstance(exc, allowed) else 'RECOVERY_OPERATION_REFUSED'
    return code if (1 <= len(code) <= 96 and code[0] in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
                    and all(c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_' for c in code)) else 'RECOVERY_OPERATION_REFUSED'


def _failure(exc, *, destination=False):
    code = _reason(exc)
    authority = (code.startswith('OWNER_AUTHORITY_') or code in (
        'RECOVERY_ATTESTATION_REVOKED', 'RECOVERY_ATTESTATION_EXPIRED_OR_FUTURE',
        'RECOVERY_OWNER_OBSERVATION_STALE', 'RECOVERY_OWNER_DAY_CHANGED',
        'RECOVERY_CLOCK_INVALID', 'RECOVERY_CLOCK_ROLLBACK',
        'ARCHIVE_AUTH_OWNER_AUTHORITY_STALE', 'ARCHIVE_AUTH_OWNER_CONTEXT_INVALID',
        'ARCHIVE_AUTH_OWNER_APPROVAL_REQUIRED', 'ARCHIVE_AUTH_CURRENT_KEY_MISMATCH',
        'ARCHIVE_AUTH_DEPLOYMENT_CODE_MISMATCH', 'ARCHIVE_AUTH_EXPIRED_OR_FUTURE',
        'BUNDLE_RECOVERY_EXPIRED_OR_FUTURE', 'BUNDLE_RECOVERY_CLOCK_ROLLBACK',
        'BUNDLE_RECOVERY_OWNER_DAY_CHANGED', 'BUNDLE_RECOVERY_AUTHORITY_STALE'))
    if authority:
        return 'AUTHORITY_REFUSED', code
    if any(part in code for part in ('RESOURCE_LIMIT', 'LIMIT_EXCEEDED', 'BUDGET', 'QUOTA')):
        return 'RESOURCE_LIMIT', code
    if destination:
        return 'DESTINATION_UNCONFIRMED', code
    if isinstance(exc, (OSError, RuntimeError)) or any(part in code for part in (
            'UNAVAILABLE', 'IO_REFUSED', 'LOCKED', 'PATH_REFUSED', 'NOT_PUBLISHED', 'NOT_FOUND', 'MISSING')):
        return 'READ_UNAVAILABLE', code
    return 'EVIDENCE_REFUSED', code


def _record_refusal(attempts, namespace, snapshot, route, incident_id, incident,
                    number, status, reason, *, now, checkpoint=None, revocation='UNOBSERVED'):
    event = F.make_event('PREFLIGHT_REFUSED', dict(route_id=route.route_id, incident_id=incident_id,
        execution_number=number, incident_head=[incident.sequence, incident.head], status=status,
        reason_code=reason, checkpoint=None if checkpoint is None else F.checkpoint_document(checkpoint),
        revocation_status=revocation), observed_at=now)
    attempts.admit(event, expected_head=snapshot.head)
    committed = _commit(attempts, namespace, event, snapshot.head)
    return _projection(committed, route, incident_id)


def _admit_execution(attempts, snapshot, event, route, incident_id, checkpoint, number, now):
    """Capacity-only pure forecast. The second event is never committed or reported."""
    probe_checkpoint = F.checkpoint_document(checkpoint)
    probe_checkpoint['owner_head'] = [2**63-1, 'f'*64]
    probe = F.make_event('ATTEMPT_OBSERVED', dict(attempt_id=F.attempt_id(route, incident_id),
        execution_number=number, status='DESTINATION_UNCONFIRMED', reason_code='R'*96,
        checkpoint=probe_checkpoint, revocation_status='NOT_REVOKED_AT_HEAD',
        verified_at=I._stamp(now), recovery_artifact_digest='f'*64,
        destination_head=[2**63-1, 'f'*64]), observed_at=now)
    attempts.admit_pair(event, probe, expected_head=snapshot.head)


def _plans(source, destination, document, snapshot, artifact_id):
    artifact, artifact_bytes, payloads = build_recovery_artifact(document, incident_id=artifact_id,
                                                                limits=destination.limits)
    artifact_digest = BF.raw_archive_digest(artifact, limits=destination.limits.format_limits)
    raw_payloads = {item.logical_id:snapshot.payloads[item.logical_id] for item in snapshot.raw_manifest.files}
    plans = [('RAW_ARCHIVED', snapshot.raw_bytes, raw_payloads)]
    if snapshot.verified_bytes is not None:
        plans.append(('VERIFIED_UNAPPROVED', snapshot.verified_bytes, snapshot.payloads))
    plans.append(('RAW_ARCHIVED', artifact_bytes, payloads))
    B._preflight(destination, plans)
    return artifact_digest


def _partial(destination, request):
    """Actual exact raw graph presence is a partial fact, never completion proof."""
    try:
        raw = destination.read_raw(request['input_archive_digest'], require_backup=True)
        expected = json.dumps(request['raw_manifest'], sort_keys=True, separators=(',', ':'),
                              ensure_ascii=True, allow_nan=False).encode('ascii')
        return raw.manifest_bytes == expected
    except Exception:
        return False


def _final_verification(incidents, attempts, config, route, incident_id, document,
                        provider, clock, checkpoint, snapshot):
    first, _ = _observe(document, provider, clock, checkpoint, minimum=snapshot.state.last_trusted_at)
    verification = B.verify_restored_archive(config.destination, route.registration.bundle_digest,
        document, incident_id=F.artifact_incident_id(incident_id), authority_provider=provider, clock=clock)
    _need(verification.revocation_status == 'NOT_REVOKED_AT_HEAD', 'RECOVERY_ATTESTATION_REVOKED')
    _need(verification.attestation_sha256 == route.attestation_sha256
          and verification.revocation_target_sha256 == route.revocation_target_sha256,
          'RECOVERY_DOCUMENT_CHANGED')
    incident = _incident(incidents, route, incident_id)
    current = attempts.inspect()
    _need(current == snapshot and _route_in(current.state, route.route_id) == route,
          'RECOVERY_ATTEMPT_CHANGED')
    _bound_config(incidents, attempts, config, route, route.attempt_namespace_sha256, paths=True)
    destination_head = _head(config.destination)
    latest, final_checkpoint = _observe(document, provider, clock, checkpoint,
                                        minimum=verification.verified_at)
    def final_guard():
        attempts.check_operation()
        _bound_config(incidents, attempts, config, route, route.attempt_namespace_sha256, paths=True)
        _need(incidents.head.read() == incident.head and attempts.head.read() == snapshot.head
              and config.destination.head.read() == destination_head[1], 'RECOVERY_FINAL_HEAD_CHANGED')
    finished = _finish(document, (first, latest), clock, minimum=latest.observed_at, provider=provider, guard=final_guard)
    return verification, final_checkpoint, destination_head, finished


def run_recovery_once(incident_store, attempts, route, *, route_id, incident_id,
                      attestation_bytes, clock, authority_provider):
    """One bounded execution/resume; never sleeps, releases holds or selects research."""
    _provider(authority_provider, clock)
    _need(type(incident_store) is IncidentStore and _hash(route_id) and _hash(incident_id),
          'RECOVERY_INPUT_INVALID')
    namespace = _attempt_namespace(attempts); _not_latched(namespace)
    with attempts.operation():
        snapshot = attempts.inspect()
        registered = _route_in(snapshot.state, route_id)
        _need(registered is not None, 'RECOVERY_ROUTE_REQUIRED')
        _bound_config(incident_store, attempts, route, registered, namespace, paths=False)
        body, request = _document_binding(attestation_bytes, registered)
        incident = _incident(incident_store, registered, incident_id)
        attempt = _attempt_in(snapshot.state, route_id, incident_id)
        if attempt is not None and attempt.terminal:
            return _projection(snapshot, registered, incident_id)
        required = _required_checkpoint(registered, attempt)
        checkpoint, first, now = None, None, None
        number = 1 if attempt is None else attempt.execution_count+1
        try:
            now = _clock(clock, snapshot.state.last_trusted_at)
        except ResearchRecoveryError as exc:
            _need(number <= 1+attempts.limits.format_limits.max_resumes, 'RECOVERY_EXECUTION_BUDGET_EXHAUSTED')
            return _record_refusal(attempts, namespace, snapshot, registered, incident_id, incident,
                number, 'AUTHORITY_REFUSED', str(exc), now=None)
        number = _admit_retry(snapshot.state, attempt, attempts.limits.format_limits, now)
        stage = 'authority'
        try:
            _need(now >= required.observed_at, 'RECOVERY_CLOCK_ROLLBACK')
            first, checkpoint = _observe(attestation_bytes, authority_provider, clock, required, minimum=now)
            stage = 'configuration'
            source_ids = _bound_config(incident_store, attempts, route, registered, namespace, paths=True)
            stage = 'destination'
            complete = False
            try:
                existing = B.verify_restored_archive(route.destination, registered.registration.bundle_digest,
                    attestation_bytes, incident_id=F.artifact_incident_id(incident_id),
                    authority_provider=authority_provider, clock=clock)
                _need(existing.revocation_status == 'NOT_REVOKED_AT_HEAD', 'RECOVERY_ATTESTATION_REVOKED')
                complete = True
            except BS.BundleStoreError as exc:
                if str(exc) != 'BUNDLE_STORE_NOT_PUBLISHED':
                    raise
            if not complete:
                stage = 'source'
                _need(source_ids[1] is not None, 'RECOVERY_SOURCE_BACKUP_UNAVAILABLE')
                inspection, source_snapshot = B._inspect(route.source, registered.registration.bundle_digest,
                    attestation_bytes, authority_provider=authority_provider, clock=clock)
                stage = 'destination'
                _plans(route.source, route.destination, attestation_bytes, source_snapshot,
                       F.artifact_incident_id(incident_id))
            stage = 'authority'
            latest, checkpoint = _observe(attestation_bytes, authority_provider, clock, required,
                                          minimum=first.observed_at)
            incident = _incident(incident_store, registered, incident_id)
            _need(attempts.inspect() == snapshot, 'RECOVERY_ATTEMPT_CHANGED')
            attempts.check_operation()
            now = _finish(attestation_bytes, (first, latest), clock, minimum=latest.observed_at,
                          provider=authority_provider, guard=lambda:_bound_config(incident_store, attempts,
                              route, registered, namespace, paths=True))
        except Exception as exc:
            if isinstance(exc, RecoveryStoreError):
                _latch(namespace)
                raise ResearchRecoveryError('RECOVERY_RECORD_UNCONFIRMED') from None
            status, code = _failure(exc, destination=stage == 'destination')
            revocation = 'UNOBSERVED'
            if isinstance(exc, _Revoked):
                checkpoint, revocation = exc.checkpoint, 'REVOKED'
            observed = None
            try:
                observed = _clock(clock, snapshot.state.last_trusted_at)
            except ResearchRecoveryError:
                status, code, checkpoint, revocation = 'AUTHORITY_REFUSED', 'RECOVERY_CLOCK_INVALID', None, 'UNOBSERVED'
            # Only a returned actual observation may populate checkpoint facts.
            return _record_refusal(attempts, namespace, snapshot, registered, incident_id, incident,
                number, status, code, now=observed, checkpoint=checkpoint, revocation=revocation)
        if attempt is None:
            event = F.make_event('ATTEMPT_STARTED', dict(route_id=route_id, incident_id=incident_id,
                incident_head=[incident.sequence, incident.head], checkpoint=F.checkpoint_document(checkpoint)),
                observed_at=now)
        else:
            event = F.make_event('RESUME_STARTED', dict(attempt_id=attempt.attempt_id,
                execution_number=number, incident_head=[incident.sequence, incident.head],
                checkpoint=F.checkpoint_document(checkpoint)), observed_at=now)
        _admit_execution(attempts, snapshot, event, registered, incident_id, checkpoint, number, now)
        snapshot = _commit(attempts, namespace, event, snapshot.head)
        attempt = _attempt_in(snapshot.state, route_id, incident_id)
        _need(attempt is not None, 'RECOVERY_ATTEMPT_MISSING')
        verification, finished, destination_head = None, None, None
        stage = 'authority'
        try:
            _observe(attestation_bytes, authority_provider, clock, checkpoint,
                     minimum=snapshot.state.last_trusted_at)
            attempts.check_operation()
            current_source_ids = _bound_config(incident_store, attempts, route, registered, namespace, paths=True)
            if not complete:
                _need(current_source_ids[1] is not None, 'RECOVERY_SOURCE_BACKUP_UNAVAILABLE')
                stage = 'copy'
                B.restore_signed_backup(route.source, route.destination, registered.registration.bundle_digest,
                    attestation_bytes, incident_id=F.artifact_incident_id(incident_id),
                    authority_provider=authority_provider, clock=clock)
            stage = 'destination'
            verification, checkpoint, destination_head, finished = _final_verification(
                incident_store, attempts, route, registered, incident_id, attestation_bytes,
                authority_provider, clock, checkpoint, snapshot)
            status, reason, revoked = 'EXACT_ARCHIVE_RESTORED', 'RECOVERY_EXACT_ARCHIVE_RESTORED', 'NOT_REVOKED_AT_HEAD'
        except Exception as exc:
            if isinstance(exc, RecoveryStoreError):
                _latch(namespace)
                raise ResearchRecoveryError('RECOVERY_RECORD_UNCONFIRMED') from None
            status, reason = _failure(exc, destination=stage == 'destination')
            if status == 'READ_UNAVAILABLE' and stage == 'copy' and _partial(route.destination, request):
                status = 'PARTIAL_UNVERIFIED'
            revoked = 'UNOBSERVED'
            if isinstance(exc, _Revoked):
                checkpoint, revoked = exc.checkpoint, 'REVOKED'
            try:
                finished = _clock(clock, snapshot.state.last_trusted_at)
            except ResearchRecoveryError:
                status, reason, checkpoint, finished, revoked = 'AUTHORITY_REFUSED', 'RECOVERY_CLOCK_INVALID', None, None, 'UNOBSERVED'
        payload = dict(attempt_id=attempt.attempt_id, execution_number=number,
            status=status, reason_code=reason,
            checkpoint=None if checkpoint is None else F.checkpoint_document(checkpoint), revocation_status=revoked,
            verified_at=I._stamp(finished) if verification is not None else None,
            recovery_artifact_digest=None if verification is None else verification.recovery_artifact_digest,
            destination_head=None if destination_head is None else list(destination_head))
        outcome = F.make_event('ATTEMPT_OBSERVED', payload, observed_at=finished)
        attempts.admit(outcome, expected_head=snapshot.head)
        committed = _commit(attempts, namespace, outcome, snapshot.head)
        return _projection(committed, registered, incident_id)
