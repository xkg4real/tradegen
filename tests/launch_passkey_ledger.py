"""Independent disk/crypto ledger tests, using temporary keys and roots only.

The signed code/release/config metadata here is a small historical fixture, not
an actual app deployment or operating RP. The separate engine integration tests
exercise actual deployment inventories and exported research packets. No source
authenticator, current-owner verifier or cryptographic success is replaced.
"""
from contextlib import contextmanager
from dataclasses import replace
from datetime import timedelta
import hashlib
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

from cryptography.hazmat.primitives.asymmetric import ed25519

from tools.signer import sign as S
from tools.approval_broker import contract as C, authority_contract as A
from tools.approval_broker import ledger as L, authority_replay as R
from tools.approval_broker import owner_view as O, bootstrap as B, webauthn_verify as W
from tests import launch_passkey_contract as F
from tests import launch_passkey_webauthn as WF

NOW=F.NOW


def refused(call,*codes):
    try: call()
    except C.PasskeyError as exc:
        assert str(exc).startswith('PASSKEY_')
        if codes: assert str(exc) in codes,(str(exc),codes)
        return str(exc)
    raise AssertionError('expected actual refusal')


def files(base):
    return {str(p.relative_to(base)):p.read_bytes() for p in base.rglob('*') if p.is_file()}


def document(raw): return A.decode_authority(raw,maximum=A.MAX_EVENT_BYTES)


def proposal(kind,payload,at=NOW):
    return A.ProposedEvent(kind=kind,observed_at=at,payload_bytes=A.canonical(payload))


def enrollment_event(e,number=1):
    request=replace(e.enrollment,enrollment_id=format(number,'064x'),nonce=number.to_bytes(32,'big'))
    return proposal('ENROLLMENT_OPENED',dict(enrollment=document(C.enrollment_bytes(request))))


def push(e,event):
    with e.ledger.operation() as op:
        current=op.load()
        return op.commit(event,expected_head=current.head)


@contextmanager
def fixture(*,limits=None,prepared=True):
    with tempfile.TemporaryDirectory(prefix='tradegen-authority-ledger-') as directory:
        base=Path(directory)
        for name in ('primary','backup','head'): (base/name).mkdir()
        owner=ed25519.Ed25519PrivateKey.generate(); recovery=ed25519.Ed25519PrivateKey.generate()
        public=owner.public_key().public_bytes_raw(); recovery_public=recovery.public_key().public_bytes_raw()
        source=b'# synthetic historical code inventory\n'
        (base/'검토.py').write_bytes(source)
        inventory=[['검토.py',hashlib.sha256(source).hexdigest()]]
        code=hashlib.sha256(S.canonical_json(inventory).encode()).hexdigest()
        previous=S.GENESIS_PREV; rows=[]; heads=[]
        for index,(kind,data) in enumerate((('code_approved',dict(sha256=code,files=inventory)),
                ('cap_set',dict(key='okx_equity_share',value=0.5)),
                ('session_armed',dict(session_id='합성 기록'))),1):
            raw,previous=S.entry_line(owner,index,previous,kind,data,
                (NOW-timedelta(seconds=1)).strftime('%Y-%m-%dT%H:%M:%SZ'))
            rows.append(raw);heads.append(A.Head(sequence=index,sha256=previous))
        roots=O.TrustRoots(initial_public_key_raw=public,initial_owner_head=heads[0],
                           recovery_public_key_raw=recovery_public)
        evidence=A.OwnerLogEvidence(public_key_raw=public,log_bytes=b''.join(rows),anchors=(heads[0],),
            observed_at=NOW,completed_at=NOW,head=heads[-1])
        O.verify_owner_evidence(evidence,roots=roots,previous=None)
        enrollment=F.enrollment()
        storage=L.LedgerRoots(primary=base/'primary',backup=base/'backup',head=base/'head')
        installation=L.LedgerInstallation(authority_id=enrollment.authority_id,
            config_sha256=hashlib.sha256(b'explicit synthetic config commitment').hexdigest(),
            operator_paths_sha256=hashlib.sha256(str(base).encode()).hexdigest(),roots=roots)
        limits=L.LedgerLimits() if limits is None else limits
        args=dict(roots=storage,installation=installation,limits=limits)
        ledger=L.prepare_authority_store(**args) if prepared else L.AuthorityLedger(**args)
        yield SimpleNamespace(base=base,roots=storage,installation=installation,limits=limits,
            ledger=ledger,args=args,owner=owner,recovery=recovery,public=public,
            evidence=evidence,code=code,enrollment=enrollment)


