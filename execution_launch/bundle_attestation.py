"""Archive-only requests and detached signatures, never operational authority.

This pure codec binds both exact B1a manifests and the whole logical file set.
RAW_ARCHIVED can describe missing, incomplete or malformed original evidence;
attestation never upgrades it to evaluated research. Even a mathematically valid
signature proves neither a trusted owner key nor provenance, current approval,
selection, activation or exact recovery eligibility. Actual consumers must read
the graph and fresh owner/code authority. Revocation is not implemented here.

No file, clock, key loading, signer, owner-state or network access. The existing
Ed25519 domains, B1a bytes and WebAuthn mechanisms are not reinterpreted.
"""
from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timedelta, timezone
import base64
import hashlib
import json
import re

from execution_launch import research_bundle_format as F

PURPOSE = 'research_archive_manifest_attestation'
SCOPE = 'archive_manifest_identity'
REQUEST_DOMAIN = b'tradegen-research-archive-attestation-request/1\n'
SIGNING_DOMAIN = b'tradegen-research-archive-attestation/1\n'
FILE_SET_DOMAIN = b'tradegen-research-archive-file-set/1\n'
DOCUMENT_DOMAIN = b'tradegen-research-archive-attestation-document/1\n'
MAX_REQUEST_BYTES = 12 * 1024 * 1024
MAX_DOCUMENT_BYTES = 13 * 1024 * 1024
MAX_VALIDITY_SECONDS = 86400
APPROVED_CHECKS = (
    'exact_manifest_and_entire_file_inventory',
    'all_available_original_bytes_match',
    'raw_and_verified_link_exact',
    'raw_incomplete_and_failure_statuses_visible',
    'archive_only_scope_and_expiry_reviewed',
)
_HASH = re.compile(r'[0-9a-f]{64}')
_LOGICAL = re.compile(r'[a-z][a-z0-9_-]{0,63}')
_EMPTY_SHA = hashlib.sha256(b'').hexdigest()
_REQUEST_KEYS = frozenset({'schema_version', 'artifact_kind', 'purpose', 'scope',
    'requested_at', 'expires_at', 'deployment_code_hash', 'bundle_kind', 'bundle_digest',
    'input_archive_digest', 'raw_manifest_sha256', 'verified_manifest_sha256', 'raw_manifest',
    'verified_manifest', 'payload_files', 'file_set_sha256', 'request_sha256'})
_BODY_KEYS = frozenset({'schema_version', 'purpose', 'scope', 'request', 'deployment_code_hash',
    'owner_fingerprint', 'reviewer_id', 'issued_at', 'expires_at', 'approved_checks'})
_FILE_KEYS = frozenset({'logical_id', 'byte_count', 'sha256'})


class ArchiveAttestationError(ValueError):
    """Fixed codes only, never original data, paths or external error text."""


def _need(value, code='ARCHIVE_ATTESTATION_FORMAT_INVALID'):
    if not value:
        raise ArchiveAttestationError(code)


def _hash(value):
    return type(value) is str and _HASH.fullmatch(value) is not None


def _stamp(value):
    try:
        _need(type(value) is datetime and value.utcoffset() is not None,
              'ARCHIVE_ATTESTATION_TIME_INVALID')
        return value.astimezone(timezone.utc).isoformat(timespec='microseconds')
    except (ValueError, TypeError, OverflowError):
        raise ArchiveAttestationError('ARCHIVE_ATTESTATION_TIME_INVALID') from None


def _time(value):
    _need(type(value) is str and len(value) == 32, 'ARCHIVE_ATTESTATION_TIME_INVALID')
    try:
        instant = datetime.fromisoformat(value)
        _need(_stamp(instant) == value, 'ARCHIVE_ATTESTATION_TIME_INVALID')
        return instant
    except (ValueError, TypeError, OverflowError):
        raise ArchiveAttestationError('ARCHIVE_ATTESTATION_TIME_INVALID') from None


def _fingerprint(value):
    return type(value) is str and value.startswith('SHA256:') and _hash(value[7:])


