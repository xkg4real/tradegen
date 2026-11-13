"""Actual archival graphs and current owner loader; disposable keys and homes only.

Positive authentication uses real Ed25519 and a genuinely signed temporary owner
log, not a fabricated authority or a boolean verifier. Some verified manifests
deliberately contain unproven research claims: archive identity must never turn
them into evaluated/qualified research. No API, account or order is used.
"""
from contextlib import contextmanager
from dataclasses import asdict, replace
from datetime import datetime, timedelta, timezone
import base64
import hashlib
import json
from pathlib import Path
import re
from types import SimpleNamespace
from unittest.mock import patch

from core.compliance import owner, model as M
from execution_control.owner_authority import CurrentOwnerAuthority, ReviewAuthority
from execution_launch import bundle_attestation as A, bundle_auth as U
from execution_launch import research_bundle as R, research_bundle_format as F
from execution_launch import strategy as E
from tests import compliance_fixtures as CF
from tests import launch_research_bundle_store as SF, launch_research_bundle as RF

NOW = datetime(2031, 1, 7, tzinfo=timezone.utc)


@contextmanager
def signed_owner():
    """Actual code approval only: absent trading tables are deliberate, not patched."""
    with CF.temp_home() as home, CF.pubkey_at(home/'owner_pubkey.pem'):
        key = CF.owner_key(home)
        files = [list(row) for row in owner.code_files(owner.REPO_ROOT)]
        code = owner.code_hash(owner.REPO_ROOT)
        CF.sign(key, 'code_approved', {'sha256':code, 'files':files})
        assert owner.PUBKEY_PATH.is_relative_to(home) and owner.home().is_relative_to(home)
        yield SimpleNamespace(home=home, key=key, code=code)


def document(request, key, *, issued_at=NOW, domain=None):
    fp = 'SHA256:' + hashlib.sha256(key.public_key().public_bytes_raw()).hexdigest()
    body = A.attestation_body(request, owner_fingerprint=fp, issued_at=issued_at)
    signed = A.attestation_signing_bytes(body)
    if domain is not None:
        signed = domain + signed[len(A.SIGNING_DOMAIN):]
    return A.attestation_document_bytes(body, key.sign(signed))


@contextmanager
def fixture(*, verified_claim=False):
    with SF.fixture() as storage:
        raw, raw_bytes, payloads = SF.raw_archive(storage.store, full=verified_claim)
        receipt = storage.store.archive_raw(raw_bytes, payloads)
        verified_bytes = None
        if verified_claim:
            _, verified_bytes, payloads = SF.verified_bundle(storage.store, raw, payloads)
            receipt = storage.store.commit_verified(verified_bytes, payloads)
        with signed_owner() as signer:
            cell = [NOW]
            clock = lambda:cell[0]
            request = A.request_from_manifests(raw_bytes, verified_bytes,
                requested_at=NOW, expires_at=NOW+timedelta(hours=1), deployment_code_hash=signer.code)
            yield SimpleNamespace(store=storage.store, root=storage.base, raw=raw, raw_bytes=raw_bytes,
                verified_bytes=verified_bytes, payloads=payloads, digest=receipt.bundle_digest,
                request=request, document=document(request, signer.key), signer=signer,
                cell=cell, clock=clock, provider=CurrentOwnerAuthority(clock=clock))


def authenticate(e, **changes):
    args = dict(store=e.store, bundle_digest=e.digest, document_bytes=e.document,
                authority_provider=e.provider, clock=e.clock)
    return U.authenticate_bundle_attestation(**(args | changes))


def refused(call, code=None):
    try:
        call()
    except ValueError as exc:
        assert re.fullmatch(r'[A-Z][A-Z0-9_]{0,95}', str(exc)), 'non-code diagnostic'
        if code is not None:
            assert str(exc) == code, (str(exc), code)
        return str(exc)
    raise AssertionError('untrusted archive accepted')


def no_operation(result):
    assert result.archive_identity_authenticated
    assert result.scope == 'archive_manifest_identity' and result.revocation_status == 'NOT_REVOKED_AT_HEAD'
    assert not result.source_authenticated and not result.research_selection_ready
    assert not result.execution_ready and not result.current_use_eligible
    assert not result.automatic_recovery_supported and not result.signature_backup_verified
    assert 'revoked' not in asdict(result)


