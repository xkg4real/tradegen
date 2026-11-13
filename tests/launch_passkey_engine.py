"""Engine orchestration using actual disposable owner, WebAuthn and disk facts.

The packet helper exports through the real app interpreter; broker source never
imports the app. All signatures and ledger/replay checks remain genuine. RP
release bytes are fixture commitments, not an operational HTTPS/IPC channel.
"""
from dataclasses import replace
from datetime import timedelta
import hashlib
from pathlib import Path
from unittest.mock import patch

from tools.approval_broker import authority_contract as A, contract as C
from tools.approval_broker import bootstrap as B, engine as E, ledger as L, owner_view as O
from tools.approval_broker import cli
from tests import passkey_authority_fixtures as F


def archive_request(e):
    return e.engine.open_archive_request(e.packet, approval_expires_at=e.clock()+timedelta(minutes=30))


def apply(e, request=None, *, counter=2):
    request = archive_request(e) if request is None else request
    assertion = e.issue_assertion(request,counter=counter)
    result = e.engine.submit_assertion(C.assertion_bytes(assertion))
    assert result.status == 'APPLIED' and result.application_id is not None
    F.engine_only(result)
    return request,assertion,result


def test_real_bootstrap_archive_apply_restart_exact_retry_and_current_engine_only():
    with F.fixture() as e:
        request,assertion,result = apply(e)
        old = e.ledger.inspect()
        e.engine = e.restart()
        repeated = e.engine.submit_assertion(C.assertion_bytes(assertion))
        assert repeated.status == 'EXACT_RETRY' and repeated.application_id == result.application_id
        assert e.ledger.inspect().head == old.head
        current = e.engine.read_current(result.application_id)
        assert current.status == 'ACTIVE' and current.packet_sha256 == e.packet_snapshot.packet_sha256
        F.engine_only(current)
        assert len(e.ledger.inspect().state.applications) == 1
        assert any(n.intent_id for n in e.engine.pending_notifications())
        F.engine_only(e.engine.inspect())


def test_unverified_assertion_does_not_consume_request_or_update_counter():
    with F.fixture() as e:
        request = archive_request(e)
        valid = e.issue_assertion(request)
        bad = replace(valid,signature=valid.signature[:-1]+bytes((valid.signature[-1]^1,)))
        before = e.ledger.inspect()
        F.refused(lambda:e.engine.submit_assertion(C.assertion_bytes(bad)), 'PASSKEY_SIGNATURE_INVALID')
        after = e.ledger.inspect()
        assert after.head == before.head and after.state.credentials == before.state.credentials
        assert next(r for r in after.state.requests if r.request.request_id==request.request_id).state == 'PENDING'
        assert e.engine.submit_assertion(C.assertion_bytes(valid)).status == 'APPLIED'


def test_second_different_genuine_assertion_is_not_exact_retry():
    with F.fixture() as e:
        request,_,result = apply(e)
        different = e.issue_assertion(request,counter=3)
        before = e.ledger.inspect()
        F.refused(lambda:e.engine.submit_assertion(C.assertion_bytes(different)), 'PASSKEY_REQUEST_REUSED')
        assert e.ledger.inspect().head == before.head
        assert len(e.ledger.inspect().state.applications) == 1


def test_actual_self_revoke_invalidates_unused_request_and_current_but_not_historical_retry():
    with F.fixture() as e:
        request,assertion,result = apply(e)
        unused = archive_request(e)
        revoke = e.engine.open_revoke_request(e.credential.credential_sha256,reason='OWNER_WITHDRAWN')
        revoked = e.engine.submit_assertion(C.assertion_bytes(e.issue_assertion(revoke,counter=3)))
        assert revoked.status == 'APPLIED' and revoked.application_id is None
        state = e.ledger.inspect().state
        assert state.registry_epoch == 2 and state.credentials[0].state == 'REVOKED'
        assert next(r for r in state.requests if r.request.request_id==unused.request_id).state == 'INVALIDATED'
        current = e.engine.read_current(result.application_id)
        assert current.status == 'REVOKED'
        F.engine_only(current)
        retry = e.restart().submit_assertion(C.assertion_bytes(assertion))
        assert retry.status == 'EXACT_RETRY' and retry.application_id == result.application_id
        F.engine_only(retry)


