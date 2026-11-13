"""Historical authority replay from exact rows, with actual signatures.

No files, ambient clock, application code, caller credential map or verifier
callback is read here. Historical observations do not establish current owner,
release, packet or operational-channel eligibility.
"""
from __future__ import annotations

from dataclasses import replace
import hashlib
import json

from tools.signer import sign as S

from tools.approval_broker import contract as C
from tools.approval_broker import authority_contract as A
from tools.approval_broker import webauthn_verify as W
from tools.approval_broker import bootstrap as B
from tools.approval_broker import owner_view as O


def _need(value,code='PASSKEY_FORMAT_INVALID'):
    C.need(value,code)


def _raw(body,maximum=A.MAX_EVENT_BYTES):
    return A.canonical(body,maximum=maximum)


def _obj(raw,maximum=A.MAX_EVENT_BYTES):
    return A.decode_authority(raw,maximum=maximum)


def _initial():
    return A.AuthorityState(grant=None,registry_epoch=0,last_trusted_at=None,owner_evidence=None,
        enrollments=(),credentials=(),requests=(),applications=(),notifications=(),deliveries=(),
        disabled=False,events=())


def _state_bytes(state,*,limits):
    _need(type(state) is A.AuthorityState)
    specifications=(('events',limits.max_events),('enrollments',128),('credentials',256),
        ('requests',4096),('applications',4096),('notifications',8192),('deliveries',16384))
    for name,cap in specifications:
        value=getattr(state,name)
        _need(type(value) is tuple and len(value)<=cap,'PASSKEY_RESOURCE_LIMIT')
    for name,cls in (('events',A.LedgerEvent),('enrollments',A.PendingEnrollment),
                     ('credentials',A.Credential),('requests',A.RequestState),
                     ('applications',A.ApplicationRecord),('notifications',A.NotificationIntent)):
        _need(all(type(x) is cls for x in getattr(state,name)))
    _need(all(type(x.request) is A.RequestRecord for x in state.requests))
    size=0
    def take(raw):
        nonlocal size
        size+=len(raw)+1
        _need(size<=limits.max_state_bytes,'PASSKEY_RESOURCE_LIMIT')
        return _obj(raw)
    def optional(value,encoder): return None if value is None else take(encoder(value))
    pending=[]
    for p in state.enrollments:
        _need(type(p) is A.PendingEnrollment)
        body=dict(enrollment=_obj(C.enrollment_bytes(p.enrollment)),
            registration=None if p.registration is None else _obj(C.registration_bytes(p.registration)),
            registration_received_at=None if p.registration_received_at is None else C.stamp(p.registration_received_at),
            proof_request=None if p.proof_request is None else _obj(C.proof_request_bytes(p.proof_request)),
            proof=None if p.proof is None else _obj(A.evidence_bytes(p.proof)),
            initial_credential=None if p.initial_credential is None else _obj(A.credential_bytes(p.initial_credential)),
            proposal_sha256=p.proposal_sha256)
        pending.append(take(_raw(body,A.MAX_DOCUMENT_BYTES)))
    body=dict(grant=optional(state.grant,A.grant_bytes),registry_epoch=state.registry_epoch,
        last_trusted_at=None if state.last_trusted_at is None else C.stamp(state.last_trusted_at),
        owner_evidence=None if state.owner_evidence is None else take(_raw(A.owner_evidence_document(state.owner_evidence))),
        enrollments=pending,credentials=[take(A.credential_bytes(x)) for x in state.credentials],
        requests=[take(_raw(dict(request=_obj(x.request.raw),state=x.state,evidence_sha256=x.evidence_sha256,
                       application_id=x.application_id))) for x in state.requests],
        applications=[take(x.raw) for x in state.applications],
        notifications=[take(x.raw) for x in state.notifications],deliveries=[take(x) for x in state.deliveries],
        disabled=state.disabled,events=[take(A.event_bytes(x)) for x in state.events])
    _raw(body,limits.max_state_bytes)  # configured cumulative/complete bound first
    raw=A.state_bytes(state)         # final strict descriptive validation, once
    _need(len(raw)<=limits.max_state_bytes,'PASSKEY_RESOURCE_LIMIT')
    return raw


