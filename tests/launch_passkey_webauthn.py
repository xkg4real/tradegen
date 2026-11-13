"""Genuine disposable ES256/fido2 checks, never an owner grant or real device."""
from dataclasses import replace
from datetime import timedelta
import hashlib
import json
from types import SimpleNamespace
from unittest.mock import patch

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from fido2 import cbor

from tools.approval_broker import contract as C
from tools.approval_broker import webauthn_verify as V
from tests.launch_passkey_contract import NOW, enrollment, refused


def client(kind, challenge, origin):
    return json.dumps({"type": kind, "challenge": C.b64(challenge), "origin": origin,
                       "crossOrigin": False}, separators=(",", ":")).encode()


def fixture(*, eligible=True, backed=False, counter=0):
    request = enrollment()
    key = ec.generate_private_key(ec.SECP256R1())
    numbers = key.public_key().public_numbers()
    cose = {1: 2, 3: -7, -1: 1, -2: numbers.x.to_bytes(32, "big"), -3: numbers.y.to_bytes(32, "big")}
    identifier = b"disposable-test-credential"
    flags = 0x45 | (8 if eligible else 0) | (16 if backed else 0)
    auth = hashlib.sha256(request.rp.rp_id.encode()).digest() + bytes((flags,)) + counter.to_bytes(4, "big")
    auth += b"\0" * 16 + len(identifier).to_bytes(2, "big") + identifier + cbor.encode(cose)
    response = C.Registration(enrollment_id=request.enrollment_id, credential_id=identifier,
        client_data_json=client("webauthn.create", request.challenge, request.rp.origin),
        attestation_object=cbor.encode({"fmt": "none", "attStmt": {}, "authData": auth}), transports=("internal",))
    registration = V.verify_registration(request, response, now=NOW)
    proof = C.ProofRequest(authority_id=request.authority_id, request_id="c" * 64, grant_sha256=None,
        registry_epoch=0, target=C.ProofTarget(credential_sha256=registration.credential.credential_sha256,
        registration_evidence_sha256=registration.registration_evidence_sha256), nonce=b"p" * 32,
        requested_at=NOW, expires_at=NOW + timedelta(seconds=300))
    return SimpleNamespace(key=key, request=request, response=response, registration=registration,
                           proof=proof, context=C.proof_context(proof, registration.credential), cose=cose)


def assertion(e, *, flags=None, counter=None, raw_client=None, auth_data=None, key=None, user_handle=None):
    credential = e.context.credential
    flags = (5 | (8 if credential.backup_eligible else 0)) if flags is None else flags
    counter = credential.counter + 1 if counter is None else counter
    raw_client = client("webauthn.get", e.context.challenge, e.context.rp.origin) if raw_client is None else raw_client
    auth_data = (hashlib.sha256(e.context.rp.rp_id.encode()).digest() + bytes((flags,))
                 + counter.to_bytes(4, "big")) if auth_data is None else auth_data
    signature = (key or e.key).sign(auth_data + hashlib.sha256(raw_client).digest(), ec.ECDSA(hashes.SHA256()))
    return C.Assertion(request_id=e.context.request_id, credential_id=credential.credential_id,
        client_data_json=raw_client, authenticator_data=auth_data, signature=signature, user_handle=user_handle)


def test_actual_none_registration_then_real_enroll_proof_grants_no_authority():
    e = fixture()
    result = V.verify_assertion(e.context, assertion(e, user_handle=e.context.user_handle), now=NOW)
    assert result.counter == 1 and result.request_sha256 == e.proof.digest
    assert result.credential_sha256 == e.registration.credential.credential_sha256
    assert not result.approval_applied and not result.current_use_eligible
    assert not e.registration.approval_applied and not e.registration.current_use_eligible


def test_pure_reverification_is_not_a_one_time_ledger_or_archive_semantic_validator():
    e = fixture()
    response = assertion(e)
    a = V.verify_assertion(e.context, response, now=NOW)
    b = V.verify_assertion(e.context, response, now=NOW)
    assert a == b and not a.approval_applied
    context = replace(e.context, purpose="ARCHIVE_CONFIRM")
    result = V.verify_assertion(context, response, now=NOW)
    assert not result.current_use_eligible and not result.approval_applied
    assert result.assertion_sha256 != a.assertion_sha256


def test_different_private_key_and_changed_signature_fail_real_library_verification():
    e = fixture()
    other = ec.generate_private_key(ec.SECP256R1())
    refused(lambda: V.verify_assertion(e.context, assertion(e, key=other), now=NOW), "PASSKEY_SIGNATURE_INVALID")
    good = assertion(e)
    bad = replace(good, signature=good.signature[:-1] + bytes((good.signature[-1] ^ 1,)))
    refused(lambda: V.verify_assertion(e.context, bad, now=NOW), "PASSKEY_SIGNATURE_INVALID")


