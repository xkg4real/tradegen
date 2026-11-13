"""Current-owner authentication of exact archived bytes; never operational authority.

Only the actual BundleStore and CurrentOwnerAuthority deployment dependencies
are accepted. A signed raw archive remains raw, including recorded failures.
The returned assessment describes this observation only: it is not a reusable
token, provenance review, strategy selection, recovery permit or order gate.
Individual-document revocation and signature-envelope backup are not implemented.
The existing owner loader may write its usual verified-state snapshot; this
module does not initialize, repair, sign or activate anything.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib

from core.compliance import model as compliance
from execution_control.owner_authority import (
    CurrentOwnerAuthority, MAX_AUTHORITY_AGE_SECONDS, ReviewAuthority,
)
from execution_launch import bundle_attestation as A
from execution_launch import research_bundle_format as F
from execution_launch.research_bundle_store import BundleStore


class BundleAuthenticationError(ValueError):
    """Fixed ARCHIVE_AUTH_* diagnostics; no original bytes, paths or owner details."""


def _need(condition, code):
    if not condition:
        raise BundleAuthenticationError(code)


def _time(value):
    _need(type(value) is datetime and value.utcoffset() is not None, 'ARCHIVE_AUTH_TIME_INVALID')
    return value.astimezone(timezone.utc)


@dataclass(frozen=True, kw_only=True)
class ArchiveAttestationAssessment:
    """Read-side report only; constructing or replaying this grants no authority."""
    scope: str
    bundle_kind: str
    bundle_digest: str
    input_archive_digest: str
    request_sha256: str
    attestation_sha256: str
    verified_at: datetime
    archive_identity_authenticated: bool
    revocation_status: str = 'UNSUPPORTED'
    source_authenticated: bool = False
    research_selection_ready: bool = False
    execution_ready: bool = False
    automatic_recovery_supported: bool = False
    current_use_eligible: bool = False
    signature_backup_verified: bool = False
    reasons: tuple[str, ...] = (
        'ARCHIVE_AUTH_IDENTITY_ONLY', 'ARCHIVE_AUTH_INDIVIDUAL_REVOCATION_UNSUPPORTED',
        'ARCHIVE_AUTH_CURRENT_OPERATIONAL_USE_UNSUPPORTED', 'ARCHIVE_AUTH_SIGNATURE_BACKUP_UNVERIFIED',
    )


def _authority(document, authority, now):
    """Validate only an observation obtained inside this call from the actual provider."""
    now = _time(now)
    _need(type(authority) is ReviewAuthority, 'ARCHIVE_AUTH_OWNER_AUTHORITY_REQUIRED')
    observed = _time(authority.observed_at)
    _need(timedelta(0) <= now-observed <= timedelta(seconds=MAX_AUTHORITY_AGE_SECONDS),
          'ARCHIVE_AUTH_OWNER_AUTHORITY_STALE')
    context = authority.context
    try:
        intact = (type(context) is compliance.Context and compliance.is_sealed(context)
            and type(context.owner) is compliance.OwnerState
            and type(context.active) is compliance.ApprovedState
            and context.ctx_hash == compliance.context_hash(context))
    except (ValueError, TypeError, AttributeError, OverflowError, RecursionError):
        intact = False
    _need(intact, 'ARCHIVE_AUTH_OWNER_CONTEXT_INVALID')
    _need(context.date == now.astimezone(compliance.KST).date()
          and context.owner.ok and context.code_signed is True,
          'ARCHIVE_AUTH_OWNER_APPROVAL_REQUIRED')
    # A halted account or unavailable trading tables does not erase the identity
    # of archived failures. No trading gate consumes this archive-only report.
    public = authority.public_key_raw
    _need(type(public) is bytes and len(public) == 32, 'ARCHIVE_AUTH_PUBLIC_KEY_INVALID')
    body = A.verify_attestation_signature(document, public_key_raw=public)
    fingerprint = 'SHA256:' + hashlib.sha256(public).hexdigest()
    _need(fingerprint == context.owner.fingerprint == body['owner_fingerprint'],
          'ARCHIVE_AUTH_CURRENT_KEY_MISMATCH')
    _need(context.code_hash == body['deployment_code_hash'], 'ARCHIVE_AUTH_DEPLOYMENT_CODE_MISMATCH')
    issued, expires = datetime.fromisoformat(body['issued_at']), datetime.fromisoformat(body['expires_at'])
    _need(issued <= now < expires, 'ARCHIVE_AUTH_EXPIRED_OR_FUTURE')
    return body


def _graph(store, bundle_digest, request, *, deployment_code_hash):
    """Read actual current primary/backup graphs and reconstruct the displayed request."""
    if request['bundle_kind'] == 'RAW_ARCHIVED':
        raw = store.read_raw(bundle_digest, require_backup=True)
        target, verified_bytes = raw, None
    else:
        target = store.read_verified(bundle_digest, require_backup=True)
        raw = store.read_raw(target.manifest.input_archive_digest, require_backup=True)
        F.validate_verified_inputs(raw.manifest, target.manifest, limits=store.limits.format_limits)
        _need(all(target.files[key] == value for key, value in raw.files.items()),
              'ARCHIVE_AUTH_RAW_INPUT_BYTES_MISMATCH')
        verified_bytes = target.manifest_bytes
    F.validate_payloads(raw.manifest, raw.files, limits=store.limits.format_limits)
    F.validate_payloads(target.manifest, target.files, limits=store.limits.format_limits)
    expected = A.request_from_manifests(raw.manifest_bytes, verified_bytes,
        requested_at=datetime.fromisoformat(request['requested_at']),
        expires_at=datetime.fromisoformat(request['expires_at']),
        deployment_code_hash=deployment_code_hash)
    _need(A.archive_request_bytes(expected) == A.archive_request_bytes(request),
          'ARCHIVE_AUTH_REQUEST_GRAPH_MISMATCH')
    A.validate_request_payloads(expected, target.files)
    # Bytes are immutable; copied tuple membership cannot later be changed by a
    # caller mutating a mapping. No StoredBundle or receipt is returned as trust.
    return raw.manifest_bytes, verified_bytes, tuple(sorted(target.files.items()))


def authenticate_bundle_attestation(store, bundle_digest, document_bytes, *, authority_provider, clock):
    """Authenticate exact archive identity with fresh real owner and full graph reads.

    The reviewed CLI supplies one actual clock and its CurrentOwnerAuthority.
    Initial and repeated owner observations retain that provider's key/code/head
    pins and rollback latch. Graphs are read twice across owner re-observation;
    the last owner read and local finish check catch expiry or stale/changed
    authorization during work. The entire attempt must fit the original
    observation's 30-second lifetime. Benign verified owner-log growth is
    permitted; the current provider keeps code and key pinned. This finite
    observation is not a storage lease.
    """
    _need(type(store) is BundleStore, 'ARCHIVE_AUTH_STORE_REQUIRED')
    _need(type(authority_provider) is CurrentOwnerAuthority and callable(clock)
          and getattr(authority_provider, '_clock', None) is clock, 'ARCHIVE_AUTH_ACTUAL_PROVIDER_REQUIRED')
    _need(type(document_bytes) is bytes, 'ARCHIVE_AUTH_DOCUMENT_BYTES_REQUIRED')
    envelope = A.parse_attestation_document(document_bytes)
    request = envelope['body']['request']
    _need(type(bundle_digest) is str and bundle_digest == request['bundle_digest'],
          'ARCHIVE_AUTH_TARGET_MISMATCH')
    started = _time(clock())
    first = authority_provider(started)
    _authority(document_bytes, first, started)
    initial_graph = _graph(store, bundle_digest, request, deployment_code_hash=first.context.code_hash)

    middle = _time(clock())
    _need(middle >= started, 'ARCHIVE_AUTH_CLOCK_ROLLBACK')
    second = authority_provider(middle)
    _authority(document_bytes, second, middle)
    _need(_graph(store, bundle_digest, request, deployment_code_hash=second.context.code_hash) == initial_graph,
          'ARCHIVE_AUTH_GRAPH_CHANGED')

    observed = _time(clock())
    _need(observed >= middle, 'ARCHIVE_AUTH_CLOCK_ROLLBACK')
    latest = authority_provider(observed)
    _authority(document_bytes, latest, observed)
    # Finish every potentially expensive parse, context hash and signature/digest
    # operation BEFORE sampling the completion clock. A large document must not
    # cross expiry during verification and retain an earlier verified_at value.
    for authority in (first, second, latest):
        _authority(document_bytes, authority, observed)
    document_digest = A.attestation_document_digest(document_bytes)
    issued = datetime.fromisoformat(envelope['body']['issued_at'])
    expires = datetime.fromisoformat(envelope['body']['expires_at'])
    observations = tuple((_time(authority.observed_at), authority.context.date)
                         for authority in (first, second, latest))
    finished = _time(clock())
    _need(finished >= observed, 'ARCHIVE_AUTH_CLOCK_ROLLBACK')
    _need(issued <= finished < expires, 'ARCHIVE_AUTH_EXPIRED_OR_FUTURE')
    day = finished.astimezone(compliance.KST).date()
    # Keep each original timestamp. The checks after the completion clock are
    # bounded comparisons only; a late observation needs a fresh attempt.
    for original_at, original_day in observations:
        _need(timedelta(0) <= finished-original_at <= timedelta(seconds=MAX_AUTHORITY_AGE_SECONDS),
              'ARCHIVE_AUTH_OWNER_AUTHORITY_STALE')
        _need(original_day == day, 'ARCHIVE_AUTH_OWNER_APPROVAL_REQUIRED')
    return ArchiveAttestationAssessment(scope=A.SCOPE, bundle_kind=request['bundle_kind'],
        bundle_digest=bundle_digest, input_archive_digest=request['input_archive_digest'],
        request_sha256=request['request_sha256'], attestation_sha256=document_digest, verified_at=finished,
        archive_identity_authenticated=True)