def _assembled(state, changes):
    # Only the private fold uses this assembly, after actual per-row parsing and
    # signature checks. Re-entering AuthorityState.__post_init__ at each prefix
    # would reparse every earlier event quadratically. Public validation rebuilds
    # the prefix and validates the final projection; no caller cache is accepted.
    names=('grant','registry_epoch','last_trusted_at','owner_evidence','enrollments',
           'credentials','requests','applications','notifications','deliveries','disabled','events')
    _need(set(changes)<=set(names))
    result=object.__new__(A.AuthorityState)
    for name in names: object.__setattr__(result,name,changes[name] if name in changes else getattr(state,name))
    return result


def _grant_digest(grant): return A.record_digest('grant-document',A.grant_bytes(grant))


def _owner(checkpoint,state,installation,index):
    evidence=state.owner_evidence
    _need(type(evidence) is A.OwnerLogEvidence,'PASSKEY_OWNER_CHANGED')
    _need(checkpoint.fingerprint=='SHA256:'+hashlib.sha256(evidence.public_key_raw).hexdigest(),
          'PASSKEY_OWNER_CHANGED')
    # Signature/rotation verification was done when this actual evidence entered
    # the replay prefix. Here retain the exact signed row membership restriction.
    # The already signature-verified owner wire permits fractional limit values
    # and UTF-8 strings. Authority JSON's no-float/ASCII codec is not its parser.
    rows=index.owner_rows
    _need(index.owner_heads.get(checkpoint.owner_head.sequence)==checkpoint.owner_head.sha256,
          'PASSKEY_OWNER_CHANGED')
    approvals=tuple((utc,code) for seq,utc,code in index.owner_approvals if seq<=checkpoint.owner_head.sequence)
    _need(S._bundle_code_approval_at(approvals,checkpoint.observed_at)==checkpoint.code_sha256,
          'PASSKEY_OWNER_CHANGED')
    if state.grant is not None:
        _need(checkpoint.code_sha256==A.grant_body(state.grant.body_bytes)['owner_checkpoint']['code_sha256'],
              'PASSKEY_OWNER_CHANGED')


class _Index:
    """Replay-local lookup built only from actual parsed history; never public input."""
    def __init__(self,state):
        self.enrollments={p.enrollment.digest:(i,p) for i,p in enumerate(state.enrollments)}
        self.enrollment_ids={p.enrollment.enrollment_id for p in state.enrollments}
        self.requests={r.request.request_sha256:(i,r) for i,r in enumerate(state.requests)}
        self.request_ids={r.request.request_id for r in state.requests}
        self.credentials={c.credential_sha256:(i,c) for i,c in enumerate(state.credentials)}
        self.applications={a.application_id for a in state.applications}
        self.notifications={n.intent_id for n in state.notifications}
        self.deliveries={_obj(d)['attempt_id'] for d in state.deliveries}
        self.pending=sum(r.state=='PENDING' for r in state.requests)
        self.owner(state.owner_evidence)
        _need(len(self.enrollments)==len(state.enrollments) and len(self.enrollment_ids)==len(state.enrollments)
              and len(self.requests)==len(state.requests) and len(self.request_ids)==len(state.requests)
              and len(self.credentials)==len(state.credentials) and len(self.applications)==len(state.applications)
              and len(self.notifications)==len(state.notifications) and len(self.deliveries)==len(state.deliveries))

    def owner(self,evidence):
        self.owner_rows=() if evidence is None else tuple(json.loads(line)
            for line in evidence.log_bytes.split(b'\n') if line)
        self.owner_heads={row['seq']:row['row_sha256'] for row in self.owner_rows}
        self.owner_approvals=tuple((row['seq'],row['utc'],row['data']['sha256'])
            for row in self.owner_rows if row['kind']=='code_approved')


def _pending(state,enrollment_sha,index):
    _need(enrollment_sha in index.enrollments,'PASSKEY_TARGET_CHANGED')
    return index.enrollments[enrollment_sha]


def _request(state,digest,index):
    _need(digest in index.requests,'PASSKEY_TARGET_CHANGED')
    return index.requests[digest]


def _credential(state,digest,index):
    _need(digest in index.credentials,'PASSKEY_TARGET_CHANGED')
    return index.credentials[digest]


