"""Pure passkey contracts; no application imports, authority or service."""
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone
import json
from unittest.mock import patch

from tools.approval_broker import contract as C

NOW = datetime(2026, 11, 13, 12, tzinfo=timezone.utc)


def enrollment():
    return C.EnrollmentRequest(authority_id="a" * 64, enrollment_id="b" * 64, grant_sha256=None,
        registry_epoch=0, rp=C.RelyingParty(rp_id="approve.test", origin="https://approve.test"),
        user_handle=b"u" * 32, nonce=b"n" * 32, requested_at=NOW, expires_at=NOW + timedelta(seconds=300))


def proof():
    return C.ProofRequest(authority_id="a" * 64, request_id="c" * 64, grant_sha256=None,
        registry_epoch=0, target=C.ProofTarget(credential_sha256="d" * 64,
        registration_evidence_sha256="e" * 64), nonce=b"p" * 32, requested_at=NOW,
        expires_at=NOW + timedelta(seconds=300))


def refused(call, code=None):
    try:
        call()
    except C.PasskeyError as exc:
        assert str(exc).startswith("PASSKEY_")
        if code is not None:
            assert str(exc) == code, (str(exc), code)
    else:
        raise AssertionError("expected fixed passkey refusal")


def test_enrollment_and_proof_wire_roundtrip_and_domains_are_distinct():
    e, p = enrollment(), proof()
    assert C.parse_enrollment(C.enrollment_bytes(e)) == e
    assert C.parse_proof_request(C.proof_request_bytes(p)) == p
    assert len(e.challenge) == len(p.challenge) == 32 and e.challenge != p.challenge
    assert e.digest != p.digest != C.digest("display", p.display())
    assert p.document()["kind"] == "ENROLL_PROOF" and p.document()["approval_expires_at"] is None


def test_every_target_time_nonce_and_request_change_rebinds_challenge():
    p = proof()
    variants = (replace(p, request_id="f" * 64), replace(p, nonce=b"q" * 32),
        replace(p, target=replace(p.target, credential_sha256="f" * 64)),
        replace(p, target=replace(p.target, registration_evidence_sha256="f" * 64)),
        replace(p, expires_at=p.expires_at - timedelta(seconds=1)))
    assert all(other.challenge != p.challenge and other.digest != p.digest for other in variants)
    document = p.document()
    document["target"]["credential_sha256"] = "f" * 64
    assert p.target.credential_sha256 == "d" * 64
    refused(lambda: C.parse_proof_request(C.encoded(document)))


def test_unknown_fields_bool_integer_changed_derived_digest_and_noncanonical_wire_refuse():
    p = proof().document()
    for body in (p | {"schema": True}, p | {"registry_epoch": False}, p | {"extra": 1},
                 p | {"kind": "ARCHIVE_CONFIRM"}, p | {"display_sha256": "f" * 64},
                 p | {"request_sha256": "f" * 64}, p | {"challenge": C.b64(b"x" * 32)}):
        refused(lambda: C.parse_proof_request(C.encoded(body)))
    raw = C.encoded(p)
    refused(lambda: C.parse_proof_request(b" " + raw))
    refused(lambda: C.parse_proof_request(raw + b"{}"))
    refused(lambda: C.parse_proof_request(raw[:-1] + b',"schema":1}'))


def test_origin_rp_policy_rejects_parent_domain_ip_userinfo_and_nonhttps():
    for rp, origin in (("approve.test", "https://sub.approve.test"),
        ("approve.test", "http://approve.test"), ("approve.test", "https://approve.test/"),
        ("approve.test", "https://user@approve.test"), ("approve.test", "https://approve.test:0"),
        ("127.0.0.1", "https://127.0.0.1"), ("localhost", "https://localhost"),
        ("Approve.test", "https://Approve.test"), ("*.approve.test", "https://approve.test")):
        refused(lambda: C.RelyingParty(rp_id=rp, origin=origin))
    assert C.RelyingParty(rp_id="approve.test", origin="https://approve.test:8443").rp_id == "approve.test"


