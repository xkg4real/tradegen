"""Explicit local archive-engine tools, never service provisioning or activation.

Installation paths come only from an exact operator sidecar. Importing this
module performs no I/O and imports no app module, engine, HTTP stack or secrets.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import stat

from . import authority_contract as A, contract as C

_MAX = 2*1024*1024
_REFUSED_ATTRIBUTES = 0x400 | 0x1000 | 0x40000 | 0x400000


def _identity(info):
    return info.st_dev, info.st_ino, info.st_mode, info.st_size, info.st_mtime_ns, info.st_ctime_ns


def _path(value):
    C.need(isinstance(value, Path) and value.is_absolute() and '..' not in value.parts,
           'PASSKEY_FORMAT_INVALID')
    return value


def _parents(path):
    path = _path(path)
    result = []
    try:
        for part in reversed(path.parents):
            info = part.lstat()
            C.need(stat.S_ISDIR(info.st_mode) and not stat.S_ISLNK(info.st_mode)
                   and not getattr(info,'st_file_attributes',0)&_REFUSED_ATTRIBUTES, 'PASSKEY_FORMAT_INVALID')
            result.append((part,(info.st_dev,info.st_ino,info.st_mode)))
    except OSError:
        raise C.PasskeyError('PASSKEY_FORMAT_INVALID') from None
    return tuple(result)


def checked_directory(path):
    before = _parents(path)
    try:
        info = path.lstat()
        C.need(stat.S_ISDIR(info.st_mode) and not stat.S_ISLNK(info.st_mode)
               and not getattr(info,'st_file_attributes',0)&_REFUSED_ATTRIBUTES, 'PASSKEY_FORMAT_INVALID')
        C.need(before == _parents(path), 'PASSKEY_FORMAT_INVALID')
        return info.st_dev,info.st_ino,info.st_mode
    except OSError:
        raise C.PasskeyError('PASSKEY_FORMAT_INVALID') from None


def read_file(path, *, maximum=_MAX):
    parents = _parents(path)
    try:
        before = path.lstat()
        C.need(stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and not stat.S_ISLNK(before.st_mode)
               and not getattr(before,'st_file_attributes',0)&_REFUSED_ATTRIBUTES
               and 0 < before.st_size <= maximum, 'PASSKEY_FORMAT_INVALID')
        fd = os.open(path, os.O_RDONLY | getattr(os,'O_NOFOLLOW',0))
        with os.fdopen(fd,'rb') as stream:
            C.need(_identity(os.fstat(stream.fileno())) == _identity(before), 'PASSKEY_FORMAT_INVALID')
            raw = stream.read(maximum+1)
            C.need(len(raw) == before.st_size and _identity(os.fstat(stream.fileno())) == _identity(before),
                   'PASSKEY_FORMAT_INVALID')
        C.need(_identity(path.lstat()) == _identity(before) and parents == _parents(path), 'PASSKEY_FORMAT_INVALID')
        return raw
    except OSError:
        raise C.PasskeyError('PASSKEY_FORMAT_INVALID') from None


def write_new_file(path, raw):
    """Exclusive output under the existing retained standalone parent pin."""
    from tools.signer import sign as S
    C.binary(raw, A.MAX_EVENT_BYTES)
    path = _path(path)
    try:
        with S._BundlePin(path.parent) as parent:
            S._bundle_write_pinned(path, raw, parent)
            C.need(S._bundle_read(path, A.MAX_EVENT_BYTES, parent_pin=parent)[0] == raw,
                   'PASSKEY_STORE_INDETERMINATE')
    except C.PasskeyError:
        raise
    except (OSError, ValueError):
        raise C.PasskeyError('PASSKEY_STORE_INDETERMINATE') from None


@dataclass(frozen=True, slots=True, kw_only=True)
class Installation:
    config: A.BrokerConfig = field(repr=False)
    locations: object = field(repr=False)
    trust_roots: object = field(repr=False)
    ledger_roots: object = field(repr=False)
    ledger_installation: object = field(repr=False)
    broker_release_root: Path = field(repr=False)
    broker_release: A.ReleaseManifest = field(repr=False)
    rp_release_root: Path = field(repr=False)
    rp_release: A.ReleaseManifest = field(repr=False)
    dependency_roots: tuple[Path,...] = field(repr=False)
    sidecar_sha256: str


def load_installation(config_path):
    """Read only: exact operator paths/pins; no missing store/head initialization."""
    from .ledger import LedgerInstallation, LedgerRoots
    from .owner_view import OwnerLocations, TrustRoots
    config_path = _path(config_path)
    config_raw = read_file(config_path)
    config = A.parse_config(config_raw)
    sidecar_path = config_path.with_name(config_path.name+'.installation.json')
    raw = read_file(sidecar_path)
    data = A.decode(raw, maximum=_MAX)
    C.keys(data, ('schema','config_sha256','owner_locations','trust_roots','broker_release_root',
        'broker_release_manifest','rp_release_root','rp_release_manifest','dependency_roots'))
    C.need(type(data['schema']) is int and data['schema']==1 and data['config_sha256']==config.digest
           and A.canonical(data, maximum=_MAX)==raw)
    C.keys(data['owner_locations'],('app_repo','app_environment','compliance_root','public_key_path'))
    C.keys(data['trust_roots'],('initial_public_key_raw','initial_owner_head','recovery_public_key_raw'))
    def explicit(value):
        C.need(type(value) is str and 0 < len(value) <= 4096 and '\0' not in value)
        return _path(Path(value))
    locations = OwnerLocations(**{name:explicit(value) for name,value in data['owner_locations'].items()})
    roots = TrustRoots(initial_public_key_raw=C.unb64(data['trust_roots']['initial_public_key_raw'],32,minimum=32),
        initial_owner_head=A.parse_head(data['trust_roots']['initial_owner_head']),
        recovery_public_key_raw=C.unb64(data['trust_roots']['recovery_public_key_raw'],32,minimum=32))
    C.need(locations.app_repo == Path(config.app_repo) and roots.initial_owner_head.sequence >= 1)
    ledger_roots = LedgerRoots(primary=explicit(config.authority_root), backup=explicit(config.backup_root),
                              head=explicit(config.head_root))
    operational_roots = (ledger_roots.primary,ledger_roots.backup,ledger_roots.head,explicit(config.packet_inbox))
    C.need(all(not left.is_relative_to(right) and not right.is_relative_to(left)
               for n,left in enumerate(operational_roots) for right in operational_roots[n+1:]))
    broker_root, rp_root = explicit(data['broker_release_root']), explicit(data['rp_release_root'])
    C.need(type(data['dependency_roots']) is list and len(data['dependency_roots']) <= 256)
    dependencies = tuple(explicit(p) for p in data['dependency_roots'])
    C.need(len(set(dependencies)) == len(dependencies))
    directories = operational_roots+(locations.app_repo,locations.app_environment,locations.compliance_root,
                                    broker_root,rp_root)+dependencies
    identities = tuple(checked_directory(directory) for directory in directories)
    # Existence/type/identity is checked independently; owner cryptography happens
    # in OwnerReader at each operation, never via a boolean in this sidecar.
    read_file(locations.public_key_path, maximum=65536)
    broker_manifest = explicit(data['broker_release_manifest'])
    rp_manifest = explicit(data['rp_release_manifest'])
    broker_raw, rp_raw = read_file(broker_manifest), read_file(rp_manifest)
    broker, rp = A.parse_release(broker_raw), A.parse_release(rp_raw)
    C.need(broker.role == 'BROKER' and rp.role == 'RP')
    digest = A.record_digest('operator-installation',raw)
    installation = LedgerInstallation(authority_id=config.authority_id, config_sha256=config.digest,
                                       operator_paths_sha256=digest, roots=roots)
    C.need(identities == tuple(checked_directory(directory) for directory in directories)
           and read_file(config_path)==config_raw and read_file(sidecar_path)==raw
           and read_file(broker_manifest)==broker_raw and read_file(rp_manifest)==rp_raw,
           'PASSKEY_OWNER_CHANGED')
    return Installation(config=config,locations=locations,trust_roots=roots,ledger_roots=ledger_roots,
        ledger_installation=installation,broker_release_root=broker_root,broker_release=broker,
        rp_release_root=rp_root,rp_release=rp,dependency_roots=dependencies,sidecar_sha256=digest)


def _result(value):
    if hasattr(value,'status'):
        result = dict(status=value.status,request_id=value.request_id,application_id=value.application_id,
                      head=None if value.head is None else A.head_document(value.head),reason=value.reason)
    else:
        result = dict(status='PREPARED_UNAPPROVED')
    return result | dict(observation_scope='ENGINE_STATE_ONLY',operational_channel_ready=False,
                        current_use_eligible=False,execution_ready=False)


def main(argv=None):
    parser = argparse.ArgumentParser(description='Local archive engine only; operational approval channel is not implemented.')
    parser.add_argument('--config',required=True,type=Path)
    commands = parser.add_subparsers(dest='command',required=True)
    commands.add_parser('prepare-authority-store',help='Explicit empty store preparation; grants no authority.')
    install = commands.add_parser('install-grant')
    install.add_argument('--document',required=True,type=Path)
    install.add_argument('--proposal-id',required=True)
    disable = commands.add_parser('archive-authority-disable',help='Install an independently signed recovery-root disable.')
    disable.add_argument('--document',required=True,type=Path)
    commands.add_parser('inspect')
    args = parser.parse_args(argv)
    try:
        if args.command == 'prepare-authority-store':
            from .ledger import prepare_authority_store
            installed = load_installation(args.config)
            prepare_authority_store(roots=installed.ledger_roots,installation=installed.ledger_installation)
            result = _result(None)
        else:
            from .engine import Engine
            engine = Engine.open(args.config)
            if args.command=='install-grant':
                result = _result(engine.install_grant(read_file(args.document), args.proposal_id))
            elif args.command=='archive-authority-disable':
                result = _result(engine.install_disable(read_file(args.document)))
            else:
                state = engine.inspect()
                result = dict(status='HISTORICAL_ENGINE_STATE',authority_id=state.authority_id,
                    head=A.head_document(state.head),grant_sha256=state.grant_sha256,registry_epoch=state.registry_epoch,
                    disabled=state.disabled,operational_channel_ready=False,current_use_eligible=False,execution_ready=False)
        print(json.dumps(result,sort_keys=True,separators=(',',':')))
        return 0
    except C.PasskeyError as exc:
        print(json.dumps(dict(status='REFUSED',reason=str(exc),operational_channel_ready=False,
                              current_use_eligible=False,execution_ready=False),sort_keys=True,separators=(',',':')))
        return 2


if __name__=='__main__':
    raise SystemExit(main())
