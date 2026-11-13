"""Independent real-byte authority lifecycle integration, entirely disposable.

The explicit app environment exports real archived synthetic studies; the broker
environment independently consumes those bytes. All positive owner, release,
ledger and WebAuthn checks execute their actual implementations. No live owner,
RP service, ACL/IPC isolation, authenticated source or execution is established.
"""
from datetime import timedelta
import hashlib
import json
import shutil
from unittest.mock import patch

from cryptography.hazmat.primitives.asymmetric import ec

from tools.signer import sign as S
from tools.approval_broker import authority_contract as A, contract as C, engine as E, packet as P
from tools.approval_broker import ledger as L, owner_view as O
from tests import passkey_authority_fixtures as F


def open_request(e, *, minutes=30):
    return e.engine.open_archive_request(e.packet, approval_expires_at=e.clock()+timedelta(minutes=minutes))


def apply(e, *, counter=2):
    request = open_request(e)
    assertion = e.issue_assertion(request, counter=counter)
    document = C.assertion_bytes(assertion)
    result = e.engine.submit_assertion(document)
    assert result.status == 'APPLIED' and result.request_id == request.request_id
    assert result.application_id is not None
    F.engine_only(result)
    snapshot = e.engine.ledger.inspect()
    applications = [a for a in snapshot.state.applications if a.application_id == result.application_id]
    assert len(applications) == 1
    application = applications[0]
    assert application.bundle_digest == e.worker.report['bundle_digest']
    assert application.credential_sha256 == e.credential.credential_sha256
    assert snapshot.state.credentials[0].last_counter == counter
    assert sum(event.kind == 'ARCHIVE_APPLIED' for event in snapshot.state.events) == 1
    current = e.engine.read_current(result.application_id)
    assert current.status == 'ACTIVE' and current.packet_sha256 == e.packet_snapshot.packet_sha256
    assert current.request_sha256 == request.request_sha256
    F.engine_only(current)
    return request, document, result, application


def test_real_engine_enrollment_proof_and_root_grant_installation_have_durable_membership():
    with F.fixture(installed=False) as e:
        assert e.engine.inspect().grant_sha256 is None
        F.refused(lambda:open_request(e), 'PASSKEY_BOOTSTRAP_REQUIRED')
        F.append_owner(e, 'cap_set', dict(key='okx_equity_share', value=0.25))
        legacy_head = F.append_owner(e, 'age_of_majority',
            dict(birth_date='1990-01-01', evidence='합성 과거 증거 — fixture only'))
        F.bootstrap(e)
        state = e.engine.ledger.inspect().state
        assert state.grant == e.grant and state.registry_epoch == 1
        assert state.owner_evidence.head == legacy_head
        assert b'0.25' in state.owner_evidence.log_bytes
        legacy_rows = [json.loads(line) for line in state.owner_evidence.log_bytes.splitlines()]
        assert legacy_rows[-1]['data']['evidence'] == '합성 과거 증거 — fixture only'
        assert len(state.credentials) == 1 and state.credentials[0] == e.credential
        assert len(state.enrollments) == 1
        enrollment = state.enrollments[0]
        assert enrollment.enrollment == e.enrollment
        assert enrollment.registration == e.registration and enrollment.proof.assertion == e.proof_assertion
        assert enrollment.proposal_sha256 == e.proposal.digest
        kinds = [event.kind for event in state.events]
        assert kinds.count('ENROLLMENT_OPENED') == kinds.count('REGISTRATION_RECORDED') == 1
        assert kinds.count('INITIAL_PROOF_RECORDED') == kinds.count('AUTHORITY_INSTALLED') == 1
        assert e.enrollment.nonce != e.proof.nonce and len(e.enrollment.user_handle) == 32
        assert e.enrollment.expires_at-e.enrollment.requested_at == timedelta(seconds=300)
        assert e.worker.report['owner_code_sha256'] == json.loads(e.grant.body_bytes)['owner_checkpoint']['code_sha256']
        assert any(name.startswith('venv:PyYAML-') for name, _ in e.worker.report['code_files'])
        assert e.owner_reader.locations.app_environment != e.dependency_roots[0]
        restarted = e.restart()
        assert restarted.ledger is not e.engine.ledger and restarted.owner_reader is not e.engine.owner_reader
        assert restarted.inspect().head == e.engine.inspect().head
        assert restarted.inspect().grant_sha256 == e.grant.digest
        F.engine_only(restarted.inspect())
        _, _, result, _ = apply(e)
        assert e.restart().read_current(result.application_id).status == 'ACTIVE'


