"""Closed data contracts and genuine temporary crypto; no installed authority."""
from dataclasses import replace
from datetime import timedelta
import hashlib
from types import SimpleNamespace
from unittest.mock import patch

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from tools.approval_broker import authority_contract as A
from tools.approval_broker import contract as C
from tools.approval_broker import webauthn_verify as V
from tests.launch_passkey_contract import NOW, enrollment, refused
from tests import launch_passkey_webauthn as W


def proposal():
    e=W.fixture()
    response=W.assertion(e,user_handle=e.context.user_handle)
    checked=V.verify_assertion(e.context,response,now=NOW)
    evidence=A.WebAuthnEvidence(request_sha256=e.proof.digest,assertion=response,received_at=NOW)
    m=e.registration.credential
    credential=A.Credential(credential_id=m.credential_id,credential_sha256=m.credential_sha256,
        public_key_cose=m.public_key_cose,algorithm=-7,user_handle=m.user_handle,rp_id=m.rp.rp_id,
        origin=m.rp.origin,registration_evidence_sha256=m.registration_evidence_sha256,
        proof_evidence_sha256=evidence.digest,created_at=NOW,backup_eligible=checked.backup_eligible,
        last_backed_up=checked.backed_up,last_counter=checked.counter,state='ACTIVE',revoked_at=None)
    p=A.BootstrapProposal(enrollment=e.request,registration=e.response,registration_received_at=NOW,
        proof_request=e.proof,proof=evidence,initial_credential=credential)
    return e,p


def grant(p):
    key=Ed25519PrivateKey.generate()
    public=key.public_key().public_bytes_raw()
    owner=A.OwnerCheckpoint(fingerprint='SHA256:'+hashlib.sha256(public).hexdigest(),code_sha256='1'*64,
        owner_head=A.Head(sequence=1,sha256='2'*64),observed_at=NOW)
    body=dict(schema=1,purpose=A.GRANT_PURPOSE,authority_id=p.enrollment.authority_id,grant_epoch=1,
        previous_grant_sha256=None,owner_checkpoint=A.owner_checkpoint_document(owner),
        recovery_fingerprint='SHA256:'+'3'*64,config_sha256='4'*64,broker_release_sha256='5'*64,
        rp_release_sha256='6'*64,approval_scope=A.SCOPE,lifecycle_actions=['REGISTER_CREDENTIAL','REVOKE_CREDENTIAL'],
        initial_credential_sha256=p.initial_credential.digest,issued_at=C.stamp(NOW),
        expires_at=C.stamp(NOW+timedelta(days=1)))
    raw=A.canonical(body)
    return key,A.GrantDocument(body_bytes=raw,signature=key.sign(A.grant_signing_bytes(raw)))


def notification(*,request_id='b'*64,status='PENDING'):
    identity=dict(authority_id='a'*64,request_id=request_id,application_id=None,kind='REQUEST_READY')
    return A.parse_notification(A.canonical(identity|dict(intent_id=A.record_digest('notification-id',A.canonical(identity)),
        status=status,created_at=C.stamp(NOW))))


def request(kind='REVOKE_CREDENTIAL',target=None):
    if target is None: target=dict(credential_sha256='c'*64,reason='OWNER_WITHDRAWN')
    display=dict(schema=1,authority_id='a'*64,kind=kind,target=target,requested_at=C.stamp(NOW),
        challenge_expires_at=C.stamp(NOW+timedelta(seconds=300)),approval_expires_at=None)
    if kind=='ARCHIVE_CONFIRM': display['approval_expires_at']=C.stamp(NOW+timedelta(hours=1))
    core=display|dict(request_id='b'*64,grant_sha256='d'*64,registry_epoch=1,nonce=C.b64(b'n'*32),
        display_sha256=A.record_digest('display',A.canonical(display)))
    digest=A.record_digest('request',A.canonical(core))
    return A.parse_request(A.canonical(core|dict(request_sha256=digest,challenge=C.b64(hashlib.sha256(
        b'tradegen-passkey-archive/challenge/1\n'+b'n'*32+bytes.fromhex(digest)).digest()))))


def row(proposed,sequence=1,previous='0'*64):
    core=dict(schema=1,sequence=sequence,previous_sha256=previous,observed_at=C.stamp(proposed.observed_at),
        kind=proposed.kind,payload=A.proposed_payload(proposed))
    return A.LedgerEvent(sequence=sequence,previous_sha256=previous,observed_at=proposed.observed_at,
        kind=proposed.kind,payload_bytes=proposed.payload_bytes,row_sha256=A.record_digest('authority-event',A.canonical(core)))


def empty_state():
    return A.AuthorityState(grant=None,registry_epoch=0,last_trusted_at=None,owner_evidence=None,
        enrollments=(),credentials=(),requests=(),applications=(),notifications=(),deliveries=(),disabled=False,events=())


