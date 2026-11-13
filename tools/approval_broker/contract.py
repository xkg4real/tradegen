"""Closed passkey data contracts, not credential registration or approval authority.

Only ENROLL_PROOF requests have a complete request/display codec here. An
AssertionContext can describe an archive assertion's expected cryptographic
values, but does not validate archive meaning, a grant, current owner, a service
identity, expiry at a real clock, or one-time challenge consumption.
"""
from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import ipaddress
import json
import re
from urllib.parse import urlsplit

MAX_ENVELOPE_BYTES = 256 * 1024
_HASH = re.compile(r"[0-9a-f]{64}")
_LABEL = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?")
_TRANSPORTS = frozenset(("internal", "hybrid", "usb", "nfc", "ble"))


class PasskeyError(ValueError):
    """Fixed diagnostics only; never raw evidence, private identifiers or paths."""


def need(condition, code="PASSKEY_FORMAT_INVALID"):
    if not condition:
        raise PasskeyError(code)


def hashed(value):
    need(type(value) is str and len(value) == 64 and _HASH.fullmatch(value) is not None)


def binary(value, maximum, *, minimum=1):
    need(type(value) is bytes and minimum <= len(value) <= maximum)


def instant(value):
    try:
        need(type(value) is datetime and value.utcoffset() is not None and 2 <= value.year <= 9998)
        return value.astimezone(timezone.utc)
    except (ValueError, TypeError, AttributeError, OverflowError):
        raise PasskeyError("PASSKEY_CLOCK_INVALID") from None


def stamp(value):
    return instant(value).isoformat(timespec="microseconds")


def time_value(value):
    need(type(value) is str and len(value) == 32)
    try:
        result = datetime.fromisoformat(value)
        need(stamp(result) == value)
        return result
    except (ValueError, TypeError, OverflowError):
        raise PasskeyError("PASSKEY_CLOCK_INVALID") from None


def interval(start, end):
    first, last = instant(start), instant(end)
    need(timedelta(0) < last-first <= timedelta(seconds=300), "PASSKEY_CLOCK_INVALID")


def at_time(start, end, now):
    interval(start, end)
    need(instant(start) <= instant(now) < instant(end), "PASSKEY_EXPIRED")


def b64(value):
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def unb64(value, maximum, *, minimum=1):
    need(type(value) is str and len(value) <= (maximum * 4 + 2) // 3 and "=" not in value)
    try:
        result = base64.b64decode(value + "=" * (-len(value) % 4), altchars=b"-_", validate=True)
    except (ValueError, binascii.Error, UnicodeError):
        raise PasskeyError("PASSKEY_FORMAT_INVALID") from None
    binary(result, maximum, minimum=minimum)
    need(b64(result) == value)
    return result


def encoded(body):
    return json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                      allow_nan=False).encode("ascii")


def digest(kind, body):
    return hashlib.sha256(b"tradegen-passkey-archive/" + kind.encode("ascii") + b"/1\n" + encoded(body)).hexdigest()


def checked(value, cls):
    need(type(value) is cls)
    try:
        value.__post_init__()
    except PasskeyError:
        raise
    except (ValueError, TypeError, AttributeError, OverflowError, RecursionError):
        raise PasskeyError("PASSKEY_FORMAT_INVALID") from None
    return value


def keys(value, expected):
    need(type(value) is dict and len(value) == len(expected) and set(value) == set(expected))


def decode(raw, *, maximum=MAX_ENVELOPE_BYTES):
    binary(raw, maximum)
    # Bound structure before json.loads, including unknown strings and integers.
    depth = nodes = scalar = 0
    quoted = escaped = False
    for char in raw:
        if quoted:
            scalar += 1
            need(scalar <= 90000, "PASSKEY_RESOURCE_LIMIT")
            if escaped:
                escaped = False
            elif char == 92:
                escaped = True
            elif char == 34:
                quoted = False
        elif char == 34:
            quoted, scalar = True, 0
        elif char in (91, 123):
            depth += 1
            nodes += 1
        elif char in (93, 125):
            depth -= 1
        elif char in (44, 58):
            nodes += 1
        need(0 <= depth <= 12 and nodes <= 4096, "PASSKEY_RESOURCE_LIMIT")
    need(not quoted and depth == 0)

    def pairs(items):
        result = {}
        for key, value in items:
            need(key not in result)
            result[key] = value
        return result

    def integer(value):
        need(len(value) <= 19)
        result = int(value)
        need(-(2**63) <= result < 2**63)
        return result

    def invalid(_):
        raise PasskeyError("PASSKEY_FORMAT_INVALID")
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=pairs, parse_int=integer,
                          parse_float=invalid, parse_constant=invalid)
    except PasskeyError:
        raise
    except (ValueError, TypeError, UnicodeError, RecursionError, OverflowError):
        raise PasskeyError("PASSKEY_FORMAT_INVALID") from None


