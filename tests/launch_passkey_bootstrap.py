"""Disposable genuine WebAuthn possession and Ed25519 grant tests; no device claim."""
from dataclasses import replace
from contextlib import contextmanager,redirect_stdout
from datetime import datetime,timedelta
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import sys
from types import SimpleNamespace
from unittest.mock import patch

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from tools.approval_broker import authority_contract as A, bootstrap as B, contract as C
from tests import launch_passkey_webauthn as W
from tests.launch_passkey_contract import NOW, refused


def proposal():
    e = W.fixture()
    assertion = W.assertion(e)
    actual = W.V.verify_assertion(e.context,assertion,now=NOW)
    evidence = A.WebAuthnEvidence(request_sha256=e.proof.digest,assertion=assertion,received_at=NOW)
    m = e.registration.credential
    credential = A.Credential(credential_id=m.credential_id,credential_sha256=m.credential_sha256,
        public_key_cose=m.public_key_cose,algorithm=-7,user_handle=m.user_handle,
        rp_id=m.rp.rp_id,origin=m.rp.origin,registration_evidence_sha256=m.registration_evidence_sha256,
        proof_evidence_sha256=evidence.digest,created_at=NOW,backup_eligible=actual.backup_eligible,
        last_backed_up=actual.backed_up,last_counter=actual.counter,state='ACTIVE',revoked_at=None)
    return A.BootstrapProposal(enrollment=e.request,registration=e.response,registration_received_at=NOW,
        proof_request=e.proof,proof=evidence,initial_credential=credential)


def config():
    return A.BrokerConfig(authority_id='a'*64,service_identity='synthetic-service',
        client_identity='synthetic-client',pipe_name='synthetic-passkey',
        authority_root='/synthetic/authority',backup_root='/synthetic/backup',head_root='/synthetic/head',
        packet_inbox='/synthetic/packets',app_repo='/synthetic/repo',rp_origin='https://approve.test',
        rp_id='approve.test',rp_transport_spki_sha256='1'*64,broker_transport_public_key=b't'*32,
        broker_mtls_spki_sha256='2'*64)


def grant_fixture():
    p = proposal()
    key = Ed25519PrivateKey.generate()
    checkpoint = A.OwnerCheckpoint(fingerprint='SHA256:'+hashlib.sha256(key.public_key().public_bytes_raw()).hexdigest(),
        code_sha256='d'*64,owner_head=A.Head(sequence=1,sha256='e'*64),observed_at=NOW)
    # These are deliberately inert builder arguments, not verified release/owner claims.
    broker = A.ReleaseManifest(role='BROKER',python_version='test-only',files=(
        A.FileDigest(name='fixture.txt',byte_count=1,sha256=hashlib.sha256(b'x').hexdigest()),),dependencies=())
    rp = replace(broker,role='RP')
    body = B.build_grant_body(p,config=config(),broker_release=broker,rp_release=rp,
        owner=checkpoint,recovery_fingerprint=checkpoint.fingerprint,issued_at=NOW,expires_at=NOW+timedelta(days=1))
    return p,key,body


def test_actual_registration_and_separate_possession_are_reverified_from_original_bytes():
    p = proposal()
    registration, assertion = W.V.verify_registration, W.V.verify_assertion
    with patch.object(W.V,'verify_registration',wraps=registration) as reg, \
         patch.object(W.V,'verify_assertion',wraps=assertion) as proof:
        result = B.verify_bootstrap(p)
    assert A.credential_bytes(result) == A.credential_bytes(p.initial_credential)
    assert reg.call_count == proof.call_count == 1
    assert reg.call_args.kwargs['now'] == p.registration_received_at
    assert proof.call_args.kwargs['now'] == p.proof.received_at


