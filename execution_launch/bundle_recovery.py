"""Exact signed backup restoration into a separately provisioned archive store.

The damaged primary catalog and its old head are never read, adopted or repaired.
Signed manifests select every source reference; actual owner/key/code/time and
all backup bytes are checked. Destination writes use the existing BundleStore
commits only. A separate backed-up auxiliary archive retains the signature and
deterministic content record. No original is overwritten, no head initialized,
no trading route changed and no operational or quarantine-release authority is
issued. An exception preserves any already committed destination evidence.
"""
from __future__ import annotations

from contextlib import ExitStack
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import stat
from types import MappingProxyType

from core.compliance import model as compliance
from core.isolation import checked_target, state_root
from execution_control.owner_authority import CurrentOwnerAuthority, MAX_AUTHORITY_AGE_SECONDS
from execution_launch import bundle_attestation as A
from execution_launch import bundle_auth as U
from execution_launch import research_bundle_format as F
from execution_launch import research_bundle_store as S
from execution_launch.bundle_review import _open_posix_directory, pin_windows_directory
from execution_launch.evidence_objects import EvidenceObjectStore, preview_payload
from execution_launch.recovery_artifact import build_recovery_artifact
from execution_launch.research_revocation import revocation_target, target_is_revoked

_REPO = Path(__file__).resolve().parents[1]


class BundleRecoveryError(ValueError):
    """Fixed diagnostics only; no supplied data, roots or OS messages."""


def _need(value, code):
    if not value:
        raise BundleRecoveryError(code)


def _copy_limits(limits):
    _need(type(limits) is S.BundleStoreLimits, 'BUNDLE_RECOVERY_LIMITS_INVALID')
    try:
        return replace(limits, format_limits=replace(limits.format_limits),
            object_limits=replace(limits.object_limits), primary_budget=replace(limits.primary_budget),
            backup_budget=replace(limits.backup_budget))
    except (ValueError, TypeError, AttributeError):
        raise BundleRecoveryError('BUNDLE_RECOVERY_LIMITS_INVALID') from None


@dataclass(frozen=True, kw_only=True)
class SignedBackupSource:
    """Explicit location/configuration only, never a trusted source assertion."""
    roots: S.BundleRoots
    limits: S.BundleStoreLimits

    def __post_init__(self):
        try:
            _need(type(self.roots) is S.BundleRoots, 'BUNDLE_RECOVERY_ROOTS_REQUIRED')
            self.roots.__post_init__()
            _copy_limits(self.limits)
        except BundleRecoveryError:
            raise
        except (ValueError, TypeError, AttributeError):
            raise BundleRecoveryError('BUNDLE_RECOVERY_SOURCE_CHANGED') from None


@dataclass(frozen=True, kw_only=True)
class RecoveryInspection:
    scope: str
    bundle_kind: str
    bundle_digest: str
    input_archive_digest: str
    request_sha256: str
    attestation_sha256: str
    verified_at: datetime
    source_backup_exact: bool = True
    revocation_status: str = 'UNSUPPORTED'
    source_authenticated: bool = False
    research_selection_ready: bool = False
    current_use_eligible: bool = False
    execution_ready: bool = False


@dataclass(frozen=True, kw_only=True)
class RecoveryResult:
    """Completed observation only; never an approval or reusable recovery token."""
    status: str
    scope: str
    incident_id: str
    bundle_kind: str
    bundle_digest: str
    input_archive_digest: str
    attestation_sha256: str
    recovery_artifact_digest: str
    verified_at: datetime
    destination_backup_verified: bool = True
    signature_backup_verified: bool = True
    original_store_modified: bool = False
    revocation_status: str = 'UNSUPPORTED'
    source_authenticated: bool = False
    research_selection_ready: bool = False
    current_use_eligible: bool = False
    execution_ready: bool = False
    automatic_operational_recovery_supported: bool = False