def bootstrap(e):
    w=WF.fixture(eligible=False,counter=0)
    assert w.request.authority_id==e.installation.authority_id
    push(e,proposal('OWNER_CHECKPOINT_ADVANCED',{'evidence':A.owner_evidence_document(e.evidence)}))
    push(e,proposal('ENROLLMENT_OPENED',{'enrollment':document(C.enrollment_bytes(w.request))}))
    push(e,proposal('REGISTRATION_RECORDED',dict(enrollment_sha256=w.request.digest,
        registration=document(C.registration_bytes(w.response)),registration_received_at=C.stamp(NOW),
        registration_evidence_sha256=w.registration.registration_evidence_sha256,
        proof_request=document(C.proof_request_bytes(w.proof)))))
    assertion=WF.assertion(w,counter=1)
    verified=W.verify_assertion(w.context,assertion,now=NOW)
    evidence=A.WebAuthnEvidence(request_sha256=w.proof.digest,assertion=assertion,received_at=NOW)
    material=w.registration.credential
    credential=A.Credential(credential_id=material.credential_id,
        credential_sha256=material.credential_sha256,public_key_cose=material.public_key_cose,
        algorithm=-7,user_handle=material.user_handle,rp_id=material.rp.rp_id,origin=material.rp.origin,
        registration_evidence_sha256=material.registration_evidence_sha256,
        proof_evidence_sha256=evidence.digest,created_at=NOW,backup_eligible=False,
        last_backed_up=verified.backed_up,last_counter=verified.counter,state='ACTIVE',revoked_at=None)
    p=A.BootstrapProposal(enrollment=w.request,registration=w.response,registration_received_at=NOW,
        proof_request=w.proof,proof=evidence,initial_credential=credential)
    assert A.credential_bytes(B.verify_bootstrap(p))==A.credential_bytes(credential)
    push(e,proposal('INITIAL_PROOF_RECORDED',dict(enrollment_sha256=w.request.digest,
        proof=document(A.evidence_bytes(evidence)),initial_credential=document(A.credential_bytes(credential)),
        proposal_sha256=p.digest)))
    checkpoint=A.OwnerCheckpoint(fingerprint=S.fingerprint(e.public),code_sha256=e.code,
        owner_head=e.evidence.head,observed_at=NOW)
    body=A.canonical(dict(schema=1,purpose='passkey_archive_authority_grant',
        authority_id=e.installation.authority_id,grant_epoch=1,previous_grant_sha256=None,
        owner_checkpoint=A.owner_checkpoint_document(checkpoint),
        recovery_fingerprint=S.fingerprint(e.installation.roots.recovery_public_key_raw),
        config_sha256=e.installation.config_sha256,
        broker_release_sha256=hashlib.sha256(b'synthetic historical broker inventory').hexdigest(),
        rp_release_sha256=hashlib.sha256(b'synthetic historical RP inventory').hexdigest(),
        approval_scope='archive_manifest_identity',lifecycle_actions=['REGISTER_CREDENTIAL','REVOKE_CREDENTIAL'],
        initial_credential_sha256=credential.digest,issued_at=C.stamp(NOW),expires_at=C.stamp(NOW+timedelta(days=1))))
    grant=A.GrantDocument(body_bytes=body,signature=e.owner.sign(A.grant_signing_bytes(body)))
    installed=proposal('AUTHORITY_INSTALLED',dict(grant=document(A.grant_bytes(grant)),
        config_sha256=e.installation.config_sha256,initial_credential=document(A.credential_bytes(credential)),
        enrollment_request=document(C.enrollment_bytes(w.request)),registration=document(C.registration_bytes(w.response)),
        proof_request=document(C.proof_request_bytes(w.proof)),proof=document(A.evidence_bytes(evidence))))
    result=push(e,installed)
    e.w,e.credential,e.grant,e.proposal=w,credential,grant,p
    return result