def test_actual_registration_proof_and_full_initial_credential_wire_roundtrip():
    _,p=proposal()
    assert A.parse_proposal(A.proposal_bytes(p))==p
    assert A.parse_credential(A.credential_bytes(p.initial_credential))==p.initial_credential
    other=replace(p.initial_credential,public_key_cose=b'altered-key-material')
    assert other.credential_sha256==p.initial_credential.credential_sha256
    assert other.digest!=p.initial_credential.digest
    assert p.proof.digest!=hashlib.sha256(C.assertion_bytes(p.proof.assertion)).hexdigest()
    assert A.parse_evidence(A.evidence_bytes(p.proof))==p.proof
    assert replace(p.proof,received_at=NOW+timedelta(microseconds=1)).digest!=p.proof.digest


def test_actual_ed25519_grant_signature_is_distinct_from_envelope_digest():
    _,p=proposal();key,g=grant(p)
    parsed=A.parse_grant(A.grant_bytes(g))
    key.public_key().verify(parsed.signature,A.grant_signing_bytes(parsed.body_bytes))
    assert parsed==g and g.digest==A.record_digest('grant-document',A.grant_bytes(g))
    assert g.digest!=hashlib.sha256(A.grant_signing_bytes(g.body_bytes)).hexdigest()
    bad=A.grant_body(g.body_bytes)|{'approval_scope':'code_approval'}
    refused(lambda:A.GrantDocument(body_bytes=A.canonical(bad),signature=g.signature))
    bad=A.grant_body(g.body_bytes)|{'initial_credential_sha256':p.initial_credential.credential_sha256}
    altered=A.GrantDocument(body_bytes=A.canonical(bad),signature=g.signature)
    try: key.public_key().verify(altered.signature,A.grant_signing_bytes(altered.body_bytes))
    except Exception as exc:
        from cryptography.exceptions import InvalidSignature
        assert type(exc) is InvalidSignature
    else: raise AssertionError('changed signed grant accepted')


def test_disable_signing_domain_is_separate_and_expected_head_is_positive():
    _,p=proposal();key,g=grant(p)
    raw=A.canonical(dict(schema=1,purpose=A.DISABLE_PURPOSE,authority_id='a'*64,grant_sha256=g.digest,
        expected_head=dict(sequence=4,sha256='e'*64),reason='DEVICE_LOST',issued_at=C.stamp(NOW),
        expires_at=C.stamp(NOW+timedelta(seconds=300))))
    d=A.DisableDocument(body_bytes=raw,signature=key.sign(A.disable_signing_bytes(raw)))
    assert A.parse_disable(A.disable_bytes(d))==d
    key.public_key().verify(d.signature,A.disable_signing_bytes(raw))
    bad=A.disable_body(raw)|{'expected_head':dict(sequence=0,sha256='e'*64)}
    refused(lambda:A.DisableDocument(body_bytes=A.canonical(bad),signature=d.signature))
    refused(lambda:A.grant_signing_bytes(raw))


def test_revoke_request_binds_target_display_epoch_and_challenge_without_effect():
    r=request(); assert A.parse_request(A.request_bytes(r))==r and r.kind=='REVOKE_CREDENTIAL'
    assert r.approval_expires_at is None
    b=r.body; b['target']['reason']='DEVICE_LOST'
    refused(lambda:A.parse_request(A.canonical(b)))
    assert r.body['target']['reason']=='OWNER_WITHDRAWN'
    for changes in ({'registry_epoch':True},{'kind':'session.activate'},{'approval_expires_at':C.stamp(NOW)},
                    {'request_sha256':'f'*64},{'challenge':C.b64(b'x'*32)},{'extra':None}):
        refused(lambda:A.parse_request(A.canonical(r.body|changes)))


def test_genuine_revoke_assertion_uses_stored_purpose_bound_challenge():
    e,p=proposal()
    r=request(target=dict(credential_sha256=p.initial_credential.credential_sha256,reason='OWNER_WITHDRAWN'))
    ctx=C.AssertionContext(purpose=r.kind,request_id=r.request_id,request_sha256=r.digest,rp=e.context.rp,
        challenge=r.challenge,user_handle=e.context.user_handle,credential=p.initial_credential.material(),
        requested_at=NOW,expires_at=r.challenge_expires_at)
    signed=W.assertion(SimpleNamespace(context=ctx,key=e.key),user_handle=ctx.user_handle)
    actual=V.verify_assertion(ctx,signed,now=NOW)
    assert actual.request_sha256==r.digest and not actual.approval_applied
    # Actual old proof signature cannot be promoted to this newly bound request.
    old=replace(p.proof.assertion,request_id=r.request_id)
    refused(lambda:V.verify_assertion(ctx,old,now=NOW),'PASSKEY_CHALLENGE_INVALID')
    refused(lambda:V.verify_assertion(replace(ctx,challenge=b'x'*32),signed,now=NOW),'PASSKEY_CHALLENGE_INVALID')
    refused(lambda:replace(ctx,purpose='PORTAL_SESSION'),'PASSKEY_SCOPE_UNSUPPORTED')