@dataclass(frozen=True, kw_only=True)
class RestoredArchiveVerification:
    """Finite archive observation, never incident linkage or current-use authority.

    The incident_id is the original artifact label. No incident store or durable
    attempt is consulted. REVOKED preserves the fact of exact archived evidence;
    no consumer may treat either revocation status as permission to use it.
    """
    status: str
    scope: str
    incident_id: str
    bundle_kind: str
    bundle_digest: str
    input_archive_digest: str
    request_sha256: str
    attestation_sha256: str
    recovery_artifact_digest: str
    verified_at: datetime
    revocation_status: str
    revocation_target_sha256: str
    revocation_owner_head: tuple[int, str]
    destination_backup_verified: bool = True
    signature_backup_verified: bool = True
    archive_storage_modified: bool = False
    source_authenticated: bool = False
    research_selection_ready: bool = False
    current_use_eligible: bool = False
    execution_ready: bool = False
    automatic_operational_recovery_supported: bool = False
    quarantine_release_supported: bool = False


@dataclass(frozen=True)
class _Snapshot:
    raw_manifest: F.RawArchiveManifest
    raw_bytes: bytes
    verified_manifest: F.VerifiedBundleManifest | None
    verified_bytes: bytes | None
    payloads: object
    request: dict
    observations: tuple


def _identity(info):
    _need(type(info.st_dev) is int and info.st_dev >= 0 and type(info.st_ino) is int and info.st_ino > 0,
          'BUNDLE_RECOVERY_IDENTITY_UNAVAILABLE')
    return info.st_dev, info.st_ino


def _directory(path, *, missing=False):
    _need(isinstance(path, Path) and path.is_absolute() and '..' not in path.parts
          and '\x00' not in str(path) and ':' not in str(path)[len(path.anchor):],
          'BUNDLE_RECOVERY_PATH_REFUSED')
    try:
        checked_target(path, 'signed recovery root')
        _need(not any(part.casefold() == 'onedrive' or part.casefold().startswith('onedrive - ')
                      for part in path.parts), 'BUNDLE_RECOVERY_PATH_REFUSED')
        for other in (state_root().absolute().resolve(), _REPO):
            _need(not path.is_relative_to(other) and not other.is_relative_to(path),
                  'BUNDLE_RECOVERY_PATH_REFUSED')
        for prefix in (*reversed(path.parents), path):
            try:
                info = os.lstat(prefix)
            except FileNotFoundError:
                _need(missing and prefix == path, 'BUNDLE_RECOVERY_PATH_REFUSED')
                return None
            _need(stat.S_ISDIR(info.st_mode) and not getattr(info, 'st_file_attributes', 0) & 0x400,
                  'BUNDLE_RECOVERY_PATH_REFUSED')
            _identity(info)
        return _identity(info)
    except BundleRecoveryError:
        raise
    except (OSError, ValueError, TypeError, RuntimeError):
        raise BundleRecoveryError('BUNDLE_RECOVERY_PATH_REFUSED') from None


def _lock_identity(path):
    try:
        info = os.lstat(path)
        _need(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and 0 <= info.st_size <= 1
              and not getattr(info, 'st_file_attributes', 0) & 0x400, 'BUNDLE_RECOVERY_PATH_REFUSED')
        return _identity(info)
    except OSError:
        raise BundleRecoveryError('BUNDLE_RECOVERY_PATH_REFUSED') from None


def _source_configuration(source):
    _need(type(source) is SignedBackupSource, 'BUNDLE_RECOVERY_SOURCE_REQUIRED')
    try:
        source.__post_init__()
        return (source.roots.sealed_root, source.roots.backup_root), asdict(source.limits)
    except BundleRecoveryError:
        raise
    except (ValueError, TypeError, AttributeError):
        raise BundleRecoveryError('BUNDLE_RECOVERY_SOURCE_CHANGED') from None


