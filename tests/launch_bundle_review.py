"""Temporary actual-store packets, standalone fixture signatures and real owner loading.

No private deployment key, real owner home, network, account or orders. Native
Windows contract fakes are separate from actual Windows operating-system proof.
"""
from contextlib import contextmanager, redirect_stdout
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from io import StringIO
import json
import os
from pathlib import Path
import tempfile
from unittest.mock import patch

from core.compliance import owner
from execution_control.owner_authority import CurrentOwnerAuthority
from execution_launch import bundle_attestation as A
from execution_launch import bundle_auth as AUTH
from execution_launch import bundle_review as R
from execution_launch import research_bundle_format as F
from tests import compliance_fixtures as CF
from tests import compliance_signer as SIGN
from tests import launch_research_bundle as REAL
from tests import launch_research_bundle_store as STORE

AT = datetime(2031, 1, 6, tzinfo=timezone.utc)


@contextmanager
def raw_fixture():
    with STORE.fixture() as e:
        manifest, raw, payloads = STORE.raw_archive(e.store)
        receipt = e.store.archive_raw(raw, payloads)
        e.digest, e.manifest, e.payloads = receipt.bundle_digest, manifest, payloads
        e.packet = e.base/'packet'; e.packet.mkdir()
        e.at = AT
        yield e


def export(e, **changes):
    arguments = dict(requested_at=e.at, expires_at=e.at+timedelta(hours=1),
                     deployment_code_hash=owner.code_hash(owner.REPO_ROOT))
    arguments.update(changes)
    return R.export_review_packet(e.store, e.digest, e.packet, **arguments)


def refused(call, *codes):
    try:
        call()
    except (ValueError, OSError, RuntimeError) as exc:
        if codes:
            assert str(exc) in codes, (str(exc), codes)
        return str(exc)
    raise AssertionError('unsafe or unauthorized packet accepted')


def invoke(*argv):
    output = StringIO()
    with redirect_stdout(output):
        code = R.main(list(argv))
    return code, json.loads(output.getvalue())


def tree(root):
    return {p.relative_to(root).as_posix():p.read_bytes() for p in root.rglob('*') if p.is_file()}


def independent_document(packet, key, at):
    # This module is loaded by path, contains its own strict codecs, and imports
    # no app modules. Its parsed packet is the actual signing input.
    request, snapshot = SIGN.signer._bundle_packet(packet)
    body = SIGN.signer._ba_attestation_body(request,
        owner_fingerprint=SIGN.signer.fingerprint(key.public_key().public_bytes_raw()), issued_at=at)
    document = SIGN.signer._ba_attestation_document_bytes(body,
        key.sign(SIGN.signer._ba_attestation_signing_bytes(body)))
    return request, document


@contextmanager
def real_owner():
    home = owner.home().parent  # owner.home() is the compliance subdirectory of the temporary state root.
    assert home.is_relative_to(Path(tempfile.gettempdir())) and home.name.startswith('tradegen_home_')
    with CF.pubkey_at(home/'owner_pubkey.pem'):
        key = CF.full_home(home)
        yield key


def test_malformed_empty_raw_exports_exact_generated_names_and_independent_signer_reads_it():
    with raw_fixture() as e:
        request = export(e)
        assert request['bundle_kind'] == 'RAW_ARCHIVED'
        assert request['verified_manifest'] is None and request['raw_manifest']['expected_candidates'] is None
        assert request['raw_manifest']['inventory_complete'] is False
        assert set(p.name for p in e.packet.iterdir()) == {'request.json', 'payloads'}
        assert {p.name:p.read_bytes() for p in (e.packet/'payloads').iterdir()} == {
            A.payload_filename(logical):value for logical,value in e.payloads.items()}
        assert (e.packet/'payloads'/'p-empty.bin').stat().st_size == 0
        assert b'CON:bad' in (e.packet/'request.json').read_bytes()
        assert not (e.base/'CON:bad').exists()
        independent, snapshot = SIGN.signer._bundle_packet(e.packet)
        assert independent == request
        assert A.archive_request_bytes(request) == (e.packet/'request.json').read_bytes()
        before = tree(e.packet)
        refused(lambda:export(e), 'BUNDLE_REVIEW_OUTPUT_EXISTS')
        assert tree(e.packet) == before