def notification(e,*,request_id=None,application_id=None,kind,status,at=NOW):
    identity=dict(authority_id=e.installation.authority_id,request_id=request_id,
                  application_id=application_id,kind=kind)
    return dict(schema=1,intent_id=A.record_digest('notification-id',A.canonical(identity)),
                **identity,status=status,created_at=C.stamp(at))


def revoke_request(e):
    body=dict(schema=1,request_id='e'*64,authority_id=e.installation.authority_id,
        grant_sha256=e.grant.digest,registry_epoch=1,kind='REVOKE_CREDENTIAL',
        target=dict(credential_sha256=e.credential.credential_sha256,reason='OWNER_WITHDRAWN'),
        requested_at=C.stamp(NOW),challenge_expires_at=C.stamp(NOW+timedelta(seconds=30)),
        approval_expires_at=None,nonce=C.b64(b'n'*32))
    display={k:body[k] for k in ('schema','authority_id','kind','target','requested_at',
                                'challenge_expires_at','approval_expires_at')}
    body['display_sha256']=A.record_digest('display',A.canonical(display))
    digest=A.record_digest('request',A.canonical(body))
    body.update(request_sha256=digest,challenge=C.b64(hashlib.sha256(
        b'tradegen-passkey-archive/challenge/1\n'+b'n'*32+bytes.fromhex(digest)).digest()))
    request=A.parse_request(A.canonical(body))
    push(e,proposal('REQUEST_OPENED',dict(request=body,notification=notification(e,
        request_id=request.request_id,kind='REQUEST_READY',status='PENDING'))))
    return request


def revoke_event(e,request,*,at=NOW,signature=None):
    context=C.AssertionContext(purpose='REVOKE_CREDENTIAL',request_id=request.request_id,
        request_sha256=request.request_sha256,rp=e.credential.material().rp,challenge=request.challenge,
        user_handle=e.credential.user_handle,credential=e.credential.material(),
        requested_at=NOW,expires_at=request.challenge_expires_at)
    signer=SimpleNamespace(context=context,key=e.w.key)
    assertion=WF.assertion(signer,counter=2)
    if signature is not None: assertion=replace(assertion,signature=signature)
    evidence=A.WebAuthnEvidence(request_sha256=request.request_sha256,assertion=assertion,received_at=NOW)
    return proposal('CREDENTIAL_REVOKED',dict(request_sha256=request.request_sha256,
        evidence=document(A.evidence_bytes(evidence)),credential_sha256=e.credential.credential_sha256,
        reason='OWNER_WITHDRAWN',new_registry_epoch=2,notification=notification(e,
        request_id=request.request_id,kind='CREDENTIAL_RESULT',status='APPLIED',at=at)),at=at)


def test_explicit_empty_preparation_and_reopen_bind_real_roots_and_never_seed_runtime():
    with fixture(prepared=False) as e:
        before=files(e.base)
        refused(e.ledger.inspect,'PASSKEY_BOOTSTRAP_REQUIRED')
        assert files(e.base)==before
        e.ledger=L.prepare_authority_store(**e.args)
        current=e.ledger.inspect(); reopened=L.AuthorityLedger(**e.args).inspect()
        assert current==reopened and current.head.sequence==0 and not current.state.events
        assert (e.roots.primary/'journal.jsonl').read_bytes()==b''
        before=files(e.base)
        refused(lambda:L.prepare_authority_store(**e.args),'PASSKEY_BOOTSTRAP_REQUIRED')
        assert files(e.base)==before


def test_append_backup_head_and_exact_last_row_retry_survive_new_object():
    with fixture() as e:
        event=enrollment_event(e); old=e.ledger.inspect().head
        with e.ledger.operation() as op: first=op.commit(event,expected_head=old)
        before=files(e.base)
        reopened=L.AuthorityLedger(**e.args)
        with reopened.operation() as op: retried=op.commit(event,expected_head=old)
        assert retried==first and first.head.sequence==1 and files(e.base)==before
        raw=(e.roots.primary/'journal.jsonl').read_bytes()
        assert (e.roots.backup/'versions'/(first.head.sha256+'.json')).read_bytes()==raw[:-1]