def test_exact_origin_challenge_and_client_type_are_checked_with_valid_signatures():
    e = fixture()
    for body, code in ((client("webauthn.get", e.context.challenge, "https://sub.approve.test"), "PASSKEY_ORIGIN_RP_INVALID"),
        (client("webauthn.get", b"x" * 32, e.context.rp.origin), "PASSKEY_CHALLENGE_INVALID"),
        (client("webauthn.create", e.context.challenge, e.context.rp.origin), "PASSKEY_FORMAT_INVALID")):
        refused(lambda: V.verify_assertion(e.context, assertion(e, raw_client=body), now=NOW), code)


def test_rp_hash_is_verified_by_real_library_not_just_browser_origin():
    e = fixture()
    data = b"x" * 32 + b"\x0d" + (1).to_bytes(4, "big")
    refused(lambda: V.verify_assertion(e.context, assertion(e, auth_data=data), now=NOW), "PASSKEY_SIGNATURE_INVALID")
    body = cbor.decode(e.response.attestation_object)
    body["authData"] = b"x" * 32 + body["authData"][32:]
    response = replace(e.response, attestation_object=cbor.encode(body))
    refused(lambda: V.verify_registration(e.request, response, now=NOW), "PASSKEY_REGISTRATION_INVALID")


def test_uv_up_missing_flags_reserved_flags_and_extensions_refuse():
    e = fixture()
    for flags in (0x09, 0x0c):
        refused(lambda: V.verify_assertion(e.context, assertion(e, flags=flags), now=NOW), "PASSKEY_UV_REQUIRED")
    for flags in (0x0f, 0x2d, 0x4d, 0x8d):
        refused(lambda: V.verify_assertion(e.context, assertion(e, flags=flags), now=NOW))
    good = assertion(e)
    refused(lambda: V.verify_assertion(e.context, assertion(e, auth_data=good.authenticator_data + b"\0"), now=NOW))


def test_user_handle_credential_id_and_request_id_mismatch_refuse():
    e = fixture(); good = assertion(e)
    refused(lambda: V.verify_assertion(e.context, replace(good, user_handle=b"wrong"), now=NOW), "PASSKEY_USER_HANDLE_INVALID")
    for changes in ({"credential_id": b"other"}, {"request_id": "f" * 64}):
        refused(lambda: V.verify_assertion(e.context, replace(good, **changes), now=NOW), "PASSKEY_TARGET_CHANGED")
    assert V.verify_assertion(e.context, good, now=NOW).counter == 1


def test_counter_rules_preserve_synced_zero_nonmonotone_and_device_bound_protection():
    for old, new, anomaly in ((0, 0, False), (5, 0, True), (5, 5, True), (5, 4, True), (5, 6, False)):
        e = fixture(eligible=True, counter=old)
        result = V.verify_assertion(e.context, assertion(e, counter=new), now=NOW)
        assert result.counter == new and result.counter_anomaly is anomaly
    for old, new in ((0, 0), (0, 1), (5, 6)):
        e = fixture(eligible=False, counter=old)
        assert not V.verify_assertion(e.context, assertion(e, counter=new), now=NOW).counter_anomaly
    for new in (0, 4, 5):
        e = fixture(eligible=False, counter=5)
        refused(lambda: V.verify_assertion(e.context, assertion(e, counter=new), now=NOW), "PASSKEY_COUNTER_INVALID")


def test_backup_eligibility_cannot_change_and_backed_up_requires_eligible():
    e = fixture(eligible=True)
    refused(lambda: V.verify_assertion(e.context, assertion(e, flags=5), now=NOW), "PASSKEY_BACKUP_FLAGS_CHANGED")
    assert V.verify_assertion(e.context, assertion(e, flags=0x1d), now=NOW).backed_up
    e = fixture(eligible=False)
    refused(lambda: V.verify_assertion(e.context, assertion(e, flags=0x15), now=NOW))
    refused(lambda: V.verify_assertion(e.context, assertion(e, flags=0x0d), now=NOW), "PASSKEY_BACKUP_FLAGS_CHANGED")


def test_duplicate_cross_origin_top_origin_and_trailing_client_json_refuse_before_library():
    e = fixture(); good = assertion(e)
    body = json.loads(good.client_data_json)
    cases = (good.client_data_json[:-1] + b',"origin":"https://approve.test"}',
        good.client_data_json + b"{}", C.encoded(body | {"crossOrigin": True}),
        C.encoded(body | {"crossOrigin": 0}), C.encoded(body | {"topOrigin": "https://approve.test"}))
    with patch.object(V, "_server", side_effect=AssertionError("must fail before library")):
        for raw in cases:
            refused(lambda: V.verify_assertion(e.context, assertion(e, raw_client=raw), now=NOW))