class _SourcePin:
    """Held directory identities; object locks remain per actual read, never nested."""
    def __init__(self, source):
        self.source, self.configuration = source, _source_configuration(source)
        self.primary, self.backup = self.configuration[0]
        self.directories = (self.backup, self.backup/'payload-objects', self.backup/'payload-objects'/'objects')
        self.lock = self.backup/'payload-objects'/'objects.lock'
        self.stack, self.pins, self.descriptors = ExitStack(), [], []

    def _anchors(self):
        primary = _directory(self.primary, missing=True)
        directories = tuple(_directory(p) for p in self.directories)
        _need((primary is None or primary != directories[0])
              and not self.primary.resolve(strict=False).is_relative_to(self.backup.resolve(strict=False))
              and not self.backup.resolve(strict=False).is_relative_to(self.primary.resolve(strict=False)),
              'BUNDLE_RECOVERY_ROOT_OVERLAP')
        return primary, directories, _lock_identity(self.lock)

    def __enter__(self):
        try:
            self.anchor = self._anchors()
            for path in self.directories:
                if os.name == 'nt':
                    self.pins.append(self.stack.enter_context(pin_windows_directory(str(path))))
                else:
                    descriptor = _open_posix_directory(path)
                    self.stack.callback(os.close, descriptor)
                    self.descriptors.append((descriptor, _identity(os.fstat(descriptor))))
            self.check()
            return self
        except BaseException:
            self.stack.close()
            raise

    def check(self):
        _need(_source_configuration(self.source) == self.configuration and self._anchors() == self.anchor,
              'BUNDLE_RECOVERY_SOURCE_CHANGED')
        for pin in self.pins:
            pin.check()
        for descriptor, identity in self.descriptors:
            _need(_identity(os.fstat(descriptor)) == identity, 'BUNDLE_RECOVERY_SOURCE_CHANGED')

    def __exit__(self, kind, value, traceback):
        try:
            self.check()
        finally:
            self.stack.close()
        return False


def _provider(provider, clock):
    _need(type(provider) is CurrentOwnerAuthority and callable(clock)
          and getattr(provider, '_clock', None) is clock, 'BUNDLE_RECOVERY_ACTUAL_PROVIDER_REQUIRED')


def _request_snapshot(document, source):
    request = A.parse_attestation_document(document)['body']['request']
    limits = _copy_limits(source.limits)
    raw_bytes = json.dumps(request['raw_manifest'], sort_keys=True, separators=(',', ':'),
                           ensure_ascii=True, allow_nan=False).encode('ascii')
    raw = F.parse_raw_archive(raw_bytes, limits=limits.format_limits)
    verified, verified_bytes = None, None
    if request['verified_manifest'] is not None:
        verified_bytes = json.dumps(request['verified_manifest'], sort_keys=True, separators=(',', ':'),
                                    ensure_ascii=True, allow_nan=False).encode('ascii')
        verified = F.parse_verified_bundle(verified_bytes, limits=limits.format_limits)
        F.validate_verified_inputs(raw, verified, limits=limits.format_limits)
    for manifest in (raw,) if verified is None else (raw, verified):
        _need(manifest.storage_policy_sha256 == limits.policy_sha256
              and manifest.object_policy_sha256 == limits.object_limits.policy_sha256,
              'BUNDLE_RECOVERY_POLICY_MISMATCH')
    return request, limits, raw, raw_bytes, verified, verified_bytes


def _read_graph(pin, limits, raw, raw_bytes, verified, verified_bytes, request, *, retained=None):
    objects = EvidenceObjectStore(root=pin.backup/'payload-objects', limits=limits.object_limits)
    for body in (raw_bytes,) if verified_bytes is None else (raw_bytes, verified_bytes):
        pin.check()
        reference = preview_payload(body, limits=limits.object_limits).reference
        _need(objects.read(reference) == body, 'BUNDLE_RECOVERY_MANIFEST_MISMATCH')
        pin.check()
    target, payloads = raw if verified is None else verified, {}
    for item in target.files:
        pin.check()
        value = b'' if item.payload_ref is None else objects.read(item.payload_ref)
        _need((None if value == b'' else preview_payload(value, limits=limits.object_limits).reference)
              == item.payload_ref, 'BUNDLE_RECOVERY_REFERENCE_MISMATCH')
        pin.check()
        if retained is not None:
            _need(value == retained[item.logical_id], 'BUNDLE_RECOVERY_GRAPH_CHANGED')
        else:
            payloads[item.logical_id] = value
    if retained is not None:
        return retained
    F.validate_payloads(raw, {file.logical_id: payloads[file.logical_id] for file in raw.files},
                        limits=limits.format_limits)
    F.validate_payloads(target, payloads, limits=limits.format_limits)
    A.validate_request_payloads(request, payloads)
    return MappingProxyType(payloads)