def test_genuine_fractional_unicode_owner_and_registration_proof_grant_replay():
    with fixture() as e:
        first=bootstrap(e)
        assert b'0.5' in e.evidence.log_bytes and '합성'.encode() in e.evidence.log_bytes
        reopened=L.AuthorityLedger(**e.args).inspect()
        assert reopened==first and reopened.state.credentials[0].last_counter==1
        assert reopened.state.grant==e.grant and reopened.state.registry_epoch==1


def test_genuine_self_revoke_uses_prefix_counter_and_exact_effect_once_on_restart():
    with fixture() as e:
        bootstrap(e); request=revoke_request(e); event=revoke_event(e,request)
        old=e.ledger.inspect().head
        with e.ledger.operation() as op: applied=op.commit(event,expected_head=old)
        assert applied.state.credentials[0].state=='REVOKED' and applied.state.credentials[0].last_counter==2
        assert applied.state.registry_epoch==2 and applied.state.requests[0].state=='APPLIED'
        before=files(e.base)
        with L.AuthorityLedger(**e.args).operation() as op: retried=op.commit(event,expected_head=old)
        assert retried==applied and files(e.base)==before


def test_real_bad_signature_does_not_consume_request_or_write_any_bytes():
    with fixture() as e:
        bootstrap(e); request=revoke_request(e)
        event=revoke_event(e,request,signature=b'\0'*64)
        before=files(e.base)
        refused(lambda:push(e,event),'PASSKEY_SIGNATURE_INVALID')
        assert files(e.base)==before and e.ledger.inspect().state.requests[0].state=='PENDING'


def test_received_in_time_but_committed_after_challenge_expiry_is_refused():
    with fixture() as e:
        bootstrap(e); request=revoke_request(e)
        event=revoke_event(e,request,at=request.challenge_expires_at)
        before=files(e.base)
        refused(lambda:push(e,event),'PASSKEY_EXPIRED')
        assert files(e.base)==before


def test_arbitrary_state_cannot_invent_registered_credential_or_skip_crypto():
    with fixture() as e:
        actual=bootstrap(e).state
        forged=replace(actual,credentials=(replace(actual.credentials[0],last_counter=0),))
        raw_event=proposal('OWNER_CHECKPOINT_ADVANCED',{'evidence':A.owner_evidence_document(e.evidence)})
        unsigned=dict(schema=1,sequence=len(actual.events)+1,previous_sha256=actual.events[-1].row_sha256,
            observed_at=C.stamp(NOW),kind=raw_event.kind,payload=document(raw_event.payload_bytes))
        event=A.parse_event(A.canonical(unsigned|{'row_sha256':A.record_digest('authority-event',A.canonical(unsigned))}))
        refused(lambda:R.validate_transition(forged,event,installation=e.installation,limits=e.limits),
                'PASSKEY_FORMAT_INVALID')


def test_same_owner_checkpoint_is_noop_but_actual_signed_growth_is_retained():
    with fixture() as e:
        event=proposal('OWNER_CHECKPOINT_ADVANCED',{'evidence':A.owner_evidence_document(e.evidence)})
        first=push(e,event); before=files(e.base)
        again=push(e,proposal(event.kind,document(event.payload_bytes),at=NOW+timedelta(seconds=1)))
        assert again==first and files(e.base)==before
        raw,digest=S.entry_line(e.owner,4,e.evidence.head.sha256,'code_approved',
            dict(sha256='b'*64,files=[['changed.py','c'*64]]),NOW.strftime('%Y-%m-%dT%H:%M:%SZ'))
        next_evidence=replace(e.evidence,log_bytes=e.evidence.log_bytes+raw,
            head=A.Head(sequence=4,sha256=digest),observed_at=NOW+timedelta(seconds=1),
            completed_at=NOW+timedelta(seconds=1))
        saved=push(e,proposal(event.kind,{'evidence':A.owner_evidence_document(next_evidence)},
                             at=NOW+timedelta(seconds=1)))
        assert L.AuthorityLedger(**e.args).inspect()==saved and saved.state.owner_evidence.head.sequence==4


