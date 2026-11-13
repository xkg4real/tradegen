"""Retain exact guard inputs and observed completion through existing BundleStore.

RAW parent links are followed explicitly. Historical replay and durable receipt
correspondence confer no source authentication, current owner approval or order
permission. Archive locks and real Journal transactions are separate phases.
There is no writer, head adoption, source request, recovery or commit engine here.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field, fields
from datetime import date, datetime, timezone
from decimal import Decimal
from functools import wraps
import hashlib

from execution_accounts.baseline_store import CheckpointStore
from execution_control.risk import RecoveryCondition, RiskPolicy
from execution_control.store import Journal
from execution_launch import committed_account as P
from execution_launch import guard_capture_archive as C
from execution_launch import guard_capture_format as CF
from execution_launch import guard_generation_format as F
from execution_launch import research_bundle_format as BF
from execution_launch import research_bundle_store as BS
from execution_launch.continuous_guard import AccountCaptureInputs, OwnerContextClaim, ValuationInputs, _input_digest
from execution_launch.continuous_guard_commit import GuardCheckpointStore, GuardCommitReceipt
from execution_launch.evidence_objects import decode_reference


class GuardGenerationArchiveError(ValueError):
    """Fixed GENERATION_ARCHIVE_* diagnostics, never private exception text."""


def _need(ok, code):
    if not ok:
        raise GuardGenerationArchiveError('GENERATION_ARCHIVE_'+code)


def _hash(value):
    return type(value) is str and len(value) == 64 and all(c in '0123456789abcdef' for c in value)


def _boundary(function):
    @wraps(function)
    def call(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except GuardGenerationArchiveError:
            raise
        except F.GuardGenerationFormatError as exc:
            code = 'RESOURCE_LIMIT' if str(exc) == 'GENERATION_RESOURCE_LIMIT' else 'INPUT_INVALID'
            raise GuardGenerationArchiveError('GENERATION_ARCHIVE_'+code) from None
        except (BS.BundleStoreError, BF.BundleFormatError, C.GuardCaptureArchiveError,
                CF.GuardCaptureFormatError) as exc:
            code = 'RESOURCE_LIMIT' if str(exc).endswith('RESOURCE_LIMIT') else 'STORE_REFUSED'
            raise GuardGenerationArchiveError('GENERATION_ARCHIVE_'+code) from None
        except Exception:
            raise GuardGenerationArchiveError('GENERATION_ARCHIVE_INPUT_INVALID') from None
    return call


_TYPES = frozenset(row[0] for row in CF._SCHEMAS.values()) | frozenset((
    RiskPolicy, RecoveryCondition, OwnerContextClaim, AccountCaptureInputs, ValuationInputs))
_QUANTA = tuple(Decimal((0, (1,), exponent)) for exponent in range(-512, 513))


def _representation(value):
    """Bounded, closed, type-sensitive comparison before deepcopy/legacy hashes.