def test_recovery_disable_requires_exact_head_and_genuine_recovery_signature():
    with F.fixture() as e:
        _,_,result = apply(e)
        before = e.ledger.inspect()
        forged = F.disable_document(e,key=e.root_key)
        F.refused(lambda:e.engine.install_disable(A.disable_bytes(forged)), 'PASSKEY_SIGNATURE_INVALID')
        assert e.ledger.inspect().head == before.head
        signed = F.disable_document(e)
        archive_request(e)  # real successor invalidates the independently selected exact head
        F.refused(lambda:e.engine.install_disable(A.disable_bytes(signed)), 'PASSKEY_GRANT_INVALID')
        actual = F.disable_document(e)
        assert e.engine.install_disable(A.disable_bytes(actual)).status == 'APPLIED'
        assert e.engine.read_current(result.application_id).status == 'INVALIDATED'
        F.refused(lambda:archive_request(e),'PASSKEY_REVOKED')


def test_valid_restrictive_owner_head_is_persisted_before_deny_and_prevents_restart_rollback():
    with F.fixture() as e:
        _,_,result = apply(e)
        original = (e.compliance/'owner.jsonl').read_bytes()
        e.clock_cell[0] += timedelta(seconds=1)
        files = [['superseding-reviewed-code.py','f'*64]]
        changed = F.append_owner(e,'code_approved',dict(sha256=hashlib.sha256(C.encoded(files)).hexdigest(),files=files))
        F.refused(lambda:e.engine.read_current(result.application_id))
        persisted = e.ledger.inspect()
        assert persisted.state.owner_evidence.head == changed
        assert persisted.state.events[-1].kind == 'OWNER_CHECKPOINT_ADVANCED'
        (e.compliance/'owner.jsonl').write_bytes(original)
        F.refused(lambda:e.restart().read_current(result.application_id))
        assert e.ledger.inspect().head == persisted.head


def test_broken_owner_signature_is_never_persisted_as_a_checkpoint():
    with F.fixture() as e:
        _,_,result = apply(e)
        before = e.ledger.inspect()
        path = e.compliance/'owner.jsonl'
        raw = path.read_bytes()
        body = __import__('json').loads(raw.splitlines()[-1])
        # Preserve strict structure while corrupting the actual signed evidence.
        key = 'signature' if 'signature' in body else 'sig'
        assert key in body
        original = body[key]
        body[key] = ('A' if original[0]!='A' else 'B')+original[1:]
        path.write_bytes(C.encoded(body)+b'\n')
        F.refused(lambda:e.engine.read_current(result.application_id))
        assert e.ledger.inspect().head == before.head


def test_objective_expiry_closes_request_without_fabricating_an_application():
    with F.fixture() as e:
        request = archive_request(e)
        assertion = e.issue_assertion(request)
        e.clock_cell[0] = request.challenge_expires_at
        result = e.engine.submit_assertion(C.assertion_bytes(assertion))
        assert result.status == 'EXPIRED' and result.application_id is None
        state = e.ledger.inspect().state
        assert not state.applications
        assert next(r for r in state.requests if r.request.request_id==request.request_id).state == 'EXPIRED'


def test_actual_packet_modification_is_rejected_before_apply_and_on_current_read():
    with F.fixture() as e:
        request = archive_request(e)
        payload = next((e.packet/'payloads').iterdir())
        original = payload.read_bytes()
        payload.write_bytes(original+b'x')
        before = e.ledger.inspect()
        F.refused(lambda:e.engine.submit_assertion(C.assertion_bytes(e.issue_assertion(request))))
        assert e.ledger.inspect().head == before.head and not before.state.applications
        payload.write_bytes(original)
        _,_,result = apply(e,request)
        payload.write_bytes(original+b'x')
        F.refused(lambda:e.engine.read_current(result.application_id))
        assert len(e.ledger.inspect().state.applications) == 1