def test_missing_head_and_each_single_store_rollback_refuse_without_repair():
    for target in ('journal','backup','head'):
        with fixture() as e:
            old=(e.ledger._head_dir/'head.json').read_bytes()
            result=push(e,enrollment_event(e))
            if target=='journal': (e.roots.primary/'journal.jsonl').write_bytes(b'')
            elif target=='backup': (e.roots.backup/'versions'/(result.head.sha256+'.json')).unlink()
            else: (e.ledger._head_dir/'head.json').write_bytes(old)
            before=files(e.base)
            refused(lambda:L.AuthorityLedger(**e.args).inspect(),'PASSKEY_STORE_INDETERMINATE')
            assert files(e.base)==before


def test_failure_after_primary_append_preserves_unpublished_row_and_refuses_restart():
    with fixture() as e:
        real=L._new
        def fail_backup(pin,name,raw):
            if pin.path==e.roots.backup/'versions': raise OSError('synthetic disk failure')
            return real(pin,name,raw)
        old=e.ledger.inspect().head
        with patch.object(L,'_new',fail_backup): refused(lambda:push(e,enrollment_event(e)), 'PASSKEY_STORE_INDETERMINATE')
        assert (e.roots.primary/'journal.jsonl').read_bytes().endswith(b'\n')
        assert document((e.ledger._head_dir/'head.json').read_bytes())['sha256']==old.sha256
        before=files(e.base)
        refused(lambda:L.AuthorityLedger(**e.args).inspect(),'PASSKEY_STORE_INDETERMINATE')
        assert files(e.base)==before


def test_full_row_and_backup_without_head_are_not_automatically_adopted():
    with fixture() as e:
        with patch.object(L._Operation,'_head',side_effect=OSError('synthetic head fault')):
            refused(lambda:push(e,enrollment_event(e)),'PASSKEY_STORE_INDETERMINATE')
        assert len(tuple((e.roots.backup/'versions').iterdir()))==1
        before=files(e.base)
        refused(lambda:L.AuthorityLedger(**e.args).inspect(),'PASSKEY_STORE_INDETERMINATE')
        assert files(e.base)==before


def test_post_head_response_loss_returns_same_actual_row_without_reappend():
    with fixture() as e:
        old=e.ledger.inspect().head; event=enrollment_event(e); real=L._Operation._head
        def lost(op,*args):
            real(op,*args)
            raise OSError('synthetic response loss after durable publication')
        with patch.object(L._Operation,'_head',lost): refused(lambda:push(e,event),'PASSKEY_STORE_INDETERMINATE')
        before=files(e.base)
        with L.AuthorityLedger(**e.args).operation() as op: result=op.commit(event,expected_head=old)
        assert result.head.sequence==1 and files(e.base)==before


def test_changed_predecessor_during_temp_fsync_is_not_overwritten():
    with fixture() as e:
        real=L._new
        def changed(pin,name,raw):
            real(pin,name,raw)
            if name=='head.tmp': (e.ledger._head_dir/'head.json').write_bytes(b'{}')
        with patch.object(L,'_new',changed): refused(lambda:push(e,enrollment_event(e)), 'PASSKEY_STORE_INDETERMINATE')
        assert (e.ledger._head_dir/'head.json').read_bytes()==b'{}'
        assert (e.ledger._head_dir/'head.tmp').exists()


def test_operation_lock_lifetime_cross_object_and_body_error_preservation():
    with fixture() as e:
        with e.ledger.operation() as op:
            refused(lambda:L.AuthorityLedger(**e.args).inspect(),'PASSKEY_STORE_INDETERMINATE')
            op.check()
        refused(op.check,'PASSKEY_STORE_INDETERMINATE')
        def body():
            with e.ledger.operation(): raise C.PasskeyError('PASSKEY_SIGNATURE_INVALID')
        refused(body,'PASSKEY_SIGNATURE_INVALID')
        assert e.ledger.inspect().head.sequence==0


