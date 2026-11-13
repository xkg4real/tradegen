"""Genuine historical enrollment/proof and root-signature verification only.

There is no private-key parameter or signing operation in this module. A data
builder does not establish current owner, release, grant membership or service
installation. Those are independently checked by the signer and engine.
"""
from __future__ import annotations

from datetime import timedelta
import hashlib
import json

from . import authority_contract as A
from . import contract as C
from . import webauthn_verify as V


def verify_bootstrap(proposal):
    proposal = A.parse_proposal(A.proposal_bytes(proposal))
    enrollment, proof = proposal.enrollment, proposal.proof_request
    C.need(enrollment.grant_sha256 is None and enrollment.registry_epoch == 0
           and proof.grant_sha256 is None and proof.registry_epoch == 0
           and proof.authority_id == enrollment.authority_id, 'PASSKEY_TARGET_CHANGED')
    C.need(enrollment.requested_at <= proposal.registration_received_at <= proof.requested_at
           <= proposal.proof.received_at, 'PASSKEY_CLOCK_ROLLBACK')
    registration = V.verify_registration(enrollment, proposal.registration, now=proposal.registration_received_at)
    context = C.proof_context(proof, registration.credential)
    C.need(proposal.proof.request_sha256 == proof.digest, 'PASSKEY_TARGET_CHANGED')
    verified = V.verify_assertion(context, proposal.proof.assertion, now=proposal.proof.received_at)
    material = registration.credential
    actual = A.Credential(credential_id=material.credential_id,
        credential_sha256=hashlib.sha256(material.credential_id).hexdigest(),
        public_key_cose=material.public_key_cose, algorithm=-7, user_handle=material.user_handle,
        rp_id=material.rp.rp_id, origin=material.rp.origin,
        registration_evidence_sha256=registration.registration_evidence_sha256,
        proof_evidence_sha256=proposal.proof.digest, created_at=proposal.registration_received_at,
        backup_eligible=verified.backup_eligible, last_backed_up=verified.backed_up,
        last_counter=verified.counter, state='ACTIVE', revoked_at=None)
    C.need(A.credential_bytes(actual) == A.credential_bytes(proposal.initial_credential),
           'PASSKEY_TARGET_CHANGED')
    return actual


def build_grant_body(proposal, *, config, broker_release, rp_release, owner,
                     recovery_fingerprint, issued_at, expires_at):
    """Build the original wire, after actual registration/proof re-verification."""
    credential = verify_bootstrap(proposal)
    config_body = json.loads(A.config_bytes(config))
    broker = json.loads(A.release_bytes(broker_release))
    rp = json.loads(A.release_bytes(rp_release))
    C.checked(owner, A.OwnerCheckpoint)
    C.need(broker['role'] == 'BROKER' and rp['role'] == 'RP', 'PASSKEY_RELEASE_INVALID')
    C.need(config.authority_id == proposal.enrollment.authority_id
           and config.rp_id == credential.rp_id and config.rp_origin == credential.origin,
           'PASSKEY_TARGET_CHANGED')
    C.need(type(recovery_fingerprint) is str and recovery_fingerprint.startswith('SHA256:'))
    C.hashed(recovery_fingerprint[7:])
    first, last = C.instant(issued_at), C.instant(expires_at)
    C.need(proposal.proof.received_at <= first and owner.observed_at <= first
           and timedelta(0) < last-first <= timedelta(days=366), 'PASSKEY_CLOCK_INVALID')
    body = {'schema':1,'purpose':'passkey_archive_authority_grant',
        'authority_id':config.authority_id,'grant_epoch':1,'previous_grant_sha256':None,
        'owner_checkpoint':{'fingerprint':owner.fingerprint,'code_sha256':owner.code_sha256,
            'owner_head':{'sequence':owner.owner_head.sequence,'sha256':owner.owner_head.sha256},
            'observed_at':C.stamp(owner.observed_at)},
        'recovery_fingerprint':recovery_fingerprint,'config_sha256':config_body['config_sha256'],
        'broker_release_sha256':broker['manifest_sha256'],'rp_release_sha256':rp['manifest_sha256'],
        'approval_scope':'archive_manifest_identity',
        'lifecycle_actions':['REGISTER_CREDENTIAL','REVOKE_CREDENTIAL'],
        'initial_credential_sha256':A.record_digest('credential',A.credential_bytes(credential)),
        'issued_at':C.stamp(first),'expires_at':C.stamp(last)}
    raw = C.encoded(body)
    A.grant_signing_bytes(raw)  # Strict body admission; no synthetic signature.
    return raw


def _verify(signature, signing_bytes, public):
    C.binary(public,32,minimum=32); C.binary(signature,64,minimum=64)
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    try:
        Ed25519PublicKey.from_public_bytes(public).verify(signature,signing_bytes)
    except (InvalidSignature, ValueError, TypeError):
        raise C.PasskeyError('PASSKEY_SIGNATURE_INVALID') from None


def verify_grant_document(document, *, signer_public_key_raw):
    document = A.parse_grant(A.grant_bytes(document))
    _verify(document.signature,A.grant_signing_bytes(document.body_bytes),signer_public_key_raw)


def verify_disable_document(document, *, recovery_public_key_raw):
    document = A.parse_disable(A.disable_bytes(document))
    _verify(document.signature,A.disable_signing_bytes(document.body_bytes),recovery_public_key_raw)
