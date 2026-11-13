"""Full capture packet archival and historical audit through actual BundleStore.

Publication uses existing primary/backup/catalog/head verification. A receipt is
an observation, never current account evidence or a source/owner/guard permit.
Historical replay keeps original times and calls the real I3a collector replay.
No runtime provision, new writer, implicit clock, source verifier or trading action.
The collect wrapper passes its explicit clock only to the existing actual source.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime

from execution_accounts.baseline import BaselineState, risk_baseline
from execution_accounts.provider import EvidenceError
from execution_launch import account_interval as A
from execution_launch import guard_capture_format as C
from execution_launch import guard_capture_material as M
from execution_launch import research_bundle_format as F
from execution_launch import research_bundle_store as S
from execution_launch.evidence_objects import decode_reference


class GuardCaptureArchiveError(ValueError):
    """Fixed CAPTURE_ARCHIVE_* diagnostics; never raw/private exception text."""


def _need(condition, code):
    if not condition:
        raise GuardCaptureArchiveError(code)


def _hash(value):
    return type(value) is str and len(value) == 64 and all(char in '0123456789abcdef' for char in value)


def _store(store):
    _need(type(store) is S.BundleStore, 'CAPTURE_ARCHIVE_ACTUAL_STORE_REQUIRED')
    store._configuration()


def _head(store):
    with store._locked():
        catalog = store._load()
        return catalog.sequence, catalog.head


def _limits(limits):
    _need(type(limits) is C.CaptureFormatLimits, 'CAPTURE_ARCHIVE_LIMITS_INVALID')
    return C._limits(limits)


def _manifest(store, packet_sha256, inventory, payloads):
    """Deterministic full wrapper, not a research/evaluation completeness claim."""
    _need(_hash(packet_sha256), 'CAPTURE_ARCHIVE_PACKET_INVALID')
    files, observations = [], []
    for item in inventory:
        files.append(F.BundleFile(logical_id=item.logical_id, original_name=item.original_name,
            source_name=None, role='other_input', study_id=None, required=True,
            byte_count=item.byte_count, sha256=item.sha256,
            payload_ref=store.preview_payload(payloads[item.logical_id])))
        observations.append(F.InputObservation(observation_id=item.logical_id,
            original_name=item.original_name, source_name=None, role='other_input', study_id=None,
            required=True, status='COLLECTED', logical_id=item.logical_id))
    value = F.RawArchiveManifest(schema_version=1, kind='RAW_ARCHIVED',
        run_id='capture-'+packet_sha256, revision_id='capture-packet-v1',
        attempt_id='capture-'+packet_sha256, parent_bundle_sha256=None,
        storage_policy_sha256=store.limits.policy_sha256,
        object_policy_sha256=store.limits.object_limits.policy_sha256,
        expected_candidates=None, inventory_complete=True,
        observed_inputs=tuple(observations), files=tuple(files))
    raw = F.raw_archive_bytes(value, limits=store.limits.format_limits)
    return value, raw, F.raw_archive_digest(value, limits=store.limits.format_limits)


def _preflight_read_locked(store, archive_digest, limits):
    """Run only inside the actual store lock, before full payload reads."""
    catalog = store._load()
    entry = catalog.entries.get(archive_digest)
    _need(entry is not None, 'CAPTURE_ARCHIVE_NOT_PUBLISHED')
    _need(entry.row['kind'] == 'RAW_ARCHIVED' and entry.backed,
          'CAPTURE_ARCHIVE_BACKED_RAW_REQUIRED')
    reference = decode_reference(S._canonical(entry.row['manifest_ref']))
    _need(reference.payload_bytes <= store.limits.format_limits.max_manifest_bytes,
          'CAPTURE_ARCHIVE_RESOURCE_LIMIT')
    raw = store._objects(False).read(reference)
    manifest, digest = store._manifest('RAW_ARCHIVED', raw)
    _need(digest == archive_digest and store._files_digest(manifest) == entry.row['files_sha256'],
          'CAPTURE_ARCHIVE_WRAPPER_INVALID')
    _need(manifest.revision_id == 'capture-packet-v1'
          and manifest.run_id.startswith('capture-') and _hash(manifest.run_id[8:])
          and manifest.attempt_id == manifest.run_id and manifest.parent_bundle_sha256 is None
          and manifest.expected_candidates is None and manifest.inventory_complete is True,
          'CAPTURE_ARCHIVE_WRAPPER_INVALID')
    _need(3 <= len(manifest.files) <= limits.max_receipts+2,
          'CAPTURE_ARCHIVE_RESOURCE_LIMIT')
    total, receipt_bytes, names, observations = 0, 0, [], []
    for item in manifest.files:
        _need(item.role == 'other_input' and item.source_name is None and item.study_id is None
              and item.required is True, 'CAPTURE_ARCHIVE_WRAPPER_INVALID')
        name = item.logical_id
        if name == 'baseline':
            expected_name, maximum = 'baseline.json', limits.max_baseline_bytes
        elif name == 'packet':
            expected_name, maximum = 'packet.json', limits.max_packet_bytes
        else:
            _need(len(name) == 14 and name.startswith('receipt-')
                  and name[8:].isascii() and name[8:].isdigit(), 'CAPTURE_ARCHIVE_WRAPPER_INVALID')
            expected_name, maximum = name+'.bin', limits.max_receipt_bytes
            receipt_bytes += item.byte_count
        _need(item.original_name == expected_name and 0 < item.byte_count <= maximum,
              'CAPTURE_ARCHIVE_RESOURCE_LIMIT')
        total += item.byte_count; names.append(name)
        _need(total <= limits.max_total_bytes and receipt_bytes <= limits.max_total_receipt_bytes,
              'CAPTURE_ARCHIVE_RESOURCE_LIMIT')
        observations.append(F.InputObservation(observation_id=name, original_name=expected_name,
            source_name=None, role='other_input', study_id=None, required=True,
            status='COLLECTED', logical_id=name))
    expected_names = ['baseline', 'packet'] + ['receipt-'+str(index).zfill(6)
                                               for index in range(len(names)-2)]
    _need(names == expected_names and manifest.observed_inputs == tuple(observations),
          'CAPTURE_ARCHIVE_WRAPPER_INVALID')
    _need(store._load() == catalog, 'CAPTURE_ARCHIVE_PUBLICATION_CHANGED')
    return raw, (catalog.sequence, catalog.head)


def _preflight_read(store, archive_digest, limits):
    """Preserve own admission diagnostics only after healthy lock cleanup."""
    failure, result = None, None
    with store._locked():
        try:
            result = _preflight_read_locked(store, archive_digest, limits)
        except GuardCaptureArchiveError as exc:
            failure = exc
    # Actual root/lock/head/cleanup errors above must override a retained error.
    if failure is not None:
        raise failure
    return result


def _read(store, archive_digest, expected_previous_state_sha256, limits):
    _store(store); limits = _limits(limits)
    _need(_hash(archive_digest) and _hash(expected_previous_state_sha256), 'CAPTURE_ARCHIVE_DIGEST_INVALID')
    manifest_bytes, original_head = _preflight_read(store, archive_digest, limits)
    # This actual call reads every primary AND backup file plus the retained head.
    retained = store.read_raw(archive_digest, require_backup=True)
    _need(retained.manifest_bytes == manifest_bytes, 'CAPTURE_ARCHIVE_READBACK_MISMATCH')
    packet = C.parse_capture_archive(retained.files,
        expected_previous_state_sha256=expected_previous_state_sha256, limits=limits)
    _, expected_bytes, expected_digest = _manifest(store, packet.packet_sha256, packet.inventory, retained.files)
    _need(expected_bytes == retained.manifest_bytes and expected_digest == archive_digest,
          'CAPTURE_ARCHIVE_WRAPPER_INVALID')
    final_head = _head(store)
    _need(final_head == original_head, 'CAPTURE_ARCHIVE_PUBLICATION_CHANGED')
    return packet, retained, final_head


class _Nonoperational:
    @property
    def source_authenticated(self): return False

    @property
    def current_freshness_verified(self): return False

    @property
    def guard_committed(self): return False

    @property
    def execution_ready(self): return False


@dataclass(frozen=True, kw_only=True)
class CaptureArchiveReceipt(_Nonoperational):
    archive_digest: str
    packet_sha256: str
    previous_state_sha256: str
    path_sha256: str
    manifest_sha256: str
    observed_at: datetime
    catalog_head: tuple[int, str]
    backup_verified: bool = True


@dataclass(frozen=True, kw_only=True)
class ArchivedCaptureReplay(_Nonoperational):
    receipt: CaptureArchiveReceipt
    historical_evaluation_at: datetime
    capture_material_sha256: str
    material: M.GuardCaptureMaterial = field(repr=False)

    @property
    def historical_replay(self): return True


@dataclass(frozen=True, kw_only=True)
class CollectedCaptureArchive(_Nonoperational):
    receipt: CaptureArchiveReceipt
    replay: ArchivedCaptureReplay | None = field(repr=False)
    audit_error_code: str | None


def _receipt(archive_digest, packet, head):
    return CaptureArchiveReceipt(archive_digest=archive_digest, packet_sha256=packet.packet_sha256,
        previous_state_sha256=packet.previous_state_sha256, path_sha256=packet.staged.path_sha256,
        manifest_sha256=packet.staged.manifest_sha256, observed_at=packet.staged.observed_at, catalog_head=head)


def archive_guard_capture_packet(store, staged, previous, *, limits=C.DEFAULT_LIMITS):
    """Commit structurally retained original bytes before any semantic audit."""
    _store(store); limits = _limits(limits)
    encoded = C.build_capture_archive(staged, previous, limits=limits)
    _, manifest_bytes, archive_digest = _manifest(store, encoded.packet_sha256, encoded.inventory, encoded.payloads)
    store.archive_raw(manifest_bytes, encoded.payloads)
    # A caller-created/returned store receipt is never accepted as publication proof.
    packet, retained, head = _read(store, archive_digest, encoded.previous_state_sha256, limits)
    _need(retained.manifest_bytes == manifest_bytes and dict(retained.files) == dict(encoded.payloads)
          and packet.packet_sha256 == encoded.packet_sha256, 'CAPTURE_ARCHIVE_READBACK_MISMATCH')
    return _receipt(archive_digest, packet, head)


def read_guard_capture_packet(store, archive_digest, *, expected_previous_state_sha256, limits=C.DEFAULT_LIMITS):
    """Actual full private archive read; returned typed packet conveys no trust."""
    packet, _, _ = _read(store, archive_digest, expected_previous_state_sha256, limits)
    return packet


def replay_guard_capture_archive(store, archive_digest, *, expected_previous_state_sha256, limits=C.DEFAULT_LIMITS):
    """Replay at the ORIGINAL preview time; never tests current operating freshness."""
    packet, original, head = _read(store, archive_digest, expected_previous_state_sha256, limits)
    historical = packet.staged.observed_at
    material = M.prepare_guard_capture_material(packet.staged, packet.previous, now=historical)
    _need(type(material) is M.GuardCaptureMaterial, 'CAPTURE_ARCHIVE_MATERIAL_INVALID')
    # Audit work is not a storage lease. Reread real bytes and roots/head afterwards.
    final_packet, final, final_head = _read(store, archive_digest, expected_previous_state_sha256, limits)
    _need(final == original and final_head == head and final_packet.packet_sha256 == packet.packet_sha256,
          'CAPTURE_ARCHIVE_READBACK_MISMATCH')
    return ArchivedCaptureReplay(receipt=_receipt(archive_digest, final_packet, final_head),
        historical_evaluation_at=historical, capture_material_sha256=material.capture_material_sha256, material=material)


def _audit_code(exc):
    value = str(exc)
    _need(isinstance(exc, EvidenceError), 'CAPTURE_ARCHIVE_AUDIT_REFUSED')
    if (1 <= len(value) <= 96 and value.startswith(('GUARD_CAPTURE_', 'EVIDENCE_', 'COLLECTOR_'))
            and all(char in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_' for char in value)):
        return value
    return 'CAPTURE_ARCHIVE_AUDIT_REFUSED'


def collect_archive_guard_capture(source, collector_source, *, store, previous, anchor, coverage,
                                 clock, trade_fees=(), limits=C.DEFAULT_LIMITS):
    """Explicit collect→commit/readback→historical audit; existing collect API unchanged."""
    _need(type(source) is A.ContinuousUpbitCandidateSource and type(previous) is BaselineState,
          'CAPTURE_ARCHIVE_ACTUAL_COLLECTION_REQUIRED')
    _store(store); _limits(limits)
    M._admit_tree(previous)
    risk_baseline(previous, now=previous.asof, expected_head=previous.state_digest)
    original = deepcopy(previous)
    staged = source.collect(collector_source, previous=deepcopy(original), anchor=anchor,
                            coverage=coverage, clock=clock, trade_fees=trade_fees)
    receipt = archive_guard_capture_packet(store, staged, original, limits=limits)
    try:
        replay = replay_guard_capture_archive(store, receipt.archive_digest,
            expected_previous_state_sha256=receipt.previous_state_sha256, limits=limits)
    except EvidenceError as exc:
        # Preserve successfully archived originals even when real replay refuses.
        packet, _, head = _read(store, receipt.archive_digest, receipt.previous_state_sha256, limits)
        _need(packet.packet_sha256 == receipt.packet_sha256, 'CAPTURE_ARCHIVE_READBACK_MISMATCH')
        return CollectedCaptureArchive(receipt=_receipt(receipt.archive_digest, packet, head),
                                       replay=None, audit_error_code=_audit_code(exc))
    return CollectedCaptureArchive(receipt=replay.receipt, replay=replay, audit_error_code=None)