def test_actual_operation_lock_replacement_is_detected_before_nested_store_read():
    with fixture() as e:
        def operation():
            with e.ledger.operation() as op:
                path=e.roots.primary/'operation.lock'; path.rename(path.with_suffix('.old'))
                path.write_bytes(b'0')
                op.load()
        refused(operation,'PASSKEY_STORE_INDETERMINATE')


def test_record_quota_and_stale_expected_head_refuse_before_writes():
    with fixture(limits=L.LedgerLimits(max_events=1)) as e:
        old=e.ledger.inspect().head; push(e,enrollment_event(e)); before=files(e.base)
        with e.ledger.operation() as op:
            refused(lambda:op.commit(enrollment_event(e,2),expected_head=old),'PASSKEY_REGISTRY_CHANGED')
            refused(lambda:op.commit(enrollment_event(e,2),expected_head=op.load().head),'PASSKEY_RESOURCE_LIMIT')
        assert files(e.base)==before


def test_hardlink_and_symlink_aliases_refuse_actual_disk_without_following():
    with fixture() as e:
        result=push(e,enrollment_event(e)); path=e.roots.backup/'versions'/(result.head.sha256+'.json')
        link=e.base/'outside.json'; os.link(path,link)
        refused(e.ledger.inspect,'PASSKEY_STORE_INDETERMINATE')
        link.unlink(); path.unlink(); path.symlink_to(e.roots.primary/'journal.jsonl')
        refused(e.ledger.inspect,'PASSKEY_STORE_INDETERMINATE')


def test_bounded_streaming_replay_does_not_validate_every_prior_prefix():
    with fixture() as e:
        def rows(count):
            result=[]; previous=e.ledger.genesis_digest
            for n in range(1,count+1):
                event=enrollment_event(e,n)
                body=dict(schema=1,sequence=n,previous_sha256=previous,observed_at=C.stamp(NOW),
                          kind=event.kind,payload=document(event.payload_bytes))
                previous=A.record_digest('authority-event',A.canonical(body))
                result.append(A.canonical(body|{'row_sha256':previous}))
            return tuple(result)
        small,large=rows(24),rows(48); original=A._payload
        counts=[]
        for raw in (small,large):
            with patch.object(A,'_payload',wraps=original) as calls:
                state=R.replay_events(raw,installation=e.installation,limits=e.limits)
            assert len(state.events)==len(raw)
            counts.append(calls.call_count)
        assert counts[1]<=counts[0]*2+20,counts


def test_arbitrary_oversized_event_tuple_is_rejected_before_encoding_children():
    with fixture() as e:
        state=e.ledger.inspect().state
        object.__setattr__(state,'events',(object(),)*(e.limits.max_events+1))
        event=enrollment_event(e)
        body=dict(schema=1,sequence=1,previous_sha256=e.ledger.genesis_digest,observed_at=C.stamp(NOW),
                  kind=event.kind,payload=document(event.payload_bytes))
        row=A.parse_event(A.canonical(body|{'row_sha256':A.record_digest('authority-event',A.canonical(body))}))
        with patch.object(A,'event_bytes',side_effect=AssertionError('must admit count before encoding')):
            refused(lambda:R.validate_transition(state,row,installation=e.installation,limits=e.limits),
                    'PASSKEY_RESOURCE_LIMIT')


def test_exact_journal_backup_event_and_state_byte_boundaries_are_admitted_before_write():
    with fixture() as e:
        snapshot=push(e,enrollment_event(e))
        row=(e.roots.primary/'journal.jsonl').read_bytes()
        sizes=dict(max_journal_bytes=len(row),max_backup_bytes=len(row)-1,
                   max_event_bytes=len(row),max_state_bytes=len(R._state_bytes(snapshot.state,limits=e.limits)))
    for field,exact in sizes.items():
        for delta in (-1,0):
            with fixture(limits=L.LedgerLimits(**{field:exact+delta})) as e:
                before=files(e.base)
                if delta<0:
                    refused(lambda:push(e,enrollment_event(e)),'PASSKEY_RESOURCE_LIMIT')
                    assert files(e.base)==before
                else:
                    result=push(e,enrollment_event(e))
                    assert result.head.sequence==1