def _finish_observation(document, provider, clock, prior, *, not_before, observe_revocation=False):
    """Complete expensive work first, then only bounded checks after final clock.

    Revocation evidence comes from this final actual owner observation, after all
    graph reads. It cannot reuse the earlier archive-authentication head.
    """
    observed = U._time(clock())
    _need(observed >= not_before, 'BUNDLE_RECOVERY_CLOCK_ROLLBACK')
    latest = provider(observed)
    body = U._authority(document, latest, observed)
    observations = tuple(prior) + (latest,)
    for authority in observations:
        U._authority(document, authority, observed)
    digest = A.attestation_document_digest(document)
    stamps = tuple((U._time(authority.observed_at), authority.context.date) for authority in observations)
    issued, expires = datetime.fromisoformat(body['issued_at']), datetime.fromisoformat(body['expires_at'])
    revocation = None
    if observe_revocation:
        target = revocation_target(document, purpose=A.PURPOSE)
        revoked = target_is_revoked(U._revocations(latest.context), purpose=A.PURPOSE, target_sha256=target)
        revocation = ('REVOKED' if revoked else 'NOT_REVOKED_AT_HEAD', target, latest.context.owner.head)
    finished = U._time(clock())
    _need(finished >= observed, 'BUNDLE_RECOVERY_CLOCK_ROLLBACK')
    _need(issued <= finished < expires, 'BUNDLE_RECOVERY_EXPIRED_OR_FUTURE')
    day = finished.astimezone(compliance.KST).date()
    for stamp, original_day in stamps:
        _need(timedelta(0) <= finished-stamp <= timedelta(seconds=MAX_AUTHORITY_AGE_SECONDS),
              'BUNDLE_RECOVERY_AUTHORITY_STALE')
        _need(original_day == day, 'BUNDLE_RECOVERY_OWNER_DAY_CHANGED')
    return finished, digest, latest, revocation


def _finish(document, provider, clock, prior, *, not_before):
    # Preserve the existing source/prewrite/copy-final observation contract.
    finished, digest, latest, _ = _finish_observation(document, provider, clock, prior, not_before=not_before)
    return finished, digest, latest


def _inspect(source, bundle_digest, document, *, authority_provider, clock):
    _source_configuration(source)
    _provider(authority_provider, clock)
    request, limits, raw, raw_bytes, verified, verified_bytes = _request_snapshot(document, source)
    _need(type(bundle_digest) is str and bundle_digest == request['bundle_digest'],
          'BUNDLE_RECOVERY_TARGET_MISMATCH')
    started = U._time(clock())
    first = authority_provider(started)
    U._authority(document, first, started)
    with _SourcePin(source) as pin:
        payloads = _read_graph(pin, limits, raw, raw_bytes, verified, verified_bytes, request)
        middle = U._time(clock())
        _need(middle >= started, 'BUNDLE_RECOVERY_CLOCK_ROLLBACK')
        second = authority_provider(middle)
        U._authority(document, second, middle)
        _read_graph(pin, limits, raw, raw_bytes, verified, verified_bytes, request, retained=payloads)
    # Release every source object/path handle before any destination commit.
    finished, digest, latest = _finish(document, authority_provider, clock, (first, second), not_before=middle)
    result = RecoveryInspection(scope='archive_identity_only', bundle_kind=request['bundle_kind'],
        bundle_digest=bundle_digest, input_archive_digest=request['input_archive_digest'],
        request_sha256=request['request_sha256'], attestation_sha256=digest, verified_at=finished)
    return result, _Snapshot(raw, raw_bytes, verified, verified_bytes, payloads, request, (first, second, latest))