def test_actual_owner_and_failed_raw_archive_authenticate_identity_only():
    with fixture() as e:
        before = dict(E._EVALUATED)
        calls, reads = [], []
        actual_owner, actual_read = owner.load_context, e.store.read_raw
        def observe(now, positions):
            context = actual_owner(now, positions)
            assert M.is_sealed(context) and context.owner.ok and context.code_signed
            assert not context.active.valid  # No trading-table approvals in this fixture.
            calls.append(context.owner.head)
            return context
        def read(*args, **kwargs):
            assert kwargs == {'require_backup':True}
            reads.append(args[0])
            return actual_read(*args, **kwargs)
        with patch.object(owner, 'load_context', side_effect=observe), \
             patch.object(e.store, 'read_raw', side_effect=read):
            result = authenticate(e)
        no_operation(result)
        assert result.bundle_kind == 'RAW_ARCHIVED' and result.bundle_digest == e.digest
        assert result.input_archive_digest == e.digest and result.verified_at == NOW
        assert result.attestation_sha256 == A.attestation_document_digest(e.document)
        assert len(calls) == 3 and reads == [e.digest, e.digest]
        assert E._EVALUATED == before
        assert e.store.read_raw(e.digest).files['bad'] == b'{broken JSON'
        assert e.store.read_raw(e.digest).files['empty'] == b''


def test_counterfeit_but_format_valid_verified_claim_can_only_attest_archive_identity():
    with fixture(verified_claim=True) as e:
        before = dict(E._EVALUATED)
        with patch.object(R, 'evaluate_sealed_study', side_effect=AssertionError('not a research approval')), \
             patch.object(E, 'evaluate_capture_json', side_effect=AssertionError('not an evaluation issuer')):
            result = authenticate(e)
        no_operation(result)
        assert result.bundle_kind == 'VERIFIED_UNAPPROVED'
        assert result.input_archive_digest == F.raw_archive_digest(e.raw)
        assert E._EVALUATED == before
        # The bytes openly state that this is not an issued numerical result.
        assert b'not an issued evaluation' in e.payloads['evaluation']


def test_actual_b1a_fixed_and_carry_graphs_remain_non_operational_after_attestation():
    for carry in (False, True):
        with RF.fixture(carry=carry) as e:
            finished = RF.finalize(e)
            assert finished.status == 'VERIFIED_UNAPPROVED', finished.reasons
            target = e.store.read_verified(finished.bundle_digest, require_backup=True)
            raw = e.store.read_raw(finished.input_archive_digest, require_backup=True)
            with signed_owner() as signer:
                request = A.request_from_manifests(raw.manifest_bytes, target.manifest_bytes,
                    requested_at=NOW, expires_at=NOW+timedelta(hours=1), deployment_code_hash=signer.code)
                clock = lambda:NOW
                result = U.authenticate_bundle_attestation(e.store, finished.bundle_digest,
                    document(request, signer.key), authority_provider=CurrentOwnerAuthority(clock=clock), clock=clock)
                no_operation(result)
                assert result.bundle_digest == finished.bundle_digest
                assert result.request_sha256 == request['request_sha256']


def test_constructed_authority_callback_stored_bundle_and_report_are_not_trust_inputs():
    with fixture() as e:
        observed = e.provider(NOW)
        stored = e.store.read_raw(e.digest)
        report = authenticate(e)
        with patch.object(owner, 'load_context', side_effect=AssertionError('invalid input must not load owner')):
            for provider in (observed, replace(observed), lambda _:observed, lambda _:True, report):
                refused(lambda provider=provider:authenticate(e, authority_provider=provider),
                        'ARCHIVE_AUTH_ACTUAL_PROVIDER_REQUIRED')
            for store in (stored, report):
                refused(lambda store=store:authenticate(e, store=store), 'ARCHIVE_AUTH_STORE_REQUIRED')
            refused(lambda:authenticate(e, clock=lambda:NOW), 'ARCHIVE_AUTH_ACTUAL_PROVIDER_REQUIRED')
            refused(lambda:authenticate(e, document_bytes=json.loads(e.document)), 'ARCHIVE_AUTH_DOCUMENT_BYTES_REQUIRED')


def test_corrupted_actual_loader_context_cannot_bypass_seal_or_hash_checks():
    for corruption in ('unsealed_clone', 'changed_field'):
        with fixture() as e:
            actual = owner.load_context
            def corrupted(now, positions):
                context = actual(now, positions)
                assert M.is_sealed(context) and context.owner.ok and context.code_signed
                if corruption == 'unsealed_clone':
                    return replace(context)
                object.__setattr__(context, 'equity_krw', context.equity_krw+1.0)
                return context
            with patch.object(owner, 'load_context', side_effect=corrupted):
                refused(lambda:authenticate(e), 'ARCHIVE_AUTH_OWNER_CONTEXT_INVALID')


