"""Actual complete-graph observations and durable, dependency-scoped holds.

No repair, re-anchor, notification transport, approval or order side effects.
Registration uses actual backed BundleStore bytes, never a constructed verdict.
The configured incident namespace must be retained: replacing every root/anchor
is not protected continuation. Capacity admission is not a disk reservation.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
import hashlib
import json
import os
import stat
from pathlib import Path
import re
from threading import Lock

from execution_launch import evidence_objects as E
from execution_launch import research_bundle_format as B
from execution_launch import research_bundle_store as S
from execution_launch import research_incidents as F
from execution_launch.baseline_head import BaselineHeadError
from execution_launch.research_incident_store import IncidentStore

_DOMAIN = b'tradegen-research-incident-monitor/1\x00'
_HASH = re.compile(r'[0-9a-f]{64}')
_CODE = re.compile(r'[A-Z][A-Z0-9_]{0,95}')
_READ_ERRORS = (S.BundleStoreError, B.BundleFormatError, E.EvidenceObjectError, BaselineHeadError, OSError)
_UNCONFIRMED = set()
_LATCH_LOCK = Lock()
_LATCH_EXHAUSTED = False
_MAX_LATCHES = 256


class IncidentMonitorError(ValueError):
    """Fixed diagnostics only; never upstream messages, payloads or paths."""


def _need(ok, code):
    if not ok:
        raise IncidentMonitorError(code)


def _digest(kind, body):
    raw = json.dumps(body, sort_keys=True, separators=(',', ':'), ensure_ascii=True,
                     allow_nan=False).encode('ascii')
    return hashlib.sha256(_DOMAIN + kind.encode('ascii') + b'\x00' + raw).hexdigest()


def namespace_identity(store):
    """Internal configured-namespace observation, not a transferable permit."""
    _need(type(store) is IncidentStore, 'INCIDENT_ACTUAL_STORE_REQUIRED')
    store._configuration()
    return _digest('namespace', dict(context=store.context_sha256,
        roots=[str(p) for p in store._roots], root_ids=store._root_ids,
        head_name=store._head_name))


def _latched(namespace):
    with _LATCH_LOCK:
        _need(not _LATCH_EXHAUSTED and namespace not in _UNCONFIRMED,
              'INCIDENT_RECORD_UNCONFIRMED')


def _latch(namespace):
    global _LATCH_EXHAUSTED
    with _LATCH_LOCK:
        if namespace in _UNCONFIRMED:
            return
        if len(_UNCONFIRMED) >= _MAX_LATCHES:
            _LATCH_EXHAUSTED = True
        else:
            _UNCONFIRMED.add(namespace)


def _inputs(incident_store, bundle_store, digest):
    _need(type(incident_store) is IncidentStore and type(bundle_store) is S.BundleStore,
          'INCIDENT_ACTUAL_STORE_REQUIRED')
    _need(type(digest) is str and _HASH.fullmatch(digest) is not None, 'INCIDENT_TARGET_INVALID')
    namespace = namespace_identity(incident_store)
    _latched(namespace)
    bundle_store._configuration()
    research_roots = (bundle_store._fixed_roots.sealed_root, bundle_store._fixed_roots.backup_root)
    # Constructor-pinned identities survive a changed/missing physical source
    # path; such changes must be attributed to its registered original binding.
    for path in incident_store._roots:
        for other in research_roots:
            # Constructors checked all original ancestors and retained actual
            # identities. Re-resolving a now-broken source path here would lose
            # a known-target observation before the durable catalog-fault path.
            _need(not path.is_relative_to(other) and not other.is_relative_to(path),
                  'INCIDENT_RESEARCH_ROOT_OVERLAP')
    _need(not set(incident_store._root_ids).intersection(bundle_store._root_ids),
          'INCIDENT_RESEARCH_ROOT_OVERLAP')
    binding = _digest('research-store', dict(context=bundle_store.context_sha256,
        roots=[str(p) for p in research_roots], root_ids=bundle_store._root_ids,
        head_name=bundle_store._head_name))
    return namespace, binding


def _observed(clock, last=None):
    try:
        value = clock()
        if type(value) is not datetime or value.utcoffset() is None:
            return None
        value = value.astimezone(timezone.utc)
        return value if last is None or value >= last else None
    except Exception:
        return None


def _catalog(store, digest):
    with store._locked():
        catalog = store._load()
        entry = catalog.entries.get(digest)
        _need(entry is not None, 'INCIDENT_REGISTERED_TARGET_MISSING')
        return catalog.head, catalog.sequence, entry.row['kind']


class _GraphFailure(Exception):
    def __init__(self, stage, cause):
        self.stage, self.cause = stage, cause


def _complete_graph(store, digest, binding, limits):
    try:
        before = _catalog(store, digest)
    except (*_READ_ERRORS, IncidentMonitorError) as exc:
        raise _GraphFailure('catalog', exc) from None
    try:
        if before[2] == 'RAW_ARCHIVED':
            raw = store.read_raw(digest, require_backup=True)
            verified = None
            raw_digest = digest
        else:
            _need(before[2] == 'VERIFIED_UNAPPROVED', 'INCIDENT_GRAPH_INVALID')
            verified = store.read_verified(digest, require_backup=True)
            raw_digest = verified.manifest.input_archive_digest
            raw = store.read_raw(raw_digest, require_backup=True)
            B.validate_verified_inputs(raw.manifest, verified.manifest, limits=store.limits.format_limits)
            _need(all(verified.files.get(k) == value for k, value in raw.files.items()), 'INCIDENT_GRAPH_INVALID')
        objects, inventories = {}, []
        def add(value, from_raw):
            if not value:
                return
            for item in E.preview_payload(value, limits=store.limits.object_limits).objects:
                previous = objects.get(item.sha256)
                if previous is None:
                    _need(len(objects) < limits.max_dependencies_per_target, 'INCIDENT_RESOURCE_LIMIT')
                else:
                    _need((previous.kind, previous.byte_count) == (item.kind, item.byte_count), 'INCIDENT_GRAPH_INVALID')
                objects[item.sha256] = F.ObjectDependency(kind=item.kind, sha256=item.sha256,
                    byte_count=item.byte_count, from_raw=from_raw or previous is not None and previous.from_raw)
        for label, graph, from_raw in (('raw', raw, True), ('verified', verified, False)):
            if graph is None:
                continue
            _need(len(graph.files) <= store.limits.format_limits.max_files, 'INCIDENT_RESOURCE_LIMIT')
            add(graph.manifest_bytes, from_raw)
            rows = []
            for logical, value in sorted(graph.files.items()):
                add(value, from_raw)
                rows.append([logical, len(value), hashlib.sha256(value).hexdigest()])
            inventories.append([label, hashlib.sha256(graph.manifest_bytes).hexdigest(), rows])
    except (*_READ_ERRORS, IncidentMonitorError) as exc:
        raise _GraphFailure('graph', exc) from None
    try:
        _need(_catalog(store, digest) == before, 'INCIDENT_CATALOG_CHANGED')
    except (*_READ_ERRORS, IncidentMonitorError) as exc:
        raise _GraphFailure('catalog', exc) from None
    value = F.TargetRegistration(store_binding_sha256=binding, bundle_digest=digest,
        input_archive_digest=raw_digest, bundle_kind=before[2],
        raw_manifest_sha256=hashlib.sha256(raw.manifest_bytes).hexdigest(),
        verified_manifest_sha256=None if verified is None else hashlib.sha256(verified.manifest_bytes).hexdigest(),
        graph_sha256=_digest('graph', inventories), catalog_head_sha256=before[0],
        catalog_sequence=before[1], objects=tuple(objects[key] for key in sorted(objects)))
    return F.parse_registration(F.registration_document(value), limits=limits)


def _existing(state, binding, digest):
    return next((item for item in state.registrations
                 if item.store_binding_sha256 == binding and item.bundle_digest == digest), None)


def _same_graph(a, b):
    def identity(value):
        document = F.registration_document(value)
        return {k:v for k,v in document.items() if k not in ('catalog_head_sha256', 'catalog_sequence')}
    return identity(a) == identity(b)


def register_target(incident_store, bundle_store, bundle_digest, *, clock):
    """Register exact backed graph facts. No evaluator or approval is invoked."""
    _, binding = _inputs(incident_store, bundle_store, bundle_digest)
    snapshot = incident_store.inspect()
    prior = _existing(snapshot.state, binding, bundle_digest)
    if prior is not None:
        # Re-registration observes existing dependencies through the same durable
        # failure path. Returning immutable identity never means healthy/released.
        check_target(incident_store, bundle_store, bundle_digest, clock=clock)
        return prior
    _need(prior is not None or len(snapshot.state.registrations) < incident_store.limits.format_limits.max_targets,
          'INCIDENT_RESOURCE_LIMIT')
    observed = _observed(clock, snapshot.state.last_trusted_at)
    _need(observed is not None, 'INCIDENT_CLOCK_INVALID')
    try:
        value = _complete_graph(bundle_store, bundle_digest, binding, incident_store.limits.format_limits)
    except _GraphFailure as exc:
        raise exc.cause from None
    event = F.make_event('REGISTER', F.registration_document(value), observed_at=observed)
    incident_store.commit(event, expected_head=snapshot.head)
    return value


@dataclass(frozen=True, kw_only=True)
class IncidentCheck:
    registered: bool
    held: bool
    incident_ids: tuple[str, ...]
    store_binding_sha256: str
    bundle_digest: str
    incident_head: str
    incident_sequence: int
    graph_checked: bool
    checked_at: datetime | None


def _projection(snapshot, registration, *, graph_checked, observed):
    blocked = F.blocked_incidents(snapshot.state, registration)
    return IncidentCheck(registered=True, held=bool(blocked),
        incident_ids=tuple(item.incident_id for item in blocked),
        store_binding_sha256=registration.store_binding_sha256, bundle_digest=registration.bundle_digest,
        incident_head=snapshot.head, incident_sequence=snapshot.sequence,
        graph_checked=graph_checked and not blocked, checked_at=observed)


def _category(cause):
    code = str(cause)
    if code in ('BUNDLE_STORE_RESOURCE_LIMIT', 'BUNDLE_STORE_NO_SPACE',
                'EVIDENCE_OBJECT_LIMIT_EXCEEDED', 'INCIDENT_RESOURCE_LIMIT'):
        return 'RESOURCE_LIMIT'
    if isinstance(cause, OSError) or code in ('BUNDLE_STORE_LOCKED', 'BUNDLE_STORE_IO_REFUSED',
            'EVIDENCE_OBJECT_IO_REFUSED', 'EVIDENCE_OBJECT_PATH_REFUSED',
            'BUNDLE_STORE_OBJECT_REFUSED', 'BUNDLE_STORE_PATH_REFUSED', 'BUNDLE_STORE_HEAD_REFUSED',
            'INCIDENT_CATALOG_CHANGED'):
        return 'READ_UNAVAILABLE'
    if code in ('BUNDLE_STORE_ROOT_CHANGED', 'BUNDLE_STORE_HEAD_MISMATCH',
            'BUNDLE_STORE_CATALOG_INVALID', 'BUNDLE_STORE_CATALOG_TORN',
            'BUNDLE_STORE_MANIFEST_MISMATCH', 'BUNDLE_STORE_REFERENCE_MISMATCH',
            'BUNDLE_STORE_BACKUP_MISMATCH', 'BUNDLE_STORE_STORAGE_CHANGED',
            'EVIDENCE_OBJECT_HASH_MISMATCH', 'EVIDENCE_OBJECT_MISSING',
            'INCIDENT_REGISTERED_TARGET_MISSING', 'INCIDENT_GRAPH_INVALID', 'INCIDENT_REGISTRATION_CHANGED'):
        return 'INTEGRITY_FAILURE'
    return 'VALIDATION_REFUSED'


def _reason(cause):
    value = str(cause)
    return value if not isinstance(cause, OSError) and _CODE.fullmatch(value) is not None else 'INCIDENT_READ_REFUSED'


def _bad_objects(store, registration):
    bad = set()
    proved = frozenset(('EVIDENCE_OBJECT_HASH_MISMATCH', 'EVIDENCE_OBJECT_MISSING'))
    for backup in (False, True):
        try:
            objects = store._objects(backup)
            with objects._locked(create=False):
                def parent_identity():
                    info = os.lstat(objects._objects)
                    if not stat.S_ISDIR(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
                        raise E.EvidenceObjectError('EVIDENCE_OBJECT_PATH_REFUSED')
                    return S._identity(info)
                parent = parent_identity()
                for item in registration.objects:
                    try:
                        objects._read_object(item.kind, item.sha256, item.byte_count)
                    except FileNotFoundError:
                        if parent_identity() == parent:
                            bad.add(item.sha256)
                        else:
                            raise E.EvidenceObjectError('EVIDENCE_OBJECT_PATH_REFUSED') from None
                    except E.EvidenceObjectError as exc:
                        if str(exc) in proved:
                            bad.add(item.sha256)
        except _READ_ERRORS:
            # No whole-object-tree or lock error proves a particular leaf bad.
            pass
    return tuple(sorted(bad))


def _failure_event(registration, *, observed, scope, failed_objects, category, reason):
    return F.make_event('FAILURE', dict(store_binding_sha256=registration.store_binding_sha256,
        bundle_digest=registration.bundle_digest, scope=scope, failed_objects=list(failed_objects),
        category=category, reason_code=reason), observed_at=observed)


def _record_failure(incident_store, bundle_store, namespace, registration, snapshot, failure, observed):
    scope, bad, cause = 'TARGET', (), failure.cause
    if failure.stage == 'catalog':
        scope = 'STORE'
    else:
        try:
            _catalog(bundle_store, registration.bundle_digest)
        except (*_READ_ERRORS, IncidentMonitorError) as exc:
            scope, cause = 'STORE', exc
        else:
            bad = _bad_objects(bundle_store, registration)
            if bad:
                scope = 'OBJECTS'
    event = _failure_event(registration, observed=observed, scope=scope, failed_objects=bad,
        category='INTEGRITY_FAILURE' if bad else _category(cause), reason=_reason(cause))
    try:
        committed = incident_store.commit(event, expected_head=snapshot.head)
    except Exception:
        # No subsequent healthy read in this process can erase an unrecorded
        # observation. On restart torn durable state refuses; a no-write I/O
        # failure cannot honestly be advertised as a persistent incident.
        _latch(namespace)
        raise IncidentMonitorError('INCIDENT_RECORD_UNCONFIRMED') from None
    return _projection(committed, registration, graph_checked=False, observed=observed)


def _check_registered_graph(incident_store, bundle_store, bundle_digest, *,
                            namespace, binding, snapshot, registration, observed):
    """Actual shared graph/failure path. A healthy read never removes a hold."""
    # This is capacity preflight, NOT a future write/disk reservation. Its
    # proposed broad failure includes all registered dependencies, never strips
    # normal quotes or records. Commit repeats admission under the actual lock.
    probe = _failure_event(registration, observed=None, scope='STORE', failed_objects=(),
        category='VALIDATION_REFUSED', reason='INCIDENT_CAPACITY_PREFLIGHT')
    incident_store.admit(probe, expected_head=snapshot.head)
    try:
        current = _complete_graph(bundle_store, bundle_digest, binding, incident_store.limits.format_limits)
        _need(_same_graph(registration, current), 'INCIDENT_REGISTRATION_CHANGED')
    except _GraphFailure as failure:
        return _record_failure(incident_store, bundle_store, namespace, registration, snapshot, failure, observed)
    except IncidentMonitorError as cause:
        return _record_failure(incident_store, bundle_store, namespace, registration, snapshot,
                               _GraphFailure('graph', cause), observed)
    _need(observed is not None, 'INCIDENT_CLOCK_INVALID')
    # Include concurrently appended restrictions in the returned observation.
    final = incident_store.inspect()
    _need(_existing(final.state, binding, bundle_digest) == registration, 'INCIDENT_REGISTRATION_CHANGED')
    return replace(_projection(final, registration, graph_checked=True, observed=observed), graph_checked=True)


def check_target(incident_store, bundle_store, bundle_digest, *, clock):
    """Finite actual graph read plus durable restriction observation, never a lease."""
    namespace, binding = _inputs(incident_store, bundle_store, bundle_digest)
    snapshot = incident_store.inspect()
    registration = _existing(snapshot.state, binding, bundle_digest)
    _need(registration is not None, 'INCIDENT_TARGET_UNREGISTERED')
    observed = _observed(clock, snapshot.state.last_trusted_at)
    if F.blocked_incidents(snapshot.state, registration):
        return _projection(snapshot, registration, graph_checked=False, observed=observed)
    result = _check_registered_graph(incident_store, bundle_store, bundle_digest,
        namespace=namespace, binding=binding, snapshot=snapshot, registration=registration, observed=observed)
    return replace(result, graph_checked=result.graph_checked and not result.held)


def _check_recovered_target(incident_store, bundle_store, bundle_digest, *, clock):
    """Read a held graph for recovery research without releasing any restriction.

    Unlike the general monitor's early held return, this private path performs
    the full backed read. Its descriptive result may be held and graph_checked;
    neither the constructor nor a historical result is a current authorization.
    """
    namespace, binding = _inputs(incident_store, bundle_store, bundle_digest)
    snapshot = incident_store.inspect()
    registration = _existing(snapshot.state, binding, bundle_digest)
    _need(registration is not None, 'INCIDENT_TARGET_UNREGISTERED')
    observed = _observed(clock, snapshot.state.last_trusted_at)
    return _check_registered_graph(incident_store, bundle_store, bundle_digest,
        namespace=namespace, binding=binding, snapshot=snapshot, registration=registration, observed=observed)