def test_exact_concrete_dispatch_ignores_instance_callbacks_and_checks_reader_start_watermark():
    with F.fixture() as e:
        e.owner_reader.observe = lambda **_: (_ for _ in ()).throw(AssertionError('instance callback used'))
        e.ledger.inspect = lambda: (_ for _ in ()).throw(AssertionError('instance ledger callback used'))
        e.ledger.operation = lambda: (_ for _ in ()).throw(AssertionError('instance operation callback used'))
        request = archive_request(e)
        assert request.kind == 'ARCHIVE_CONFIRM'
        now = e.clock_cell[0]
        e.clock_cell[0] = now+timedelta(seconds=5)
        e.engine._time()
        class SequenceClock(list):
            def __init__(self):
                self.values = iter((now+timedelta(seconds=1),now+timedelta(seconds=6)))
            def __getitem__(self,index):
                return next(self.values)
        e.clock_cell = SequenceClock()
        with L.AuthorityLedger.operation(e.ledger) as op:
            snapshot = op.load()
            F.refused(lambda:e.engine._owner(op,snapshot),'PASSKEY_CLOCK_INVALID')
            assert op.load().head == snapshot.head


def test_late_actual_owner_work_refuses_before_request_effect_and_preserves_original_observation():
    with F.fixture() as e:
        before = e.ledger.inspect()
        original = O.OwnerReader.observe
        first = []
        def delayed(reader, *, retained):
            value = original(reader,retained=retained)
            first.append(value.evidence.observed_at)
            if len(first)==1:
                e.clock_cell[0] += timedelta(seconds=31)
            return value
        with patch.object(O.OwnerReader,'observe',delayed):
            F.refused(lambda:archive_request(e),'PASSKEY_CLOCK_INVALID')
        assert len(first) == 1 and not e.ledger.inspect().state.requests
        assert e.ledger.inspect().head == before.head


def test_pending_bootstrap_proposal_export_uses_original_received_times_and_never_overwrites():
    with F.fixture(installed=False) as e:
        e.enrollment = e.engine.prepare_initial_enrollment()
        registration = F.registration(e.enrollment,e.credential_key,e.credential_id)
        proof = e.engine.submit_registration(e.enrollment.enrollment_id,C.registration_bytes(registration))
        assertion = e.issue_assertion(proof,counter=1)
        proposal = e.engine.submit_initial_proof(proof.request_id,C.assertion_bytes(assertion))
        output = e.base/'proposal.json'
        receipt = e.engine.export_grant_proposal(proposal.digest,output)
        assert output.read_bytes() == A.proposal_bytes(proposal)
        assert receipt.sha256 == hashlib.sha256(output.read_bytes()).hexdigest()
        assert B.verify_bootstrap(A.parse_proposal(output.read_bytes())) == proposal.initial_credential
        assert proposal.registration_received_at == proposal.initial_credential.created_at
        F.refused(lambda:e.engine.export_grant_proposal(proposal.digest,output),'PASSKEY_STORE_INDETERMINATE')
        assert e.ledger.inspect().state.grant is None
        F.engine_only(receipt)


def test_historical_proof_can_install_after_challenge_expiry_without_restamping_raw_evidence():
    with F.fixture(installed=False) as e:
        F.bootstrap(e,install=False)
        original = A.proposal_bytes(e.proposal)
        received = e.proposal.proof.received_at
        e.clock_cell[0] += timedelta(minutes=10)
        result = e.engine.install_grant(A.grant_bytes(e.grant),e.proposal.digest)
        assert result.status == 'APPLIED'
        state = e.ledger.inspect().state
        pending = next(p for p in state.enrollments if p.proposal_sha256==e.proposal.digest)
        assert pending.proof.received_at == received
        assert A.proposal_bytes(E.Engine._proposal(pending)) == original
        assert state.credentials[0].created_at == e.proposal.registration_received_at