def test_none_attestation_is_strict_and_entire_authdata_cose_is_consumed():
    e = fixture(); body = cbor.decode(e.response.attestation_object)
    variants = (body | {"fmt": "packed"}, body | {"attStmt": {"sig": b"fake"}},
        body | {"authData": body["authData"][:32] + bytes((body["authData"][32] & ~0x40,)) + body["authData"][33:]},
        body | {"authData": body["authData"] + b"\0"})
    with patch.object(V, "_server", side_effect=AssertionError("must fail before library")):
        for variant in variants:
            response = replace(e.response, attestation_object=cbor.encode(variant))
            refused(lambda: V.verify_registration(e.request, response, now=NOW))
        refused(lambda: V.verify_registration(e.request,
            replace(e.response, attestation_object=e.response.attestation_object + b"\0"), now=NOW))


def test_cbor_duplicate_keys_bool_integer_alias_depth_and_oversize_admission():
    e = fixture()
    raw = e.response.attestation_object
    assert raw[0] == 0xa3
    duplicate = b"\xa4" + raw[1:] + cbor.encode("fmt") + cbor.encode("none")
    for bad in (duplicate, b"\xa1\xf4\x01", b"\x9f\x01\xff", b"\xc0\x00", b"\x81" * 9 + b"\x00",
                b"\xb8\x81"):
        with patch.object(V, "_server", side_effect=AssertionError("must fail before library")):
            refused(lambda: V.verify_registration(e.request, replace(e.response, attestation_object=bad), now=NOW))
    broken = replace(e.response)
    object.__setattr__(broken, "attestation_object", b"x" * 65537)
    with patch.object(V, "_server", side_effect=AssertionError("must fail before library")):
        refused(lambda: V.verify_registration(e.request, broken, now=NOW))


def test_cose_unknown_algorithm_extra_key_and_duplicate_integer_key_refuse():
    e = fixture(); body = cbor.decode(e.response.attestation_object)
    prefix = body["authData"][:55 + len(e.response.credential_id)]
    keys = (cbor.encode(e.cose | {3: -8}), cbor.encode(e.cose | {99: 1}),
            b"\xa6" + cbor.encode(e.cose)[1:] + cbor.encode(3) + cbor.encode(-7))
    with patch.object(V, "_server", side_effect=AssertionError("must fail before library")):
        for key in keys:
            bad = replace(e.response, attestation_object=cbor.encode(body | {"authData": prefix + key}))
            refused(lambda: V.verify_registration(e.request, bad, now=NOW))


def test_none_registration_rejects_off_curve_and_field_range_public_keys():
    e = fixture(); body = cbor.decode(e.response.attestation_object)
    prefix = body["authData"][:55 + len(e.response.credential_id)]
    # Both are structurally valid EC2/P-256 keys; real cryptography must reject
    # invalid coordinates even though none attestation carries no signature.
    for coordinates in ((b"\0" * 32, b"\0" * 32), (b"\xff" * 32, b"\xff" * 32)):
        key = e.cose | {-2: coordinates[0], -3: coordinates[1]}
        response = replace(e.response,
            attestation_object=cbor.encode(body | {"authData": prefix + cbor.encode(key)}))
        refused(lambda: V.verify_registration(e.request, response, now=NOW), "PASSKEY_REGISTRATION_INVALID")


def test_expiry_future_and_mutated_context_types_refuse_before_library():
    e = fixture(); response = assertion(e)
    assert V.verify_assertion(e.context, response, now=e.context.expires_at - timedelta(microseconds=1))
    with patch.object(V, "_server", side_effect=AssertionError("must fail before library")):
        for now in (NOW - timedelta(microseconds=1), e.context.expires_at):
            refused(lambda: V.verify_assertion(e.context, response, now=now), "PASSKEY_EXPIRED")
            refused(lambda: V.verify_registration(e.request, e.response, now=now), "PASSKEY_EXPIRED")
        context = replace(e.context)
        object.__setattr__(context, "challenge", bytearray(context.challenge))
        refused(lambda: V.verify_assertion(context, response, now=NOW))


def test_raw_json_whitespace_survives_evidence_and_real_signature_input():
    e = fixture()
    original = client("webauthn.get", e.context.challenge, e.context.rp.origin)
    spaced = json.dumps(json.loads(original), indent=2).encode()
    a, b = assertion(e, raw_client=original), assertion(e, raw_client=spaced)
    va = V.verify_assertion(e.context, a, now=NOW)
    vb = V.verify_assertion(e.context, b, now=NOW)
    assert va.assertion_sha256 != vb.assertion_sha256
    assert C.parse_assertion(C.assertion_bytes(b)).client_data_json == spaced