def inspect_signed_backup(source, bundle_digest, attestation_bytes, *, authority_provider, clock):
    """Actual signature and full backup graph inspection; returns no authority token."""
    try:
        result, _ = _inspect(source, bundle_digest, attestation_bytes, authority_provider=authority_provider, clock=clock)
        return result
    except (OSError, RuntimeError):
        raise BundleRecoveryError('BUNDLE_RECOVERY_IO_REFUSED') from None
    except (AttributeError, TypeError, OverflowError):
        raise BundleRecoveryError('BUNDLE_RECOVERY_INPUT_INVALID') from None


def _separate(source, destination):
    _need(type(destination) is S.BundleStore, 'BUNDLE_RECOVERY_DESTINATION_REQUIRED')
    roots, values = _source_configuration(source)
    destination._configuration()
    _need(asdict(destination.limits) == values, 'BUNDLE_RECOVERY_POLICY_MISMATCH')
    all_roots = roots + (destination.roots.sealed_root, destination.roots.backup_root)
    identities = []
    for index, path in enumerate(all_roots):
        identities.append(_directory(path, missing=index == 0))
    for index, path in enumerate(all_roots):
        for other_index, other in enumerate(all_roots[:index]):
            _need(not path.is_relative_to(other) and not other.is_relative_to(path)
                  and not path.resolve(strict=False).is_relative_to(other.resolve(strict=False))
                  and not other.resolve(strict=False).is_relative_to(path.resolve(strict=False))
                  and (identities[index] is None or identities[index] != identities[other_index]),
                  'BUNDLE_RECOVERY_ROOT_OVERLAP')


def _preflight(destination, plans):
    """Read-only whole-batch forecast; not a capacity reservation or head adoption."""
    prepared, values = [], []
    for kind, raw, payloads in plans:
        manifest, digest = destination._manifest(kind, raw)
        F.validate_payloads(manifest, payloads, limits=destination.limits.format_limits)
        for file in manifest.files:
            if destination.preview_payload(payloads[file.logical_id]) != file.payload_ref:
                raise S.BundleStoreError('BUNDLE_STORE_REFERENCE_MISMATCH')
        prepared.append((kind, raw, payloads, manifest, digest))
        values.extend(payloads.values()); values.append(raw)
    # These are existing read/admission primitives. No public store method is
    # called while its non-reentrant session lock is held.
    with destination._locked() as anchor:
        actual = destination._load()
        predicted, planned_rows, entries = actual, [], dict(actual.entries)
        for kind, raw, payloads, manifest, digest in prepared:
            if any(entry.row['run_id'] == manifest.run_id and entry.row['revision_id'] == manifest.revision_id
                   and entry.row['bundle_sha256'] != digest for entry in entries.values()):
                raise S.BundleStoreError('BUNDLE_STORE_ID_REUSED')
            existing = actual.entries.get(digest)
            if existing is not None:
                retained = destination._validate_graph(actual, digest, require_backup=existing.backed)
                if retained.manifest_bytes != raw or dict(retained.files) != dict(payloads):
                    raise S.BundleStoreError('BUNDLE_STORE_ID_REUSED')
                if existing.backed:
                    continue
            source = dict(kind=kind, bundle_sha256=digest, run_id=manifest.run_id, revision_id=manifest.revision_id,
                attempt_id=manifest.attempt_id, manifest_ref=asdict(destination.preview_payload(raw)),
                files_sha256=destination._files_digest(manifest))
            events = ('PRIMARY_COMMITTED','BACKUP_VERIFIED') if existing is None else ('BACKUP_VERIFIED',)
            for event in events:
                row = destination._row(predicted, event, source)
                planned_rows.append(row)
                predicted = replace(predicted, head=row['row_sha256'], sequence=predicted.sequence+1,
                                    size=predicted.size+len(S._canonical(row))+1)
            entries[digest] = S._Entry(row, backed=True)
        destination._admit_catalog(actual, tuple(planned_rows))
        destination._admit_objects(tuple(values), False)
        destination._admit_objects(tuple(values), True)
        destination._check_anchor(anchor)


