"""Engine orchestration using actual disposable owner, WebAuthn and disk facts.

The packet helper exports through the real app interpreter; broker source never
imports the app. All signatures and ledger/replay checks remain genuine. RP
release bytes are fixture commitments, not an operational HTTPS/IPC channel.
"""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
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
        applied = e.engine.install_disable(A.disable_bytes(actual))
        assert applied.status == 'APPLIED'
        # Only the exact durable disable is a response-loss retry; another disable is refused as revoked.
        assert e.restart().install_disable(A.disable_bytes(actual)) == applied
        F.refused(lambda:e.engine.install_disable(A.disable_bytes(F.disable_document(e))),'PASSKEY_REVOKED')
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
        head = e.ledger.inspect().head
        again = e.restart().submit_assertion(C.assertion_bytes(assertion))
        assert (again.status, again.reason, again.application_id) == ('EXPIRED', 'PASSKEY_EXPIRED', None)
        assert e.ledger.inspect().head == head


def test_actual_packet_modification_is_rejected_before_apply_and_on_current_read():
    with F.fixture() as e:
        request = archive_request(e)
        payload = next((e.packet/'payloads').iterdir())
        original = payload.read_bytes()
        payload.write_bytes(original+b'x')
        document = C.assertion_bytes(e.issue_assertion(request))
        # Authenticated, but the target changed: a fixed REJECTED close, never a later apply (8.3).
        rejected = e.engine.submit_assertion(document)
        assert (rejected.status, rejected.reason, rejected.application_id) == ('REJECTED', 'PASSKEY_TARGET_CHANGED', None)
        F.engine_only(rejected)
        payload.write_bytes(original)
        state = e.ledger.inspect().state
        closed = next(r for r in state.requests if r.request.request_id==request.request_id)
        assert closed.state == 'REJECTED' and closed.evidence_sha256 is not None and not state.applications
        assert state.events[-1].kind == 'REQUEST_CLOSED' and state.credentials[0].last_counter == 2
        again = e.restart().submit_assertion(document)
        assert (again.status, again.reason) == ('REJECTED', 'PASSKEY_TARGET_CHANGED')
        assert e.ledger.inspect().head == rejected.head and not e.ledger.inspect().state.applications
        _,_,result = apply(e,counter=3)
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
            # Grant eligibility (30 s owner age) runs before Engine._fresh in _begin, so it names the refusal.
            F.refused(lambda:archive_request(e),'PASSKEY_OWNER_STALE')
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


def _late_after(e, kind, delay):
    """Advance the actual fixture clock only once the named row is durable."""
    original = L._Operation.commit
    def commit(operation, event, *, expected_head):
        result = original(operation, event, expected_head=expected_head)
        if event.kind == kind:
            e.clock_cell[0] += delay
        return result
    return patch.object(L._Operation, 'commit', commit)


def test_late_check_after_durable_disable_is_indeterminate_and_exact_retry_is_historical():
    with F.fixture() as e:
        document = A.disable_bytes(F.disable_document(e))
        with _late_after(e, 'AUTHORITY_DISABLED', timedelta(seconds=301)):
            F.refused(lambda:e.engine.install_disable(document), 'PASSKEY_STORE_INDETERMINATE')
        state = e.ledger.inspect()
        assert state.state.disabled and state.state.events[-1].kind == 'AUTHORITY_DISABLED'
        retried = e.restart().install_disable(document)
        assert (retried.status, retried.reason, retried.head) == ('APPLIED', 'PASSKEY_APPLIED', state.head)
        assert e.ledger.inspect().head == state.head


def test_late_check_after_durable_grant_is_indeterminate_and_exact_retry_is_historical():
    with F.fixture(installed=False) as e:
        F.bootstrap(e, install=False)
        document = A.grant_bytes(e.grant)
        with _late_after(e, 'AUTHORITY_INSTALLED', timedelta(seconds=31)):
            F.refused(lambda:e.engine.install_grant(document, e.proposal.digest), 'PASSKEY_STORE_INDETERMINATE')
        state = e.ledger.inspect()
        installed = next(v for v in state.state.events if v.kind == 'AUTHORITY_INSTALLED')
        assert state.state.grant == e.grant
        retried = e.restart().install_grant(document, e.proposal.digest)
        assert (retried.status, retried.reason) == ('APPLIED', 'PASSKEY_APPLIED')
        assert retried.head == A.Head(sequence=installed.sequence, sha256=installed.row_sha256)
        F.refused(lambda:e.engine.install_grant(document, 'f'*64), 'PASSKEY_TARGET_CHANGED')
        assert e.ledger.inspect().head == state.head