def _set(rows,index,value): return rows[:index]+(value,)+rows[index+1:]


def _notification(body,*,authority_id,request_id,application_id,kind,status,observed_at):
    notification=A.parse_notification(_raw(body))
    actual=_obj(notification.raw)
    identity=dict(authority_id=authority_id,request_id=request_id,application_id=application_id,kind=kind)
    _need(all(actual[k]==v for k,v in identity.items()) and actual['status']==status
          and actual['intent_id']==A.record_digest('notification-id',_raw(identity))
          and C.time_value(actual['created_at'])<=observed_at,'PASSKEY_TARGET_CHANGED')
    return notification


def _active(state,at,index):
    _need(state.grant is not None and state.registry_epoch>=1 and not state.disabled,'PASSKEY_GRANT_INVALID')
    body=A.grant_body(state.grant.body_bytes)
    C.at_time(C.time_value(body['issued_at']),C.time_value(body['expires_at']),at)
    _need(state.owner_evidence is not None,'PASSKEY_OWNER_CHANGED')
    checkpoint=A.parse_owner_checkpoint(body['owner_checkpoint'])
    _owner(checkpoint,state,None,index)
    approvals=tuple((utc,code) for _,utc,code in index.owner_approvals)
    _need(S._bundle_code_approval_at(approvals,at)==checkpoint.code_sha256,'PASSKEY_OWNER_CHANGED')
    return body


def _assertion(state,request,evidence,*,at,purpose,index):
    _need(evidence.request_sha256==request.request_sha256
          and evidence.assertion.request_id==request.request_id,'PASSKEY_TARGET_CHANGED')
    body=_obj(request.raw)
    _need(request.kind==purpose and body['registry_epoch']==state.registry_epoch
          and body['grant_sha256']==_grant_digest(state.grant),'PASSKEY_REGISTRY_CHANGED')
    digest=hashlib.sha256(evidence.assertion.credential_id).hexdigest()
    credential_index,credential=_credential(state,digest,index)
    _need(credential.state=='ACTIVE','PASSKEY_REVOKED')
    _need(C.time_value(body['requested_at'])<=evidence.received_at<=at,'PASSKEY_CLOCK_INVALID')
    C.at_time(C.time_value(body['requested_at']),request.challenge_expires_at,at)
    context=C.AssertionContext(purpose=purpose,request_id=request.request_id,
        request_sha256=request.request_sha256,rp=credential.material().rp,challenge=request.challenge,
        user_handle=credential.user_handle,credential=credential.material(),
        requested_at=C.time_value(body['requested_at']),expires_at=request.challenge_expires_at)
    verified=W.verify_assertion(context,evidence.assertion,now=evidence.received_at)
    updated=replace(credential,last_counter=verified.counter,last_backed_up=verified.backed_up)
    return credential_index,updated