def test_raw_archive_assertion_is_once_and_restart_retry_preserves_original_received_evidence():
    with F.fixture(packet_kind='raw') as e:
        request, document, result, application = apply(e)
        before = e.engine.ledger.inspect()
        applied = next(event for event in before.state.events if event.kind == 'ARCHIVE_APPLIED')
        evidence = A.parse_evidence(A.canonical(A.decode(applied.payload_bytes)['evidence']))
        assert evidence.received_at == F.NOW
        assert b'{broken JSON' in (e.packet/'payloads'/'p-bad.bin').read_bytes()
        assert (e.packet/'payloads'/'p-empty.bin').read_bytes() == b''
        assert request.body['target']['archive_request']['raw_manifest']['inventory_complete'] is False
        assert {note.body['kind'] for note in e.engine.pending_notifications()} >= {'REQUEST_READY', 'APPLICATION_RESULT'}
        e.clock_cell[0] += timedelta(seconds=301)
        restarted = e.restart()
        retry = restarted.submit_assertion(document)
        assert retry.status == 'EXACT_RETRY' and retry.application_id == result.application_id
        F.engine_only(retry)
        after = restarted.ledger.inspect()
        assert after.head == before.head and after.journal_bytes == before.journal_bytes
        assert after.state.applications[0].raw == application.raw
        assert next(v.payload_bytes for v in after.state.events if v.kind == 'ARCHIVE_APPLIED') == applied.payload_bytes
        assert restarted.read_current(result.application_id).status == 'ACTIVE'
        e.clock_cell[0] = application.expires_at
        expired = e.restart().read_current(result.application_id)
        assert expired.status == 'EXPIRED'
        F.engine_only(expired)
        assert e.restart().submit_assertion(document).status == 'EXACT_RETRY'
        assert e.restart().inspect().application_count == 1


def _verified_packet_lifecycle(kind):
    with F.fixture(packet_kind=kind) as e:
        request, _, result, application = apply(e)
        archive = request.body['target']['archive_request']
        assert archive['bundle_kind'] == 'VERIFIED_UNAPPROVED'
        assert archive['raw_manifest'] and archive['verified_manifest']
        assert e.worker.report['payload_count'] > 8 and e.worker.report['actual_store_backup_readback']
        assert e.worker.report['independent_packet_readback']
        assert application.body['input_archive_digest'] == archive['input_archive_digest']
        assert application.body['file_set_sha256'] == archive['file_set_sha256']
        assert application.body['archive_request_sha256'] == archive['request_sha256']
        current = e.restart().read_current(result.application_id)
        assert current.status == 'ACTIVE'
        F.engine_only(current)


def test_actual_fixed_research_store_export_crosses_app_environment_and_is_archive_only():
    _verified_packet_lifecycle('fixed')


def test_actual_carry_research_store_export_crosses_app_environment_and_is_archive_only():
    _verified_packet_lifecycle('carry')


def test_new_signature_for_applied_request_is_refused_even_when_real_es256_signature_is_valid():
    with F.fixture() as e:
        request, document, result, _ = apply(e)
        before = e.engine.ledger.inspect()
        different = C.assertion_bytes(e.issue_assertion(request, counter=3))
        assert different != document
        F.refused(lambda:e.restart().submit_assertion(different), 'PASSKEY_REQUEST_REUSED')
        assert e.engine.inspect().head == before.head
        assert e.restart().submit_assertion(document).application_id == result.application_id
        assert e.engine.inspect().application_count == 1


def test_grant_with_real_wrong_root_signature_or_expanded_scope_cannot_install():
    with F.fixture(installed=False) as e:
        F.bootstrap(e, install=False)
        before = e.engine.inspect().head
        wrong_root = A.GrantDocument(body_bytes=e.grant.body_bytes,
            signature=e.recovery_key.sign(A.grant_signing_bytes(e.grant.body_bytes)))
        F.refused(lambda:e.engine.install_grant(A.grant_bytes(wrong_root), e.proposal.digest),
                  'PASSKEY_SIGNATURE_INVALID')
        body = A.decode(e.grant.body_bytes)
        body['approval_scope'] = 'execution_authority'
        raw = A.canonical(body)
        # A genuine root signature cannot make an unsupported scope admissible.
        signature = e.root_key.sign(b'tradegen-passkey-archive/authority-grant/1\n'+raw)
        expanded = A.canonical(dict(body=body, signature_b64=C.b64(signature)))
        F.refused(lambda:e.engine.install_grant(expanded, e.proposal.digest), 'PASSKEY_FORMAT_INVALID')
        assert e.engine.inspect().head == before and e.engine.inspect().grant_sha256 is None
        assert e.engine.inspect().credential_count == 0
        assert e.engine.install_grant(A.grant_bytes(e.grant), e.proposal.digest).status == 'APPLIED'