@dataclass(frozen=True, slots=True, kw_only=True)
class RelyingParty:
    rp_id: str
    origin: str

    def __post_init__(self):
        need(type(self.rp_id) is str and 1 <= len(self.rp_id) <= 253
             and self.rp_id != "localhost" and "." in self.rp_id
             and all(_LABEL.fullmatch(label) for label in self.rp_id.split(".")))
        try:
            ipaddress.ip_address(self.rp_id)
        except ValueError:
            pass
        else:
            raise PasskeyError("PASSKEY_ORIGIN_RP_INVALID")
        need(type(self.origin) is str and len(self.origin) <= 255)
        try:
            url = urlsplit(self.origin)
            port = url.port
            expected = "https://" + self.rp_id + (":" + str(port) if port is not None else "")
            need(self.origin == expected and url.hostname == self.rp_id and not url.username
                 and not url.password and (port is None or 1 <= port <= 65535), "PASSKEY_ORIGIN_RP_INVALID")
        except (ValueError, TypeError):
            raise PasskeyError("PASSKEY_ORIGIN_RP_INVALID") from None


def rp_document(rp):
    checked(rp, RelyingParty)
    return {"rp_id": rp.rp_id, "origin": rp.origin}


def _grant(grant, epoch):
    need(type(epoch) is int and 0 <= epoch < 2**63)
    if grant is None:
        need(epoch == 0)
    else:
        hashed(grant)
        need(epoch >= 1)


@dataclass(frozen=True, slots=True, kw_only=True)
class EnrollmentRequest:
    authority_id: str
    enrollment_id: str
    grant_sha256: str | None
    registry_epoch: int
    rp: RelyingParty
    user_handle: bytes
    nonce: bytes
    requested_at: datetime
    expires_at: datetime

    def __post_init__(self):
        hashed(self.authority_id); hashed(self.enrollment_id)
        _grant(self.grant_sha256, self.registry_epoch)
        checked(self.rp, RelyingParty)
        binary(self.user_handle, 32, minimum=32); binary(self.nonce, 32, minimum=32)
        interval(self.requested_at, self.expires_at)

    def _core(self):
        checked(self, EnrollmentRequest)
        return {"schema": 1, "authority_id": self.authority_id, "enrollment_id": self.enrollment_id,
            "grant_sha256": self.grant_sha256, "registry_epoch": self.registry_epoch,
            **rp_document(self.rp), "user_handle": b64(self.user_handle), "nonce": b64(self.nonce),
            "requested_at": stamp(self.requested_at), "expires_at": stamp(self.expires_at)}

    @property
    def digest(self):
        return digest("enrollment", self._core())

    @property
    def challenge(self):
        return hashlib.sha256(b"tradegen-passkey-archive/enrollment-challenge/1\n" + self.nonce
                              + bytes.fromhex(self.digest)).digest()

    def document(self):
        return self._core() | {"enrollment_sha256": self.digest, "challenge": b64(self.challenge)}


@dataclass(frozen=True, slots=True, kw_only=True)
class ProofTarget:
    credential_sha256: str
    registration_evidence_sha256: str

    def __post_init__(self):
        hashed(self.credential_sha256); hashed(self.registration_evidence_sha256)

    def document(self):
        checked(self, ProofTarget)
        return {"credential_sha256": self.credential_sha256,
                "registration_evidence_sha256": self.registration_evidence_sha256}