def _budget(value, maximum):
    # Bound caller-owned dicts before serialization; cycles exceed depth first.
    pending, nodes, characters = [(value, 0)], 0, 0
    while pending:
        item, depth = pending.pop()
        nodes += 1
        _need(nodes <= 500000 and depth <= 16, 'ARCHIVE_ATTESTATION_RESOURCE_LIMIT')
        if type(item) is dict:
            _need(len(item) <= 500000, 'ARCHIVE_ATTESTATION_RESOURCE_LIMIT')
            for key, child in item.items():
                _need(type(key) is str)
                characters += len(key)
                pending.append((child, depth + 1))
        elif type(item) is list:
            _need(len(item) <= 500000, 'ARCHIVE_ATTESTATION_RESOURCE_LIMIT')
            pending.extend((child, depth + 1) for child in item)
        elif type(item) is str:
            characters += len(item)
        elif type(item) is int:
            _need(-(10**15) < item < 10**15)
        else:
            _need(item is None or type(item) is bool)
        _need(characters <= maximum, 'ARCHIVE_ATTESTATION_RESOURCE_LIMIT')


def _canonical(value, maximum):
    _budget(value, maximum)
    try:
        raw = json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True,
                         allow_nan=False).encode('ascii')
    except (ValueError, TypeError, UnicodeError, OverflowError, RecursionError):
        raise ArchiveAttestationError('ARCHIVE_ATTESTATION_FORMAT_INVALID') from None
    _need(len(raw) <= maximum, 'ARCHIVE_ATTESTATION_RESOURCE_LIMIT')
    return raw


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
            _need(depth <= 16, 'ARCHIVE_ATTESTATION_RESOURCE_LIMIT')
        elif char in (93, 125):
            depth -= 1
            _need(depth >= 0)
        elif char in (44, 58):
            nodes += 1
        _need(nodes <= 500000, 'ARCHIVE_ATTESTATION_RESOURCE_LIMIT')
    _need(depth == 0 and not quoted)


def _pairs(pairs):
    body = {}
    for key, value in pairs:
        _need(key not in body)
        body[key] = value
    return body


def _integer(value):
    _need(len(value) <= 16)
    return int(value)


def _number(value):
    raise ArchiveAttestationError('ARCHIVE_ATTESTATION_FORMAT_INVALID')


def _decode(raw, maximum):
    _need(type(raw) is bytes and raw)
    _need(len(raw) <= maximum, 'ARCHIVE_ATTESTATION_RESOURCE_LIMIT')
    _scan(raw)
    try:
        body = json.loads(raw.decode('ascii'), object_pairs_hook=_pairs, parse_int=_integer,
                          parse_float=_number, parse_constant=_number)
    except ArchiveAttestationError:
        raise
    except (ValueError, TypeError, UnicodeError, OverflowError, RecursionError):
        raise ArchiveAttestationError('ARCHIVE_ATTESTATION_FORMAT_INVALID') from None
    _need(_canonical(body, maximum) == raw)
    return body


def _clone(body, maximum):
    return _decode(_canonical(body, maximum), maximum)


def payload_filename(logical_id: str) -> str:
    _need(type(logical_id) is str and _LOGICAL.fullmatch(logical_id) is not None,
          'ARCHIVE_ATTESTATION_FILE_SET_INVALID')
    # A valid logical ID may itself be a Win32 device name (con, nul, com1).
    # Prefix every name so extensions cannot turn it into a device path.
    return 'p-' + logical_id + '.bin'


def file_set_digest(payload_files: list[dict]) -> str:
    _need(type(payload_files) is list, 'ARCHIVE_ATTESTATION_FILE_SET_INVALID')
    _need(len(payload_files) <= 2048, 'ARCHIVE_ATTESTATION_RESOURCE_LIMIT')
    identifiers, total = [], 0
    for row in payload_files:
        _need(type(row) is dict and set(row) == _FILE_KEYS, 'ARCHIVE_ATTESTATION_FILE_SET_INVALID')
        payload_filename(row['logical_id'])
        _need(type(row['byte_count']) is int and 0 <= row['byte_count'] <= 64 * 1024 * 1024
              and _hash(row['sha256']), 'ARCHIVE_ATTESTATION_FILE_SET_INVALID')
        _need(row['byte_count'] != 0 or row['sha256'] == _EMPTY_SHA,
              'ARCHIVE_ATTESTATION_FILE_SET_INVALID')
        identifiers.append(row['logical_id'])
        total += row['byte_count']
    _need(identifiers == sorted(set(identifiers)), 'ARCHIVE_ATTESTATION_FILE_SET_INVALID')
    _need(total <= 512 * 1024 * 1024, 'ARCHIVE_ATTESTATION_RESOURCE_LIMIT')
    return hashlib.sha256(FILE_SET_DOMAIN + _canonical(payload_files, MAX_REQUEST_BYTES)).hexdigest()