def test_event_canonical_roundtrip_self_hash_and_payload_detachment():
    e=enrollment();p=A.ProposedEvent(kind='ENROLLMENT_OPENED',observed_at=NOW,
        payload_bytes=A.canonical({'enrollment':e.document()}))
    event=row(p); assert A.parse_event(A.event_bytes(event))==event
    body=A.proposed_payload(event);body['enrollment']['nonce']=C.b64(b'x'*32)
    assert A.proposed_payload(event)['enrollment']['nonce']==C.b64(e.nonce)
    for changes in ({'sequence':True},{'row_sha256':'f'*64},{'previous_sha256':'f'*64},{'kind':'AUTHORITY_RESET'}):
        refused(lambda:replace(event,**changes))
    refused(lambda:A.parse_event(A.event_bytes(event)+b'\n'))
    refused(lambda:A.ProposedEvent(kind='ENROLLMENT_OPENED',observed_at=NOW,
        payload_bytes=A.canonical({'enrollment':e.document(),'approved':True})))


def test_registration_event_requires_exact_existing_proof_codec():
    e,p=proposal()
    payload=dict(enrollment_sha256=p.enrollment.digest,registration=p.registration.document(),
        registration_received_at=C.stamp(NOW),registration_evidence_sha256=e.registration.registration_evidence_sha256,
        proof_request=p.proof_request.document())
    event=row(A.ProposedEvent(kind='REGISTRATION_RECORDED',observed_at=NOW,payload_bytes=A.canonical(payload)))
    assert A.parse_event(A.event_bytes(event))==event
    refused(lambda:A.ProposedEvent(kind=event.kind,observed_at=NOW,payload_bytes=A.canonical(payload|{'proof_request':request().body})))


def test_install_event_retains_all_original_proof_inputs_without_issuing_trust():
    _,p=proposal();_,g=grant(p)
    body=dict(grant=A.decode(A.grant_bytes(g)),config_sha256='4'*64,initial_credential=A.credential_document(p.initial_credential),
        enrollment_request=p.enrollment.document(),registration=p.registration.document(),proof_request=p.proof_request.document(),
        proof=A.decode(A.evidence_bytes(p.proof)))
    event=row(A.ProposedEvent(kind='AUTHORITY_INSTALLED',observed_at=NOW,payload_bytes=A.canonical(body)))
    assert A.parse_event(A.event_bytes(event))==event
    for key in body:
        changed=dict(body);del changed[key]
        refused(lambda:A.ProposedEvent(kind=event.kind,observed_at=NOW,payload_bytes=A.canonical(changed)))


def test_notification_id_is_effect_bound_and_delivery_never_replaces_effect():
    n=notification();assert A.parse_notification(A.notification_bytes(n))==n
    payload=dict(intent_id=n.intent_id,attempt_id='c'*64,outcome='SENT',reported_at=C.stamp(NOW))
    e=row(A.ProposedEvent(kind='DELIVERY_REPORTED',observed_at=NOW,payload_bytes=A.canonical(payload)))
    assert A.parse_event(A.event_bytes(e))==e
    refused(lambda:A.ProposedEvent(kind='DELIVERY_REPORTED',observed_at=NOW,payload_bytes=A.canonical(payload|{'outcome':'APPROVED'})))
    refused(lambda:A.parse_notification(A.canonical(n.body|{'request_id':'f'*64})))
    assert A.record_digest('notification-id',b'{}')!=A.record_digest('application-id',b'{}')


def test_pending_stage_null_shapes_and_bounded_projection_are_data_only():
    p=A.PendingEnrollment(enrollment=enrollment(),registration=None,registration_received_at=None,
        proof_request=None,proof=None,initial_credential=None,proposal_sha256=None)
    s=replace(empty_state(),enrollments=(p,)); assert A.decode(A.state_bytes(s))['enrollments'][0]['proof'] is None
    refused(lambda:replace(p,registration_received_at=NOW))
    refused(lambda:replace(s,registry_epoch=1))
    refused(lambda:replace(s,enrollments=(p,)*257),'PASSKEY_RESOURCE_LIMIT')
    broken=replace(s);object.__delattr__(broken,'events')
    refused(lambda:A.state_bytes(broken))
    r=A.RequestState(request=request(),state='PENDING',evidence_sha256=None,application_id=None)
    refused(lambda:replace(r,evidence_sha256='c'*64))
    refused(lambda:replace(empty_state(),requests=(r,)*129),'PASSKEY_RESOURCE_LIMIT')