def test_actual_fixed_and_carry_verified_graph_exports_then_authenticates_only_archival_identity():
    for carry in (False, True):
        with REAL.fixture(carry=carry) as e, real_owner() as key:
            result = REAL.finalize(e)
            assert result.status == 'VERIFIED_UNAPPROVED', result.reasons
            e.digest = result.bundle_digest
            e.packet = e.base/'packet'; e.packet.mkdir()
            request = export(e)
            raw = e.store.read_raw(result.input_archive_digest, require_backup=True)
            verified = e.store.read_verified(result.bundle_digest, require_backup=True)
            assert request['input_archive_digest'] == result.input_archive_digest
            assert request['raw_manifest'] == json.loads(raw.manifest_bytes)
            assert request['verified_manifest'] == json.loads(verified.manifest_bytes)
            assert len(request['payload_files']) == len(verified.files)
            for logical, value in raw.files.items():
                assert (e.packet/'payloads'/A.payload_filename(logical)).read_bytes() == value
            parsed, document = independent_document(e.packet, key, e.at)
            assert parsed == request
            clock = lambda:e.at
            assessment = AUTH.authenticate_bundle_attestation(e.store, e.digest, document,
                authority_provider=CurrentOwnerAuthority(clock=clock), clock=clock)
            assert assessment.archive_identity_authenticated and assessment.bundle_kind == 'VERIFIED_UNAPPROVED'
            assert assessment.revocation_status == 'UNSUPPORTED'
            assert not any((assessment.source_authenticated, assessment.current_use_eligible,
                assessment.execution_ready, assessment.research_selection_ready,
                assessment.automatic_recovery_supported, assessment.signature_backup_verified))


def test_raw_signature_authenticates_failure_archive_without_promoting_it():
    with raw_fixture() as e, real_owner() as key:
        request = export(e)
        _, document = independent_document(e.packet, key, e.at)
        clock = lambda:e.at
        result = AUTH.authenticate_bundle_attestation(e.store, e.digest, document,
            authority_provider=CurrentOwnerAuthority(clock=clock), clock=clock)
        assert result.archive_identity_authenticated and result.bundle_kind == 'RAW_ARCHIVED'
        assert not result.current_use_eligible and not result.source_authenticated
        assert request['raw_manifest']['inventory_complete'] is False
        assert e.store.read_raw(e.digest).manifest == e.manifest


def test_export_reads_current_backup_graph_and_never_accepts_storedbundle_as_store():
    with raw_fixture() as e:
        stored = e.store.read_raw(e.digest)
        refused(lambda:R.export_review_packet(stored, e.digest, e.packet, requested_at=e.at,
            expires_at=e.at+timedelta(hours=1), deployment_code_hash='a'*64), 'BUNDLE_REVIEW_STORE_REQUIRED')
        path = STORE.chunk_path(e.store, e.payloads['bad'], backup=True)
        path.write_bytes(b'damaged backup')
        refused(lambda:export(e))
        assert list(e.packet.iterdir()) == []


def test_partial_write_does_not_publish_request_or_overwrite_retry_evidence():
    with raw_fixture() as e:
        actual = R._write_new
        def interrupted(packet, name, raw, *, payload):
            if not payload:
                raise OSError('synthetic interruption before publication')
            return actual(packet, name, raw, payload=payload)
        with patch.object(R, '_write_new', side_effect=interrupted):
            refused(lambda:export(e))
        assert not (e.packet/'request.json').exists()
        before = tree(e.packet)
        assert before and 'payloads/p-bad.bin' in before
        refused(lambda:SIGN.signer._bundle_packet(e.packet))
        refused(lambda:export(e), 'BUNDLE_REVIEW_OUTPUT_EXISTS')
        assert tree(e.packet) == before


