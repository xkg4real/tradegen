"""Bounded archival envelopes, never research issuance, approvals or authority.

RAW_ARCHIVED preserves available bytes, including empty or malformed originals.
VERIFIED_UNAPPROVED is a caller-claimed document kind: a codec or store accepting
it does not prove that research was evaluated. The actual consumer must inspect
the full raw archive, source and receipts and invoke the real family evaluator.
Parent links are archival claims, not proof of complete previous attempts.

Original names are bounded metadata, never filesystem paths used by this module.
Only generated logical IDs identify payloads. No files, clocks, keys or network
are accessed. Legacy result/review/signature formats are unchanged.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, fields
from datetime import datetime, timezone
import hashlib
import json
import re
import unicodedata

from execution_launch.evidence_objects import PayloadReference

_HASH = re.compile(r'[0-9a-f]{64}')
_ID = re.compile(r'[A-Za-z][A-Za-z0-9_.:-]{0,95}')
_LOGICAL = re.compile(r'[a-z][a-z0-9_-]{0,63}')
_EMPTY_SHA = hashlib.sha256(b'').hexdigest()
_RAW_DOMAIN = b'tradegen-research-raw-archive/1\x00'
_VERIFIED_DOMAIN = b'tradegen-research-bundle/1\x00'
_ROLES = frozenset({'plan', 'profile', 'registration_commitment', 'capture',
    'incomplete_capture', 'source_receipts', 'program_source', 'capture_source_manifest',
    'source_file', 'prior_research', 'report', 'other_input', 'evaluation_record'})
_STATUSES = frozenset({'COLLECTED', 'MISSING', 'REFUSED', 'CHANGED', 'LIMIT_EXCEEDED', 'NOT_READ'})
_REVISIONS = frozenset({'forward-paper-v1', 'forward-paper-carry-v2'})
_SOURCES = frozenset({'prospective_paper_capture', 'synthetic', 'retrospective_replay'})
_SINGLE_ROLES = frozenset({'plan', 'profile', 'registration_commitment', 'source_receipts',
    'program_source', 'capture_source_manifest', 'prior_research', 'evaluation_record'})
_RESERVED = frozenset({'con', 'prn', 'aux', 'nul', 'conin$', 'conout$'} |
    {prefix + digit for prefix in ('com', 'lpt') for digit in '123456789¹²³'})


class BundleFormatError(ValueError):
    """Fixed diagnostics only; no supplied names, values or OS messages."""


def _need(value, code='BUNDLE_FORMAT_INVALID'):
    if not value:
        raise BundleFormatError(code)


def _hash(value):
    return type(value) is str and _HASH.fullmatch(value) is not None


def _identifier(value):
    return type(value) is str and _ID.fullmatch(value) is not None


def _logical(value):
    return type(value) is str and _LOGICAL.fullmatch(value) is not None


def _name(value, maximum=1024):
    _need(type(value) is str and value and '\x00' not in value)
    try:
        _need(len(value.encode('utf-8')) <= maximum, 'BUNDLE_RESOURCE_LIMIT')
    except UnicodeError:
        raise BundleFormatError('BUNDLE_FORMAT_INVALID') from None


def _stamp(value):
    try:
        _need(type(value) is datetime and value.utcoffset() is not None)
        return value.astimezone(timezone.utc).isoformat(timespec='microseconds')
    except (ValueError, TypeError, OverflowError):
        raise BundleFormatError('BUNDLE_FORMAT_INVALID') from None


def _parse_time(value):
    _need(type(value) is str and len(value) == 32)
    try:
        stamp = datetime.fromisoformat(value)
        _need(_stamp(stamp) == value)
        return stamp
    except (ValueError, TypeError, OverflowError):
        raise BundleFormatError('BUNDLE_FORMAT_INVALID') from None


@dataclass(frozen=True, kw_only=True, slots=True)
class BundleLimits:
    max_manifest_bytes: int = 4 * 1024 * 1024
    max_files: int = 2048
    max_file_bytes: int = 64 * 1024 * 1024
    max_total_bytes: int = 512 * 1024 * 1024
    max_candidates: int = 128
    max_name_bytes: int = 1024

    def __post_init__(self):
        ceilings = (4 * 1024 * 1024, 2048, 64 * 1024 * 1024, 512 * 1024 * 1024, 128, 1024)
        for field, ceiling in zip(fields(type(self)), ceilings):
            value = getattr(self, field.name)
            _need(type(value) is int and 0 < value <= ceiling, 'BUNDLE_LIMITS_INVALID')


DEFAULT_LIMITS = BundleLimits()


def _limits(value):
    _need(type(value) is BundleLimits, 'BUNDLE_LIMITS_INVALID')
    try:
        value.__post_init__()
    except (AttributeError, TypeError):
        raise BundleFormatError('BUNDLE_LIMITS_INVALID') from None
    return value


def _metadata(value):
    _name(value.original_name)
    _need(type(value.role) is str and value.role in _ROLES)
    _need(value.study_id is None or _identifier(value.study_id))
    _need(type(value.required) is bool)
    if value.source_name is not None:
        _need(value.role == 'source_file')
        _name(value.source_name)


@dataclass(frozen=True, kw_only=True, slots=True)
class BundleFile:
    logical_id: str
    original_name: str
    source_name: str | None
    role: str
    study_id: str | None
    required: bool
    byte_count: int
    sha256: str
    payload_ref: PayloadReference | None

    def __post_init__(self):
        _need(_logical(self.logical_id))
        _metadata(self)
        _need(type(self.byte_count) is int and 0 <= self.byte_count)
        _need(self.byte_count <= DEFAULT_LIMITS.max_file_bytes, 'BUNDLE_RESOURCE_LIMIT')
        _need(_hash(self.sha256))
        if self.byte_count == 0:
            _need(self.sha256 == _EMPTY_SHA and self.payload_ref is None)
        else:
            _need(type(self.payload_ref) is PayloadReference)
            try:
                self.payload_ref.__post_init__()
            except (ValueError, TypeError, AttributeError):
                raise BundleFormatError('BUNDLE_FORMAT_INVALID') from None
            _need(self.payload_ref.payload_bytes == self.byte_count
                  and self.payload_ref.payload_sha256 == self.sha256)


@dataclass(frozen=True, kw_only=True, slots=True)
class InputObservation:
    observation_id: str
    original_name: str
    source_name: str | None
    role: str
    study_id: str | None
    required: bool
    status: str
    logical_id: str | None

    def __post_init__(self):
        _need(_logical(self.observation_id))
        _metadata(self)
        _need(type(self.status) is str and self.status in _STATUSES)
        _need(_logical(self.logical_id) if self.status == 'COLLECTED' else self.logical_id is None)


def _ordered(values, cls, attribute, maximum):
    _need(type(values) is tuple)
    _need(len(values) <= maximum, 'BUNDLE_RESOURCE_LIMIT')
    keys = []
    for value in values:
        _need(type(value) is cls)
        value.__post_init__()
        keys.append(getattr(value, attribute))
    _need(keys == sorted(set(keys)))


def _files(manifest, limits):
    _ordered(manifest.files, BundleFile, 'logical_id', limits.max_files)
    total = 0
    for file in manifest.files:
        _name(file.original_name, limits.max_name_bytes)
        if file.source_name is not None:
            _name(file.source_name, limits.max_name_bytes)
        _need(file.byte_count <= limits.max_file_bytes, 'BUNDLE_RESOURCE_LIMIT')
        total += file.byte_count
        _need(file.payload_ref is None or file.payload_ref.policy_sha256 == manifest.object_policy_sha256)
    _need(total <= limits.max_total_bytes, 'BUNDLE_RESOURCE_LIMIT')


def _base(manifest, kind, limits):
    _need(type(manifest.schema_version) is int and manifest.schema_version == 1)
    _need(type(manifest.kind) is str and manifest.kind == kind)
    _need(all(_identifier(value) for value in (manifest.run_id, manifest.revision_id, manifest.attempt_id)))
    _need(manifest.parent_bundle_sha256 is None or _hash(manifest.parent_bundle_sha256))
    _need(_hash(manifest.storage_policy_sha256) and _hash(manifest.object_policy_sha256))
    _files(manifest, limits)


def _expected(values, limits):
    _need(type(values) is tuple)
    _need(len(values) <= limits.max_candidates, 'BUNDLE_RESOURCE_LIMIT')
    _need(all(_identifier(value) for value in values) and values == tuple(sorted(set(values))))


@dataclass(frozen=True, kw_only=True, slots=True)
class RawArchiveManifest:
    schema_version: int
    kind: str
    run_id: str
    revision_id: str
    attempt_id: str
    parent_bundle_sha256: str | None
    storage_policy_sha256: str
    object_policy_sha256: str
    expected_candidates: tuple[str, ...] | None
    inventory_complete: bool
    observed_inputs: tuple[InputObservation, ...]
    files: tuple[BundleFile, ...]

    def __post_init__(self):
        _raw(self, DEFAULT_LIMITS)


def _raw(manifest, limits):
    _need(type(manifest) is RawArchiveManifest)
    _base(manifest, 'RAW_ARCHIVED', limits)
    _need(type(manifest.inventory_complete) is bool)
    if manifest.expected_candidates is not None:
        _expected(manifest.expected_candidates, limits)
    _ordered(manifest.observed_inputs, InputObservation, 'observation_id', limits.max_files)
    lookup, collected = {file.logical_id: file for file in manifest.files}, []
    for row in manifest.observed_inputs:
        _name(row.original_name, limits.max_name_bytes)
        if row.source_name is not None:
            _name(row.source_name, limits.max_name_bytes)
        _need(row.role != 'evaluation_record')
        if row.status == 'COLLECTED':
            _need(row.logical_id in lookup)
            file = lookup[row.logical_id]
            _need(all(getattr(file, name) == getattr(row, name)
                      for name in ('original_name', 'source_name', 'role', 'study_id', 'required')))
            collected.append(row.logical_id)
    _need(len(collected) == len(set(collected)) and set(collected) == set(lookup))


@dataclass(frozen=True, kw_only=True, slots=True)
class CandidateEvidence:
    study_id: str
    protocol_digest: str
    capture_logical_id: str
    result_digest: str

    def __post_init__(self):
        _need(_identifier(self.study_id) and _logical(self.capture_logical_id)
              and _hash(self.protocol_digest) and _hash(self.result_digest))


def _safe_relative(name):
    # This is ambiguity prevention for later audit/export, not a path opener.
    _name(name)
    _need(not any(ord(char) < 32 or ord(char) == 127 for char in name))
    _need('\\' not in name and ':' not in name)
    parts = name.split('/')
    _need(all(part and part not in ('.', '..') and not part.endswith(('.', ' '))
              and part.split('.')[0].casefold() not in _RESERVED
              and not any(char in '<>"|?*' for char in part) for part in parts))


@dataclass(frozen=True, kw_only=True, slots=True)
class VerifiedBundleManifest:
    schema_version: int
    kind: str
    run_id: str
    revision_id: str
    attempt_id: str
    parent_bundle_sha256: str | None
    storage_policy_sha256: str
    object_policy_sha256: str
    input_archive_digest: str
    plan_digest: str
    profile_digest: str
    rules_digest: str
    registry_digest: str
    source_digest: str
    family_digest: str
    receipt_audit_digest: str
    evaluator_revision: str
    source_kind_claim: str
    capture_start: datetime
    capture_end: datetime
    evaluated_at: datetime
    candidates: tuple[CandidateEvidence, ...]
    files: tuple[BundleFile, ...]

    def __post_init__(self):
        _verified(self, DEFAULT_LIMITS)


def _complete_files(files, single_roles):
    """Shared metadata eligibility only; no source validation or result issuance."""
    names, by_role = set(), {}
    for file in files:
        _need(file.role not in ('incomplete_capture', 'other_input'))
        _safe_relative(file.original_name)
        name = file.original_name
        if file.role == 'source_file':
            _need(file.source_name is not None)
            _safe_relative(file.source_name)
            name = file.source_name
        key = file.role, unicodedata.normalize('NFC', name).casefold()
        _need(key not in names)
        names.add(key)
        by_role.setdefault(file.role, []).append(file)
    for role in single_roles:
        rows = by_role.get(role, [])
        _need(len(rows) == 1 and rows[0].required and rows[0].study_id is None and rows[0].byte_count > 0)
    _need(by_role.get('source_file') and all(file.required and file.study_id is None and file.byte_count > 0
                                          for file in by_role['source_file']))
    return by_role


def _verified(manifest, limits):
    _need(type(manifest) is VerifiedBundleManifest)
    _base(manifest, 'VERIFIED_UNAPPROVED', limits)
    _need(all(_hash(getattr(manifest, name)) for name in ('input_archive_digest', 'plan_digest',
        'profile_digest', 'rules_digest', 'registry_digest', 'source_digest', 'family_digest',
        'receipt_audit_digest')))
    _need(type(manifest.evaluator_revision) is str and manifest.evaluator_revision in _REVISIONS)
    _need(type(manifest.source_kind_claim) is str and manifest.source_kind_claim in _SOURCES)
    for instant in (manifest.capture_start, manifest.capture_end, manifest.evaluated_at):
        _stamp(instant)
    _need(manifest.capture_start < manifest.capture_end <= manifest.evaluated_at)
    _ordered(manifest.candidates, CandidateEvidence, 'study_id', limits.max_candidates)
    _need(manifest.candidates)
    by_role = _complete_files(manifest.files, _SINGLE_ROLES)
    captures = {file.logical_id: file for file in by_role.get('capture', [])}
    _need(len(captures) == len(manifest.candidates))
    _need({candidate.capture_logical_id for candidate in manifest.candidates} == set(captures))
    for candidate in manifest.candidates:
        file = captures[candidate.capture_logical_id]
        _need(file.study_id == candidate.study_id and file.required and file.byte_count > 0)


def _plain(value):
    if type(value) is datetime:
        return _stamp(value)
    if type(value) is tuple:
        return [_plain(item) for item in value]
    if type(value) in (BundleFile, InputObservation, CandidateEvidence, PayloadReference,
                       RawArchiveManifest, VerifiedBundleManifest):
        return {field.name: _plain(getattr(value, field.name)) for field in fields(type(value))}
    _need(value is None or type(value) in (str, int, bool))
    return value


def _encode(manifest, validator, limits):
    limits = _limits(limits)
    try:
        validator(manifest, limits)
        raw = json.dumps(_plain(manifest), sort_keys=True, separators=(',', ':'),
                         ensure_ascii=True, allow_nan=False).encode('ascii')
    except BundleFormatError:
        raise
    except (ValueError, TypeError, AttributeError, OverflowError, RecursionError, UnicodeError):
        raise BundleFormatError('BUNDLE_FORMAT_INVALID') from None
    _need(len(raw) <= limits.max_manifest_bytes, 'BUNDLE_RESOURCE_LIMIT')
    return raw


def raw_archive_bytes(manifest, *, limits=DEFAULT_LIMITS):
    return _encode(manifest, _raw, limits)


def verified_bundle_bytes(manifest, *, limits=DEFAULT_LIMITS):
    return _encode(manifest, _verified, limits)


def raw_archive_digest(manifest, *, limits=DEFAULT_LIMITS):
    return hashlib.sha256(_RAW_DOMAIN + raw_archive_bytes(manifest, limits=limits)).hexdigest()


def verified_bundle_digest(manifest, *, limits=DEFAULT_LIMITS):
    return hashlib.sha256(_VERIFIED_DOMAIN + verified_bundle_bytes(manifest, limits=limits)).hexdigest()


def _scan(raw):
    depth, nodes, quoted, escaped = 0, 0, False, False
    for char in raw:
        if quoted:
            if escaped:
                escaped = False
            elif char == 92:
                escaped = True
            elif char == 34:
                quoted = False
        elif char == 34:
            quoted = True
        elif char in (91, 123):
            depth += 1
            nodes += 1
            _need(depth <= 12)
        elif char in (93, 125):
            depth -= 1
            _need(depth >= 0)
        elif char in (44, 58):
            nodes += 1
        _need(nodes <= 200000, 'BUNDLE_RESOURCE_LIMIT')
    _need(depth == 0 and not quoted)


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        _need(key not in result)
        result[key] = value
    return result


def _integer(value):
    _need(len(value) <= 16)
    return int(value)


def _number(value):
    raise BundleFormatError('BUNDLE_FORMAT_INVALID')


def _keys(body, cls):
    _need(type(body) is dict and set(body) == {field.name for field in fields(cls)})


def _file(body):
    _keys(body, BundleFile)
    reference = body['payload_ref']
    if reference is not None:
        _keys(reference, PayloadReference)
        reference = PayloadReference(**reference)
    return BundleFile(**(body | {'payload_ref': reference}))


def _parse(raw, cls, encoder, limits):
    limits = _limits(limits)
    _need(type(raw) is bytes and raw)
    _need(len(raw) <= limits.max_manifest_bytes, 'BUNDLE_RESOURCE_LIMIT')
    _scan(raw)
    try:
        body = json.loads(raw.decode('ascii'), object_pairs_hook=_pairs, parse_int=_integer,
                          parse_float=_number, parse_constant=_number)
        _keys(body, cls)
        _need(type(body['files']) is list)
        _need(len(body['files']) <= limits.max_files, 'BUNDLE_RESOURCE_LIMIT')
        body['files'] = tuple(_file(file) for file in body['files'])
        if cls is RawArchiveManifest:
            _need(type(body['observed_inputs']) is list)
            _need(len(body['observed_inputs']) <= limits.max_files, 'BUNDLE_RESOURCE_LIMIT')
            for item in body['observed_inputs']:
                _keys(item, InputObservation)
            body['observed_inputs'] = tuple(InputObservation(**row) for row in body['observed_inputs'])
            if body['expected_candidates'] is not None:
                _need(type(body['expected_candidates']) is list)
                body['expected_candidates'] = tuple(body['expected_candidates'])
        else:
            _need(type(body['candidates']) is list)
            _need(len(body['candidates']) <= limits.max_candidates, 'BUNDLE_RESOURCE_LIMIT')
            for item in body['candidates']:
                _keys(item, CandidateEvidence)
            body['candidates'] = tuple(CandidateEvidence(**row) for row in body['candidates'])
            for name in ('capture_start', 'capture_end', 'evaluated_at'):
                body[name] = _parse_time(body[name])
        manifest = cls(**body)
        _need(encoder(manifest, limits=limits) == raw)
        return manifest
    except BundleFormatError:
        raise
    except (ValueError, TypeError, AttributeError, OverflowError, UnicodeError, RecursionError, KeyError):
        raise BundleFormatError('BUNDLE_FORMAT_INVALID') from None


def parse_raw_archive(raw: bytes, *, limits=DEFAULT_LIMITS):
    return _parse(raw, RawArchiveManifest, raw_archive_bytes, limits)


def parse_verified_bundle(raw: bytes, *, limits=DEFAULT_LIMITS):
    return _parse(raw, VerifiedBundleManifest, verified_bundle_bytes, limits)


def validate_complete_inputs(raw_archive, *, limits=DEFAULT_LIMITS):
    """Preflight every original's metadata before actual evaluation.

    This pure check proves neither source authenticity nor semantic validity.
    It does not construct result digests or a candidate evaluation document.
    Malformed/incomplete originals remain representable by the raw codec.
    """
    raw_archive_bytes(raw_archive, limits=limits)
    _need(raw_archive.inventory_complete and raw_archive.expected_candidates
          and all(row.status == 'COLLECTED' for row in raw_archive.observed_inputs),
          'BUNDLE_INPUT_ARCHIVE_INCOMPLETE')
    roles = _complete_files(raw_archive.files, _SINGLE_ROLES - {'evaluation_record'})
    captures = roles.get('capture', [])
    _need(len(captures) == len(raw_archive.expected_candidates)
          and {file.study_id for file in captures} == set(raw_archive.expected_candidates),
          'BUNDLE_CANDIDATE_SET_MISMATCH')
    _need(all(file.required and file.byte_count > 0 for file in captures))


def validate_verified_inputs(raw_archive, verified, *, limits=DEFAULT_LIMITS):
    """Check exact archival linkage only; never issue research or approval."""
    raw_archive_bytes(raw_archive, limits=limits)
    verified_bundle_bytes(verified, limits=limits)
    _need(raw_archive_digest(raw_archive, limits=limits) == verified.input_archive_digest,
          'BUNDLE_INPUT_ARCHIVE_MISMATCH')
    _need(all(getattr(raw_archive, name) == getattr(verified, name)
              for name in ('run_id', 'attempt_id', 'storage_policy_sha256', 'object_policy_sha256'))
          and raw_archive.revision_id != verified.revision_id, 'BUNDLE_INPUT_ARCHIVE_MISMATCH')
    _need(raw_archive.inventory_complete and raw_archive.expected_candidates
          and all(row.status == 'COLLECTED' for row in raw_archive.observed_inputs),
          'BUNDLE_INPUT_ARCHIVE_INCOMPLETE')
    _need(raw_archive.expected_candidates == tuple(row.study_id for row in verified.candidates),
          'BUNDLE_CANDIDATE_SET_MISMATCH')
    originals = {file.logical_id: file for file in raw_archive.files}
    derived = {file.logical_id: file for file in verified.files}
    _need(set(originals) <= set(derived), 'BUNDLE_INPUT_FILE_MISMATCH')
    for name, file in originals.items():
        _need(_plain(file) == _plain(derived[name]), 'BUNDLE_INPUT_FILE_MISMATCH')
    _need(all(file.role in ('evaluation_record', 'report')
              for name, file in derived.items() if name not in originals), 'BUNDLE_INPUT_FILE_MISMATCH')
    _need({file.study_id for file in raw_archive.files if file.role == 'capture'}
          == set(raw_archive.expected_candidates), 'BUNDLE_CANDIDATE_SET_MISMATCH')


def validate_payloads(manifest, payloads: Mapping[str, bytes], *, limits=DEFAULT_LIMITS):
    """Check original bytes; object availability and semantic truth are separate."""
    if type(manifest) is RawArchiveManifest:
        raw_archive_bytes(manifest, limits=limits)
    else:
        verified_bundle_bytes(manifest, limits=limits)
    _need(isinstance(payloads, Mapping), 'BUNDLE_PAYLOAD_MISMATCH')
    expected = {file.logical_id: file for file in manifest.files}
    _need(len(payloads) == len(expected), 'BUNDLE_PAYLOAD_MISMATCH')
    seen = set()
    for name, raw in payloads.items():
        _need(type(name) is str and name in expected and name not in seen and type(raw) is bytes,
              'BUNDLE_PAYLOAD_MISMATCH')
        seen.add(name)
        file = expected[name]
        _need(len(raw) == file.byte_count and hashlib.sha256(raw).hexdigest() == file.sha256,
              'BUNDLE_PAYLOAD_MISMATCH')
    _need(seen == set(expected), 'BUNDLE_PAYLOAD_MISMATCH')
