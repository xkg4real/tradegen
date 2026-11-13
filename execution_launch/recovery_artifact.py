"""Deterministic auxiliary archival bytes, not recovery or approval authority.

No files, clock or signer. A record commits content and the declared recovery
method, not when recovery happened. Actual restoration and backup readback must
be performed by bundle_recovery; constructing this artifact proves neither.
"""
from dataclasses import replace
import hashlib
import json
import re
from types import MappingProxyType

from execution_launch import bundle_attestation as A
from execution_launch import research_bundle_format as F
from execution_launch.evidence_objects import preview_payload
from execution_launch.research_bundle_store import BundleStoreLimits

_ID = re.compile(r'[a-z][a-z0-9_-]{0,63}')


class RecoveryArtifactError(ValueError):
    """Fixed diagnostics only."""


def build_recovery_artifact(attestation_bytes, *, incident_id, limits):
    """Return (manifest, exact_manifest_bytes, immutable_original_payloads)."""
    if type(incident_id) is not str or _ID.fullmatch(incident_id) is None:
        raise RecoveryArtifactError('BUNDLE_RECOVERY_INCIDENT_INVALID')
    if type(limits) is not BundleStoreLimits:
        raise RecoveryArtifactError('BUNDLE_RECOVERY_LIMITS_INVALID')
    try:
        limits = replace(limits, format_limits=replace(limits.format_limits),
            object_limits=replace(limits.object_limits), primary_budget=replace(limits.primary_budget),
            backup_budget=replace(limits.backup_budget))
    except (ValueError, TypeError, AttributeError):
        raise RecoveryArtifactError('BUNDLE_RECOVERY_LIMITS_INVALID') from None
    document = A.parse_attestation_document(attestation_bytes)
    request = document['body']['request']
    attestation_digest = A.attestation_document_digest(attestation_bytes)
    record = {'schema_version': 1, 'kind': 'exact-signed-archive-recovery',
        'scope': 'archive_identity_only', 'incident_id': incident_id,
        'bundle_kind': request['bundle_kind'], 'bundle_digest': request['bundle_digest'],
        'input_archive_digest': request['input_archive_digest'],
        'attestation_sha256': attestation_digest, 'request_sha256': request['request_sha256'],
        'file_set_sha256': request['file_set_sha256'], 'storage_policy_sha256': limits.policy_sha256}
    raw_record = json.dumps(record, sort_keys=True, separators=(',', ':'), ensure_ascii=True,
                            allow_nan=False).encode('ascii')
    payloads = {'attestation': attestation_bytes, 'record': raw_record}
    files = tuple(F.BundleFile(logical_id=name,
        original_name='attestation.json' if name == 'attestation' else 'recovery-record.json',
        source_name=None, role='other_input', study_id=None, required=True, byte_count=len(raw),
        sha256=hashlib.sha256(raw).hexdigest(),
        payload_ref=preview_payload(raw, limits=limits.object_limits).reference)
        for name, raw in sorted(payloads.items()))
    observations = tuple(F.InputObservation(observation_id='o-'+file.logical_id,
        original_name=file.original_name, source_name=None, role=file.role, study_id=None,
        required=True, status='COLLECTED', logical_id=file.logical_id) for file in files)
    manifest = F.RawArchiveManifest(schema_version=1, kind='RAW_ARCHIVED',
        run_id='recovery-'+attestation_digest, revision_id='incident-'+incident_id, attempt_id=incident_id,
        parent_bundle_sha256=request['bundle_digest'], storage_policy_sha256=limits.policy_sha256,
        object_policy_sha256=limits.object_limits.policy_sha256, expected_candidates=None,
        inventory_complete=True, observed_inputs=observations, files=files)
    raw_manifest = F.raw_archive_bytes(manifest, limits=limits.format_limits)
    F.validate_payloads(manifest, payloads, limits=limits.format_limits)
    return manifest, raw_manifest, MappingProxyType(payloads)