def test_payload_mutation_extra_file_and_hardlink_are_refused_before_publication():
    for kind in ('mutate', 'extra', 'hardlink'):
        with raw_fixture() as e:
            actual = R._write_new
            changed = []
            def change(packet, name, raw, *, payload):
                identity = actual(packet, name, raw, payload=payload)
                if payload and not changed:
                    changed.append(True)
                    if kind == 'mutate':
                        (packet.payloads/name).write_bytes(b'other bytes')
                    elif kind == 'extra':
                        (packet.payloads/'unexpected.bin').write_bytes(b'extra')
                    else:
                        os.link(packet.payloads/name, e.base/'second-link')
                return identity
            with patch.object(R, '_write_new', side_effect=change):
                refused(lambda:export(e))
            assert changed and not (e.packet/'request.json').exists()


def test_payload_open_a_b_a_replacement_is_rejected_by_the_original_handle_identity():
    with raw_fixture() as e:
        actual_open = os.open
        injected = []
        original = e.packet/'payloads'/'p-bad.bin'
        saved, substitute = e.base/'saved.bin', e.base/'substitute.bin'
        substitute.write_bytes(b'B'*len(e.payloads['bad']))
        def open_(name, flags, *args, **kwargs):
            if str(name) in ('p-bad.bin', str(original)) and not flags & os.O_CREAT and not injected:
                original.rename(saved); substitute.rename(original)
                descriptor = actual_open(name, flags, *args, **kwargs)
                original.rename(substitute); saved.rename(original)
                injected.append(True)
                return descriptor
            return actual_open(name, flags, *args, **kwargs)
        with patch.object(R.os, 'open', side_effect=open_):
            refused(lambda:export(e))
        assert injected and original.read_bytes() == e.payloads['bad']
        assert not (e.packet/'request.json').exists()


def test_output_root_replacement_cannot_redirect_an_active_export():
    with raw_fixture() as e:
        actual = R._write_new
        saved = e.base/'moved-original'
        injected = []
        def swap(packet, name, raw, *, payload):
            if not injected:
                injected.append(True)
                packet.root.rename(saved); packet.root.mkdir()
            return actual(packet, name, raw, payload=payload)
        with patch.object(R, '_write_new', side_effect=swap):
            refused(lambda:export(e), 'BUNDLE_REVIEW_DIRECTORY_CHANGED')
        assert list(e.packet.iterdir()) == [] and not (saved/'request.json').exists()


def test_nonempty_symlink_private_repository_and_store_outputs_are_not_written():
    with raw_fixture() as e:
        marker = e.packet/'keep'; marker.write_bytes(b'unchanged')
        refused(lambda:export(e), 'BUNDLE_REVIEW_OUTPUT_EXISTS')
        assert marker.read_bytes() == b'unchanged'
        link = e.base/'alias'; link.symlink_to(e.packet, target_is_directory=True)
        for target in (link, e.store.roots.sealed_root, owner.home(), R._REPO):
            refused(lambda target=target:R.export_review_packet(e.store, e.digest, target,
                requested_at=e.at, expires_at=e.at+timedelta(hours=1), deployment_code_hash='a'*64))
        assert marker.read_bytes() == b'unchanged'


def test_independent_packet_reader_rejects_all_extra_missing_changed_linked_and_request_rewrites():
    for kind in ('extra-top', 'extra-payload', 'missing', 'bytes', 'hardlink', 'request'):
        with raw_fixture() as e:
            export(e)
            target = e.packet/'payloads'/'p-bad.bin'
            if kind == 'extra-top':
                (e.packet/'raw-manifest.json').write_bytes(b'not part of the agreed packet')
            elif kind == 'extra-payload':
                (e.packet/'payloads'/'P-BAD.bin').write_bytes(e.payloads['bad'])
            elif kind == 'missing':
                target.unlink()
            elif kind == 'bytes':
                target.write_bytes(b'not the original')
            elif kind == 'hardlink':
                os.link(target, e.base/'alias.bin')
            else:
                body = json.loads((e.packet/'request.json').read_bytes())
                body['raw_manifest']['inventory_complete'] = True
                (e.packet/'request.json').write_text(json.dumps(body))
            refused(lambda:SIGN.signer._bundle_packet(e.packet))