def test_initial_credential_binds_key_registration_proof_time_and_counter():
    p = proposal()
    for c in (replace(p.initial_credential,last_counter=p.initial_credential.last_counter+1),
              replace(p.initial_credential,created_at=NOW+timedelta(microseconds=1)),
              replace(p.initial_credential,proof_evidence_sha256='f'*64),
              replace(p.initial_credential,registration_evidence_sha256='f'*64)):
        refused(lambda:B.verify_bootstrap(replace(p,initial_credential=c)),'PASSKEY_TARGET_CHANGED')


def test_full_credential_digest_is_not_the_identifier_digest():
    p,key,body = grant_fixture()
    value = json.loads(body)
    assert value['initial_credential_sha256'] == A.record_digest('credential',A.credential_bytes(p.initial_credential))
    assert value['initial_credential_sha256'] != p.initial_credential.credential_sha256


def test_real_grant_signature_is_separate_from_owner_and_archive_domains():
    _,key,body = grant_fixture()
    raw = key.public_key().public_bytes_raw()
    document = A.GrantDocument(body_bytes=body,signature=key.sign(A.grant_signing_bytes(body)))
    B.verify_grant_document(document,signer_public_key_raw=raw)
    for domain in (b'tradegen-owner-log/1\n',b'tradegen-research-archive-attestation/1\n'):
        wrong = replace(document,signature=key.sign(domain+body))
        refused(lambda:B.verify_grant_document(wrong,signer_public_key_raw=raw),'PASSKEY_SIGNATURE_INVALID')
    refused(lambda:B.verify_grant_document(document,signer_public_key_raw=Ed25519PrivateKey.generate().public_key().public_bytes_raw()),
            'PASSKEY_SIGNATURE_INVALID')


def test_proof_signature_and_origin_are_checked_despite_rehashed_public_documents():
    p = proposal()
    original = p.proof.assertion
    broken = replace(original,signature=original.signature[:-1]+bytes((original.signature[-1]^1,)))
    evidence = replace(p.proof,assertion=broken)
    changed = replace(p,proof=evidence,initial_credential=replace(p.initial_credential,proof_evidence_sha256=evidence.digest))
    refused(lambda:B.verify_bootstrap(changed),'PASSKEY_SIGNATURE_INVALID')


def test_historical_proof_time_is_bound_without_relabeling_as_current_authentication():
    p = proposal()
    # No current-time callback exists: same historical original verifies later.
    assert B.verify_bootstrap(p).created_at == NOW
    evidence = replace(p.proof,received_at=p.proof_request.expires_at)
    changed = replace(p,proof=evidence,initial_credential=replace(p.initial_credential,proof_evidence_sha256=evidence.digest))
    refused(lambda:B.verify_bootstrap(changed),'PASSKEY_EXPIRED')


def test_bootstrap_authority_epoch_and_grant_cannot_be_promoted():
    p = proposal()
    other = replace(p.proof_request,authority_id='f'*64)
    refused(lambda:B.verify_bootstrap(replace(p,proof_request=other)))
    other = replace(p.enrollment,grant_sha256='f'*64,registry_epoch=1)
    refused(lambda:B.verify_bootstrap(replace(p,enrollment=other)))


def test_disable_has_independent_real_recovery_signature():
    key = Ed25519PrivateKey.generate()
    body = C.encoded({'schema':1,'purpose':'passkey_archive_authority_disable','authority_id':'a'*64,
        'grant_sha256':'b'*64,'expected_head':{'sequence':5,'sha256':'c'*64},'reason':'DEVICE_LOST',
        'issued_at':C.stamp(NOW),'expires_at':C.stamp(NOW+timedelta(seconds=300))})
    document = A.DisableDocument(body_bytes=body,signature=key.sign(A.disable_signing_bytes(body)))
    B.verify_disable_document(document,recovery_public_key_raw=key.public_key().public_bytes_raw())
    refused(lambda:B.verify_disable_document(replace(document,signature=key.sign(b'tradegen-owner-log/1\n'+body)),
        recovery_public_key_raw=key.public_key().public_bytes_raw()),'PASSKEY_SIGNATURE_INVALID')