def test_owner_checkpoint_quota_failure_is_indeterminate_and_never_an_active_success():
    with F.fixture() as e:
        _,_,result = apply(e)
        old = e.ledger.inspect()
        e.clock_cell[0] += timedelta(seconds=1)
        F.append_owner(e,'code_approved',dict(sha256=e.worker.report['owner_code_sha256'],
                                             files=e.worker.report['code_files']))
        original = L._Operation.commit
        def denied(operation,event,*,expected_head):
            if event.kind=='OWNER_CHECKPOINT_ADVANCED':
                raise C.PasskeyError('PASSKEY_RESOURCE_LIMIT')
            return original(operation,event,expected_head=expected_head)
        with patch.object(L._Operation,'commit',denied):
            F.refused(lambda:e.engine.read_current(result.application_id),'PASSKEY_STORE_INDETERMINATE')
        assert e.ledger.inspect().head == old.head


def test_operator_sidecar_is_exact_read_only_and_engine_open_does_not_claim_service_readiness():
    with F.fixture(installed=False) as e:
        before = {str(p.relative_to(e.base)):p.read_bytes() for p in e.base.rglob('*') if p.is_file()}
        installed = cli.load_installation(e.config_path)
        assert installed.ledger_installation == e.installation
        opened = E.Engine.open(e.config_path)
        summary = opened.inspect()
        assert summary.grant_sha256 is None and not summary.application_count
        F.engine_only(summary)
        assert {str(p.relative_to(e.base)):p.read_bytes() for p in e.base.rglob('*') if p.is_file()} == before
        raw = e.sidecar_path.read_bytes()
        extra = A.decode(raw)
        extra['ready'] = True
        e.sidecar_path.write_bytes(A.canonical(extra))
        F.refused(lambda:cli.load_installation(e.config_path),'PASSKEY_FORMAT_INVALID')
        F.refused(opened.inspect,'PASSKEY_FORMAT_INVALID')


def test_verified_future_code_change_crossed_during_final_configuration_never_returns_active():
    with F.fixture() as e:
        _,_,result = apply(e)
        now = e.clock_cell[0]
        files = [['future-reviewed-code.py','e'*64]]
        e.clock_cell[0] = now+timedelta(seconds=10)
        F.append_owner(e,'code_approved',dict(sha256=hashlib.sha256(C.encoded(files)).hexdigest(),files=files))
        e.clock_cell[0] = now
        original = E.Engine._configuration
        calls = []
        # Begin config, two release guards, final release guards, then the final
        # actual owner observer: advance only once that final owner has run.
        actual_owner = O.OwnerReader.observe
        seen = []
        def owner(reader,*,retained):
            observed = actual_owner(reader,retained=retained)
            seen.append(observed)
            return observed
        def configuration(engine):
            original(engine)
            calls.append(True)
            if len(seen)>=2:
                e.clock_cell[0] = now+timedelta(seconds=11)
        with patch.object(O.OwnerReader,'observe',owner), patch.object(E.Engine,'_configuration',configuration):
            F.refused(lambda:e.engine.read_current(result.application_id),'PASSKEY_OWNER_CHANGED')
        assert len(seen)==2 and calls
        assert e.ledger.inspect().state.owner_evidence.head.sequence == 2


def _cli_failure(exception):
    """Exercise CLI failure before any preparation effect, without an authority success double."""
    from contextlib import redirect_stdout
    from io import StringIO
    import json
    output = StringIO()
    with patch.object(cli,'load_installation',side_effect=exception), \
         patch.object(L,'prepare_authority_store',side_effect=AssertionError('preparation must not run')) as prepare, \
         redirect_stdout(output):
        exit_code = cli.main(['--config','/private/fixture-config.json','prepare-authority-store'])
    prepare.assert_not_called()
    assert exit_code == 2
    raw = output.getvalue()
    body = json.loads(raw)
    assert body['status'] == 'REFUSED'
    assert body['operational_channel_ready'] is body['current_use_eligible'] is body['execution_ready'] is False
    assert '/private/' not in raw
    return body['reason']