def _read_restored_graph(destination, bundle_digest, attestation_bytes, *, artifact_digest,
                         artifact_bytes, artifact_payloads, authority_provider, clock):
    """Shared actual artifact/target/artifact reads, not a trusted result adapter.

    Caller retains its own first owner observation across this heavy work and
    any required final source check, then completes the original time window.
    """
    retained = destination.read_raw(artifact_digest, require_backup=True)
    _need(retained.manifest_bytes == artifact_bytes and dict(retained.files) == dict(artifact_payloads)
          and retained.files['attestation'] == attestation_bytes, 'BUNDLE_RECOVERY_SIGNATURE_BACKUP_MISMATCH')
    authenticated = U.authenticate_bundle_attestation(destination, bundle_digest, attestation_bytes,
        authority_provider=authority_provider, clock=clock)
    retained = destination.read_raw(artifact_digest, require_backup=True)
    _need(retained.manifest_bytes == artifact_bytes and dict(retained.files) == dict(artifact_payloads),
          'BUNDLE_RECOVERY_SIGNATURE_BACKUP_MISMATCH')
    return authenticated


def _restore_signed_backup(source, destination, bundle_digest, attestation_bytes, *, incident_id,
                           authority_provider, clock):
    """Restore exact archival evidence; no runtime provision, re-anchor or orders."""
    _separate(source, destination)
    inspection, snapshot = _inspect(source, bundle_digest, attestation_bytes,
                                    authority_provider=authority_provider, clock=clock)
    artifact, artifact_bytes, artifact_payloads = build_recovery_artifact(attestation_bytes,
        incident_id=incident_id, limits=destination.limits)
    artifact_digest = F.raw_archive_digest(artifact, limits=destination.limits.format_limits)
    raw_payloads = {file.logical_id: snapshot.payloads[file.logical_id] for file in snapshot.raw_manifest.files}
    plans = [('RAW_ARCHIVED', snapshot.raw_bytes, raw_payloads)]
    if snapshot.verified_bytes is not None:
        plans.append(('VERIFIED_UNAPPROVED', snapshot.verified_bytes, snapshot.payloads))
    plans.append(('RAW_ARCHIVED', artifact_bytes, artifact_payloads))
    _preflight(destination, plans)
    _separate(source, destination)
    prewrite_at, _, _ = _finish(attestation_bytes, authority_provider, clock, snapshot.observations,
                                not_before=inspection.verified_at)
    for kind, raw, payloads in plans:
        receipt = (destination.archive_raw(raw, payloads) if kind == 'RAW_ARCHIVED'
                   else destination.commit_verified(raw, payloads))
        _need(receipt.backup_verified, 'BUNDLE_RECOVERY_DESTINATION_BACKUP_REQUIRED')
    # Copying exact immutable evidence is not an operational grant. A fresh
    # bounded FINAL transaction must reread the destination target and signature
    # graphs; it cannot relabel the earlier source inspection as current proof.
    final_started = U._time(clock())
    _need(final_started >= prewrite_at, 'BUNDLE_RECOVERY_CLOCK_ROLLBACK')
    final_first = authority_provider(final_started)
    U._authority(attestation_bytes, final_first, final_started)
    authenticated = _read_restored_graph(destination, bundle_digest, attestation_bytes,
        artifact_digest=artifact_digest, artifact_bytes=artifact_bytes, artifact_payloads=artifact_payloads,
        authority_provider=authority_provider, clock=clock)
    _separate(source, destination)
    finished, final_digest, _ = _finish(attestation_bytes, authority_provider, clock, (final_first,),
                                      not_before=authenticated.verified_at)
    _need(final_digest == inspection.attestation_sha256, 'BUNDLE_RECOVERY_DOCUMENT_CHANGED')
    return RecoveryResult(status='EXACT_ARCHIVE_RESTORED', scope='archive_identity_only', incident_id=incident_id,
        bundle_kind=inspection.bundle_kind, bundle_digest=bundle_digest,
        input_archive_digest=inspection.input_archive_digest, attestation_sha256=final_digest,
        recovery_artifact_digest=artifact_digest, verified_at=finished)