def test_builder_never_accepts_verified_result_boolean_or_private_key_argument():
    refused(lambda:B.verify_bootstrap(True))
    p,key,body = grant_fixture()
    assert json.loads(body)['approval_scope'] == 'archive_manifest_identity'
    assert 'ready' not in json.loads(body) and 'execution_ready' not in json.loads(body)


@contextmanager
def copied_signer(e, *, key=None, confirmed=None):
    """Actual copied handler, not a native terminal or installed -I CLI claim.

    Only disposable-key unlock, typed input and the test clock are substituted.
    Owner/release/config/ledger/crypto/output are the actual production paths.
    """
    from tools.signer import sign as original
    path=e.base/'independent-sign.py'
    shutil.copyfile(Path(original.__file__),path)
    name='_disposable_passkey_signer_'+hashlib.sha256(str(path).encode()).hexdigest()[:16]
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module
    spec.loader.exec_module(module)
    class TestClock(datetime):
        @classmethod
        def now(cls,tz=None):
            return e.clock() if tz is None else e.clock().astimezone(tz)
    def typed(prompt):
        value=prompt.rsplit(': ',1)[1].split('\n')[0]
        if confirmed is not None:
            confirmed()
        return value,[n*.05 for n in range(len(value))]
    output=io.StringIO()
    try:
        with patch.dict(os.environ,{'TRADEGEN_HOME':str(e.base)}), \
             patch.object(module,'datetime',TestClock), \
             patch.object(module,'_read_typed',side_effect=typed), \
             patch.object(module,'_unlock',return_value=e.recovery_key if key is None else key), \
             redirect_stdout(output):
            yield module,output
    finally:
        sys.modules.pop(name,None)


def disable_args(e, *, key='explicit-disposable-recovery-key.enc', seconds=300):
    return SimpleNamespace(config=str(e.config_path),key=key,reason='DEVICE_LOST',
        expires_at=C.stamp(e.clock()+timedelta(seconds=seconds)),output=str(e.base/'disable.json'))


def displayed_body(output):
    text=output.getvalue()
    return json.JSONDecoder().raw_decode(text[text.index('{'):])[0]


def test_actual_copied_recovery_handler_signs_same_displayed_body_and_does_not_apply():
    from tests.passkey_authority_fixtures import fixture
    with fixture(target_app_clone=True) as e:
        before=e.ledger.inspect()
        args=disable_args(e)
        with copied_signer(e) as (signer,output):
            assert signer._cmd_archive_authority_disable(args)==0
        document=A.parse_disable(Path(args.output).read_bytes())
        B.verify_disable_document(document,recovery_public_key_raw=e.recovery_public)
        assert document.body==displayed_body(output)
        assert A.parse_head(document.body['expected_head'])==before.head
        assert e.ledger.inspect().head==before.head and not e.ledger.inspect().state.disabled
        result=e.engine.install_disable(A.disable_bytes(document))
        assert result.status=='APPLIED' and e.ledger.inspect().state.disabled


def test_recovery_handler_does_not_require_an_active_passkey_after_genuine_self_revoke():
    from tests.passkey_authority_fixtures import fixture
    with fixture(target_app_clone=True) as e:
        request=e.engine.open_revoke_request(e.credential.credential_sha256,reason='DEVICE_LOST')
        result=e.engine.submit_assertion(C.assertion_bytes(e.issue_assertion(request,counter=2)))
        assert result.status=='APPLIED'
        assert all(c.state=='REVOKED' for c in e.ledger.inspect().state.credentials)
        args=disable_args(e)
        with copied_signer(e) as (signer,output):
            assert signer._cmd_archive_authority_disable(args)==0
        document=A.parse_disable(Path(args.output).read_bytes())
        B.verify_disable_document(document,recovery_public_key_raw=e.recovery_public)
        assert e.engine.install_disable(A.disable_bytes(document)).status=='APPLIED'