def test_real_signature_wrong_target_deployment_key_or_domain_refuses():
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    with fixture() as e:
        other = Ed25519PrivateKey.from_private_bytes(bytes(range(1,33)))
        refused(lambda:authenticate(e, bundle_digest='f'*64), 'ARCHIVE_AUTH_TARGET_MISMATCH')
        wrong = A.request_from_manifests(e.raw_bytes, None, requested_at=NOW,
            expires_at=NOW+timedelta(hours=1), deployment_code_hash='f'*64)
        refused(lambda:authenticate(e, document_bytes=document(wrong, e.signer.key)),
                'ARCHIVE_AUTH_DEPLOYMENT_CODE_MISMATCH')
        for raw in (document(e.request, other), document(e.request, e.signer.key, domain=b'tradegen-owner-log/1\n')):
            refused(lambda raw=raw:authenticate(e, document_bytes=raw))


def test_signed_other_file_inventory_cannot_be_replayed_for_requested_store_digest():
    with fixture() as e:
        other, raw, payloads = SF.raw_archive(e.store, {'different':b'another original'}, run='run-b', revision='raw-b')
        receipt = e.store.archive_raw(raw, payloads)
        request = A.request_from_manifests(raw, None, requested_at=NOW,
            expires_at=NOW+timedelta(hours=1), deployment_code_hash=e.signer.code)
        assert receipt.bundle_digest != e.digest
        refused(lambda:authenticate(e, document_bytes=document(request,e.signer.key)), 'ARCHIVE_AUTH_TARGET_MISMATCH')


def test_primary_or_backup_original_damage_refuses_despite_genuine_signature():
    for backup in (False, True):
        with fixture() as e:
            path = SF.chunk_path(e.store, e.payloads['bad'], backup)
            original = path.read_bytes()
            path.write_bytes(original+b'damaged')
            refused(lambda:authenticate(e))
            assert path.read_bytes() == original+b'damaged'  # No repair or backup adoption.


def test_verified_authentication_rechecks_its_linked_raw_and_backup_dependencies():
    with fixture(verified_claim=True) as e:
        path = SF.chunk_path(e.store, e.payloads['source_receipts'], True)
        path.unlink()
        refused(lambda:authenticate(e))
        assert not path.exists()


def test_object_mutation_during_owner_reobservation_is_caught_by_second_graph_read():
    with fixture() as e:
        actual_owner = owner.load_context
        count = []
        path = SF.chunk_path(e.store, e.payloads['bad'])
        def observe(now, positions):
            value = actual_owner(now, positions)
            count.append(now)
            if len(count) == 2:
                path.write_bytes(b'changed during genuine second owner load')
            return value
        with patch.object(owner, 'load_context', side_effect=observe):
            refused(lambda:authenticate(e))
        assert len(count) == 2 and path.read_bytes().startswith(b'changed during')


def test_expiry_and_clock_rollback_during_graph_work_refuse():
    for change, expected in ((timedelta(hours=1), 'ARCHIVE_AUTH_EXPIRED_OR_FUTURE'),
                             (-timedelta(microseconds=1), 'ARCHIVE_AUTH_CLOCK_ROLLBACK')):
        with fixture() as e:
            actual = e.store.read_raw
            def read(*args, **kwargs):
                value = actual(*args, **kwargs)
                e.cell[0] = NOW+change
                return value
            with patch.object(e.store, 'read_raw', side_effect=read):
                refused(lambda:authenticate(e), expected)


def test_total_observation_window_cannot_refresh_away_the_original_thirty_second_limit():
    for delay, accepted in ((timedelta(seconds=30),True), (timedelta(seconds=30,microseconds=1),False)):
        with fixture() as e:
            actual = e.store.read_raw
            def read(*args, **kwargs):
                value = actual(*args, **kwargs)
                e.cell[0] = NOW+delay
                return value
            with patch.object(e.store, 'read_raw', side_effect=read):
                if accepted:
                    result = authenticate(e)
                    no_operation(result)
                    assert result.verified_at == NOW+delay
                else:
                    refused(lambda:authenticate(e), 'ARCHIVE_AUTH_OWNER_AUTHORITY_STALE')


def test_future_or_expired_signature_refuses_with_actual_current_owner():
    with fixture() as e:
        e.cell[0] = NOW-timedelta(microseconds=1)
        refused(lambda:authenticate(e), 'ARCHIVE_AUTH_EXPIRED_OR_FUTURE')
    with fixture() as e:
        e.cell[0] = NOW+timedelta(hours=1)
        refused(lambda:authenticate(e), 'ARCHIVE_AUTH_EXPIRED_OR_FUTURE')