def test_cli_public_error_codes_pass_exactly_without_becoming_success():
    # This is the closed public protocol list, independent of the CLI mapping.
    codes = ('PASSKEY_PENDING PASSKEY_APPLIED PASSKEY_EXACT_RETRY PASSKEY_EXPIRED PASSKEY_REVOKED '
        'PASSKEY_GRANT_INVALID PASSKEY_REGISTRY_CHANGED PASSKEY_TARGET_CHANGED PASSKEY_ORIGIN_RP_INVALID '
        'PASSKEY_UV_REQUIRED PASSKEY_SIGNATURE_INVALID PASSKEY_REQUEST_REUSED PASSKEY_CLOCK_INVALID '
        'PASSKEY_OWNER_CHANGED PASSKEY_RESOURCE_LIMIT PASSKEY_STORE_INDETERMINATE PASSKEY_FORMAT_INVALID '
        'PASSKEY_CHANNEL_REFUSED PASSKEY_SCOPE_UNSUPPORTED PASSKEY_BOOTSTRAP_REQUIRED').split()
    for code in codes:
        assert _cli_failure(C.PasskeyError(code)) == code


def test_cli_known_internal_diagnostics_map_to_public_failure_domains():
    cases = (
        ('PASSKEY_PACKET_INVALID','PASSKEY_TARGET_CHANGED'),
        ('PASSKEY_RELEASE_CHANGED','PASSKEY_GRANT_INVALID'),
        ('PASSKEY_RELEASE_INVENTORY_CHANGED','PASSKEY_GRANT_INVALID'),
        ('PASSKEY_RELEASE_READ_REFUSED','PASSKEY_GRANT_INVALID'),
        ('PASSKEY_DEPLOYMENT_REFUSED','PASSKEY_OWNER_CHANGED'),
        ('PASSKEY_OWNER_PREFIX_INVALID','PASSKEY_OWNER_CHANGED'),
        ('PASSKEY_OWNER_KEY_CHANGED','PASSKEY_OWNER_CHANGED'),
        ('PASSKEY_OWNER_LOG_INVALID','PASSKEY_OWNER_CHANGED'),
        ('PASSKEY_OWNER_STALE','PASSKEY_CLOCK_INVALID'),
        ('PASSKEY_CLOCK_ROLLBACK','PASSKEY_CLOCK_INVALID'),
        ('PASSKEY_RUNTIME_UNSUPPORTED','PASSKEY_CHANNEL_REFUSED'),
        ('PASSKEY_LIBRARY_UNAVAILABLE','PASSKEY_CHANNEL_REFUSED'),
    )
    for internal, public in cases:
        assert _cli_failure(C.PasskeyError(internal)) == public


def test_cli_arbitrary_typed_text_os_errors_and_unknown_codes_are_redacted():
    class NoStringError(Exception):
        def __str__(self):
            raise AssertionError('exception formatter must not be invoked')
    class NoStringPasskeyError(C.PasskeyError):
        def __str__(self):
            raise AssertionError('typed exception formatter must not be invoked')
    cases = (
        C.PasskeyError('/private/owner.pem: private fixture detail'),
        C.PasskeyError('PASSKEY_RELEASE_NOT_A_REVIEWED_CODE'),
        C.PasskeyError('PASSKEY_OWNER_CHANGED /private/owner.jsonl'),
        C.PasskeyError('PASSKEY_OWNER_CHANGED\n'),
        C.PasskeyError('P'*1000),
        C.PasskeyError(['PASSKEY_OWNER_CHANGED']),
        C.PasskeyError('PASSKEY_OWNER_CHANGED','/private/extra'),
        C.PasskeyError(),
        OSError('/private/config.json: sensitive operating-system detail'),
        ValueError('PASSKEY_OWNER_CHANGED'),
        NoStringError('/private/unformatted'),
        NoStringPasskeyError('/private/unformatted'),
    )
    for error in cases:
        assert _cli_failure(error) == 'PASSKEY_STORE_INDETERMINATE'