def test_export_invalid_time_or_code_claim_refuses_before_any_destination_write():
    for changes in ({'expires_at':AT}, {'requested_at':AT.replace(tzinfo=None)}, {'deployment_code_hash':'wrong'}):
        with raw_fixture() as e:
            refused(lambda:export(e, **changes))
            assert list(e.packet.iterdir()) == []


def test_cli_export_uses_actual_code_and_authenticate_uses_actual_provider_with_current_clock():
    with raw_fixture() as e, real_owner() as key:
        config = e.base/'limits.json'; config.write_text(json.dumps(asdict(e.store.limits)))
        common = ('--sealed-root', str(e.store.roots.sealed_root), '--backup-root', str(e.store.roots.backup_root),
            '--head-name', 'bundle-head', '--limits', str(config), '--digest', e.digest)
        code, output = invoke('export', *common, '--out', str(e.packet), '--requested-at', e.at.isoformat(),
                              '--expires-at',(e.at+timedelta(hours=1)).isoformat())
        assert code == 0 and output['status'] == 'EXPORTED_UNAPPROVED', output
        assert not output['archive_identity_authenticated'] and not output['execution_ready']
        request, document = independent_document(e.packet, key, e.at)
        assert request['deployment_code_hash'] == owner.code_hash(owner.REPO_ROOT)
        signed = e.base/'archive-attestation.json'; signed.write_bytes(document)
        class Clock:
            @staticmethod
            def now(tz): return e.at
        # Production provider and verified owner chain stay real. Only wall time
        # is frozen so a fixture signature is neither expired nor backdated.
        with patch.object(R, 'datetime', Clock):
            code, output = invoke('authenticate', *common, '--document', str(signed))
        assert code == 0 and output['status'] == 'ARCHIVE_IDENTITY_AUTHENTICATED', output
        assert output['archive_identity_authenticated'] and output['revocation_status'] == 'UNSUPPORTED'
        assert not output['current_use_eligible'] and not output['execution_ready']
        with patch.object(R, 'CurrentOwnerAuthority', side_effect=AssertionError('no owner loading')):
            code, output = invoke('authenticate', *common, '--document', str(signed), '--now', e.at.isoformat())
        assert code == 2 and output['reasons'] == ['BUNDLE_REVIEW_ARGUMENTS_INVALID']


def test_cli_malformed_document_is_rejected_before_actual_owner_loading():
    with raw_fixture() as e:
        config = e.base/'limits.json'; config.write_text(json.dumps(asdict(e.store.limits)))
        bad = e.base/'invalid.json'; bad.write_bytes(b'{malformed')
        common = ('--sealed-root', str(e.store.roots.sealed_root), '--backup-root', str(e.store.roots.backup_root),
            '--head-name','bundle-head','--limits',str(config),'--digest',e.digest)
        with patch.object(R, 'CurrentOwnerAuthority', side_effect=AssertionError('no owner loading')):
            code, output = invoke('authenticate', *common, '--document',str(bad))
        assert code == 2 and not output['archive_identity_authenticated']
        assert not output['current_use_eligible'] and not output['execution_ready']


# Hermetic Win32 call-contract tests; these do not execute native Windows APIs.
import ctypes

class FakeDirectoryAPI:
    def __init__(self, *, fail_at=None):
        self.opened, self.closed, self.attributes, self.indices = [], [], {}, {}
        self.fail_at = fail_at

    def open_directory(self, path):
        if len(self.opened) == self.fail_at:
            raise OSError('injected open refusal')
        self.opened.append(path)
        return len(self.opened)

    def information(self, handle):
        return R.DirectoryInformation(attributes=self.attributes.get(handle, 16),
            volume_serial=1, file_index=self.indices.get(handle, handle))

    def final_path(self, handle):
        return '\\\\?\\' + self.opened[handle-1]

    def close(self, handle):
        self.closed.append(handle)