def test_exact_types_deleted_slots_and_mutation_refuse_on_encode():
    e = enrollment()
    for value in (True, -1, 1.0, "0"):
        refused(lambda: replace(e, registry_epoch=value))
    for value in (bytearray(b"n" * 32), b"n" * 31, b"n" * 33):
        refused(lambda: replace(e, nonce=value))
    broken = enrollment()
    object.__delattr__(broken, "nonce")
    refused(lambda: C.enrollment_bytes(broken))
    try:
        e.nonce = b"x" * 32
    except (FrozenInstanceError, AttributeError):
        pass
    else:
        raise AssertionError("mutable request")


def test_time_boundaries_timezone_roundtrip_and_bootstrap_not_active_grant():
    e = enrollment()
    for end in (NOW, NOW + timedelta(seconds=300, microseconds=1)):
        refused(lambda: replace(e, expires_at=end), "PASSKEY_CLOCK_INVALID")
    refused(lambda: replace(e, requested_at=NOW.replace(tzinfo=None)), "PASSKEY_CLOCK_INVALID")
    refused(lambda: replace(e, registry_epoch=1))
    refused(lambda: replace(e, grant_sha256="f" * 64))
    offset = timezone(timedelta(hours=9))
    same = replace(e, requested_at=e.requested_at.astimezone(offset), expires_at=e.expires_at.astimezone(offset))
    assert C.enrollment_bytes(same) == C.enrollment_bytes(e)
    C.at_time(e.requested_at, e.expires_at, e.expires_at - timedelta(microseconds=1))
    refused(lambda: C.at_time(e.requested_at, e.expires_at, e.expires_at), "PASSKEY_EXPIRED")


def test_preallocation_limits_reject_before_json_loader():
    with patch.object(C.json, "loads", side_effect=AssertionError("admission must run first")):
        refused(lambda: C.decode(b" " * (C.MAX_ENVELOPE_BYTES + 1)))
        refused(lambda: C.decode(b"[" * 13 + b"0" + b"]" * 13), "PASSKEY_RESOURCE_LIMIT")
        refused(lambda: C.decode(b'"' + b"x" * 90001 + b'"'), "PASSKEY_RESOURCE_LIMIT")
        refused(lambda: C.decode(b"[" + b"0," * 4097 + b"0]"), "PASSKEY_RESOURCE_LIMIT")


def test_envelope_roundtrip_preserves_original_raw_bytes_and_null_user_handle():
    raw = b'{ "type" : "unvalidated original" }'
    registration = C.Registration(enrollment_id="a" * 64, credential_id=b"id", client_data_json=raw,
        attestation_object=b"not verified by codec", transports=("hybrid", "internal"))
    assertion = C.Assertion(request_id="b" * 64, credential_id=b"id", client_data_json=raw,
        authenticator_data=b"not verified by codec", signature=b"x", user_handle=None)
    assert C.parse_registration(C.registration_bytes(registration)) == registration
    assert C.parse_assertion(C.assertion_bytes(assertion)) == assertion
    body = assertion.document() | {"client_extensions": {"approved": True}}
    refused(lambda: C.parse_assertion(C.encoded(body)))
    body = registration.document() | {"credential_id": C.b64(b"id") + "="}
    refused(lambda: C.parse_registration(C.encoded(body)))


def test_id_digest_is_not_full_material_binding_and_only_proof_request_has_codec():
    e = enrollment()
    # Deliberately unverified key bytes: these data objects issue no authority.
    a = C.CredentialMaterial(credential_id=b"same-id", public_key_cose=b"key-one", rp=e.rp,
        user_handle=e.user_handle, registration_evidence_sha256="d" * 64,
        backup_eligible=True, backed_up=False, counter=0)
    b = replace(a, public_key_cose=b"key-two")
    assert a.credential_sha256 == b.credential_sha256 and a.material_sha256 != b.material_sha256
    p = replace(proof(), target=C.ProofTarget(credential_sha256=a.credential_sha256,
                                            registration_evidence_sha256=a.registration_evidence_sha256))
    context = C.proof_context(p, a)
    refused(lambda: C.proof_context(p, replace(a, registration_evidence_sha256="f" * 64)), "PASSKEY_TARGET_CHANGED")
    refused(lambda: replace(context, purpose="session.activate"), "PASSKEY_SCOPE_UNSUPPORTED")
    refused(lambda: replace(context, user_handle=b"x" * 32))