def test_real_bad_key_and_origin_cannot_consume_request_or_create_application():
    with F.fixture() as e:
        request = open_request(e)
        head = e.engine.inspect().head
        wrong = ec.generate_private_key(ec.SECP256R1())
        F.refused(lambda:e.engine.submit_assertion(C.assertion_bytes(e.issue_assertion(request, key=wrong))),
                  'PASSKEY_SIGNATURE_INVALID')
        F.refused(lambda:e.engine.submit_assertion(C.assertion_bytes(e.issue_assertion(request,
                  origin='https://other.test'))), 'PASSKEY_ORIGIN_RP_INVALID')
        assert e.engine.inspect().head == head and e.engine.inspect().application_count == 0
        assert e.engine.inspect().pending_request_count == 1
        assert e.engine.ledger.inspect().state.credentials[0].last_counter == 1
        assert e.engine.submit_assertion(C.assertion_bytes(e.issue_assertion(request))).status == 'APPLIED'


def test_self_revoke_advances_epoch_invalidates_pending_work_and_keeps_historical_archive():
    with F.fixture() as e:
        _, document, result, _ = apply(e)
        pending = open_request(e)
        revoke = e.engine.open_revoke_request(e.credential.credential_sha256, reason='OWNER_WITHDRAWN')
        revoke_document = C.assertion_bytes(e.issue_assertion(revoke, counter=3))
        revoked = e.engine.submit_assertion(revoke_document)
        assert revoked.status == 'APPLIED' and revoked.application_id is None
        F.engine_only(revoked)
        state = e.engine.ledger.inspect().state
        assert state.registry_epoch == 2 and state.credentials[0].state == 'REVOKED'
        assert state.credentials[0].last_counter == 3 and state.credentials[0].revoked_at == e.clock()
        assert len(state.applications) == 1
        current = e.restart().read_current(result.application_id)
        assert current.status == 'REVOKED'
        F.engine_only(current)
        head = e.engine.inspect().head
        assert e.restart().submit_assertion(document).status == 'EXACT_RETRY'
        assert e.restart().submit_assertion(revoke_document).status == 'EXACT_RETRY'
        F.refused(lambda:e.engine.submit_assertion(C.assertion_bytes(e.issue_assertion(pending, counter=4))),
                  'PASSKEY_REGISTRY_CHANGED', 'PASSKEY_REVOKED')
        assert e.engine.inspect().head == head and e.engine.inspect().application_count == 1


def test_independent_recovery_disable_requires_signature_and_exact_head_then_survives_restart():
    with F.fixture() as e:
        _, document, result, _ = apply(e)
        original = e.engine.inspect().head
        bad = F.disable_document(e, key=e.root_key)
        F.refused(lambda:e.engine.install_disable(A.disable_bytes(bad)), 'PASSKEY_SIGNATURE_INVALID')
        assert e.engine.inspect().head == original
        stale = F.disable_document(e)
        open_request(e)
        F.refused(lambda:e.engine.install_disable(A.disable_bytes(stale)), 'PASSKEY_GRANT_INVALID')
        valid = F.disable_document(e)
        disabled = e.engine.install_disable(A.disable_bytes(valid))
        assert disabled.status == 'APPLIED'
        F.engine_only(disabled)
        restarted = e.restart()
        assert restarted.inspect().disabled and restarted.inspect().application_count == 1
        assert restarted.read_current(result.application_id).status == 'INVALIDATED'
        assert restarted.submit_assertion(document).status == 'EXACT_RETRY'
        F.refused(lambda:restarted.open_archive_request(e.packet,
                  approval_expires_at=e.clock()+timedelta(minutes=10)), 'PASSKEY_REVOKED')
        assert e.engine.ledger.inspect().state.disabled


def test_authentic_restrictive_owner_head_is_retained_before_refusal_and_cannot_be_rolled_back():
    with F.fixture() as e:
        _, _, result, _ = apply(e)
        original = (e.compliance/'owner.jsonl').read_bytes()
        files = [['synthetic-replacement.py', hashlib.sha256(b'owner deliberately changes code approval').hexdigest()]]
        restrictive = F.append_owner(e, 'code_approved', dict(files=files, sha256=S.sha256_hex(S.canonical_json(files))))
        F.refused(lambda:e.engine.read_current(result.application_id), 'PASSKEY_DEPLOYMENT_CHANGED')
        retained = e.engine.ledger.inspect()
        assert retained.state.owner_evidence.head == restrictive
        assert retained.state.owner_evidence.log_bytes == (e.compliance/'owner.jsonl').read_bytes()
        assert len(retained.state.applications) == 1
        (e.compliance/'owner.jsonl').write_bytes(original)
        F.refused(lambda:e.restart().read_current(result.application_id), 'PASSKEY_OWNER_PREFIX_INVALID')
        assert e.engine.ledger.inspect().head == retained.head
        assert e.engine.ledger.inspect().state.owner_evidence.head == restrictive