def _transition_owned(state,event,*,installation,limits,_index=None):
    """Private fold for this module/ledger's actual replay-local prefix only."""
    _need(type(state) is A.AuthorityState and type(event) is A.LedgerEvent)
    _need(event.sequence==len(state.events)+1,'PASSKEY_STORE_INDETERMINATE')
    if state.events: _need(event.previous_sha256==state.events[-1].row_sha256,'PASSKEY_STORE_INDETERMINATE')
    _need(state.last_trusted_at is None or event.observed_at>=state.last_trusted_at,'PASSKEY_CLOCK_INVALID')
    index_map=_Index(state) if _index is None else _index
    body=_obj(event.payload_bytes)
    changes={}
    kind=event.kind; at=event.observed_at
    if kind=='OWNER_CHECKPOINT_ADVANCED':
        evidence=A.parse_owner_evidence(body['evidence'])
        O.verify_owner_evidence(evidence,roots=installation.roots,previous=state.owner_evidence)
        _need(evidence.observed_at<=evidence.completed_at<=at,'PASSKEY_CLOCK_INVALID')
        if state.owner_evidence is not None and evidence.head==state.owner_evidence.head:
            return state
        changes['owner_evidence']=evidence
    elif kind=='ENROLLMENT_OPENED':
        _need(state.grant is None and not state.disabled,'PASSKEY_SCOPE_UNSUPPORTED')
        enrollment=C.parse_enrollment(_raw(body['enrollment']))
        _need(enrollment.authority_id==installation.authority_id and enrollment.grant_sha256 is None
              and enrollment.registry_epoch==0,'PASSKEY_TARGET_CHANGED')
        C.at_time(enrollment.requested_at,enrollment.expires_at,at)
        _need(enrollment.enrollment_id not in index_map.enrollment_ids,
              'PASSKEY_REQUEST_REUSED')
        _need(len(state.enrollments)<128,'PASSKEY_RESOURCE_LIMIT')
        changes['enrollments']=state.enrollments+(A.PendingEnrollment(enrollment=enrollment,
            registration=None,registration_received_at=None,proof_request=None,proof=None,
            initial_credential=None,proposal_sha256=None),)
    elif kind=='REGISTRATION_RECORDED':
        _need(state.grant is None,'PASSKEY_SCOPE_UNSUPPORTED')
        index,pending=_pending(state,body['enrollment_sha256'],index_map)
        _need(pending.registration is None,'PASSKEY_REQUEST_REUSED')
        registration=C.parse_registration(_raw(body['registration']))
        received=C.time_value(body['registration_received_at'])
        _need(received<=at,'PASSKEY_CLOCK_INVALID')
        verified=W.verify_registration(pending.enrollment,registration,now=received)
        proof=C.parse_proof_request(_raw(body['proof_request']))
        _need(verified.registration_evidence_sha256==body['registration_evidence_sha256']
              and proof.authority_id==installation.authority_id and proof.grant_sha256 is None
              and proof.registry_epoch==0 and received<=proof.requested_at<=at,'PASSKEY_TARGET_CHANGED')
        C.proof_context(proof,verified.credential)
        changes['enrollments']=_set(state.enrollments,index,replace(pending,registration=registration,
            registration_received_at=received,proof_request=proof))
    elif kind=='INITIAL_PROOF_RECORDED':
        _need(state.grant is None,'PASSKEY_SCOPE_UNSUPPORTED')
        index,pending=_pending(state,body['enrollment_sha256'],index_map)
        _need(pending.registration is not None and pending.proof is None,'PASSKEY_REQUEST_REUSED')
        proof=A.parse_evidence(_raw(body['proof']))
        initial=A.parse_credential(_raw(body['initial_credential']))
        proposal=A.BootstrapProposal(enrollment=pending.enrollment,registration=pending.registration,
            registration_received_at=pending.registration_received_at,proof_request=pending.proof_request,
            proof=proof,initial_credential=initial)
        verified=B.verify_bootstrap(proposal)
        _need(A.credential_bytes(verified)==A.credential_bytes(initial)
              and proposal.digest==body['proposal_sha256'] and proof.received_at<=at,'PASSKEY_TARGET_CHANGED')
        changes['enrollments']=_set(state.enrollments,index,replace(pending,proof=proof,
            initial_credential=initial,proposal_sha256=proposal.digest))
    elif kind=='AUTHORITY_INSTALLED':
        _need(state.grant is None and state.registry_epoch==0 and not state.disabled,'PASSKEY_REQUEST_REUSED')
        grant=A.parse_grant(_raw(body['grant']))
        g=A.grant_body(grant.body_bytes)
        _need(g['authority_id']==installation.authority_id and g['config_sha256']==installation.config_sha256
              and body['config_sha256']==installation.config_sha256 and g['grant_epoch']==1
              and g['previous_grant_sha256'] is None
              and g['recovery_fingerprint']=='SHA256:'+hashlib.sha256(installation.roots.recovery_public_key_raw).hexdigest(),
              'PASSKEY_GRANT_INVALID')
        _need(state.owner_evidence is not None,'PASSKEY_OWNER_CHANGED')
        B.verify_grant_document(grant,signer_public_key_raw=state.owner_evidence.public_key_raw)
        checkpoint=A.parse_owner_checkpoint(g['owner_checkpoint']); _owner(checkpoint,state,installation,index_map)
        C.at_time(C.time_value(g['issued_at']),C.time_value(g['expires_at']),at)
        enrollment=C.parse_enrollment(_raw(body['enrollment_request']))
        _,pending=_pending(state,enrollment.digest,index_map)
        initial=A.parse_credential(_raw(body['initial_credential']))
        proposal=A.BootstrapProposal(enrollment=enrollment,
            registration=C.parse_registration(_raw(body['registration'])),
            registration_received_at=initial.created_at,
            proof_request=C.parse_proof_request(_raw(body['proof_request'])),
            proof=A.parse_evidence(_raw(body['proof'])),initial_credential=initial)
        actual=B.verify_bootstrap(proposal)
        _need(pending.proposal_sha256==proposal.digest and proposal.proof.received_at<=at
              and A.credential_bytes(actual)==A.credential_bytes(initial)
              and g['initial_credential_sha256']==A.record_digest('credential',A.credential_bytes(initial)),
              'PASSKEY_GRANT_INVALID')
        changes.update(grant=grant,registry_epoch=1,credentials=(initial,))
    elif kind=='REQUEST_OPENED':
        _active(state,at,index_map)
        request=A.parse_request(_raw(body['request'],A.MAX_REQUEST_BYTES)); r=_obj(request.raw)
        _need(request.kind in ('ARCHIVE_CONFIRM','REVOKE_CREDENTIAL'),'PASSKEY_SCOPE_UNSUPPORTED')
        _need(r['authority_id']==installation.authority_id and r['grant_sha256']==_grant_digest(state.grant)
              and r['registry_epoch']==state.registry_epoch,'PASSKEY_REGISTRY_CHANGED')
        C.at_time(C.time_value(r['requested_at']),request.challenge_expires_at,at)
        _need(request.request_id not in index_map.request_ids,'PASSKEY_REQUEST_REUSED')
        _need(len(state.requests)<4096 and index_map.pending<128,'PASSKEY_RESOURCE_LIMIT')
        if request.kind=='REVOKE_CREDENTIAL':
            _,target=_credential(state,r['target']['credential_sha256'],index_map)
            _need(target.state=='ACTIVE','PASSKEY_REVOKED')
        note=_notification(body['notification'],authority_id=installation.authority_id,
            request_id=request.request_id,application_id=None,kind='REQUEST_READY',status='PENDING',observed_at=at)
        changes.update(requests=state.requests+(A.RequestState(request=request,state='PENDING',
            evidence_sha256=None,application_id=None),),notifications=state.notifications+(note,))
    elif kind in ('ARCHIVE_APPLIED','CREDENTIAL_REVOKED'):
        _active(state,at,index_map)
        evidence=A.parse_evidence(_raw(body['evidence']))
        digest=body['request_sha256'] if kind=='CREDENTIAL_REVOKED' else evidence.request_sha256
        index,pending=_request(state,digest,index_map)
        _need(pending.state=='PENDING','PASSKEY_REQUEST_REUSED')
        purpose='ARCHIVE_CONFIRM' if kind=='ARCHIVE_APPLIED' else 'REVOKE_CREDENTIAL'
        ci,credential=_assertion(state,pending.request,evidence,at=at,purpose=purpose,index=index_map)
        request=_obj(pending.request.raw)
        if kind=='ARCHIVE_APPLIED':
            app=A.parse_application(_raw(body['application'])); a=_obj(app.raw)
            target=request['target']; archive=target['archive_request']
            expected=dict(authority_id=installation.authority_id,grant_sha256=_grant_digest(state.grant),
                registry_epoch=state.registry_epoch,request_sha256=digest,evidence_sha256=evidence.digest,
                credential_sha256=credential.credential_sha256,bundle_digest=archive['bundle_digest'],
                input_archive_digest=archive['input_archive_digest'],file_set_sha256=archive['file_set_sha256'],
                archive_request_sha256=target['archive_request_sha256'],packet_sha256=target['packet_sha256'])
            _need(all(a[k]==value for k,value in expected.items()),'PASSKEY_TARGET_CHANGED')
            identity={k:expected[k] for k in ('authority_id','request_sha256','evidence_sha256')}
            _need(a['application_id']==A.record_digest('application-id',_raw(identity))
                  and evidence.received_at<=C.time_value(a['applied_at'])<=at
                  and C.time_value(a['expires_at'])==pending.request.approval_expires_at
                  and at<C.time_value(a['expires_at']),'PASSKEY_TARGET_CHANGED')
            _owner(A.parse_owner_checkpoint(a['owner_checkpoint']),state,installation,index_map)
            _need(app.application_id not in index_map.applications,'PASSKEY_REQUEST_REUSED')
            note=_notification(body['notification'],authority_id=installation.authority_id,
                request_id=pending.request.request_id,application_id=app.application_id,
                kind='APPLICATION_RESULT',status='APPLIED',observed_at=at)
            changes['applications']=state.applications+(app,)
            pending=replace(pending,state='APPLIED',evidence_sha256=evidence.digest,application_id=app.application_id)
        else:
            target=request['target']
            _need(body['credential_sha256']==target['credential_sha256']==credential.credential_sha256
                  and body['reason']==target['reason'] and body['new_registry_epoch']==state.registry_epoch+1,
                  'PASSKEY_TARGET_CHANGED')
            credential=replace(credential,state='REVOKED',revoked_at=at)
            note=_notification(body['notification'],authority_id=installation.authority_id,
                request_id=pending.request.request_id,application_id=None,
                kind='CREDENTIAL_RESULT',status='APPLIED',observed_at=at)
            changes['registry_epoch']=state.registry_epoch+1
            pending=replace(pending,state='APPLIED',evidence_sha256=evidence.digest,application_id=None)
        requests=_set(state.requests,index,pending)
        if kind=='CREDENTIAL_REVOKED':
            requests=tuple(replace(x,state='INVALIDATED') if x.state=='PENDING' else x for x in requests)
        changes.update(requests=requests,credentials=_set(state.credentials,ci,credential),
                       notifications=state.notifications+(note,))
    elif kind=='AUTHORITY_DISABLED':
        _need(state.grant is not None and not state.disabled,'PASSKEY_GRANT_INVALID')
        document=A.parse_disable(_raw(body['disable'])); d=A.disable_body(document.body_bytes)
        B.verify_disable_document(document,recovery_public_key_raw=installation.roots.recovery_public_key_raw)
        _need(d['authority_id']==installation.authority_id and d['grant_sha256']==_grant_digest(state.grant)
              and A.parse_head(d['expected_head'])==A.Head(sequence=event.sequence-1,sha256=event.previous_sha256),
              'PASSKEY_TARGET_CHANGED')
        C.at_time(C.time_value(d['issued_at']),C.time_value(d['expires_at']),at)
        note=_notification(body['notification'],authority_id=installation.authority_id,request_id=None,
                           application_id=None,kind='CREDENTIAL_RESULT',status='APPLIED',observed_at=at)
        changes.update(disabled=True,requests=tuple(replace(x,state='INVALIDATED')
            if x.state=='PENDING' else x for x in state.requests),notifications=state.notifications+(note,))
    elif kind=='REQUEST_CLOSED':
        index,pending=_request(state,body['request_sha256'],index_map)
        _need(pending.state=='PENDING' and body['state']=='EXPIRED'
              and at>=min(pending.request.challenge_expires_at,
                  pending.request.approval_expires_at or pending.request.challenge_expires_at)
              and body['evidence_sha256'] is None,
              'PASSKEY_EXPIRED')
        note=_notification(body['notification'],authority_id=installation.authority_id,
            request_id=pending.request.request_id,application_id=None,
            kind='APPLICATION_RESULT' if pending.request.kind=='ARCHIVE_CONFIRM' else 'CREDENTIAL_RESULT',
            status='EXPIRED',observed_at=at)
        changes.update(requests=_set(state.requests,index,replace(pending,state='EXPIRED')),
                       notifications=state.notifications+(note,))
    elif kind=='DELIVERY_REPORTED':
        _need(body['intent_id'] in index_map.notifications,'PASSKEY_TARGET_CHANGED')
        _need(body['attempt_id'] not in index_map.deliveries,'PASSKEY_REQUEST_REUSED')
        _need(C.time_value(body['reported_at'])<=at,'PASSKEY_CLOCK_INVALID')
        changes['deliveries']=state.deliveries+(event.payload_bytes,)
    else: raise C.PasskeyError('PASSKEY_SCOPE_UNSUPPORTED')
    changes.update(last_trusted_at=at,events=state.events+(event,))
    result=_assembled(state,changes)
    _need(len(result.events)<=limits.max_events and len(result.credentials)<=256
          and sum(c.state=='ACTIVE' for c in result.credentials)<=16
          and len(result.notifications)<=8192 and len(result.deliveries)<=16384,'PASSKEY_RESOURCE_LIMIT')
    # Update only the new/changed records in this private actual replay index.
    if 'owner_evidence' in changes: index_map.owner(result.owner_evidence)
    if 'enrollments' in changes:
        if len(result.enrollments)>len(state.enrollments):
            p=result.enrollments[-1]; i=len(result.enrollments)-1
        else:
            i=index; p=result.enrollments[i]
        index_map.enrollments[p.enrollment.digest]=(i,p)
        index_map.enrollment_ids.add(p.enrollment.enrollment_id)
    if 'credentials' in changes:
        for i,c in enumerate(result.credentials): index_map.credentials[c.credential_sha256]=(i,c)
    if 'requests' in changes:
        if kind in ('CREDENTIAL_REVOKED','AUTHORITY_DISABLED'):
            for i,r in enumerate(result.requests): index_map.requests[r.request.request_sha256]=(i,r)
            index_map.pending=sum(r.state=='PENDING' for r in result.requests)
        elif len(result.requests)>len(state.requests):
            r=result.requests[-1];i=len(result.requests)-1
            index_map.requests[r.request.request_sha256]=(i,r)
            index_map.request_ids.add(r.request.request_id); index_map.pending+=1
        else:
            r=result.requests[index]; index_map.requests[r.request.request_sha256]=(index,r)
            index_map.pending-=1
    if 'applications' in changes: index_map.applications.add(result.applications[-1].application_id)
    if 'notifications' in changes:
        intent=result.notifications[-1].intent_id
        _need(intent not in index_map.notifications,'PASSKEY_REQUEST_REUSED')
        index_map.notifications.add(intent)
    if 'deliveries' in changes: index_map.deliveries.add(body['attempt_id'])
    return result