def _manifests(raw_body, verified_body):
    try:
        _need(type(raw_body) is dict)
        raw_bytes = _canonical(raw_body, F.DEFAULT_LIMITS.max_manifest_bytes)
        raw = F.parse_raw_archive(raw_bytes)
        verified, verified_bytes = None, None
        if verified_body is not None:
            _need(type(verified_body) is dict)
            verified_bytes = _canonical(verified_body, F.DEFAULT_LIMITS.max_manifest_bytes)
            verified = F.parse_verified_bundle(verified_bytes)
            F.validate_verified_inputs(raw, verified)
        return raw, raw_bytes, verified, verified_bytes
    except F.BundleFormatError as exc:
        code = ('ARCHIVE_ATTESTATION_RESOURCE_LIMIT' if str(exc) == 'BUNDLE_RESOURCE_LIMIT'
                else 'ARCHIVE_ATTESTATION_MANIFEST_INVALID')
        raise ArchiveAttestationError(code) from None


def _request_hash(body):
    unsigned = {key: value for key, value in body.items() if key != 'request_sha256'}
    return hashlib.sha256(REQUEST_DOMAIN + _canonical(unsigned, MAX_REQUEST_BYTES)).hexdigest()


def _validate_request(request):
    _need(type(request) is dict and set(request) == _REQUEST_KEYS)
    _need(type(request['schema_version']) is int and request['schema_version'] == 1)
    for key, expected in (('artifact_kind', 'unsigned_research_archive_attestation_request'),
                          ('purpose', PURPOSE), ('scope', SCOPE)):
        _need(type(request[key]) is str and request[key] == expected)
    start, end = _time(request['requested_at']), _time(request['expires_at'])
    _need(start < end and end - start <= timedelta(seconds=MAX_VALIDITY_SECONDS),
          'ARCHIVE_ATTESTATION_VALIDITY_INVALID')
    _need(_hash(request['deployment_code_hash']), 'ARCHIVE_ATTESTATION_CODE_BINDING_INVALID')
    raw, raw_bytes, verified, verified_bytes = _manifests(request['raw_manifest'], request['verified_manifest'])
    target = raw if verified is None else verified
    target_digest = F.raw_archive_digest(raw) if verified is None else F.verified_bundle_digest(verified)
    expected_files = [{'logical_id': file.logical_id, 'byte_count': file.byte_count, 'sha256': file.sha256}
                      for file in target.files]
    _need(type(request['bundle_kind']) is str and request['bundle_kind'] == target.kind
          and request['bundle_digest'] == target_digest
          and request['input_archive_digest'] == F.raw_archive_digest(raw)
          and request['raw_manifest_sha256'] == hashlib.sha256(raw_bytes).hexdigest()
          and request['verified_manifest_sha256'] == (None if verified_bytes is None else
                                                       hashlib.sha256(verified_bytes).hexdigest()),
          'ARCHIVE_ATTESTATION_MANIFEST_BINDING_MISMATCH')
    if verified is not None:
        _need(start >= verified.evaluated_at, 'ARCHIVE_ATTESTATION_VALIDITY_INVALID')
    supplied_digest = file_set_digest(request['payload_files'])
    _need(_canonical(request['payload_files'], MAX_REQUEST_BYTES) == _canonical(expected_files, MAX_REQUEST_BYTES)
          and request['file_set_sha256'] == supplied_digest, 'ARCHIVE_ATTESTATION_FILE_SET_MISMATCH')
    _need(_hash(request['request_sha256']) and request['request_sha256'] == _request_hash(request),
          'ARCHIVE_ATTESTATION_REQUEST_DIGEST_MISMATCH')