No caller Mapping/iterator hooks are visited. Decimal admission avoids creating
a coefficient tuple until both its exponent and coefficient length are bounded.
"""
    nodes = text = 0
    def visit(item, depth):
        nonlocal nodes, text
        nodes += 1
        _need(depth <= 24 and nodes <= 2000000, 'RESOURCE_LIMIT')
        kind = type(item)
        if kind in _TYPES:
            declared = fields(kind)
            actual = vars(item)
            _need(type(actual) is dict and len(actual) == len(declared)
                  and all(type(name) is str for name in actual)
                  and set(actual) == {entry.name for entry in declared}, 'INPUT_INVALID')
            return (kind.__name__, tuple((entry.name, visit(actual[entry.name], depth+1)) for entry in declared))
        if kind is dict:
            _need(depth == 0 and len(item) == len(P._PACKAGE_KEYS)
                  and all(type(name) is str for name in item) and set(item) == P._PACKAGE_KEYS,
                  'INPUT_INVALID')
            return ('package', tuple((name, visit(item[name], depth+1)) for name in sorted(item)))
        if kind is tuple:
            _need(len(item) <= 100000, 'RESOURCE_LIMIT')
            return ('tuple', tuple(visit(child, depth+1) for child in item))
        if kind is Decimal:
            _need(item.is_finite(), 'INPUT_INVALID')
            exponent = next((index-512 for index, quantum in enumerate(_QUANTA)
                             if item.same_quantum(quantum)), None)
            _need(exponent is not None and (item.is_zero() or item.adjusted()-exponent+1 <= 512),
                  'RESOURCE_LIMIT')
            return ('Decimal', item.as_tuple())
        if kind is str:
            _need(len(item) <= 65536, 'RESOURCE_LIMIT')
            text += len(item)*12
            _need(text <= 192*1024*1024, 'RESOURCE_LIMIT')
            return ('str', item)
        if kind is int:
            _need(item.bit_length() <= 256, 'RESOURCE_LIMIT')
            return ('int', item)
        if kind is datetime:
            _need(item.utcoffset() is not None and 2 <= item.year <= 9998, 'INPUT_INVALID')
            return ('datetime', item.astimezone(timezone.utc).isoformat())
        if kind is date:
            return ('date', item.isoformat())
        _need(item is None or kind is bool, 'INPUT_INVALID')
        return ('None' if item is None else 'bool', item)
    return visit(value, 0)


def _snapshot(package):
    representation = _representation(package)
    P._check_package(package)
    saved = deepcopy(package)
    _need(_representation(saved) == representation == _representation(package), 'BINDING_MISMATCH')
    return saved


def _store(store, limits, capture_limits):
    _need(type(store) is BS.BundleStore and type(limits) is F.GenerationFormatLimits
          and type(capture_limits) is CF.CaptureFormatLimits, 'INPUT_INVALID')
    limits.__post_init__(); CF._limits(capture_limits)
    store._configuration()


def _head(store):
    with store._locked():
        catalog = store._load()
        return catalog.sequence, catalog.head


def _spec(kind):
    return ('guard-input', 'guard-input-v1') if kind == 'input' else ('guard-completion', 'guard-completion-v1')


def _record_bytes(record, kind, limits):
    return (F.input_bytes if kind == 'input' else F.completion_bytes)(record, limits=limits)


def _record_digest(record, kind, limits):
    return (F.input_digest if kind == 'input' else F.completion_digest)(record, limits=limits)


def _manifest(store, raw, record_sha, parent, kind):
    logical, revision = _spec(kind)
    item = BF.BundleFile(logical_id=logical, original_name=logical+'.json', source_name=None,
        role='other_input', study_id=None, required=True, byte_count=len(raw),
        sha256=hashlib.sha256(raw).hexdigest(), payload_ref=store.preview_payload(raw))
    observation = BF.InputObservation(observation_id=logical, original_name=item.original_name,
        source_name=None, role='other_input', study_id=None, required=True,
        status='COLLECTED', logical_id=logical)
    manifest = BF.RawArchiveManifest(schema_version=1, kind='RAW_ARCHIVED',
        run_id=logical+'-'+record_sha, revision_id=revision, attempt_id=logical+'-'+record_sha,
        parent_bundle_sha256=parent, storage_policy_sha256=store.limits.policy_sha256,
        object_policy_sha256=store.limits.object_limits.policy_sha256,
        expected_candidates=None, inventory_complete=True, observed_inputs=(observation,), files=(item,))
    return (BF.raw_archive_bytes(manifest, limits=store.limits.format_limits),
            BF.raw_archive_digest(manifest, limits=store.limits.format_limits), {logical: raw})


def _preflight(store, digest, kind, limits):
    """Bound the singleton graph before any complete payload materialization."""
    failure = result = None
    with store._locked():
        try:
            catalog = store._load()
            entry = catalog.entries.get(digest)
            _need(entry is not None, 'NOT_PUBLISHED')
            _need(entry.row['kind'] == 'RAW_ARCHIVED' and entry.backed, 'WRAPPER_INVALID')
            reference = decode_reference(BS._canonical(entry.row['manifest_ref']))
            _need(reference.payload_bytes <= store.limits.format_limits.max_manifest_bytes, 'RESOURCE_LIMIT')
            raw = store._objects(False).read(reference)
            manifest, actual_digest = store._manifest('RAW_ARCHIVED', raw)
            logical, revision = _spec(kind)
            _need(actual_digest == digest and store._files_digest(manifest) == entry.row['files_sha256']
                  and len(manifest.files) == 1 and manifest.revision_id == revision
                  and manifest.expected_candidates is None and manifest.inventory_complete is True
                  and _hash(manifest.parent_bundle_sha256), 'WRAPPER_INVALID')
            item = manifest.files[0]
            _need(item.logical_id == logical and item.original_name == logical+'.json'
                  and item.role == 'other_input' and item.source_name is None and item.study_id is None
                  and item.required is True, 'WRAPPER_INVALID')
            _need(0 < item.byte_count <= limits.max_record_bytes, 'RESOURCE_LIMIT')
            _need(store._load() == catalog, 'READBACK_MISMATCH')
            result = raw, (catalog.sequence, catalog.head)
        except GuardGenerationArchiveError as exc:
            failure = exc
    if failure is not None:
        raise failure
    return result


def _metadata(store, digest, kind, limits):
    _need(_hash(digest), 'INPUT_INVALID')
    before, head = _preflight(store, digest, kind, limits)
    retained = store.read_raw(digest, require_backup=True)
    logical, _ = _spec(kind)
    _need(retained.manifest_bytes == before and set(retained.files) == {logical}, 'READBACK_MISMATCH')
    raw = retained.files[logical]
    record = (F.parse_input if kind == 'input' else F.parse_completion)(raw, limits=limits)
    record_sha = _record_digest(record, kind, limits)
    parent = record.capture_archive_digest if kind == 'input' else record.input_archive_digest
    expected, expected_digest, payloads = _manifest(store, raw, record_sha, parent, kind)
    _need(expected == before and expected_digest == digest and payloads == dict(retained.files)
          and _head(store) == head, 'WRAPPER_INVALID')
    return record, record_sha, raw, head


def _input_digest_from_package(expected_guard_head, package):
    return _input_digest(expected_guard_head, package['baseline_before'], package['policy'],
        package['owner_before'], package['owner_after'], package['path'], package['valuation_inputs'],
        package['account_capture'], package['coverage'], package['interval'])


def _reconstruct(store, record, capture_limits):
    packet = C.read_guard_capture_packet(store, record.capture_archive_digest,
        expected_previous_state_sha256=record.previous_state_sha256, limits=capture_limits)
    replay = C.replay_guard_capture_archive(store, record.capture_archive_digest,
        expected_previous_state_sha256=record.previous_state_sha256, limits=capture_limits)
    material = replay.material
    package = dict(baseline_before=packet.previous, policy=record.policy,
        owner_before=record.owner_before, owner_after=record.owner_after,
        path=material.path, valuation_inputs=material.valuation_inputs,
        account_capture=material.account_capture, coverage=material.coverage,
        interval=material.interval, now=record.evaluated_at)
    package = _snapshot(package)
    _need(packet.packet_sha256 == replay.receipt.packet_sha256 == record.capture_packet_sha256
          and replay.capture_material_sha256 == record.capture_material_sha256
          and packet.previous.state_digest == record.expected_baseline_head == record.previous_state_sha256
          and P._package_digest(package) == record.package_sha256
          and _input_digest_from_package(record.expected_guard_head, package) == record.input_sha256,
          'BINDING_MISMATCH')
    return package


class _Nonoperational:
    @property
    def source_authenticated(self): return False
    @property
    def current_freshness_verified(self): return False
    @property
    def execution_ready(self): return False


@dataclass(frozen=True, kw_only=True)
class RetainedGuardInput(_Nonoperational):
    archive_digest: str
    record_sha256: str
    record: F.GuardInputRecord = field(repr=False)
    package: dict = field(repr=False)


@dataclass(frozen=True, kw_only=True)
class RetainedGuardCompletion(_Nonoperational):
    archive_digest: str
    record_sha256: str
    record: F.GuardCompletionRecord = field(repr=False)
    retained_input: RetainedGuardInput = field(repr=False)


def _read_input(store, digest, limits, capture_limits):
    record, record_sha, raw, head = _metadata(store, digest, 'input', limits)
    package = _reconstruct(store, record, capture_limits)
    final, final_sha, final_raw, final_head = _metadata(store, digest, 'input', limits)
    _need(raw == final_raw and record_sha == final_sha and head == final_head, 'READBACK_MISMATCH')
    return RetainedGuardInput(archive_digest=digest, record_sha256=record_sha, record=final, package=package)


@_boundary
def retain_guard_input(store, capture_archive_digest, package, *, expected_guard_head,
                       expected_baseline_head, expected_control_head,
                       limits=F.DEFAULT_LIMITS, capture_limits=CF.DEFAULT_LIMITS):
    _store(store, limits, capture_limits)
    _need(all(_hash(value) for value in (capture_archive_digest, expected_guard_head,
                                       expected_baseline_head, expected_control_head)), 'INPUT_INVALID')
    supplied = _snapshot(package)
    packet = C.read_guard_capture_packet(store, capture_archive_digest,
        expected_previous_state_sha256=expected_baseline_head, limits=capture_limits)
    replay = C.replay_guard_capture_archive(store, capture_archive_digest,
        expected_previous_state_sha256=expected_baseline_head, limits=capture_limits)
    record = F.GuardInputRecord(schema_version=1, kind='GUARD_INPUT', replay_revision=CF.REPLAY_REVISION,
        capture_archive_digest=capture_archive_digest, capture_packet_sha256=packet.packet_sha256,
        capture_material_sha256=replay.capture_material_sha256, previous_state_sha256=expected_baseline_head,
        expected_guard_head=expected_guard_head, expected_baseline_head=expected_baseline_head,
        expected_control_head=expected_control_head, package_sha256=P._package_digest(supplied),
        input_sha256=_input_digest_from_package(expected_guard_head, supplied), policy=supplied['policy'],
        owner_before=supplied['owner_before'], owner_after=supplied['owner_after'], evaluated_at=supplied['now'])
    # Format roundtrip detaches the small metadata before any slow publication.
    raw = F.input_bytes(record, limits=limits)
    record = F.parse_input(raw, limits=limits)
    candidate = _reconstruct(store, record, capture_limits)
    _need(_representation(candidate) == _representation(supplied), 'BINDING_MISMATCH')
    record_sha = F.input_digest(record, limits=limits)
    manifest, digest, payloads = _manifest(store, raw, record_sha, capture_archive_digest, 'input')
    store.archive_raw(manifest, payloads)
    retained = _read_input(store, digest, limits, capture_limits)
    _need(retained.record_sha256 == record_sha
          and _representation(retained.package) == _representation(supplied), 'READBACK_MISMATCH')
    return retained


@_boundary
def read_guard_input(store, input_archive_digest, *, limits=F.DEFAULT_LIMITS, capture_limits=CF.DEFAULT_LIMITS):
    _store(store, limits, capture_limits)
    return _read_input(store, input_archive_digest, limits, capture_limits)


def _read_completion(store, digest, expected_input, limits, capture_limits):
    record, record_sha, raw, head = _metadata(store, digest, 'completion', limits)
    _need(_hash(expected_input) and record.input_archive_digest == expected_input, 'BINDING_MISMATCH')
    retained = _read_input(store, expected_input, limits, capture_limits)
    _need(record.input_record_sha256 == retained.record_sha256
          and record.package_sha256 == retained.record.package_sha256
          and record.input_sha256 == retained.record.input_sha256, 'BINDING_MISMATCH')
    final, final_sha, final_raw, final_head = _metadata(store, digest, 'completion', limits)
    _need(raw == final_raw and record_sha == final_sha and head == final_head, 'READBACK_MISMATCH')
    return RetainedGuardCompletion(archive_digest=digest, record_sha256=record_sha,
                                  record=final, retained_input=retained)


@_boundary
def read_guard_completion(store, completion_archive_digest, *, expected_input_archive_digest,
                          limits=F.DEFAULT_LIMITS, capture_limits=CF.DEFAULT_LIMITS):
    """Return actual archived claims; no Journal completion or current-use proof."""
    _store(store, limits, capture_limits)
    return _read_completion(store, completion_archive_digest, expected_input_archive_digest, limits, capture_limits)


def _clock(clock, previous=None):
    _need(callable(clock), 'CLOCK_INVALID')
    try:
        now = clock()
        _need(type(now) is datetime and now.utcoffset() is not None and 2 <= now.year <= 9998, 'CLOCK_INVALID')
        now = now.astimezone(timezone.utc)
    except GuardGenerationArchiveError:
        raise
    except Exception:
        raise GuardGenerationArchiveError('GENERATION_ARCHIVE_CLOCK_INVALID') from None
    _need(previous is None or now >= previous, 'CLOCK_ROLLBACK')
    return now


def _provider(retained, receipt, journal, guard_store, guard_head, baseline_store, baseline_head):
    _need(type(journal) is Journal and journal.requires_existing is True
          and type(guard_store) is GuardCheckpointStore
          and type(baseline_store) is CheckpointStore and type(receipt) is GuardCommitReceipt,
          'INPUT_INVALID')
    receipt = _receipt(receipt)
    record = retained.record
    return P.CommittedAccountProvider(package=retained.package, receipt=receipt,
        expected_guard_head=record.expected_guard_head, expected_baseline_head=record.expected_baseline_head,
        expected_control_head=record.expected_control_head, journal=journal, guard_store=guard_store,
        guard_head=guard_head, baseline_store=baseline_store, baseline_head=baseline_head)


def _receipt(receipt):
    _need(type(receipt) is GuardCommitReceipt and type(vars(receipt)) is dict
          and len(vars(receipt)) == 6 and all(type(name) is str for name in vars(receipt))
          and set(vars(receipt)) == {entry.name for entry in fields(GuardCommitReceipt)},
          'INPUT_INVALID')
    values = dict(vars(receipt))
    _need(all(_hash(values[name]) for name in ('transaction_id', 'guard_head', 'baseline_head', 'control_head'))
          and type(values['permanently_halted']) is bool and type(values['replayed']) is bool, 'INPUT_INVALID')
    return GuardCommitReceipt(**values)


def _completion_matches(record, retained, inspection, events, now):
    """Only meaningful with the calling path's actual inspected Transaction."""
    receipt = record.receipt
    _need(type(inspection) is P.CommittedGenerationInspection
          and record.input_archive_digest == retained.archive_digest
          and record.input_record_sha256 == retained.record_sha256
          and inspection.transaction_id == receipt.transaction_id
          and inspection.guard_head == receipt.guard_head and inspection.baseline_head == receipt.baseline_head
          and inspection.completion_head == record.completion_head
          and inspection.receipt_control_head == receipt.control_head
          and inspection.package_sha256 == record.package_sha256 == retained.record.package_sha256
          and inspection.input_sha256 == record.input_sha256 == retained.record.input_sha256
          and inspection.evaluated_at == retained.record.evaluated_at
          and inspection.asof == retained.package['interval'].end, 'BINDING_MISMATCH')
    saved = [index for index, row in enumerate(events) if row['row_sha256'] == record.observed_control_head]
    prefixes = [index for index, row in enumerate(events) if row['row_sha256'] == receipt.control_head]
    _need(len(saved) == len(prefixes) == 1 and saved[0] >= prefixes[0]
          and datetime.fromisoformat(events[saved[0]]['utc']) <= record.recorded_at <= now,
          'BINDING_MISMATCH')