def test_interrupted_actual_partial_append_is_preserved_and_never_retried_as_unused():
    with fixture() as e:
        def partial(op,line,size):
            path=e.roots.primary/'journal.jsonl'
            with path.open('ab') as stream:
                stream.write(line[:len(line)//2]);stream.flush();os.fsync(stream.fileno())
            raise OSError('synthetic interrupted append')
        with patch.object(L._Operation,'_append',partial):
            refused(lambda:push(e,enrollment_event(e)),'PASSKEY_STORE_INDETERMINATE')
        raw=(e.roots.primary/'journal.jsonl').read_bytes()
        assert raw and not raw.endswith(b'\n')
        before=files(e.base)
        refused(lambda:L.AuthorityLedger(**e.args).inspect(),'PASSKEY_STORE_INDETERMINATE')
        assert files(e.base)==before


def test_replay_work_holds_no_writer_or_head_lock_during_actual_crypto():
    with fixture() as e:
        bootstrap(e)
        real_lock=L._lock; real_verify=W.verify_assertion; active=[]; verified=[]
        @contextmanager
        def lock(pin,name):
            with real_lock(pin,name):
                active.append(name)
                try: yield
                finally: active.remove(name)
        def verification(*args,**kwargs):
            assert active==['operation.lock'],active
            result=real_verify(*args,**kwargs)
            verified.append(result)
            return result
        with patch.object(L,'_lock',lock),patch.object(W,'verify_assertion',verification):
            result=L.AuthorityLedger(**e.args).inspect()
        assert verified and result.state.credentials[0].last_counter==1


def test_request_notification_replay_work_is_linear_over_actual_verified_prefix():
    with fixture() as e:
        bootstrap(e)
        request=revoke_request(e)
        prefix=tuple((e.roots.primary/'journal.jsonl').read_bytes().split(b'\n')[:-1])
        def rows(count):
            result=list(prefix[:-1]); previous=A.parse_event(result[-1]).row_sha256
            original=document(request.raw)
            for number in range(count):
                body=dict(original);body['request_id']=format(number+100,'064x')
                body['nonce']=C.b64((number+100).to_bytes(32,'big'))
                core={k:v for k,v in body.items() if k not in ('request_sha256','challenge')}
                digest=A.record_digest('request',A.canonical(core));body['request_sha256']=digest
                body['challenge']=C.b64(hashlib.sha256(b'tradegen-passkey-archive/challenge/1\n'
                    +(number+100).to_bytes(32,'big')+bytes.fromhex(digest)).digest())
                actual=A.parse_request(A.canonical(body))
                payload=dict(request=body,notification=notification(e,request_id=actual.request_id,
                    kind='REQUEST_READY',status='PENDING'))
                row=dict(schema=1,sequence=len(result)+1,previous_sha256=previous,observed_at=C.stamp(NOW),
                         kind='REQUEST_OPENED',payload=payload)
                previous=A.record_digest('authority-event',A.canonical(row))
                result.append(A.canonical(row|{'row_sha256':previous}))
            return tuple(result)
        small,large=rows(12),rows(24); original=A._notification_body; counts=[]; owner_counts=[]
        owner_lines={line.decode() for line in e.evidence.log_bytes.split(b'\n') if line}
        original_json=R.json.loads
        for raw in (small,large):
            owner_parses=[]
            def decoding(value,*args,**kwargs):
                text=value.decode() if type(value) is bytes else value
                if type(text) is str and text.rstrip('\n') in owner_lines: owner_parses.append(True)
                return original_json(value,*args,**kwargs)
            with (patch.object(A,'_notification_body',wraps=original) as calls,
                  patch.object(R.json,'loads',decoding)):
                result=R.replay_events(raw,installation=e.installation,limits=e.limits)
            assert len(result.events)==len(raw)
            counts.append(calls.call_count)
            owner_counts.append(len(owner_parses))
        assert counts[1]<=counts[0]*2+20,counts
        assert owner_counts[0]>0 and owner_counts[0]==owner_counts[1],owner_counts