def request_from_manifests(raw_manifest: bytes, verified_manifest: bytes | None, *,
                           requested_at: datetime, expires_at: datetime, deployment_code_hash: str) -> dict:
    """Bind explicit canonical originals; no source authenticity or actual evaluation."""
    try:
        raw = F.parse_raw_archive(raw_manifest)
        verified = None if verified_manifest is None else F.parse_verified_bundle(verified_manifest)
        if verified is not None:
            F.validate_verified_inputs(raw, verified)
    except F.BundleFormatError as exc:
        code = ('ARCHIVE_ATTESTATION_RESOURCE_LIMIT' if str(exc) == 'BUNDLE_RESOURCE_LIMIT'
                else 'ARCHIVE_ATTESTATION_MANIFEST_INVALID')
        raise ArchiveAttestationError(code) from None
    target = raw if verified is None else verified
    files = [{'logical_id': file.logical_id, 'byte_count': file.byte_count, 'sha256': file.sha256}
             for file in target.files]
    request = {'schema_version': 1, 'artifact_kind': 'unsigned_research_archive_attestation_request',
        'purpose': PURPOSE, 'scope': SCOPE, 'requested_at': _stamp(requested_at), 'expires_at': _stamp(expires_at),
        'deployment_code_hash': deployment_code_hash, 'bundle_kind': target.kind,
        'bundle_digest': F.raw_archive_digest(raw) if verified is None else F.verified_bundle_digest(verified),
        'input_archive_digest': F.raw_archive_digest(raw),
        'raw_manifest_sha256': hashlib.sha256(raw_manifest).hexdigest(),
        'verified_manifest_sha256': None if verified_manifest is None else hashlib.sha256(verified_manifest).hexdigest(),
        'raw_manifest': _decode(raw_manifest, F.DEFAULT_LIMITS.max_manifest_bytes),
        'verified_manifest': None if verified_manifest is None else _decode(verified_manifest, F.DEFAULT_LIMITS.max_manifest_bytes),
        'payload_files': files, 'file_set_sha256': file_set_digest(files)}
    request['request_sha256'] = _request_hash(request)
    return parse_archive_request(_canonical(request, MAX_REQUEST_BYTES))


def archive_request_bytes(request: dict) -> bytes:
    copied = _clone(request, MAX_REQUEST_BYTES)
    _validate_request(copied)
    return _canonical(copied, MAX_REQUEST_BYTES)


def parse_archive_request(raw: bytes) -> dict:
    request = _decode(raw, MAX_REQUEST_BYTES)
    _validate_request(request)
    return request


def archive_request_digest(request: dict) -> str:
    return parse_archive_request(archive_request_bytes(request))['request_sha256']


def validate_request_payloads(request: dict, payloads: Mapping[str, bytes]) -> None:
    request = parse_archive_request(archive_request_bytes(request))
    _need(isinstance(payloads, Mapping), 'ARCHIVE_ATTESTATION_PAYLOAD_MISMATCH')
    expected = {row['logical_id']: row for row in request['payload_files']}
    _need(len(payloads) == len(expected), 'ARCHIVE_ATTESTATION_PAYLOAD_MISMATCH')
    seen = set()
    for name, raw in payloads.items():
        _need(type(name) is str and name in expected and name not in seen and type(raw) is bytes,
              'ARCHIVE_ATTESTATION_PAYLOAD_MISMATCH')
        row = expected[name]
        _need(len(raw) == row['byte_count'] and hashlib.sha256(raw).hexdigest() == row['sha256'],
              'ARCHIVE_ATTESTATION_PAYLOAD_MISMATCH')
        seen.add(name)
    _need(seen == set(expected), 'ARCHIVE_ATTESTATION_PAYLOAD_MISMATCH')


