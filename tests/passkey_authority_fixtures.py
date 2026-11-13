"""Genuine disposable archive-authority fixtures, never an operational service.

Only synthetic research inputs cross the explicit app-worker boundary. Owner,
recovery and WebAuthn signatures are real; no accepted authority is mocked.
RP files commit actual temporary bytes but are not an HTTPS/RP implementation.
"""
from __future__ import annotations

import atexit
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import sysconfig
import tempfile
from types import SimpleNamespace

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, ed25519
from fido2 import cbor

from tools.signer import sign as S
from tools.approval_broker import authority_contract as A, contract as C
from tools.approval_broker import bootstrap as B, ledger as L, owner_view as O, release as R

REPO = Path(__file__).resolve().parents[1]
NOW = datetime(2031, 1, 7, 12, tzinfo=timezone.utc)
_PACKETS = {}
_TEMPORARIES = []


def _cleanup():
    for temporary in _TEMPORARIES:
        temporary.cleanup()


atexit.register(_cleanup)


def refused(call, *codes):
    try:
        call()
    except C.PasskeyError as exc:
        assert str(exc).startswith('PASSKEY_'), str(exc)
        if codes:
            assert str(exc) in codes, (str(exc), codes)
        return str(exc)
    raise AssertionError('expected actual authority refusal')


def engine_only(value):
    assert value.observation_scope == 'ENGINE_STATE_ONLY'
    for name in ('operational_channel_ready', 'current_use_eligible', 'source_authenticated',
                 'research_selection_ready', 'execution_ready'):
        assert getattr(value, name) is False, name