def test_lapsed_pending_requests_are_closed_before_a_new_request_meets_the_pending_cap():
    with F.fixture() as e:
        at = e.clock()
        with L.AuthorityLedger.operation(e.ledger) as op:
            snapshot = op.load()
            for _ in range(128):
                request = E._request(e.config, snapshot.state.grant, snapshot.state.registry_epoch, 'REVOKE_CREDENTIAL',
                    dict(credential_sha256=e.credential.credential_sha256, reason='OWNER_WITHDRAWN'), at)
                note = E._notification(e.config.authority_id, 'REQUEST_READY', request_id=request.request_id,
                                       status='PENDING', at=at)
                snapshot = op.commit(A.ProposedEvent(kind='REQUEST_OPENED', observed_at=at, payload_bytes=A.canonical(
                    dict(request=E._body(request.raw), notification=E._body(A.notification_bytes(note))))),
                    expected_head=snapshot.head)
        assert e.engine.inspect().pending_request_count == 128
        e.clock_cell[0] = request.challenge_expires_at
        opened = e.engine.open_revoke_request(e.credential.credential_sha256, reason='OWNER_WITHDRAWN')
        state = e.ledger.inspect().state
        assert [r.state for r in state.requests] == ['EXPIRED']*128+['PENDING']
        assert state.requests[-1].request == opened
        assert sum(v.kind == 'REQUEST_CLOSED' for v in state.events) == 128


def test_archive_request_open_closes_a_lapsed_pending_request_first():
    with F.fixture() as e:
        lapsed = e.engine.open_revoke_request(e.credential.credential_sha256, reason='OWNER_WITHDRAWN')
        e.clock_cell[0] = lapsed.challenge_expires_at
        opened = archive_request(e)
        state = e.ledger.inspect().state
        assert [r.state for r in state.requests] == ['EXPIRED', 'PENDING'] and state.requests[-1].request == opened
        assert [v.kind for v in state.events[-2:]] == ['REQUEST_CLOSED', 'REQUEST_OPENED']


def test_kst_date_change_before_the_final_clock_refuses_before_any_request_row():
    with F.fixture(now=datetime(2031, 1, 7, 14, 59, 50, tzinfo=timezone.utc)) as e:
        before = e.ledger.inspect()
        now = e.clock_cell[0]
        original = E.Engine._configuration
        actual_owner = O.OwnerReader.observe
        seen = []
        def owner(reader,*,retained):
            observed = actual_owner(reader,retained=retained)
            seen.append(observed)
            return observed
        def configuration(engine):
            original(engine)
            if len(seen)>=2:  # after the pre-commit final owner observation: 15 s old, but next KST day
                e.clock_cell[0] = now+timedelta(seconds=15)
        with patch.object(O.OwnerReader,'observe',owner), patch.object(E.Engine,'_configuration',configuration):
            F.refused(lambda:e.engine.open_revoke_request(e.credential.credential_sha256, reason='OWNER_WITHDRAWN'),
                      'PASSKEY_CLOCK_INVALID')
        assert len(seen) == 2 and e.clock_cell[0]-seen[0].evidence.observed_at == timedelta(seconds=15)
        after = e.ledger.inspect()
        assert after.head == before.head and not after.state.requests


def test_registration_received_time_is_read_after_the_locked_owner_and_release_checks():
    with F.fixture(installed=False) as e:
        enrollment = e.engine.prepare_initial_enrollment()
        registration = F.registration(enrollment,e.credential_key,e.credential_id)
        original = E.Engine._begin
        def begin(engine, op, **options):
            result = original(engine, op, **options)
            e.clock_cell[0] += timedelta(seconds=5)
            return result
        late = e.clock()+timedelta(seconds=5)
        with patch.object(E.Engine,'_begin',begin):
            e.engine.submit_registration(enrollment.enrollment_id,C.registration_bytes(registration))
        pending = next(p for p in e.ledger.inspect().state.enrollments
                       if p.enrollment.enrollment_id==enrollment.enrollment_id)
        assert pending.registration_received_at == late


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
