"""Closed archive authority records. Data/codec validation never issues authority.

No clock, files, credentials or application imports. Historical crypto replay and
current independent owner/installation checks are separate required consumers.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import hashlib
import json
import re

from . import contract as C

MAX_EVENT_BYTES = 14 * 1024 * 1024
MAX_STATE_BYTES = 64 * 1024 * 1024
MAX_REQUEST_BYTES = 12 * 1024 * 1024
MAX_DOCUMENT_BYTES = 2 * 1024 * 1024
SCOPE = 'archive_manifest_identity'
GRANT_PURPOSE = 'passkey_archive_authority_grant'
DISABLE_PURPOSE = 'passkey_archive_authority_disable'
APPLICATION_PURPOSE = 'passkey_archive_manifest_confirmation'
STATUSES = frozenset(('PENDING', 'APPLIED', 'EXACT_RETRY', 'EXPIRED', 'REJECTED', 'INVALIDATED', 'INDETERMINATE'))
KINDS = frozenset(('ENROLLMENT_OPENED', 'REGISTRATION_RECORDED', 'INITIAL_PROOF_RECORDED',
    'AUTHORITY_INSTALLED', 'REQUEST_OPENED', 'ARCHIVE_APPLIED', 'CREDENTIAL_REVOKED',
    'AUTHORITY_DISABLED', 'REQUEST_CLOSED', 'OWNER_CHECKPOINT_ADVANCED', 'DELIVERY_REPORTED'))
DIGEST_KINDS = frozenset(('config', 'release', 'credential', 'grant-document', 'disable-document',
    'proposal', 'evidence', 'request', 'display', 'application-id', 'notification-id', 'authority-event',
    'ledger-context', 'ledger-genesis', 'packet', 'operator-installation', 'dependency-artifacts'))
_REASON = re.compile(r'[A-Z][A-Z0-9_]{0,95}')


def _text(value, maximum=512, minimum=1):
    C.need(type(value) is str and minimum <= len(value) <= maximum and '\x00' not in value)


def _int(value, maximum=2**63-1, minimum=0):
    C.need(type(value) is int and minimum <= value <= maximum)


def _tuple(value, maximum):
    C.need(type(value) is tuple and len(value) <= maximum, 'PASSKEY_RESOURCE_LIMIT')


def _schema(body, fields):
    C.keys(body, ('schema', *fields))
    C.need(type(body['schema']) is int and body['schema'] == 1)


def _string_size(value, available):
    # Exact ensure_ascii JSON string size, without materializing escaped bytes.
    C.need(len(value) + 2 <= available, 'PASSKEY_RESOURCE_LIMIT')
    size = 2
    for char in value:
        code = ord(char)
        size += (2 if char in ('"', '\\', '\b', '\f', '\n', '\r', '\t')
                 else 6 if code < 32 or 126 < code <= 65535
                 else 12 if code > 65535 else 1)
        C.need(size <= available, 'PASSKEY_RESOURCE_LIMIT')
    return size


def _budget(body, maximum):
    pending, scheduled, size, tokens = [(body, 0)], 1, 0, 0
    while pending:
        value, depth = pending.pop()
        C.need(depth <= 16, 'PASSKEY_RESOURCE_LIMIT')
        if type(value) in (dict, list):
            count = len(value)
            C.need(depth < 16, 'PASSKEY_RESOURCE_LIMIT')
            tokens += 1 + max(0, count - 1) + (count if type(value) is dict else 0)
            C.need(tokens <= 500000, 'PASSKEY_RESOURCE_LIMIT')
            # Charge all work BEFORE growing the traversal stack.
            C.need(scheduled + count <= 500000, 'PASSKEY_RESOURCE_LIMIT')
            scheduled += count
            size += 2 + max(0, count - 1)
            C.need(size <= maximum, 'PASSKEY_RESOURCE_LIMIT')
            if type(value) is dict:
                size += count  # colons
                C.need(size <= maximum, 'PASSKEY_RESOURCE_LIMIT')
                for key, child in value.items():
                    C.need(type(key) is str)
                    size += _string_size(key, maximum - size)
                    pending.append((child, depth + 1))
            else:
                pending.extend((child, depth + 1) for child in value)
        elif type(value) is str:
            size += _string_size(value, maximum - size)
        elif type(value) is int:
            C.need(-(2**63) <= value < 2**63)
            size += len(str(value))
        else:
            C.need(value is None or type(value) is bool)
            size += 4 if value is None or value is True else 5
        C.need(size <= maximum, 'PASSKEY_RESOURCE_LIMIT')


def canonical(body, *, maximum=MAX_EVENT_BYTES):
    _int(maximum, MAX_STATE_BYTES, 1)
    _budget(body, maximum)
    try:
        raw = C.encoded(body)
    except (ValueError, TypeError, UnicodeError, OverflowError, RecursionError):
        raise C.PasskeyError('PASSKEY_FORMAT_INVALID') from None
    C.need(len(raw) <= maximum, 'PASSKEY_RESOURCE_LIMIT')
    return raw


def decode_authority(raw, *, maximum=MAX_EVENT_BYTES):
    _int(maximum, MAX_STATE_BYTES, 1)
    C.binary(raw, maximum)
    depth = nodes = scalar = 0
    quoted = escaped = False
    for char in raw:
        if quoted:
            scalar += 1
            C.need(scalar <= maximum, 'PASSKEY_RESOURCE_LIMIT')
            if escaped: escaped = False
            elif char == 92: escaped = True
            elif char == 34: quoted = False
        elif char == 34: quoted, scalar = True, 0
        elif char in (91, 123): depth += 1; nodes += 1
        elif char in (93, 125): depth -= 1
        elif char in (44, 58): nodes += 1
        C.need(0 <= depth <= 16 and nodes <= 500000, 'PASSKEY_RESOURCE_LIMIT')
    C.need(not quoted and depth == 0)
    def pairs(items):
        result = {}
        for key, value in items:
            C.need(key not in result)
            result[key] = value
        return result
    def integer(value):
        C.need(len(value) <= 20)
        result = int(value); C.need(-(2**63) <= result < 2**63)
        return result
    def invalid(_): raise C.PasskeyError('PASSKEY_FORMAT_INVALID')
    try:
        body = json.loads(raw.decode('ascii'), object_pairs_hook=pairs,
                          parse_int=integer, parse_float=invalid, parse_constant=invalid)
    except C.PasskeyError: raise
    except (ValueError, TypeError, UnicodeError, RecursionError, OverflowError):
        raise C.PasskeyError('PASSKEY_FORMAT_INVALID') from None
    C.need(canonical(body, maximum=maximum) == raw)
    return body


decode = decode_authority


def record_digest(record_type, canonical_bytes):
    C.need(type(record_type) is str and record_type in DIGEST_KINDS)
    C.binary(canonical_bytes, MAX_STATE_BYTES)
    # Callers have already encoded a typed record. This does not issue trust.
    return hashlib.sha256(b'tradegen-passkey-archive/' + record_type.encode('ascii') + b'/1\n' + canonical_bytes).hexdigest()


def _digest(kind, body, maximum=MAX_EVENT_BYTES):
    return record_digest(kind, canonical(body, maximum=maximum))


def _fingerprint(value):
    C.need(type(value) is str and value.startswith('SHA256:'))
    C.hashed(value[7:])


@dataclass(frozen=True, slots=True, kw_only=True, repr=False)
class Head:
    sequence: int
    sha256: str
    def __post_init__(self): _int(self.sequence); C.hashed(self.sha256)


def head_document(value):
    C.checked(value, Head)
    return {'sequence': value.sequence, 'sha256': value.sha256}


def parse_head(body):
    C.keys(body, ('sequence', 'sha256'))
    return Head(**body)


@dataclass(frozen=True, slots=True, kw_only=True, repr=False)
class OwnerCheckpoint:
    fingerprint: str
    code_sha256: str
    owner_head: Head
    observed_at: datetime
    def __post_init__(self):
        _fingerprint(self.fingerprint); C.hashed(self.code_sha256)
        C.checked(self.owner_head, Head); C.need(self.owner_head.sequence > 0)
        C.instant(self.observed_at)


def owner_checkpoint_document(value):
    C.checked(value, OwnerCheckpoint)
    return {'fingerprint': value.fingerprint, 'code_sha256': value.code_sha256,
            'owner_head': head_document(value.owner_head), 'observed_at': C.stamp(value.observed_at)}


def parse_owner_checkpoint(body):
    C.keys(body, ('fingerprint', 'code_sha256', 'owner_head', 'observed_at'))
    return OwnerCheckpoint(fingerprint=body['fingerprint'], code_sha256=body['code_sha256'],
        owner_head=parse_head(body['owner_head']), observed_at=C.time_value(body['observed_at']))


@dataclass(frozen=True, slots=True, kw_only=True, repr=False)
class OwnerLogEvidence:
    public_key_raw: bytes
    log_bytes: bytes
    anchors: tuple[Head, ...]
    observed_at: datetime
    completed_at: datetime
    head: Head
    def __post_init__(self):
        C.binary(self.public_key_raw, 32, minimum=32); C.binary(self.log_bytes, 8*1024*1024)
        C.need(self.log_bytes.count(b'\n') <= 32768, 'PASSKEY_RESOURCE_LIMIT')
        _tuple(self.anchors, 8192)
        for anchor in self.anchors: C.checked(anchor, Head)
        C.need(tuple((h.sequence,h.sha256) for h in self.anchors) == tuple(sorted(set((h.sequence,h.sha256) for h in self.anchors))))
        C.checked(self.head, Head); C.need(self.head.sequence > 0)
        C.need(C.instant(self.observed_at) <= C.instant(self.completed_at))


def owner_evidence_document(value):
    C.checked(value, OwnerLogEvidence)
    return {'public_key_raw': C.b64(value.public_key_raw), 'log_bytes': C.b64(value.log_bytes),
        'anchors': [head_document(h) for h in value.anchors], 'observed_at': C.stamp(value.observed_at),
        'completed_at': C.stamp(value.completed_at), 'head': head_document(value.head)}


def parse_owner_evidence(body):
    C.keys(body, ('public_key_raw','log_bytes','anchors','observed_at','completed_at','head'))
    C.need(type(body['anchors']) is list and len(body['anchors']) <= 8192)
    return OwnerLogEvidence(public_key_raw=C.unb64(body['public_key_raw'],32,minimum=32),
        log_bytes=C.unb64(body['log_bytes'],8*1024*1024), anchors=tuple(parse_head(h) for h in body['anchors']),
        observed_at=C.time_value(body['observed_at']), completed_at=C.time_value(body['completed_at']), head=parse_head(body['head']))


def _relative(value):
    _text(value)
    C.need('\\' not in value and not value.startswith('/') and all(part and part not in ('.','..') for part in value.split('/')))
    C.need(':' not in value)


@dataclass(frozen=True, slots=True, kw_only=True, repr=False)
class FileDigest:
    name: str
    byte_count: int
    sha256: str
    def __post_init__(self): _relative(self.name); _int(self.byte_count); C.hashed(self.sha256)


@dataclass(frozen=True, slots=True, kw_only=True, repr=False)
class DependencyDigest:
    distribution: str
    version: str
    record_sha256: str
    artifact_sha256: str
    def __post_init__(self):
        _text(self.distribution,128); _text(self.version,64)
        C.hashed(self.record_sha256); C.hashed(self.artifact_sha256)


def file_document(f):
    C.checked(f, FileDigest)
    return {'name': f.name, 'byte_count': f.byte_count, 'sha256': f.sha256}


@dataclass(frozen=True, slots=True, kw_only=True, repr=False)
class ReleaseManifest:
    role: str
    python_version: str
    files: tuple[FileDigest, ...]
    dependencies: tuple[DependencyDigest, ...]
    def __post_init__(self):
        C.need(type(self.role) is str and self.role in ('BROKER','RP')); _text(self.python_version,64)
        _tuple(self.files,8192); _tuple(self.dependencies,256)
        for f in self.files: C.checked(f,FileDigest)
        for d in self.dependencies: C.checked(d,DependencyDigest)
        C.need(tuple(f.name for f in self.files) == tuple(sorted(set(f.name for f in self.files))))
        C.need(tuple(d.distribution for d in self.dependencies) == tuple(sorted(set(d.distribution for d in self.dependencies))))
    def core(self):
        C.checked(self,ReleaseManifest)
        return {'schema':1,'role':self.role,'python_version':self.python_version,
            'files':[file_document(f) for f in self.files],
            'dependencies':[{'distribution':d.distribution,'version':d.version,'record_sha256':d.record_sha256,
                'artifact_sha256':d.artifact_sha256} for d in self.dependencies]}
    @property
    def digest(self): return _digest('release',self.core(),MAX_DOCUMENT_BYTES)


_CONFIG_FIELDS = ('authority_id','service_identity','client_identity','pipe_name','authority_root','backup_root','head_root',
    'packet_inbox','app_repo','rp_origin','rp_id','rp_transport_spki_sha256','broker_transport_public_key','broker_mtls_spki_sha256')


@dataclass(frozen=True, slots=True, kw_only=True, repr=False)
class BrokerConfig:
    authority_id: str
    service_identity: str
    client_identity: str
    pipe_name: str
    authority_root: str
    backup_root: str
    head_root: str
    packet_inbox: str
    app_repo: str
    rp_origin: str
    rp_id: str
    rp_transport_spki_sha256: str
    broker_transport_public_key: bytes
    broker_mtls_spki_sha256: str
    def __post_init__(self):
        C.hashed(self.authority_id)
        _text(self.service_identity,256); _text(self.client_identity,256)
        C.need(self.service_identity != self.client_identity)
        _text(self.pipe_name,128)
        for name in ('authority_root','backup_root','head_root','packet_inbox','app_repo'): _text(getattr(self,name),4096)
        C.RelyingParty(rp_id=self.rp_id,origin=self.rp_origin)
        C.hashed(self.rp_transport_spki_sha256); C.hashed(self.broker_mtls_spki_sha256)
        C.binary(self.broker_transport_public_key,32,minimum=32)
    def core(self):
        C.checked(self,BrokerConfig)
        return {'schema':1, **{k:C.b64(getattr(self,k)) if k=='broker_transport_public_key' else getattr(self,k) for k in _CONFIG_FIELDS}}
    @property
    def digest(self): return _digest('config',self.core(),MAX_DOCUMENT_BYTES)


_CREDENTIAL_FIELDS = ('credential_id','credential_sha256','public_key_cose','algorithm','user_handle','rp_id','origin',
    'registration_evidence_sha256','proof_evidence_sha256','created_at','backup_eligible','last_backed_up','last_counter','state','revoked_at')


@dataclass(frozen=True, slots=True, kw_only=True, repr=False)
class Credential:
    credential_id: bytes
    credential_sha256: str
    public_key_cose: bytes
    algorithm: int
    user_handle: bytes
    rp_id: str
    origin: str
    registration_evidence_sha256: str
    proof_evidence_sha256: str
    created_at: datetime
    backup_eligible: bool
    last_backed_up: bool
    last_counter: int
    state: str
    revoked_at: datetime | None
    def __post_init__(self):
        C.binary(self.credential_id,1024); C.hashed(self.credential_sha256)
        C.need(hashlib.sha256(self.credential_id).hexdigest()==self.credential_sha256)
        C.binary(self.public_key_cose,1024); C.need(type(self.algorithm) is int and self.algorithm==-7)
        C.binary(self.user_handle,32,minimum=32); C.RelyingParty(rp_id=self.rp_id,origin=self.origin)
        C.hashed(self.registration_evidence_sha256); C.hashed(self.proof_evidence_sha256)
        C.instant(self.created_at)
        C.need(type(self.backup_eligible) is bool and type(self.last_backed_up) is bool and (not self.last_backed_up or self.backup_eligible))
        _int(self.last_counter,2**32-1)
        C.need(type(self.state) is str and self.state in ('ACTIVE','REVOKED'))
        C.need((self.revoked_at is None)==(self.state=='ACTIVE'))
        if self.revoked_at is not None: C.need(C.instant(self.revoked_at)>=C.instant(self.created_at))
    def material(self):
        C.checked(self,Credential)
        return C.CredentialMaterial(credential_id=self.credential_id,public_key_cose=self.public_key_cose,
            rp=C.RelyingParty(rp_id=self.rp_id,origin=self.origin),user_handle=self.user_handle,
            registration_evidence_sha256=self.registration_evidence_sha256,backup_eligible=self.backup_eligible,
            backed_up=self.last_backed_up,counter=self.last_counter)
    @property
    def digest(self): return record_digest('credential',credential_bytes(self))


def credential_document(value):
    C.checked(value,Credential)
    body={'schema':1}
    for key in _CREDENTIAL_FIELDS:
        item=getattr(value,key)
        if key in ('credential_id','public_key_cose','user_handle'): item=C.b64(item)
        elif key in ('created_at','revoked_at'): item=None if item is None else C.stamp(item)
        body[key]=item
    return body


def config_bytes(v): return canonical(C.checked(v,BrokerConfig).core()|{'config_sha256':v.digest},maximum=MAX_DOCUMENT_BYTES)
def release_bytes(v): return canonical(C.checked(v,ReleaseManifest).core()|{'manifest_sha256':v.digest},maximum=MAX_DOCUMENT_BYTES)
def credential_bytes(v): return canonical(credential_document(v),maximum=MAX_DOCUMENT_BYTES)


def parse_config(raw):
    b=decode(raw,maximum=MAX_DOCUMENT_BYTES); _schema(b,(*_CONFIG_FIELDS,'config_sha256'))
    values={k:b[k] for k in _CONFIG_FIELDS}; values['broker_transport_public_key']=C.unb64(values['broker_transport_public_key'],32,minimum=32)
    v=BrokerConfig(**values); C.need(config_bytes(v)==raw); return v


def parse_release(raw):
    b=decode(raw,maximum=MAX_DOCUMENT_BYTES); _schema(b,('role','python_version','files','dependencies','manifest_sha256'))
    C.need(type(b['files']) is list and len(b['files'])<=8192 and type(b['dependencies']) is list and len(b['dependencies'])<=256)
    for f in b['files']: C.keys(f,('name','byte_count','sha256'))
    for d in b['dependencies']: C.keys(d,('distribution','version','record_sha256','artifact_sha256'))
    v=ReleaseManifest(role=b['role'],python_version=b['python_version'],files=tuple(FileDigest(**f) for f in b['files']),dependencies=tuple(DependencyDigest(**d) for d in b['dependencies']))
    C.need(release_bytes(v)==raw); return v


def parse_credential(raw):
    b=decode(raw,maximum=MAX_DOCUMENT_BYTES); _schema(b,_CREDENTIAL_FIELDS)
    values={k:b[k] for k in _CREDENTIAL_FIELDS}
    for k,n in (('credential_id',1024),('public_key_cose',1024),('user_handle',32)): values[k]=C.unb64(values[k],n)
    values['created_at']=C.time_value(values['created_at'])
    values['revoked_at']=None if values['revoked_at'] is None else C.time_value(values['revoked_at'])
    v=Credential(**values); C.need(credential_bytes(v)==raw); return v


_GRANT_FIELDS = ('purpose','authority_id','grant_epoch','previous_grant_sha256','owner_checkpoint','recovery_fingerprint',
    'config_sha256','broker_release_sha256','rp_release_sha256','approval_scope','lifecycle_actions','initial_credential_sha256','issued_at','expires_at')
_DISABLE_FIELDS = ('purpose','authority_id','grant_sha256','expected_head','reason','issued_at','expires_at')


def grant_body(raw):
    b=decode(raw,maximum=MAX_DOCUMENT_BYTES); _schema(b,_GRANT_FIELDS)
    C.need(b['purpose']==GRANT_PURPOSE and type(b['purpose']) is str and b['approval_scope']==SCOPE)
    for k in ('authority_id','config_sha256','broker_release_sha256','rp_release_sha256','initial_credential_sha256'): C.hashed(b[k])
    _int(b['grant_epoch'],minimum=1)
    if b['previous_grant_sha256'] is not None: C.hashed(b['previous_grant_sha256'])
    C.need((b['grant_epoch']==1)==(b['previous_grant_sha256'] is None))
    owner=parse_owner_checkpoint(b['owner_checkpoint']); _fingerprint(b['recovery_fingerprint'])
    C.need(type(b['lifecycle_actions']) is list and b['lifecycle_actions']==['REGISTER_CREDENTIAL','REVOKE_CREDENTIAL'])
    issued,expires=C.time_value(b['issued_at']),C.time_value(b['expires_at'])
    C.need(owner.observed_at<=issued<expires and expires-issued<=timedelta(days=366))
    return b


def disable_body(raw):
    b=decode(raw,maximum=MAX_DOCUMENT_BYTES); _schema(b,_DISABLE_FIELDS)
    C.need(type(b['purpose']) is str and b['purpose']==DISABLE_PURPOSE)
    C.hashed(b['authority_id']); C.hashed(b['grant_sha256'])
    h=parse_head(b['expected_head']); C.need(h.sequence>0)
    C.need(type(b['reason']) is str and b['reason'] in ('DEVICE_LOST','AUTHORITY_COMPROMISED'))
    C.interval(C.time_value(b['issued_at']),C.time_value(b['expires_at']))
    return b


@dataclass(frozen=True, slots=True, kw_only=True, repr=False)
class GrantDocument:
    body_bytes: bytes
    signature: bytes
    def __post_init__(self): grant_body(self.body_bytes); C.binary(self.signature,64,minimum=64)
    @property
    def body(self): return grant_body(self.body_bytes)
    @property
    def digest(self): return record_digest('grant-document',grant_bytes(self))


@dataclass(frozen=True, slots=True, kw_only=True, repr=False)
class DisableDocument:
    body_bytes: bytes
    signature: bytes
    def __post_init__(self): disable_body(self.body_bytes); C.binary(self.signature,64,minimum=64)
    @property
    def body(self): return disable_body(self.body_bytes)
    @property
    def digest(self): return record_digest('disable-document',disable_bytes(self))


def grant_signing_bytes(body_bytes):
    grant_body(body_bytes)
    return b'tradegen-passkey-archive/authority-grant/1\n'+body_bytes


def disable_signing_bytes(body_bytes):
    disable_body(body_bytes)
    return b'tradegen-passkey-archive/authority-disable/1\n'+body_bytes


def grant_bytes(v):
    C.checked(v,GrantDocument)
    return canonical({'body':v.body,'signature_b64':C.b64(v.signature)},maximum=MAX_DOCUMENT_BYTES)


def disable_bytes(v):
    C.checked(v,DisableDocument)
    return canonical({'body':v.body,'signature_b64':C.b64(v.signature)},maximum=MAX_DOCUMENT_BYTES)


def parse_grant(raw):
    b=decode(raw,maximum=MAX_DOCUMENT_BYTES); C.keys(b,('body','signature_b64'))
    v=GrantDocument(body_bytes=canonical(b['body'],maximum=MAX_DOCUMENT_BYTES),signature=C.unb64(b['signature_b64'],64,minimum=64))
    C.need(grant_bytes(v)==raw); return v


def parse_disable(raw):
    b=decode(raw,maximum=MAX_DOCUMENT_BYTES); C.keys(b,('body','signature_b64'))
    v=DisableDocument(body_bytes=canonical(b['body'],maximum=MAX_DOCUMENT_BYTES),signature=C.unb64(b['signature_b64'],64,minimum=64))
    C.need(disable_bytes(v)==raw); return v


@dataclass(frozen=True, slots=True, kw_only=True, repr=False)
class WebAuthnEvidence:
    request_sha256: str
    assertion: C.Assertion
    received_at: datetime
    def __post_init__(self):
        C.hashed(self.request_sha256); C.checked(self.assertion,C.Assertion); C.instant(self.received_at)
    def core(self):
        C.checked(self,WebAuthnEvidence)
        return {'schema':1,'request_sha256':self.request_sha256,'assertion':self.assertion.document(),'received_at':C.stamp(self.received_at)}
    @property
    def digest(self): return _digest('evidence',self.core(),C.MAX_ENVELOPE_BYTES)


def evidence_bytes(v):
    C.checked(v,WebAuthnEvidence)
    return canonical(v.core()|{'evidence_sha256':v.digest},maximum=C.MAX_ENVELOPE_BYTES)


def parse_evidence(raw):
    b=decode(raw,maximum=C.MAX_ENVELOPE_BYTES); _schema(b,('request_sha256','assertion','received_at','evidence_sha256'))
    v=WebAuthnEvidence(request_sha256=b['request_sha256'],assertion=C.parse_assertion(canonical(b['assertion'],maximum=C.MAX_ENVELOPE_BYTES)),received_at=C.time_value(b['received_at']))
    C.need(evidence_bytes(v)==raw); return v


@dataclass(frozen=True, slots=True, kw_only=True, repr=False)
class BootstrapProposal:
    enrollment: C.EnrollmentRequest
    registration: C.Registration
    registration_received_at: datetime
    proof_request: C.ProofRequest
    proof: WebAuthnEvidence
    initial_credential: Credential
    def __post_init__(self):
        C.checked(self.enrollment,C.EnrollmentRequest); C.checked(self.registration,C.Registration)
        C.instant(self.registration_received_at); C.checked(self.proof_request,C.ProofRequest)
        C.checked(self.proof,WebAuthnEvidence); C.checked(self.initial_credential,Credential)
        C.need(self.enrollment.enrollment_id==self.registration.enrollment_id and self.enrollment.authority_id==self.proof_request.authority_id)
        C.need(self.proof_request.request_id==self.proof.assertion.request_id and self.proof_request.digest==self.proof.request_sha256)
    def core(self):
        C.checked(self,BootstrapProposal)
        return {'schema':1,'enrollment':self.enrollment.document(),'registration':self.registration.document(),
            'registration_received_at':C.stamp(self.registration_received_at),'proof_request':self.proof_request.document(),
            'proof':decode(evidence_bytes(self.proof)),'initial_credential':credential_document(self.initial_credential)}
    @property
    def digest(self): return _digest('proposal',self.core(),MAX_DOCUMENT_BYTES)


def proposal_bytes(v):
    C.checked(v,BootstrapProposal)
    return canonical(v.core()|{'proposal_sha256':v.digest},maximum=MAX_DOCUMENT_BYTES)


def parse_proposal(raw):
    b=decode(raw,maximum=MAX_DOCUMENT_BYTES); _schema(b,('enrollment','registration','registration_received_at','proof_request','proof','initial_credential','proposal_sha256'))
    v=BootstrapProposal(enrollment=C.parse_enrollment(canonical(b['enrollment'])),registration=C.parse_registration(canonical(b['registration'])),
        registration_received_at=C.time_value(b['registration_received_at']),proof_request=C.parse_proof_request(canonical(b['proof_request'])),
        proof=parse_evidence(canonical(b['proof'])),initial_credential=parse_credential(canonical(b['initial_credential'])))
    C.need(proposal_bytes(v)==raw); return v


_REQUEST_FIELDS = ('request_id','authority_id','grant_sha256','registry_epoch','kind','target','display_sha256',
    'requested_at','challenge_expires_at','approval_expires_at','nonce','challenge','request_sha256')


def _archive_request(body):
    # This is the separately reviewed standalone parser, not application code.
    from tools.signer import sign as S
    try:
        return S._ba_parse_archive_request(canonical(body,maximum=MAX_REQUEST_BYTES))
    except (ValueError,TypeError,AttributeError,OverflowError,RecursionError):
        raise C.PasskeyError('PASSKEY_TARGET_CHANGED') from None


def _request_body(raw):
    b=decode(raw,maximum=MAX_REQUEST_BYTES); _schema(b,_REQUEST_FIELDS)
    C.need(type(b['kind']) is str and b['kind'] in ('ENROLL_PROOF','ARCHIVE_CONFIRM','REVOKE_CREDENTIAL'),'PASSKEY_SCOPE_UNSUPPORTED')
    if b['kind']=='ENROLL_PROOF':
        C.parse_proof_request(raw); return b
    for k in ('request_id','authority_id','grant_sha256','display_sha256','request_sha256'): C.hashed(b[k])
    _int(b['registry_epoch'],minimum=1)
    start,end=C.time_value(b['requested_at']),C.time_value(b['challenge_expires_at']); C.interval(start,end)
    nonce=C.unb64(b['nonce'],32,minimum=32); challenge=C.unb64(b['challenge'],32,minimum=32)
    target=b['target']
    if b['kind']=='ARCHIVE_CONFIRM':
        C.keys(target,('scope','archive_request','archive_request_sha256','packet_sha256','approved_checks'))
        C.need(target['scope']==SCOPE and type(target['scope']) is str)
        archive=_archive_request(target['archive_request'])
        C.hashed(target['packet_sha256']); C.need(target['archive_request_sha256']==archive['request_sha256'])
        from tools.signer import sign as S
        C.need(type(target['approved_checks']) is list and target['approved_checks']==list(S._ba_APPROVED_CHECKS))
        expiry=C.time_value(b['approval_expires_at'])
        C.need(start<expiry<=C.time_value(archive['expires_at']) and expiry-start<=timedelta(days=1))
    else:
        C.keys(target,('credential_sha256','reason')); C.hashed(target['credential_sha256'])
        C.need(type(target['reason']) is str and target['reason'] in ('OWNER_WITHDRAWN','DEVICE_LOST','CREDENTIAL_SUSPECTED'))
        C.need(b['approval_expires_at'] is None)
    display={k:b[k] for k in ('schema','authority_id','kind','target','requested_at','challenge_expires_at','approval_expires_at')}
    C.need(b['display_sha256']==_digest('display',display,MAX_REQUEST_BYTES))
    core={k:v for k,v in b.items() if k not in ('request_sha256','challenge')}
    C.need(b['request_sha256']==_digest('request',core,MAX_REQUEST_BYTES))
    C.need(challenge==hashlib.sha256(b'tradegen-passkey-archive/challenge/1\n'+nonce+bytes.fromhex(b['request_sha256'])).digest())
    return b


@dataclass(frozen=True, slots=True, kw_only=True, repr=False)
class RequestRecord:
    raw: bytes
    def __post_init__(self): _request_body(self.raw)
    @property
    def body(self): return _request_body(self.raw)
    @property
    def request_id(self): return self.body['request_id']
    @property
    def request_sha256(self): return self.body['request_sha256']
    @property
    def digest(self): return self.request_sha256
    @property
    def kind(self): return self.body['kind']
    @property
    def challenge(self): return C.unb64(self.body['challenge'],32,minimum=32)
    @property
    def challenge_expires_at(self): return C.time_value(self.body['challenge_expires_at'])
    @property
    def approval_expires_at(self):
        v=self.body['approval_expires_at']; return None if v is None else C.time_value(v)
    @property
    def display_bytes(self):
        b=self.body
        return canonical({k:b[k] for k in ('schema','authority_id','kind','target','requested_at','challenge_expires_at','approval_expires_at')},maximum=MAX_REQUEST_BYTES)


def request_bytes(v): return C.checked(v,RequestRecord).raw
def parse_request(raw): return RequestRecord(raw=raw)


_APPLICATION_FIELDS = ('purpose','application_id','authority_id','grant_sha256','registry_epoch','request_sha256',
    'evidence_sha256','credential_sha256','bundle_digest','input_archive_digest','file_set_sha256','archive_request_sha256',
    'packet_sha256','owner_checkpoint','applied_at','expires_at')


def _application_body(raw):
    b=decode(raw,maximum=MAX_DOCUMENT_BYTES); _schema(b,_APPLICATION_FIELDS)
    C.need(type(b['purpose']) is str and b['purpose']==APPLICATION_PURPOSE)
    for k in _APPLICATION_FIELDS:
        if k not in ('purpose','registry_epoch','owner_checkpoint','applied_at','expires_at'): C.hashed(b[k])
    _int(b['registry_epoch'],minimum=1); owner=parse_owner_checkpoint(b['owner_checkpoint'])
    at,end=C.time_value(b['applied_at']),C.time_value(b['expires_at'])
    C.need(owner.observed_at<=at<end and end-at<=timedelta(days=1))
    C.need(b['application_id']==_digest('application-id',{k:b[k] for k in ('authority_id','request_sha256','evidence_sha256')}))
    return b


@dataclass(frozen=True, slots=True, kw_only=True, repr=False)
class ApplicationRecord:
    raw: bytes
    def __post_init__(self): _application_body(self.raw)
    @property
    def body(self): return _application_body(self.raw)
    @property
    def application_id(self): return self.body['application_id']
    @property
    def credential_sha256(self): return self.body['credential_sha256']
    @property
    def bundle_digest(self): return self.body['bundle_digest']
    @property
    def expires_at(self): return C.time_value(self.body['expires_at'])


def application_bytes(v): return C.checked(v,ApplicationRecord).raw
def parse_application(raw): return ApplicationRecord(raw=raw)


def _notification_body(raw):
    b=decode(raw,maximum=C.MAX_ENVELOPE_BYTES)
    C.keys(b,('intent_id','authority_id','request_id','application_id','kind','status','created_at'))
    C.hashed(b['intent_id']); C.hashed(b['authority_id'])
    for k in ('request_id','application_id'):
        if b[k] is not None: C.hashed(b[k])
    C.need(type(b['kind']) is str and b['kind'] in ('REQUEST_READY','APPLICATION_RESULT','CREDENTIAL_RESULT'))
    C.need(type(b['status']) is str and b['status'] in STATUSES)
    C.time_value(b['created_at'])
    C.need(b['intent_id']==_digest('notification-id',{k:b[k] for k in ('authority_id','request_id','application_id','kind')}))
    return b


@dataclass(frozen=True, slots=True, kw_only=True, repr=False)
class NotificationIntent:
    raw: bytes
    def __post_init__(self): _notification_body(self.raw)
    @property
    def body(self): return _notification_body(self.raw)
    @property
    def intent_id(self): return self.body['intent_id']


def notification_bytes(v): return C.checked(v,NotificationIntent).raw
def parse_notification(raw): return NotificationIntent(raw=raw)


def _reason(value):
    C.need(type(value) is str and len(value) <= 96 and _REASON.fullmatch(value) is not None)


def _delivery(body):
    C.keys(body,('intent_id','attempt_id','outcome','reported_at'))
    C.hashed(body['intent_id']); C.hashed(body['attempt_id'])
    C.need(type(body['outcome']) is str and body['outcome'] in ('SENT','FAILED','UNKNOWN'))
    C.time_value(body['reported_at'])


def _payload(kind, raw):
    C.need(type(kind) is str and kind in KINDS,'PASSKEY_SCOPE_UNSUPPORTED')
    b=decode(raw,maximum=MAX_EVENT_BYTES)
    def parsed(name, parser): return parser(canonical(b[name],maximum=MAX_EVENT_BYTES))
    if kind=='ENROLLMENT_OPENED':
        C.keys(b,('enrollment',)); parsed('enrollment',C.parse_enrollment)
    elif kind=='REGISTRATION_RECORDED':
        C.keys(b,('enrollment_sha256','registration','registration_received_at','registration_evidence_sha256','proof_request'))
        C.hashed(b['enrollment_sha256']); C.hashed(b['registration_evidence_sha256'])
        parsed('registration',C.parse_registration); C.time_value(b['registration_received_at'])
        parsed('proof_request',C.parse_proof_request)
    elif kind=='INITIAL_PROOF_RECORDED':
        C.keys(b,('enrollment_sha256','proof','initial_credential','proposal_sha256'))
        C.hashed(b['enrollment_sha256']); C.hashed(b['proposal_sha256'])
        parsed('proof',parse_evidence); parsed('initial_credential',parse_credential)
    elif kind=='AUTHORITY_INSTALLED':
        C.keys(b,('grant','config_sha256','initial_credential','enrollment_request','registration','proof_request','proof'))
        parsed('grant',parse_grant); C.hashed(b['config_sha256'])
        parsed('initial_credential',parse_credential); parsed('enrollment_request',C.parse_enrollment)
        parsed('registration',C.parse_registration); parsed('proof_request',C.parse_proof_request); parsed('proof',parse_evidence)
    elif kind=='REQUEST_OPENED':
        C.keys(b,('request','notification')); request=parsed('request',parse_request)
        C.need((b['notification'] is None)==(request.kind=='ENROLL_PROOF'))
        if b['notification'] is not None: parsed('notification',parse_notification)
    elif kind=='ARCHIVE_APPLIED':
        C.keys(b,('application','evidence','notification'))
        parsed('application',parse_application); parsed('evidence',parse_evidence); parsed('notification',parse_notification)
    elif kind=='CREDENTIAL_REVOKED':
        C.keys(b,('request_sha256','evidence','credential_sha256','reason','new_registry_epoch','notification'))
        C.hashed(b['request_sha256']); C.hashed(b['credential_sha256']); _int(b['new_registry_epoch'],minimum=2)
        C.need(type(b['reason']) is str and b['reason'] in ('OWNER_WITHDRAWN','DEVICE_LOST','CREDENTIAL_SUSPECTED'))
        parsed('evidence',parse_evidence); parsed('notification',parse_notification)
    elif kind=='AUTHORITY_DISABLED':
        C.keys(b,('disable','notification')); parsed('disable',parse_disable); parsed('notification',parse_notification)
    elif kind=='REQUEST_CLOSED':
        C.keys(b,('request_sha256','state','reason','evidence_sha256','notification'))
        C.hashed(b['request_sha256']); _reason(b['reason'])
        C.need(type(b['state']) is str and b['state'] in ('EXPIRED','REJECTED','INVALIDATED'))
        if b['evidence_sha256'] is not None: C.hashed(b['evidence_sha256'])
        parsed('notification',parse_notification)
    elif kind=='OWNER_CHECKPOINT_ADVANCED':
        C.keys(b,('evidence',)); parse_owner_evidence(b['evidence'])
    else:
        _delivery(b)
    return b


@dataclass(frozen=True, slots=True, kw_only=True, repr=False)
class ProposedEvent:
    kind: str
    observed_at: datetime
    payload_bytes: bytes
    def __post_init__(self):
        C.instant(self.observed_at); _payload(self.kind,self.payload_bytes)


@dataclass(frozen=True, slots=True, kw_only=True, repr=False)
class LedgerEvent:
    sequence: int
    previous_sha256: str
    observed_at: datetime
    kind: str
    payload_bytes: bytes
    row_sha256: str
    def __post_init__(self):
        _int(self.sequence,minimum=1); C.hashed(self.previous_sha256); C.hashed(self.row_sha256)
        C.instant(self.observed_at); _payload(self.kind,self.payload_bytes)
        C.need(self.row_sha256==record_digest('authority-event',canonical(_event_core(self))))


def proposed_payload(value):
    C.need(type(value) in (ProposedEvent,LedgerEvent))
    C.checked(value,type(value))
    return _payload(value.kind,value.payload_bytes)


def _event_core(v):
    return {'schema':1,'sequence':v.sequence,'previous_sha256':v.previous_sha256,
        'observed_at':C.stamp(v.observed_at),'kind':v.kind,'payload':_payload(v.kind,v.payload_bytes)}


def event_bytes(value):
    C.checked(value,LedgerEvent)
    raw=canonical(_event_core(value)|{'row_sha256':value.row_sha256})
    C.need(len(raw)+1<=MAX_EVENT_BYTES,'PASSKEY_RESOURCE_LIMIT')
    return raw


def parse_event(raw):
    C.binary(raw,MAX_EVENT_BYTES-1)
    b=decode(raw); _schema(b,('sequence','previous_sha256','observed_at','kind','payload','row_sha256'))
    v=LedgerEvent(sequence=b['sequence'],previous_sha256=b['previous_sha256'],observed_at=C.time_value(b['observed_at']),
        kind=b['kind'],payload_bytes=canonical(b['payload']),row_sha256=b['row_sha256'])
    C.need(event_bytes(v)==raw); return v


@dataclass(frozen=True, slots=True, kw_only=True, repr=False)
class PendingEnrollment:
    enrollment: C.EnrollmentRequest
    registration: C.Registration | None
    registration_received_at: datetime | None
    proof_request: C.ProofRequest | None
    proof: WebAuthnEvidence | None
    initial_credential: Credential | None
    proposal_sha256: str | None
    def __post_init__(self):
        C.checked(self.enrollment,C.EnrollmentRequest)
        C.need((self.registration is None)==(self.registration_received_at is None)==(self.proof_request is None))
        C.need((self.proof is None)==(self.initial_credential is None)==(self.proposal_sha256 is None))
        if self.registration is None: C.need(self.proof is None)
        else:
            C.checked(self.registration,C.Registration); C.instant(self.registration_received_at)
            C.checked(self.proof_request,C.ProofRequest)
            C.need(self.registration.enrollment_id==self.enrollment.enrollment_id)
        if self.proof is not None:
            C.checked(self.proof,WebAuthnEvidence); C.checked(self.initial_credential,Credential); C.hashed(self.proposal_sha256)


@dataclass(frozen=True, slots=True, kw_only=True, repr=False)
class RequestState:
    request: RequestRecord
    state: str
    evidence_sha256: str | None
    application_id: str | None
    def __post_init__(self):
        C.checked(self.request,RequestRecord)
        C.need(type(self.state) is str and self.state in ('PENDING','APPLIED','EXPIRED','REJECTED','INVALIDATED'))
        if self.evidence_sha256 is not None: C.hashed(self.evidence_sha256)
        if self.application_id is not None: C.hashed(self.application_id)
        if self.state=='PENDING': C.need(self.evidence_sha256 is None and self.application_id is None)
        if self.application_id is not None: C.need(self.state=='APPLIED' and self.evidence_sha256 is not None)


@dataclass(frozen=True, slots=True, kw_only=True, repr=False)
class AuthorityState:
    """Descriptive, bounded projection. Only actual crypto replay can establish it."""
    grant: GrantDocument | None
    registry_epoch: int
    last_trusted_at: datetime | None
    owner_evidence: OwnerLogEvidence | None
    enrollments: tuple[PendingEnrollment,...]
    credentials: tuple[Credential,...]
    requests: tuple[RequestState,...]
    applications: tuple[ApplicationRecord,...]
    notifications: tuple[NotificationIntent,...]
    deliveries: tuple[bytes,...]
    disabled: bool
    events: tuple[LedgerEvent,...]
    def __post_init__(self):
        _int(self.registry_epoch); C.need(type(self.disabled) is bool)
        if self.grant is not None: C.checked(self.grant,GrantDocument)
        C.need((self.grant is None)==(self.registry_epoch==0))
        if self.last_trusted_at is not None: C.instant(self.last_trusted_at)
        if self.owner_evidence is not None: C.checked(self.owner_evidence,OwnerLogEvidence)
        specifications=(('enrollments',PendingEnrollment,256),('credentials',Credential,256),('requests',RequestState,4096),
            ('applications',ApplicationRecord,4096),('notifications',NotificationIntent,8192),('events',LedgerEvent,16384))
        # Admit every outer collection before inspecting any child.
        for name,_,limit in specifications: _tuple(getattr(self,name),limit)
        _tuple(self.deliveries,16384)
        for name,cls,_ in specifications:
            for value in getattr(self,name): C.checked(value,cls)
        for raw in self.deliveries: _delivery(decode(raw,maximum=C.MAX_ENVELOPE_BYTES))
        C.need(sum(v.state=='ACTIVE' for v in self.credentials)<=16,'PASSKEY_RESOURCE_LIMIT')
        C.need(sum(v.state=='PENDING' for v in self.requests)<=128,'PASSKEY_RESOURCE_LIMIT')


def _pending_document(v):
    C.checked(v,PendingEnrollment)
    return {'enrollment':v.enrollment.document(),'registration':None if v.registration is None else v.registration.document(),
        'registration_received_at':None if v.registration_received_at is None else C.stamp(v.registration_received_at),
        'proof_request':None if v.proof_request is None else v.proof_request.document(),
        'proof':None if v.proof is None else decode(evidence_bytes(v.proof)),
        'initial_credential':None if v.initial_credential is None else credential_document(v.initial_credential),
        'proposal_sha256':v.proposal_sha256}


def state_bytes(v):
    C.checked(v,AuthorityState)
    # Admission is checked cumulatively before constructing a combined document.
    pieces={}
    size=1024
    def put(name,rows):
        nonlocal size
        values=[]
        for raw in rows:
            size+=len(raw)+1; C.need(size<=MAX_STATE_BYTES,'PASSKEY_RESOURCE_LIMIT')
            values.append(decode(raw,maximum=MAX_EVENT_BYTES))
        pieces[name]=values
    put('enrollments',(canonical(_pending_document(e),maximum=MAX_DOCUMENT_BYTES) for e in v.enrollments))
    put('credentials',(credential_bytes(e) for e in v.credentials))
    put('requests',(canonical({'request':e.request.body,'state':e.state,'evidence_sha256':e.evidence_sha256,'application_id':e.application_id}) for e in v.requests))
    put('applications',(application_bytes(e) for e in v.applications))
    put('notifications',(notification_bytes(e) for e in v.notifications))
    put('deliveries',iter(v.deliveries)); put('events',(event_bytes(e) for e in v.events))
    body={'schema':1,'grant':None if v.grant is None else decode(grant_bytes(v.grant)),
        'registry_epoch':v.registry_epoch,'last_trusted_at':None if v.last_trusted_at is None else C.stamp(v.last_trusted_at),
        'owner_evidence':None if v.owner_evidence is None else owner_evidence_document(v.owner_evidence),'disabled':v.disabled,**pieces}
    return canonical(body,maximum=MAX_STATE_BYTES)