def pin_refused(call):
    try:
        call()
    except R.WindowsPinError:
        return
    raise AssertionError('pin accepted an invalid native observation')


def use(api, path='C:\\review\\packet', action=None):
    with R.pin_windows_directory(path, api=api) as pin:
        if action:
            action(pin)
        pin.check()


def test_native_open_arguments_deny_write_and_delete_sharing():
    calls = []
    class Kernel:
        def CreateFileW(self, *args):
            calls.append(args)
            return 7
    api = R.NativeDirectoryAPI.__new__(R.NativeDirectoryAPI)
    api._kernel, api._ctypes = Kernel(), ctypes
    assert api.open_directory('C:\\review') == 7
    assert calls == [('C:\\review', 0x80, 0x1, None, 3, 0x02000000 | 0x00200000, None)]


def test_all_ancestors_remain_pinned_and_close_in_reverse_order():
    api = FakeDirectoryAPI()
    def check(pin):
        pin.check()
        assert pin.identity == (1, 3) and pin.root_handle == 3
    use(api, action=check)
    assert api.opened == ['C:\\', 'C:\\review', 'C:\\review\\packet']
    assert api.closed == [3, 2, 1]


def test_partial_open_failure_closes_every_acquired_handle():
    api = FakeDirectoryAPI(fail_at=2)
    pin_refused(lambda: use(api))
    assert api.closed == [2, 1]


def test_finalpath_reparse_identity_and_unavailable_identity_are_refused():
    api = FakeDirectoryAPI()
    original = api.final_path
    api.final_path = lambda handle: '\\\\?\\C:\\different' if handle == 2 else original(handle)
    pin_refused(lambda: use(api))
    assert api.closed == [2, 1]
    for change in ('reparse', 'identity', 'zero'):
        api = FakeDirectoryAPI()
        def mutate(pin):
            if change == 'reparse':
                api.attributes[2] = 16 | 1024
            else:
                api.indices[2] = 999 if change == 'identity' else 0
            pin.check()
        pin_refused(lambda: use(api, action=mutate))
        assert api.closed == [3, 2, 1]


def test_close_failures_do_not_skip_the_remaining_handles():
    api = FakeDirectoryAPI()
    def close(handle):
        api.closed.append(handle)
        if handle == 3:
            raise OSError('injected close failure')
    api.close = close
    pin_refused(lambda: use(api))
    assert api.closed == [3, 2, 1]


def test_reserved_windows_logical_identifiers_use_safe_generated_payload_filenames():
    with STORE.fixture() as e:
        payloads = {'con':b'reserved logical ID is metadata', 'nul':b'', 'com1':b'opaque original'}
        manifest, raw, originals = STORE.raw_archive(e.store, payloads)
        receipt = e.store.archive_raw(raw, originals)
        packet = e.base/'reserved-packet'; packet.mkdir()
        request = R.export_review_packet(e.store, receipt.bundle_digest, packet, requested_at=AT,
            expires_at=AT+timedelta(hours=1), deployment_code_hash=owner.code_hash(owner.REPO_ROOT))
        assert {path.name for path in (packet/'payloads').iterdir()} == {'p-con.bin','p-nul.bin','p-com1.bin'}
        for logical, raw in payloads.items():
            assert (packet/'payloads'/('p-'+logical+'.bin')).read_bytes() == raw
        assert SIGN.signer._bundle_packet(packet)[0] == request
        # Prefixless leaf creation is refused before accessing packet or filesystem.
        refused(lambda:R._write_new(None, 'con.bin', b'bad', payload=True),
                'BUNDLE_REVIEW_GENERATED_NAME_REQUIRED')