def _validate_body(body):
    _need(type(body) is dict and set(body) == _BODY_KEYS)
    _need(type(body['schema_version']) is int and body['schema_version'] == 1)
    _need(type(body['purpose']) is str and body['purpose'] == PURPOSE
          and type(body['scope']) is str and body['scope'] == SCOPE)
    _validate_request(body['request'])
    request = body['request']
    _need(_hash(body['deployment_code_hash']) and body['deployment_code_hash'] == request['deployment_code_hash'],
          'ARCHIVE_ATTESTATION_CODE_BINDING_INVALID')
    _need(_fingerprint(body['owner_fingerprint']) and type(body['reviewer_id']) is str
          and body['reviewer_id'] == 'owner:' + body['owner_fingerprint'][7:],
          'ARCHIVE_ATTESTATION_SIGNER_INVALID')
    issued, expires = _time(body['issued_at']), _time(body['expires_at'])
    _need(body['expires_at'] == request['expires_at'] and _time(request['requested_at']) <= issued < expires
          and expires - issued <= timedelta(seconds=MAX_VALIDITY_SECONDS), 'ARCHIVE_ATTESTATION_VALIDITY_INVALID')
    _need(type(body['approved_checks']) is list and body['approved_checks'] == list(APPROVED_CHECKS),
          'ARCHIVE_ATTESTATION_CHECKLIST_INVALID')


def attestation_body(request: dict, *, owner_fingerprint: str, issued_at: datetime) -> dict:
    copied = parse_archive_request(archive_request_bytes(request))
    body = {'schema_version': 1, 'purpose': PURPOSE, 'scope': SCOPE, 'request': copied,
        'deployment_code_hash': copied['deployment_code_hash'], 'owner_fingerprint': owner_fingerprint,
        'reviewer_id': 'owner:' + owner_fingerprint[7:] if type(owner_fingerprint) is str else None,
        'issued_at': _stamp(issued_at), 'expires_at': copied['expires_at'], 'approved_checks': list(APPROVED_CHECKS)}
    _validate_body(body)
    return body


def attestation_signing_bytes(body: dict) -> bytes:
    copied = _clone(body, MAX_DOCUMENT_BYTES)
    _validate_body(copied)
    return SIGNING_DOMAIN + _canonical(copied, MAX_DOCUMENT_BYTES)


def attestation_document_bytes(body: dict, signature: bytes) -> bytes:
    copied = _clone(body, MAX_DOCUMENT_BYTES)
    _validate_body(copied)
    _need(type(signature) is bytes and len(signature) == 64, 'ARCHIVE_ATTESTATION_SIGNATURE_INVALID')
    return _canonical({'body': copied, 'signature_b64': base64.b64encode(signature).decode('ascii')},
                      MAX_DOCUMENT_BYTES)


def parse_attestation_document(raw: bytes) -> dict:
    envelope = _decode(raw, MAX_DOCUMENT_BYTES)
    _need(type(envelope) is dict and set(envelope) == {'body', 'signature_b64'})
    _validate_body(envelope['body'])
    encoded = envelope['signature_b64']
    _need(type(encoded) is str and len(encoded) == 88, 'ARCHIVE_ATTESTATION_SIGNATURE_INVALID')
    try:
        signature = base64.b64decode(encoded, validate=True)
    except (ValueError, TypeError):
        raise ArchiveAttestationError('ARCHIVE_ATTESTATION_SIGNATURE_INVALID') from None
    _need(len(signature) == 64 and base64.b64encode(signature).decode('ascii') == encoded,
          'ARCHIVE_ATTESTATION_SIGNATURE_INVALID')
    return envelope


def attestation_document_digest(raw: bytes) -> str:
    parse_attestation_document(raw)
    return hashlib.sha256(DOCUMENT_DOMAIN + raw).hexdigest()


def verify_attestation_signature(raw: bytes, *, public_key_raw: bytes) -> dict:
    """Verify exact bytes with a supplied key, NOT that key's trust or current use."""
    envelope = parse_attestation_document(raw)
    _need(type(public_key_raw) is bytes and len(public_key_raw) == 32, 'ARCHIVE_ATTESTATION_PUBLIC_KEY_INVALID')
    body = envelope['body']
    _need(body['owner_fingerprint'] == 'SHA256:' + hashlib.sha256(public_key_raw).hexdigest(),
          'ARCHIVE_ATTESTATION_KEY_MISMATCH')
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    try:
        Ed25519PublicKey.from_public_bytes(public_key_raw).verify(
            base64.b64decode(envelope['signature_b64']), attestation_signing_bytes(body))
    except (InvalidSignature, ValueError, TypeError):
        raise ArchiveAttestationError('ARCHIVE_ATTESTATION_SIGNATURE_UNVERIFIED') from None
    return body