def test_duplicate_keys_float_int_alias_and_noncanonical_text_are_refused():
    for raw in (b'{"x":1,"x":2}',b'{"x":1.0}',b'{"x":NaN}',b'{"x":9223372036854775808}',
                b' {"x":1}',b'{"x":1}{}',b'{"x":-0}',b'"\\u0061"'):
        refused(lambda:A.decode(raw))
    refused(lambda:A.Head(sequence=True,sha256='a'*64))
    refused(lambda:A.record_digest('arbitrary-purpose',b'{}'))
    refused(lambda:A.canonical({False:'bool-key'}))


def test_scanner_refuses_structure_before_json_and_accepts_larger_than_foundation():
    raw=A.canonical({'values':list(range(5000))})
    assert len(A.decode(raw)['values'])==5000
    refused(lambda:C.decode(raw),'PASSKEY_RESOURCE_LIMIT')
    with patch.object(A.json,'loads',side_effect=AssertionError('scan must precede decoder')):
        refused(lambda:A.decode(b'['*17+b'0'+b']'*17),'PASSKEY_RESOURCE_LIMIT')
        refused(lambda:A.decode(b' '*100,maximum=99))


def test_constructed_node_budget_is_charged_before_stack_growth_or_encoder():
    child=[None]*100000
    tree=[child]*6
    with patch.object(C,'encoded',side_effect=AssertionError('admission before encoder')):
        refused(lambda:A.canonical(tree),'PASSKEY_RESOURCE_LIMIT')


def test_constructed_escaped_size_is_admitted_before_encoder_exact_unicode_boundary():
    values=['\x00'*100,'😀'*100,'\\'*100,'\x7f'*100]
    for value in values:
        expected=C.encoded(value)
        assert A.canonical(value,maximum=len(expected))==expected
        with patch.object(C,'encoded',side_effect=AssertionError('escaped budget before encoder')):
            refused(lambda:A.canonical(value,maximum=len(expected)-1),'PASSKEY_RESOURCE_LIMIT')
    assert A.decode(A.canonical({'text':'😀'*65536}))=={'text':'😀'*65536}


def test_owner_log_evidence_is_bounded_and_never_an_issuer():
    head=A.Head(sequence=1,sha256='a'*64)
    e=A.OwnerLogEvidence(public_key_raw=b'p'*32,log_bytes=b'unverified raw\n',anchors=(head,),
        observed_at=NOW,completed_at=NOW,head=head)
    assert A.parse_owner_evidence(A.owner_evidence_document(e))==e
    assert e.log_bytes==b'unverified raw\n'  # owner_view must actually verify it later
    refused(lambda:replace(e,anchors=(head,head)))
    refused(lambda:replace(e,completed_at=NOW-timedelta(microseconds=1)))
    assert 'unverified raw' not in repr(e)


def test_release_inventory_and_config_domains_bind_complete_exact_fields():
    release=A.ReleaseManifest(role='RP',python_version='3.13.16',files=(A.FileDigest(name='index.html',byte_count=2,sha256='a'*64),),dependencies=())
    assert A.parse_release(A.release_bytes(release))==release
    assert replace(release,files=(replace(release.files[0],byte_count=3),)).digest!=release.digest
    refused(lambda:replace(release,files=release.files*2))
    refused(lambda:A.FileDigest(name='../escape',byte_count=0,sha256='a'*64))
    refused(lambda:A.FileDigest(name='C:/escape',byte_count=0,sha256='a'*64))
    config=A.BrokerConfig(authority_id='a'*64,service_identity='broker',client_identity='client',pipe_name='archive',
        authority_root='/synthetic/primary',backup_root='/synthetic/backup',head_root='/synthetic/head',packet_inbox='/synthetic/inbox',
        app_repo='/synthetic/app',rp_origin='https://approve.test',rp_id='approve.test',rp_transport_spki_sha256='b'*64,
        broker_transport_public_key=b'p'*32,broker_mtls_spki_sha256='c'*64)
    assert A.parse_config(A.config_bytes(config))==config
    refused(lambda:replace(config,client_identity='broker'))
    assert '/synthetic/' not in repr(config)


def test_constructed_container_depth_and_scanner_tokens_match_decoder_admission():
    value=[]
    for _ in range(15): value=[value]
    raw=A.canonical(value); assert A.decode(raw)==value
    wide={str(i):None for i in range(250001)}
    with patch.object(C,'encoded',side_effect=AssertionError('structural admission before encoder')):
        refused(lambda:A.canonical([value]),'PASSKEY_RESOURCE_LIMIT')
        refused(lambda:A.canonical(wide),'PASSKEY_RESOURCE_LIMIT')