@dataclass(frozen=True, slots=True, kw_only=True)
class ProofRequest:
    authority_id: str
    request_id: str
    grant_sha256: str | None
    registry_epoch: int
    target: ProofTarget
    nonce: bytes
    requested_at: datetime
    expires_at: datetime

    def __post_init__(self):
        hashed(self.authority_id); hashed(self.request_id)
        _grant(self.grant_sha256, self.registry_epoch)
        checked(self.target, ProofTarget)
        binary(self.nonce, 32, minimum=32)
        interval(self.requested_at, self.expires_at)

    def display(self):
        checked(self, ProofRequest)
        return {"schema": 1, "authority_id": self.authority_id, "kind": "ENROLL_PROOF",
            "target": self.target.document(), "requested_at": stamp(self.requested_at),
            "challenge_expires_at": stamp(self.expires_at), "approval_expires_at": None}

    def _core(self):
        return self.display() | {"request_id": self.request_id, "grant_sha256": self.grant_sha256,
            "registry_epoch": self.registry_epoch, "nonce": b64(self.nonce),
            "display_sha256": digest("display", self.display())}

    @property
    def digest(self):
        return digest("request", self._core())

    @property
    def challenge(self):
        return hashlib.sha256(b"tradegen-passkey-archive/challenge/1\n" + self.nonce
                              + bytes.fromhex(self.digest)).digest()

    def document(self):
        return self._core() | {"request_sha256": self.digest, "challenge": b64(self.challenge)}


@dataclass(frozen=True, slots=True, kw_only=True)
class Registration:
    enrollment_id: str
    credential_id: bytes
    client_data_json: bytes
    attestation_object: bytes
    transports: tuple[str, ...] = ()

    def __post_init__(self):
        hashed(self.enrollment_id)
        binary(self.credential_id, 1024); binary(self.client_data_json, 16384)
        binary(self.attestation_object, 65536)
        need(type(self.transports) is tuple and len(self.transports) <= 5
             and all(type(item) is str and item in _TRANSPORTS for item in self.transports)
             and self.transports == tuple(sorted(set(self.transports))))

    def document(self):
        checked(self, Registration)
        return {"schema": 1, "enrollment_id": self.enrollment_id, "credential_id": b64(self.credential_id),
            "client_data_json": b64(self.client_data_json), "attestation_object": b64(self.attestation_object),
            "client_extensions": {}, "transports": list(self.transports)}


@dataclass(frozen=True, slots=True, kw_only=True)
class Assertion:
    request_id: str
    credential_id: bytes
    client_data_json: bytes
    authenticator_data: bytes
    signature: bytes
    user_handle: bytes | None

    def __post_init__(self):
        hashed(self.request_id)
        binary(self.credential_id, 1024); binary(self.client_data_json, 16384)
        binary(self.authenticator_data, 16384); binary(self.signature, 512)
        if self.user_handle is not None:
            binary(self.user_handle, 64)

    def document(self):
        checked(self, Assertion)
        return {"schema": 1, "request_id": self.request_id, "credential_id": b64(self.credential_id),
            "client_data_json": b64(self.client_data_json), "authenticator_data": b64(self.authenticator_data),
            "signature": b64(self.signature), "user_handle": None if self.user_handle is None else b64(self.user_handle),
            "client_extensions": {}}


@dataclass(frozen=True, slots=True, kw_only=True)
class CredentialMaterial:
    credential_id: bytes
    public_key_cose: bytes
    rp: RelyingParty
    user_handle: bytes
    registration_evidence_sha256: str
    backup_eligible: bool
    backed_up: bool
    counter: int

    def __post_init__(self):
        binary(self.credential_id, 1024); binary(self.public_key_cose, 1024)
        checked(self.rp, RelyingParty); binary(self.user_handle, 32, minimum=32)
        hashed(self.registration_evidence_sha256)
        need(type(self.backup_eligible) is bool and type(self.backed_up) is bool
             and (not self.backed_up or self.backup_eligible)
             and type(self.counter) is int and 0 <= self.counter < 2**32)

    @property
    def credential_sha256(self):
        checked(self, CredentialMaterial)
        return hashlib.sha256(self.credential_id).hexdigest()

    @property
    def material_sha256(self):
        checked(self, CredentialMaterial)
        return digest("credential-material", {"credential_id": b64(self.credential_id),
            "public_key_cose": b64(self.public_key_cose), **rp_document(self.rp),
            "user_handle": b64(self.user_handle), "registration_evidence_sha256": self.registration_evidence_sha256,
            "backup_eligible": self.backup_eligible, "backed_up": self.backed_up, "counter": self.counter})