def test_key_rotation_during_graph_work_uses_actual_owner_chain_and_latches():
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    with fixture() as e:
        other = Ed25519PrivateKey.from_private_bytes(bytes(range(1,33)))
        actual = e.store.read_raw
        changed = []
        def read(*args, **kwargs):
            value = actual(*args, **kwargs)
            if not changed:
                encode = lambda key:base64.b64encode(key.public_key().public_bytes_raw()).decode('ascii')
                CF.sign(e.signer.key, 'key_rotated', {'old_pubkey_b64':encode(e.signer.key),'new_pubkey_b64':encode(other)})
                CF.write_pubkey(owner.PUBKEY_PATH, other)
                changed.append(True)
            return value
        with patch.object(e.store, 'read_raw', side_effect=read):
            refused(lambda:authenticate(e), 'OWNER_AUTHORITY_KEY_CHANGED')
        with patch.object(owner, 'load_context', side_effect=AssertionError('latched authority must not reload')):
            refused(lambda:authenticate(e), 'OWNER_AUTHORITY_KEY_CHANGED')


def test_code_approval_change_during_graph_work_refuses_without_source_mutation():
    with fixture() as e:
        actual = e.store.read_raw
        changed = []
        def read(*args, **kwargs):
            value = actual(*args, **kwargs)
            if not changed:
                CF.other_code(e.signer.key)
                changed.append(True)
            return value
        with patch.object(e.store, 'read_raw', side_effect=read):
            refused(lambda:authenticate(e), 'OWNER_AUTHORITY_CODE_NOT_SIGNED')


def test_benign_owner_log_growth_and_existing_halt_do_not_become_trading_permission():
    with fixture() as e:
        owner.append_system_entry('system_halt', {'floor_krw':1.0}, NOW)
        actual = e.store.read_raw
        changed = []
        def read(*args, **kwargs):
            value = actual(*args, **kwargs)
            if not changed:
                CF.sign(e.signer.key, 'age_of_majority', {'birth_date':'2000-01-01','evidence':'synthetic fixture'})
                changed.append(True)
            return value
        with patch.object(e.store, 'read_raw', side_effect=read):
            result = authenticate(e)
        no_operation(result)
        observed = e.provider(NOW)
        assert observed.context.owner.halted_floors and not observed.context.active.valid
        assert observed.context.owner.head[0] == 3


def test_owner_log_rollback_after_success_is_refused_by_same_provider():
    with fixture() as e:
        first = owner.log_path().read_bytes()
        CF.sign(e.signer.key, 'age_of_majority', {'birth_date':'2000-01-01','evidence':'synthetic fixture'})
        no_operation(authenticate(e))
        owner.log_path().write_bytes(first)
        refused(lambda:authenticate(e), 'OWNER_AUTHORITY_LOG_REWRITTEN')


def test_each_authentication_observes_current_graph_and_key_instead_of_accepting_old_report():
    with fixture() as e:
        old = authenticate(e)
        no_operation(old)
        path = SF.chunk_path(e.store, e.payloads['bad'], True)
        path.write_bytes(b'new damage after successful observation')
        refused(lambda:authenticate(e))
        assert old.archive_identity_authenticated and not old.current_use_eligible


def test_final_owner_loader_expiry_is_checked_with_the_completion_clock():
    with fixture() as e:
        # The document expires in five seconds. The final loader returns its
        # genuine sealed observation, then the actual shared clock advances.
        request = A.request_from_manifests(e.raw_bytes, None, requested_at=NOW,
            expires_at=NOW+timedelta(seconds=5), deployment_code_hash=e.signer.code)
        raw = document(request, e.signer.key)
        actual = owner.load_context
        calls = []
        def load(now, positions):
            value = actual(now, positions)
            calls.append(now)
            if len(calls) == 3:
                e.cell[0] = NOW+timedelta(seconds=5)
            return value
        with patch.object(owner, 'load_context', side_effect=load):
            refused(lambda:authenticate(e, document_bytes=raw), 'ARCHIVE_AUTH_EXPIRED_OR_FUTURE')
        assert len(calls) == 3


def test_final_heavy_signature_and_document_digest_work_cannot_hide_expiry():
    for name, final_call in (('verify_attestation_signature',6), ('attestation_document_digest',1)):
        with fixture() as e:
            request = A.request_from_manifests(e.raw_bytes, None, requested_at=NOW,
                expires_at=NOW+timedelta(seconds=5), deployment_code_hash=e.signer.code)
            raw = document(request, e.signer.key)
            actual = getattr(A, name)
            calls = []
            def delayed(*args, **kwargs):
                value = actual(*args, **kwargs)
                calls.append(True)
                if len(calls) == final_call:
                    e.cell[0] = NOW+timedelta(seconds=5)
                return value
            with patch.object(A, name, side_effect=delayed):
                refused(lambda:authenticate(e, document_bytes=raw), 'ARCHIVE_AUTH_EXPIRED_OR_FUTURE')
            assert len(calls) == final_call