def _inspect(provider, journal, now, record=None, retained=None):
    try:
        with journal.transaction() as tx:
            result = P.CommittedAccountProvider.inspect_committed(provider, now=now, transaction=tx)
            if record is not None:
                _completion_matches(record, retained, result, tx.events, now)
            return result
    except GuardGenerationArchiveError:
        raise
    except Exception:
        raise GuardGenerationArchiveError('GENERATION_ARCHIVE_DURABLE_REFUSED') from None


@_boundary
def record_guard_completion(store, input_archive_digest, receipt, *, journal, guard_store, guard_head,
                            baseline_store, baseline_head, clock,
                            limits=F.DEFAULT_LIMITS, capture_limits=CF.DEFAULT_LIMITS):
    _store(store, limits, capture_limits)
    receipt = _receipt(receipt)
    started = _clock(clock)
    retained = _read_input(store, input_archive_digest, limits, capture_limits)
    provider = _provider(retained, receipt, journal, guard_store, guard_head, baseline_store, baseline_head)
    inspected_at = _clock(clock, started)
    observed = _inspect(provider, journal, inspected_at)
    recorded_at = _clock(clock, inspected_at)
    record = F.GuardCompletionRecord(schema_version=1, kind='GUARD_COMPLETION',
        input_archive_digest=retained.archive_digest, input_record_sha256=retained.record_sha256,
        package_sha256=retained.record.package_sha256, input_sha256=retained.record.input_sha256,
        receipt=receipt, completion_head=observed.completion_head,
        observed_control_head=observed.observed_control_head, recorded_at=recorded_at)
    raw = F.completion_bytes(record, limits=limits)
    record = F.parse_completion(raw, limits=limits)
    digest = F.completion_digest(record, limits=limits)
    manifest, archive_digest, payloads = _manifest(store, raw, digest, input_archive_digest, 'completion')
    store.archive_raw(manifest, payloads)  # Journal transaction is already closed.
    final = _read_completion(store, archive_digest, input_archive_digest, limits, capture_limits)
    _need(final.record_sha256 == digest, 'READBACK_MISMATCH')
    final_provider = _provider(final.retained_input, final.record.receipt, journal, guard_store,
                               guard_head, baseline_store, baseline_head)
    checked_at = _clock(clock, recorded_at)
    _inspect(final_provider, journal, checked_at, final.record, final.retained_input)
    _clock(clock, checked_at)  # after the last actual durable read, no claimed lease
    return final
