"""Deterministic content commitments never issue recovery or trading authority."""
from dataclasses import replace
import json
from execution_launch import recovery_artifact as R, research_bundle_format as F, bundle_attestation as A
from tests import launch_bundle_auth as AF


def test_artifact_preserves_exact_signature_bytes_and_deterministic_incident_identity():
    with AF.fixture() as e:
        first = R.build_recovery_artifact(e.document,incident_id='incident-a',limits=e.store.limits)
        second = R.build_recovery_artifact(e.document,incident_id='incident-a',limits=e.store.limits)
        assert first == second
        manifest,raw,payloads = first
        assert F.parse_raw_archive(raw) == manifest and manifest.kind == 'RAW_ARCHIVED'
        assert manifest.parent_bundle_sha256 == e.digest and manifest.expected_candidates is None
        assert payloads['attestation'] == e.document and set(payloads) == {'attestation','record'}
        record = json.loads(payloads['record'])
        assert record['attestation_sha256'] == A.attestation_document_digest(e.document)
        assert record['request_sha256'] == e.request['request_sha256']
        assert record['file_set_sha256'] == e.request['file_set_sha256']
        assert 'verified_at' not in record and 'approved' not in record
        try: payloads['record'] = b'changed'
        except TypeError: pass
        else: raise AssertionError('mutable artifact')
        other,_,_ = R.build_recovery_artifact(e.document,incident_id='incident-b',limits=e.store.limits)
        assert F.raw_archive_digest(other) != F.raw_archive_digest(manifest)


def test_artifact_rejects_unbounded_or_path_incident_ids_and_malformed_limits():
    with AF.fixture() as e:
        for value in (None,True,1,'../escape','C:drive','A','a'*65,'a\n'):
            AF.refused(lambda value=value:R.build_recovery_artifact(e.document,incident_id=value,limits=e.store.limits),
                       'BUNDLE_RECOVERY_INCIDENT_INVALID')
        AF.refused(lambda:R.build_recovery_artifact(e.document,incident_id='incident-a',limits=True),
                   'BUNDLE_RECOVERY_LIMITS_INVALID')
        bad = replace(e.store.limits)
        object.__delattr__(bad,'format_limits')
        AF.refused(lambda:R.build_recovery_artifact(e.document,incident_id='incident-a',limits=bad),
                   'BUNDLE_RECOVERY_LIMITS_INVALID')


def test_constructing_artifact_does_not_authenticate_a_signature_or_restore_any_bytes():
    with AF.fixture() as e:
        # This is a well-formed but cryptographically invalid envelope. Archival
        # construction may retain it; actual restoration must reject its signature.
        document = A.parse_attestation_document(e.document)
        bad = A.attestation_document_bytes(document['body'],bytes(64))
        manifest,raw,payloads = R.build_recovery_artifact(bad,incident_id='incident-a',limits=e.store.limits)
        assert payloads['attestation'] == bad and manifest.kind == 'RAW_ARCHIVED'
        assert not hasattr(manifest,'authenticated') and not hasattr(manifest,'execution_ready')
        AF.refused(lambda:A.verify_attestation_signature(bad,public_key_raw=e.signer.key.public_key().public_bytes_raw()))