def test_actual_packet_payload_change_and_external_location_are_refused_without_consumption():
    with F.fixture() as e:
        outside = e.base/'outside-packet'
        shutil.copytree(e.packet, outside)
        F.refused(lambda:e.engine.open_archive_request(outside,
                  approval_expires_at=e.clock()+timedelta(minutes=10)), 'PASSKEY_TARGET_CHANGED')
        request = open_request(e)
        payload = e.packet/'payloads'/'p-bad.bin'
        original = payload.read_bytes()
        before = e.engine.inspect().head
        payload.write_bytes(b'{changed payload')
        F.refused(lambda:e.engine.submit_assertion(C.assertion_bytes(e.issue_assertion(request))))
        assert e.engine.inspect().head == before and e.engine.inspect().application_count == 0
        assert e.engine.inspect().pending_request_count == 1
        payload.write_bytes(original)
        assert P.read_packet(e.packet).packet_sha256 == e.packet_snapshot.packet_sha256
        assert e.engine.submit_assertion(C.assertion_bytes(e.issue_assertion(request))).status == 'APPLIED'


def test_actual_release_byte_change_refuses_current_observation_but_retains_historical_application():
    with F.fixture() as e:
        _, document, result, _ = apply(e)
        path = e.rp_root/'index.html'
        original = path.read_bytes()
        head = e.engine.inspect().head
        path.write_bytes(original+b'changed')
        F.refused(lambda:e.restart().read_current(result.application_id))
        assert e.engine.inspect().head == head and e.engine.inspect().application_count == 1
        assert e.restart().submit_assertion(document).status == 'EXACT_RETRY'
        path.write_bytes(original)
        assert e.restart().read_current(result.application_id).status == 'ACTIVE'


def test_clock_expiry_after_real_final_release_work_never_reports_success_or_erases_durable_apply():
    with F.fixture() as e:
        request = open_request(e)
        document = C.assertion_bytes(e.issue_assertion(request))
        actual = E.verify_release
        seen = []
        def delayed(directory, manifest, *, dependency_roots):
            result = actual(directory, manifest, dependency_roots=dependency_roots)
            seen.append(manifest.role)
            if len(seen) == 6:
                e.clock_cell[0] += timedelta(seconds=31)
            return result
        with patch.object(E, 'verify_release', side_effect=delayed):
            F.refused(lambda:e.engine.submit_assertion(document), 'PASSKEY_CLOCK_INVALID')
        assert seen == ['BROKER', 'RP', 'BROKER', 'RP', 'BROKER', 'RP']
        state = e.engine.ledger.inspect().state
        assert len(state.applications) == 1 and state.credentials[0].last_counter == 2
        assert sum(event.kind == 'ARCHIVE_APPLIED' for event in state.events) == 1
        restarted = e.restart()
        assert restarted.submit_assertion(document).status == 'EXACT_RETRY'
        current = restarted.read_current(state.applications[0].application_id)
        assert current.status == 'ACTIVE'
        F.engine_only(current)


def test_current_result_final_clock_follows_actual_owner_release_packet_and_full_ledger_reads():
    with F.fixture() as e:
        _, _, result, _ = apply(e)
        trace = []
        class ClockCell(list):
            def __getitem__(self, index):
                trace.append('clock')
                return super().__getitem__(index)
        e.clock_cell = ClockCell(e.clock_cell)
        actual_owner = O.OwnerReader.observe
        actual_load = L._Operation.load
        actual_release = E.verify_release
        actual_packet = E.recheck_packet
        def owner(reader, *, retained):
            value = actual_owner(reader, retained=retained)
            trace.append('owner')
            return value
        def load(operation):
            value = actual_load(operation)
            trace.append('ledger')
            return value
        def release(directory, manifest, *, dependency_roots):
            value = actual_release(directory, manifest, dependency_roots=dependency_roots)
            trace.append('release')
            return value
        def packet(directory, expected):
            value = actual_packet(directory, expected)
            trace.append('packet')
            return value
        with patch.object(O.OwnerReader, 'observe', owner), patch.object(L._Operation, 'load', load), \
                patch.object(E, 'verify_release', release), patch.object(E, 'recheck_packet', packet):
            current = e.engine.read_current(result.application_id)
        assert current.status == 'ACTIVE'
        assert {'owner', 'ledger', 'release', 'packet'} <= set(trace)
        assert trace[-1] == 'clock', trace
        last_owner = max(i for i, value in enumerate(trace) if value == 'owner')
        assert all(max(i for i, value in enumerate(trace) if value == name) < last_owner
                   for name in ('release', 'packet', 'ledger'))
        assert current.completed_at == e.clock_cell[0]
        F.engine_only(current)
