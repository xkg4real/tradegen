"""Bounded genuine WebAuthn verification, not an authority or replay ledger.

An attestation of format 'none' has no attestation signature. Registration
returns candidate key material only; a later ENROLL_PROOF assertion establishes
possession of that key. Neither result activates a credential or an approval.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib

from . import contract as C


def _cbor(raw, maximum):
    """Bounded structural admission before the library's CBOR/COSE constructors.

    Only the definite integer/bytes/text/array/map subset is needed by v1 none
    attestation and EC2 keys. No float, tag, boolean, indefinite or trailing item.
    This is a duplicate-safe input parser, not signature verification.
    """
    C.binary(raw, maximum)
    position = count = 0

    def read(depth):
        nonlocal position, count
        count += 1
        C.need(depth <= 8 and count <= 256, "PASSKEY_RESOURCE_LIMIT")
        C.need(position < len(raw))
        initial = raw[position]
        position += 1
        major, additional = initial >> 5, initial & 31
        C.need(major <= 5 and additional <= 27)
        if additional < 24:
            length = additional
        else:
            width = {24: 1, 25: 2, 26: 4, 27: 8}[additional]
            C.need(position + width <= len(raw))
            length = int.from_bytes(raw[position:position + width], "big")
            position += width
        if major in (0, 1):
            C.need(length < 2**63)
            return length if major == 0 else -1-length
        C.need(length <= maximum, "PASSKEY_RESOURCE_LIMIT")
        if major in (2, 3):
            C.need(position + length <= len(raw))
            value = raw[position:position + length]
            position += length
            if major == 2:
                return value
            try:
                return value.decode("utf-8")
            except UnicodeError:
                raise C.PasskeyError("PASSKEY_FORMAT_INVALID") from None
        C.need(length <= 128, "PASSKEY_RESOURCE_LIMIT")
        if major == 4:
            return [read(depth + 1) for _ in range(length)]
        result = {}
        for _ in range(length):
            key = read(depth + 1)
            C.need(type(key) in (int, str) and key not in result)
            result[key] = read(depth + 1)
        return result

    value = read(0)
    C.need(position == len(raw))
    return value


def _cose(raw):
    body = _cbor(raw, 1024)
    C.keys(body, (1, 3, -1, -2, -3))
    C.need(all(type(body[key]) is int for key in (1, 3, -1))
           and (body[1], body[3], body[-1]) == (2, -7, 1), "PASSKEY_ALGORITHM_UNSUPPORTED")
    C.binary(body[-2], 32, minimum=32); C.binary(body[-3], 32, minimum=32)
    return body


def _client(raw, *, kind, rp, challenge):
    body = C.decode(raw, maximum=16384)
    C.need(type(body) is dict and len(body) in (3, 4))
    C.need(set(body) in ({"type", "challenge", "origin"}, {"type", "challenge", "origin", "crossOrigin"}))
    C.need("crossOrigin" not in body or body["crossOrigin"] is False, "PASSKEY_ORIGIN_RP_INVALID")
    C.need(type(body["type"]) is str and body["type"] == kind)
    C.need(type(body["origin"]) is str and body["origin"] == rp.origin, "PASSKEY_ORIGIN_RP_INVALID")
    C.need(C.unb64(body["challenge"], 32, minimum=32) == challenge, "PASSKEY_CHALLENGE_INVALID")


def _auth_data(raw, *, registering):
    C.binary(raw, 16384)
    C.need(len(raw) >= 37)
    flags, counter = raw[32], int.from_bytes(raw[33:37], "big")
    C.need(not flags & 0xA2 and bool(flags & 0x40) is registering)
    C.need(flags & 1 and flags & 4, "PASSKEY_UV_REQUIRED")
    eligible, backed = bool(flags & 8), bool(flags & 16)
    C.need(not backed or eligible)
    if not registering:
        C.need(len(raw) == 37)
        return eligible, backed, counter, None, None
    C.need(len(raw) >= 55)
    size = int.from_bytes(raw[53:55], "big")
    C.need(1 <= size <= 1024 and 55 + size < len(raw))
    identifier, key_bytes = raw[55:55 + size], raw[55 + size:]
    key = _cose(key_bytes)
    return eligible, backed, counter, identifier, key


def _server(rp):
    try:
        from fido2.server import Fido2Server
        from fido2.webauthn import PublicKeyCredentialRpEntity, AttestationConveyancePreference
        return Fido2Server(PublicKeyCredentialRpEntity(id=rp.rp_id, name="TRADEGEN archive confirmation"),
            attestation=AttestationConveyancePreference.NONE, verify_origin=lambda value: value == rp.origin)
    except ImportError:
        raise C.PasskeyError("PASSKEY_LIBRARY_UNAVAILABLE") from None


def _state(challenge):
    from fido2.webauthn import UserVerificationRequirement
    return {"challenge": C.b64(challenge), "user_verification": UserVerificationRequirement.REQUIRED}


@dataclass(frozen=True, slots=True, kw_only=True)
class VerifiedRegistration:
    """Inert candidate material; none attestation is not proof of key possession."""
    credential: C.CredentialMaterial
    request_sha256: str
    registration_evidence_sha256: str

    @property
    def approval_applied(self):
        return False

    @property
    def current_use_eligible(self):
        return False


@dataclass(frozen=True, slots=True, kw_only=True)
class VerifiedAssertion:
    """Signature facts only; constructing/copying this does not grant authority."""
    credential_sha256: str
    request_sha256: str
    assertion_sha256: str
    counter: int
    backup_eligible: bool
    backed_up: bool
    counter_anomaly: bool

    @property
    def approval_applied(self):
        return False

    @property
    def current_use_eligible(self):
        return False


def verify_registration(request, response, *, now):
    C.checked(request, C.EnrollmentRequest); C.checked(response, C.Registration)
    C.at_time(request.requested_at, request.expires_at, now)
    C.need(response.enrollment_id == request.enrollment_id, "PASSKEY_TARGET_CHANGED")
    _client(response.client_data_json, kind="webauthn.create", rp=request.rp, challenge=request.challenge)
    attestation = _cbor(response.attestation_object, 65536)
    C.keys(attestation, ("fmt", "authData", "attStmt"))
    C.need(type(attestation["fmt"]) is str and attestation["fmt"] == "none")
    C.keys(attestation["attStmt"], ())
    eligible, backed, counter, identifier, key = _auth_data(attestation["authData"], registering=True)
    C.need(identifier == response.credential_id, "PASSKEY_TARGET_CHANGED")
    server = _server(request.rp)
    try:
        from fido2 import cbor
        from fido2.cose import CoseKey
        from cryptography.hazmat.primitives.asymmetric import ec
        # CoseKey.parse and none attestation do not check whether the point is
        # on the curve. Let cryptography validate the candidate public key.
        ec.EllipticCurvePublicNumbers(int.from_bytes(key[-2], "big"),
            int.from_bytes(key[-3], "big"), ec.SECP256R1()).public_key()
        CoseKey.parse(key)
        result = server.register_complete(_state(request.challenge), {"id": C.b64(identifier),
            "rawId": C.b64(identifier), "type": "public-key", "clientExtensionResults": {},
            "response": {"clientDataJSON": C.b64(response.client_data_json),
                         "attestationObject": C.b64(response.attestation_object)}})
        C.need(result.credential_data.credential_id == identifier)
        key_bytes = cbor.encode(dict(result.credential_data.public_key))
        C.need(_cose(key_bytes) == key)
    except C.PasskeyError:
        raise
    except (ValueError, TypeError, KeyError, AttributeError, OverflowError, RecursionError):
        raise C.PasskeyError("PASSKEY_REGISTRATION_INVALID") from None
    evidence = C.digest("registration-evidence", {"request": request.document(), "response": response.document()})
    credential = C.CredentialMaterial(credential_id=identifier, public_key_cose=key_bytes, rp=request.rp,
        user_handle=request.user_handle, registration_evidence_sha256=evidence,
        backup_eligible=eligible, backed_up=backed, counter=counter)
    return VerifiedRegistration(credential=credential, request_sha256=request.digest,
                                registration_evidence_sha256=evidence)


def verify_assertion(context, response, *, now):
    C.checked(context, C.AssertionContext); C.checked(response, C.Assertion)
    C.at_time(context.requested_at, context.expires_at, now)
    C.need(response.request_id == context.request_id and response.credential_id == context.credential.credential_id,
           "PASSKEY_TARGET_CHANGED")
    C.need(response.user_handle is None or response.user_handle == context.user_handle, "PASSKEY_USER_HANDLE_INVALID")
    _client(response.client_data_json, kind="webauthn.get", rp=context.rp, challenge=context.challenge)
    eligible, backed, counter, _, _ = _auth_data(response.authenticator_data, registering=False)
    C.need(eligible is context.credential.backup_eligible, "PASSKEY_BACKUP_FLAGS_CHANGED")
    old = context.credential.counter
    anomaly = (counter > 0 or old > 0) and counter <= old
    C.need(eligible or not anomaly, "PASSKEY_COUNTER_INVALID")
    key = _cose(context.credential.public_key_cose)
    server = _server(context.rp)
    try:
        from fido2.cose import CoseKey
        from fido2.webauthn import AttestedCredentialData, Aaguid
        credential = AttestedCredentialData.create(Aaguid.NONE, response.credential_id, CoseKey.parse(key))
        supplied = {"id": C.b64(response.credential_id), "rawId": C.b64(response.credential_id),
            "type": "public-key", "clientExtensionResults": {}, "response": {
                "clientDataJSON": C.b64(response.client_data_json),
                "authenticatorData": C.b64(response.authenticator_data), "signature": C.b64(response.signature),
                "userHandle": None if response.user_handle is None else C.b64(response.user_handle)}}
        result = server.authenticate_complete(_state(context.challenge), (credential,), supplied)
        C.need(result.credential_id == response.credential_id)
    except C.PasskeyError:
        raise
    except (ValueError, TypeError, KeyError, AttributeError, OverflowError, RecursionError):
        raise C.PasskeyError("PASSKEY_SIGNATURE_INVALID") from None
    evidence = C.digest("assertion-evidence", {"request_sha256": context.request_sha256,
        "purpose": context.purpose, "assertion": response.document()})
    return VerifiedAssertion(credential_sha256=context.credential.credential_sha256,
        request_sha256=context.request_sha256, assertion_sha256=evidence, counter=counter,
        backup_eligible=eligible, backed_up=backed, counter_anomaly=anomaly)