def replay_events(raw_rows,*,installation,limits):
    from tools.approval_broker.ledger import LedgerInstallation,LedgerLimits
    _need(type(installation) is LedgerInstallation and type(limits) is LedgerLimits)
    installation.__post_init__();limits.__post_init__()
    _need(type(raw_rows) is tuple and len(raw_rows)<=limits.max_events,'PASSKEY_RESOURCE_LIMIT')
    state=_initial(); total=0; index=_Index(state)
    for raw in raw_rows:
        C.binary(raw,limits.max_event_bytes)
        total+=len(raw)+1
        _need(len(raw)+1<=limits.max_event_bytes and total<=limits.max_journal_bytes,'PASSKEY_RESOURCE_LIMIT')
        event=A.parse_event(raw)
        _need(A.event_bytes(event)==raw,'PASSKEY_FORMAT_INVALID')
        proposed=_transition_owned(state,event,installation=installation,limits=limits,_index=index)
        _need(proposed is not state,'PASSKEY_STORE_INDETERMINATE')
        state=proposed
    _state_bytes(state,limits=limits)
    return state


def validate_transition(state,event,*,installation,limits):
    """Public data helper always reconstructs arbitrary supplied state first."""
    _need(type(state) is A.AuthorityState and type(event) is A.LedgerEvent)
    _need(type(state.events) is tuple and len(state.events)<=limits.max_events,'PASSKEY_RESOURCE_LIMIT')
    rows=[]; total=0
    for value in state.events:
        raw=A.event_bytes(value);total+=len(raw)+1
        _need(total<=limits.max_journal_bytes and total<=limits.max_state_bytes,'PASSKEY_RESOURCE_LIMIT')
        rows.append(raw)
    actual=replay_events(tuple(rows),installation=installation,limits=limits)
    _need(_state_bytes(actual,limits=limits)==_state_bytes(state,limits=limits),'PASSKEY_FORMAT_INVALID')
    parsed=A.parse_event(A.event_bytes(event))
    proposed=_transition_owned(actual,parsed,installation=installation,limits=limits)
    _state_bytes(proposed,limits=limits)
    return proposed