def test_owner_key_is_not_an_implicit_recovery_key_and_missing_explicit_key_refuses():
    from tests.passkey_authority_fixtures import fixture
    with fixture(target_app_clone=True) as e:
        args=disable_args(e)
        with copied_signer(e,key=e.root_key) as (signer,output):
            refused(lambda:signer._cmd_archive_authority_disable(args),'PASSKEY_RECOVERY_KEY_REQUIRED')
            args.key=None
            refused(lambda:signer._cmd_archive_authority_disable(args),'PASSKEY_RECOVERY_KEY_REQUIRED')
            for root in (e.locations.app_environment,*e.dependency_roots):
                refused(lambda:signer._passkey_output(root/'passkey-must-not-be-created.json',e.operator_installation),
                        'PASSKEY_OUTPUT_REFUSED')
        assert not Path(args.output).exists()


def test_recovery_handler_refuses_real_ledger_growth_after_exact_typed_confirmation():
    from tests.passkey_authority_fixtures import fixture
    with fixture(target_app_clone=True) as e:
        before=e.ledger.inspect().head
        def changed():
            e.engine.open_revoke_request(e.credential.credential_sha256,reason='DEVICE_LOST')
        args=disable_args(e)
        with copied_signer(e,confirmed=changed) as (signer,output):
            refused(lambda:signer._cmd_archive_authority_disable(args),'PASSKEY_TARGET_CHANGED')
        assert e.ledger.inspect().head!=before and not Path(args.output).exists()
        assert A.parse_head(displayed_body(output)['expected_head'])==before


def test_recovery_handler_refuses_changed_pinned_configuration_after_confirmation():
    from tests.passkey_authority_fixtures import fixture
    with fixture(target_app_clone=True) as e:
        def changed():
            body=json.loads(e.sidecar_path.read_bytes())
            body['trust_roots']['recovery_public_key_raw']=C.b64(Ed25519PrivateKey.generate().public_key().public_bytes_raw())
            e.sidecar_path.write_bytes(A.canonical(body))
        args=disable_args(e)
        with copied_signer(e,confirmed=changed) as (signer,output):
            refused(lambda:signer._cmd_archive_authority_disable(args),'PASSKEY_INSTALLATION_CHANGED')
        assert not Path(args.output).exists()


def test_recovery_handler_never_restamps_an_expired_confirmed_body():
    from tests.passkey_authority_fixtures import fixture
    with fixture(target_app_clone=True) as e:
        original=e.clock()
        args=disable_args(e)
        def delayed():
            e.clock_cell[0]+=timedelta(seconds=300)
        with copied_signer(e,confirmed=delayed) as (signer,output):
            refused(lambda:signer._cmd_archive_authority_disable(args),'PASSKEY_EXPIRED')
        assert not Path(args.output).exists()
        assert C.time_value(displayed_body(output)['issued_at'])==original


def test_actual_copied_grant_handler_signs_exact_body_shown_before_confirmation():
    from tests.passkey_authority_fixtures import fixture
    with fixture(target_app_clone=True) as e:
        proposal_path=e.base/'proposal.json';proposal_path.write_bytes(A.proposal_bytes(e.proposal))
        args=SimpleNamespace(config=str(e.config_path),proposal=str(proposal_path),key='disposable-owner.enc',
            expires_at=C.stamp(e.clock()+timedelta(days=1)),output=str(e.base/'grant.json'))
        before=e.ledger.inspect().head
        def delayed():
            e.clock_cell[0]+=timedelta(seconds=1)
        with copied_signer(e,key=e.root_key,confirmed=delayed) as (signer,output):
            assert signer._cmd_archive_authority_grant(args)==0
        document=A.parse_grant(Path(args.output).read_bytes())
        B.verify_grant_document(document,signer_public_key_raw=e.root_public)
        assert document.body==displayed_body(output)
        assert C.time_value(document.body['issued_at'])<e.clock()
        assert e.ledger.inspect().head==before