def restore_signed_backup(source, destination, bundle_digest, attestation_bytes, *, incident_id,
                          authority_provider, clock):
    """Actual exact restoration; bounded diagnostics preserve all partial evidence."""
    try:
        return _restore_signed_backup(source, destination, bundle_digest, attestation_bytes,
            incident_id=incident_id, authority_provider=authority_provider, clock=clock)
    except (OSError, RuntimeError):
        raise BundleRecoveryError('BUNDLE_RECOVERY_IO_REFUSED') from None
    except (AttributeError, TypeError, OverflowError):
        raise BundleRecoveryError('BUNDLE_RECOVERY_INPUT_INVALID') from None



def _verify_restored_archive(destination, bundle_digest, attestation_bytes, *, incident_id,
                             authority_provider, clock):
    _need(type(destination) is S.BundleStore, 'BUNDLE_RECOVERY_DESTINATION_REQUIRED')
    _provider(authority_provider, clock)
    _need(type(attestation_bytes) is bytes, 'BUNDLE_RECOVERY_DOCUMENT_BYTES_REQUIRED')
    destination._configuration()
    request = A.parse_attestation_document(attestation_bytes)['body']['request']
    _need(type(bundle_digest) is str and bundle_digest == request['bundle_digest'],
          'BUNDLE_RECOVERY_TARGET_MISMATCH')
    artifact, artifact_bytes, artifact_payloads = build_recovery_artifact(attestation_bytes,
        incident_id=incident_id, limits=destination.limits)
    artifact_digest = F.raw_archive_digest(artifact, limits=destination.limits.format_limits)

    started = U._time(clock())
    first = authority_provider(started)
    U._authority(attestation_bytes, first, started)
    authenticated = _read_restored_graph(destination, bundle_digest, attestation_bytes,
        artifact_digest=artifact_digest, artifact_bytes=artifact_bytes, artifact_payloads=artifact_payloads,
        authority_provider=authority_provider, clock=clock)
    destination._configuration()
    finished, document_digest, _, revocation = _finish_observation(attestation_bytes,
        authority_provider, clock, (first,), not_before=authenticated.verified_at, observe_revocation=True)
    status, target, head = revocation
    return RestoredArchiveVerification(status='RESTORED_ARCHIVE_REVERIFIED', scope='archive_identity_only',
        incident_id=incident_id, bundle_kind=request['bundle_kind'], bundle_digest=bundle_digest,
        input_archive_digest=request['input_archive_digest'], request_sha256=request['request_sha256'],
        attestation_sha256=document_digest, recovery_artifact_digest=artifact_digest, verified_at=finished,
        revocation_status=status, revocation_target_sha256=target, revocation_owner_head=head)


def verify_restored_archive(destination, bundle_digest, attestation_bytes, *, incident_id,
                            authority_provider, clock):
    """Re-read completed destination evidence without accessing its former source.

    Actual destination raw/verified and both backups, plus the exact original
    signature artifact and its backup, are mandatory. The final actual owner
    observation reports canonical revocation status at its retained head. This
    report neither clears incident holds nor permits selection or orders. An
    archived revoked signature can still identify exact evidence. No archive
    writes, provision, source discovery or recovery action happens here; the
    trusted owner loader retains its existing verified-state side effects.
    """
    try:
        return _verify_restored_archive(destination, bundle_digest, attestation_bytes,
            incident_id=incident_id, authority_provider=authority_provider, clock=clock)
    except (OSError, RuntimeError):
        raise BundleRecoveryError('BUNDLE_RECOVERY_IO_REFUSED') from None
    except (AttributeError, TypeError, OverflowError):
        raise BundleRecoveryError('BUNDLE_RECOVERY_INPUT_INVALID') from None
