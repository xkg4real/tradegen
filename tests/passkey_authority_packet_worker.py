"""Fixed test-only app-environment worker for genuine BundleStore packet export.

The parent supplies an explicit app interpreter, never executable source. Source
and market inputs are synthetic. Export/audit success is archive identity only;
this worker does not establish source, selection, passkey or execution authority.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta
import hashlib
import json
import os
from pathlib import Path
import socket
import sys
from unittest.mock import patch

KEYS = """KIS_APP_KEY KIS_APP_SECRET KIS_ACCOUNT_8 KIS_ACCOUNT_PD UPBIT_ACCESS_KEY
UPBIT_SECRET_KEY OKX_API_KEY OKX_API_SECRET OKX_API_PASSPHRASE OPENDART_API_KEY KRX_API_KEY
FMP_API_KEY ANTHROPIC_API_KEY GS_CLIENT_ID GS_CLIENT_SECRET FINVIZ_API_KEY ALPACA_API_KEY
ALPACA_SECRET_KEY FXMACRODATA_API_KEY""".split()
REPO = Path(__file__).resolve().parents[1]


def metadata():
    # Metadata only: never read either actual owner home's file contents.
    result = []
    for name in ('.tradegen', '.nextgen'):
        root = Path.home()/name
        result.append([(p.relative_to(root).as_posix(), p.stat().st_size, p.stat().st_mtime_ns)
                       for p in sorted(root.rglob('*')) if p.is_file()] if root.exists() else [])
    return result


def no_network(*args, **kwargs):
    raise AssertionError('PASSKEY_WORKER_NETWORK_FORBIDDEN')


def export_packet(kind, output, at):
    # These are the first non-stdlib imports, after KEYLESS and home protections.
    from core.compliance import owner
    from execution_launch import bundle_review as R
    from tools.signer import sign as S
    from tests import launch_research_bundle_store as STORE
    from tests import launch_research_bundle as REAL

    owner_files = owner.code_files(REPO)
    signer_files = S.code_files(REPO)
    code = owner.code_hash(REPO)
    assert owner_files == signer_files and code == S.code_hash(REPO)
    assert any(name.startswith('venv:cryptography-') for name, _ in owner_files)
    assert any(name.startswith('venv:PyYAML-') for name, _ in owner_files)
    packet = output/'packet'; packet.mkdir()
    if kind == 'raw':
        with STORE.fixture() as e:
            manifest, raw, payloads = STORE.raw_archive(e.store)
            receipt = e.store.archive_raw(raw, payloads)
            durable = e.store.read_raw(receipt.bundle_digest, require_backup=True)
            assert durable.manifest == manifest and dict(durable.files) == payloads
            request = R.export_review_packet(e.store, receipt.bundle_digest, packet,
                requested_at=at, expires_at=at+timedelta(hours=1), deployment_code_hash=code)
            assert request['bundle_kind'] == 'RAW_ARCHIVED'
            assert request['raw_manifest']['inventory_complete'] is False
    else:
        with REAL.fixture(carry=kind == 'carry') as e:
            result = REAL.finalize(e)
            assert result.status == 'VERIFIED_UNAPPROVED', result
            raw = e.store.read_raw(result.input_archive_digest, require_backup=True)
            verified = e.store.read_verified(result.bundle_digest, require_backup=True)
            assert raw.manifest_bytes and verified.manifest_bytes
            request = R.export_review_packet(e.store, result.bundle_digest, packet,
                requested_at=at, expires_at=at+timedelta(hours=1), deployment_code_hash=code)
            assert request['bundle_kind'] == 'VERIFIED_UNAPPROVED'
    independently_read, _ = S._bundle_packet(packet)
    assert independently_read == request
    payload_rows = request['payload_files']
    for row in payload_rows:
        body = (packet/'payloads'/('p-'+row['logical_id']+'.bin')).read_bytes()
        assert len(body) == row['byte_count'] and hashlib.sha256(body).hexdigest() == row['sha256']
    return dict(kind=kind, app_environment=sys.prefix, app_interpreter=sys.executable,
        owner_code_sha256=code, signer_code_sha256=S.code_hash(REPO), code_files=owner_files,
        bundle_digest=request['bundle_digest'], bundle_kind=request['bundle_kind'],
        request_sha256=request['request_sha256'], payload_count=len(payload_rows),
        actual_store_backup_readback=True, independent_packet_readback=True,
        source_inputs='SYNTHETIC', source_authenticated=False, research_selection_ready=False,
        execution_ready=False, operational_channel_ready=False)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kind', choices=('raw', 'fixed', 'carry'), required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--requested-at', required=True)
    args = parser.parse_args(argv)
    assert args.output.is_absolute() and args.output.is_dir() and not list(args.output.iterdir())
    at = datetime.fromisoformat(args.requested_at)
    assert at.tzinfo is not None
    for key in KEYS:
        os.environ[key] = '<unset>'
    before = metadata()
    sys.path.insert(0, str(REPO))
    report = None
    try:
        with patch.object(socket.socket, 'connect', no_network), \
                patch.object(socket.socket, 'connect_ex', no_network), \
                patch.object(socket, 'create_connection', no_network):
            report = export_packet(args.kind, args.output, at)
    finally:
        assert metadata() == before, 'PASSKEY_WORKER_REAL_HOME_METADATA_CHANGED'
    report.update(keyless_count=len(KEYS), real_home_metadata_unchanged=True,
                  network_guard=True, app_imports_after_protection=True)
    (args.output/'worker-report.json').write_text(json.dumps(report, sort_keys=True)+'\n', encoding='ascii')
    print(json.dumps(dict(kind=args.kind, payload_count=report['payload_count'], checks='COMPLETE')))


if __name__ == '__main__':
    main()