def packet_export(kind='raw'):
    """Cache only immutable genuine worker output; every engine reads copied bytes."""
    assert kind in ('raw', 'fixed', 'carry')
    environment = Path(os.environ['PASSKEY_TEST_APP_ENV'])
    assert environment.is_absolute() and environment.is_dir() and not environment.is_symlink()
    if kind not in _PACKETS:
        temporary = tempfile.TemporaryDirectory(prefix='tradegen-passkey-worker-')
        _TEMPORARIES.append(temporary)
        output = Path(temporary.name)
        python = environment/('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
        result = subprocess.run([str(python), '-I', '-B', str(REPO/'tests/passkey_authority_packet_worker.py'),
            '--kind', kind, '--output', str(output), '--requested-at', NOW.isoformat()],
            cwd=REPO, env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'), capture_output=True,
            text=True, timeout=600, check=False)
        assert result.returncode == 0, (result.returncode, result.stdout, result.stderr)
        report = json.loads((output/'worker-report.json').read_text(encoding='ascii'))
        assert Path(report['app_environment']) == environment
        assert report['keyless_count'] == 19 and report['real_home_metadata_unchanged']
        assert report['network_guard'] and report['app_imports_after_protection']
        assert report['actual_store_backup_readback'] and report['independent_packet_readback']
        assert report['owner_code_sha256'] == report['signer_code_sha256']
        assert report['source_inputs'] == 'SYNTHETIC'
        assert not any(report[name] for name in ('source_authenticated', 'research_selection_ready',
                                                'execution_ready', 'operational_channel_ready'))
        _PACKETS[kind] = SimpleNamespace(root=output, report=report, trace=result.stdout)
    return _PACKETS[kind]


def client(kind, challenge, origin):
    return json.dumps(dict(type=kind, challenge=C.b64(challenge), origin=origin,
                           crossOrigin=False), separators=(',', ':')).encode('ascii')


def registration(enrollment, key, identifier):
    numbers = key.public_key().public_numbers()
    cose = {1:2, 3:-7, -1:1, -2:numbers.x.to_bytes(32, 'big'), -3:numbers.y.to_bytes(32, 'big')}
    auth = hashlib.sha256(enrollment.rp.rp_id.encode()).digest()+b'\x45'+bytes(4)
    auth += bytes(16)+len(identifier).to_bytes(2, 'big')+identifier+cbor.encode(cose)
    return C.Registration(enrollment_id=enrollment.enrollment_id, credential_id=identifier,
        client_data_json=client('webauthn.create', enrollment.challenge, enrollment.rp.origin),
        attestation_object=cbor.encode(dict(fmt='none', attStmt={}, authData=auth)), transports=('internal',))


def issue_assertion(e, request, *, counter=2, key=None, origin=None, flags=5):
    raw_client = client('webauthn.get', request.challenge, origin or e.config.rp_origin)
    auth = hashlib.sha256(e.config.rp_id.encode()).digest()+bytes((flags,))+counter.to_bytes(4, 'big')
    signing_key = e.credential_key if key is None else key
    signature = signing_key.sign(auth+hashlib.sha256(raw_client).digest(), ec.ECDSA(hashes.SHA256()))
    return C.Assertion(request_id=request.request_id, credential_id=e.credential_id,
        client_data_json=raw_client, authenticator_data=auth, signature=signature,
        user_handle=e.enrollment.user_handle)


def append_owner(e, kind, data):
    previous = S._head((e.compliance/'owner.jsonl').read_bytes().splitlines(keepends=True))
    stamp = e.clock().astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    line, digest = S.entry_line(e.root_key, previous[0]+1, previous[1], kind, data, stamp)
    with (e.compliance/'owner.jsonl').open('ab') as stream:
        stream.write(line)
        stream.flush(); os.fsync(stream.fileno())
    return A.Head(sequence=previous[0]+1, sha256=digest)


def bootstrap(e, *, install=True):
    e.enrollment = e.engine.prepare_initial_enrollment()
    assert e.enrollment.grant_sha256 is None and e.enrollment.registry_epoch == 0
    e.registration = registration(e.enrollment, e.credential_key, e.credential_id)
    e.proof = e.engine.submit_registration(e.enrollment.enrollment_id, C.registration_bytes(e.registration))
    e.proof_assertion = issue_assertion(e, e.proof, counter=1)
    e.proposal = e.engine.submit_initial_proof(e.proof.request_id, C.assertion_bytes(e.proof_assertion))
    e.credential = B.verify_bootstrap(e.proposal)
    assert e.credential.last_counter == 1 and e.credential.state == 'ACTIVE'
    observation = e.owner_reader.observe(retained=e.ledger.inspect().state.owner_evidence)
    assert observation.deployment_code_sha256 == e.worker.report['owner_code_sha256']
    checkpoint = A.OwnerCheckpoint(fingerprint=S.fingerprint(observation.evidence.public_key_raw),
        code_sha256=observation.deployment_code_sha256, owner_head=observation.evidence.head,
        observed_at=observation.evidence.observed_at)
    R.verify_release(e.broker_root, e.broker_release, dependency_roots=e.dependency_roots)
    R.verify_release(e.rp_root, e.rp_release, dependency_roots=e.dependency_roots)
    body = B.build_grant_body(e.proposal, config=e.config, broker_release=e.broker_release,
        rp_release=e.rp_release, owner=checkpoint, recovery_fingerprint=S.fingerprint(e.recovery_public),
        issued_at=e.clock(), expires_at=e.clock()+timedelta(days=30))
    e.grant = A.GrantDocument(body_bytes=body, signature=e.root_key.sign(A.grant_signing_bytes(body)))
    B.verify_grant_document(e.grant, signer_public_key_raw=e.root_public)
    if install:
        e.install_result = e.engine.install_grant(A.grant_bytes(e.grant), e.proposal.digest)
        assert e.install_result.status == 'APPLIED'
        engine_only(e.install_result)
    return e


def restart(e):
    from tools.approval_broker.engine import Engine
    ledger = L.AuthorityLedger(roots=e.roots, installation=e.installation)
    reader = O.OwnerReader(locations=e.locations, roots=e.trust_roots, clock=e.clock)
    return Engine(config=e.config, ledger=ledger, owner_reader=reader,
        broker_release_root=e.broker_root, broker_release=e.broker_release,
        rp_release_root=e.rp_root, rp_release=e.rp_release,
        dependency_roots=e.dependency_roots, clock=e.clock)


def disable_document(e, *, head=None, key=None):
    body = A.canonical(dict(schema=1, purpose='passkey_archive_authority_disable',
        authority_id=e.config.authority_id, grant_sha256=e.grant.digest,
        expected_head=A.head_document(e.engine.inspect().head if head is None else head),
        reason='DEVICE_LOST', issued_at=C.stamp(e.clock()),
        expires_at=C.stamp(e.clock()+timedelta(seconds=300))))
    signing_key = e.recovery_key if key is None else key
    return A.DisableDocument(body_bytes=body, signature=signing_key.sign(A.disable_signing_bytes(body)))


@contextmanager
def fixture(*, packet_kind='raw', installed=True, now=NOW, target_app_clone=False):
    from tools.approval_broker import packet as P
    from tools.approval_broker.cli import load_installation
    worker = packet_export(packet_kind)
    app_environment = Path(os.environ['PASSKEY_TEST_APP_ENV'])
    with tempfile.TemporaryDirectory(prefix='tradegen-passkey-authority-') as raw:
        base = Path(raw)
        e = SimpleNamespace(base=base, worker=worker, clock_cell=[now], packet_kind=packet_kind)
        e.clock = lambda:e.clock_cell[0]
        e.app_repo = REPO
        if target_app_clone:
            # Copy only the real worker's D14 source closure. Dependencies remain
            # the explicit actual app environment, independently reread below.
            e.app_repo = base/'app'
            e.app_repo.mkdir()
            for name, digest in worker.report['code_files']:
                if name.startswith('venv:'):
                    continue
                relative = Path(name)
                assert not relative.is_absolute() and '..' not in relative.parts
                body = (REPO/relative).read_bytes()
                assert hashlib.sha256(body).hexdigest() == digest
                destination = e.app_repo/relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(body)
        for name in ('primary', 'backup', 'head', 'inbox', 'compliance', 'public', 'broker', 'rp'):
            (base/name).mkdir()
        e.compliance = base/'compliance'
        (e.compliance/'snapshots').mkdir(); (e.compliance/'approved').mkdir()
        e.root_key = ed25519.Ed25519PrivateKey.generate()
        e.recovery_key = ed25519.Ed25519PrivateKey.generate()
        e.root_public = e.root_key.public_key().public_bytes_raw()
        e.recovery_public = e.recovery_key.public_key().public_bytes_raw()
        pem = base/'public'/'owner.pem'
        pem.write_bytes(e.root_key.public_key().public_bytes(serialization.Encoding.PEM,
                                                          serialization.PublicFormat.SubjectPublicKeyInfo))
        code = R.target_deployment_code_hash(e.app_repo, app_environment)
        assert code == worker.report['owner_code_sha256']
        files = worker.report['code_files']
        assert S.sha256_hex(S.canonical_json(files)) == code
        stamp = (now-timedelta(seconds=1)).astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        line, owner_sha = S.entry_line(e.root_key, 1, S.GENESIS_PREV, 'code_approved',
            dict(sha256=code, files=files), stamp)
        (e.compliance/'owner.jsonl').write_bytes(line)
        initial_head = A.Head(sequence=1, sha256=owner_sha)
        (e.compliance/'snapshots'/'initial.json').write_text(json.dumps(dict(head=[1, owner_sha])))
        e.trust_roots = O.TrustRoots(initial_public_key_raw=e.root_public,
            initial_owner_head=initial_head, recovery_public_key_raw=e.recovery_public)
        e.locations = O.OwnerLocations(app_repo=e.app_repo, app_environment=app_environment,
                                      compliance_root=e.compliance, public_key_path=pem)
        e.broker_root, e.rp_root = base/'broker', base/'rp'
        shutil.copytree(REPO/'tools'/'approval_broker', e.broker_root/'tools'/'approval_broker')
        (e.broker_root/'tools'/'signer').mkdir()
        shutil.copyfile(REPO/'tools'/'signer'/'sign.py', e.broker_root/'tools'/'signer'/'sign.py')
        for relative in ('tools/__init__.py', 'tools/signer/__init__.py'):
            source = REPO/relative
            if source.exists(): shutil.copyfile(source, e.broker_root/relative)
        (e.rp_root/'index.html').write_bytes(b'<!doctype html><title>Disposable RP byte commitment</title>')
        (e.rp_root/'policy.json').write_bytes(b'{"fixture":true,"operational":false}')
        e.dependency_roots = tuple(sorted({Path(sysconfig.get_path(name)) for name in ('purelib', 'platlib')}))
        e.broker_release = R._release_inventory(e.broker_root, role='BROKER', dependency_roots=e.dependency_roots)
        e.rp_release = R._release_inventory(e.rp_root, role='RP', dependency_roots=())
        transport = ed25519.Ed25519PrivateKey.generate().public_key().public_bytes_raw()
        spki = ec.generate_private_key(ec.SECP256R1()).public_key().public_bytes(
            serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
        mtls_spki = ec.generate_private_key(ec.SECP256R1()).public_key().public_bytes(
            serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
        e.config = A.BrokerConfig(authority_id=secrets.token_hex(32), service_identity='fixture-service',
            client_identity='fixture-client', pipe_name='fixture-archive-pipe', authority_root=str(base/'primary'),
            backup_root=str(base/'backup'), head_root=str(base/'head'), packet_inbox=str(base/'inbox'),
            app_repo=str(e.app_repo), rp_origin='https://approve.test', rp_id='approve.test',
            rp_transport_spki_sha256=hashlib.sha256(spki).hexdigest(), broker_transport_public_key=transport,
            broker_mtls_spki_sha256=hashlib.sha256(mtls_spki).hexdigest())
        e.roots = L.LedgerRoots(primary=base/'primary', backup=base/'backup', head=base/'head')
        e.config_path = base/'config.json'
        e.config_path.write_bytes(A.config_bytes(e.config))
        (base/'broker-manifest.json').write_bytes(A.release_bytes(e.broker_release))
        (base/'rp-manifest.json').write_bytes(A.release_bytes(e.rp_release))
        sidecar = dict(schema=1, config_sha256=e.config.digest,
            owner_locations=dict(app_repo=str(e.app_repo), app_environment=str(app_environment),
                                 compliance_root=str(e.compliance), public_key_path=str(pem)),
            trust_roots=dict(initial_public_key_raw=C.b64(e.root_public),
                initial_owner_head=A.head_document(initial_head), recovery_public_key_raw=C.b64(e.recovery_public)),
            broker_release_root=str(e.broker_root), broker_release_manifest=str(base/'broker-manifest.json'),
            rp_release_root=str(e.rp_root), rp_release_manifest=str(base/'rp-manifest.json'),
            dependency_roots=[str(p) for p in e.dependency_roots])
        e.sidecar_path = e.config_path.with_name(e.config_path.name+'.installation.json')
        e.sidecar_path.write_bytes(A.canonical(sidecar))
        e.operator_installation = load_installation(e.config_path)
        e.installation = e.operator_installation.ledger_installation
        e.ledger = L.prepare_authority_store(roots=e.roots, installation=e.installation)
        e.owner_reader = O.OwnerReader(locations=e.locations, roots=e.trust_roots, clock=e.clock)
        e.engine = restart(e)
        # Expose the actual reader used by the engine, not a positive status callback.
        e.owner_reader = e.engine.owner_reader
        e.ledger = e.engine.ledger
        e.credential_key = ec.generate_private_key(ec.SECP256R1())
        e.credential_id = secrets.token_bytes(32)
        staging = base/'inbox'/'operator-staging'
        shutil.copytree(worker.root/'packet', staging)
        snapshot = P.read_packet(staging)
        e.packet = base/'inbox'/('packet-'+snapshot.packet_sha256)
        staging.rename(e.packet)
        e.packet_snapshot = P.read_packet(e.packet)
        assert e.packet_snapshot.packet_sha256 == snapshot.packet_sha256
        e.restart = lambda:restart(e)
        e.issue_assertion = lambda request, **options:issue_assertion(e, request, **options)
        if installed:
            bootstrap(e)
        yield e