@dataclass(frozen=True, slots=True, kw_only=True)
class AssertionContext:
    purpose: str
    request_id: str
    request_sha256: str
    rp: RelyingParty
    challenge: bytes
    user_handle: bytes
    credential: CredentialMaterial
    requested_at: datetime
    expires_at: datetime

    def __post_init__(self):
        need(type(self.purpose) is str and self.purpose in ("ENROLL_PROOF", "ARCHIVE_CONFIRM"),
             "PASSKEY_SCOPE_UNSUPPORTED")
        hashed(self.request_id); hashed(self.request_sha256)
        checked(self.rp, RelyingParty); checked(self.credential, CredentialMaterial)
        binary(self.challenge, 32, minimum=32); binary(self.user_handle, 32, minimum=32)
        need(self.credential.rp == self.rp and self.credential.user_handle == self.user_handle)
        interval(self.requested_at, self.expires_at)


def proof_context(request, credential):
    checked(request, ProofRequest); checked(credential, CredentialMaterial)
    need(request.target.credential_sha256 == credential.credential_sha256
         and request.target.registration_evidence_sha256 == credential.registration_evidence_sha256,
         "PASSKEY_TARGET_CHANGED")
    return AssertionContext(purpose="ENROLL_PROOF", request_id=request.request_id, request_sha256=request.digest,
        rp=credential.rp, challenge=request.challenge, user_handle=credential.user_handle, credential=credential,
        requested_at=request.requested_at, expires_at=request.expires_at)


def enrollment_bytes(value):
    return encoded(checked(value, EnrollmentRequest).document())


def proof_request_bytes(value):
    return encoded(checked(value, ProofRequest).document())


def registration_bytes(value):
    return encoded(checked(value, Registration).document())


def assertion_bytes(value):
    return encoded(checked(value, Assertion).document())


def parse_enrollment(raw):
    body = decode(raw)
    keys(body, ("schema", "authority_id", "enrollment_id", "grant_sha256", "registry_epoch", "rp_id", "origin",
                "user_handle", "nonce", "requested_at", "expires_at", "enrollment_sha256", "challenge"))
    result = EnrollmentRequest(authority_id=body["authority_id"], enrollment_id=body["enrollment_id"],
        grant_sha256=body["grant_sha256"], registry_epoch=body["registry_epoch"],
        rp=RelyingParty(rp_id=body["rp_id"], origin=body["origin"]), user_handle=unb64(body["user_handle"], 32, minimum=32),
        nonce=unb64(body["nonce"], 32, minimum=32), requested_at=time_value(body["requested_at"]),
        expires_at=time_value(body["expires_at"]))
    need(enrollment_bytes(result) == raw)
    return result


def parse_proof_request(raw):
    body = decode(raw)
    keys(body, ("schema", "authority_id", "kind", "target", "requested_at", "challenge_expires_at",
        "approval_expires_at", "request_id", "grant_sha256", "registry_epoch", "nonce", "display_sha256",
        "request_sha256", "challenge"))
    keys(body["target"], ("credential_sha256", "registration_evidence_sha256"))
    result = ProofRequest(authority_id=body["authority_id"], request_id=body["request_id"],
        grant_sha256=body["grant_sha256"], registry_epoch=body["registry_epoch"], target=ProofTarget(**body["target"]),
        nonce=unb64(body["nonce"], 32, minimum=32), requested_at=time_value(body["requested_at"]),
        expires_at=time_value(body["challenge_expires_at"]))
    need(proof_request_bytes(result) == raw)
    return result


def parse_registration(raw):
    body = decode(raw)
    keys(body, ("schema", "enrollment_id", "credential_id", "client_data_json", "attestation_object",
                "client_extensions", "transports"))
    keys(body["client_extensions"], ())
    need(type(body["transports"]) is list and len(body["transports"]) <= 5)
    result = Registration(enrollment_id=body["enrollment_id"], credential_id=unb64(body["credential_id"], 1024),
        client_data_json=unb64(body["client_data_json"], 16384),
        attestation_object=unb64(body["attestation_object"], 65536), transports=tuple(body["transports"]))
    need(registration_bytes(result) == raw)
    return result


def parse_assertion(raw):
    body = decode(raw)
    keys(body, ("schema", "request_id", "credential_id", "client_data_json", "authenticator_data", "signature",
                "user_handle", "client_extensions"))
    keys(body["client_extensions"], ())
    result = Assertion(request_id=body["request_id"], credential_id=unb64(body["credential_id"], 1024),
        client_data_json=unb64(body["client_data_json"], 16384), authenticator_data=unb64(body["authenticator_data"], 16384),
        signature=unb64(body["signature"], 512), user_handle=None if body["user_handle"] is None
        else unb64(body["user_handle"], 64))
    need(assertion_bytes(result) == raw)
    return result
